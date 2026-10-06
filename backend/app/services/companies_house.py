"""
Client for the Companies House Public Data API.
Basic auth: API key as username, empty password.

One shared httpx.AsyncClient per CompaniesHouseClient (get_ch_client() keeps a single
instance). Every request goes through _request(), which:
  - takes a token from the in-process rate limiter (500 req / 5 min, reconciled with
    CH's X-Ratelimit-Remaining header),
  - retries up to 2 times with jittered exponential backoff on 5xx and network errors only,
  - raises CompaniesHouseError (never containing the API key) for any non-2xx outcome.
"""

import math

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_random_exponential

from app.config import settings
from app.core.rate_limiter import TokenBucket, seconds_until_reset

CH_BASE = "https://api.company-information.service.gov.uk"
CH_DOCUMENT_BASE = "https://document-api.company-information.service.gov.uk"

CH_TIMEOUT_SECONDS = 10.0
CH_MAX_RETRIES = 2
CH_PAGE_SIZE = 100
CH_MAX_PAGES = 100  # safety stop: 10,000 items


class CompaniesHouseError(Exception):
    """A failed Companies House call. Deliberately carries no request headers or auth."""

    def __init__(self, status_code: int, retry_after: int | None = None) -> None:
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f"Companies House request failed with status {status_code}")


class _TransientError(Exception):
    """Internal: a 5xx response, raised so tenacity retries it."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, (_TransientError, httpx.TransportError))


class CompaniesHouseClient:
    def __init__(
        self,
        api_key: str | None = None,
        rate_limiter: TokenBucket | None = None,
        retry_wait=None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=CH_BASE,
            auth=(api_key if api_key is not None else settings.ch_api_key, ""),
            timeout=CH_TIMEOUT_SECONDS,
        )
        self._limiter = rate_limiter or TokenBucket()
        self._retry_wait = retry_wait or wait_random_exponential(multiplier=0.5, max=4)

    async def _request(self, url: str, params: dict | None = None, **kwargs) -> httpx.Response:
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_is_transient),
                stop=stop_after_attempt(CH_MAX_RETRIES + 1),
                wait=self._retry_wait,
                reraise=True,
            ):
                with attempt:
                    await self._limiter.acquire()
                    r = await self._client.get(url, params=params, **kwargs)
                    self._limiter.update_from_headers(r.headers)
                    if r.status_code >= 500:
                        raise _TransientError(r)
        except _TransientError as exc:
            raise CompaniesHouseError(exc.response.status_code) from None
        except httpx.TimeoutException:
            raise CompaniesHouseError(504) from None
        except httpx.TransportError:
            raise CompaniesHouseError(502) from None

        if r.status_code == 429:
            raise CompaniesHouseError(429, retry_after=_retry_after_seconds(r))
        if r.status_code >= 400:
            raise CompaniesHouseError(r.status_code)
        return r

    async def _get(self, path: str, params: dict | None = None) -> dict:
        return (await self._request(path, params=params)).json()

    async def _get_all_pages(self, path: str) -> dict:
        """Page through a CH list endpoint until total_results items have been collected."""
        first: dict | None = None
        items: list = []
        start_index = 0
        for _ in range(CH_MAX_PAGES):
            page = await self._get(path, params={"items_per_page": CH_PAGE_SIZE, "start_index": start_index})
            if first is None:
                first = page
            batch = page.get("items") or []
            items.extend(batch)
            start_index += len(batch)
            total = page.get("total_results")
            if not batch or total is None or len(items) >= total:
                break
        result = dict(first or {})
        result["items"] = items
        result["start_index"] = 0
        result["items_per_page"] = len(items)
        return result

    async def search_companies(self, query: str, items_per_page: int = 20, start_index: int = 0) -> dict:
        return await self._get("/search/companies", params={
            "q": query,
            "items_per_page": items_per_page,
            "start_index": start_index,
        })

    async def get_company(self, number: str) -> dict:
        return await self._get(f"/company/{number}")

    async def get_officers(self, number: str) -> dict:
        return await self._get_all_pages(f"/company/{number}/officers")

    async def get_pscs(self, number: str) -> dict:
        return await self._get_all_pages(f"/company/{number}/persons-with-significant-control")

    async def get_psc_statements(self, number: str) -> dict:
        return await self._get_all_pages(f"/company/{number}/persons-with-significant-control-statements")

    async def get_exemptions(self, number: str) -> dict:
        return await self._get(f"/company/{number}/exemptions")

    async def get_filings(self, number: str, items_per_page: int = 25) -> dict:
        return await self._get(f"/company/{number}/filing-history", params={"items_per_page": items_per_page})

    async def get_filing_document(self, number: str, transaction_id: str) -> bytes:
        # transaction_id is not a valid document-api ID — look up the filing first
        # to read links.document_metadata, which embeds the actual document ID.
        meta = await self._get(f"/company/{number}/filing-history/{transaction_id}")
        document_metadata_url = (meta.get("links") or {}).get("document_metadata")
        if not document_metadata_url:
            raise ValueError(f"Filing {transaction_id} has no document available")

        doc_id = document_metadata_url.rstrip("/").rsplit("/", 1)[-1]

        content_url = f"{CH_DOCUMENT_BASE}/document/{doc_id}/content"
        r = await self._request(content_url, follow_redirects=True)
        return r.content

    async def close(self) -> None:
        await self._client.aclose()


def _retry_after_seconds(r: httpx.Response) -> int:
    header = r.headers.get("Retry-After")
    if header and header.isdigit():
        return max(1, int(header))
    return max(1, math.ceil(seconds_until_reset(r.headers.get("X-Ratelimit-Reset"))))

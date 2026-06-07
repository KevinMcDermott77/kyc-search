"""
Client for the Companies House Public Data API.
Basic auth: API key as username, empty password.
Retries on 5xx with exponential backoff (tenacity).
Rate-limited via Redis token bucket.
"""

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.rate_limiter import acquire_ch_token

CH_BASE = "https://api.company-information.service.gov.uk"
CH_DOCUMENT_BASE = "https://document-api.company-information.service.gov.uk"


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


class CompaniesHouseClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=CH_BASE,
            auth=(settings.ch_api_key, ""),
            timeout=15.0,
        )

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        await acquire_ch_token()
        r = await self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def search_companies(self, query: str, items_per_page: int = 20, start_index: int = 0) -> dict:
        return await self._get("/search/companies", params={
            "q": query,
            "items_per_page": items_per_page,
            "start_index": start_index,
        })

    async def get_company(self, number: str) -> dict:
        return await self._get(f"/company/{number}")

    async def get_officers(self, number: str, items_per_page: int = 100) -> dict:
        return await self._get(f"/company/{number}/officers", params={"items_per_page": items_per_page})

    async def get_pscs(self, number: str) -> dict:
        return await self._get(f"/company/{number}/persons-with-significant-control")

    async def get_filings(self, number: str, items_per_page: int = 25) -> dict:
        return await self._get(f"/company/{number}/filing-history", params={"items_per_page": items_per_page})

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_filing_document(self, number: str, transaction_id: str) -> bytes:
        # transaction_id is not a valid document-api ID — look up the filing first
        # to read links.document_metadata, which embeds the actual document ID.
        await acquire_ch_token()
        meta_response = await self._client.get(f"/company/{number}/filing-history/{transaction_id}")
        meta_response.raise_for_status()
        document_metadata_url = (meta_response.json().get("links") or {}).get("document_metadata")
        if not document_metadata_url:
            raise ValueError(f"Filing {transaction_id} has no document available")

        doc_id = document_metadata_url.rstrip("/").rsplit("/", 1)[-1]

        await acquire_ch_token()
        content_url = f"{CH_DOCUMENT_BASE}/document/{doc_id}/content"
        r = await self._client.get(content_url, follow_redirects=True)
        r.raise_for_status()
        return r.content

    async def close(self) -> None:
        await self._client.aclose()

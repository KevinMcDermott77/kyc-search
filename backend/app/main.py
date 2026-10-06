import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import User  # noqa: F401
from app.models import AuditLog, Case, CaseNote, Company, Filing, Officer, Psc  # noqa: F401
from app.routers import admin, audit, auth, cases, companies, ownership, screening, search
from app.services.companies_house import CompaniesHouseError

logger = logging.getLogger(__name__)


async def _seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            user = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                is_admin=True,
            )
            db.add(user)
            await db.commit()
            print(f"[startup] Created admin user: {settings.admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_admin()
    yield
    await engine.dispose()


app = FastAPI(
    title="KYC Search Engine",
    description="UK Companies House KYC lookup tool",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:3000",
        "https://fabulous-perfection-production-2b31.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Fetched-At", "Retry-After"],
)

app.include_router(auth.router)
app.include_router(search.router)
app.include_router(companies.router)
app.include_router(ownership.router)
app.include_router(screening.router)
app.include_router(cases.router)
app.include_router(audit.router)
app.include_router(admin.router)


@app.exception_handler(CompaniesHouseError)
async def companies_house_error_handler(request: Request, exc: CompaniesHouseError) -> JSONResponse:
    # CH rate limiting is our capacity problem, not the caller's: surface as 503 + Retry-After.
    if exc.status_code == 429:
        return JSONResponse(
            status_code=503,
            content={"detail": "Companies House rate limit reached, retry later"},
            headers={"Retry-After": str(exc.retry_after or 60)},
        )
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"detail": "Not found at Companies House"})
    # An upstream 5xx is a gateway failure on our side: never surface it as our own 500.
    status_code = exc.status_code
    if status_code >= 500 and status_code not in (503, 504):
        status_code = 502
    return JSONResponse(status_code=status_code, content={"detail": "Companies House request failed"})


@app.exception_handler(OperationalError)
@app.exception_handler(InterfaceError)
@app.exception_handler(SQLAlchemyTimeoutError)
async def database_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    # Lost connection / pool exhaustion: transient, so 503 rather than an unmapped 500.
    # Only the type is logged: the message can carry SQL parameters.
    logger.warning("Database unavailable on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable, retry later"},
        headers={"Retry-After": "5"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}
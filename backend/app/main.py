from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import User  # noqa: F401
from app.models import AuditLog, Case, CaseNote, Company, Filing, Officer, Psc  # noqa: F401
from app.routers import admin, audit, auth, cases, companies, ownership, screening, search


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
)

app.include_router(auth.router)
app.include_router(search.router)
app.include_router(companies.router)
app.include_router(ownership.router)
app.include_router(screening.router)
app.include_router(cases.router)
app.include_router(audit.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User
from app.services.companies_house import CompaniesHouseClient
from app.services.mock_data import MockCompaniesHouseClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_ch_client: CompaniesHouseClient | MockCompaniesHouseClient | None = None


def get_ch_client() -> CompaniesHouseClient | MockCompaniesHouseClient:
    global _ch_client
    if _ch_client is None:
        if settings.mock_mode:
            _ch_client = MockCompaniesHouseClient()
        else:
            _ch_client = CompaniesHouseClient()
    return _ch_client


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    email = payload.get("sub")
    result = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user

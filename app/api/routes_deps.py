import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from app.agents.travel_agent import TravelAgent
from app.core.lifespan_db import create_session
from app.models.users import Users
from app.utils.jwt import bearer_scheme, decode_access_token

logger = logging.getLogger(__name__)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(create_session)
) -> Users:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(credentials.credentials)
    email: str = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    result = await db.execute(select(Users).where(Users.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user

async def require_admin(current_user: Users = Depends(get_current_user)) -> Users:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return current_user


async def logging_middleware(request: Request, call_next):
    response = await call_next(request)
    logger.info(f"← {response.status_code} {request.method} {request.url} ")

    return response

def get_travel_agent(request: Request) -> TravelAgent:
    return request.app.state.travel_agent
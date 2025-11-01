from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.user import hash_password, require_role
from db.db import db as database
from db.models import User, UserRole

router = APIRouter()


@router.get("/")
async def list_users(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(database),
    _: dict = Depends(require_role(UserRole.Admin))
):
    # 查询总用户数
    total_result = await db.execute(select(func.count(User.id)))
    total_count = total_result.scalar_one()

    # 分页查询用户
    offset = (page - 1) * page_size
    stmt = select(User.username, User.role).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    users = result.all()

    return {
        "total_count": total_count,
        "total_pages": ceil(total_count / page_size),
        "page": page,
        "page_size": page_size,
        "items": [{"username": u.username, "role": u.role} for u in users]
    }


@router.post("/")
async def create_user(
    data: dict,
    db: AsyncSession = Depends(database),
    _: dict = Depends(require_role(UserRole.Admin))
):
    username = data.get("username")
    password = data.get("password")
    role = int(data.get("role"))
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username or password")

    # 检查是否存在
    # noinspection PyTypeChecker
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(username=username, password=hash_password(password), role=role)
    db.add(new_user)
    await db.commit()
    return {"message": "User created successfully"}


@router.delete("/{username}")
async def delete_user(
    username: str,
    db: AsyncSession = Depends(database),
    _: dict = Depends(require_role(UserRole.Admin))
):
    # noinspection PyTypeChecker
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}


@router.put("/{username}/password")
async def update_password(
    username: str,
    data: dict,
    db: AsyncSession = Depends(database),
    _: dict = Depends(require_role(UserRole.Admin))
):
    password = data.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Missing password")

    # noinspection PyTypeChecker
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = hash_password(password)
    db.add(user)
    await db.commit()
    return {"message": "Password updated successfully"}

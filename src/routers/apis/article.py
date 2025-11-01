from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import JSONResponse

from core.user import require_role
from db.models import Markdown, UserRole
from db.db import db as database

router = APIRouter()


@router.get("/")
async def get_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(database),
    _: dict = Depends(require_role(UserRole.Admin))
):
    # 查询总文章数
    total_result = await db.execute(select(func.count(Markdown.id)))
    total_count = total_result.scalar_one()

    # 分页查询文章
    offset = (page - 1) * page_size
    stmt = select(Markdown.id, Markdown.title, Markdown.date).order_by(Markdown.date.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    articles = result.all()

    return {
        "total_count": total_count,
        "total_pages": ceil(total_count / page_size),
        "page": page,
        "page_size": page_size,
        "items": [{"id": a.id, "title": a.title, "date": a.date} for a in articles]
    }


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(database),
    _: dict = Depends(require_role(UserRole.Admin))
):
    # noinspection PyTypeChecker
    result = await db.execute(select(Markdown).where(Markdown.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    await db.delete(article)
    await db.commit()
    return JSONResponse(status_code=204, content=None)
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import HTMLResponse

from core.user import require_role
from db import db
from db.models import Markdown, UserRole
from core.template import templates

router = APIRouter()


@router.get("/view", response_class=HTMLResponse)
async def read_index(
        request: Request,
        q: str = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1),
        start_date: str = Query(None),
        end_date: str = Query(None),
        database: AsyncSession = Depends(db.db),
        _: dict = Depends(require_role(UserRole.User))
):
    # 构建查询
    stmt = select(Markdown)
    if q:
        stmt = stmt.where(Markdown.title.ilike(f"%{q}%"))
    if start_date:
        stmt = stmt.where(Markdown.date >= start_date)
    if end_date:
        stmt = stmt.where(Markdown.date <= end_date)

    # 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    result = await database.execute(count_stmt)
    total = result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Markdown.date.desc()).offset(offset).limit(page_size)
    result = await database.execute(stmt)
    rows = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return templates.TemplateResponse("list.html", {
        "request": request,
        "rows": rows,
        "query": q,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "start_date": start_date,
        "end_date": end_date
    })


@router.get("/view/{md_id}", response_class=HTMLResponse)
async def view_markdown(
        request: Request,
        md_id: str,
        database: AsyncSession = Depends(db.db),
        _: dict = Depends(require_role(UserRole.User))
):
    # noinspection PyTypeChecker
    stmt = select(Markdown).where(Markdown.id == md_id)
    result = await database.execute(stmt)
    markdown = result.scalar_one_or_none()
    if not markdown:
        raise HTTPException(status_code=404, detail="Markdown not found")

    file_path = db.files_path / Path(markdown.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content = file_path.read_text(encoding="utf-8")
    return templates.TemplateResponse("view.html", {"request": request, "content": content})
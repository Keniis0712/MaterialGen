from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import HTMLResponse

from core.user import require_role
from db import db
from db.db import files_path
from db.models import Markdown, UserRole
from core.template import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def view_articles_page(
    request: Request,
    _: dict = Depends(require_role(UserRole.User))
):
    """
    返回文章列表页面模板，实际数据通过前端 JS 调用 /api/articles 获取
    """
    return templates.TemplateResponse("view/view_articles.html", {"request": request})


@router.get("/{md_id}", response_class=HTMLResponse)
async def view_markdown(
    request: Request,
    md_id: str,
    db: AsyncSession = Depends(db.db),
    _: dict = Depends(require_role(UserRole.User))
):
    # noinspection PyTypeChecker
    stmt = select(Markdown).where(Markdown.id == md_id)
    result = await db.execute(stmt)
    markdown = result.scalar_one_or_none()
    if not markdown:
        raise HTTPException(status_code=404, detail="Markdown not found")

    file_path = files_path / Path(markdown.path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content = file_path.read_text(encoding="utf-8")

    return templates.TemplateResponse(
        "view/view_md.html",
        {"request": request, "title": markdown.title, "content": content}
    )
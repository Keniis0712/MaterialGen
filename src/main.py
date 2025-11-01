import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterable, Optional

from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Query
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

import db
import user
from db import Markdown, UserRole
from gen.rss import fetch_updates_multi
from gen import llm_parse, news, post_processing
from user import require_role
from config import *

# Default UA
user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

# Config logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

rss: Optional[AsyncIterable] = None
gen_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global rss

    rss = fetch_updates_multi(news.get_all_rss_urls(), interval=60)
    news.set_user_agent(user_agent)
    await db.init_db()
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


async def generation():
    async for item in rss:
        logger.info("新新闻: %s", item["title"])
        article = await news.parse_article(item["feed_url"], item["link"])
        if not article:
            logger.warning("文章抓取失败: %s", item["link"])
            continue
        logger.info("文章抓取完成: %s", article.title if article else "失败")
        if not (summary := getattr(item["entry"], "summary", "")):
            logger.warning("摘要缺失")
            continue
        if not news.filter_article(article):
            logger.info("文章未通过过滤")
            continue
        llm = await llm_parse.run_sequence(article.title, summary, article.text)
        if not llm.is_ok:
            logger.info("LLM处理不合格")
            continue
        await post_processing.post_process_material(llm, article)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # 401 Unauthorized
    if exc.status_code == 401:
        if exc.detail == "Insufficient permissions":
            # 返回“无权访问”页面
            return templates.TemplateResponse(
                "errors/401_no_permission.html",
                {"request": request, "detail": exc.detail},
                status_code=401
            )
        else:
            # 跳转到登录页，并传参 error
            login_url = f"/login"
            return RedirectResponse(url=login_url, status_code=302)

    # 404 Not Found
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "path": request.url.path},
            status_code=404
        )

    # 其他 HTTP 异常
    return templates.TemplateResponse(
        "errors/error.html",
        {"request": request, "detail": exc.detail},
        status_code=exc.status_code
    )


# 捕获未处理的异常（500 Internal Server Error）
@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request, "detail": str(exc)},
        status_code=500
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, token: Optional[str] = Cookie(None)):
    user_obj = None
    if token:
        try:
            user_obj = user.get_current_user_by_default(token)
            if user_obj:
                user_obj["role"] = UserRole(int(user_obj["role"])).name
        except JWTError:
            user_obj = None
    return templates.TemplateResponse("index.html", {"request": request, "user": user_obj})


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("user/login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    async with db.AsyncSessionLocal() as session:
        # ORM 查询
        stmt = select(db.User).where(db.User.username == username)
        result = await session.execute(stmt)
        user_obj = result.scalar_one_or_none()  # 返回单个对象或None

        if not user_obj or not user.verify_password(password, user_obj.password):
            return templates.TemplateResponse(
                "user/login.html",
                {"request": request, "error": "Invalid credentials"}
            )

        # 登录成功
        access_token = user.create_access_token({"sub": user_obj.username, "role": user_obj.role})

        # 设置 cookie
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="token", value=f"{access_token}", httponly=True)
        return response


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    if not ALLOW_EVERYONE_REGISTER:
        return templates.TemplateResponse(
            "user/deny_register.html",
            {"request": request}
        )
    return templates.TemplateResponse("user/register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def register_post(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(...)
):
    if not ALLOW_EVERYONE_REGISTER:
        return templates.TemplateResponse(
            "user/deny_register.html",
            {"request": request}
        )
    if password != confirm_password:
        return templates.TemplateResponse(
            "user/register.html",
            {"request": request, "error": "Passwords do not match"}
        )

    async with db.AsyncSessionLocal() as session:
        # ORM 查询判断用户是否存在
        stmt = select(db.User).where(db.User.username == username)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return templates.TemplateResponse(
                "user/register.html",
                {"request": request, "error": "Username already exists"}
            )

        new_user = db.User(username=username, password=db.User.hash_password(password), role="user")
        session.add(new_user)
        await session.commit()

        return templates.TemplateResponse(
            "user/register.html",
            {"request": request, "success": "Registration successful! You can login now."}
        )


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="token", path="/")
    return response


@app.get("/view", response_class=HTMLResponse)
async def read_index(
        request: Request,
        q: str = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1),
        start_date: str = Query(None),
        end_date: str = Query(None),
        database: AsyncSession = Depends(db.db),
        current_user: dict = Depends(require_role(UserRole.User))
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


@app.get("/view/{md_id}", response_class=HTMLResponse)
async def view_markdown(
        request: Request,
        md_id: str,
        database: AsyncSession = Depends(db.db),
        current_user: dict = Depends(require_role(UserRole.User))
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

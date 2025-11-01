from fastapi import APIRouter, Form
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from config import ALLOW_EVERYONE_REGISTER
from core import user
from db import db
from db.models import User
from core.template import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("user/login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    async with db.AsyncSessionLocal() as session:
        # noinspection PyTypeChecker
        stmt = select(User).where(User.username == username)
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


@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    if not ALLOW_EVERYONE_REGISTER:
        return templates.TemplateResponse(
            "user/deny_register.html",
            {"request": request}
        )
    return templates.TemplateResponse("user/register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
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
        # noinspection PyTypeChecker
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return templates.TemplateResponse(
                "user/register.html",
                {"request": request, "error": "Username already exists"}
            )

        new_user = User(username=username, password=User.hash_password(password), role="user")
        session.add(new_user)
        await session.commit()

        return templates.TemplateResponse(
            "user/register.html",
            {"request": request, "success": "Registration successful! You can login now."}
        )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="token", path="/")
    return response

from typing import Optional

from fastapi import APIRouter, Cookie, Depends
from jose import JWTError
from starlette.requests import Request
from starlette.responses import HTMLResponse

from core import user
from core.user import require_role
from db.models import UserRole
from core.template import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
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


@router.get("/admin", response_class=HTMLResponse)
async def admin(
        request: Request,
        user_obj: dict = Depends(require_role(UserRole.Admin))
):
    return templates.TemplateResponse("admin.html", {"request": request, "user": user_obj})
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from core.template import templates


# For StarletteHTTPException
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    if exc.status_code == 401:
        if exc.detail == "Insufficient permissions":
            return templates.TemplateResponse(
                "errors/401_no_permission.html",
                {"request": request, "detail": exc.detail},
                status_code=401
            )
        login_url = f"/login"
        return RedirectResponse(url=login_url, status_code=302)

    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "path": request.url.path},
            status_code=404
        )

    return templates.TemplateResponse(
        "errors/error.html",
        {"request": request, "detail": exc.detail},
        status_code=exc.status_code
    )


# For Exception
async def internal_exception_handler(request: Request, exc: Exception) -> Response:
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request, "detail": str(exc)},
        status_code=500
    )

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.exceptions import HTTPException

from db import db
from gen.rss import fetch_updates_multi
from gen import news
import routers
from handlers import exceptions
from core import logger

# Default UA
user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

@asynccontextmanager
async def lifespan(_: FastAPI):
    news.set_user_agent(user_agent)
    await db.init_db()
    yield
    if routers.apis.generator.task:
        routers.apis.generator.task.cancel()


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.include_router(routers.pages.index.router)
app.include_router(routers.pages.user.router)
app.include_router(routers.pages.view.router, prefix="/view")
app.include_router(routers.apis.article.router, prefix="/api/articles")
app.include_router(routers.apis.generator.router, prefix="/api/generator")
app.include_router(routers.apis.user.router, prefix="/api/users")

app.add_exception_handler(Exception, exceptions.internal_exception_handler)
# noinspection PyTypeChecker
app.add_exception_handler(HTTPException, exceptions.http_exception_handler)

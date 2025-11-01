import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.exceptions import HTTPException

from db import db
from gen.rss import fetch_updates_multi
from gen import news
from routers import main_pages, user_pages, view_pages
from handlers import exceptions

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

@asynccontextmanager
async def lifespan(_: FastAPI):
    global rss

    rss = fetch_updates_multi(news.get_all_rss_urls(), interval=60)
    news.set_user_agent(user_agent)
    await db.init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.include_router(main_pages.router)
app.include_router(user_pages.router)
app.include_router(view_pages.router)

app.add_exception_handler(Exception, exceptions.internal_exception_handler)
app.add_exception_handler(HTTPException, exceptions.http_exception_handler)

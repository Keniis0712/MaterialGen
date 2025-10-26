from . import common
from . import chinanews

from .common import *


def get_all_rss_urls() -> list[str]:
    rss = []
    for names in globals():
        mod = globals()[names]
        if hasattr(mod, "NEWS_URLS"):
            rss.extend(mod.NEWS_URLS)

    return rss


async def parse_article(rss_url: str, article_url: str) -> Article | None:
    mod = None
    for names in globals():
        mod = globals()[names]
        if hasattr(mod, "NEWS_URLS") and rss_url in mod.NEWS_URLS:
            break
    if not mod or not hasattr(mod, "parse"):
        return None
    return await mod.parse(article_url)

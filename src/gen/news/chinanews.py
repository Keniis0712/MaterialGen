from typing import Optional

import aiohttp
from aiohttp.web_exceptions import HTTPException
from bs4 import BeautifulSoup as bs

from .common import Article, request_url

NEWS_URLS = [
    "https://www.chinanews.com.cn/rss/scroll-news.xml"
]


async def parse(url: str) -> Optional[Article]:
    async with aiohttp.ClientSession() as session:
        try:
            text = await request_url(url, session)
        except HTTPException:
            return None

    soup = bs(text, "lxml")
    title_tag = soup.find("h1", class_="content_left_title")
    info_tag = soup.find("div", id="BaiduSpider")
    pubtime_tag = info_tag.find("span", id="pubtime_baidu")
    source_tag = info_tag.find("span", id="source_baidu")
    content_tag = soup.find("div", class_="left_zw")
    image_counts = len(content_tag.find_all("img")) if content_tag else 0

    article = Article(
        title=title_tag.get_text(strip=True) if title_tag else "",
        text=content_tag.get_text(strip=True) if content_tag else "",
        image_counts=image_counts,
        source=source_tag.get_text(strip=True).rsplit('：', 1)[1] if source_tag else "",
        link=url,
        pub_date=pubtime_tag.get_text(strip=True) if pubtime_tag else "",
    )
    return article

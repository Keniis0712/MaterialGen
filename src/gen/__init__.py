import asyncio
import logging
from typing import AsyncIterable, Optional

from gen import llm_parse, news, post_processing

rss_gen: Optional[AsyncIterable] = None
logger = logging.getLogger(__name__)


async def generation():
    if rss_gen is None:
        logger.error("rss not set")
        return
    try:
        async for item in rss_gen:
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
    except asyncio.CancelledError:
        logger.info("正在退出")
        raise


def set_rss_obj(rss_):
    global rss_gen
    rss_gen = rss_

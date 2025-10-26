import asyncio
import aiohttp
import feedparser
from collections import deque
from typing import AsyncGenerator, Deque, TypedDict

from feedparser import FeedParserDict


RSSResult = TypedDict(
    "RSSResult",
    {
        "feed_url": str,
        "title": str,
        "link": str,
        "published": str,
        "entry": FeedParserDict,
    }
)


async def fetch_feed_text(session: aiohttp.ClientSession, url: str, headers: dict[str, str] = None):
    async with session.get(url, headers=headers) as resp:
        if resp.status == 304:
            # 无更新
            return None, resp.headers
        resp.raise_for_status()
        text = await resp.text()
        return text, resp.headers


async def fetch_updates_from_source(
    rss_url: str,
    interval: float = 60.0,
    session: aiohttp.ClientSession = None
) -> AsyncGenerator[RSSResult, None]:
    """
    单个 RSS 源的异步生成器：周期性拉取，yield 新条目。
    """
    own_session = False
    if session is None:
        session = aiohttp.ClientSession()
        own_session = True

    seen: Deque[str] = deque()
    seen_set: set[str] = set()
    max_seen = None

    etag = None
    modified = None

    try:
        while True:
            headers = {}
            if etag:
                headers["If-None-Match"] = etag
            if modified:
                headers["If-Modified-Since"] = modified

            try:
                result = await fetch_feed_text(session, rss_url, headers=headers)
                if result is None:
                    await asyncio.sleep(interval)
                    continue
                text, resp_headers = result
            except aiohttp.ClientError as e:
                print(f"[{rss_url}] fetch error: {e}")
                await asyncio.sleep(interval)
                continue

            etag = resp_headers.get("ETag") or etag
            modified = resp_headers.get("Last-Modified") or modified

            entries = feedparser.parse(text).entries
            if max_seen is None:
                max_seen = max(50, len(entries) * 10)

            for entry in entries:
                entry_id = getattr(entry, "id", None) or getattr(entry, "link", None) or entry.title
                if entry_id in seen_set:
                    continue

                # 维护 seen 队列大小
                seen.append(entry_id)
                seen_set.add(entry_id)
                if len(seen) > max_seen:
                    old = seen.popleft()
                    seen_set.discard(old)

                ret: RSSResult = {
                    "feed_url": rss_url,
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "published": entry.get("published"),
                    "entry": entry,
                }
                yield ret

            await asyncio.sleep(interval)
    finally:
        if own_session:
            await session.close()


async def fetch_updates_multi(
    rss_urls: list[str],
    interval: float = 60.0
) -> AsyncGenerator[RSSResult, None]:
    async with aiohttp.ClientSession() as session:
        tasks = []
        queue = asyncio.Queue()

        async def collect_updates(fetch_url: str):
            async for fetch_item in fetch_updates_from_source(fetch_url, interval, session):
                await queue.put(fetch_item)

        for url in rss_urls:
            task = asyncio.create_task(collect_updates(url))
            tasks.append(task)

        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


# === 示例使用 ===
async def main():
    rss_urls = [
        "https://www.chinanews.com.cn/rss/scroll-news.xml",
    ]
    async for item in fetch_updates_multi(rss_urls, interval=5):
        print(f"[{item['feed_url']}] {item['title']} -> {item['link']}")


if __name__ == "__main__":
    asyncio.run(main())

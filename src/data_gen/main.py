import asyncio

from rss import fetch_updates_multi
import news
import llm_parse
import post_processing


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"


async def main():
    post_processing.init_db()
    rss = fetch_updates_multi(news.get_all_rss_urls(), interval=60)
    news.set_user_agent(UA)
    try:
        async for item in rss:
            print("新新闻:", item["title"])
            article = await news.parse_article(item["feed_url"], item["link"])
            if not article:
                print("文章抓取失败:", item["link"])
                continue
            print("文章抓取完成:", article.title if article else "失败")
            if not (summary := getattr(item["entry"], "summary", "")):
                print("摘要缺失")
                continue
            if not news.filter_article(article):
                print("文章未通过过滤")
                continue
            llm = await llm_parse.run_sequence(article.title, summary, article.text)
            if not llm.is_ok:
                print("LLM处理不合格")
                continue
            post_processing.post_process_material(llm, article)
    except KeyboardInterrupt:
        print("正在退出...")
        post_processing.cleanup_db()


if __name__ == "__main__":
    asyncio.run(main())

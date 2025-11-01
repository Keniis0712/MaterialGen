import dataclasses


@dataclasses.dataclass
class Article:
    title: str
    text: str
    image_counts: int
    source: str
    link: str
    pub_date: str


USER_AGENT = ""


def set_user_agent(ua: str):
    global USER_AGENT
    USER_AGENT = ua


def get_user_agent() -> str:
    return USER_AGENT


async def request_url(url: str, session) -> str:
    headers = {}
    if USER_AGENT:
        headers["User-Agent"] = USER_AGENT

    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        return await response.text()


def filter_article(
        article: Article,
        min_text_length: int = 400,
        max_image_text_ratio: float = 1/400
) -> bool:
    if not article.text or not article.title:
        return False
    if len(article.text) < min_text_length:
        return False
    ratio = article.image_counts / len(article.text)
    if ratio > max_image_text_ratio:
        return False
    return True

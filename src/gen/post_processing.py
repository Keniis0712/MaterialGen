import datetime
import uuid
from string import Template
import logging

from sqlalchemy import String, insert

from db.db import AsyncSessionLocal, files_path
from db.models import Markdown
from .llm_parse import LLMOutputs
from .news.common import Article


logger = logging.getLogger(__name__)


markdown_template = Template(
    """
## ${title}

### 简介:
${summary}

### 适用主题:
${themes}

### 例文：
例文1
${example1}

例文2
${example2}

例文3
${example3}

> 更新时间: ${update_time}
>
> 来源: ${source} (${link})

""".strip()
)


async def save_markdown(content: str, title: str) -> str:
    # 生成唯一ID
    md_id = uuid.uuid4().hex
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 创建目录
    folder = files_path / date[:7].replace("-", "/")
    folder.mkdir(parents=True, exist_ok=True)

    # 保存 Markdown 文件
    filename = f"{date}_{md_id}.md"
    file_path = folder / filename
    file_path.write_text(content, encoding="utf-8")

    # 记录到数据库
    async with AsyncSessionLocal() as session:
        stmt = insert(Markdown).values(
            id=md_id,
            date=date,
            path=str(file_path.relative_to(files_path)),
            title=title
        )
        await session.execute(stmt)
        await session.commit()

    return md_id


async def post_process_material(
    material: LLMOutputs,
    article: Article
):
    md = markdown_template.substitute(
        title=material.title,
        summary=material.summary,
        themes=material.themes,
        example1=material.example[0],
        example2=material.example[1],
        example3=material.example[2],
        update_time=article.pub_date,
        source=article.source,
        link=article.link,
    )
    md_id = await save_markdown(md, material.title)
    logger.info(f"保存md文件, id: {md_id}")


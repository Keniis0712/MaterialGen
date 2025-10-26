import datetime
import pathlib
import uuid
from string import Template
import sqlite3
from typing import Optional

from llm_parse import LLMOutputs
from news.common import Article

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


data_path = pathlib.Path(__file__).parent.parent / "data"
if not data_path.exists():
    data_path.mkdir(exist_ok=True)

files_path = data_path / "files"
if not files_path.exists():
    files_path.mkdir(exist_ok=True)

database: Optional[sqlite3.Connection] = None


def init_db():
    global database
    db_path = data_path / "materials.db"
    database = sqlite3.connect(db_path)
    cursor = database.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS markdowns (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        path TEXT NOT NULL,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON markdowns(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON markdowns(title)")
    database.commit()


def cleanup_db():
    global database
    if database:
        database.close()
        database = None


def save_markdown(content: str, title: str) -> str:
    # 生成唯一ID
    md_id = uuid.uuid4().hex
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 创建目录
    folder = files_path / date[:7].replace("-", "/")
    folder.mkdir(exist_ok=True, parents=True)

    # 保存 Markdown 文件
    filename = f"{date}_{md_id}.md"
    file_path = folder / filename
    with file_path.open("w", encoding="utf-8") as f:
        f.write(content)

    # 记录到 SQLite
    cur = database.cursor()
    cur.execute(
        "INSERT INTO markdowns (id, date, path, title) VALUES (?, ?, ?, ?)",
        (md_id, date, str(file_path.relative_to(files_path)), title)
    )
    database.commit()
    return md_id


def post_process_material(
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
    md_id = save_markdown(md, material.title)
    print(f"保存md文件, id: {md_id}")


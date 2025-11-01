import sqlite3
import uuid
import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import markdown

# 数据库和文件路径
data_path = Path(__file__).parent.parent / "data"
files_path = data_path / "files"
db_path = data_path / "materials.db"
database = None

# FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")


# 初始化数据库
def init_db():
    global database
    data_path.mkdir(exist_ok=True)
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
    database.close()


init_db()


# 获取数据库连接
def get_db():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# 首页：显示所有 Markdown
@app.get("/", response_class=HTMLResponse)
def read_index(
    request: Request,
    q: str = None,
    page: int = 1,
    page_size: int = 10,
    start_date: str = None,
    end_date: str = None
):
    conn = get_db()
    cur = conn.cursor()

    # 构建 SQL 查询
    sql = "SELECT * FROM markdowns WHERE 1=1"
    params = []

    if q:
        sql += " AND title LIKE ?"
        params.append(f"%{q}%")

    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)

    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)

    # 总数
    count_sql = "SELECT COUNT(*) FROM (" + sql + ")"
    cur.execute(count_sql, params)
    total = cur.fetchone()[0]

    # 分页
    offset = (page - 1) * page_size
    sql += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    total_pages = (total + page_size - 1) // page_size

    return templates.TemplateResponse("index.html", {
        "request": request,
        "rows": rows,
        "query": q,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "start_date": start_date,
        "end_date": end_date
    })

# 查看 Markdown 内容
@app.get("/view/{md_id}", response_class=HTMLResponse)
def view_markdown(request: Request, md_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM markdowns WHERE id = ?", (md_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Markdown not found")

    file_path = files_path / Path(row["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    with file_path.open("r", encoding="utf-8") as f:
        content = f.read()

    return templates.TemplateResponse("view.html", {"request": request, "content": content})

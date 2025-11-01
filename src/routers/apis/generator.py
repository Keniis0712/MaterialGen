import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse

from core.logger import sse_handler
from core.user import require_role
from db.models import UserRole
import gen.rss
import gen.news

router = APIRouter()

task: Optional[asyncio.Task] = None
first_start = True


@router.post("/start")
async def start_generation_task(
    _: dict = Depends(require_role(UserRole.Admin))
):
    global task, first_start
    if task:
        return {"code": 403, "msg": "生成器已经启动"}
    rss = gen.rss.fetch_updates_multi(gen.news.get_all_rss_urls(), ignore_first=not first_start)
    first_start = False
    gen.set_rss_obj(rss)
    task = asyncio.create_task(gen.generation())
    return {"code": 200, "msg": ""}


@router.post("/stop")
async def start_generation_task(
    _: dict = Depends(require_role(UserRole.Admin))
):
    global task
    if not task:
        return {"code": 403, "msg": "生成器未启动"}
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    task = None
    return {"code": 200, "msg": ""}


@router.get("/logs")
async def stream_logs():
    queue = sse_handler.subscribe()

    async def event_generator():
        try:
            for line in sse_handler.get_history():
                yield f"data: {line}\n\n"
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        finally:
            sse_handler.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
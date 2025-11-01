import asyncio
import datetime
import logging
from collections import deque
from typing import Optional


class LogItem:
    def __init__(self, timestamp: datetime.datetime, level: int, message: str):
        self.timestamp = timestamp
        self.level = level
        self.message = message

    def __lt__(self, other):
        return self.timestamp < other.timestamp


class SSELoggingHandler(logging.Handler):
    """
    Logging handler that:
    1. Sends log messages via SSE.
    2. Keeps separate history per log level with different max sizes.
    3. Returns merged history in chronological order.
    """

    def __init__(
            self,
            info_lines: Optional[int] = 100,
            warn_lines: Optional[int] = 50,
            error_lines: Optional[int] = 50
    ):
        super().__init__()
        # 每个级别的历史日志
        self.history: dict[int, deque[LogItem]] = {
            logging.INFO: deque(maxlen=info_lines),
            logging.WARNING: deque(maxlen=warn_lines),
            logging.ERROR: deque(maxlen=error_lines),
        }
        self.subscribers: list[asyncio.Queue] = []

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        item = LogItem(timestamp=datetime.datetime.now(), level=record.levelno, message=msg)
        if record.levelno in self.history:
            self.history[record.levelno].append(item)
        # 异步广播给订阅者
        asyncio.create_task(self._broadcast(msg))

    async def _broadcast(self, message: str):
        for queue in self.subscribers:
            await queue.put(message)

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def get_history(self) -> list[str]:
        # 合并所有级别的日志
        all_items = []
        for q in self.history.values():
            all_items.extend(q)
        # 按时间排序
        all_items.sort()
        # 返回消息列表
        return [item.message for item in all_items]


sse_handler = SSELoggingHandler()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(), sse_handler]
)

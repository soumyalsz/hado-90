import asyncio
from typing import List


class BroadcastLogger:
    """Fans out log lines to every connected WebSocket client."""

    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        subscriber_queue = asyncio.Queue()
        self.subscribers.append(subscriber_queue)
        return subscriber_queue

    def unsubscribe(self, subscriber_queue: asyncio.Queue):
        if subscriber_queue in self.subscribers:
            self.subscribers.remove(subscriber_queue)

    async def broadcast(self, message: str):
        for subscriber_queue in self.subscribers:
            await subscriber_queue.put(message)


ws_logger = BroadcastLogger()

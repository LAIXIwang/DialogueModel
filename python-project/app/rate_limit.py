"""限流：内存滑动窗口计数器。

单实例部署足够；多实例 / 多进程部署请替换为 Redis 等共享存储实现
（接口保持不变，仅替换本类即可）。
"""

import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self, window_seconds: float, max_requests: int) -> None:
        self.window = window_seconds
        self.max = max_requests
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """判断 key 在窗口内是否仍有余量；命中则计数一次。"""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max:
                return False
            q.append(now)
            self._gc()
            return True

    def _gc(self) -> None:
        """防止字典随 IP 数量无限增长。"""
        if len(self._hits) > 10_000:
            cutoff = time.monotonic() - self.window
            stale = [k for k, q in self._hits.items() if not q or q[-1] < cutoff]
            for k in stale:
                del self._hits[k]

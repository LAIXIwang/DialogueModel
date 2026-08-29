"""上游协议适配器。

BFF 对浏览器统一输出 SSE（meta/delta/done/error），不同上游协议由适配器
转换为内部事件流 —— 新增自建模型协议时只需实现 BaseAdapter 并注册。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterEvent:
    """上游一次返回解析出的内部事件。"""

    delta: str = ""  # 增量文本
    done: bool = False  # 生成结束
    finish_reason: str = ""
    usage: dict = field(default_factory=dict)
    error: str = ""


class BaseAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def build_request(
        self,
        messages: list[dict],
        params: dict[str, Any],
        base_url: str,
    ) -> tuple[str, dict]:
        """构造上游请求，返回 (url, payload)。"""

    @abstractmethod
    def parse_data(self, payload: str) -> AdapterEvent | None:
        """解析上游 SSE 的一条 data 行；非内容行返回 None。"""

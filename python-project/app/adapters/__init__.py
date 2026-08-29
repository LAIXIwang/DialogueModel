"""协议适配器注册表。"""

from .base import AdapterEvent, BaseAdapter
from .llamacpp import LlamaCppAdapter
from .openai_compat import OpenAICompatAdapter

_REGISTRY: dict[str, BaseAdapter] = {
    a.name: a for a in (OpenAICompatAdapter(), LlamaCppAdapter())
}


def get_adapter(name: str) -> BaseAdapter:
    key = name.strip().lower()
    if key not in _REGISTRY:
        raise ValueError(f"未知上游协议: {name!r}，可用: {', '.join(sorted(_REGISTRY))}")
    return _REGISTRY[key]


__all__ = ["AdapterEvent", "BaseAdapter", "get_adapter"]

"""模型接入服务：读取/修改本地大模型接口配置，修改后即时生效。

生效链路：MySQL（持久） → Redis `config:model`（运行时） → BFF 每次对话实时读取。
"""

import json

from sqlalchemy.orm import Session

from ..core import redis_client
from ..core.exceptions import BizError
from ..dao.model_config_dao import ModelConfigDao

# 与 BFF app/upstream.py 保持一致
MODEL_CONFIG_KEY = "config:model"
PROTOCOLS = ("openai", "llamacpp")


def get_config(db: Session) -> dict:
    row = ModelConfigDao.get(db)
    if row is None:
        from ..config import get_admin_settings

        s = get_admin_settings()
        return {
            "base_url": s.upstream_base_url,
            "api_key": s.upstream_api_key,
            "protocol": s.upstream_protocol,
            "model": s.upstream_model,
            "updated_by": "",
            "updated_at": "",
        }
    return {
        "base_url": row.base_url,
        "api_key": row.api_key,
        "protocol": row.protocol,
        "model": row.model,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat(),
    }


def update_config(
    db: Session,
    *,
    base_url: str | None,
    api_key: str | None,
    protocol: str | None,
    model: str | None,
    operator_name: str,
) -> dict:
    current = get_config(db)

    new_base = (base_url or current["base_url"]).strip()
    new_protocol = (protocol or current["protocol"]).strip().lower()
    new_model = (model if model is not None else current["model"]).strip()

    if not new_base.startswith(("http://", "https://")):
        raise BizError("接口地址必须以 http:// 或 https:// 开头", code=4301)
    if new_protocol not in PROTOCOLS:
        raise BizError(f"协议仅支持: {', '.join(PROTOCOLS)}", code=4302)
    if not new_model:
        raise BizError("模型名称不能为空", code=4303)

    # 密钥：空字符串或打码占位（****开头）都视为"保留原密钥"（防御前端误提交打码值）
    if api_key is None or api_key == "" or api_key.startswith("****"):
        new_key = current["api_key"]
    else:
        new_key = api_key

    row = ModelConfigDao.save(
        db,
        base_url=new_base,
        api_key=new_key,
        protocol=new_protocol,
        model=new_model,
        updated_by=operator_name,
    )

    # 写入 Redis → BFF 实时读取，无需重启
    redis_client.get_redis().set(
        MODEL_CONFIG_KEY,
        json.dumps(
            {"base_url": new_base, "api_key": new_key, "protocol": new_protocol, "model": new_model},
            ensure_ascii=False,
        ),
    )

    return {
        "base_url": row.base_url,
        "api_key": row.api_key,
        "protocol": row.protocol,
        "model": row.model,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat(),
    }

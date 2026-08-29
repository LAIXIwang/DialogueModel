"""模型接入接口：查看/修改本地大模型 API 配置。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.audit import record_log
from ..core.deps import client_ip, require_permission
from ..core.exceptions import ok
from ..database import get_db
from ..models import User
from ..schemas import ModelConfigOut, UpdateModelConfigRequest
from ..services import model_config_service

router = APIRouter(prefix="/api/model-config", tags=["模型接入"])


def _masked(cfg: dict) -> dict:
    """返回给前端时对密钥打码（仅保留后 4 位）。"""
    key = cfg.get("api_key", "")
    cfg = dict(cfg)
    cfg["api_key"] = key if not key else "****" + key[-4:]
    return cfg


@router.get("")
def get_model_config(
    _: User = Depends(require_permission("model:read")),
    db: Session = Depends(get_db),
):
    return ok(_masked(model_config_service.get_config(db)))


@router.put("")
def update_model_config(
    req: UpdateModelConfigRequest,
    request: Request,
    operator: User = Depends(require_permission("model:edit")),
    db: Session = Depends(get_db),
):
    cfg = model_config_service.update_config(
        db,
        base_url=req.base_url,
        api_key=req.api_key,
        protocol=req.protocol,
        model=req.model,
        operator_name=operator.username,
    )
    record_log(
        db,
        "model_config.update",
        ip=client_ip(request),
        user_id=operator.id,
        username=operator.username,
        params={"base_url": req.base_url, "protocol": req.protocol, "model": req.model},
    )
    return ok(_masked(cfg), message="模型接入配置已保存并即时生效")

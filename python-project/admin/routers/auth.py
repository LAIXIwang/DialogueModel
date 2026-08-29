"""认证接口：登录 / 注册 / 刷新 / 登出 / 修改密码 / 当前用户。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.deps import client_ip, get_current_user
from ..core.exceptions import BizError, ok
from ..database import get_db
from ..models import User
from ..schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserBrief,
)
from ..services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    return ok(auth_service.login(db, req.username, req.password, client_ip(request)))


@router.post("/register")
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    return ok(auth_service.register(db, req.username, req.password, req.email, client_ip(request)))


@router.post("/refresh")
def refresh(req: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    return ok(auth_service.refresh(db, req.refresh_token, client_ip(request)))


@router.post("/logout")
def logout(
    request: Request,
    body: dict | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    refresh_token = (body or {}).get("refresh_token")
    auth_service.logout(db, request.state.token_payload, refresh_token, client_ip(request))
    return ok()


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.change_password(db, user, req.old_password, req.new_password, client_ip(request))
    return ok(message="密码已修改，请重新登录")


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    from ..dao.rbac_dao import PermissionDao

    return ok({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "role_code": user.role.code,
        "role_name": user.role.name,
        "status": user.status,
        # 角色权限 ∪ 分组权限
        "permissions": sorted(PermissionDao.codes_by_user(user)),
    })

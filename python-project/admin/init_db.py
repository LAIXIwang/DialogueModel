"""数据库初始化与种子数据（幂等，可重复执行）。

用法：conda activate work && python -m admin.init_db
"""

import sys

import pymysql

from .config import get_admin_settings
from .core.security import hash_password
from .database import Base, SessionLocal, engine
from .models import ApiQuota, Permission, Role, User

# 内置角色
SEED_ROLES = [
    ("super_admin", "超级管理员", "拥有全部权限"),
    ("admin", "管理员", "负责用户与内容管理"),
    ("user", "普通用户", "仅能查看自己的对话记录"),
    ("guest", "访客", "无后台权限"),
]

# 权限清单：(code, name, module)
SEED_PERMISSIONS = [
    ("user:list", "用户查询", "用户管理"),
    ("user:create", "新增用户", "用户管理"),
    ("user:edit", "编辑用户", "用户管理"),
    ("user:delete", "删除用户", "用户管理"),
    ("user:status", "启用/禁用用户", "用户管理"),
    ("user:reset_password", "重置密码", "用户管理"),
    ("user:assign_role", "分配角色", "用户管理"),
    ("role:list", "角色查询", "角色权限"),
    ("role:create", "新增角色", "角色权限"),
    ("role:edit", "编辑角色", "角色权限"),
    ("role:delete", "删除角色", "角色权限"),
    ("role:assign_permission", "角色分配权限", "角色权限"),
    ("permission:list", "权限查询", "角色权限"),
    ("group:list", "分组查询", "分组管理"),
    ("group:create", "新增分组", "分组管理"),
    ("group:edit", "编辑分组", "分组管理"),
    ("group:delete", "删除分组", "分组管理"),
    ("group:assign_member", "分组成员分配", "分组管理"),
    ("group:assign_permission", "分组权限分配", "分组管理"),
    ("model:read", "模型接入查看", "模型接入"),
    ("model:edit", "模型接入修改", "模型接入"),
    ("conversation:list", "对话记录查询", "会话管理"),
    ("conversation:delete", "删除对话/会话", "会话管理"),
    ("stats:read", "调用统计查看", "统计配额"),
    ("quota:read", "配额查看", "统计配额"),
    ("quota:edit", "配额与限流调整", "统计配额"),
    ("log:read", "审计日志查看", "审计日志"),
]

# 角色 → 权限编码
# 管理员：仅 用户管理 + 分组管理 + 会话管理（权限查询仅用于下拉选择）
ROLE_PERMS = {
    "super_admin": [c for c, _, _ in SEED_PERMISSIONS],
    "admin": [
        "user:list", "user:create", "user:edit", "user:delete",
        "user:status", "user:reset_password", "user:assign_role",
        "group:list", "group:create", "group:edit", "group:delete",
        "group:assign_member", "group:assign_permission",
        "conversation:list", "conversation:delete",
        "permission:list",
    ],
    "user": ["conversation:list", "conversation:delete"],
    "guest": [],
}

DEFAULT_ADMIN = {"username": "admin", "password": "Admin@123456", "email": "admin@dialogue.local"}


def create_database_if_not_exists() -> None:
    """连接 MySQL 服务器创建 DialogueModel 库（不存在时）。"""
    s = get_admin_settings()
    conn = pymysql.connect(
        host=s.mysql_host, port=s.mysql_port, user=s.mysql_user, password=s.mysql_password, charset="utf8mb4"
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{s.mysql_db}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"[init_db] 数据库 {s.mysql_db} 就绪")
    finally:
        conn.close()


def _migrate_columns() -> None:
    """为已有数据库补充新增列（幂等）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "user" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("user")]
        if "pwd_version" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `user` ADD COLUMN pwd_version INT NOT NULL DEFAULT 0"))
            print("[init_db] 已为 user 表新增 pwd_version 列")


def ensure_seeded(db) -> None:
    """幂等种子：角色 → 权限 → 角色-权限 → 管理员 → 配额。"""
    _migrate_columns()
    s = get_admin_settings()

    roles = {}
    for code, name, desc in SEED_ROLES:
        role = db.query(Role).filter(Role.code == code).first()
        if role is None:
            role = Role(code=code, name=name, description=desc)
            db.add(role)
            db.flush()
        roles[code] = role

    perms = {}
    for code, name, module in SEED_PERMISSIONS:
        p = db.query(Permission).filter(Permission.code == code).first()
        if p is None:
            p = Permission(code=code, name=name, module=module)
            db.add(p)
            db.flush()
        perms[code] = p

    for role_code, codes in ROLE_PERMS.items():
        role = roles[role_code]
        if role.code == "super_admin":
            # 超级管理员代码层全放行，这里也落库便于前端展示
            role.permissions = list(perms.values())
        elif {p.code for p in role.permissions} != set(codes):
            role.permissions = [perms[c] for c in codes]

    admin = db.query(User).filter(User.username == DEFAULT_ADMIN["username"]).first()
    if admin is None:
        admin = User(
            username=DEFAULT_ADMIN["username"],
            password_hash=hash_password(DEFAULT_ADMIN["password"]),
            email=DEFAULT_ADMIN["email"],
            role_id=roles["super_admin"].id,
            status=1,
        )
        db.add(admin)
        db.flush()

    if db.query(ApiQuota).filter(ApiQuota.user_id == admin.id).first() is None:
        db.add(ApiQuota(user_id=admin.id, daily_limit=1_000_000))

    # ---- 模型接入默认配置（幂等：仅首次写入，之后由管理平台修改）----
    from .models import ModelConfig

    if db.get(ModelConfig, 1) is None:
        db.add(
            ModelConfig(
                id=1,
                base_url=s.upstream_base_url,
                api_key=s.upstream_api_key,
                protocol=s.upstream_protocol,
                model=s.upstream_model,
                updated_by="system",
            )
        )

    db.commit()
    print(
        f"[init_db] 种子完成：{len(roles)} 角色 / {len(perms)} 权限 / "
        f"管理员 {DEFAULT_ADMIN['username']} / {DEFAULT_ADMIN['password']}"
    )


def main() -> int:
    create_database_if_not_exists()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_seeded(db)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

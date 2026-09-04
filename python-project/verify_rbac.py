"""验证/准备 RBAC 调整：检查管理员角色权限集合，确保 ops1 管理员账号存在。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.core.security import hash_password
from admin.database import SessionLocal
from admin.models import Role, User

EXPECTED_ADMIN_PERMS = {
    "user:list", "user:create", "user:edit", "user:delete",
    "user:status", "user:reset_password", "user:assign_role",
    "group:list", "group:create", "group:edit", "group:delete",
    "group:assign_member", "group:assign_permission",
    "conversation:list", "conversation:delete",
    "permission:list",
}

db = SessionLocal()
try:
    admin_role = db.query(Role).filter(Role.code == "admin").first()
    actual = {p.code for p in admin_role.permissions}
    print(f"[check] 管理员角色权限 {len(actual)} 项：{sorted(actual)}")
    print(f"[check] 与预期一致: {actual == EXPECTED_ADMIN_PERMS}")
    print(f"[check] 已移除: {sorted(EXPECTED_ADMIN_PERMS - actual) or '无'} | 多出: {sorted(actual - EXPECTED_ADMIN_PERMS) or '无'}")

    ops = db.query(User).filter(User.username == "ops1").first()
    if ops is None:
        ops = User(
            username="ops1",
            password_hash=hash_password("Ops@123456"),
            email="",
            role_id=admin_role.id,
            status=1,
        )
        db.add(ops)
        db.commit()
        print(f"[check] 已创建管理员账号 ops1 (id={ops.id})")
    else:
        ops.role_id = admin_role.id
        db.commit()
        print(f"[check] ops1 已存在 (id={ops.id})，角色已校正为 admin")
finally:
    db.close()

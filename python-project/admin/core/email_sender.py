"""邮件发送：找回密码验证码。

- 配置了 SMTP（.env / 环境变量）→ 真实发信
- 未配置 SMTP（开发模式）→ 验证码打印到服务端日志，并在响应中携带 debug_code 便于联调
"""

import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText

from ..config import get_admin_settings

logger = logging.getLogger("admin")


def send_reset_code(to_email: str, username: str, code: str) -> bool:
    """发送验证码邮件；返回是否真实发信成功（开发模式返回 False 表示走日志通道）。"""
    settings = get_admin_settings()

    if not settings.smtp_host:
        # 开发模式：未配置 SMTP，验证码进日志
        logger.warning("[reset-password][DEV] 未配置 SMTP：用户=%s 邮箱=%s 验证码=%s", username, to_email, code)
        return False

    subject = "【Dialogue】密码找回验证码"
    body = (
        f"您好，{username}：\n\n"
        f"您正在找回登录密码，验证码为：{code}\n"
        f"验证码 10 分钟内有效，请勿泄露给他人。如非本人操作请忽略本邮件。\n\n"
        f"—— Dialogue 团队"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email

    try:
        if settings.smtp_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        try:
            if settings.smtp_starttls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        finally:
            server.quit()
        logger.info("[reset-password] 验证码邮件已发送: %s (%s)", username, to_email)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("[reset-password] 邮件发送失败: %s", exc)
        raise

# SMTP 邮件发送服务
# 配置项在 backend/.env 中由 database.Settings 统一加载：
#   SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / SMTP_FROM

import smtplib
from email.message import EmailMessage

from database import settings


# 同步发送纯文本邮件；SMTP 未配置或发送失败时抛出异常
def send_email(to: str, subject: str, body: str) -> None:
    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_pass or "").strip()
    if not host or not user or not password:
        raise RuntimeError(
            "SMTP 未配置：请在 backend/.env 设置 SMTP_HOST/SMTP_USER/SMTP_PASS"
        )

    port = int(settings.smtp_port or 465)
    sender = (settings.smtp_from or "").strip() or user

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    # 465 端口使用 SSL，其他端口使用 STARTTLS
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, password)
            s.send_message(msg)

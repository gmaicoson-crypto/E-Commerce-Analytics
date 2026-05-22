"""SMTP 邮件发送服务。

配置项放在 backend/.env(由 database.Settings 统一加载):
    SMTP_HOST=smtp.163.com          # 163 邮箱用这个,QQ 用 smtp.qq.com
    SMTP_PORT=465                   # 465=SSL  587=STARTTLS
    SMTP_USER=youraccount@163.com   # 发件邮箱
    SMTP_PASS=xxxxxxxxxxxxxxxx      # 邮箱的 "授权码" (不是登录密码)
    SMTP_FROM=youraccount@163.com   # 可选,缺省=SMTP_USER
"""
import smtplib
from email.message import EmailMessage

from database import settings


def send_email(to: str, subject: str, body: str) -> None:
    """同步发送一封纯文本邮件。SMTP 未配置或发送失败时 raise。"""
    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_pass or "").strip()
    if not host or not user or not password:
        raise RuntimeError("SMTP 未配置:请在 backend/.env 设置 SMTP_HOST/SMTP_USER/SMTP_PASS")

    port = int(settings.smtp_port or 465)
    sender = (settings.smtp_from or "").strip() or user

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

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

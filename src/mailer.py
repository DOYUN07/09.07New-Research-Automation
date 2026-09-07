"""Gmail SMTP 발송.

앱 비밀번호는 코드에 절대 넣지 않습니다.
GitHub 저장소 → Settings → Secrets and variables → Actions 에서
  SMTP_USER      보내는 Gmail 주소
  SMTP_PASSWORD  Gmail 앱 비밀번호 16자리 (일반 비밀번호 아님)
두 개를 등록하면 그때부터 발송이 켜집니다. 등록 전에는 발송을 건너뛰고
결과를 파일(out/brief.html)로만 남깁니다.
"""
from __future__ import annotations

import os
import smtplib
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from pathlib import Path


class MailNotConfigured(Exception):
    """SMTP 자격증명이 아직 등록되지 않음 — 오류가 아니라 '아직 설정 전' 상태."""


def is_configured() -> bool:
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def send(
    subject: str,
    html_body: str,
    text_body: str,
    recipients: list[str],
    sender_name: str = "공고 브리핑",
    attachments: list[Path] | None = None,
) -> None:
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "465"))

    if not user or not password:
        raise MailNotConfigured(
            "SMTP_USER / SMTP_PASSWORD 가 설정되지 않았습니다. "
            "GitHub Secrets에 등록하면 발송이 시작됩니다."
        )
    if not recipients:
        raise MailNotConfigured("수신자가 없습니다. config.yaml의 recipients를 확인하세요.")

    body = MIMEMultipart("alternative")
    body.attach(MIMEText(text_body, "plain", "utf-8"))
    body.attach(MIMEText(html_body, "html", "utf-8"))

    files = [p for p in (attachments or []) if p and p.exists()]
    if files:
        msg = MIMEMultipart("mixed")
        msg.attach(body)
        for p in files:
            part = MIMEApplication(p.read_bytes(), _subtype="octet-stream")
            # 파일명이 한글이어도 깨지지 않도록 RFC 2231 형식으로 넣는다
            part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", p.name))
            msg.attach(part)
    else:
        msg = body

    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(sender_name, "utf-8")), user))
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=45) as smtp:
            smtp.login(user, password)
            smtp.sendmail(user, recipients, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=45) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, recipients, msg.as_string())

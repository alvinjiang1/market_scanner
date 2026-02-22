"""
Notification module - send reports via Telegram, Email, or WhatsApp.
"""

import logging
from pathlib import Path
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


def send_telegram(message: str, parse_mode: Optional[str] = None) -> bool:
    """Send message via Telegram Bot API."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram has 4096 char limit - split long messages
    max_len = 4000
    for i in range(0, len(message), max_len):
        chunk = message[i : i + max_len]
        payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": chunk}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    return True


def send_email(subject: str, body: str, attachment_path: Optional[Path] = None) -> bool:
    """Send email via SMTP."""
    if not config.EMAIL_FROM or not config.EMAIL_TO or not config.EMAIL_PASSWORD:
        logger.warning("Email not configured (EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD)")
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_FROM
        msg["To"] = config.EMAIL_TO
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={attachment_path.name}")
            msg.attach(part)

        with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_FROM, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_FROM, config.EMAIL_TO, msg.as_string())

        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_whatsapp(message: str) -> bool:
    """Send message via Twilio WhatsApp API."""
    if not all(
        [
            config.TWILIO_ACCOUNT_SID,
            config.TWILIO_AUTH_TOKEN,
            config.TWILIO_WHATSAPP_FROM,
            config.TWILIO_WHATSAPP_TO,
        ]
    ):
        logger.warning("WhatsApp not configured (Twilio credentials)")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"
    payload = {
        "From": config.TWILIO_WHATSAPP_FROM,
        "To": config.TWILIO_WHATSAPP_TO,
        "Body": message,
    }
    try:
        r = requests.post(
            url,
            data=payload,
            auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return False


def send_report(report_content: str, session: str) -> bool:
    """
    Send report via all configured notification methods.
    Returns True if at least one method succeeded.
    """
    subject = f"Algo Trading Bot - {session} Report"
    report_path = config.REPORTS_DIR / f"report_latest.txt"
    report_path.write_text(report_content, encoding="utf-8")

    success = False
    for method in config.NOTIFICATION_METHODS:
        if method == "telegram":
            # Use plain text - report may contain characters that break HTML
            if send_telegram(report_content[:4000], parse_mode=None):
                success = True
        elif method == "email":
            if send_email(subject, report_content, report_path):
                success = True
        elif method == "whatsapp":
            if send_whatsapp(report_content[:1500]):  # WhatsApp has length limits
                success = True

    return success

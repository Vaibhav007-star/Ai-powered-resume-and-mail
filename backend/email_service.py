import os
import re
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.config import BASE_DIR, DRY_RUN

logger = logging.getLogger(__name__)

# Directory to save dry run email previews
PREVIEWS_DIR = BASE_DIR / "data" / "sent_previews"
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

def is_valid_email(email_str: str) -> bool:
    """Validate email address format."""
    if not email_str:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email_str.strip()))

def send_application_email(
    recipient_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    sender_email: Optional[str] = None,
    override_dry_run: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Dispatches an application email with resume attachment.
    Enforces DRY_RUN safety mode by default to prevent accidental real emails during development.
    """
    recipient = recipient_email.strip()
    if not is_valid_email(recipient):
        raise ValueError(f"Invalid recipient email address: '{recipient_email}'")

    if not subject.strip():
        raise ValueError("Email subject cannot be empty.")

    if not body.strip():
        raise ValueError("Email body cannot be empty.")

    dry_run_active = DRY_RUN if override_dry_run is None else override_dry_run
    sender = sender_email or os.getenv("SMTP_USERNAME") or "candidate@assistant.local"

    # Assemble MIME Message
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach resume if provided and exists
    attached_file_name = None
    if attachment_path:
        attach_path = Path(attachment_path)
        if attach_path.exists() and attach_path.is_file():
            attached_file_name = attach_path.name
            with open(attach_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=attached_file_name)
            part["Content-Disposition"] = f'attachment; filename="{attached_file_name}"'
            msg.attach(part)
        else:
            logger.warning(f"Attachment file not found at {attachment_path}. Sending without attachment.")

    # 1. DRY RUN / SAFE PREVIEW MODE
    if dry_run_active:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_recipient = re.sub(r"[^a-zA-Z0-9_.-]", "_", recipient)
        preview_filename = f"preview_{timestamp_str}_{safe_recipient}.eml"
        preview_file_path = PREVIEWS_DIR / preview_filename

        with open(preview_file_path, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        logger.info(f"[DRY RUN] Email logged to preview file: {preview_file_path}")

        return {
            "success": True,
            "dry_run": True,
            "message": "Application processed in SAFE DRY-RUN mode. Email preview was logged without sending live.",
            "recipient": recipient,
            "subject": subject,
            "attached_file": attached_file_name,
            "preview_file": str(preview_file_path),
            "sent_at": datetime.now(timezone.utc).isoformat()
        }

    # 2. LIVE SMTP MODE
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USERNAME", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()

    if not smtp_user or not smtp_pass:
        raise ValueError(
            "SMTP credentials not configured in .env. Please configure SMTP_USERNAME and SMTP_PASSWORD, "
            "or set DRY_RUN=True to use safe preview mode."
        )

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Live application email successfully sent to {recipient}")

        return {
            "success": True,
            "dry_run": False,
            "message": f"Application email successfully dispatched to {recipient}.",
            "recipient": recipient,
            "subject": subject,
            "attached_file": attached_file_name,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
    except smtplib.SMTPAuthenticationError:
        raise ValueError("SMTP Authentication failed. Please verify your email and app password in .env.")
    except Exception as e:
        raise RuntimeError(f"Failed to send email via SMTP: {str(e)}")


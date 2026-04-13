import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NotifierConfig:
    smtp_host: str
    smtp_port: int
    sender: str
    recipient: str
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True


class Notifier:
    def __init__(self, config: NotifierConfig):
        self.config = config

    def send_alert(self, subject: str, body: str) -> bool:
        """Send an email alert. Returns True on success, False on failure."""
        msg = MIMEMultipart()
        msg["From"] = self.config.sender
        msg["To"] = self.config.recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)
                server.sendmail(self.config.sender, self.config.recipient, msg.as_string())
            logger.info("Alert sent: %s", subject)
            return True
        except smtplib.SMTPException as e:
            logger.error("Failed to send alert '%s': %s", subject, e)
            return False

    def notify_failure(self, job_name: str, error: Optional[str] = None) -> bool:
        subject = f"[cronwatcher] Job FAILED: {job_name}"
        body = f"Cron job '{job_name}' has failed."
        if error:
            body += f"\n\nError details:\n{error}"
        return self.send_alert(subject, body)

    def notify_missed(self, job_name: str, schedule: str) -> bool:
        subject = f"[cronwatcher] Job MISSED: {job_name}"
        body = (
            f"Cron job '{job_name}' did not run as scheduled.\n"
            f"Expected schedule: {schedule}"
        )
        return self.send_alert(subject, body)

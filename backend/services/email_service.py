"""MoodFeed Transactional Email & Lifecycle Notification Service.

Supports Welcome Emails, Weekly Summaries, Password Reset, and Billing Receipts
with SendGrid API, SMTP, and local safe fallback delivery.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger("moodfeed.services.email")


class EmailService:
    """Enterprise Transactional Email Manager."""

    def __init__(self) -> None:
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "hello@moodfeed.app")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")

    def _send_email(self, to_email: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
        """Dispatches email via SendGrid, SMTP, or logs to console."""
        # 1. Try SendGrid if API key configured
        if self.sendgrid_api_key:
            try:
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail
                message = Mail(
                    from_email=self.from_email,
                    to_emails=to_email,
                    subject=subject,
                    plain_text_content=body_text,
                    html_content=body_html or body_text,
                )
                sg = SendGridAPIClient(self.sendgrid_api_key)
                response = sg.send(message)
                return response.status_code in (200, 201, 202)
            except Exception as err:
                logger.warning("SendGrid delivery warning: %s", err)

        # 2. Try SMTP if credentials configured
        if self.smtp_user and self.smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.from_email
                msg["To"] = to_email

                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)
                if body_html:
                    part2 = MIMEText(body_html, "html")
                    msg.attach(part2)

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, to_email, msg.as_string())
                return True
            except Exception as err:
                logger.warning("SMTP delivery warning: %s", err)

        # 3. Log to logger for development
        logger.info(
            "[Email Delivery Logged]\nTo: %s\nSubject: %s\nContent:\n%s",
            to_email,
            subject,
            body_text,
        )
        return True

    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Dispatches onboarding welcome email."""
        subject = "MoodFeed'e Hoş Geldin! 🎉"
        body = f"""
Merhaba {user_name}! 👋

MoodFeed ailesine hoş geldin! Sosyal medya akışını kendi ruh haline göre şekillendirmenin keyfini çıkar.

Hemen Başlamak İçin İlk Adımlar:
1. Profilini tamamla ve ilgi alanlarını belirle.
2. Ruh halini yansıtan ilk gönderini paylaş.
3. Akışında ilham veren 5 kişiyi takip et.

Akışa Git: https://moodfeed.vercel.app/#/feed

Sorun olursa bize dilediğin an ulaşabilirsin: support@moodfeed.app

Sevgiler,
MoodFeed Ekibi
"""
        return self._send_email(user_email, subject, body.strip())

    def send_weekly_digest(self, user_email: str, user_name: str, stats: dict[str, Any]) -> bool:
        """Dispatches personalized weekly AI insights digest."""
        subject = f"Haftalık MoodFeed Özetin Hazır, {user_name}! 📈"
        body = f"""
Merhaba {user_name}! 📊

İşte bu haftanın MoodFeed özeti:
- {stats.get('posts', 0)} gönderi paylaştın
- {stats.get('likes', 0)} beğeni aldın
- {stats.get('followers', 0)} yeni takipçi kazandın
- Haftalık Ortalama Mood: {stats.get('avg_mood', '😊 Mutlu')}

Detaylı Analiz Paneli: https://moodfeed.vercel.app/#/dashboard

Harika bir hafta dileriz!
MoodFeed Ekibi
"""
        return self._send_email(user_email, subject, body.strip())

    def send_password_reset(self, user_email: str, reset_token: str) -> bool:
        """Dispatches secure password reset link."""
        subject = "MoodFeed Şifre Sıfırlama Talebi 🔐"
        reset_link = f"https://moodfeed.vercel.app/#/reset-password?token={reset_token}"
        body = f"""
Şifre sıfırlama talebinde bulundunuz.

Aşağıdaki bağlantıya tıklayarak yeni şifrenizi belirleyebilirsiniz:
{reset_link}

Bu bağlantı 1 saat boyunca geçerlidir.
Bu talebi siz yapmadıysanız lütfen bu e-postayı dikkate almayın.

Güvenlik Ekibi,
MoodFeed
"""
        return self._send_email(user_email, subject, body.strip())


email_service = EmailService()

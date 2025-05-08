# --coding: utf-8 --
import smtplib
from email.mime.text import MIMEText
from email.header import Header

from utils.logger import logger


class Email:
    def __init__(self):
        pass

    def send_email(self, subject, body, email_config):
        """
        发送邮件
        """
        try:
            email_send = email_config["email_send"]

            if email_send == "true":
                try:
                    recipients = [e.strip() for e in email_config["email_to"].split(",")]

                    msg = MIMEText(body, "plain", "utf-8")
                    msg["From"] = email_config["email_account"]
                    msg["To"] = ", ".join(recipients)
                    msg["Subject"] = Header(subject, "utf-8")

                    with smtplib.SMTP_SSL(
                        email_config["smtp_server"], email_config["smtp_port"]
                    ) as server:
                        server.login(
                            email_config["email_account"], email_config["email_pass"]
                        )
                        server.sendmail(
                            email_config["email_account"], recipients, msg.as_string()
                        )

                    logger.info(f"Email sent to {len(recipients)} recipients: {subject}")
                except Exception as e:
                    logger.error(f"Failed to send email: {e}")
            else:
                logger.info(body)
        except Exception as e:
            logger.error(f"Failed to deal email config: {e}")

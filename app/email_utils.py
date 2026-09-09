import smtplib
from email.mime.text import MIMEText

from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM


def send_reset_email(to_email: str, reset_link: str) -> None:
    subject = "Réinitialisation de votre mot de passe MIABEWIFI"
    body = (
        "Bonjour,\n\n"
        "Vous avez demandé la réinitialisation de votre mot de passe MIABEWIFI.\n"
        "Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe "
        f"(ce lien expire dans 30 minutes) :\n\n{reset_link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet email.\n\n"
        "— L'équipe MIABEWIFI"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())

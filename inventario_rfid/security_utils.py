import base64
import hashlib
import secrets
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer


def _fernet():
    secret = current_app.config["DATA_ENCRYPTION_KEY"].encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_value(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        value = str(value)
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value):
    if value in (None, ""):
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value


def blind_index(value):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def build_signed_token(user, purpose):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"user_id": user.id, "purpose": purpose})


def read_signed_token(token):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.loads(token, max_age=current_app.config["RESET_TOKEN_MAX_AGE"])


def build_reset_token(user):
    return build_signed_token(user, "password-reset")


def read_reset_token(token):
    return read_signed_token(token)


def build_verify_email_token(user):
    return build_signed_token(user, "email-verify")


def generate_temporary_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_reset_email(user):
    token = build_reset_token(user)
    reset_url = current_app.config["APP_BASE_URL"].rstrip("/") + url_for("reset_password", token=token)
    subject = "Recuperacion de contrasena - Trazia RFID"
    text_body = (
        f"Hola {user.full_name},\n\n"
        "Recibimos una solicitud de recuperacion de contrasena.\n"
        f"Usa este enlace: {reset_url}\n\n"
        "Si no solicitaste este cambio, ignora este mensaje."
    )
    html_body = (
        f"<p>Hola <strong>{user.full_name}</strong>,</p>"
        "<p>Recibimos una solicitud de recuperacion de contrasena.</p>"
        f"<p><a href=\"{reset_url}\">Restablecer contrasena</a></p>"
        "<p>Si no solicitaste este cambio, ignora este mensaje.</p>"
    )

    if not current_app.config["MAIL_ENABLED"]:
        return False, reset_url

    _send_email(user.email, subject, text_body, html_body)
    return True, reset_url


def send_temporary_password_email(user, temporary_password):
    login_url = current_app.config["APP_BASE_URL"].rstrip("/") + url_for("login")
    subject = "Acceso temporal - Trazia RFID"
    text_body = (
        f"Hola {user.full_name},\n\n"
        "Se genero una contrasena temporal para tu cuenta.\n"
        f"Usuario: {user.username}\n"
        f"Contrasena temporal: {temporary_password}\n"
        f"Ingreso: {login_url}\n\n"
        "Debes cambiarla inmediatamente al iniciar sesion."
    )
    html_body = (
        f"<p>Hola <strong>{user.full_name}</strong>,</p>"
        "<p>Se genero una contrasena temporal para tu cuenta.</p>"
        f"<p><strong>Usuario:</strong> {user.username}<br>"
        f"<strong>Contrasena temporal:</strong> {temporary_password}</p>"
        f"<p><a href=\"{login_url}\">Ingresar a la plataforma</a></p>"
        "<p>Debes cambiarla inmediatamente al iniciar sesion.</p>"
    )

    if not current_app.config["MAIL_ENABLED"]:
        return False, temporary_password

    _send_email(user.email, subject, text_body, html_body)
    return True, None


def send_verification_email(user):
    token = build_verify_email_token(user)
    verify_url = current_app.config["APP_BASE_URL"].rstrip("/") + url_for("verify_email", token=token)
    subject = "Verifica tu correo - Trazia RFID"
    text_body = (
        f"Hola {user.full_name},\n\n"
        "Verifica tu correo para activar completamente tu cuenta.\n"
        f"Enlace: {verify_url}"
    )
    html_body = (
        f"<p>Hola <strong>{user.full_name}</strong>,</p>"
        "<p>Verifica tu correo para activar completamente tu cuenta.</p>"
        f"<p><a href=\"{verify_url}\">Verificar correo</a></p>"
    )

    if not current_app.config["MAIL_ENABLED"]:
        return False, verify_url

    _send_email(user.email, subject, text_body, html_body)
    return True, verify_url


def _send_email(to_email, subject, text_body, html_body):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"]) as server:
        if current_app.config["MAIL_USE_TLS"]:
            server.starttls()
        if current_app.config["MAIL_USERNAME"]:
            try:
                server.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
            except smtplib.SMTPAuthenticationError as exc:
                raise RuntimeError(
                    "Gmail rechazo la autenticacion SMTP. Usa una App Password de Google en MAIL_PASSWORD en lugar de la contrasena normal."
                ) from exc
        server.sendmail(message["From"], [message["To"]], message.as_string())

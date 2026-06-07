from datetime import datetime

from flask import current_app, render_template
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

from extensions import mail


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_email_token(email):
    return _serializer().dumps(email, salt=current_app.config["SECURITY_PASSWORD_SALT"] + "-verify")


def confirm_email_token(token, expiration_seconds):
    return _serializer().loads(
        token,
        salt=current_app.config["SECURITY_PASSWORD_SALT"] + "-verify",
        max_age=expiration_seconds,
    )


def generate_password_reset_token(email):
    return _serializer().dumps(email, salt=current_app.config["SECURITY_PASSWORD_SALT"] + "-reset")


def confirm_password_reset_token(token, expiration_seconds):
    return _serializer().loads(
        token,
        salt=current_app.config["SECURITY_PASSWORD_SALT"] + "-reset",
        max_age=expiration_seconds,
    )


def send_email(to, subject, template, **context):
    html_body = render_template(f"emails/{template}.html", **context)
    text_body = render_template(f"emails/{template}.txt", **context)
    message = Message(subject=subject, recipients=[to], html=html_body, body=text_body)
    mail.send(message)


def send_verification_email(user):
    expiration_hours = current_app.config["EMAIL_TOKEN_EXPIRATION_HOURS"]
    token = generate_email_token(user.email)
    action_url = current_app.config["APP_BASE_URL"].rstrip("/") + f"/verify-email/{token}"
    email_logo_url = (
        current_app.config["APP_BASE_URL"].rstrip("/")
        + "/static/"
        + current_app.config["BRAND_EMAIL_LOGO_PATH"].lstrip("/")
    )
    send_email(
        user.email,
        f"Verifica tu cuenta - {current_app.config['APP_NAME']}",
        "verify_account",
        user=user,
        action_url=action_url,
        expiration_hours=expiration_hours,
        app_name=current_app.config["APP_NAME"],
        current_year=datetime.utcnow().year,
        email_logo_url=email_logo_url,
    )


def send_password_reset_email(user):
    expiration_hours = current_app.config["PASSWORD_RESET_EXPIRATION_HOURS"]
    token = generate_password_reset_token(user.email)
    action_url = current_app.config["APP_BASE_URL"].rstrip("/") + f"/reset-password/{token}"
    email_logo_url = (
        current_app.config["APP_BASE_URL"].rstrip("/")
        + "/static/"
        + current_app.config["BRAND_EMAIL_LOGO_PATH"].lstrip("/")
    )
    send_email(
        user.email,
        f"Restablece tu contraseña - {current_app.config['APP_NAME']}",
        "reset_password",
        user=user,
        action_url=action_url,
        expiration_hours=expiration_hours,
        app_name=current_app.config["APP_NAME"],
        current_year=datetime.utcnow().year,
        email_logo_url=email_logo_url,
    )

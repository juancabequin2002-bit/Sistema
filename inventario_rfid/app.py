import csv
import io
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import qrcode
from qrcode.image.pil import PilImage

import click
import requests
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from config import Config
from decorators import role_required
from extensions import mail
from forms import (
    AIQuestionForm,
    AssetForm,
    AssignmentForm,
    BarcodeForm,
    ChangePasswordForm,
    DisposalForm,
    DocumentForm,
    ForgotPasswordForm,
    LoginForm,
    LocationForm,
    MaintenanceForm,
    NFCForm,
    RFIDForm,
    RegisterForm,
    ResendVerificationForm,
    ReportFilterForm,
    ResetPasswordForm,
    RoleChangeForm,
    ScanForm,
    UserCreateForm,
    UserEditForm,
)
from models import (
    ROLE_ADMIN,
    ROLE_AUDITOR,
    ROLE_TECH,
    ROLE_VIEW,
    Asset,
    AssetAssignment,
    AssetDisposal,
    AssetDocument,
    AssetMovement,
    Location,
    MaintenanceRecord,
    SystemLog,
    User,
    db,
)
from services.email_service import (
    confirm_email_token,
    confirm_password_reset_token,
    send_password_reset_email,
    send_verification_email,
)
from security_utils import (
    blind_index,
    generate_temporary_password,
    send_temporary_password_email,
)


app = Flask(__name__)
app.config.from_object(Config)

from api import api_bp
app.register_blueprint(api_bp)

Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

db.init_app(app)
mail.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesion para continuar."


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        response = jsonify({"ok": False, "message": "Sesion no iniciada. Debes autenticarte."})
        response.status_code = 401
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    return redirect(url_for("login", next=request.path))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def save_uploaded_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None
    if not allowed_file(file_storage.filename):
        raise ValueError("Tipo de archivo no permitido.")
    original_filename = secure_filename(file_storage.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = Path(app.config["UPLOAD_FOLDER"]) / stored_filename
    file_storage.save(file_path)
    return stored_filename, original_filename


def generate_virtual_rfid_code():
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"VRFID-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


def generate_qr_for_asset(asset):
    qr_dir = Path(app.config["UPLOAD_FOLDER"]) / "qr"
    qr_dir.mkdir(parents=True, exist_ok=True)
    qr_data = f"{app.config.get('APP_BASE_URL', '')}/activos/{asset.id}"
    img = qrcode.make(qr_data, image_factory=PilImage, box_size=10, border=2)
    filename = f"qr_{asset.internal_code.replace(' ', '_')}_{asset.id}.png"
    filepath = qr_dir / filename
    img.save(str(filepath))
    return filename


def get_qr_filename(asset):
    qr_dir = Path(app.config["UPLOAD_FOLDER"]) / "qr"
    filename = f"qr_{asset.internal_code.replace(' ', '_')}_{asset.id}.png"
    filepath = qr_dir / filename
    if filepath.exists():
        return filename
    return None


def normalize_identifier(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def resolve_asset_by_identifier(identifier_type, code):
    cleaned_code = normalize_identifier(code)
    if not cleaned_code:
        return None
    if identifier_type == "rfid":
        return Asset.query.filter_by(rfid_code=cleaned_code).first()
    if identifier_type == "nfc":
        return Asset.query.filter_by(nfc_code=cleaned_code).first()
    if identifier_type == "barcode":
        return Asset.query.filter_by(barcode_code=cleaned_code).first()
    return None


def validate_unique_asset_identifiers(rfid_code, nfc_code, barcode_code, asset_id=None):
    checks = [
        ("RFID", "rfid_code", rfid_code),
        ("NFC", "nfc_code", nfc_code),
        ("codigo de barras", "barcode_code", barcode_code),
    ]
    for label, field_name, value in checks:
        if not value:
            continue
        query = Asset.query.filter(getattr(Asset, field_name) == value)
        if asset_id:
            query = query.filter(Asset.id != asset_id)
        if query.first():
            raise ValueError(f"Ya existe un activo con ese {label}.")


def log_action(action, module, description, user=None):
    log = SystemLog(
        user_id=getattr(user, "id", None),
        action=action,
        module=module,
        description=description,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    db.session.add(log)
    db.session.commit()


def asset_history(asset):
    events = []

    events.append(
        {
            "date": asset.created_at,
            "label": "Creacion del activo",
            "detail": f"Activo creado con estado {asset.status}.",
            "module": "activos",
        }
    )
    for assignment in asset.assignments:
        events.append(
            {
                "date": datetime.combine(assignment.assignment_date, datetime.min.time()),
                "label": "Asignacion",
                "detail": f"{assignment.previous_responsible or 'Sin responsable'} -> {assignment.new_responsible}",
                "module": "asignaciones",
            }
        )
    for maintenance in asset.maintenances:
        events.append(
            {
                "date": datetime.combine(maintenance.maintenance_date, datetime.min.time()),
                "label": "Mantenimiento",
                "detail": f"{maintenance.maintenance_type.capitalize()} por {maintenance.technician_name}",
                "module": "mantenimientos",
            }
        )
    for document in asset.documents:
        events.append(
            {
                "date": document.created_at,
                "label": "Documento cargado",
                "detail": f"{document.document_name} ({document.document_type})",
                "module": "documentos",
            }
        )
    for movement in asset.movements:
        events.append(
            {
                "date": datetime.combine(movement.movement_date, datetime.min.time()),
                "label": movement.movement_type,
                "detail": f"{movement.from_location or 'N/D'} -> {movement.to_location or 'N/D'}",
                "module": "movimientos",
            }
        )
    if asset.disposal:
        events.append(
            {
                "date": datetime.combine(asset.disposal.disposal_date, datetime.min.time()),
                "label": "Baja del activo",
                "detail": asset.disposal.reason,
                "module": "bajas",
            }
        )

    return sorted(events, key=lambda event: event["date"], reverse=True)


def build_dashboard_context():
    today = date.today()
    maintenance_limit = today + timedelta(days=app.config["MAINTENANCE_ALERT_DAYS"])
    warranty_limit = today + timedelta(days=app.config["WARRANTY_ALERT_DAYS"])

    total_assets = Asset.query.count()
    active_assets = Asset.query.filter_by(status="activo").count()
    maintenance_assets = Asset.query.filter_by(status="mantenimiento").count()
    disposed_assets = Asset.query.filter_by(status="dado_de_baja").count()
    active_users = User.query.filter_by(is_active_user=True).count()

    upcoming_maintenances = MaintenanceRecord.query.filter(
        MaintenanceRecord.next_maintenance_date.isnot(None),
        MaintenanceRecord.next_maintenance_date <= maintenance_limit,
    ).order_by(MaintenanceRecord.next_maintenance_date.asc()).limit(5).all()

    upcoming_warranties = Asset.query.filter(
        Asset.warranty_until.isnot(None),
        Asset.warranty_until <= warranty_limit,
    ).order_by(Asset.warranty_until.asc()).limit(5).all()

    category_rows = (
        db.session.query(Asset.category, db.func.count(Asset.id))
        .group_by(Asset.category)
        .order_by(db.func.count(Asset.id).desc())
        .all()
    )
    status_rows = (
        db.session.query(Asset.status, db.func.count(Asset.id))
        .group_by(Asset.status)
        .order_by(db.func.count(Asset.id).desc())
        .all()
    )

    latest_movements = AssetMovement.query.order_by(AssetMovement.created_at.desc()).limit(6).all()
    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(8).all()
    highlighted_asset = Asset.query.order_by(Asset.updated_at.desc()).first()
    category_total = sum(row[1] for row in category_rows) or 1
    category_breakdown = [
        {
            "label": row[0] or "Sin categoria",
            "count": row[1],
            "percent": round((row[1] / category_total) * 100, 1),
        }
        for row in category_rows[:6]
    ]
    alerts = []
    if upcoming_maintenances:
        alerts.append(f"{len(upcoming_maintenances)} activos requieren mantenimiento proximo.")
    if upcoming_warranties:
        alerts.append(f"{len(upcoming_warranties)} garantias estan proximas a vencer.")
    if Asset.query.filter((Asset.responsible_name.is_(None)) | (Asset.responsible_name == "")).count():
        alerts.append("Existen activos sin responsable asignado.")
    if Asset.query.filter(Asset.location_id.is_(None)).count():
        alerts.append("Existen activos sin ubicacion asignada.")

    return {
        "stats": {
            "total_assets": total_assets,
            "active_assets": active_assets,
            "maintenance_assets": maintenance_assets,
            "disposed_assets": disposed_assets,
            "active_users": active_users,
            "upcoming_maintenance_count": len(upcoming_maintenances),
            "upcoming_warranty_count": len(upcoming_warranties),
            "assets_without_responsible": Asset.query.filter(
                (Asset.responsible_name.is_(None)) | (Asset.responsible_name == "")
            ).count(),
            "assets_without_location": Asset.query.filter(Asset.location_id.is_(None)).count(),
        },
        "upcoming_maintenances": upcoming_maintenances,
        "upcoming_warranties": upcoming_warranties,
        "category_labels": [row[0] or "Sin categoria" for row in category_rows],
        "category_values": [row[1] for row in category_rows],
        "status_labels": [row[0].replace("_", " ").capitalize() for row in status_rows],
        "status_values": [row[1] for row in status_rows],
        "latest_movements": latest_movements,
        "recent_logs": recent_logs,
        "highlighted_asset": highlighted_asset,
        "category_breakdown": category_breakdown,
        "alerts": alerts,
    }


def build_alert_context():
    today = date.today()
    maintenance_limit = today + timedelta(days=app.config["MAINTENANCE_ALERT_DAYS"])
    warranty_limit = today + timedelta(days=app.config["WARRANTY_ALERT_DAYS"])
    return {
        "upcoming_maintenances": MaintenanceRecord.query.filter(
            MaintenanceRecord.next_maintenance_date.isnot(None),
            MaintenanceRecord.next_maintenance_date <= maintenance_limit,
        ).order_by(MaintenanceRecord.next_maintenance_date.asc()).all(),
        "upcoming_warranties": Asset.query.filter(
            Asset.warranty_until.isnot(None),
            Asset.warranty_until <= warranty_limit,
        ).order_by(Asset.warranty_until.asc()).all(),
        "assets_without_responsible": Asset.query.filter(
            (Asset.responsible_name.is_(None)) | (Asset.responsible_name == "")
        ).order_by(Asset.created_at.desc()).all(),
        "assets_without_location": Asset.query.filter(
            Asset.location_id.is_(None)
        ).order_by(Asset.created_at.desc()).all(),
    }


def get_topbar_alert_count():
    today = date.today()
    maintenance_limit = today + timedelta(days=app.config["MAINTENANCE_ALERT_DAYS"])
    warranty_limit = today + timedelta(days=app.config["WARRANTY_ALERT_DAYS"])
    return (
        MaintenanceRecord.query.filter(
            MaintenanceRecord.next_maintenance_date.isnot(None),
            MaintenanceRecord.next_maintenance_date <= maintenance_limit,
        ).count()
        + Asset.query.filter(
            Asset.warranty_until.isnot(None),
            Asset.warranty_until <= warranty_limit,
        ).count()
    )


def query_assets():
    query = Asset.query
    search = request.args.get("q", "").strip()
    asset_type = request.args.get("type", "").strip()
    status = request.args.get("status", "").strip()
    location = request.args.get("location", "").strip()
    responsible = request.args.get("responsible", "").strip()

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Asset.rfid_code.ilike(like),
                Asset.nfc_code.ilike(like),
                Asset.barcode_code.ilike(like),
                Asset.name.ilike(like),
                Asset.responsible_name.ilike(like),
                Asset.internal_code.ilike(like),
                Asset.serial_number_hash == blind_index(search),
                Asset.invoice_number_hash == blind_index(search),
            )
        )
    if asset_type:
        query = query.filter_by(asset_type=asset_type)
    if status:
        query = query.filter_by(status=status)
    if location:
        query = query.join(Location, isouter=True).filter(Location.name == location)
    if responsible:
        query = query.filter(Asset.responsible_name.ilike(f"%{responsible}%"))

    return query.order_by(Asset.created_at.desc()).all()


def serialize_asset_for_ai(asset):
    return {
        "nombre": asset.name,
        "tipo": asset.asset_type,
        "categoria": asset.category,
        "rfid": asset.rfid_code,
        "nfc": asset.nfc_code,
        "barcode": asset.barcode_code,
        "codigo_interno": asset.internal_code,
        "serial": asset.serial_number,
        "estado": asset.status,
        "responsable": asset.current_responsible,
        "ubicacion": asset.current_location,
        "garantia_hasta": asset.warranty_until.isoformat() if asset.warranty_until else None,
        "observaciones": asset.observations,
        "mantenimientos": [
            {
                "fecha": item.maintenance_date.isoformat(),
                "tipo": item.maintenance_type,
                "tecnico": item.technician_name,
                "descripcion": item.description,
            }
            for item in asset.maintenances[-5:]
        ],
    }


def ask_gpt4all(question, asset):
    if not app.config["GPT4ALL_ENABLED"]:
        raise RuntimeError("La integracion GPT4All esta deshabilitada por configuracion.")

    system_prompt = (
        "Eres un asistente tecnico para inventario RFID de oficina. "
        "Responde de forma profesional, breve y accionable. "
        "Si faltan datos, dilo con claridad y evita inventar."
    )
    user_prompt = (
        f"Activo: {serialize_asset_for_ai(asset)}\n"
        f"Pregunta: {question}\n"
        "Entrega recomendaciones tecnicas, riesgos, mantenimiento sugerido y observaciones relevantes."
    )

    if app.config["GPT4ALL_MODE"] == "server":
        response = requests.post(
            f"{app.config['GPT4ALL_SERVER_URL'].rstrip('/')}/chat/completions",
            json={
                "model": app.config["GPT4ALL_MODEL"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 350,
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    if app.config["GPT4ALL_MODE"] == "sdk":
        from gpt4all import GPT4All

        model = GPT4All(app.config["GPT4ALL_SDK_MODEL"])
        with model.chat_session(system_prompt):
            return model.generate(user_prompt, max_tokens=350, temp=0.2)

    raise RuntimeError("Modo GPT4All no soportado.")


def ensure_schema_compatibility():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []

    if "email_verified_at" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN email_verified_at DATETIME")
    if "password_reset_requested_at" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_reset_requested_at DATETIME")
    if "force_password_change" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN force_password_change BOOLEAN DEFAULT 0 NOT NULL")
    if "temporary_password_expires_at" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN temporary_password_expires_at DATETIME")
    if "password_changed_at" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_changed_at DATETIME")

    if "assets" in inspector.get_table_names():
        asset_columns = {column["name"] for column in inspector.get_columns("assets")}
        if "nfc_code" not in asset_columns:
            statements.append("ALTER TABLE assets ADD COLUMN nfc_code VARCHAR(120)")
        if "barcode_code" not in asset_columns:
            statements.append("ALTER TABLE assets ADD COLUMN barcode_code VARCHAR(120)")
        if "identification_technology" not in asset_columns:
            statements.append("ALTER TABLE assets ADD COLUMN identification_technology VARCHAR(30) DEFAULT 'rfid_125khz'")

    for statement in statements:
        db.session.execute(text(statement))

    if statements:
        db.session.commit()


def seed_admin():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            full_name="Administrador del Sistema",
            username="admin",
            email="admin@example.com",
            role=ROLE_ADMIN,
            is_active_user=True,
            email_verified=True,
        )
        admin.set_password("admin123")
        db.session.add(admin)

    initial_locations = [
        "Oficina Sistemas",
        "Sala de Servidores",
        "Archivo Central",
        "Administracion",
        "Bodega",
    ]
    for location_name in initial_locations:
        if not Location.query.filter_by(name=location_name).first():
            db.session.add(Location(name=location_name, description=f"Ubicacion inicial: {location_name}"))

    db.session.commit()
    return admin


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    ensure_schema_compatibility()
    admin = seed_admin()
    click.echo(f"Base de datos inicializada. Usuario admin: {admin.username}")


@app.context_processor
def inject_globals():
    static_folder = Path(app.static_folder)
    return {
        "PLATFORM_NAME": app.config["PLATFORM_NAME"],
        "PLATFORM_TAGLINE": app.config["PLATFORM_TAGLINE"],
        "APP_NAME": app.config["APP_NAME"],
        "ROLE_ADMIN": ROLE_ADMIN,
        "ROLE_TECH": ROLE_TECH,
        "ROLE_VIEW": ROLE_VIEW,
        "ROLE_AUDITOR": ROLE_AUDITOR,
        "current_year": datetime.utcnow().year,
        "BRAND_LOGO_PATH": app.config["BRAND_LOGO_PATH"],
        "BRAND_MARK_PATH": app.config["BRAND_MARK_PATH"],
        "BRAND_EMAIL_LOGO_PATH": app.config["BRAND_EMAIL_LOGO_PATH"],
        "BRAND_FAVICON_PATH": app.config["BRAND_FAVICON_PATH"],
        "BRAND_LOGO_EXISTS": (static_folder / app.config["BRAND_LOGO_PATH"]).exists(),
        "BRAND_MARK_EXISTS": (static_folder / app.config["BRAND_MARK_PATH"]).exists(),
        "BRAND_EMAIL_LOGO_EXISTS": (static_folder / app.config["BRAND_EMAIL_LOGO_PATH"]).exists(),
        "BRAND_FAVICON_EXISTS": (static_folder / app.config["BRAND_FAVICON_PATH"]).exists(),
        "TOPBAR_ALERT_COUNT": get_topbar_alert_count() if current_user.is_authenticated else 0,
    }


@app.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if not user or not user.is_active_user or not user.check_password(form.password.data):
            flash("Credenciales invalidas o usuario inactivo.", "danger")
        elif app.config["REQUIRE_EMAIL_VERIFICATION"] and not user.email_verified:
            flash("Debes verificar tu correo antes de ingresar.", "warning")
            return redirect(url_for("resend_verification"))
        elif user.force_password_change and user.temporary_password_expires_at and user.temporary_password_expires_at < datetime.utcnow():
            flash("La contrasena temporal vencio. Solicita una nueva recuperacion o acceso temporal.", "danger")
        else:
            login_user(user)
            user.last_access = datetime.utcnow()
            db.session.commit()
            log_action("login", "auth", f"Inicio de sesion de {user.username}", user)
            if not user.email_verified:
                flash("Tu correo aun no esta verificado. Un administrador puede reenviar la verificacion.", "warning")
            flash(f"Bienvenido, {user.full_name}.", "success")
            if user.force_password_change:
                flash("Debes cambiar tu contrasena antes de continuar.", "warning")
                return redirect(url_for("change_password"))
            return redirect(url_for("dashboard"))
    return render_template("login.html", form=form)


@app.route("/registro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data.strip()).first():
            flash("Ese nombre de usuario ya esta en uso.", "danger")
        elif User.query.filter_by(email=form.email.data.strip()).first():
            flash("Ese correo electronico ya esta registrado.", "danger")
        else:
            user = User(
                full_name=form.full_name.data.strip(),
                username=form.username.data.strip(),
                email=form.email.data.strip(),
                role=ROLE_VIEW,
                is_active_user=True,
                email_verified=False,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            log_action("registro", "auth", f"Nuevo usuario registrado: {user.username}", user)
            login_user(user)
            user.last_access = datetime.utcnow()
            db.session.commit()
            flash(f"Bienvenido, {user.full_name}. Tu cuenta ha sido creada exitosamente.", "success")
            return redirect(url_for("dashboard"))
    return render_template("registro.html", form=form)


@app.route("/recuperar-clave", methods=["GET", "POST"])
def forgot_password():
    return redirect(url_for("forgot_password_page"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active_user:
            try:
                user.password_reset_requested_at = datetime.utcnow()
                db.session.commit()
                send_password_reset_email(user)
                log_action("solicitud_reset", "auth", f"Solicitud de reset para {user.username}", user)
            except Exception as exc:
                flash(f"No fue posible procesar el correo de recuperacion: {exc}", "danger")
                return render_template("forgot_password.html", form=form)
        flash("Si el correo existe, enviaremos instrucciones para restablecer la contrasena.", "info")
        return render_template(
            "auth/email_sent.html",
            title="Correo enviado",
            message="Si el correo existe, enviaremos instrucciones para restablecer la contrasena.",
        )
    return render_template("forgot_password.html", form=form)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    try:
        email = confirm_password_reset_token(
            token,
            app.config["PASSWORD_RESET_EXPIRATION_HOURS"] * 3600,
        )
        user = User.query.filter_by(email=email, is_active_user=True).first_or_404()
    except Exception:
        flash("El enlace de recuperacion es invalido o ya vencio.", "danger")
        return redirect(url_for("forgot_password_page"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.force_password_change = False
        user.temporary_password_expires_at = None
        user.password_reset_requested_at = None
        db.session.commit()
        log_action("reset_password", "auth", f"Contrasena restablecida para {user.username}", user)
        flash("La contrasena fue actualizada correctamente.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)


@app.route("/verify-email/<token>")
def verify_email(token):
    try:
        email = confirm_email_token(
            token,
            app.config["EMAIL_TOKEN_EXPIRATION_HOURS"] * 3600,
        )
        user = User.query.filter_by(email=email, is_active_user=True).first_or_404()
    except Exception:
        flash("El enlace de verificacion no es valido o ya vencio.", "danger")
        return redirect(url_for("login"))

    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.session.commit()
    log_action("verificacion_correo", "auth", f"Correo verificado para {user.username}", user)
    flash("Correo verificado correctamente.", "success")
    return redirect(url_for("login"))


@app.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if current_user.is_authenticated:
        user = current_user
        if user.email_verified:
            flash("Tu correo ya fue verificado.", "info")
            return redirect(url_for("dashboard"))
        try:
            send_verification_email(user)
            log_action("reenviar_verificacion", "auth", f"Verificacion reenviada para {user.username}", user)
            return render_template(
                "auth/email_sent.html",
                title="Verificacion enviada",
                message="Reenviamos el correo de verificacion a tu direccion registrada.",
            )
        except Exception as exc:
            flash(f"No fue posible reenviar la verificacion: {exc}", "danger")
            return redirect(url_for("login"))

    form = ResendVerificationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower(), is_active_user=True).first()
        if user and not user.email_verified:
            try:
                send_verification_email(user)
                log_action("reenviar_verificacion", "auth", f"Verificacion reenviada para {user.username}", user)
            except Exception as exc:
                flash(f"No fue posible reenviar la verificacion: {exc}", "danger")
                return render_template("forgot_password.html", form=form)
        return render_template(
            "auth/email_sent.html",
            title="Verificacion enviada",
            message="Si el correo existe y la cuenta no esta verificada, enviaremos un nuevo enlace de verificacion.",
        )
    return render_template("forgot_password.html", form=form, mode="resend")


@app.route("/mi-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("La contrasena actual no coincide.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            current_user.force_password_change = False
            current_user.temporary_password_expires_at = None
            db.session.commit()
            log_action("cambio_password", "auth", f"Contrasena cambiada por {current_user.username}", current_user)
            flash("Contrasena actualizada correctamente.", "success")
            return redirect(url_for("dashboard"))
    return render_template("change_password.html", form=form)


@app.route("/logout")
@login_required
def logout():
    username = current_user.username
    user = current_user
    log_action("logout", "auth", f"Cierre de sesion de {username}", user)
    logout_user()
    flash("Sesion cerrada correctamente.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    context = build_dashboard_context()
    return render_template("dashboard.html", **context)


@app.route("/usuarios")
@login_required
@role_required(ROLE_ADMIN)
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("usuarios/listar.html", users=users)


@app.route("/roles", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def manage_roles():
    if request.method == "POST":
        user = User.query.get_or_404(request.form.get("user_id", type=int))
        new_role = request.form.get("role", "").strip()
        if new_role not in {ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR}:
            flash("Rol no valido.", "danger")
            return redirect(url_for("manage_roles"))
        previous_role = user.role
        user.role = new_role
        db.session.commit()
        log_action("cambio_rol", "roles", f"Rol de {user.username}: {previous_role} -> {new_role}", current_user)
        if user.id == current_user.id and new_role != ROLE_ADMIN:
            logout_user()
            flash("Tu rol fue actualizado. Debes iniciar sesion de nuevo con los nuevos permisos.", "warning")
            return redirect(url_for("login"))
        flash("Rol actualizado correctamente.", "success")
        return redirect(url_for("manage_roles"))

    users = User.query.order_by(User.full_name.asc()).all()
    return render_template("usuarios/roles.html", users=users)


@app.route("/usuarios/crear", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def create_user():
    form = UserCreateForm()
    if form.validate_on_submit():
        try:
            user = User(
                full_name=form.full_name.data.strip(),
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                role=form.role.data,
                is_active_user=form.is_active_user.data == "true",
                email_verified=False,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            try:
                send_verification_email(user)
                flash("Se envio un correo de verificacion al nuevo usuario.", "info")
            except Exception as exc:
                flash(f"Usuario creado, pero no fue posible enviar verificacion: {exc}", "warning")
            log_action("crear_usuario", "usuarios", f"Usuario creado: {user.username}", current_user)
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("list_users"))
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe un usuario con ese nombre o correo.", "danger")
    return render_template("usuarios/crear.html", form=form)


@app.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    if request.method == "GET":
        form.is_active_user.data = "true" if user.is_active_user else "false"
    if form.validate_on_submit():
        try:
            user.full_name = form.full_name.data.strip()
            user.username = form.username.data.strip()
            user.email = form.email.data.strip().lower()
            user.role = form.role.data
            user.is_active_user = form.is_active_user.data == "true"
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            log_action("editar_usuario", "usuarios", f"Usuario actualizado: {user.username}", current_user)
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("list_users"))
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar cambios. Revisa usuario y correo.", "danger")
    return render_template("usuarios/editar.html", form=form, user=user)


@app.route("/usuarios/<int:user_id>/toggle")
@login_required
@role_required(ROLE_ADMIN)
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_user = not user.is_active_user
    db.session.commit()
    log_action("cambiar_estado_usuario", "usuarios", f"Estado de {user.username}: {user.is_active_user}", current_user)
    flash("Estado del usuario actualizado.", "success")
    return redirect(url_for("list_users"))


@app.route("/usuarios/<int:user_id>/enviar-acceso-temporal")
@login_required
@role_required(ROLE_ADMIN)
def send_temporary_access(user_id):
    user = User.query.get_or_404(user_id)
    temporary_password = generate_temporary_password()
    user.set_password(temporary_password)
    user.force_password_change = True
    user.temporary_password_expires_at = datetime.utcnow() + timedelta(hours=12)
    db.session.commit()
    try:
        sent, preview = send_temporary_password_email(user, temporary_password)
        if sent:
            flash("Se envio acceso temporal al correo del usuario.", "success")
        else:
            flash("Correo no configurado. En desarrollo se muestra la contrasena temporal.", "warning")
            flash(f"Temporal para {user.username}: {preview}", "info")
    except Exception as exc:
        flash(f"No fue posible enviar el acceso temporal: {exc}", "danger")
    log_action("acceso_temporal", "usuarios", f"Acceso temporal generado para {user.username}", current_user)
    return redirect(url_for("list_users"))


@app.route("/usuarios/<int:user_id>/reenviar-verificacion")
@login_required
@role_required(ROLE_ADMIN)
def resend_verification_admin(user_id):
    user = User.query.get_or_404(user_id)
    try:
        send_verification_email(user)
        flash("Correo de verificacion reenviado correctamente.", "success")
    except Exception as exc:
        flash(f"No fue posible reenviar verificacion: {exc}", "danger")
    log_action("reenviar_verificacion", "usuarios", f"Verificacion reenviada para {user.username}", current_user)
    return redirect(url_for("list_users"))


@app.route("/usuarios/<int:user_id>/verificar-manual")
@login_required
@role_required(ROLE_ADMIN)
def verify_user_manual(user_id):
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        flash(f"El usuario {user.username} ya esta verificado.", "info")
    else:
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        db.session.commit()
        log_action("verificacion_manual", "usuarios", f"Admin verifico manualmente a {user.username}", current_user)
        flash(f"Usuario {user.username} verificado manualmente.", "success")
    return redirect(url_for("list_users"))


@app.route("/activos")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def list_assets():
    assets = query_assets()
    locations = Location.query.filter_by(is_active=True).order_by(Location.name.asc()).all()
    return render_template("activos/listar.html", assets=assets, locations=locations)


@app.route("/activos/crear", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def create_asset():
    form = AssetForm()
    locations = [(0, "Sin ubicacion")] + [(location.id, location.name) for location in Location.query.filter_by(is_active=True)]
    form.location_id.choices = locations

    if request.method == "GET":
        form.rfid_code.data = request.args.get("rfid_code", "")
        form.nfc_code.data = request.args.get("nfc_code", "")
        form.barcode_code.data = request.args.get("barcode_code", "")
        form.identification_technology.data = request.args.get("technology", "rfid_125khz")
        form.status.data = "activo"
    if form.validate_on_submit():
        try:
            rfid_code = normalize_identifier(form.rfid_code.data) or generate_virtual_rfid_code()
            nfc_code = normalize_identifier(form.nfc_code.data)
            barcode_code = normalize_identifier(form.barcode_code.data)
            validate_unique_asset_identifiers(rfid_code, nfc_code, barcode_code)
            asset = Asset(
                rfid_code=rfid_code,
                nfc_code=nfc_code,
                barcode_code=barcode_code,
                identification_technology=form.identification_technology.data,
                internal_code=form.internal_code.data.strip(),
                name=form.name.data.strip(),
                asset_type=form.asset_type.data,
                category=form.category.data.strip() if form.category.data else None,
                brand=form.brand.data.strip() if form.brand.data else None,
                model=form.model.data.strip() if form.model.data else None,
                serial_number=form.serial_number.data.strip() if form.serial_number.data else None,
                purchase_date=form.purchase_date.data,
                invoice_number=form.invoice_number.data.strip() if form.invoice_number.data else None,
                vendor=form.vendor.data.strip() if form.vendor.data else None,
                purchase_value=form.purchase_value.data,
                warranty_until=form.warranty_until.data,
                responsible_name=form.responsible_name.data.strip() if form.responsible_name.data else None,
                location_id=form.location_id.data or None,
                status=form.status.data,
                observations=form.observations.data.strip() if form.observations.data else None,
                created_by_id=current_user.id,
            )
            db.session.add(asset)
            db.session.commit()

            if asset.location:
                movement = AssetMovement(
                    asset_id=asset.id,
                    movement_type="Ubicacion inicial",
                    from_location=None,
                    to_location=asset.location.name,
                    moved_by_id=current_user.id,
                    observations="Ubicacion registrada al crear el activo.",
                )
                db.session.add(movement)
                db.session.commit()

            label_type = form.label_type.data if hasattr(form, 'label_type') else "none"
            qr_filename = None
            if label_type == "qr":
                qr_filename = generate_qr_for_asset(asset)

            log_action("crear_activo", "activos", f"Activo creado: {asset.internal_code}", current_user)

            if qr_filename:
                flash("Activo creado correctamente. Se genero el codigo QR.", "success")
                return redirect(url_for("asset_detail", asset_id=asset.id, qr_generated=1))
            else:
                flash("Activo creado correctamente.", "success")
                return redirect(url_for("asset_detail", asset_id=asset.id))
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible crear el activo. Verifica RFID y codigo interno.", "danger")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("activos/crear.html", form=form)


@app.route("/activos/<int:asset_id>/editar", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if asset.status == "dado_de_baja" and current_user.role != ROLE_ADMIN:
        flash("Los activos dados de baja solo pueden ser editados por administradores.", "warning")
        return redirect(url_for("asset_detail", asset_id=asset.id))

    old_location = asset.current_location
    old_status = asset.status
    form = AssetForm(obj=asset)
    form.location_id.choices = [(0, "Sin ubicacion")] + [
        (location.id, location.name) for location in Location.query.filter_by(is_active=True)
    ]
    if request.method == "GET":
        form.location_id.data = asset.location_id or 0

    if form.validate_on_submit():
        try:
            asset.rfid_code = normalize_identifier(form.rfid_code.data) or asset.rfid_code or generate_virtual_rfid_code()
            asset.nfc_code = normalize_identifier(form.nfc_code.data)
            asset.barcode_code = normalize_identifier(form.barcode_code.data)
            asset.identification_technology = form.identification_technology.data
            validate_unique_asset_identifiers(asset.rfid_code, asset.nfc_code, asset.barcode_code, asset.id)
            asset.internal_code = form.internal_code.data.strip()
            asset.name = form.name.data.strip()
            asset.asset_type = form.asset_type.data
            asset.category = form.category.data.strip() if form.category.data else None
            asset.brand = form.brand.data.strip() if form.brand.data else None
            asset.model = form.model.data.strip() if form.model.data else None
            asset.serial_number = form.serial_number.data.strip() if form.serial_number.data else None
            asset.purchase_date = form.purchase_date.data
            asset.invoice_number = form.invoice_number.data.strip() if form.invoice_number.data else None
            asset.vendor = form.vendor.data.strip() if form.vendor.data else None
            asset.purchase_value = form.purchase_value.data
            asset.warranty_until = form.warranty_until.data
            asset.responsible_name = form.responsible_name.data.strip() if form.responsible_name.data else None
            asset.location_id = form.location_id.data or None
            asset.status = form.status.data
            asset.observations = form.observations.data.strip() if form.observations.data else None
            db.session.commit()

            if old_location != asset.current_location:
                movement = AssetMovement(
                    asset_id=asset.id,
                    movement_type="Cambio de ubicacion",
                    from_location=old_location,
                    to_location=asset.current_location,
                    moved_by_id=current_user.id,
                    observations="Cambio de ubicacion desde la edicion del activo.",
                )
                db.session.add(movement)

            if old_status != asset.status:
                movement = AssetMovement(
                    asset_id=asset.id,
                    movement_type="Cambio de estado",
                    from_location=old_status,
                    to_location=asset.status,
                    moved_by_id=current_user.id,
                    observations="Cambio de estado desde la edicion del activo.",
                )
                db.session.add(movement)

            db.session.commit()
            log_action("editar_activo", "activos", f"Activo actualizado: {asset.internal_code}", current_user)
            flash("Activo actualizado correctamente.", "success")
            return redirect(url_for("asset_detail", asset_id=asset.id))
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar los cambios del activo.", "danger")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("activos/editar.html", form=form, asset=asset)


@app.route("/ubicaciones/crear", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def create_location():
    form = LocationForm()
    if form.validate_on_submit():
        try:
            location = Location(name=form.name.data.strip(), description=form.description.data.strip() if form.description.data else None)
            db.session.add(location)
            db.session.commit()
            log_action("crear_ubicacion", "ubicaciones", f"Ubicacion creada: {location.name}", current_user)
            flash("Ubicacion creada correctamente.", "success")
            return redirect(request.args.get("next") or url_for("list_assets"))
        except IntegrityError:
            db.session.rollback()
            flash("Esa ubicacion ya existe.", "danger")
    return render_template("activos/ubicacion.html", form=form)


@app.route("/activos/<int:asset_id>")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def asset_detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    history = asset_history(asset)
    ai_form = AIQuestionForm()
    qr_generated = request.args.get("qr_generated")
    qr_file = get_qr_filename(asset)
    return render_template("activos/detalle.html", asset=asset, history=history, ai_form=ai_form, qr_generated=qr_generated, qr_file=qr_file)


@app.route("/activos/<int:asset_id>/qr")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def asset_qr(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    qr_file = get_qr_filename(asset)
    if not qr_file:
        qr_file = generate_qr_for_asset(asset)
    qr_dir = Path(app.config["UPLOAD_FOLDER"]) / "qr"
    return send_from_directory(str(qr_dir), qr_file, as_attachment=True)


@app.route("/activos/<int:asset_id>/qr/ver")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def asset_qr_view(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    qr_file = get_qr_filename(asset)
    if not qr_file:
        qr_file = generate_qr_for_asset(asset)
    qr_dir = Path(app.config["UPLOAD_FOLDER"]) / "qr"
    return send_from_directory(str(qr_dir), qr_file)


def generate_qr_labels_pdf(assets):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buffer = BytesIO()
    page_width, page_height = letter
    c = canvas.Canvas(buffer, pagesize=letter)

    cols = 3
    rows = 8
    label_width = 6.0 * cm
    label_height = 3.5 * cm

    margin_x = (page_width - cols * label_width) / 2
    margin_y = (page_height - rows * label_height) / 2

    qr_size = 2.2 * cm
    base_url = app.config.get("APP_BASE_URL", "http://127.0.0.1:5000")

    for idx, asset in enumerate(assets):
        page_idx = idx % (cols * rows)
        if page_idx == 0 and idx > 0:
            c.showPage()

        col = page_idx % cols
        row = page_idx // cols

        x = margin_x + col * label_width
        y = page_height - margin_y - (row + 1) * label_height

        qr_data = f"{base_url}/activos/{asset.id}"
        qr_img = qrcode.make(qr_data, image_factory=PilImage, box_size=6, border=1)
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        qr_x = x + (label_width - qr_size) / 2
        qr_y = y + label_height - qr_size - 0.2 * cm
        c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

        c.setFont("Helvetica-Bold", 7)
        code_text = asset.internal_code or ""
        text_x = x + label_width / 2
        c.drawCentredString(text_x, y + 0.7 * cm, code_text)

        c.setFont("Helvetica", 6)
        name_text = asset.name or ""
        if len(name_text) > 28:
            name_text = name_text[:25] + "..."
        c.drawCentredString(text_x, y + 0.25 * cm, name_text)

    c.save()
    buffer.seek(0)
    return buffer


@app.route("/activos/qr-lote", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def qr_batch_export():
    if request.method == "POST":
        asset_ids = request.form.getlist("asset_ids", type=int)
        if not asset_ids:
            flash("Debes seleccionar al menos un activo.", "warning")
            return redirect(url_for("qr_batch_export"))
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
        if not assets:
            flash("No se encontraron activos validos.", "danger")
            return redirect(url_for("qr_batch_export"))
        pdf_buffer = generate_qr_labels_pdf(assets)
        log_action("exportar_qr_lote", "activos", f"Exportacion QR en lote: {len(assets)} activos", current_user)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"qr_labels_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
        )

    assets = Asset.query.order_by(Asset.name.asc()).all()
    return render_template("activos/qr_lote.html", assets=assets)


@app.route("/activos/<int:asset_id>/asignar", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def assign_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    form = AssignmentForm()
    if form.validate_on_submit():
        assignment = AssetAssignment(
            asset_id=asset.id,
            previous_responsible=asset.current_responsible if asset.current_responsible != "Sin responsable" else None,
            new_responsible=form.new_responsible.data.strip(),
            assigned_by_id=current_user.id,
            observations=form.observations.data.strip() if form.observations.data else None,
        )
        asset.responsible_name = form.new_responsible.data.strip()
        db.session.add(assignment)
        db.session.commit()
        log_action("asignar_activo", "asignaciones", f"Activo {asset.internal_code} asignado a {asset.responsible_name}", current_user)
        flash("Activo asignado correctamente.", "success")
        return redirect(url_for("asset_detail", asset_id=asset.id))
    return render_template("activos/asignar.html", form=form, asset=asset)


@app.route("/asignaciones")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def list_assignments():
    assignments = AssetAssignment.query.order_by(AssetAssignment.assignment_date.desc(), AssetAssignment.created_at.desc()).all()
    return render_template("asignaciones/listar.html", assignments=assignments)


@app.route("/movimientos")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def list_movements():
    movements = AssetMovement.query.order_by(AssetMovement.movement_date.desc(), AssetMovement.created_at.desc()).all()
    return render_template("movimientos/listar.html", movements=movements)


@app.route("/ubicaciones")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def list_locations():
    locations = Location.query.order_by(Location.name.asc()).all()
    return render_template("ubicaciones/listar.html", locations=locations)


@app.route("/activos/<int:asset_id>/baja", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def dispose_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    form = DisposalForm()
    if form.validate_on_submit():
        stored_filename = None
        if form.support_file.data:
            stored_filename, _ = save_uploaded_file(form.support_file.data)
        disposal = AssetDisposal(
            asset_id=asset.id,
            disposal_date=form.disposal_date.data,
            reason=form.reason.data.strip(),
            authorized_by_id=current_user.id,
            observations=form.observations.data.strip() if form.observations.data else None,
            support_filename=stored_filename,
        )
        asset.status = "dado_de_baja"
        db.session.add(disposal)
        db.session.commit()
        log_action("baja_activo", "bajas", f"Activo dado de baja: {asset.internal_code}", current_user)
        flash("Activo dado de baja correctamente.", "warning")
        return redirect(url_for("asset_detail", asset_id=asset.id))
    return render_template("activos/baja.html", form=form, asset=asset)


@app.route("/escanear", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def unified_scan():
    scan_type = request.args.get("type", "rfid")
    if scan_type not in ("rfid", "nfc", "barcode"):
        scan_type = "rfid"
    form = ScanForm()
    if request.method == "GET":
        form.scan_type.data = scan_type

    if form.validate_on_submit():
        code = form.code.data.strip()
        selected_type = form.scan_type.data
        asset = resolve_asset_by_identifier(selected_type, code)
        if asset:
            log_action(f"lectura_{selected_type}", selected_type, f"{selected_type.upper()} {code} asociado a {asset.internal_code}", current_user)
            flash(f"Codigo encontrado. Abriendo hoja de vida de {asset.name}.", "success")
            return redirect(url_for("asset_detail", asset_id=asset.id))
        log_action(f"lectura_{selected_type}", selected_type, f"{selected_type.upper()} no registrado: {code}", current_user)
        flash("Codigo no registrado. Completa el formulario para crear el activo.", "warning")
        create_params = {"technology": selected_type}
        if selected_type == "rfid":
            create_params["rfid_code"] = code
        elif selected_type == "nfc":
            create_params["nfc_code"] = code
        else:
            create_params["barcode_code"] = code
        return redirect(url_for("create_asset", **create_params))

    return render_template("escanear.html", form=form, scan_type=scan_type)


@app.route("/rfid", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def rfid_scan():
    return redirect(url_for("unified_scan", type="rfid"))


@app.route("/nfc", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def nfc_scan():
    return redirect(url_for("unified_scan", type="nfc"))


@app.route("/barcode", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def barcode_scan():
    return redirect(url_for("unified_scan", type="barcode"))


@app.route("/mantenimientos")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def list_maintenances():
    records = MaintenanceRecord.query.order_by(MaintenanceRecord.maintenance_date.desc()).all()
    return render_template("mantenimientos/listar.html", records=records)


@app.route("/mantenimientos/crear", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def create_maintenance():
    form = MaintenanceForm()
    form.asset_id.choices = [(asset.id, f"{asset.internal_code} - {asset.name}") for asset in Asset.query.order_by(Asset.name.asc()).all()]
    asset_id = request.args.get("asset_id", type=int)
    if request.method == "GET" and asset_id:
        form.asset_id.data = asset_id

    if form.validate_on_submit():
        stored_filename = None
        if form.attachment.data:
            stored_filename, _ = save_uploaded_file(form.attachment.data)
        record = MaintenanceRecord(
            asset_id=form.asset_id.data,
            maintenance_type=form.maintenance_type.data,
            maintenance_date=form.maintenance_date.data,
            technician_name=form.technician_name.data.strip(),
            description=form.description.data.strip(),
            cost=form.cost.data,
            next_maintenance_date=form.next_maintenance_date.data,
            attachment_filename=stored_filename,
            created_by_id=current_user.id,
        )
        asset = Asset.query.get(form.asset_id.data)
        asset.status = "mantenimiento" if form.maintenance_type.data in {"correctivo", "revision"} else asset.status
        db.session.add(record)
        db.session.commit()
        log_action("registrar_mantenimiento", "mantenimientos", f"Mantenimiento registrado para {asset.internal_code}", current_user)
        flash("Mantenimiento registrado correctamente.", "success")
        return redirect(url_for("asset_detail", asset_id=asset.id))
    return render_template("mantenimientos/crear.html", form=form)


@app.route("/documentos")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def list_documents():
    documents = AssetDocument.query.order_by(AssetDocument.created_at.desc()).all()
    return render_template("documentos/listar.html", documents=documents)


@app.route("/documentos/subir", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def upload_document():
    form = DocumentForm()
    form.asset_id.choices = [(asset.id, f"{asset.internal_code} - {asset.name}") for asset in Asset.query.order_by(Asset.name.asc()).all()]
    asset_id = request.args.get("asset_id", type=int)
    if request.method == "GET" and asset_id:
        form.asset_id.data = asset_id

    if form.validate_on_submit():
        stored_filename, original_filename = save_uploaded_file(form.file.data)
        document = AssetDocument(
            asset_id=form.asset_id.data,
            document_name=form.document_name.data.strip(),
            document_type=form.document_type.data,
            stored_filename=stored_filename,
            original_filename=original_filename,
            uploaded_by_id=current_user.id,
            observations=form.observations.data.strip() if form.observations.data else None,
        )
        db.session.add(document)
        db.session.commit()
        asset = Asset.query.get(form.asset_id.data)
        log_action("subir_documento", "documentos", f"Documento cargado para {asset.internal_code}: {document.document_name}", current_user)
        flash("Documento cargado correctamente.", "success")
        return redirect(url_for("asset_detail", asset_id=asset.id))
    return render_template("documentos/subir.html", form=form)


@app.route("/documentos/<filename>")
@login_required
def download_document(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


@app.route("/reportes", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_AUDITOR)
def reports():
    form = ReportFilterForm()
    if form.validate_on_submit():
        return redirect(url_for("export_report", report_type=form.report_type.data))
    logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(30).all()
    return render_template("reportes/index.html", form=form, logs=logs)


@app.route("/bitacora")
@login_required
@role_required(ROLE_ADMIN, ROLE_AUDITOR)
def system_log():
    form = ReportFilterForm()
    logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(100).all()
    return render_template("reportes/index.html", form=form, logs=logs, active_tab="bitacora")


@app.route("/alertas")
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR)
def alerts():
    context = build_alert_context()
    return render_template("alertas/index.html", **context)


@app.route("/reportes/export/<report_type>")
@login_required
@role_required(ROLE_ADMIN, ROLE_AUDITOR)
def export_report(report_type):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "inventario_general":
        writer.writerow(["RFID", "Codigo interno", "Nombre", "Tipo", "Estado", "Responsable", "Ubicacion"])
        for asset in Asset.query.order_by(Asset.name.asc()).all():
            writer.writerow(
                [
                    asset.rfid_code,
                    asset.internal_code,
                    asset.name,
                    asset.asset_type,
                    asset.status,
                    asset.current_responsible,
                    asset.current_location,
                ]
            )
    elif report_type == "mantenimientos":
        writer.writerow(["Activo", "Tipo", "Fecha", "Tecnico", "Costo", "Proximo mantenimiento"])
        for record in MaintenanceRecord.query.order_by(MaintenanceRecord.maintenance_date.desc()).all():
            writer.writerow(
                [
                    record.asset.internal_code,
                    record.maintenance_type,
                    record.maintenance_date,
                    record.technician_name,
                    record.cost,
                    record.next_maintenance_date,
                ]
            )
    elif report_type == "bajas":
        writer.writerow(["Activo", "Fecha baja", "Motivo", "Autorizado por"])
        for disposal in AssetDisposal.query.order_by(AssetDisposal.disposal_date.desc()).all():
            writer.writerow(
                [
                    disposal.asset.internal_code,
                    disposal.disposal_date,
                    disposal.reason,
                    disposal.authorized_by.full_name,
                ]
            )
    elif report_type == "documentos":
        writer.writerow(["Activo", "Documento", "Tipo", "Fecha carga", "Usuario"])
        for document in AssetDocument.query.order_by(AssetDocument.created_at.desc()).all():
            writer.writerow(
                [
                    document.asset.internal_code,
                    document.document_name,
                    document.document_type,
                    document.created_at,
                    document.uploaded_by.full_name,
                ]
            )
    elif report_type == "garantias":
        writer.writerow(["Activo", "Garantia hasta", "Estado", "Responsable"])
        for asset in Asset.query.filter(Asset.warranty_until.isnot(None)).order_by(Asset.warranty_until.asc()).all():
            writer.writerow([asset.internal_code, asset.warranty_until, asset.status, asset.current_responsible])
    else:
        writer.writerow(["Codigo", "Nombre", "Tipo", "Estado", "Responsable", "Ubicacion"])
        for asset in Asset.query.order_by(Asset.name.asc()).all():
            writer.writerow(
                [asset.internal_code, asset.name, asset.asset_type, asset.status, asset.current_responsible, asset.current_location]
            )

    output.seek(0)
    log_action("exportar_reporte", "reportes", f"Reporte exportado: {report_type}", current_user)
    return app.response_class(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}.csv"},
    )


@app.route("/search")
@login_required
def global_search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("dashboard"))
    assets = Asset.query.filter(
        db.or_(
            Asset.rfid_code.ilike(f"%{query}%"),
            Asset.nfc_code.ilike(f"%{query}%"),
            Asset.barcode_code.ilike(f"%{query}%"),
            Asset.name.ilike(f"%{query}%"),
            Asset.internal_code.ilike(f"%{query}%"),
            Asset.responsible_name.ilike(f"%{query}%"),
            Asset.serial_number_hash == blind_index(query),
            Asset.invoice_number_hash == blind_index(query),
        )
    ).order_by(Asset.updated_at.desc()).all()
    locations = Location.query.filter_by(is_active=True).order_by(Location.name.asc()).all()
    return render_template("activos/listar.html", assets=assets, locations=locations, global_query=query)


@app.route("/activos/<int:asset_id>/ia", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH, ROLE_AUDITOR)
def asset_ai(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    form = AIQuestionForm()
    if not form.validate_on_submit():
        return jsonify({"ok": False, "message": "Debes escribir una consulta para la IA."}), 400

    try:
        answer = ask_gpt4all(form.question.data.strip(), asset)
        log_action("consulta_ia", "ia", f"Consulta IA sobre activo {asset.internal_code}", current_user)
        return jsonify({"ok": True, "answer": answer})
    except Exception as exc:
        return jsonify({"ok": False, "message": f"No fue posible consultar GPT4All: {exc}"}), 500


@app.route("/inventario-modo", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def inventario_modo():
    locations = Location.query.filter_by(is_active=True).order_by(Location.name.asc()).all()
    return render_template("inventario_modo.html", locations=locations)


@app.route("/api/inventario/verificar-codigo", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def inventario_verificar_codigo():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"found": False}), 400
    identifier_type = data.get("type", "rfid")
    code = data.get("code", "").strip()
    if not code:
        return jsonify({"found": False}), 400
    asset = resolve_asset_by_identifier(identifier_type, code)
    if asset:
        return jsonify({
            "found": True,
            "asset_id": asset.id,
            "asset_name": asset.name,
            "internal_code": asset.internal_code,
            "location_id": asset.location_id,
        })
    return jsonify({"found": False})


@app.route("/api/inventario/verificar", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def inventario_verificar():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "message": "Datos no proporcionados."}), 400

    location_id = data.get("location_id")
    scanned_codes = data.get("scanned_codes", [])

    if not location_id:
        return jsonify({"ok": False, "message": "Ubicacion no proporcionada."}), 400

    location = Location.query.get(location_id)
    if not location:
        return jsonify({"ok": False, "message": "Ubicacion no encontrada."}), 404

    # Get all assets registered in this location
    expected_assets = Asset.query.filter_by(location_id=location_id).all()
    expected_map = {a.id: a for a in expected_assets}

    # Resolve scanned codes to assets
    found_asset_ids = set()
    extras = []

    for scan in scanned_codes:
        scan_type = scan.get("type", "rfid")
        scan_code = scan.get("code", "").strip()
        if not scan_code:
            continue
        asset = resolve_asset_by_identifier(scan_type, scan_code)
        if asset:
            if asset.location_id == location_id:
                found_asset_ids.add(asset.id)
            else:
                extras.append({
                    "code": scan_code,
                    "type": scan_type,
                    "asset_name": asset.name,
                    "internal_code": asset.internal_code,
                    "registered_location": asset.current_location,
                })
        else:
            extras.append({
                "code": scan_code,
                "type": scan_type,
                "asset_name": None,
                "internal_code": None,
                "registered_location": None,
            })

    # Build results
    found_list = []
    missing_list = []

    for asset_id, asset in expected_map.items():
        if asset_id in found_asset_ids:
            # Find the scanned code that matched
            scanned_code = ""
            for scan in scanned_codes:
                resolved = resolve_asset_by_identifier(scan.get("type", "rfid"), scan.get("code", ""))
                if resolved and resolved.id == asset_id:
                    scanned_code = scan.get("code", "")
                    break
            found_list.append({
                "asset_id": asset.id,
                "internal_code": asset.internal_code,
                "name": asset.name,
                "scanned_code": scanned_code,
            })
        else:
            identifier = asset.rfid_code or asset.nfc_code or asset.barcode_code or ""
            missing_list.append({
                "asset_id": asset.id,
                "internal_code": asset.internal_code,
                "name": asset.name,
                "identifier": identifier,
            })

    log_action(
        "inventario_modo",
        "inventario",
        f"Inventario en '{location.name}': {len(found_list)} encontrados, {len(missing_list)} faltantes, {len(extras)} extras",
        current_user,
    )

    return jsonify({
        "ok": True,
        "location_name": location.name,
        "total_expected": len(expected_assets),
        "found": found_list,
        "missing": missing_list,
        "extras": extras,
    })


@app.route("/inventario-modo/exportar", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_TECH)
def inventario_exportar():
    import json as json_lib

    results_json = request.form.get("results_data", "")
    location_name = request.form.get("location_name", "inventario")

    try:
        data = json_lib.loads(results_json)
    except (ValueError, TypeError):
        flash("No fue posible exportar los resultados.", "danger")
        return redirect(url_for("inventario_modo"))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Resultado Inventario - Ubicacion: " + location_name])
    writer.writerow([f"Total esperados: {data.get('total_expected', 0)}", f"Encontrados: {len(data.get('found', []))}", f"No encontrados: {len(data.get('missing', []))}", f"Extras: {len(data.get('extras', []))}"])
    writer.writerow([])

    # Found
    writer.writerow(["== ENCONTRADOS =="])
    writer.writerow(["Codigo interno", "Nombre", "Codigo escaneado"])
    for item in data.get("found", []):
        writer.writerow([item.get("internal_code", ""), item.get("name", ""), item.get("scanned_code", "")])
    writer.writerow([])

    # Missing
    writer.writerow(["== NO ENCONTRADOS =="])
    writer.writerow(["Codigo interno", "Nombre", "Identificador"])
    for item in data.get("missing", []):
        writer.writerow([item.get("internal_code", ""), item.get("name", ""), item.get("identifier", "")])
    writer.writerow([])

    # Extras
    writer.writerow(["== EXTRAS =="])
    writer.writerow(["Codigo escaneado", "Tipo", "Activo", "Ubicacion registrada"])
    for item in data.get("extras", []):
        writer.writerow([item.get("code", ""), item.get("type", ""), item.get("asset_name", "No registrado"), item.get("registered_location", "N/A")])

    output.seek(0)
    safe_name = location_name.replace(" ", "_").lower()
    log_action("exportar_inventario", "inventario", f"CSV inventario exportado: {location_name}", current_user)
    return app.response_class(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventario_{safe_name}.csv"},
    )


@app.errorhandler(403)
def forbidden(_error):
    return render_template("errores/403.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("errores/404.html"), 404


with app.app_context():
    db.create_all()
    ensure_schema_compatibility()
    seed_admin()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 5000)),
    )

# =============================================================================
# REST API Blueprint for the RFID Inventory mobile app.
#
# To register this blueprint in app.py, add the following lines:
#
#     from api import api_bp
#     app.register_blueprint(api_bp)
#
# =============================================================================

import hashlib
import hmac
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from models import (
    ASSET_STATUSES,
    ASSET_TYPES,
    IDENTIFICATION_TECHNOLOGIES,
    MAINTENANCE_TYPES,
    ROLE_AUDITOR,
    ROLE_ADMIN,
    ROLE_TECH,
    ROLE_VIEW,
    ROLES,
    Asset,
    AssetAssignment,
    AssetMovement,
    Location,
    MaintenanceRecord,
    SystemLog,
    User,
    db,
)
from security_utils import (
    blind_index,
    decrypt_value,
    encrypt_value,
    generate_temporary_password,
    send_temporary_password_email,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Token auth for mobile (React Native can't handle cookies)
# ---------------------------------------------------------------------------

def generate_mobile_token(user_id):
    secret = current_app.config.get("SECRET_KEY", "dev")
    payload = f"{user_id}:{secret}"
    return hmac.new(secret.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()


def verify_mobile_token(token):
    secret = current_app.config.get("SECRET_KEY", "dev")
    for user in User.query.filter_by(is_active_user=True).all():
        expected = hmac.new(secret.encode(), str(user.id).encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(token, expected):
            return user
    return None


def mobile_auth_required(f):
    """Allow both session auth (Flask-Login) and token auth (X-Mobile-Token)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if already authenticated via session
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        # Check mobile token
        token = request.headers.get("X-Mobile-Token", "")
        if token:
            user = verify_mobile_token(token)
            if user:
                login_user(user, remember=False)
                return f(*args, **kwargs)
        return jsonify({"ok": False, "message": "Sesion no iniciada. Debes autenticarte."}), 401
    return decorated


def mobile_role_required(*roles):
    """Require mobile/session auth and one of the provided roles."""
    def decorator(f):
        @wraps(f)
        @mobile_auth_required
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                return error_response("No tienes permisos para realizar esta accion.", 403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ---------------------------------------------------------------------------
# CORS headers for all API responses
# ---------------------------------------------------------------------------

@api_bp.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Device-Token, X-Mobile-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@api_bp.route("/<path:path>", methods=["OPTIONS"])
@api_bp.route("/", methods=["OPTIONS"])
def handle_options(**kwargs):
    """Handle CORS preflight requests."""
    return "", 204


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ok_response(data=None, **kwargs):
    """Return a successful JSON response."""
    payload = {"ok": True, "data": data}
    payload.update(kwargs)
    return jsonify(payload)


def error_response(message, status_code=400):
    """Return an error JSON response."""
    return jsonify({"ok": False, "message": message}), status_code


def serialize_user(user, token=None):
    data = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "must_change_password": user.force_password_change,
        "temporary_password_expires_at": (
            user.temporary_password_expires_at.isoformat()
            if user.temporary_password_expires_at else None
        ),
    }
    if token:
        data["token"] = token
    return data


def normalize_identifier(value):
    """Normalize an identifier value (strip whitespace)."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def parse_date(value, field_name):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"{field_name} debe tener formato YYYY-MM-DD.")


def parse_decimal(value, field_name):
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_name} debe ser un numero valido.")
    if parsed < 0:
        raise ValueError(f"{field_name} no puede ser negativo.")
    return parsed


def generate_virtual_rfid_code():
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"VRFID-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


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


def resolve_asset_by_identifier(identifier_type, code):
    """Look up an asset by its RFID, NFC, or barcode identifier."""
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


def log_action(action, module, description, user=None):
    """Create a system log entry."""
    log = SystemLog(
        user_id=getattr(user, "id", None),
        action=action,
        module=module,
        description=description,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    db.session.add(log)
    db.session.commit()


def serialize_asset_summary(asset):
    """Serialize an asset for list views (no decryption of sensitive fields)."""
    return {
        "id": asset.id,
        "rfid_code": asset.rfid_code,
        "nfc_code": asset.nfc_code,
        "barcode_code": asset.barcode_code,
        "internal_code": asset.internal_code,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "category": asset.category,
        "brand": asset.brand,
        "model": asset.model,
        "status": asset.status,
        "identification_technology": asset.identification_technology,
        "responsible_name": asset.current_responsible,
        "location": asset.current_location,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


def serialize_asset_detail(asset):
    """Serialize an asset for detail view (includes decrypted sensitive fields)."""
    data = serialize_asset_summary(asset)
    data.update({
        "serial_number": asset.serial_number,
        "invoice_number": asset.invoice_number,
        "vendor": asset.vendor,
        "observations": asset.observations,
        "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
        "purchase_value": float(asset.purchase_value) if asset.purchase_value else None,
        "warranty_until": asset.warranty_until.isoformat() if asset.warranty_until else None,
        "responsible_user_id": asset.responsible_user_id,
        "location_id": asset.location_id,
        "created_by_id": asset.created_by_id,
    })
    return data


# ---------------------------------------------------------------------------
# AUTH endpoints
# ---------------------------------------------------------------------------

@api_bp.route("/auth/register", methods=["POST"])
def api_register():
    """Register a new user account."""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Se requiere un cuerpo JSON.")

    full_name = (data.get("full_name") or "").strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not full_name or not username or not email or not password:
        return error_response("Todos los campos son obligatorios.")

    if len(password) < 8:
        return error_response("La contrasena debe tener al menos 8 caracteres.")

    if password != confirm_password:
        return error_response("Las contrasenas no coinciden.")

    if User.query.filter_by(username=username).first():
        return error_response("Ese nombre de usuario ya esta en uso.")

    if User.query.filter_by(email=email).first():
        return error_response("Ese correo electronico ya esta registrado.")

    from models import ROLE_VIEW
    user = User(
        full_name=full_name,
        username=username,
        email=email,
        role=ROLE_VIEW,
        is_active_user=True,
        email_verified=False,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)
    user.last_access = datetime.utcnow()
    db.session.commit()

    log_action("registro", "api_auth", f"Nuevo usuario registrado: {user.username}", user=user)

    token = generate_mobile_token(user.id)

    return ok_response(serialize_user(user, token)), 201


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    """Authenticate a user and return their profile."""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Se requiere un cuerpo JSON con username y password.")

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return error_response("Usuario y contrasena son obligatorios.")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return error_response("Credenciales invalidas.", 401)

    if not user.is_active:
        return error_response("La cuenta esta desactivada.", 403)

    if user.force_password_change and user.temporary_password_expires_at and user.temporary_password_expires_at < datetime.utcnow():
        return error_response("La contrasena temporal vencio. Solicita una nueva recuperacion.", 403)

    login_user(user, remember=True)
    user.last_access = datetime.utcnow()
    db.session.commit()

    log_action("login", "api_auth", f"Inicio de sesion API: {user.username}", user=user)

    token = generate_mobile_token(user.id)

    return ok_response(serialize_user(user, token))


@api_bp.route("/auth/forgot-password", methods=["POST"])
def api_forgot_password():
    """Generate a temporary password and send it to the registered email."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()

    if not email and not username:
        return error_response("Ingresa el correo o el usuario.")

    query = User.query.filter_by(is_active_user=True)
    user = query.filter_by(email=email).first() if email else query.filter_by(username=username).first()

    if user:
        try:
            temporary_password = generate_temporary_password()
            user.set_password(temporary_password)
            user.force_password_change = True
            user.temporary_password_expires_at = datetime.utcnow() + timedelta(hours=12)
            user.password_reset_requested_at = datetime.utcnow()
            db.session.commit()

            sent, preview = send_temporary_password_email(user, temporary_password)
            log_action("recuperacion_temporal", "api_auth", f"Temporal generado para {user.username}", user=user)

            response_data = {"message": "Si la cuenta existe, enviaremos una contrasena temporal al correo registrado."}
            if not sent:
                response_data["preview_temporary_password"] = preview
            return ok_response(response_data)
        except Exception as exc:
            return error_response(f"No fue posible enviar la recuperacion: {exc}", 500)

    return ok_response({"message": "Si la cuenta existe, enviaremos una contrasena temporal al correo registrado."})


@api_bp.route("/auth/change-password", methods=["POST"])
@mobile_auth_required
def api_change_password():
    """Change password from the mobile app, including mandatory temporary-password flow."""
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not current_password or not new_password:
        return error_response("Contrasena actual y nueva contrasena son obligatorias.")

    if len(new_password) < 8:
        return error_response("La nueva contrasena debe tener al menos 8 caracteres.")

    if new_password != confirm_password:
        return error_response("Las contrasenas no coinciden.")

    if not current_user.check_password(current_password):
        return error_response("La contrasena actual no coincide.", 401)

    current_user.set_password(new_password)
    current_user.force_password_change = False
    current_user.temporary_password_expires_at = None
    current_user.password_reset_requested_at = None
    db.session.commit()

    log_action("cambio_password", "api_auth", f"Contrasena cambiada por {current_user.username}", current_user)
    return ok_response(serialize_user(current_user))


@api_bp.route("/auth/logout", methods=["POST"])
@mobile_auth_required
def api_logout():
    """Logout the current user."""
    log_action("logout", "api_auth", f"Cierre de sesion API: {current_user.username}", user=current_user)
    logout_user()
    return ok_response({"message": "Sesion cerrada exitosamente."})


@api_bp.route("/auth/me", methods=["GET"])
@mobile_auth_required
def api_me():
    """Return the current authenticated user's profile."""
    user = current_user
    data = serialize_user(user)
    data["last_access"] = user.last_access.isoformat() if user.last_access else None
    return ok_response(data)


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

@api_bp.route("/dashboard", methods=["GET"])
@mobile_auth_required
def api_dashboard():
    """Return dashboard statistics."""
    total_assets = Asset.query.count()
    active_assets = Asset.query.filter_by(status="activo").count()
    maintenance_assets = Asset.query.filter_by(status="mantenimiento").count()
    disposed_assets = Asset.query.filter_by(status="dado_de_baja").count()
    active_users = User.query.filter_by(is_active_user=True).count()

    recent_movements = (
        AssetMovement.query
        .order_by(AssetMovement.created_at.desc())
        .limit(10)
        .all()
    )

    movements_data = []
    for mov in recent_movements:
        movements_data.append({
            "id": mov.id,
            "asset_id": mov.asset_id,
            "movement_type": mov.movement_type,
            "from_location": mov.from_location,
            "to_location": mov.to_location,
            "movement_date": mov.movement_date.isoformat() if mov.movement_date else None,
            "moved_by": mov.moved_by.full_name if mov.moved_by else None,
            "created_at": mov.created_at.isoformat() if mov.created_at else None,
        })

    return ok_response({
        "total_assets": total_assets,
        "active_assets": active_assets,
        "maintenance_assets": maintenance_assets,
        "disposed_assets": disposed_assets,
        "active_users": active_users,
        "recent_movements": movements_data,
    })


# ---------------------------------------------------------------------------
# ASSETS
# ---------------------------------------------------------------------------

@api_bp.route("/assets", methods=["GET"])
@mobile_auth_required
def api_assets_list():
    """List assets with optional search, status filter, and pagination."""
    query_param = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Clamp per_page to reasonable bounds
    per_page = max(1, min(per_page, 100))

    q = Asset.query

    if status_filter:
        q = q.filter(Asset.status == status_filter)

    if query_param:
        search = f"%{query_param}%"
        q = q.filter(
            db.or_(
                Asset.name.ilike(search),
                Asset.internal_code.ilike(search),
                Asset.rfid_code.ilike(search),
                Asset.nfc_code.ilike(search),
                Asset.barcode_code.ilike(search),
                Asset.brand.ilike(search),
                Asset.model.ilike(search),
                Asset.responsible_name.ilike(search),
                Asset.category.ilike(search),
            )
        )

    q = q.order_by(Asset.updated_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    assets_data = [serialize_asset_summary(a) for a in pagination.items]

    return ok_response(assets_data, pagination={
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    })


@api_bp.route("/assets/<int:asset_id>", methods=["GET"])
@mobile_auth_required
def api_asset_detail(asset_id):
    """Return full asset detail including assignments, maintenances, and movements."""
    asset = Asset.query.get(asset_id)
    if not asset:
        return error_response("Activo no encontrado.", 404)

    data = serialize_asset_detail(asset)

    # Assignments
    assignments = []
    for a in asset.assignments:
        assignments.append({
            "id": a.id,
            "previous_responsible": a.previous_responsible,
            "new_responsible": a.new_responsible,
            "assignment_date": a.assignment_date.isoformat() if a.assignment_date else None,
            "assigned_by": a.assigned_by.full_name if a.assigned_by else None,
            "observations": a.observations,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # Maintenances
    maintenances = []
    for m in asset.maintenances:
        maintenances.append({
            "id": m.id,
            "maintenance_type": m.maintenance_type,
            "maintenance_date": m.maintenance_date.isoformat() if m.maintenance_date else None,
            "technician_name": m.technician_name,
            "description": m.description,
            "cost": float(m.cost) if m.cost else None,
            "next_maintenance_date": m.next_maintenance_date.isoformat() if m.next_maintenance_date else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    # Movements
    movements = []
    for mov in asset.movements:
        movements.append({
            "id": mov.id,
            "movement_type": mov.movement_type,
            "from_location": mov.from_location,
            "to_location": mov.to_location,
            "movement_date": mov.movement_date.isoformat() if mov.movement_date else None,
            "moved_by": mov.moved_by.full_name if mov.moved_by else None,
            "created_at": mov.created_at.isoformat() if mov.created_at else None,
        })

    data["assignments"] = assignments
    data["maintenances"] = maintenances
    data["movements"] = movements

    return ok_response(data)


@api_bp.route("/assets/scan", methods=["POST"])
@mobile_auth_required
def api_asset_scan():
    """Look up an asset by scanning an RFID, NFC, or barcode identifier."""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Se requiere un cuerpo JSON con identifier_type y code.")

    identifier_type = (data.get("identifier_type") or "").strip().lower()
    code = (data.get("code") or "").strip()

    if identifier_type not in ("rfid", "nfc", "barcode"):
        return error_response("identifier_type debe ser 'rfid', 'nfc' o 'barcode'.")

    if not code:
        return error_response("El campo code es obligatorio.")

    asset = resolve_asset_by_identifier(identifier_type, code)
    if not asset:
        return error_response("No se encontro ningun activo con ese identificador.", 404)

    log_action(
        "scan",
        "api_assets",
        f"Escaneo {identifier_type.upper()} '{code}' -> Activo #{asset.id} ({asset.internal_code})",
        user=current_user,
    )

    return ok_response(serialize_asset_detail(asset))


# ---------------------------------------------------------------------------
# LOCATIONS
# ---------------------------------------------------------------------------

@api_bp.route("/locations", methods=["GET"])
@mobile_auth_required
def api_locations():
    """List all active locations."""
    locations = Location.query.filter_by(is_active=True).order_by(Location.name).all()

    locations_data = []
    for loc in locations:
        locations_data.append({
            "id": loc.id,
            "name": loc.name,
            "description": loc.description,
        })

    return ok_response(locations_data)


# ---------------------------------------------------------------------------
# ADMIN MOBILE ENDPOINTS
# ---------------------------------------------------------------------------

@api_bp.route("/admin/options", methods=["GET"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_options():
    """Return enum values and active records needed by mobile admin forms."""
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name.asc()).all()
    assets = Asset.query.order_by(Asset.name.asc()).all()
    locations = Location.query.filter_by(is_active=True).order_by(Location.name.asc()).all()
    return ok_response({
        "roles": ROLES,
        "asset_statuses": ASSET_STATUSES,
        "asset_types": ASSET_TYPES,
        "identification_technologies": IDENTIFICATION_TECHNOLOGIES,
        "maintenance_types": MAINTENANCE_TYPES,
        "users": [serialize_user(user) for user in users],
        "assets": [serialize_asset_summary(asset) for asset in assets],
        "locations": [
            {"id": location.id, "name": location.name, "description": location.description}
            for location in locations
        ],
    })


@api_bp.route("/admin/users", methods=["GET"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return ok_response([serialize_user(user) for user in users])


@api_bp.route("/admin/users", methods=["POST"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_create_user():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or ROLE_VIEW).strip()
    is_active_user = bool(data.get("is_active_user", True))

    if not full_name or not username or not email or not password:
        return error_response("Nombre, usuario, correo y contrasena son obligatorios.")
    if len(password) < 8:
        return error_response("La contrasena debe tener al menos 8 caracteres.")
    if role not in ROLES:
        return error_response("Rol no valido.")

    try:
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            role=role,
            is_active_user=is_active_user,
            email_verified=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_action("crear_usuario", "api_admin", f"Usuario creado desde movil: {user.username}", current_user)
        return ok_response(serialize_user(user)), 201
    except IntegrityError:
        db.session.rollback()
        return error_response("Ya existe un usuario con ese nombre o correo.")
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))


@api_bp.route("/admin/users/<int:user_id>", methods=["PUT"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return error_response("Usuario no encontrado.", 404)

    data = request.get_json(silent=True) or {}
    role = (data.get("role") or user.role).strip()
    if role not in ROLES:
        return error_response("Rol no valido.")

    try:
        user.full_name = (data.get("full_name") or user.full_name).strip()
        user.username = (data.get("username") or user.username).strip()
        user.email = (data.get("email") or user.email).strip().lower()
        user.role = role
        if "is_active_user" in data:
            user.is_active_user = bool(data.get("is_active_user"))
        if data.get("password"):
            if len(data["password"]) < 8:
                return error_response("La contrasena debe tener al menos 8 caracteres.")
            user.set_password(data["password"])
        db.session.commit()
        log_action("editar_usuario", "api_admin", f"Usuario actualizado desde movil: {user.username}", current_user)
        return ok_response(serialize_user(user))
    except IntegrityError:
        db.session.rollback()
        return error_response("No fue posible guardar cambios. Revisa usuario y correo.")
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))


@api_bp.route("/admin/assets", methods=["POST"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_create_asset():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    internal_code = (data.get("internal_code") or "").strip()
    asset_type = (data.get("asset_type") or "").strip()
    identification_technology = (data.get("identification_technology") or "rfid_125khz").strip()
    status = (data.get("status") or "activo").strip()

    if not name or not internal_code or not asset_type:
        return error_response("Codigo interno, nombre y tipo son obligatorios.")
    if asset_type not in ASSET_TYPES:
        return error_response("Tipo de activo no valido.")
    if status not in ASSET_STATUSES:
        return error_response("Estado no valido.")
    if identification_technology not in IDENTIFICATION_TECHNOLOGIES:
        return error_response("Tecnologia de identificacion no valida.")

    try:
        rfid_code = normalize_identifier(data.get("rfid_code")) or generate_virtual_rfid_code()
        nfc_code = normalize_identifier(data.get("nfc_code"))
        barcode_code = normalize_identifier(data.get("barcode_code"))
        validate_unique_asset_identifiers(rfid_code, nfc_code, barcode_code)

        location_id = data.get("location_id") or None
        if location_id and not Location.query.get(location_id):
            return error_response("Ubicacion no encontrada.", 404)

        asset = Asset(
            rfid_code=rfid_code,
            nfc_code=nfc_code,
            barcode_code=barcode_code,
            identification_technology=identification_technology,
            internal_code=internal_code,
            name=name,
            asset_type=asset_type,
            category=(data.get("category") or "").strip() or None,
            brand=(data.get("brand") or "").strip() or None,
            model=(data.get("model") or "").strip() or None,
            serial_number=(data.get("serial_number") or "").strip() or None,
            purchase_date=parse_date(data.get("purchase_date"), "purchase_date"),
            invoice_number=(data.get("invoice_number") or "").strip() or None,
            vendor=(data.get("vendor") or "").strip() or None,
            purchase_value=parse_decimal(data.get("purchase_value"), "purchase_value"),
            warranty_until=parse_date(data.get("warranty_until"), "warranty_until"),
            responsible_name=(data.get("responsible_name") or "").strip() or None,
            location_id=location_id,
            status=status,
            observations=(data.get("observations") or "").strip() or None,
            created_by_id=current_user.id,
        )
        db.session.add(asset)
        db.session.flush()

        if asset.location:
            db.session.add(AssetMovement(
                asset_id=asset.id,
                movement_type="Ubicacion inicial",
                from_location=None,
                to_location=asset.location.name,
                moved_by_id=current_user.id,
                observations="Ubicacion registrada al crear el activo desde movil.",
            ))

        db.session.commit()
        log_action("crear_activo", "api_admin", f"Activo creado desde movil: {asset.internal_code}", current_user)
        return ok_response(serialize_asset_detail(asset)), 201
    except IntegrityError:
        db.session.rollback()
        return error_response("No fue posible crear el activo. Verifica codigos unicos.")
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))


@api_bp.route("/admin/assets/<int:asset_id>", methods=["PUT"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_update_asset(asset_id):
    asset = Asset.query.get(asset_id)
    if not asset:
        return error_response("Activo no encontrado.", 404)

    data = request.get_json(silent=True) or {}
    try:
        rfid_code = normalize_identifier(data.get("rfid_code")) or asset.rfid_code or generate_virtual_rfid_code()
        nfc_code = normalize_identifier(data.get("nfc_code"))
        barcode_code = normalize_identifier(data.get("barcode_code"))
        validate_unique_asset_identifiers(rfid_code, nfc_code, barcode_code, asset_id=asset.id)

        location_id = data.get("location_id") if "location_id" in data else asset.location_id
        location_id = location_id or None
        if location_id and not Location.query.get(location_id):
            return error_response("Ubicacion no encontrada.", 404)

        old_location = asset.current_location
        old_status = asset.status
        asset.rfid_code = rfid_code
        asset.nfc_code = nfc_code
        asset.barcode_code = barcode_code
        asset.identification_technology = data.get("identification_technology") or asset.identification_technology
        asset.internal_code = (data.get("internal_code") or asset.internal_code).strip()
        asset.name = (data.get("name") or asset.name).strip()
        asset.asset_type = data.get("asset_type") or asset.asset_type
        asset.category = (data.get("category") or "").strip() or None
        asset.brand = (data.get("brand") or "").strip() or None
        asset.model = (data.get("model") or "").strip() or None
        asset.serial_number = (data.get("serial_number") or "").strip() or None
        asset.purchase_date = parse_date(data.get("purchase_date"), "purchase_date") if "purchase_date" in data else asset.purchase_date
        asset.invoice_number = (data.get("invoice_number") or "").strip() or None
        asset.vendor = (data.get("vendor") or "").strip() or None
        asset.purchase_value = parse_decimal(data.get("purchase_value"), "purchase_value") if "purchase_value" in data else asset.purchase_value
        asset.warranty_until = parse_date(data.get("warranty_until"), "warranty_until") if "warranty_until" in data else asset.warranty_until
        asset.responsible_name = (data.get("responsible_name") or "").strip() or None
        asset.location_id = location_id
        asset.status = data.get("status") or asset.status
        asset.observations = (data.get("observations") or "").strip() or None

        if asset.current_location != old_location:
            db.session.add(AssetMovement(
                asset_id=asset.id,
                movement_type="Cambio de ubicacion",
                from_location=old_location,
                to_location=asset.current_location,
                moved_by_id=current_user.id,
                observations="Cambio de ubicacion desde movil.",
            ))
        if asset.status != old_status:
            db.session.add(AssetMovement(
                asset_id=asset.id,
                movement_type="Cambio de estado",
                from_location=old_status,
                to_location=asset.status,
                moved_by_id=current_user.id,
                observations="Cambio de estado desde movil.",
            ))

        db.session.commit()
        log_action("editar_activo", "api_admin", f"Activo actualizado desde movil: {asset.internal_code}", current_user)
        return ok_response(serialize_asset_detail(asset))
    except IntegrityError:
        db.session.rollback()
        return error_response("No fue posible guardar el activo. Revisa codigos unicos.")
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))


@api_bp.route("/admin/locations", methods=["POST"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_create_location():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip() or None
    if not name:
        return error_response("El nombre de ubicacion es obligatorio.")
    try:
        location = Location(name=name, description=description, is_active=True)
        db.session.add(location)
        db.session.commit()
        log_action("crear_ubicacion", "api_admin", f"Ubicacion creada desde movil: {location.name}", current_user)
        return ok_response({"id": location.id, "name": location.name, "description": location.description}), 201
    except IntegrityError:
        db.session.rollback()
        return error_response("Ya existe una ubicacion con ese nombre.")
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))


def serialize_maintenance(record):
    return {
        "id": record.id,
        "asset_id": record.asset_id,
        "asset_name": record.asset.name if record.asset else None,
        "asset_code": record.asset.internal_code if record.asset else None,
        "maintenance_type": record.maintenance_type,
        "maintenance_date": record.maintenance_date.isoformat() if record.maintenance_date else None,
        "technician_name": record.technician_name,
        "description": record.description,
        "cost": float(record.cost) if record.cost else None,
        "next_maintenance_date": record.next_maintenance_date.isoformat() if record.next_maintenance_date else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@api_bp.route("/admin/maintenances", methods=["GET"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_maintenances_list():
    records = MaintenanceRecord.query.order_by(MaintenanceRecord.maintenance_date.desc()).limit(100).all()
    return ok_response([serialize_maintenance(record) for record in records])


@api_bp.route("/admin/maintenances", methods=["POST"])
@mobile_role_required(ROLE_ADMIN)
def api_admin_create_maintenance():
    data = request.get_json(silent=True) or {}
    asset_id = data.get("asset_id")
    maintenance_type = (data.get("maintenance_type") or "").strip()
    technician_name = (data.get("technician_name") or "").strip()
    description = (data.get("description") or "").strip()

    if not asset_id or not maintenance_type or not technician_name or not description:
        return error_response("Activo, tipo, tecnico y descripcion son obligatorios.")
    if maintenance_type not in MAINTENANCE_TYPES:
        return error_response("Tipo de mantenimiento no valido.")

    asset = Asset.query.get(asset_id)
    if not asset:
        return error_response("Activo no encontrado.", 404)

    try:
        record = MaintenanceRecord(
            asset_id=asset.id,
            maintenance_type=maintenance_type,
            maintenance_date=parse_date(data.get("maintenance_date"), "maintenance_date") or date.today(),
            technician_name=technician_name,
            description=description,
            cost=parse_decimal(data.get("cost"), "cost"),
            next_maintenance_date=parse_date(data.get("next_maintenance_date"), "next_maintenance_date"),
            created_by_id=current_user.id,
        )
        if maintenance_type in {"correctivo", "revision"}:
            asset.status = "mantenimiento"
        db.session.add(record)
        db.session.commit()
        log_action("registrar_mantenimiento", "api_admin", f"Mantenimiento movil para {asset.internal_code}", current_user)
        return ok_response(serialize_maintenance(record)), 201
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc))


# ---------------------------------------------------------------------------
# DEVICE ENDPOINTS (ESP32 / Arduino - token auth, no session required)
# ---------------------------------------------------------------------------

def device_token_required(f):
    """Decorator that validates device token from X-Device-Token header."""
    from functools import wraps
    from flask import current_app

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Device-Token", "")
        expected = current_app.config.get("DEVICE_API_TOKEN", "trazia-device-secret-token")
        if not token or token != expected:
            return error_response("Token de dispositivo invalido.", 401)
        return f(*args, **kwargs)
    return decorated


@api_bp.route("/device/scan", methods=["POST"])
@device_token_required
def api_device_scan():
    """ESP32/Arduino scan endpoint. Looks up asset by RFID UID and logs the reading."""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Se requiere un cuerpo JSON.")

    uid = (data.get("uid") or "").strip()
    device_name = (data.get("device") or "ESP32").strip()
    read_at = (data.get("read_at") or "").strip()
    scan_type = (data.get("type") or "rfid").strip().lower()

    if not uid:
        return error_response("El campo uid es obligatorio.")

    if scan_type == "nfc":
        asset = Asset.query.filter_by(nfc_code=uid).first()
    elif scan_type == "barcode":
        asset = Asset.query.filter_by(barcode_code=uid).first()
    else:
        asset = Asset.query.filter_by(rfid_code=uid).first()

    if not asset:
        log_action("scan_no_encontrado", "dispositivo",
                   f"[{device_name}] {scan_type.upper()} '{uid}' - No encontrado")
        return error_response("No se encontro ningun activo con ese identificador.", 404)

    log_action("scan_dispositivo", "dispositivo",
               f"[{device_name}] {scan_type.upper()} '{uid}' -> {asset.internal_code} ({asset.name})")

    return ok_response({
        "asset_id": asset.id,
        "internal_code": asset.internal_code,
        "name": asset.name,
        "status": asset.status,
        "asset_type": asset.asset_type,
        "responsible": asset.current_responsible,
        "location": asset.current_location,
    })


@api_bp.route("/device/register-read", methods=["POST"])
@device_token_required
def api_device_register_read():
    """Register a batch of RFID readings from a device (for inventory rounds)."""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Se requiere un cuerpo JSON.")

    readings = data.get("readings", [])
    device_name = (data.get("device") or "ESP32").strip()

    if not readings:
        return error_response("Se requiere al menos una lectura en 'readings'.")

    results = []
    for reading in readings:
        uid = (reading.get("uid") or "").strip()
        if not uid:
            continue
        asset = Asset.query.filter_by(rfid_code=uid).first()
        results.append({
            "uid": uid,
            "found": asset is not None,
            "asset_id": asset.id if asset else None,
            "name": asset.name if asset else None,
            "internal_code": asset.internal_code if asset else None,
        })

    log_action("scan_lote", "dispositivo",
               f"[{device_name}] Lote de {len(results)} lecturas registradas")

    return ok_response({
        "device": device_name,
        "total": len(results),
        "found": sum(1 for r in results if r["found"]),
        "not_found": sum(1 for r in results if not r["found"]),
        "results": results,
    })


@api_bp.route("/device/ping", methods=["GET"])
@device_token_required
def api_device_ping():
    """Health check for ESP32 devices."""
    return ok_response({"status": "ok", "server": "trazia-rfid"})


# ---------------------------------------------------------------------------
# STATS / NETWORK CHECK
# ---------------------------------------------------------------------------

@api_bp.route("/stats/network", methods=["GET"])
def api_network_check():
    """Simple connectivity check endpoint (no auth required)."""
    return ok_response({"online": True})

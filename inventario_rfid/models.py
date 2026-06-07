from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from security_utils import blind_index, decrypt_value, encrypt_value


db = SQLAlchemy()

ROLE_ADMIN = "administrador"
ROLE_TECH = "tecnico"
ROLE_VIEW = "consulta"
ROLE_AUDITOR = "auditor"
ROLES = [ROLE_ADMIN, ROLE_TECH, ROLE_VIEW, ROLE_AUDITOR]

ASSET_STATUSES = ["activo", "inactivo", "mantenimiento", "dado_de_baja"]
ASSET_TYPES = [
    "Equipo de computo",
    "Servidor",
    "Impresora",
    "Red",
    "Mueble",
    "Archivo fisico",
    "Expediente",
    "Carpeta",
    "Documento",
    "Caja",
    "Otro",
]
MAINTENANCE_TYPES = ["preventivo", "correctivo", "revision", "limpieza", "actualizacion", "otro"]
IDENTIFICATION_TECHNOLOGIES = ["rfid_125khz", "nfc", "barcode", "dual", "multiple"]


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_VIEW)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    last_access = db.Column(db.DateTime, nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    password_reset_requested_at = db.Column(db.DateTime, nullable=True)
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)
    temporary_password_expires_at = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)

    created_assets = db.relationship("Asset", back_populates="created_by", foreign_keys="Asset.created_by_id")
    responsible_assets = db.relationship(
        "Asset",
        back_populates="responsible_user",
        foreign_keys="Asset.responsible_user_id",
    )
    assignments_made = db.relationship("AssetAssignment", back_populates="assigned_by")
    movements_made = db.relationship("AssetMovement", back_populates="moved_by")
    maintenances_created = db.relationship("MaintenanceRecord", back_populates="created_by")
    documents_uploaded = db.relationship("AssetDocument", back_populates="uploaded_by")
    disposals_authorized = db.relationship("AssetDisposal", back_populates="authorized_by")
    system_logs = db.relationship("SystemLog", back_populates="user")

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_user

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    @validates("username", "email", "full_name", "role")
    def validate_text_fields(self, key, value):
        if not value:
            raise ValueError(f"El campo {key} es obligatorio.")
        value = value.strip()
        if key == "role" and value not in ROLES:
            raise ValueError("Rol no valido.")
        return value

    def __repr__(self):
        return f"<User {self.username}>"


class Location(TimestampMixin, db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    assets = db.relationship("Asset", back_populates="location")

    @validates("name")
    def validate_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("La ubicacion es obligatoria.")
        return value.strip()

    def __repr__(self):
        return f"<Location {self.name}>"


class Asset(TimestampMixin, db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    rfid_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    nfc_code = db.Column(db.String(120), unique=True, nullable=True, index=True)
    barcode_code = db.Column(db.String(120), unique=True, nullable=True, index=True)
    identification_technology = db.Column(db.String(30), nullable=False, default="rfid_125khz")
    internal_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    asset_type = db.Column(db.String(50), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=True, index=True)
    brand = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    serial_number_encrypted = db.Column("serial_number", db.Text, nullable=True)
    serial_number_hash = db.Column(db.String(64), nullable=True, index=True)
    purchase_date = db.Column(db.Date, nullable=True)
    invoice_number_encrypted = db.Column("invoice_number", db.Text, nullable=True)
    invoice_number_hash = db.Column(db.String(64), nullable=True, index=True)
    vendor_encrypted = db.Column("vendor", db.Text, nullable=True)
    purchase_value = db.Column(db.Numeric(12, 2), nullable=True)
    warranty_until = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="activo", index=True)
    observations_encrypted = db.Column("observations", db.Text, nullable=True)

    responsible_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    responsible_name = db.Column(db.String(150), nullable=True, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    responsible_user = db.relationship("User", back_populates="responsible_assets", foreign_keys=[responsible_user_id])
    location = db.relationship("Location", back_populates="assets")
    created_by = db.relationship("User", back_populates="created_assets", foreign_keys=[created_by_id])

    assignments = db.relationship("AssetAssignment", back_populates="asset", cascade="all, delete-orphan")
    maintenances = db.relationship("MaintenanceRecord", back_populates="asset", cascade="all, delete-orphan")
    documents = db.relationship("AssetDocument", back_populates="asset", cascade="all, delete-orphan")
    movements = db.relationship("AssetMovement", back_populates="asset", cascade="all, delete-orphan")
    disposal = db.relationship("AssetDisposal", back_populates="asset", uselist=False, cascade="all, delete-orphan")

    @property
    def current_responsible(self) -> str:
        return self.responsible_name or (self.responsible_user.full_name if self.responsible_user else "Sin responsable")

    @property
    def current_location(self) -> str:
        return self.location.name if self.location else "Sin ubicacion"

    @property
    def serial_number(self):
        return decrypt_value(self.serial_number_encrypted)

    @serial_number.setter
    def serial_number(self, value):
        self.serial_number_encrypted = encrypt_value(value)
        self.serial_number_hash = blind_index(value)

    @property
    def invoice_number(self):
        return decrypt_value(self.invoice_number_encrypted)

    @invoice_number.setter
    def invoice_number(self, value):
        self.invoice_number_encrypted = encrypt_value(value)
        self.invoice_number_hash = blind_index(value)

    @property
    def vendor(self):
        return decrypt_value(self.vendor_encrypted)

    @vendor.setter
    def vendor(self, value):
        self.vendor_encrypted = encrypt_value(value)

    @property
    def observations(self):
        return decrypt_value(self.observations_encrypted)

    @observations.setter
    def observations(self, value):
        self.observations_encrypted = encrypt_value(value)

    @property
    def can_receive_updates(self) -> bool:
        return self.status != "dado_de_baja"

    def is_editable_by(self, user: User) -> bool:
        if not user:
            return False
        if user.role == ROLE_ADMIN:
            return True
        return self.status != "dado_de_baja"

    @property
    def primary_identifier(self) -> str:
        return self.rfid_code or self.nfc_code or self.barcode_code or self.internal_code

    @property
    def identifier_labels(self):
        return {
            "rfid": self.rfid_code,
            "nfc": self.nfc_code,
            "barcode": self.barcode_code,
        }

    @validates("rfid_code", "nfc_code", "barcode_code", "internal_code", "name", "asset_type", "status", "identification_technology")
    def validate_required_fields(self, key, value):
        if key in {"rfid_code", "nfc_code", "barcode_code"}:
            if value in (None, ""):
                return None
            return str(value).strip()
        if not value or not str(value).strip():
            raise ValueError(f"El campo {key} es obligatorio.")
        value = str(value).strip()
        if key == "asset_type" and value not in ASSET_TYPES:
            raise ValueError("Tipo de activo no valido.")
        if key == "status" and value not in ASSET_STATUSES:
            raise ValueError("Estado no valido.")
        if key == "identification_technology" and value not in IDENTIFICATION_TECHNOLOGIES:
            raise ValueError("Tecnologia de identificacion no valida.")
        return value

    @validates("purchase_value")
    def validate_purchase_value(self, key, value):
        if value in (None, ""):
            return None
        value = Decimal(value)
        if value < 0:
            raise ValueError("El valor de compra no puede ser negativo.")
        return value

    def __repr__(self):
        return f"<Asset {self.internal_code}>"


class AssetAssignment(TimestampMixin, db.Model):
    __tablename__ = "asset_assignments"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    previous_responsible = db.Column(db.String(150), nullable=True)
    new_responsible = db.Column(db.String(150), nullable=False)
    assignment_date = db.Column(db.Date, default=date.today, nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    observations = db.Column(db.Text, nullable=True)

    asset = db.relationship("Asset", back_populates="assignments")
    assigned_by = db.relationship("User", back_populates="assignments_made")


class MaintenanceRecord(TimestampMixin, db.Model):
    __tablename__ = "maintenance_records"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    maintenance_type = db.Column(db.String(30), nullable=False)
    maintenance_date = db.Column(db.Date, default=date.today, nullable=False)
    technician_name = db.Column(db.String(150), nullable=False)
    description_encrypted = db.Column("description", db.Text, nullable=False)
    cost = db.Column(db.Numeric(12, 2), nullable=True)
    next_maintenance_date = db.Column(db.Date, nullable=True)
    attachment_filename = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    asset = db.relationship("Asset", back_populates="maintenances")
    created_by = db.relationship("User", back_populates="maintenances_created")

    @property
    def description(self):
        return decrypt_value(self.description_encrypted)

    @description.setter
    def description(self, value):
        self.description_encrypted = encrypt_value(value)

    @validates("maintenance_type")
    def validate_maintenance_type(self, key, value):
        value = value.strip()
        if value not in MAINTENANCE_TYPES:
            raise ValueError("Tipo de mantenimiento no valido.")
        return value


class AssetDocument(TimestampMixin, db.Model):
    __tablename__ = "asset_documents"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    document_name = db.Column(db.String(150), nullable=False)
    document_type = db.Column(db.String(80), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    observations_encrypted = db.Column("observations", db.Text, nullable=True)

    asset = db.relationship("Asset", back_populates="documents")
    uploaded_by = db.relationship("User", back_populates="documents_uploaded")

    @property
    def observations(self):
        return decrypt_value(self.observations_encrypted)

    @observations.setter
    def observations(self, value):
        self.observations_encrypted = encrypt_value(value)


class AssetMovement(TimestampMixin, db.Model):
    __tablename__ = "asset_movements"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    movement_type = db.Column(db.String(50), nullable=False)
    from_location = db.Column(db.String(150), nullable=True)
    to_location = db.Column(db.String(150), nullable=True)
    movement_date = db.Column(db.Date, default=date.today, nullable=False)
    moved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    observations_encrypted = db.Column("observations", db.Text, nullable=True)

    asset = db.relationship("Asset", back_populates="movements")
    moved_by = db.relationship("User", back_populates="movements_made")

    @property
    def observations(self):
        return decrypt_value(self.observations_encrypted)

    @observations.setter
    def observations(self, value):
        self.observations_encrypted = encrypt_value(value)


class AssetDisposal(TimestampMixin, db.Model):
    __tablename__ = "asset_disposals"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, unique=True)
    disposal_date = db.Column(db.Date, default=date.today, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    authorized_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    observations = db.Column(db.Text, nullable=True)
    support_filename = db.Column(db.String(255), nullable=True)

    asset = db.relationship("Asset", back_populates="disposal")
    authorized_by = db.relationship("User", back_populates="disposals_authorized")

    @property
    def observations(self):
        return decrypt_value(self.observations_encrypted)

    @observations.setter
    def observations(self, value):
        self.observations_encrypted = encrypt_value(value)


class SystemLog(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    module = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="system_logs")

from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, Optional

from models import ASSET_STATUSES, ASSET_TYPES, IDENTIFICATION_TECHNOLOGIES, MAINTENANCE_TYPES, ROLES


ROLE_CHOICES = [(role, role.capitalize()) for role in ROLES]
STATUS_CHOICES = [(status, status.replace("_", " ").capitalize()) for status in ASSET_STATUSES]
TYPE_CHOICES = [(asset_type, asset_type) for asset_type in ASSET_TYPES]
MAINTENANCE_CHOICES = [(kind, kind.capitalize()) for kind in MAINTENANCE_TYPES]
IDENTIFICATION_CHOICES = [
    ("rfid_125khz", "RFID 125 kHz"),
    ("nfc", "NFC"),
    ("barcode", "Codigo de barras"),
    ("dual", "RFID + NFC"),
    ("multiple", "RFID + NFC + barras"),
]
DOCUMENT_TYPES = [
    ("Factura", "Factura"),
    ("Garantia", "Garantia"),
    ("Foto", "Foto"),
    ("Acta", "Acta"),
    ("Hoja de vida", "Hoja de vida"),
    ("Manual", "Manual"),
    ("PDF", "PDF"),
    ("Escaneado", "Escaneado"),
    ("Otro", "Otro"),
]


class LoginForm(FlaskForm):
    username = StringField("Usuario", validators=[InputRequired(), Length(max=80)])
    password = PasswordField("Contrasena", validators=[InputRequired()])
    submit = SubmitField("Ingresar")


class RegisterForm(FlaskForm):
    full_name = StringField("Nombre completo", validators=[InputRequired(), Length(max=150)])
    username = StringField("Usuario", validators=[InputRequired(), Length(max=80)])
    email = StringField("Correo electronico", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Contrasena", validators=[InputRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirmar contrasena",
        validators=[InputRequired(), EqualTo("password", message="Las contrasenas no coinciden.")],
    )
    submit = SubmitField("Crear cuenta")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Correo registrado", validators=[InputRequired(), Email(), Length(max=120)])
    submit = SubmitField("Enviar enlace")


class ResendVerificationForm(FlaskForm):
    email = StringField("Correo registrado", validators=[InputRequired(), Email(), Length(max=120)])
    submit = SubmitField("Reenviar verificación")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Nueva contrasena", validators=[InputRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirmar contrasena",
        validators=[InputRequired(), EqualTo("password")],
    )
    submit = SubmitField("Actualizar contrasena")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Contrasena actual", validators=[InputRequired()])
    new_password = PasswordField("Nueva contrasena", validators=[InputRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirmar nueva contrasena",
        validators=[InputRequired(), EqualTo("new_password")],
    )
    submit = SubmitField("Cambiar contrasena")


class UserCreateForm(FlaskForm):
    full_name = StringField("Nombre completo", validators=[InputRequired(), Length(max=150)])
    username = StringField("Usuario", validators=[InputRequired(), Length(max=80)])
    email = StringField("Correo", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Contrasena", validators=[InputRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirmar contrasena",
        validators=[InputRequired(), EqualTo("password")],
    )
    role = SelectField("Rol", choices=ROLE_CHOICES, validators=[InputRequired()])
    is_active_user = SelectField(
        "Estado",
        choices=[("true", "Activo"), ("false", "Inactivo")],
        validators=[InputRequired()],
    )
    submit = SubmitField("Guardar usuario")


class UserEditForm(FlaskForm):
    full_name = StringField("Nombre completo", validators=[InputRequired(), Length(max=150)])
    username = StringField("Usuario", validators=[InputRequired(), Length(max=80)])
    email = StringField("Correo", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Nueva contrasena", validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirmar contrasena",
        validators=[Optional(), EqualTo("password")],
    )
    role = SelectField("Rol", choices=ROLE_CHOICES, validators=[InputRequired()])
    is_active_user = SelectField(
        "Estado",
        choices=[("true", "Activo"), ("false", "Inactivo")],
        validators=[InputRequired()],
    )
    submit = SubmitField("Actualizar usuario")


class AssetForm(FlaskForm):
    rfid_code = StringField("Codigo RFID 125 kHz", validators=[Optional(), Length(max=80)])
    nfc_code = StringField("Codigo NFC", validators=[Optional(), Length(max=120)])
    barcode_code = StringField("Codigo de barras", validators=[Optional(), Length(max=120)])
    identification_technology = SelectField(
        "Tecnologia principal",
        choices=IDENTIFICATION_CHOICES,
        validators=[InputRequired()],
    )
    internal_code = StringField("Codigo interno", validators=[InputRequired(), Length(max=80)])
    name = StringField("Nombre", validators=[InputRequired(), Length(max=150)])
    asset_type = SelectField("Tipo de activo", choices=TYPE_CHOICES, validators=[InputRequired()])
    category = StringField("Categoria", validators=[Optional(), Length(max=100)])
    brand = StringField("Marca", validators=[Optional(), Length(max=100)])
    model = StringField("Modelo", validators=[Optional(), Length(max=100)])
    serial_number = StringField("Numero serial", validators=[Optional(), Length(max=100)])
    purchase_date = DateField("Fecha de compra", validators=[Optional()], default=date.today)
    invoice_number = StringField("Numero de factura", validators=[Optional(), Length(max=80)])
    vendor = StringField("Proveedor", validators=[Optional(), Length(max=150)])
    purchase_value = DecimalField("Valor de compra", validators=[Optional()], places=2)
    warranty_until = DateField("Garantia hasta", validators=[Optional()])
    responsible_name = StringField("Responsable actual", validators=[Optional(), Length(max=150)])
    location_id = SelectField("Ubicacion actual", coerce=int, validators=[Optional()])
    status = SelectField("Estado", choices=STATUS_CHOICES, validators=[InputRequired()])
    observations = TextAreaField("Observaciones", validators=[Optional()])
    label_type = RadioField(
        "Generar etiqueta de identificacion",
        choices=[
            ("none", "No generar etiqueta"),
            ("qr", "Generar codigo QR"),
            ("rfid", "Solo etiqueta RFID (ya tengo tag fisico)"),
        ],
        default="qr",
        validators=[InputRequired()],
    )
    submit = SubmitField("Guardar activo")


class AssignmentForm(FlaskForm):
    new_responsible = StringField("Nuevo responsable", validators=[InputRequired(), Length(max=150)])
    observations = TextAreaField("Observaciones", validators=[Optional()])
    submit = SubmitField("Asignar activo")


class MaintenanceForm(FlaskForm):
    asset_id = SelectField("Activo", coerce=int, validators=[InputRequired()])
    maintenance_type = SelectField("Tipo", choices=MAINTENANCE_CHOICES, validators=[InputRequired()])
    maintenance_date = DateField("Fecha", validators=[InputRequired()], default=date.today)
    technician_name = StringField("Tecnico responsable", validators=[InputRequired(), Length(max=150)])
    description = TextAreaField("Descripcion", validators=[InputRequired()])
    cost = DecimalField("Costo", validators=[Optional()], places=2)
    next_maintenance_date = DateField("Proximo mantenimiento", validators=[Optional()])
    attachment = FileField(
        "Documento adjunto",
        validators=[Optional(), FileAllowed(["pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"])],
    )
    submit = SubmitField("Registrar mantenimiento")


class DocumentForm(FlaskForm):
    asset_id = SelectField("Activo", coerce=int, validators=[InputRequired()])
    document_name = StringField("Nombre del documento", validators=[InputRequired(), Length(max=150)])
    document_type = SelectField("Tipo de documento", choices=DOCUMENT_TYPES, validators=[InputRequired()])
    file = FileField(
        "Archivo",
        validators=[InputRequired(), FileAllowed(["pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"])],
    )
    observations = TextAreaField("Observaciones", validators=[Optional()])
    submit = SubmitField("Subir documento")


class DisposalForm(FlaskForm):
    disposal_date = DateField("Fecha de baja", validators=[InputRequired()], default=date.today)
    reason = StringField("Motivo", validators=[InputRequired(), Length(max=255)])
    observations = TextAreaField("Observaciones", validators=[Optional()])
    support_file = FileField(
        "Documento soporte",
        validators=[Optional(), FileAllowed(["pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"])],
    )
    submit = SubmitField("Dar de baja")


class RFIDForm(FlaskForm):
    rfid_code = StringField("Codigo RFID", validators=[InputRequired(), Length(max=80)])
    submit = SubmitField("Procesar")


class NFCForm(FlaskForm):
    nfc_code = StringField("Codigo NFC", validators=[InputRequired(), Length(max=120)])
    submit = SubmitField("Procesar NFC")


class BarcodeForm(FlaskForm):
    barcode_code = StringField("Codigo de barras", validators=[InputRequired(), Length(max=120)])
    submit = SubmitField("Procesar codigo")


class ScanForm(FlaskForm):
    scan_type = SelectField(
        "Tipo",
        choices=[("rfid", "RFID"), ("nfc", "NFC"), ("barcode", "Barras")],
        default="rfid",
    )
    code = StringField("Codigo", validators=[InputRequired(), Length(max=120)])
    submit = SubmitField("Buscar")


class LocationForm(FlaskForm):
    name = StringField("Nombre de ubicacion", validators=[InputRequired(), Length(max=120)])
    description = TextAreaField("Descripcion", validators=[Optional()])
    submit = SubmitField("Guardar ubicacion")


class RoleChangeForm(FlaskForm):
    role = SelectField("Rol", choices=ROLE_CHOICES, validators=[InputRequired()])
    submit = SubmitField("Actualizar rol")


class ReportFilterForm(FlaskForm):
    report_type = SelectField(
        "Reporte",
        choices=[
            ("inventario_general", "Inventario general"),
            ("por_estado", "Activos por estado"),
            ("por_tipo", "Activos por tipo"),
            ("por_responsable", "Activos por responsable"),
            ("por_ubicacion", "Activos por ubicacion"),
            ("mantenimientos", "Mantenimientos"),
            ("bajas", "Bajas"),
            ("documentos", "Documentos cargados"),
            ("garantias", "Garantias proximas a vencer"),
        ],
        validators=[InputRequired()],
    )
    submit = SubmitField("Exportar CSV")


class AIQuestionForm(FlaskForm):
    question = TextAreaField("Consulta a la IA", validators=[InputRequired(), Length(max=1000)])
    submit = SubmitField("Consultar IA")

# ============================================================
# app.py — RenalPro by Dr. Tapia (v3.0.0)
# ============================================================
# Módulos nuevos v2.0:
#   + Citrato Regional completo (acumulación, contraindicaciones, monitoreo)
#   + Sodio en TRRC (predicción + corrección)
#   + Predicción HD + KoA
#   + Plasmaféresis / TPE
#   + Reposición de electrolitos en TRRC
#   + Tarjeta de orden de enfermería
#   + CSS clínico oscuro mejorado
# ============================================================

import streamlit as st
import math
import hashlib
import json as _json
import os
from math import log
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, PageBreak, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ── Base de datos Railway (opcional — la app funciona sin ella) ───────────────
try:
    import db as _db
    _DB_ON = True
except ImportError:
    _DB_ON = False

# ── Caché de consultas DB (evita ir a Railway en cada clic) ───────────────────
@st.cache_data(ttl=15)
def _cached_prescriptions(uid: int):
    """Consulta prescripciones con caché de 15s."""
    return _db.get_prescriptions(uid) if _DB_ON else []

@st.cache_data(ttl=15)
def _cached_sessions(presc_id: int):
    """Consulta sesiones con caché de 15s."""
    return _db.get_sessions(presc_id) if _DB_ON else []

@st.cache_data(ttl=15)
def _cached_patients(uid: int):
    """Consulta pacientes con caché de 15s."""
    if not _DB_ON:
        return []
    try:
        return _db.get_patients(uid)
    except AttributeError:
        return []  # db.py desactualizado — subir versión nueva a GitHub

@st.cache_data(ttl=15)
def _cached_clinical_records(patient_id: int):
    """Consulta registros clínicos con caché de 15s."""
    if not _DB_ON:
        return []
    try:
        return _db.get_clinical_records(patient_id)
    except AttributeError:
        return []  # db.py desactualizado — subir versión nueva a GitHub

@st.cache_data(ttl=20)
def _cached_all_users():
    """Consulta todos los usuarios con caché de 20s."""
    return _db.get_all_users() if _DB_ON else []

def _clear_cache():
    """Invalida todos los cachés tras una escritura."""
    st.cache_data.clear()

VERSION = "v3.1.0"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RenalPro by Dr. Tapia",
    layout="wide",
    page_icon="🩺",
    initial_sidebar_state="expanded"
)

# ─── CSS CLÍNICO OSCURO ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ══ RenalPro — Tema Médico Claro v3 ══════════════════════════════════════ */

/* ── BASE ────────────────────────────────────────────────────────────────── */
.stApp { background-color: #F0F4F8 !important; }

/* ── SIDEBAR ─────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E3A8A 0%, #1E40AF 100%) !important;
}

/* Todo texto en sidebar → blanco (reset global) */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] small {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stMarkdown hr {
    border-color: rgba(255,255,255,0.25) !important;
}

/* ── SIDEBAR — BOTONES DE NAV ────────────────────────────────────────────── */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 7px 12px !important;
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
    box-shadow: none !important;
    transition: background 0.12s ease !important;
    transform: none !important;
}
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stButton > button *,
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button span,
section[data-testid="stSidebar"] .stButton > button div {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.15) !important;
    box-shadow: none !important;
    transform: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

/* ── SIDEBAR — INPUTS ────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    background: rgba(255,255,255,0.15) !important;
    border: 1px solid rgba(255,255,255,0.35) !important;
    border-radius: 7px !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.15) !important;
    border: 1px solid rgba(255,255,255,0.35) !important;
}
section[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: rgba(255,255,255,0.25) !important;
}

/* ── ÁREA PRINCIPAL — ENCABEZADOS ────────────────────────────────────────── */
.stApp h1 { color: #1E3A8A !important; font-weight: 800 !important; }
.stApp h2 { color: #1E40AF !important; font-weight: 700 !important; }
.stApp h3 { color: #2563EB !important; font-weight: 600 !important; }
.stApp h4, .stApp h5 { color: #3B82F6 !important; font-weight: 600 !important; }

/* ── ÁREA PRINCIPAL — TEXTO Y LABELS ─────────────────────────────────────── */
.stApp p,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] ul li,
[data-testid="stMarkdownContainer"] ol li { color: #1E293B !important; -webkit-text-fill-color: #1E293B !important; }
.stApp label { color: #374151 !important; font-weight: 500 !important; }
.stCaption, [data-testid="stCaptionContainer"] p { color: #64748B !important; }
hr { border-color: #E2E8F0 !important; margin: 12px 0 !important; }

/* ── BLOCKQUOTE — antes invisible, ahora siempre legible ─────────────────── */
[data-testid="stMarkdownContainer"] blockquote {
    background: #EFF6FF !important;
    border-left: 4px solid #2563EB !important;
    border-radius: 0 8px 8px 0 !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
}
[data-testid="stMarkdownContainer"] blockquote p,
[data-testid="stMarkdownContainer"] blockquote li,
[data-testid="stMarkdownContainer"] blockquote strong,
[data-testid="stMarkdownContainer"] blockquote em,
[data-testid="stMarkdownContainer"] blockquote * {
    color: #1E293B !important;
    -webkit-text-fill-color: #1E293B !important;
}

/* ── ÁREA PRINCIPAL — INPUTS ─────────────────────────────────────────────── */
.stApp input[type="number"],
.stApp input[type="text"],
.stApp input[type="password"],
.stApp textarea {
    color: #1E293B !important;
    background-color: #FFFFFF !important;
    -webkit-text-fill-color: #1E293B !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}
/* Placeholder — gris claro, claramente diferente al texto real */
.stApp input::placeholder,
.stApp textarea::placeholder {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    opacity: 1 !important;
}
.stApp input:focus, .stApp textarea:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    color: #1E293B !important;
}

/* ── BOTONES ─────────────────────────────────────────────────────────────── */
.stButton > button {
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
    box-shadow: 0 2px 6px rgba(37,99,235,0.25) !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background-color: #1D4ED8 !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton > button {
    background-color: #059669 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stDownloadButton > button:hover { background-color: #047857 !important; }

/* ── ALERTAS — fondo claro + texto oscuro garantizado ───────────────────── */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    background-color: #EFF6FF !important;
}
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span,
div[data-testid="stAlert"] li,
div[data-testid="stAlert"] strong,
div[data-testid="stAlert"] b,
div[data-testid="stAlert"] em,
div[data-testid="stAlert"] code,
div[data-testid="stAlert"] * {
    color: #1E293B !important;
    -webkit-text-fill-color: #1E293B !important;
    background-color: transparent !important;
}
/* Info — azul claro */
div[data-testid="stAlert"][data-baseweb="notification"],
div[data-testid="stAlert"][kind="info"],
.stInfo { background-color: #EFF6FF !important; border-left: 4px solid #2563EB !important; }
/* Success — verde claro */
div[data-testid="stAlert"][kind="success"],
.stSuccess { background-color: #F0FDF4 !important; border-left: 4px solid #16A34A !important; }
/* Warning — amarillo claro */
div[data-testid="stAlert"][kind="warning"],
.stWarning { background-color: #FFFBEB !important; border-left: 4px solid #D97706 !important; }
/* Error — rojo claro */
div[data-testid="stAlert"][kind="error"],
.stError { background-color: #FEF2F2 !important; border-left: 4px solid #DC2626 !important; }


/* ── MÉTRICAS ────────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #BFDBFE !important;
    border-left: 4px solid #2563EB !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    box-shadow: 0 1px 4px rgba(37,99,235,0.08) !important;
}
[data-testid="stMetricValue"] {
    color: #1E3A8A !important;
    font-weight: 700 !important;
    font-size: 22px !important;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* ── TABLAS ──────────────────────────────────────────────────────────────── */
[data-testid="stMarkdownContainer"] table {
    background: #FFFFFF !important;
    border-radius: 10px !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    width: 100% !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    overflow: hidden;
}
[data-testid="stMarkdownContainer"] th {
    background: #2563EB !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    padding: 10px 14px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-align: left !important;
}
[data-testid="stMarkdownContainer"] td {
    color: #1E293B !important;
    -webkit-text-fill-color: #1E293B !important;
    padding: 8px 14px !important;
    border-bottom: 1px solid #F1F5F9 !important;
    background: #FFFFFF !important;
}
[data-testid="stMarkdownContainer"] tr:nth-child(even) td {
    background: #F8FAFC !important;
}

/* ── TABS ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #FFFFFF !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    gap: 2px;
    flex-wrap: wrap !important;
}
.stTabs [data-baseweb="tab"] {
    color: #475569 !important;
    background-color: transparent !important;
    border-radius: 7px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 10px !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    color: #FFFFFF !important;
    background-color: #2563EB !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 6px rgba(37,99,235,0.3) !important;
}

/* ── RADIO Y CHECKBOX ────────────────────────────────────────────────────── */
.stRadio label, .stCheckbox label { color: #1E293B !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #1E293B !important; }

/* ── EXPANDER ────────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background-color: #EFF6FF !important;
    color: #2563EB !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ── MULTISELECT ─────────────────────────────────────────────────────────── */
.stMultiSelect [data-baseweb="tag"] {
    background-color: #DBEAFE !important;
    color: #1E3A8A !important;
    font-weight: 600 !important;
}

/* ── SLIDER ──────────────────────────────────────────────────────────────── */
[data-testid="stSliderThumb"] { background-color: #2563EB !important; }

/* ── KaTeX ───────────────────────────────────────────────────────────────── */
.katex, .katex * { color: #1E293B !important; }
[data-testid="stLatex"] {
    background: #EFF6FF !important;
    border-left: 4px solid #2563EB !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin: 6px 0 !important;
}
[data-testid="stLatex"] .katex,
[data-testid="stLatex"] .katex span { color: #1E293B !important; }

/* ── RESPONSIVE — TABLET (≤1024px) ──────────────────────────────────────── */
@media (max-width: 1024px) {
    section[data-testid="stSidebar"] .stButton > button {
        font-size: 14px !important;
        padding: 8px 10px !important;
    }
    [data-testid="stMetricValue"] { font-size: 18px !important; }
    [data-testid="stMarkdownContainer"] th,
    [data-testid="stMarkdownContainer"] td {
        padding: 6px 10px !important;
        font-size: 13px !important;
    }
}

/* ── RESPONSIVE — MÓVIL (≤768px) ────────────────────────────────────────── */
@media (max-width: 768px) {
    .stApp h1 { font-size: 20px !important; }
    .stApp h2 { font-size: 17px !important; }
    .stApp h3 { font-size: 15px !important; }
    [data-testid="metric-container"] {
        padding: 8px 10px !important;
        margin-bottom: 6px !important;
    }
    [data-testid="stMetricValue"] { font-size: 16px !important; }
    [data-testid="stMetricLabel"] { font-size: 10px !important; }
    section[data-testid="stSidebar"] .stButton > button {
        font-size: 14px !important;
        padding: 8px 10px !important;
    }
    [data-testid="stMarkdownContainer"] table {
        font-size: 12px !important;
    }
    [data-testid="stMarkdownContainer"] th,
    [data-testid="stMarkdownContainer"] td {
        padding: 5px 8px !important;
    }
    /* Inputs touch-friendly */
    .stApp input[type="number"],
    .stApp input[type="text"],
    .stApp input[type="password"] {
        font-size: 16px !important;
        min-height: 44px !important;
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }
    /* Buttons más altos para touch */
    .stButton > button {
        min-height: 44px !important;
        font-size: 15px !important;
    }
    /* Alertas más compactas */
    div[data-testid="stAlert"] {
        padding: 10px 12px !important;
        font-size: 13px !important;
    }
    /* Blockquote en móvil */
    [data-testid="stMarkdownContainer"] blockquote {
        padding: 8px 12px !important;
        font-size: 13px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ─── SISTEMA DE AUTENTICACIÓN (Railway DB + fallback local) ────────────────────

# ── Helpers locales (fallback sin Railway) ─────────────────────────────────────
def _hash(pwd: str) -> str:
    return hashlib.sha256((pwd + "trrc360_s4lt").encode()).hexdigest()

def _verify(pwd: str, h: str) -> bool:
    return _hash(pwd) == h

def _init_db():
    """Inicializa cuentas demo en session_state (fallback sin Railway)."""
    if "auth_users" not in st.session_state:
        admin_u = "josuetapia"
        admin_p = "Tapia2024!"
        try:
            admin_u = st.secrets.get("ADMIN_USERNAME", "josuetapia")
            admin_p = st.secrets.get("ADMIN_PASSWORD", "Tapia2024!")
        except Exception:
            pass
        trial_demo = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        st.session_state["auth_users"] = {
            admin_u: {
                "nombre": "Dr. Josué Tapia López", "email": "josue@nefrologo.com",
                "password_hash": _hash(admin_p), "rol": "admin", "is_active": True,
                "trial_end": None, "sub_end": None,
                "created": datetime.now().strftime("%Y-%m-%d"), "last_login": None
            },
            "demo_trial": {
                "nombre": "Dr. Demo Prueba", "email": "demo@hospital.com",
                "password_hash": _hash("demo123"), "rol": "trial", "is_active": True,
                "trial_end": trial_demo, "sub_end": None,
                "created": datetime.now().strftime("%Y-%m-%d"), "last_login": None
            },
        }

    # Inicializar tablas Railway si está disponible
    if _DB_ON and _db.db_ok():
        _db.init_tables()

def _get_role(user: dict) -> str:
    if not user.get("is_active", True): return "inactivo"
    if user["rol"] == "admin": return "admin"
    if user["rol"] == "pro":
        end = user.get("sub_end")
        return "pro" if end and datetime.strptime(end, "%Y-%m-%d") > datetime.now() else "expirado"
    if user["rol"] == "trial":
        end = user.get("trial_end")
        return "trial" if end and datetime.strptime(end, "%Y-%m-%d") > datetime.now() else "expirado"
    return "expirado"

def _days_left_local(user: dict) -> int:
    key = "sub_end" if user.get("rol") == "pro" else "trial_end"
    end = user.get(key)
    if not end: return 0
    try:
        return max(0, (datetime.strptime(end, "%Y-%m-%d") - datetime.now()).days)
    except Exception:
        return 0

# ── Login con DB Railway o fallback local ──────────────────────────────────────
def _do_login(username: str, password: str):
    _init_db()
    uname = username.strip().lower()

    # ── Intento 1: Railway DB ──────────────────────────────────────────────────
    if _DB_ON and _db.db_ok():
        user_db = _db.login_user(uname, password)
        if user_db:
            rol = _db.get_effective_rol(user_db)
            st.session_state.update({
                "logged_in": True, "consent_ok": True,
                "sess_user": uname,
                "sess_user_id": user_db["id"],
                "sess_rol": rol,
                "sess_nombre": user_db.get("nombre", uname),
                "sess_dias": _db.get_dias_restantes(user_db),
                "sess_avatar":        user_db.get("avatar", "👨‍⚕️"),
                "sess_institucion":   user_db.get("institucion", ""),
                "sess_email":         user_db.get("email", ""),
                "sess_especialidad":  user_db.get("especialidad", ""),
                "sess_cedula":        user_db.get("cedula_especialidad", "") or user_db.get("cedula_profesional", ""),
                "sess_universidad":   user_db.get("universidad_especialidad", "") or user_db.get("universidad", ""),
                "sess_domicilio":     user_db.get("domicilio_consultorio", ""),
                "sess_telefono":      user_db.get("telefono_consultorio", ""),
                "sess_ced_general":   user_db.get("cedula_general", ""),
                "sess_univ_general":  user_db.get("universidad_general", ""),
                "sess_consejo_nombre":user_db.get("consejo_nombre", ""),
                "sess_consejo_numero":user_db.get("consejo_numero", ""),
                "using_db": True,
            })
            return True, rol
        # User not in DB → try local fallback
    
    # ── Intento 2: cuentas locales (admin demo) ────────────────────────────────
    users = st.session_state["auth_users"]
    user = users.get(uname)
    if user and user.get("is_active", True) and _verify(password, user["password_hash"]):
        user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        rol = _get_role(user)
        st.session_state.update({
            "logged_in": True, "consent_ok": True,
            "sess_user": uname,
            "sess_user_id": None,
            "sess_rol": rol,
            "sess_nombre": user["nombre"],
            "sess_dias": _days_left_local(user),
            "sess_avatar": user.get("avatar", "👨‍⚕️"),
            "sess_institucion": user.get("institucion", ""),
            "sess_email": user.get("email", ""),
            "using_db": False,
        })
        return True, rol
    return False, None

def _do_register(username, password, nombre, email, especialidad=""):
    _init_db()
    uname = username.strip().lower()
    if len(password) < 6:
        return False, "La contraseña debe tener mínimo 6 caracteres."

    # ── Railway DB ─────────────────────────────────────────────────────────────
    if _DB_ON and _db.db_ok():
        ok, msg = _db.create_user(uname, password, nombre, email, trial_days=7)
        return ok, msg

    # ── Local fallback ─────────────────────────────────────────────────────────
    users = st.session_state["auth_users"]
    if uname in users:
        return False, "El nombre de usuario ya existe."
    trial_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    users[uname] = {
        "nombre": nombre, "email": email,
        "password_hash": _hash(password), "rol": "trial", "is_active": True,
        "trial_end": trial_end, "sub_end": None,
        "created": datetime.now().strftime("%Y-%m-%d"), "last_login": None
    }
    return True, "¡Cuenta creada! 7 días de prueba activos."

def _is_auth():   return st.session_state.get("logged_in", False)
def _rol():       return st.session_state.get("sess_rol", "guest")
def _can_save():  return _rol() in ["admin", "pro", "trial", "beca"]
def _nombre():    return st.session_state.get("sess_nombre", "Invitado")
def _user_id():   return st.session_state.get("sess_user_id")


# ─── LOGIN SCREEN ─────────────────────────────────────────────────────────────
def _show_login():
    st.markdown("""
<style>
.stApp{background:linear-gradient(135deg,#1E3A8A 0%,#2563EB 55%,#3B82F6 100%)!important;}
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="stHeader"]{background:transparent!important;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.12)!important;border:1px solid rgba(255,255,255,0.2)!important;}
.stTabs [data-baseweb="tab"]{color:rgba(255,255,255,0.7)!important;}
.stTabs [aria-selected="true"]{color:#fff!important;background:rgba(255,255,255,0.2)!important;}
.stTextInput input{background:rgba(255,255,255,0.95)!important;color:#1E293B!important;border:1px solid #CBD5E1!important;border-radius:8px!important;}
.stCheckbox label{color:rgba(255,255,255,0.85)!important;}
.stSelectbox>div>div{background:rgba(255,255,255,0.95)!important;color:#1E293B!important;}
</style>""", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center;padding:36px 0 16px 0;">
  <div style="font-size:56px;font-weight:900;color:#fff;letter-spacing:-3px;line-height:1;">
    RenalPro
  </div>
  <div style="color:rgba(255,255,255,0.85);font-size:16px;font-weight:500;margin-top:8px;">
    Plataforma Clínica de Nefrología
  </div>
  <div style="color:rgba(255,255,255,0.55);font-size:12px;margin-top:4px;">
    TRRC · Nefrología · Trasplante · Guardia
  </div>
</div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([0.8, 2, 0.8])
    with col:
        login_tab, reg_tab = st.tabs(["🔑  Iniciar sesión", "📝  Registrarse — 7 días gratis"])

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                u = st.text_input("Usuario", placeholder="tu_usuario", key="li_u",
                                  label_visibility="collapsed")
                p = st.text_input("Contraseña", type="password", placeholder="contraseña",
                                  key="li_p", label_visibility="collapsed")
                submitted = st.form_submit_button("Iniciar sesión →", use_container_width=True,
                                                  type="primary")
            if submitted:
                if u and p:
                    ok, rol = _do_login(u, p)
                    if ok:
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")
                else:
                    st.warning("Ingresa usuario y contraseña.")
            st.markdown("<div style='text-align:center;margin:6px 0;color:rgba(255,255,255,0.5);font-size:12px;'>— o —</div>", unsafe_allow_html=True)
            if st.button("👁️  Entrar como invitado", use_container_width=True, key="btn_guest"):
                st.session_state.update({
                    "sess_user": "guest", "sess_rol": "guest",
                    "sess_nombre": "Invitado", "logged_in": True, "consent_ok": True})
                st.rerun()
            st.markdown("""
<div style="margin-top:12px;padding:10px 14px;background:rgba(255,255,255,0.1);
     border-radius:8px;font-size:11px;color:rgba(255,255,255,0.6);text-align:center;">
  Demo: <code style="color:#93C5FD;">demo_trial / demo123</code>
</div>""", unsafe_allow_html=True)

        with reg_tab:
            nombre_r = st.text_input("Nombre completo", placeholder="Tu nombre completo", key="r_nombre")
            u_r = st.text_input("Nombre de usuario (sin espacios)", placeholder="juanperez", key="r_user")
            email_r = st.text_input("Correo electrónico", key="r_email")
            esp_r = st.selectbox("Especialidad", ["Nefrología", "Medicina Crítica / UCI",
                "Medicina Interna", "Urgencias", "Anestesiología", "Otra"], key="r_esp")
            p_r = st.text_input("Contraseña (mín. 6 caracteres)", type="password", key="r_pass")
            p_r2 = st.text_input("Confirmar contraseña", type="password", key="r_pass2")
            st.markdown("""
<div style="background:rgba(255,255,255,0.12);border-radius:8px;padding:10px 14px;
     font-size:12px;color:rgba(255,255,255,0.8);margin:6px 0;">
  🎁 <strong>7 días de prueba completa gratis.</strong><br>
  Después continúas como invitado o activas Premium por <strong>$99 MXN/mes</strong>.
</div>""", unsafe_allow_html=True)
            agree_r = st.checkbox("Acepto que es uso académico y no sustituye el juicio clínico.", key="r_agree")
            if st.button("Crear cuenta →", use_container_width=True, type="primary", key="btn_reg"):
                if not all([nombre_r, u_r, email_r, p_r]):
                    st.error("Completa todos los campos.")
                elif p_r != p_r2:
                    st.error("Las contraseñas no coinciden.")
                elif not agree_r:
                    st.error("Debes aceptar los términos de uso.")
                else:
                    ok, msg = _do_register(u_r, p_r, nombre_r, email_r, esp_r)
                    if ok:
                        _do_login(u_r, p_r)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.markdown("""
<div style="text-align:center;padding:20px 0;color:rgba(255,255,255,0.4);font-size:11px;">
  RenalPro · Dr. Josué Tapia Nefrólogo · León, Gto. · Uso académico · v3.1.0
</div>""", unsafe_allow_html=True)
    st.stop()

# ─── BANNER DE ESTADO DE USUARIO ──────────────────────────────────────────────
def _avatar():
    """Retorna el avatar del usuario actual."""
    return st.session_state.get("sess_avatar", "👨‍⚕️")

def _status_banner():
    rol    = _rol()
    nombre = _nombre()
    av     = _avatar()
    days   = st.session_state.get("sess_dias", 0)

    if rol == "guest":
        st.markdown("""<div style="background:#FFFBEB;border:1px solid #FCD34D;border-radius:10px;
            padding:8px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
            <span>👁️</span>
            <span style="color:#78350F;font-size:13px;"><strong>Modo Invitado</strong> —
            Los datos no persisten al cerrar. Regístrate gratis para guardar prescripciones.</span>
            </div>""", unsafe_allow_html=True)

    elif rol == "trial":
        color = "#EFF6FF" if days > 2 else "#FEF3C7"
        bc    = "#BFDBFE" if days > 2 else "#FCD34D"
        tc    = "#1E40AF" if days > 2 else "#92400E"
        st.markdown(f"""<div style="background:{color};border:1px solid {bc};border-radius:10px;
            padding:8px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:18px;">{av}</span>
            <span style="color:{tc};font-size:13px;"><strong>{nombre}</strong> —
            Prueba gratuita: <strong>{days} día(s) restante(s)</strong></span>
            </div>""", unsafe_allow_html=True)

    elif rol == "pro":
        st.markdown(f"""<div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:10px;
            padding:8px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:18px;">{av}</span>
            <span style="color:#166534;font-size:13px;"><strong>{nombre} — Premium</strong> ·
            {days} días restantes</span>
            </div>""", unsafe_allow_html=True)

    elif rol == "beca":
        dias_txt = "Acceso indefinido" if days > 365 * 5 else f"{days} días"
        st.markdown(f"""<div style="background:linear-gradient(90deg,#0D9488,#0891B2);
            border-radius:10px;padding:8px 16px;margin-bottom:8px;
            display:flex;align-items:center;gap:10px;">
            <span style="font-size:18px;">{av}</span>
            <span style="color:#fff;font-size:13px;">
            <strong>{nombre} — Beca Académica</strong> ·
            Dr. Josué Tapia Nefrólogo · {dias_txt}</span>
            </div>""", unsafe_allow_html=True)

    elif rol == "admin":
        st.markdown(f"""<div style="background:#1E3A8A;border-radius:10px;
            padding:8px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:18px;">{av}</span>
            <span style="color:#fff;font-size:13px;"><strong>{nombre}</strong> ·
            Administrador · Acceso total</span>
            </div>""", unsafe_allow_html=True)

    elif rol in ("expirado", "grace"):
        st.markdown(f"""<div style="background:#FEF2F2;border:1px solid #FCA5A5;border-radius:10px;
            padding:8px 16px;margin-bottom:8px;">
            <strong style="color:#991B1B;">⚠️ {nombre} — Suscripción vencida.</strong>
            <span style="color:#7F1D1D;font-size:12px;"> Tus datos están guardados {days if rol=='grace' else 0} días más.
            Renueva en 💳 Premium.</span>
            </div>""", unsafe_allow_html=True)

# ─── MOSTRAR PANTALLA DE LOGIN SI NO AUTENTICADO ──────────────────────────────
_init_db()
if not _is_auth():
    _show_login()


# ─── HELPERS MATEMÁTICOS ──────────────────────────────────────────────────────
def watson(sex: str, age: float, height_cm: float, weight_kg: float) -> float:
    """ACT estimada por fórmula de Watson (L)."""
    if sex == "M":
        return 2.447 - 0.09156 * age + 0.1074 * height_cm + 0.3362 * weight_kg
    else:
        return -2.097 + 0.1069 * height_cm + 0.2466 * weight_kg

def calc_na_pred_trrc(sex, age, ht, wt, na_plasma, na_bags, qeff, tiempo_hr,
                      na_cit_sol=0.0, inf_cit=0.0, na_post=0.0, inf_post=0.0) -> dict:
    """Predicción de sodio post-TRRC."""
    tbw = watson(sex, age, ht, wt)
    if tbw <= 0:
        return {}
    na_rem = qeff * na_bags / 1000          # mmol/hr eliminado en efluente
    na_from_cit = inf_cit * na_cit_sol / 1000  # mmol/hr aportado por citrato
    na_from_post = inf_post * na_post / 1000    # mmol/hr aportado por reposición post
    net_na = na_from_cit + na_from_post - na_rem  # mmol/hr neto
    na_pred = (na_plasma * tbw + net_na * tiempo_hr) / tbw
    return {"tbw": tbw, "net_na": net_na, "na_pred": na_pred}

def calc_na_corr_trrc(sex, age, ht, wt, na_plasma, na_meta, qeff, na_bags,
                      na_cit_sol=0.0, inf_cit=0.0) -> dict:
    """Estrategias de corrección de sodio en TRRC."""
    tbw = watson(sex, age, ht, wt)
    if tbw <= 0 or qeff <= 0:
        return {}
    delta_total = (na_meta - na_plasma) * tbw      # mmol necesarios en 24h
    delta_hr = delta_total / 24                      # mmol/hr
    na_rem = qeff * na_bags / 1000                   # mmol/hr removido
    na_cit = inf_cit * na_cit_sol / 1000             # mmol/hr del citrato
    needed_from_post = delta_hr + na_rem - na_cit    # mmol/hr que debe aportar post-filtro
    pf_rate = needed_from_post / 0.140               # mL/hr (solución estándar Na=140)
    target_bags = na_bags + delta_hr / (qeff / 1000) # mmol/L objetivo en bolsas
    return {"tbw": tbw, "delta_hr": delta_hr, "pf_rate": max(0, pf_rate),
            "target_bags": target_bags}

def calc_hd_pred(sex, age, ht, wt, tiempo_min, uf_L, qb, qd, koa=0.0) -> dict:
    """Predicción de HD por ecuación de Michaels."""
    tbw = watson(sex, age, ht, wt)
    V_mL = tbw * 1000
    QB, QD, KA = float(qb), float(qd), float(koa)
    if KA > 0:
        if abs(QB - QD) < 1:
            K = QB * KA / (QB + KA)
        else:
            r = QB / QD
            a = KA / QB
            et = math.exp(-a * (1 - r))
            K = QB * (1 - et) / (1 - r * et)
        K = min(K, min(QB, QD) * 0.99)
    else:
        K = min(QB, QD) * 0.85
    KtV = K * tiempo_min / V_mL if V_mL > 0 else 0
    URR = (1 - math.exp(-KtV)) * 100
    UFrate = uf_L * 1000 / tiempo_min if tiempo_min > 0 else 0
    return {"tbw": tbw, "K": K, "Kt": K * tiempo_min / 1000,
            "KtV": KtV, "URR": URR, "UFrate": UFrate}

def calc_koa(K, QB, QD) -> Optional[float]:
    """KoA desde datos in vitro (resolución numérica de Michaels)."""
    if K <= 0 or QB <= 0 or QD <= 0 or K >= min(QB, QD):
        return None
    if abs(QB - QD) < 1:
        return QB * K / (QB - K)
    r = QB / QD
    lo, hi = 0.001, 500.0
    for _ in range(120):
        a = (lo + hi) / 2
        et = math.exp(-a * (1 - r))
        K_calc = QB * (1 - et) / (1 - r * et)
        if K_calc < K:
            lo = a
        else:
            hi = a
    return ((lo + hi) / 2) * QB

def calc_tpe(peso, hct, n_recambios) -> dict:
    """Volúmenes y cinética de plasmaféresis."""
    EPV = 65 * peso * (1 - hct / 100)
    vol_ex = n_recambios * EPV
    res1 = math.exp(-n_recambios) * 100
    return {"EPV": EPV, "vol_ex": vol_ex, "red1": 100 - res1, "res1": res1}

def calc_tpe_total(n_recambios, n_sesiones) -> dict:
    """Cinética IgG acumulada con redistribución extravascular (fracción intravascular ≈45%)."""
    sess_res = 0.55 + 0.45 * math.exp(-n_recambios)
    total_res = sess_res ** n_sesiones * 100
    return {"total_res": total_res, "total_red": 100 - total_res}

def calc_albumin_tpe(pct_vial, pct_deseado, vol_prep_ml) -> int:
    """Número de viales de albúmina para preparación de TPE."""
    return math.ceil(pct_deseado * vol_prep_ml / (pct_vial * 50))

# ── CALCULADORAS NEFROLOGÍA ────────────────────────────────────────────────────
def ckd_epi_2021(sex: str, age: float, cr: float) -> float:
    """CKD-EPI 2021 sin ajuste racial (NEJM 2021)."""
    if cr <= 0: return 0.0
    if sex == "M":
        kappa, mult = 0.9, 1.0
        alpha = -0.302 if cr <= 0.9 else -1.200
    else:
        kappa, mult = 0.7, 1.012
        alpha = -0.241 if cr <= 0.7 else -1.200
    return 142 * ((cr / kappa) ** alpha) * (0.9938 ** age) * mult

def cockcroft_gault(sex: str, age: float, peso_kg: float, cr: float) -> float:
    """Cockcroft-Gault (mL/min)."""
    if cr <= 0: return 0.0
    cg = (140 - age) * peso_kg / (72 * cr)
    return cg * 0.85 if sex == "F" else cg

def peso_ideal_kg(sex: str, height_cm: float) -> float:
    base = 50.0 if sex == "M" else 45.5
    return max(base + 0.906 * (height_cm - 152.4), base)

def estadio_ckd(egfr: float, acr: float = 0) -> tuple:
    if egfr >= 90: g = "G1"
    elif egfr >= 60: g = "G2"
    elif egfr >= 45: g = "G3a"
    elif egfr >= 30: g = "G3b"
    elif egfr >= 15: g = "G4"
    else: g = "G5"
    a = "A1" if acr < 30 else ("A2" if acr < 300 else "A3")
    return g, a

def phos_dose_iv(phos_mg_dl: float, peso_kg: float) -> dict:
    """Dosis IV de reposición de fosfato."""
    if phos_mg_dl >= 2.0:
        sev, lo, hi, t, color = "Leve", 0.08, 0.16, "2–4h", "🟡"
    elif phos_mg_dl >= 1.0:
        sev, lo, hi, t, color = "Moderada", 0.16, 0.32, "4–6h", "🟠"
    else:
        sev, lo, hi, t, color = "Severa", 0.32, 0.64, "6–12h", "🔴"
    return {"sev": sev, "lo": lo * peso_kg, "hi": hi * peso_kg, "tiempo": t, "color": color}

def _s_int(x):
    try:
        return str(int(round(float(x))))
    except Exception:
        return "—"

# ─── HELPERS PDF ──────────────────────────────────────────────────────────────
def _draw_wrapped_text(c, text, x, y, max_width,
                       font_name="Helvetica", font_size=11, leading=14):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    if not text:
        return y
    c.setFont(font_name, font_size)
    words = str(text).split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if stringWidth(test, font_name, font_size) <= max_width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= leading
            line = w
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y

def _fundamento_texto_resumen(qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt):
    return [
        "• Dosis objetivo: Qe = dosis (mL/kg/h) × peso (kg).",
        "• Qp = Qb × (1 − Hto). Qp·h = Qp × 60.",
        "• Límite convectivo: ≤25% de Qp·h para proteger el filtro (FF y coagulación).",
        "• Fracción convectiva: CVVHD=0, CVVHF=1, CVVHDF≈0.6.",
        "• Qr_total = min(Qp·h×0.25, max(Qe − UF, 0)) × fracción.",
        "• División 70/30 (pre/post) para balance depuración/protección filtro.",
        "• Qd = max(Qe − (Qr_pre + Qr_post + UF), 0).",
        "• FF = (Qr_post + UF) / (Qp·h + Qr_pre). Objetivo: FF < 25%.",
        (f"Contexto: Qb={_s_int(qb)} mL/min, Hto={hto:.2f}, Qp={_s_int(qp)} mL/min, "
         f"Qp·h={_s_int(qp_h)} mL/h, Qe={_s_int(qe)} mL/h, Qr_pre={_s_int(qr_pre)}, "
         f"Qr_post={_s_int(qr_post)}, Qd={_s_int(qd)}, UF={_s_int(uf)}, FF≈{ff_txt}."),
    ]

def _fundamento_texto_extendido(na, k, ph, pam, vasopresor_alto, lactato_desc,
                                albumina, anticoag_tipo, r_targets, filtro_final):
    return [
        "— Selección de modalidad —",
        "• CVVHDF en sepsis/choque: mezcla convección y difusión para depurar mediadores y controlar urea/electrolitos.",
        "• CVVHD si se prioriza difusión rápida (hiperK grave) o no hay capacidad convectiva.",
        "",
        "— Límite convectivo y FF —",
        "• Limitar convección a ≤25% de Qp·h disminuye hemoconcentración y riesgo de coagulación.",
        "• Si FF sube: aumenta predilución o reduce Qr_post/UF.",
        "",
        "— División 70/30 (pre/post) —",
        "• 70% predilución: reduce viscosidad intrafiltro, protege membrana.",
        "• 30% postdilución: asegura depuración efectiva.",
        "",
        "— Citrato — Principios farmacológicos —",
        "• Citrato quelata Ca2+ en el circuito → anticoagulación local sin efecto sistémico.",
        "• El complejo Ca-citrato es eliminado por el filtro (~75-80% según Qeff).",
        "• El citrato residual que pasa al paciente es metabolizado por el hígado → HCO3-.",
        "• Cada mmol de citrato genera 3 mmol de HCO3- (vigilar alcalosis).",
        "• Citrato trisódico 4% aporta Na: 3 × 136 = 408 mmol/L de Na → balance de sodio importante.",
        "• Acumulación si: Ca_total/Ca_iónico > 2.5, AG elevado, alcalosis, iCa bajo pese a ↑ Ca.",
        "",
        "— Ajustes por laboratorio —",
        "• K ≥6.0: incrementar Qd (2–3 L/h) con K 0–2 mmol/L; re-labs cada 2–4 h.",
        "• pH <7.20 y/o HCO3 bajo: usar bicarbonato; evitar lactato.",
        "• Hiponatremia: no exceder 8–10 mmol/L/24h (≤8 si alto riesgo ODS).",
        "• Hipernatremia: ≈0.5 mmol/L/h (8–10 mmol/día); corrección gradual.",
        "",
        f"— Contexto actual — Na={na:.1f}, K={k:.1f}, pH={ph:.2f}, PAM={pam:.0f} mmHg, "
        f"Vasopresor={'Sí' if vasopresor_alto else 'No'}, Lactato ↓={'Sí' if lactato_desc else 'No'}, "
        f"Alb={albumina:.2f} g/dL, Anticoag={anticoag_tipo}, Filtro={filtro_final or '—'}.",
    ]

# ─── BIBLIOGRAFÍA ─────────────────────────────────────────────────────────────
Ref = Dict[str, str]
BIBLIO: List[Ref] = [
    {"id": "dose_core_2024", "yr": "2024", "title": "Continuous Renal Replacement Therapy - StatPearls",
     "where": "NCBI/StatPearls", "url": "https://www.ncbi.nlm.nih.gov/books/NBK556028/",
     "tags": "dosis,crrt,revision", "blurb": "Dosis entregada 20–25 mL/kg/h; sin beneficio >25."},
    {"id": "dose_review_2021", "yr": "2021", "title": "Dose of CRRT in Critically Ill Patients",
     "where": "Karger (Nephron)", "url": "https://karger.com/nef/article/145/2/91/227459",
     "tags": "dosis,crrt,revision", "blurb": "Revisión de evidencia de dosis y métricas de calidad."},
    {"id": "rca_review_2023", "yr": "2023", "title": "Regional Citrate Anticoagulation in CRRT",
     "where": "PMC Review", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10221969/",
     "tags": "rca,anticoagulacion,citrato,crrt", "blurb": "RCA primera línea si no hay contraindicaciones."},
    {"id": "rca_consensus_2023", "yr": "2023", "title": "Management of RCA for CRRT",
     "where": "Military Medical Research",
     "url": "https://mmrjournal.biomedcentral.com/articles/10.1186/s40779-023-00457-9",
     "tags": "rca,anticoagulacion,citrato,consenso", "blurb": "Consenso operativo de RCA en CKRT."},
    {"id": "cit_accumulation_2022", "yr": "2022",
     "title": "Citrate Accumulation in CRRT: Detection and Management",
     "where": "NDT (Oxford)", "url": "https://academic.oup.com/ndt/article/37/7/1329/6472893",
     "tags": "citrato,acumulacion,rca,seguridad",
     "blurb": "Ca total/Ca iónico >2.5 como criterio principal de acumulación."},
    {"id": "ff_practical_2025", "yr": "2025", "title": "Renal replacement therapy in ICU (practical)",
     "where": "Ann Intensive Care",
     "url": "https://annalsofintensivecare.springeropen.com/articles/10.1186/s13613-025-01517-0",
     "tags": "ff,crrt,practica", "blurb": "FF <25% como objetivo para proteger el filtro."},
    {"id": "oxiris_meta_2024", "yr": "2024", "title": "CRRT with oXiris improve outcomes in septic shock?",
     "where": "J Clin Med", "url": "https://www.mdpi.com/2077-0383/13/24/7527",
     "tags": "oxiris,sepsis,adsorcion", "blurb": "Señales favorables pero heterogeneidad/sesgo presentes."},
    {"id": "crrt_corecurr_2025", "yr": "2025", "title": "CKRT Core Curriculum",
     "where": "AJKD", "url": "https://www.ajkd.org/article/S0272-6386%2824%2901120-X/fulltext",
     "tags": "crrt,revision,general", "blurb": "Currículo núcleo 2025: cuándo y cómo prescribir CKRT."},
    {"id": "hd_adequacy_2021", "yr": "2021", "title": "Hemodialysis Adequacy: 2020 Update",
     "where": "AJKD", "url": "https://www.ajkd.org/article/S0272-6386(20)31249-3/fulltext",
     "tags": "hd,ktv,adecuacion", "blurb": "Kt/V ≥1.2 por sesión (3×/semana); Kt/V 1.4 objetivo."},
    {"id": "tpe_guidelines_2023", "yr": "2023", "title": "TPE Guidelines ASFA 2023",
     "where": "J Clin Apheresis", "url": "https://onlinelibrary.wiley.com/doi/10.1002/jca.22043",
     "tags": "tpe,plasmaferesis,guias", "blurb": "Indicaciones y técnica de TPE por categorías de evidencia."},
]

def filtrar_refs_por_contexto(escenarios_sel: List[str], anticoag_tipo: str) -> List[Ref]:
    e = " ".join([s.lower() for s in escenarios_sel])
    tags_req = {"dosis", "ff", "crrt", "revision"}
    if any(x in e for x in ["sepsis", "choque"]):
        tags_req.update(["sepsis", "oxiris"])
    if "RCA" in (anticoag_tipo or "") or "citrato" in (anticoag_tipo or "").lower():
        tags_req.update(["rca", "anticoagulacion", "citrato"])
    seen, sel = set(), []
    for r in BIBLIO:
        rtags = set(r.get("tags", "").split(","))
        if rtags & tags_req and r["id"] not in seen:
            sel.append(r)
            seen.add(r["id"])
    return sel[:12]

# ─── LÓGICA CLÍNICA PRINCIPAL ─────────────────────────────────────────────────
def prioridad_modalidad(m):
    if m in ["CVVHDF", "CVVHDF (flujos bajos)", "CVVHDF + HCO"]:
        return 3
    if m == "CVVHD":
        return 2
    if m == "CVVHF":
        return 1
    return 0

def prioridad_filtro(f):
    if f == "Alta adsorción/HCO":
        return 99
    if "M200" in f:
        return 3
    if "M150" in f or "M100–M150" in f:
        return 2
    if "M100" in f:
        return 1
    return 0

def sugerir_por_escenario(esc):
    MAP = {
        "Sepsis / choque séptico": ("CVVHDF", "Alta adsorción/HCO",
            "Mixto conv/dif; FF≤25%. Adsorción opcional; beneficio duro aún incierto."),
        "Choque cardiogénico": ("CVVHDF", "M150 (~1.5 m²)",
            "Evitar cambios bruscos; UF conservadora; vigilar FF."),
        "Post infarto": ("CVVHD", "M100–M150",
            "Difusivo; control fino de electrolitos; UF cauta."),
        "Neurocrítico / TCE": ("CVVHDF (flujos bajos)", "M100 (~1.0 m²)",
            "Evitar oscilaciones osmóticas; corrección Na guiada."),
        "Sobrecarga hídrica aislada": ("CVVHF", "M200 (~2.0 m²)",
            "Convectivo favorece UF; vigilar FF y tolerancia hemodinámica."),
        "Intoxicación / sobredosis": ("CVVHD (alta dosis)", "M200 (~2.0 m²)",
            "Difusión alta; evaluar unión a proteínas."),
        "Hiponatremia severa": ("CVVHDF", "M100 (~1.0 m²)",
            "Dializado Na bajo; no exceder 8–10 mEq/L/24h (≤8 si alto riesgo ODS)."),
        "Hipernatremia": ("CVVHDF", "M100–M150",
            "≈0.5 mEq/L/h (8–10 mEq/día); dializado Na más alto."),
        "Hiperamonemia": ("CVVHD", "M150 (~1.5 m²)",
            "Difusión continua; prioriza dosis/flujo; buffer adecuado."),
        "Rabdomiólisis": ("CVVHDF", "M200 (~2.0 m²)",
            "Mioglobina; considerar HCO con vigilancia de albúmina."),
        "Síndrome de liberación de citocinas": ("CVVHDF + HCO", "Alta adsorción/HCO",
            "Adsorción de mediadores; beneficio duro incierto."),
    }
    return MAP.get(esc, ("", "", ""))

def combinar_recomendaciones(escenarios_sel):
    mods, filts, coments = [], [], []
    for e in escenarios_sel:
        m, f, c = sugerir_por_escenario(e)
        if m:
            mods.append(m)
        if f:
            filts.append(f)
        if c:
            coments.append(c)
    mod_final = sorted(mods, key=lambda x: prioridad_modalidad(x), reverse=True)[0] if mods else ""
    filtro_final = sorted(filts, key=lambda x: prioridad_filtro(x), reverse=True)[0] if filts else ""
    return mod_final, filtro_final, " | ".join(coments)

def flows_and_ff(qb, hto, dosis_mlkg, peso, uf, modalidad):
    qp = qb * (1 - hto)
    qp_h = qp * 60
    qe = dosis_mlkg * peso
    if "CVVHD" in modalidad and "CVVHDF" not in modalidad:
        frac_conv = 0.0
    elif "CVVHF" in modalidad:
        frac_conv = 1.0
    else:
        frac_conv = 0.6
    qr_total = 0 if frac_conv == 0 else max(min(qp_h * 0.25, max(qe - uf, 0)), 0) * frac_conv
    qr_pre = round(qr_total * 0.7)
    qr_post = round(qr_total * 0.3)
    qd = max(qe - (qr_pre + qr_post + uf), 0)
    denom = max(qp_h + qr_pre, 1e-9)
    ff = (qr_post + uf) / denom
    return qp, qp_h, qe, qr_pre, qr_post, qd, ff

@dataclass
class Filtro:
    nombre: str
    tags: List[str]
    area_m2: Optional[float]
    comentarios: str

FILTROS: Dict[str, Filtro] = {
    # ── Prismaflex ST series (Baxter/Gambro) — los más usados en México ──────
    "Prismaflex ST 60 (0.6 m²)": Filtro(
        "Prismaflex ST 60 (0.6 m²)", ["convectivo", "CVVH", "CVVHDF", "prismaflex"], 0.6,
        "Pacientes pediátricos o adultos pequeños. CVVH/CVVHDF a dosis bajas."),
    "Prismaflex ST 100 (1.0 m²)": Filtro(
        "Prismaflex ST 100 (1.0 m²)", ["convectivo", "CVVH", "CVVHDF", "prismaflex"], 1.0,
        "Estándar adulto menor. Compatible con Prismocitrate. Qb hasta 180 mL/min."),
    "Prismaflex ST 150 (1.5 m²)": Filtro(
        "Prismaflex ST 150 (1.5 m²)", ["convectivo", "CVVH", "CVVHDF", "prismaflex"], 1.5,
        "El más usado. Adulto estándar/grande. Compatible con Prismocitrate y citrato 4%. Qb hasta 250 mL/min."),
    "Prismaflex ST 200 (2.0 m²)": Filtro(
        "Prismaflex ST 200 (2.0 m²)", ["convectivo", "CVVH", "CVVHDF", "prismaflex"], 2.0,
        "Adulto grande o dosis alta. Alta área de membrana. Qb hasta 300 mL/min."),
    # ── Fresenius AV series ───────────────────────────────────────────────────
    "Fresenius AV 400 (0.4 m²)": Filtro(
        "Fresenius AV 400 (0.4 m²)", ["convectivo", "CVVH", "CVVHDF", "fresenius"], 0.4,
        "Pacientes pequeños. multiFiltrate. Bajo volumen del circuito."),
    "Fresenius AV 600 (0.6 m²)": Filtro(
        "Fresenius AV 600 (0.6 m²)", ["convectivo", "CVVH", "CVVHDF", "fresenius"], 0.6,
        "Adulto bajo peso. multiFiltrate."),
    "Fresenius AV 1000 (1.0 m²)": Filtro(
        "Fresenius AV 1000 (1.0 m²)", ["convectivo", "difusivo", "CVVH", "CVVHDF", "CVVHD", "fresenius"], 1.0,
        "Adulto estándar. multiFiltrate. Útil para CVVHD y CVVHDF."),
    # ── Alta adsorción / HCO ─────────────────────────────────────────────────
    "Oxiris AN69-ST (1.5 m²; adsorción alta)": Filtro(
        "Oxiris AN69-ST (1.5 m²; adsorción alta)", ["adsorción", "CVVHDF", "sepsis"], 1.5,
        "Adsorción de endotoxinas y mediadores inflamatorios. Beneficio en desenlaces duros aún incierto. Prismaflex."),
    "HCO 1100 (1.1 m²; alta cut-off)": Filtro(
        "HCO 1100 (1.1 m²; alta cut-off)", ["HCO", "CVVH", "CVVHDF", "mioglobina"], 1.1,
        "Elimina medianas/mioglobina. Vigilar pérdidas de albúmina (Alb <2.5: reconsiderar)."),
    "HCO 730 (0.7 m²; alta cut-off)": Filtro(
        "HCO 730 (0.7 m²; alta cut-off)", ["HCO", "CVVH", "CVVHDF", "mioglobina"], 0.7,
        "Similar a HCO 1100, menor área. Mismas precauciones de albúmina."),
    # ── Genérico / disponibilidad local ──────────────────────────────────────
    "Filtro convectivo genérico (1.3 m²)": Filtro(
        "Filtro convectivo genérico (1.3 m²)", ["convectivo", "CVVH", "CVVHDF"], 1.3,
        "Uso general cuando no hay Prismaflex/Fresenius específico disponible."),
    "Filtro difusivo genérico (2.1 m²)": Filtro(
        "Filtro difusivo genérico (2.1 m²)", ["difusivo", "CVVHD", "CVVHDF"], 2.1,
        "Cuando se prioriza depuración difusiva (urea/K alta). Alta área de membrana."),
}

def sugerir_filtro_por_escenarios(escenarios_sel):
    e = " ".join([s.lower() for s in escenarios_sel])
    if any(x in e for x in ["sepsis", "choque", "citocinas"]):
        return "Oxiris AN69-ST (1.5 m²; adsorción alta)"
    if any(x in e for x in ["rabdomiólisis", "rabdomiolisis"]):
        return "HCO 1100 (1.1 m²; alta cut-off)"
    if any(x in e for x in ["amonio", "hiperamonemia"]):
        return "Prismaflex ST 150 (1.5 m²)"
    return "Prismaflex ST 150 (1.5 m²)"

def checar_contraindicaciones(filtro, albumina_gdl=None, hit=None):
    alerts = []
    fn = filtro.lower()
    if "hco" in fn and albumina_gdl is not None and albumina_gdl < 2.5:
        alerts.append("⚠️ HCO con Alb <2.5 g/dL: reconsiderar su uso.")
    if "oxiris" in fn and hit:
        alerts.append("⚠️ Evitar Oxiris si hay antecedente de HIT.")
    return alerts

def sepsis_presente(escs):
    e = " ".join([s.lower() for s in (escs or [])])
    return any(x in e for x in ["sepsis", "choque séptico", "séptico"])

def rec_labs(k, ph, na):
    ajustes = []
    if k is not None and k >= 6.0:
        ajustes.append("K≥6: ↑ Qd 2–3 L/h con dializado K 0–2; labs cada 2–4 h.")
    if ph is not None and ph < 7.20:
        ajustes.append("Acidosis severa: bicarbonato (no lactato); ↑ Qd/Qe hasta 2–3 L/h.")
    if na is not None and na < 125:
        ajustes.append("Hiponatremia: no exceder 8–10 mmol/L/24h (≤8 si riesgo ODS).")
    if na is not None and na > 155:
        ajustes.append("Hipernatremia: ≈0.5 mmol/L/h (8–10/día); dializado Na más alto.")
    return ajustes or ["Sin ajustes críticos automáticos por laboratorio."]

# ─── EXPORT PDF ───────────────────────────────────────────────────────────────
def export_pdf():
    s = st.session_state
    peso = float(s.get("sb_peso", 70.0))
    hto = float(s.get("sb_hto", 0.30))
    qb = int(s.get("sb_qb", 200))
    uf = int(s.get("sb_uf", 100))
    dosis_mlkg = int(s.get("sb_dosis", 30))
    escenarios = s.get("sb_escenarios", ["Sepsis / choque séptico"])
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    filtro_final = s.get("ui_filtro", filtro_final)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(
        qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_txt = f"{ff:.1%}" if ff is not None else "—"
    na = float(s.get("na_main", 140.0))
    k = float(s.get("k_main", 4.0))
    ph = float(s.get("ph_main", 7.35))
    pam = float(s.get("pam", 65.0))
    vasopresor_alto = s.get("vaso_alto_sel", "No") == "Sí"
    lactato_desc = s.get("lactato_desc_sel", "No") == "Sí"
    albumina = float(s.get("alb_main", 3.0))
    anticoag_tipo = s.get("anticoagulacion_tipo", "—")
    r_targets = s.get("rca_targets", {})
    unidad = s.get("rx_unidad", "")
    nombre_paciente = s.get("rx_nombre_paciente", "")
    fecha_nac = s.get("rx_fecha_nac", "")
    edad = s.get("rx_edad", "")
    sexo = s.get("rx_sexo", "")
    expediente = s.get("rx_expediente", "")
    nombre_medico = s.get("rx_nombre_medico", "")
    sello = s.get("rx_sello", "")
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_name = "".join(ch for ch in (nombre_paciente or "").replace(" ", "") if ch.isalnum())
    filename = f"RenalPro_{safe_name}_{ts}.pdf" if safe_name else f"RenalPro_{ts}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    w, h = letter
    margin = 50
    y = h - margin
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "RenalPro — Prescripción Terapia de Reemplazo Renal Continua")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - margin, y, datetime.now().strftime("%d/%m/%Y %H:%M"))
    y -= 22
    if unidad:
        c.setFont("Helvetica", 11)
        c.drawString(margin, y, f"Unidad: {unidad}")
        y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Ficha de identificación")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Nombre: {nombre_paciente}")
    c.drawString(margin + 280, y, f"FN: {fecha_nac}")
    y -= 14
    c.drawString(margin, y, f"Edad: {edad}  Sexo: {sexo}  Expediente: {expediente}")
    y -= 20
    c.drawString(margin, y, "—" * 90)
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Diagnóstico / escenarios")
    y -= 14
    c.setFont("Helvetica", 11)
    y = _draw_wrapped_text(c, ", ".join(escenarios) if escenarios else "—", margin, y, w - 2 * margin)
    c.drawString(margin, y, f"Modalidad: {mod_final or '—'}  |  Filtro: {filtro_final or '—'}  |  FF: {ff_txt}")
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Flujos")
    y -= 14
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Qb: {_s_int(qb)} mL/min  |  Qp: {_s_int(qp)} mL/min  |  Qe: {_s_int(qe)} mL/h")
    y -= 14
    c.drawString(margin, y,
                 f"Qr pre: {_s_int(qr_pre)} mL/h  |  Qr post: {_s_int(qr_post)} mL/h  |  Qd: {_s_int(qd)} mL/h  |  UF: {_s_int(uf)} mL/h")
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Anticoagulación")
    y -= 14
    c.setFont("Helvetica", 11)
    if anticoag_tipo == "HNF":
        iu_h = s.get("hnf_ui_h", int(peso * 5))
        c.drawString(margin, y, f"HNF — Dosis inicial: {_s_int(iu_h)} UI/h (ajustar a aPTT)")
        y -= 14
    elif anticoag_tipo == "RCA":
        cit_ml = s.get("rca_citrato_ml_h", 0)
        ca_ml = s.get("rca_calcio_ml_h", 0)
        c.drawString(margin, y,
                     f"RCA — Citrato: {_s_int(cit_ml)} mL/h  |  Ca-Gluconato: {_s_int(ca_ml)} mL/h")
        y -= 14
        c.drawString(margin, y,
                     f"Dianas: iCa post-filtro {r_targets.get('iCa_post', '0.25-0.40')} mmol/L  |  iCa sistémico {r_targets.get('iCa_sist', '1.0-1.2')} mmol/L")
        y -= 14
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Comentarios")
    y -= 14
    c.setFont("Helvetica", 11)
    y = _draw_wrapped_text(c, s.get("rx_comentarios", "") or "—", margin, y, w - 2 * margin)
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Médico tratante:")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, nombre_medico or "")
    if sello:
        y -= 14
        y = _draw_wrapped_text(c, f"Sello: {sello}", margin, y, w - 2 * margin)
    # Página 2: fundamento
    c.showPage()
    y = h - 50
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Fundamento y Cálculos — RenalPro v3.1.0")
    y -= 22
    c.setFont("Helvetica", 11)
    pdf_ext = bool(s.get("pdf_extendido", False))
    for linea in _fundamento_texto_resumen(qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt):
        y = _draw_wrapped_text(c, linea, 50, y, w - 100)
        if y < 80:
            c.showPage()
            y = h - 50
            c.setFont("Helvetica", 11)
    if pdf_ext:
        y -= 8
        for linea in _fundamento_texto_extendido(na, k, ph, pam, vasopresor_alto, lactato_desc,
                                                 albumina, anticoag_tipo, r_targets, filtro_final):
            y = _draw_wrapped_text(c, linea, 50, y, w - 100)
            if y < 80:
                c.showPage()
                y = h - 50
                c.setFont("Helvetica", 11)
    # Referencias
    refs_pdf = filtrar_refs_por_contexto(escenarios, anticoag_tipo)
    if refs_pdf:
        c.showPage()
        y = h - 50
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Referencias")
        y -= 22
        c.setFont("Helvetica", 10)
        for idx, r in enumerate(refs_pdf, 1):
            y = _draw_wrapped_text(c, f"[{idx}] {r['title']} — {r['where']} ({r['yr']})",
                                   50, y, w - 100, font_size=10, leading=12)
            if r.get("url"):
                y = _draw_wrapped_text(c, f"URL: {r['url']}", 60, y, w - 110, font_size=9, leading=11)
            y -= 4
            if y < 80:
                c.showPage()
                y = h - 50
                c.setFont("Helvetica", 10)
    c.save()
    return filename

def export_pdf_pro():
    """
    Genera un PDF clínico profesional con:
    - Página 1: Prescripción con tablas y colores
    - Página 2: Protocolo de Enfermería (adaptativo HNF vs RCA)
    - Página 3: Fundamento matemático + referencias
    """
    import io
    s = st.session_state

    # ── PALETTE ──────────────────────────────────────────────────────────────
    AZUL      = rl_colors.HexColor('#1E3A8A')
    AZUL_MED  = rl_colors.HexColor('#2563EB')
    AZUL_CLR  = rl_colors.HexColor('#DBEAFE')
    GRIS      = rl_colors.HexColor('#F8FAFC')
    GRIS2     = rl_colors.HexColor('#E2E8F0')
    BLANCO    = rl_colors.white
    NEGRO     = rl_colors.HexColor('#1E293B')
    AMARILLO  = rl_colors.HexColor('#FCD34D')
    ROJO_CLR  = rl_colors.HexColor('#FEF2F2')
    ROJO      = rl_colors.HexColor('#DC2626')
    VERDE_CLR = rl_colors.HexColor('#F0FDF4')
    VERDE     = rl_colors.HexColor('#16A34A')

    # ── ESTILOS ───────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    def estilo(name, parent='Normal', fontSize=10, leading=13, textColor=NEGRO,
               fontName='Helvetica', alignment=TA_LEFT, spaceBefore=0, spaceAfter=0,
               leftIndent=0, bold=False):
        return ParagraphStyle(name=name, parent=styles['Normal'],
            fontSize=fontSize, leading=leading, textColor=textColor,
            fontName='Helvetica-Bold' if bold else fontName,
            alignment=alignment, spaceBefore=spaceBefore, spaceAfter=spaceAfter,
            leftIndent=leftIndent)

    E_TITULO   = estilo('titulo',   fontSize=15, textColor=BLANCO, bold=True, alignment=TA_LEFT)
    E_SUBTIT   = estilo('subtit',   fontSize=9,  textColor=rl_colors.HexColor('#BFDBFE'), alignment=TA_LEFT)
    E_FECHA    = estilo('fecha',    fontSize=9,  textColor=BLANCO, alignment=TA_RIGHT)
    E_SEC      = estilo('sec',      fontSize=10, textColor=BLANCO, bold=True)
    E_SECN     = estilo('secn',     fontSize=11, textColor=AZUL, bold=True, spaceBefore=8, spaceAfter=4)
    E_CUERPO   = estilo('cuerpo',   fontSize=9,  leading=12, textColor=NEGRO)
    E_TH       = estilo('th',       fontSize=9,  textColor=BLANCO, bold=True, alignment=TA_CENTER)
    E_TH_L     = estilo('th_l',     fontSize=9,  textColor=BLANCO, bold=True)
    E_TD       = estilo('td',       fontSize=9,  leading=11, textColor=NEGRO)
    E_TD_B     = estilo('td_b',     fontSize=9,  leading=11, textColor=NEGRO, bold=True)
    E_BULLET   = estilo('bul',      fontSize=9,  leading=12, textColor=NEGRO, leftIndent=12)
    E_FIRMA    = estilo('firma',    fontSize=9,  textColor=rl_colors.HexColor('#64748B'))
    E_FOOT     = estilo('foot',     fontSize=7,  textColor=rl_colors.HexColor('#94A3B8'), alignment=TA_CENTER)
    E_WARN     = estilo('warn',     fontSize=9,  leading=12, textColor=rl_colors.HexColor('#92400E'))
    E_OK       = estilo('ok',       fontSize=9,  leading=12, textColor=rl_colors.HexColor('#166534'))
    E_ENF_TIT  = estilo('enft',     fontSize=11, textColor=AZUL, bold=True, spaceBefore=6, spaceAfter=3)
    E_ENF_CRIT = estilo('enfc',     fontSize=9,  leading=12, textColor=ROJO, bold=True)

    # ── DATOS ─────────────────────────────────────────────────────────────────
    peso      = float(s.get("sb_peso", 70.0))
    hto       = float(s.get("sb_hto", 0.30))
    qb        = int(s.get("sb_qb", 200))
    uf        = int(s.get("sb_uf", 100))
    dosis_mlkg = int(s.get("sb_dosis", 30))
    escenarios = s.get("sb_escenarios", ["Sepsis / choque séptico"])
    mod_final, filtro_final, _ = combinar_recomendaciones(escenarios)
    filtro_final = s.get("ui_filtro", filtro_final)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(
        qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_pct = ff * 100 if ff else 0
    ff_txt = f"{ff_pct:.1f}%"
    ff_ok  = ff_pct < 25 if ff else True

    anticoag  = s.get("anticoagulacion_tipo", "HNF")
    hnf_ui_h  = float(s.get("hnf_ui_h", peso * 5))
    r_targets = s.get("rca_targets", {})
    cit_ml_h  = s.get("rca_citrato_ml_h", 0)
    ca_ml_h   = s.get("rca_calcio_ml_h", 0)

    unidad   = s.get("rx_unidad", "")
    nom_pac  = s.get("rx_nombre_paciente", "")
    fn       = s.get("rx_fecha_nac", "")
    edad     = s.get("rx_edad", "")
    sexo     = s.get("rx_sexo", "")
    expte    = s.get("rx_expediente", "")
    nom_med  = s.get("rx_nombre_medico", "")
    sello    = s.get("rx_sello", "")
    coments  = s.get("rx_comentarios", "") or "—"
    na       = float(s.get("na_main", 140.0))
    k        = float(s.get("k_main", 4.0))
    ph       = float(s.get("ph_main", 7.35))
    pdf_ext  = bool(s.get("pdf_extendido", False))

    ts = datetime.now().strftime("%d/%m/%Y  %H:%M")
    buf = io.BytesIO()

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def sec_bar(texto):
        """Barra de sección azul."""
        t = Table([[Paragraph(texto, E_SEC)]], colWidths=[PAGE_W])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), AZUL_MED),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        return t

    def data_table(rows, col_widths, header=True):
        t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
        style = [
            ('GRID', (0,0), (-1,-1), 0.5, GRIS2),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        if header:
            style += [
                ('BACKGROUND', (0,0), (-1,0), AZUL_MED),
                ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]
            for i in range(1, len(rows)):
                bg = BLANCO if i % 2 == 1 else GRIS
                style.append(('BACKGROUND', (0,i), (-1,i), bg))
        t.setStyle(TableStyle(style))
        return t

    def bullet(txt, color=NEGRO):
        return Paragraph(f"• {txt}",
            ParagraphStyle('b', parent=styles['Normal'], fontSize=9,
                leading=12, textColor=color, leftIndent=14, spaceAfter=2))

    # ── DOCUMENTO ─────────────────────────────────────────────────────────────
    PAGE_W = letter[0] - 2.5*cm
    doc = SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=1.25*cm, rightMargin=1.25*cm,
        topMargin=1.0*cm, bottomMargin=1.5*cm)

    story = []

    # ══ PÁGINA 1: PRESCRIPCIÓN ════════════════════════════════════════════════

    # ── HEADER ────────────────────────────────────────────────────────────────
    hdr = Table([
        [Paragraph("<b>RenalPro</b>", E_TITULO),
         Paragraph(f"Prescripción — Terapia de Reemplazo Renal Continua", E_SUBTIT),
         Paragraph(ts, E_FECHA)],
        [Paragraph(f"{unidad or 'Unidad: —'}", E_SUBTIT),
         Paragraph("Dr. Josué Tapia Nefrólogo", E_SUBTIT),
         Paragraph(f"{VERSION}", E_FOOT)],
    ], colWidths=[3.5*cm, 10*cm, 4*cm])
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), AZUL),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (0,0), (0,1)),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 4*mm))

    # ── DATOS DEL PACIENTE ────────────────────────────────────────────────────
    story.append(sec_bar("▌  IDENTIFICACIÓN DEL PACIENTE"))
    story.append(Spacer(1, 1*mm))
    pac = data_table([
        [Paragraph('Nombre', E_TH_L), Paragraph('Expediente', E_TH_L),
         Paragraph('F. Nacimiento', E_TH_L), Paragraph('Edad / Sexo', E_TH_L),
         Paragraph('Peso / Hto', E_TH_L)],
        [Paragraph(nom_pac or '—', E_TD_B), Paragraph(expte or '—', E_TD),
         Paragraph(fn or '—', E_TD), Paragraph(f"{edad} años / {sexo}", E_TD),
         Paragraph(f"{peso:.0f} kg / {hto*100:.0f}%", E_TD)],
    ], col_widths=[5.5*cm, 2.5*cm, 3*cm, 3*cm, 3.5*cm])
    story.append(pac)
    story.append(Spacer(1, 3*mm))

    # ── DIAGNÓSTICO ───────────────────────────────────────────────────────────
    story.append(sec_bar("▌  DIAGNÓSTICO / ESCENARIOS CLÍNICOS"))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(", ".join(escenarios) if escenarios else "—", E_CUERPO))
    story.append(Spacer(1, 3*mm))

    # ── MODALIDAD Y FLUJOS ────────────────────────────────────────────────────
    story.append(sec_bar("▌  MODALIDAD Y FLUJOS PRESCRITOS"))
    story.append(Spacer(1, 1*mm))

    ff_color = VERDE if ff_ok else ROJO
    ff_label = f"{ff_txt} ✓" if ff_ok else f"{ff_txt} ⚠ ALTO"
    flujos = data_table([
        [Paragraph('Modalidad', E_TH), Paragraph('Filtro', E_TH),
         Paragraph('Qb (mL/min)', E_TH), Paragraph('Qp (mL/min)', E_TH),
         Paragraph('Qe (mL/h)', E_TH), Paragraph('FF', E_TH)],
        [Paragraph(mod_final or '—', E_TD_B), Paragraph(filtro_final or '—', E_TD),
         Paragraph(_s_int(qb), E_TD), Paragraph(_s_int(qp), E_TD),
         Paragraph(_s_int(qe), E_TD),
         Paragraph(ff_label, ParagraphStyle('ff', parent=styles['Normal'],
             fontSize=9, textColor=ff_color, fontName='Helvetica-Bold'))],
    ], col_widths=[2.8*cm, 3.2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm])
    story.append(flujos)
    story.append(Spacer(1, 2*mm))

    flujos2 = data_table([
        [Paragraph('Qr pre (mL/h)', E_TH), Paragraph('Qr post (mL/h)', E_TH),
         Paragraph('Qd (mL/h)', E_TH), Paragraph('UF neta (mL/h)', E_TH),
         Paragraph('Dosis (mL/kg/h)', E_TH)],
        [Paragraph(_s_int(qr_pre), E_TD), Paragraph(_s_int(qr_post), E_TD),
         Paragraph(_s_int(qd), E_TD), Paragraph(_s_int(uf), E_TD),
         Paragraph(f"{dosis_mlkg}", E_TD)],
    ], col_widths=[3.4*cm, 3.4*cm, 2.8*cm, 3*cm, 3.4*cm])
    story.append(flujos2)
    story.append(Spacer(1, 3*mm))

    # ── ANTICOAGULACIÓN ───────────────────────────────────────────────────────
    story.append(sec_bar("▌  ANTICOAGULACIÓN"))
    story.append(Spacer(1, 1*mm))

    if anticoag == "HNF":
        ac_rows = [
            [Paragraph('Tipo', E_TH_L), Paragraph('Dosis inicial', E_TH_L),
             Paragraph('Meta aPTT', E_TH_L), Paragraph('Control', E_TH_L)],
            [Paragraph('Heparina No Fraccionada (HNF)', E_TD_B),
             Paragraph(f'{_s_int(hnf_ui_h)} UI/hr IV continuo', E_TD),
             Paragraph('45 – 80 segundos', E_TD),
             Paragraph('c/ 4–6 h hasta estabilizar, luego c/12 h', E_TD)],
        ]
    else:
        ac_rows = [
            [Paragraph('Tipo', E_TH_L), Paragraph('Parámetro', E_TH_L),
             Paragraph('Valor', E_TH_L), Paragraph('Meta', E_TH_L)],
            [Paragraph('RCA — Citrato Trisódico 4%', E_TD_B),
             Paragraph('Tasa citrato', E_TD),
             Paragraph(f'{_s_int(cit_ml_h)} mL/h', E_TD),
             Paragraph('iCa post-filtro 0.25–0.40 mmol/L', E_TD)],
            [Paragraph('', E_TD),
             Paragraph('Ca-gluconato post-filtro', E_TD),
             Paragraph(f'{_s_int(ca_ml_h)} mL/h', E_TD),
             Paragraph('iCa sistémico 1.0–1.2 mmol/L', E_TD)],
        ]
    story.append(data_table(ac_rows, col_widths=[4.5*cm, 4*cm, 3*cm, 6*cm]))
    story.append(Spacer(1, 3*mm))

    # ── RECOMENDACIONES CLÍNICAS POR ESCENARIO ────────────────────────────────
    RECS_ESCENARIO = {
        "Sepsis / choque séptico": [
            "UF objetivo inicial 150–200 mL/h; ajustar si PAM <65 mmHg",
            "Meta de balance: neutro a ligeramente negativo (-500 a -1,000 mL/día)",
            "Monitoreo de lactato c/4–6h; meta <2 mmol/L",
            "Fósforo sérico c/6–8h (riesgo hipofosforemia por soluciones sin PO₄)",
            "Si vasopresor alto: priorizar RCA sobre HNF (menor riesgo de sangrado)",
        ],
        "Choque cardiogénico": [
            "UF conservadora: 100–150 mL/h para evitar hipotensión",
            "Monitoreo estrecho de PA c/15–30 min durante TRRC",
            "Considerar soporte inotrópico antes de UF agresiva",
            "Evitar hipokalemia (riesgo arrítmico) — K en bolsas según laboratorio",
        ],
        "Sobrecarga hídrica aislada": [
            "UF agresiva posible: 200–500 mL/h si hemodinámica estable",
            "Meta de balance negativo según objetivo del médico tratante",
            "Monitoreo de PA cada hora durante UF intensiva",
        ],
        "Neurocrítico / TCE": [
            "Evitar cambios bruscos de Na — corrección máx 8–10 mEq/L/día",
            "Hipernatremia permisiva si hay hipertensión intracraneal (PIC elevada)",
            "UF conservadora para evitar hipotensión y ↓ PPC",
            "Usar RCA si está en anticoagulación sistémica concomitante",
        ],
        "Hiponatremia severa": [
            "Meta de corrección: NO exceder 8–10 mEq/L en 24h (riesgo de mielinolisis)",
            "Na en bolsas de reemplazo ajustado según cálculo de sodio TRRC",
            "Monitoreo de Na sérico c/2–4h hasta estabilización",
        ],
        "Hipernatremia": [
            "Corrección gradual: No bajar Na >10 mEq/L/24h (riesgo de edema cerebral)",
            "Usar solución de reemplazo con Na ajustado — ver módulo Sodio TRRC",
            "Monitoreo de Na sérico c/2–4h",
        ],
        "Rabdomiólisis": [
            "UF alta + dosis alta (>35 mL/kg/h) para clearance de mioglobina",
            "Meta de diuresis si se recupera: >200–300 mL/h (alcalinización urinaria)",
            "CK, creatinina, electrolitos c/6–8h",
            "Hiperkalemia severa frecuente — K 0 mEq/L en bolsas inicialmente",
        ],
        "Hiperamonemia": [
            "Dosis muy alta recomendada: 45–60 mL/kg/h para clearance de amonio",
            "Monitoreo de amonio sérico c/4–6h",
            "Alanina (o glutamina) pueden necesitarse si nutrición parenteral",
        ],
        "Intoxicación / sobredosis": [
            "Dosis alta: 35–45 mL/kg/h para clearance del tóxico",
            "Identificar si el tóxico es dializable (peso molecular, unión a proteínas)",
            "Documentar hora de ingesta y niveles séricos del tóxico si disponibles",
        ],
        "Síndrome de liberación de citocinas": [
            "Filtro de alta adsorción (oXiris® o similar) si disponible",
            "Dosis alta: 35 mL/kg/h o más según protocolo institucional",
            "Monitoreo de IL-6 y ferritina si están disponibles",
        ],
    }

    recs = []
    for esc in escenarios:
        for r in RECS_ESCENARIO.get(esc, []):
            recs.append(r)
    if recs:
        story.append(sec_bar("▌  RECOMENDACIONES CLÍNICAS (por escenario)"))
        story.append(Spacer(1, 2*mm))
        for r in recs:
            story.append(bullet(r))
        story.append(Spacer(1, 3*mm))

    # ── PLAN DE LABORATORIO ────────────────────────────────────────────────────
    story.append(sec_bar("▌  PLAN DE LABORATORIO Y MONITOREO"))
    story.append(Spacer(1, 1*mm))
    lab_rows = [
        [Paragraph('Frecuencia', E_TH_L), Paragraph('Parámetro', E_TH_L),
         Paragraph('Objetivo / acción', E_TH_L)],
        [Paragraph('Inicio', E_TD_B),
         Paragraph('Verificar circuito, flujos, acceso vascular', E_TD),
         Paragraph('Todo correcto antes de conectar', E_TD)],
    ]
    if anticoag == "HNF":
        lab_rows += [
            [Paragraph('c/ 4–6 h', E_TD_B),
             Paragraph('aPTT', E_TD),
             Paragraph('Meta 45–80 s; ajustar HNF según nomograma', E_TD)],
            [Paragraph('c/ 12 h', E_TD_B),
             Paragraph('Plaquetas + TP/INR', E_TD),
             Paragraph('Vigilar HIT (↓ plaquetas ≥50%)', E_TD)],
        ]
    else:
        lab_rows += [
            [Paragraph('c/ 4–6 h', E_TD_B),
             Paragraph('iCa post-filtro', E_TD),
             Paragraph('Meta 0.25–0.40 mmol/L; ajustar citrato', E_TD)],
            [Paragraph('c/ 4–6 h', E_TD_B),
             Paragraph('iCa sistémico', E_TD),
             Paragraph('Meta 1.0–1.2 mmol/L; ajustar Ca-gluconato', E_TD)],
            [Paragraph('c/ 12 h', E_TD_B),
             Paragraph('Ca total / iCa ratio', E_TD),
             Paragraph('>2.5 = acumulación de citrato → avisar médico', E_TD)],
        ]
    lab_rows += [
        [Paragraph('c/ 6–8 h', E_TD_B),
         Paragraph('Na, K, HCO₃⁻, Ca, Mg, Fósforo', E_TD),
         Paragraph('Ajustar composición de bolsas según resultado', E_TD)],
        [Paragraph('c/ 24 h', E_TD_B),
         Paragraph('BH, Creatinina, BUN, Urea', E_TD),
         Paragraph('Monitoreo de función y adecuación de TRRC', E_TD)],
    ]
    story.append(data_table(lab_rows, col_widths=[2.5*cm, 6*cm, 9*cm]))
    story.append(Spacer(1, 4*mm))

    # ── COMENTARIOS + FIRMA ────────────────────────────────────────────────────
    if coments and coments != "—":
        story.append(sec_bar("▌  COMENTARIOS CLÍNICOS"))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(coments, E_CUERPO))
        story.append(Spacer(1, 4*mm))

    firma_data = [[
        Paragraph(f"<b>{nom_med or 'Dr. / Dra. _______________'}</b>", E_FIRMA),
        Paragraph("Firma: ______________________", E_FIRMA),
        Paragraph(f"Sello: {sello or '____________'}", E_FIRMA),
    ]]
    firma_t = Table(firma_data, colWidths=[PAGE_W/3]*3)
    firma_t.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('LINEABOVE', (0,0), (-1,0), 0.5, GRIS2),
    ]))
    story.append(firma_t)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"RenalPro {VERSION} — Generado {ts} — Uso académico y de apoyo clínico exclusivo. "
        "No reemplaza el juicio clínico del médico tratante.", E_FOOT))

    # ══ PÁGINA 2: PROTOCOLO DE ENFERMERÍA ═════════════════════════════════════
    story.append(PageBreak())

    enf_hdr = Table([[
        Paragraph("<b>RenalPro — PROTOCOLO DE ENFERMERÍA</b>", E_TITULO),
        Paragraph(f"{ts}", E_FECHA),
    ]], colWidths=[PAGE_W*0.7, PAGE_W*0.3])
    enf_hdr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), AZUL),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(enf_hdr)
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph(
        f"Paciente: {nom_pac or '—'} · Expediente: {expte or '—'} · "
        f"Anticoagulación: {'HNF (Heparina No Fraccionada)' if anticoag=='HNF' else 'RCA — Citrato Regional'} · "
        f"Unidad: {unidad or '—'}", E_CUERPO))
    story.append(Spacer(1, 3*mm))

    if anticoag == "HNF":
        # ── PROTOCOLO HNF ─────────────────────────────────────────────────────
        story.append(sec_bar("▌  PRE-INICIO — LISTA DE VERIFICACIÓN"))
        story.append(Spacer(1, 2*mm))
        for txt in [
            "Verificar catéter: aspirar y refluir ambos lúmenes libremente (flujo ≥150 mL/min)",
            f"Preparar HNF: {_s_int(hnf_ui_h)} UI/hr en infusor (según dosis prescrita)",
            "Confirmar flujos programados en la máquina con el médico tratante",
            "Verificar que el circuito esté correctamente purgado (sin burbujas)",
            "Confirmar disponibilidad de bolsas de solución de reemplazo (pedir a farmacia)",
        ]:
            story.append(bullet(txt))
        story.append(Spacer(1, 3*mm))

        story.append(sec_bar("▌  DURANTE LA SESIÓN — MONITOREO HORARIO"))
        story.append(Spacer(1, 2*mm))
        mon_rows = [
            [Paragraph('Frecuencia', E_TH), Paragraph('Qué registrar', E_TH),
             Paragraph('Valor objetivo / acción', E_TH)],
            [Paragraph('Cada hora', E_TD_B),
             Paragraph('Qb, Qe, UF, presiones del circuito, temperatura del paciente', E_TD),
             Paragraph('Registrar en hoja de TRRC. Avisar si P acceso < −250 o P retorno >250 mmHg', E_TD)],
            [Paragraph('c/ 4–6 h', E_TD_B),
             Paragraph('aPTT', E_TD),
             Paragraph('Meta 45–80 s. Si <45: ↑ HNF. Si >100: ↓ HNF o pausar. AVISAR MÉDICO', E_TD)],
            [Paragraph('c/ 12 h', E_TD_B),
             Paragraph('Plaquetas', E_TD),
             Paragraph('Si bajan ≥50% del basal: SOSPECHAR HIT. SUSPENDER HNF. AVISAR MÉDICO URGENTE', E_TD)],
            [Paragraph('c/ 6–8 h', E_TD_B),
             Paragraph('Na, K, HCO₃⁻, Ca, Mg, Fósforo', E_TD),
             Paragraph('Ajustar composición de bolsas según indicación médica', E_TD)],
            [Paragraph('c/ hora', E_TD_B),
             Paragraph('Balance de líquidos', E_TD),
             Paragraph('Registrar entradas y salidas. Avisar si hay discrepancia >200 mL/h', E_TD)],
        ]
        story.append(data_table(mon_rows, col_widths=[2.5*cm, 6.5*cm, 8.5*cm]))
        story.append(Spacer(1, 3*mm))

        story.append(sec_bar("▌  ALERTAS — LLAMAR AL MÉDICO DE INMEDIATO"))
        story.append(Spacer(1, 2*mm))
        alertas = [
            ("FF >25%", "Reducir UF o Qr_post, aumentar predilución (Qr_pre). Avisar médico."),
            ("Presión transmembrana ↑ sostenida", "Revisar coagulación del circuito. Evaluar cambio de filtro."),
            ("aPTT <45 s", "↑ HNF según protocolo. Revisar acceso vascular."),
            ("aPTT >100 s", "↓ HNF o suspender temporalmente. Vigilar sangrado activo."),
            ("Plaquetas ↓ ≥50% del basal", "Sospechar HIT. SUSPENDER HNF inmediatamente. Avisar médico URGENTE."),
            ("Pérdida del circuito (coágulo)", "Documentar hora. Avisar médico. Preparar nuevo circuito."),
            ("PAM <65 mmHg o ↑ vasopresores", "Reducir UF. Avisar médico antes de continuar."),
        ]
        for alerta, accion in alertas:
            row = [[
                Paragraph(f"⚠ {alerta}", E_ENF_CRIT),
                Paragraph(accion, E_TD),
            ]]
            t = Table(row, colWidths=[5*cm, 12.5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,0), ROJO_CLR),
                ('BACKGROUND', (1,0), (1,0), GRIS),
                ('GRID', (0,0), (-1,-1), 0.5, GRIS2),
                ('LEFTPADDING', (0,0), (-1,-1), 7),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t)

    else:
        # ── PROTOCOLO CITRATO RCA ──────────────────────────────────────────────
        story.append(Paragraph(
            "⚠ IMPORTANTE: Con Citrato RCA, el calcio SIEMPRE va por línea post-filtro SISTÉMICA. "
            "NUNCA mezclar citrato y calcio en la misma línea (precipitación = pérdida del circuito).",
            ParagraphStyle('crit', parent=styles['Normal'], fontSize=10,
                textColor=ROJO, fontName='Helvetica-Bold', leading=14,
                borderColor=ROJO, borderWidth=1, borderPadding=8,
                backColor=ROJO_CLR)))
        story.append(Spacer(1, 3*mm))

        story.append(sec_bar("▌  PRE-INICIO — LISTA DE VERIFICACIÓN"))
        story.append(Spacer(1, 2*mm))
        for txt in [
            "Identificar y etiquetar las DOS líneas: CITRATO (rojo/pre-filtro) y CALCIO (azul/post-filtro sistémica)",
            f"Preparar citrato trisódico 4% a {_s_int(cit_ml_h)} mL/h (según prescripción)",
            f"Preparar Ca-gluconato aforado a {_s_int(ca_ml_h)} mL/h (según prescripción del médico)",
            "NUNCA conectar calcio en la misma línea que el citrato — riesgo de precipitación",
            "Confirmar flujos en máquina con médico. Verificar que no hay contraindicaciones (insuficiencia hepática severa, lactato >5)",
            "Tener disponible Ca-gluconato IV para bolo de emergencia (hipocalcemia sintomática)",
        ]:
            story.append(bullet(txt))
        story.append(Spacer(1, 3*mm))

        story.append(sec_bar("▌  DURANTE LA SESIÓN — MONITOREO DE iCa"))
        story.append(Spacer(1, 2*mm))
        mon_rows_rca = [
            [Paragraph('Frecuencia', E_TH), Paragraph('Qué medir', E_TH),
             Paragraph('Meta', E_TH), Paragraph('Si fuera de rango → acción', E_TH)],
            [Paragraph('c/ 4–6 h', E_TD_B),
             Paragraph('iCa POST-filtro', E_TD),
             Paragraph('0.25–0.40 mmol/L', E_TD_B),
             Paragraph('Si >0.40: ↑ citrato 10–20%. Si <0.25: ↓ citrato 10–20%. AVISAR MÉDICO', E_TD)],
            [Paragraph('c/ 4–6 h', E_TD_B),
             Paragraph('iCa SISTÉMICO', E_TD),
             Paragraph('1.0–1.2 mmol/L', E_TD_B),
             Paragraph('Si <1.0: ↑ calcio 10–20%. Si >1.2: ↓ calcio 10–20%. AVISAR MÉDICO', E_TD)],
            [Paragraph('c/ 12 h', E_TD_B),
             Paragraph('Ca total / iCa sistémico (ratio)', E_TD),
             Paragraph('<2.5', E_TD_B),
             Paragraph('Si >2.5: ACUMULACIÓN de citrato. AVISAR MÉDICO. Considerar cambio a HNF', E_TD)],
            [Paragraph('c/ 12 h', E_TD_B),
             Paragraph('pH / HCO₃⁻ / lactato', E_TD),
             Paragraph('pH 7.35–7.45', E_TD_B),
             Paragraph('Alcalosis sin causa aparente = posible acumulación de citrato', E_TD)],
            [Paragraph('c/ 6–8 h', E_TD_B),
             Paragraph('Na, K, Mg, Fósforo', E_TD),
             Paragraph('Rangos normales', E_TD_B),
             Paragraph('Ajustar composición de bolsas según indicación médica', E_TD)],
        ]
        story.append(data_table(mon_rows_rca, col_widths=[2.2*cm, 3.8*cm, 2.8*cm, 8.7*cm]))
        story.append(Spacer(1, 3*mm))

        story.append(sec_bar("▌  ALERTAS CITRATO — LLAMAR AL MÉDICO DE INMEDIATO"))
        story.append(Spacer(1, 2*mm))
        alertas_rca = [
            ("iCa post-filtro <0.25", "Riesgo de coagulación del filtro. ↓ citrato. AVISAR MÉDICO."),
            ("iCa post-filtro >0.45", "Anticoagulación insuficiente. ↑ citrato. AVISAR MÉDICO."),
            ("iCa sistémico <0.9 mmol/L", "Hipocalcemia significativa. Ca-gluconato bolo IV. AVISAR MÉDICO URGENTE."),
            ("Parestesias periorales / calambres", "Hipocalcemia sintomática. Detener sesión si grave. Ca IV bolo. AVISAR."),
            ("Ca total/iCa >2.5", "Acumulación de citrato (¿insuficiencia hepática?). AVISAR MÉDICO."),
            ("Alcalosis metabólica inexplicable", "Posible acumulación de citrato. AVISAR MÉDICO."),
            ("FF >25%", "Reducir UF o reajustar flujos. Riesgo de coagulación del filtro."),
        ]
        for alerta, accion in alertas_rca:
            row = [[
                Paragraph(f"⚠ {alerta}", E_ENF_CRIT),
                Paragraph(accion, E_TD),
            ]]
            t = Table(row, colWidths=[5.5*cm, 12*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,0), ROJO_CLR),
                ('BACKGROUND', (1,0), (1,0), GRIS),
                ('GRID', (0,0), (-1,-1), 0.5, GRIS2),
                ('LEFTPADDING', (0,0), (-1,-1), 7),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t)

    story.append(Spacer(1, 4*mm))
    # ── FIN DE SESIÓN (común a ambos) ─────────────────────────────────────────
    story.append(sec_bar("▌  FIN DE SESIÓN"))
    story.append(Spacer(1, 2*mm))
    fin_items = [
        "Documentar hora de fin, volumen total tratado y balance final",
        f"Sellar catéter: {('Heparina 1,000 UI/mL en cada lumen (volumen del lumen + 0.1 mL)' if anticoag == 'HNF' else 'Heparina 1,000 UI/mL; CitraLock 46.7% solo si disfunción previa')}",
        "Suspender infusiones simultáneamente (citrato y calcio al mismo tiempo si RCA)" if anticoag == "RCA" else "Suspender infusión de HNF al final de la sesión",
        "Registrar en expediente: indicación, parámetros, dosis, balance, tolerancia",
        "Notificar al médico tratante el resultado de la sesión",
    ]
    for item in fin_items:
        story.append(bullet(item))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Este protocolo es una guía de referencia. Siempre seguir indicaciones específicas del médico tratante "
        "y protocolos institucionales vigentes. Ante cualquier duda: AVISAR AL MÉDICO.", E_FOOT))

    # ══ PÁGINA 3: FUNDAMENTO + REFERENCIAS ════════════════════════════════════
    story.append(PageBreak())
    story.append(sec_bar(f"▌  FUNDAMENTO Y CÁLCULOS — RenalPro {VERSION}"))
    story.append(Spacer(1, 3*mm))

    for linea in _fundamento_texto_resumen(qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt):
        story.append(Paragraph(linea, E_CUERPO))
        story.append(Spacer(1, 1*mm))

    if pdf_ext:
        story.append(Spacer(1, 3*mm))
        vasopresor_alto = s.get("vaso_alto_sel", "No") == "Sí"
        lactato_desc    = s.get("lactato_desc_sel", "No") == "Sí"
        albumina        = float(s.get("alb_main", 3.0))
        for linea in _fundamento_texto_extendido(na, k, ph, float(s.get("pam", 65.0)),
                                                 vasopresor_alto, lactato_desc, albumina,
                                                 anticoag, r_targets, filtro_final):
            story.append(Paragraph(linea, E_CUERPO))
            story.append(Spacer(1, 1*mm))

    refs_pdf = filtrar_refs_por_contexto(escenarios, anticoag)
    if refs_pdf:
        story.append(Spacer(1, 4*mm))
        story.append(sec_bar("▌  REFERENCIAS"))
        story.append(Spacer(1, 2*mm))
        for idx, r in enumerate(refs_pdf, 1):
            story.append(Paragraph(
                f"[{idx}] {r['title']} — {r['where']} ({r['yr']})",
                ParagraphStyle('ref', parent=styles['Normal'], fontSize=8,
                    leading=11, textColor=NEGRO, leftIndent=12, spaceBefore=2)))
            if r.get("url"):
                story.append(Paragraph(f"     {r['url']}",
                    ParagraphStyle('refurl', parent=styles['Normal'], fontSize=7,
                        leading=10, textColor=rl_colors.HexColor('#2563EB'), leftIndent=20)))

    # ── BUILD ──────────────────────────────────────────────────────────────────
    doc.build(story)
    buf.seek(0)
    return buf



# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 60%, #3B82F6 100%);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 24px rgba(37,99,235,0.22);
">
    <div style="
        background: rgba(255,255,255,0.18);
        border: 2px solid rgba(255,255,255,0.35);
        border-radius: 14px;
        padding: 10px 18px;
        text-align: center;
        min-width: 90px;
    ">
        <div style="font-size:26px; font-weight:900; color:#FFFFFF; letter-spacing:-1px; line-height:1;">
            RenalPro
        </div>
        <div style="font-size:9px; color:rgba(255,255,255,0.75); font-weight:600; letter-spacing:0.08em; margin-top:2px;">
            NEFROLOGÍA
        </div>
    </div>
    <div style="flex:1;">
        <div style="font-size:20px; font-weight:800; color:#FFFFFF; letter-spacing:-0.3px; line-height:1.1;">
            Plataforma Clínica de Nefrología
        </div>
        <div style="font-size:12px; color:rgba(255,255,255,0.75); margin-top:4px; font-weight:500;">
            TRRC · Nefrología · Trasplante · Guardia
        </div>
        <div style="font-size:10px; color:rgba(255,255,255,0.50); margin-top:3px;">
            Dr. Josué Tapia · León, Gto. · {VERSION} · Uso académico
        </div>
    </div>
    <div style="text-align:right;">
        <div style="
            background:rgba(255,255,255,0.15);
            border:1px solid rgba(255,255,255,0.3);
            border-radius:8px;
            padding:6px 12px;
            font-size:11px;
            color:rgba(255,255,255,0.85);
            font-weight:600;
        ">🩺 Medicina Crítica</div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.button("🔁 Actualizar", help="Borrar caché y recargar", key="btn_refresh"):
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass
    st.rerun()

# Banner de estado
_status_banner()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Modo")
    doc_mode = st.checkbox("🎓 Modo docente", value=st.session_state.get("doc_mode", False),
                           key="doc_mode", help="Activa explicación extendida en UI y PDF.")
    st.session_state["pdf_extendido"] = bool(doc_mode)
    st.session_state["mostrar_fund_extendido"] = bool(doc_mode)

    # ── NAVEGACIÓN ────────────────────────────────────────────────────────────
    st.markdown("---")
    if "nav_sel" not in st.session_state:
        st.session_state["nav_sel"] = "presc"

    def _navbtn(label, key, icon=""):
        active = st.session_state["nav_sel"] == key
        prefix = "▶ " if active else "   "
        if st.button(f"{prefix}{label}", key=f"nav_{key}", use_container_width=True):
            st.session_state["nav_sel"] = key
            st.rerun()

    def _navsec(title):
        st.markdown(f"""<div style="color:#93C5FD;font-size:10px;font-weight:700;
            letter-spacing:.08em;padding:8px 4px 2px;opacity:0.85;">── {title} ──</div>""",
            unsafe_allow_html=True)

    _navsec("TRRC / CRRT")
    _navbtn("🩺 Prescripción", "presc")
    _navbtn("🧪 Citrato RCA", "cit")
    _navbtn("🧂 Sodio en TRRC", "na")
    _navbtn("⚗️ Electrolitos & Bolsas", "electrolitos")
    _navbtn("📐 Kt/V por objetivos", "ktv")
    _navbtn("⚖️ Balance dinámico", "bal")
    _navbtn("🔧 Complicaciones TRRC", "complic")

    _navsec("OTRAS TERAPIAS")
    _navbtn("💉 Predicción HD + KoA", "hd")
    _navbtn("🔄 Plasmaféresis / TPE", "tpe")

    _navsec("EVALUACIÓN")
    _navbtn("📊 Scores / Candidatura", "scores")
    _navbtn("💊 Anticoagulación", "anticoag")
    _navbtn("👩‍⚕️ Protocolo Enfermería", "enfermeria")

    _navsec("GUARDIA")
    _navbtn("⚡ Hiperkalemia", "hiperkalemia")
    _navbtn("💧 Hiponatremia", "hiponatremia")
    _navbtn("💊 Diuréticos", "diureticos")
    _navbtn("🔬 AKI por Contraste", "contraste")

    _navsec("NEFROLOGÍA")
    _navbtn("🔢 Calculadoras Nefro", "nefro")
    _navbtn("💉 Trasplante", "trasplante")
    _navbtn("🧬 Inmunología Tx", "inmuno_tx")
    _navbtn("⏱️ Función Retardada (DGF)", "dgf")
    _navbtn("🦠 Infecciones Tx", "infecciones_tx")
    _navbtn("🔵 Glomerulopatías", "glomerulopatias")
    _navbtn("🩸 Acceso Vascular", "acceso")

    _navsec("DOCUMENTACIÓN")
    _navbtn("📋 Resumen / PDF", "resumen")
    _navbtn("📂 Mis Pacientes", "pacientes")
    _navbtn("🏥 Expediente Clínico", "expediente")
    _navbtn("🔴 Nota Post-Trasplante", "nota_tx")
    _navbtn("📄 Receta Médica", "receta")
    _navbtn("📚 Fundamento", "fund")
    _navbtn("📖 Referencias", "refs")

    _navsec("CUENTA")
    _navbtn("👤 Mi Cuenta", "micuenta")
    _navbtn("💳 Premium", "premium")
    _navbtn("🛡️ Admin" if _rol() == "admin" else "👤 Mi Cuenta", "admin")

    st.markdown("---")
    if st.button("🚪 Cerrar sesión", key="btn_logout", use_container_width=True):
        for k in ["logged_in", "sess_user", "sess_rol", "sess_nombre", "consent_ok", "nav_sel"]:
            st.session_state.pop(k, None)
        st.rerun()

# ─── NAVEGACIÓN: variable de control ──────────────────────────────────────────
nav = st.session_state.get("nav_sel", "presc")

# ── Variables globales TRRC — leídas de session_state (definidas en módulo Prescripción) ──
# Todos los módulos que usen estos valores los toman de aquí
peso      = float(st.session_state.get("sb_peso", 70.0))
hto       = float(st.session_state.get("sb_hto", 0.30))
qb        = int(st.session_state.get("sb_qb", 200))
uf        = int(st.session_state.get("sb_uf", 100))
dosis_mlkg = int(st.session_state.get("sb_dosis", 30))
escenarios = list(st.session_state.get("sb_escenarios", ["Sepsis / choque séptico"]))



# ══════════════════════════════════════════════════════════════════════════════
# TAB: SCORES / CANDIDATURA TRRC
# Refs: SOFA (Sepsis-3, 2016), APACHE II, KDIGO 2026 AKI (borrador público)
#       STARRT-AKI 2020, AKIKI 2016, AKIKI-2 2021
# ══════════════════════════════════════════════════════════════════════════════
if nav == "scores":
    st.subheader("📊 Scores de Severidad y Candidatura a TRRC")
    st.info("💡 Los scores de mortalidad (SOFA, APACHE II) son **pronósticos**, "
            "no contraindicaciones al TRRC. Un score alto indica enfermedad crítica "
            "severa que **justifica** el soporte renal continuo.")

    modo_score = st.radio("Calculadora", ["SOFA", "APACHE II", "AKI — KDIGO 2026",
                                          "🏥 Candidatura a TRRC"], horizontal=True,
                          key="modo_score")

    # ── SOFA ──────────────────────────────────────────────────────────────────
    if modo_score == "SOFA":
        st.markdown("### SOFA Score — Sequential Organ Failure Assessment")
        st.caption("Sepsis-3 (Singer et al., JAMA 2016). Evalúa 6 sistemas. Score 0–24.")

        st.markdown("#### Sistema Respiratorio")
        sc_r1, sc_r2 = st.columns(2)
        with sc_r1:
            resp_mode = st.radio("Método", ["PaO₂/FiO₂", "SpO₂/FiO₂ (sin gases)"],
                                 horizontal=True, key="sofa_resp_mode")
        with sc_r2:
            if resp_mode == "PaO₂/FiO₂":
                pafi = st.number_input("PaO₂/FiO₂ (mmHg)", 0.0, 600.0, 400.0, 10.0, key="sofa_pafi")
                if pafi >= 400: resp_score = 0
                elif pafi >= 300: resp_score = 1
                elif pafi >= 200: resp_score = 2
                elif pafi >= 100: resp_score = 3
                else: resp_score = 4
            else:
                spafi = st.number_input("SpO₂/FiO₂", 0.0, 600.0, 315.0, 5.0, key="sofa_spafi")
                if spafi >= 315: resp_score = 0
                elif spafi >= 235: resp_score = 1
                elif spafi >= 148: resp_score = 2
                elif spafi >= 67: resp_score = 3
                else: resp_score = 4
        st.metric("Puntos respiratorio", resp_score)

        st.markdown("#### Coagulación · Hígado · Cardiovascular · SNC")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            plaq_sofa = st.number_input("Plaquetas (×10³/µL)", 0.0, 800.0, 200.0, 10.0, key="sofa_plaq")
            if plaq_sofa >= 150: coag_score = 0
            elif plaq_sofa >= 100: coag_score = 1
            elif plaq_sofa >= 50: coag_score = 2
            elif plaq_sofa >= 20: coag_score = 3
            else: coag_score = 4
            st.metric("Coagulación", coag_score)
        with col_s2:
            bili_sofa = st.number_input("Bilirrubina (mg/dL)", 0.0, 30.0, 1.0, 0.1, key="sofa_bili")
            if bili_sofa < 1.2: liver_score = 0
            elif bili_sofa < 2.0: liver_score = 1
            elif bili_sofa < 6.0: liver_score = 2
            elif bili_sofa < 12.0: liver_score = 3
            else: liver_score = 4
            st.metric("Hígado", liver_score)
        with col_s3:
            map_sofa = st.number_input("PAM (mmHg)", 0.0, 150.0,
                                       float(st.session_state.get("pam", 65.0)), 1.0, key="sofa_map")
            vaso_sofa = st.selectbox("Vasopresores",
                ["Ninguno", "Dopamina ≤5 o Dobutamina",
                 "Dopamina >5 o NE/Epi ≤0.1 µg/kg/min",
                 "Dopamina >15 o NE/Epi >0.1 µg/kg/min"], key="sofa_vaso")
            if "Ninguno" in vaso_sofa:
                cv_score = 0 if map_sofa >= 70 else 1
            elif "≤5" in vaso_sofa: cv_score = 2
            elif "NE/Epi ≤0.1" in vaso_sofa: cv_score = 3
            else: cv_score = 4
            st.metric("Cardiovascular", cv_score)
        with col_s4:
            gcs_sofa = st.number_input("GCS", 3, 15, 15, 1, key="sofa_gcs")
            if gcs_sofa == 15: cns_score = 0
            elif gcs_sofa >= 13: cns_score = 1
            elif gcs_sofa >= 10: cns_score = 2
            elif gcs_sofa >= 6: cns_score = 3
            else: cns_score = 4
            st.metric("SNC", cns_score)

        st.markdown("#### Sistema Renal")
        cr_sofa_c1, cr_sofa_c2, cr_sofa_c3 = st.columns(3)
        with cr_sofa_c1:
            cr_sofa = st.number_input("Creatinina (mg/dL)", 0.0, 20.0,
                                      1.0, 0.1, key="sofa_cr")
        with cr_sofa_c2:
            uo_sofa = st.number_input("Diuresis 24h (mL)", 0, 5000,
                                      int(st.session_state.get("ur_main", 800)), 50, key="sofa_uo")
        with cr_sofa_c3:
            if cr_sofa < 1.2 and uo_sofa >= 500: renal_score = 0
            elif cr_sofa < 2.0: renal_score = 1
            elif cr_sofa < 3.5: renal_score = 2
            elif cr_sofa < 5.0 or uo_sofa < 500: renal_score = 3
            else: renal_score = 4
            st.metric("Renal", renal_score)

        sofa_total = resp_score + coag_score + liver_score + cv_score + cns_score + renal_score
        if sofa_total <= 6: sofa_mort = "<10%"; sofa_color = "✅"
        elif sofa_total <= 9: sofa_mort = "15–20%"; sofa_color = "🟡"
        elif sofa_total <= 12: sofa_mort = "40–50%"; sofa_color = "🟠"
        elif sofa_total <= 14: sofa_mort = "50–60%"; sofa_color = "🔴"
        elif sofa_total == 15: sofa_mort = ">80%"; sofa_color = "🔴"
        else: sofa_mort = ">90%"; sofa_color = "🔴"

        st.divider()
        sr1, sr2, sr3 = st.columns(3)
        sr1.metric("SOFA TOTAL", sofa_total, help="Máximo 24 puntos")
        sr2.metric("Mortalidad predicha UCI", sofa_mort)
        sr3.metric("Interpretación", sofa_color + (" Crítico" if sofa_total > 9 else " Severo" if sofa_total > 6 else " Moderado"))

        if sofa_total >= 2: st.error(f"🔴 SOFA ≥2: criterio diagnóstico de **SEPSIS** si hay infección sospechada.")
        if renal_score >= 2:
            st.warning(f"⚠️ SOFA renal {renal_score}/4 — AKI significativa. "
                       f"SOFA total {sofa_total} **justifica TRRC**, no lo contraindica.")
        st.session_state["sofa_total"] = sofa_total

    # ── APACHE II ─────────────────────────────────────────────────────────────
    elif modo_score == "APACHE II":
        st.markdown("### APACHE II — Acute Physiology and Chronic Health Evaluation II")
        st.caption("Knaus et al., Crit Care Med 1985. Predice mortalidad hospitalaria. Score 0–71.")

        st.markdown("#### Variables fisiológicas agudas")
        ap1, ap2, ap3, ap4 = st.columns(4)
        with ap1:
            temp_ap = st.number_input("Temperatura rectal (°C)", 30.0, 42.0, 37.0, 0.1, key="ap_temp")
            if temp_ap >= 41 or temp_ap < 30: t_s = 4
            elif temp_ap >= 39 or (temp_ap < 32 and temp_ap >= 30): t_s = 3
            elif temp_ap >= 38.5 or (temp_ap < 34 and temp_ap >= 32): t_s = 1 if temp_ap >= 38.5 else 2
            elif temp_ap >= 36: t_s = 0
            else: t_s = 2
            # Simplified lookup
            if temp_ap >= 41: t_s = 4
            elif temp_ap >= 39: t_s = 3
            elif temp_ap >= 38.5: t_s = 1
            elif temp_ap >= 36: t_s = 0
            elif temp_ap >= 34: t_s = 1
            elif temp_ap >= 32: t_s = 2
            elif temp_ap >= 30: t_s = 3
            else: t_s = 4
            st.metric("Temperatura", t_s)

            map_ap = st.number_input("PAM (mmHg)", 0, 200,
                                     int(st.session_state.get("pam", 70)), 5, key="ap_map")
            if map_ap >= 160: map_s = 4
            elif map_ap >= 130: map_s = 3
            elif map_ap >= 110: map_s = 2
            elif map_ap >= 70: map_s = 0
            elif map_ap >= 50: map_s = 2
            else: map_s = 4
            st.metric("PAM", map_s)

        with ap2:
            fc_ap = st.number_input("FC (lpm)", 0, 250, 90, 5, key="ap_fc")
            if fc_ap >= 180: fc_s = 4
            elif fc_ap >= 140: fc_s = 3
            elif fc_ap >= 110: fc_s = 2
            elif fc_ap >= 70: fc_s = 0
            elif fc_ap >= 55: fc_s = 2
            elif fc_ap >= 40: fc_s = 3
            else: fc_s = 4
            st.metric("FC", fc_s)

            fr_ap = st.number_input("FR (rpm)", 0, 60, 16, 1, key="ap_fr")
            if fr_ap >= 50: fr_s = 4
            elif fr_ap >= 35: fr_s = 3
            elif fr_ap >= 25: fr_s = 1
            elif fr_ap >= 12: fr_s = 0
            elif fr_ap >= 10: fr_s = 1
            elif fr_ap >= 6: fr_s = 2
            else: fr_s = 4
            st.metric("FR", fr_s)

        with ap3:
            pafi_ap = st.number_input("PaO₂/FiO₂ (si FiO₂<0.5 → PaO₂ solo)", 0.0, 600.0, 350.0, 10.0, key="ap_pafi")
            fi_ap = st.number_input("FiO₂", 0.21, 1.0, 0.21, 0.01, key="ap_fio2")
            if fi_ap >= 0.5:
                # Use A-aDO2 approximation: A-aDO2 ≈ (FiO2*713 - PaCO2/0.8) - PaO2
                # Simplified: use PaO2/FiO2
                if pafi_ap >= 400: ox_s = 0
                elif pafi_ap >= 300: ox_s = 1
                elif pafi_ap >= 200: ox_s = 3
                else: ox_s = 4
            else:
                pao2 = pafi_ap  # treated as PaO2 when FiO2<0.5
                if pao2 >= 70: ox_s = 0
                elif pao2 >= 61: ox_s = 1
                elif pao2 >= 55: ox_s = 3
                else: ox_s = 4
            st.metric("Oxigenación", ox_s)

            ph_ap = st.number_input("pH arterial", 6.8, 7.7,
                                    float(st.session_state.get("ph_main", 7.40)), 0.01, key="ap_ph")
            if ph_ap >= 7.7: ph_s = 4
            elif ph_ap >= 7.6: ph_s = 3
            elif ph_ap >= 7.5: ph_s = 1
            elif ph_ap >= 7.33: ph_s = 0
            elif ph_ap >= 7.25: ph_s = 2
            elif ph_ap >= 7.15: ph_s = 3
            else: ph_s = 4
            st.metric("pH", ph_s)

        with ap4:
            na_ap = st.number_input("Na sérico (mEq/L)", 100, 200,
                                    int(st.session_state.get("na_main", 140)), 1, key="ap_na")
            if na_ap >= 180: na_s = 4
            elif na_ap >= 160: na_s = 3
            elif na_ap >= 155: na_s = 2
            elif na_ap >= 150: na_s = 1
            elif na_ap >= 130: na_s = 0
            elif na_ap >= 120: na_s = 2
            elif na_ap >= 111: na_s = 3
            else: na_s = 4
            st.metric("Na", na_s)

            k_ap = st.number_input("K sérico (mEq/L)", 1.0, 10.0,
                                   float(st.session_state.get("k_main", 4.0)), 0.1, key="ap_k")
            if k_ap >= 7.0: k_s = 4
            elif k_ap >= 6.0: k_s = 3
            elif k_ap >= 5.5: k_s = 1
            elif k_ap >= 3.5: k_s = 0
            elif k_ap >= 3.0: k_s = 1
            elif k_ap >= 2.5: k_s = 2
            else: k_s = 4
            st.metric("K", k_s)

        st.markdown("#### Creatinina · Hematocrito · Leucocitos · GCS")
        ap5, ap6, ap7, ap8 = st.columns(4)
        with ap5:
            cr_ap = st.number_input("Creatinina (mg/dL)", 0.0, 20.0, 1.0, 0.1, key="ap_cr")
            falla_renal_ap = st.checkbox("¿AKI agudo? (duplica puntaje Cr)", key="ap_aki")
            if cr_ap >= 3.5: cr_s = 4
            elif cr_ap >= 2.0: cr_s = 3
            elif cr_ap >= 1.5: cr_s = 2
            elif cr_ap >= 0.6: cr_s = 0
            else: cr_s = 2
            if falla_renal_ap: cr_s = min(4, cr_s * 2)
            st.metric("Creatinina", cr_s)
        with ap6:
            hto_ap = st.number_input("Hematocrito (%)", 0.0, 60.0,
                                     float(st.session_state.get("sb_hto", 0.30)) * 100, 1.0, key="ap_hto")
            if hto_ap >= 60: hto_s = 4
            elif hto_ap >= 50: hto_s = 2
            elif hto_ap >= 46: hto_s = 1
            elif hto_ap >= 30: hto_s = 0
            elif hto_ap >= 20: hto_s = 2
            else: hto_s = 4
            st.metric("Hematocrito", hto_s)
        with ap7:
            wbc_ap = st.number_input("Leucocitos (×10³/mm³)", 0.0, 60.0, 10.0, 0.5, key="ap_wbc")
            if wbc_ap >= 40: wbc_s = 4
            elif wbc_ap >= 20: wbc_s = 2
            elif wbc_ap >= 15: wbc_s = 1
            elif wbc_ap >= 3: wbc_s = 0
            elif wbc_ap >= 1: wbc_s = 2
            else: wbc_s = 4
            st.metric("Leucocitos", wbc_s)
        with ap8:
            gcs_ap = st.number_input("GCS", 3, 15, 15, 1, key="ap_gcs")
            gcs_s = 15 - gcs_ap
            st.metric("GCS (15 − GCS)", gcs_s)

        aps = t_s + map_s + fc_s + fr_s + ox_s + ph_s + na_s + k_s + cr_s + hto_s + wbc_s + gcs_s

        st.markdown("#### Edad y salud crónica")
        age_ap_c1, age_ap_c2 = st.columns(2)
        with age_ap_c1:
            age_ap = st.number_input("Edad (años)", 0, 110, 60, 1, key="ap_age")
            if age_ap < 45: age_s = 0
            elif age_ap < 55: age_s = 2
            elif age_ap < 65: age_s = 3
            elif age_ap < 75: age_s = 5
            else: age_s = 6
            st.metric("Puntos por edad", age_s)
        with age_ap_c2:
            cronica_ap = st.selectbox("Enfermedad crónica severa",
                ["Ninguna", "Cirugía electiva con enfermedad crónica",
                 "No quirúrgico o cirugía de urgencia con enfermedad crónica"],
                key="ap_cronica")
            if "urgencia" in cronica_ap or "No quirúrgico" in cronica_ap: ch_s = 5
            elif "electiva" in cronica_ap: ch_s = 2
            else: ch_s = 0
            st.metric("Puntos salud crónica", ch_s)

        apache2_total = aps + age_s + ch_s

        # Predicted mortality (simplified Knaus table)
        if apache2_total <= 4: ap_mort = "4%"
        elif apache2_total <= 9: ap_mort = "8%"
        elif apache2_total <= 14: ap_mort = "15%"
        elif apache2_total <= 19: ap_mort = "25%"
        elif apache2_total <= 24: ap_mort = "40%"
        elif apache2_total <= 29: ap_mort = "55%"
        elif apache2_total <= 34: ap_mort = "73%"
        else: ap_mort = "85%"

        st.divider()
        ar1, ar2, ar3 = st.columns(3)
        ar1.metric("APS (fisiológico)", aps)
        ar2.metric("APACHE II TOTAL", apache2_total)
        ar3.metric("Mortalidad hospitalaria predicha", ap_mort)

        if apache2_total > 25:
            st.error(f"🔴 APACHE II {apache2_total} — Enfermedad crítica severa. "
                     "Este score **indica soporte orgánico agresivo**, incluido TRRC. "
                     "No es contraindicación.")
        elif apache2_total > 15:
            st.warning(f"🟠 APACHE II {apache2_total} — Enfermedad moderada-severa. "
                       "Evaluar indicaciones de TRRC.")
        else:
            st.info(f"ℹ️ APACHE II {apache2_total} — Documentar en expediente como contexto clínico.")
        st.session_state["apache2_total"] = apache2_total

    # ── KDIGO 2026 AKI STAGING ────────────────────────────────────────────────
    elif modo_score == "AKI — KDIGO 2026":
        st.markdown("### Estadificación AKI — KDIGO 2026")
        st.caption("KDIGO 2026 AKI & AKD Guideline (borrador revisión pública, marzo 2026). "
                   "Estadificación idéntica a KDIGO 2012, con biomarcadores actualizados.")

        st.markdown("#### Creatinina sérica")
        kd1, kd2, kd3 = st.columns(3)
        with kd1:
            cr_base = st.number_input("Creatinina basal (mg/dL)", 0.0, 15.0, 0.9, 0.05, key="kd_crbase",
                                      help="Previa estable o estimada por CKD-EPI inverso")
        with kd2:
            cr_act = st.number_input("Creatinina actual (mg/dL)", 0.0, 20.0, 1.5, 0.05, key="kd_cract")
        with kd3:
            cr_48h = st.number_input("Cr hace 48h (mg/dL, si disponible)", 0.0, 20.0, 0.0, 0.05,
                                     key="kd_cr48",
                                     help="Para detectar incremento ≥0.3 en 48h")

        st.markdown("#### Diuresis")
        kd4, kd5, kd6 = st.columns(3)
        with kd4:
            uo_h_kd = st.number_input("Diuresis más baja (mL/kg/hr)", 0.0, 3.0, 0.5, 0.05,
                                      key="kd_uo_h")
        with kd5:
            uo_dur = st.selectbox("Durante cuántas horas", ["<6h", "6–12h", "12–24h", "≥24h"],
                                  key="kd_uo_dur")
        with kd6:
            en_rrt = st.checkbox("¿Ya inició TRR (diálisis/TRRC)?", key="kd_rrt")

        # Calculate staging
        ratio_cr = cr_act / cr_base if cr_base > 0 else 0
        delta_48h = cr_act - cr_48h if cr_48h > 0 else 0

        aki_stage_cr = 0
        if en_rrt: aki_stage_cr = 3
        elif cr_act >= 4.0 and cr_act >= cr_base + 0.5: aki_stage_cr = 3
        elif ratio_cr >= 3.0: aki_stage_cr = 3
        elif ratio_cr >= 2.0: aki_stage_cr = 2
        elif ratio_cr >= 1.5 or delta_48h >= 0.3: aki_stage_cr = 1

        aki_stage_uo = 0
        if uo_h_kd < 0.3 and uo_dur in ["≥24h"]: aki_stage_uo = 3
        elif uo_h_kd < 0.3 and uo_dur == "12–24h": aki_stage_uo = 3
        elif uo_h_kd < 0.5 and uo_dur in ["12–24h", "≥24h"]: aki_stage_uo = 2
        elif uo_h_kd < 0.5 and uo_dur in ["6–12h"]: aki_stage_uo = 1
        elif uo_h_kd == 0 and uo_dur == "≥24h": aki_stage_uo = 3  # anuria

        aki_stage = max(aki_stage_cr, aki_stage_uo)

        st.divider()
        ks1, ks2, ks3 = st.columns(3)
        ks1.metric("Ratio Cr actual/basal", f"{ratio_cr:.2f}x")
        ks2.metric("Estadio por Cr", f"AKI {aki_stage_cr}" if aki_stage_cr > 0 else "Sin criterio")
        ks3.metric("Estadio por diuresis", f"AKI {aki_stage_uo}" if aki_stage_uo > 0 else "Sin criterio")

        if aki_stage == 0:
            st.success("✅ Sin criterios de AKI al momento. Monitoreo continuo.")
        elif aki_stage == 1:
            st.warning(f"🟡 **AKI Estadio 1** — Riesgo. Monitoreo estrecho, evitar nefrotóxicos, "
                       f"optimizar volemia. Evaluar TRR si hay indicación urgente.")
        elif aki_stage == 2:
            st.error(f"🔴 **AKI Estadio 2** — Daño. Evaluar TRRC. "
                     f"Iniciar si hay indicaciones de urgencia o hemodynamia inestable.")
        else:
            st.error(f"🔴 **AKI Estadio 3** — Falla renal. **Indicación formal de evaluar TRRC** "
                     f"(KDIGO 2026, Capítulo 5). Sin beneficio de inicio acelerado vs estándar "
                     f"(STARRT-AKI 2020). Individualizar timing según contexto clínico.")

        if en_rrt:
            st.info("ℹ️ El inicio de TRR clasifica automáticamente como AKI Estadio 3, "
                    "independientemente de la creatinina.")

        with st.expander("📚 Biomarcadores — KDIGO 2026"):
            st.markdown("""
| Biomarcador | Umbral de riesgo | Aplicación clínica |
|-------------|-----------------|-------------------|
| **TIMP-2 × IGFBP7** | ≥0.3 (alto riesgo), ≥2.0 (muy alto) | Predicción de AKI en UCI dentro de 12h |
| **NGAL urinario** | >150 ng/mL | Daño tubular temprano |
| **KIM-1** | Elevado | Daño tubular proximal |
| **Cistatina C** | Alternativa a Cr | Mejor en musculatura reducida, malnutrición, cirrosis |
| **L-FABP urinario** | Elevado | Daño tubular |

*KDIGO 2026 recomienda el uso de biomarcadores validados para estratificación de riesgo de AKI, especialmente en pacientes en UCI.*
            """)

        with st.expander("📊 Evidencia sobre timing de inicio de TRRC"):
            st.markdown("""
| Ensayo | Diseño | Resultado principal |
|--------|--------|---------------------|
| **AKIKI** (2016) | Precoz vs tardío, AKI3 | Sin diferencia en mortalidad a 60 días |
| **IDEAL-ICU** (2018) | Precoz vs diferido, sepsis+AKI | Detenido por futilidad. Sin beneficio precoz |
| **STARRT-AKI** (2020) | Acelerado vs estándar, 168 UCI, n=2927 | Mortalidad 90d: 43.9% vs 43.7% (p=0.92) |
| **AKIKI-2** (2021) | Dos estrategias diferidas | Sin diferencia. Mayor riesgo con espera prolongada |

**Conclusión KDIGO 2026:** No hay indicación de inicio acelerado universal.  
**Individualizar** según: indicaciones de urgencia, tendencia del AKI, contexto clínico, metas de atención.
            """)
        st.session_state["aki_stage"] = aki_stage

    # ── CANDIDATURA A TRRC ────────────────────────────────────────────────────
    else:
        st.markdown("### 🏥 Candidatura a TRRC — Evaluación integral")
        st.caption("Basado en KDIGO 2026, SCCM/ESICM guidelines. "
                   "Los scores de mortalidad son pronósticos, NO contraindicaciones.")

        st.markdown("#### ✅ Indicaciones de urgencia (AEIOU+)")
        ind1, ind2 = st.columns(2)
        with ind1:
            i_acidosis = st.checkbox("**A** — Acidosis: pH <7.15 refractaria", key="cand_acid")
            i_electro = st.checkbox("**E** — Electrolitos: K+ >6.5 o refractario >6.0", key="cand_elec")
            i_intox = st.checkbox("**I** — Intoxicación: tóxico dializable confirmado", key="cand_intox")
            i_overload = st.checkbox("**O** — Sobrecarga hídrica: >10% peso + compromiso respiratorio", key="cand_overload")
            i_uremia = st.checkbox("**U** — Uremia sintomática: encefalopatía, pericarditis, sangrado", key="cand_uremia")
        with ind2:
            i_aki3 = st.checkbox("AKI Estadio 3 (KDIGO)", key="cand_aki3",
                                 value=st.session_state.get("aki_stage", 0) >= 3)
            i_sepsis = st.checkbox("Sepsis + AKI Estadio 2–3 con SOFA ≥2", key="cand_sepsis")
            i_hemo = st.checkbox("Inestabilidad hemodinámica (intolerante a HD convencional)", key="cand_hemo")
            i_mods = st.checkbox("MODS (≥3 órganos en falla)", key="cand_mods")
            i_rabdo = st.checkbox("Rabdomiólisis severa (CK >5000) o mioglobinuria", key="cand_rabdo")
            i_hyperamm = st.checkbox("Hiperamonemia refractaria", key="cand_hyperamm")

        st.markdown("#### ⛔ Contraindicaciones reales (no scores de mortalidad)")
        contra1, contra2 = st.columns(2)
        with contra1:
            c_confort = st.checkbox("Decisión de cuidados de confort / limitación de esfuerzo", key="cand_confort")
            c_acceso = st.checkbox("Sin posibilidad de acceso vascular central", key="cand_acceso")
        with contra2:
            c_choque = st.checkbox("Choque irreversible sin vasopresores (muerte inminente)", key="cand_choque")
            c_coag_abs = st.checkbox("Coagulopatía refractaria absoluta (sin anticoagulación posible)",
                                     key="cand_coag")

        # Scoring
        indics = [i_acidosis, i_electro, i_intox, i_overload, i_uremia,
                  i_aki3, i_sepsis, i_hemo, i_mods, i_rabdo, i_hyperamm]
        contras = [c_confort, c_acceso, c_choque, c_coag_abs]
        n_indics = sum(indics)
        n_contras = sum(contras)

        # Scores from other tabs
        sofa_prev = st.session_state.get("sofa_total", None)
        apache_prev = st.session_state.get("apache2_total", None)
        aki_prev = st.session_state.get("aki_stage", None)

        st.divider()
        st.markdown("### 📋 Conclusión y argumento clínico")

        if n_contras > 0:
            contras_activas = []
            if c_confort: contras_activas.append("Decisión de cuidados de confort")
            if c_acceso: contras_activas.append("Sin acceso vascular posible")
            if c_choque: contras_activas.append("Choque irreversible inminente")
            if c_coag_abs: contras_activas.append("Coagulopatía refractaria absoluta")
            st.error(f"⛔ **TRRC no indicado en este momento** por: {', '.join(contras_activas)}. "
                     f"Re-evaluar si las condiciones cambian.")
        elif n_indics >= 2:
            st.success(f"✅ **TRRC INDICADO** — {n_indics} indicaciones presentes. "
                       f"Iniciar según disponibilidad y metas de atención.")
        elif n_indics == 1:
            st.warning(f"🟡 **TRRC a evaluar** — 1 indicación presente. "
                       f"Puede ser suficiente si hay deterioro progresivo. Decisión clínica individualizada.")
        else:
            st.info("ℹ️ Sin indicaciones formales activas al momento. Monitoreo continuo y reevaluación.")

        # Generate clinical text
        st.markdown("#### 📝 Texto para expediente")
        indics_texto = []
        if i_acidosis: indics_texto.append("acidosis metabólica refractaria (pH <7.15)")
        if i_electro: indics_texto.append("hipercalemia refractaria (K+ >6.0 mEq/L)")
        if i_intox: indics_texto.append("intoxicación con tóxico dializable")
        if i_overload: indics_texto.append("sobrecarga hídrica >10% con compromiso respiratorio")
        if i_uremia: indics_texto.append("uremia sintomática")
        if i_aki3: indics_texto.append("AKI Estadio 3 por criterios KDIGO 2026")
        if i_sepsis: indics_texto.append("sepsis con AKI Estadio 2–3 y SOFA ≥2")
        if i_hemo: indics_texto.append("inestabilidad hemodinámica (intolerante a HD convencional)")
        if i_mods: indics_texto.append("síndrome de disfunción multiorgánica (≥3 órganos)")
        if i_rabdo: indics_texto.append("rabdomiólisis severa con mioglobinuria")
        if i_hyperamm: indics_texto.append("hiperamonemia refractaria")

        sofa_txt = f"SOFA {sofa_prev}/24" if sofa_prev is not None else ""
        apache_txt = f"APACHE II {apache_prev}" if apache_prev is not None else ""
        aki_txt = f"AKI Estadio {aki_prev} (KDIGO 2026)" if aki_prev is not None else ""
        scores_txt = ", ".join(filter(None, [sofa_txt, apache_txt, aki_txt]))

        if indics_texto:
            texto_exp = (
                f"Paciente con enfermedad crítica severa ({scores_txt}). "
                f"Se indica inicio de Terapia de Reemplazo Renal Continua (TRRC) por las siguientes indicaciones: "
                f"{'; '.join(indics_texto)}. "
                f"Los scores de severidad documentados reflejan la gravedad de la disfunción orgánica "
                f"y constituyen indicación de soporte renal continuo, de acuerdo con KDIGO 2026 "
                f"(Capítulo 5: Kidney Replacement Therapy) y guías SCCM/ESICM. "
                f"Se planifica TRRC con modalidad, flujos y anticoagulación según prescripción adjunta. "
                f"Inicio individualizado; sin evidencia de beneficio del inicio acelerado vs estándar "
                f"(STARRT-AKI 2020, n=2927, mortalidad 90d 43.9 vs 43.7%, p=0.92)."
            )
        else:
            texto_exp = (
                f"Paciente con monitoreo renal activo ({scores_txt}). "
                f"Sin indicaciones formales de TRRC al momento de esta evaluación. "
                f"Se continuará vigilancia estrecha y se reevaluará candidatura ante cambios clínicos. "
                f"Criterios de inicio según KDIGO 2026."
            )
        st.text_area("Copiar al expediente:", value=texto_exp, height=180, key="texto_expediente")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: PRESCRIPCIÓN TRRC
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "presc":
    st.subheader("Prescripción TRRC — Recomendación combinada")

    # ── PARÁMETROS DEL PACIENTE ────────────────────────────────────────────────
    st.markdown("#### ⚙️ Parámetros globales")
    pg1, pg2, pg3, pg4, pg5 = st.columns(5)
    with pg1:
        peso = st.number_input("Peso (kg)", 10.0, 300.0,
                               float(st.session_state.get("sb_peso", 70.0)), 0.5, key="sb_peso")
    with pg2:
        hto = st.number_input("Hematocrito (fracción)", 0.10, 0.60,
                              float(st.session_state.get("sb_hto", 0.30)), 0.01,
                              format="%.2f", key="sb_hto")
    with pg3:
        qb = st.number_input("Qb (mL/min)", 80, 300,
                             int(st.session_state.get("sb_qb", 200)), 10, key="sb_qb")
    with pg4:
        uf = st.number_input("UF neta (mL/h)", 0, 2000,
                             int(st.session_state.get("sb_uf", 100)), 10, key="sb_uf")
    with pg5:
        dosis_mlkg = st.slider("Dosis objetivo (mL/kg/h)", 10, 45,
                               int(st.session_state.get("sb_dosis", 30)), key="sb_dosis")

    escenarios_catalogo = [
        "Sepsis / choque séptico", "Choque cardiogénico", "Post infarto",
        "Neurocrítico / TCE", "Sobrecarga hídrica aislada", "Intoxicación / sobredosis",
        "Hiponatremia severa", "Hipernatremia", "Hiperamonemia",
        "Rabdomiólisis", "Síndrome de liberación de citocinas",
    ]
    escenarios = st.multiselect("Escenarios clínicos (hasta 3)", escenarios_catalogo,
                                max_selections=3,
                                default=st.session_state.get("sb_escenarios", ["Sepsis / choque séptico"]),
                                key="sb_escenarios")
    st.divider()

    cP1, cP2, cP3 = st.columns(3)
    with cP1:
        pam = st.number_input("PAM (mmHg)", 30.0, 130.0, 65.0, 1.0, key="pam")
    with cP2:
        vasopresor_alto = st.selectbox("Vasopresor dosis altas", ["No", "Sí"], key="vaso_alto_sel")
        vasopresor_alto_bool = vasopresor_alto == "Sí"
    with cP3:
        lactato_desc = st.selectbox("Lactato en descenso", ["No", "Sí"], key="lactato_desc_sel")
        lactato_desc_bool = lactato_desc == "Sí"

    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    filtro_sugerido = sugerir_filtro_por_escenarios(escenarios)
    opciones_filtro = list(FILTROS.keys())
    idx_default = opciones_filtro.index(filtro_sugerido) if filtro_sugerido in opciones_filtro else 0

    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(
        qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_txt = f"{ff:.1%}" if ff is not None else "—"

    c1, c2, c3 = st.columns(3)
    c1.metric("Modalidad", mod_final or "—")
    c2.metric("Filtro sugerido", filtro_sugerido or "—")
    c3.metric("FF estimada", ff_txt)

    filtro_elegido = st.selectbox("Filtro (puedes cambiarlo)", opciones_filtro,
                                  index=idx_default, key="ui_filtro")

    st.markdown("### Laboratorios rápidos")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        na = st.number_input("Na (mEq/L)", 100.0, 200.0, 140.0, 0.5, key="na_main")
        k = st.number_input("K (mEq/L)", 1.0, 10.0, 4.0, 0.1, key="k_main")
    with col2:
        hco3 = st.number_input("HCO₃⁻ (mEq/L)", 5.0, 45.0, 20.0, 0.5, key="hco3_main")
        lactato = st.number_input("Lactato (mmol/L)", 0.0, 20.0, 2.0, 0.1, key="lac_main")
    with col3:
        amonio = st.number_input("Amonio (µmol/L)", 0.0, 1000.0, 80.0, 5.0, key="nh4_main")
        ck = st.number_input("CK (U/L)", 0.0, 100000.0, 200.0, 50.0, key="ck_main")
    with col4:
        ph = st.number_input("pH", 6.80, 7.80, 7.35, 0.01, format="%.2f", key="ph_main")
        uresis24 = st.number_input("Uresis 24h (mL)", 0, 20000, 800, 50, key="ur_main")
        albumina = st.number_input("Albúmina (g/dL)", 1.0, 5.5, 3.0, 0.1, key="alb_main")

    hit_bool = bool(st.session_state.get("hit_previa_bool", False))
    alertas_filtro = checar_contraindicaciones(filtro_elegido, albumina_gdl=albumina, hit=hit_bool)
    if "HCO" in filtro_elegido and albumina < 3.0:
        alertas_filtro.append(f"💡 HCO con Alb {albumina:.1f} g/dL: vigilar pérdidas proteicas.")
    if alertas_filtro:
        st.warning(" | ".join(alertas_filtro))

    st.markdown("### Flujos sugeridos")
    ca, cb, cc, cd = st.columns(4)
    ca.metric("Qb (mL/min)", qb)
    cb.metric("Qp (mL/min)", int(qp))
    cc.metric("Qe (mL/h)", int(qe))
    cd.metric("UF (mL/h)", uf)
    ce, cf, cg = st.columns(3)
    ce.metric("Qr PRE (mL/h)", qr_pre)
    cf.metric("Qr POST (mL/h)", qr_post)
    cg.metric("Qd (mL/h)", int(qd))

    st.info(comentarios or "—")
    st.caption("Dosis objetivo 20–25 mL/kg/h (KDIGO). FF <25% para proteger el filtro.")

    # ── Anticoagulación — selector directo en prescripción ────────────────────
    st.divider()
    st.markdown("### 💊 Anticoagulación")
    ac_sel_presc = st.radio(
        "Tipo de anticoagulación", 
        ["Heparina no fraccionada (HNF)", "Citrato Regional (RCA)"],
        horizontal=True, key="presc_ac_sel",
        help="La elección ajusta los flujos de prescripción y se refleja en Resumen/Impresión.")

    if "HNF" in ac_sel_presc:
        # ── HNF ──────────────────────────────────────────────────────────────
        st.session_state["anticoagulacion_tipo"] = "HNF"
        hnf_default = int(peso * 5)
        hnf_dose_presc = st.number_input(
            "Dosis inicial HNF (UI/hr)", 0, 5000, hnf_default, 50,
            key="presc_hnf_dose",
            help=f"Estimado: 5 UI/kg/hr × {peso:.0f} kg = {hnf_default} UI/hr. Ajustar a aPTT 45–70 s.")
        st.session_state["hnf_ui_h"] = float(hnf_dose_presc)
        st.success(f"**HNF: {hnf_dose_presc} UI/hr** en infusión continua — "
                   f"Ajustar según aPTT (objetivo 45–70 s o protocolo institucional). "
                   f"Monitoreo cada 4–6 hrs.")
        # No hay ajuste de QrPre con HNF
        ff_efectiva = ff
        qr_pre_efectivo = qr_pre

    else:
        # ── CITRATO RCA ───────────────────────────────────────────────────────
        st.session_state["anticoagulacion_tipo"] = "RCA"

        rca_c1, rca_c2, rca_c3 = st.columns(3)
        with rca_c1:
            cit_sol_presc = st.selectbox(
                "Solución de citrato",
                ["Citrato trisódico 4% (136 mmol/L)", "Prismocitrate (concentración configurable)"],
                key="presc_cit_sol_type")
            if "4%" in cit_sol_presc:
                cit_conc_presc = 136.0
                na_in_cit_presc = 408.0
            else:
                cit_conc_presc = st.number_input(
                    "Concentración (mmol/L)", 100.0, 1200.0, 1000.0, 10.0,
                    key="presc_cit_conc_custom")
                na_in_cit_presc = st.number_input(
                    "Na en solución (mmol/L)", 0.0, 500.0, 100.0, 5.0,
                    key="presc_cit_na_custom")
        with rca_c2:
            cit_dose_presc = st.number_input(
                "Dosis objetivo citrato (mmol/L sangre)",
                1.0, 6.0, float(st.session_state.get("cit_dose", 3.0)), 0.1,
                key="presc_cit_dose",
                help="Inicio habitual: 3 mmol/L. Rango: 2–4 mmol/L.")
        with rca_c3:
            st.metric("QB utilizado (mL/min)", qb,
                      help="Tomado de la barra lateral. Ajusta QB ahí si es necesario.")

        # Cálculos de citrato
        cit_inf_presc = cit_dose_presc * qb * 60 / cit_conc_presc if cit_conc_presc > 0 else 0
        qr_pre_efectivo = max(0.0, qr_pre - cit_inf_presc)
        ff_adj_val = (qr_post + uf) / max(qp_h + qr_pre_efectivo + cit_inf_presc, 1e-9)
        ff_efectiva = ff_adj_val
        ff_adj_pct = ff_adj_val * 100

        # Guardar en session_state para que Resumen/Impresión lo recoja
        st.session_state["rca_citrato_ml_h"] = float(cit_inf_presc)
        st.session_state["cit_conc_mmol_L"] = cit_conc_presc
        st.session_state["cit_na_mmol_L"] = na_in_cit_presc
        st.session_state["presc_cit_dose_val"] = float(cit_dose_presc)   # key diferente a "cit_dose"
        st.session_state["presc_cit_sol_label"] = cit_sol_presc           # key diferente a "cit_sol_type"
        st.session_state["rca_targets"] = {
            "iCa_post": "0.25–0.40", "iCa_sist": "1.0–1.2",
            "citrato_obj_mmolL": float(cit_dose_presc)}

        # Mostrar flujos ajustados
        st.markdown("##### Flujos con citrato — configuración en máquina")
        fm_c1, fm_c2, fm_c3, fm_c4 = st.columns(4)
        fm_c1.metric("Citrato PRE-filtro (mL/hr)", f"{cit_inf_presc:.0f}",
                     help="Infundir por bomba de citrato en línea arterial, antes del filtro")
        fm_c2.metric("Qr PRE solución (mL/hr)", f"{qr_pre_efectivo:.0f}",
                     delta=f"{qr_pre_efectivo - qr_pre:+.0f} vs sin citrato",
                     help=f"Qr_pre base {qr_pre:.0f} − citrato {cit_inf_presc:.0f}")
        fm_c3.metric("Predilución efectiva total (mL/hr)", f"{qr_pre_efectivo + cit_inf_presc:.0f}",
                     help="Solución PRE + citrato (ambos van pre-filtro)")
        fm_c4.metric("FF efectiva con citrato", f"{ff_adj_pct:.1f}%",
                     delta="✅ OK" if ff_adj_pct <= 25 else "⚠️ ALTA")

        if qr_pre_efectivo <= 0:
            st.info(f"💡 El citrato ({cit_inf_presc:.0f} mL/hr) cubre **toda** la predilución prevista. "
                    f"**Qr_pre solución = 0 mL/hr** en la máquina. FF ≈ {ff_adj_pct:.1f}%")
        else:
            st.info(f"💡 Configura en máquina: **Qr_pre solución = {qr_pre_efectivo:.0f} mL/hr** "
                    f"+ bomba citrato **{cit_inf_presc:.0f} mL/hr** (PRE-filtro). "
                    f"FF efectiva ≈ {ff_adj_pct:.1f}%")

        # Reposición de calcio
        ca_stored = float(st.session_state.get("rca_calcio_ml_h", 0))
        qeff_est = float(dosis_mlkg * peso)
        ca_loss_est = qeff_est * 1.25 / 1000
        num_v_stored = int(st.session_state.get("ca_viales", 12))
        prep_v_stored = 250 if st.session_state.get("ca_prep_vol", "250 mL") == "250 mL" else 500
        ca_conc_est = (num_v_stored * 2.23) / ((prep_v_stored + num_v_stored * 10) / 1000)
        ca_rate_est = ca_loss_est / (ca_conc_est / 1000) if ca_conc_est > 0 else 0
        if ca_stored <= 0:
            st.session_state["rca_calcio_ml_h"] = float(ca_rate_est)
        st.warning(f"⚠️ **Reposición Ca (sistémica POST-filtro):** "
                   f"{ca_stored if ca_stored > 0 else ca_rate_est:.0f} mL/hr "
                   f"de gluconato Ca 10% — Para preparación exacta → pestaña 🧪 Citrato RCA.")

    # ── Semáforo FF (usa FF efectiva según anticoagulación elegida) ───────────
    st.markdown("#### Estado del filtro (FF efectiva)")
    ff_pct_ef = (ff_efectiva * 100) if ff_efectiva is not None else 0.0
    if ff_pct_ef <= 20:
        st.success(f"✅ FF efectiva ≈ {ff_pct_ef:.1f}% — Óptima.")
    elif ff_pct_ef <= 25:
        st.warning(f"🟡 FF efectiva ≈ {ff_pct_ef:.1f}% — Límite. Considerar ↑ predilución o ↑ Qb.")
    else:
        st.error(f"🔴 FF efectiva ≈ {ff_pct_ef:.1f}% — ALTO RIESGO. Reducir Qr_post o UF, ↑ predilución.")

    # Sugerencias por laboratorio
    sugs = []
    if na < 125:
        sugs.append("HipoNa: ≤8–10 mmol/L/24h (≤8 si ODS); ajustar Na en solución.")
    if na > 155:
        sugs.append("HiperNa: ≈0.5 mmol/L/h; dializado Na más alto.")
    if k < 3.0:
        sugs.append("K<3: corregir antes de escalar convección.")
    if k > 5.5:
        sugs.append("K>5.5: ↑ difusivo; dializado K bajo.")
    if amonio > 150:
        sugs.append("Amonio alto: CVVHD alta dosis; prioriza flujo.")
    if ck > 5000:
        sugs.append("CK>5000: rabdomiólisis — HCO con vigilancia de albúmina.")
    if sugs:
        st.markdown("**Sugerencias automáticas:** " + " | ".join(sugs))

    if k >= 6.0 or ph < 7.20:
        st.error("🔴 K≥6.0 y/o pH<7.20 → proponer Qd 2,000–3,000 mL/h con K 0–2 mmol/L y re-labs cada 2–4 h.")

    # Bloque sepsis
    if sepsis_presente(escenarios):
        st.divider()
        st.markdown("### Recomendaciones automáticas — Sepsis")
        colA, colB = st.columns([2, 1])
        with colA:
            st.markdown("**Modalidad:** CVVHDF (preferente)")
            st.markdown("**Dosis:** Inicio 25–30, mantenimiento 20–25 mL/kg/h")
            if pam < 60 or vasopresor_alto_bool:
                st.info("💡 **UF sugerida:** Mínima o 0 (PAM <60 o vasopresor en aumento)")
            elif pam >= 65 and lactato_desc_bool:
                st.info("💡 **UF sugerida:** Puede ↑ 25–50 mL/h cada 4–6h (PAM estable + lactato ↓)")
            for a in rec_labs(k, ph, na):
                st.write("- " + a)
        with colB:
            alertas_sep = []
            if ph < 7.20:
                alertas_sep.append("Confirmar bicarbonato (no lactato) si pH <7.20.")
            if pam < 60 or vasopresor_alto_bool:
                alertas_sep.append("Suspender UF si PAM <60 o ↑ vasopresores.")
            if k >= 6.0:
                alertas_sep.append("K≥6: Qd 2–3 L/h, K 0–2 mmol/L.")
            if alertas_sep:
                st.warning("**Alertas de seguridad:**\n\n- " + "\n- ".join(alertas_sep))

    # ── GUARDAR PRESCRIPCIÓN ───────────────────────────────────────────────────
    st.divider()
    if _can_save() and _DB_ON and _db.db_ok() and _user_id():
        st.markdown("### 💾 Guardar esta prescripción")
        save1, save2 = st.columns([2, 1])
        with save1:
            alias_pac = st.text_input("Nombre / clave del paciente (opcional)",
                                      placeholder="Ej: Paciente UCI-01",
                                      value=st.session_state.get("presc_alias_cargado", ""),
                                      key="presc_alias")
            notas_pac = st.text_input("Notas clínicas (opcional)",
                                      placeholder="Ej: sepsis foco pulmonar, inicio día 2",
                                      key="presc_notas")
        with save2:
            st.markdown(" ")
            st.markdown(" ")
            update_id = st.session_state.get("update_presc_id")
            if update_id:
                st.info(f"↩️ Actualizando prescripción existente — ID {update_id}. "
                        "Los parámetros se guardarán sobre el registro original.")
                if st.button("🔄 Actualizar prescripción", type="primary",
                             key="btn_guardar_presc", use_container_width=True):
                    _esc  = list(st.session_state.get("sb_escenarios", []))
                    _mod, _, _ = combinar_recomendaciones(_esc)
                    _qb   = int(st.session_state.get("sb_qb", 200))
                    _hto  = float(st.session_state.get("sb_hto", 0.30))
                    _dosis = float(st.session_state.get("sb_dosis", 30))
                    _peso = float(st.session_state.get("sb_peso", 70))
                    _uf   = int(st.session_state.get("sb_uf", 100))
                    _, _, _qe, _, _, _, _ = flows_and_ff(_qb, _hto, _dosis, _peso, _uf, _mod or "CVVHDF")
                    datos = {
                        "alias": alias_pac or "Paciente sin nombre",
                        "modality": _mod or "—", "peso": _peso, "hto": _hto,
                        "qb": _qb, "qeff": float(_qe) if _qe else _qb * 3.0,
                        "uf": _uf, "dosis_mlkgh": _dosis,
                        "anticoag": st.session_state.get("anticoagulacion_tipo", "—"),
                        "escenarios": _esc, "notas": notas_pac or "",
                    }
                    datos_j = {k: st.session_state.get(k) for k in [
                        "sb_peso","sb_hto","sb_qb","sb_uf","sb_dosis","sb_escenarios",
                        "anticoagulacion_tipo","rx_nombre_paciente","rx_expediente",
                        "rx_edad","rx_sexo","rx_unidad","rx_nombre_medico","rx_sello",
                    ]}
                    datos_j["alias"] = alias_pac or "Paciente sin nombre"
                    datos["datos_json"] = _json.dumps(datos_j, default=str)
                    if _db.update_prescription(update_id, _user_id(), datos):
                        st.session_state.pop("update_presc_id", None)
                        st.session_state.pop("presc_alias_cargado", None)
                        _clear_cache()
                        st.success(f"✅ Prescripción de **{datos['alias']}** actualizada.")
                    else:
                        st.error("Error al actualizar.")
                if st.button("❌ Cancelar y guardar como nuevo", key="btn_cancel_update"):
                    st.session_state.pop("update_presc_id", None)
                    st.rerun()
            else:
                if st.button("💾 Guardar prescripción", type="primary",
                             key="btn_guardar_presc", use_container_width=True):
                    _esc  = list(st.session_state.get("sb_escenarios", []))
                    _mod, _, _ = combinar_recomendaciones(_esc)
                    _qb   = int(st.session_state.get("sb_qb", 200))
                    _hto  = float(st.session_state.get("sb_hto", 0.30))
                    _dosis = float(st.session_state.get("sb_dosis", 30))
                    _peso = float(st.session_state.get("sb_peso", 70))
                    _uf   = int(st.session_state.get("sb_uf", 100))
                    _, _, _qe, _, _, _, _ = flows_and_ff(_qb, _hto, _dosis, _peso, _uf, _mod or "CVVHDF")
                    datos = {
                        "alias": alias_pac or "Paciente sin nombre",
                        "modality": _mod or "—", "peso": _peso, "hto": _hto,
                        "qb": _qb, "qeff": float(_qe) if _qe else _qb * 3.0,
                        "uf": _uf, "dosis_mlkgh": _dosis,
                        "anticoag": st.session_state.get("anticoagulacion_tipo", "—"),
                        "escenarios": _esc, "notas": notas_pac or "",
                    }
                    datos_j = {k: st.session_state.get(k) for k in [
                        "sb_peso","sb_hto","sb_qb","sb_uf","sb_dosis","sb_escenarios",
                        "anticoagulacion_tipo","rx_nombre_paciente","rx_expediente",
                        "rx_edad","rx_sexo","rx_unidad","rx_nombre_medico","rx_sello",
                    ]}
                    datos_j["alias"] = alias_pac or "Paciente sin nombre"
                    datos["datos_json"] = _json.dumps(datos_j, default=str)
                    if _db.save_prescription(_user_id(), datos):
                        st.session_state.pop("presc_alias_cargado", None)
                        _clear_cache()
                        st.success(f"✅ Prescripción de **{datos['alias']}** guardada.")
                    else:
                        st.error("Error al guardar.")
    elif _can_save() and not (_DB_ON and _db.db_ok()):
        st.info("💡 Conecta Railway para habilitar el guardado de prescripciones.")
    elif not _can_save():
        st.info("🔒 [Pro] Guarda prescripciones y accede a tu historial. "
                "[Activar Pro →](/?nav=premium)")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: CITRATO REGIONAL (RCA) — COMPLETO
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "cit":
    st.subheader("Anticoagulación Regional con Citrato (RCA)")
    st.caption("Anticoagulación local del circuito sin efecto sistémico — primera línea si no hay contraindicaciones.")

    # ── Contraindicaciones ──────────────────────────────────────────────────
    st.markdown("### ⚠️ Verificación de contraindicaciones")
    ci1, ci2, ci3 = st.columns(3)
    with ci1:
        insuf_hep = st.selectbox("Insuficiencia hepática grave", ["No", "Sí"], key="ci_hep")
    with ci2:
        lac_ci = st.number_input("Lactato actual (mmol/L)", 0.0, 25.0, 2.0, 0.1, key="ci_lac")
    with ci3:
        alcalosis_ci = st.selectbox("Alcalosis metabólica severa (HCO₃>35)", ["No", "Sí"], key="ci_alk")

    contraindicado = insuf_hep == "Sí" or lac_ci > 5.0 or alcalosis_ci == "Sí"
    if contraindicado:
        razones = []
        if insuf_hep == "Sí":
            razones.append("Insuficiencia hepática grave (metabolismo de citrato deteriorado)")
        if lac_ci > 5.0:
            razones.append(f"Lactato {lac_ci:.1f} mmol/L > 5.0 (hipoperfusión hepática)")
        if alcalosis_ci == "Sí":
            razones.append("Alcalosis metabólica severa (citrato genera más HCO₃⁻)")
        st.error("⛔ **CONTRAINDICACIÓN detectada.** Usar HEPARINA NO FRACCIONADA.\n\n" +
                 "\n".join(f"• {r}" for r in razones))
    else:
        st.success("✅ Sin contraindicaciones detectadas. Citrato es la opción recomendada.")

    st.divider()

    # ── Tipo de solución ─────────────────────────────────────────────────────
    st.markdown("### Selección de solución de citrato")
    sol_opts = ["Citrato trisódico 4% (136 mmol/L — más común)", "Prismocitrate (concentración configurable)"]
    sol_type = st.selectbox("Tipo de solución", sol_opts, key="cit_sol_type")

    if "4%" in sol_type:
        cit_conc = 136.0
        na_en_cit = 408.0   # 3 × 136 mmol/L de Na (citrato TRIsódico)
        st.info("Citrato trisódico 4%: **136 mmol/L** de citrato | **408 mmol/L** de Na (3 Na por molécula) — considerar en balance de sodio.")
    else:
        cit_conc = st.number_input("Concentración del Prismocitrate (mmol/L)",
                                   100.0, 1200.0, 1000.0, 10.0, key="cit_prismo_conc")
        na_en_cit = st.number_input("Contenido de Na en solución (mmol/L)",
                                    0.0, 500.0, 100.0, 5.0, key="cit_prismo_na",
                                    help="Consultar ficha técnica del fabricante")
        st.caption(f"Prismocitrate configurado: {cit_conc:.0f} mmol/L citrato | {na_en_cit:.0f} mmol/L Na")

    # Guardar para módulo de sodio
    st.session_state["cit_conc_mmol_L"] = cit_conc
    st.session_state["cit_na_mmol_L"] = na_en_cit

    st.divider()

    # ── Cálculo de infusión de citrato ──────────────────────────────────────
    st.markdown("### Cálculo de infusión de citrato")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        cit_qb = st.number_input("QB (mL/min)", 80, 300, int(st.session_state.get("sb_qb", 150)),
                                 10, key="cit_qb")
    with rc2:
        cit_dose = st.number_input("Dosis objetivo (mmol/L sangre)", 1.0, 6.0, 3.0, 0.1,
                                   key="cit_dose",
                                   help="Habitual: 2–4 mmol/L. Inicio conservador a 3 mmol/L.")
    with rc3:
        qe_from_presc = int(dosis_mlkg * peso) if peso > 0 else 2000
        cit_qeff = st.number_input("Efluente total (mL/hr)", 0, 6000,
                                   qe_from_presc, 100, key="cit_qeff",
                                   help=f"Vinculado a prescripción: {dosis_mlkg} mL/kg/h × {peso:.1f} kg = {qe_from_presc} mL/hr")
        st.caption(f"📌 Qe prescripción = {qe_from_presc} mL/hr")

    cit_qb_hr = cit_qb * 60
    cit_inf_rate = cit_dose * cit_qb_hr / cit_conc if cit_conc > 0 else 0
    total_flow = cit_qb_hr + cit_inf_rate
    cit_circuit = cit_inf_rate * cit_conc / total_flow if total_flow > 0 else 0
    cit_load = cit_inf_rate * cit_conc / 1000
    cit_removal = cit_qeff * cit_circuit / 1000
    cit_to_patient = cit_load - cit_removal

    # Aporte de Na por citrato
    na_aporte_cit = cit_inf_rate * na_en_cit / 1000  # mmol/hr

    rcr1, rcr2, rcr3, rcr4 = st.columns(4)
    rcr1.metric("Tasa citrato (mL/hr)", f"{cit_inf_rate:.0f}")
    rcr2.metric("Carga al circuito (mmol/hr)", f"{cit_load:.2f}")
    rcr3.metric("Remoción por filtro (mmol/hr)", f"{cit_removal:.2f}")
    rcr4.metric("Carga al paciente (mmol/hr)", f"{cit_to_patient:.2f}")

    st.caption(f"[Citrato] en circuito: **{cit_circuit:.1f} mmol/L** | "
               f"Aporte de Na por citrato: **{na_aporte_cit:.1f} mmol/hr** "
               f"({na_aporte_cit * 24:.0f} mmol/día) — incluir en balance de sodio.")

    # Guardar para PDF y tarjeta enfermería
    st.session_state["rca_citrato_ml_h"] = float(cit_inf_rate)
    st.session_state["anticoagulacion_tipo"] = "RCA"

    st.divider()

    # ── Reposición de calcio ─────────────────────────────────────────────────
    st.markdown("### Calculadora de reposición de calcio")
    st.caption("Gluconato de calcio 10% — cada ámpula de **10 mL = 2.23 mmol** de Ca elemental")

    ca_loss = cit_qeff * 1.25 / 1000  # mmol/hr estimado

    cac1, cac2, cac3 = st.columns(3)
    with cac1:
        num_viales = st.number_input("# de ámpulas de gluconato Ca 10% (10 mL c/u)",
                                     1, 30, 12, 1, key="ca_viales",
                                     help="Ejemplo habitual: 12 ámpulas")
    with cac2:
        prep_vol_str = st.selectbox("Volumen de NaCl 0.9% para aforar",
                                    ["250 mL", "500 mL"], key="ca_prep_vol")
        prep_vol_ml = 250 if "250" in prep_vol_str else 500
    with cac3:
        st.metric("Pérdida estimada de Ca (mmol/hr)", f"{ca_loss:.2f}",
                  help="Estimado: Qeff × 1.25 mmol/L / 1000")

    mmol_per_vial = 2.23
    total_ca = num_viales * mmol_per_vial
    # AFORO: el volumen total de la preparación es el de la bolsa (250 o 500 mL).
    # Las ámpulas se añaden a la bolsa ya aforada — el volumen final NO se suma.
    vol_total_ca = prep_vol_ml
    ca_conc_mmol_L = total_ca / (vol_total_ca / 1000) if vol_total_ca > 0 else 0
    ca_inf_rate_ml_hr = ca_loss / (ca_conc_mmol_L / 1000) if ca_conc_mmol_L > 0 else 0

    carc1, carc2, carc3, carc4 = st.columns(4)
    carc1.metric("Ca total en bolsa (mmol)", f"{total_ca:.2f}")
    carc2.metric("Volumen total aforado (mL)", f"{vol_total_ca}",
                 help="Aforado: el volumen final es el de la bolsa de NaCl")
    carc3.metric("Concentración Ca (mmol/L)", f"{ca_conc_mmol_L:.1f}")
    carc4.metric("Tasa infusión inicial (mL/hr)", f"{ca_inf_rate_ml_hr:.0f}")

    st.info(f"📋 **Preparación (aforado):** Agregar {num_viales} ámpulas gluconato Ca 10% (10mL c/u) "
            f"a bolsa de **{prep_vol_ml}mL NaCl 0.9%** — volumen final aforado = **{vol_total_ca}mL** "
            f"con **{ca_conc_mmol_L:.1f} mmol/L** Ca elemental. "
            f"Infundir a **{ca_inf_rate_ml_hr:.0f} mL/hr** por línea sistémica (POSTFILTRO).")
    st.caption("⚠️ El calcio se infunde por línea sistémica post-filtro, NUNCA en la línea de citrato ni pre-filtro.")

    # Guardar para PDF
    st.session_state["rca_calcio_ml_h"] = float(ca_inf_rate_ml_hr)

    st.divider()

    # ── Ajuste por iCa ──────────────────────────────────────────────────────
    st.markdown("### Ajuste por calcio ionizado medido")
    adj1, adj2 = st.columns(2)
    with adj1:
        ica_post = st.number_input("iCa POST-filtro (mmol/L)", 0.0, 2.0, 0.35, 0.01,
                                   key="ica_post", help="Objetivo: 0.25–0.40 mmol/L")
    with adj2:
        ica_sist = st.number_input("iCa sistémico (mmol/L)", 0.0, 2.5, 1.10, 0.01,
                                   key="ica_sist", help="Objetivo: 1.0–1.2 mmol/L")

    # Ajuste citrato por iCa post-filtro
    if ica_post < 0.25:
        st.warning(f"⬇️ iCa post-filtro BAJO ({ica_post:.2f} mmol/L). "
                   f"**↓ Citrato 10–20%:** nueva tasa ≈ {cit_inf_rate * 0.85:.0f}–{cit_inf_rate * 0.90:.0f} mL/hr")
    elif ica_post > 0.40:
        st.warning(f"⬆️ iCa post-filtro ALTO ({ica_post:.2f} mmol/L). "
                   f"**↑ Citrato 10–20%:** nueva tasa ≈ {cit_inf_rate * 1.10:.0f}–{cit_inf_rate * 1.20:.0f} mL/hr")
    else:
        st.success(f"✅ iCa post-filtro en rango ({ica_post:.2f} mmol/L — objetivo 0.25–0.40). Citrato adecuado.")

    # Ajuste calcio por iCa sistémico
    if ica_sist < 1.0:
        st.warning(f"⬆️ iCa sistémico BAJO ({ica_sist:.2f} mmol/L). "
                   f"**↑ Calcio 10–20%:** nueva tasa ≈ {ca_inf_rate_ml_hr * 1.10:.0f}–{ca_inf_rate_ml_hr * 1.20:.0f} mL/hr")
    elif ica_sist > 1.2:
        st.warning(f"⬇️ iCa sistémico ALTO ({ica_sist:.2f} mmol/L). "
                   f"**↓ Calcio 10–20%:** nueva tasa ≈ {ca_inf_rate_ml_hr * 0.80:.0f}–{ca_inf_rate_ml_hr * 0.90:.0f} mL/hr")
    else:
        st.success(f"✅ iCa sistémico en rango ({ica_sist:.2f} mmol/L — objetivo 1.0–1.2). Calcio adecuado.")

    # Guardar targets para PDF
    st.session_state["rca_targets"] = {
        "iCa_post": f"{ica_post:.2f}",
        "iCa_sist": f"{ica_sist:.2f}",
        "citrato_obj_mmolL": float(cit_dose)
    }

    st.divider()

    # ── Calendario de monitoreo ──────────────────────────────────────────────
    st.markdown("### 📅 Calendario de monitoreo RCA")
    st.markdown("""
| Momento | Qué medir | Acción |
|---------|-----------|--------|
| **30 min post-inicio** | iCa post-filtro + iCa sistémico | Ajuste inicial ±10–20% |
| **1–2 hrs** | iCa ambos | Confirmar estabilidad |
| **Cada 4–6 hrs (estable)** | iCa ambos + Na, K, HCO₃⁻, AG | Mantenimiento |
| **Post-ajuste de dosis** | 30 min después del cambio | Verificar nuevo equilibrio |
| **Cada 12–24 hrs** | Ca total, Ca iónico, AG, pH, HCO₃⁻, lactato | Detección acumulación |
    """)

    st.divider()

    # ── Detección de acumulación de citrato ─────────────────────────────────
    st.markdown("### 🔍 Detección de acumulación de citrato")
    st.caption("La acumulación ocurre cuando el hígado no metaboliza el citrato (insuficiencia hepática, bajo gasto cardíaco).")

    acc1, acc2, acc3 = st.columns(3)
    with acc1:
        ca_total_acc = st.number_input("Ca total sérico (mmol/L)", 1.0, 4.0, 2.3, 0.1, key="acc_catot",
                                       help="Normal: 2.1–2.6 mmol/L")
        ca_ion_acc = st.number_input("Ca iónico sistémico (mmol/L)", 0.3, 2.0, 1.1, 0.01, key="acc_caion")
    with acc2:
        ag_acc = st.number_input("Anión gap (mEq/L)", 5.0, 40.0, 12.0, 0.5, key="acc_ag",
                                 help="Normal: 8–16 mEq/L")
        hco3_acc = st.number_input("HCO₃⁻ (mEq/L)", 10.0, 50.0, 24.0, 0.5, key="acc_hco3")
    with acc3:
        ph_acc = st.number_input("pH", 7.10, 7.70, 7.40, 0.01, key="acc_ph")
        ca_inf_sube = st.selectbox("¿Infusión Ca en aumento sin corregir iCa?", ["No", "Sí"],
                                   key="acc_ca_sube")

    ratio_ca = ca_total_acc / ca_ion_acc if ca_ion_acc > 0 else 0
    criterios_acum = []
    if ratio_ca > 2.5:
        criterios_acum.append(f"🔴 Ca total / Ca iónico = **{ratio_ca:.2f}** (>2.5 — CRITERIO PRINCIPAL)")
    if ag_acc > 16:
        criterios_acum.append(f"🟠 Anión gap elevado: **{ag_acc:.1f} mEq/L** (>16)")
    if hco3_acc > 30 or ph_acc > 7.50:
        criterios_acum.append(f"🟠 Alcalosis metabólica: HCO₃⁻={hco3_acc:.1f}, pH={ph_acc:.2f}")
    if ca_inf_sube == "Sí" and ca_ion_acc < 1.0:
        criterios_acum.append("🟠 iCa sistémico bajo a pesar de ↑ infusión de calcio")

    st.metric("Relación Ca total / Ca iónico", f"{ratio_ca:.2f}",
              delta="Normal (<2.5)" if ratio_ca <= 2.5 else "ELEVADO (>2.5)")

    if len(criterios_acum) >= 2:
        st.error("🚨 **PROBABLE ACUMULACIÓN DE CITRATO**\n\n" +
                 "\n".join(criterios_acum) +
                 "\n\n**Acciones:** Reducir citrato 30–50% o suspender → cambiar a HNF. "
                 "Monitorear iCa cada hora. Identificar causa (disfunción hepática, bajo GC).")
    elif len(criterios_acum) == 1:
        st.warning("⚠️ Un criterio de acumulación presente. Monitoreo estrecho:\n\n" + criterios_acum[0])
    else:
        st.success(f"✅ Sin criterios de acumulación. Ratio Ca total/iónico = {ratio_ca:.2f} (normal <2.5).")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: SODIO EN TRRC
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "na":
    st.subheader("Sodio en TRRC — Predicción y Corrección")

    modo_na = st.radio("Modo", ["📊 Predicción de sodio", "🎯 Corrección de sodio"], horizontal=True,
                       key="modo_na")

    # Datos del paciente compartidos
    st.markdown("### Datos del paciente")
    nac1, nac2, nac3, nac4, nac5 = st.columns(5)
    with nac1:
        na_sex = st.selectbox("Sexo", ["M", "F"], key="na_sex")
    with nac2:
        na_age = st.number_input("Edad (años)", 0, 110, 55, 1, key="na_age")
    with nac3:
        na_ht = st.number_input("Talla (cm)", 100, 220, 170, 1, key="na_ht")
    with nac4:
        na_wt = st.number_input("Peso (kg)", 10.0, 300.0, float(peso), 0.5, key="na_wt")
    with nac5:
        na_plasma = st.number_input("Na plasmático actual (mEq/L)", 100.0, 200.0, 140.0, 0.5,
                                    key="na_plasma")

    st.markdown("### Parámetros de la terapia")
    nat1, nat2, nat3 = st.columns(3)
    with nat1:
        na_bags = st.number_input("[Na] en bolsas TRRC (mEq/L)", 100.0, 160.0, 140.0, 1.0,
                                  key="na_bags", help="Na en solución de reemplazo/dializato")
        na_qeff = st.number_input("Efluente total (mL/hr)", 0, 6000, int(dosis_mlkg * peso),
                                  100, key="na_qeff")
    with nat2:
        cit_sol_tipo_na = st.session_state.get("cit_sol_type", "Citrato trisódico 4% (136 mmol/L — más común)")
        na_in_cit = st.number_input("[Na] en solución de citrato (mEq/L)",
                                    0.0, 500.0, float(st.session_state.get("cit_na_mmol_L", 408.0)),
                                    1.0, key="na_in_cit",
                                    help="Citrato trisódico 4%: ~408 mEq/L")
        cit_inf_na = st.number_input("Tasa infusión citrato (mL/hr)", 0.0, 500.0,
                                     float(st.session_state.get("rca_citrato_ml_h", 0.0)),
                                     1.0, key="cit_inf_na")
    with nat3:
        na_post_sol = st.number_input("[Na] solución postfiltro (mEq/L)", 0.0, 160.0, 0.0, 1.0,
                                      key="na_post_sol", help="0 si no hay reposición postfiltro separada")
        post_inf_na = st.number_input("Tasa reposición postfiltro (mL/hr)", 0.0, 3000.0, 0.0, 10.0,
                                      key="post_inf_na")

    if "Predicción" in modo_na:
        st.markdown("### Predicción")
        na_tiempo = st.number_input("Tiempo de terapia (hrs)", 1, 72, 24, 1, key="na_tiempo")
        result_na = calc_na_pred_trrc(
            na_sex, na_age, na_ht, na_wt, na_plasma, na_bags, na_qeff, na_tiempo,
            na_in_cit, cit_inf_na, na_post_sol, post_inf_na)
        if result_na:
            rn1, rn2, rn3 = st.columns(3)
            rn1.metric("ACT estimada (Watson)", f"{result_na['tbw']:.1f} L")
            rn2.metric("Balance neto de Na", f"{result_na['net_na']:.1f} mEq/hr",
                       help="+: Na se retiene | -: Na se elimina")
            rn3.metric("[Na] predicho al final", f"{result_na['na_pred']:.1f} mEq/L",
                       delta=f"{result_na['na_pred'] - na_plasma:+.1f} vs actual")
            delta_24 = result_na["net_na"] * na_tiempo
            st.info(f"Balance acumulado en {na_tiempo}h: **{delta_24:+.0f} mEq de Na** → "
                    f"Na final predicho **{result_na['na_pred']:.1f} mEq/L**")
            # Alertas de corrección
            if na_plasma < 130 and (result_na["na_pred"] - na_plasma) > 10:
                st.error("⚠️ Corrección de hiponatremia >10 mEq/L proyectada. Riesgo de ODS. Ajustar [Na] en bolsas o reducir efluente.")
            if abs(result_na["na_pred"] - na_plasma) / na_tiempo > 0.5 and na_tiempo <= 24:
                st.warning(f"⚠️ Velocidad de corrección ≈ {abs(result_na['na_pred'] - na_plasma) / na_tiempo:.2f} mEq/L/hr. Verificar meta clínica.")
        else:
            st.info("Completa los datos del paciente para calcular la predicción.")

    else:  # Corrección
        st.markdown("### Estrategias de corrección de sodio en 24h")
        na_meta = st.number_input("[Na] objetivo en 24h (mEq/L)", 100.0, 200.0, 140.0, 0.5,
                                  key="na_meta")
        result_corr = calc_na_corr_trrc(
            na_sex, na_age, na_ht, na_wt, na_plasma, na_meta, na_qeff, na_bags,
            na_in_cit, cit_inf_na)
        if result_corr:
            st.metric("ACT estimada (Watson)", f"{result_corr['tbw']:.1f} L")
            st.metric("Δ Na necesario", f"{result_corr['delta_hr']:+.1f} mEq/hr",
                      help="Na neto que debe moverse por hora para alcanzar la meta en 24h")
            st.markdown("---")
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown("#### Estrategia 1")
                st.markdown("**Ajustar flujo de reposición postfiltro** (Na estándar = 140 mEq/L)")
                st.metric("Tasa postfiltro recomendada", f"{result_corr['pf_rate']:.0f} mL/hr")
                st.caption("Mantener [Na] en bolsas sin cambios. Ajustar sólo el flujo postfiltro.")
            with rc2:
                st.markdown("#### Estrategia 2")
                st.markdown("**Ajustar [Na] en bolsas TRRC** (sin reposición postfiltro adicional)")
                st.metric("[Na] objetivo en bolsas", f"{result_corr['target_bags']:.1f} mEq/L")
                st.caption("Mantener flujo de efluente. Cambiar composición de la solución.")
            # Alertas
            delta_na_24 = na_meta - na_plasma
            if na_plasma < 130 and delta_na_24 > 10:
                st.error("⚠️ Meta implica corrección >10 mEq/L en 24h. Para hiponatremia ≤ 8 mEq/L/24h (≤8 si riesgo de ODS). Reconsiderar meta.")
            if na_plasma > 150 and delta_na_24 < -12:
                st.warning("⚠️ Corrección de hipernatremia: no exceder 10–12 mEq/L/24h. Verificar meta.")
        else:
            st.info("Completa los datos para calcular las estrategias de corrección.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: PREDICCIÓN HD + KoA
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "hd":
    st.subheader("Predicción de Hemodiálisis convencional + KoA")

    modo_hd = st.radio("Modo", ["💉 Predicción HD", "🔧 Calculadora KoA"], horizontal=True, key="modo_hd")

    if "Predicción" in modo_hd:
        st.markdown("### Datos del paciente")
        hd1, hd2, hd3, hd4, hd5 = st.columns(5)
        with hd1:
            hd_sex = st.selectbox("Sexo", ["M", "F"], key="hd_sex")
        with hd2:
            hd_age = st.number_input("Edad (años)", 0, 110, 55, 1, key="hd_age")
        with hd3:
            hd_ht = st.number_input("Talla (cm)", 100, 220, 170, 1, key="hd_ht")
        with hd4:
            hd_wt = st.number_input("Peso seco (kg)", 10.0, 200.0, 70.0, 0.5, key="hd_wt")
        with hd5:
            pass

        st.markdown("### Terapia prescrita")
        hdt1, hdt2, hdt3, hdt4, hdt5 = st.columns(5)
        with hdt1:
            hd_time = st.number_input("Tiempo (min)", 60, 480, 240, 15, key="hd_time")
        with hdt2:
            hd_uf = st.number_input("UF total (L)", 0.0, 10.0, 2.0, 0.1, key="hd_uf")
        with hdt3:
            hd_qb = st.number_input("QB (mL/min)", 100, 500, 300, 10, key="hd_qb")
        with hdt4:
            hd_qd = st.number_input("QD (mL/min)", 100, 800, 500, 50, key="hd_qd")
        with hdt5:
            hd_koa = st.number_input("KoA membrana (mL/min)", 0.0, 2000.0, 0.0, 10.0,
                                     key="hd_koa", help="Opcional. Si 0, estimado por QB/QD × 0.85")

        result_hd = calc_hd_pred(hd_sex, hd_age, hd_ht, hd_wt, hd_time, hd_uf, hd_qb, hd_qd, hd_koa)
        if result_hd:
            st.markdown("### Resultados predichos")
            hdr1, hdr2, hdr3, hdr4, hdr5 = st.columns(5)
            hdr1.metric("ACT (Watson)", f"{result_hd['tbw']:.1f} L")
            hdr2.metric("Aclar. urea K (mL/min)", f"{result_hd['K']:.1f}")
            hdr3.metric("Urea Kt (L)", f"{result_hd['Kt']:.2f}")
            hdr4.metric("Kt/V", f"{result_hd['KtV']:.2f}",
                        delta="✅ Adecuado" if result_hd["KtV"] >= 1.2 else "⚠️ Bajo")
            hdr5.metric("URR estimada", f"{result_hd['URR']:.1f}%",
                        delta="✅" if result_hd["URR"] >= 65 else "⚠️")

            if result_hd["KtV"] < 1.2:
                st.warning(f"⚠️ Kt/V {result_hd['KtV']:.2f} < 1.2 (meta KDIGO para 3×/semana). "
                           f"Considerar ↑ tiempo, ↑ QB o ↑ QD.")
            elif result_hd["KtV"] >= 1.4:
                st.success(f"✅ Kt/V {result_hd['KtV']:.2f} ≥ 1.4 — Excelente adecuación.")
            else:
                st.success(f"✅ Kt/V {result_hd['KtV']:.2f} — Adecuado (meta ≥1.2).")

            st.metric("Tasa UF (mL/min)", f"{result_hd['UFrate']:.1f}",
                      help="UF rate. Objetivo <13 mL/min/m² BSA (~10 mL/kg/hr)")

            # Predicción de solutos post-diálisis
            st.markdown("### Predicción de solutos post-sesión")
            st.caption("Modelos de un pool con supuestos de equilibrio simplificados.")
            solt1, solt2, solt3 = st.columns(3)
            with solt1:
                pre_bun = st.number_input("BUN/Urea pre (cualquier ud.)", 0.0, 500.0, 80.0, 1.0,
                                          key="hd_prebun")
                pre_na = st.number_input("[Na] pre (mEq/L)", 100.0, 200.0, 140.0, 0.5, key="hd_prena")
                pre_k = st.number_input("[K] pre (mEq/L)", 1.0, 10.0, 5.0, 0.1, key="hd_prek")
            with solt2:
                dial_na = st.number_input("[Na] dializado (mEq/L)", 100.0, 160.0, 140.0, 0.5,
                                          key="hd_dialna")
                dial_k = st.number_input("[K] dializado (mEq/L)", 0.0, 4.0, 2.0, 0.5, key="hd_dialk")
            with solt3:
                ktv_val = result_hd["KtV"]
                post_bun = pre_bun * math.exp(-ktv_val)
                post_na = dial_na + (pre_na - dial_na) * math.exp(-ktv_val * 0.3)
                post_k = dial_k + (pre_k - dial_k) * math.exp(-ktv_val * 1.2)
                two_pool_k = post_k * 1.3

                st.metric("BUN/Urea post (predicho)", f"{post_bun:.1f}")
                st.metric("[Na] post (mEq/L)", f"{post_na:.1f}")
                st.metric("[K] post (mEq/L)", f"{post_k:.1f}")
                st.metric("[K] post 2-pool (rebote)", f"{two_pool_k:.1f}",
                          help="Estimado 30% de rebote desde compartimento intracelular")

    else:  # KoA
        st.markdown("### Calculadora de KoA (datos in vitro del fabricante)")
        st.caption("Basada en la ecuación de Michaels. Resolución numérica. Usar datos del datasheet del dializador.")
        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            koa_K = st.number_input("Aclaramiento in vitro K (mL/min)", 0.0, 500.0, 180.0, 1.0,
                                    key="koa_K")
        with kc2:
            koa_QB = st.number_input("QB in vitro (mL/min)", 50.0, 500.0, 200.0, 10.0, key="koa_QB")
        with kc3:
            koa_QD = st.number_input("QD in vitro (mL/min)", 50.0, 800.0, 500.0, 50.0, key="koa_QD")

        koa_result = calc_koa(koa_K, koa_QB, koa_QD)
        if koa_result is not None:
            st.metric("KoA in vitro (mL/min)", f"{koa_result:.0f}")
            st.success(f"✅ KoA = **{koa_result:.0f} mL/min** — Puedes usar este valor en el módulo de Predicción HD.")
        elif koa_K >= min(koa_QB, koa_QD):
            st.error("⚠️ El aclaramiento no puede ser mayor o igual al mínimo de QB y QD. Revisar datos.")
        else:
            st.info("Ingresa datos del datasheet del dializador para calcular el KoA.")

        with st.expander("¿Qué es el KoA?"):
            st.markdown("""
**KoA (Mass Transfer Area Coefficient)** es el coeficiente de transferencia de masa del dializador.
Representa la eficiencia intrínseca de la membrana independientemente de los flujos.

**Fórmula (Michaels):**
$$K = Q_B \\cdot \\frac{1 - e^{-KoA/Q_B \\cdot (1 - Q_B/Q_D)}}{1 - Q_B/Q_D \\cdot e^{-KoA/Q_B \\cdot (1 - Q_B/Q_D)}}$$

Se obtiene de los datos in vitro del fabricante (K a QB y QD estándar).
            """)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: PLASMAFÉRESIS / TPE — COMPLETO
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "tpe":
    st.subheader("🔄 Plasmaféresis Terapéutica (TPE)")

    tpe_modo = st.radio("Sección",
        ["⚗️ Cálculo de sesión", "📊 Indicaciones ASFA 2023",
         "🔬 Mecanismo por indicación", "💉 Anticoagulación ACD-A",
         "📋 Monitoreo y contraindicaciones"],
        horizontal=True, key="tpe_modo")

    # ── CÁLCULO DE SESIÓN ──────────────────────────────────────────────────────
    if tpe_modo == "⚗️ Cálculo de sesión":
        st.markdown("### Datos del paciente")
        tpe1, tpe2, tpe3 = st.columns(3)
        with tpe1:
            tpe_peso = st.number_input("Peso (kg)", 10.0, 200.0, float(peso), 0.5, key="tpe_peso")
        with tpe2:
            tpe_hct = st.number_input("Hematocrito (%)", 10.0, 60.0, 30.0, 0.5, key="tpe_hct")
        with tpe3:
            tpe_nex = st.number_input("Número de recambios por sesión", 0.5, 4.0, 1.5, 0.1,
                                      key="tpe_nex", help="1 recambio = 1 VPE. Habitual: 1.0–1.5")

        result_tpe = calc_tpe(tpe_peso, tpe_hct, tpe_nex)

        st.markdown("### Volúmenes estimados")
        tpe_r1, tpe_r2 = st.columns(2)
        tpe_r1.metric("Volumen plasmático estimado (VPE)", f"{result_tpe['EPV']:.0f} mL",
                      help="Fórmula: 65 × peso × (1 − Hto)")
        tpe_r2.metric("Volumen a intercambiar", f"{result_tpe['vol_ex']:.0f} mL",
                      help=f"{tpe_nex:.1f} recambios × VPE")

        st.divider()
        st.markdown("### Cinética IgG — 1 sesión")
        cs1, cs2 = st.columns(2)
        cs1.metric("Reducción intravascular", f"{result_tpe['red1']:.1f}%")
        cs2.metric("Residual intravascular", f"{result_tpe['res1']:.1f}%")

        st.markdown("### Cinética IgG total — múltiples sesiones")
        st.caption("Con redistribución extravascular (fracción IV ≈ 45%, EV ≈ 55%).")
        tpe_nsess = st.number_input("Número total de sesiones", 1, 20, 5, 1, key="tpe_nsess")
        result_multi = calc_tpe_total(tpe_nex, tpe_nsess)
        cm1, cm2 = st.columns(2)
        cm1.metric("Reducción total de IgG", f"{result_multi['total_red']:.2f}%")
        cm2.metric("Residual total de IgG", f"{result_multi['total_res']:.2f}%")

        st.divider()
        st.markdown("### Líquido de reemplazo")

        st.markdown("""
> **Base científica:** La albúmina 5% replica la presión oncótica fisiológica del plasma (albumina plasmática normal: 3.5–5 g/dL). Se usa en reemplazo 1:1 del volumen plasmático intercambiado. El PFC se reserva para TTP porque además de remover inhibidores de ADAMTS13, **aporta ADAMTS13 funcional** que la albúmina no puede reemplazar.
        """)

        remp_tipo = st.radio("Tipo de reemplazo", ["Albúmina 5%", "PFC (Plasma Fresco Congelado)"],
                             horizontal=True, key="tpe_remp")

        vol_intercambio = result_tpe['vol_ex']

        if remp_tipo == "Albúmina 5%":
            st.info("✅ **Reemplazo estándar** para la mayoría de indicaciones. ⛔ NO usar en TTP — usar PFC.")

            st.markdown("#### ¿Por qué albúmina al 5%?")
            st.markdown("""
La concentración fisiológica de albúmina en plasma es **3.5–5 g/dL**.
La albúmina 5% = **50 g/L**, lo que replicas directamente la presión oncótica normal del plasma.
Concentraciones mayores (20%, 25%) deben diluirse antes de usarse como reemplazo.
            """)

            st.divider()
            st.markdown("#### Preparación de bolsas de albúmina al 5%")
            st.caption("La albúmina concentrada NO se aforta — se diluye de forma aditiva con NaCl 0.9%.")

            pr1, pr2, pr3 = st.columns(3)
            with pr1:
                alb_pct_vial = st.selectbox("Albúmina disponible en vial",
                                            ["20% (vial 50 mL = 10g)", "25% (vial 50 mL = 12.5g)", "5% (lista para usar)"],
                                            key="alb_pct_vial")
            with pr2:
                alb_bolsa_str = st.selectbox("Tamaño de bolsa NaCl 0.9%",
                                             ["1000 mL", "500 mL", "250 mL"], key="alb_bolsa")
                alb_bolsa_ml = int(alb_bolsa_str.replace(" mL", ""))
            with pr3:
                alb_n_bolsas_calc = st.number_input("Número de bolsas a preparar", 1, 20,
                                                    max(1, math.ceil(vol_intercambio / alb_bolsa_ml)),
                                                    1, key="alb_n_bolsas")

            # Calculate based on selected concentration
            if "20%" in alb_pct_vial:
                pct_vial = 20
                g_por_vial = 10.0  # 50mL × 20% = 10g
            elif "25%" in alb_pct_vial:
                pct_vial = 25
                g_por_vial = 12.5  # 50mL × 25% = 12.5g
            else:
                pct_vial = 5
                g_por_vial = 2.5   # 50mL × 5% = 2.5g

            if pct_vial == 5:
                st.success("✅ Albúmina 5% lista — usar directamente sin preparación.")
                n_bolsas_total = math.ceil(vol_intercambio / alb_bolsa_ml)
                st.metric("Bolsas de albúmina 5% para la sesión", f"{n_bolsas_total} bolsas de {alb_bolsa_str}")
            else:
                # How many vials per bag to get 5%
                # Need: 5g per 100mL → 50g per 1000mL
                g_necesarios_por_bolsa = 5 * alb_bolsa_ml / 100  # grams of albumin needed
                viales_por_bolsa = math.ceil(g_necesarios_por_bolsa / g_por_vial)
                vol_albumina_en_bolsa = viales_por_bolsa * 50  # mL of albumin added
                vol_nacl = alb_bolsa_ml - vol_albumina_en_bolsa  # remaining NaCl
                conc_real = (viales_por_bolsa * g_por_vial) / (alb_bolsa_ml / 100)

                # Session totals
                n_bolsas_total = math.ceil(vol_intercambio / alb_bolsa_ml)
                viales_total = viales_por_bolsa * n_bolsas_total

                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("Viales por bolsa", f"{viales_por_bolsa} viales")
                rc2.metric("Concentración real lograda", f"{conc_real:.1f}%")
                rc3.metric("Bolsas para la sesión", f"{n_bolsas_total} bolsas")
                rc4.metric("Viales TOTALES para la sesión", f"{viales_total} viales",
                           help="Lo que debes pedir a farmacia para toda la sesión")

                st.success(f"""
📋 **Preparación de cada bolsa ({alb_bolsa_str} al 5%):**
1. Tomar una bolsa de **NaCl 0.9% {alb_bolsa_str}**
2. Extraer **{vol_albumina_en_bolsa} mL** de la bolsa (para hacer espacio) — o usar bolsa vacía
3. Agregar **{viales_por_bolsa} viales de albúmina {pct_vial}%** (50 mL c/u = {viales_por_bolsa*50} mL)
4. Mezclar **invirtiendo suavemente** (nunca agitar — desnaturaliza proteínas)
5. Usar a temperatura ambiente o calentada a 37°C si hay riesgo de hipotermia

**Para toda la sesión:** preparar {n_bolsas_total} bolsas × {viales_por_bolsa} viales = **{viales_total} viales en total**
                """)

                st.info(f"💊 **Pedir a farmacia:** {viales_total} viales de albúmina {pct_vial}% (50mL c/u) + {n_bolsas_total} bolsas NaCl 0.9% {alb_bolsa_str}")

            st.divider()
            st.markdown("#### Volumen total de la sesión")
            vr1, vr2 = st.columns(2)
            vr1.metric("Volumen de intercambio (= volumen de albúmina 5% necesario)",
                       f"{vol_intercambio:.0f} mL", help="Reemplazo 1:1 del volumen plasmático intercambiado")
            vr2.metric("Bolsas necesarias", f"{math.ceil(vol_intercambio/alb_bolsa_ml)} × {alb_bolsa_str}")

        else:  # PFC
            st.warning("⚠️ **PFC indicado principalmente en TTP activo.** Verificar compatibilidad ABO/Rh.")

            st.markdown("#### ¿Por qué PFC y no albúmina en TTP?")
            st.markdown("""
En la PTT (Púrpura Trombocitopénica Trombótica), el mecanismo es:
- **Deficiencia de ADAMTS13** (congénita o anticuerpos adquiridos)
- ADAMTS13 normalmente **degrada los multímeros ultra-largos de FvW** (ULvWF)
- Sin ADAMTS13 → ULvWF acumulan → agregación plaquetaria → microtrombos → isquemia

El PFC **aporta ADAMTS13 funcional** además de remover los inhibidores.
La albúmina NO contiene ADAMTS13 → no trata el déficit enzimático.
            """)

            vol_pfc = result_tpe['vol_ex']
            unidades_pfc = math.ceil(vol_pfc / 225)
            bolsas_pfc_200 = math.ceil(vol_pfc / 200)

            pfc1, pfc2, pfc3 = st.columns(3)
            pfc1.metric("Volumen PFC necesario", f"{vol_pfc:.0f} mL")
            pfc2.metric("Unidades PFC (≈225 mL/u)", f"{unidades_pfc} unidades")
            pfc3.metric("Si unidades de 200 mL", f"{bolsas_pfc_200} unidades")

            st.info(f"📋 Solicitar **{unidades_pfc} unidades de PFC** compatibles por ABO/Rh. "
                    f"Descongelar 30–60 min antes en banco de sangre (37°C agua o microondas validado). "
                    f"Usar en las primeras 4h post-descongelación.")

            st.markdown("""
**Monitoreo específico con PFC:**
- Alergia/anafilaxia: más frecuente que con albúmina (1–3%)
- Tener antihistamínico IV (difenhidramina) + adrenalina disponibles
- TRALI (lesión pulmonar aguda): raro pero grave — vigilar saturación c/15 min
- Hipocalcemia por citrato del PFC: monitorear iCa
            """)

    # ── INDICACIONES ASFA 2023 ─────────────────────────────────────────────────
    elif tpe_modo == "📊 Indicaciones ASFA 2023":
        st.markdown("### Indicaciones por categoría — ASFA 2023")
        st.caption("Schwartz et al., J Clin Apheresis 2023. Categoría determina nivel de evidencia.")

        st.markdown("""
| Categoría | Significado |
|-----------|------------|
| **I** | Primera línea, estándar de tratamiento |
| **II** | Segunda línea, soportado por evidencia moderada |
| **III** | Evidencia insuficiente — rol óptimo no establecido |
| **IV** | Evidencia de daño o sin beneficio — NO recomendado |
""")
        st.divider()

        st.markdown("#### 🔴 Categoría I — Primera línea (nefrología y relacionadas)")
        st.markdown("""
| Diagnóstico | Indicación | Reemplazo | Notas |
|-------------|-----------|-----------|-------|
| **PTT** (Púrpura Trombocitopénica Trombótica) | Urgencia | **PFC** | Iniciar <4h del diagnóstico. ADAMTS13 antes de empezar. |
| **Enfermedad anti-MBG / Goodpasture** | Con hemorragia pulmonar o Cr <6 mg/dL | Albúmina | No evidencia si dialisis-dependiente y sin hemorragia |
| **GNRP** (rápidamente progresiva, anti-MBG+) | Sí | Albúmina/PFC | Combinada con inmunosupresión |
| **FSGS recurrente post-trasplante** | Sí | Albúmina | Inicio temprano mejora respuesta |
| **ANCA vasculitis** (Cr >5.7 o diálisis) | Sí | Albúmina | PEXIVAS trial: beneficio en hemorragia alveolar |
| **Rechazo mediado por Ac (AMR)** | Sí | Albúmina | Con rituximab e IVIG |
| **Miastenia gravis — crisis** | Sí | Albúmina | Alternativa a IVIG; efecto más rápido |
| **AIDP / Guillain-Barré (grave)** | Sí | Albúmina o PFC | Equivalente a IVIG en formas graves |
| **Hiperviscosidad (Waldenström)** | Sí | Albúmina | Alivio sintomático inmediato |
""")

        st.markdown("#### 🟡 Categoría II — Segunda línea")
        st.markdown("""
| Diagnóstico | Notas |
|-------------|-------|
| **Crioglobulinemia grave** (vasculitis activa) | Útil en crisis. Reemplazo con albúmina caliente (37°C) |
| **HUS atípico** (resistente a eculizumab) | Antes de disponibilidad de eculizumab |
| **SHU-STEC** (Síndrome urémico hemolítico) | En adultos con afección neurológica grave |
| **NMO** (Neuromielitis óptica, aguda) | Cuando falla esteroide IV |
| **CIDP** (Polineuropatía desmielinizante crónica) | Mantenimiento en casos refractarios |
| **Inhibidores de factores de coagulación** | Factor VIII, Factor V |
""")

        st.markdown("#### ⚪ Categoría III — Evidencia insuficiente")
        st.markdown("""
| Diagnóstico | Notas |
|-------------|-------|
| **Lupus eritematoso sistémico grave** | Sin beneficio sostenido; puede usarse en crisis severas |
| **Nefropatía membranosa** refractaria | Algunos reportes favorables |
| **Síndrome antifosfolípido catastrófico** | Como terapia de rescate |
| **Sepsis / Falla multiorgánica** | Sin beneficio en grandes ensayos |
""")

        st.markdown("#### ⛔ Categoría IV — No recomendado")
        st.markdown("""
| Diagnóstico | Razón |
|-------------|-------|
| **Nefropatía por IgA** | Sin beneficio demostrado |
| **Nefritis lúpica** (sin crisis) | Mejor con inmunosupresión sola |
| **Enfermedad de Alzheimer** | Sin evidencia |
| **Esclerosis lateral amiotrófica** | Sin beneficio |
""")

        st.info("📖 Referencia: Schwartz J et al. *Guidelines on the Use of Therapeutic Apheresis in Clinical Practice* — Evidence-Based Approach from the Writing Committee of the American Society for Apheresis (ASFA). J Clin Apheresis 2023.")

    elif tpe_modo == "🔬 Mecanismo por indicación":
        st.markdown("### 🔬 Fisiopatología — ¿Por qué funciona la TPE?")
        st.caption("Entender el mecanismo es clave para saber cuándo indicarla, con qué reemplazo y por cuánto tiempo.")

        diag_sel = st.selectbox("Selecciona diagnóstico", [
            "PTT — Púrpura Trombocitopénica Trombótica",
            "Enfermedad anti-MBG / Goodpasture",
            "Vasculitis ANCA (con Cr >5.7 o hemorragia alveolar)",
            "FSGS recurrente post-trasplante",
            "AMR — Rechazo mediado por anticuerpos",
            "Miastenia gravis — Crisis",
            "AIDP / Guillain-Barré grave",
            "Hiperviscosidad — Waldenström",
            "Crioglobulinemia grave",
        ], key="tpe_diag_mec")

        mecanismos = {
            "PTT — Púrpura Trombocitopénica Trombótica": {
                "patofis": """
**Deficiencia de ADAMTS13** (congénita o por anticuerpos adquiridos, IgG inhibidores):
- ADAMTS13 normalmente degrada los **multímeros ultra-largos de FvW** (ULvWF)
- Sin ADAMTS13 → ULvWF se acumulan en endotelio → activan y agregan plaquetas
- → Microtrombos de plaquetas + fibrina → isquemia en cerebro, riñón, corazón
- → Consumo de plaquetas → trombocitopenia + hemólisis microangiopática (MAHA)
                """,
                "mecanismo_tpe": """
La TPE actúa por **doble mecanismo**:
1. **Remueve:** anticuerpos anti-ADAMTS13 (IgG) + ULvWF + citocinas inflamatorias
2. **Aporta:** ADAMTS13 funcional contenido en el PFC (plasma fresco congelado)
                """,
                "reemplazo": "🔴 **PFC OBLIGATORIO** — No usar albúmina. El PFC aporta ADAMTS13.",
                "frecuencia": "Diario hasta remisión (plaquetas >150,000 × 2 días consecutivos)",
                "meta": "Plaquetas >150,000, LDH normal, ausencia de síntomas neurológicos",
                "ref": "ASFA Cat I | George JN, NEJM 2019"
            },
            "Enfermedad anti-MBG / Goodpasture": {
                "patofis": """
**Anticuerpos IgG** contra la **cadena α3 del colágeno tipo IV** de la membrana basal glomerular (y alveolar):
- Activación del complemento → inflamación → necrosis fibrinoide glomerular
- Resultado: **GNRP** (glomerulonefritis rápidamente progresiva) + hemorragia pulmonar
- Diagnóstico: anti-MBG+ en sangre; inmunofluorescencia lineal en biopsia renal
                """,
                "mecanismo_tpe": """
TPE remueve los **anticuerpos anti-MBG circulantes (IgG)**:
- Reducción rápida del título de anticuerpos antes de que causen daño irreversible
- Especialmente útil si creatinina <6 mg/dL o hay hemorragia pulmonar activa
- Sin beneficio demostrado si el paciente ya es diálisis-dependiente sin hemorragia pulmonar
                """,
                "reemplazo": "✅ **Albúmina 5%** (excepto si hay hemorragia pulmonar activa → alternar con PFC)",
                "frecuencia": "Diario × 14 días o hasta anti-MBG negativo",
                "meta": "Anti-MBG indetectable, estabilización de función renal",
                "ref": "ASFA Cat I | Jayne DR, JASN 2007"
            },
            "Vasculitis ANCA (con Cr >5.7 o hemorragia alveolar)": {
                "patofis": """
**Anticuerpos ANCA** (anti-PR3 o anti-MPO) activan neutrófilos circulantes:
- Neutrófilos activados → degranulación → daño endotelial → vasculitis necrotizante
- Predomina en capilares glomerulares (→ GNRP) y alveolares (→ hemorragia)
- Histología: vasculitis pauciinmune (poca o sin depósito de Ig en biopsia)
                """,
                "mecanismo_tpe": """
TPE remueve **ANCA circulantes** y citocinas inflamatorias:
- Evidencia: estudio PEXIVAS (2019) — beneficio principalmente en **hemorragia alveolar difusa**
- En pacientes con Cr >5.7 sin hemorragia: beneficio renal modesto, sin impacto en mortalidad
- Complementaria a inmunosupresión (ciclofosfamida + prednisona)
                """,
                "reemplazo": "✅ **Albúmina 5%** (alternar con PFC si hay hemorragia alveolar activa)",
                "frecuencia": "Cada día o cada tercer día × 7 sesiones en 2 semanas",
                "meta": "Control de hemorragia, mejoría de creatinina, ANCA en descenso",
                "ref": "ASFA Cat I | Walsh M (PEXIVAS), NEJM 2020"
            },
            "FSGS recurrente post-trasplante": {
                "patofis": """
**Factor de permeabilidad circulante** (candidatos: suPAR, CLCF-1, anti-CD40):
- Induce **daño podocitario** → fusión de procesos podocitarios → proteinuria masiva
- La FSGS primaria recurre en 20–40% de trasplantes, especialmente en FSGS de inicio temprano
- Recurre horas a días post-trasplante si el factor circulante está presente
                """,
                "mecanismo_tpe": """
TPE remueve el **factor de permeabilidad circulante**:
- Inicio temprano (primeras horas-días post-trasplante) mejora la respuesta
- Puede combinarse con rituximab para reducir la producción del factor
- Criterio de respuesta: disminución de proteinuria >50% del basal
                """,
                "reemplazo": "✅ **Albúmina 5%**",
                "frecuencia": "Diario × 5–10 sesiones iniciales; luego espaciar según respuesta",
                "meta": "Proteinuria <1g/día o reducción >50%, función del injerto estable",
                "ref": "ASFA Cat I | Ponticelli C, CJASN 2010"
            },
            "AMR — Rechazo mediado por anticuerpos": {
                "patofis": """
**Anticuerpos donante-específicos (DSA)** contra antígenos HLA del donante:
- DSA activan complemento (C1q, C3d, C4d) → depósito en capilares peritubulares
- → Inflamación microvascular → disfunción y pérdida del injerto
- AMR agudo: dentro de 1 año; crónico: evolución insidiosa
                """,
                "mecanismo_tpe": """
TPE remueve **DSA circulantes** rápidamente:
- Combinada con IVIG (inhibe complemento + modulación inmune) y rituximab (deplección B)
- La sola remoción de DSA sin inmunosupresión resulta en rebote rápido
- Respuesta evaluada por DSA en MFI post-sesión
                """,
                "reemplazo": "✅ **Albúmina 5%**",
                "frecuencia": "Cada día o cada tercer día × 5–10 sesiones",
                "meta": "↓DSA >50% en MFI, mejoría de biopsia, estabilización de creatinina",
                "ref": "ASFA Cat I | Montgomery RA, NEJM 2011"
            },
            "Miastenia gravis — Crisis": {
                "patofis": """
**Anticuerpos IgG** contra el **receptor de acetilcolina (AChR)** o contra MuSK:
- Bloquean y destruyen la unión neuromuscular (UNM)
- → Debilidad muscular fluctuante, ptosis, diplopía, disfagia, insuficiencia respiratoria
- Crisis miasténica: insuficiencia respiratoria que requiere ventilación o riesgo de ella
                """,
                "mecanismo_tpe": """
TPE remueve **anticuerpos anti-AChR / anti-MuSK**:
- Efecto más rápido que IVIG (días vs 1–2 semanas)
- Equivalente a IVIG en eficacia a corto plazo (MGTX trial)
- No modifica la historia natural — requiere inmunosupresión de mantenimiento
                """,
                "reemplazo": "✅ **Albúmina 5%**",
                "frecuencia": "Cada día o cada tercer día × 5–6 sesiones (crisis) o pre-timectomía",
                "meta": "Mejoría clínica, extubación, puntaje MG-ADL",
                "ref": "ASFA Cat I | Barth D (MGTX), Neurology 2011"
            },
            "AIDP / Guillain-Barré grave": {
                "patofis": """
**Respuesta autoinmune** post-infecciosa (Campylobacter, CMV, EBV, SARS-CoV-2) contra **gangliósidos** del nervio periférico:
- Anticuerpos + complemento → desmielinización + daño axonal
- Presentación: parálisis ascendente simétrica, arreflexia, posible falla respiratoria
- Subtipos: AIDP (desmielinizante), AMAN/AMSAN (axonal — peor pronóstico)
                """,
                "mecanismo_tpe": """
TPE remueve **anticuerpos antigangliosídicos** y mediadores inflamatorios:
- Equivalente a IVIG en formas graves (ensayos controlados)
- No combinar TPE + IVIG simultáneamente (la IVIG se elimina en la sesión de TPE)
- Inicio temprano (<2 semanas del inicio) → mejor respuesta
                """,
                "reemplazo": "✅ **Albúmina 5%** (o parte con PFC para reponer factores de coagulación)",
                "frecuencia": "Cada día o cada tercer día × 4–6 sesiones",
                "meta": "Mejoría en escala funcional GBS, evitar VMI o reducir duración",
                "ref": "ASFA Cat I | French GBS Group, Ann Neurol 1997"
            },
            "Hiperviscosidad — Waldenström": {
                "patofis": """
**Exceso de IgM monoclonal** (gammapatía de células B linfoplasmocíticas):
- IgM es una macroglobulina (alto peso molecular, >900 kDa) — mayoritariamente **intravascular**
- → Hiperviscosidad sérica → enlentecimiento de flujo → síntomas: visión borrosa, sangrado, cefalea, confusión
- El compartimento intravascular de IgM es ~80% (a diferencia de IgG que es 50%)
                """,
                "mecanismo_tpe": """
TPE remueve **IgM intravascular** de forma muy eficiente:
- Una sesión puede reducir IgM 30–60% (excelente porque es mayormente intravascular)
- Alivio sintomático casi inmediato (horas)
- No es curación — la producción continúa → requiere quimioterapia (rituximab, bortezomib)
- TPE como puente hasta que la quimioterapia surta efecto
                """,
                "reemplazo": "✅ **Albúmina 5%**",
                "frecuencia": "Diario × 3–5 sesiones o hasta remisión sintomática",
                "meta": "Viscosidad sérica <4 cP, resolución de síntomas",
                "ref": "ASFA Cat I | Kwaan HC, Semin Thromb Hemost 2003"
            },
            "Crioglobulinemia grave": {
                "patofis": """
**Crioglobulinas** (Ig que precipitan a <37°C) → vasculitis de pequeño vaso:
- Tipo I: IgM monoclonal (Waldenström) — hiperviscosidad
- Tipo II/III: IgM + IgG (mixta) — asociada a VHC en 80–90% → vasculitis, neuropatía, glomerulonefritis
- Activan complemento → inflamación → depósitos en glomérulos, piel, nervios
                """,
                "mecanismo_tpe": """
TPE remueve **crioglobulinas circulantes** antes de que precipiten:
- Circuito y líquido de reemplazo deben mantenerse **a 37–39°C** para evitar precipitación en el circuito
- Combinada con inmunosupresión (rituximab) y tratamiento del VHC si aplica
                """,
                "reemplazo": "✅ **Albúmina 5% calentada a 37°C** — crítico para evitar precipitación en el circuito",
                "frecuencia": "Cada día o cada tercer día × 3–8 sesiones según severidad",
                "meta": "Mejoría de vasculitis, reducción de crioglobulinas, función renal estable",
                "ref": "ASFA Cat II | Ramos-Casals M, Medicine 2003"
            },
        }

        if diag_sel in mecanismos:
            m = mecanismos[diag_sel]
            st.markdown("#### 🔴 Fisiopatología")
            st.markdown(m["patofis"])
            st.markdown("#### 🔵 Mecanismo de acción de la TPE")
            st.markdown(m["mecanismo_tpe"])
            mc1, mc2, mc3 = st.columns(3)
            mc1.info(f"**Líquido de reemplazo:** {m['reemplazo']}")
            mc2.info(f"**Frecuencia:** {m['frecuencia']}")
            mc3.info(f"**Meta:** {m['meta']}")
            st.caption(f"📖 {m['ref']}")

    # ── ANTICOAGULACIÓN ACD-A ──────────────────────────────────────────────────
    elif tpe_modo == "💉 Anticoagulación ACD-A":
        st.markdown("### Anticoagulación con ACD-A (Anticoagulant Citrate Dextrose A)")
        st.caption("Anticoagulación estándar en plasmaféresis. Quelación de calcio en circuito.")

        st.info("""
**Composición ACD-A:** Citrato trisódico 22 g/L + Ácido cítrico 8 g/L + Dextrosa 24.5 g/L
→ Citrato ≈ **113 mmol/L** · Na ≈ **224 mmol/L**
        """)

        ac1, ac2 = st.columns(2)
        with ac1:
            qb_acd = st.number_input("Flujo sanguíneo QB (mL/min)", 30, 150, 60, 5, key="acd_qb")
            ratio_acd = st.selectbox("Ratio ACD-A : Sangre",
                                     ["1:8 (12.5%)", "1:10 (10%)", "1:12 (8.3%)", "1:16 (6.3%)"],
                                     index=2, key="acd_ratio",
                                     help="Estándar: 1:12. Mayor anticoagulación: 1:8")
        with ac2:
            vol_sesion = st.number_input("Volumen total de la sesión (mL)", 500, 10000,
                                         int(result_tpe['vol_ex']) if 'result_tpe' in dir() else 2000,
                                         100, key="acd_vol")

        ratio_num = int(ratio_acd.split(":")[1].split(" ")[0])
        acd_rate_min = qb_acd / ratio_num
        acd_rate_hr = acd_rate_min * 60
        acd_total = (vol_sesion / (qb_acd * 60)) * acd_rate_hr if qb_acd > 0 else 0

        ar1, ar2, ar3 = st.columns(3)
        ar1.metric("Tasa ACD-A (mL/min)", f"{acd_rate_min:.1f}")
        ar2.metric("Tasa ACD-A (mL/hr)", f"{acd_rate_hr:.0f}")
        ar3.metric("Volumen ACD-A en sesión (mL)", f"{acd_total:.0f}")

        st.divider()
        st.markdown("### Reposición de calcio durante TPE")
        st.caption("El ACD-A quela Ca²⁺ sistémico. Monitorear iCa cada 30–60 min. Reponer si síntomas o iCa <1.0.")

        profilaxis = st.radio("Estrategia de calcio",
                              ["Profiláctico", "Solo si sintomático / iCa <1.0"],
                              horizontal=True, key="acd_ca_strat")

        if profilaxis == "Profiláctico":
            ca_prof1, ca_prof2 = st.columns(2)
            with ca_prof1:
                st.markdown("**Esquema profiláctico habitual:**")
                st.markdown("""
- 1 g Gluconato Ca 10% IV (10 mL) por cada 1,000 mL de ACD-A infundido
- ó 1 g Gluconato Ca 10% IV por cada 250 mL de plasma intercambiado
- Infundir lento (IV directa en 10 min o diluido)
                """)
            with ca_prof2:
                dosis_ca_total = acd_total / 1000  # g gluconato (1g por 1000mL ACD-A)
                ampulas_ca_prof = math.ceil(dosis_ca_total)
                st.metric("Gluconato Ca 10% estimado para sesión",
                          f"{ampulas_ca_prof} ámpulas de 10mL",
                          help=f"1 ámpula (1g) por cada 1000mL ACD-A ({acd_total:.0f} mL total)")
        else:
            st.markdown("""
**Tratar síntomas de hipocalcemia:**
- Parestesias peribucales, hormigueo dedos, calambres → **1 g Gluconato Ca IV lento**
- Tetania, Chvostek/Trousseau positivo → **2 g Gluconato Ca IV** en 10 min
- Repetir según respuesta clínica e iCa
            """)

        st.divider()
        st.markdown("### Síntomas de toxicidad por citrato (ACD-A)")
        st.markdown("""
| Grado | Síntomas | Acción |
|-------|----------|--------|
| **Leve** | Parestesias periorales, hormigueo | ↓ flujo ACD-A 10–20%, Ca IV |
| **Moderado** | Calambres, náusea, ansiedad | Pausar 5 min, Ca IV 1–2g, reiniciar a flujo menor |
| **Grave** | Tetania, arritmia, hipotensión | Suspender, Ca IV urgente, monitoreo cardíaco |
        """)

    elif tpe_modo == "📋 Monitoreo y contraindicaciones":
        st.markdown("### 🔬 Monitoreo durante TPE")
        st.markdown("""
| Momento | Parámetro | Acción si anormal |
|---------|-----------|------------------|
| **Pre-sesión** | PA, FC, saturación, peso, T° | Suspender si PA <90/60 o inestabilidad |
| **Pre-sesión** | BH, plaquetas, TP/TTP, fibrinógeno | Documentar basal |
| **Pre-sesión** | iCa, Na, K, Mg | Corregir hipocalcemia antes de iniciar |
| **Cada 15–30 min** | PA, FC, saturación | Cualquier deterioro → pausar |
| **Cada 30–60 min** | iCa (si usa ACD-A) | iCa <1.0 → Ca IV |
| **Al terminar** | PA, FC, peso, iCa | Documentar tolerancia |
| **Post-sesión** | BH, plaquetas, fibrinógeno, TP | Evaluar efecto del intercambio |
| **Post-sesión (TTP)** | ADAMTS13, LDH, esquistocitos | Guía para próxima sesión |
        """)

        st.divider()
        st.markdown("### ⛔ Contraindicaciones")
        ct1, ct2 = st.columns(2)
        with ct1:
            st.markdown("**Absolutas:**")
            st.markdown("""
- Inestabilidad hemodinámica no controlada
- Sin acceso vascular adecuado
- Alergia grave al líquido de reemplazo (anafilaxia a albúmina o PFC)
- Coagulación intravascular diseminada activa (CID) ← relativa
            """)
        with ct2:
            st.markdown("**Relativas:**")
            st.markdown("""
- Hipocalcemia severa no corregida
- Hipotensión activa
- Sangrado activo (valorar PFC como reemplazo)
- Anticoagulación sistémica concomitante (ajustar ACD-A)
- Trombocitopenia grave (<20,000) ← valorar riesgo/beneficio
- Embarazo (no es contraindicación absoluta, valorar)
            """)

        st.divider()
        st.markdown("### 📋 Acceso vascular recomendado")
        st.markdown("""
| Tipo | Flujo posible | Comentario |
|------|--------------|------------|
| **Catéter venoso central** (≥11Fr, doble lumen) | 60–120 mL/min | Preferido. Femoral o yugular. |
| **AV fístula madura** | 80–150 mL/min | Excelente si disponible |
| **Catéter periférico** | <60 mL/min | Solo para sesiones urgentes cortas |
| **Puerto implantable** | Variable | No recomendado para flujos altos |
        """)

        st.divider()
        st.markdown("### ⚠️ Complicaciones frecuentes")
        st.markdown("""
| Complicación | Frecuencia | Manejo |
|-------------|-----------|--------|
| Hipocalcemia (por ACD-A) | 5–10% | Ca IV según síntomas |
| Hipotensión | 3–8% | Carga de fluidos, ↓ flujo |
| Reacción alérgica (PFC) | 1–3% | Antihistamínico, esteroide; suspender si grave |
| Sangrado del acceso | 2–5% | Compresión local, ajustar anticoagulación |
| Hipotermia | Poco frecuente | Calentar líquido de reemplazo |
| Embolia aérea | Raro | Posición Trendelenburg, O₂ |
        """)

        st.info("📖 ASFA 2023 | KDIGO 2021 | British Society for Haematology Guidelines on Therapeutic Apheresis")



# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: KT/V POR OBJETIVOS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "ktv":
    st.subheader("Dosis por objetivos (Kt/V urea — TRRC)")
    V = st.number_input("Volumen de distribución V (L) ≈ 0.6×peso", value=round(0.6 * peso, 1),
                        step=0.1)
    C0 = st.number_input("Urea inicial C0 (mg/dL)", value=150.0, step=1.0)
    Ct = st.number_input("Urea objetivo Ct (mg/dL)", value=100.0, step=1.0)
    horas = st.number_input("Tiempo de tratamiento (h)", value=24, step=1)
    E = st.number_input("Eficiencia del sistema (0.8–1.0)", value=0.9, step=0.05,
                        min_value=0.5, max_value=1.0)
    ktv_req = log(C0 / Ct) if (C0 > 0 and Ct > 0 and C0 > Ct) else None
    st.metric("Kt/V requerido", f"{ktv_req:.2f}" if ktv_req else "—")
    K_Lh = ((ktv_req * V) / horas) / E if ktv_req else None
    dosis_calc = (K_Lh * 1000) / peso if K_Lh and peso > 0 else None
    colx, coly = st.columns(2)
    colx.metric("K requerido (L/h)", f"{K_Lh:.2f}" if K_Lh else "—")
    coly.metric("Dosis estimada (mL/kg/h)", f"{dosis_calc:.1f}" if dosis_calc else "—")
    if dosis_calc:
        if dosis_calc < 20:
            st.warning(f"⚠️ Dosis {dosis_calc:.1f} mL/kg/h < 20. Considerar aumentar.")
        elif dosis_calc > 35:
            st.info(f"ℹ️ Dosis {dosis_calc:.1f} mL/kg/h > 35. Sin evidencia de beneficio adicional.")
        else:
            st.success(f"✅ Dosis {dosis_calc:.1f} mL/kg/h dentro del rango 20–35.")
    st.caption("Relación entre Kt/V objetivo y dosis de efluente (ver Referencias).")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7: BALANCE DINÁMICO
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "bal":
    st.subheader("Balance dinámico y metas de UF")
    peso_seco = st.number_input("Peso seco objetivo (kg)", value=max(0.0, peso - 5), step=0.5)
    fo_actual = (peso - peso_seco) / peso_seco if peso_seco > 0 else 0.0
    fo_obj = st.number_input("FO% objetivo (p. ej. 0.05 = 5%)", value=0.05, step=0.01)
    horas_trrc = st.number_input("Horas de TRRC planificadas (h)", value=24, step=1)
    ingresos = st.number_input("Ingresos previstos (mL)", value=0, step=50)
    uresis_res = st.number_input("Uresis residual 24h (mL)",
                                 value=int(st.session_state.get("ur_main", 0)), step=50)
    uf_obj = ((peso - (1 + fo_obj) * peso_seco) * 1000) if peso_seco > 0 else None
    uf_mant = ingresos - uresis_res
    uf_total = (uf_obj if uf_obj is not None else 0) + uf_mant
    uf_h = uf_total / horas_trrc if horas_trrc > 0 else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FO% actual", f"{fo_actual:.1%}")
    c2.metric("UF objetivo (mL)", f"{int(uf_obj) if uf_obj is not None else 0}")
    c3.metric("UF total 24h (mL)", f"{int(uf_total)}")
    c4.metric("UF/h sugerida", f"{int(uf_h)}")
    ratio_uf_peso = uf_h / max(float(peso), 1e-9)
    if ratio_uf_peso > 0.002:
        st.warning(f"⚠️ UF/h > 2 mL/kg/h ({ratio_uf_peso * 1000:.1f} mL/kg/h). Evaluar tolerancia hemodinámica.")
    else:
        st.success(f"✅ UF/h aceptable ({ratio_uf_peso * 1000:.1f} mL/kg/h).")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8: ANTICOAGULACIÓN EXTENDIDA
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "anticoag":
    st.subheader("Anticoagulación — Evaluación extendida")
    colA, colB, colC, colD = st.columns(4)
    plaquetas = colA.number_input("Plaquetas (mil/µL)", 0, 1000, 200, 5)
    fib = colB.number_input("Fibrinógeno (mg/dL)", 0, 1000, 300, 10)
    sangrado = colC.selectbox("Sangrado activo", ["No", "Sí"])
    neuro = colD.selectbox("Post-op neuro / riesgo alto", ["No", "Sí"])
    inr = colA.number_input("INR", 0.8, 5.0, 1.1, 0.1, key="inr_ext")
    aptt = colB.number_input("aPTT (s)", 20.0, 120.0, 35.0, 1.0, key="aptt_ext")
    hbpm_12h = colC.selectbox("HBPM en últimas 12h", ["No", "Sí"],
                               help="Si 'Sí', preferir RCA o iniciar HNF con precaución.")
    hit_previa = colD.selectbox("Antecedente de HIT", ["No", "Sí"])
    st.session_state["hit_previa_bool"] = (hit_previa == "Sí")

    usar_rca = (plaquetas < 50 or fib < 150 or sangrado == "Sí" or neuro == "Sí" or
                inr >= 1.5 or aptt >= 45 or hbpm_12h == "Sí" or hit_previa == "Sí")
    ac = "RCA (citrato)" if usar_rca else "Heparina no fraccionada (HNF)"
    st.success(f"Anticoagulación sugerida: **{ac}**")
    st.caption("RCA es preferente si no hay contraindicaciones. "
               "Para cálculo detallado de citrato → 🧪 Citrato RCA.")

    if ac.startswith("Heparina"):
        if hbpm_12h == "Sí":
            st.warning("HBPM reciente: considerar diferir HNF o iniciar con dosis reducida.")
        iu_h = peso * 5
        st.info(f"**Dosis inicial HNF sugerida:** {iu_h:.0f} UI/h (ajustar a aPTT objetivo).")
        st.session_state["anticoagulacion_tipo"] = "HNF"
        st.session_state["hnf_ui_h"] = float(iu_h)

        # ── NOMOGRAMA HNF COMPLETO ─────────────────────────────────────────
        st.divider()
        st.markdown("### 📊 Nomograma HNF para TRRC")
        st.caption("Objetivo aPTT en TRRC: **45–80 segundos** (anticoagulación moderada). "
                   "Más conservador que anticoagulación terapéutica sistémica.")

        hn1, hn2 = st.columns(2)
        with hn1:
            aptt_actual = st.number_input("aPTT actual (s)", 20.0, 200.0,
                                          float(aptt), 1.0, key="hnf_aptt_nom")
            dosis_actual_hnf = st.number_input("Dosis HNF actual (UI/hr)", 0.0, 5000.0,
                                               float(iu_h), 50.0, key="hnf_dosis_act")
        with hn2:
            tipo_bolo = st.selectbox("¿Incluir bolo inicial?",
                                     ["No (riesgo de sangrado)", "Sí — 25 UI/kg", "Sí — 50 UI/kg"],
                                     key="hnf_bolo")

        # Calculate adjustment
        if aptt_actual < 45:
            ajuste = "+2–3 UI/kg/hr"
            delta_ui = 2.5 * peso
            bolo = ""
            if aptt_actual < 35:
                bolo = f"+ Bolo 1,000–2,000 UI"
            accion = f"⬆️ **AUMENTAR** {delta_ui:.0f} UI/hr (nueva dosis ≈ {dosis_actual_hnf + delta_ui:.0f} UI/hr). {bolo}"
            color = "warning"
        elif aptt_actual <= 60:
            accion = "✅ **MANTENER** dosis actual — aPTT en objetivo bajo (45–60s)"
            color = "success"
        elif aptt_actual <= 80:
            accion = "✅ **MANTENER** dosis actual — aPTT en objetivo óptimo (61–80s)"
            color = "success"
        elif aptt_actual <= 100:
            delta_ui = 1.5 * peso
            accion = f"⬇️ **REDUCIR** {delta_ui:.0f} UI/hr (nueva dosis ≈ {max(0, dosis_actual_hnf - delta_ui):.0f} UI/hr)"
            color = "warning"
        elif aptt_actual <= 120:
            delta_ui = 2.5 * peso
            accion = (f"⬇️ **PAUSAR 30 min** → reducir {delta_ui:.0f} UI/hr "
                     f"(nueva dosis ≈ {max(0, dosis_actual_hnf - delta_ui):.0f} UI/hr). Repetir aPTT en 4h.")
            color = "error"
        else:
            accion = (f"🛑 **PAUSAR 60 min** → reducir {2.5*peso:.0f} UI/hr. "
                     f"Monitoreo estrecho. Si sangrado activo: protamina.")
            color = "error"

        if color == "success":
            st.success(accion)
        elif color == "warning":
            st.warning(accion)
        else:
            st.error(accion)

        st.markdown("""
| aPTT (segundos) | Acción | Bolo | Cambio de dosis |
|----------------|--------|------|----------------|
| **<35** | Aumentar urgente | 2,000 UI | +3 UI/kg/hr |
| **35–44** | Aumentar | 1,000 UI | +2 UI/kg/hr |
| **45–60** | Mantener (objetivo bajo) | No | Sin cambio |
| **61–80** | Mantener (objetivo óptimo) | No | Sin cambio |
| **81–100** | Reducir ligeramente | No | −1.5 UI/kg/hr |
| **101–120** | Pausar + reducir | No | Pausar 30 min; −2.5 UI/kg/hr |
| **>120** | Pausar + reducir mayor | No | Pausar 60 min; −2.5 UI/kg/hr |
        """)

        st.markdown("**Frecuencia de monitoreo:**")
        st.markdown("""
- Primera aPTT: **4–6 horas** después de iniciar o cambiar dosis
- Hasta 2 controles consecutivos en rango → cada **12 horas**
- Estable >24h → cada **24 horas**
- Siempre post-ajuste: repetir a las **4 horas**
        """)

        if tipo_bolo != "No (riesgo de sangrado)":
            bolo_ui = 25 * peso if "25" in tipo_bolo else 50 * peso
            st.info(f"💉 **Bolo inicial:** {bolo_ui:.0f} UI IV directo, luego iniciar infusión a {iu_h:.0f} UI/hr")

        with st.expander("🔬 Anti-Xa como alternativa al aPTT"):
            st.markdown(f"""
**Anti-Xa para monitoreo de HNF en TRRC:**
- Meta: **0.3–0.7 UI/mL** (anticoagulación moderada para TRRC)
- Ventaja: No afectado por factor VIII elevado, lupus anticoagulante o coagulopatías
- Tomar muestra: **4–6h** después de iniciar o cambiar dosis, en estado estable
- Ajuste: mismo nomograma de aPTT como referencia; usar anti-Xa para confirmar

**Conversión aproximada:**
- Anti-Xa 0.3 UI/mL ≈ aPTT 45–50s
- Anti-Xa 0.5 UI/mL ≈ aPTT 60–70s
- Anti-Xa 0.7 UI/mL ≈ aPTT 80–90s
            """)
    else:
        st.info("💡 Dirígete a la pestaña **🧪 Citrato RCA** para el cálculo completo de tasas y monitoreo.")
        st.session_state["anticoagulacion_tipo"] = "RCA"

# ══════════════════════════════════════════════════════════════════════════════
# TAB 9: FUNDAMENTO Y CÁLCULOS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "fund":
    st.subheader("Fundamento y Cálculos — Transparencia pedagógica")
    mostrar_ext = bool(st.session_state.get("mostrar_fund_extendido", False))
    if mostrar_ext:
        st.info("Vista extendida ACTIVADA (switch global en barra lateral).")

    mod_for_fund, filtro_for_fund, _ = combinar_recomendaciones(escenarios)
    filtro_for_fund = st.session_state.get("ui_filtro", filtro_for_fund)
    qp_f, qp_h_f, qe_f, qr_pre_f, qr_post_f, qd_f, ff_f = flows_and_ff(
        qb, hto, dosis_mlkg, peso, uf, mod_for_fund or "CVVHDF")

    st.markdown("### Fórmulas TRRC (LaTeX)")
    st.latex(r"Q_p = Q_b \times (1 - Hto)")
    st.latex(r"Q_{p,h} = Q_p \times 60 \quad \text{(mL/h)}")
    st.latex(r"Q_e = \text{dosis}_{mL/kg/h} \times \text{peso}_{kg}")
    st.latex(r"FF = \frac{Q_{r,post} + UF}{Q_{p,h} + Q_{r,pre}} < 25\%")
    st.latex(r"Q_{r,total} = \min(0.25 \cdot Q_{p,h},\ \max(Q_e - UF, 0)) \times f_{conv}")
    st.latex(r"Q_d = \max(Q_e - Q_{r,pre} - Q_{r,post} - UF,\ 0)")

    st.markdown("### Citrato RCA")
    st.latex(r"\dot{V}_{cit} = \frac{D_{obj}[mmol/L] \times Q_b[mL/min] \times 60}{[Cit][mmol/L]}")
    st.latex(r"\text{Carga al circuito} = \dot{V}_{cit} \times [Cit]/1000 \quad [mmol/h]")
    st.latex(r"\text{Remoción} = Q_{eff} \times [Cit]_{circuito}/1000 \quad [mmol/h]")
    st.latex(r"\frac{Ca_{total}}{Ca_{i\acute{o}nico}} > 2.5 \Rightarrow \text{Acumulación de citrato}")

    st.markdown("### HD — Ecuación de Michaels")
    st.latex(r"K = Q_B \cdot \frac{1 - e^{-\alpha(1-r)}}{1 - r \cdot e^{-\alpha(1-r)}}")
    st.latex(r"\alpha = KoA/Q_B \quad r = Q_B/Q_D")
    st.latex(r"Kt/V = K \cdot t_{min} / V_{mL}")

    st.markdown("### Plasmaféresis")
    st.latex(r"VPE = 65 \times peso \times (1 - Hto)")
    st.latex(r"C_{res}^{1\,ses} = e^{-n_{recambios}} \times 100\%")
    st.latex(r"C_{res}^{total} = (0.55 + 0.45 \cdot e^{-n_{rec}})^{n_{ses}} \times 100\%")

    st.markdown("### Sustitución numérica (valores actuales TRRC)")
    nc1, nc2, nc3 = st.columns(3)
    with nc1:
        st.write(f"**Qb** = {int(qb)} mL/min")
        st.write(f"**Hto** = {hto:.2f}")
        st.write(f"**Qp** = {int(qp_f)} mL/min")
        st.write(f"**Qp·h** = {int(qp_h_f)} mL/h")
    with nc2:
        st.write(f"**Dosis** = {int(dosis_mlkg)} mL/kg/h")
        st.write(f"**Peso** = {peso:.1f} kg")
        st.write(f"**Qe** = {int(qe_f)} mL/h")
        st.write(f"**UF** = {int(uf)} mL/h")
    with nc3:
        st.write(f"**Qr_pre** = {int(qr_pre_f)} mL/h")
        st.write(f"**Qr_post** = {int(qr_post_f)} mL/h")
        st.write(f"**Qd** = {int(qd_f)} mL/h")
        st.write(f"**FF** ≈ {ff_f:.2%}")

    if mostrar_ext:
        st.divider()
        st.markdown("### Fundamento clínico extendido")
        for linea in _fundamento_texto_extendido(
                na=float(st.session_state.get("na_main", 140.0)),
                k=float(st.session_state.get("k_main", 4.0)),
                ph=float(st.session_state.get("ph_main", 7.35)),
                pam=float(st.session_state.get("pam", 65.0)),
                vasopresor_alto=st.session_state.get("vaso_alto_sel", "No") == "Sí",
                lactato_desc=st.session_state.get("lactato_desc_sel", "No") == "Sí",
                albumina=float(st.session_state.get("alb_main", 3.0)),
                anticoag_tipo=st.session_state.get("anticoagulacion_tipo", "—"),
                r_targets=st.session_state.get("rca_targets", {}),
                filtro_final=filtro_for_fund):
            if linea:
                st.write(linea)
            else:
                st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 10: RESUMEN / IMPRESIÓN (unificado: orden enfermería + PDF)
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "resumen":
    st.subheader("📋 Resumen Clínico / Orden de Enfermería / Impresión")
    st.caption("Completa todos los campos y luego genera el PDF. "
               "Este documento integra prescripción, anticoagulación y monitoreo en un solo lugar.")

    # ── Sección 1: Identificación ─────────────────────────────────────────────
    st.markdown("### 👤 Identificación del paciente")
    idU, _ = st.columns([3, 1])
    with idU:
        st.text_input("Unidad hospitalaria", key="rx_unidad",
                      value=st.session_state.get("rx_unidad", ""))
    id1, id2, id3 = st.columns([2, 1, 1])
    with id1:
        st.text_input("Nombre del paciente", key="rx_nombre_paciente",
                      value=st.session_state.get("rx_nombre_paciente", ""))
    with id2:
        st.text_input("Fecha de nacimiento", key="rx_fecha_nac",
                      value=st.session_state.get("rx_fecha_nac", ""))
    with id3:
        st.text_input("Edad", key="rx_edad", value=st.session_state.get("rx_edad", ""))
    id4, id5 = st.columns([1, 2])
    with id4:
        _sxo = ["", "M", "F"]
        st.selectbox("Sexo", _sxo,
                     index=_sxo.index(st.session_state.get("rx_sexo", ""))
                     if st.session_state.get("rx_sexo", "") in _sxo else 0, key="rx_sexo")
    with id5:
        st.text_input("Expediente / NSS", key="rx_expediente",
                      value=st.session_state.get("rx_expediente", ""))

    # ── Sección 2: Prescripción completa ──────────────────────────────────────
    st.divider()
    st.markdown("### ⚙️ Prescripción TRRC")

    mod_rs, filtro_rs, coment_rs = combinar_recomendaciones(escenarios)
    filtro_rs = st.session_state.get("ui_filtro", filtro_rs)
    qp_rs, qp_h_rs, qe_rs, qr_pre_rs, qr_post_rs, qd_rs, ff_rs = flows_and_ff(
        qb, hto, dosis_mlkg, peso, uf, mod_rs or "CVVHDF")
    ff_txt_rs = f"{ff_rs:.1%}" if ff_rs is not None else "—"

    # Citrate adjustment
    ac_rs = st.session_state.get("anticoagulacion_tipo", "—")
    v_cit_rs = float(st.session_state.get("rca_citrato_ml_h", 0))
    ca_ml_rs = float(st.session_state.get("rca_calcio_ml_h", 0))
    rca_targets_rs = st.session_state.get("rca_targets", {})
    hnf_rs = float(st.session_state.get("hnf_ui_h", peso * 5))

    if ac_rs == "RCA" and v_cit_rs > 0:
        qr_pre_sol_rs = max(0.0, qr_pre_rs - v_cit_rs)
        ff_adj_rs = (qr_post_rs + uf) / max(qp_h_rs + qr_pre_sol_rs + v_cit_rs, 1e-9)
    else:
        qr_pre_sol_rs = float(qr_pre_rs)
        ff_adj_rs = ff_rs

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Modalidad", mod_rs or "—")
    sc2.metric("Filtro", filtro_rs or "—")
    sc3.metric("FF efectiva", f"{ff_adj_rs:.1%}" if ff_adj_rs else "—",
               delta="✅" if ff_adj_rs and ff_adj_rs <= 0.25 else "⚠️ ALTA")

    st.markdown("**Flujos programados en la máquina:**")
    fm1, fm2, fm3, fm4 = st.columns(4)
    fm1.metric("QB (mL/min)", qb)
    fm2.metric("Qe total (mL/hr)", int(qe_rs))
    fm3.metric("UF neta (mL/hr)", uf)
    fm4.metric("Qd dialisato (mL/hr)", int(qd_rs))

    fm5, fm6, fm7, fm8 = st.columns(4)
    if ac_rs == "RCA" and v_cit_rs > 0:
        fm5.metric("Qr PRE — citrato (mL/hr)", f"{v_cit_rs:.0f}",
                   help="Citrato va PRE-filtro por bomba de citrato")
        fm6.metric("Qr PRE — solución (mL/hr)", f"{qr_pre_sol_rs:.0f}",
                   help=f"Original {qr_pre_rs:.0f} − citrato {v_cit_rs:.0f}")
    else:
        fm5.metric("Qr PRE — solución (mL/hr)", f"{qr_pre_rs:.0f}")
        fm6.metric("Qr PRE — citrato", "No aplica")
    fm7.metric("Qr POST (mL/hr)", f"{qr_post_rs:.0f}")
    fm8.metric("Qe efluente = dosis × peso", f"{int(qe_rs)} mL/hr")

    if coment_rs:
        st.info(coment_rs)

    # ── Sección 3: Anticoagulación (dinámica) ─────────────────────────────────
    st.divider()
    st.markdown("### 💊 Anticoagulación")

    if ac_rs == "RCA":
        num_viales_rs = st.session_state.get("ca_viales", 12)
        prep_vol_rs = 250 if st.session_state.get("ca_prep_vol", "250 mL") == "250 mL" else 500
        # AFORO: volumen final = volumen de la bolsa (no se suma el de las ámpulas)
        vol_total_rs = prep_vol_rs
        ca_conc_rs = (int(num_viales_rs) * 2.23) / (vol_total_rs / 1000) if vol_total_rs > 0 else 0

        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown("#### 🧪 Citrato")
            st.markdown(f"""
| Parámetro | Valor |
|-----------|-------|
| Tipo de solución | {st.session_state.get('cit_sol_type', 'Citrato 4%')[:30]} |
| Dosis objetivo | {st.session_state.get('cit_dose', 3.0):.1f} mmol/L sangre |
| **Tasa de infusión citrato** | **{v_cit_rs:.0f} mL/hr** (línea arterial PRE-filtro) |
| iCa post-filtro diana | **0.25–0.40 mmol/L** |
""")
        with ac2:
            st.markdown("#### 🫙 Calcio — reposición sistémica")
            st.markdown(f"""
| Parámetro | Valor |
|-----------|-------|
| Preparación | {int(num_viales_rs)} ámpulas gluconato Ca 10% en {prep_vol_rs} mL NaCl 0.9% |
| Volumen total preparado | {vol_total_rs} mL |
| Concentración resultante | {ca_conc_rs:.1f} mmol/L de Ca elemental |
| **Tasa de infusión calcio** | **{ca_ml_rs:.0f} mL/hr** (línea sistémica POST-filtro) |
| iCa sistémico diana | **1.0–1.2 mmol/L** |
""")
        st.warning("⚠️ El calcio se infunde **SIEMPRE por línea sistémica post-filtro**, nunca en la línea de citrato ni pre-filtro.")

    elif ac_rs == "HNF":
        st.markdown(f"""
| Parámetro | Valor |
|-----------|-------|
| Tipo | Heparina No Fraccionada (HNF) |
| **Dosis inicial** | **{hnf_rs:.0f} UI/hr** en infusión continua |
| Ajuste | Según aPTT (objetivo: 45–70 s o protocolo institucional) |
| Frecuencia aPTT | Cada 4–6 hrs |
""")
    else:
        st.info("Sin anticoagulación registrada. Ve a **💊 Anticoagulación** o **🧪 Citrato RCA** para configurarla.")

    # ── Sección 4: Sodio (si relevante) ───────────────────────────────────────
    na_actual = float(st.session_state.get("na_main", 140.0))
    if na_actual < 130 or na_actual > 150:
        st.divider()
        st.markdown("### 🧂 Sodio — Consideraciones especiales")
        if na_actual < 130:
            st.warning(f"**Hiponatremia: Na = {na_actual:.0f} mEq/L** — "
                       "Corrección máxima: ≤8–10 mEq/L/24h (≤8 si riesgo de ODS). "
                       "Ajustar [Na] en bolsas o flujo postfiltro. "
                       "Ve a pestaña 🧂 Sodio TRRC para calcular la estrategia.")
        elif na_actual > 150:
            st.warning(f"**Hipernatremia: Na = {na_actual:.0f} mEq/L** — "
                       "Corrección: ≈0.5 mEq/L/hr (8–10 mEq/día). "
                       "Usar dializado con Na más alto. "
                       "Ve a pestaña 🧂 Sodio TRRC para calcular la estrategia.")

    # ── Sección 5: Monitoreo (dinámico) ───────────────────────────────────────
    st.divider()
    st.markdown("### 🔬 Monitoreo")

    if ac_rs == "RCA":
        st.markdown("""
| Momento | Parámetro | Objetivo / Acción |
|---------|-----------|-------------------|
| **Inicio** | Verificar circuito, presiones, flujos | Todo OK antes de conectar |
| **30 min** | iCa post-filtro + iCa sistémico | Post: 0.25–0.40 / Sist: 1.0–1.2 mmol/L |
| **1–2 hrs** | iCa ambos | Confirmar estabilidad |
| **Cada 4–6 hrs** | iCa post + iCa sistémico + Na, K, HCO₃⁻ | Ajuste ±10–20% si fuera de meta |
| **Cada 12–24 hrs** | Ca total + Ca iónico + Anión gap + pH + lactato | Ratio Ca_total/Ca_iónico: normal <2.5 |
| **Post-ajuste** | iCa ambos a los 30 min del cambio | Verificar nuevo equilibrio |
| **Circuito** | Presión transmembrana (PTM), presión de retorno | Alarma → revisar coagulación |
""")
        st.error("🚨 **ALERTA DE ACUMULACIÓN:** Si Ca_total/Ca_iónico >2.5 + anión gap elevado + "
                 "iCa sistémico bajo pese a ↑ calcio → **suspender citrato, cambiar a HNF. Avisar médico URGENTE.**")
    else:
        st.markdown("""
| Momento | Parámetro | Objetivo / Acción |
|---------|-----------|-------------------|
| **Inicio** | Verificar circuito y flujos | Todo OK antes de conectar |
| **Cada 4–6 hrs** | aPTT | Objetivo: 45–70 s (o protocolo institucional) |
| **Cada 4–6 hrs** | BMP (Na, K, HCO₃⁻, Ca, glucosa) | Ajustar solución según resultados |
| **Cada 12 hrs** | Plaquetas + TP/INR | Vigilar HIT (↓ plaquetas ≥50%) |
| **Circuito** | Presión transmembrana (PTM), coágulos | Alarma → revisar HNF |
""")

    # ── Sección 6: Alertas inmediatas ─────────────────────────────────────────
    st.divider()
    st.markdown("### ⚠️ Alertas inmediatas")
    alertas_txt = [
        f"**FF >25%:** Reducir UF o Qr_post, ↑ predilución {'(citrato o solución PRE)' if ac_rs == 'RCA' else '(Qr_pre)'}. Avisar médico.",
        "**Presión transmembrana ↑ sostenida:** Revisar coagulación del circuito. Evaluar cambio de filtro.",
    ]
    if ac_rs == "RCA":
        alertas_txt += [
            "**iCa post-filtro <0.25:** ↓ Citrato 10–20%. Avisar médico.",
            "**iCa post-filtro >0.40:** ↑ Citrato 10–20%. Avisar médico.",
            "**iCa sistémico <1.0:** ↑ Calcio (gluconato) 10–20%. Avisar médico.",
            "**iCa sistémico >1.2:** ↓ Calcio 10–20%. Avisar médico.",
            "**Ca_total/Ca_iónico >2.5:** ACUMULACIÓN DE CITRATO. Suspender citrato → HNF. URGENTE.",
        ]
    else:
        alertas_txt += [
            "**aPTT <45 s:** ↑ HNF según protocolo. Revisar acceso vascular.",
            "**aPTT >100 s:** ↓ HNF o suspender temporalmente. Vigilar sangrado.",
            "**Plaquetas ↓ ≥50% del basal:** Sospechar HIT. Suspender HNF. Avisar médico URGENTE.",
        ]

    k_actual = float(st.session_state.get("k_main", 4.0))
    ph_actual2 = float(st.session_state.get("ph_main", 7.35))
    if k_actual >= 6.0:
        alertas_txt.append(f"**K = {k_actual:.1f} mEq/L ≥6.0:** Dializado K 0–2 mEq/L, ↑ Qd. Re-labs cada 2 h.")
    if ph_actual2 < 7.20:
        alertas_txt.append(f"**pH = {ph_actual2:.2f} <7.20:** Confirmar solución con bicarbonato. ↑ Qd.")

    for a in alertas_txt:
        st.markdown(f"- {a}")

    # ── Sección 7: Electrolitos TRRC ──────────────────────────────────────────
    st.divider()
    st.markdown("### ⚗️ Guía rápida de electrolitos en TRRC")
    k_enf = float(st.session_state.get("k_main", 4.0))
    ph_enf = float(st.session_state.get("ph_main", 7.35))
    hco3_enf = float(st.session_state.get("hco3_main", 20.0))
    if k_enf < 3.0:
        st.error(f"K = {k_enf:.1f} — Hipocalemia severa: KCl 20–40 mEq/L en bolsas + IV según protocolo.")
    elif k_enf < 3.5:
        st.warning(f"K = {k_enf:.1f} — Agregar KCl 10–20 mEq/L a bolsas de reposición.")
    elif k_enf >= 6.0:
        st.error(f"K = {k_enf:.1f} — Hipercalemia: bolsas K=0 mEq/L, ↑ Qd 2–3 L/h.")
    elif k_enf >= 5.5:
        st.warning(f"K = {k_enf:.1f} — Bolsas K 0–2 mEq/L. Monitoreo cada 2–4h.")
    else:
        st.success(f"K = {k_enf:.1f} — Rango aceptable.")
    if ph_enf < 7.20 or hco3_enf < 15:
        st.error(f"pH {ph_enf:.2f} / HCO₃⁻ {hco3_enf:.0f} — Acidosis severa: solución con bicarbonato, ↑ Qd.")
    elif ph_enf > 7.50 or hco3_enf > 30:
        st.warning(f"pH {ph_enf:.2f} / HCO₃⁻ {hco3_enf:.0f} — Alcalosis: "
                   f"{'revisar tasa de citrato (genera HCO₃⁻).' if ac_rs == 'RCA' else 'revisar buffer en solución.'}")
    else:
        st.success(f"pH {ph_enf:.2f} / HCO₃⁻ {hco3_enf:.0f} — Equilibrio ácido-base aceptable.")

    # ── Sección 8: Médico + comentarios + PDF ─────────────────────────────────
    st.divider()
    st.markdown("### ✍️ Médico tratante")
    pd1, pd2 = st.columns(2)
    with pd1:
        st.text_input("Nombre del médico", key="rx_nombre_medico",
                      value=st.session_state.get("rx_nombre_medico", ""))
    with pd2:
        st.text_input("Cédula / Sello", key="rx_sello",
                      value=st.session_state.get("rx_sello", ""))

    st.text_area("Comentarios clínicos adicionales", key="rx_comentarios",
                 value=st.session_state.get("rx_comentarios", ""), height=80)

    st.markdown("### 📄 Generar PDF")
    st.write(f"Modo docente (PDF extendido): **{'Sí ✅' if st.session_state.get('pdf_extendido') else 'No'}**")
    st.caption("Activa el modo docente en la barra lateral para incluir fundamento clínico extendido.")

    col_pdf, _ = st.columns([1, 3])
    with col_pdf:
        if st.button("📄 Generar PDF clínico", key="btn_export_pdf",
                     type="primary", use_container_width=True):
            try:
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
                nom = st.session_state.get("rx_nombre_paciente", "").replace(" ", "")
                safe = "".join(c for c in nom if c.isalnum())
                fname = f"RenalPro_{safe}_{ts}.pdf" if safe else f"RenalPro_{ts}.pdf"
                buf = export_pdf_pro()
                st.download_button("⬇️ Descargar PDF", data=buf, file_name=fname,
                                   mime="application/pdf", use_container_width=True,
                                   key="btn_download_pdf")
                st.success("✅ PDF generado — 3 páginas: Prescripción · Enfermería · Fundamento")
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")
                st.caption("Si el error persiste, verifica que todos los campos estén completos.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB: PREMIUM — Pago automático MP + CLABE manual
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "premium":
    rol_actual = _rol()
    nombre_actual = _nombre()
    uid = _user_id()
    dias = st.session_state.get("sess_dias", 0)

    # ── Ya es Pro/Admin ────────────────────────────────────────────────────────
    if rol_actual in ("admin", "pro"):
        st.success(f"✅ **{nombre_actual}** — Acceso Premium activo.")
        if rol_actual == "pro" and dias:
            st.info(f"📅 Tu suscripción vence en **{dias} días**.")

        # Historial de pagos
        if _DB_ON and _db.db_ok() and uid:
            hist = _db.get_payment_history(uid)
            if hist:
                st.markdown("### 💳 Historial de pagos")
                for h in hist:
                    estado = "✅" if h["status"] == "approved" else "⏳"
                    st.caption(f"{estado} ${h['amount']:.0f} MXN — {str(h['created_at'])[:10]}")

        if st.button("🔄 Renovar suscripción", key="btn_renew"):
            st.session_state["_show_payment"] = True

    # ── Free / Trial / Expirado ────────────────────────────────────────────────
    if rol_actual not in ("admin", "pro") or st.session_state.get("_show_payment"):
        st.markdown("""
<div style="background:linear-gradient(135deg,#1E3A8A,#2563EB);border-radius:16px;
     padding:24px 28px;margin-bottom:16px;text-align:center;">
  <div style="font-size:32px;font-weight:800;color:#fff;">⭐ RenalPro Pro</div>
  <div style="color:rgba(255,255,255,0.85);font-size:15px;margin-top:6px;">
    El asistente clínico de nefrología y terapias extracorpóreas más completo
  </div>
  <div style="font-size:40px;font-weight:900;color:#FCD34D;margin:12px 0;">
    $99 <span style="font-size:18px;font-weight:500;color:rgba(255,255,255,0.8)">MXN / mes</span>
  </div>
</div>""", unsafe_allow_html=True)

        pf1, pf2 = st.columns(2)
        with pf1:
            st.markdown("**✅ Pro incluye:**")
            for f in ["Guardar prescripciones ilimitadas",
                       "Historial clínico por paciente",
                       "Búsqueda en historial",
                       "PDF exportable personalizado",
                       "Todos los módulos clínicos",
                       "Acceso desde cualquier dispositivo",
                       "Actualizaciones automáticas",
                       "Datos preservados 60 días tras vencimiento"]:
                st.markdown(f"• {f}")
        with pf2:
            st.markdown("**❌ Modo libre:**")
            for l in ["Sin guardar pacientes",
                       "Sin historial",
                       "Datos se pierden al cerrar",
                       "Sin PDF personalizado"]:
                st.markdown(f"• {l}")

        if rol_actual == "trial":
            st.warning(f"⏱️ Te quedan **{dias} día(s)** de prueba. Activa Pro para conservar tus datos.")
        elif rol_actual in ("expirado", "grace"):
            st.error("⚠️ Tu período expiró. Renueva para recuperar acceso a tus prescripciones guardadas.")

        st.divider()
        st.markdown("### 💳 Pagar con Mercado Pago")

        # ── Botón de pago MP ──────────────────────────────────────────────────
        mp_link_directo = ""
        mp_token = ""
        try:
            mp_link_directo = st.secrets.get("MP_LINK_PAGO", "")
            mp_token = st.secrets.get("MP_ACCESS_TOKEN", "")
        except Exception:
            pass

        if mp_link_directo:
            # Link directo de MP (más simple y confiable)
            st.markdown(f"""
<div style="text-align:center;padding:16px;">
  <a href="{mp_link_directo}" target="_blank"
     style="background:#009EE3;color:#fff;padding:14px 32px;border-radius:10px;
            font-weight:700;font-size:16px;text-decoration:none;display:inline-block;">
    💳 Pagar con Mercado Pago — $99 MXN
  </a>
  <p style="color:#64748B;font-size:12px;margin-top:8px;">
    Acepta: tarjeta, OXXO, transferencia bancaria, efectivo
  </p>
</div>""", unsafe_allow_html=True)
            st.info("✅ Después de pagar, envía tu comprobante por WhatsApp para activar tu cuenta. "
                    "Activación en menos de 24 horas.")

        elif mp_token and uid:
            if st.button("🔗 Pagar con Mercado Pago — Tarjeta / OXXO / Transferencia",
                         type="primary", key="btn_pagar_mp", use_container_width=True):
                with st.spinner("Generando tu link de pago..."):
                    link = _db.create_mp_preference(uid,
                           st.session_state.get("sess_user","user")) if _DB_ON else None
                    if link:
                        st.markdown(f"""
<div style="text-align:center;padding:16px;">
  <a href="{link}" target="_blank"
     style="background:#009EE3;color:#fff;padding:14px 32px;border-radius:10px;
            font-weight:700;font-size:16px;text-decoration:none;">
    Ir a Mercado Pago →
  </a>
</div>""", unsafe_allow_html=True)
                    else:
                        st.error("No se pudo generar el link. Usa la transferencia bancaria abajo.")
        else:
            st.warning("🔧 Configura MP_LINK_PAGO en Streamlit Secrets para habilitar el pago en línea.")

        # ── CLABE manual (siempre disponible como alternativa) ─────────────────
        with st.expander("📥 Transferencia bancaria / CLABE (alternativa)"):
            try:
                clabe   = st.secrets.get("CLABE_BANCARIA", "—")
                banco   = st.secrets.get("BANCO", "—")
                titular = st.secrets.get("TITULAR", "Dr. Josué Tapia López")
                wa      = st.secrets.get("WHATSAPP_CONTACTO", "477XXXXXXX")
            except Exception:
                clabe = "—"; banco = "—"; titular = "Dr. Josué Tapia"; wa = "477XXXXXXX"

            st.markdown(f"""
| | |
|---|---|
| **Banco** | {banco} |
| **Titular** | {titular} |
| **Monto** | $99 MXN / mes |
""")
            st.markdown(f"**CLABE:** {clabe}",
                        help="Copia este número para tu transferencia")
            # Also show as selectable text field for easy copy
            st.text_input("CLABE (toca para copiar)", value=clabe,
                         key="clabe_display", disabled=True,
                         label_visibility="collapsed")
            st.info(f"📱 Envía tu comprobante a WhatsApp **{wa}** con tu usuario. "
                    f"Activación en <24h.")



# ══════════════════════════════════════════════════════════════════════════════
# TAB: ADMIN / MI CUENTA
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "admin":
    rol_adm = _rol()
    if rol_adm == "admin":
        st.subheader("🛡️ Panel de Administrador")
        _init_db()

        # ── Datos según origen (DB o local) ──────────────────────────────────
        using_db = _DB_ON and _db.db_ok()
        if using_db:
            all_users_db = _cached_all_users()
        else:
            all_users_db = []
        users_adm = st.session_state.get("auth_users", {})

        # ── Resumen ──────────────────────────────────────────────────────────
        if using_db:
            total  = len(all_users_db)
            admins = sum(1 for u in all_users_db if u.get("rol") == "admin")
            pros   = sum(1 for u in all_users_db if _db.get_effective_rol(u) == "pro")
            becas  = sum(1 for u in all_users_db if _db.get_effective_rol(u) == "beca")
            trials = sum(1 for u in all_users_db if _db.get_effective_rol(u) == "trial")
            exps   = sum(1 for u in all_users_db if _db.get_effective_rol(u) in ("free","grace"))
        else:
            total  = len(users_adm)
            admins = sum(1 for u in users_adm.values() if u["rol"] == "admin")
            pros   = sum(1 for u in users_adm.values() if _get_role(u) == "pro")
            becas  = sum(1 for u in users_adm.values() if u.get("rol") == "beca")
            trials = sum(1 for u in users_adm.values() if _get_role(u) == "trial")
            exps   = sum(1 for u in users_adm.values() if _get_role(u) == "expirado")

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Total usuarios", total)
        m2.metric("Admins", admins)
        m3.metric("⭐ Premium", pros)
        m4.metric("🎓 Becas", becas)
        m5.metric("⏱️ Trial", trials)
        m6.metric("Free/Exp", exps)

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN BECAS
        # ═══════════════════════════════════════════════════════════════════
        st.divider()
        st.markdown("### 🎓 Becas y Acceso Académico")
        st.caption("Da acceso completo gratuito a residentes, colegas o cualquier persona que elijas.")

        beca_tab1, beca_tab2 = st.tabs(["🎓 Dar beca a usuario existente",
                                         "➕ Crear cuenta con beca"])

        with beca_tab1:
            bc1, bc2, bc3 = st.columns([2, 2, 1])
            with bc1:
                beca_user = st.text_input("Usuario (ya registrado)", key="beca_user",
                                          placeholder="nombre_usuario")
            with bc2:
                beca_dur = st.selectbox("Duración del acceso",
                    ["Sin límite (indefinido)", "1 mes", "3 meses",
                     "6 meses", "1 año"], key="beca_dur")
            with bc3:
                st.markdown(" ")
                st.markdown(" ")
                dar_beca = st.button("🎓 Dar acceso", key="btn_dar_beca",
                                     type="primary", use_container_width=True)

            if dar_beca and beca_user:
                meses_beca = {"Sin límite (indefinido)": 0, "1 mes": 1,
                              "3 meses": 3, "6 meses": 6, "1 año": 12}.get(beca_dur, 0)

                if using_db:
                    target = _db.get_user(beca_user.strip().lower())
                    if target:
                        ok = _db.grant_beca(target["id"], meses_beca)
                        if ok:
                            dur_txt = "indefinido" if meses_beca == 0 else f"{beca_dur}"
                            st.success(f"🎓 **{beca_user}** ahora tiene acceso de beca académica — {dur_txt}.")
                            st.info("El residente verá '🎓 Beca Académica — Dr. Josué Tapia Nefrólogo' al iniciar sesión.")
                        else:
                            st.error("Error al otorgar beca. Verifica la conexión con Railway.")
                    else:
                        st.error(f"Usuario '{beca_user}' no encontrado en la base de datos.")
                else:
                    # Local fallback
                    uname_b = beca_user.strip().lower()
                    if uname_b in users_adm:
                        users_adm[uname_b]["rol"] = "beca"
                        if meses_beca > 0:
                            from datetime import date, timedelta
                            end_d = (date.today() + timedelta(days=30*meses_beca)).strftime("%Y-%m-%d")
                            users_adm[uname_b]["sub_end"] = end_d
                        else:
                            users_adm[uname_b]["sub_end"] = "2099-12-31"
                        st.success(f"🎓 Beca otorgada a **{beca_user}**.")
                    else:
                        st.error(f"Usuario '{beca_user}' no encontrado.")

            # Mostrar becas activas
            st.markdown("#### Becas activas")
            if using_db:
                becados = [u for u in all_users_db if _db.get_effective_rol(u) == "beca"]
            else:
                becados = [(k, v) for k, v in users_adm.items() if v.get("rol") == "beca"]
                becados = [{"username": k, "nombre": v.get("nombre",""), "subscription_end": v.get("sub_end")} for k,v in users_adm.items() if v.get("rol") == "beca"]

            if not becados:
                st.info("No hay becas activas actualmente.")
            else:
                for b in becados:
                    uname_b = b.get("username","")
                    nombre_b = b.get("nombre","")
                    sub_b = b.get("subscription_end")
                    if sub_b and hasattr(sub_b, 'year') and sub_b.year >= 2099:
                        dur_b = "Indefinida"
                    elif sub_b:
                        dur_b = f"Vence: {str(sub_b)[:10]}"
                    else:
                        dur_b = "Indefinida"
                    col_b1, col_b2 = st.columns([3, 1])
                    col_b1.markdown(f"🎓 **{uname_b}** — {nombre_b} · {dur_b}")
                    with col_b2:
                        if st.button("Revocar", key=f"rev_{uname_b}"):
                            if using_db and b.get("id"):
                                _db.revoke_beca(b["id"])
                            else:
                                if uname_b in users_adm:
                                    users_adm[uname_b]["rol"] = "free"
                                    users_adm[uname_b]["sub_end"] = None
                            st.warning(f"Beca de {uname_b} revocada.")
                            st.rerun()

        with beca_tab2:
            st.caption("Crea la cuenta del residente y dale beca en un solo paso.")
            nc1, nc2 = st.columns(2)
            with nc1:
                nb_nombre = st.text_input("Nombre completo", key="nb_nombre",
                                          placeholder="Dr. / Dra. Nombre Apellido")
                nb_user   = st.text_input("Usuario", key="nb_user",
                                          placeholder="nombre_usuario")
                nb_pass   = st.text_input("Contraseña temporal", key="nb_pass",
                                          type="password", placeholder="mínimo 6 caracteres")
            with nc2:
                nb_email  = st.text_input("Email (opcional)", key="nb_email")
                nb_dur    = st.selectbox("Duración de beca",
                    ["Sin límite (indefinido)", "1 mes", "3 meses", "6 meses", "1 año"],
                    key="nb_dur")
                nb_esp    = st.text_input("Especialidad", key="nb_esp",
                                          placeholder="Residencia/Especialidad")

            if st.button("➕ Crear cuenta con beca", key="btn_crear_beca",
                         type="primary", use_container_width=True):
                if nb_nombre and nb_user and nb_pass and len(nb_pass) >= 6:
                    meses_nb = {"Sin límite (indefinido)": 0, "1 mes": 1,
                                "3 meses": 3, "6 meses": 6, "1 año": 12}.get(nb_dur, 0)
                    if using_db:
                        ok, msg = _db.create_user(nb_user.strip().lower(), nb_pass,
                                                  nb_nombre, nb_email, trial_days=0)
                        if ok:
                            new_u = _db.get_user(nb_user.strip().lower())
                            if new_u:
                                _db.grant_beca(new_u["id"], meses_nb)
                            st.success(f"🎓 Cuenta creada con beca para **{nb_nombre}**.")
                            st.info(f"Usuario: `{nb_user}` · Contraseña temporal: entregada de forma segura")
                        else:
                            st.error(f"Error: {msg}")
                    else:
                        uname_nb = nb_user.strip().lower()
                        if uname_nb in users_adm:
                            st.error("Ese usuario ya existe.")
                        else:
                            users_adm[uname_nb] = {
                                "nombre": nb_nombre, "email": nb_email,
                                "especialidad": nb_esp,
                                "password_hash": _hash(nb_pass),
                                "rol": "beca", "is_active": True,
                                "trial_end": None, "sub_end": "2099-12-31",
                                "created": datetime.now().strftime("%Y-%m-%d"), "last_login": None
                            }
                            st.success(f"🎓 Cuenta con beca creada para **{nb_nombre}**.")
                else:
                    st.warning("Completa nombre, usuario y contraseña (mínimo 6 caracteres).")

        # ═══════════════════════════════════════════════════════════════════
        # GESTIÓN DE USUARIOS
        # ═══════════════════════════════════════════════════════════════════
        # ═══════════════════════════════════════════════════════════════════
        # GESTIÓN DE USUARIOS — usa Railway DB si está conectado
        # ═══════════════════════════════════════════════════════════════════
        st.divider()
        st.markdown("### 👥 Gestión de usuarios")

        if using_db and all_users_db:
            # ── Vista Railway DB (usuarios reales) ───────────────────────────
            buscar_adm = st.text_input("🔍 Buscar usuario", key="adm_buscar",
                                       placeholder="Nombre o username...")
            usuarios_filtrados = [u for u in all_users_db
                if buscar_adm.lower() in (u.get("username","") + u.get("nombre","")).lower()
            ] if buscar_adm else all_users_db

            for u in usuarios_filtrados:
                uid_u   = u.get("id")
                uname_u = u.get("username","")
                rol_u   = _db.get_effective_rol(u)
                nom_u   = u.get("nombre","—")
                av_u    = u.get("avatar","👤")
                dias_u  = _db.get_dias_restantes(u)
                icon_m  = {"admin":"🛡️","pro":"⭐","beca":"🎓","trial":"⏱️","free":"👁️"}.get(rol_u,"❓")
                dias_txt = f" · {dias_u}d" if dias_u and dias_u < 365 else ""

                with st.expander(f"{av_u} {icon_m} **{uname_u}** — {nom_u} ({rol_u}{dias_txt})"):
                    ci1, ci2 = st.columns([2,1])
                    with ci1:
                        st.write(f"**Email:** {u.get('email','—')}")
                        st.write(f"**Institución:** {u.get('institucion','—')}")
                        st.write(f"**Rol:** {rol_u}")
                        st.write(f"**Creado:** {str(u.get('created_at',''))[:10]}")
                        st.write(f"**Último acceso:** {str(u.get('last_login','Nunca'))[:16] if u.get('last_login') else 'Nunca'}")
                        if u.get("subscription_end"):
                            st.write(f"**Acceso hasta:** {str(u['subscription_end'])[:10]}")
                    with ci2:
                        if uname_u != st.session_state.get("sess_user"):
                            # Dar beca
                            if rol_u != "beca":
                                if st.button(f"🎓 Dar beca indef.", key=f"beca_db_{uid_u}",
                                             use_container_width=True):
                                    _db.grant_beca(uid_u, 0)
                                    _clear_cache()
                                    st.success(f"🎓 Beca otorgada a {uname_u}")
                                    st.rerun()
                            else:
                                if st.button(f"Revocar beca", key=f"rev_db_{uid_u}",
                                             use_container_width=True):
                                    _db.revoke_beca(uid_u)
                                    _clear_cache()
                                    st.warning(f"Beca revocada de {uname_u}")
                                    st.rerun()
                            # Activar Premium
                            end_d = st.date_input("Premium hasta:", key=f"end_db_{uid_u}")
                            if st.button(f"⭐ Activar Premium", key=f"pro_db_{uid_u}",
                                         use_container_width=True):
                                import psycopg2
                                from datetime import datetime as _dt
                                conn_adm = _db.get_conn()
                                if conn_adm:
                                    try:
                                        cur_adm = conn_adm.cursor()
                                        cur_adm.execute("""UPDATE users SET rol='pro',
                                            subscription_end=%s, grace_until=%s WHERE id=%s""",
                                            (end_d, end_d, uid_u))
                                        conn_adm.commit()
                                        cur_adm.close()
                                        _clear_cache()
                                        st.success(f"✅ {uname_u} activado Premium hasta {end_d}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            # Hacer admin
                            if rol_u != "admin":
                                if st.button(f"🛡️ Hacer admin", key=f"adm_db_{uid_u}",
                                             use_container_width=True):
                                    conn_adm = _db.get_conn()
                                    if conn_adm:
                                        try:
                                            cur_adm = conn_adm.cursor()
                                            cur_adm.execute("UPDATE users SET rol='admin' WHERE id=%s", (uid_u,))
                                            conn_adm.commit()
                                            cur_adm.close()
                                            _clear_cache()
                                            st.success(f"🛡️ {uname_u} ahora es admin")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                        else:
                            st.caption("Tu propia cuenta")
        else:
            # ── Vista local (sin Railway) ─────────────────────────────────────
            users_adm = st.session_state.get("auth_users", {})
            for uname_l, udata_l in list(users_adm.items()):
                rol_l = _get_role(udata_l)
                with st.expander(f"**{uname_l}** — {udata_l.get('nombre','—')} ({rol_l})"):
                    st.write(f"**Email:** {udata_l.get('email','—')}")
                    st.write(f"**Rol:** {rol_l}")
                    if uname_l != st.session_state.get("sess_user"):
                        if st.button(f"🎓 Dar beca", key=f"beca_local_{uname_l}"):
                            udata_l["rol"] = "beca"
                            udata_l["sub_end"] = "2099-12-31"
                            st.success(f"🎓 Beca otorgada a {uname_l}")
                            st.rerun()

elif nav == "micuenta":
    # ══════════════════════════════════════════════════════════════════════════
    # MI CUENTA — Perfil, avatar y contraseña
    # ══════════════════════════════════════════════════════════════════════════
    if not _is_auth():
        st.warning("Inicia sesión para ver tu perfil.")
    else:
        st.subheader("👤 Mi Cuenta")
        uid_mc  = _user_id()
        rol_mc  = _rol()
        db_mc   = _DB_ON and _db.db_ok() and uid_mc

        AVATARES = [
            "👨‍⚕️","👩‍⚕️","🧑‍⚕️","👨‍🔬","👩‍🔬","🧑‍💻",
            "🫀","🩺","🔬","🏥","🩻","💊","🧬","🫁","⚕️","🩸",
            "😊","😎","🤓","🧐","💪","🌟",
        ]

        mc1, mc2 = st.columns([1, 2])

        with mc1:
            st.markdown("### Avatar")
            av_actual = st.session_state.get("sess_avatar", "👨‍⚕️")
            st.markdown(f"""
<div style="background:#1E3A8A;width:100px;height:100px;border-radius:50%;
     display:flex;align-items:center;justify-content:center;margin:0 auto 12px auto;
     font-size:52px;">{av_actual}</div>""", unsafe_allow_html=True)
            st.caption("Selecciona tu avatar:")
            av_sel = av_actual
            cols_av = st.columns(6)
            for i, av in enumerate(AVATARES):
                with cols_av[i % 6]:
                    border = "3px solid #2563EB" if av == av_actual else "1px solid #CBD5E1"
                    if st.button(av, key=f"av_{i}",
                                 help=f"Seleccionar {av}"):
                        av_sel = av
                        st.session_state["sess_avatar"] = av

        with mc2:
            st.markdown("### Información del perfil")
            nom_mc  = st.text_input("Nombre completo",
                                    value=st.session_state.get("sess_nombre",""), key="mc_nombre")
            email_mc= st.text_input("Email",
                                    value=st.session_state.get("sess_email",""), key="mc_email")
            esp_mc  = st.text_input("Especialidad",
                                    value=st.session_state.get("sess_especialidad",""),
                                    key="mc_esp", placeholder="Ej: Nefrología")
            inst_mc = st.text_input("Institución / Hospital",
                                    value=st.session_state.get("sess_institucion",""),
                                    key="mc_inst", placeholder="Ej: IMSS CMNO N1, León, Gto.")
            dom_mc  = st.text_input("Domicilio del consultorio",
                                    value=st.session_state.get("sess_domicilio",""),
                                    key="mc_dom", placeholder="Av. Juan Alonso de Torres 1702, León, Gto.")
            tel_mc  = st.text_input("Teléfono del consultorio",
                                    value=st.session_state.get("sess_telefono",""),
                                    key="mc_tel", placeholder="(477) 123-4567")

            st.markdown("---")
            st.markdown("**Credenciales COFEPRIS**")
            st.caption("Requeridas para receta médica oficial en México")

            cg1, cg2 = st.columns(2)
            with cg1:
                ced_gen_mc = st.text_input("Cédula Medicina General",
                                           value=st.session_state.get("sess_ced_general",""),
                                           key="mc_ced_gen", placeholder="Ej: 8765432")
            with cg2:
                univ_gen_mc = st.text_input("Universidad (título general)",
                                            value=st.session_state.get("sess_univ_general",""),
                                            key="mc_univ_gen", placeholder="Ej: UNAM")
            ce1, ce2 = st.columns(2)
            with ce1:
                ced_esp_mc = st.text_input("Cédula de Especialidad",
                                           value=st.session_state.get("sess_cedula",""),
                                           key="mc_cedula", placeholder="Ej: 9940966")
            with ce2:
                univ_esp_mc = st.text_input("Universidad (especialidad)",
                                            value=st.session_state.get("sess_universidad",""),
                                            key="mc_univ", placeholder="Ej: UNAM")

            cc1, cc2 = st.columns(2)
            with cc1:
                consejo_mc = st.text_input("Consejo Mexicano de certificación",
                                           value=st.session_state.get("sess_consejo_nombre",""),
                                           key="mc_consejo", placeholder="Ej: Consejo Mexicano de Nefrología")
            with cc2:
                consejo_num_mc = st.text_input("Número de certificación",
                                               value=st.session_state.get("sess_consejo_numero",""),
                                               key="mc_consejo_num", placeholder="Ej: 1267")

            if st.button("💾 Guardar cambios", type="primary", key="btn_mc_save",
                         use_container_width=True):
                av_nuevo = st.session_state.get("sess_avatar", av_actual)
                if db_mc:
                    try:
                        ok = _db.update_user_profile(
                            uid_mc, nom_mc, email_mc, esp_mc, inst_mc, av_nuevo,
                            cedula     = ced_esp_mc,
                            universidad= univ_esp_mc,
                            domicilio  = dom_mc,
                            telefono   = tel_mc,
                            cedula_general        = ced_gen_mc,
                            universidad_general   = univ_gen_mc,
                            cedula_especialidad   = ced_esp_mc,
                            universidad_especialidad = univ_esp_mc,
                            consejo_nombre = consejo_mc,
                            consejo_numero = consejo_num_mc,
                        )
                    except TypeError:
                        ok = _db.update_user_profile(uid_mc, nom_mc, email_mc,
                                                     esp_mc, inst_mc, av_nuevo)
                    if ok:
                        st.session_state.update({
                            "sess_nombre":         nom_mc,
                            "sess_email":          email_mc,
                            "sess_institucion":    inst_mc,
                            "sess_especialidad":   esp_mc,
                            "sess_cedula":         ced_esp_mc,
                            "sess_universidad":    univ_esp_mc,
                            "sess_domicilio":      dom_mc,
                            "sess_telefono":       tel_mc,
                            "sess_ced_general":    ced_gen_mc,
                            "sess_univ_general":   univ_gen_mc,
                            "sess_consejo_nombre": consejo_mc,
                            "sess_consejo_numero": consejo_num_mc,
                        })
                        _clear_cache()
                        st.success("✅ Perfil actualizado.")
                    else:
                        st.error("Error al guardar. Verifica conexión con Railway.")
                else:
                    st.session_state.update({
                        "sess_nombre": nom_mc, "sess_email": email_mc,
                        "sess_institucion": inst_mc, "sess_especialidad": esp_mc,
                    })
                    st.success("✅ Perfil actualizado (sesión actual).")
        st.divider()
        st.markdown("### 🔒 Cambiar contraseña")
        if db_mc:
            cp1, cp2, cp3 = st.columns(3)
            with cp1:
                pwd_old = st.text_input("Contraseña actual", type="password", key="mc_old_pwd")
            with cp2:
                pwd_new = st.text_input("Nueva contraseña (mín. 6 car.)", type="password", key="mc_new_pwd")
            with cp3:
                pwd_conf = st.text_input("Confirmar nueva", type="password", key="mc_conf_pwd")
            if st.button("🔒 Cambiar contraseña", key="btn_mc_pwd"):
                if not pwd_old or not pwd_new:
                    st.warning("Completa todos los campos.")
                elif len(pwd_new) < 6:
                    st.warning("La nueva contraseña debe tener al menos 6 caracteres.")
                elif pwd_new != pwd_conf:
                    st.warning("Las contraseñas no coinciden.")
                else:
                    import bcrypt as _bcrypt
                    new_hash = _bcrypt.hashpw(pwd_new.encode(), _bcrypt.gensalt()).decode()
                    ok = _db.change_password(uid_mc, pwd_old, new_hash)
                    if ok:
                        st.success("✅ Contraseña actualizada correctamente.")
                    else:
                        st.error("Contraseña actual incorrecta.")
        else:
            st.info("Conecta Railway para cambiar tu contraseña.")

        st.divider()
        st.markdown("### 🖼️ Logo / Sello del consultorio")
        st.caption("Se incluirá en la receta médica. JPG o PNG · Máximo 2 MB · Recomendado: 300×300 px")
        logo_file = st.file_uploader("Subir logo", type=["jpg","jpeg","png"],
                                     key="mc_logo_upload")
        if logo_file:
            if logo_file.size > 2_097_152:
                st.error("El archivo supera 2 MB. Sube una imagen más pequeña.")
            else:
                import base64
                logo_b64 = base64.b64encode(logo_file.read()).decode()
                st.session_state["sess_logo_b64"]  = logo_b64
                st.session_state["sess_logo_mime"] = logo_file.type
                st.success("✅ Logo cargado — aparecerá en las recetas.")
        if st.session_state.get("sess_logo_b64"):
            import base64
            logo_data = base64.b64decode(st.session_state["sess_logo_b64"])
            st.image(logo_data, width=120, caption="Logo actual")
            if st.button("🗑️ Quitar logo", key="btn_rm_logo"):
                st.session_state.pop("sess_logo_b64", None)
                st.session_state.pop("sess_logo_mime", None)
                st.rerun()

        st.divider()
        st.markdown("### 📊 Información de cuenta")
        r1, r2, r3 = st.columns(3)
        r1.metric("Rol actual", rol_mc)
        r2.metric("Usuario", st.session_state.get("sess_user","—"))
        dias_mc = st.session_state.get("sess_dias", 0)
        r3.metric("Días restantes",
                  "Indefinido" if rol_mc in ("admin","beca") and dias_mc > 365*5
                  else str(dias_mc) if dias_mc else "—")

        st.divider()
        st.markdown("### ➕ Crear usuario manualmente")
        nc1, nc2 = st.columns(2)
        with nc1:
            new_u = st.text_input("Usuario", key="new_u")
            new_nombre = st.text_input("Nombre completo", key="new_nombre")
            new_email = st.text_input("Email", key="new_email")
        with nc2:
            new_esp = st.selectbox("Especialidad", ["Nefrología", "Medicina Crítica",
                "Medicina Interna", "Otra"], key="new_esp")
            new_rol = st.selectbox("Rol inicial", ["trial", "beca", "pro"], key="new_rol",
                                help="Rol 'admin' solo puede asignarse directamente en DB por seguridad.")
            new_pass = st.text_input("Contraseña temporal", type="password", key="new_pass")
        if st.button("Crear usuario", key="btn_create_user", type="primary"):
            if new_u and new_pass and new_nombre:
                ok, msg = _do_register(new_u, new_pass, new_nombre, new_email, new_esp)
                if ok:
                    if new_rol != "trial":
                        users_adm[new_u.lower()]["rol"] = new_rol
                    st.success(f"✅ Usuario {new_u} creado como {new_rol}.")
                else:
                    st.error(msg)
            else:
                st.error("Completa usuario, nombre y contraseña.")

        st.divider()
        st.markdown("### 🔑 Cambiar mi contraseña")
        adm_uname = st.session_state.get("sess_user", "")
        adm_data = st.session_state.get("auth_users", {}).get(adm_uname, {})
        acp1, acp2 = st.columns(2)
        with acp1:
            old_pa = st.text_input("Contraseña actual", type="password", key="adm_old")
            new_pa1 = st.text_input("Nueva contraseña (mín. 6 caracteres)", type="password", key="adm_new1")
            new_pa2 = st.text_input("Confirmar nueva contraseña", type="password", key="adm_new2")
            if st.button("✅ Actualizar contraseña", key="btn_adm_pass", type="primary"):
                if _verify(old_pa, adm_data.get("password_hash", "")):
                    if new_pa1 == new_pa2 and len(new_pa1) >= 6:
                        adm_data["password_hash"] = _hash(new_pa1)
                        st.success("✅ Contraseña actualizada correctamente.")
                    else:
                        st.error("Las contraseñas no coinciden o tienen menos de 6 caracteres.")
                else:
                    st.error("Contraseña actual incorrecta.")
        with acp2:
            st.info("💡 **Recuerda:** Si cambias tu contraseña aquí, actualiza también "
                    "`ADMIN_PASSWORD` en **Streamlit Secrets** para que el cambio persista "
                    "después de un redeploy.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 12: REFERENCIAS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "refs":
    st.subheader("Referencias — filtradas por contexto clínico")
    escenarios_sel_ref = st.session_state.get("sb_escenarios", [])
    anticoag_ref = st.session_state.get("anticoagulacion_tipo", "—")

    colf1, colf2 = st.columns([2, 1])
    query_ref = colf1.text_input("Buscar en títulos/resumen", "")
    solo_ctx = colf2.checkbox("Solo relevantes al contexto actual", value=True)

    refs = filtrar_refs_por_contexto(escenarios_sel_ref, anticoag_ref) if solo_ctx else BIBLIO
    if query_ref.strip():
        ql = query_ref.lower()
        refs = [r for r in refs if ql in r["title"].lower() or ql in r["blurb"].lower()]

    if not refs:
        st.info("No hay referencias que coincidan. Amplía la búsqueda.")
    else:
        for i, r in enumerate(refs, 1):
            st.markdown(f"**[{i}] {r['title']}**  \n"
                        f"*{r['where']}* ({r['yr']}) — {r['blurb']}  \n"
                        f"[🔗 Ver fuente]({r['url']})")
            st.markdown("---")
    st.caption("Las referencias se actualizan al cambiar escenarios o anticoagulación.")

elif nav == "electrolitos":
    st.subheader("⚗️ Electrolitos en TRRC & Cálculo de Bolsas")
    elec_modo = st.radio("Sección",
        ["🔵 Fosfato", "🟢 Magnesio", "📦 Bolsas de solución", "🧬 Composición de bolsas"],
        horizontal=True, key="elec_modo")

    peso_elec = float(st.session_state.get("sb_peso", 70.0))

    # ── FOSFATO ────────────────────────────────────────────────────────────────
    if elec_modo == "🔵 Fosfato":
        st.markdown("### Hipofosforemia en TRRC")
        st.info("La hipofosforemia es la complicación electrolítica más frecuente en TRRC prolongado "
                "(las soluciones estándar no contienen fosfato). Incidencia: 50–80% en CRRT >24h.")

        ep1, ep2 = st.columns(2)
        with ep1:
            phos_act = st.number_input("Fósforo sérico actual (mg/dL)", 0.0, 8.0, 2.0, 0.1, key="phos_act")
            peso_phos = st.number_input("Peso (kg)", 10.0, 300.0, peso_elec, 0.5, key="peso_phos")
        with ep2:
            phos_meta = st.number_input("Meta de fósforo (mg/dL)", 2.0, 5.0, 3.0, 0.1, key="phos_meta")
            via_phos = st.selectbox("Vía de administración", ["IV (de elección en TRRC)", "Oral/SNG"], key="via_phos")

        r_phos = phos_dose_iv(phos_act, peso_phos)
        pr1, pr2, pr3 = st.columns(3)
        pr1.metric("Severidad", f"{r_phos['color']} {r_phos['sev']}")
        pr2.metric("Dosis mínima (mmol)", f"{r_phos['lo']:.1f}")
        pr3.metric("Dosis máxima (mmol)", f"{r_phos['hi']:.1f}")

        st.markdown(f"### Esquema de reposición")
        if phos_act >= 2.5:
            st.success("✅ Fósforo normal. Monitorear cada 6–8h durante TRRC.")
        else:
            if "IV" in via_phos:
                st.markdown(f"""
#### Fosfato de potasio IV (KH₂PO₄/K₂HPO₄)
| Parámetro | Valor |
|-----------|-------|
| Presentación típica | Fosfato de K 3 mmol/mL (+ 4.4 mEq K/mL) |
| Dosis recomendada | **{r_phos['lo']:.1f} – {r_phos['hi']:.1f} mmol de fosfato** |
| Tiempo de infusión | **{r_phos['tiempo']}** |
| Tasa máxima | **7 mmol/hr** (riesgo de hipocalcemia e hipotensión) |
| Monitoreo | Fósforo, Ca, K c/4–6h durante reposición |

> 🔸 Con TRRC activo: el fosfato se elimina continuamente. Puede requerirse infusión continua o agregar fosfato a las bolsas de reemplazo ({f"{phos_meta:.1f} – 1.5 mmol/L" } en bolsas si disponible).
                """)
            else:
                dosis_oral = (phos_meta - phos_act) * peso_phos * 0.3  # rough estimate
                st.info(f"Oral/SNG: Fosfato de sodio/potasio oral. Dosis estimada: {dosis_oral:.0f}–{dosis_oral*1.5:.0f} mg de fósforo elemental dividido en 3–4 dosis. Ajustar según respuesta.")

        with st.expander("📋 Fosfato en bolsas de TRRC"):
            st.markdown("""
**Agregar fosfato a las bolsas de reemplazo:**
- Concentración objetivo: **1.0–1.5 mmol/L** en la solución
- Por cada 5L de bolsa: agregar **5–7.5 mmol de fosfato**
- Equivalente a: 1.7–2.5 mL de KH₂PO₄ 3 mmol/mL
- ⚠️ No mezclar fosfato con calcio en la misma línea (precipitación)
- Verificar disponibilidad con farmacia institucional
            """)

    # ── MAGNESIO ───────────────────────────────────────────────────────────────
    elif elec_modo == "🟢 Magnesio":
        st.markdown("### Hipomagnesemia en TRRC")
        st.info("Mg se elimina libremente en TRRC si las soluciones no lo contienen. "
                "Prismasol®/Accusol® contienen ~0.6 mmol/L de Mg. Vigilar niveles c/12–24h.")

        mg1, mg2 = st.columns(2)
        with mg1:
            mg_act = st.number_input("Magnesio sérico (mg/dL)", 0.5, 5.0, 1.5, 0.1, key="mg_act",
                                     help="Normal: 1.7–2.4 mg/dL (0.70–1.0 mmol/L)")
            peso_mg = st.number_input("Peso (kg)", 10.0, 300.0, peso_elec, 0.5, key="peso_mg")
        with mg2:
            st.metric("Mg en mmol/L", f"{mg_act * 0.4113:.2f}",
                      help="Conversión: mg/dL × 0.4113 = mmol/L")

        mg_mmol = mg_act * 0.4113
        if mg_mmol >= 0.70:
            st.success(f"✅ Mg normal ({mg_act:.1f} mg/dL). Monitorear c/12–24h.")
        elif mg_mmol >= 0.50:
            dosis_g = 2.0
            st.warning(f"🟡 Hipomagnesemia leve ({mg_act:.1f} mg/dL). "
                       f"**MgSO₄ 2g IV** (4mL al 50%) en 100mL NaCl 0.9% en 2h.")
        elif mg_mmol >= 0.30:
            dosis_g = 4.0
            st.error(f"🔴 Hipomagnesemia moderada ({mg_act:.1f} mg/dL). "
                     f"**MgSO₄ 4g IV** (8mL al 50%) en 250mL NaCl 0.9% en 4h.")
        else:
            st.error(f"🚨 Hipomagnesemia severa ({mg_act:.1f} mg/dL). "
                     f"**MgSO₄ 4–8g IV** en 4–8h. Monitoreo cardíaco. Repetir nivel c/4h.")

        st.markdown("""
#### MgSO₄ presentaciones comunes
| Presentación | Contenido | Equivalencia |
|-------------|-----------|-------------|
| MgSO₄ 50% (ámpulas 10mL) | 5g/10mL | 1g = 2mL = 4 mEq = 2 mmol Mg |
| MgSO₄ 20% (ámpulas 10mL) | 2g/10mL | 1g = 5mL |
| MgSO₄ 10% | 1g/10mL | 1g = 10mL |

> Tasa máxima IV: **1g/hr** (150 mg/min) para evitar hipotensión y depresión respiratoria.
        """)

    # ── BOLSAS ─────────────────────────────────────────────────────────────────
    elif elec_modo == "📦 Bolsas de solución":
        st.markdown("### Cálculo de bolsas de solución para TRRC")
        st.caption("Cuántas bolsas pedir a farmacia para una prescripción dada.")

        bb1, bb2, bb3 = st.columns(3)
        with bb1:
            qr_pre_b = st.number_input("Qr PRE (mL/hr)", 0, 3000,
                                       int(st.session_state.get("presc_qr_pre", 840)), 50, key="bb_pre")
            qr_post_b = st.number_input("Qr POST (mL/hr)", 0, 3000,
                                        int(st.session_state.get("presc_qr_post", 360)), 50, key="bb_post")
        with bb2:
            qd_b = st.number_input("Qd Dialisato (mL/hr)", 0, 5000, 800, 50, key="bb_qd")
            horas_b = st.number_input("Horas de TRRC", 1, 72, 24, 1, key="bb_horas")
        with bb3:
            tam_bolsa = st.selectbox("Tamaño de bolsa disponible",
                                     ["5 L", "2.5 L", "1 L"], key="bb_tam")
            tam_L = float(tam_bolsa.replace(" L", ""))

        vol_pre = qr_pre_b * horas_b / 1000
        vol_post = qr_post_b * horas_b / 1000
        vol_dial = qd_b * horas_b / 1000

        bolsas_pre = math.ceil(vol_pre / tam_L) if vol_pre > 0 else 0
        bolsas_post = math.ceil(vol_post / tam_L) if vol_post > 0 else 0
        bolsas_dial = math.ceil(vol_dial / tam_L) if vol_dial > 0 else 0
        bolsas_total = bolsas_pre + bolsas_post + bolsas_dial

        bc1, bc2, bc3, bc4 = st.columns(4)
        bc1.metric("Bolsas PRE-filtro", f"{bolsas_pre}",
                   help=f"{vol_pre:.1f} L totales")
        bc2.metric("Bolsas POST-filtro", f"{bolsas_post}",
                   help=f"{vol_post:.1f} L totales")
        bc3.metric("Bolsas dialisato", f"{bolsas_dial}",
                   help=f"{vol_dial:.1f} L totales")
        bc4.metric("TOTAL bolsas", f"{bolsas_total} bolsas de {tam_bolsa}")

        st.info(f"📦 **Pedir a farmacia:** {bolsas_pre} bolsas PRE + {bolsas_post} bolsas POST + "
                f"{bolsas_dial} bolsas dialisato = **{bolsas_total} bolsas de {tam_bolsa}** "
                f"para {horas_b}h de TRRC.")
        st.caption("Pedir 10–20% extra por posibles pérdidas o interrupciones.")

    # ── COMPOSICIÓN DE BOLSAS ──────────────────────────────────────────────────
    else:
        st.markdown("### Composición personalizada de bolsas de reemplazo")
        st.caption("Qué agregar a las bolsas según laboratorios del paciente.")

        k_act = float(st.session_state.get("k_main", 4.0))
        ph_act = float(st.session_state.get("ph_main", 7.35))
        hco3_act = float(st.session_state.get("hco3_main", 20.0))

        st.markdown("#### Ajustes sugeridos automáticamente según tus laboratorios:")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Potasio (K)**")
            if k_act < 3.0:
                st.warning(f"K = {k_act:.1f} → Agregar **20–30 mEq KCl por litro** de solución")
            elif k_act < 3.5:
                st.info(f"K = {k_act:.1f} → Agregar **10–20 mEq KCl por litro**")
            elif k_act > 5.5:
                st.error(f"K = {k_act:.1f} → Usar solución **K = 0 mEq/L**")
            elif k_act > 5.0:
                st.warning(f"K = {k_act:.1f} → Usar solución **K = 1–2 mEq/L**")
            else:
                st.success(f"K = {k_act:.1f} → Solución estándar K = **2–4 mEq/L**")

            st.markdown("**Buffer / Bicarbonato**")
            if hco3_act < 18 or ph_act < 7.25:
                st.error(f"pH {ph_act:.2f} / HCO₃ {hco3_act:.0f} → "
                         "Usar **bicarbonato 32–35 mEq/L**. Evitar lactato.")
            elif hco3_act > 28 or ph_act > 7.50:
                st.warning(f"pH {ph_act:.2f} / HCO₃ {hco3_act:.0f} → "
                           "Usar buffer bajo (28–30 mEq/L). Verificar tasa citrato si aplica.")
            else:
                st.success(f"pH {ph_act:.2f} / HCO₃ {hco3_act:.0f} → "
                           "Bicarbonato estándar **32 mEq/L** aceptable.")

        with cc2:
            st.markdown("**Fosfato**")
            phos_comp = st.number_input("Fósforo sérico (mg/dL)", 0.5, 6.0, 2.0, 0.1, key="phos_comp")
            if phos_comp < 2.0:
                st.warning(f"Fósforo bajo → Considerar agregar **1.0–1.5 mmol/L** de fosfato a bolsas")
            else:
                st.success("Fósforo normal → Solución estándar (sin fosfato adicional)")

            st.markdown("**Magnesio**")
            mg_comp = st.number_input("Mg sérico (mg/dL)", 0.5, 5.0, 1.5, 0.1, key="mg_comp")
            mg_mmol_c = mg_comp * 0.4113
            if mg_mmol_c < 0.70:
                st.warning(f"Mg bajo ({mg_comp:.1f}) → Verificar si solución contiene Mg (Prismasol: 0.6 mmol/L)")
            else:
                st.success(f"Mg normal ({mg_comp:.1f} mg/dL)")

        st.divider()
        st.markdown("#### Composición de soluciones comerciales comunes")
        st.markdown("""
| Componente | Prismasol® 2K/0Ca | Prismasol® 4K | Accusol® 35 | Solución personalizable |
|-----------|------------------|--------------|-------------|------------------------|
| Na (mEq/L) | 140 | 140 | 140 | Ajustable |
| K (mEq/L) | 2 | 4 | 2 | **Agregar KCl** |
| Ca (mEq/L) | 0 (con citrato) | 1.75 | 1.75 | — |
| Mg (mmol/L) | 0.6 | 0.6 | 0.5 | — |
| HCO₃ (mEq/L) | 32 | 32 | 35 | — |
| Glucosa (mg/dL) | 100 | 100 | 0 | — |
| Fosfato | **0** | **0** | **0** | **Agregar** |
        """)

# ── CALCULADORAS DE NEFROLOGÍA ─────────────────────────────────────────────────
elif nav == "nefro":
    st.subheader("🔢 Calculadoras de Nefrología")
    nefro_modo = st.radio("Sección",
        ["📐 FG & Estadificación ERC", "🧪 Orina & Electrolitos",
         "🩸 Anemia en ERC", "💊 Medicamentos en ERC/Diálisis"],
        horizontal=True, key="nefro_modo")

    # ── FG & ERC ──────────────────────────────────────────────────────────────
    if nefro_modo == "📐 FG & Estadificación ERC":
        st.markdown("### Estimación de Filtración Glomerular")

        fg1, fg2, fg3, fg4, fg5 = st.columns(5)
        with fg1:
            fg_sex = st.selectbox("Sexo", ["M", "F"], key="fg_sex")
        with fg2:
            fg_age = st.number_input("Edad (años)", 0, 110, 55, 1, key="fg_age")
        with fg3:
            fg_cr = st.number_input("Creatinina (mg/dL)", 0.1, 20.0, 1.0, 0.05, key="fg_cr")
        with fg4:
            fg_ht = st.number_input("Talla (cm)", 100, 220, 170, 1, key="fg_ht")
        with fg5:
            fg_peso_real = st.number_input("Peso real (kg)", 10.0, 200.0, float(peso), 0.5, key="fg_peso")

        pi = peso_ideal_kg(fg_sex, fg_ht)
        egfr_val = ckd_epi_2021(fg_sex, fg_age, fg_cr)
        cg_real = cockcroft_gault(fg_sex, fg_age, fg_peso_real, fg_cr)
        cg_ideal = cockcroft_gault(fg_sex, fg_age, pi, fg_cr)

        st.divider()
        fr1, fr2, fr3, fr4 = st.columns(4)
        fr1.metric("CKD-EPI 2021 (mL/min/1.73m²)", f"{egfr_val:.1f}",
                   help="Sin ajuste racial. Recomendado KDIGO 2021.")
        fr2.metric("Cockcroft-Gault (peso real)", f"{cg_real:.0f} mL/min")
        fr3.metric("Cockcroft-Gault (peso ideal)", f"{cg_ideal:.0f} mL/min",
                   help=f"Peso ideal: {pi:.1f} kg")
        fr4.metric("Peso ideal estimado", f"{pi:.1f} kg")

        acr_fg = st.number_input("RAC — Relación Albúmina/Creatinina urinaria (mg/g)", 0.0, 10000.0, 0.0, 10.0, key="fg_acr")
        g_stage, a_stage = estadio_ckd(egfr_val, acr_fg)
        st.markdown(f"### Estadio ERC: **{g_stage} {a_stage}**")

        color_map = {"G1":"✅","G2":"🟢","G3a":"🟡","G3b":"🟠","G4":"🔴","G5":"🚨"}
        st.markdown(f"""
| Estadio G | TFG (mL/min/1.73m²) | Estadio A | RAC (mg/g) |
|-----------|--------------------|-----------|--------------------|
| G1 | ≥90 | A1 | <30 (normal) |
| G2 | 60–89 | **A2** | **30–300 (aumento moderado)** |
| **{g_stage}** | **{egfr_val:.0f}** | **{a_stage}** | **{acr_fg:.0f}** |
| G4 | 15–29 | A3 | >300 (aumento grave) |
| G5 | <15 | | |
        """)

        if egfr_val < 15:
            st.error("🚨 G5 — Falla renal. Evaluar inicio de TRS (diálisis, trasplante).")
        elif egfr_val < 30:
            st.error(f"🔴 {g_stage} — Preparar acceso para diálisis. Derivar a nefrología urgente.")
        elif egfr_val < 45:
            st.warning(f"🟠 {g_stage} — Seguimiento estrecho. Ajustar medicamentos. Derivar a nefrología.")
        elif egfr_val < 60:
            st.warning(f"🟡 {g_stage} — Vigilar progresión. Control de factores de riesgo.")
        else:
            st.success(f"✅ {g_stage} — TFG preservada.")

        st.caption("CKD-EPI 2021: Inker LA et al., NEJM 2021. Cockcroft-Gault: Cockcroft DW, Gault MH, Nephron 1976.")

    # ── ANEMIA EN ERC ──────────────────────────────────────────────────────────
    # ── ORINA & ELECTROLITOS ──────────────────────────────────────────────────
    elif nefro_modo == "🧪 Orina & Electrolitos":
        calc_sel = st.selectbox("Calculadora", [
            "📊 RACU — Relación Albúmina/Creatinina Urinaria",
            "🔬 RPCU — Relación Proteína/Creatinina Urinaria",
            "🧂 FENa / FEUrea — Prerrenal vs Renal",
            "💧 Osmolalidad Plasmática + Gap Osmolar",
            "⚡ Anión Gap Urinario",
            "🦴 Corrección de Calcio por Albúmina",
            "🩸 Déficit de Bicarbonato & Brecha Aniónica",
        ], key="calc_orina_sel")

        st.divider()

        # ── RACU ──────────────────────────────────────────────────────────────
        if "RACU" in calc_sel:
            st.markdown("### 📊 RACU — Relación Albúmina/Creatinina Urinaria")
            st.caption("Índice de detección temprana de daño renal. Muestra puntual de orina (spot).")

            r1, r2, r3 = st.columns(3)
            with r1:
                racu_unidad_alb = st.selectbox("Unidades de albúmina",
                    ["mg/L", "mg/dL", "μg/min (tasa de excreción)"], key="racu_ua")
                racu_alb = st.number_input("Albúmina urinaria",
                    0.0, 10000.0, 30.0, 1.0, key="racu_alb_val")
            with r2:
                racu_unidad_cr = st.selectbox("Unidades de creatinina",
                    ["g/L", "mg/dL", "mmol/L"], key="racu_uc")
                racu_cr = st.number_input("Creatinina urinaria",
                    0.0, 500.0, 100.0, 1.0, key="racu_cr_val")

            # Normalizar a mg/L y g/L
            alb_mgl = racu_alb if racu_unidad_alb == "mg/L" else (racu_alb * 10 if racu_unidad_alb == "mg/dL" else racu_alb * 0.0667)
            cr_gl   = racu_cr if racu_unidad_cr == "g/L" else (racu_cr / 100 if racu_unidad_cr == "mg/dL" else racu_cr * 0.1131)
            racu_val = (alb_mgl / cr_gl) if cr_gl > 0 else 0

            with r3:
                st.markdown(" ")
                if racu_val < 30:
                    st.success(f"**RACU: {racu_val:.1f} mg/g**\n\n✅ Normal (<30 mg/g)")
                elif racu_val < 300:
                    st.warning(f"**RACU: {racu_val:.1f} mg/g**\n\n⚠️ A3 — Albuminuria moderada\n(30–300 mg/g)")
                else:
                    st.error(f"**RACU: {racu_val:.1f} mg/g**\n\n🔴 A3 — Albuminuria severa\n(>300 mg/g)")

            st.markdown("""
| RACU (mg/g) | Categoría | Estadio |
|-------------|-----------|---------|
| <10 | Normal | A1 |
| 10–29 | Normal-alto | A1 |
| 30–300 | Albuminuria moderada | A2 — Microalbuminuria |
| >300 | Albuminuria severa | A3 — Macroalbuminuria |
| >2,200 | Rango nefrótico | A3 |
            """)
            st.caption("**Conversión rápida:** mg/dL × 10 = mg/L | Resultado en mg/g (equivalente a mg/mmol × 8.84)")
            st.caption("Ref: KDIGO CKD 2024 | Levey AS et al. Kidney International 2011")

        # ── RPCU ──────────────────────────────────────────────────────────────
        elif "RPCU" in calc_sel:
            st.markdown("### 🔬 RPCU — Relación Proteína/Creatinina Urinaria")
            rp1, rp2, rp3 = st.columns(3)
            with rp1:
                rpcu_prot = st.number_input("Proteína urinaria (mg/dL)", 0.0, 2000.0, 30.0, 1.0, key="rpcu_prot")
            with rp2:
                rpcu_cr   = st.number_input("Creatinina urinaria (mg/dL)", 0.0, 500.0, 100.0, 1.0, key="rpcu_cr")
            rpcu_val = (rpcu_prot / rpcu_cr) * 1000 if rpcu_cr > 0 else 0  # mg/g
            with rp3:
                st.markdown(" ")
                if rpcu_val < 150:
                    st.success(f"**RPCU: {rpcu_val:.0f} mg/g** — Normal")
                elif rpcu_val < 500:
                    st.warning(f"**RPCU: {rpcu_val:.0f} mg/g** — Proteinuria leve")
                elif rpcu_val < 3500:
                    st.error(f"**RPCU: {rpcu_val:.0f} mg/g** — Proteinuria significativa")
                else:
                    st.error(f"**RPCU: {rpcu_val:.0f} mg/g** — Rango nefrótico (>3,500 mg/g)")
            st.caption("Equivalencia: RPCU (mg/g) ≈ Proteinuria en orina 24h (mg/día) | Ref: KDIGO 2024")

        # ── FENa / FEUrea ──────────────────────────────────────────────────────
        elif "FENa" in calc_sel:
            st.markdown("### 🧂 FENa / FEUrea — Diferencial Prerrenal vs Renal")
            st.caption("Útil en oliguria/AKI para diferenciar causa prerrenal de intrínseca.")

            fe1, fe2 = st.columns(2)
            with fe1:
                st.markdown("**Datos séricos:**")
                fe_na_s  = st.number_input("Na sérico (mEq/L)", 100.0, 170.0, 140.0, 1.0, key="fe_na_s")
                fe_cr_s  = st.number_input("Creatinina sérica (mg/dL)", 0.1, 30.0, 2.0, 0.1, key="fe_cr_s")
                fe_urea_s = st.number_input("BUN sérico (mg/dL)", 1.0, 200.0, 40.0, 1.0, key="fe_urea_s")
            with fe2:
                st.markdown("**Datos urinarios:**")
                fe_na_u  = st.number_input("Na urinario (mEq/L)", 0.0, 300.0, 20.0, 1.0, key="fe_na_u")
                fe_cr_u  = st.number_input("Creatinina urinaria (mg/dL)", 0.0, 500.0, 120.0, 1.0, key="fe_cr_u")
                fe_urea_u = st.number_input("BUN urinario (mg/dL)", 0.0, 2000.0, 400.0, 10.0, key="fe_urea_u")

            fena  = (fe_na_u * fe_cr_s) / (fe_na_s * fe_cr_u) * 100 if (fe_na_s * fe_cr_u) > 0 else 0
            feurea = (fe_urea_u * fe_cr_s) / (fe_urea_s * fe_cr_u) * 100 if (fe_urea_s * fe_cr_u) > 0 else 0

            rc1, rc2 = st.columns(2)
            with rc1:
                color_na = "success" if fena < 1 else ("warning" if fena < 2 else "error")
                dx_na = "🟢 Prerrenal / Hepatorrenal" if fena < 1 else ("🟡 Indeterminado" if fena < 2 else "🔴 Necrosis tubular aguda")
                getattr(st, color_na)(f"**FENa: {fena:.2f}%**\n\n{dx_na}")
            with rc2:
                color_u = "success" if feurea < 35 else "error"
                dx_u = "🟢 Prerrenal (útil si hay diuréticos)" if feurea < 35 else "🔴 NTA / Daño intrínseco"
                getattr(st, color_u)(f"**FEUrea: {feurea:.1f}%**\n\n{dx_u}")

            st.markdown("""
| | FENa | FEUrea | Interpretación |
|--|------|--------|---------------|
| **Prerrenal** | <1% | <35% | Túbulo intacto, reabsorbe avidamente |
| **NTA** | >2% | >50% | Daño tubular, pierde sodio |
| **Con diuréticos** | No confiable | <35% útil | FEUrea más confiable en este contexto |
| **Hepatorrenal** | <1% | <35% | Como prerrenal |
            """)
            st.caption("Ref: Steiner RW. Ann Intern Med 1984 | Carvounis CP. Am J Kidney Dis 2002")

        # ── OSMOLALIDAD ───────────────────────────────────────────────────────
        elif "Osmolalidad" in calc_sel:
            st.markdown("### 💧 Osmolalidad Plasmática & Gap Osmolar")
            os1, os2 = st.columns(2)
            with os1:
                os_na   = st.number_input("Na sérico (mEq/L)", 100.0, 170.0, 140.0, 1.0, key="os_na")
                os_glu  = st.number_input("Glucosa (mg/dL)", 50.0, 1000.0, 100.0, 1.0, key="os_glu")
                os_bun  = st.number_input("BUN (mg/dL)", 0.0, 200.0, 15.0, 1.0, key="os_bun")
                os_etoh = st.number_input("Etanol (mg/dL) — si aplica", 0.0, 500.0, 0.0, 1.0, key="os_etoh")
            with os2:
                os_medida = st.number_input("Osmolalidad medida (mOsm/kg) — si disponible",
                                             200.0, 400.0, 290.0, 1.0, key="os_med")

            osm_calc = 2*os_na + os_glu/18 + os_bun/2.8 + os_etoh/4.6
            gap_osm  = os_medida - osm_calc

            om1, om2, om3 = st.columns(3)
            om1.metric("Osmolalidad calculada", f"{osm_calc:.1f} mOsm/kg", help="Normal: 280–295")
            om2.metric("Osmolalidad medida", f"{os_medida:.0f} mOsm/kg")
            if gap_osm > 10:
                om3.metric("Gap osmolar", f"{gap_osm:.1f} mOsm/kg", delta="⚠️ Elevado (>10)", delta_color="inverse")
                st.error("Gap osmolar elevado — sospechar: metanol, etilenglicol, isopropanol, acetona, propilenglicol")
            else:
                om3.metric("Gap osmolar", f"{gap_osm:.1f} mOsm/kg", delta="Normal (<10)")
            st.caption("Fórmula: 2×Na + Glucosa/18 + BUN/2.8 (+Etanol/4.6). Normal: 280–295 mOsm/kg. Gap normal: <10.")

        # ── ANIÓN GAP URINARIO ────────────────────────────────────────────────
        elif "Anión Gap" in calc_sel:
            st.markdown("### ⚡ Anión Gap Urinario")
            st.caption("Evalúa la excreción de NH₄⁺. Útil en acidosis metabólica para diferenciar diarrea de ATR.")
            ag1, ag2, ag3 = st.columns(3)
            with ag1:
                agu_na = st.number_input("Na urinario (mEq/L)", 0.0, 300.0, 40.0, 1.0, key="agu_na")
            with ag2:
                agu_k  = st.number_input("K urinario (mEq/L)", 0.0, 200.0, 30.0, 1.0, key="agu_k")
            with ag3:
                agu_cl = st.number_input("Cl urinario (mEq/L)", 0.0, 300.0, 80.0, 1.0, key="agu_cl")
            agu_val = agu_na + agu_k - agu_cl
            if agu_val < 0:
                st.success(f"**Anión Gap Urinario: {agu_val:.0f} mEq/L (negativo)**\n\n"
                           "🟢 Excreción de NH₄⁺ adecuada → causa extrarrenal (diarrea, pérdidas GI)")
            else:
                st.error(f"**Anión Gap Urinario: {agu_val:.0f} mEq/L (positivo)**\n\n"
                         "🔴 Excreción de NH₄⁺ deficiente → causa renal (ATR tipo I, II o IV)")
            st.caption("AGU = Na_u + K_u – Cl_u. Negativo = renal acidifica bien. Positivo = ATR.")

        # ── CORRECCIÓN DE CALCIO ──────────────────────────────────────────────
        elif "Calcio" in calc_sel:
            st.markdown("### 🦴 Corrección de Calcio por Albúmina")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                cc_ca  = st.number_input("Calcio total sérico (mg/dL)", 4.0, 16.0, 8.5, 0.1, key="cc_ca")
            with cc2:
                cc_alb = st.number_input("Albúmina sérica (g/dL)", 0.5, 6.0, 4.0, 0.1, key="cc_alb")
            with cc3:
                cc_alb_norm = st.number_input("Albúmina normal del lab (g/dL)", 3.0, 5.0, 4.0, 0.1, key="cc_albn")
            ca_corr = cc_ca + 0.8 * (cc_alb_norm - cc_alb)
            if ca_corr < 8.5:
                st.error(f"**Ca corregido: {ca_corr:.2f} mg/dL** — Hipocalcemia")
            elif ca_corr > 10.5:
                st.error(f"**Ca corregido: {ca_corr:.2f} mg/dL** — Hipercalcemia")
            else:
                st.success(f"**Ca corregido: {ca_corr:.2f} mg/dL** — Normal (8.5–10.5 mg/dL)")
            st.info("Si albumina baja, el calcio total subestima el Ca ionizado real. "
                    "Fórmula: Ca_corr = Ca_total + 0.8 × (Albúmina_normal – Albúmina_paciente)")
            st.caption("⚠️ En ERC: usar Ca ionizado cuando sea posible — la fórmula puede ser imprecisa. "
                       "Ref: Payne RB. Lancet 1973.")

        # ── DÉFICIT BICARBONATO / BRECHA ANIÓNICA ────────────────────────────
        else:
            st.markdown("### 🩸 Déficit de Bicarbonato & Brecha Aniónica")
            ba1, ba2 = st.columns(2)
            with ba1:
                st.markdown("**Gasometría / Labs séricos:**")
                bic_na  = st.number_input("Na (mEq/L)", 100.0, 170.0, 140.0, 1.0, key="bic_na")
                bic_cl  = st.number_input("Cl (mEq/L)", 70.0, 130.0, 104.0, 1.0, key="bic_cl")
                bic_hco3 = st.number_input("HCO₃⁻ actual (mEq/L)", 1.0, 40.0, 12.0, 0.5, key="bic_hco3")
                bic_alb  = st.number_input("Albúmina (g/dL)", 0.5, 6.0, 4.0, 0.1, key="bic_alb")
            with ba2:
                st.markdown("**Datos del paciente:**")
                bic_peso = st.number_input("Peso (kg)", 30.0, 200.0, 70.0, 1.0, key="bic_peso")
                bic_meta_hco3 = st.number_input("HCO₃⁻ meta (mEq/L)", 18.0, 26.0, 22.0, 0.5, key="bic_meta")

            # Cálculos
            deficit_hco3 = 0.5 * bic_peso * (bic_meta_hco3 - bic_hco3)
            ba = bic_na - bic_cl - bic_hco3
            ba_corr = ba + 2.5 * (4.0 - bic_alb)  # corrección por albúmina

            br1, br2, br3 = st.columns(3)
            br1.metric("Déficit de HCO₃⁻", f"{max(deficit_hco3,0):.0f} mEq",
                       help="0.5 × peso × (meta − actual)")
            if ba > 12:
                br2.metric("Brecha aniónica", f"{ba:.0f} mEq/L", delta="⚠️ Alta (>12)")
                br3.metric("BA corregida por albúmina", f"{ba_corr:.0f} mEq/L")
            else:
                br2.metric("Brecha aniónica", f"{ba:.0f} mEq/L", delta="Normal (≤12)")
                br3.metric("BA corregida por albúmina", f"{ba_corr:.0f} mEq/L")

            if ba > 12:
                st.error("**Acidosis metabólica con BA elevada** — causas: láctica, cetoacidosis, "
                         "urémica, tóxicos (metanol, etilenglicol, salicilatos)")
            else:
                st.info("**BA normal** — acidosis hiperclorémica: diarrea, ATR, dilucional, post-NaCl")

            if deficit_hco3 > 0:
                amp_hco3 = deficit_hco3 / 50  # ámpulas de 50 mEq
                st.markdown(f"**Reposición estimada:** {deficit_hco3:.0f} mEq NaHCO₃ "
                            f"≈ **{amp_hco3:.1f} ámpulas de 50 mEq**\n\n"
                            "⚠️ Reponer 50% en 4–6h, reevaluar gases y electrolitos.")
            st.caption("BA = Na – Cl – HCO₃. Normal: 8–12. Corrección albúmina: +2.5 por cada g/dL < 4. "
                       "Ref: Haber RJ. West J Med 1991.")

    # ── ANEMIA EN ERC ─────────────────────────────────────────────────────────
    elif nefro_modo == "🩸 Anemia en ERC":
        st.markdown("### Anemia en ERC — Diagnóstico, Hierro y AEE")
        st.caption("KDIGO 2012 Anemia in CKD + actualizaciones 2024.")

        # ── DATOS DEL PACIENTE ────────────────────────────────────────────────
        an1, an2, an3, an4 = st.columns(4)
        with an1:
            hgb = st.number_input("Hgb actual (g/dL)", 4.0, 20.0, 10.5, 0.1, key="an_hgb")
            hgb_sex = st.selectbox("Sexo", ["M", "F"], key="an_sex")
        with an2:
            ferritina = st.number_input("Ferritina (ng/mL)", 0.0, 2000.0, 150.0, 10.0, key="an_ferr")
            ist = st.number_input("IST (%)", 0.0, 60.0, 20.0, 1.0, key="an_ist",
                                  help="Índice de Saturación de Transferrina. Normal: 20–50%")
        with an3:
            an_contexto = st.selectbox("Contexto clínico",
                                       ["Prediálisis (ERC 3–5)", "Hemodiálisis crónica",
                                        "Diálisis Peritoneal", "Post-trasplante renal"], key="an_ctx")
            en_dialisis_an = "Hemodiálisis" in an_contexto or "Peritoneal" in an_contexto
            if en_dialisis_an:
                st.caption("📌 Paciente en diálisis — TFG no aplicable (<5 mL/min)")
                egfr_an = 4.0
            else:
                egfr_an = st.number_input("TFG estimada (mL/min)", 0.0, 120.0, 20.0, 1.0, key="an_egfr")
        with an4:
            reticulocitos = st.number_input("Reticulocitos (%)", 0.0, 10.0, 1.5, 0.1, key="an_retic")
            crp = st.number_input("PCR (mg/L)", 0.0, 300.0, 5.0, 1.0, key="an_crp",
                                  help="Proteína C Reactiva. Inflamación → resistencia a AEE")

        # ── DIAGNÓSTICO ───────────────────────────────────────────────────────
        umbral_dx = 13.0 if hgb_sex == "M" else 12.0
        tiene_anemia = hgb < umbral_dx
        deficit_abs = ferritina < 30
        deficit_hierro = ferritina < 100 or ist < 20
        hierro_ok = ferritina >= 200 and ist >= 20
        inflamacion = crp > 10

        st.divider()
        st.markdown("### 📋 Evaluación diagnóstica")

        # Explicar los umbrales claramente
        st.markdown("""
> **⚠️ Tres umbrales distintos en anemia ERC — no confundir:**
> - 🔴 **Diagnóstico de anemia** (OMS/KDIGO): Hgb <13 g/dL (H) / <12 g/dL (M)
> - 🟡 **Iniciar AEE** (KDIGO 2012): considerar cuando Hgb **<10 g/dL** (individualizado)
> - 🎯 **Meta de tratamiento**: mantener Hgb **10–11.5 g/dL** — NO pasar de 13 (riesgo CV)
        """)

        da1, da2, da3, da4 = st.columns(4)
        da1.metric("Anemia ERC (diagnóstico)", "✅ Presente" if tiene_anemia else "No",
                   delta=f"Hgb {hgb:.1f} g/dL (umbral OMS: {umbral_dx})")
        da2.metric("AEE indicado", "🟡 Considerar" if hgb < 10 else ("✅ Meta lograda" if 10 <= hgb <= 11.5 else "⚠️ Hgb alta"),
                   delta="Hgb <10 → considerar AEE" if hgb >= 10 else f"Hgb {hgb:.1f} < 10 g/dL")
        da3.metric("Estado del hierro",
                   "🔴 Déficit absoluto" if deficit_abs else ("🟡 Déficit funcional" if deficit_hierro else "✅ Adecuado"),
                   delta=f"Ferritina {ferritina:.0f} | IST {ist:.0f}%")
        da4.metric("Respuesta medular",
                   "⚠️ Inapropiada" if reticulocitos < 1.0 else "✅ Adecuada",
                   delta=f"Reticulocitos {reticulocitos:.1f}%")

        if hgb < 10 and deficit_hierro:
            st.error("⚠️ **Corregir hierro ANTES o junto con AEE.** "
                     "Iniciar AEE con hierro deficiente es inefectivo y costoso.")
        if inflamacion and hgb < 10:
            st.warning(f"⚠️ **PCR elevada ({crp:.0f} mg/L)** — inflamación activa. "
                       "Reduce respuesta a AEE. Tratar la causa subyacente.")

        # ── HIERRO IV ─────────────────────────────────────────────────────────
        st.divider()
        st.markdown("### 💉 Hierro IV")
        peso_anemia = float(st.session_state.get("sb_peso", 70.0))

        if deficit_abs:
            st.error("🔴 Deficiencia absoluta (Ferritina <30) → **Hierro IV urgente**")
        elif deficit_hierro:
            st.warning("🟡 Deficiencia funcional → **Hierro IV antes de escalar AEE**")
        else:
            st.success("✅ Hierro adecuado. Mantener con hierro IV de mantenimiento en HD.")

        hierro_tipo = st.selectbox("Preparación de hierro IV disponible",
                                   ["Hierro sacarosa (Venofer® 20 mg/mL, ámp 5mL = 100 mg)",
                                    "Hierro carboximaltosa (Ferinject® 50 mg/mL)",
                                    "Hierro dextran bajo peso molecular (Cosmofer®)"],
                                   key="hierro_tipo")
        if "sacarosa" in hierro_tipo:
            st.info(f"""
📋 **Hierro sacarosa (Venofer®):** ámpulas 5 mL = 100 mg Fe elemental
- **HD crónica:** 100–200 mg IV **post-sesión** × 10 sesiones (1,000–2,000 mg total)
- **Prediálisis / PD:** 200 mg IV en 100 mL NaCl 0.9% en 30 min, c/semana × 5
- Tasa máxima: 100 mg en 15 min; 200 mg en 30 min
- Meta: **Ferritina 200–500 ng/mL + IST 25–35%**
            """)
        elif "carboximaltosa" in hierro_tipo:
            st.info(f"""
📋 **Hierro carboximaltosa (Ferinject®):** frascos 500 mg / 1,000 mg
- Dosis única: **500–1,000 mg IV** sin dosis prueba
- Infusión: 500 mg en 6–15 min; 1,000 mg en 15 min (bolo IV lento)
- Puede repetir a las **4–8 semanas** si persiste déficit
- Ventaja: dosis altas en visita única (ideal prediálisis y PD)
            """)
        else:
            st.info("""
📋 **Hierro dextran (Cosmofer®):** requiere dosis prueba 25 mg IV
- Luego: 100–1,000 mg según déficit calculado
- Test de tolerancia obligatorio antes de la dosis completa
- Menor uso por mayor riesgo de reacciones (anafilaxia 0.6%)
            """)

        # ── CALCULADORA AEE ───────────────────────────────────────────────────
        st.divider()
        st.markdown("### 💊 Agentes Estimulantes de Eritropoyesis (AEE)")

        aee_modo = st.radio("Modo de cálculo",
                            ["🆕 Paciente nuevo — dosis inicial",
                             "🔄 Paciente en AEE — ajuste de dosis",
                             "🔁 Conversión entre AEEs",
                             "🧬 Clase nueva: HIF-PHI"],
                            horizontal=True, key="aee_modo")

        en_hd = "Hemodial" in an_contexto
        en_pd = "Peritoneal" in an_contexto

        # ── MODO 1: NUEVO ─────────────────────────────────────────────────────
        if "nuevo" in aee_modo:
            if hgb >= 10.0:
                st.warning(f"⚠️ Hgb actual {hgb:.1f} g/dL — AEE **no indicado** de inicio. "
                           f"KDIGO recomienda considerar AEE solo con Hgb <10 g/dL.")
                st.caption("Si el paciente tiene Hgb entre 10–11.5 con AEE previo, ir a modo 'Ajuste de dosis'.")
            else:
                st.success(f"✅ Hgb {hgb:.1f} g/dL < 10 — Criterio de inicio de AEE cumplido.")

            aee_n1, aee_n2 = st.columns(2)
            with aee_n1:
                aee_nuevo_tipo = st.selectbox("AEE a iniciar",
                                              ["Epoetina alfa",
                                               "Epoetina beta (NeoRecormon®)",
                                               "Darbepoetina alfa (Aranesp®)",
                                               "Metoxi-PEG-epoetina beta (Mircera®)"],
                                              key="aee_n_tipo")
            with aee_n2:
                peso_aee = st.number_input("Peso (kg)", 10.0, 200.0,
                                           float(st.session_state.get("sb_peso", 70.0)),
                                           0.5, key="aee_n_peso")

            # ── Epoetina alfa ──────────────────────────────────────────────────
            if "alfa" in aee_nuevo_tipo and "Darbe" not in aee_nuevo_tipo:
                marca_alfa = st.selectbox("Marca / presentación disponible",
                    ["Eprex® (Janssen) — gama completa",
                     "Epokine® (Pisa) — 2,000 / 4,000 / 10,000 UI",
                     "Hemax® (Chinoin) — 1,000 / 2,000 / 4,000 UI",
                     "Genérica institucional (IMSS/ISSSTE)"],
                    key="aee_marca_alfa")

                # Vials by brand
                if "Eprex" in marca_alfa:
                    viales_ref = [1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 20000, 40000]
                    pres_txt = "1,000 / 2,000 / 3,000 / 4,000 / 5,000 / 6,000 / 8,000 / 10,000 / 20,000 / 40,000 UI"
                elif "Epokine" in marca_alfa:
                    viales_ref = [2000, 4000, 10000]
                    pres_txt = "2,000 / 4,000 / 10,000 UI"
                elif "Hemax" in marca_alfa:
                    viales_ref = [1000, 2000, 4000]
                    pres_txt = "1,000 / 2,000 / 4,000 UI"
                else:
                    viales_ref = [2000, 4000, 10000]
                    pres_txt = "Variable — verificar formulario institucional"

                dosis_low  = 50 * peso_aee
                dosis_high = 100 * peso_aee
                frec = "3 × semana IV post-sesión" if en_hd else \
                       "3 × semana SC (o 1× semana esquema simplificado)"
                via_alfa = "IV" if en_hd else "SC"
                vial_sug = min(viales_ref, key=lambda x: abs(x - dosis_low))

                st.markdown(f"""
#### Epoetina alfa — Dosis inicial
| | |
|---|---|
| **Dosis por aplicación** | **{dosis_low:.0f} – {dosis_high:.0f} UI** (50–100 UI/kg) |
| **Frecuencia** | {frec} |
| **Vial sugerido** | **{vial_sug:,} UI** |
| **Vía** | {via_alfa} |
| **Presentaciones ({marca_alfa.split('—')[0].strip()})** | {pres_txt} |
| **Primera evaluación** | **4 semanas** |
| **Meta Hgb** | **10 – 11.5 g/dL** (no pasar de 13) |
                """)
                st.caption("💡 Epoetina alfa e Epoetina beta son bioequivalentes en dosis UI:UI. "
                           "El cálculo aplica igual para ambas marcas.")

            # ── Epoetina beta ──────────────────────────────────────────────────
            elif "beta" in aee_nuevo_tipo and "Metoxi" not in aee_nuevo_tipo:
                viales_beta = [1000, 2000, 3000, 4000, 5000, 6000, 10000, 20000, 30000]
                dosis_low  = 50 * peso_aee
                dosis_high = 100 * peso_aee
                frec_beta = "3 × semana IV post-sesión" if en_hd else \
                            "1–3 × semana SC o 1× semana (mantenimiento SC)"
                vial_beta = min(viales_beta, key=lambda x: abs(x - dosis_low))

                st.markdown(f"""
#### Epoetina beta — NeoRecormon® (Roche) — Dosis inicial
| | |
|---|---|
| **Dosis por aplicación** | **{dosis_low:.0f} – {dosis_high:.0f} UI** (50–100 UI/kg) |
| **Frecuencia (inicio)** | {frec_beta} |
| **Vial sugerido** | **{vial_beta:,} UI** |
| **Vía** | IV (HD) o SC (prediálisis / PD) |
| **Presentaciones** | 1,000 / 2,000 / 3,000 / 4,000 / 5,000 / 6,000 / 10,000 / 20,000 / 30,000 UI |
| **Ventaja vs epoetina alfa** | Se puede dar **1× semana SC** en mantenimiento (menor frecuencia) |
| **Primera evaluación** | **4 semanas** |
| **Meta Hgb** | **10 – 11.5 g/dL** |
                """)
                st.info("💡 **Equivalencia:** Epoetina beta e Epoetina alfa son 1:1 en UI. "
                        "Puedes intercambiarlas manteniendo la misma dosis total semanal. "
                        "NeoRecormon® en jeringa prellenada es conveniente para SC domiciliario.")

            # ── Darbepoetina alfa ──────────────────────────────────────────────
            elif "Darbepoetina" in aee_nuevo_tipo:
                dosis_sem = round(0.45 * peso_aee, 1)
                dosis_2sem = round(0.75 * peso_aee, 1)
                darb_viales = [10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 130, 150, 200, 300, 500]
                vial_darb_sem = min(darb_viales, key=lambda x: abs(x - dosis_sem))
                vial_darb_2s  = min(darb_viales, key=lambda x: abs(x - dosis_2sem))
                via_darb = "IV post-HD" if en_hd else "SC"

                st.markdown(f"""
#### Darbepoetina alfa — Aranesp® — Dosis inicial
| Esquema | Dosis para {peso_aee:.0f} kg | Vial sugerido | Frecuencia | Vía |
|---------|---------------------------|---------------|-----------|-----|
| **Semanal** | **{dosis_sem:.1f} mcg** | {vial_darb_sem} mcg | 1 × semana | {via_darb} |
| **Quincenal** | **{dosis_2sem:.1f} mcg** | {vial_darb_2s} mcg | 1 × 2 semanas | {via_darb} |

**Presentaciones Aranesp®:** 10 / 15 / 20 / 25 / 30 / 40 / 50 / 60 / 80 / 100 / 130 / 150 / 200 / 300 / 500 mcg
**Primera evaluación:** 4 semanas · **Meta:** 10 – 11.5 g/dL
                """)
                st.caption("Darbepoetina dura más que epoetina alfa (t½ ~25h vs ~8h). "
                           "Se puede pasar a quincenal una vez estabilizado.")

            # ── Mircera ────────────────────────────────────────────────────────
            else:
                dosis_mircera = round(0.6 * peso_aee, 1)
                mircera_viales = [30, 50, 75, 100, 120, 150, 200, 250, 360]
                vial_mircera = min(mircera_viales, key=lambda x: abs(x - dosis_mircera))

                st.markdown(f"""
#### Metoxi-PEG-epoetina beta — Mircera® (Roche) — Dosis inicial
| | |
|---|---|
| **Dosis** | **{dosis_mircera:.1f} mcg** ({peso_aee:.0f} kg × 0.6 mcg/kg) |
| **Vial sugerido** | **{vial_mircera} mcg** |
| **Frecuencia** | **1 vez al mes** (cada 4 semanas) |
| **Vía** | SC o IV |
| **Presentaciones** | 30 / 50 / 75 / 100 / 120 / 150 / 200 / 250 / 360 mcg/jeringa prellenada |
| **Ventaja** | Dosis mensual — máxima adherencia, ideal para pacientes con dificultad de seguimiento |
| **Primera evaluación** | A las **4 semanas** (después del 2° mes para valorar respuesta completa) |
                """)

        # ── MODO 4: HIF-PHI ───────────────────────────────────────────────────
        elif "HIF" in aee_modo:
            st.markdown("### 🧬 Inhibidores de HIF-PH (HIF Prolyl Hydroxylase Inhibitors)")
            st.info("**Nueva clase terapéutica** — mecanismo diferente a los AEE clásicos. "
                    "Disponibilidad limitada en México actualmente.")

            st.markdown("""
#### ¿Cómo funcionan?

Los **HIF-PHI** actúan bloqueando la enzima **prolil-hidroxilasa** (PHD), que normalmente degrada el factor HIF-1α (Hypoxia-Inducible Factor):

- En condiciones normales: PHD hidroxila HIF-1α → ubiquitinación → degradación
- Con HIF-PHI: PHD inhibida → HIF-1α se estabiliza → activa la transcripción de **eritropoyetina endógena**
- También mejoran la absorción de hierro (↑ hepcidina inversa, ↑ expresión ferroportina)
- Mecanismo: **oral**, a diferencia de AEE parenterales

> **Ventaja clave:** funcionan incluso en presencia de inflamación (donde los AEE clásicos pierden eficacia por hepcidina elevada)
            """)

            hif_data = {
                "Roxadustat (Evrenzo®)": {
                    "lab": "AstraZeneca / FibroGen",
                    "disponibilidad": "Aprobado en UE, China, Japón. **No aprobado en México ni EUA aún** (FDA rechazó 2021 por señales CV)",
                    "dosis_inicio": "70–100 mg 3×/semana VO",
                    "presentaciones": "20 / 50 / 100 / 150 / 200 mg tabletas",
                    "evidencia": "ROXSTAR, ROCKIES, SIERRAS, OLYMPUS — no inferioridad vs darbepoetina",
                    "nota": "⚠️ FDA: señal de mortalidad CV vs placebo en prediálisis. Usar con precaución.",
                },
                "Daprodustat (Jesduvroq®)": {
                    "lab": "GSK",
                    "disponibilidad": "Aprobado FDA 2023 (solo HD). Disponibilidad en México: pendiente",
                    "dosis_inicio": "4 mg/día VO (ajustar según respuesta)",
                    "presentaciones": "1 / 2 / 4 / 6 / 8 mg tabletas",
                    "evidencia": "ASCEND-D (HD), ASCEND-ND (prediálisis) — no inferioridad vs darbepoetina",
                    "nota": "Primer HIF-PHI aprobado por FDA. Solo para HD en EUA.",
                },
                "Vadadustat (Vafseo®)": {
                    "lab": "Akebia / Otsuka",
                    "disponibilidad": "Aprobado FDA 2023 (solo HD). México: pendiente",
                    "dosis_inicio": "300 mg/día VO",
                    "presentaciones": "150 / 300 mg tabletas",
                    "evidencia": "PRO2TECT (prediálisis), INNO2VATE (HD)",
                    "nota": "No inferioridad CV solo demostrada en HD, no en prediálisis.",
                },
                "Molidustat (Molidustat®)": {
                    "lab": "Bayer",
                    "disponibilidad": "Aprobado en Japón. No disponible en México",
                    "dosis_inicio": "25–75 mg/día VO (individualizado)",
                    "presentaciones": "5 / 10 / 15 / 25 / 50 / 75 / 100 / 150 / 200 mg",
                    "evidencia": "MIYABI — no inferioridad en HD y prediálisis",
                    "nota": "Solo disponible en Japón actualmente.",
                },
            }

            hif_sel = st.selectbox("Agente HIF-PHI", list(hif_data.keys()), key="hif_sel")
            h = hif_data[hif_sel]

            hc1, hc2 = st.columns(2)
            with hc1:
                st.markdown(f"**Laboratorio:** {h['lab']}")
                st.markdown(f"**Disponibilidad:** {h['disponibilidad']}")
                st.markdown(f"**Dosis inicio:** {h['dosis_inicio']}")
                st.markdown(f"**Presentaciones:** {h['presentaciones']}")
            with hc2:
                st.markdown(f"**Evidencia:** {h['evidencia']}")
                st.warning(h['nota'])

            st.divider()
            st.markdown("""
#### Comparativa HIF-PHI vs AEE clásicos
| | AEE clásicos | HIF-PHI |
|--|--------------|---------|
| **Vía** | SC / IV | **Oral** |
| **Frecuencia** | 1–3×/semana | Diario o 3×/semana |
| **Hierro** | No mejora absorción | ↑ absorción entérica |
| **Inflamación** | Pierde eficacia | Mantiene eficacia |
| **Disponibilidad MX** | ✅ Amplia | ⚠️ Limitada / no aprobada |
| **Costo** | Moderado | Alto (donde disponible) |
| **Seguridad CV** | Establecida | En evaluación (señales en prediálisis) |

**Conclusión práctica:** Los HIF-PHI son prometedores para pacientes resistentes a AEE por inflamación crónica, pero su disponibilidad en México es mínima y la seguridad CV a largo plazo aún se evalúa.
            """)
            st.caption("Ref: Fishbane S et al., NEJM 2019 | Singh AK et al., NEJM 2021 | Akebia Therapeutics 2023")

        # ── MODO 2: AJUSTE ────────────────────────────────────────────────────
        elif "Ajuste" in aee_modo:
            st.markdown("#### Ajuste de dosis según respuesta — KDIGO 2012/2024")
            st.caption("Evaluar respuesta cada **4 semanas**. No cambiar dosis antes de 4 semanas.")

            adj1, adj2, adj3 = st.columns(3)
            with adj1:
                aee_actual = st.selectbox("AEE actual",
                                          ["Epoetina alfa", "Darbepoetina alfa",
                                           "Metoxi-PEG-epoetina beta (Mircera®)"], key="aee_adj_tipo")
                if "Epoetina" in aee_actual and "Metoxi" not in aee_actual:
                    dosis_act = st.number_input("Dosis actual (UI/aplicación)", 1000, 40000, 4000, 500, key="aee_dosis_act")
                    freq_sel  = st.selectbox("Frecuencia", ["3×/semana","2×/semana","c/semana"], key="aee_freq")
                    unidad    = "UI"
                    # Weekly dose
                    freq_factor = {"3×/semana": 3, "2×/semana": 2, "c/semana": 1}.get(freq_sel, 1)
                    dosis_sem = dosis_act * freq_factor
                elif "Darb" in aee_actual:
                    dosis_act = st.number_input("Dosis actual (mcg/aplicación)", 10.0, 500.0, 40.0, 5.0, key="aee_dosis_act")
                    freq_sel  = st.selectbox("Frecuencia", ["c/semana","c/2 semanas","c/mes"], key="aee_freq")
                    unidad    = "mcg"
                    freq_factor_darb = {"c/semana": 1, "c/2 semanas": 0.5, "c/mes": 0.25}.get(freq_sel, 1)
                    dosis_sem = dosis_act * freq_factor_darb
                else:
                    dosis_act = st.number_input("Dosis actual (mcg/mes)", 30.0, 360.0, 120.0, 30.0, key="aee_dosis_act")
                    freq_sel  = "c/mes"
                    unidad    = "mcg"
                    dosis_sem = dosis_act / 4.33

            with adj2:
                hgb_hace4s = st.number_input("Hgb hace 4 semanas (g/dL)", 4.0, 20.0, 6.5, 0.1, key="aee_hgb_prev")

            with adj3:
                delta_hgb = hgb - hgb_hace4s
                st.metric("Δ Hgb en 4 semanas", f"{delta_hgb:+.1f} g/dL",
                          delta=f"{'↑ Sube' if delta_hgb>0 else '↓ Baja' if delta_hgb<0 else '→ Estable'}")
                peso_adj = st.number_input("Peso (kg)", 30.0, 150.0,
                                           float(st.session_state.get("sb_peso", 70.0)),
                                           1.0, key="aee_peso_adj")

            # Hiporrespuesta threshold
            if "Darb" in aee_actual:
                dosis_kg_sem = dosis_sem / peso_adj
                hipo_umbral  = 1.5  # mcg/kg/semana para darb
                es_hiporrespuesta = dosis_kg_sem >= hipo_umbral and hgb < 10.0
            else:
                dosis_kg_sem = dosis_sem / peso_adj
                hipo_umbral  = 300  # UI/kg/semana para epoetina
                es_hiporrespuesta = dosis_kg_sem >= hipo_umbral and hgb < 10.0

            st.divider()

            # Adjustment logic (KDIGO Table 4)
            dosis_nueva = dosis_act
            if hgb > 13.0:
                accion_aee = "🛑 **SUSPENDER AEE** temporalmente. Hgb >13 g/dL = riesgo cardiovascular aumentado."
                dosis_nueva = 0; color_aee = "error"
            elif hgb > 11.5 and delta_hgb > 0:
                dosis_nueva = round(dosis_act * 0.75, 1)
                accion_aee = (f"⬇️ **REDUCIR 25%**: {dosis_act:.0f} → **{dosis_nueva:.0f} {unidad}** {freq_sel}. "
                              "Hgb sobre meta o ascendiendo hacia 13.")
                color_aee = "warning"
            elif delta_hgb > 2.0:
                dosis_nueva = round(dosis_act * 0.75, 1)
                accion_aee = (f"⬇️ **REDUCIR 25%**: {dosis_act:.0f} → **{dosis_nueva:.0f} {unidad}** {freq_sel}. "
                              "Ascenso demasiado rápido (>2 g/dL en 4 sem).")
                color_aee = "warning"
            elif delta_hgb >= 1.0 and 10.0 <= hgb <= 11.5:
                accion_aee = f"✅ **MANTENER** {dosis_act:.0f} {unidad} {freq_sel}. Respuesta adecuada, Hgb en meta."
                color_aee = "success"
            elif delta_hgb >= 1.0 and hgb < 10.0:
                accion_aee = (f"✅ **MANTENER** {dosis_act:.0f} {unidad} {freq_sel}. "
                              "Sube adecuado — aún bajo meta, continuar y reevaluar en 4 semanas.")
                color_aee = "success"
            elif es_hiporrespuesta:
                accion_aee = (f"🔴 **HIPORRESPUESTA AEE** — {dosis_kg_sem:.2f} {unidad[0].lower()}g/kg/sem ≥ umbral "
                              f"({hipo_umbral} {'mcg' if 'Darb' in aee_actual else 'UI'}/kg/sem) sin alcanzar meta. "
                              "**No aumentar dosis** — investigar causas. Ver abajo.")
                color_aee = "error"; dosis_nueva = dosis_act
            elif delta_hgb < 1.0 and hgb < 10.0:
                dosis_nueva = round(dosis_act * 1.25, 1)
                accion_aee = (f"⬆️ **AUMENTAR 25%**: {dosis_act:.0f} → **{dosis_nueva:.0f} {unidad}** {freq_sel}. "
                              "Respuesta insuficiente (<1 g/dL en 4 sem).")
                color_aee = "warning"
                if crp > 10:
                    accion_aee += f" ⚠️ PCR {crp:.0f} mg/L elevada — considerar hiporrespuesta por inflamación."
            else:
                accion_aee = f"ℹ️ **MANTENER** dosis actual. Reevaluar en 4 semanas."
                color_aee = "info"

            if color_aee == "success": st.success(accion_aee)
            elif color_aee == "warning": st.warning(accion_aee)
            elif color_aee == "error": st.error(accion_aee)
            else: st.info(accion_aee)

            # Show dose summary
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Dosis actual/aplicación", f"{dosis_act:.0f} {unidad}")
            mc2.metric("Dosis semanal equiv.", f"{dosis_sem:.0f} {unidad}/sem")
            mc3.metric("Dosis/kg/semana", f"{dosis_kg_sem:.2f} {unidad[0].lower()}g/kg/sem")

            # Hiporrespuesta workup
            if es_hiporrespuesta or (hgb < 10.0 and delta_hgb < 0.5):
                st.error("""
#### 🔍 Protocolo de investigación de hiporrespuesta AEE
*(Hgb no sube a pesar de dosis AEE adecuada)*

**Causas más frecuentes (buscar en este orden):**

| Causa | Estudio | Hallazgo | Manejo |
|-------|---------|---------|--------|
| **Déficit de hierro** | Ferritina + IST | Ferritina <200 o IST <20% | Hierro IV antes de aumentar AEE |
| **Inflamación / infección** | PCR, leucocitos | PCR >10 mg/L | Tratar causa + hierro si IST <30% |
| **Pérdida de sangre** | Heces/oculto, diálisis | — | Buscar y tratar fuente |
| **Déficit B12/ácido fólico** | B12, folato sérico | Bajos | Suplementar |
| **Hiperparatiroidismo** | PTHi | >300 pg/mL en HD | Control de PTH |
| **Hemólisis** | LDH, bilirrubina, frotis | Esquistocitos | Descartar TMA/TTP |
| **Aplasia eritroide (B19)** | PCR Parvovirus B19 | + | IVIG + reducir IS |
| **Aluminio** | Al sérico | >60 μg/L | Deferoxamina |
| **Timoglobulina reciente** | Historia | — | Esperar recuperación medular |
                """)

            st.markdown("""
#### Tabla de ajuste rápido KDIGO 2012
| Situación | Acción |
|-----------|--------|
| Hgb **>13 g/dL** | Suspender AEE |
| Hgb **>11.5** subiendo | ↓ 25% |
| Δ Hgb **>2 g/dL** en 4 sem | ↓ 25% |
| Δ Hgb **1–2 g/dL** en meta | Mantener |
| Δ Hgb **<1 g/dL** + Hgb <10 | ↑ 25% |
| Darb **≥1.5 mcg/kg/sem** sin meta | **Hiporrespuesta → investigar** |
| Epoetina **≥300 UI/kg/sem** sin meta | **Hiporrespuesta → investigar** |
            """)

        # ── MODO 3: CONVERSIÓN ────────────────────────────────────────────────
        elif "Conversión" in aee_modo:
            st.markdown("#### Conversión entre AEEs")
            st.caption("Epoetina alfa y beta son bioequivalentes 1:1 en UI — no requieren conversión entre sí.")

            cv1, cv2 = st.columns(2)
            with cv1:
                aee_from = st.selectbox("Convertir DESDE",
                                        ["Epoetina alfa o beta (UI/semana)",
                                         "Darbepoetina alfa (mcg/semana)",
                                         "Darbepoetina alfa (mcg/2 semanas)"],
                                        key="aee_from")
                if "Epoetina" in aee_from:
                    dosis_from = st.number_input("Dosis semanal total (UI/sem)",
                                                 500, 200000, 6000, 500, key="cv_from_val")
                elif "semana)" in aee_from:
                    dosis_from = st.number_input("Dosis semanal Darbepoetina (mcg/sem)",
                                                 5.0, 500.0, 20.0, 5.0, key="cv_from_val")
                else:
                    dosis_from = st.number_input("Dosis quincenal Darbepoetina (mcg/2sem)",
                                                 5.0, 500.0, 30.0, 5.0, key="cv_from_val")
            with cv2:
                aee_to = st.selectbox("Convertir A",
                                      ["Darbepoetina alfa (mcg/semana)",
                                       "Darbepoetina alfa (mcg/2 semanas)",
                                       "Metoxi-PEG-epoetina beta — Mircera® (mcg/mes)",
                                       "Epoetina alfa/beta (UI/semana)"],
                                      key="aee_to")

            darb_viales = [10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 130, 150, 200, 300, 500]
            mircera_viales = [30, 50, 75, 100, 120, 150, 200, 250, 360]

            if "Epoetina" in aee_from:
                epo_sem = dosis_from
            elif "semana)" in aee_from:
                epo_sem = dosis_from * 200
            else:
                epo_sem = (dosis_from / 2) * 200

            if "Darbepoetina" in aee_to and "semana)" in aee_to:
                resultado = epo_sem / 200
                vial_sug = min(darb_viales, key=lambda x: abs(x - resultado))
                res_txt = f"**{resultado:.1f} mcg/semana** — Vial sugerido: **{vial_sug} mcg**"
                res_freq = "1 × semana SC/IV"
            elif "2 semanas" in aee_to:
                resultado = (epo_sem / 200) * 2
                vial_sug = min(darb_viales, key=lambda x: abs(x - resultado))
                res_txt = f"**{resultado:.1f} mcg/2 semanas** — Vial sugerido: **{vial_sug} mcg**"
                res_freq = "1 × 2 semanas SC/IV"
            elif "Mircera" in aee_to:
                if epo_sem < 8000: mircera_dosis = 60
                elif epo_sem <= 16000: mircera_dosis = 120
                else: mircera_dosis = 180
                res_txt = f"**{mircera_dosis} mcg/mes**"
                res_freq = "1 × mes SC/IV"
            else:
                if "Epoetina" in aee_from:
                    res_txt = f"Ya es Epoetina: **{dosis_from:,.0f} UI/semana** (alfa o beta)"
                    res_freq = "3 × semana"
                elif "semana)" in aee_from:
                    epo_calc = dosis_from * 200
                    res_txt = f"**{epo_calc:,.0f} UI/semana** (÷ 3 = {epo_calc/3:,.0f} UI/aplicación)"
                    res_freq = "3 × semana SC/IV"
                else:
                    epo_calc = (dosis_from / 2) * 200
                    res_txt = f"**{epo_calc:,.0f} UI/semana** (÷ 3 = {epo_calc/3:,.0f} UI/aplicación)"
                    res_freq = "3 × semana SC/IV"

            st.markdown(f"""
---
#### Resultado de la conversión
| Desde | Dosis | → | Hasta | Equivalente | Frecuencia |
|-------|-------|---|-------|-------------|-----------|
| {aee_from} | {dosis_from:g} | **→** | {aee_to} | {res_txt} | {res_freq} |
            """)

            st.info("💡 Al cambiar de AEE: iniciar con dosis equivalente, verificar Hgb a las **4 semanas** y ajustar ±25% según respuesta.")
            st.info("💡 **Epoetina alfa ↔ beta:** conversión 1:1 en UI. No requieren ajuste entre sí.")

            st.markdown("#### Tabla de referencia rápida — Conversión completa")
            st.markdown("""
| Epoetina alfa/beta (UI/sem) | Darbepoetina (mcg/sem) | Darbepoetina (mcg/2sem) | Mircera (mcg/mes) |
|----------------------------|----------------------|------------------------|------------------|
| <2,500 | 6.25 | 12.5 | 60 |
| 2,500–4,999 | 12.5 | 25 | 60 |
| 5,000–10,999 | 25 | 50 | 120 |
| 11,000–17,999 | 40 | 80 | 120 |
| 18,000–33,999 | 60 | 120 | 180 |
| 34,000–89,999 | 100 | 200 | 180 |
| ≥90,000 | 200 | 400 | 360 |
            """)
            st.caption("Ref: KDIGO 2012 Tabla 4. Mircera: ficha técnica Roche. Ajustar siempre por respuesta clínica.")



    # ── MEDICAMENTOS EN ERC ────────────────────────────────────────────────────
    else:
        st.markdown("### 💊 Ajuste de Medicamentos en ERC y Diálisis")
        st.caption("Referencia rápida. Siempre verificar en ficha técnica actualizada y Micromedex/UpToDate.")
        st.warning("⚠️ Esta guía es de referencia orientativa. Individualizar según función renal actual, contexto clínico y disponibilidad institucional.")

        cat_med = st.selectbox("Categoría de medicamento",
                               ["Antibióticos (ICU)", "Cardiovascular / Metabólico",
                                "Analgésicos / Neurológico", "Inmunosupresores (Trasplante)",
                                "Diuréticos", "Hipoglucemiantes"], key="cat_med")

        if cat_med == "Antibióticos (ICU)":
            st.markdown("""
| Medicamento | TFG 30–60 | TFG 15–29 | TFG <15 o Diálisis | Notas |
|------------|-----------|-----------|-------------------|-------|
| **Piperacilina/tazobactam** | Sin cambio | 3.375g c/8h | 2.25g c/8h | Eliminar dosis extra post-HD |
| **Meropenem** | Sin cambio | 1g c/12h | 0.5g c/24h | Ajustar según CMI patógeno |
| **Imipenem** | Sin cambio | 250mg c/6h | 250mg c/12h | Riesgo convulsiones si ↑ dosis |
| **Vancomicina** | Ajustar por nivel | Ajustar | 20–25 mg/kg post-HD | Meta AUC/MIC 400–600 |
| **Ceftriaxona** | Sin cambio | Sin cambio | Sin cambio | Excreción biliar predominante |
| **Levofloxacino** | 500mg c/24h | 250mg c/24h | 500mg carga, 250 c/48h | Ajuste significativo |
| **Ciprofloxacino** | 200–400mg c/18h | 200mg c/24h | 200mg c/24h | — |
| **Gentamicina** | Extender intervalo | Monitorear | Monitorear niveles | Nefrotóxico — evitar si posible |
| **Ampicilina** | Sin cambio | 1g c/6h | 1g c/12h | Acúmulo de metabolitos |
| **Fluconazol** | Sin cambio | Reducir 50% | 50% dosis normal | Post-HD: dosis adicional |
| **Aciclovir** | Reducir 25% | Reducir 50% | 2.5–5 mg/kg c/24h | Nefrotóxico; hidratar bien |
| **Ganciclovir** | 1.25–2.5 mg/kg c/24h | 0.625 mg/kg c/24h | Post-HD: 1.25mg/kg | Mielosupresor |
            """)

        elif cat_med == "Cardiovascular / Metabólico":
            st.markdown("""
| Medicamento | TFG 30–60 | TFG <30 | Diálisis | Notas críticas |
|------------|-----------|---------|---------|----------------|
| **Metformina** | Reducir 50%; monitorear | ⛔ **CONTRAINDICADA** | ⛔ **CONTRAINDICADA** | Riesgo acidosis láctica fatal |
| **Digoxina** | Reducir 25–50% | Reducir 50% | Evitar | Índice terapéutico estrecho |
| **Atenolol** | Reducir 50% | 25mg/día | Dosis post-HD | Eliminado en HD |
| **Espironolactona** | Cautela | ⛔ Contraindicada | ⛔ Contraindicada | Riesgo hipercalemia grave |
| **IECA/ARA II** | Continuar; monitorear K y Cr | Cautela; ajustar | Continuar si tolera | Monitoreo estrecho K |
| **Atorvastatina** | Sin cambio | Sin cambio | Sin cambio | No requiere ajuste |
| **Furosemida** | Dosis más altas necesarias | ↑ dosis (hasta 500mg/día) | Ineficaz en anuria | HD > diurético en sobrecarga |
| **Amlodipino** | Sin cambio | Sin cambio | Sin cambio | Metabolismo hepático |
| **Warfarina** | Sin cambio; monitorear INR | Mayor sensibilidad | Sin cambio; INR frecuente | Acumulación de metabolitos |
| **Heparina** | Sin cambio | Sin cambio | Sin cambio | No requiere ajuste renal |
            """)

        elif cat_med == "Analgésicos / Neurológico":
            st.markdown("""
| Medicamento | TFG 30–60 | TFG <30 | Diálisis | Alternativa en ERC |
|------------|-----------|---------|---------|-------------------|
| **Morfina** | Reducir 25% | ⚠️ Evitar | ⚠️ Evitar | Metabolito M6G acumula → sedación |
| **Tramadol** | Extender intervalo | ⚠️ Evitar | ⚠️ Evitar | Convulsiones en ERC |
| **Gabapentina** | 300mg c/12h | 300mg c/24h | 300mg post-HD | Ajuste muy significativo |
| **Pregabalina** | 75mg c/12h | 25–50mg c/12h | 25mg/día | Igual que gabapentina |
| **Tramadol** | 50–100mg c/12h | 50mg c/12h | Evitar | — |
| **Ketorolaco** | ⚠️ Cautela | ⛔ Evitar | ⛔ Evitar | AINES = nefrotóxicos |
| **Ibuprofeno** | ⚠️ Cautela | ⛔ Evitar | ⛔ Evitar | AINES nefrotóxicos |
| **Paracetamol** | Sin cambio | Sin cambio | Sin cambio | ✅ Analgésico de elección en ERC |
| **Fentanilo** | Sin cambio | Sin cambio | Sin cambio | ✅ Opioide de elección en ERC |
| **Levetiracetam** | 500mg c/12h | 250–500mg c/12h | 250–500mg c/24h + post-HD | — |
            """)
            st.info("✅ **Analgésico de elección en ERC:** Paracetamol (dosis normal). **Opioide de elección:** Fentanilo o Hidromorfona (metabolismo hepático).")

        elif cat_med == "Inmunosupresores (Trasplante)":
            st.markdown("""
| Medicamento | Ajuste en ERC | Monitoreo | Notas |
|------------|--------------|-----------|-------|
| **Tacrolimus** | Sin ajuste por función renal | Niveles en sangre (C₀) | Meta C₀: 8–12 ng/mL (mes 1–3); 5–8 (mes 3–12) |
| **Ciclosporina** | Sin ajuste por función renal | Niveles C₀ o C₂ | Nefrotóxico — monitoreo estrecho |
| **Micofenolato mofetil** | Reducir si TFG <25 | Leucocitos | Leucopenia dosis-dependiente |
| **Prednisona** | Sin ajuste | Glucemia, TA | Dosis de mantenimiento 5mg/día |
| **Everolimus** | Sin ajuste | Niveles, función renal | Nefrotóxico; vigilar proteinuria |
| **Sirolimus** | Sin ajuste por función renal | Niveles | No nefrotóxico per se |
| **Basiliximab** | Sin ajuste | — | Inducción; sin ajuste necesario |
| **Timoglobulina** | Sin ajuste | Leucocitos, plaquetas | Dosis según protocolo |
            """)

        elif cat_med == "Diuréticos":
            st.markdown("""
| Diurético | TFG 30–60 | TFG <30 | Diálisis | Notas |
|----------|-----------|---------|---------|-------|
| **Furosemida** | Dosis estándar | ↑↑ dosis (250–500mg/día) | Ineficaz si anuria | Puede combinarse con tiazida en resistencia |
| **Torasemida** | Dosis estándar | Dosis más altas | Poco efecto | Mayor biodisponibilidad oral que furosemida |
| **Hidroclorotiazida** | Reducir eficacia | ⛔ Sin efecto <30 | ⛔ Sin efecto | Ineficaz con TFG <30 |
| **Clortalidona** | Mantiene algo de efecto | Cautela <30 | — | Mejor que HCTZ en ERC |
| **Espironolactona** | Cautela; monitorear K | ⛔ Contraindicada | ⛔ Contraindicada | Hipercalemia → paro cardíaco |
| **Eplerenona** | Cautela | ⛔ Contraindicada | ⛔ Contraindicada | Igual que espironolactona |
| **Acetazolamida** | Evitar | ⛔ Contraindicada | ⛔ Contraindicada | Acumulación tóxica |
            """)

        else:  # Hipoglucemiantes
            st.markdown("""
| Medicamento | TFG 45–60 | TFG 30–45 | TFG <30 | Diálisis | Alternativa |
|------------|-----------|-----------|---------|---------|------------|
| **Metformina** | Reducir 50% | Reducir; vigilar | ⛔ **CONTRAINDICADA** | ⛔ **CONTRAINDICADA** | Insulina |
| **Empagliflozina** | Sin cambio si TFG≥20 | Cautela | No usar si TFG<20 | ⛔ Contraindicada | Insulina/GLP-1 |
| **Dapagliflozina** | Sin cambio si TFG≥25 | Menos eficaz | No usar si TFG<25 | ⛔ Contraindicada | — |
| **Sitagliptina** | Sin cambio | 50mg/día | 25mg/día | 25mg/día | — |
| **Linagliptina** | Sin cambio | Sin cambio | Sin cambio | Sin cambio | ✅ No requiere ajuste |
| **Glibenclamida** | ⚠️ Cautela | ⛔ Evitar | ⛔ Evitar | ⛔ Evitar | Riesgo hipoglucemia prolongada |
| **Glipizida** | Sin cambio | Reducir | Reducir | Cautela | Menor acumulación que glibenclamida |
| **Insulina** | Reducir 25% | Reducir 50% | Reducir 75% | Reducir 75% | ✅ De elección en ERC avanzada |
            """)
            st.info("✅ **Hipoglucemiante de elección en ERC avanzada (TFG <30):** Insulina. Linagliptina si monoterapia oral.")

    st.divider()
    st.caption("Fuentes: KDIGO 2012/2021, Micromedex, Lexicomp, Drug Prescribing in Renal Failure (Bennett). Actualizar según fichas técnicas vigentes.")

elif nav == "complic":
    st.subheader("🔧 Complicaciones del Circuito TRRC & Transición a HD Intermitente")
    comp_modo = st.radio("Sección",
        ["⚙️ Troubleshooting del circuito", "🛑 Cuándo suspender TRRC", "🔄 Transición a HD intermitente"],
        horizontal=True, key="comp_modo")

    if comp_modo == "⚙️ Troubleshooting del circuito":
        st.markdown("### ⚙️ Guía de Troubleshooting")
        st.caption("Abordaje sistemático de las complicaciones más frecuentes del circuito de TRRC.")

        problema = st.selectbox("Selecciona el problema", [
            "🔴 Coagulación del filtro / pérdida del circuito",
            "🟠 Presiones de acceso (inlet) elevadas",
            "🟠 Presiones de retorno (outlet) elevadas",
            "🟡 Acumulación de citrato",
            "🟡 Hipotermia",
            "🔵 Alarmas de volumen / balance",
            "🔵 Hipofosforemia / hipomagnesemia",
        ], key="comp_problema")

        guias = {
            "🔴 Coagulación del filtro / pérdida del circuito": {
                "causas": """
- Fracción de filtración (FF) >25% → hemoconcentración en el filtro
- Anticoagulación insuficiente (aPTT <45s con HNF, iCa post-filtro >0.45 con citrato)
- Flujo sanguíneo bajo (Qb <100 mL/min)
- Interrupciones frecuentes del circuito (transfusiones, movilización)
- Coagulopatía de base (CID, plaquetas muy elevadas)
                """,
                "signos": "↑ TMP (presión transmembrana), ↓ flujo de efluente, filtro oscuro/negro, coágulos visibles en cámara venosa",
                "manejo": """
**Inmediato:**
1. Evaluar anticoagulación: aPTT actual + dosis HNF (o iCa post-filtro si RCA)
2. Si FF >25%: ↑ flujo pre-dilución o ↓ efluente total
3. Flush con NaCl 0.9% 200 mL rápido si el circuito aún fluye
4. Si filtro coagulado → **cambiar circuito completo**

**Preventivo:**
- Mantener FF 20–25%, nunca >30%
- Optimizar anticoagulación antes de interrupciones programadas
- Bolo de HNF 1,000–2,000 UI antes de transfusiones o procedimientos
- Minimizar tiempo de circuito detenido (<20 min)
                """
            },
            "🟠 Presiones de acceso (inlet) elevadas": {
                "causas": """
- Catéter contra la pared del vaso (posición)
- Trombo en lumen de acceso
- Catéter doblado o con kink
- Paciente con pierna flexionada (femoral)
                """,
                "signos": "Presión acceso muy negativa (< −200 mmHg), alarma repetida, bajo Qb",
                "manejo": """
1. Reposicionar al paciente (extender pierna si femoral, rotar cabeza si yugular)
2. Rotar catéter 180° e intentar aspirar
3. Intentar invertir líneas (usar lumen venoso como arterial)
4. Flush manual con NaCl 0.9% 10 mL en cada lumen
5. Si persiste: considerar instilación de rtPA 1 mg/lumen × 30–60 min (si disponible)
6. Si sin resolución → cambiar acceso vascular
                """
            },
            "🟠 Presiones de retorno (outlet) elevadas": {
                "causas": """
- Estenosis o trombosis en segmento venoso del catéter
- Kink en línea de retorno
- Trombo en cámara venosa del circuito
                """,
                "signos": "Presión retorno >250 mmHg, alarma repetida",
                "manejo": """
1. Inspeccionar línea de retorno — buscar kink o doblez
2. Verificar posición del catéter (Rx si necesario)
3. Aspirar lumen venoso del catéter — si sale trombo: flush y continuar
4. Revisar cámara venosa del circuito — limpiar o reemplazar
5. Instilación de rtPA en lumen venoso si hay trombo confirmado
                """
            },
            "🟡 Acumulación de citrato": {
                "causas": """
- Disfunción hepática grave (cirrosis, falla hepática aguda, síndrome de Budd-Chiari)
- Dosis de citrato excesiva
- Shock severo con hipoperfusión hepática
                """,
                "signos": "Ca total/iCa sistémico >2.5, alcalosis metabólica inexplicable, ↓iCa sistémico persistente pese a infusión de calcio",
                "manejo": """
**Diagnóstico:**
- Ratio Ca_total/iCa_sistémico >2.5 mmol/mmol = acumulación de citrato

**Manejo:**
1. ↓ Tasa de citrato 10–20%
2. ↓ Qb para reducir la dosis total de citrato
3. Si persiste: cambiar a HNF (suspender RCA)
4. Corregir hipoperfusión hepática si es la causa
5. Monitoreo de Ca ionizado c/2–4h hasta estabilización

**Prevención:**
- No usar RCA si lactato >5 mmol/L o insuficiencia hepática grave
- Monitorear ratio Ca_total/iCa en cada turno
                """
            },
            "🟡 Hipotermia": {
                "causas": "Pérdida de calor a través del circuito extracorpóreo (especialmente con flujos altos y ambiente frío)",
                "signos": "T° central <36°C, escalofríos, taquicardia, vasoconstricción",
                "manejo": """
1. Activar calentador de solución en la máquina (si disponible) — target 37–38°C
2. Calentamiento externo: cobertores, aire caliente (Bair Hugger)
3. Si T° <35°C: evaluar reducir flujos temporalmente
4. Monitorear T° cada hora en pacientes críticos con TRRC

**Nota clínica:** La hipotermia en TRRC puede enmascarar fiebre y alterar la respuesta a sepsis. Un paciente con TRRC normotérmico puede estar febril sin criterios clínicos.
                """
            },
            "🔵 Alarmas de volumen / balance": {
                "causas": "Diferencia entre volumen infundido y efluente, burbujas, interrupciones",
                "signos": "Alarma de balance en la máquina, volumen acumulado fuera de objetivo",
                "manejo": """
1. Verificar que los flujos programados coincidan con los reales (revisar pantalla)
2. Reiniciar el balance si hubo interrupción prolongada
3. Ajustar UF para compensar diferencia acumulada
4. Verificar bolsas de solución — cambiar si están vacías
5. Documentar interrupciones y tiempo fuera de circuito
                """
            },
            "🔵 Hipofosforemia / hipomagnesemia": {
                "causas": "Remoción continua por el circuito; soluciones estándar no contienen fosfato",
                "signos": "Fosfato <2.0 mg/dL (fósforo) o Mg <1.5 mg/dL; debilidad muscular, falla de weaning ventilatorio",
                "manejo": """
Ver módulo **⚗️ Electrolitos & Bolsas** para cálculo de dosis de reposición.

**En urgencia:**
- Fósforo <1.0 mg/dL: 0.32–0.64 mmol/kg IV en 6–12h (máx 7 mmol/hr)
- Mg <1.2 mg/dL: MgSO₄ 2–4g IV en 2–4h

**Preventivo:** considerar agregar fosfato 1.0–1.5 mmol/L y Mg a bolsas si TRRC >24h
                """
            },
        }

        if problema in guias:
            g = guias[problema]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🔍 Causas frecuentes**")
                st.markdown(g["causas"])
            with c2:
                if "signos" in g:
                    st.markdown("**⚠️ Señales de alerta**")
                    st.info(g["signos"])
                st.markdown("**🛠️ Manejo**")
                st.markdown(g["manejo"])

    elif comp_modo == "🛑 Cuándo suspender TRRC":
        st.markdown("### 🛑 Criterios de Suspensión de TRRC")
        st.markdown("""
> La decisión de suspender TRRC es tan importante como la de iniciarla. Suspender demasiado pronto → rebote de falla renal. Suspender demasiado tarde → prolongar riesgos innecesarios.
        """)

        st.markdown("#### ✅ Criterios de recuperación renal (suspensión exitosa)")
        st.markdown("""
| Criterio | Valor orientativo | Nivel de evidencia |
|----------|------------------|-------------------|
| Diuresis espontánea | **>500 mL/día** sin diuréticos o **>1,000 mL/día** con furosemida | Moderado |
| Creatinina | Estable o en descenso sostenido × 24–48h | Moderado |
| Estabilidad hemodinámica | PAM >65 sin vasopresores (o dosis muy baja) | Bajo |
| Causa desencadenante | Controlada o en resolución | Experto |
| NGAL urinario | <200 ng/mL sugiere recuperación tubular | Exploratorio |
        """)

        st.markdown("#### 🔄 Trial de suspensión (weaning de TRRC)")
        st.info("""
**Protocolo sugerido:**
1. Suspender TRRC durante **24–48 horas** en prueba
2. Monitorear cada 6–8 horas: creatinina, diuresis, K, pH
3. **Éxito:** creatinina no sube >0.3 mg/dL en 24h + diuresis ≥500 mL/día
4. **Fracaso:** creatinina sube, oliguria, hipercalemia, acidosis → reiniciar TRRC o transitar a IHD
        """)

        st.markdown("#### ⛔ Criterios de suspensión definitiva (sin recuperación)")
        st.markdown("""
- **Recuperación irreversible no esperada:** KDIGO estadio 3 persistente >2 semanas sin recuperación
- **Transición a diálisis de mantenimiento:** IHD 3×/semana o DP si el paciente tolera
- **Limitación del esfuerzo terapéutico (LET):** decisión compartida con familia/paciente
        """)

        st.warning("⚠️ La recuperación renal post-TRRC es posible incluso después de semanas de terapia. No suspender prematuramente por ausencia de diuresis si la causa subyacente aún está activa.")

        st.caption("Ref: KDIGO 2012 AKI, STARRT-AKI, Wald R (NEJM 2020), Gibney N (Crit Care Med 2008)")

    else:
        st.markdown("### 🔄 Transición de TRRC a HD Intermitente (IHD)")
        st.markdown("""
> **¿Cuándo pasar de TRRC a IHD?** No siempre el paciente recupera función renal. Si requiere diálisis de mantenimiento pero ya no necesita soporte continuo, la transición a IHD convencional es el siguiente paso.
        """)

        st.markdown("#### Criterios para considerar transición a IHD")
        st.markdown("""
| Dominio | Criterio favorable para IHD |
|---------|---------------------------|
| **Hemodinámica** | PAM >65 mmHg sin vasopresores o con dosis mínima estable |
| **Tolerancia a UF** | Capaz de tolerar UF de 2–3 L en 4h sin hipotensión |
| **Acceso vascular** | Catéter funcionante o acceso permanente (FAV, Permcath) |
| **Causa** | No hay indicación activa de TRRC (no más sepsis, no edema cerebral) |
| **Frecuencia** | Diuresis <200 mL/día (si oligúrico) o necesidad persistente de diálisis |
        """)

        st.markdown("#### Proceso de transición")
        st.info("""
**Paso a paso:**
1. Evaluar tolerancia hemodinámica con un test: suspender TRRC 4–6h y monitorear PA
2. Solicitar acceso vascular definitivo si no lo tiene (Permcath, tunelizado)
3. Primera sesión de IHD: **3–3.5h**, UF conservadora (≤10 mL/kg/h)
4. Monitoreo estrecho: PA cada 15–30 min durante primera sesión
5. Ajustar prescripción según tolerancia y laboratorios post-sesión
        """)

        st.markdown("#### Ventajas de IHD vs TRRC")
        st.markdown("""
| | TRRC | IHD |
|--|------|-----|
| **Hemodinámica** | Mejor tolerada en inestabilidad | Requiere estabilidad |
| **Movilización** | Dificulta rehabilitación | Permite rehabilitación entre sesiones |
| **Control de solutos** | Continuo, gradual | Intermitente, más intenso |
| **Costo** | Mayor (insumos continuos) | Menor |
| **Acceso** | Catéter temporal | Catéter tunelizado o FAV |
        """)

        st.caption("Ref: Schetz M, Crit Care 2007 | Wald R, NEJM 2020 | KDIGO AKI 2012")

elif nav == "acceso":
    st.subheader("🫀 Acceso Vascular — TRRC y Hemodiálisis Crónica")
    acc_modo = st.radio("Sección",
        ["🔵 Catéteres para TRRC", "🟢 Acceso vascular para HD crónica", "📐 Vigilancia y complicaciones"],
        horizontal=True, key="acc_modo")

    if acc_modo == "🔵 Catéteres para TRRC":
        st.markdown("### 🔵 Catéteres para TRRC — Selección y Colocación")
        st.markdown("""
> El acceso vascular es el **talón de Aquiles de la TRRC**. Un catéter mal colocado o disfuncional es la causa más común de pérdida del circuito y subóptima entrega de dosis.
        """)

        st.markdown("#### Especificaciones del catéter")
        st.markdown("""
| Parámetro | Recomendación | Notas |
|-----------|--------------|-------|
| **Calibre** | 11–13.5 Fr, doble lumen | Mayor calibre = mayor flujo |
| **Longitud femoral** | 19–24 cm | Punta en VCI infrarrenal |
| **Longitud yugular D** | 15–16 cm | Punta en unión VCS-AD |
| **Longitud yugular I** | 19–20 cm | Más larga por trayecto tortuoso |
| **Flujo mínimo** | ≥150–200 mL/min | Para Qb objetivo de 200 mL/min |
| **Tipo** | No tunelizado (agudo) | Tunelizado si TRRC >2–3 semanas |
        """)

        st.markdown("#### Sitios de acceso — jerarquía recomendada")
        st.markdown("""
| Orden | Sitio | Ventajas | Desventajas |
|-------|-------|----------|-------------|
| **1°** | Yugular interna derecha | Línea recta a AD, bajo riesgo neumotórax, menor infección que femoral | Requiere técnica, incómodo despierto |
| **2°** | Femoral (cualquier lado) | Fácil acceso, útil en urgencia | Mayor infección, flujo afectado por posición de cadera, trombosis |
| **3°** | Yugular interna izquierda | Accesible | Trayecto tortuoso (ángulo con VCS), mayor riesgo de malposición |
| **⛔ Evitar** | Subclavia | — | **Riesgo de estenosis venosa central** → afecta permanentemente la posibilidad de FAV ipsilateral |
        """)

        st.error("⛔ **Regla cardinal:** NUNCA colocar catéter subclavio en pacientes con ERC o en diálisis. La estenosis de la vena subclavia es permanente y compromete el brazo para FAV de por vida.")

        with st.expander("🔍 Verificación de posición y flujo"):
            st.markdown("""
**Post-colocación:**
- Rx de tórax obligatoria para catéteres yugulares (descartar neumotórax, verificar punta)
- Punta en unión VCS-aurícula derecha → flujo óptimo
- Si punta en vena cava superior alta: mayor riesgo de trombosis y flujo pobre

**Evaluación de flujo antes de conectar TRRC:**
- Aspirar y refluir cada lumen libremente
- Flujo por gravedad >100 mL/min en cada lumen = aceptable
- Si pobre flujo: reposicionar antes de conectar (rotar, retirar 1–2 cm)

**Sello del catéter (entre sesiones de TRRC):**
- Heparina 1,000 UI/mL (sello estándar) en cada lumen, volumen del lumen (+0.1 mL)
- CitraLock 46.7%: reservar para CRBSI o disfunción recurrente
- NO rtPA de rutina (reservar para oclusión confirmada)
            """)

        with st.expander("🧮 Cálculo de volumen de sello"):
            sel1, sel2 = st.columns(2)
            with sel1:
                vol_lumen = st.number_input("Volumen del lumen del catéter (mL)", 0.5, 3.0, 1.3, 0.1, key="acc_vol_lumen")
                n_lumens = st.selectbox("Número de lúmenes", [2, 3], key="acc_nlumen")
            with sel2:
                tipo_sello = st.selectbox("Tipo de sello",
                                          ["Heparina 1,000 UI/mL", "CitraLock 46.7%"],
                                          key="acc_sello_tipo")
            vol_sello = vol_lumen + 0.1
            st.metric(f"Volumen de sello por lumen", f"{vol_sello:.1f} mL",
                      help="+0.1 mL sobre el volumen del lumen para asegurar sellado")
            st.info(f"📋 Instalar **{vol_sello:.1f} mL** de {tipo_sello} en **cada uno** de los {n_lumens} lúmenes = {vol_sello*n_lumens:.1f} mL total")

    elif acc_modo == "🟢 Acceso vascular para HD crónica":
        st.markdown("### 🟢 Acceso Vascular para Hemodiálisis Crónica")
        st.markdown("""
> **Jerarquía estándar (KDOQI/KDIGO):** FAV autóloga > Prótesis (PTFE) > Catéter tunelizado
> El acceso vascular es considerado el **"talón de Aquiles" de la hemodiálisis crónica**.
        """)

        st.markdown("#### Fístula Arteriovenosa (FAV) — Gold Standard")
        st.markdown("""
| Aspecto | Detalle |
|---------|---------|
| **Tipo 1°** | Radiocefálica (muñeca) — menor flujo pero excelente durabilidad |
| **Tipo 2°** | Braquiocefálica (codo) — flujo mayor, maduración más rápida |
| **Tipo 3°** | Braquiobasílica (transposición) — útil cuando venas superficiales agotadas |
| **Maduración** | Mínimo 6–8 semanas; óptimo 3–4 meses antes de primera punción |
| **Regla de los 6** | Flujo ≥600 mL/min, diámetro ≥6 mm, profundidad ≤6 mm |
| **Ventajas** | Mayor durabilidad, menor infección, menor trombosis |
| **Desventajas** | Tiempo de maduración, puede no madurar (30–60% en pacientes diabéticos/ancianos) |
        """)

        st.info("💡 **Planificación:** La FAV debe crearse **con al menos 3–6 meses de anticipación** al inicio de diálisis. En ERC G4 (TFG <30), referir al cirujano vascular. Preservar venas del antebrazo dominante (no venopunciones, no catéteres IV).")

        st.markdown("#### Prótesis AV (PTFE / Dacron)")
        st.markdown("""
| Aspecto | Detalle |
|---------|---------|
| **Indicación** | Vasos inadecuados para FAV autóloga |
| **Sitio** | Braquioaxilar, braquiobasílica, en asa en antebrazo |
| **Uso** | 2–4 semanas post-implante (algunas inmediato si urgencia) |
| **Desventajas** | Mayor tasa de trombosis (10–30% al año) e infección (1–5%) |
| **Flujo** | 600–1,500 mL/min típico |
        """)

        st.markdown("#### Catéter Venoso Tunelizado (Permcath)")
        st.markdown("""
| Aspecto | Detalle |
|---------|---------|
| **Indicación** | Cuando FAV/prótesis no son posibles o como puente |
| **Sitios** | Yugular D (1°), yugular I (2°), femoral (3°) — **nunca subclavio** |
| **Uso** | Inmediato post-colocación |
| **Meta institucional** | <10% de pacientes prevalentes en catéter (KDOQI) |
| **Complicaciones** | Mayor CRBSI, recirculación 5–15%, estenosis central |
        """)

        st.error("📊 **Meta de calidad:** En una unidad de HD de excelencia, <10% de los pacientes deberían estar en catéter. >30% en catéter = indicador de problema de acceso vascular.")

    else:
        st.markdown("### 📐 Vigilancia del Acceso Vascular y Complicaciones")

        st.markdown("#### Monitoreo periódico del acceso")
        st.markdown("""
| Parámetro | Frecuencia | Valor normal | Alerta |
|-----------|-----------|-------------|--------|
| **Flujo del acceso (Qa)** | Mensual (dilución) | ≥600 mL/min (FAV) | <600 o caída >25% en 4 meses |
| **Presión venosa estática** | Cada sesión | <0.5 × PAM | >0.5 × PAM = estenosis de outflow |
| **Kt/V** | Mensual | ≥1.2 (3×/sem) | <1.2 = subadecuación |
| **Recirculación** | Si Kt/V bajo | <5% | >10% = estenosis severa |
| **Examen físico** | Cada sesión | Frémito palpable, soplo continuo | Frémito débil/pulsátil = estenosis |
        """)

        st.markdown("#### Complicaciones y manejo")
        comp_acc = st.selectbox("Complicación", [
            "Trombosis de FAV",
            "Estenosis del acceso",
            "Infección del catéter (CRBSI)",
            "Síndrome de robo vascular (steal)",
            "Aneurisma de FAV",
        ], key="comp_acc")

        comps_acc = {
            "Trombosis de FAV": "**Causa:** estenosis no tratada (80%), hipotensión, compresión. **Manejo:** trombolisis farmacológica (rtPA) o trombectomía quirúrgica en <24–48h de inicio. Después de 72h: rescate menos exitoso.",
            "Estenosis del acceso": "**Causa:** hiperplasia neointimal (anastomosis o mid-graft). **Diagnóstico:** eco-Doppler, fistulografía. **Manejo:** angioplastia percutánea (ATP) con stent si recurrencia. Vigilar Qa cada 3 meses.",
            "Infección del catéter (CRBSI)": "**Diagnóstico:** hemocultivos periférico + catéter. **Manejo:** vancomicina empírica IV + sello antibiótico. **Criterio de retiro:** Staphylococcus aureus, hongos, sepsis grave, tunelitis → retirar. Gramnegativos: intentar salvar con sello 14 días.",
            "Síndrome de robo vascular (steal)": "**Manifestación:** dolor isquémico de mano durante y después de HD, palidez/frialdad distal. **Diagnóstico:** eco-Doppler, índice dedo-braquial <0.6. **Manejo:** DRIL (Distal Revascularization Interval Ligation), PAI (Proximalization Arterial Inflow), ligadura si isquemia crítica.",
            "Aneurisma de FAV": "**Indicación de cirugía:** diámetro >3 cm, piel adelgazada/brillante, sangrado previo, dificultad para puncionar, infección. **Manejo conservador:** si asintomático y piel íntegra — vigilar.",
        }
        if comp_acc in comps_acc:
            st.info(comps_acc[comp_acc])

        st.caption("Ref: KDOQI Clinical Practice Guidelines for Vascular Access 2019 | ESVS 2018")

elif nav == "pacientes":
    # Redirigir a expediente clínico digital
    st.session_state["nav_sel"] = "expediente"
    st.rerun()


elif nav == "enfermeria":
    anticoag_enf = st.session_state.get("anticoagulacion_tipo", "HNF")
    st.subheader(f"👩‍⚕️ Protocolo de Enfermería — TRRC con {'HNF' if anticoag_enf == 'HNF' else 'Citrato RCA'}")
    st.caption("Guía adaptativa según anticoagulación seleccionada en el módulo de Prescripción.")

    if anticoag_enf not in ("HNF", "RCA"):
        st.info("Ve al módulo 🩺 Prescripción → selecciona la anticoagulación para ver el protocolo correspondiente.")
    else:
        enf_sec = st.radio("Sección",
            ["✅ Pre-inicio", "⏱️ Durante la sesión", "🚨 Alertas inmediatas", "🏁 Fin de sesión"],
            horizontal=True, key="enf_sec")

        if enf_sec == "✅ Pre-inicio":
            st.markdown("### ✅ Checklist de pre-inicio")
            if anticoag_enf == "HNF":
                st.markdown("""
| ☐ | Verificación |
|---|-------------|
| ☐ | **Catéter:** aspirar y refluir ambos lúmenes. Flujo mínimo ≥150 mL/min |
| ☐ | **HNF preparada:** concentración y tasa programadas según prescripción médica |
| ☐ | **Flujos confirmados** con el médico tratante: Qb, Qe, UF, Qr_pre, Qr_post |
| ☐ | **Circuito purgado** correctamente, sin burbujas visibles |
| ☐ | **Bolsas de reemplazo** disponibles (pedir a farmacia según cálculo) |
| ☐ | **Alarmas de la máquina** verificadas y dentro de rango |
| ☐ | **Signos vitales basales** documentados (PA, FC, T°, SpO₂) |
| ☐ | **Hora de inicio** registrada en hoja de TRRC |
                """)
            else:
                st.error("⚠️ **REGLA ABSOLUTA:** El calcio SIEMPRE por línea post-filtro SISTÉMICA. "
                         "El citrato SIEMPRE por línea pre-filtro. NUNCA en la misma línea.")
                st.markdown("""
| ☐ | Verificación |
|---|-------------|
| ☐ | **Dos líneas identificadas y etiquetadas:** 🔴 CITRATO (pre-filtro) · 🔵 CALCIO (post-filtro sistémica) |
| ☐ | **Citrato trisódico 4%** preparado a la tasa prescrita |
| ☐ | **Ca-gluconato** aforado preparado a la tasa prescrita |
| ☐ | **Confirmar** que calcio NO está conectado en línea de citrato |
| ☐ | **Flujos confirmados** con médico: Qb, citrato, calcio, Qe, UF |
| ☐ | **Verificar** que no hay insuficiencia hepática severa ni lactato >5 (contraindicaciones) |
| ☐ | **Ca-gluconato IV extra** disponible para bolo de emergencia por hipocalcemia |
| ☐ | **iCa basal** tomado antes de iniciar |
| ☐ | **Primera muestra de iCa** programada a las 2 horas del inicio |
                """)

        elif enf_sec == "⏱️ Durante la sesión":
            st.markdown("### ⏱️ Monitoreo durante la sesión")
            if anticoag_enf == "HNF":
                st.markdown("""
| Frecuencia | Qué monitorear | Objetivo / Acción |
|-----------|---------------|------------------|
| **Cada hora** | Qb, Qe, UF, presiones del circuito, T° del paciente | Registrar en hoja de TRRC |
| **c/ 4–6 h** | aPTT | Meta **45–80 s** — ajustar HNF según nomograma |
| **c/ 12 h** | Plaquetas + TP/INR | Vigilar HIT (↓ plaquetas ≥50% = AVISAR MÉDICO URGENTE) |
| **c/ 6–8 h** | Na, K, HCO₃⁻, Ca, Mg, Fósforo | Ajustar composición de bolsas |
| **c/ 24 h** | Creatinina, BUN, BH | Evaluación de adecuación de TRRC |
| **Cada hora** | Balance de líquidos (entradas/salidas) | Discrepancia >200 mL/h → avisar médico |
| **Continuo** | Presión transmembrana (TMP), presión de acceso/retorno | Alarma sostenida → revisar circuito |
                """)
                st.info("💡 **Truco clínico:** Si el filtro empieza a coagularse, el TMP sube gradualmente antes de que pierda el circuito. Monitorear la tendencia, no solo el valor puntual.")
            else:
                st.markdown("""
| Frecuencia | Qué medir | Meta | Acción si fuera de rango |
|-----------|----------|------|------------------------|
| **c/ 2h (primeras 8h)** | iCa **post-filtro** | **0.25–0.40 mmol/L** | Si >0.40: ↑ citrato 10–20% · Si <0.25: ↓ citrato 10–20% |
| **c/ 4–6 h** | iCa **sistémico** | **1.0–1.2 mmol/L** | Si <1.0: ↑ calcio · Si >1.2: ↓ calcio |
| **c/ 12 h** | Ca total / iCa sistémico **(ratio)** | **<2.5** | Si >2.5: acumulación de citrato → AVISAR MÉDICO |
| **c/ 12 h** | pH / HCO₃⁻ | pH 7.35–7.45 | Alcalosis sin causa = posible acumulación |
| **c/ 6–8 h** | Na, K, Mg, Fósforo | Rangos normales | Ajustar bolsas según indicación |
| **Cada hora** | Balance de líquidos | Según meta del médico | Discrepancia >200 mL/h → avisar |
| **Continuo** | TMP, P acceso, P retorno | Dentro de alarmas | Alarma sostenida → revisar circuito |
                """)
                st.warning("⚠️ Con citrato, el **iCa post-filtro** es el parámetro más importante para la anticoagulación del circuito. El **iCa sistémico** protege al paciente. Son dos sistemas independientes.")

        elif enf_sec == "🚨 Alertas inmediatas":
            st.markdown("### 🚨 Cuándo llamar al médico de inmediato")
            if anticoag_enf == "HNF":
                alertas = [
                    ("🔴 URGENTE", "Plaquetas ↓ ≥50% del basal", "SOSPECHAR HIT. SUSPENDER HNF. Avisar médico. NO reiniciar heparina."),
                    ("🔴 URGENTE", "PAM <65 mmHg durante TRRC", "Reducir UF. Valorar pausar sesión. Avisar médico."),
                    ("🟠 IMPORTANTE", "FF >25%", "Reducir UF o Qr_post. Aumentar Qr_pre. Riesgo de coagulación del filtro."),
                    ("🟠 IMPORTANTE", "aPTT >100 s", "Reducir HNF. Si >120s: pausar 30–60 min. Vigilar sangrado activo."),
                    ("🟠 IMPORTANTE", "aPTT <45 s pese a ajuste", "Verificar acceso vascular. Considerar bolo de HNF."),
                    ("🟡 MONITOREAR", "TMP sostenida en aumento", "Revisar coagulación del circuito. Preparar cambio de filtro."),
                    ("🟡 MONITOREAR", "Pérdida del circuito", "Documentar hora y causa. Preparar nuevo circuito. Avisar médico."),
                ]
            else:
                alertas = [
                    ("🔴 URGENTE", "iCa sistémico <0.9 mmol/L o síntomas de hipocalcemia", "Ca-gluconato bolo IV urgente. AVISAR MÉDICO INMEDIATAMENTE."),
                    ("🔴 URGENTE", "Parestesias periorales, calambres, tetania", "Hipocalcemia sintomática. Ca IV. Si grave: pausar sesión. AVISAR."),
                    ("🟠 IMPORTANTE", "Ca total / iCa ratio >2.5", "Acumulación de citrato. Reducir citrato. Evaluar función hepática. AVISAR."),
                    ("🟠 IMPORTANTE", "iCa post-filtro <0.20 mmol/L", "Anticoagulación excesiva. ↓↓ citrato. Riesgo de hipocalcemia."),
                    ("🟠 IMPORTANTE", "iCa post-filtro >0.50 mmol/L", "Anticoagulación insuficiente. ↑↑ citrato. Riesgo de coagulación del filtro."),
                    ("🟠 IMPORTANTE", "Alcalosis metabólica inexplicable (pH >7.50)", "Posible acumulación de citrato. AVISAR MÉDICO."),
                    ("🟡 MONITOREAR", "FF >25%", "Ajustar flujos. Riesgo de coagulación del filtro."),
                    ("🟡 MONITOREAR", "PAM <65 mmHg", "Reducir UF. Avisar médico antes de continuar."),
                ]

            for nivel, titulo, accion in alertas:
                color_bg = {"🔴 URGENTE": "#FEF2F2", "🟠 IMPORTANTE": "#FFFBEB", "🟡 MONITOREAR": "#F0F9FF"}.get(nivel, "#F8FAFC")
                color_brd = {"🔴 URGENTE": "#DC2626", "🟠 IMPORTANTE": "#D97706", "🟡 MONITOREAR": "#0EA5E9"}.get(nivel, "#CBD5E1")
                tc = {"🔴 URGENTE": "#7F1D1D", "🟠 IMPORTANTE": "#78350F", "🟡 MONITOREAR": "#0C4A6E"}.get(nivel, "#1E293B")
                st.markdown(f"""
<div style="border-left:4px solid {color_brd};background:{color_bg};
     padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;">
  <b style="color:{tc};-webkit-text-fill-color:{tc};">{nivel} — {titulo}</b><br>
  <span style="font-size:14px;color:{tc};-webkit-text-fill-color:{tc};">{accion}</span>
</div>""", unsafe_allow_html=True)

        else:
            st.markdown("### 🏁 Fin de sesión")
            st.markdown("""
| Paso | Acción |
|------|--------|
| **1** | Registrar hora de fin, volumen total tratado y balance final en hoja de TRRC |
| **2** | Suspender infusiones: HNF (o citrato + calcio simultáneamente si RCA) |
| **3** | Desconectar circuito según protocolo aséptico |
| **4** | Sellar catéter con heparina 1,000 UI/mL (volumen del lumen + 0.1 mL por cada lumen) |
| **5** | Verificar signos vitales post-sesión y documentar |
| **6** | Notificar al médico: tolerancia, balance, incidencias durante la sesión |
| **7** | Registrar en expediente clínico: indicación, parámetros utilizados, resultado |
            """)
            if anticoag_enf == "RCA":
                st.info("💡 Con RCA: suspender citrato Y calcio de forma simultánea para evitar desequilibrio de iCa sistémico.")
            st.success("✅ Este protocolo fue generado automáticamente por RenalPro según la anticoagulación seleccionada. "
                       "Siempre seguir indicaciones específicas del médico tratante.")

elif nav == "trasplante":
    st.subheader("💉 Trasplante Renal — Inmunosupresores")
    st.caption("Protocolos basados en KDIGO Transplant Work Group 2009 (Am J Transplant 9 Suppl 3:S1-155). Siempre ajustar a protocolo institucional vigente.")

    tx_modo = st.radio("Módulo", [
        "🧪 Timoglobulina (ATG-r)",
        "💉 Basiliximab",
        "💊 Tacrolimus",
        "🔵 Micofenolato (MMF/MFS)",
        "🟡 Ciclosporina A",
        "⚙️ Everolimus / Sirolimus",
        "💉 Esteroides",
        "🚨 Protocolo de Rechazo",
        "🔴 Rechazo Humoral (AMR)",
        "⚡ Interacciones Farmacológicas",
    ], horizontal=True, key="tx_modo")

    st.divider()

    # ── TIMOGLOBULINA ──────────────────────────────────────────────────────────
    if "Timoglobulina" in tx_modo:
        st.markdown("### 🧪 Timoglobulina — Globulina Antitimocítica de Conejo (ATG-r)")
        st.info("**Presentación:** Timoglobulina® (Sanofi) — viales de 25 mg. "
                "No aprobada por FDA para inducción (uso off-label). "
                "**FDA aprobada** para rechazo agudo: 1.5 mg/kg/día × 7–14 días.")
        st.caption("Ref: Hardinger KL et al. J Transplant 2010;957549 | "
                   "Brennan DC et al. Am J Transplant 2011;11(11):2279-2287 | "
                   "KDIGO Transplant 2009")

        tg1, tg2 = st.columns(2)
        with tg1:
            tg_indicacion = st.selectbox("Indicación", [
                "Inducción — bajo riesgo inmunológico",
                "Inducción — riesgo estándar",
                "Inducción — alto riesgo (PRA >80%, retrasplante, DSA)",
                "Rechazo celular agudo (Banff IA–IIB)",
                "Rechazo refractario a esteroides",
            ], key="tg_ind")
            tg_peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0, 1.0, key="tg_peso")

        with tg2:
            if "bajo riesgo" in tg_indicacion:
                dosis_ref = 1.5; dias_ref = 2; meta = "3 mg/kg (bajo riesgo)"
            elif "riesgo estándar" in tg_indicacion:
                dosis_ref = 1.5; dias_ref = 3; meta = "4.5 mg/kg (estándar)"
            elif "alto riesgo" in tg_indicacion:
                dosis_ref = 1.5; dias_ref = 4; meta = "6 mg/kg (alto riesgo)"
            else:
                dosis_ref = 1.5; dias_ref = 7; meta = "1.5 mg/kg/día × 7–14 días (rechazo)"

            tg_dosis = st.number_input("Dosis (mg/kg/día)", 1.0, 2.0, dosis_ref, 0.25, key="tg_dosis")
            tg_dias  = st.number_input("Número de días", 1, 14, dias_ref, 1, key="tg_dias")

        dosis_dia_mg = tg_dosis * tg_peso
        dosis_acum   = tg_dosis * tg_dias
        viales_dia   = dosis_dia_mg / 25
        viales_tot   = (dosis_dia_mg * tg_dias) / 25

        dr1, dr2, dr3, dr4 = st.columns(4)
        dr1.metric("Dosis diaria", f"{dosis_dia_mg:.0f} mg ({tg_dosis} mg/kg)")
        dr2.metric("Viales/día (25 mg)", f"{viales_dia:.1f}")
        dr3.metric("Dosis acumulada", f"{dosis_acum:.1f} mg/kg", help=f"Meta: {meta}")
        dr4.metric("Viales totales", f"{viales_tot:.1f}")

        if dosis_acum < 3.0:
            st.warning(f"⚠️ Acumulada {dosis_acum:.1f} mg/kg < 3 mg/kg — puede ser insuficiente.")
        elif dosis_acum > 7.5:
            st.warning(f"⚠️ Acumulada {dosis_acum:.1f} mg/kg > 7.5 mg/kg — mayor riesgo de infecciones y PTLD.")

        st.markdown(f"""
#### Preparación y administración — Ficha técnica Thymoglobulin® (Sanofi/Genzyme)

> 📌 **El vial de Thymoglobulin® contiene 25 mg de polvo liofilizado** (sólido) en vial de vidrio de 10 mL — **NO es un líquido de 50 mL**. El "50 mL" es el volumen de diluyente que se agrega después.

**Paso 1 — Reconstitución (en cada vial):**
- Agregar **5 mL de agua estéril para inyección** al vial con polvo
- Rotar suavemente hasta disolver por completo → concentración: **5 mg/mL**
- Inspeccionar: si persiste materia particulada después de rotar → desechar ese vial
- Usar dentro de **4 horas** tras reconstitución a temperatura ambiente

**Paso 2 — Dilución en bolsa de infusión:**
- Transferir el contenido de los viales necesarios a una bolsa de **SSF 0.9%** o **SG5%**
- Volumen recomendado: **50 mL de diluyente por cada vial de 25 mg** (concentración final 0.5 mg/mL)
- Volumen total: entre 50 y 500 mL según el número de viales
- Invertir la bolsa suavemente 1–2 veces para mezclar — **NO agitar**
- Usar **inmediatamente** (sin conservantes)

**Ejemplo para este paciente ({dosis_dia_mg:.0f} mg = {viales_dia:.1f} viales):**
- Viales necesarios (redondeando): **{int(viales_dia) + (1 if viales_dia % 1 > 0 else 0)} viales**
- Volumen de reconstitución: {int(viales_dia) + (1 if viales_dia % 1 > 0 else 0)} × 5 mL = **{(int(viales_dia) + (1 if viales_dia % 1 > 0 else 0)) * 5} mL de agua estéril**
- Volumen de dilución: {int(viales_dia) + (1 if viales_dia % 1 > 0 else 0)} × 50 mL = **{(int(viales_dia) + (1 if viales_dia % 1 > 0 else 0)) * 50} mL de SSF o SG5%**

| Parámetro | Detalles |
|-----------|---------|
| **Dosis** | **1.5 mg/kg/día** IV |
| **Meta acumulada** | 3 mg/kg (bajo) · **4.5 mg/kg (estándar)** · 6 mg/kg (alto/rechazo) |
| **Inicio** | **Día 0** (intraoperatorio, antes del clampeo) o Día 1 post-Tx |
| **Concentración final** | **0.5 mg/mL** (50 mL SSF por cada vial de 25 mg) |
| **Filtro** | **Filtro de 0.22 μm en línea — OBLIGATORIO** |
| **1ª infusión** | Mínimo **6 horas** |
| **Dosis subsecuentes** | Mínimo **4 horas** |
| **Vía** | Vena de alto flujo — **central preferida** (periférica: agregar heparina + hidrocortisona al SSF para reducir flebitis) |
        """)

        st.warning("""
#### 💉 Premedicación — **1 hora antes de CADA dosis**
| Fármaco | Dosis | Vía | Objetivo |
|---------|-------|-----|---------|
| **Metilprednisolona** | 1 mg/kg IV (o 500 mg fijo) | IV | Reacción infusional + IS |
| **Difenhidramina** | 25–50 mg | IV | Antihistamínico |
| **Paracetamol / Acetaminofén** | 650–1,000 mg | VO | Antipirético |

⚠️ Sin premedicación hay riesgo de **síndrome de liberación de citocinas**: fiebre, escalofríos, hipotensión, taquicardia durante la infusión.
Si ocurre: reducir velocidad de infusión, no detener abruptamente.
        """)



        st.error("""
#### 🛑 CRITERIOS DE PARO — verificar BH antes de CADA dosis
| Parámetro | Reducir 50% | SUSPENDER DEFINITIVAMENTE |
|-----------|------------|--------------------------|
| **Plaquetas** | <80,000 /μL | **<50,000 /μL** |
| **Leucocitos (WBC)** | <2,000 /μL | **<1,000 /μL** |
| **Neutrófilos (ANC)** | — | **<500 /μL** |
| **CD3** (si disponible) | <200 cel/μL | **<50 cel/μL** |

Si se suspende antes de la meta acumulada: evaluar si la depleción linfocitaria es adecuada (CD3) antes de decidir retomar.
        """)

        st.info("""
#### Profilaxis infecciosa obligatoria
| Patógeno | Profilaxis | Duración |
|---------|-----------|---------|
| **CMV** | Valganciclovir 900 mg/día | D+/R-: 6 m · R+: 3 m |
| **PCP** | TMP-SMX 1 tab simple c/24h | ≥6–12 meses |
| **Hongos** | Fluconazol 100 mg/día o Nistatina | 1–3 meses |
| **HSV** | Aciclovir 200 mg c/12h | Si seropositivo |

> ⚠️ No iniciar sin profilaxis CMV asegurada.
        """)

    # ── BASILIXIMAB ────────────────────────────────────────────────────────────
    elif "Basiliximab" in tx_modo:
        st.markdown("### 💉 Basiliximab — Antagonista del Receptor de IL-2 (Anti-CD25)")
        st.info("**Presentación:** Simulect® (Novartis) — viales de 20 mg. "
                "Aprobado para profilaxis de rechazo agudo en trasplante renal. "
                "Alternativa a timoglobulina en bajo-moderado riesgo inmunológico.")
        st.caption("Ref: Nashan B et al. Lancet 1997;350:1193-1198 | "
                   "Vincenti F et al. NEJM 1998;338:161-165 | KDIGO Transplant 2009")

        bl1, bl2 = st.columns(2)
        with bl1:
            bl_peso = st.number_input("Peso del receptor (kg)", 20.0, 150.0, 70.0, 1.0, key="bl_peso")
            bl_riesgo = st.selectbox("Nivel de riesgo inmunológico", [
                "Bajo riesgo (primer Tx, PRA 0%, crossmatch neg)",
                "Riesgo moderado (PRA <50%, 1er Tx)",
                "Alto riesgo (PRA >80%, retrasplante, DSA)",
            ], key="bl_riesgo")
        with bl2:
            st.markdown("**Esquema estándar (dosis fija, independiente del peso):**")
            st.markdown("""
| Dosis | Momento | Vía |
|-------|---------|-----|
| **20 mg** | Día 0 — 2h ANTES del clampeo | IV en 20–30 min |
| **20 mg** | **Día 4** post-trasplante | IV en 20–30 min |
| **Dosis total** | **40 mg** | 2 dosis únicamente |
            """)
            if bl_peso < 35:
                st.warning(f"⚠️ Peso {bl_peso:.0f} kg < 35 kg → "
                           "Usar **10 mg por dosis** (no 20 mg) en pacientes pediátricos.")

        if "Alto riesgo" in bl_riesgo:
            st.error("⚠️ **Riesgo alto — considerar timoglobulina en lugar de basiliximab.**\n\n"
                     "Basiliximab no está recomendado en pacientes altamente sensibilizados "
                     "(PRA >80%, retrasplante con rechazo previo, DSA preformados fuertes). "
                     "La depleción linfocítica de timoglobulina ofrece mayor protección en estos casos.")
        else:
            st.success(f"✅ Basiliximab apropiado para este nivel de riesgo.")

        st.markdown("""
#### Mecanismo de acción
Anticuerpo monoclonal quimérico que bloquea el receptor de IL-2 (CD25) en linfocitos T activados.
Previene la proliferación de células T sin depleción linfocítica — por eso NO causa leucopenia ni trombocitopenia.

#### Ventajas vs Timoglobulina
| Parámetro | Basiliximab | Timoglobulina |
|-----------|------------|--------------|
| **Mecanismo** | Bloqueo IL-2R (no depleta) | Depleción linfocítica |
| **Monitoreo BH** | No necesario | BH antes de cada dosis |
| **Pretratamiento** | No necesario | MP + antihistamínico |
| **Riesgo infeccioso** | Bajo | Moderado-alto |
| **CMV profilaxis** | Solo si R+ o D+/R- | Siempre obligatoria |
| **Costo** | Menor | Mayor |
| **Indicación ideal** | Bajo-moderado riesgo | Alto riesgo / DGF esperado |

#### Dilución y administración
- Reconstituir con 5 mL agua estéril → disolver → diluir en 50 mL SSF 0.9% o SG5%
- Administrar en bolus IV o infusión en 20–30 min
- Compatible con SSF y SG5% — NO mezclar con otros fármacos en la misma línea
- Refrigerar (2–8°C) — no congelar. Usar dentro de 24h tras reconstitución.

#### Cuándo NO usar basiliximab
- PRA >80% o crossmatch positivo
- DSA preformados MFI >3,000
- Retrasplante con pérdida por rechazo agudo
- DCD + KDPI >85% (DGF probable — preferir timoglobulina)
- Riesgo de rechazo hiperagudo
        """)

    # ── RECHAZO HUMORAL (AMR) ──────────────────────────────────────────────────
    elif "Rechazo Humoral" in tx_modo or "AMR" in tx_modo:
        st.markdown("### 🔴 Rechazo Humoral Agudo (AMR) — Protocolo de Tratamiento")
        st.caption("Ref: Lefaucheur C et al. Am J Transplant 2018 | "
                   "Banff 2022 Naesens M et al. Am J Transplant 2024 | "
                   "KDIGO Transplant 2009 Ch.7")

        st.info("""
**AMR (Antibody-Mediated Rejection):** el más grave de los rechazos y el más difícil de tratar.
Causado por DSA que activan el complemento y dañan el endotelio vascular del injerto.
Diagnóstico: Banff 2022 requiere histología + C4d + DSA (no todos necesariamente juntos).
        """)

        amr1, amr2 = st.tabs(["🔬 Diagnóstico y clasificación", "💊 Tratamiento por protocolo"])

        with amr1:
            st.markdown("""
#### Criterios diagnósticos Banff 2022 — AMR activo
Se requieren los **3 componentes:**

**1. Evidencia histológica de daño:**
- Glomerulitis (g ≥1) y/o capilaritis peritubular (ptc ≥1)
- Microangiopatía trombótica (TMA) sin otra causa
- Infarto intimal agudo (rechazo vascular)

**2. Evidencia de interacción Ac-endotelio:**
- C4d ≥1 en tinción IF en capilares peritubulares **O**
- ≥2 transcritos de endotelio en biopsia (molecular Banff)

**3. Evidencia de DSA:**
- DSA positivos (HLA clase I o II) en suero al momento de la biopsia

> 📌 AMR puede ser C4d-negativo — el C4d negativo NO descarta AMR si hay histología + DSA.

#### Clasificación y gravedad
| Tipo | Características | Pronóstico |
|------|----------------|-----------|
| **AMR hiperagudo** | Minutos-horas post-Tx, crossmatch positivo | Muy malo — pérdida casi segura |
| **AMR agudo** | Días-semanas, caída súbita de TFG + DSA | Malo sin tratamiento urgente |
| **AMR crónico activo** | Meses-años, DSA de novo, proteinuria progresiva | Variable — responde menos al tto |
| **Rechazo mixto** | Componente celular + humoral | Tratar ambos simultáneamente |

#### Estudio ante sospecha de AMR
```
1. DSA cuantitativo (SAB Luminex) — urgente
2. Biopsia renal con IF + MO + C4d (urgente, misma día si posible)
3. Eco Doppler renal (perfusión, obstrucción)
4. Complemento C3, C4 (bajo → activación de complemento)
5. Hemograma (TMA: anemia hemolítica + trombocitopenia)
6. Esquistocitos en frotis si TMA sospechada
7. ADAMTS-13 si TTP posible
```
            """)

        with amr2:
            st.markdown("""
#### Protocolo de tratamiento AMR agudo — escalonado

**Paso 1 — Inmediato (iniciar en las primeras 24h):**
""")
            st.error("""
⚠️ AMR es urgencia — NO esperar más de 24–48h para iniciar tratamiento una vez confirmado.
            """)
            st.markdown("""
| Intervención | Dosis | Objetivo |
|-------------|-------|---------|
| **Pulsos de metilprednisolona** | 500 mg IV c/24h × 3 días | Suprimir componente celular |
| **Plasmaféresis (PP)** | 1–1.5 volúmenes plasmáticos · Cada 2 días × 5–7 sesiones | Eliminar DSA circulantes |
| **IVIG post-plasmaféresis** | 100–200 mg/kg IV después de cada sesión de PP | Neutralizar Ac residuales |

**Paso 2 — Biológicos (días 5–14 según respuesta):**
| Intervención | Dosis | Objetivo |
|-------------|-------|---------|
| **Rituximab** | 375 mg/m² IV × 1–4 dosis (cada 1–2 semanas) | Depletar células B productoras de DSA |
| **IVIG dosis alta** | 2 g/kg total (dividido en 2 días) | Si DSA persisten o PP no disponible |

**Paso 3 — AMR refractario (falla a PP + IVIG + Rituximab):**
| Intervención | Dosis | Evidencia |
|-------------|-------|----------|
| **Eculizumab** | 900 mg IV semanal × 4 sem → 1,200 mg c/2 sem | 2D — bloqueo C5, TMA y AMR agudo |
| **Bortezomib** | 1.3 mg/m² SC × 4 dosis (ciclo) | Series de casos — depleta células plasmáticas |
| **Imlifidase (IdeS)** | 0.25 mg/kg IV × 1 dosis | Degrada IgG — úsense en centros especializados |

**Ajuste de inmunosupresión de mantenimiento en AMR:**
- Si en tacrolimus: optimizar niveles C0 a 10–12 ng/mL
- Si en ciclosporina: considerar conversión a tacrolimus
- Agregar o mantener MMF a dosis plena (2 g/día)
- Monitoreo DSA c/2–4 semanas durante tratamiento

**Respuesta al tratamiento — criterios de evaluación:**
```
Semana 2: DSA (reducción MFI >50% = respuesta parcial)
Semana 4: Creatinina (estabilización o mejoría = respuesta)
Semana 6: Biopsia de seguimiento (resolución de g + ptc)

✅ Respuesta completa: DSA negativos + Cr estable + histología mejorada
⚠️ Respuesta parcial: DSA reducidos pero persistentes → continuar PP + rituximab
❌ Sin respuesta: considerar eculizumab + evaluación de retrasplante futuro
```

> 📌 AMR crónico activo: responde menos a tratamiento agresivo.
> Priorizar manejo conservador (RASi, SGLT2i, control BP <130/80) y
> enlistar para retrasplante si hay pérdida progresiva del injerto.
            """)

    # ── INTERACCIONES FARMACOLÓGICAS ───────────────────────────────────────────
    elif "Interacciones" in tx_modo:
        st.markdown("### ⚡ Interacciones Farmacológicas en Trasplante Renal")
        st.caption("Ref: Vanhoof J et al. Transplant Rev 2019 | "
                   "Pea F et al. Clin Pharmacokinet 2007 | "
                   "van Gelder T et al. Transplantation 2018")

        st.info("""
En trasplante, los inhibidores de calcineurina (tacrolimus, ciclosporina) tienen margen terapéutico
estrecho y son metabolizados por **CYP3A4** e transportados por **P-gp**. 
Cualquier inductor o inhibidor de estas enzimas puede causar toxicidad por sobredosis
o rechazo por niveles subterapéuticos.
        """)

        int_tab1, int_tab2, int_tab3 = st.tabs([
            "🔺 Aumentan niveles CNI",
            "🔻 Reducen niveles CNI",
            "⚠️ Combinaciones peligrosas",
        ])

        with int_tab1:
            st.markdown("""
#### Fármacos que AUMENTAN niveles de tacrolimus/ciclosporina
*(Inhiben CYP3A4 o P-gp → menos metabolismo → niveles más altos → toxicidad)*

| Categoría | Fármaco | Magnitud | Acción |
|-----------|---------|---------|--------|
| **Antifúngicos azólicos** | **Voriconazol** | ⭐⭐⭐⭐ Muy alta (×3–5) | Reducir tacrolimus 50–75% antes de iniciar |
| | **Fluconazol** | ⭐⭐⭐ Alta (×2–3) | Reducir tacrolimus 30–50% |
| | Itraconazol | ⭐⭐⭐ Alta | Monitoreo estrecho |
| | Isavuconazol | ⭐⭐ Moderada | Menor que voriconazol — preferible |
| | Posaconazol | ⭐⭐⭐ Alta | Reducir CNI 30–50% |
| **Antivíricos** | Cobicistat (HIV) | ⭐⭐⭐⭐ Muy alta | Evitar si posible |
| | Ritonavir | ⭐⭐⭐⭐ Muy alta | Evitar |
| **Calcioantagonistas** | **Diltiazem** | ⭐⭐⭐ Alta (×1.5–3) | Usado a veces intencionalmente para ahorrar CNI |
| | Verapamilo | ⭐⭐⭐ Alta | Similar a diltiazem |
| | Nicardipino | ⭐⭐ Moderada | |
| | Amlodipino | ⭐ Leve | Seguro, preferible |
| **Antibióticos** | Claritromicina | ⭐⭐⭐ Alta | Usar azitromicina como alternativa |
| | Eritromicina | ⭐⭐⭐ Alta | Evitar |
| **Antiarrítmicos** | Amiodarona | ⭐⭐ Moderada | Monitoreo estrecho |
| **Otros** | Jugo de toronja (pomelo) | ⭐⭐ Moderada | Prohibir en dieta del trasplantado |
| | Zumo de naranja amarga | ⭐ Leve | Evitar en exceso |

> 📌 **Regla práctica Voriconazol + Tacrolimus:**
> Al iniciar voriconazol → reducir tacrolimus 50–75% de la dosis actual.
> Monitorear nivel C0 a las 24h y a las 72h.
> Al suspender voriconazol → retomar dosis original gradualmente con monitoreo.
            """)

        with int_tab2:
            st.markdown("""
#### Fármacos que REDUCEN niveles de tacrolimus/ciclosporina
*(Inducen CYP3A4 o P-gp → más metabolismo → niveles más bajos → riesgo de rechazo)*

| Categoría | Fármaco | Magnitud | Acción |
|-----------|---------|---------|--------|
| **Antiepilépticos** | **Rifampicina** | ⭐⭐⭐⭐⭐ Extrema (hasta ×20 reducción) | Evitar absolutamente. Si imprescindible, triplicar CNI y monitorear c/24h |
| | Carbamazepina | ⭐⭐⭐⭐ Muy alta | Usar alternativa (levetiracetam, gabapentina) |
| | Fenitoína | ⭐⭐⭐⭐ Muy alta | Usar alternativa |
| | Fenobarbital | ⭐⭐⭐⭐ Muy alta | Usar alternativa |
| | Oxcarbazepina | ⭐⭐⭐ Alta | Evitar si posible |
| **Antibióticos** | Rifampicina | ⭐⭐⭐⭐⭐ Extrema | Situación de emergencia — ver nota |
| **Antivirales** | Efavirenz (HIV) | ⭐⭐⭐ Alta | Preferir INSTI (dolutegravir) en VIH |
| | Nevirapina | ⭐⭐⭐ Alta | Evitar |
| **Herbales** | **Hierba de San Juan** (St John's Wort) | ⭐⭐⭐⭐ Muy alta | **Prohibición absoluta** — causa rechazos documentados |
| **Antifúngicos** | Caspofungina | ⭐⭐ Moderada | Monitoreo extra |

> ⚠️ **Rifampicina + CNI:** Combinación peligrosa. Si es imprescindible (TBC activa):
> - Aumentar dosis de tacrolimus hasta 3× la dosis habitual
> - Monitoreo de niveles C0 cada 24–48h las primeras 2 semanas
> - Considerar alternativa: bedaquilina, linezolid (con monitoreo)
> - Al suspender rifampicina → reducir CNI de inmediato para evitar toxicidad

> ⚠️ **Hierba de San Juan:** Suplemento herbal muy común. Preguntar SIEMPRE en la historia
> farmacológica. Ha causado episodios documentados de rechazo agudo.
            """)

        with int_tab3:
            st.markdown("""
#### Combinaciones especialmente peligrosas en trasplante

| Combinación | Riesgo | Manejo |
|------------|--------|--------|
| **CNI + AINEs** | Nefrotoxicidad sinérgica (vasoconstricción renal) | ❌ Prohibir AINEs. Usar paracetamol para dolor |
| **CNI + Aminoglucósidos** | Nefrotoxicidad aditiva | Evitar. Si imprescindible: monitoreo Cr c/24h + nivel CNI |
| **Tacrolimus + QT prolongers** | Arritmias (torsades) | Monitoreo ECG con azitromicina, haloperidol, ondansetrón |
| **MMF + Azatioprina** | Mielosupresión severa | Nunca combinar |
| **mTOR + CNI plena** | Nefrotoxicidad grave | Si combinar: reducir CNI 50% |
| **mTOR + heridas** | Retraso de cicatrización | Evitar everolimus/sirolimus en primeros 3 meses post-Tx |
| **Cotrimoxazol + MMF** | Leucopenia aditiva | Monitoreo BH mensual |
| **Cotrimoxazol + CNI** | Aumento de creatinina (bloquea secreción tubular) | No es nefrotoxicidad real — Cr sube sin caída de TFG |

#### Fármacos SEGUROS (sin interacción significativa con CNI)
- Antihipertensivos: **amlodipino**, nifedipino, felodipino (los dihidropiridínicos son seguros)
- Antibióticos: azitromicina (preferir sobre claritromicina), ampicilina, cefalosporinas, carbapenems
- Analgésicos: **paracetamol** (de elección), tramadol (con precaución)
- Antiácidos: **omeprazol** (preferido), pantoprazol
- Hipoglucemiantes: insulina, metformina (reducir si TFG <45)
- Antidepresivos: **sertralina** (preferida), escitalopram

#### Calculadora de ajuste empírico de tacrolimus
            """)
            ia1, ia2, ia3 = st.columns(3)
            with ia1:
                tac_nivel_act = st.number_input("Nivel actual C0 tacrolimus (ng/mL)", 0.0, 30.0, 8.0, 0.5, key="ia_niv")
                tac_dosis_act = st.number_input("Dosis actual (mg c/12h)", 0.0, 15.0, 2.0, 0.5, key="ia_dos")
            with ia2:
                tac_meta    = st.number_input("Nivel meta C0 (ng/mL)", 3.0, 20.0, 10.0, 0.5, key="ia_meta")
                interaccion = st.selectbox("Fármaco a agregar/suspender", [
                    "Ninguna interacción",
                    "Agregar Voriconazol (-75% dosis empírica)",
                    "Agregar Fluconazol (-50% dosis empírica)",
                    "Agregar Diltiazem (-30% dosis empírica)",
                    "Agregar Isavuconazol (-30% dosis empírica)",
                    "Suspender Voriconazol (+200% dosis empírica)",
                    "Suspender Fluconazol (+100% dosis empírica)",
                    "Agregar Rifampicina (+200% dosis empírica)",
                    "Suspender Rifampicina (-66% dosis empírica)",
                ], key="ia_inter")
            with ia3:
                # Calculate adjusted dose
                if tac_nivel_act > 0:
                    factor_meta = tac_meta / tac_nivel_act
                else:
                    factor_meta = 1.0

                ajustes = {
                    "Ninguna interacción": 1.0,
                    "Agregar Voriconazol (-75% dosis empírica)": 0.25,
                    "Agregar Fluconazol (-50% dosis empírica)": 0.50,
                    "Agregar Diltiazem (-30% dosis empírica)": 0.70,
                    "Agregar Isavuconazol (-30% dosis empírica)": 0.70,
                    "Suspender Voriconazol (+200% dosis empírica)": 3.00,
                    "Suspender Fluconazol (+100% dosis empírica)": 2.00,
                    "Agregar Rifampicina (+200% dosis empírica)": 3.00,
                    "Suspender Rifampicina (-66% dosis empírica)": 0.34,
                }
                factor_interac = ajustes.get(interaccion, 1.0)
                dosis_nueva = round(tac_dosis_act * factor_meta * factor_interac * 2) / 2

                st.metric("Dosis sugerida (c/12h)", f"{dosis_nueva:.1f} mg")
                st.caption("⚠️ Empírica — verificar C0 a las 24–48h")

            st.caption("Ref: Vanhoof J et al. Drug interactions with tacrolimus. Transplant Rev 2019. "
                       "Shuker N et al. Drug Metab Rev 2014.")


        st.markdown("### 💊 Tacrolimus — Inhibidor de Calcineurina")
        st.info("**Presentaciones:** Prograf® (IR c/12h) · Advagraf®/Envarsus® (LP c/24h). Metabolismo CYP3A4/P-gp.")

        tc1, tc2 = st.columns(2)
        with tc1:
            tc_peso   = st.number_input("Peso (kg)", 30.0, 150.0, 70.0, 1.0, key="tc_peso")
            tc_fase   = st.selectbox("Fase post-trasplante", [
                "Fase 1: 0–3 meses",
                "Fase 2: 3–12 meses",
                "Fase 3: >12 meses (mantenimiento)",
            ], key="tc_fase")
            tc_riesgo = st.selectbox("Riesgo inmunológico", [
                "Bajo riesgo (0 DSA, crossmatch negativo)",
                "Riesgo estándar",
                "Alto riesgo (PRA alto, retrasplante, rechazo previo)",
            ], key="tc_riesgo")
        with tc2:
            tc_nivel_actual = st.number_input("Nivel C0 actual (ng/mL) — si disponible",
                                              0.0, 30.0, 0.0, 0.5, key="tc_nivel")
            tc_dosis_actual = st.number_input("Dosis actual (mg c/12h)",
                                              0.0, 20.0, 0.0, 0.5, key="tc_dosis_act")

        # Targets según fase y riesgo
        targets = {
            "Fase 1: 0–3 meses": {"Bajo riesgo (0 DSA, crossmatch negativo)": (8,12),
                                    "Riesgo estándar": (10,15),
                                    "Alto riesgo (PRA alto, retrasplante, rechazo previo)": (12,15)},
            "Fase 2: 3–12 meses": {"Bajo riesgo (0 DSA, crossmatch negativo)": (6,10),
                                    "Riesgo estándar": (8,12),
                                    "Alto riesgo (PRA alto, retrasplante, rechazo previo)": (10,12)},
            "Fase 3: >12 meses (mantenimiento)": {"Bajo riesgo (0 DSA, crossmatch negativo)": (4,7),
                                    "Riesgo estándar": (5,8),
                                    "Alto riesgo (PRA alto, retrasplante, rechazo previo)": (6,10)},
        }
        meta_low, meta_high = targets[tc_fase][tc_riesgo]
        dosis_inicio = round(0.1 * tc_peso / 2, 2)  # 0.1 mg/kg/día ÷ 2 (c/12h)

        tm1, tm2, tm3 = st.columns(3)
        tm1.metric("Meta C0", f"{meta_low}–{meta_high} ng/mL")
        tm2.metric("Dosis inicio sugerida", f"{dosis_inicio:.1f} mg c/12h",
                   help="0.1 mg/kg/día dividido c/12h. Ajustar por nivel.")
        if tc_nivel_actual > 0 and tc_dosis_actual > 0:
            if tc_nivel_actual < meta_low:
                ajuste = round(tc_dosis_actual * 1.25, 1)
                tm3.metric("Ajuste sugerido", f"↑ {ajuste} mg c/12h", delta="Nivel bajo")
            elif tc_nivel_actual > meta_high:
                ajuste = round(tc_dosis_actual * 0.75, 1)
                tm3.metric("Ajuste sugerido", f"↓ {ajuste} mg c/12h", delta="Nivel alto")
            else:
                tm3.metric("Nivel en meta ✅", f"{tc_nivel_actual} ng/mL")

        st.markdown("""
#### Interacciones farmacológicas relevantes
| Aumentan niveles (inhibidores CYP3A4) | Disminuyen niveles (inductores CYP3A4) |
|---------------------------------------|---------------------------------------|
| Fluconazol, Voriconazol, Itraconazol | Rifampicina |
| Claritromicina, Eritromicina | Fenitoína, Carbamazepina |
| Diltiazem, Verapamilo, Amlodipino | Rifabutina |
| Omeprazol (leve) | Hierba de San Juan |
| Jugo de toronja | Rifapentina |
        """)
        st.caption("Monitorear niveles C0 (valle, antes de la dosis): diario × 1 semana → semanal × 1 mes → mensual. "
                   "Ref: KDIGO Transplant 2009 | Webster AC, Cochrane 2005")

    # ── MICOFENOLATO ───────────────────────────────────────────────────────────
    elif "Micofenolato" in tx_modo:
        st.markdown("### 🔵 Micofenolato — MMF / Micofenolato de Sodio (MFS)")
        st.info("**MMF (Cellcept®):** 250/500 mg cápsulas · **MFS (Myfortic®):** 180/360 mg tabletas EC. "
                "Equivalencia: MMF 1,000 mg = MFS 720 mg.")

        mf1, mf2 = st.columns(2)
        with mf1:
            mf_tipo = st.selectbox("Formulación", ["MMF (Cellcept®)", "MFS — Micofenolato Sódico (Myfortic®)"], key="mf_tipo")
            mf_peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0, 1.0, key="mf_peso")
            mf_erc  = st.selectbox("Función renal", [
                "Normal / TFG >50", "TFG 25–50", "TFG <25 (sin diálisis)", "En diálisis"], key="mf_erc")
        with mf2:
            mf_indicacion = st.selectbox("Indicación", [
                "Mantenimiento post-trasplante",
                "Rechazo celular agudo — aumentar dosis",
            ], key="mf_ind")

        dosis_std = 1000 if "MMF" in mf_tipo else 720  # mg c/12h estándar
        if "TFG <25" in mf_erc:
            dosis_ajust = dosis_std * 0.75
            nota_erc = "⚠️ Reducir dosis 25% — niveles de MPAG se acumulan"
        elif "diálisis" in mf_erc:
            dosis_ajust = dosis_std * 0.75
            nota_erc = "⚠️ Reducir dosis 25% en peritoneo diálisis. En HD: sin ajuste adicional."
        else:
            dosis_ajust = dosis_std
            nota_erc = "✅ Dosis estándar"

        mfr1, mfr2, mfr3 = st.columns(3)
        mfr1.metric("Dosis estándar", f"{dosis_std} mg c/12h")
        mfr2.metric("Dosis ajustada ERC", f"{dosis_ajust:.0f} mg c/12h")
        mfr3.metric("Dosis diaria total", f"{dosis_ajust*2:.0f} mg/día")
        st.caption(nota_erc)

        st.warning("**Toxicidad principal:** diarrea, náusea, leucopenia · "
                   "Si leucocitos <2,000: reducir 50% o suspender · "
                   "**Teratogénico:** anticoncepción obligatoria en mujeres en edad fértil")
        st.caption("Ref: Sollinger HW. Transplantation 1995;60(3):225–232 | KDIGO Transplant Work Group. Am J Transplant 2009;9 Suppl 3:S1-155")

    # ── CICLOSPORINA ──────────────────────────────────────────────────────────
    elif "Ciclosporina" in tx_modo:
        st.markdown("### 🟡 Ciclosporina A — Inhibidor de Calcineurina")
        st.info("**Presentaciones:** Sandimmun Neoral® (microemulsión) · Genéricos. No intercambiables sin monitoreo de niveles.")

        cs1, cs2 = st.columns(2)
        with cs1:
            cs_peso  = st.number_input("Peso (kg)", 30.0, 150.0, 70.0, 1.0, key="cs_peso")
            cs_fase  = st.selectbox("Fase", ["0–3 meses", "3–12 meses", ">12 meses"], key="cs_fase")
        with cs2:
            cs_c0    = st.number_input("Nivel C0 (ng/mL) — 12h post-dosis", 0.0, 600.0, 0.0, 5.0, key="cs_c0")
            cs_c2    = st.number_input("Nivel C2 (ng/mL) — 2h post-dosis (opcional)", 0.0, 2000.0, 0.0, 50.0, key="cs_c2")

        dosis_inicio = round(8 * cs_peso / 2, 0)
        metas_c0 = {"0–3 meses": (200,300), "3–12 meses": (100,200), ">12 meses": (75,125)}
        metas_c2 = {"0–3 meses": (1000,1500), "3–12 meses": (700,1000), ">12 meses": (500,700)}
        meta_c0  = metas_c0[cs_fase]
        meta_c2  = metas_c2[cs_fase]

        csr1, csr2, csr3 = st.columns(3)
        csr1.metric("Dosis inicio", f"{dosis_inicio:.0f} mg c/12h", help="8 mg/kg/día ÷ 2")
        csr2.metric("Meta C0", f"{meta_c0[0]}–{meta_c0[1]} ng/mL")
        csr3.metric("Meta C2", f"{meta_c2[0]}–{meta_c2[1]} ng/mL")

        st.markdown("""
#### Conversión Ciclosporina → Tacrolimus
Si se decide cambiar por toxicidad o falta de eficacia:
- Suspender ciclosporina
- Iniciar tacrolimus 12h después
- Dosis inicial tacrolimus: 0.05–0.1 mg/kg/día c/12h
- Monitorear nivel C0 tacrolimus a las 72h
        """)
        st.caption("Ref: Vanhove T. Transplantation 2016 | KDIGO Transplant 2009")

    # ── EVEROLIMUS / SIROLIMUS ────────────────────────────────────────────────
    elif "Everolimus" in tx_modo:
        st.markdown("### ⚙️ Everolimus / Sirolimus — mTOR Inhibidores")
        st.warning("⚠️ **No usar en los primeros 30 días post-trasplante** — deteriora la cicatrización. "
                   "Introducir cuando creatinina estable y herida cerrada.")

        ev1, ev2 = st.columns(2)
        with ev1:
            ev_tipo = st.selectbox("Agente", ["Everolimus (Certican®)", "Sirolimus (Rapamune®)"], key="ev_tipo")
            ev_indicacion = st.selectbox("Indicación", [
                "Conversión por nefrotoxicidad de CNI",
                "Rechazo crónico — minimizar CNI",
                "Neoplasia post-trasplante — conversión",
            ], key="ev_ind")
        with ev2:
            ev_nivel = st.number_input("Nivel actual (ng/mL) — si disponible", 0.0, 30.0, 0.0, 0.5, key="ev_niv")

        if "Everolimus" in ev_tipo:
            dosis_inicio = "0.75 mg c/12h (combinado con CNI reducido)"
            meta_nivel = "3–8 ng/mL"
            presentacion = "0.25 / 0.5 / 0.75 / 1.0 mg tabletas"
        else:
            dosis_inicio = "2 mg c/24h (dosis de carga 6 mg día 1)"
            meta_nivel = "5–15 ng/mL (4–12 en combinación con CNI)"
            presentacion = "0.5 / 1 / 2 mg tabletas · Solución 1 mg/mL"

        st.markdown(f"""
| Parámetro | Valor |
|-----------|-------|
| **Dosis inicio** | {dosis_inicio} |
| **Meta de nivel** | {meta_nivel} |
| **Presentación** | {presentacion} |
| **Monitoreo** | Nivel C0 c/1–2 semanas hasta estable, luego mensual |
| **CNI concomitante** | Reducir tacrolimus 50% al iniciar mTOR |
        """)
        st.error("**Contraindicaciones:** herida quirúrgica abierta, proteinuria >500 mg/g, "
                 "neumocistosis (requiere cotrimoxazol), dislipidemia severa no controlada")
        st.caption("Ref: Pascual J. Transplantation 2006 | Budde K. NEJM 2012")

    # ── ESTEROIDES ────────────────────────────────────────────────────────────
    elif "Esteroides" in tx_modo:
        st.markdown("### 💉 Esteroides — Metilprednisolona / Prednisona")

        est_modo = st.radio("Tipo de protocolo",
            ["Inducción (intraoperatorio + post-Qx inmediato)",
             "Mantenimiento (esquema de reducción)",
             "Pulsos para rechazo agudo"], horizontal=True, key="est_modo")

        if "Inducción" in est_modo:
            est_peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0, 1.0, key="est_peso_ind")
            st.markdown(f"""
#### Protocolo de inducción esteroide
| Momento | Dosis | Vía |
|---------|-------|-----|
| Intraoperatorio (clampeo) | **Metilprednisolona 500 mg IV** | IV bolo lento |
| Día 1 post-Qx | **Metilprednisolona 250 mg IV** | IV c/12h |
| Día 2 | **Metilprednisolona 125 mg IV** | IV |
| Día 3 | **Prednisona 60 mg VO** | VO c/24h |
| Día 7–14 | **Prednisona 30 mg VO** | VO c/24h |
| Mes 1–3 | **Prednisona 20 mg VO** | VO c/24h |
| Mes 3–6 | **Prednisona 10 mg VO** | VO c/24h |
| Mes 6–12 | **Prednisona 5–7.5 mg VO** | VO c/24h |
| >12 meses | **Prednisona 5 mg VO** | VO c/24h (mantenimiento) |
            """)

        elif "Mantenimiento" in est_modo:
            est_mes = st.slider("Mes post-trasplante", 1, 60, 6, key="est_mes")
            if est_mes <= 1: dosis_mant = 30; nota = "Reducción activa"
            elif est_mes <= 3: dosis_mant = 20; nota = "Reducción activa"
            elif est_mes <= 6: dosis_mant = 15; nota = "Reducción gradual"
            elif est_mes <= 12: dosis_mant = 10; nota = "Reducción lenta"
            else: dosis_mant = 5; nota = "Mantenimiento a largo plazo"
            st.metric(f"Prednisona VO — mes {est_mes}", f"{dosis_mant} mg/día", nota)
            st.caption("Protocolo orientativo. Ajustar según episodios de rechazo, función renal y efectos secundarios.")

        else:  # Pulsos de rechazo
            est_peso_r = st.number_input("Peso (kg)", 30.0, 150.0, 70.0, 1.0, key="est_peso_r")
            st.markdown("""
#### Pulsos de metilprednisolona para rechazo agudo
| Dosis | Vía | Frecuencia | Duración |
|-------|-----|-----------|---------|
| **Metilprednisolona 500 mg IV** | IV bolo en 30 min | c/24h | 3 días |

**Pretratamiento:** SSF 500 mL previo · Monitor de glucemia c/2h · Calcio · Omeprazol
**Post-pulsos:** Retornar a esquema oral habitual o aumentar prednisona VO 0.5 mg/kg/día
**Si no responde:** biopsia de confirmación + timoglobulina (rechazo celular ≥IB) o IVIG + Rituximab (rechazo humoral)
            """)
        st.caption("Ref: KDIGO Transplant Work Group. Am J Transplant 2009;9 Suppl 3:S1-155 | Kasiske BL et al. Am J Transplant 2010;10(6):1293–1338")

    # ── PROTOCOLO DE RECHAZO ──────────────────────────────────────────────────
    else:
        st.markdown("### 🚨 Protocolo de Rechazo del Injerto")

        rec_tipo = st.selectbox("Tipo de rechazo (Clasificación Banff 2022)", [
            "Rechazo Celular Agudo (ACR) Banff IA — tubulitis moderada",
            "Rechazo Celular Agudo (ACR) Banff IB — tubulitis severa",
            "Rechazo Celular Agudo (ACR) Banff IIA/IIB — arteritis",
            "Rechazo Humoral Agudo (AMR) — DSA + C4d + lesión microvascular",
            "Rechazo Crónico Activo — Banff III / Fibrosis",
            "Rechazo Hiperagudo",
        ], key="rec_tipo")

        protocolos = {
            "Rechazo Celular Agudo (ACR) Banff IA — tubulitis moderada": {
                "primera_linea": "Pulsos de metilprednisolona 500 mg IV × 3 días",
                "segunda_linea": "Timoglobulina 1.5 mg/kg/día × 7–10 días si no responde",
                "ajuste_is": "Optimizar niveles de tacrolimus (C0 10–15 ng/mL fase aguda)",
                "pronostico": "80–90% respuesta a esteroides",
                "seguimiento": "Creatinina diaria × 1 semana · Biopsia de control si no mejora en 5–7 días",
            },
            "Rechazo Celular Agudo (ACR) Banff IB — tubulitis severa": {
                "primera_linea": "Pulsos de metilprednisolona 500 mg IV × 3 días",
                "segunda_linea": "Timoglobulina 1.5 mg/kg/día × 7–14 días (alta probabilidad de necesitar)",
                "ajuste_is": "Optimizar tacrolimus + considerar aumentar MMF",
                "pronostico": "60–80% respuesta",
                "seguimiento": "Biopsia de control a los 14 días · Monitoreo CD3 durante ATG",
            },
            "Rechazo Celular Agudo (ACR) Banff IIA/IIB — arteritis": {
                "primera_linea": "Timoglobulina 1.5 mg/kg/día × 7–14 días (primera línea directa)",
                "segunda_linea": "Plasmaféresis si componente humoral asociado",
                "ajuste_is": "Optimizar tacrolimus agresivamente · Revisar DSA",
                "pronostico": "50–70% respuesta. Mayor riesgo de pérdida del injerto.",
                "seguimiento": "Biopsia de control a los 14–21 días · Nefrología frecuente",
            },
            "Rechazo Humoral Agudo (AMR) — DSA + C4d + lesión microvascular": {
                "primera_linea": "Plasmaféresis (5–7 sesiones, días alternos) + IVIG 2 g/kg (dividido en 2 días)",
                "segunda_linea": "Rituximab 375 mg/m² × 1–4 dosis (si no responde o recurrente)",
                "ajuste_is": "Pulsos de metilprednisolona + optimizar CNI + considerar Eculizumab en casos graves",
                "pronostico": "50–60% respuesta parcial. Alta tasa de pérdida crónica.",
                "seguimiento": "DSA cuantitativo pre/post plasmaféresis · C4d en biopsia de control",
            },
            "Rechazo Crónico Activo — Banff III / Fibrosis": {
                "primera_linea": "Optimizar inmunosupresión base · Conversión a mTOR si CNI nefrotóxico",
                "segunda_linea": "Rituximab si AMR crónico activo con DSA",
                "ajuste_is": "Reducir CNI o convertir a everolimus · Mantener MMF",
                "pronostico": "Progresión lenta. Meta: enlentecer pérdida de función.",
                "seguimiento": "FG cada 3 meses · Proteinuria · Biopsia c/1–2 años",
            },
            "Rechazo Hiperagudo": {
                "primera_linea": "⚠️ Nefrectomía del injerto (no tiene tratamiento efectivo)",
                "segunda_linea": "—",
                "ajuste_is": "Diálisis de urgencia · Trasplante futuro con crossmatch virtual negativo",
                "pronostico": "Pérdida del injerto en horas",
                "seguimiento": "Soporte del paciente · Reiniciar diálisis · Evaluación para retrasplante",
            },
        }

        p = protocolos.get(rec_tipo, {})
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(f"**🔴 Primera línea:**\n{p.get('primera_linea','—')}")
            st.markdown(f"**🟠 Segunda línea / Si no responde:**\n{p.get('segunda_linea','—')}")
            st.markdown(f"**💊 Ajuste de inmunosupresión:**\n{p.get('ajuste_is','—')}")
        with rc2:
            st.info(f"**Pronóstico:** {p.get('pronostico','—')}")
            st.caption(f"**Seguimiento:** {p.get('seguimiento','—')}")

        st.divider()
        st.markdown("#### Algoritmo diagnóstico de disfunción del injerto")
        st.markdown("""
```
Creatinina ↑ post-trasplante
        │
        ├── Primeras 24–72h → Función retardada del injerto (DGF)
        │      → Diálisis temporal, optimizar hidratación, Doppler renal
        │
        ├── 1ª semana → Rechazo hiperagudo / agudo acelerado
        │      → Biopsia urgente + crossmatch
        │
        ├── 1–12 semanas → Rechazo celular agudo
        │      → Biopsia → Clasificación Banff → Protocolo arriba
        │
        ├── >3 meses → AMR / Rechazo crónico / Nefrotoxicidad CNI
        │      → Biopsia + DSA cuantitativo + C4d
        │
        └── Cualquier momento → Descartar causas no inmunes
               → IVU, obstrucción, deshidratación, fármacos nefrotóxicos
```
        """)
        st.caption("Ref: Naesens M et al. (Banff 2022). Am J Transplant 2024;24:338–349 | KDIGO Transplant Work Group. Am J Transplant 2009;9 Suppl 3:S1-155")

elif nav == "glomerulopatias":
    st.subheader("🔵 Glomerulopatías — Diagnóstico y Tratamiento")
    st.caption("Basado en KDIGO 2021 (Kidney Int 2021;100[4S]:S1-S276) · "
               "KDIGO 2025 IgAN/IgAV · KDIGO 2024 ANCA (Kidney Int 2024;105[3S]:S71-S116). "
               "Siempre ajustar a protocolo institucional.")

    gx_sel = st.selectbox("Selecciona la glomerulopatía", [
        "🔵 Enfermedad de Cambios Mínimos (MCD)",
        "🔶 GESF — Glomeruloesclerosis Focal y Segmentaria",
        "🟣 Nefropatía Membranosa (NM / MN)",
        "🟢 Nefropatía por IgA (IgAN) — KDIGO 2025",
        "🔴 Vasculitis ANCA (MPA/GPA) — KDIGO 2024",
        "🟠 Nefritis Lúpica (LN)",
        "⚡ Enfermedad Anti-MBG (Goodpasture)",
        "🌀 MPGN — Algoritmo diagnóstico por patrón de IF",
        "🌀 Glomerulopatía C3 / C3GN / DDD",
    ], key="gx_sel")

    st.divider()

    # ── ENFERMEDAD DE CAMBIOS MÍNIMOS ──────────────────────────────────────────
    if "Cambios Mínimos" in gx_sel:
        st.markdown("### 🔵 Enfermedad de Cambios Mínimos (MCD)")
        st.info("Causa más frecuente de síndrome nefrótico en niños (90%) y en adultos jóvenes (~15–25%). "
                "Biopsia: fusión de podocitos en MEB, sin depósitos en IF ni MO.")

        mcd_tab1, mcd_tab2, mcd_tab3 = st.tabs(["🔬 Diagnóstico", "💊 Tratamiento", "📊 Monitoreo"])

        with mcd_tab1:
            st.markdown("""
#### Criterios diagnósticos KDIGO 2021
- **Síndrome nefrótico:** proteinuria >3.5 g/día (adultos) + hipoalbuminemia + edema
- **Biopsia renal:** fusión difusa de pedicelos en MEB, IF negativa o mínima, MO normal
- **Descartar:** MCD secundaria (AINEs, litio, linfoma Hodgkin, VIH, alergias)

#### Estudio complementario
| Estudio | Objetivo |
|---------|---------|
| Orina 24h o RPCU | Cuantificar proteinuria |
| Albúmina sérica, colesterol, TG | Severidad del síndrome nefrótico |
| Complemento (C3/C4) | Normal en MCD — útil para diagnóstico diferencial |
| Serología: ANA, ANCA, anti-GBM | Descartar glomerulopatías secundarias |
| Biometría hemática | Descartar linfoma Hodgkin en adultos |
| Biopsia renal | Indicada en adultos antes de iniciar tratamiento |
            """)

        with mcd_tab2:
            st.markdown("#### Tratamiento — KDIGO 2021")

            mcd_peso = st.number_input("Peso (kg)", 20.0, 200.0, 70.0, 1.0, key="mcd_peso")
            mcd_escen = st.selectbox("Escenario clínico", [
                "1ª vez (primer episodio)",
                "Recaída frecuente o dependiente de esteroides",
                "Resistente a esteroides (sin remisión en 16 semanas)",
            ], key="mcd_escen")

            pred_dosis = min(1.0 * mcd_peso, 80)
            if "1ª vez" in mcd_escen:
                st.markdown(f"""
**1ª línea: Prednisona**
- Dosis: **{pred_dosis:.0f} mg/día VO** (1 mg/kg/día, máximo 80 mg)
- Duración mínima: **16 semanas** (hasta remisión + 4–8 semanas adicionales)
- Si remisión completa: reducción gradual en 6–12 meses

> 📌 KDIGO 2021: "Sugerimos iniciar prednisona/prednisolona 1 mg/kg/día (máx 80 mg/día) en dosis única matutina." (2D)
                """)
            elif "Recaída" in mcd_escen:
                st.markdown(f"""
**Recaída infrecuente:** repetir prednisona al mismo esquema.

**Recaída frecuente / Dependiente de esteroides — opciones:**
| Agente | Dosis | Evidencia KDIGO 2021 |
|--------|-------|---------------------|
| **Ciclofosfamida VO** | 2–2.5 mg/kg/día × 8–12 semanas | 2B |
| **Tacrolimus** | 0.05–0.1 mg/kg/día c/12h (nivel 5–10 ng/mL) | 2C |
| **Rituximab** | 375 mg/m² × 1–4 dosis | 2C |
| Micofenolato (MMF) | 1–2 g/día | 2D (menos evidencia) |
                """)
            else:
                st.markdown(f"""
**Resistente a esteroides (sin remisión en 16 semanas):**
> 📌 Antes de clasificar como resistente: verificar adherencia y descartar MCD secundaria.

| Agente | Dosis | Evidencia |
|--------|-------|-----------|
| **Tacrolimus** | 0.05–0.1 mg/kg/día c/12h × mín. 6–12 meses | 2C |
| **Ciclosporina** | 4–6 mg/kg/día c/12h | 2C |
| **Ciclofosfamida IV** | 500–1000 mg/m² mensual × 6 meses | 2C |
| **Rituximab** | Considerar si falla CNI | 2D |

> ⚠️ Si persiste resistencia, reconsiderar diagnóstico — ¿es realmente MCD o GESF primaria?
                """)

        with mcd_tab3:
            st.markdown("""
#### Monitoreo — KDIGO 2021
| Frecuencia | Parámetro | Meta |
|-----------|-----------|------|
| Semanal × 4 semanas | Proteinuria (tira reactiva o RPCU) | Remisión: <300 mg/día |
| Mensual | Albúmina, creatinina, presión arterial | Albúmina >3.5 g/dL |
| c/3 meses | BH, glucosa, densidad ósea si esteroides crónicos | Vigilar efectos adversos |
| c/6–12 meses | RPCU en remisión | Confirmar remisión sostenida |

**Definiciones de respuesta:**
- Remisión completa: proteinuria <300 mg/día (o RPCU <0.3)
- Remisión parcial: reducción ≥50% y proteinuria 300–3,500 mg/día
- Recaída: proteinuria ≥3.5 g/día después de remisión
            """)
            st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276.")

    # ── GESF ───────────────────────────────────────────────────────────────────
    elif "GESF" in gx_sel:
        st.markdown("### 🔶 GESF — Glomeruloesclerosis Focal y Segmentaria")
        st.warning("⚠️ Antes de tratar: descartar GESF secundaria (obesidad, reflujo, VIH, anemia falciforme, uso de heroína). "
                   "La GESF secundaria NO se trata con inmunosupresión.")

        gesf_tipo = st.selectbox("Tipo de GESF", [
            "Primaria (idiopática) — síndrome nefrótico clásico",
            "Secundaria — investigar causa subyacente",
            "Genética / familiar",
        ], key="gesf_tipo")

        if "Primaria" in gesf_tipo:
            st.markdown(f"""
#### Tratamiento 1ª línea — KDIGO 2021
**Prednisona:** 1 mg/kg/día (máx 80 mg) × mínimo **16 semanas** antes de clasificar resistencia.

**Si resistente a esteroides:**
| Opción | Dosis KDIGO 2021 |
|--------|-----------------|
| **Tacrolimus (CNI preferido)** | 0.05–0.1 mg/kg/día c/12h (nivel 5–10 ng/mL) × ≥12 meses | 
| Ciclosporina | 3–5 mg/kg/día c/12h × ≥12 meses |
| Ciclofosfamida | Solo con esteroides; menos eficaz que CNI en GESF |

> 📌 KDIGO 2021 sugiere CNI como agente preferido en GESF resistente a esteroides (2B).
> ⚠️ Riesgo de nefrotoxicidad por CNI en uso prolongado: monitorear TFG y niveles.
            """)
        elif "Secundaria" in gesf_tipo:
            st.markdown("""
#### GESF Secundaria — Manejo KDIGO 2021
**NO usar inmunosupresión.** El tratamiento es de la causa subyacente:
| Causa | Manejo |
|-------|--------|
| Obesidad | Pérdida de peso >10% reduce proteinuria significativamente |
| Reflujo nefrovascular | Corrección quirúrgica o médica |
| VIH | TARV + RASi (tenofovir evitar en ERC avanzada) |
| Hiperfiltración por nefrona solitaria | RASi + control estricto de PA |
| Anemia de células falciformes | Hidroxiurea + RASi |

> 📌 RASi: primer pilar en GESF secundaria — reduce proteinuria y progresión.
            """)
        else:
            st.markdown("""
#### GESF Genética — KDIGO 2021
- Sospechar en: inicio en infancia/adolescencia, historia familiar, resistencia a esteroides
- Estudio: panel genético (NPHS1, NPHS2, WT1, TRPC6, INF2, etc.)
- **No responde a inmunosupresión** — manejo de soporte: RASi, control de PA
- Referir a centro especializado en nefropatías genéticas
- Implicaciones para trasplante: riesgo de recurrencia en injerto (GESF primaria >50%; genética <5%)
            """)
        st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276.")

    # ── NEFROPATÍA MEMBRANOSA ──────────────────────────────────────────────────
    elif "Membranosa" in gx_sel:
        st.markdown("### 🟣 Nefropatía Membranosa (NM / MN)")
        st.info("70–80% primaria (anti-PLA2R+). 20–30% secundaria (lupus, neoplasia, VHB, fármacos). "
                "Causa más frecuente de SN en adultos >40 años.")

        nm1, nm2, nm3, nm4 = st.tabs(["🔬 Algoritmo Diagnóstico", "📊 Riesgo & IF", "💊 Tratamiento", "📊 Monitoreo"])

        with nm1:
            st.markdown("#### Algoritmo diagnóstico — Nefropatía Membranosa")
            st.info("""
**KDIGO 2021:** La biopsia ya **no es obligatoria** si el anti-PLA2R es positivo
en un contexto clínico compatible (adulto con SN, sin evidencia de causa secundaria).
Sin embargo, la biopsia aporta valor pronóstico e información sobre el estadio de la lesión.
            """)

            st.markdown("##### Paso 1 — Sospecha clínica")
            st.markdown("""
| Hallazgo | Valor |
|---------|-------|
| Adulto >40 años con SN de inicio gradual | Alta sospecha de NM primaria |
| Proteinuria >3.5 g/día + hipoalbuminemia + edema | Síndrome nefrótico clásico |
| Hematuria microscópica | Presente en 30–50% |
| Función renal | Normal al inicio en la mayoría |
| Complemento C3/C4 | **Normal** en NM primaria — si bajo → sospechar secundaria (LES) |
            """)

            st.markdown("##### Paso 2 — Anti-PLA2R (pivote diagnóstico)")
            nm_pla2r_dx = st.radio("Resultado de Anti-PLA2R sérico:", [
                "✅ Positivo (cualquier título)",
                "❌ Negativo o no disponible",
            ], key="nm_pla2r_dx")

            if "Positivo" in nm_pla2r_dx:
                st.success("""
**Anti-PLA2R+ → NM PRIMARIA probable (70–80% de NM primaria)**

✅ Según KDIGO 2021: **biopsia no obligatoria** si:
- Adulto con SN compatible
- Anti-PLA2R positivo en lab estandarizado
- Sin datos clínicos de causa secundaria (sin lupus, sin malignidad obvia, sin drogas)

Aun así, la biopsia aporta:
- Estadio de la lesión (útil para pronóstico)
- Confirmación en casos dudosos
- Anti-PLA2R en tejido si el sérico es bajo

**Siguiente paso:** Estratificar riesgo → Pestaña "📊 Riesgo & IF"
                """)
                st.markdown("""
**Estudio mínimo aún recomendado:**
- Cuantificar proteinuria (RPCU o 24h)
- Albúmina, creatinina, TFG (CKD-EPI)
- Anti-PLA2R cuantitativo (títulos — sirven para monitoreo)
- Descartar malignidad según edad y factores de riesgo
- Repetir anti-PLA2R a los 3 meses (útil para guiar tratamiento)
                """)
            else:
                st.warning("""
**Anti-PLA2R negativo → Investigar causa secundaria + anticuerpos alternativos**
                """)
                st.markdown("""
##### Paso 2b — Descartar causas secundarias (orden prioritario KDIGO 2021)

**1. Malignidad** (especialmente si >60 años, tabaquismo, pérdida de peso)
| Estudio | Malignidad asociada |
|---------|-------------------|
| TC tórax-abdomen-pelvis | Pulmón, colon, riñón, linfoma |
| PSA (hombre >50 años) | Cáncer de próstata |
| Mamografía (mujer >40) | Cáncer de mama |
| Colonoscopía (>45 años o síntomas) | Colon |
| SPEP + inmunofijación | Linfoma, mieloma |
| Marcadores tumorales (CEA, CA19-9) | Orientativos |

**2. Enfermedad autoinmune**
| Estudio | Diagnóstico |
|---------|------------|
| ANA, anti-dsDNA | LES (NM = clase V) |
| FR, anti-CCP | AR con NM |
| Anti-Ro, anti-La | Sjögren |
| ANCA (MPO, PR3) | Vasculitis (raramente NM) |
| Complemento C3, C4 | Bajo en LES activo |

**3. Fármacos nefrotóxicos** (suspender y reevaluar en 3–6 meses)
- AINEs (ibuprofeno, naproxeno)
- Sales de oro
- Penicilamina
- Mercurio
- Captopril (a altas dosis, antiguo)
- Litio (raramente)
- Nivolumab, pembrolizumab (inmunoterapia oncológica — creciente)

**4. Infección**
| Estudio | Agente |
|---------|--------|
| HBsAg, anti-HBc, DNA VHB | VHB (especialmente en Asia, África) |
| Anti-VHC + PCR RNA | VHC (más raro que en IC-MPGN) |
| VDRL/FTA-ABS | Sífilis |
| Estudio de heces (Schistosoma sp.) | Esquistosomiasis (regiones endémicas) |

**5. Otras causas**
- Sarcoidosis (ECA sérica, Rx tórax)
- Tiroiditis autoinmune (TSH, anti-TPO)
- Diabetes mellitus avanzada (aunque raramente NM pura)
                """)
                st.markdown("""
##### Paso 2c — Anticuerpos alternativos si PLA2R negativo y causa secundaria descartada
| Anticuerpo | % NM primaria | Contexto |
|-----------|--------------|---------|
| **Anti-THSD7A** | 3–5% | A veces asociado a malignidad — descartar |
| **Anti-NELL-1** | ~5% | Asociado a malignidad (especialmente próstata) |
| **Anti-SEMA3B** | <3% | Más frecuente en niños |
| **Anti-EXT1/EXT2** | ~2% | Asociado a LES/enf. autoinmune |
| **Anti-PCDH7** | Raro | En adultos con NM sin otra causa |

> Si todos negativos y secundaria descartada: **NM idiopática seronegativa**
> Biopsia obligatoria para confirmar el diagnóstico.
                """)
                st.markdown("""
##### Algoritmo diagnóstico — árbol de decisión:
```
SN + proteinuria >3.5 g/día en adulto
            │
     Anti-PLA2R sérico
      │             │
   Positivo       Negativo
      │             │
  NM Primaria   ┌──────────────────────────────┐
  probable      │ Descartar secundarias:       │
  (KDIGO 2021:  │ → Malignidad (TC + marcadores)│
  biopsia no   │ → LES (ANA, dsDNA, C3/C4)   │
  obligatoria) │ → Fármacos (historia)        │
               │ → VHB/VHC/sífilis            │
               └──────────┬───────────────────┘
                           │
                    Todos negativos
                           │
               ┌───────────┴──────────────┐
           Anti-THSD7A               Biopsia renal
           Anti-NELL-1            (IF + MO + ME)
               │                       │
            Positivo          IgG subepitelial + spikes
               │              → NM confirmada
          NM Primaria         → Búsqueda adicional si
          seronegativa          IF atípica (IgA, IgM dominante)
```
                """)
                st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276. "
                           "Beck LH et al. NEJM 2009 (anti-PLA2R). Tomas NM et al. NEJM 2014 (anti-THSD7A).")

        with nm2:
            st.markdown("""
#### Diagnóstico KDIGO 2021
- **Biopsia:** engrosamiento de la MBG, depósitos subepiteliales (IF: IgG + C3 granular)
- **Anti-PLA2R:** positivo en 70–80% NM primaria — sensibilidad 96–100%
- **Descartar NM secundaria:** ANA, anti-dsDNA (lupus), VHB, VHC, neoplasia (>65 años: cribado)

#### Estratificación de riesgo KDIGO 2021
            """)
            nm_prot = st.number_input("Proteinuria (g/día)", 0.0, 30.0, 4.0, 0.5, key="nm_prot")
            nm_cr = st.number_input("Creatinina sérica (mg/dL)", 0.3, 10.0, 1.0, 0.1, key="nm_cr")
            nm_pla2r = st.selectbox("Anti-PLA2R", ["Negativo / no disponible", "Positivo bajo (<50 U/mL)", "Positivo alto (≥50 U/mL)"], key="nm_pla2r")

            # Risk stratification KDIGO 2021
            if nm_prot < 4 and nm_cr < 1.5:
                riesgo = "BAJO"
                color_r = "success"
                plan_r = "Observación 6 meses con RASi. No iniciar inmunosupresión de inmediato."
            elif nm_prot >= 8 or nm_cr >= 1.5 or "alto" in nm_pla2r:
                riesgo = "ALTO / MUY ALTO"
                color_r = "error"
                plan_r = "Iniciar tratamiento inmunosupresor. No esperar."
            else:
                riesgo = "MODERADO"
                color_r = "warning"
                plan_r = "Período de observación 6 meses con RASi. Iniciar IS si no mejora."

            getattr(st, color_r)(f"**Riesgo: {riesgo}** — {plan_r}")

        with nm3:
            st.markdown("""
#### Tratamiento por nivel de riesgo — KDIGO 2021
> 📌 **Cambio mayor vs 2012:** Rituximab es ahora tratamiento de primera línea para riesgo moderado y alto.
> La observación de 6 meses sigue siendo válida en riesgo bajo y moderado (remisión espontánea ~30%).

#### 🟢 Riesgo BAJO
- Solo manejo conservador: RASi (IECA/ARA-II) optimizado, control de PA <125/75 mmHg
- **NO iniciar inmunosupresión**
- Reevaluar c/3–6 meses

#### 🟡 Riesgo MODERADO — 3 opciones paralelas válidas (KDIGO 2021):
| Opción | Descripción | Evidencia |
|--------|-------------|-----------|
| **① Observación 6 meses** | Watchful waiting con RASi — remisión espontánea en ~30% | 2C |
| **② Rituximab** | 375 mg/m² × 4 semanas **o** 1g × 2 (día 1 y 15) | 2C |
| **③ CNI monotherapy** | Tacrolimus 0.05–0.1 mg/kg/día o ciclosporina 4–6 mg/kg/día · solo si TFG normal | 2C |

> Si se elige observación y no hay mejoría a los 6 meses → iniciar rituximab o CNI.
> CNI acorta período de proteinuria pero tiene alta tasa de recaída (40–50%) al suspender.

#### 🔴 Riesgo ALTO — iniciar tratamiento activo:
| Opción | Descripción | Evidencia |
|--------|-------------|-----------|
| **① Rituximab (preferido)** | 375 mg/m² × 4 semanas **o** 1g × 2 | 2B |
| **② CNI → + Rituximab** | CNI × 6 meses → agregar rituximab si no hay respuesta (excepto si PLA2R desapareció) | 2C |
| **③ Ciclofosfamida + esteroides** | Esquema Ponticelli alternado × 6 meses | 2B |

#### 🚨 Riesgo MUY ALTO / SN amenazante de vida:
| Opción | Descripción | Evidencia |
|--------|-------------|-----------|
| **① Ciclofosfamida + esteroides** (1ª línea) | Esquema Ponticelli modificado × 6 meses | 1B |
| **② Rituximab** | Alternativa si no tolera o tiene contraindicación a CYC | 2C |

> ⚠️ **¿Por qué CYC y no rituximab en riesgo muy alto?**
> El rituximab tiene un efecto antiproteinúrico lento — puede tardar **6–18 meses** en lograr remisión.
> En SN muy grave (trombosis, AKI superpuesta, infecciones recurrentes, desnutrición severa)
> ese tiempo puede ser fatal. La ciclofosfamida + esteroides reduce la proteinuria en **semanas**,
> lo que marca la diferencia en el pronóstico a corto plazo.
> El rituximab se reserva para quienes no toleran ciclofosfamida (oncológicos, infertilidad, edad >70).

> ⚠️ Si TFG <50 mL/min: reducir dosis de ciclofosfamida a la mitad.
> Consultar centro de referencia si falla rituximab y CYC.

**Esquema Ponticelli modificado:**
- Meses 1, 3, 5: Metilprednisolona 1g IV × 3 días → Prednisona 0.5 mg/kg/día × 27 días
- Meses 2, 4, 6: Ciclofosfamida VO 2.5 mg/kg/día × 30 días
- Dosis acumulada máxima CYC: 36g (preservar fertilidad: máx 10g)
            """)

        with nm4:
            st.markdown("""
#### Monitoreo KDIGO 2021
| Momento | Parámetro | Objetivo |
|---------|-----------|---------|
| c/3 meses | Anti-PLA2R, proteinuria, creatinina | PLA2R cae antes que proteinuria |
| c/6 meses | Proteinuria 24h, albúmina, C3/C4 | Remisión: <0.3 g/día (completa) |
| Anual si estable | Creatinina, TFG, proteinuria | Preservar función renal |

**Definiciones de respuesta:**
- Remisión completa: proteinuria <0.3 g/día + albumina normal
- Remisión parcial: proteinuria <3.5 g/día + reducción ≥50%
- Tiempo para evaluar respuesta: **mínimo 6 meses** (rituximab puede tardar hasta 18m)
            """)
            st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276. "
                       "Rovin BH et al. (MENTOR trial). NEJM 2019.")

    # ── NEFROPATÍA IgA ────────────────────────────────────────────────────────
    elif "IgA" in gx_sel:
        st.markdown("### 🟢 Nefropatía por IgA (IgAN) — KDIGO 2025")
        st.info("Glomerulopatía primaria más frecuente a nivel mundial. "
                "Diagnóstico definitivo por biopsia: depósitos mesangiales de IgA en IF.")

        igan1, igan2, igan3 = st.tabs(["📊 Riesgo KDIGO 2025", "💊 Tratamiento", "📖 Estudio"])

        with igan1:
            st.markdown("#### Calculadora de riesgo de progresión")
            ig1, ig2 = st.columns(2)
            with ig1:
                igan_egfr = st.number_input("TFG estimada (mL/min/1.73m²)", 5.0, 120.0, 60.0, 1.0, key="igan_egfr")
                igan_prot = st.number_input("Proteinuria (g/día)", 0.0, 15.0, 1.0, 0.1, key="igan_prot")
                igan_hta  = st.checkbox("Hipertensión arterial", key="igan_hta")
            with ig2:
                igan_hematuria = st.checkbox("Hematuria macroscópica episódica", key="igan_hem")
                igan_mest = st.multiselect("MEST-C (hallazgos de biopsia disponibles)",
                    ["M1 (hipercelularidad mesangial)", "E1 (hipercelularidad endocapilar)",
                     "S1 (esclerosis segmentaria)", "T1/T2 (atrofia tubular >25%)",
                     "C1/C2 (semilunas)"], key="igan_mest")

            # Risk classification KDIGO 2025
            puntos = 0
            if igan_egfr < 60: puntos += 2
            elif igan_egfr < 90: puntos += 1
            if igan_prot >= 1.0: puntos += 2
            elif igan_prot >= 0.5: puntos += 1
            if igan_hta: puntos += 1
            if any("T1" in m or "T2" in m for m in igan_mest): puntos += 1
            if any("C1" in m or "C2" in m for m in igan_mest): puntos += 1

            if puntos <= 1:
                st.success("🟢 **Riesgo BAJO** — Manejo conservador. RASi optimizado. Seguimiento.")
                riesgo_igan = "bajo"
            elif puntos <= 3:
                st.warning("🟡 **Riesgo MODERADO** — Optimizar RASi. Considerar SGLT2i. Seguimiento estrecho.")
                riesgo_igan = "moderado"
            else:
                st.error("🔴 **Riesgo ALTO** — Tratamiento activo recomendado. RASi + SGLT2i + considerar sparsentan o budesonida.")
                riesgo_igan = "alto"

            st.caption("Clasificación orientativa basada en factores de riesgo KDIGO 2025. "
                       "No reemplaza el juicio clínico completo.")

        with igan2:
            st.markdown("#### Tratamiento por nivel de riesgo — KDIGO 2025")
            st.markdown("""
#### Base para TODOS los pacientes:
- **RASi (IECAs o ARA-II):** optimizar hasta dosis máxima tolerada — meta PA <130/80 mmHg
- **Dieta baja en sodio**, control de peso, no fumar

#### Pacientes en RIESGO de progresión (KDIGO 2025):
| Agente | Recomendación | Evidencia |
|--------|--------------|-----------|
| **SGLT2i** (empagliflozin, dapagliflozin) | Recomendado para riesgo de progresión | 2B |
| **Sparsentan** 400 mg/día VO | SUSTITUYE al RASi (no se combina) | 2B |
| **Budesonida MR (Nefecon®)** 16 mg/día VO × 9 meses | Si proteinuria persistente ≥1 g/día con RASi optimizado | 2B |

> ⚠️ **Sparsentan:** aprobado FDA sept 2024 / EMA abril 2024. Reemplaza al RASi, no se suma.
> No usar sparsentan + SGLT2i + RASi simultáneamente sin supervisión especializada.

#### Glucocorticoides sistémicos (KDIGO 2025):
- Solo si proteinuria persistente ≥1 g/día con RASi + SGLT2i optimizados Y TFG >30
- Considerar riesgo de efectos adversos (infección, diabetes, osteoporosis)
- Ciclo: prednisona 0.5–1 mg/kg/día con reducción gradual en 6 meses

#### IgAN de progresión rápida (crescéntica):
- Ciclofosfamida + glucocorticoides (como vasculitis ANCA — KDIGO 2025)
            """)

        with igan3:
            st.markdown("""
#### Estudio diagnóstico
| Prueba | Objetivo |
|--------|---------|
| Biopsia renal | MEST-C score (diagnóstico definitivo) |
| IgA sérica | Elevada en ~50% — inespecífico |
| Complemento C3/C4 | Normal en IgAN primaria |
| Anti-PLA2R, ANA, ANCA | Diagnóstico diferencial |
| RPCU / proteinuria 24h | Cuantificar y estratificar |

**MEST-C Score:**
M (mesangial) · E (endocapilar) · S (esclerosis) · T (atrofia tubular) · C (semilunas)
Mayor puntuación = mayor riesgo de progresión.
            """)
            st.caption("Ref: KDIGO IgAN/IgAV Work Group. Kidney Int. 2025. "
                       "(Basado en draft público KDIGO 2024 — publicación final 2025). "
                       "PROTECT trial: Heerspink HJL et al. NEJM 2023. "
                       "NefIgArd trial: Barratt J et al. NEJM 2023.")

    # ── VASCULITIS ANCA ────────────────────────────────────────────────────────
    elif "ANCA" in gx_sel:
        st.markdown("### 🔴 Vasculitis ANCA-Asociada (MPA / GPA) — KDIGO 2024")
        st.error("⚠️ **EMERGENCIA NEFROLÓGICA.** No esperar biopsia para iniciar tratamiento si hay deterioro rápido "
                 "y ANCA positivo con clínica compatible.")

        anc1, anc2, anc3 = st.tabs(["🔬 Diagnóstico", "💊 Tratamiento", "🔄 Mantenimiento"])

        with anc1:
            st.markdown("""
#### Diagnóstico KDIGO 2024
| Estudio | Hallazgo |
|---------|---------|
| **ANCA-MPO (p-ANCA)** | MPA — 60–70% |
| **ANCA-PR3 (c-ANCA)** | GPA — 65–75% |
| **Biopsia renal** | GN necrotizante pauci-inmune ± semilunas |
| Creatinina, orina | Sedimento nefrítico, cilindros eritrocitarios |
| Rx/TC tórax | Hemorragia pulmonar, nódulos (GPA) |
| Complemento C3/C4 | Normal (pauci-inmune — sin depósitos) |

> 📌 KDIGO 2024: No retrasar IS por biopsia si clínica + ANCA+ y deterioro rápido.
            """)

        with anc2:
            st.markdown("""
#### Inducción — KDIGO 2024
| Agente | Dosis | Evidencia |
|--------|-------|-----------|
| **Rituximab (1ª línea)** | 375 mg/m² × 4 semanas O 1g × 2 (d1, d15) | 1B |
| **Ciclofosfamida IV** | 15 mg/kg c/2 semanas × 3, luego c/3 semanas × 3–6 | 1B |
| **Glucocorticoides** | Metilprednisolona 1–3 g IV × 3 días → prednisona 1 mg/kg/día (reducción en 5–6 meses) | — |
| **Avacopan** | 30 mg c/12h VO — sustitución parcial o total de GC | 2B |

> 📌 **Avacopan (KDIGO 2024):** inhibidor del receptor C5a. Aprobado FDA/EMA 2021.
> Puede reemplazar glucocorticoides orales en pacientes con alto riesgo de efectos adversos.
> ADVOCATE trial: no inferioridad vs prednisona + superior en remisión sostenida.

**Plasmaféresis (PEXIVAS 2020):**
> ⚠️ KDIGO 2024 ya NO recomienda plasmaféresis de rutina.
> Solo considerar en: hemorragia alveolar severa o Cr >6 mg/dL con posibilidad de recuperación.
            """)

        with anc3:
            st.markdown("""
#### Mantenimiento — KDIGO 2024
| Agente | Dosis | Duración |
|--------|-------|---------|
| **Rituximab (preferido)** | 500 mg IV c/6 meses | Mínimo 18–24 meses |
| Azatioprina | 2 mg/kg/día VO | Hasta 18–24 meses post-remisión |
| Micofenolato | 1–2 g/día | Alternativa a azatioprina |

**Monitoreo de recaída:**
- ANCA persiste positivo o títulos aumentan → mayor riesgo de recaída
- Creatinina + orina c/1–3 meses durante mantenimiento
- No suspender mantenimiento abruptamente
            """)
            st.caption("Ref: KDIGO ANCA Vasculitis Work Group. Kidney Int. 2024;105(3S):S71-S116. "
                       "ADVOCATE trial: Jayne DRW et al. NEJM 2021. "
                       "PEXIVAS trial: Walsh M et al. NEJM 2020.")

    # ── NEFRITIS LÚPICA ────────────────────────────────────────────────────────
    elif "Lúpica" in gx_sel:
        st.markdown("### 🟠 Nefritis Lúpica (LN)")

        ln1, ln2 = st.tabs(["📋 Clasificación ISN/RPS", "💊 Tratamiento por clase"])

        with ln1:
            st.markdown("""
#### Clasificación ISN/RPS 2003 (revisión 2018)
| Clase | Histología | Implicación |
|-------|-----------|-------------|
| **I** | Mesangial mínima | No requiere IS específica |
| **II** | Mesangial proliferativa | Tratar la extra-renal |
| **III** | Focal (<50% glomérulos) | Requiere IS |
| **IV** | Difusa (≥50% glomérulos) | IS agresiva — peor pronóstico |
| **V** | Membranosa | SN — tratamiento según proteinuria |
| **VI** | Esclerosis avanzada (>90%) | Preparar para TRS |

> La clase III y IV pueden coexistir con V (III+V o IV+V).
            """)
            ln_clase = st.selectbox("Clase histológica", ["III", "IV", "III+V", "IV+V", "V", "I-II"], key="ln_clase")

        with ln2:
            tratamientos_ln = {
                "III": {
                    "induccion": "Micofenolato (MMF) 2–3 g/día VO + prednisona 0.5–1 mg/kg/día",
                    "alternativa": "Ciclofosfamida IV bajas dosis (Euro-Lupus) 500 mg c/2 semanas × 6",
                    "mantenimiento": "MMF 1–2 g/día o Azatioprina 2 mg/kg/día",
                    "duracion": "Inducción 6 meses → mantenimiento ≥3 años",
                },
                "IV": {
                    "induccion": "MMF 3 g/día VO + prednisona 1 mg/kg/día (máx 80 mg)\nO ciclofosfamida IV bajas dosis (Euro-Lupus)",
                    "alternativa": "Ciclofosfamida IV altas dosis (NIH) 0.5–1 g/m² mensual × 6",
                    "mantenimiento": "MMF 2 g/día o Azatioprina 2 mg/kg/día",
                    "duracion": "Inducción 6 meses → mantenimiento ≥3 años",
                },
                "V": {
                    "induccion": "Si proteinuria nefrótica: MMF 2–3 g/día ± prednisona\nVoclosporin (donde disponible): 23.7 mg c/12h añadir a MMF",
                    "alternativa": "CNI (tacrolimus) + MMF + prednisona (triple terapia)",
                    "mantenimiento": "MMF 1–2 g/día ± dosis baja de prednisona",
                    "duracion": "≥ 2 años de mantenimiento",
                },
            }
            datos = tratamientos_ln.get(ln_clase.split("+")[0],
                      {"induccion": "Manejo de enfermedad extrarrenal y control de PA",
                       "alternativa": "RASi si proteinuria presente",
                       "mantenimiento": "Sin IS renal específica en clase I/II",
                       "duracion": "Seguimiento cada 3–6 meses"})

            st.markdown(f"""
**Clase {ln_clase} — Tratamiento KDIGO 2021:**

**Inducción:**
{datos['induccion']}

**Alternativa:**
{datos['alternativa']}

**Mantenimiento:**
{datos['mantenimiento']}

**Duración:**
{datos['duracion']}

**Adicional para todos:**
- Hidroxicloroquina 200–400 mg/día (nefroprotector — continuar siempre)
- Belimumab puede añadirse a terapia estándar (BLISS-LN trial — KDIGO 2021)
- RASi si proteinuria >0.5 g/día
- Meta PA: <130/80 mmHg
            """)
            st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276. "
                       "BLISS-LN trial: Furie R et al. NEJM 2020.")

    # ── ANTI-MBG ──────────────────────────────────────────────────────────────
    elif "Anti-MBG" in gx_sel:
        st.markdown("### ⚡ Enfermedad Anti-MBG (Síndrome de Goodpasture)")
        st.error("🚨 **EMERGENCIA NEFROLÓGICA.** Requiere diagnóstico y tratamiento dentro de las primeras horas. "
                 "Riesgo de pérdida irreversible de función renal y hemorragia alveolar fatal.")

        st.markdown("""
#### Diagnóstico
- **Anti-MBG** (anti-colágeno IV α3) sérico — sensibilidad ~95%
- **Biopsia renal:** GN crescéntica con depósitos lineales de IgG en MBF (IF)
- TC tórax: hemorragia alveolar (hasta 40–60% de casos — síndrome pulmón-riñón)
- Descartar: ANCA co-positivo (~30% doble positivos — peor pronóstico)

#### Tratamiento de emergencia — KDIGO 2021
| Componente | Protocolo |
|-----------|---------|
| **Plasmaféresis** | 4L/sesión c/día × 14 días o hasta anti-MBG negativo |
| **Ciclofosfamida VO** | 2–3 mg/kg/día × 3 meses (ajustar por edad y función renal) |
| **Prednisona** | 1 mg/kg/día (máx 60–80 mg) → reducción progresiva en 6 meses |
| **Pulsos MP** | Metilprednisolona 500–1000 mg IV × 3 días si afección pulmonar severa |

> ⚠️ Si creatinina >6 mg/dL al diagnóstico con oligoanuria: probabilidad de recuperación muy baja.
> Continuar tratamiento por posible componente pulmonar — la diálisis no contraindica el tratamiento.

#### Pronóstico
- Cr <6 mg/dL al inicio: ~90% independencia de diálisis
- Cr >6 mg/dL + anuria: ~10% independencia de diálisis
- Hemorragia alveolar masiva: mortalidad 25–50% sin tratamiento urgente
        """)
        st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276.")

    # ── MPGN ALGORITMO DIAGNÓSTICO ────────────────────────────────────────────
    elif "MPGN.*Algoritmo" in gx_sel or "Algoritmo diagnóstico" in gx_sel:
        st.markdown("### 🌀 MPGN — Algoritmo diagnóstico por patrón de inmunofluorescencia")
        st.info("""
**Concepto clave (KDIGO 2021):** MPGN es un **patrón histológico**, no un diagnóstico.
La inmunofluorescencia (IF) es el pivote diagnóstico que orienta todo el estudio subsecuente.
Cada causa requiere tratamiento diferente — nunca tratar empíricamente sin clasificar primero.
        """)
        st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276. "
                   "Appel GB et al. CJASN 2021. Smith RJH et al. Nat Rev Nephrol 2019.")

        mp_tab1, mp_tab2, mp_tab3, mp_tab4 = st.tabs([
            "🔬 Paso 1 — IF biopsia",
            "🧪 Paso 2 — Estudios según IF",
            "🔀 Paso 3 — Diagnóstico diferencial",
            "💊 Paso 4 — Tratamiento por causa",
        ])

        with mp_tab1:
            st.markdown("#### Paso 1 — Resultado de inmunofluorescencia en biopsia")
            st.markdown("""
La IF clasifica el patrón MPGN en 3 grupos con implicaciones diagnósticas y terapéuticas distintas:

| Patrón IF | Depósitos | Diagnóstico orientado | Prevalencia en adultos |
|-----------|-----------|----------------------|----------------------|
| **Inmunocomplejos (IC-MPGN)** | IgG + C3 ± IgM, IgA, C1q | Buscar causa sistémica | 70–80% |
| **C3 dominante (C3G)** | C3 ≥2 cruces sobre cualquier Ig | Desregulación vía alterna | 15–25% |
| **Pauci-inmune / sin depósitos** | Sin depósitos significativos | ANCA, TMA, SHU | <5% |
            """)

            mp_if = st.radio("¿Cuál es el patrón de IF en la biopsia?", [
                "🟡 Inmunocomplejos (IgG + C3 ± IgM, C1q) — Ig dominante",
                "🔵 C3 dominante (C3 ≥2 cruces sobre Ig) — patrón C3G",
                "⬜ Sin depósitos significativos (pauci-inmune)",
                "❓ Pendiente / no disponible",
            ], key="mp_if")

            if "Inmunocomplejos" in mp_if:
                st.warning("""
**Patrón IC-MPGN → Buscar causa subyacente (orden de prioridad KDIGO 2021):**
1. **Infección** (VHC, VHB, endocarditis, HIV, otras bacteriemias crónicas)
2. **Enfermedad autoinmune** (LES, síndrome de Sjögren, artritis reumatoide)
3. **Gammapatía monoclonal** (obligatorio en >50 años — puede enmascararse en IF rutinaria)
4. **Crioglobulinemia** (tipos I, II, III)
5. **Idiopática** — solo si se agotaron todas las anteriores (rara en adultos)

> ⚠️ La GN por IC idiopática es diagnóstico de exclusión en adultos. KDIGO 2021 la considera infrecuente.
                """)
            elif "C3 dominante" in mp_if:
                st.error("""
**Patrón C3G → Desregulación de vía alterna del complemento:**
- Excluir primero: infección activa (puede producir patrón C3G transitorio)
- Si >50 años: excluir gammapatía monoclonal (requiere proteólisis en parafina si IF normal)
- Iniciar estudio de complemento completo → ver Paso 2
                """)
            elif "pauci" in mp_if.lower() or "Sin depósitos" in mp_if:
                st.error("""
**Sin depósitos / pauci-inmune con patrón MPGN:**
- **ANCA** → descartar vasculitis ANCA (MPO, PR3)
- **TMA / SHU** → SHU atípico, TTP (ADAMTS-13), síndrome antifosfolípido
- **Lesión isquémica crónica** → revisar historia vascular
                """)

        with mp_tab2:
            st.markdown("#### Paso 2 — Estudios complementarios según patrón de IF")

            st.markdown("**🟡 Para IC-MPGN (inmunocomplejos):**")
            st.markdown("""
| Estudio | Objetivo | Interpretación |
|---------|---------|---------------|
| **VHC** (anti-VHC + PCR RNA) | Causa más frecuente de IC-MPGN en adultos | Positivo → tratar VHC primero |
| **VHB** (HBsAg, anti-HBc, DNA) | Asociación directa IC-MPGN | Positivo → TARV específico |
| **Hemocultivos seriados** | Endocarditis bacteriana subaguda | Cultivo + ecocardiografía |
| **HIV** | Causa IC-MPGN y GESF | TARV si positivo |
| **ANA, anti-dsDNA, C3, C4** | LES | C3 y C4 bajos en lupus activo |
| **FR, anti-CCP, crioglobulinas** | AR, Sjögren, crioglobulinemia | Crioglobulinas → tipo I/II/III |
| **SPEP + inmunofijación sérica y urinaria** | Gammapatía monoclonal | κ/λ ratio libre, cadenas ligeras |
| **Cadenas ligeras libres séricas** | Mieloma, amiloidosis | Ratio κ/λ anormal |
| **Biopsia de médula ósea** | Si SPEP anormal o >50 años con IC-MPGN | Hematología |
            """)

            st.markdown("**🔵 Para C3G (C3 dominante):**")
            st.markdown("""
| Estudio | Objetivo | Interpretación |
|---------|---------|---------------|
| **C3 sérico** | Vía alterna activa | Bajo en 70–80% de C3G |
| **C4 sérico** | Vía clásica | Normal en C3G pura; bajo en IC-MPGN |
| **CH50** (vía clásica total) | Integridad del complemento | Bajo si hay deficiencias |
| **AP50** (vía alterna) | Activación vía alterna | Bajo o ausente en C3G activa |
| **Factor H, I, B séricos** | Reguladores de vía alterna | Deficiencia → causa de C3G |
| **Anti-C3 nefritogénico (C3NeF)** | Autoanticuerpo contra C3bBb | + en 80% DDD, 40–50% C3GN |
| **Anti-factor H (anti-FH)** | Autoanticuerpo | Tratable con plasmaféresis + IS |
| **SPEP + inmunofijación** | Gammapatía monoclonal que activa C3G | Excluir en >50 años |
| **Panel genético complemento** | FH, FI, FHRs, C3, FB | Indicado si <30 años, historia familiar |
| **Biopsia retiniana / fondo de ojo** | Drusen (C3G crónica) | DDD asociada a lipodistrofia parcial |
            """)

            # Interactive complement interpretation
            st.divider()
            st.markdown("#### 🔢 Interpretación rápida del complemento")
            ci1, ci2, ci3, ci4 = st.columns(4)
            with ci1:
                mp_c3  = st.selectbox("C3 sérico", ["Normal", "Bajo (<85 mg/dL)"], key="mp_c3")
            with ci2:
                mp_c4  = st.selectbox("C4 sérico", ["Normal", "Bajo (<16 mg/dL)"], key="mp_c4")
            with ci3:
                mp_c3nef = st.selectbox("Anti-C3NeF", ["Negativo", "Positivo"], key="mp_c3nef")
            with ci4:
                mp_antifh = st.selectbox("Anti-factor H", ["Negativo", "Positivo"], key="mp_antifh")

            if mp_c3 == "Bajo (<85 mg/dL)" and mp_c4 == "Normal":
                st.success("🔵 **Vía alterna activada** — Compatible con C3G, infección crónica, o déficit de factor H/I")
            elif mp_c3 == "Bajo (<85 mg/dL)" and mp_c4 == "Bajo (<16 mg/dL)":
                st.warning("🟡 **Vías clásica y alterna activadas** — Compatible con IC-MPGN (LES, endocarditis, crioglobulinemia)")
            elif mp_c3 == "Normal" and mp_c4 == "Normal":
                st.info("Complemento normal — No descarta C3G. Puede ser proceso intermitente. Repetir en fase activa.")

            if mp_antifh == "Positivo":
                st.error("⚠️ **Anti-factor H positivo** — C3G mediada por autoanticuerpo. Responde a plasmaféresis + rituximab. Urgente.")
            if mp_c3nef == "Positivo":
                st.warning("⚠️ **C3NeF positivo** — Estabiliza C3bBb → consumo continuo de C3. DDD en 80%. MMF puede ser útil.")

        with mp_tab3:
            st.markdown("#### Paso 3 — Algoritmo diagnóstico integrado")
            st.markdown("""
```
BIOPSIA: Patrón MPGN en microscopía óptica
                │
    ┌───────────┴────────────────────┐
    │                                │
 IF: IgG + C3 ± C1q            IF: C3 dominante
 (Inmunocomplejos)              (≥2 cruces sobre Ig)
    │                                │
    ├── VHC/VHB/HIV ──► +         ┌──┴──────────────────────┐
    │   → Tratar infección         │                          │
    │                           C4 bajo                   C4 normal
    ├── ANA/dsDNA ──► +            │                          │
    │   → Lupus class III/IV     Vía clásica               Vía alterna
    │   (ver módulo LN)          activada                  activada
    │                           (IC-MPGN                 (C3G verdadera)
    ├── Crioglobulinas ──► +      enmascarado                  │
    │   → Crioglobulinemia         como C3G)              ┌───┴─────────────┐
    │                                  │                  │                 │
    ├── SPEP/κλ ──► +             Excluir            Anti-FH +        Anti-FH -
    │   → Gammapatía monoclonal   gammapatía          Plasmaféresis    Anti-C3NeF?
    │   → Hematología                                 + Rituximab      Panel genético
    │
    └── Todo negativo
        → IC-MPGN IDIOPÁTICA
          (Rara en adultos — diagnóstico de exclusión)
          MMF ± prednisona baja dosis
```
            """)

            st.markdown("""
#### Diferencias clave C3GN vs DDD
| Característica | C3GN | DDD (Dense Deposit Disease) |
|----------------|------|-----------------------------|
| IF | C3 mesangial + subendotelial | C3 en lámina densa (intenso) |
| ME | Depósitos subendoteliales | Densificación lamina densa ("sausage") |
| Anti-C3NeF | 40–50% | 80% |
| Lipodistrofia parcial | Raro | 20–30% |
| Drusen retinianos | Raro | Frecuente |
| Pronóstico | Moderado | Peor — 50% ESRD a 10 años |
| Recurrencia post-Tx | 50–70% | >90% |
            """)

        with mp_tab4:
            st.markdown("#### Paso 4 — Tratamiento por diagnóstico etiológico")
            st.markdown("""
#### IC-MPGN — Tratar la causa subyacente:

| Causa | Tratamiento específico |
|-------|----------------------|
| **VHC** | Antivirales de acción directa (DAA) — glefaprevir/pibrentasvir u otros según genotipo |
| **VHB** | Entecavir o tenofovir (evitar TDF si ERC avanzada — usar TAF) |
| **Endocarditis** | Antibióticos según cultivo × 6 semanas + reparación valvular si aplica |
| **HIV** | TARV optimizado — NF puede mejorar con supresión viral |
| **Lupus** | Ver módulo Nefritis Lúpica |
| **Crioglobulinemia tipo II/III** | Rituximab 375 mg/m² × 4 sem. Si VHC positivo: DAA + rituximab |
| **Gammapatía monoclonal** | Tratamiento del clon según hematología (quimioterapia, bortezomib, trasplante autólogo) |
| **IC-MPGN idiopática** | MMF 1.5–2 g/día ± prednisona 0.5 mg/kg/día. Evidencia limitada (observacional). |

#### C3G — Tratamiento por mecanismo:

| Mecanismo | Tratamiento |
|-----------|------------|
| **Anti-factor H** | Plasmaféresis × 5–7 sesiones + rituximab 375 mg/m² × 4 sem (urgente) |
| **Anti-C3NeF activo con progresión** | MMF 2 g/día ± prednisona. Respuesta parcial en ~50% |
| **Gammapatía monoclonal** | Tratar el clon → puede mejorar o resolver la C3G |
| **Mutación genética (FH, FI, FB, C3)** | Soporte: RASi, SGLT2i, control PA. No IS. Eculizumab si progresión rápida |
| **Idiopática / anti-C3NeF solo** | MMF ± prednisona. Eculizumab off-label en C3G refractaria grave |

> 📌 **Eculizumab en C3G (KDIGO 2021 — 2D):**
> Evidencia limitada a series de casos. Considerar en: TFG que cae rápido, crescéntica, o
> refractaria a IS convencional. Respuesta variable — mejor en anti-FH que en C3G genética.
>
> 📌 **Soporte universal:** RASi optimizado, control PA <130/80, SGLT2i si proteinuria >0.5 g/día y TFG >20.
            """)
            st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276. "
                       "Appel GB et al. CJASN 2021. Smith RJH et al. Nat Rev Nephrol 2019. "
                       "Rovin BH et al. Kidney Int 2021. (Eculizumab en C3G).")

    # ── GLOMERULOPATÍA C3 / MPGN ──────────────────────────────────────────────
    elif "C3" in gx_sel or "C3GN" in gx_sel or "DDD" in gx_sel:
        st.markdown("### 🌀 Glomerulopatía C3 / C3GN / DDD — Vista detallada")
        st.info("Para el algoritmo diagnóstico completo desde la biopsia, selecciona **'MPGN — Algoritmo diagnóstico'**. "
                "Esta sección muestra la clasificación y manejo específico de C3G confirmada.")

        st.markdown("""
#### Clasificación actualizada
| Entidad | IF | MO | Mecanismo |
|---------|----|----|-----------|
| **C3G — GN C3** | C3 dominante (IF3+) | Patrón MPGN | Desregulación vía alterna |
| **C3G — Enfermedad de depósitos densos (DDD)** | C3 dominante | Densificación de lámina densa | Mutación/anticuerpo factor H |
| **MPGN tipo I (inmunocomplejos)** | IgG + C3 + C1q | Patrón MPGN | Complejos inmunes — buscar causa |

#### Estudio complementario — KDIGO 2021
| Prueba | Objetivo |
|--------|---------|
| Complemento (C3, C4, CH50, AP50) | C3 bajo ± C4 normal → vía alterna |
| Factor H, I, B | Deficiencias del complemento |
| Anti-C3 nefritogénico (anti-C3Nef) | Positivo en DDD 80%, GN C3 40–50% |
| Anticuerpos anti-factor H | Causa tratable con IS |
| Electroforesis proteínas + inmunofijación | Gammapatía monoclonal en adultos |
| Genética del complemento | Si < 30 años o historia familiar |

#### Tratamiento — KDIGO 2021
| Situación | Manejo |
|-----------|--------|
| **Gammapatía monoclonal** (adultos >50a) | Tratar la discrasia de células plasmáticas |
| **Anti-factor H** | Plasmaféresis + IS (rituximab o prednisona) |
| **Deficiencia genética** | Soporte conservador, RASi |
| **Progresión activa** | MMF 2 g/día ± prednisona baja dosis (evidencia limitada) |
| **Eculizumab** | Considerar en C3G con DDD severa o progresión rápida (off-label, evidencia 2D) |

> 📌 No hay ensayos clínicos aleatorizados de alta calidad en C3G. La evidencia es principalmente observacional.
        """)
        st.caption("Ref: KDIGO Glomerular Diseases Work Group. Kidney Int. 2021;100(4S):S1-S276. "
                   "Smith RJH et al. Nat Rev Nephrol. 2019.")

elif nav == "hiperkalemia":
    st.subheader("⚡ Hiperkalemia — Protocolo de Urgencia")
    st.caption("Ref: Mount DB. NEJM 2016 | Kovesdy CP. Kidney Int 2014 | KDIGO AKI 2012")

    hk1, hk2 = st.columns([1,2])
    with hk1:
        hk_k    = st.number_input("K sérico (mEq/L)", 4.0, 10.0, 6.5, 0.1, key="hk_k")
        hk_peso = st.number_input("Peso (kg)", 20.0, 200.0, 70.0, 1.0, key="hk_peso")
        hk_ecg  = st.selectbox("Cambios en ECG", [
            "Sin cambios",
            "Ondas T picudas",
            "PR prolongado / QRS ancho",
            "Patrón sinusoidal / FV inminente",
        ], key="hk_ecg")
        hk_cr   = st.number_input("Creatinina (mg/dL)", 0.5, 20.0, 3.0, 0.1, key="hk_cr")
        hk_diur = st.selectbox("Diuresis", ["Presente (>200 mL/día)", "Oliguria (<200 mL/día)", "Anuria"], key="hk_diur")
    with hk2:
        # Severity
        if hk_k < 5.5:
            st.success(f"**K {hk_k} — Normal / Límite**\nMonitoreo y reducción de K en dieta.")
        elif hk_k < 6.0:
            st.warning(f"**K {hk_k} — Hiperkalemia leve**")
        elif hk_k < 6.5:
            st.error(f"**K {hk_k} — Hiperkalemia moderada**")
        else:
            st.error(f"**K {hk_k} — ⚠️ HIPERKALEMIA SEVERA — Riesgo de muerte súbita**")

        tiene_ecg = hk_ecg != "Sin cambios"
        if tiene_ecg or hk_k >= 6.0:
            st.markdown("---")
            st.markdown("### Protocolo C-BIG-K")

            # C — Calcium
            st.markdown(f"""
**C — Calcio** *(estabilizador de membrana — NO baja el K)*
- **Gluconato de calcio 10%: 10–30 mL IV** en 2–5 min
- Puede repetirse en 5 min si persisten cambios en ECG
- Efecto: inmediato · Duración: 30–60 min
- ⚠️ Si recibe digoxina: infundir lento (30 min) — riesgo de toxicidad digitálica
            """)

            # B — Bicarbonate
            bicarb_amp = round(hk_peso * 1.0 / 50, 1)
            st.markdown(f"""
**B — Bicarbonato** *(solo si acidosis metabólica)*
- NaHCO₃ 8.4%: **50–100 mEq IV** (1–2 ámpulas de 50 mEq)
- Efecto: 15–30 min · Duración: 1–2h
- ⚠️ Poco eficaz sin acidosis. No usar si Na elevado o EAP
            """)

            # I-G — Insulin-Glucose
            ins_ui = 10
            glu_g  = 50
            st.markdown(f"""
**I-G — Insulina + Glucosa** *(desplazamiento intracelular)*
- **Insulina regular: 10 UI IV** en bolo
- **Glucosa 50%: 50 mL IV** (25g) simultánea — o glucosa 10% 250 mL en 15 min
- Efecto: 15–30 min · Duración: 4–6h · Baja K ~0.5–1 mEq/L
- Monitorear glucemia c/30 min × 2h (riesgo de hipoglucemia)
            """)

            # K — Kayexalate / Patiromer / Zirconium
            st.markdown("""
**K — Resinas / Quelantes** *(eliminación real de K — efecto tardío)*
| Agente | Dosis | Inicio |
|--------|-------|--------|
| **Poliestireno sulfonato (Kayexalate)** | 15–60g VO o rectal c/6h | 2–4h |
| **Patiromer** | 8.4g VO c/12h | 7–12h |
| **Ciclosilicato de Zirconio (ZS-9)** | 10g VO c/8h × 3 dosis | 1h |

> Kayexalate más disponible; evitar en íleo u obstrucción.
            """)

            # Diuresis
            if "Presente" in hk_diur:
                furo = min(80, max(40, int(hk_cr * 20)))
                st.markdown(f"""
**+ Furosemida** *(si hay diuresis presente)*
- **{furo} mg IV** — favorece eliminación renal de K
- Aumentar dosis si eGFR reducido (CKD: hasta 160–240 mg)
                """)

            # Dialysis
            st.markdown("""
**Diálisis de emergencia** *(más efectiva — elimina ~50 mEq K/h)*
- Indicada si: K ≥7 con cambios ECG, anuria, fallo renal agudo severo, o sin respuesta a medidas anteriores
- HD emergencia supera a todas las medidas anteriores en velocidad de corrección
            """)

            st.info("""
**Resumen de tiempos:**
| Medida | Inicio | Duración | Efecto |
|--------|--------|---------|--------|
| Calcio IV | <5 min | 30–60 min | Estabiliza membrana |
| Insulina-Glucosa | 15–30 min | 4–6h | Baja K ~1 mEq/L |
| Bicarbonato | 15–30 min | 1–2h | Baja K ~0.5 mEq/L |
| Resinas VO | 2–4h | 6–12h | Elimina K GI |
| Furosemida | 30–60 min | 4–6h | Elimina K renal |
| Hemodiálisis | Inmediato | — | Más eficaz |
            """)

elif nav == "hiponatremia":
    st.subheader("💧 Hiponatremia — Diagnóstico y Corrección")
    st.caption("Ref: Spasovski G et al. Eur J Endocrinol 2014 | Verbalis JG et al. Am J Med 2013 | Hoorn EJ. Kidney Int 2017")

    hn_tab1, hn_tab2, hn_tab3 = st.tabs(["🔬 Algoritmo diagnóstico", "💊 Tratamiento & Corrección", "📋 Criterios SIADH"])

    # ── TAB 1 — DIAGNÓSTICO ────────────────────────────────────────────────────
    with hn_tab1:
        st.markdown("#### Paso 1 — Datos séricos y osmolalidad plasmática")
        p1a, p1b, p1c, p1d = st.columns(4)
        with p1a:
            hn_na   = st.number_input("Na sérico (mEq/L)", 100.0, 145.0, 122.0, 1.0, key="hn_na")
        with p1b:
            hn_glu  = st.number_input("Glucosa (mg/dL)", 50.0, 1000.0, 100.0, 1.0, key="hn_glu")
        with p1c:
            hn_bun  = st.number_input("BUN (mg/dL)", 0.0, 200.0, 15.0, 1.0, key="hn_bun")
        with p1d:
            hn_posm_med = st.number_input("Osm plasmática medida (mOsm/kg) — si disponible",
                                          200.0, 400.0, 0.0, 1.0, key="hn_posm_med")

        posm_calc = 2*hn_na + hn_glu/18 + hn_bun/2.8
        posm_usar = hn_posm_med if hn_posm_med > 200 else posm_calc

        oc1, oc2 = st.columns(2)
        oc1.metric("Osmolalidad plasmática calculada", f"{posm_calc:.1f} mOsm/kg",
                   help="2×Na + Glucosa/18 + BUN/2.8")
        if hn_posm_med > 200:
            oc2.metric("Osmolalidad medida (en uso)", f"{posm_med:.1f} mOsm/kg")

        # Osmolality classification
        if posm_usar < 275:
            st.success(f"**Osm {posm_usar:.1f} — HIPOTÓNICA** → Hiponatremia verdadera. Continúa con el algoritmo ↓")
            tipo_osm = "hipotonica"
        elif posm_usar <= 295:
            st.warning(f"**Osm {posm_usar:.1f} — ISOTÓNICA** → Pseudohiponatremia")
            tipo_osm = "isotonica"
            st.info("**Pseudohiponatremia:** hiperproteinemia severa (mieloma múltiple) o hiperlipidemia severa. "
                    "El Na sérico medido por fotometría de llama es falsamente bajo. "
                    "Confirmar con gasometría (Na directo por electrodo ion-selectivo).")
        else:
            st.error(f"**Osm {posm_usar:.1f} — HIPERTÓNICA** → Hiponatremia translocacional")
            tipo_osm = "hipertonica"
            na_corr_glu = hn_na + 1.6 * (hn_glu - 100) / 100
            st.info(f"**Causa más frecuente: hiperglucemia.** "
                    f"Na corregido por glucosa: **{na_corr_glu:.1f} mEq/L** "
                    f"(Katz: +1.6 mEq/L por cada 100 mg/dL de glucosa sobre 100). "
                    f"Tratar la hiperglucemia — el Na se normalizará.")

        if tipo_osm == "hipotonica":
            st.divider()
            st.markdown("#### Paso 2 — Estudios urinarios")
            st.caption("Muestra de orina spot al momento de la evaluación (idealmente antes de iniciar tratamiento)")
            u1, u2, u3 = st.columns(3)
            with u1:
                hn_osm_u = st.number_input("Osmolalidad urinaria (mOsm/kg)", 50.0, 1200.0, 400.0, 10.0, key="hn_osm_u")
            with u2:
                hn_na_u  = st.number_input("Na urinario (mEq/L)", 0.0, 200.0, 60.0, 1.0, key="hn_na_u")
            with u3:
                hn_k_u   = st.number_input("K urinario (mEq/L) — opcional", 0.0, 200.0, 30.0, 1.0, key="hn_k_u")

            st.divider()
            st.markdown("#### Paso 3 — Estado de volumen (evaluación clínica)")
            hn_vol = st.radio("Estado de volumen estimado", [
                "🔻 Hipovolémico — mucosas secas, taquicardia, piel turgente ↓, PVC baja",
                "⚖️ Euvolémico — sin edema, sin signos de hipovolemia",
                "🔺 Hipervolémico — edema, ascitis, ingurgitación yugular",
            ], key="hn_vol")

            st.divider()
            st.markdown("#### Resultado del algoritmo diagnóstico")

            # Diagnostic algorithm
            if hn_osm_u < 100:
                st.info("""
**Osm urinaria <100 → ADH suprimida → POLIDIPSIA / INTOXICACIÓN HÍDRICA**

Causas:
- Polidipsia psicógena
- Intoxicación por agua (maratón, MDMA, psicosis)
- Dieta té y tostadas ("tea and toast" — ancianos)
- Intoxicación por cerveza (beer potomania)

**Manejo:** restricción hídrica estricta. No reponer sodio — el riñón lo corregirá solo al restringir agua.
                """)

            elif "Hipovolémico" in hn_vol:
                if hn_na_u < 25:
                    st.warning("""
**Hipovolémico + Na_u <25 → PÉRDIDAS EXTRARRENALES de sodio**

Causas: vómito prolongado, diarrea, pérdidas por piel (quemaduras, sudoración extrema), 
secuestro en tercer espacio (pancreatitis, peritonitis)

**Manejo:** SSF 0.9% para reponer volumen → Na sube al corregir la hipovolemia (ADH suprimida).
Monitorear Na c/2h — riesgo de sobrecorrección rápida.
                    """)
                else:
                    st.warning("""
**Hipovolémico + Na_u ≥25 → PÉRDIDAS RENALES de sodio**

Causas: diuréticos (tiazídicos > asa), hipoaldosteronismo, insuficiencia adrenal,
cerebral salt wasting (tras HSA/TCE), tubulopatías (Fanconi, Bartter, Gitelman)

**Manejo:** SSF 0.9%. Considerar fludrocortisona si hipoaldosteronismo.
Descartar insuficiencia adrenal: cortisol matutino + estimulación con ACTH.
                    """)

            elif "Euvolémico" in hn_vol:
                siadh_probable = hn_osm_u > 100 and hn_na_u >= 40
                if siadh_probable:
                    st.error("""
**Euvolémico + Osm_u >100 + Na_u ≥40 → SIADH (más probable)**

Confirmar con criterios completos en la pestaña "📋 Criterios SIADH".

Otras causas a descartar:
- Hipotiroidismo (TSH)
- Insuficiencia adrenal (cortisol, ACTH)
- Fármacos (ISRS, carbamazepina, omeprazol, AINEs, opioides, antipsicóticos)
- Náusea, dolor, cirugía reciente (ADH no osmótica)
                    """)
                else:
                    st.warning("""
**Euvolémico + Osm_u <100 → Considerar polidipsia psicógena o hipotiroidismo severo**

Si Osm_u entre 100–300: puede ser SIADH con dilución o uso previo de diuréticos.
Revisar medicamentos y solicitar TSH, cortisol.
                    """)

            else:  # Hipervolémico
                if hn_na_u < 25:
                    st.error("""
**Hipervolémico + Na_u <25 → IC, Cirrosis o Síndrome Nefrótico**

El riñón retiene sodio ávidamente (SRAA activado, bajo GC o baja presión oncótica).
El agua libre se acumula más que el sodio → dilución → hiponatremia.

**Manejo:** restricción hídrica + restricción de sal (<2g/día) + tratar la causa base.
Diuréticos de asa para reducir sobrecarga. Tolvaptan en IC refractaria (con precaución).
                    """)
                else:
                    st.error("""
**Hipervolémico + Na_u ≥40 → AKI / ERC avanzada**

El riñón no puede excretar Na ni agua adecuadamente.
El edema coexiste con retención de agua libre.

**Manejo:** restricción hídrica + restricción de sal.
Diuréticos de asa IV si diuresis presente. Considerar diálisis si refractario.
                    """)

    # ── TAB 2 — TRATAMIENTO ────────────────────────────────────────────────────
    with hn_tab2:
        st.markdown("#### Datos del paciente")
        tc1, tc2, tc3, tc4 = st.columns(4)
        with tc1:
            hn_na2   = st.number_input("Na actual (mEq/L)", 100.0, 135.0, 122.0, 1.0, key="hn_na2")
        with tc2:
            hn_peso2 = st.number_input("Peso (kg)", 20.0, 200.0, 70.0, 1.0, key="hn_peso2")
        with tc3:
            hn_sexo2 = st.selectbox("Sexo / grupo", ["Hombre adulto", "Mujer adulta",
                                                      "Hombre adulto mayor", "Mujer adulta mayor"], key="hn_sexo2")
        with tc4:
            hn_sint2 = st.selectbox("Síntomas", [
                "Asintomático / leves (náusea leve)",
                "Moderados (náusea, confusión, cefalea)",
                "Severos (convulsiones, coma, paro respiratorio)",
            ], key="hn_sint2")

        # TBW and calculations
        tbw_f = {"Hombre adulto": 0.6, "Mujer adulta": 0.5,
                 "Hombre adulto mayor": 0.5, "Mujer adulta mayor": 0.45}[hn_sexo2]
        tbw = tbw_f * hn_peso2

        na_meta_24 = hn_na2 + 8      # safe max
        na_meta_48 = hn_na2 + 16     # 48h max
        deficit_8  = tbw * 8         # mEq to gain 8 mEq/L in 24h

        # Vol de SSF 0.9% y NaCl 3% necesarios
        # SSF 0.9% tiene 154 mEq/L Na
        # NaCl 3% tiene 513 mEq/L Na
        # Adrogue-Madias: ΔNa = (Na_infundido - Na_sérico) / (TBW + 1)
        delta_ssf_1L = (154 - hn_na2) / (tbw + 1)    # mEq/L por litro de SSF
        delta_3pct_1L = (513 - hn_na2) / (tbw + 1)   # mEq/L por litro de NaCl 3%

        # Volume needed to raise 8 mEq/L
        vol_ssf_8  = round(8 / delta_ssf_1L, 1) if delta_ssf_1L > 0 else 0
        vol_3pct_8 = round(8 / delta_3pct_1L, 1) if delta_3pct_1L > 0 else 0

        rv1, rv2, rv3, rv4 = st.columns(4)
        rv1.metric("Agua corporal total", f"{tbw:.1f} L")
        rv2.metric("Meta segura 24h", f"Na {na_meta_24:.0f} mEq/L (+8)")
        rv3.metric("⚠️ Límite absoluto 24h", "≤12 mEq/L (ODS si crónica)")
        rv4.metric("Meta 48h máxima", f"Na {na_meta_48:.0f} mEq/L (+16)")

        st.warning("⚠️ **Síndrome de desmielinización osmótica (ODS):** irreversible. "
                   "Riesgo si Na corrige >12 mEq en 24h en hiponatremia crónica (>48h de evolución). "
                   "Grupos de mayor riesgo: alcoholismo, desnutrición, hipopotasemia.")

        st.divider()

        if "Severos" in hn_sint2:
            bolo_3pct = round(hn_peso2 * 1.5, 0)
            st.error(f"""
#### 🚨 Síntomas severos — NaCl 3% URGENTE
**Bolo inmediato: {bolo_3pct:.0f} mL de NaCl 3% IV en 10–20 minutos**
Repetir hasta × 3 si persisten los síntomas o Na sube <5 mEq/L

**Meta inicial:** subir Na **5 mEq/L en 1–2h** (resuelve síntomas agudos)
Luego DETENER o reducir la velocidad para no superar +8 mEq/24h total.

**Preparación de NaCl 3%:**
30 mL de ClNa 20% + 70 mL de SSF 0.9% = 100 mL de NaCl 3%
            """)

        st.markdown("#### Cálculo de infusión (Fórmula de Adrogue-Madias)")
        st.markdown(f"""
| Solución | ΔNa por litro | Volumen para +8 mEq/L en 24h |
|----------|---------------|------------------------------|
| **SSF 0.9%** (154 mEq/L) | +{delta_ssf_1L:.2f} mEq/L | **{vol_ssf_8:.1f} L** en 24h → {vol_ssf_8*1000/24:.0f} mL/h |
| **NaCl 3%** (513 mEq/L) | +{delta_3pct_1L:.2f} mEq/L | **{vol_3pct_8*1000:.0f} mL** en 24h → {vol_3pct_8*1000/24:.0f} mL/h |

> ⚠️ Monitorear Na sérico c/2h las primeras 6h, c/4h las siguientes 18h.
> Si Na sube demasiado rápido → agua libre VO o desmopresina 2–4 mcg IV para frenar.
        """)

        st.markdown("#### Tolvaptan (acuarético V2)")
        st.info("""
**Indicación:** SIADH refractaria a restricción hídrica, euvolémico, Na >120 mEq/L
**Dosis:** 15 mg VO c/24h · titular hasta 30–60 mg si necesario
**Contraindicaciones:** uso con CYP3A4 fuertes, hepatopatía severa, hipovolemia, necesidad de corregir rápido
**Precaución:** NO iniciar en hospitalizados sin monitoreo cada 2h primeras 8h — sobrecorrección frecuente
**Duración:** máximo 30 días continuos
        """)

    # ── TAB 3 — SIADH ─────────────────────────────────────────────────────────
    with hn_tab3:
        st.markdown("### 📋 Criterios diagnósticos de SIADH")
        st.caption("Verbalis JG et al. Am J Med 2013 | Schwartz WB et al. Am J Med 1957 (criterios originales)")

        st.markdown("#### Criterios esenciales (todos deben cumplirse)")
        crit = {
            "Osm plasmática <275 mOsm/kg (hiponatremia hipotónica)": False,
            "Osm urinaria >100 mOsm/kg (ADH inadecuadamente activa)": False,
            "Euvolemia clínica (sin signos de hipovolemia ni hipervolemia)": False,
            "Na urinario ≥40 mEq/L con ingesta normal de sal": False,
            "Función tiroidea normal (TSH normal)": False,
            "Función adrenal normal (cortisol normal o estimulación ACTH normal)": False,
            "Sin uso reciente de diuréticos (o >5 vidas medias sin diurético)": False,
        }
        cumplidos = 0
        for i, (criterio, _) in enumerate(crit.items()):
            val = st.checkbox(criterio, key=f"siadh_c{i}")
            if val:
                cumplidos += 1

        if cumplidos == 7:
            st.success("✅ **SIADH confirmado** — todos los criterios cumplidos")
        elif cumplidos >= 5:
            st.warning(f"⚠️ **SIADH probable** — {cumplidos}/7 criterios. Verificar los pendientes.")
        else:
            st.info(f"**{cumplidos}/7 criterios** — Diagnóstico de SIADH no confirmado aún.")

        st.divider()
        st.markdown("#### Causas de SIADH — clasificación")
        st.markdown("""
| Categoría | Causas frecuentes |
|-----------|-------------------|
| **SNC** | HSA, ACV isquémico, TCE, meningitis, encefalitis, psicosis |
| **Pulmonar** | Neumonía, tuberculosis, EPOC exacerbado, ventilación mecánica |
| **Neoplasias** | Cáncer de pulmón (células pequeñas), páncreas, duodeno, SNC |
| **Fármacos** | ISRS, carbamazepina, oxcarbazepina, ciclofosfamida, omeprazol, opioides, MDMA |
| **Postoperatorio** | Dolor, náusea, volumen IV hipotónico excesivo |
| **Idiopática** | Adultos mayores — diagnóstico de exclusión |

#### Diagnóstico diferencial con insuficiencia adrenal
| Criterio | SIADH | Insuf. adrenal |
|----------|-------|----------------|
| Na urinario | ≥40 mEq/L | ≥40 mEq/L |
| Osm urinaria | >100 | >100 |
| K sérico | Normal | ↑ (hiperkalemia) |
| Cortisol matutino | Normal | <18 μg/dL |
| Tratamiento | Restricción hídrica | Hidrocortisona |
        """)
        st.caption("Ref: Verbalis JG et al. Am J Med 2013;126(10 Suppl 1):S1-42. "
                   "Hoorn EJ, Zietse R. J Am Soc Nephrol 2017.")

elif nav == "diureticos":
    st.subheader("💊 Diuréticos — Optimización y Resistencia")
    st.caption("Ref: Mullens W et al. JACC 2020 | ADVOR trial: Mullens W et al. NEJM 2022 | Felker GM. NEJM 2011")

    st.markdown("""
### Bloqueo tubular secuencial
La resistencia diurética ocurre cuando no hay respuesta adecuada de natriuresis pese a dosis correctas.
    """)

    du1, du2 = st.columns([1, 2])
    with du1:
        du_egfr = st.number_input("TFG estimada (mL/min)", 5.0, 120.0, 35.0, 1.0, key="du_egfr")
        du_peso = st.number_input("Peso (kg)", 30.0, 200.0, 80.0, 1.0, key="du_peso")
        du_furo = st.number_input("Furosemida oral actual (mg/día)", 0.0, 1000.0, 80.0, 20.0, key="du_furo")
        du_resp = st.selectbox("Respuesta a furosemida actual", [
            "Buena respuesta (diuresis >1L/día sobre ingesta)",
            "Respuesta parcial (diuresis <1L sobre ingesta)",
            "Sin respuesta (diuresis ≤ ingesta)",
        ], key="du_resp")
        du_hipo = st.checkbox("Hipoalbuminemia (<3 g/dL)", key="du_hipo")

    with du2:
        # Furosemide IV equivalent
        furo_iv = du_furo * 2.5 if "Sin respuesta" in du_resp else du_furo * 2
        if du_egfr < 30:
            furo_iv = max(furo_iv, 160)

        st.markdown("#### Paso 1 — Optimizar furosemida IV")
        fm1, fm2, fm3 = st.columns(3)
        fm1.metric("TFG", f"{du_egfr:.0f} mL/min")
        fm2.metric("Dosis IV equivalente", f"{furo_iv:.0f} mg/dosis")
        fm3.metric("Vía recomendada", "IV > VO si edema severo")

        st.markdown(f"""
| TFG | Dosis furosemida IV sugerida |
|-----|------------------------------|
| >60 | 40–80 mg c/12h |
| 30–60 | 80–160 mg c/12h |
| 15–30 | 160–240 mg c/12h o infusión continua |
| <15 | 240–500 mg/día o infusión continua 10–20 mg/h |

{'⚠️ **Hipoalbuminemia:** la furosemida viaja unida a albúmina. Dosis más altas o albúmina IV previa pueden mejorar respuesta.' if du_hipo else ''}
        """)

        if "Sin respuesta" in du_resp or "parcial" in du_resp:
            st.markdown("#### Paso 2 — Bloqueo tubular secuencial")
            st.markdown("""
Agregar un diurético de segmento diferente al asa:

| Nivel tubular | Agente | Dosis | Nota |
|--------------|--------|-------|------|
| **Túbulo proximal** | **Acetazolamida 500 mg IV** | 1 vez antes de furosemida | ADVOR 2022: superior a placebo en descongestión |
| **TDC / TCD** | **Metolazona 5–10 mg VO** | 30–60 min antes de furosemida | Eficaz incluso con TFG <30 — preferida en ERC |
| | **Clortalidona 25–100 mg VO** | c/24h | Acción larga (24–72h) — mejor que HCT en TFG 15–45 |
| | Hidroclorotiazida 25–50 mg | VO c/12h | Menos eficaz con TFG <30 |
| **Colector** | Espironolactona 25–100 mg | VO c/24h | Útil en cirrosis, IC con hiperaldosteronismo |
| | Amilorida 5–10 mg | VO c/12h | Alternativa sin acción hormonal |

> 📌 **ADVOR trial (NEJM 2022):** acetazolamida 500 mg IV + furosemida IV fue superior a placebo en descongestión en IC descompensada.
> 📌 Clortalidona mantiene eficacia con TFG 15–45 y tiene duración de acción más larga que metolazona — útil en ERC moderada.
            """)

        st.markdown("#### Infusión continua de furosemida")
        st.markdown(f"""
Evidencia del DOSE trial (NEJM 2011): infusión continua = bolos intermitentes en IC, pero más cómodo.

**Esquema:**
- Dosis de carga: {min(int(du_furo), 200):.0f} mg IV en 30 min
- Infusión: **10–20 mg/h** ajustar hasta diuresis meta (3–5 mL/kg/h)
- Meta de diuresis: 200 mL/h o peso –500 a –1000 g/día

**Si no hay respuesta en 6h:** doblar la infusión o agregar metolazona/acetazolamida.
        """)

        st.markdown("#### Causas de resistencia diurética")
        st.info("""
1. **Incumplimiento** de restricción de sodio (<2g/día) y líquidos
2. **Dosis insuficiente** — necesidad de ajuste por ERC
3. **Absorción intestinal reducida** — edema de pared intestinal → preferir IV
4. **Hipoalbuminemia** — furosemida no llega al túbulo
5. **Reabsorción de rebote** — el riñón "recupera" Na entre dosis → usar c/8h vs c/12h
6. **Activación neurohumoral** → añadir espironolactona / sacubitril-valsartán
7. **AINES / contrastes** → revisar medicación concomitante
        """)

elif nav == "contraste":
    st.subheader("🔬 Prevención de AKI por Contraste (CA-AKI)")
    st.caption("Ref: Weisbord SD et al. (PRESERVE trial) NEJM 2018 | Mehran R et al. JACC 2004 | ACR Manual on Contrast Media 2023 | KDIGO AKI 2012")

    st.info("**Terminología actualizada:** CA-AKI (Contrast-Associated AKI) reemplaza 'nefropatía por contraste' (CIN). "
            "El contraste IV tiene menor riesgo de lo antes estimado; el contraste intra-arterial tiene mayor riesgo.")

    ca_tab1, ca_tab2, ca_tab3 = st.tabs(["📊 Riesgo & Estratificación", "💧 Protocolo de prevención", "📋 Mehran Score (post-ICP)"])

    with ca_tab1:
        st.markdown("#### Datos del paciente — TFG automática (CKD-EPI 2021)")
        ca1, ca2, ca3, ca4 = st.columns(4)
        with ca1:
            ca_cr   = st.number_input("Creatinina basal (mg/dL)", 0.3, 15.0, 1.5, 0.1, key="ca_cr")
            ca_edad = st.number_input("Edad (años)", 18, 100, 65, 1, key="ca_edad")
        with ca2:
            ca_sexo = st.selectbox("Sexo biológico", ["Masculino", "Femenino"], key="ca_sexo")
            ca_dm   = st.checkbox("Diabetes mellitus", key="ca_dm")
        with ca3:
            ca_ic   = st.checkbox("Insuficiencia cardíaca", key="ca_ic")
            ca_via  = st.selectbox("Vía del contraste", [
                "Intravenosa (TAC, uro-TC, angio-TC)",
                "Intra-arterial 1ª circulación (coronaria, aortografía)",
                "Intra-arterial 2ª circulación (arteriografía periférica)",
            ], key="ca_via")
        with ca4:
            ca_vol  = st.number_input("Volumen de contraste (mL)", 50.0, 400.0, 100.0, 10.0, key="ca_vol")

        # CKD-EPI 2021 calculation (race-free)
        kappa = 0.7 if ca_sexo == "Femenino" else 0.9
        alpha = -0.241 if ca_sexo == "Femenino" else -0.302
        sexo_f = 1.012 if ca_sexo == "Femenino" else 1.0
        cr_kappa = ca_cr / kappa
        if cr_kappa < 1:
            egfr_ckdepi = 142 * (cr_kappa ** alpha) * (0.9938 ** ca_edad) * sexo_f
        else:
            egfr_ckdepi = 142 * (cr_kappa ** -1.200) * (0.9938 ** ca_edad) * sexo_f

        ratio_vol_egfr = ca_vol / egfr_ckdepi if egfr_ckdepi > 0 else 99

        eg1, eg2, eg3 = st.columns(3)
        eg1.metric("TFG CKD-EPI 2021", f"{egfr_ckdepi:.1f} mL/min/1.73m²")
        eg2.metric("Ratio Volumen/TFG", f"{ratio_vol_egfr:.1f}",
                   delta="⚠️ Alto si >3.7" if ratio_vol_egfr > 3.7 else "✅ Aceptable (<3.7)")
        # ERC stage
        if egfr_ckdepi >= 60:
            eg3.metric("Estadio ERC", "G1–G2 (bajo riesgo basal)")
        elif egfr_ckdepi >= 45:
            eg3.metric("Estadio ERC", "G3a (riesgo moderado)")
        elif egfr_ckdepi >= 30:
            eg3.metric("Estadio ERC", "G3b (riesgo alto)")
        else:
            eg3.metric("Estadio ERC", "G4–G5 (riesgo muy alto)")

        # Risk stratification
        riesgo_pts = 0
        if egfr_ckdepi < 30: riesgo_pts += 3
        elif egfr_ckdepi < 45: riesgo_pts += 2
        elif egfr_ckdepi < 60: riesgo_pts += 1
        if ca_dm: riesgo_pts += 1
        if ca_ic: riesgo_pts += 1
        if "Intra-arterial 1ª" in ca_via: riesgo_pts += 2
        elif "Intra-arterial 2ª" in ca_via: riesgo_pts += 1
        if ratio_vol_egfr > 3.7: riesgo_pts += 1

        if riesgo_pts <= 1:
            st.success("**Riesgo BAJO de CA-AKI** — Hidratación oral suficiente en la mayoría")
        elif riesgo_pts <= 3:
            st.warning("**Riesgo MODERADO de CA-AKI** — Hidratación IV obligatoria")
        else:
            st.error("**Riesgo ALTO de CA-AKI** — Hidratación IV + optimización completa del protocolo")

    with ca_tab2:
        st.markdown("#### Protocolo de prevención según TFG")

        if egfr_ckdepi >= 45:
            st.markdown(f"""
**TFG {egfr_ckdepi:.0f} ≥45 mL/min — Riesgo bajo:**
- Hidratación oral ≥500 mL agua 2h antes del procedimiento
- Hidratación IV no necesaria de rutina (ACR 2023)
- Evitar deshidratación el día del estudio
            """)
        else:
            st.markdown(f"""
**TFG {egfr_ckdepi:.0f} <45 mL/min — Hidratación IV con SSF 0.9%:**
- **Pre-procedimiento:** 1 mL/kg/h × 6–12h antes
- **Post-procedimiento:** 1 mL/kg/h × 6h después
- Procedimiento urgente: 3 mL/kg/h × 1h pre + 1 mL/kg/h × 6h post
            """)

        st.markdown("""
#### Medidas universales
| Medida | Recomendación | Evidencia |
|--------|--------------|-----------|
| **Contraste iso/low-osmolar** | Siempre — evitar alto-osmolar | Fuerte |
| **Minimizar volumen** | Meta ratio Volumen/TFG <3.7 | Fuerte |
| **Suspender metformina** | 48h antes si TFG <60 (acidosis láctica) | Moderada |
| **Suspender AINEs** | 24–48h antes | Moderada |
| **Suspender aminoglucósidos** | Si es posible | Moderada |
| **N-acetilcisteína** | ❌ Sin beneficio — PRESERVE 2018 | No recomendada |
| **Bicarbonato IV** | ❌ No superior a SSF — PRESERVE 2018 | No recomendado |
| **HD post-contraste profiláctica** | ❌ No previene CA-AKI | No recomendada |
        """)

        if egfr_ckdepi < 30:
            st.error(f"""
**TFG {egfr_ckdepi:.0f} <30 mL/min — Consideraciones especiales:**
- Balance riesgo/beneficio antes de usar contraste yodado
- TFG <15 o diálisis: el contraste no empeora la función renal (ya no la tienen) — SE PUEDE usar
- Preferir alternativa sin contraste si la información diagnóstica es equivalente
- Monitoreo de creatinina 24h y 48h post-procedimiento
            """)

        st.markdown("#### Monitoreo post-procedimiento")
        st.markdown("""
- Creatinina a las **24h y 48h** en pacientes con TFG <60 o factores de riesgo
- **Definición CA-AKI:** Cr sube ≥0.3 mg/dL o ≥50% en 48h post-contraste
- Si CA-AKI: suspender nefrotóxicos, hidratación IV, monitoreo estrecho, considerar nefrología
        """)

    with ca_tab3:
        st.markdown("### 📋 Score de Mehran — Riesgo de nefropatía post-ICP")
        st.caption("Mehran R et al. JACC 2004. Desarrollado específicamente para procedimientos coronarios percutáneos.")

        st.markdown("Selecciona los factores de riesgo presentes:")
        m1, m2 = st.columns(2)
        with m1:
            m_hipo  = st.checkbox("Hipotensión (PAS <80 mmHg >1h o soporte inotrópico)", key="m_hipo")   # 5 pts
            m_bcia  = st.checkbox("Balón de contrapulsación intraaórtico (BCIA)", key="m_bcia")             # 5 pts
            m_ic    = st.checkbox("Insuficiencia cardíaca (NYHA III–IV o historia de EAP)", key="m_ic")     # 5 pts
            m_edad  = st.checkbox("Edad >75 años", key="m_edad")                                            # 4 pts
            m_dm    = st.checkbox("Diabetes mellitus", key="m_dm")                                          # 3 pts
        with m2:
            m_cr    = st.number_input("Creatinina basal (mg/dL)", 0.3, 15.0, 1.2, 0.1, key="m_cr")
            m_egfr  = st.number_input("TFG estimada (mL/min/1.73m²)", 5.0, 120.0,
                                      float(egfr_ckdepi), 1.0, key="m_egfr")
            m_hto   = st.number_input("Hematocrito (%)", 20.0, 60.0, 42.0, 1.0, key="m_hto")
            m_sexo2 = st.selectbox("Sexo", ["Masculino", "Femenino"], key="m_sexo2")
            m_vol   = st.number_input("Volumen de contraste (mL)", 50.0, 400.0, 150.0, 10.0, key="m_vol")

        # Mehran score calculation
        score = 0
        if m_hipo: score += 5
        if m_bcia: score += 5
        if m_ic:   score += 5
        if m_edad: score += 4
        if m_dm:   score += 3

        # Hematocrit (anemia)
        umbral_hto = 39 if m_sexo2 == "Masculino" else 36
        if m_hto < umbral_hto:
            score += 3
            hto_flag = f"✅ Hto <{umbral_hto}% → +3 pts (anemia)"
        else:
            hto_flag = f"Hto {m_hto:.0f}% (normal para {m_sexo2.lower()})"

        # Creatinine / eGFR points
        if m_egfr < 20:    score += 6
        elif m_egfr < 40:  score += 4
        elif m_egfr < 60:  score += 2
        # Creatinine >1.5 mg/dL adds 4 pts (independent of eGFR in original Mehran)
        if m_cr > 1.5:     score += 4

        # Contrast volume (per 100 mL)
        vol_pts = int(m_vol / 100)
        score += vol_pts

        # Display score
        st.divider()
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Score de Mehran", str(score))

        if score <= 5:
            sc2.metric("Riesgo CA-AKI", "~7.5%", delta="Bajo")
            sc3.metric("Riesgo diálisis", "~0.04%")
            st.success("Riesgo BAJO — Hidratación estándar")
        elif score <= 10:
            sc2.metric("Riesgo CA-AKI", "~14%", delta="Moderado")
            sc3.metric("Riesgo diálisis", "~0.12%")
            st.warning("Riesgo MODERADO — Hidratación IV obligatoria")
        elif score <= 15:
            sc2.metric("Riesgo CA-AKI", "~26%", delta="Alto")
            sc3.metric("Riesgo diálisis", "~1.09%")
            st.error("Riesgo ALTO — Hidratación IV + minimizar contraste")
        else:
            sc2.metric("Riesgo CA-AKI", "~57%", delta="Muy alto")
            sc3.metric("Riesgo diálisis", "~12.6%")
            st.error("Riesgo MUY ALTO — Considerar alternativa al contraste")

        st.markdown(f"""
**Desglose del score:**
- Hipotensión/soporte inotrópico: {5 if m_hipo else 0} pts
- BCIA: {5 if m_bcia else 0} pts
- IC / NYHA III-IV / EAP: {5 if m_ic else 0} pts
- Edad >75: {4 if m_edad else 0} pts
- Diabetes: {3 if m_dm else 0} pts
- {hto_flag}
- TFG {m_egfr:.0f}: {6 if m_egfr<20 else 4 if m_egfr<40 else 2 if m_egfr<60 else 0} pts
- Cr >{1.5} mg/dL: {4 if m_cr>1.5 else 0} pts
- Volumen contraste ({m_vol:.0f} mL): {vol_pts} pts (1 pt/100 mL)
        """)
        st.caption("Ref: Mehran R et al. A simple risk score for prediction of contrast-induced nephropathy. JACC 2004;44(7):1393-1399.")

elif nav == "expediente":
    # ── BLOQUEO PARA INVITADOS ─────────────────────────────────────────────────
    if _rol() in ("guest", "free", "expirado"):
        st.warning("🔒 **El Expediente Clínico Digital requiere registro.** "
                   "Los datos del invitado no se guardan entre sesiones.")
        st.info("Regístrate gratis — 7 días de acceso completo sin tarjeta de crédito.")
        if st.button("📝 Registrarme gratis", type="primary", key="btn_reg_exp"):
            st.session_state["show_register"] = True
            st.rerun()
        st.stop()
    # ══════════════════════════════════════════════════════════════════════════
    # EXPEDIENTE CLÍNICO — centrado en el paciente
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("🏥 Expediente Clínico Digital")
    uid = _user_id()
    db_activa = _DB_ON and _db.db_ok() and uid

    if not _is_auth():
        st.warning("Inicia sesión para acceder al expediente.")
    elif not db_activa:
        st.error("Railway DB no disponible. Verifica la conexión.")
    else:
        # ── SELECCIÓN DE PACIENTE ───────────────────────────────────────────
        pacientes = _cached_patients(uid)
        sel_exp_id = st.session_state.get("exp_pac_id")
        sel_exp = next((p for p in pacientes if p["id"] == sel_exp_id), None) if sel_exp_id else None

        if not sel_exp:
            # ── LISTA DE PACIENTES ──────────────────────────────────────────
            col_lista, col_nuevo = st.columns([3, 1])
            with col_lista:
                buscar_p = st.text_input("🔍 Buscar paciente", placeholder="Nombre o expediente...", key="exp_buscar")
            with col_nuevo:
                st.markdown(" ")
                if st.button("➕ Nuevo paciente", type="primary", use_container_width=True, key="btn_nuevo_pac"):
                    st.session_state["exp_modo"] = "nuevo"

            if st.session_state.get("exp_modo") == "nuevo":
                with st.expander("➕ Registrar nuevo paciente", expanded=True):
                    np1, np2, np3 = st.columns(3)
                    with np1:
                        np_nombre = st.text_input("Nombre completo *", key="np_nombre")
                        np_exp    = st.text_input("N° expediente", key="np_exp")
                        np_edad   = st.number_input("Edad", 0, 120, 50, 1, key="np_edad")
                    with np2:
                        np_sexo   = st.selectbox("Sexo", ["Masculino","Femenino","Otro"], key="np_sexo")
                        np_peso   = st.number_input("Peso (kg)", 0.0, 300.0, 70.0, 0.5, key="np_peso")
                        np_tipo   = st.selectbox("Tipo de paciente", [
                            "General","TRRC / UCI","Trasplante renal","ERC crónica",
                            "Hemodiálisis","Diálisis peritoneal","Agudo hospitalizado"
                        ], key="np_tipo")
                    with np3:
                        # CIE-10 selector + texto libre
                        CIE10_EXP = [
                            "N18.5 — ERC Estadio 5","N18.4 — ERC Estadio 4",
                            "N18.3 — ERC Estadio 3","N18.2 — ERC Estadio 2",
                            "N18.1 — ERC Estadio 1","N17 — Lesión Renal Aguda",
                            "Z94.0 — Trasplante renal","T86.1 — Rechazo trasplante",
                            "N04 — Síndrome nefrótico","N05 — Síndrome nefrítico",
                            "M32.1 — Nefritis lúpica","E11.21 — Nefropatía DM2",
                            "I12 — HTA con ERC","N39.0 — IVU",
                            "D59.3 — SHU","M31.1 — Vasculitis ANCA",
                            "✏️ Escribir diagnóstico manualmente",
                        ]
                        dx_cie_sel = st.selectbox("Diagnóstico (CIE-10)", CIE10_EXP, key="np_cie_sel")
                        # Always editable - pre-fill with selected value but allow editing
                        dx_prefill = "" if dx_cie_sel.startswith("✏️") else dx_cie_sel
                        np_dx = st.text_area("Diagnóstico (editable)", height=60, key="np_dx",
                                             value=dx_prefill,
                                             placeholder="Selecciona arriba o escribe aquí tu propio diagnóstico")
                        np_notas = st.text_area("Notas adicionales", height=40, key="np_notas")

                    if st.button("💾 Registrar paciente", type="primary", key="btn_reg_pac"):
                        if not np_nombre:
                            st.warning("El nombre es obligatorio.")
                        else:
                            try:
                                new_id = _db.create_patient(uid, {
                                    "nombre": np_nombre, "expediente": np_exp,
                                    "edad": int(np_edad), "sexo": np_sexo,
                                    "peso": float(np_peso), "tipo": np_tipo,
                                    "diagnostico": np_dx, "notas": np_notas,
                                })
                                if new_id:
                                    _clear_cache()
                                    st.session_state["exp_pac_id"] = new_id
                                    st.session_state.pop("exp_modo", None)
                                    st.success(f"✅ Paciente '{np_nombre}' registrado.")
                                    st.rerun()
                                else:
                                    st.error("Error al registrar paciente.")
                            except AttributeError:
                                st.error("⚠️ db.py desactualizado en el servidor. "
                                         "Sube el db.py que te entregué a GitHub y espera el redeploy.")

            # Lista de pacientes
            pacientes_filtrados = [p for p in pacientes
                if buscar_p.lower() in (p.get("nombre","") + p.get("expediente","")).lower()
            ] if buscar_p else pacientes

            if pacientes_filtrados:
                for p in pacientes_filtrados:
                    records = _cached_clinical_records(p["id"])
                    tipo_icon = {"TRRC / UCI":"🏥","Trasplante renal":"💉","ERC crónica":"🔵",
                                 "Hemodiálisis":"⚙️","Diálisis peritoneal":"💧"}.get(p.get("tipo",""),"👤")
                    with st.expander(f"{tipo_icon} **{p.get('nombre','—')}** · Exp: {p.get('expediente','—')} · "
                                     f"{p.get('edad','—')} años · {len(records)} registro(s)"):
                        ec1, ec2 = st.columns([2,1])
                        with ec1:
                            st.write(f"**Dx:** {p.get('diagnostico','—')}")
                            st.write(f"**Tipo:** {p.get('tipo','—')} · **Peso:** {p.get('peso','—')} kg · **Sexo:** {p.get('sexo','—')}")
                            if p.get("notas"): st.caption(p["notas"])
                        with ec2:
                            if st.button("📋 Abrir expediente", key=f"abrir_{p['id']}", use_container_width=True):
                                st.session_state["exp_pac_id"] = p["id"]
                                st.rerun()
                            if st.button("🗑️ Eliminar", key=f"del_exp_{p['id']}", use_container_width=True):
                                _db.delete_patient(p["id"], uid)
                                _clear_cache(); st.rerun()
            else:
                if not st.session_state.get("exp_modo"):
                    st.info("No hay pacientes registrados. Usa **➕ Nuevo paciente** para comenzar.")

        else:
            # ── EXPEDIENTE DEL PACIENTE SELECCIONADO ───────────────────────
            col_back, col_title = st.columns([1, 5])
            with col_back:
                if st.button("← Volver", key="btn_exp_back"):
                    st.session_state.pop("exp_pac_id", None)
                    st.rerun()
            with col_title:
                tipo_icon = {"TRRC / UCI":"🏥","Trasplante renal":"💉","ERC crónica":"🔵",
                             "Hemodiálisis":"⚙️"}.get(sel_exp.get("tipo",""),"👤")
                st.markdown(f"### {tipo_icon} {sel_exp.get('nombre','—')} · "
                            f"Exp: {sel_exp.get('expediente','—')} · "
                            f"{sel_exp.get('edad','—')} años · {sel_exp.get('sexo','—')}")
                st.caption(f"**Dx:** {sel_exp.get('diagnostico','—')} · **Peso:** {sel_exp.get('peso','—')} kg")

            st.divider()
            records = _cached_clinical_records(sel_exp["id"])

            # Nuevo registro
            # ── GET PREVIOUS RECORD FOR PRE-LOADING ─────────────────────
            last_rec = records[0] if records else None
            import json as _jrec
            last_datos = {}
            last_receta = ""
            if last_rec:
                try:
                    last_datos = _jrec.loads(last_rec.get("datos_json","{}"))
                    last_receta = last_rec.get("resumen","") if last_rec.get("tipo") == "Receta médica" else last_datos.get("receta","")
                except Exception:
                    pass

            with st.expander("➕ Nueva consulta — Formato SOAP", expanded=len(records)==0):
                st.caption("Estructura SOAP — Subjetivo / Objetivo / Análisis / Plan")

                # ── ENCABEZADO ─────────────────────────────────────────────────
                soap1, soap2, soap3 = st.columns(3)
                with soap1:
                    nr_fecha = st.date_input("Fecha de consulta", key="nr_fecha")
                with soap2:
                    nr_tipo  = st.selectbox("Tipo", [
                        "Consulta externa","Seguimiento","Urgencias / Guardia",
                        "Trasplante","TRRC / UCI","Interconsulta","Otro"
                    ], key="nr_tipo")
                with soap3:
                    nr_titulo = st.text_input("Título / motivo", key="nr_titulo",
                                              placeholder="Ej: Control trasplante mes 3")

                st.divider()

                # ── S — SUBJETIVO ──────────────────────────────────────────────
                st.markdown("**S — Subjetivo**")
                s1, s2 = st.columns(2)
                with s1:
                    nr_motivo = st.text_area("Motivo de consulta",
                                             height=80, key="nr_motivo",
                                             placeholder="Ej: Paciente acude a control post-trasplante mes 3. Refiere edema leve en miembros inferiores.")
                with s2:
                    nr_evolucion = st.text_area("Evolución del padecimiento / síntomas",
                                                height=80, key="nr_evolucion",
                                                placeholder="Ej: Sin fiebre. Diuresis conservada aprox 2L/día. Adherente a medicamentos.")

                st.divider()

                # ── O — OBJETIVO ────────────────────────────────────────────────
                st.markdown("**O — Objetivo**")

                # Signos vitales
                with st.expander("🩺 Signos vitales y exploración física", expanded=True):
                    sv1, sv2, sv3, sv4, sv5, sv6 = st.columns(6)
                    with sv1:
                        nr_peso_sv  = st.number_input("Peso (kg)", 0.0, 300.0,
                                                      float(last_datos.get("peso",0) or sel_exp.get("peso",70) or 70),
                                                      0.1, key="nr_peso_sv")
                    with sv2:
                        nr_talla_sv = st.number_input("Talla (cm)", 0.0, 220.0,
                                                      float(last_datos.get("talla",0) or 0), 0.5, key="nr_talla_sv")
                    with sv3:
                        nr_ta_sv    = st.text_input("TA (mmHg)", value=last_datos.get("ta",""), key="nr_ta_sv", placeholder="120/80")
                    with sv4:
                        nr_fc_sv    = st.text_input("FC (lpm)", value=str(last_datos.get("fc","") or ""), key="nr_fc_sv", placeholder="72")
                    with sv5:
                        nr_temp_sv  = st.text_input("T° (°C)", value=str(last_datos.get("temp","") or ""), key="nr_temp_sv", placeholder="36.5")
                    with sv6:
                        nr_spo2_sv  = st.text_input("SpO₂ (%)", value=str(last_datos.get("spo2","") or ""), key="nr_spo2_sv", placeholder="98")

                    imc_sv = nr_peso_sv / ((nr_talla_sv/100)**2) if nr_talla_sv > 0 and nr_peso_sv > 0 else 0
                    if imc_sv: st.caption(f"IMC: {imc_sv:.1f} kg/m²")

                    ef1, ef2 = st.columns(2)
                    with ef1:
                        nr_exp_gen  = st.text_area("Exploración general / HEENT",
                                                   height=60, key="nr_exp_gen",
                                                   placeholder="Ej: Consciente, orientado, sin dificultad respiratoria. Mucosas hidratadas.")
                        nr_exp_card = st.text_area("Cardiopulmonar",
                                                   height=60, key="nr_exp_card",
                                                   placeholder="Ej: Ruidos cardíacos rítmicos. Campos pulmonares limpios.")
                    with ef2:
                        nr_exp_abd  = st.text_area("Abdomen e injerto",
                                                   height=60, key="nr_exp_abd",
                                                   placeholder="Ej: Abdomen blando. Injerto en FID sin dolor a la palpación, bien delimitado.")
                        nr_exp_ext  = st.text_area("Extremidades / neurológico",
                                                   height=60, key="nr_exp_ext",
                                                   placeholder="Ej: Edema ++/++++ bilateral. Sin focalización neurológica.")

                # Laboratorios
                with st.expander("🔬 Laboratorios", expanded=True):
                    lab_col1, lab_col2, lab_col3, lab_col4 = st.columns(4)
                    with lab_col1:
                        st.caption("**Función renal**")
                        nr_cr  = st.number_input("Cr (mg/dL)", 0.0, 30.0, float(last_datos.get("cr",0) or 0), 0.1, key="nr_cr")
                        nr_bun = st.number_input("BUN (mg/dL)", 0.0, 200.0, float(last_datos.get("bun",0) or 0), 1.0, key="nr_bun")
                        st.caption("**Electrolitos**")
                        nr_k   = st.number_input("K (mEq/L)", 0.0, 10.0, float(last_datos.get("k",0) or 0), 0.1, key="nr_k_lab")
                        nr_na  = st.number_input("Na (mEq/L)", 100.0, 170.0, float(last_datos.get("na",138) or 138), 1.0, key="nr_na_lab")
                        nr_co3 = st.number_input("HCO₃ (mEq/L)", 0.0, 40.0, float(last_datos.get("hco3",0) or 0), 0.5, key="nr_hco3")
                    with lab_col2:
                        st.caption("**Biometría**")
                        nr_hb  = st.number_input("Hb (g/dL)", 0.0, 20.0, float(last_datos.get("hb",0) or 0), 0.1, key="nr_hb")
                        nr_hto = st.number_input("Hto (%)", 0.0, 65.0, float(last_datos.get("hto",0) or 0), 0.5, key="nr_hto_lab")
                        nr_leu = st.number_input("Leucos (/mm³)", 0.0, 50000.0, float(last_datos.get("leu",0) or 0), 100.0, key="nr_leu")
                        nr_plt = st.number_input("Plaquetas (/mm³)", 0.0, 800000.0, float(last_datos.get("plt",0) or 0), 1000.0, key="nr_plt")
                        st.caption("**Inflamación**")
                        nr_pcr = st.number_input("PCR (mg/L)", 0.0, 500.0, float(last_datos.get("pcr",0) or 0), 1.0, key="nr_pcr")
                    with lab_col3:
                        st.caption("**Metabolismo óseo**")
                        nr_ca   = st.number_input("Ca (mg/dL)", 0.0, 15.0, float(last_datos.get("ca",0) or 0), 0.1, key="nr_ca")
                        nr_p    = st.number_input("P (mg/dL)", 0.0, 15.0, float(last_datos.get("p",0) or 0), 0.1, key="nr_p")
                        nr_pth  = st.number_input("PTHi (pg/mL)", 0.0, 3000.0, float(last_datos.get("pth",0) or 0), 10.0, key="nr_pth")
                        st.caption("**Anemia ERC**")
                        nr_ferr = st.number_input("Ferritina (ng/mL)", 0.0, 3000.0, float(last_datos.get("ferr",0) or 0), 10.0, key="nr_ferr")
                        nr_ist  = st.number_input("IST (%)", 0.0, 60.0, float(last_datos.get("ist",0) or 0), 1.0, key="nr_ist")
                    with lab_col4:
                        st.caption("**Trasplante**")
                        nr_tac  = st.number_input("Tacrolimus C0 (ng/mL)", 0.0, 30.0, float(last_datos.get("tac",0) or 0), 0.5, key="nr_tac")
                        nr_csA  = st.number_input("CsA C0 (ng/mL)", 0.0, 600.0, float(last_datos.get("csa",0) or 0), 5.0, key="nr_csa")
                        st.caption("**Hígado / glucosa**")
                        nr_alb  = st.number_input("Albúmina (g/dL)", 0.0, 6.0, float(last_datos.get("alb",0) or 0), 0.1, key="nr_alb")
                        nr_glu  = st.number_input("Glucosa (mg/dL)", 0.0, 600.0, float(last_datos.get("glu",0) or 0), 5.0, key="nr_glu")
                        nr_hba1c= st.number_input("HbA1c (%)", 0.0, 15.0, float(last_datos.get("hba1c",0) or 0), 0.1, key="nr_hba1c")

                st.divider()

                # ── A — ANÁLISIS ────────────────────────────────────────────────
                st.markdown("**A — Análisis / Impresión diagnóstica**")
                nr_analisis = st.text_area("Análisis clínico e impresión diagnóstica",
                                           height=100, key="nr_analisis",
                                           placeholder="Ej: Paciente post-Tx mes 3. Función estable, Cr basal. Nivel de tacrolimus en rango. Anemia leve con hierro adecuado. Sin datos de rechazo.")

                st.divider()

                # ── P — PLAN ────────────────────────────────────────────────────
                st.markdown("**P — Plan**")

                # Pre-load previous prescription
                prev_receta = last_receta or (last_rec.get("resumen","") if last_rec and last_rec.get("tipo") == "Receta médica" else "")

                nr_receta = st.text_area("💊 Indicaciones / Receta (pre-cargada de última consulta — modifica lo necesario)",
                                         height=180, key="nr_receta",
                                         value=prev_receta,
                                         placeholder="1. Tacrolimus 2 mg c/12h VO\n2. MMF 500 mg c/12h VO\n3. Prednisona 5 mg c/24h VO")

                if prev_receta:
                    st.caption("✅ Receta pre-cargada de la última consulta. Modifica lo que cambió.")
                else:
                    st.caption("ℹ️ Sin receta previa. Escribe las indicaciones para esta consulta.")

                p1, p2 = st.columns(2)
                with p1:
                    nr_labs_sol = st.text_area("🔬 Laboratorios solicitados",
                                               height=80, key="nr_labs_sol",
                                               placeholder="Ej: BH, QS, niveles de tacrolimus, orina de 24h")
                with p2:
                    nr_notas = st.text_area("📋 Plan adicional / notas",
                                            height=80, key="nr_notas",
                                            placeholder="Ej: Reducir tacrolimus a 1.5 mg c/12h. Próxima cita en 4 semanas.")

                p3, p4 = st.columns(2)
                with p3:
                    nr_prox_cita = st.date_input("📅 Próxima cita", value=None, key="nr_prox_cita")
                with p4:
                    nr_interconsulta = st.text_input("🔄 Interconsulta",
                                                     key="nr_interconsulta",
                                                     placeholder="Ej: Cardiología — control de HTA post-Tx")

                # ── GUARDAR ───────────────────────────────────────────────────
                if st.button("💾 Guardar registro clínico", type="primary",
                             key="btn_guardar_rec", use_container_width=True):
                    if not nr_titulo and not nr_analisis:
                        st.warning("Agrega al menos un título o análisis.")
                    else:
                        nr_datos = {
                            "peso": nr_peso_sv, "talla": nr_talla_sv,
                            "ta": nr_ta_sv, "fc": nr_fc_sv, "temp": nr_temp_sv, "spo2": nr_spo2_sv,
                            "imc": round(imc_sv, 1) if imc_sv else 0,
                            "exp_gen": nr_exp_gen, "exp_card": nr_exp_card,
                            "exp_abd": nr_exp_abd, "exp_ext": nr_exp_ext,
                            "cr": nr_cr, "bun": nr_bun, "k": nr_k, "na": nr_na, "hco3": nr_co3,
                            "hb": nr_hb, "hto": nr_hto, "leu": nr_leu, "plt": nr_plt, "pcr": nr_pcr,
                            "ca": nr_ca, "p": nr_p, "pth": nr_pth, "ferr": nr_ferr, "ist": nr_ist,
                            "tac": nr_tac, "csa": nr_csA, "alb": nr_alb, "glu": nr_glu, "hba1c": nr_hba1c,
                            "motivo": nr_motivo, "evolucion": nr_evolucion,
                            "exp_fisica": {"gen": nr_exp_gen, "card": nr_exp_card,
                                           "abd": nr_exp_abd, "ext": nr_exp_ext},
                            "analisis": nr_analisis,
                            "receta": nr_receta,
                            "labs_solicitados": nr_labs_sol,
                            "interconsulta": nr_interconsulta,
                            "prox_cita": str(nr_prox_cita) if nr_prox_cita else "",
                        }
                        titulo_final = nr_titulo or f"Consulta {nr_fecha}"
                        resumen_final = (f"S: {nr_motivo[:100] if nr_motivo else '—'}\n"
                                         f"A: {nr_analisis[:200] if nr_analisis else '—'}\n"
                                         f"P: {nr_receta[:200] if nr_receta else '—'}")
                        try:
                            rec_id = _db.add_clinical_record(sel_exp["id"], uid, {
                                "tipo": nr_tipo,
                                "titulo": titulo_final,
                                "fecha_consulta": nr_fecha,
                                "resumen": resumen_final,
                                "notas": nr_notas,
                                "datos": nr_datos,
                            })
                            if rec_id:
                                _clear_cache()
                                st.success("✅ Consulta guardada correctamente.")
                                st.rerun()
                            else:
                                st.error("Error al guardar.")
                        except AttributeError:
                            st.error("Sube el db.py actualizado a GitHub.")

            # Lista de registros
            st.markdown(f"#### Registros clínicos ({len(records)})")
            tipo_icons = {"TRRC / Prescripción":"🏥","Nefrología / Calculadoras":"🔢",
                          "Trasplante / Inmunosupresores":"💉","Glomerulopatía":"🔵",
                          "Guardia / Urgencias":"⚡","Consulta externa":"🩺",
                          "Seguimiento":"📊","Interconsulta":"🔄","Otro":"📋"}
            for rec in records:
                fecha_r = str(rec.get("fecha_consulta",""))[:10] or str(rec.get("created_at",""))[:10]
                icono_r = tipo_icons.get(rec.get("tipo","Otro"), "📋")
                with st.expander(f"{icono_r} {fecha_r} — **{rec.get('titulo','—')}** · _{rec.get('tipo','—')}_"):
                    import json as _json_rec
                    try:
                        datos_r = _json_rec.loads(rec.get("datos_json","{}"))
                    except Exception:
                        datos_r = {}

                    # Vital signs row
                    sv_items = []
                    if datos_r.get("peso"): sv_items.append(f"**Peso:** {datos_r['peso']} kg")
                    if datos_r.get("ta"):   sv_items.append(f"**TA:** {datos_r['ta']}")
                    if datos_r.get("fc"):   sv_items.append(f"**FC:** {datos_r['fc']} lpm")
                    if datos_r.get("temp"): sv_items.append(f"**T°:** {datos_r['temp']}°C")
                    if datos_r.get("spo2"): sv_items.append(f"**SpO₂:** {datos_r['spo2']}%")
                    if sv_items:
                        st.markdown(" · ".join(sv_items))

                    # Key lab values as metrics
                    lab_show = [(k, label, fmt) for k, label, fmt in [
                        ("cr","Cr","mg/dL"), ("k","K","mEq/L"), ("hb","Hb","g/dL"),
                        ("tac","Tac C0","ng/mL"), ("pth","PTH","pg/mL"),
                        ("p","P","mg/dL"), ("ferr","Ferr","ng/mL"),
                    ] if datos_r.get(k)]
                    if lab_show:
                        cols = st.columns(min(len(lab_show), 7))
                        for idx, (k, label, fmt) in enumerate(lab_show[:7]):
                            cols[idx].metric(label, f"{datos_r[k]} {fmt}")

                    # SOAP sections
                    if datos_r.get("motivo"):
                        st.markdown(f"**S:** {datos_r['motivo']}")
                    if datos_r.get("exp_abd") or datos_r.get("exp_gen"):
                        st.markdown(f"**O (exploración):** {datos_r.get('exp_gen','')} {datos_r.get('exp_abd','')}")
                    if datos_r.get("analisis"):
                        st.markdown(f"**A:** {datos_r['analisis']}")
                    if datos_r.get("receta"):
                        with st.expander("💊 Ver receta / indicaciones"):
                            st.text(datos_r["receta"])
                    if rec.get("notas"):
                        st.caption(f"**Plan adicional:** {rec['notas']}")
                    if datos_r.get("prox_cita"):
                        st.info(f"📅 Próxima cita: {datos_r['prox_cita']}")

                    rc1, rc2, rc3 = st.columns(3)
                    with rc1:
                        if st.button("📄 Generar receta", key=f"receta_{rec['id']}", use_container_width=True):
                            st.session_state["receta_pac"] = sel_exp
                            st.session_state["receta_rec"] = rec
                            st.session_state["nav_sel"]    = "receta"
                            st.rerun()
                    with rc2:
                        if st.button("🗑️ Eliminar", key=f"del_rec_{rec['id']}", use_container_width=True):
                            _db.delete_clinical_record(rec["id"], uid)
                            _clear_cache(); st.rerun()
                    with rc3:
                        pass  # future: edit record
            if not records:
                st.info("Sin registros aún. Usa '➕ Nueva consulta' arriba para agregar el primero.")

elif nav == "nota_tx":
    # ══════════════════════════════════════════════════════════════════════════
    # NOTA INICIAL NEFROLÓGICA POST-TRASPLANTE RENAL
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("🔴 Nota Inicial Nefrológica Post-Trasplante Renal")
    st.caption("Genera y guarda la nota de ingreso post-TR en el expediente del paciente.")

    if _rol() in ("guest", "free", "expirado"):
        st.warning("🔒 Requiere registro para guardar notas.")
        if st.button("📝 Registrarme", type="primary", key="btn_reg_ntx"):
            st.session_state["show_register"] = True; st.rerun()
        st.stop()

    uid_ntx = _user_id()

    # ── SELECCIÓN O CREACIÓN DEL PACIENTE ─────────────────────────────────────
    st.markdown("### 👤 Ficha de Identificación del Paciente")
    st.caption("Los datos aquí capturados quedan guardados en el expediente y "
               "se pre-cargan en notas de evolución, recetas y calculadoras.")

    ntx_pac_mode = st.radio("", ["🔍 Paciente ya registrado",
                                 "➕ Registro nuevo (primer trasplante)"],
                            horizontal=True, key="ntx_pac_mode")

    pac_ntx = {}
    pac_id_ntx = None

    if "ya registrado" in ntx_pac_mode:
        if uid_ntx and _DB_ON and _db.db_ok():
            try:
                pacs_ntx = _cached_patients(uid_ntx)
                tx_pacs  = [p for p in pacs_ntx if "Trasplante" in (p.get("tipo","") or "")]
                todos    = tx_pacs + [p for p in pacs_ntx if p not in tx_pacs]
                if todos:
                    opts = {f"{p['nombre']} — Exp:{p.get('expediente','—')}": p for p in todos}
                    sel  = st.selectbox("Selecciona paciente", list(opts.keys()), key="ntx_pac_sel")
                    pac_ntx  = opts[sel]
                    pac_id_ntx = pac_ntx.get("id")
                else:
                    st.info("Sin pacientes registrados. Usa 'Registro nuevo'.")
            except Exception:
                st.info("Sube el db.py actualizado a GitHub.")
        else:
            st.info("Conecta Railway DB.")
    else:
        # Ficha de identificación completa
        fid1, fid2, fid3 = st.columns(3)
        with fid1:
            ntx_nombre  = st.text_input("Nombre completo *", key="ntx_nombre")
            ntx_exp     = st.text_input("N° expediente", key="ntx_exp")
            ntx_fecha_n = st.date_input("Fecha de nacimiento", key="ntx_fecha_n")
            ntx_edad    = st.number_input("Edad (años)", 0, 100, 45, 1, key="ntx_edad")
        with fid2:
            ntx_sexo    = st.selectbox("Sexo", ["Masculino","Femenino","Otro"], key="ntx_sexo")
            ntx_edo_civ = st.selectbox("Estado civil",
                          ["Soltero","Casado","Unión libre","Divorciado","Viudo"], key="ntx_edo_civ")
            ntx_ocup    = st.text_input("Ocupación", key="ntx_ocup")
            ntx_origi   = st.text_input("Lugar de origen / residencia", key="ntx_origi")
        with fid3:
            ntx_peso    = st.number_input("Peso (kg)", 20.0, 200.0, 70.0, 0.5, key="ntx_peso")
            ntx_talla   = st.number_input("Talla (cm)", 100.0, 220.0, 170.0, 0.5, key="ntx_talla")
            ntx_imc     = ntx_peso / ((ntx_talla/100)**2) if ntx_talla > 0 else 0
            st.metric("IMC", f"{ntx_imc:.1f} kg/m²")
            ntx_tel     = st.text_input("Teléfono / contacto", key="ntx_tel")

        # Diagnóstico de base
        CIE10_TX = [
            "N18.5 — ERC Estadio 5 (ERCT)","N18.4 — ERC Estadio 4",
            "E11.21 — Nefropatía diabética DM2","E10.21 — Nefropatía diabética DM1",
            "I12 — Nefroesclerosis hipertensiva","N04 — Síndrome nefrótico",
            "M32.1 — Nefritis lúpica","N02 — IgA Nefropatía",
            "N04.0 — Nefropatía membranosa","M31.1 — Vasculitis ANCA",
            "D59.3 — SHU atípico","Q61 — Enfermedad poliquística renal",
            "N18.0 — ERC de causa no determinada","Otro (escribir)",
        ]
        ntx_dx_sel = st.selectbox("Diagnóstico de base (CIE-10)", CIE10_TX, key="ntx_dx_sel")
        if ntx_dx_sel.startswith("Otro"):
            ntx_dx = st.text_input("Diagnóstico manual", key="ntx_dx_txt")
        else:
            ntx_dx = ntx_dx_sel

        fid4, fid5 = st.columns(2)
        with fid4:
            ntx_dialisis_tipo = st.selectbox("Modalidad de diálisis previa",
                                ["Hemodiálisis crónica","Diálisis peritoneal",
                                 "Prediálisis (trasplante anticipado)","Ninguna"], key="ntx_dial_tipo")
            ntx_t_dialisis = st.number_input("Tiempo en diálisis (meses)", 0, 360, 24, 1, key="ntx_t_dial")
        with fid5:
            ntx_tx_previo = st.checkbox("Retrasplante (trasplante previo)", key="ntx_retx")
            if ntx_tx_previo:
                ntx_causa_falla = st.text_input("Causa de falla del trasplante previo", key="ntx_causa_falla")
            ntx_alergias = st.text_input("Alergias conocidas", key="ntx_alergias",
                                          placeholder="Ej: Penicilina — rash. No otras conocidas.")

    st.divider()

    # ── DATOS DEL DONANTE ──────────────────────────────────────────────────────
    st.markdown("### 🫀 Datos del Donante")
    don1, don2, don3 = st.columns(3)
    with don1:
        don_tipo = st.selectbox("Tipo de donante", [
            "Donante fallecido — Muerte encefálica (DBD)",
            "Donante fallecido — Muerte cardíaca (DCD)",
            "Donante vivo relacionado",
            "Donante vivo no relacionado",
            "Donante vivo altruista",
        ], key="don_tipo")
        don_edad = st.number_input("Edad del donante", 0, 90, 45, 1, key="don_edad")
        don_sexo = st.selectbox("Sexo donante", ["Masculino","Femenino"], key="don_sexo")
    with don2:
        don_causa = st.text_input("Causa de muerte / motivo donación",
                                  placeholder="Ej: TCE por accidente automovilístico",
                                  key="don_causa")
        don_hta  = st.checkbox("Historia de HTA en donante", key="don_hta")
        don_dm   = st.checkbox("Historia de DM en donante", key="don_dm")
        don_cr   = st.number_input("Creatinina terminal donante (mg/dL)",
                                   0.0, 15.0, 1.0, 0.1, key="don_cr")
    with don3:
        don_cmv_d = st.selectbox("Serología CMV donante",
                                 ["Positivo (D+)","Negativo (D-)","Desconocido"], key="don_cmv")
        don_vhb   = st.selectbox("VHB donante",
                                 ["Negativo","HBsAg positivo","Anti-HBc positivo"], key="don_vhb")
        don_vhc   = st.selectbox("VHC donante",
                                 ["Negativo","Anti-VHC positivo","RNA VHC positivo"], key="don_vhc")
        don_hiv   = st.selectbox("HIV donante", ["Negativo","Positivo","Desconocido"], key="don_hiv")

    # KDPI
    with st.expander("📊 KDPI del donante (opcional — si ya lo calculaste)"):
        ntx_kdpi = st.number_input("KDPI calculado (%)", 0, 100, 0, 1, key="ntx_kdpi")
        if ntx_kdpi:
            if ntx_kdpi < 20:
                st.success(f"KDPI {ntx_kdpi}% — Órgano de alta calidad")
            elif ntx_kdpi < 85:
                st.warning(f"KDPI {ntx_kdpi}% — Criterio estándar/expandido")
            else:
                st.error(f"KDPI {ntx_kdpi}% — Alto riesgo. DGF probable.")

    st.divider()

    # ── DATOS DE LA CIRUGÍA ────────────────────────────────────────────────────
    st.markdown("### 🔪 Datos de la Cirugía")
    cir1, cir2, cir3 = st.columns(3)
    with cir1:
        cir_fecha   = st.date_input("Fecha del trasplante", key="cir_fecha")
        cir_isq_fri = st.number_input("Isquemia fría total (horas)", 0.0, 48.0, 16.0, 0.5, key="cir_isq_fri")
        cir_wit2    = st.number_input("Isquemia caliente 2 / WIT2 (min)", 0, 120, 35, 1, key="cir_wit2")
    with cir2:
        cir_wit1    = st.number_input("Isquemia caliente 1 / WIT1 (min, solo DCD)",
                                      0, 60, 0, 1, key="cir_wit1",
                                      disabled="DCD" not in don_tipo)
        cir_diuresis_intra = st.selectbox("Diuresis intraoperatoria",
            ["Sí — inmediata al clampeo","Sí — tardía (>15 min)","No — anuria intraoperatoria"],
            key="cir_diuresis")
        cir_anastomosis = st.selectbox("Anastomosis",
            ["Arteria ilíaca externa + vena ilíaca externa",
             "Arteria ilíaca interna (hipogástrica) + vena ilíaca externa",
             "Arteria aorta + vena cava (pediátrico)",
             "Otro"], key="cir_anastomosis")
    with cir3:
        cir_eventualidades = st.text_area("Eventualidades quirúrgicas",
            height=100, key="cir_event",
            placeholder="Ej: Sin eventualidades. / Lesión vascular reparada. / Arteria polar reimplantada.")

    st.divider()

    # ── RIESGO INMUNOLÓGICO ────────────────────────────────────────────────────
    st.markdown("### 🧬 Riesgo Inmunológico del Receptor")
    rim1, rim2, rim3 = st.columns(3)
    with rim1:
        ntx_cpra    = st.number_input("cPRA (%)", 0, 100, 0, 1, key="ntx_cpra")
        ntx_xm      = st.selectbox("Crossmatch",
            ["Virtual negativo / CDC negativo",
             "FCXM débilmente positivo (CDC neg)",
             "CDC positivo células B",
             "CDC positivo células T"], key="ntx_xm")
    with rim2:
        ntx_dsa_pre = st.selectbox("DSA preformados",
            ["No detectados","MFI <3,000 (débiles)","MFI 3,000–5,000","MFI >5,000 (fuertes)"],
            key="ntx_dsa")
        ntx_mm_dr   = st.number_input("Mismatches HLA-DR", 0, 2, 0, 1, key="ntx_mm_dr")
        ntx_mm_tot  = st.number_input("Mismatches totales (A+B+DR)", 0, 6, 2, 1, key="ntx_mm_tot")
    with rim3:
        if ntx_cpra >= 80 or "positivo células T" in ntx_xm or "5,000" in ntx_dsa_pre:
            st.error("🔴 **Riesgo inmunológico ALTO**")
            riesgo_inm = "Alto"
        elif ntx_cpra >= 30 or ntx_mm_tot >= 4 or ntx_tx_previo if "ya registrado" not in ntx_pac_mode else False:
            st.warning("🟡 **Riesgo inmunológico MODERADO**")
            riesgo_inm = "Moderado"
        else:
            st.success("🟢 **Riesgo inmunológico BAJO-ESTÁNDAR**")
            riesgo_inm = "Estándar"

    st.divider()

    # ── RIESGO INFECCIOSO ──────────────────────────────────────────────────────
    st.markdown("### 🦠 Riesgo Infeccioso")
    rin1, rin2 = st.columns(2)
    with rin1:
        ntx_cmv_r = st.selectbox("Serología CMV receptor",
                                 ["Positivo (R+)","Negativo (R-)","Desconocido"], key="ntx_cmv_r")
        ntx_tb    = st.selectbox("Riesgo de tuberculosis",
            ["Bajo (Quantiferon negativo, sin contactos)",
             "Moderado (contacto TB, zona endémica, sin Quantiferon)",
             "Alto (Quantiferon positivo, TB latente)"], key="ntx_tb")
        ntx_vhb_r = st.selectbox("VHB receptor",
            ["Anti-HBs positivo (vacunado/inmune)","HBsAg positivo","Susceptible (sin inmunidad)"],
            key="ntx_vhb_r")
    with rin2:
        # CMV risk
        if "D+" in don_cmv_d and "R-" in ntx_cmv_r:
            st.error("🔴 **CMV D+/R- → Alto riesgo** — Profilaxis 6 meses con valganciclovir")
        elif "R+" in ntx_cmv_r:
            st.warning("🟡 **CMV R+ → Riesgo intermedio** — Profilaxis 3 meses con valganciclovir")
        else:
            st.success("🟢 **CMV D-/R- → Bajo riesgo** — Sin profilaxis CMV específica")

        if "Alto" in ntx_tb:
            st.error("🔴 **TB latente** → Iniciar isoniazida profilaxis tras establecer fecha de cirugía")
        elif "Moderado" in ntx_tb:
            st.warning("🟡 **Riesgo TB moderado** → Solicitar Quantiferon + Rx tórax")

    st.divider()

    # ── INDUCCIÓN ──────────────────────────────────────────────────────────────
    st.markdown("### 💉 Inducción de Inmunosupresión")
    ind1, ind2 = st.columns(2)
    with ind1:
        ntx_induccion = st.selectbox("Agente de inducción",
            ["Basiliximab (20 mg día 0 + día 4)",
             "Timoglobulina (ATG-r) — bajo riesgo 3 mg/kg",
             "Timoglobulina (ATG-r) — estándar 4.5 mg/kg",
             "Timoglobulina (ATG-r) — alto riesgo 6 mg/kg",
             "Sin inducción biológica"], key="ntx_ind")
        ntx_ind_dosis = st.text_area("Dosis administradas / incidencias",
                                     height=80, key="ntx_ind_dosis",
                                     placeholder="Ej: Timoglobulina 1.5 mg/kg/día × 3 dosis = 4.5 mg/kg total. Sin reacciones.")
    with ind2:
        ntx_is_inicial = st.text_area("Inmunosupresión de mantenimiento inicial",
                                      height=80, key="ntx_is_ini",
                                      placeholder="Ej: Tacrolimus 0.1 mg/kg/día c/12h + MMF 1g c/12h + Prednisona 60 mg/día taper")
        ntx_profilaxis = st.text_area("Profilaxis infecciosa indicada",
                                      height=80, key="ntx_profilaxis",
                                      placeholder="Ej: Valganciclovir 900 mg/día × 6 meses. TMP-SMX 1 tab/día × 12 meses.")

    st.divider()

    # ── EVALUACIÓN POST-Tx ─────────────────────────────────────────────────────
    st.markdown("### 🏥 Evaluación Inicial Post-Trasplante")
    ep1, ep2, ep3 = st.columns(3)
    with ep1:
        ntx_funcion = st.selectbox("Función inicial del injerto",
            ["Función inmediata (IFG) — diuresis >500 mL/h",
             "Función lenta (SGF) — oliguria <500 mL/h sin diálisis",
             "Función retardada (DGF) — requirió diálisis en 1ª semana",
             "No función primaria (PNF) — anuria sin recuperación"], key="ntx_funcion")
        ntx_diuresis_24h = st.number_input("Diuresis primeras 24h (mL)", 0, 20000, 0, 100, key="ntx_diuresis")
    with ep2:
        ntx_cr_post = st.number_input("Creatinina post-Tx (mg/dL)", 0.0, 30.0, 0.0, 0.1, key="ntx_cr_post")
        ntx_k_post  = st.number_input("K post-Tx (mEq/L)", 0.0, 10.0, 0.0, 0.1, key="ntx_k_post")
        ntx_ta_post = st.text_input("TA post-Tx", placeholder="Ej: 140/90", key="ntx_ta_post")
    with ep3:
        ntx_doppler = st.selectbox("Eco Doppler renal",
            ["Pendiente","Normal — flujo conservado, IR <0.70",
             "IR 0.70–0.80 — monitoreo estrecho",
             "IR >0.80 — anormal, trombosis excluida",
             "Trombosis arterial — cirugía urgente",
             "Trombosis venosa — cirugía urgente"], key="ntx_doppler")

    ntx_notas_ev = st.text_area("Notas adicionales de la evaluación / plan inicial",
                                 height=100, key="ntx_notas_ev",
                                 placeholder="Ej: Se inicia manitol IV 50g en QX. HD post-Tx día 1 por K 6.2. "
                                             "Se ajusta tacrolimus a niveles 10-12 ng/mL. "
                                             "Control con eco Doppler mañana.")

    # ── GUARDAR NOTA ───────────────────────────────────────────────────────────
    st.divider()
    if st.button("💾 Guardar Nota Post-Trasplante", type="primary",
                 use_container_width=True, key="btn_save_nota_tx"):

        if not uid_ntx or not _DB_ON or not _db.db_ok():
            st.error("Sube el db.py actualizado a GitHub.")
            st.stop()

        # Create patient if new
        if "ya registrado" not in ntx_pac_mode and ntx_nombre:
            try:
                pac_id_ntx = _db.create_patient(uid_ntx, {
                    "nombre": ntx_nombre, "expediente": ntx_exp,
                    "edad": int(ntx_edad), "sexo": ntx_sexo,
                    "peso": float(ntx_peso), "tipo": "Trasplante renal",
                    "diagnostico": ntx_dx,
                    "notas": f"Estado civil: {ntx_edo_civ} | Ocupación: {ntx_ocup} | Tel: {ntx_tel}",
                })
                _clear_cache()
            except Exception as e_pac:
                st.error(f"Error al crear paciente: {e_pac}"); st.stop()

        if not pac_id_ntx:
            st.warning("Selecciona o registra un paciente primero.")
            st.stop()

        # Build structured note data
        datos_nota_tx = {
            # Ficha identificación
            "peso": ntx_peso if "ya registrado" not in ntx_pac_mode else pac_ntx.get("peso"),
            "talla": ntx_talla if "ya registrado" not in ntx_pac_mode else 0,
            "ta": ntx_ta_post,
            # Donante
            "donante_tipo": don_tipo, "donante_edad": don_edad,
            "donante_causa": don_causa, "donante_cmv": don_cmv_d,
            "donante_cr": don_cr, "kdpi": ntx_kdpi,
            # Cirugía
            "fecha_tx": str(cir_fecha),
            "isquemia_fria_h": cir_isq_fri,
            "wit2_min": cir_wit2, "wit1_min": cir_wit1,
            "diuresis_intra": cir_diuresis_intra,
            "eventualidades": cir_eventualidades,
            # Inmunología
            "cpra": ntx_cpra, "xm": ntx_xm, "dsa_pre": ntx_dsa_pre,
            "mm_dr": ntx_mm_dr, "mm_total": ntx_mm_tot,
            "riesgo_inm": riesgo_inm,
            # Riesgo infeccioso
            "cmv_receptor": ntx_cmv_r, "tb_riesgo": ntx_tb,
            # Inducción
            "induccion": ntx_induccion, "induccion_dosis": ntx_ind_dosis,
            "is_inicial": ntx_is_inicial, "profilaxis": ntx_profilaxis,
            # Evaluación
            "funcion_injerto": ntx_funcion, "diuresis_24h": ntx_diuresis_24h,
            "cr": ntx_cr_post, "k": ntx_k_post, "doppler": ntx_doppler,
        }

        resumen_nota = (
            f"NOTA POST-TR | {str(cir_fecha)} | "
            f"Donante: {don_tipo.split('—')[0].strip()} | "
            f"Isq. fría: {cir_isq_fri}h | WIT2: {cir_wit2}min | "
            f"Función: {ntx_funcion.split('(')[0].strip()} | "
            f"Diuresis 24h: {ntx_diuresis_24h} mL | "
            f"Cr: {ntx_cr_post} mg/dL | "
            f"Inducción: {ntx_induccion.split('(')[0].strip()}\n"
            f"IS inicial: {ntx_is_inicial}\n"
            f"Profilaxis: {ntx_profilaxis}"
        )

        try:
            rec_id_ntx = _db.add_clinical_record(pac_id_ntx, uid_ntx, {
                "tipo": "Trasplante / Nota inicial post-TR",
                "titulo": f"Nota inicial post-trasplante renal — {cir_fecha}",
                "fecha_consulta": cir_fecha,
                "resumen": resumen_nota,
                "notas": ntx_notas_ev,
                "datos": datos_nota_tx,
            })
            if rec_id_ntx:
                _clear_cache()
                st.success("✅ Nota post-trasplante guardada correctamente en el expediente del paciente.")
                st.info("💡 Ahora puedes ir a **🏥 Expediente Clínico** para ver el paciente "
                        "y agregar notas de evolución. La receta y los datos de inducción "
                        "se pre-cargarán en cada nueva consulta.")
                # Store patient for quick navigation
                st.session_state["exp_pac_id"] = pac_id_ntx
                col_nx1, col_nx2 = st.columns(2)
                with col_nx1:
                    if st.button("📋 Ver expediente del paciente",
                                 key="btn_ver_exp_tx"):
                        st.session_state["nav_sel"] = "expediente"; st.rerun()
                with col_nx2:
                    if st.button("📄 Generar receta inicial",
                                 key="btn_rx_post_tx"):
                        p_data = {"id": pac_id_ntx,
                                  "nombre": ntx_nombre if "ya registrado" not in ntx_pac_mode else pac_ntx.get("nombre",""),
                                  "diagnostico": ntx_dx if "ya registrado" not in ntx_pac_mode else pac_ntx.get("diagnostico",""),
                                  "peso": ntx_peso if "ya registrado" not in ntx_pac_mode else pac_ntx.get("peso",70)}
                        st.session_state["receta_pac"] = p_data
                        st.session_state["receta_rec"] = {"resumen": ntx_is_inicial, "tipo": "Receta médica"}
                        st.session_state["nav_sel"] = "receta"; st.rerun()
            else:
                st.error("Error al guardar. Revisa la conexión con Railway.")
        except AttributeError:
            st.error("Sube el db.py actualizado a GitHub y espera el redeploy.")

elif nav == "receta":
    # ── BLOQUEO PARA INVITADOS ─────────────────────────────────────────────────
    if _rol() in ("guest", "free", "expirado"):
        st.warning("🔒 **La Receta Médica requiere registro.** "
                   "Como invitado las recetas no se guardan ni se asocian a un médico.")
        st.info("Regístrate gratis — 7 días de acceso completo.")
        if st.button("📝 Registrarme gratis", type="primary", key="btn_reg_rx"):
            st.session_state["show_register"] = True
            st.rerun()
        st.stop()

    # ══════════════════════════════════════════════════════════════════════════
    # RECETA MÉDICA — NOM-004-SSA3-2012 / COFEPRIS — rediseño completo
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("📄 Receta Médica — NOM-004-SSA3-2012 / COFEPRIS")

    if not _is_auth():
        st.warning("Inicia sesión para generar recetas.")
    else:
        uid_rx    = _user_id()
        dr_nombre = st.session_state.get("sess_nombre","")
        dr_cedula = st.session_state.get("sess_cedula","")         # esp
        dr_ced_gen= st.session_state.get("sess_ced_general","")
        dr_univ   = st.session_state.get("sess_universidad","")    # esp
        dr_univ_gen=st.session_state.get("sess_univ_general","")
        dr_esp    = st.session_state.get("sess_especialidad","")
        dr_inst   = st.session_state.get("sess_institucion","")
        dr_dom    = st.session_state.get("sess_domicilio","")
        dr_tel    = st.session_state.get("sess_telefono","")
        dr_consejo= st.session_state.get("sess_consejo_nombre","")
        dr_cons_num=st.session_state.get("sess_consejo_numero","")

        faltantes = [f for f,v in [("nombre",dr_nombre),("cédula de especialidad",dr_cedula),
                                    ("domicilio",dr_dom)] if not v]
        if faltantes:
            st.warning(f"⚠️ Perfil incompleto: faltan **{', '.join(faltantes)}**. "
                       "Ve a 👤 Mi Cuenta.")
            if st.button("→ Mi Cuenta"): st.session_state["nav_sel"]="micuenta"; st.rerun()
        else:
            # CIE-10 frecuentes
            CIE10_BASE = [
                "N18.5 — ERC Estadio 5 (ERCT)","N18.4 — ERC Estadio 4",
                "N18.3 — ERC Estadio 3","N18.2 — ERC Estadio 2","N18.1 — ERC Estadio 1",
                "N17 — Lesión Renal Aguda","Z94.0 — Trasplante renal presente",
                "T86.1 — Rechazo de trasplante renal","N04 — Síndrome nefrótico",
                "N05 — Síndrome nefrítico crónico","M32.1 — Nefritis lúpica",
                "E11.21 — Nefropatía diabética DM2","I12 — HTA con ERC",
                "N39.0 — IVU","D59.3 — SHU","M31.1 — Vasculitis ANCA",
                "N04.0 — Nefropatía membranosa","N02 — Hematuria recurrente (IgAN)",
            ]
            # Custom diagnoses from DB
            custom_dx = []
            if uid_rx and _DB_ON and _db.db_ok():
                try:
                    custom_dx = _db.get_user_diagnosticos(uid_rx)
                except Exception:
                    custom_dx = []
            todos_dx = CIE10_BASE + [f"★ {d}" for d in custom_dx] + ["✏️ Agregar diagnóstico nuevo"]

            rx_tab1, rx_tab2 = st.tabs(["✍️ Crear Receta", "📋 Historial de recetas"])

            with rx_tab1:
                # ── PASO 1: PACIENTE ──────────────────────────────────────────
                st.markdown("#### 👤 Paso 1 — Paciente")
                pac_mode = st.radio("", ["🔍 Cargar paciente existente",
                                         "➕ Nuevo paciente",
                                         "✏️ Sin paciente (solo indicaciones)"],
                                    horizontal=True, key="rx_pac_mode")

                pac_data = {}
                pac_id_rx = None

                if "existente" in pac_mode:
                    if uid_rx and _DB_ON and _db.db_ok():
                        try:
                            pacs = _cached_patients(uid_rx)
                            if pacs:
                                buscar_rx = st.text_input("Buscar paciente",
                                    placeholder="Nombre o expediente...", key="rx_buscar_pac")
                                pacs_f = [p for p in pacs
                                          if buscar_rx.lower() in
                                          (p.get("nombre","") + p.get("expediente","")).lower()
                                ] if buscar_rx else pacs
                                pac_opts = {
                                    f"{p['nombre']} — Exp:{p.get('expediente','—')} — {p.get('diagnostico','')[:30]}": p
                                    for p in pacs_f
                                }
                                sel = st.selectbox("Selecciona paciente", list(pac_opts.keys()),
                                                   key="rx_pac_sel")
                                pac_data = pac_opts.get(sel, {})
                                pac_id_rx = pac_data.get("id")
                            else:
                                st.info("No hay pacientes registrados. Crea uno nuevo.")
                        except Exception:
                            st.info("Sube el db.py actualizado a GitHub.")
                    else:
                        st.info("Conecta Railway DB para cargar pacientes.")

                elif "Nuevo" in pac_mode:
                    np1, np2, np3 = st.columns(3)
                    with np1:
                        nrx_nombre = st.text_input("Nombre *", key="nrx_nombre")
                        nrx_exp    = st.text_input("N° Expediente", key="nrx_exp")
                    with np2:
                        nrx_edad   = st.number_input("Edad", 0, 120, 50, 1, key="nrx_edad")
                        nrx_sexo   = st.selectbox("Sexo", ["Masculino","Femenino","Otro"], key="nrx_sexo")
                        nrx_peso   = st.number_input("Peso (kg)", 0.0, 300.0, 70.0, 0.5, key="nrx_peso")
                    with np3:
                        nrx_tipo   = st.selectbox("Tipo", ["Trasplante renal","ERC crónica",
                            "Hemodiálisis","TRRC / UCI","General"], key="nrx_tipo")
                        nrx_dx_sel = st.selectbox("Diagnóstico principal", todos_dx[:20], key="nrx_dx_sel")
                        nrx_dx     = nrx_dx_sel if not nrx_dx_sel.startswith("✏️") else st.text_input("Dx manual", key="nrx_dx_txt")

                    if st.button("💾 Guardar como nuevo paciente", key="btn_rx_save_pac"):
                        if not nrx_nombre:
                            st.warning("El nombre es obligatorio.")
                        elif uid_rx and _DB_ON and _db.db_ok():
                            try:
                                new_pid = _db.create_patient(uid_rx, {
                                    "nombre": nrx_nombre, "expediente": nrx_exp,
                                    "edad": int(nrx_edad), "sexo": nrx_sexo,
                                    "peso": float(nrx_peso), "tipo": nrx_tipo,
                                    "diagnostico": nrx_dx,
                                })
                                if new_pid:
                                    _clear_cache()
                                    pac_id_rx = new_pid
                                    pac_data = {"id": new_pid, "nombre": nrx_nombre,
                                                "expediente": nrx_exp, "edad": nrx_edad,
                                                "sexo": nrx_sexo, "peso": nrx_peso,
                                                "diagnostico": nrx_dx}
                                    st.success(f"✅ Paciente '{nrx_nombre}' guardado en expediente.")
                            except AttributeError:
                                st.error("Sube el db.py actualizado a GitHub.")
                        else:
                            pac_data = {"nombre": nrx_nombre, "expediente": nrx_exp,
                                        "edad": nrx_edad, "sexo": nrx_sexo,
                                        "peso": nrx_peso, "diagnostico": nrx_dx}

                st.divider()

                # ── PASO 2: DATOS CLÍNICOS ────────────────────────────────────
                st.markdown("#### 🩺 Paso 2 — Datos clínicos")
                rx1, rx2, rx3 = st.columns(3)
                with rx1:
                    rx_nombre = st.text_input("Nombre del paciente *",
                                              value=pac_data.get("nombre",""), key="rx_nombre")
                    rx_exp    = st.text_input("N° Expediente",
                                              value=pac_data.get("expediente",""), key="rx_exp")
                    rx_edad   = st.text_input("Edad",
                                              value=str(pac_data.get("edad","")) if pac_data.get("edad") else "",
                                              key="rx_edad")
                with rx2:
                    rx_sexo   = st.selectbox("Sexo",
                                             ["Masculino","Femenino","No especificado"],
                                             index=["Masculino","Femenino","No especificado"].index(
                                                 pac_data.get("sexo","Masculino"))
                                             if pac_data.get("sexo","Masculino") in
                                             ["Masculino","Femenino","No especificado"] else 0,
                                             key="rx_sexo")
                    rxp1, rxp2 = st.columns(2)
                    with rxp1:
                        rx_peso  = st.number_input("Peso (kg)", 0.0, 300.0,
                                                   float(pac_data.get("peso",0)) if pac_data.get("peso") else 0.0,
                                                   0.1, key="rx_peso")
                    with rxp2:
                        rx_talla = st.number_input("Talla (cm)", 0.0, 250.0, 0.0, 0.5, key="rx_talla")
                    rx_imc = rx_peso/((rx_talla/100)**2) if rx_talla>0 and rx_peso>0 else 0
                    if rx_imc: st.caption(f"IMC: {rx_imc:.1f} kg/m²")
                with rx3:
                    rx_fecha  = st.date_input("Fecha *", key="rx_fecha")
                    rxsv1, rxsv2 = st.columns(2)
                    with rxsv1:
                        rx_ta   = st.text_input("TA (mmHg)", placeholder="120/80", key="rx_ta")
                        rx_temp = st.text_input("T° (°C)", placeholder="36.5", key="rx_temp")
                    with rxsv2:
                        rx_fc   = st.text_input("FC (lpm)", placeholder="72", key="rx_fc")
                        rx_spo2 = st.text_input("SpO₂ (%)", placeholder="98", key="rx_spo2")

                st.divider()

                # ── PASO 3: DIAGNÓSTICOS ──────────────────────────────────────
                st.markdown("#### 🏷️ Paso 3 — Diagnósticos (CIE-10)")
                dx_list_key = "rx_dx_list"
                if dx_list_key not in st.session_state:
                    dx_init = pac_data.get("diagnostico","")
                    st.session_state[dx_list_key] = [dx_init] if dx_init else []

                # Add from frequent list
                dxc1, dxc2 = st.columns([2,1])
                with dxc1:
                    dx_sel = st.selectbox("Agregar diagnóstico frecuente o nuevo",
                                          ["— Seleccionar —"] + todos_dx, key="rx_dx_sel")
                with dxc2:
                    st.markdown(" ")
                    if st.button("➕ Agregar", key="btn_add_dx") and dx_sel != "— Seleccionar —":
                        if dx_sel.startswith("✏️"):
                            pass  # handled below
                        elif dx_sel not in st.session_state[dx_list_key]:
                            st.session_state[dx_list_key].append(dx_sel)
                            st.rerun()

                # Add custom diagnosis
                with st.expander("✏️ Agregar diagnóstico manual / propio"):
                    dxm1, dxm2, dxm3 = st.columns([2,1,1])
                    with dxm1:
                        dx_manual_txt = st.text_input("Diagnóstico", key="rx_dx_manual")
                    with dxm2:
                        dx_manual_cie = st.text_input("CIE-10", key="rx_dx_cie",
                                                       placeholder="Ej: N18.6")
                    with dxm3:
                        st.markdown(" ")
                        if st.button("➕ Agregar", key="btn_add_dx_manual"):
                            if dx_manual_txt:
                                entrada = f"{dx_manual_cie} — {dx_manual_txt}" if dx_manual_cie else dx_manual_txt
                                if entrada not in st.session_state[dx_list_key]:
                                    st.session_state[dx_list_key].append(entrada)
                                # Save to user's custom list
                                if uid_rx and _DB_ON and _db.db_ok() and dx_manual_txt not in custom_dx:
                                    try:
                                        custom_dx.append(dx_manual_txt)
                                        _db.save_user_diagnosticos(uid_rx, custom_dx)
                                    except Exception:
                                        pass
                                st.rerun()

                # Show current diagnoses list
                if st.session_state[dx_list_key]:
                    st.markdown("**Diagnósticos de esta receta:**")
                    for i, dx in enumerate(st.session_state[dx_list_key]):
                        dc1, dc2 = st.columns([8,1])
                        dc1.markdown(f"• {dx}")
                        if dc2.button("✕", key=f"rm_dx_{i}"):
                            st.session_state[dx_list_key].pop(i)
                            st.rerun()
                    dx_str    = " · ".join(st.session_state[dx_list_key])
                    cie_codes = " / ".join([d.split(" — ")[0] for d in st.session_state[dx_list_key]
                                            if " — " in d])
                else:
                    dx_str    = ""
                    cie_codes = ""

                st.divider()

                # ── PASO 4: INDICACIONES ──────────────────────────────────────
                st.markdown("#### 💊 Paso 4 — Indicaciones médicas")
                st.caption("Formato COFEPRIS: nombre genérico (marca comercial), dosis, vía, frecuencia, duración")
                rx_body = st.text_area("Indicaciones *", height=180, key="rx_body",
                    placeholder="1. Tacrolimus (Prograf®) 1 mg c/12h VO × indefinido\n"
                                 "2. Micofenolato de mofetilo (Cellcept®) 500 mg c/12h VO\n"
                                 "3. Prednisona 5 mg c/24h VO en la mañana")
                rx_notas = st.text_input("Instrucciones al paciente", key="rx_notas",
                    placeholder="Tomar a la misma hora cada día. No suspender sin consultar al médico.")
                rx_prox_fecha = st.date_input("Próxima cita", value=None, key="rx_prox_fecha")
                rx_prox_hora  = st.time_input("Hora", value=None, key="rx_prox_hora")

                # ── LOGO ──────────────────────────────────────────────────────
                with st.expander("🖼️ Logo del consultorio"):
                    st.caption("JPG o PNG · Máx 2MB. Configurable permanentemente en 👤 Mi Cuenta.")
                    logo_up2 = st.file_uploader("Subir logo", type=["jpg","jpeg","png"],
                                                key="rx_logo_up2")
                    if logo_up2:
                        if logo_up2.size > 2_097_152:
                            st.error("Supera 2 MB.")
                        else:
                            import base64 as _b64r
                            st.session_state["sess_logo_b64"]  = _b64r.b64encode(logo_up2.read()).decode()
                            st.session_state["sess_logo_mime"] = logo_up2.type
                            st.success("✅ Logo cargado.")
                    if st.session_state.get("sess_logo_b64"):
                        import base64 as _b64r
                        st.image(_b64r.b64decode(st.session_state["sess_logo_b64"]), width=80)

                st.divider()

                # ── GENERADOR PDF ──────────────────────────────────────────────
                def _pdf_receta(dr_nombre, dr_cedula, dr_ced_gen, dr_univ, dr_univ_gen,
                                dr_esp, dr_inst, dr_dom, dr_tel,
                                dr_consejo, dr_cons_num,
                                folio,
                                rx_nombre, rx_exp, rx_edad, rx_sexo,
                                rx_peso, rx_talla, rx_imc,
                                rx_ta, rx_fc, rx_temp, rx_spo2,
                                dx_str, cie_codes, rx_fecha,
                                rx_prox_fecha, rx_prox_hora,
                                rx_body, rx_notas,
                                logo_b64=None):
                    import io, base64
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.units import cm
                    from reportlab.lib.colors import HexColor, white, black
                    from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                                    Spacer, Table, TableStyle,
                                                    HRFlowable, Image as RLImage)
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
                    from reportlab.lib.utils import ImageReader

                    buf = io.BytesIO()
                    doc = SimpleDocTemplate(buf, pagesize=letter,
                                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                                            topMargin=1.5*cm, bottomMargin=1.5*cm)

                    AZUL  = HexColor("#1E3A8A")
                    AZUL2 = HexColor("#2563EB")
                    AZULC = HexColor("#EFF6FF")
                    AZULM = HexColor("#BFDBFE")
                    GRIS  = HexColor("#6B7280")
                    GRISL = HexColor("#F8FAFC")

                    def P(txt, fn="Helvetica", fs=9, color=black, align=TA_LEFT,
                          bold=False, sp=2, lead=None):
                        return Paragraph(str(txt) if txt else "",
                                         ParagraphStyle("s",
                                             fontName="Helvetica-Bold" if bold else fn,
                                             fontSize=fs, textColor=color,
                                             alignment=align, spaceAfter=sp,
                                             leading=lead or (fs+3)))

                    story = []

                    # ── ENCABEZADO ────────────────────────────────────────────
                    if logo_b64:
                        try:
                            logo_bytes = base64.b64decode(logo_b64)
                            logo_cell = RLImage(io.BytesIO(logo_bytes),
                                                width=1.8*cm, height=1.8*cm,
                                                kind="proportional")
                        except Exception:
                            logo_cell = P("☤", fn="Helvetica-Bold", fs=24, color=AZUL, align=TA_CENTER)
                    else:
                        logo_cell = P("☤", fn="Helvetica-Bold", fs=24, color=AZUL, align=TA_CENTER)

                    hdr_txt = [
                        P(dr_inst or "Consultorio Médico", bold=True, fs=11, color=AZUL, sp=1),
                        P(dr_dom, fs=8, color=GRIS, sp=1),
                        P(f"Tel: {dr_tel}" if dr_tel else "", fs=8, color=GRIS, sp=1),
                        P(f"Folio: {folio}", fs=8, color=AZUL2, align=TA_RIGHT),
                    ]
                    th = Table([[logo_cell, hdr_txt]], colWidths=[2.2*cm, 14.8*cm])
                    th.setStyle(TableStyle([
                        ("BACKGROUND",    (0,0),(-1,-1), AZULC),
                        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                        ("TOPPADDING",    (0,0),(-1,-1), 8),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                        ("LEFTPADDING",   (0,0),(-1,-1), 8),
                        ("BOX",           (0,0),(-1,-1), 1.5, AZUL),
                        ("LINEABOVE",     (0,0),(-1,0),  4,   AZUL2),
                    ]))
                    story.append(th)
                    story.append(Spacer(1, 0.3*cm))

                    # ── DATOS DEL MÉDICO ──────────────────────────────────────
                    med_rows = [
                        [P(dr_nombre, bold=True, fs=12, color=AZUL),
                         P("", fs=8)],
                        [P(dr_esp, fs=9, color=GRIS),
                         P("", fs=8)],
                    ]
                    creds = []
                    if dr_ced_gen:
                        creds.append(f"Méd. Gral. Céd.: {dr_ced_gen} | {dr_univ_gen}")
                    if dr_cedula:
                        creds.append(f"Especialidad Céd.: {dr_cedula} | {dr_univ}")
                    if dr_consejo:
                        creds.append(f"Certif.: {dr_consejo} N°{dr_cons_num}")
                    for c in creds:
                        med_rows.append([P(c, fs=8, color=GRIS), P("", fs=8)])

                    tm = Table(med_rows, colWidths=[13*cm, 4*cm])
                    tm.setStyle(TableStyle([
                        ("TOPPADDING",    (0,0),(-1,-1), 3),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                        ("LEFTPADDING",   (0,0),(-1,-1), 4),
                    ]))
                    story.append(tm)
                    story.append(HRFlowable(width="100%", thickness=1.5, color=AZUL2))
                    story.append(Spacer(1, 0.3*cm))

                    # ── DATOS DEL PACIENTE ────────────────────────────────────
                    sv = []
                    if rx_peso > 0:  sv.append(f"Peso: {rx_peso:.1f} kg")
                    if rx_talla > 0: sv.append(f"Talla: {rx_talla:.0f} cm")
                    if rx_imc > 0:   sv.append(f"IMC: {rx_imc:.1f}")
                    if rx_ta:        sv.append(f"TA: {rx_ta} mmHg")
                    if rx_fc:        sv.append(f"FC: {rx_fc} lpm")
                    if rx_temp:      sv.append(f"T°: {rx_temp}°C")
                    if rx_spo2:      sv.append(f"SpO₂: {rx_spo2}%")

                    sv_style = ParagraphStyle("sv", fontName="Helvetica",
                                              fontSize=8, leading=11, textColor=black)
                    pac_rows = [
                        [P("Paciente:", bold=True, fs=8), P(rx_nombre, bold=True, fs=10),
                         P("Expediente:", bold=True, fs=8), P(rx_exp, fs=9),
                         P("Fecha:", bold=True, fs=8), P(str(rx_fecha), fs=9)],
                        [P("Edad:", bold=True, fs=8), P(f"{rx_edad} años" if rx_edad else "—", fs=9),
                         P("Sexo:", bold=True, fs=8), P(rx_sexo, fs=9),
                         P("CIE-10:", bold=True, fs=8),
                         P(cie_codes or "—", fs=9, color=AZUL2, bold=True)],
                        [P("Dx:", bold=True, fs=8),
                         Paragraph(dx_str or "—",
                                   ParagraphStyle("dx2", fontName="Helvetica-Oblique",
                                                  fontSize=8, leading=11)),
                         P(""), P(""), P(""), P("")],
                    ]
                    if sv:
                        pac_rows.append([P("Signos:", bold=True, fs=8),
                                         Paragraph("  ·  ".join(sv), sv_style),
                                         P(""), P(""), P(""), P("")])

                    tp = Table(pac_rows,
                               colWidths=[2*cm, 5.5*cm, 2*cm, 2.5*cm, 1.5*cm, 3.5*cm])
                    tp.setStyle(TableStyle([
                        ("BACKGROUND",    (0,0), (-1,-1), GRISL),
                        ("ROWBACKGROUNDS",(0,0), (-1,-1), [AZULC, GRISL, white, white]),
                        ("TOPPADDING",    (0,0), (-1,-1), 4),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                        ("LEFTPADDING",   (0,0), (-1,-1), 6),
                        ("BOX",           (0,0), (-1,-1), 1,   AZULM),
                        ("SPAN",          (1,2), (-1,2)),
                    ]))
                    story.append(tp)
                    story.append(Spacer(1, 0.4*cm))

                    # ── Rx ────────────────────────────────────────────────────
                    story.append(Paragraph("&#x211E;",
                        ParagraphStyle("rxs", fontName="Helvetica-Bold",
                                       fontSize=28, textColor=AZUL2, spaceAfter=6)))
                    ind_s = ParagraphStyle("ind", fontName="Helvetica",
                                           fontSize=11, leading=18, spaceAfter=4)
                    for linea in (rx_body or "").strip().split("\n"):
                        story.append(Paragraph(linea.strip() or " ", ind_s))

                    if rx_notas:
                        story.append(Spacer(1, 0.15*cm))
                        story.append(HRFlowable(width="100%", thickness=0.5, color=AZULM))
                        story.append(Paragraph(f"Instrucciones: {rx_notas}",
                            ParagraphStyle("n", fontName="Helvetica-Oblique",
                                           fontSize=9, textColor=GRIS, spaceAfter=2)))

                    if rx_prox_fecha:
                        hora_txt = f" a las {rx_prox_hora}" if rx_prox_hora else ""
                        story.append(Spacer(1, 0.2*cm))
                        cita_b = [[P(f"📅  Próxima cita: {rx_prox_fecha}{hora_txt}",
                                     bold=True, fs=10, color=AZUL2)]]
                        tc = Table(cita_b, colWidths=[17*cm])
                        tc.setStyle(TableStyle([
                            ("BACKGROUND",   (0,0),(-1,-1), AZULC),
                            ("TOPPADDING",   (0,0),(-1,-1), 6),
                            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                            ("LEFTPADDING",  (0,0),(-1,-1), 10),
                            ("BOX",          (0,0),(-1,-1), 1, AZUL2),
                        ]))
                        story.append(tc)

                    story.append(Spacer(1, 1.0*cm))

                    # ── FIRMA ─────────────────────────────────────────────────
                    fc = ParagraphStyle("fc", fontName="Helvetica",     fontSize=9, alignment=TA_CENTER)
                    fb = ParagraphStyle("fb", fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER)
                    fg = ParagraphStyle("fg", fontName="Helvetica",     fontSize=8,
                                        textColor=GRIS, alignment=TA_CENTER)
                    firma_items = [Paragraph("_"*40, fc), Spacer(1, 0.1*cm),
                                   Paragraph(dr_nombre, fb)]
                    for c in creds:
                        firma_items.append(Paragraph(c, fg))
                    tf = Table([["", firma_items]], colWidths=[6*cm, 11*cm])
                    tf.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "BOTTOM")]))
                    story.append(tf)
                    story.append(Spacer(1, 0.3*cm))

                    # ── PIE ───────────────────────────────────────────────────
                    story.append(HRFlowable(width="100%", thickness=1, color=AZULM))
                    story.append(Paragraph(
                        f"Receta médica general · NOM-004-SSA3-2012 · COFEPRIS · "
                        f"Folio: {folio} · {dr_inst} · {dr_dom} · Tel: {dr_tel} · "
                        "RenalPro v3.1.0",
                        ParagraphStyle("pie", fontName="Helvetica", fontSize=7,
                                       textColor=GRIS, alignment=TA_CENTER)))
                    doc.build(story)
                    buf.seek(0)
                    return buf.read()

                # ── BOTONES GENERAR / GUARDAR ─────────────────────────────────
                gb1, gb2 = st.columns(2)
                with gb1:
                    if st.button("📄 Generar PDF", type="primary",
                                 use_container_width=True, key="btn_gen_rx"):
                        if not rx_nombre or not rx_body:
                            st.warning("Nombre e indicaciones son obligatorios.")
                        else:
                            # Get folio
                            folio_str = "SIN-FOLIO"
                            if uid_rx and _DB_ON and _db.db_ok():
                                try:
                                    folio_str = _db.get_next_folio(uid_rx)
                                except Exception:
                                    pass
                            try:
                                pdf = _pdf_receta(
                                    dr_nombre, dr_cedula, dr_ced_gen,
                                    dr_univ, dr_univ_gen, dr_esp,
                                    dr_inst, dr_dom, dr_tel,
                                    dr_consejo, dr_cons_num, folio_str,
                                    rx_nombre, rx_exp, rx_edad, rx_sexo,
                                    rx_peso, rx_talla, rx_imc,
                                    rx_ta, rx_fc, rx_temp, rx_spo2,
                                    dx_str, cie_codes, rx_fecha,
                                    rx_prox_fecha, rx_prox_hora,
                                    rx_body, rx_notas,
                                    logo_b64=st.session_state.get("sess_logo_b64"),
                                )
                                safe = "".join(c for c in rx_nombre
                                               if c.isalnum() or c==" ")[:18].strip()
                                st.download_button("⬇️ Descargar PDF", data=pdf,
                                    file_name=f"Rx_{folio_str}_{safe}.pdf",
                                    mime="application/pdf", key="btn_dl_rx")
                                st.success(f"✅ Folio: **{folio_str}**")
                            except Exception as e:
                                st.error(f"Error PDF: {e}")

                with gb2:
                    if pac_id_rx and uid_rx and _DB_ON and _db.db_ok():
                        if st.button("💾 Guardar en expediente",
                                     use_container_width=True, key="btn_save_rx"):
                            try:
                                _db.add_clinical_record(pac_id_rx, uid_rx, {
                                    "tipo": "Receta médica",
                                    "titulo": f"Receta — {(dx_str or rx_body[:40])}",
                                    "fecha_consulta": rx_fecha,
                                    "resumen": rx_body,
                                    "notas": rx_notas,
                                    "datos": {"dx": dx_str, "cie": cie_codes,
                                               "peso": rx_peso, "ta": rx_ta},
                                })
                                _clear_cache()
                                st.success("✅ Receta guardada en expediente.")
                            except AttributeError:
                                st.error("Sube el db.py actualizado a GitHub.")
                    elif not pac_id_rx:
                        st.caption("Selecciona o crea un paciente para guardar en expediente.")

            with rx_tab2:
                st.markdown("#### 📋 Historial de recetas")
                if uid_rx and _DB_ON and _db.db_ok():
                    try:
                        pacs_all = _cached_patients(uid_rx)
                        recetas_all = []
                        for p in pacs_all:
                            for r in _cached_clinical_records(p["id"]):
                                if r.get("tipo") == "Receta médica":
                                    recetas_all.append({**r, "_pac": p.get("nombre","—")})
                        recetas_all.sort(key=lambda x: str(x.get("created_at","")), reverse=True)

                        if recetas_all:
                            for r in recetas_all[:30]:
                                fecha_r = str(r.get("fecha_consulta",""))[:10]
                                with st.expander(
                                    f"📄 {fecha_r} — {r.get('titulo','—')} · {r['_pac']}"):
                                    st.markdown(f"**Indicaciones:**\n{r.get('resumen','')}")
                                    if r.get("notas"):
                                        st.caption(r["notas"])
                                    if st.button("↩️ Cargar indicaciones",
                                                 key=f"load_rx_{r['id']}"):
                                        st.session_state["rx_body_prefill"] = r.get("resumen","")
                                        st.info("Ve a la pestaña ✍️ y pega las indicaciones.")
                        else:
                            st.info("No hay recetas guardadas. Genera y guarda una receta para verla aquí.")
                    except Exception as e:
                        st.warning(f"Sube el db.py actualizado a GitHub para ver el historial. ({e})")
                else:
                    st.info("Conecta Railway DB para ver el historial.")

elif nav == "infecciones_tx":
    st.subheader("🦠 Infecciones Post-Trasplante Renal")
    st.caption("Ref: AST-IDCOP Guidelines 2019 | KDIGO Transplant 2009 | IDSA/EAU 2023 | ESCMID/ECMM 2022")

    # ── TIMELINE DE RIESGO ─────────────────────────────────────────────────────
    with st.expander("📅 Timeline de riesgo infeccioso post-trasplante", expanded=False):
        st.markdown("""
| Período | Infecciones predominantes | Contexto |
|---------|--------------------------|---------|
| **0–1 mes** | Infecciones quirúrgicas, bacteriemia, IVU, Candida mucocutánea, VHS recurrente | IS alta + cirugía + catéteres |
| **1–6 meses** | CMV ⭐, BKV ⭐, PCP, Listerio, Nocardia, Aspergillus, Criptococo, IVU | Período de mayor riesgo oportunista |
| **>6 meses (IS estable)** | Infecciones comunitarias (influenza, neumococo, COVID-19) | IS en descenso |
| **>6 meses (IS alta)** | Todas las del período 1–6 meses persisten | Rechazo crónico, múltiples episodios |

> ⭐ CMV y BKV son las infecciones virales más importantes en trasplante renal — requieren screening activo.
        """)

    inf_sel = st.selectbox("Selecciona la infección", [
        "🔴 CMV — Citomegalovirus",
        "🟡 BKV — Virus BK / Nefropatía BK",
        "🟢 PCP — Pneumocystis jirovecii",
        "🟣 EBV / PTLD — Post-Transplant Lymphoproliferative Disorder",
        "🔵 IVU — Infección del Tracto Urinario",
        "🟠 Infecciones Fúngicas (Candida / Aspergillus)",
        "🩸 Parvovirus B19 — Aplasia Eritroide Pura",
        "📉 Guía de reducción de IS durante infecciones",
    ], key="inf_sel")

    st.divider()

    # ── CMV ────────────────────────────────────────────────────────────────────
    if "CMV" in inf_sel:
        st.markdown("### 🔴 CMV — Citomegalovirus en Trasplante Renal")
        st.caption("AST-IDCOP CMV Guideline 2019 | KDIGO Transplant 2009 Ch. 13")

        cmv1, cmv2, cmv3, cmv4 = st.tabs([
            "📊 Estratificación de riesgo",
            "🛡️ Profilaxis",
            "🔍 Diagnóstico",
            "💊 Tratamiento",
        ])

        with cmv1:
            st.markdown("#### Estratificación por serología D/R")
            cmv_d = st.selectbox("Serología CMV del DONANTE", ["Positivo (D+)", "Negativo (D-)"], key="cmv_d")
            cmv_r = st.selectbox("Serología CMV del RECEPTOR", ["Positivo (R+)", "Negativo (R-)"], key="cmv_r")

            if "D+" in cmv_d and "R-" in cmv_r:
                st.error("""
**D+/R− → ALTO RIESGO (25–75% sin profilaxis)**
El receptor no tiene inmunidad previa — el virus del donante puede replicar libremente.
- Profilaxis obligatoria: **6 meses** con valganciclovir
- Monitoreo de carga viral durante y después de profilaxis
- Mayor riesgo de enfermedad grave y resistencia
                """)
                riesgo_cmv = "alto"
            elif "R+" in cmv_r:
                st.warning("""
**D±/R+ → RIESGO INTERMEDIO (8–20%)**
El receptor tiene inmunidad residual, pero la IS puede reactivar el virus latente.
- Profilaxis: **3 meses** con valganciclovir
- O estrategia pre-emptiva (monitoreo + tratamiento si DNAemia detectada)
                """)
                riesgo_cmv = "intermedio"
            else:
                st.success("""
**D−/R− → BAJO RIESGO (<5%)**
Ninguno tiene CMV. Riesgo solo por transfusión o nuevo contacto.
- No se recomienda profilaxis antiviral específica para CMV
- Screening solo si se expone a fuente de riesgo
                """)
                riesgo_cmv = "bajo"

        with cmv2:
            st.markdown("#### Estrategia de profilaxis universal — AST-IDCOP 2019")
            st.markdown("""
| Serología | Fármaco | Dosis | Duración |
|-----------|---------|-------|---------|
| **D+/R−** | **Valganciclovir** | 900 mg VO c/24h (ajustar por TFG) | **6 meses** |
| **R+ (cualquier D)** | **Valganciclovir** | 900 mg VO c/24h | **3 meses** |
| **D−/R−** | No indicado | — | — |

**Ajuste de dosis valganciclovir por TFG (AST-IDCOP):**
| TFG (mL/min) | Dosis profilaxis |
|-------------|-----------------|
| ≥60 | 900 mg c/24h |
| 40–59 | 450 mg c/24h |
| 25–39 | 450 mg c/48h |
| 10–24 | 450 mg c/3 días |
| <10 / diálisis | No recomendado de rutina — individualizar |

> ⚠️ **Profilaxis de baja dosis ("mini-dosis") NO recomendada** — favorece resistencia.
> Alternativa para pacientes que no toleran valganciclovir: ganciclovir IV 5 mg/kg c/24h.
            """)

            st.info("""
**Estrategia pre-emptiva** (alternativa a profilaxis universal para R+):
- Monitoreo de CMV DNAemia: c/1–2 semanas × primeros 3 meses
- Si DNAemia supera umbral institucional → iniciar tratamiento dosis plena
- Ventaja: menor toxicidad, menor gasto
- Desventaja: no protege contra efectos indirectos del CMV
            """)

        with cmv3:
            st.markdown("""
#### Diagnóstico de infección y enfermedad por CMV
| Entidad | Criterio diagnóstico |
|---------|---------------------|
| **Infección CMV** | CMV DNAemia detectable (PCR cuantitativa en plasma) |
| **Síndrome CMV** | DNAemia + fiebre, leucopenia, trombocitopenia (≥2 síntomas) |
| **Enfermedad de órgano** | Histopatología + síntomas (hepatitis, colitis, neumonitis, retinitis) |

**Biopsia de injerto renal + CMV:**
- Tinción inmunohistoquímica para CMV (si sospecha de nefritis por CMV)
- CMV puede causar nefritis intersticial del injerto — simula rechazo celular

**Resistencia a ganciclovir:**
- Sospechar si: no respuesta clínica + DNAemia persistente tras 2 semanas de tratamiento adecuado
- Mutaciones en UL97 (más frecuente) y UL54 (más rara)
- Manejo: foscarnet 60 mg/kg IV c/8h o cidofovir (nefrotóxico — evitar en TFG <55)
            """)

        with cmv4:
            st.markdown("""
#### Tratamiento de enfermedad por CMV activa — AST-IDCOP 2019
| Severidad | Fármaco | Dosis | Duración |
|-----------|---------|-------|---------|
| **Leve-moderada** | Valganciclovir VO | **900 mg c/12h** | Hasta DNAemia negativa + 1 semana (mín. 21 días) |
| **Grave / neumonitis / retinitis** | Ganciclovir IV | **5 mg/kg c/12h** → luego VGCV VO | Hasta estabilización clínica |
| **Resistente (UL97)** | Foscarnet IV | **60 mg/kg c/8h** o 90 mg/kg c/12h | 3–4 semanas |
| **Multirresistente** | Maribavir | 400 mg VO c/12h | FDA aprobado 2021 — 8 semanas |

> ⚠️ Reducir inmunosupresión durante tratamiento de CMV grave.
> Monitorear creatinina con foscarnet (nefrotóxico) y cidofovir (muy nefrotóxico).
> Control de DNAemia c/1–2 semanas durante tratamiento.
            """)
            st.caption("Ref: Kotton CN et al. AST-IDCOP CMV Guidelines. Transplantation 2019. "
                       "Maribavir (Livtencity): FDA approval 2021. Papanicolaou GA et al. NEJM 2021.")

    # ── BKV ────────────────────────────────────────────────────────────────────
    elif "BKV" in inf_sel:
        st.markdown("### 🟡 BKV — Virus BK / Nefropatía BK (BKPyVAN)")
        st.caption("Ref: Hirsch HH et al. AST-IDCOP BKV Guidelines. Transplant Infect Dis 2019.")
        st.info("""
No existe antiviral aprobado para BKV. El único tratamiento efectivo es la **reducción de inmunosupresión (IS)**.
El objetivo es restaurar la inmunidad específica anti-BKV sin precipitar un rechazo agudo.
        """)

        bk1, bk2, bk3 = st.tabs(["📊 Screening & Diagnóstico", "🔽 Reducción de IS", "📋 Protocolo"])

        with bk1:
            st.markdown("""
#### Screening obligatorio — AST-IDCOP 2019
**TODOS los receptores de trasplante renal deben ser monitoreados:**
- BKPyV DNAemia en plasma (PCR cuantitativa): **mensual × 9 meses → c/3 meses hasta 2 años**

#### Umbrales de acción
| Nivel de DNAemia | Clasificación | Acción |
|-----------------|--------------|--------|
| No detectable | Normal | Continuar screening rutinario |
| >200 copies/mL (detectable) | Viremia presuntiva | Repetir en 2–4 semanas |
| **>1,000 copies/mL × 3 semanas** o **>10,000 copies/mL** | **BKPyVAN probable / presuntiva** | **Reducir IS** |
| Biopsia: cambios histológicos | **BKPyVAN confirmada** | Reducir IS + seguimiento estrecho |

> Biopsia renal NO es obligatoria para iniciar reducción de IS si la DNAemia supera los umbrales.
> Biopsia es útil si hay duda diagnóstica (rechazo vs BKPyVAN) o sin respuesta a la reducción de IS.
            """)

        with bk2:
            st.markdown("""
#### Reducción de inmunosupresión — Esquema por pasos
| Paso | Acción | Meta DNAemia |
|------|--------|-------------|
| **1** | Reducir MMF/MPA 25–50% (o suspender si DNAemia muy alta) | >1 log de reducción en 4–6 semanas |
| **2** | Si no responde: reducir CNI (tacrolimus → nivel C0 <6 ng/mL) | Continuar descenso |
| **3** | Si falla: considerar conversión tacrolimus → ciclosporina | — |
| **4** | Si falla: mTOR inhibidor puede ser útil (sirolimus/everolimus) | Evidencia observacional |

> ⚠️ Monitorear función renal y rechazo c/2–4 semanas tras cada ajuste.
> Si aparece rechazo: reiniciar IS y aceptar nivel de BKV controlable.

**Fármacos que NO se recomiendan (AST-IDCOP 2019):**
- ❌ Ciprofloxacino/levofloxacino: sin beneficio clínico demostrado
- ❌ Cidofovir: nefrotóxico, sin eficacia clara
- ❌ Leflunomide: sin ensayos controlados sólidos
- ❌ IVIG: sin evidencia suficiente para uso rutinario
            """)

        with bk3:
            st.markdown("""
#### Protocolo de seguimiento durante BKPyVAN
```
BKPyV DNAemia >1,000 c/mL × 3 sem o >10,000 c/mL
    │
    └─ Reducir MMF 25–50%
              │
    ┌─────────┴────────────┐
    │ DNAemia <200 c/mL   │ DNAemia persiste >1000 c/mL
    │ en 4–6 sem          │ a las 4–6 sem
    │ ✅ Éxito            │ → Paso 2: reducir CNI
    │ Screening c/3 meses │
    └─────────────────────┘

Monitoreo durante reducción de IS:
- Creatinina + orina c/2 semanas
- DNAemia c/4 semanas
- Si Cr sube >20%: biopsia para descartar rechazo
- Si DNAemia negativa × 3 meses: IS puede reanudarse gradualmente
```
**Retrasplante post-BKPyVAN:**
- Posible si DNAemia negativa (independiente de nefrectomía del injerto fallido)
            """)

    # ── PCP ────────────────────────────────────────────────────────────────────
    elif "PCP" in inf_sel:
        st.markdown("### 🟢 PCP — Pneumocystis jirovecii en Trasplante Renal")
        st.caption("Ref: IDSA Guidelines PCP 2021 | KDIGO Transplant 2009 | Martin SI et al. Clin Infect Dis 2021")

        st.markdown("""
#### Profilaxis — TODOS los receptores de trasplante renal
| Fármaco | Dosis | Duración | Evidencia |
|---------|-------|---------|-----------|
| **TMP-SMX (Cotrimoxazol)** — 1ª línea | **1 tableta simple (80/400 mg) c/24h VO** | **Mínimo 3–6 meses** (muchos centros 12 meses o indefinido) | Fuerte |
| Alternativa si alergia: Dapsona | 100 mg c/24h VO | Misma duración | Moderada |
| Alternativa: Pentamidina inhalada | 300 mg c/mes nebulizada | — | Solo si oral no posible |
| Atovacuona | 1,500 mg c/24h VO | — | Alternativa oral |

> ⭐ TMP-SMX también protege contra Nocardia, Toxoplasma, Listeria e IVU — ventaja dual.
> Ajustar dosis TMP-SMX si TFG <30 mL/min (puede ser c/48h).

#### Diagnóstico de PCP activa
| Estudio | Hallazgo |
|---------|---------|
| TC de tórax | Patrón en vidrio esmerilado bilateral, peribronquial |
| BAL + PCR para P. jirovecii | Más sensible que tinción directa |
| Tinción de metenamina de plata o GMS en BAL | Gold standard si disponible |
| β-D-glucano sérico | Elevado (>80 pg/mL) — sensible pero poco específico |
| LDH sérica | Elevada — marcador de gravedad |

#### Tratamiento de PCP activa
| Severidad | Tratamiento |
|-----------|------------|
| **Leve-moderada** (PaO2 >70 mmHg) | TMP-SMX 15–20 mg/kg/día (componente TMP) VO dividido c/8h × **21 días** |
| **Grave** (PaO2 <70 mmHg) | TMP-SMX IV misma dosis × 21 días + **prednisona 40 mg c/12h × 5 días → taper** |
| Intolerancia a TMP-SMX | Pentamidina IV 4 mg/kg/día o Atovacuona VO 750 mg c/12h |

> ⚠️ Reducir inmunosupresión durante el episodio de PCP activa.
> Monitorear K, glucosa, función renal con TMP-SMX IV a dosis plena.
        """)

    # ── EBV / PTLD ─────────────────────────────────────────────────────────────
    elif "EBV" in inf_sel:
        st.markdown("### 🟣 EBV / PTLD — Desorden Linfoproliferativo Post-Trasplante")
        st.caption("Ref: AST-IDCOP EBV/PTLD Guidelines 2019 | EBMT/EHA 2021 | Swerdlow SH et al. WHO Classification 2022")

        st.markdown("""
#### Factores de riesgo y screening
| Factor de riesgo | Implicación |
|-----------------|-------------|
| **D+/R− (EBV)** | Mayor riesgo de PTLD (10–15× vs D+/R+) |
| IS intensa (timoglobulina, múltiples pulsos) | Riesgo aumentado |
| Trasplante en niños/adolescentes | EBV primario frecuente |
| Edad avanzada del receptor | Riesgo de PTLD tardío |

**Screening de EBV DNA (en plasma):** Mensual × 3–6 meses, luego c/3 meses hasta 1 año (especialmente D+/R−).

#### Diagnóstico y clasificación PTLD (WHO 2022)
| Categoría | Histología | Manejo |
|-----------|-----------|--------|
| Hiperplasia plasmacelular/mononucleosis | Benigna, EBV+ | Reducción IS |
| PTLD polimórfico | Células B polimorfas EBV+ | Reducción IS + rituximab |
| PTLD monomórfico (DLBCL-like) | CD20+ EBV+/- | Rituximab ± quimioterapia |
| Linfoma de Hodgkin post-Tx | Células de Reed-Sternberg | Quimioterapia clásica |

#### Algoritmo de manejo
```
EBV DNAemia elevada (sin masa)
    │
    ├─ Reducir IS (primer paso siempre)
    │    │
    │    └─ Si DNAemia desciende: continuar monitoring
    │
    └─ Si masa / síntomas → Biopsia (PET-TC para estadificación)
              │
              ├─ CD20+: Rituximab 375 mg/m² × 4 ciclos
              │    │
              │    └─ Respuesta parcial o agresivo: R-CHOP u otro esquema
              │
              └─ CD20−: Quimioterapia según histología
```

> ⚠️ Biopsia es indispensable para clasificar el PTLD — el manejo difiere radicalmente por subtipo.
> Rituximab solo sin quimioterapia es adecuado para PTLD polimórfico CD20+, no para monomórfico agresivo.
        """)

    # ── IVU ────────────────────────────────────────────────────────────────────
    elif "IVU" in inf_sel:
        st.markdown("### 🔵 IVU — Infección del Tracto Urinario Post-Trasplante Renal")
        st.caption("Ref: IDSA/EAU UTI Guidelines 2023 | AST-IDCOP UTI Guidelines 2019")
        st.info("IVU es la infección bacteriana más frecuente en KT (20–80% en el primer año). "
                "El uréter del injerto y la vejiga son sitios de riesgo particular.")

        st.markdown("""
#### Clasificación y manejo por categoría

| Categoría | Definición | Manejo |
|-----------|-----------|--------|
| **Bacteriuria asintomática** | Urocultivo+ sin síntomas | **Tratar SOLO en los primeros 2 meses post-Tx** · Después: NO tratar |
| **Cistitis** | Disuria, urgencia, frecuencia + urocultivo+ | Antibiótico 7–14 días según antibiograma |
| **Pielonefritis del injerto** | Fiebre + dolor en injerto + urocultivo+ | ATB IV × 14 días + imágenes del injerto |
| **Urosepsis** | Bacteriemia + origen urinario | ATB IV + UCI si sepsis grave |

> ⚠️ En KT, la pielonefritis del injerto puede ser silenciosa (sin dolor lumbar clásico) —
> el injerto está denervado. Fiebre sola + urocultivo+ es suficiente para diagnóstico.

#### Profilaxis
- **TMP-SMX** (ya cubre PCP + IVU): 1 tab simple c/24h × 3–6 meses
- Si alergia: cefalexina 250–500 mg c/24h o nitrofurantoína (evitar con TFG <30)

#### Patógenos más frecuentes en KT
| Patógeno | Frecuencia | Preocupación |
|---------|-----------|-------------|
| E. coli | ~50% | BLEE frecuente — solicitar antibiograma siempre |
| Klebsiella pneumoniae | ~15% | Productora de carbapenemasas en centros terciarios |
| Enterococcus faecalis | ~10% | Resistencia a ampicilina creciente |
| Pseudomonas aeruginosa | ~5% | KT con estructura urológica compleja |
| Candida sp. | Raro | Inmunosupresión intensa |

#### Estudio de IVU recurrente en KT
- Urocultivos seriados con antibiograma
- Ecografía del injerto (hidronefrosis, litiasis, colección)
- Cistoscopía si obstrucción del uréter
- Descontinuar catéter urinario lo antes posible (factor de riesgo mayor)
        """)

    elif "Parvovirus" in inf_sel:
        st.markdown("### 🩸 Parvovirus B19 — Aplasia Eritroide Pura Post-Trasplante")
        st.caption("Ref: Waldman M et al. Clin J Am Soc Nephrol 2007 | "
                   "Mascaretti L et al. Transplant Proc 2010 | AST-IDCOP 2019")
        st.info("""
**Parvovirus B19** infecta y destruye los precursores eritroides en médula ósea.
En inmunocompetentes causa eritema infeccioso autolimitado. En trasplantados (IS) → 
**aplasia eritroide pura crónica**: anemia severa progresiva con reticulocitopenia.
        """)
        st.markdown("""
#### Presentación clínica en trasplante renal
| Hallazgo | Descripción |
|---------|------------|
| **Anemia severa** | Hb 5–8 g/dL, de instalación progresiva (semanas-meses) |
| **Reticulocitopenia** | Reticulocitos <0.5% — clave diagnóstica (médula no produce) |
| **Sin causa aparente** | Se descarta pérdida, hemólisis, déficit de hierro, B12, EPO |
| **Leucocitos/plaquetas normales** | La afectación es exclusiva de la serie roja |
| **Cronología** | Habitualmente 3–12 meses post-trasplante |

#### Diagnóstico
| Estudio | Hallazgo esperado | Umbral de significancia |
|---------|-------------------|------------------------|
| **PCR Parvovirus B19 en sangre** | Positivo — carga viral alta | >10⁴ copias/mL = significativo |
| **Anticuerpos IgM anti-B19** | Pueden ser negativos en IS severa | No descartan si PCR + |
| **Anticuerpos IgG anti-B19** | Pueden estar ausentes (sin seroconversión) | — |
| **BH con reticulocitos** | Reticulocitopenia + anemia normocítica | Ret <0.5% orientativo |
| **Biopsia de médula** (si PCR neg y anemia severa) | Ausencia de precursores eritroides, inclusiones intranucleares | Confirma aplasia |

> 📌 En trasplantados IS, la respuesta serológica puede ser negativa aunque hay viremia alta.
> **La PCR cuantitativa en plasma es el gold standard diagnóstico.**

#### Tratamiento
| Intervención | Dosis / Detalles | Evidencia |
|-------------|-----------------|-----------|
| **IVIG** (1ª línea) | **0.4 g/kg/día × 5 días** (total: 2 g/kg) IV | Series de casos — evidencia moderada |
| **IVIG ciclo 2** | Si no responde: repetir en 4 semanas | Muchos responden al 2° ciclo |
| **Reducción de IS** | Reducir MMF 25–50% · Mantener CNI si función renal estable | Esencial para responder a IVIG |
| **Transfusión** | Si Hb <7 g/dL o sintomática | Soporte temporal |
| **No existen antivirales efectivos** | Cidofovir y otros — sin evidencia clara | — |

#### Protocolo de seguimiento post-IVIG
```
Semana 1–2: PCR B19 en sangre + reticulocitos
✅ Respuesta: reticulocitos >1% + subida de Hb ≥1 g/dL/semana → continuar reducción IS gradual
⚠️ No respuesta: segundo ciclo IVIG + considerar mayor reducción IS o conversión
❌ Recurrencia: frecuente si IS se reintensifica → ciclos repetidos de IVIG
```

> ⚠️ **Riesgo de recurrencia:** el B19 puede persistir latente y reactivar si la IS aumenta
> (rechazo tratado con timoglobulina, pulsos de esteroides). Monitorizar Hb tras episodios de IS intensa.
        """)
        st.caption("Ref: Waldman M et al. B19 in transplantation. Clin J Am Soc Nephrol 2007. "
                   "Young NS et al. NEJM 2004.")

    elif "reducción de IS" in inf_sel or "Guía" in inf_sel:
        st.markdown("### 📉 Guía de reducción de IS durante infecciones post-trasplante")
        st.caption("Ref: AST-IDCOP Guidelines 2019 | KDIGO Transplant 2009 | Fishman JA. NEJM 2007")
        st.warning("""
⚠️ **Principio fundamental:** Existe tensión permanente entre tratar la infección
(reducir IS) y proteger el injerto (mantener IS). No hay reglas absolutas — la decisión
debe individualizarse según gravedad de la infección, función del injerto, tiempo post-trasplante
y nivel de IS actual.
        """)
        st.markdown("""
#### Escala de reducción de IS según gravedad de la infección
| Gravedad | Definición | Acción IS recomendada |
|---------|-----------|----------------------|
| **Leve** | Sin hospitalización, buen estado general | Continuar IS habitual · ajuste mínimo |
| **Moderada** | Hospitalización, responde a ATB/antiviral | Reducir MMF 25–50% · Mantener CNI y esteroides |
| **Grave** | UCI, fallo orgánico, infección diseminada | Suspender MMF · Reducir CNI 50% · Mantener esteroides (evitar insuficiencia adrenal) |
| **Amenazante de vida** | Sepsis severa, encefalitis, neumonía grave | Suspender MMF y CNI · Mantener sólo hidrocortisona IV |

#### Por tipo de inmunosupresor — jerarquía de reducción
| Fármaco | Primero en reducir | Razón |
|---------|-------------------|-------|
| **MMF / Micofenolato** | ✅ Siempre primero | Acción anti-proliferativa — reduce respuesta anti-infecciosa |
| **CNI (Tacrolimus / CsA)** | ✅ Segundo | Mantener si función renal lo permite |
| **mTOR (Everolimus)** | ✅ Reducir pronto | Inhibe respuesta inmune celular anti-viral |
| **Esteroides** | ❌ Último en reducir | Riesgo de insuficiencia adrenal aguda — bajar gradualmente |
| **Azatioprina** | ✅ Suspender en infecciones graves | Menor uso hoy en día |

#### Recomendaciones específicas por patógeno
| Infección | IS recomendada durante tratamiento |
|----------|----------------------------------|
| **CMV activo** | Reducir MMF 25–50% · Mantener CNI en niveles bajos (C0 6–8) |
| **BKV >1,000 c/mL** | Reducir MMF 25–50% primero → luego CNI si persiste |
| **PCP grave** | Suspender MMF · Reducir CNI · Mantener esteroides + agregar prednisona para PCP |
| **EBV / PTLD** | Reducir IS al mínimo · Rituximab según histología |
| **Parvovirus B19** | Reducir MMF 25–50% para mejorar respuesta a IVIG |
| **IVU grave (pielonefritis)** | Mantener IS · Solo ajustar si no responde a ATB en 72h |
| **Aspergillus invasivo** | Reducir MMF · Mantener CNI (voriconazol ↑ niveles tacrolimus — monitorear) |
| **Candida sistémica** | Reducir o suspender MMF · Mantener CNI con monitoreo |
| **Sepsis bacteriana grave** | Suspender MMF · Reducir CNI · Solo hidrocortisona |

#### Cuándo reintroducir IS tras control de la infección
```
Criterios para retomar IS a dosis objetivo:
✅ Documentación microbiológica de resolución (cultivos negativos, carga viral indetectable)
✅ Afebril ≥48–72h + normalización de parámetros inflamatorios
✅ Función del injerto estable
✅ Fin del tratamiento antimicrobiano activo

Retomar en pasos graduales (no de golpe):
• Semana 1 post-resolución: MMF al 50% de la dosis objetivo
• Semana 2–3: MMF al 75%
• Semana 4: dosis objetivo (con monitoreo de DSA y función)
```

> 📌 Si durante la reducción de IS aparecen signos de rechazo → biopsia antes de reinstaurar.
> La prioridad en los primeros 3 meses post-Tx es la función del injerto;
> después de 1 año, el riesgo de rechazo disminuye y la reducción de IS es más segura.
        """)
        st.caption("Ref: Fishman JA. Infection in Solid-Organ Transplant Recipients. NEJM 2007;357:2601. "
                   "AST-IDCOP Guidelines. Transplantation 2019.")


    # ── FÚNGICAS ───────────────────────────────────────────────────────────────
    else:
        st.markdown("### 🟠 Infecciones Fúngicas Post-Trasplante")
        st.caption("Ref: ESCMID/ECMM Candida Guidelines 2023 | IDSA Aspergillus Guidelines 2016 (update 2020)")

        fun1, fun2 = st.tabs(["🍄 Candida", "🫁 Aspergillus / Mohos"])

        with fun1:
            st.markdown("""
#### Candida en trasplante renal
**Presentaciones clínicas:**
- Candiduria (más frecuente): catéter urinario, IS intensa, ATB de amplio espectro
- Candidiasis esofágica / mucocutánea
- Candidemia (menos frecuente pero grave)

#### Candiduria — Manejo (ESCMID 2023)
| Escenario | Tratamiento |
|-----------|------------|
| Asintomática, sin catéter urinario | **No tratar** (retirar catéter si es posible) |
| Asintomática + catéter | Retirar catéter y repetir urocultivo |
| **Sintomática** (cistitis) | Fluconazol 200 mg/día VO × 14 días |
| **Pielonefritis** del injerto por Candida | Fluconazol 400 mg/día × 14 días o equinocandina IV × 14 días |
| **C. glabrata** (fluconazol resistente) | Anidulafungina o caspofungina IV |

**Profilaxis antifúngica:** Fluconazol 100–200 mg/día VO × 1–3 meses (especialmente post-timoglobulina o en centros de alto riesgo).

#### Candidemia — protocolo urgente
1. Hemocultivos × 2 + fungemias
2. Fondo de ojo (descartar retinitis)
3. Ecocardiograma transtorácico
4. Tratamiento: Equinocandina IV (micafungina 150 mg c/24h o anidulafungina 200 mg → 100 mg)
5. Duración: 14 días desde último hemocultivo negativo + resolución de síntomas
6. Step-down a fluconazol VO si sensible y estabilidad clínica
            """)

        with fun2:
            st.markdown("""
#### Aspergilosis invasiva (AI) en trasplante renal
**Factores de riesgo:**
- Inducción con timoglobulina
- Rechazo con pulsos de esteroides
- Colonización bronquial previa
- Construcción/renovación hospitalaria (esporas ambientales)
- Falla renal post-trasplante + HD o IS intensa

#### Diagnóstico de AI
| Estudio | Hallazgo |
|---------|---------|
| TC tórax (HRCT) | Nódulos con halo, consolidaciones, signo del aire creciente |
| Galactomanano sérico | ≥0.5 índice (2 muestras) — sensibilidad 60–70% en SOT |
| Galactomanano en BAL | ≥1.0 índice — más sensible |
| Beta-D-glucano | Inespecífico — apoya el diagnóstico |
| Cultivo + PCR BAL | Confirma especie y sensibilidad |

#### Tratamiento — IDSA 2020
| Escenario | Fármaco | Dosis | Duración |
|-----------|---------|-------|---------|
| **1ª línea** | **Voriconazol VO/IV** | 6 mg/kg c/12h × 2 dosis → 4 mg/kg c/12h IV, luego 200 mg c/12h VO | Mínimo 6–12 semanas |
| **Alternativa** | Isavuconazol | 200 mg c/8h × 6 dosis → 200 mg c/24h | Igual que voriconazol |
| **Refractario** | Liposomal anfotericina B | 3–5 mg/kg c/24h IV | Según respuesta |

> ⚠️ **Interacción voriconazol + tacrolimus:** voriconazol inhibe fuertemente CYP3A4.
> Al iniciar voriconazol: reducir tacrolimus 25–33% y monitorear nivel C0 a las 24–48h.
> Isavuconazol tiene menor inhibición de CYP3A4 — preferible si tacrolimus es crítico.
            """)
            st.caption("Ref: Pappas PG et al. IDSA Candida Guidelines. Clin Infect Dis 2016. "
                       "Patterson TF et al. IDSA Aspergillus Guidelines. Clin Infect Dis 2016. "
                       "Tissot F et al. ESCMID/ECMM Aspergillus. Clin Microbiol Infect 2020.")


elif nav == "inmuno_tx":
    st.subheader("🧬 Inmunología del Trasplante Renal")
    st.caption("Ref: OPTN/UNOS Policy 2023 | Delmonico FL, Dew MA. Am J Transplant 2007 | "
               "Leffell MS et al. Transplantation 2007 | Tambur AR et al. Am J Transplant 2015")

    im_tab = st.radio("Módulo", [
        "📚 HLA — Conceptos fundamentales",
        "🧮 Calculadora cPRA",
        "🔀 Calculadora de Mismatches HLA",
        "📊 Interpretador DSA / Luminex",
        "🔬 Crossmatch — tipos e interpretación",
        "⚠️ Estratificación de riesgo inmunológico",
    ], horizontal=True, key="im_tab")

    st.divider()

    # ── HLA CONCEPTOS ──────────────────────────────────────────────────────────
    if "HLA" in im_tab:
        st.markdown("### 📚 Sistema HLA — Conceptos fundamentales")

        hla1, hla2, hla3 = st.tabs(["🔬 Estructura HLA", "🔗 Sensibilización", "📋 Terminología clave"])

        with hla1:
            st.markdown("""
#### Sistema HLA — Complejo Mayor de Histocompatibilidad (MHC)
Los antígenos HLA son proteínas de superficie que el sistema inmune usa para distinguir "propio" de "extraño".
En trasplante, las diferencias HLA entre donante y receptor desencadenan la respuesta de rechazo.

**Clases de HLA relevantes en trasplante renal:**

| Clase | Loci principales | Expresión | Importancia en Tx |
|-------|-----------------|-----------|-------------------|
| **Clase I** | HLA-A, HLA-B, HLA-C | Todas las células nucleadas | Anticuerpos anti-clase I preceden rechazo humoral agudo |
| **Clase II** | HLA-DR, HLA-DQ, HLA-DP | Células presentadoras de Ag | Anti-DQ de novo = causa más frecuente de rechazo crónico activo |

**¿Por qué DQ es tan importante?**
- Anti-DQ de novo son los DSA más frecuentes post-trasplante
- Están fuertemente asociados a pérdida crónica del injerto
- Muchos centros los monitorizan específicamente aunque no se usen como criterio de exclusión inicial

#### HLA Mismatches — ¿cuáles importan más?
| Mismatch | Impacto relativo | Nota clínica |
|---------|-----------------|-------------|
| DR + DQ | ⭐⭐⭐ Mayor impacto | Mejor compatibilizar DR y DQ — definen la respuesta CD4+ |
| B | ⭐⭐ Impacto moderado | Importante en trasplante pediátrico |
| A | ⭐ Menor impacto | Relevante en hipersensibilizados |
| C / DP | Menor evidencia directa | Se incluyen en cPRA pero no en asignación clásica |

> 📌 Máximo 6 mismatches posibles (2 por locus A, B, DR).
> "0 mismatch" = trasplante idéntico en A+B+DR → mejor sobrevida del injerto a largo plazo.
            """)

        with hla2:
            st.markdown("""
#### Sensibilización — Causas y mecanismo
El sistema inmune forma anticuerpos anti-HLA cuando es expuesto a HLA extraño:

| Causa | Mecanismo | Importancia |
|-------|-----------|------------|
| **Embarazo** | Exposición al HLA paterno del feto | Principal causa en mujeres — hasta 30% después de 1 embarazo |
| **Transfusiones** | HLA de leucocitos en la sangre | 5–15% de sensibilización por evento |
| **Trasplante previo** | Respuesta al injerto del donante | 30–90% dependiendo del rechazo |
| **Infección (raro)** | Mimetismo molecular | Poco documentado |

#### Tipos de anticuerpos anti-HLA
| Tipo | Definición | Riesgo |
|------|-----------|--------|
| **DSA preformados** | Contra antígenos HLA específicos del donante — presentes ANTES del Tx | Contraindicación relativa / crossmatch positivo |
| **DSA de novo** | Aparecen DESPUÉS del Tx | Marcador de rechazo humoral crónico |
| **No-DSA** | Contra HLA que el donante no tiene | No directamente dañinos al injerto actual |

> ⚠️ Los DSA de novo anti-DQ son los más frecuentes y más asociados a pérdida crónica del injerto.
> Muchos centros monitorizan DSA a 1, 3, 6, 12 meses y anualmente.
            """)

        with hla3:
            st.markdown("""
#### Glosario de términos en inmunología del trasplante

| Término | Definición clínica |
|---------|-------------------|
| **PRA** *(Panel Reactive Antibody)* | % histórico de reactividad contra un panel de células de donantes — método antiguo, variable entre laboratorios |
| **cPRA** *(calculated PRA)* | Cálculo estandarizado (OPTN): % de donantes potenciales con los que el receptor sería incompatible, basado en sus anticuerpos anti-HLA identificados |
| **DSA** *(Donor-Specific Antibodies)* | Anticuerpos contra antígenos HLA específicos del donante actual o potencial |
| **MFI** *(Mean Fluorescence Intensity)* | Intensidad de señal en Luminex — cuantifica la cantidad de anticuerpo anti-HLA |
| **SAB** *(Single Antigen Beads)* | Panel de Luminex con un HLA por bead — permite identificar especificidades exactas de anticuerpos |
| **Crossmatch CDC** | Prueba con suero del receptor + células del donante + complemento — positivo si hay lisis celular |
| **FCXM** *(Flow Cytometry XM)* | Más sensible que CDC — detecta anticuerpos no citotóxicos |
| **Virtual Crossmatch** | Comparar anticuerpos del receptor (SAB) vs tipificación HLA del donante — sin células del donante |
| **Desensibilización** | Protocolo para reducir anticuerpos anti-HLA pre-trasplante (IVIG, rituximab, plasmaféresis) |
| **Epitopo** | Región específica del HLA reconocida por el anticuerpo — base de la compatibilidad epítopo |
| **MICA** | MHC class I chain-related protein A — antígeno no-HLA asociado a rechazo |
            """)

    # ── CALCULADORA cPRA ────────────────────────────────────────────────────────
    elif "cPRA" in im_tab:
        st.markdown("### 🧮 Calculadora cPRA")
        st.info("""
**cPRA = % de donantes potenciales incompatibles con este receptor.**
Se calcula con la fórmula OPTN: **cPRA = 1 − ∏(1 − f_i)**
donde f_i = frecuencia del antígeno i en el pool de donantes (ponderada por etnia).

Las frecuencias usadas son aproximaciones de la tabla de referencia OPTN/NMDP para población Hispana/Latinoamericana.
        """)

        # HLA antigen frequencies (Hispanic/Latino - OPTN reference approximations)
        HLA_FREQ = {
            # HLA-A
            "A1":0.130, "A2":0.280, "A3":0.100, "A11":0.040, "A23":0.040,
            "A24":0.130, "A25":0.020, "A26":0.030, "A28":0.040, "A29":0.020,
            "A30":0.040, "A31":0.040, "A32":0.020, "A33":0.030, "A34":0.010,
            "A36":0.010, "A43":0.005, "A66":0.010, "A68":0.050, "A69":0.010,
            "A74":0.020, "A80":0.010,
            # HLA-B
            "B7":0.090, "B8":0.060, "B13":0.030, "B14":0.040, "B15":0.060,
            "B18":0.070, "B27":0.030, "B35":0.130, "B38":0.020, "B39":0.050,
            "B40":0.050, "B41":0.010, "B42":0.020, "B44":0.080, "B45":0.010,
            "B47":0.010, "B48":0.020, "B49":0.020, "B50":0.020, "B51":0.070,
            "B52":0.020, "B53":0.030, "B54":0.010, "B55":0.020, "B56":0.010,
            "B57":0.030, "B58":0.030, "B60":0.030, "B61":0.030, "B62":0.040,
            "B63":0.010, "B65":0.010, "B67":0.010, "B71":0.010, "B72":0.010,
            "B73":0.010, "B75":0.010, "B76":0.010, "B77":0.010,
            # HLA-C (Cw)
            "Cw1":0.040, "Cw2":0.080, "Cw3":0.150, "Cw4":0.130, "Cw5":0.090,
            "Cw6":0.100, "Cw7":0.280, "Cw8":0.060, "Cw9":0.050, "Cw10":0.070,
            "Cw12":0.050, "Cw14":0.040, "Cw15":0.060, "Cw16":0.040, "Cw17":0.020,
            "Cw18":0.010,
            # HLA-DR
            "DR1":0.070, "DR2":0.080, "DR3":0.090, "DR4":0.150, "DR5":0.090,
            "DR6":0.100, "DR7":0.130, "DR8":0.050, "DR9":0.020, "DR10":0.020,
            "DR11":0.110, "DR12":0.020, "DR13":0.100, "DR14":0.060, "DR15":0.080,
            "DR16":0.020, "DR17":0.060, "DR18":0.020,
            # HLA-DQ
            "DQ1":0.250, "DQ2":0.180, "DQ3":0.220, "DQ4":0.050, "DQ5":0.180,
            "DQ6":0.140, "DQ7":0.150, "DQ8":0.120, "DQ9":0.080,
        }

        st.markdown("#### Ingresa los anticuerpos anti-HLA del receptor (antígenos inaceptables)")
        st.caption("Selecciona los HLA contra los que el receptor tiene anticuerpos identificados por Luminex SAB.")

        col_a, col_b, col_c, col_dr, col_dq = st.columns(5)
        with col_a:
            st.markdown("**HLA-A**")
            ags_a = st.multiselect("A", [k for k in HLA_FREQ if k.startswith("A") and not k.startswith("A0")],
                                   key="cpra_a", label_visibility="collapsed")
        with col_b:
            st.markdown("**HLA-B**")
            ags_b = st.multiselect("B", [k for k in HLA_FREQ if k.startswith("B")],
                                   key="cpra_b", label_visibility="collapsed")
        with col_c:
            st.markdown("**HLA-C (Cw)**")
            ags_c = st.multiselect("Cw", [k for k in HLA_FREQ if k.startswith("Cw")],
                                   key="cpra_c", label_visibility="collapsed")
        with col_dr:
            st.markdown("**HLA-DR**")
            ags_dr = st.multiselect("DR", [k for k in HLA_FREQ if k.startswith("DR")],
                                    key="cpra_dr", label_visibility="collapsed")
        with col_dq:
            st.markdown("**HLA-DQ**")
            ags_dq = st.multiselect("DQ", [k for k in HLA_FREQ if k.startswith("DQ")],
                                    key="cpra_dq", label_visibility="collapsed")

        todos_ags = ags_a + ags_b + ags_c + ags_dr + ags_dq

        if todos_ags:
            # cPRA calculation: 1 - product(1 - freq_i)
            prod = 1.0
            for ag in todos_ags:
                freq = HLA_FREQ.get(ag, 0.01)
                prod *= (1 - freq)
            cpra_val = (1 - prod) * 100

            cr1, cr2, cr3 = st.columns(3)
            cr1.metric("Antígenos inaceptables", len(todos_ags))
            cr2.metric("cPRA calculado", f"{cpra_val:.1f}%")

            if cpra_val < 30:
                cr3.metric("Riesgo inmunológico", "BAJO")
                st.success(f"**cPRA {cpra_val:.1f}%** — Bajo riesgo inmunológico. Buenas perspectivas de encontrar donante compatible.")
            elif cpra_val < 80:
                cr3.metric("Riesgo inmunológico", "MODERADO")
                st.warning(f"**cPRA {cpra_val:.1f}%** — Riesgo moderado. Tiempo de espera aumentado.")
            elif cpra_val < 99:
                cr3.metric("Riesgo inmunológico", "ALTO")
                st.error(f"**cPRA {cpra_val:.1f}%** — Altamente sensibilizado. Dificultad significativa para encontrar donante compatible. Considerar desensibilización.")
            else:
                cr3.metric("Riesgo inmunológico", "MUY ALTO")
                st.error(f"**cPRA {cpra_val:.1f}%** — Hipersensibilizado. Candidato prioritario en lista de espera (OPTN). Protocolo de desensibilización obligatorio.")

            st.markdown("**Antígenos seleccionados y su frecuencia en pool hispano:**")
            freq_data = [(ag, HLA_FREQ.get(ag, 0.01), f"{HLA_FREQ.get(ag,0.01)*100:.1f}%")
                         for ag in sorted(todos_ags)]
            import pandas as pd
            df_freq = pd.DataFrame(freq_data, columns=["Antígeno", "Frecuencia", "% pool"])
            st.dataframe(df_freq, use_container_width=True, hide_index=True)

            st.caption("""
⚠️ Este cálculo usa frecuencias aproximadas para población Hispana/Latinoamericana basadas en la tabla OPTN/NMDP.
El cPRA oficial para asignación de órganos se calcula en el sistema UNOS/OPTN o el equivalente institucional.
Este módulo es de uso educativo y orientativo para el fellow de trasplante.
Ref: OPTN Policy 2023 | Leffell MS et al. Transplantation 2007.
            """)
        else:
            st.info("Selecciona al menos un antígeno inaceptable para calcular el cPRA.")
            st.markdown("""
**Referencia rápida de estratificación cPRA:**
| cPRA | Clasificación | Implicación |
|------|--------------|------------|
| 0% | No sensibilizado | Sin restricciones para donante |
| 1–79% | Sensibilizado | Tiempo de espera variable |
| 80–98% | Altamente sensibilizado | Acceso reducido a donantes compatibles |
| ≥99% | Hipersensibilizado | Prioridad en lista OPTN · Candidato a desensibilización |
            """)

    # ── CALCULADORA DE MISMATCHES HLA ──────────────────────────────────────────
    elif "Mismatches" in im_tab:
        st.markdown("### 🔀 Calculadora de Mismatches HLA")

        st.info("""
**¿Qué es un mismatch HLA?**
Cuando el donante tiene un antígeno HLA que el receptor **no tiene** — el sistema inmune del receptor
lo reconoce como "extraño" y puede generar anticuerpos contra él (DSA) o activar linfocitos T en su contra.

**Máximo 6 mismatches posibles** (2 por locus × 3 loci: A + B + DR).
**0 mismatches** = trasplante HLA idéntico → mejor sobrevida del injerto a largo plazo.

> 📌 La compatibilidad de **DR** es la más importante — determina la respuesta CD4+.
> Los mismatches de DR+DQ juntos predicen mejor el riesgo de rechazo crónico.
        """)

        st.markdown("#### Ingresa la tipificación HLA del Donante y el Receptor")
        st.caption("Usa los alelos serológicos (ej: A2, B35, DR4). Si solo conoces uno de los dos alelos, deja el segundo en blanco.")

        mm1, mm2, mm3 = st.columns(3)
        loci_config = {
            "A": ("HLA-A", mm1),
            "B": ("HLA-B", mm2),
            "DR": ("HLA-DR", mm3),
        }

        donante_hla = {}
        receptor_hla = {}

        for locus, (label, col) in loci_config.items():
            with col:
                st.markdown(f"**{label}**")
                st.markdown("*Donante:*")
                d1 = st.text_input(f"D-{locus}-1", placeholder=f"Ej: {locus}2", key=f"d_{locus}_1").strip().upper()
                d2 = st.text_input(f"D-{locus}-2", placeholder="Opcional", key=f"d_{locus}_2").strip().upper()
                st.markdown("*Receptor:*")
                r1 = st.text_input(f"R-{locus}-1", placeholder=f"Ej: {locus}2", key=f"r_{locus}_1").strip().upper()
                r2 = st.text_input(f"R-{locus}-2", placeholder="Opcional", key=f"r_{locus}_2").strip().upper()
                donante_hla[locus]  = {a for a in [d1, d2] if a}
                receptor_hla[locus] = {a for a in [r1, r2] if a}

        # Calculate mismatches
        if any(donante_hla[l] for l in ["A", "B", "DR"]):
            st.divider()
            total_mm = 0
            mm_details = []

            for locus in ["A", "B", "DR"]:
                donor_set    = donante_hla[locus]
                receptor_set = receptor_hla[locus]
                # Mismatches = donor antigens not present in recipient
                mismatched = donor_set - receptor_set
                locus_mm   = len(mismatched)
                total_mm  += locus_mm
                mm_details.append({
                    "Locus": f"HLA-{locus}",
                    "Donante": " / ".join(sorted(donor_set)) if donor_set else "—",
                    "Receptor": " / ".join(sorted(receptor_set)) if receptor_set else "—",
                    "Ag. mismatch": " / ".join(sorted(mismatched)) if mismatched else "✅ Compatible",
                    "Mismatches": locus_mm,
                })

            # Display results
            rm1, rm2, rm3 = st.columns(3)
            rm1.metric("Total Mismatches", f"{total_mm} / 6")
            if total_mm == 0:
                rm2.metric("Compatibilidad", "Excelente")
                rm3.metric("Riesgo relativo", "Mínimo")
                st.success("**0 Mismatches — Trasplante HLA idéntico o casi idéntico.** "
                           "Mejor pronóstico a largo plazo.")
            elif total_mm <= 2:
                rm2.metric("Compatibilidad", "Buena")
                rm3.metric("Riesgo relativo", "Bajo")
                st.success(f"**{total_mm} Mismatch(es) — Buena compatibilidad.** "
                           "Riesgo bajo de rechazo crónico.")
            elif total_mm <= 4:
                rm2.metric("Compatibilidad", "Moderada")
                rm3.metric("Riesgo relativo", "Moderado")
                st.warning(f"**{total_mm} Mismatches — Compatibilidad moderada.** "
                           "Monitoreo estrecho de DSA post-trasplante recomendado.")
            else:
                rm2.metric("Compatibilidad", "Baja")
                rm3.metric("Riesgo relativo", "Alto")
                st.error(f"**{total_mm} Mismatches — Alta incompatibilidad HLA.** "
                         "Mayor riesgo de rechazo crónico y pérdida del injerto a largo plazo. "
                         "IS más intensa y monitoreo de DSA obligatorio.")

            # Detail table
            import pandas as pd
            df_mm = pd.DataFrame(mm_details)
            st.dataframe(df_mm, use_container_width=True, hide_index=True)

            # Impact table
            st.markdown("#### Impacto clínico de los mismatches DR")
            dr_mm = mm_details[2]["Mismatches"]
            if dr_mm == 0:
                st.success("✅ Sin mismatches DR — menor riesgo de rechazo crónico mediado por anticuerpos.")
            elif dr_mm == 1:
                st.warning("⚠️ 1 mismatch DR — riesgo moderado. Monitoreo DSA a 1, 3, 6, 12 meses.")
            else:
                st.error("🔴 2 mismatches DR — alto riesgo de DSA de novo anti-DR y anti-DQ. "
                         "Monitoreo estricto y biopsia de protocolo recomendada.")

            st.caption("""
**¿Cómo se calculan?** Un mismatch ocurre cuando el donante tiene un antígeno HLA
que el receptor no tiene. Cada locus tiene hasta 2 alelos → máximo 2 mismatches por locus.
No se cuenta si el receptor ya tiene ese antígeno (aunque el donante también lo tenga).

Ref: Meier-Kriesche HU et al. Am J Transplant 2004 | OPTN Policy 2023
            """)

    # ── DSA / MFI INTERPRETER ──────────────────────────────────────────────────
    elif "DSA" in im_tab:
        st.markdown("### 📊 Interpretador DSA / Luminex (Single Antigen Beads)")
        st.caption("Ref: Tambur AR et al. Am J Transplant 2015 | ASHI Standards 2022 | Tait BD et al. Transplantation 2013")

        st.info("""
**Luminex SAB (Single Antigen Beads):** Cada bead contiene un solo antígeno HLA.
El suero del paciente se incuba con las beads y el MFI indica cuánto anticuerpo hay contra ese HLA específico.
**MFI alto ≠ siempre daño clínico** — el contexto clínico es fundamental para interpretar.
        """)

        st.markdown("#### Ingresa los DSA identificados y sus valores de MFI")
        st.caption("Puedes agregar múltiples DSA:")

        n_dsa = st.number_input("Número de DSA a evaluar", 1, 10, 3, 1, key="n_dsa")

        dsa_entries = []
        for i in range(int(n_dsa)):
            dc1, dc2, dc3, dc4 = st.columns([2, 1, 1, 2])
            with dc1:
                ag_name = st.text_input(f"HLA {i+1}", placeholder="Ej: DQ7, B35, DR4",
                                        key=f"dsa_ag_{i}")
            with dc2:
                mfi_val = st.number_input("MFI", 0, 25000, 0, 100, key=f"dsa_mfi_{i}")
            with dc3:
                clase = st.selectbox("Clase", ["I (A,B,C)", "II (DR,DQ,DP)"],
                                     key=f"dsa_clase_{i}")
            with dc4:
                es_dnovo = st.selectbox("Timing", ["Pre-formado (pre-Tx)", "De novo (post-Tx)"],
                                        key=f"dsa_timing_{i}")
            if ag_name:
                dsa_entries.append({
                    "hla": ag_name, "mfi": mfi_val,
                    "clase": clase, "dnovo": "de novo" in es_dnovo.lower()
                })

        if dsa_entries:
            st.divider()
            st.markdown("#### Interpretación clínica")

            riesgo_max = "bajo"
            for dsa in dsa_entries:
                mfi = dsa["mfi"]
                ag  = dsa["hla"]
                dnovo = dsa["dnovo"]

                if mfi < 500:
                    nivel = "⬜ Negativo / No significativo"
                    color = "success"
                    riesgo = "bajo"
                    recom  = "Sin relevancia clínica inmediata. Repetir si sospecha clínica."
                elif mfi < 3000:
                    nivel = "🟡 Débilmente positivo"
                    color = "warning"
                    riesgo = "bajo-moderado"
                    recom  = "Monitorear función renal y DSA seriados. Bajo riesgo de AMR agudo."
                elif mfi < 5000:
                    nivel = "🟠 Moderadamente positivo"
                    color = "warning"
                    riesgo = "moderado"
                    recom  = "Significativo. Biopsia si deterioro de función. Optimizar IS."
                elif mfi < 10000:
                    nivel = "🔴 Altamente positivo"
                    color = "error"
                    riesgo = "alto"
                    recom  = "Alto riesgo de rechazo humoral. Biopsia + C4d. Tratamiento de AMR si histología compatible."
                else:
                    nivel = "🔴🔴 Muy altamente positivo"
                    color = "error"
                    riesgo = "muy alto"
                    recom  = "Riesgo muy alto de AMR. Tratamiento urgente: plasmaféresis + IVIG ± rituximab."

                dnovo_txt = " ⚠️ **DE NOVO** — mayor riesgo de pérdida crónica" if dnovo else " (pre-formado)"
                getattr(st, color)(f"**{ag}** (Clase {dsa['clase'].split('(')[0].strip()}) — MFI: {mfi:,} — {nivel}{dnovo_txt}\n\n💊 {recom}")

                if riesgo in ("muy alto", "alto") and (riesgo_max not in ("muy alto")):
                    riesgo_max = riesgo

            st.divider()
            st.markdown("""
#### Tabla de referencia MFI — Umbrales clínicos
| MFI | Interpretación | Acción sugerida |
|-----|---------------|----------------|
| <500 | Negativo / no significativo | Continuar monitoreo rutinario |
| 500–2,999 | Débilmente positivo | Seriados c/3 meses, monitoreo función |
| 3,000–4,999 | Moderadamente positivo | Biopsia si función deteriora |
| 5,000–9,999 | Altamente positivo | Biopsia + C4d, tratar si AMR |
| ≥10,000 | Muy altamente positivo | Tratamiento urgente de AMR |

> ⚠️ **Contexto crítico:** Los umbrales de MFI varían entre laboratorios y kits.
> Un MFI alto sin daño histológico no justifica tratamiento agresivo.
> Siempre correlacionar con: función del injerto (creatinina), proteinuria, biopsia y C4d.

**DSA de novo** — Los más importantes en seguimiento post-trasplante:
- Anti-DQ de novo: causa más frecuente de pérdida crónica de injerto
- Aparecen típicamente a 6–24 meses post-Tx
- Factores de riesgo: incumplimiento, reducción de IS, infección CMV
            """)
            st.caption("Ref: Tambur AR et al. Am J Transplant 2015. Crespo M et al. Transplantation 2018.")

    # ── CROSSMATCH ─────────────────────────────────────────────────────────────
    elif "Crossmatch" in im_tab:
        st.markdown("### 🔬 Crossmatch — Tipos e Interpretación")

        st.markdown("""
#### ¿Qué es el crossmatch?
Prueba que mezcla el **suero del receptor** con **células del donante** para detectar anticuerpos preformados contra ese donante específico.
Un crossmatch **positivo** generalmente contraindica el trasplante sin desensibilización previa.

#### Tipos de crossmatch — de menos a más sensible

| Tipo | Principio | Sensibilidad | Cuando usar |
|------|-----------|-------------|------------|
| **CDC** (Citotoxicidad dependiente de complemento) | Lisis celular si IgG/IgM se unen → complemento activa → muerte | ++ | Estándar histórico, más rápido |
| **CDC-AHG** (Anti-Human Globulin) | Agrega anti-IgG para amplificar la señal | +++ | Sospecha de anticuerpos a bajo título |
| **FCXM** (Citometría de flujo) | Fluorescencia en células con anticuerpos — sin necesidad de lisis | ++++ | Mejor sensibilidad, detecta no-citotóxicos |
| **Virtual Crossmatch** | Compara SAB del receptor vs HLA del donante — sin células | Variable | Pre-evaluación rápida, sin células disponibles |

#### Interpretación de resultados

| Resultado | Significado | Acción |
|-----------|------------|--------|
| **CDC negativo + FCXM negativo** | Sin anticuerpos detectables contra el donante | ✅ Trasplante posible |
| **CDC negativo + FCXM positivo** | Anticuerpos a bajo título, no citotóxicos | ⚠️ Riesgo incrementado — decisión individualizada |
| **CDC positivo en células T** | DSA de clase I significativos | ❌ Contraindicación relativa — desensibilización |
| **CDC positivo solo en células B** | DSA de clase II (DR/DQ) | ⚠️ Riesgo moderado — considerar con MFI |
| **CDC positivo T y B** | DSA clase I y II ambos | ❌ Alto riesgo — desensibilización obligatoria |

#### Crossmatch virtual — ventajas y limitaciones

```
Ventajas:
✅ No requiere células del donante en tiempo real
✅ Permite evaluación previa de donantes cadavéricos a distancia
✅ Más rápido para la asignación urgente

Limitaciones:
⚠️ No detecta anticuerpos contra antígenos no tipificados
⚠️ No detecta anticuerpos no-HLA (anti-MICA, anti-AT1R)
⚠️ El MFI puede ser negativo y el crossmatch celular positivo (anticuerpos complement-fixing)
⚠️ Requiere tipificación HLA de alta resolución del donante
```

#### Anticuerpos no-HLA — cada vez más relevantes
| Anticuerpo | Antígeno | Asociación clínica |
|-----------|---------|-------------------|
| Anti-MICA | MHC class I chain-related protein A | Rechazo humoral sin DSA HLA detectable |
| Anti-AT1R | Receptor de angiotensina 1 | Rechazo vascular, HTA severa post-Tx |
| Anti-endoteliales | Antígenos endoteliales | Rechazo mediado por anticuerpos C4d neg |

> 📌 Si hay rechazo humoral sin DSA HLA → estudiar anticuerpos no-HLA.
        """)
        st.caption("Ref: Tait BD et al. Transplantation 2013 | Gebel HM et al. Clin Transpl 2012 | "
                   "Lefaucheur C et al. Am J Transplant 2010.")

    # ── ESTRATIFICACIÓN DE RIESGO ───────────────────────────────────────────────
    else:
        st.markdown("### ⚠️ Estratificación de Riesgo Inmunológico Pre-Trasplante")
        st.caption("Ref: OPTN Policy 2023 | Meier-Kriesche HU et al. Am J Transplant 2004 | "
                   "Wiebe C et al. Am J Transplant 2012")

        st.markdown("#### Evaluación interactiva del riesgo del receptor")
        er1, er2 = st.columns(2)

        with er1:
            er_cpra  = st.slider("cPRA del receptor (%)", 0, 100, 0, 1, key="er_cpra")
            er_retx  = st.checkbox("Retrasplante (trasplante previo fallido)", key="er_retx")
            er_emb   = st.number_input("Número de embarazos", 0, 15, 0, 1, key="er_emb")
            er_transfusiones = st.number_input("Número de transfusiones previas", 0, 50, 0, 1, key="er_transf")

        with er2:
            er_dsa_pre = st.selectbox("DSA preformados", [
                "No detectados", "MFI 500–2,999 (débiles)",
                "MFI 3,000–5,000 (moderados)", "MFI >5,000 (fuertes)"
            ], key="er_dsa")
            er_xm = st.selectbox("Crossmatch con donante potencial", [
                "Virtual negativo / CDC negativo",
                "FCXM débilmente positivo (CDC neg)",
                "CDC positivo solo células B",
                "CDC positivo células T (con o sin B)",
            ], key="er_xm")
            er_mismatch = st.selectbox("Mismatches DR+DQ esperados", [
                "0 mismatches", "1–2 mismatches", "3–4 mismatches (máximo)"
            ], key="er_mm")

        # Calculate risk score
        riesgo_pts = 0
        if er_cpra >= 99:    riesgo_pts += 4
        elif er_cpra >= 80:  riesgo_pts += 3
        elif er_cpra >= 50:  riesgo_pts += 2
        elif er_cpra >= 20:  riesgo_pts += 1

        if er_retx:          riesgo_pts += 2
        if er_emb >= 3:      riesgo_pts += 2
        elif er_emb >= 1:    riesgo_pts += 1
        if er_transfusiones >= 5: riesgo_pts += 1

        if "5,000" in er_dsa_pre:    riesgo_pts += 3
        elif "3,000" in er_dsa_pre:  riesgo_pts += 2
        elif "500" in er_dsa_pre:    riesgo_pts += 1

        if "células T" in er_xm: riesgo_pts += 4
        elif "solo células B" in er_xm: riesgo_pts += 2
        elif "FCXM" in er_xm:    riesgo_pts += 1

        if "3–4" in er_mismatch: riesgo_pts += 1

        st.divider()
        if riesgo_pts == 0:
            st.success("""
**🟢 RIESGO INMUNOLÓGICO BAJO**
- Candidato ideal para trasplante estándar
- Inducción estándar (basiliximab o timoglobulina según protocolo)
- Monitoreo rutinario post-trasplante
- Sin restricciones especiales por factor inmunológico
            """)
        elif riesgo_pts <= 3:
            st.success(f"""
**🟢-🟡 RIESGO INMUNOLÓGICO BAJO-MODERADO** (score: {riesgo_pts})
- Trasplante viable sin desensibilización
- Considerar timoglobulina en inducción si DSA débiles presentes
- Monitoreo estrecho de DSA post-trasplante (c/3 meses primer año)
- Biopsia de protocolo recomendada (3 y 12 meses)
            """)
        elif riesgo_pts <= 6:
            st.warning(f"""
**🟡 RIESGO INMUNOLÓGICO MODERADO** (score: {riesgo_pts})
- Inducción con timoglobulina obligatoria
- Si DSA moderados: valorar desensibilización pre-Tx
- Crossmatch celular obligatorio antes del trasplante
- IS de mantenimiento más intensa (niveles de tacrolimus más altos)
- Monitoreo DSA mensual primer año
- Biopsia de protocolo obligatoria
            """)
        elif riesgo_pts <= 9:
            st.error(f"""
**🔴 RIESGO INMUNOLÓGICO ALTO** (score: {riesgo_pts})
- Desensibilización pre-trasplante recomendada:
  → IVIG 2 g/kg IV (dividido en 2 días) + Rituximab 375 mg/m²
  → Plasmaféresis si DSA fuertes (×5 sesiones pre-trasplante)
- Crossmatch celular T y B obligatorio
- Inducción con timoglobulina (dosis completa 7–14 días)
- Objetivos de tacrolimus más altos (C0 12–15 ng/mL fase 1)
- DSA post-trasplante c/1–2 semanas primer mes → mensual
            """)
        else:
            st.error(f"""
**🚨 RIESGO INMUNOLÓGICO MUY ALTO / HIPERSENSIBILIZADO** (score: {riesgo_pts})
- Candidato con cPRA ≥99% — prioridad máxima en lista de espera
- Desensibilización agresiva pre-trasplante:
  → IVIG 2 g/kg + Rituximab × múltiples ciclos
  → Plasmaféresis intensiva (× 10–15 sesiones)
  → Eculizumab perioperatorio en algunos protocolos
- Crossmatch T + B debe ser negativo antes de proceder
- Considerar trasplante AB0-incompatible o donante vivo HLA compatible
- Centros especializados — derivar si no hay experiencia local
            """)

        st.markdown("""
#### Protocolo de desensibilización — esquema general (IVIG + Rituximab)
| Paso | Intervención | Objetivo |
|------|-------------|---------|
| **1** | IVIG 2 g/kg IV (1 g/kg × 2 días) | Bloqueo Fc + eliminación de anticuerpos |
| **2** | Rituximab 375 mg/m² × 1 dosis | Depleción de células B productoras de anticuerpos |
| **3** | Repetir IVIG en 21–30 días si DSA persisten | Reducción sostenida |
| **4** | Plasmaféresis × 5–10 sesiones si DSA fuertes (MFI >5,000) | Eliminación directa de anticuerpos |
| **5** | Monitorear DSA mensualmente durante desensibilización | Meta: reducción MFI >50% |
| **6** | Trasplante cuando crossmatch virtual negativo o FCXM negativo | — |

> ⚠️ No existe protocolo estándar universal — varía por centro y disponibilidad.
> La evidencia para desensibilización viene principalmente de estudios observacionales.
        """)
        st.caption("Ref: Montgomery RA et al. NEJM 2011 | Stegall MD et al. Am J Transplant 2012 | "
                   "Vo AA et al. Transplantation 2015.")

elif nav == "dgf":
    st.subheader("⏱️ Función Retardada del Injerto (DGF)")
    st.caption("Ref: Yarlagadda SG. Nephrol Dial Transplant 2008 | Rao PS et al. Am J Transplant 2009 (KDPI) | "
               "Massie AB et al. Am J Transplant 2016 | Irish WD et al. Transplantation 2010 (DGF score)")

    dgf_tab = st.radio("", [
        "📚 Conceptos y Manejo",
        "🧮 Calculadora KDPI",
        "📊 Calculadora EPTS",
        "⚠️ Score de riesgo DGF",
    ], horizontal=True, key="dgf_tab")
    st.divider()

    if "Conceptos" in dgf_tab:
        st.markdown("""
### ¿Qué es la Función Retardada del Injerto?

**Definición operacional:** Necesidad de diálisis en los **primeros 7 días** post-trasplante.
        """)

        # ── ISQUEMIA FRÍA Y CALIENTE ────────────────────────────────────────────
        with st.expander("🧊 Isquemia fría e isquemia caliente — ¿qué son y cómo se miden?", expanded=True):
            st.markdown("""
#### Concepto fundamental
Cuando un riñón pierde el flujo sanguíneo, sus células comienzan a sufrir daño.
La velocidad del daño depende de la **temperatura**:
- A temperatura corporal → daño muy rápido (minutos-horas) = **Isquemia caliente**
- A 4°C con solución fría → metabolismo casi en pausa → puede tolerar horas = **Isquemia fría**

---

#### Secuencia de eventos en el trasplante renal — línea de tiempo

```
DONANTE FALLECIDO
│
├─ [Paro cardíaco / muerte cerebral]
│
├─ 🔴 WIT1 — Isquemia Caliente 1 (solo en donante DCD)
│   │  Tiempo sin flujo a temperatura corporal antes de enfriar
│   │  Meta: <20 min · Cada minuto cuenta
│   │
├─ ❄️ INICIO ISQUEMIA FRÍA ← aquí empieza
│   │  Cirujanos perfunden riñón in situ con solución fría (UW, Custodiol, HTK)
│   │  Temperatura cae a 4°C
│   │
├─ Extracción del riñón → bolsas con hielo
│   │
├─ Transporte en hielera
│   │  ← Todo esto sigue siendo ISQUEMIA FRÍA →
│   │
├─ Quirófano del receptor:
│   │  
│   ├─ "Back table" (mesa de preparación/disección)
│   │   El cirujano prepara los vasos renales mientras el riñón
│   │   está en un recipiente con HIELO y solución fría
│   │   ← SIGUE SIENDO ISQUEMIA FRÍA (esto es lo que se pregunta)
│   │
│   ├─ ❄️ FIN ISQUEMIA FRÍA
│   │   El riñón sale del hielo para colocarse en la fosa ilíaca
│   │
│   ├─ 🟡 WIT2 — Isquemia Caliente 2
│   │   El riñón empieza a calentarse durante la anastomosis
│   │   (sutura de arteria y vena renal) — a temperatura ambiente
│   │   Meta: <45 minutos
│   │
└─ 🔴 REPERFUSIÓN → retiro de clamps → sangre fluye → FIN ISQUEMIA
```

---

#### Definiciones precisas

| Tipo | Definición | Duración aceptable | Riesgo DGF |
|------|-----------|-------------------|-----------|
| **WIT1** (caliente 1) | Paro cardíaco → inicio perfusión fría (solo DCD) | <20 min | ⭐⭐⭐⭐ |
| **CIT** (fría) | Inicio perfusión fría → riñón sale del hielo para anastomosis | **<18–24h** (riñón cadavérico) | ⭐⭐⭐ |
| **WIT2** (caliente 2) | Riñón fuera de hielo → reperfusión (durante anastomosis) | <45 min | ⭐⭐ |

> 📌 **La "mesa de preparación" o back table** es parte de la isquemia fría — el riñón está en hielo, a 4°C.
> La isquemia caliente 2 empieza cuando el cirujano saca el riñón del recipiente con hielo
> para colocarlo en la fosa ilíaca del receptor.

#### Impacto clínico
- **Cada hora adicional de CIT >18h** → aumenta el riesgo de DGF ~6%
- **CIT <12h** en donante vivo: DGF <2%
- **CIT >24h** en donante cadavérico: DGF hasta 40–60%
- **WIT1 >30 min** en DCD: riñón probablemente no viable
- **WIT2 >60 min**: aumento significativo de DGF y retardo de recuperación

> 💡 **Regla práctica para el fellow:**
> Cuando te digan que un riñón "lleva X horas de isquemia", están hablando de isquemia fría total (CIT).
> Eso incluye la extracción, el transporte, y la preparación en el back table.
> La isquemia caliente 1 solo aplica en DCD y la intraoperatoria (WIT2) la mide el cirujano.
            """)

        st.markdown("""
### Incidencia y expectativa según tipo de donante

**Definiciones alternativas también usadas:**
- Cr sérica >3 mg/dL al día 5 post-Tx (Halloran PF)
- Diuresis <1,200 mL/día en las primeras 24h
- Caída de Cr <10% en 24h durante los primeros 3 días

> 📌 Para tu práctica clínica: la definición de **diálisis en la primera semana** es la más usada.

#### Incidencia por tipo de donante
| Tipo de donante | DGF |
|----------------|-----|
| Donante vivo | 1–5% |
| Donante fallecido criterio estándar | 15–30% |
| Donante criterio expandido (ECD/KDPI >85%) | 30–60% |
| Donante tras muerte cardiaca (DCD) | 30–50% |

#### ¿Por qué los nefrólogos de trasplante no se inmutan con DGF?
Porque saben lo que tú vas a aprender aquí:

1. **DGF no predice pérdida del injerto a corto plazo** — el riñón puede tardar 2–6 semanas en
   funcionar y aun así tener excelente función a los 5 años si se maneja bien.

2. **El KDPI predice quién va a tener DGF** — si el KDPI es >85%, la expectativa
   ya era que el riñón tardara en arrancar. No es sorpresa, es parte del plan.

3. **Lo que importa es el Doppler y la tendencia** — no la creatinina del día 1.

4. **La IS se ajusta en DGF** — no es el mismo esquema que con función inmediata.

#### Factores de riesgo de DGF
| Factor | Peso |
|--------|------|
| Tiempo de isquemia fría >18h | ⭐⭐⭐ |
| KDPI >85% | ⭐⭐⭐ |
| Donante tras muerte cardíaca (DCD) | ⭐⭐⭐ |
| Hipotensión del donante o receptor intraoperatoria | ⭐⭐ |
| PRA elevado / rechazo hiperagudo | ⭐⭐ |
| Oliguria del donante pre-donación | ⭐⭐ |
| Obesidad del receptor (IMC >30) | ⭐ |

#### Protocolo de manejo de DGF

**Días 1–3 (oliguria/anuria):**
```
✅ Confirmar perfusión del injerto:
   → Eco Doppler URGENTE (descartar trombosis vascular — cirugía si <6h)
   → Descartar obstrucción ureteral o fuga urinaria (TC si sospecha)
   → Descartar rechazo hiperagudo (anti-HLA preformados, crossmatch)

✅ Manejo médico:
   → Mantener PAM >75–85 mmHg (hidratación + vasopresores si necesario)
   → Furosemida IV 100–200 mg → si no responde, no repetir (isquemia)
   → Hemodiálisis si: K >5.5, acidosis severa, sobrecarga hídrica sintomática
   → NO hacer biopsia de rutina en DGF si Doppler conservado

✅ Inmunosupresión en DGF:
   → Reducir o diferir tacrolimus (nefrotóxico en isquemia tubular)
   → Algunos centros: nivel C0 tacrolimus 5–8 ng/mL en DGF (vs 10–15 normal)
   → Continuar MMF + esteroides sin modificación
   → Monitoreo de DSA — DGF no implica rechazo per se
```

**Días 4–14 (seguimiento):**
```
✅ Monitoreo diario:
   → Creatinina sérica c/24h
   → Balance hídrico estricto
   → Diuresis horaria (aparición de diuresis = buen signo)

✅ ¿Cuándo sospechar rechazo y hacer biopsia?
   → Fiebre + aumento de Cr después de inicio de diuresis
   → Doppler: aumento de índice de resistencia >0.80
   → DSA de novo positivos en el post-Tx
   → Sin mejoría alguna después de día 14

✅ Inicio de diuresis → "slow DGF":
   → Creatinina comienza a caer (aunque lentamente)
   → Esto es la señal de que el TRRC tubular está recuperando
   → Ajustar IS gradualmente al nivel objetivo
```

**Semanas 3–8 (recuperación tardía):**
```
✅ DGF prolongada (>3 semanas): biopsia obligatoria
   → Descartar rechazo agudo (celular o humoral)
   → Descartar nefrotoxicidad por CNI
   → Reevaluar IS

✅ Criterios de "no función primaria del injerto" (PNF):
   → Nunca inició diuresis
   → Cr no cae en 4–6 semanas
   → Biopsia: necrosis cortical, trombosis → pérdida del injerto
   → Nefrectomía si: dolor del injerto, fiebre persistente, consumo de plaquetas
```

#### Factores predictores de recuperación
- ✅ Flujo diastólico conservado en Doppler (IR <0.80)
- ✅ Aparición de diuresis aunque sea pequeña
- ✅ Caída progresiva de creatinina (aunque lenta)
- ✅ Sin DSA de novo + crossmatch negativo pre-Tx
- ✅ Tiempo de isquemia fría <24h
- ⚠️ KDPI <85%

> 📌 **Regla práctica:** Si el Doppler muestra flujo y la Cr cae aunque sea 0.2 mg/dL/día,
> el riñón va a funcionar. Ten paciencia. La naturaleza del TRRC tubular es recuperarse.
        """)

    elif "KDPI" in dgf_tab:
        st.markdown("### 🧮 Calculadora KDPI — Kidney Donor Profile Index")
        st.info("""
**KDPI** expresa el riesgo relativo de falla del injerto de un donante cadavérico comparado
con el pool de donantes. KDPI 85% = este riñón tiene mayor probabilidad de falla que el 85% de los donantes.
**No es una contraindicación** — es información para tomar decisiones y para preparar al receptor.
        """)
        k1, k2 = st.columns(2)
        with k1:
            k_edad  = st.number_input("Edad del donante (años)", 0, 100, 50, 1, key="k_edad")
            k_peso  = st.number_input("Peso del donante (kg)", 20.0, 200.0, 75.0, 0.5, key="k_peso")
            k_talla = st.number_input("Talla del donante (cm)", 100.0, 220.0, 170.0, 0.5, key="k_talla")
            k_cr    = st.number_input("Creatinina terminal (mg/dL)", 0.3, 15.0, 1.2, 0.1, key="k_cr")
            k_hta   = st.checkbox("Historia de hipertensión arterial", key="k_hta")
        with k2:
            k_dm    = st.checkbox("Historia de diabetes mellitus", key="k_dm")
            k_aacv  = st.checkbox("Muerte por ACV / causa cerebrovascular", key="k_acv")
            k_hcv   = st.checkbox("Hepatitis C positivo", key="k_hcv")
            k_dcd   = st.checkbox("Donante tras muerte cardíaca (DCD)", key="k_dcd")
            k_raza  = st.selectbox("Raza del donante", ["No afroamericano", "Afroamericano"], key="k_raza")

        import math
        # KDRI calculation (OPTN 2013 formula, simplified)
        age_term = (0.0128*(k_edad-40)
                    - 0.0194*max(0, 18-k_edad)
                    + 0.0107*max(0, k_edad-50))
        ht_term  = -0.0464*(k_talla-170)/10
        wt_term  = 0.1262*max(0, 80-k_peso)*(80-k_peso)/5 if k_peso < 80 else 0
        aa_term  = 0.1082 if k_raza=="Afroamericano" else 0
        hta_term = 0.2350 if k_hta else 0
        dm_term  = 0.5125 if k_dm else 0
        cr_term  = 0.2140*(k_cr-1) - (0.0790*(k_cr-1.5) if k_cr>1.5 else 0)
        dcd_term = 0.1330 if k_dcd else 0
        hcv_term = 0.2490 if k_hcv else 0
        acv_term = -0.0776 if k_aacv else 0  # CVA as cause reduces risk slightly

        kdri_raw = math.exp(age_term + ht_term + wt_term + aa_term +
                            hta_term + dm_term + cr_term + dcd_term +
                            hcv_term + acv_term)
        # KDRI scaling (median donor 2021 ≈ 1.0) and KDPI from lookup
        # Simplified: KDPI ≈ percentile of kdri_raw relative to population
        # Using approximate conversion (OPTN 2021 scaling factor ~1.0)
        kdri_rao = kdri_raw  # simplified (actual needs scaling factor from OPTN)

        # Approximate KDPI from KDRI using logistic approximation
        # KDPI = 100 * CDF of log-normal distribution
        kdpi_approx = min(99, max(1, int(100 * (1 - math.exp(-kdri_rao * 0.62)))))

        rp1, rp2, rp3 = st.columns(3)
        rp1.metric("KDRI (raw)", f"{kdri_raw:.3f}")
        rp2.metric("KDPI aproximado", f"~{kdpi_approx}%")
        if kdpi_approx < 20:
            rp3.metric("Calidad del órgano", "Excelente")
            st.success(f"**KDPI ~{kdpi_approx}%** — Órgano de alta calidad. Bajo riesgo de DGF y falla del injerto.")
        elif kdpi_approx < 50:
            rp3.metric("Calidad del órgano", "Buena")
            st.success(f"**KDPI ~{kdpi_approx}%** — Estándar. Buen candidato para receptores de EPTS moderado-alto.")
        elif kdpi_approx < 85:
            rp3.metric("Calidad del órgano", "Aceptable")
            st.warning(f"**KDPI ~{kdpi_approx}%** — Criterio expandido (ECD). Mayor riesgo de DGF. "
                       "Preparar receptor para posible diálisis temporal.")
        else:
            rp3.metric("Calidad del órgano", "Alto riesgo")
            st.error(f"**KDPI ~{kdpi_approx}%** — Órgano de muy alto riesgo. "
                     "Discutir con el receptor. DGF probable (30–60%). "
                     "Beneficio vs riesgo: ¿cuánto tiempo lleva en diálisis?")

        st.markdown("""
#### Interpretación clínica del KDPI
| KDPI | Calidad | Expectativa | DGF estimado |
|------|---------|-------------|-------------|
| <20% | Óptima | Mejor sobrevida del injerto | <10% |
| 20–50% | Estándar | Buen pronóstico | 10–25% |
| 50–85% | Criterio expandido | Pronóstico moderado | 25–40% |
| >85% | Muy alto riesgo | Mayor riesgo de pérdida | 40–60% |

> ⚠️ Este cálculo es una aproximación educativa basada en la fórmula OPTN 2013.
> El KDPI oficial se calcula en el sistema UNOS con la tabla de scaling actualizada anualmente.
        """)
        st.caption("Ref: Rao PS et al. Am J Transplant 2009;9(11):2567-2573. "
                   "OPTN KDPI Guide. optn.transplant.hrsa.gov")

    elif "EPTS" in dgf_tab:
        st.markdown("### 📊 Calculadora EPTS — Estimated Post-Transplant Survival")
        st.info("""
**EPTS** predice la sobrevida post-trasplante del **receptor** basándose en sus características.
Se usa para matching: receptores con EPTS bajo (<20%) tienen prioridad para recibir riñones
con KDPI bajo (<20%) — los mejores riñones para los mejores candidatos.
        """)
        e1, e2 = st.columns(2)
        with e1:
            e_edad  = st.number_input("Edad del receptor (años)", 18, 90, 45, 1, key="e_edad")
            e_dm    = st.checkbox("Diabetes mellitus", key="e_dm")
            e_retx  = st.checkbox("Trasplante previo (retrasplante)", key="e_retx")
        with e2:
            e_dial  = st.checkbox("Actualmente en diálisis", key="e_dial")
            e_t_dial = st.number_input("Años en diálisis (si aplica)", 0.0, 30.0, 0.0, 0.5,
                                       key="e_t_dial", disabled=not e_dial)

        # EPTS formula (OPTN 2014)
        epts_raw = (0.047 * max(e_edad - 25, 0)
                    - 0.015 * (1 if e_dm else 0) * max(e_edad - 25, 0)
                    + 0.398 * (1 if e_retx else 0)
                    - 0.237 * (1 if e_dm else 0) * (1 if e_retx else 0)
                    + 6.321 * (1 if e_dial else 0)
                    + 0.130 * max(e_t_dial, 0)
                    - 0.282 * (1 if e_dm else 0) * max(e_t_dial, 0)
                    + 1.490 * (1 if e_dm else 0))

        # Convert raw score to percentile (approximate)
        import math
        epts_pct = min(99, max(1, int(100 * (1 - math.exp(-epts_raw * 0.08)))))

        ep1, ep2, ep3 = st.columns(3)
        ep1.metric("EPTS score (raw)", f"{epts_raw:.2f}")
        ep2.metric("EPTS percentil (aprox.)", f"~{epts_pct}%")
        if epts_pct < 20:
            ep3.metric("Candidato a", "KDPI <20%")
            st.success(f"**EPTS ~{epts_pct}%** — Candidato excelente. Tiene prioridad para riñones KDPI <20%. "
                       "Mayor esperanza de vida post-trasplante.")
        elif epts_pct < 50:
            ep3.metric("Perfil", "Estándar")
            st.info(f"**EPTS ~{epts_pct}%** — Perfil estándar. Puede recibir riñones de cualquier KDPI.")
        else:
            ep3.metric("Perfil", "Mayor comorbilidad")
            st.warning(f"**EPTS ~{epts_pct}%** — Mayor comorbilidad. "
                       "Considerar riñones de criterio expandido (KDPI alto) "
                       "si el tiempo de espera es prolongado — el beneficio del Tx sigue siendo positivo.")

        st.markdown("""
#### Uso del EPTS en la asignación
El sistema OPTN usa EPTS + KDPI para el matching óptimo:

| Receptor | Donante ideal |
|---------|--------------|
| EPTS <20% (joven, sin comorbilidades) | KDPI <20% (riñón de alta calidad) |
| EPTS 20–50% | KDPI <50% |
| EPTS >50% | Cualquier KDPI — tiempo de espera pesa más |
| En diálisis >10 años | Aceptar KDPI >85% — el Tx sigue siendo mejor que la diálisis |

> 📌 Para México/IMSS: el sistema de asignación puede diferir del OPTN,
> pero los conceptos KDPI/EPTS son aplicables para decisiones clínicas individuales.
        """)
        st.caption("Ref: Massie AB et al. Am J Transplant 2016;16(3):849-858. "
                   "OPTN EPTS Guide. optn.transplant.hrsa.gov")

    else:
        st.markdown("### ⚠️ Score de Riesgo de DGF")
        st.info("Calcula la probabilidad de que el receptor desarrolle DGF "
                "(necesite diálisis en la primera semana post-trasplante).")
        st.caption("Ref: Irish WD et al. Transplantation 2010;89(8):1028-1035")

        sg1, sg2 = st.columns(2)
        with sg1:
            sg_kdpi = st.number_input("KDPI del donante (%)", 0, 100, 40, 1, key="sg_kdpi")
            sg_isq  = st.number_input("Tiempo de isquemia fría (horas)", 0.0, 48.0, 16.0, 0.5, key="sg_isq")
            sg_dcd  = st.checkbox("Donante tras muerte cardíaca (DCD)", key="sg_dcd")
            sg_dial_recep = st.checkbox("Receptor en diálisis crónica", key="sg_dial_r")
        with sg2:
            sg_dm_rec = st.checkbox("Receptor diabético", key="sg_dm_r")
            sg_bmi  = st.number_input("IMC del receptor (kg/m²)", 15.0, 55.0, 25.0, 0.5, key="sg_bmi")
            sg_fh   = st.selectbox("Donante femenino → Receptor masculino",
                                   ["No (misma sexo o H→F)", "Sí (F→M)"], key="sg_fh")
            sg_pra  = st.number_input("cPRA del receptor (%)", 0, 100, 0, 1, key="sg_pra")

        # DGF risk score (Irish WD 2010 adaptation)
        pts = 0
        if sg_kdpi >= 85: pts += 6
        elif sg_kdpi >= 50: pts += 3
        elif sg_kdpi >= 20: pts += 1
        if sg_dcd: pts += 4
        if sg_isq >= 24: pts += 3
        elif sg_isq >= 18: pts += 2
        elif sg_isq >= 12: pts += 1
        if sg_bmi >= 30: pts += 3
        if sg_dm_rec: pts += 2
        if sg_fh == "Sí (F→M)": pts += 2
        if sg_pra >= 80: pts += 2
        elif sg_pra >= 30: pts += 1

        # Risk estimation
        if pts <= 2: risk_pct = 5; risk_label = "🟢 Bajo"
        elif pts <= 5: risk_pct = 15; risk_label = "🟡 Moderado"
        elif pts <= 9: risk_pct = 30; risk_label = "🟠 Alto"
        else: risk_pct = 55; risk_label = "🔴 Muy Alto"

        r1, r2, r3 = st.columns(3)
        r1.metric("Puntuación DGF", f"{pts} pts")
        r2.metric("Riesgo estimado de DGF", f"~{risk_pct}%")
        r3.metric("Nivel de riesgo", risk_label.split()[1])

        if pts <= 2:
            st.success("**Riesgo BAJO de DGF.** Alta probabilidad de función inmediata del injerto. "
                       "Protocolo de IS estándar.")
        elif pts <= 5:
            st.warning("**Riesgo MODERADO.** Preparar para posible DGF. "
                       "Informar al receptor. Monitoreo estrecho las primeras 72h.")
        elif pts <= 9:
            st.error("**Riesgo ALTO.** DGF probable. "
                     "Planear acceso dialítico si no lo tiene. "
                     "Considerar reducir CNI en las primeras 48h. "
                     "Eco Doppler en las primeras 24h.")
        else:
            st.error("**Riesgo MUY ALTO.** DGF casi segura. "
                     "Catéter temporal de diálisis disponible en pabellón. "
                     "Reducir tacrolimus. Eco Doppler urgente a las 6h post-Tx.")

        st.info("""
**Acciones preventivas según riesgo:**
- **Isquemia fría:** minimizar — cada hora adicional >20h aumenta el riesgo 6%
- **KDPI alto:** consentimiento informado pre-Tx; preparar soporte dialítico
- **DCD:** solución de preservación con adición de cardioprotectores; isquemia fría <14h ideal
- **IMC >30:** diuresis post-clampeo es predictora; furosemida intraoperatoria
        """)
        st.caption("Score adaptado de: Irish WD et al. Transplantation 2010;89(8):1028-1035. "
                   "Boom H et al. JASN 2000.")

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"© Dr. Josué Tapia Nefrólogo — RenalPro {VERSION} — Uso académico exclusivo | "
    "Nefrología / Medicina Crítica | León, Gto., México"
)

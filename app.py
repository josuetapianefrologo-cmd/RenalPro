# ============================================================
# app.py — TRRC360 by Dr. Tapia (v2.0.0)
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

VERSION = "v3.0.0"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TRRC360 by Dr. Tapia",
    layout="wide",
    page_icon="🩺",
    initial_sidebar_state="expanded"
)

# ─── CSS CLÍNICO OSCURO ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ══ TRRC360 — Tema Médico Claro v3 ══════════════════════════════════════ */

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
    TRRC<span style="font-size:28px;vertical-align:super;font-weight:700;letter-spacing:0;">360</span>
  </div>
  <div style="color:rgba(255,255,255,0.85);font-size:16px;font-weight:500;margin-top:8px;">
    Calculadora Clínica de Terapias Extracorpóreas
  </div>
  <div style="color:rgba(255,255,255,0.55);font-size:12px;margin-top:4px;">
    TRRC · HD · Citrato · Plasmaféresis · Scores UCI
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
  TRRC360 · Dr. Josué Tapia Nefrólogo · León, Gto. · Uso académico · v2.1.0
</div>""", unsafe_allow_html=True)
    st.stop()

# ─── BANNER DE ESTADO DE USUARIO ──────────────────────────────────────────────
def _status_banner():
    rol    = _rol()
    nombre = _nombre()
    _init_db()
    users  = st.session_state.get("auth_users", {})
    user   = users.get(st.session_state.get("sess_user", ""))
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
            <span>⏱️</span>
            <span style="color:{tc};font-size:13px;"><strong>{nombre}</strong> —
            Prueba gratuita: <strong>{days} día(s) restante(s)</strong></span>
            </div>""", unsafe_allow_html=True)

    elif rol == "pro":
        st.markdown(f"""<div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:10px;
            padding:8px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
            <span>⭐</span>
            <span style="color:#166534;font-size:13px;"><strong>{nombre} — Premium</strong> ·
            {days} días restantes</span>
            </div>""", unsafe_allow_html=True)

    elif rol == "beca":
        dias_txt = "Acceso indefinido" if days > 365 * 5 else f"{days} días"
        st.markdown(f"""<div style="background:linear-gradient(90deg,#0D9488,#0891B2);
            border-radius:10px;padding:8px 16px;margin-bottom:8px;
            display:flex;align-items:center;gap:10px;">
            <span style="font-size:18px;">🎓</span>
            <span style="color:#fff;font-size:13px;">
            <strong>{nombre} — Beca Académica</strong> ·
            Dr. Josué Tapia Nefrólogo · {dias_txt}</span>
            </div>""", unsafe_allow_html=True)

    elif rol == "admin":
        st.markdown(f"""<div style="background:#1E3A8A;border-radius:10px;
            padding:8px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;">
            <span>🛡️</span>
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
    filename = f"TRRC360_{safe_name}_{ts}.pdf" if safe_name else f"TRRC360_{ts}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    w, h = letter
    margin = 50
    y = h - margin
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "TRRC360 — Prescripción Terapia de Reemplazo Renal Continua")
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
    c.drawString(50, y, "Fundamento y Cálculos — TRRC360 v2.0.0")
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
        [Paragraph("<b>TRRC360</b>", E_TITULO),
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
        f"TRRC360 {VERSION} — Generado {ts} — Uso académico y de apoyo clínico exclusivo. "
        "No reemplaza el juicio clínico del médico tratante.", E_FOOT))

    # ══ PÁGINA 2: PROTOCOLO DE ENFERMERÍA ═════════════════════════════════════
    story.append(PageBreak())

    enf_hdr = Table([[
        Paragraph("<b>TRRC360 — PROTOCOLO DE ENFERMERÍA</b>", E_TITULO),
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
    story.append(sec_bar(f"▌  FUNDAMENTO Y CÁLCULOS — TRRC360 {VERSION}"))
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
            TRRC<span style="font-size:14px; vertical-align:super; font-weight:700;">360</span>
        </div>
        <div style="font-size:9px; color:rgba(255,255,255,0.75); font-weight:600; letter-spacing:0.08em; margin-top:2px;">
            NEFROLOGÍA
        </div>
    </div>
    <div style="flex:1;">
        <div style="font-size:20px; font-weight:800; color:#FFFFFF; letter-spacing:-0.3px; line-height:1.1;">
            Calculadora Clínica de Terapias Extracorpóreas
        </div>
        <div style="font-size:12px; color:rgba(255,255,255,0.75); margin-top:4px; font-weight:500;">
            Prescripción TRRC · Citrato · HD · Plasmaféresis · Scores UCI
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

    st.header("Parámetros globales")
    peso = st.number_input("Peso (kg)", 10.0, 300.0, 70.0, 0.5, key="sb_peso")
    hto = st.number_input("Hematocrito (fracción)", 0.10, 0.60, 0.30, 0.01, format="%.2f", key="sb_hto")
    qb = st.number_input("Qb (mL/min)", 80, 300, 200, 10, key="sb_qb")
    uf = st.number_input("UF neta (mL/h)", 0, 2000, 100, 10, key="sb_uf")
    dosis_mlkg = st.slider("Dosis objetivo (mL/kg/h)", 10, 45, 30, key="sb_dosis")

    st.markdown("---")
    st.subheader("Escenarios clínicos")
    escenarios_catalogo = [
        "Sepsis / choque séptico", "Choque cardiogénico", "Post infarto",
        "Neurocrítico / TCE", "Sobrecarga hídrica aislada", "Intoxicación / sobredosis",
        "Hiponatremia severa", "Hipernatremia", "Hiperamonemia",
        "Rabdomiólisis", "Síndrome de liberación de citocinas",
    ]
    escenarios = st.multiselect("Hasta 3", escenarios_catalogo, max_selections=3,
                                default=["Sepsis / choque séptico"], key="sb_escenarios")

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

    _navsec("NEFROLOGÍA")
    _navbtn("🔢 Calculadoras Nefro", "nefro")
    _navbtn("🫀 Acceso Vascular", "acceso")

    _navsec("DOCUMENTACIÓN")
    _navbtn("📋 Resumen / PDF", "resumen")
    _navbtn("📂 Mis Pacientes", "pacientes")
    _navbtn("📚 Fundamento", "fund")
    _navbtn("📖 Referencias", "refs")

    _navsec("CUENTA")
    _navbtn("💳 Premium", "premium")
    _navbtn("🛡️ Admin" if _rol() == "admin" else "👤 Mi Cuenta", "admin")

    st.markdown("---")
    if st.button("🚪 Cerrar sesión", key="btn_logout", use_container_width=True):
        for k in ["logged_in", "sess_user", "sess_rol", "sess_nombre", "consent_ok", "nav_sel"]:
            st.session_state.pop(k, None)
        st.rerun()

# ─── NAVEGACIÓN: variable de control ──────────────────────────────────────────
nav = st.session_state.get("nav_sel", "presc")



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
                                      placeholder="Ej: Paciente UCI-01 o sin nombre",
                                      key="presc_alias")
            notas_pac = st.text_input("Notas clínicas (opcional)",
                                      placeholder="Ej: sepsis foco pulmonar, inicio día 2",
                                      key="presc_notas")
        with save2:
            st.markdown(" ")
            st.markdown(" ")
            if st.button("💾 Guardar prescripción", type="primary",
                         key="btn_guardar_presc", use_container_width=True):
                datos = {
                    "alias":       alias_pac or "Paciente sin nombre",
                    "modality":    st.session_state.get("presc_modality", "—"),
                    "peso":        float(st.session_state.get("sb_peso", 70)),
                    "hto":         float(st.session_state.get("sb_hto", 0.30)),
                    "qb":          int(st.session_state.get("sb_qb", 200)),
                    "qeff":        float(st.session_state.get("sb_qb", 200)) * 3,
                    "uf":          int(st.session_state.get("sb_uf", 100)),
                    "dosis_mlkgh": float(st.session_state.get("sb_dosis", 30)),
                    "anticoag":    st.session_state.get("anticoagulacion_tipo", "—"),
                    "escenarios":  list(st.session_state.get("sb_escenarios", [])),
                    "notas":       notas_pac or "",
                }
                ok = _db.save_prescription(_user_id(), datos)
                if ok:
                    st.success(f"✅ Prescripción de **{datos['alias']}** guardada correctamente.")
                else:
                    st.error("Error al guardar. Verifica la conexión con Railway.")
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
                fname = f"TRRC360_{safe}_{ts}.pdf" if safe else f"TRRC360_{ts}.pdf"
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
  <div style="font-size:32px;font-weight:800;color:#fff;">⭐ TRRC360 Pro</div>
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
| **CLABE** | `{clabe}` |
| **Titular** | {titular} |
| **Monto** | $99 MXN / mes |
""")
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
            all_users_db = _db.get_all_users()
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
        st.divider()
        st.markdown("### 👥 Gestión de usuarios")

        for uname, udata in list(users_adm.items()):
            rol_u = _get_role(udata)
            icon_map = {"admin":"🛡️","pro":"⭐","beca":"🎓","trial":"⏱️",
                        "expirado":"⚠️","inactivo":"🔴"}
            rol_color = icon_map.get(rol_u, "❓")
            days_u = _days_left_local(udata)
            days_txt = f" · {days_u}d restantes" if days_u > 0 else ""

            with st.expander(f"{rol_color} **{uname}** — {udata['nombre']} ({rol_u}{days_txt})"):
                col_i, col_a = st.columns([2, 1])
                with col_i:
                    st.write(f"**Email:** {udata.get('email', '—')}")
                    st.write(f"**Especialidad:** {udata.get('especialidad', '—')}")
                    st.write(f"**Rol actual:** {rol_u}")
                    st.write(f"**Creado:** {udata.get('created', '—')}")
                    st.write(f"**Último acceso:** {udata.get('last_login', 'Nunca')}")
                    if udata.get("trial_end"): st.write(f"**Trial vence:** {udata['trial_end']}")
                    if udata.get("sub_end"): st.write(f"**Acceso vence:** {udata['sub_end']}")
                with col_a:
                    if uname != st.session_state.get("sess_user"):
                        new_end = st.date_input("Activar Premium hasta:", key=f"end_{uname}")
                        if st.button(f"⭐ Activar Premium", key=f"pro_{uname}"):
                            udata["rol"] = "pro"
                            udata["sub_end"] = new_end.strftime("%Y-%m-%d")
                            udata["is_active"] = True
                            st.success(f"✅ {uname} activado como Premium hasta {new_end}")
                            st.rerun()
                        if st.button(f"🎓 Dar beca indef.", key=f"beca_{uname}"):
                            udata["rol"] = "beca"
                            udata["sub_end"] = "2099-12-31"
                            st.success(f"🎓 {uname} tiene beca académica indefinida.")
                            st.rerun()
                        st.markdown("")
                        if udata.get("is_active", True):
                            if st.button(f"🔴 Desactivar", key=f"deact_{uname}"):
                                udata["is_active"] = False
                                st.warning(f"{uname} desactivado.")
                                st.rerun()
                        else:
                            if st.button(f"🟢 Reactivar", key=f"react_{uname}"):
                                udata["is_active"] = True
                                st.success(f"{uname} reactivado.")
                                st.rerun()
                        if st.button(f"🗑️ Eliminar", key=f"del_{uname}", type="primary"):
                            del users_adm[uname]
                            st.error(f"{uname} eliminado.")
                            st.rerun()
                    else:
                        st.info("Tu propia cuenta.")

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
            new_rol = st.selectbox("Rol inicial", ["trial", "pro", "admin"], key="new_rol")
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

    else:
        # Mi cuenta (usuario no admin)
        st.subheader("👤 Mi cuenta")
        _init_db()
        users_mc = st.session_state.get("auth_users", {})
        user_mc = users_mc.get(st.session_state.get("sess_user", ""), {})
        rol_mc = _rol()

        if rol_mc == "guest":
            st.info("Estás en modo invitado. Regístrate para guardar tus prescripciones.")
        else:
            st.write(f"**Nombre:** {user_mc.get('nombre', '—')}")
            st.write(f"**Email:** {user_mc.get('email', '—')}")
            st.write(f"**Especialidad:** {user_mc.get('especialidad', '—')}")
            st.write(f"**Estado:** {rol_mc}")
            if rol_mc == "trial":
                st.info(f"⏱️ Prueba gratuita: **{_days_left(user_mc)} día(s) restante(s)**. "
                        f"Ve a **💳 Premium** para activar tu suscripción.")
            elif rol_mc == "expirado":
                st.warning("⚠️ Tu período de prueba expiró. Ve a **💳 Premium** para activar.")
            elif rol_mc == "pro":
                st.success(f"⭐ Premium activo hasta: **{user_mc.get('sub_end', '—')}**")

            # Cambiar contraseña
            st.divider()
            st.markdown("### 🔑 Cambiar contraseña")
            old_p = st.text_input("Contraseña actual", type="password", key="mc_old")
            new_p1 = st.text_input("Nueva contraseña", type="password", key="mc_new1")
            new_p2 = st.text_input("Confirmar nueva", type="password", key="mc_new2")
            if st.button("Cambiar contraseña", key="btn_chg_pass"):
                if _verify(old_p, user_mc.get("password_hash", "")):
                    if new_p1 == new_p2 and len(new_p1) >= 6:
                        user_mc["password_hash"] = _hash(new_p1)
                        st.success("✅ Contraseña actualizada.")
                    else:
                        st.error("Las contraseñas no coinciden o son muy cortas.")
                else:
                    st.error("Contraseña actual incorrecta.")

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
        ["📐 FG & Estadificación ERC", "🩸 Anemia en ERC", "💊 Medicamentos en ERC/Diálisis"],
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
            st.markdown("#### Ajuste de dosis según respuesta — KDIGO 2012")
            st.caption("Evaluar respuesta cada **4 semanas**. No cambiar dosis antes de 4 semanas.")

            adj1, adj2, adj3 = st.columns(3)
            with adj1:
                aee_actual = st.selectbox("AEE actual",
                                          ["Epoetina alfa", "Darbepoetina alfa",
                                           "Metoxi-PEG-epoetina beta (Mircera®)"], key="aee_adj_tipo")
                if "Epoetina" in aee_actual and "Metoxi" not in aee_actual:
                    dosis_act = st.number_input("Dosis actual (UI/aplicación)", 1000, 40000, 4000, 1000, key="aee_dosis_act")
                    unidad = "UI"
                elif "Darb" in aee_actual:
                    dosis_act = st.number_input("Dosis actual (mcg/aplicación)", 10.0, 500.0, 30.0, 5.0, key="aee_dosis_act")
                    unidad = "mcg"
                else:
                    dosis_act = st.number_input("Dosis actual (mcg/mes)", 30.0, 360.0, 120.0, 30.0, key="aee_dosis_act")
                    unidad = "mcg"
            with adj2:
                hgb_hace4s = st.number_input("Hgb hace 4 semanas (g/dL)", 4.0, 20.0, 9.5, 0.1, key="aee_hgb_prev")
            with adj3:
                delta_hgb = hgb - hgb_hace4s
                st.metric("Δ Hgb en 4 semanas", f"{delta_hgb:+.1f} g/dL")

            # Adjustment logic (KDIGO Table 4)
            dosis_nueva = dosis_act
            if hgb > 13.0:
                accion_aee = "🛑 **SUSPENDER AEE** temporalmente. Hgb >13 g/dL = riesgo cardiovascular."
                dosis_nueva = 0
                color_aee = "error"
            elif hgb > 11.5 and delta_hgb > 0:
                dosis_nueva = dosis_act * 0.75
                accion_aee = (f"⬇️ **REDUCIR 25%**: {dosis_act:.0f} → **{dosis_nueva:.0f} {unidad}**. "
                              "Hgb sobre meta o subiendo hacia 13.")
                color_aee = "warning"
            elif delta_hgb > 2.0:
                dosis_nueva = dosis_act * 0.75
                accion_aee = (f"⬇️ **REDUCIR 25%**: {dosis_act:.0f} → **{dosis_nueva:.0f} {unidad}**. "
                              "Subida demasiado rápida (>2 g/dL en 4 sem).")
                color_aee = "warning"
            elif delta_hgb >= 1.0 and 10.0 <= hgb <= 11.5:
                accion_aee = f"✅ **MANTENER** dosis actual ({dosis_act:.0f} {unidad}). Respuesta adecuada."
                color_aee = "success"
            elif delta_hgb >= 1.0 and hgb < 10.0:
                accion_aee = f"✅ **MANTENER** dosis actual ({dosis_act:.0f} {unidad}). Subida adecuada, aún bajo meta."
                color_aee = "success"
            elif delta_hgb < 1.0 and hgb < 10.0:
                dosis_nueva = dosis_act * 1.25
                accion_aee = (f"⬆️ **AUMENTAR 25%**: {dosis_act:.0f} → **{dosis_nueva:.0f} {unidad}**. "
                              "Respuesta insuficiente (<1 g/dL en 4 sem).")
                color_aee = "warning"
                if crp > 10:
                    accion_aee += f" ⚠️ Verificar: PCR {crp:.0f} mg/L → investigar causas de hiporrespuesta."
            else:
                accion_aee = f"ℹ️ **MANTENER** dosis actual. Evaluar nuevamente en 4 semanas."
                color_aee = "info"

            if color_aee == "success": st.success(accion_aee)
            elif color_aee == "warning": st.warning(accion_aee)
            elif color_aee == "error": st.error(accion_aee)
            else: st.info(accion_aee)

            st.markdown("""
#### Tabla de ajuste KDIGO 2012
| Situación | Acción |
|-----------|--------|
| Hgb **>13 g/dL** | Suspender AEE temporalmente |
| Hgb **>11.5 g/dL** subiendo | ↓ Dosis 25% |
| Δ Hgb **>2 g/dL** en 4 sem | ↓ Dosis 25% |
| Δ Hgb **1–2 g/dL** + Hgb en meta | Mantener dosis |
| Δ Hgb **<1 g/dL** + Hgb <10 | ↑ Dosis 25% |
| Hgb <10 pese a dosis alta* | Investigar hiporrespuesta |

*Hiporrespuesta: Epoetina >300 UI/kg/sem o Darb >1.5 mcg/kg/sem sin alcanzar meta → investigar: déficit de hierro, infección, inflamación, hiperparatiroidismo, hemólisis.
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
    st.subheader("📂 Mis Pacientes — Prescripciones Guardadas")

    rol_actual = _rol()
    uid = _user_id()
    puede_guardar = _can_save()
    db_activa = _DB_ON and _db.db_ok()

    # ── USUARIO FREE: teaser de lo que se verá ────────────────────────────────
    if rol_actual in ("free", "guest", "expirado", "grace"):
        st.info("👀 Así se ve tu historial de pacientes en la versión **Pro**:")

        # Tarjetas de ejemplo borrosas
        ejemplo = [
            {"alias": "Paciente UCI-01", "modality": "CVVHDF", "peso": 72, "anticoag": "Citrato RCA", "created_at": "2025-05-10"},
            {"alias": "Paciente UCI-02", "modality": "CVVH",   "peso": 85, "anticoag": "HNF",         "created_at": "2025-05-09"},
            {"alias": "Paciente UCI-03", "modality": "CVVHD",  "peso": 61, "anticoag": "Citrato RCA", "created_at": "2025-05-08"},
        ]
        st.markdown("""
<style>
.card-blur { filter: blur(4px); pointer-events: none; user-select: none;
             background: #fff; border: 1px solid #BFDBFE; border-left: 4px solid #2563EB;
             border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
</style>""", unsafe_allow_html=True)

        for e in ejemplo:
            st.markdown(f"""
<div class="card-blur">
  <b>🩺 {e['alias']}</b> &nbsp;·&nbsp; {e['modality']} &nbsp;·&nbsp; {e['peso']} kg
  &nbsp;·&nbsp; {e['anticoag']}<br>
  <small style="color:#64748B">Guardado: {e['created_at']}</small>
</div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ✨ Con TRRC360 Pro puedes:")
        col1, col2 = st.columns(2)
        col1.markdown("""
- 📥 Guardar prescripciones TRRC con un clic
- 📂 Acceder a tu historial completo
- 🔍 Buscar pacientes por nombre o fecha
        """)
        col2.markdown("""
- 📊 Ver parámetros de sesiones anteriores
- 📋 Recargar una prescripción guardada
- 🗑️ Eliminar registros cuando quieras
        """)

        if rol_actual == "grace":
            st.warning("⏳ Tu suscripción venció. Tus datos están guardados por 60 días. Renueva para recuperar acceso.")

        if st.button("💳 Activar Pro — $99 MXN/mes", type="primary", key="btn_upgrade_pac"):
            st.session_state["nav_sel"] = "premium"
            st.rerun()

    # ── USUARIO PRO / TRIAL / ADMIN: historial real ────────────────────────────
    else:
        if not db_activa:
            st.warning("⚠️ Base de datos Railway no conectada. Agrega DATABASE_URL en Streamlit Secrets para habilitar el guardado de pacientes.")
        elif uid is None:
            st.warning("⚠️ Inicia sesión con tu cuenta para ver tus pacientes guardados.")
        else:
            prescriptions = _db.get_prescriptions(uid)
            total = len(prescriptions)

            st.markdown(f"**{total} prescripción(es) guardada(s)**")

            if total == 0:
                st.info("Aún no tienes prescripciones guardadas. "
                        "Ve a **🩺 Prescripción** y guarda tu primera sesión con el botón 💾.")
            else:
                # Búsqueda
                buscar = st.text_input("🔍 Buscar por nombre de paciente", key="pac_buscar")
                filtradas = [p for p in prescriptions
                             if buscar.lower() in (p.get("alias") or "").lower()] if buscar else prescriptions

                for p in filtradas:
                    with st.expander(f"🩺 {p.get('alias','—')}  ·  {p.get('modality','—')}  ·  {str(p.get('created_at',''))[:10]}"):
                        pc1, pc2, pc3, pc4 = st.columns(4)
                        pc1.metric("Peso", f"{p.get('peso','—')} kg")
                        pc2.metric("Modalidad", p.get("modality", "—"))
                        pc3.metric("Anticoag.", p.get("anticoag", "—"))
                        pc4.metric("Qeff", f"{p.get('qeff','—')} mL/hr" if p.get('qeff') else "—")
                        if p.get("escenarios"):
                            st.caption(f"📋 Escenarios: {p['escenarios']}")
                        if p.get("notas"):
                            st.caption(f"📝 Notas: {p['notas']}")
                        col_del, _ = st.columns([1, 4])
                        with col_del:
                            if st.button("🗑️ Eliminar", key=f"del_{p['id']}"):
                                _db.delete_prescription(p["id"], uid)
                                st.success("Prescripción eliminada.")
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
                st.markdown(f"""
<div style="border-left:4px solid {color_brd};background:{color_bg};
     padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;">
  <b>{nivel} — {titulo}</b><br>
  <span style="font-size:14px;">{accion}</span>
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
            st.success("✅ Este protocolo fue generado automáticamente por TRRC360 según la anticoagulación seleccionada. "
                       "Siempre seguir indicaciones específicas del médico tratante.")

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"© Dr. Josué Tapia Nefrólogo — TRRC360 {VERSION} — Uso académico exclusivo | "
    "Nefrología / Medicina Crítica | León, Gto., México"
)

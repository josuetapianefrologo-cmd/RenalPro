# ============================================================
# renalpro_consulta.py
# RenalPro v3.1.0 | TRRC360 — Módulo: Consulta Completa
# Incluye: Labs mejorados, Receta integrada, Flujo consulta, PDF Resumen Médico
#
# Importar en app.py:
#   from renalpro_consulta import render_consultation_complete
# ============================================================

import json
import base64
from io import BytesIO
from datetime import date, datetime

import streamlit as st
import psycopg2
import psycopg2.extras

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether,
)

from renalpro_patient import calcular_edad_exacta

# ─── Configuración de Laboratorios ──────────────────────────────────────────

LABS_CONFIG = {
    "🔬 Función Renal": [
        ("cr",        "Cr (mg/dL)",    0.5,   1.2),
        ("urea",      "Urea (mg/dL)",  10,    50),      # ← NUEVO
        ("bun",       "BUN (mg/dL)",   5,     20),
        ("ac_urico",  "Ac. Úrico (mg/dL)", 2.4, 6.0),
    ],
    "⚡ Electrolitos": [
        ("k",    "K (mEq/L)",    3.5, 5.0),
        ("na",   "Na (mEq/L)",   136, 145),
        ("hco3", "HCO₃ (mEq/L)", 22,  29),
        ("cl",   "Cl (mEq/L)",   98,  106),
        ("mg",   "Mg (mg/dL)",   1.7, 2.2),
    ],
    "🩸 Biometría": [
        ("hb",        "Hb (g/dL)",       12,    17),
        ("hto",       "Hto (%)",          36,    50),
        ("vcm",       "VCM (fL)",         80,    100),
        ("chcm",      "CHCM (g/dL)",      32,    36),
        ("leucos",    "Leucos (/mm³)",    4500,  11000),
        ("plaquetas", "Plaquetas (/mm³)", 150000, 400000),
    ],
    "🔥 Inflamación": [
        ("pcr",      "PCR (mg/L)",    0,   10),
        ("albumina", "Albúmina (g/dL)", 3.5, 5.0),
    ],
    "🦴 Metabolismo Óseo": [
        ("ca",    "Ca (mg/dL)",          8.5,  10.5),
        ("p",     "P (mg/dL)",           2.5,  4.5),
        ("pthi",  "PTHi (pg/mL)",        15,   65),
        ("vitd",  "25-OH Vit D (ng/mL)", 30,   100),   # ← NUEVO
    ],
    "🩺 Anemia ERC": [
        ("ferritina", "Ferritina (ng/mL)", 30,  500),
        ("ist",       "IST (%)",           20,  50),
        ("reticuloc", "Reticulocitos (%)", 0.5, 2.5),
    ],
    "🍬 Hígado / Glucosa": [
        ("glucosa",    "Glucosa (mg/dL)",  70,  100),
        ("hba1c",      "HbA1c (%)",        4,   5.7),
        ("alt",        "ALT (U/L)",        7,   56),
        ("ast",        "AST (U/L)",        10,  40),
        ("bilirrubina","Bilirrubina T (mg/dL)", 0, 1.2),
        ("col_total",  "Colesterol T (mg/dL)", 0, 200),
        ("tg",         "Triglicéridos (mg/dL)", 0, 150),
        ("ldl",        "LDL (mg/dL)",      0,   100),
    ],
    "💊 Trasplante": [
        ("tacrolimus",  "Tacrolimus C0 (ng/mL)", 5,  10),
        ("csa",         "CsA C0 (ng/mL)",        100, 200),
        ("everolimus",  "Everolimus C0 (ng/mL)",  3,  8),
        ("sirrolimus",  "Sirrolimus C0 (ng/mL)",  4,  12),
    ],
    "🚽 Orina": [
        ("creatinuria",  "Creatinuria (mg/dL)", None, None),
        ("albumin_ori",  "Albuminuria (mg/dL)", None, None),
        ("acr",          "Cociente ACR (mg/g)", None, None),
        ("prot_orina",   "Proteínas orina (mg/dL)", None, None),
        ("ego_leu",      "EGO Leucos (x cpo)", None, None),
        ("ego_eri",      "EGO Eritrocitos (x cpo)", None, None),
    ],
}

# ─── Listado de medicamentos (fallback si no hay DB) ─────────────────────────

MEDICAMENTOS_NEFRO = [
    # Inmunosupresores
    {"nombre": "Tacrolimus", "marcas": "Prograf, Advagraf", "dosis_default": "2 mg c/12h VO"},
    {"nombre": "Micofenolato de mofetilo", "marcas": "CellCept, MMF", "dosis_default": "500 mg c/12h VO"},
    {"nombre": "Micofenolato sódico", "marcas": "Myfortic", "dosis_default": "360 mg c/12h VO"},
    {"nombre": "Ciclosporina A", "marcas": "Neoral, Sandimmune", "dosis_default": "100 mg c/12h VO"},
    {"nombre": "Prednisolona", "marcas": "Meticorten", "dosis_default": "5 mg c/24h VO"},
    {"nombre": "Prednisona", "marcas": "Prednisona", "dosis_default": "5 mg c/24h VO"},
    {"nombre": "Azatioprina", "marcas": "Imuran", "dosis_default": "100 mg c/24h VO"},
    {"nombre": "Everolimus", "marcas": "Certican", "dosis_default": "0.75 mg c/12h VO"},
    {"nombre": "Sirolimus", "marcas": "Rapamune", "dosis_default": "2 mg c/24h VO"},
    {"nombre": "Belatacept", "marcas": "Nulojix", "dosis_default": "10 mg/kg IV mensual"},
    # Antihipertensivos
    {"nombre": "Amlodipino", "marcas": "Norvasc", "dosis_default": "5 mg c/24h VO"},
    {"nombre": "Nifedipino LP", "marcas": "Adalat", "dosis_default": "30 mg c/24h VO"},
    {"nombre": "Telmisartán", "marcas": "Micardis", "dosis_default": "40 mg c/24h VO"},
    {"nombre": "Losartán", "marcas": "Cozaar", "dosis_default": "50 mg c/24h VO"},
    {"nombre": "Enalapril", "marcas": "Renitec", "dosis_default": "5 mg c/12h VO"},
    {"nombre": "Bisoprolol", "marcas": "Concor", "dosis_default": "5 mg c/24h VO"},
    {"nombre": "Carvedilol", "marcas": "Coreg", "dosis_default": "6.25 mg c/12h VO"},
    {"nombre": "Doxazosina", "marcas": "Cardura", "dosis_default": "2 mg c/24h VO"},
    {"nombre": "Clonidina", "marcas": "Catapresan", "dosis_default": "0.1 mg c/12h VO"},
    {"nombre": "Hidralazina", "marcas": "Apresolina", "dosis_default": "25 mg c/8h VO"},
    # Diuréticos
    {"nombre": "Furosemida", "marcas": "Lasix", "dosis_default": "40 mg c/24h VO"},
    {"nombre": "Torasemida", "marcas": "Torem", "dosis_default": "10 mg c/24h VO"},
    {"nombre": "Espironolactona", "marcas": "Aldactone", "dosis_default": "25 mg c/24h VO"},
    # Anemia / Eritropoyesis
    {"nombre": "Eritropoyetina alfa", "marcas": "Hemax, Epogen", "dosis_default": "4000 UI SC c/semana"},
    {"nombre": "Darbepoetina alfa", "marcas": "Aranesp", "dosis_default": "40 mcg SC c/2 semanas"},
    {"nombre": "Metoxipolietilenglicol-epoetina beta", "marcas": "Mircera", "dosis_default": "120 mcg SC c/mes"},
    {"nombre": "Hierro sacarosa IV", "marcas": "Venofer", "dosis_default": "200 mg IV en 100 mL NaCl post-HD"},
    {"nombre": "Carboximaltosa férrica", "marcas": "Ferinject", "dosis_default": "500 mg IV"},
    {"nombre": "Hierro polimaltosa", "marcas": "Ferrum Hausmann", "dosis_default": "100 mg c/24h VO"},
    # Metabolismo mineral
    {"nombre": "Calcitriol", "marcas": "Rocaltrol", "dosis_default": "0.25 mcg c/24h VO"},
    {"nombre": "Paricalcitol", "marcas": "Zemplar", "dosis_default": "5 mcg IV 3x/semana (post-HD)"},
    {"nombre": "Carbonato de calcio", "marcas": "Caltrate", "dosis_default": "500 mg c/8h VO (con alimentos)"},
    {"nombre": "Sevelamer", "marcas": "Renvela, Renagel", "dosis_default": "800 mg c/8h VO (con alimentos)"},
    {"nombre": "Lantano", "marcas": "Fosrenol", "dosis_default": "750 mg c/8h VO (masticar)"},
    {"nombre": "Cinacalcet", "marcas": "Sensipar, Mimpara", "dosis_default": "30 mg c/24h VO"},
    # Diabetes
    {"nombre": "Insulina glargina", "marcas": "Lantus, Toujeo", "dosis_default": "10 UI SC al dormir"},
    {"nombre": "Insulina lispro", "marcas": "Humalog", "dosis_default": "4 UI SC c/alimento"},
    {"nombre": "Dapagliflozina", "marcas": "Forxiga", "dosis_default": "10 mg c/24h VO"},
    {"nombre": "Empagliflozina", "marcas": "Jardiance", "dosis_default": "10 mg c/24h VO"},
    # Lípidos
    {"nombre": "Atorvastatina", "marcas": "Lipitor", "dosis_default": "20 mg c/24h VO (noche)"},
    {"nombre": "Rosuvastatina", "marcas": "Crestor", "dosis_default": "10 mg c/24h VO (noche)"},
    # Otros nefro
    {"nombre": "Bicarbonato de sodio", "marcas": "NaHCO3", "dosis_default": "1 g c/8h VO"},
    {"nombre": "Alopurinol", "marcas": "Zyloric", "dosis_default": "100 mg c/24h VO"},
    {"nombre": "Finerenona", "marcas": "Kerendia", "dosis_default": "10 mg c/24h VO"},
    {"nombre": "Omeprazol", "marcas": "Losec, Omeprazol", "dosis_default": "20 mg c/24h VO (en ayunas)"},
    {"nombre": "Pantoprazol", "marcas": "Ulcopen", "dosis_default": "40 mg c/24h VO"},
    {"nombre": "Trimetoprim/Sulfametoxazol", "marcas": "Bactrim", "dosis_default": "80/400 mg c/24h VO (profilaxis)"},
    {"nombre": "Valganciclovir", "marcas": "Valcyte", "dosis_default": "450 mg c/24h VO (ajustar a FG)"},
]

INTERACCIONES_CRITICAS = [
    ({"tacrolimus", "claritromicina"}, "🔴 CRÍTICA: Claritromicina inhibe CYP3A4 — niveles de Tacrolimus ↑↑"),
    ({"tacrolimus", "fluconazol"}, "🔴 CRÍTICA: Fluconazol inhibe CYP3A4 — niveles de Tacrolimus ↑↑↑"),
    ({"tacrolimus", "rifampicina"}, "🔴 CRÍTICA: Rifampicina induce CYP3A4 — niveles de Tacrolimus ↓↓↓"),
    ({"ciclosporina a", "estatina"}, "🟠 MODERADA: Riesgo de miopatía — monitorear CPK"),
    ({"tacrolimus", "aine"}, "🟠 MODERADA: Riesgo de nefrotoxicidad aditiva"),
    ({"tacrolimus", "potasio"}, "🟡 LEVE: Tacrolimus puede elevar K sérico — monitorear"),
    ({"enalapril", "losartán"}, "🟠 MODERADA: Doble bloqueo SRAA — riesgo de hipercalemia e IRA"),
    ({"enalapril", "telmisartán"}, "🟠 MODERADA: Doble bloqueo SRAA — riesgo de hipercalemia e IRA"),
    ({"dapagliflozina", "furosemida"}, "🟡 LEVE: Riesgo de depleción de volumen — monitorear TA"),
    ({"espironolactona", "enalapril"}, "🟠 MODERADA: Riesgo de hipercalemia — monitorear K"),
    ({"espironolactona", "losartán"}, "🟠 MODERADA: Riesgo de hipercalemia — monitorear K"),
]


def verificar_interacciones(meds_list):
    """Verifica interacciones entre la lista de medicamentos seleccionados."""
    nombres = {m["nombre"].lower() for m in meds_list}
    alertas = []
    for par, msg in INTERACCIONES_CRITICAS:
        # Chequeo simple por palabras clave
        if all(any(kw in n for n in nombres) for kw in par):
            alertas.append(msg)
    return alertas


# ─── DB helpers ─────────────────────────────────────────────────────────────

def get_medicamentos_catalogo(conn):
    """
    Carga medicamentos desde la DB. Si falla o no existe la tabla,
    retorna el catálogo hardcoded.
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM medicamentos ORDER BY nombre")
            rows = cur.fetchall()
            if rows:
                return [dict(r) for r in rows]
    except Exception:
        pass
    return MEDICAMENTOS_NEFRO


def save_consultation_record(conn, user_id, patient_id, data):
    """
    Guarda o actualiza el registro de consulta en clinical_records.
    Retorna el id del registro guardado.
    """
    labs_json = json.dumps(data.get("labs", {}), ensure_ascii=False)
    meds_json = json.dumps(data.get("medicamentos", []), ensure_ascii=False)
    sv_json   = json.dumps(data.get("signos_vitales", {}), ensure_ascii=False)

    proxima = data.get("proxima_cita") or None
    if isinstance(proxima, str) and proxima:
        try:
            proxima = datetime.strptime(proxima, "%Y-%m-%d").date()
        except Exception:
            proxima = None

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO clinical_records (
                user_id, patient_id, fecha_registro,
                anamnesis, exploracion_fisica, analisis_apreciativo,
                interconsulta, estudios_solicitados, proxima_cita,
                medicamentos_json, labs_json, indicaciones_extra,
                signos_vitales_json, notes
            ) VALUES (
                %s, %s, NOW(),
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            ) RETURNING id
        """, (
            user_id, patient_id,
            data.get("anamnesis", ""),
            data.get("exploracion_fisica", ""),
            data.get("analisis_apreciativo", ""),
            data.get("interconsulta", ""),
            data.get("estudios_solicitados", ""),
            proxima,
            meds_json, labs_json,
            data.get("indicaciones_extra", ""),
            sv_json,
            data.get("indicaciones", ""),  # campo notes existente
        ))
        record_id = cur.fetchone()[0]
    conn.commit()
    return record_id


def get_last_prescription(conn, patient_id):
    """Recupera la última receta del paciente (para pre-cargar)."""
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT medicamentos_json FROM clinical_records
                WHERE patient_id = %s AND medicamentos_json IS NOT NULL
                ORDER BY fecha_registro DESC LIMIT 1
            """, (patient_id,))
            row = cur.fetchone()
            if row and row["medicamentos_json"]:
                return json.loads(row["medicamentos_json"]) if isinstance(
                    row["medicamentos_json"], str) else row["medicamentos_json"]
    except Exception:
        pass
    return []


def get_next_folio_consulta(conn, user_id):
    """Obtiene el siguiente folio de consulta para el médico."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) + 1 FROM clinical_records WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()[0]
    except Exception:
        return 1


# ─── Sub-módulo: Sección de Laboratorios ────────────────────────────────────

def _lab_input(label, key, normal_low=None, normal_high=None):
    """
    Campo de laboratorio con click-to-clear.
    Retorna float o None.
    El placeholder '—' aparece si el campo está vacío.
    Al hacer clic se limpia automáticamente (comportamiento nativo de text_input).
    """
    val_str = st.text_input(
        label,
        value=st.session_state.get(f"_lab_val_{key}", ""),
        placeholder="—",
        key=key,
        label_visibility="visible",
    )
    # Guardar en session state para persistencia dentro de la sesión
    st.session_state[f"_lab_val_{key}"] = val_str

    if val_str.strip() == "" or val_str.strip() == "—":
        return None

    try:
        val = float(val_str.replace(",", "."))
    except ValueError:
        st.markdown(
            '<span style="color:orange;font-size:0.72em">⚠ Valor inválido</span>',
            unsafe_allow_html=True,
        )
        return None

    # Colorear si fuera de rango
    if normal_low is not None and normal_high is not None:
        if val < normal_low or val > normal_high:
            st.markdown(
                f'<span style="color:#E74C3C;font-size:0.72em">'
                f'↕ Rango: {normal_low}–{normal_high}</span>',
                unsafe_allow_html=True,
            )
    return val


def render_labs_section(key_prefix="labs", initial_labs=None):
    """
    Renderiza el panel de laboratorios ampliado con click-to-clear.
    Retorna dict {campo: valor_float}.
    initial_labs: dict opcional para pre-llenar valores (edición).
    """
    labs = {}
    init = initial_labs or {}

    # Pre-cargar valores iniciales en session state
    for cat, campos in LABS_CONFIG.items():
        for campo, label, lo, hi in campos:
            sk = f"_lab_val_{key_prefix}_{campo}"
            if sk not in st.session_state and campo in init and init[campo]:
                st.session_state[sk] = str(init[campo])

    for cat, campos in LABS_CONFIG.items():
        with st.expander(cat, expanded=(cat in ("🔬 Función Renal", "⚡ Electrolitos",
                                                 "🩸 Biometría", "🦴 Metabolismo Óseo"))):
            cols = st.columns(4)
            for i, (campo, label, lo, hi) in enumerate(campos):
                with cols[i % 4]:
                    val = _lab_input(label, f"{key_prefix}_{campo}", lo, hi)
                    if val is not None:
                        labs[campo] = val
    return labs


def labs_to_text(labs: dict) -> str:
    """Convierte el dict de labs a texto legible para el PDF."""
    if not labs:
        return "No se registraron laboratorios en esta consulta."
    lineas = []
    for cat, campos in LABS_CONFIG.items():
        resultados = [(label, labs[campo]) for campo, label, *_ in campos if campo in labs]
        if resultados:
            lineas.append(cat.split(" ", 1)[-1] + ":")
            lineas.append("  " + " | ".join(f"{l}: {v}" for l, v in resultados))
    return "\n".join(lineas)


# ─── Sub-módulo: Receta integrada ────────────────────────────────────────────

def render_prescription_embedded(conn, user_data, patient_id, key_prefix="rx"):
    """
    Módulo completo de receta dentro de la consulta.
    Retorna dict con {medicamentos: list, indicaciones_extra: str}.
    """
    catalogo = get_medicamentos_catalogo(conn)
    nombres_catalogo = ["— Buscar medicamento —"] + [
        f"{m['nombre']} ({m.get('marcas', '')})" for m in catalogo
    ]

    # Inicializar lista de meds en session state
    sk_meds = f"{key_prefix}_meds_list"
    if sk_meds not in st.session_state:
        previos = get_last_prescription(conn, patient_id)
        st.session_state[sk_meds] = previos if previos else []

    meds_list = st.session_state[sk_meds]

    # ── Buscador ────────────────────────────────────────────────────────
    st.markdown("**💊 Agregar medicamento**")
    c1, c2 = st.columns([3, 2])
    med_sel = c1.selectbox("Buscar en catálogo", nombres_catalogo,
                            key=f"{key_prefix}_buscar")
    texto_libre = c2.text_input("O escribir nombre directo",
                                 key=f"{key_prefix}_libre",
                                 placeholder="Ej: Metildopa 500 mg")

    c1, c2, c3 = st.columns([2, 2, 1])
    dosis_input = c1.text_input("Dosis e instrucciones",
                                 key=f"{key_prefix}_dosis",
                                 placeholder="Ej: 2 mg c/12h VO con alimentos")

    # Pre-llenar dosis si viene del catálogo
    if med_sel != "— Buscar medicamento —" and not dosis_input:
        idx = nombres_catalogo.index(med_sel) - 1
        if 0 <= idx < len(catalogo):
            dosis_input = catalogo[idx].get("dosis_default", "")

    duracion_input = c2.text_input("Duración / cantidad",
                                    key=f"{key_prefix}_dur",
                                    placeholder="30 días / hasta nueva valoración")

    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Agregar", key=f"{key_prefix}_add"):
            nombre_med = (
                texto_libre.strip()
                if texto_libre.strip()
                else (catalogo[nombres_catalogo.index(med_sel) - 1]["nombre"]
                      if med_sel != "— Buscar medicamento —" else "")
            )
            if nombre_med:
                meds_list.append({
                    "nombre": nombre_med,
                    "dosis": dosis_input.strip(),
                    "duracion": duracion_input.strip(),
                })
                st.session_state[sk_meds] = meds_list
                st.rerun()

    # ── Lista actual ────────────────────────────────────────────────────
    if meds_list:
        st.markdown("**Medicamentos en esta consulta:**")
        for i, med in enumerate(meds_list):
            c1, c2, c3, c4 = st.columns([3, 3, 2, 0.7])
            c1.markdown(f"**{i+1}. {med['nombre']}**")
            c2.markdown(f"*{med.get('dosis','—')}*")
            c3.markdown(f"{med.get('duracion','')}")
            if c4.button("🗑", key=f"{key_prefix}_del_{i}"):
                meds_list.pop(i)
                st.session_state[sk_meds] = meds_list
                st.rerun()

        # ── Interacciones ───────────────────────────────────────────────
        alertas = verificar_interacciones(meds_list)
        if alertas:
            for alerta in alertas:
                nivel = "error" if "🔴" in alerta else "warning" if "🟠" in alerta else "info"
                getattr(st, nivel)(alerta)

    if st.button("🗑️ Limpiar receta completa", key=f"{key_prefix}_clear"):
        st.session_state[sk_meds] = []
        st.rerun()

    # ── Indicaciones adicionales ─────────────────────────────────────────
    st.markdown("**Indicaciones adicionales:**")
    ind_extra = st.text_area("", key=f"{key_prefix}_ind_extra", height=70,
                              placeholder="- Evitar ingesta de alcohol\n- Dieta hiposódica\n- Control de TA en casa")

    return {
        "medicamentos": meds_list,
        "indicaciones_extra": ind_extra,
    }


# ─── Módulo principal: Consulta Completa ────────────────────────────────────

def render_consultation_complete(conn, user_id, patient_id, patient_data, user_data):
    """
    Renderiza el flujo completo de consulta.
    Incluye: SV → Nota → Labs → EF → Análisis → Plan/Receta → Interconsulta → Estudios → Próxima cita → Guardar → Resumen PDF

    Uso en app.py (dentro del tab de consulta del expediente):
        from renalpro_consulta import render_consultation_complete
        render_consultation_complete(conn, user_id, patient_id, patient_data, user_data)
    """
    p = patient_data or {}
    kp = f"cons_{patient_id}"

    # Calcular edad exacta
    fecha_nac = p.get("fecha_nacimiento")
    años, meses, dias = calcular_edad_exacta(fecha_nac)
    edad_str = f"{años} años, {meses} meses, {dias} días" if años else "—"

    nombre = p.get("nombre_completo") or (
        f"{p.get('apellido_paterno','')} {p.get('apellido_materno','')}, "
        f"{p.get('nombres','')}").strip()

    st.markdown(f"### 📋 Nueva Consulta — {nombre}")
    st.caption(f"Edad: {edad_str}  |  Expediente: {p.get('id','—')}")

    # ── 1. Signos Vitales Básicos ──────────────────────────────────────
    st.markdown("#### ❤️ Signos Vitales")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    sv_sist = c1.text_input("TA Sist.", key=f"{kp}_sv_sist", placeholder="mmHg")
    sv_diast = c2.text_input("TA Diast.", key=f"{kp}_sv_diast", placeholder="mmHg")
    sv_fc = c3.text_input("FC", key=f"{kp}_sv_fc", placeholder="lpm")
    sv_fr = c4.text_input("FR", key=f"{kp}_sv_fr", placeholder="rpm")
    sv_temp = c5.text_input("Temp", key=f"{kp}_sv_temp", placeholder="°C")
    sv_spo2 = c6.text_input("SpO₂", key=f"{kp}_sv_spo2", placeholder="%")
    c1, c2, c3, c4 = st.columns(4)
    sv_peso = c1.text_input("Peso (kg)", key=f"{kp}_sv_peso")
    sv_talla = c2.text_input("Talla (cm)", key=f"{kp}_sv_talla")
    sv_imc = ""
    if sv_peso and sv_talla:
        try:
            imc = float(sv_peso) / (float(sv_talla) / 100) ** 2
            sv_imc = f"{imc:.2f}"
            c3.metric("IMC", sv_imc)
        except Exception:
            pass
    primera_vez = c4.checkbox("Primera vez en el año", key=f"{kp}_pv")

    st.markdown("---")
    # ── 2. Nota de Evolución ───────────────────────────────────────────
    st.markdown("#### 📝 Nota de Evolución / Anamnesis")
    anamnesis = st.text_area("", key=f"{kp}_anam", height=110,
                              placeholder="Motivo de consulta, evolución del padecimiento, síntomas actuales…")

    # ── 3. Laboratorios ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🧬 Laboratorios")
    labs = render_labs_section(key_prefix=f"{kp}_labs")

    # ── 4. Exploración Física ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🩺 Exploración Física")
    ef = st.text_area("", key=f"{kp}_ef", height=90,
                       placeholder="Consciente, orientado/a. Cardiológico rítmico sin agregados. "
                                   "Pulmonar sin estertores. Abdomen blando. EI: edema ++. "
                                   "Acceso vascular: FAV palpable con thrill…")

    # ── 5. Análisis / Apreciativo ──────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🧠 Análisis / Apreciativo")
    analisis = st.text_area("", key=f"{kp}_analisis", height=90,
                             placeholder="Paciente con ERC G5D en HD, con adecuado/inadecuado control de…\n"
                                        "Se optimiza tratamiento por…")

    # ── 6. Plan / Receta ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💊 Plan de Tratamiento / Receta")
    rx_data = render_prescription_embedded(conn, user_data, patient_id, f"{kp}_rx")

    # Botón imprimir receta
    if rx_data["medicamentos"]:
        if st.button("🖨️ Imprimir Receta", key=f"{kp}_print_rx"):
            rx_pdf = generate_pdf_receta(rx_data, p, user_data, conn)
            st.download_button(
                "⬇️ Descargar Receta PDF",
                data=rx_pdf,
                file_name=f"Receta_{p.get('apellido_paterno','')}"
                          f"_{date.today().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )

    # ── 7. Interconsulta ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔄 Interconsulta")
    interconsulta = st.text_input("Interconsulta a:", key=f"{kp}_interconsulta",
                                   placeholder="Ej: Cardiología — control de HTA post-Tx")

    # ── 8. Estudios solicitados ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🧪 Estudios Requeridos")
    LABS_COMUNES = [
        "Biometría hemática completa",
        "Química sanguínea (glucosa, urea, creatinina, ác. úrico)",
        "Electrolitos séricos (Na, K, Cl, HCO3)",
        "Calcio, fósforo, magnesio sérico",
        "PTH intacta",
        "25-OH Vitamina D",
        "Perfil de hierro (Fe, ferritina, IST)",
        "Perfil hepático (ALT, AST, bilirrubinas)",
        "Perfil de lípidos (CT, TG, LDL, HDL)",
        "HbA1c",
        "Tacrolimus C0",
        "Ciclosporina C0",
        "EGO (examen general de orina)",
        "Proteínas en orina de 24h",
        "Cociente albúmina/creatinina (ACR)",
        "PCR cuantitativa (proteína C reactiva)",
        "Albumina sérica",
        "Hemocultivos (par)",
        "Urocultivo",
        "Rx tórax AP",
        "Electrocardiograma (ECG)",
        "USG renal con Doppler",
        "Ecocardiograma transtorácico",
        "Otro (especificar abajo)",
    ]
    estudios_sel = st.multiselect("Seleccionar estudios", LABS_COMUNES,
                                   key=f"{kp}_est_sel")
    estudio_custom = st.text_area("Estudio adicional / especificación", height=60,
                                   key=f"{kp}_est_custom",
                                   placeholder="Ej: PCR Parvovirus B19, Anticuerpos anti-HLA…")
    estudios_completo = "\n".join([f"{i+1}. {e}" for i, e in enumerate(estudios_sel)])
    if estudio_custom.strip():
        n = len(estudios_sel) + 1
        estudios_completo += "\n" + "\n".join(
            f"{n+j}. {l}" for j, l in enumerate(estudio_custom.strip().split("\n")) if l.strip()
        )

    # ── 9. Próxima cita ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📅 Próxima Cita")
    c1, c2 = st.columns(2)
    prox_cita = c1.date_input("Fecha de próxima cita",
                               value=None, format="DD/MM/YYYY",
                               key=f"{kp}_prox_cita")
    prox_cita_nota = c2.text_input("Nota de próxima cita",
                                    key=f"{kp}_prox_nota",
                                    placeholder="Ej: Semana del 17/08/2026 — con resultados de labs")

    # ── 10. Guardar ────────────────────────────────────────────────────
    st.markdown("---")
    col_save, col_pdf = st.columns(2)

    consulta_data = {
        "signos_vitales": {
            "ta_sist": sv_sist, "ta_diast": sv_diast,
            "fc": sv_fc, "fr": sv_fr, "temp": sv_temp, "spo2": sv_spo2,
            "peso": sv_peso, "talla": sv_talla, "imc": sv_imc,
            "primera_vez": primera_vez,
        },
        "anamnesis": anamnesis,
        "labs": labs,
        "exploracion_fisica": ef,
        "analisis_apreciativo": analisis,
        "medicamentos": rx_data["medicamentos"],
        "indicaciones_extra": rx_data["indicaciones_extra"],
        "interconsulta": interconsulta,
        "estudios_solicitados": estudios_completo,
        "proxima_cita": prox_cita.isoformat() if prox_cita else "",
        "proxima_cita_nota": prox_cita_nota,
        "fecha_consulta": date.today().isoformat(),
        "indicaciones": f"{analisis}\n\nEstudios: {estudios_completo}",
    }

    record_id = st.session_state.get(f"{kp}_saved_id")

    with col_save:
        if st.button("💾 Guardar Consulta", use_container_width=True,
                     key=f"{kp}_save", type="primary"):
            rid = save_consultation_record(conn, user_id, patient_id, consulta_data)
            st.session_state[f"{kp}_saved_id"] = rid
            st.success(f"✅ Consulta guardada correctamente (ID #{rid})")

    with col_pdf:
        if st.button("🖨️ Imprimir Resumen Médico", use_container_width=True,
                     key=f"{kp}_pdf"):
            # Guardar automáticamente antes de imprimir
            rid = save_consultation_record(conn, user_id, patient_id, consulta_data)
            st.session_state[f"{kp}_saved_id"] = rid

            pdf_bytes = generate_pdf_resumen_medico(consulta_data, patient_data, user_data)
            nombre_archivo = (
                f"Resumen_{p.get('apellido_paterno','')}"
                f"_{date.today().strftime('%Y%m%d')}.pdf"
            )
            st.download_button(
                label="⬇️ Descargar Resumen PDF",
                data=pdf_bytes,
                file_name=nombre_archivo,
                mime="application/pdf",
                use_container_width=True,
            )


# ─── Generador PDF: Receta Médica ────────────────────────────────────────────

def generate_pdf_receta(rx_data, patient_data, user_data, conn=None):
    """
    Genera PDF de receta médica en formato Renalmedic.
    Nombre del med en negrita, instrucciones en normal.
    """
    buf = BytesIO()
    p = patient_data or {}
    u = user_data or {}

    doc = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    AZUL = colors.HexColor("#1B4F72")
    s_normal = ParagraphStyle("n", fontSize=9, leading=13, fontName="Helvetica")
    s_bold   = ParagraphStyle("b", fontSize=9, leading=13, fontName="Helvetica-Bold")
    s_title  = ParagraphStyle("t", fontSize=11, leading=15, fontName="Helvetica-Bold",
                               alignment=TA_CENTER)
    s_small  = ParagraphStyle("sm", fontSize=7, leading=10, fontName="Helvetica",
                               textColor=colors.HexColor("#555555"))

    story = []

    # ── Header ─────────────────────────────────────────────────────
    logo_b64 = u.get("logo_b64") or u.get("logo")
    logo_img = None
    if logo_b64:
        try:
            logo_img = RLImage(BytesIO(base64.b64decode(logo_b64)),
                               width=3*cm, height=1.5*cm, kind="proportional")
        except Exception:
            pass

    dir_txt = (f"Av. México #719, Col. Los Paraísos, León, Gto.\n"
               f"Tel: {u.get('telefono_consultorio','477 694-5392')}\n"
               f"Cédula Esp.: {u.get('cedula_especialidad','9940966')}")
    hdr = [[logo_img or Paragraph("<b>RENALMEDIC</b>", s_title),
            Paragraph(dir_txt, s_small),
            Paragraph(f"<b>Fecha: {date.today().strftime('%d/%m/%Y')}</b>", s_bold)]]
    t_hdr = Table(hdr, colWidths=[4*cm, 10*cm, 5*cm])
    t_hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, AZUL),
    ]))
    story.append(t_hdr)
    story.append(Spacer(1, 0.4*cm))

    # ── Datos paciente ──────────────────────────────────────────────
    nombre = p.get("nombre_completo", "")
    story.append(Paragraph(f"<b>Paciente:</b> {nombre}", s_bold))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.3*cm))

    # ── Medicamentos ────────────────────────────────────────────────
    story.append(Paragraph("Medicamentos:", s_bold))
    story.append(Spacer(1, 0.2*cm))
    for i, med in enumerate(rx_data.get("medicamentos", []), 1):
        nombre_m = med.get("nombre", "")
        dosis_m  = med.get("dosis", "")
        dur_m    = med.get("duracion", "")
        linea = f"<b>{i}. {nombre_m}</b> — {dosis_m}"
        if dur_m:
            linea += f" ({dur_m})"
        story.append(Paragraph(linea, s_normal))
        story.append(Spacer(1, 0.1*cm))

    # ── Indicaciones adicionales ────────────────────────────────────
    ind = rx_data.get("indicaciones_extra", "").strip()
    if ind:
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Paragraph("Indicaciones adicionales:", s_bold))
        for linea in ind.split("\n"):
            if linea.strip():
                story.append(Paragraph(f"- {linea.lstrip('- ')}", s_normal))

    # ── Firma ───────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*cm))
    firma_b64 = u.get("firma_b64")
    firma_img = None
    if firma_b64:
        try:
            firma_img = RLImage(BytesIO(base64.b64decode(firma_b64)),
                                width=3*cm, height=1.5*cm, kind="proportional")
        except Exception:
            pass

    medico = u.get("nombre", "Dr. Josué Wigberto Tapia López")
    ced_esp = u.get("cedula_especialidad", "9940966")
    ced_gen = u.get("cedula_general", "6446765")

    fila_firma = [
        [firma_img or Spacer(1, 1.5*cm),
         Paragraph(
             f"<i><b>{medico}</b></i><br/>"
             f"Esp.: Nefrología — Cédula: {ced_esp}<br/>"
             f"Medicina General — Cédula: {ced_gen}",
             s_normal,
         )],
    ]
    t_firma = Table(fila_firma, colWidths=[5*cm, 12*cm])
    t_firma.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(t_firma)

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ─── Generador PDF: Resumen Médico ──────────────────────────────────────────

def generate_pdf_resumen_medico(consulta, patient_data, user_data):
    """
    Genera PDF de Resumen Médico estilo Eleonor adaptado a RenalPro.
    consulta: dict con datos de la consulta (de render_consultation_complete)
    patient_data: dict con datos del paciente
    user_data: dict con datos del médico
    Retorna bytes del PDF.
    """
    buf = BytesIO()
    p = patient_data or {}
    u = user_data or {}
    sv = consulta.get("signos_vitales", {})

    doc = SimpleDocTemplate(buf, pagesize=letter,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    AZUL = colors.HexColor("#1B4F72")
    GRIS_SEC = colors.HexColor("#EBF5FB")

    s_normal  = ParagraphStyle("n", fontSize=9, leading=13, fontName="Helvetica")
    s_bold    = ParagraphStyle("b", fontSize=9, leading=13, fontName="Helvetica-Bold")
    s_section = ParagraphStyle("sec", fontSize=9.5, leading=14,
                                fontName="Helvetica-Bold", textColor=AZUL)
    s_title   = ParagraphStyle("t", fontSize=12, leading=16,
                                fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_small   = ParagraphStyle("sm", fontSize=7, leading=10, fontName="Helvetica",
                                textColor=colors.HexColor("#555555"))
    s_med_nom = ParagraphStyle("mn", fontSize=9, leading=13,
                                fontName="Helvetica-Bold")
    s_right   = ParagraphStyle("r", fontSize=9, leading=13,
                                fontName="Helvetica-Bold", alignment=TA_RIGHT)

    story = []

    # ── Header ─────────────────────────────────────────────────────
    logo_b64 = u.get("logo_b64") or u.get("logo")
    logo_img = None
    if logo_b64:
        try:
            logo_img = RLImage(BytesIO(base64.b64decode(logo_b64)),
                               width=3*cm, height=1.5*cm, kind="proportional")
        except Exception:
            pass

    fecha_consulta = consulta.get("fecha_consulta", date.today().isoformat())
    try:
        fecha_fmt = datetime.strptime(fecha_consulta, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        fecha_fmt = fecha_consulta

    hdr = [
        [logo_img or Paragraph("<b>RENALMEDIC</b>", s_title),
         Paragraph(f"<b>Fecha de consulta: {fecha_fmt}</b>", s_right)],
    ]
    t_hdr = Table(hdr, colWidths=[5*cm, 14*cm])
    t_hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, AZUL),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_hdr)
    story.append(Spacer(1, 0.3*cm))

    # ── Datos del paciente ──────────────────────────────────────────
    nombre = p.get("nombre_completo", "")
    fecha_nac = p.get("fecha_nacimiento")
    años, meses, dias = calcular_edad_exacta(fecha_nac)
    edad_str = f"{años} años, {meses} meses, {dias} días" if años else "—"
    consultorio = u.get("institucion", "Renalmedic")

    story.append(Paragraph(f"<b>Paciente: {nombre}</b>", s_bold))
    story.append(Paragraph(f"Edad: {edad_str}", s_normal))
    story.append(Paragraph(f"Consultorio: {consultorio}", s_normal))
    story.append(Spacer(1, 0.3*cm))

    def sep(titulo):
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#AED6F1")))
        story.append(Paragraph(f"<b>{titulo}</b>", s_section))
        story.append(Spacer(1, 0.1*cm))

    # ── Resumen consulta ────────────────────────────────────────────
    sep("Resumen de consulta")
    story.append(Paragraph(f"Paciente: {nombre}", s_normal))
    story.append(Paragraph(f"Edad: {edad_str}", s_normal))
    story.append(Paragraph(f"Consultorio: {consultorio}", s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Nota de evolución ───────────────────────────────────────────
    sep("Nota de Evolución")
    story.append(Paragraph(consulta.get("anamnesis", ""), s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Signos vitales ──────────────────────────────────────────────
    sep("Signos Vitales / Básicos")
    sv_row = [
        [Paragraph(f"Altura <b>{sv.get('talla','—')} cm</b>", s_normal),
         Paragraph(f"Peso <b>{sv.get('peso','—')} kg</b>", s_normal),
         Paragraph(f"T.A. <b>{sv.get('ta_sist','—')}/{sv.get('ta_diast','—')}</b>", s_normal),
         Paragraph(f"Temp <b>{sv.get('temp','—')} °C</b>", s_normal),
         Paragraph(f"F.C. <b>{sv.get('fc','—')}</b>", s_normal)],
        [Paragraph(f"F.R. <b>{sv.get('fr','—')}</b>", s_normal),
         Paragraph(f"O₂ <b>{sv.get('spo2','—')} %</b>", s_normal),
         Paragraph(f"I.M.C. <b>{sv.get('imc','—')}</b>", s_normal),
         Paragraph(f"Primera vez: <b>{'Sí' if sv.get('primera_vez') else 'No'}</b>", s_normal),
         Paragraph("", s_normal)],
    ]
    t_sv = Table(sv_row, colWidths=[3.8*cm]*5)
    t_sv.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_sv)
    story.append(Spacer(1, 0.2*cm))

    # ── Exploración física ──────────────────────────────────────────
    sep("Exploración Física")
    story.append(Paragraph(consulta.get("exploracion_fisica", ""), s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Laboratorios ────────────────────────────────────────────────
    labs = consulta.get("labs", {})
    if labs:
        sep("Estudios de Laboratorio")
        story.append(Paragraph(labs_to_text(labs), s_normal))
        story.append(Spacer(1, 0.2*cm))

    # ── Análisis ────────────────────────────────────────────────────
    sep("Análisis / Apreciativo")
    story.append(Paragraph(consulta.get("analisis_apreciativo", ""), s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Medicamentos ────────────────────────────────────────────────
    meds = consulta.get("medicamentos", [])
    if meds:
        sep("Medicamentos")
        for med in meds:
            nombre_m = med.get("nombre", "")
            dosis_m  = med.get("dosis", "")
            dur_m    = med.get("duracion", "")
            linea = f"<b>{nombre_m}</b>"
            if dosis_m:
                linea += f" — {dosis_m}"
            if dur_m:
                linea += f" ({dur_m})"
            story.append(Paragraph(linea, s_normal))
        story.append(Spacer(1, 0.15*cm))

    ind = consulta.get("indicaciones_extra", "").strip()
    if ind:
        sep("Indicaciones Adicionales de la Receta")
        for linea in ind.split("\n"):
            if linea.strip():
                story.append(Paragraph(f"- {linea.lstrip('- ')}", s_normal))
        story.append(Spacer(1, 0.15*cm))

    # ── Interconsulta ───────────────────────────────────────────────
    interconsulta = consulta.get("interconsulta", "").strip()
    if interconsulta:
        sep("Interconsulta")
        story.append(Paragraph(interconsulta, s_normal))
        story.append(Spacer(1, 0.15*cm))

    # ── Estudios requeridos ─────────────────────────────────────────
    estudios = consulta.get("estudios_solicitados", "").strip()
    if estudios:
        sep("Estudios Requeridos")
        story.append(Paragraph("<b>Orden de laboratorio</b>", s_bold))
        for linea in estudios.split("\n"):
            if linea.strip():
                story.append(Paragraph(linea, s_normal))
        story.append(Spacer(1, 0.15*cm))

    # ── Próxima cita ────────────────────────────────────────────────
    prox = consulta.get("proxima_cita", "")
    prox_nota = consulta.get("proxima_cita_nota", "")
    if prox or prox_nota:
        sep("Próxima Cita")
        if prox:
            try:
                prox_fmt = datetime.strptime(prox, "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                prox_fmt = prox
            story.append(Paragraph(prox_fmt, s_normal))
        if prox_nota:
            story.append(Paragraph(prox_nota, s_normal))
        story.append(Spacer(1, 0.3*cm))

    # ── Firma ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    firma_b64 = u.get("firma_b64")
    firma_img = None
    if firma_b64:
        try:
            firma_img = RLImage(BytesIO(base64.b64decode(firma_b64)),
                                width=3*cm, height=1.5*cm, kind="proportional")
        except Exception:
            pass

    medico = u.get("nombre", "Dr. Josué Wigberto Tapia López")
    ced_esp = u.get("cedula_especialidad", "9940966")
    ced_gen = u.get("cedula_general", "6446765")

    fila_firma = [
        [firma_img or Spacer(1, 1.5*cm),
         Paragraph(
             f"<i><b>Nombre del médico: {medico}</b></i><br/>"
             f"Esp.: Nefrología | Cédula: {ced_esp}<br/>"
             f"Medicina General | Cédula: {ced_gen}",
             s_normal,
         )],
    ]
    t_firma = Table(fila_firma, colWidths=[5*cm, 14*cm])
    t_firma.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(t_firma)

    # ── Footer ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"<font size='6' color='grey'>RenalPro v3.1.0 / TRRC360 — "
        f"Generado {datetime.now().strftime('%d/%m/%Y %H:%M')} — RENALMEDIC LEON</font>",
        ParagraphStyle("foot", fontSize=6, alignment=TA_CENTER,
                       textColor=colors.HexColor("#888888")),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

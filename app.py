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
from math import log
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

VERSION = "v2.1.0"

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
/* Fondo principal */
.stApp { background-color: #0f1624; }
/* Sidebar */
section[data-testid="stSidebar"] { background-color: #111827; }
section[data-testid="stSidebar"] .stMarkdown p { color: #94a3b8; }
/* Metric cards */
[data-testid="metric-container"] {
    background: #1a2535 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
}
[data-testid="stMetricValue"] { color: #38bdf8 !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #7dd3fc !important; font-size: 12px !important; }
[data-testid="stMetricDelta"] { color: #22c55e !important; }
/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: #111827;
    border-radius: 8px;
    padding: 3px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important;
    background-color: transparent !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    padding: 6px 10px !important;
}
.stTabs [aria-selected="true"] {
    color: #38bdf8 !important;
    background-color: #1e293b !important;
}
/* Headings */
.stApp h1 { color: #38bdf8 !important; }
.stApp h2 { color: #7dd3fc !important; }
.stApp h3 { color: #bae6fd !important; }
/* Dividers */
hr { border-color: #1e293b !important; margin: 10px 0 !important; }
/* Buttons */
.stButton > button {
    background-color: #0e4d7b !important;
    color: #e2e8f0 !important;
    border: 1px solid #1e6fa8 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stButton > button:hover {
    background-color: #2563eb !important;
    border-color: #3b82f6 !important;
}
/* Download button */
.stDownloadButton > button {
    background-color: #065f46 !important;
    color: #ecfdf5 !important;
    border: 1px solid #059669 !important;
    border-radius: 8px !important;
}
/* Tables in markdown */
[data-testid="stMarkdownContainer"] table {
    background: #1a2535;
    border-radius: 8px;
    width: 100%;
    border-collapse: collapse;
}
[data-testid="stMarkdownContainer"] th {
    background: #0e4d7b;
    color: #bae6fd !important;
    padding: 8px 12px;
}
[data-testid="stMarkdownContainer"] td {
    color: #e2e8f0 !important;
    padding: 6px 12px;
    border-bottom: 1px solid #1e293b;
}
/* Checkbox and radio */
.stCheckbox label, .stRadio label { color: #e2e8f0 !important; }
/* Expander */
.streamlit-expanderHeader { color: #7dd3fc !important; }
/* Caption */
.stCaption { color: #475569 !important; }
/* Success / Info / Warning / Error boxes */
div[data-testid="stAlert"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ─── CONSENT GATE ─────────────────────────────────────────────────────────────
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = True
if "consent_ok" not in st.session_state:
    st.session_state.consent_ok = False

def _consent_gate():
    st.title("⚖️ Aviso de confidencialidad y descargo de responsabilidad")
    st.markdown("""
Esta herramienta es de **uso académico** y **no sustituye** el juicio clínico profesional
ni constituye una prescripción médica formal. Los datos introducidos se tratan de forma
**confidencial** dentro de esta sesión y **no** se almacenan permanentemente.
    """)
    agree = st.checkbox("He leído y acepto el aviso.", key="consent_chk")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.button("Aceptar y continuar", type="primary", disabled=not agree,
                  on_click=lambda: st.session_state.update({"consent_ok": True}))
    with col_b:
        st.button("Salir", on_click=lambda: st.session_state.update({"consent_ok": False}))
    if not st.session_state.get("consent_ok", False):
        st.stop()

if not st.session_state.get("consent_ok", False):
    _consent_gate()

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

# ─── HEADER ───────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 7])
with col_logo:
    try:
        st.image("logo.png", width=90)
    except Exception:
        st.markdown("### 🩺")
with col_title:
    st.title(f"TRRC360 by Dr. Tapia — {VERSION}")
    st.caption("Herramienta clínica de uso académico — Nefrología / Medicina Crítica")

if st.button("🔁 Actualizar", help="Borrar caché y recargar", key="btn_refresh"):
    try:
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass
    st.rerun()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Modo")
    doc_mode = st.checkbox("🎓 Modo docente extendido", value=st.session_state.get("doc_mode", False),
                           key="doc_mode", help="Activa explicación extendida en UI y PDF.")
    st.session_state["pdf_extendido"] = bool(doc_mode)
    st.session_state["mostrar_fund_extendido"] = bool(doc_mode)

    st.header("Parámetros básicos TRRC")
    peso = st.number_input("Peso (kg)", 10.0, 300.0, 70.0, 0.5, key="sb_peso")
    hto = st.number_input("Hematocrito (fracción)", 0.10, 0.60, 0.30, 0.01, format="%.2f", key="sb_hto",
                          help="0.30 = 30%")
    qb = st.number_input("Qb (mL/min)", 80, 300, 200, 10, key="sb_qb")
    uf = st.number_input("UF neta (mL/h)", 0, 2000, 100, 10, key="sb_uf")
    dosis_mlkg = st.slider("Dosis objetivo (mL/kg/h)", 10, 45, 30, key="sb_dosis",
                           help="Objetivo habitual: 20–25 mL/kg/h")

    st.markdown("---")
    st.subheader("Escenario(s) clínico(s)")
    escenarios_catalogo = [
        "Sepsis / choque séptico", "Choque cardiogénico", "Post infarto",
        "Neurocrítico / TCE", "Sobrecarga hídrica aislada", "Intoxicación / sobredosis",
        "Hiponatremia severa", "Hipernatremia", "Hiperamonemia",
        "Rabdomiólisis", "Síndrome de liberación de citocinas",
    ]
    escenarios = st.multiselect("Selecciona hasta 3", escenarios_catalogo, max_selections=3,
                                default=["Sepsis / choque séptico"], key="sb_escenarios")

# ─── TABS ─────────────────────────────────────────────────────────────────────
(tab_main, tab_citrato, tab_na_trrc, tab_hd, tab_tpe,
 tab_ktv, tab_balance, tab_anticoag, tab_fund,
 tab_resumen, tab_refs) = st.tabs([
    "🩺 Prescripción",
    "🧪 Citrato RCA",
    "🧂 Sodio TRRC",
    "💉 Predicción HD",
    "🔄 Plasmaféresis",
    "📐 Kt/V",
    "⚖️ Balance",
    "💊 Anticoagulación",
    "📚 Fundamento",
    "📋 Resumen / Impresión",
    "📖 Referencias",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: PRESCRIPCIÓN TRRC
# ══════════════════════════════════════════════════════════════════════════════
with tab_main:
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
        st.session_state["cit_dose"] = float(cit_dose_presc)
        st.session_state["cit_sol_type"] = cit_sol_presc
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: CITRATO REGIONAL (RCA) — COMPLETO
# ══════════════════════════════════════════════════════════════════════════════
with tab_citrato:
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
    vol_viales = num_viales * 10
    vol_total_ca = prep_vol_ml + vol_viales
    ca_conc_mmol_L = total_ca / (vol_total_ca / 1000) if vol_total_ca > 0 else 0
    ca_inf_rate_ml_hr = ca_loss / (ca_conc_mmol_L / 1000) if ca_conc_mmol_L > 0 else 0

    carc1, carc2, carc3, carc4 = st.columns(4)
    carc1.metric("Ca total en bolsa (mmol)", f"{total_ca:.2f}")
    carc2.metric("Volumen total preparación (mL)", f"{vol_total_ca}")
    carc3.metric("Concentración Ca (mmol/L)", f"{ca_conc_mmol_L:.1f}")
    carc4.metric("Tasa infusión inicial (mL/hr)", f"{ca_inf_rate_ml_hr:.0f}")

    st.info(f"📋 **Preparación:** {num_viales} ámpulas gluconato Ca 10% (10mL c/u) + {prep_vol_ml}mL NaCl 0.9% "
            f"→ **{vol_total_ca}mL** con **{ca_conc_mmol_L:.1f} mmol/L** Ca elemental. "
            f"Infundir a **{ca_inf_rate_ml_hr:.0f} mL/hr** por línea sistémica (POSTFILTRO).")
    st.caption("⚠️ El calcio siempre se infunde por línea sistémica post-filtro, NUNCA en la línea de citrato ni en el acceso vascular pre-filtro.")

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
with tab_na_trrc:
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
        cit_sol_tipo_na = st.session_state.get("cit_sol_type", sol_opts[0])
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
with tab_hd:
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
# TAB 5: PLASMAFÉRESIS / TPE
# ══════════════════════════════════════════════════════════════════════════════
with tab_tpe:
    st.subheader("Plasmaféresis Terapéutica (TPE)")

    st.markdown("### Datos del paciente")
    tpe1, tpe2, tpe3 = st.columns(3)
    with tpe1:
        tpe_peso = st.number_input("Peso (kg)", 10.0, 200.0, float(peso), 0.5, key="tpe_peso")
    with tpe2:
        tpe_hct = st.number_input("Hematocrito (%)", 10.0, 60.0, 30.0, 0.5, key="tpe_hct")
    with tpe3:
        tpe_nex = st.number_input("Número de recambios por sesión", 0.5, 4.0, 1.5, 0.1,
                                  key="tpe_nex",
                                  help="1 recambio = 1 VPE. Habitual: 1.0–1.5 recambios.")

    result_tpe = calc_tpe(tpe_peso, tpe_hct, tpe_nex)

    st.markdown("### Volúmenes estimados")
    tpe_r1, tpe_r2 = st.columns(2)
    tpe_r1.metric("Volumen plasmático estimado (VPE)", f"{result_tpe['EPV']:.0f} mL",
                  help="Fórmula: 65 × peso × (1 − Hto)")
    tpe_r2.metric("Volumen a intercambiar", f"{result_tpe['vol_ex']:.0f} mL",
                  help=f"{tpe_nex:.1f} recambios × VPE")

    st.divider()
    st.markdown("### Cinética de macromoléculas — 1 sesión (pool intravascular)")
    st.caption("Aplica para IgG. Reducción intravascular por sesión.")
    cs1, cs2 = st.columns(2)
    cs1.metric("Reducción (intravascular)", f"{result_tpe['red1']:.1f}%")
    cs2.metric("Residual (intravascular)", f"{result_tpe['res1']:.1f}%")

    st.divider()
    st.markdown("### Cinética IgG total — múltiples sesiones")
    st.caption("Con redistribución extravascular entre sesiones (fracción IV ≈ 45%, EV ≈ 55%). "
               "Tras cada sesión la IgG extravascular redistribuye parcialmente al compartimento IV.")
    tpe_nsess = st.number_input("Número total de sesiones", 1, 20, 5, 1, key="tpe_nsess")
    result_multi = calc_tpe_total(tpe_nex, tpe_nsess)
    cm1, cm2 = st.columns(2)
    cm1.metric("Reducción total de IgG", f"{result_multi['total_red']:.2f}%")
    cm2.metric("Residual total de IgG", f"{result_multi['total_res']:.2f}%")

    st.divider()
    st.markdown("### Calculadora de albúmina (líquido de reemplazo)")
    st.caption("Para cuando se usa albúmina como líquido de reemplazo en TPE.")
    alb1, alb2, alb3 = st.columns(3)
    with alb1:
        alb_pct_vial = st.selectbox("Albúmina en vial (%)", [5, 20, 25], index=1, key="alb_pct_vial")
    with alb2:
        alb_pct_des = st.number_input("% albúmina final deseado", 1.0, 10.0, 5.0, 0.5,
                                      key="alb_pct_des")
    with alb3:
        alb_prep_str = st.selectbox("Volumen de preparación", ["250 mL", "500 mL", "1000 mL"],
                                    index=2, key="alb_prep")
        alb_prep_ml = int(alb_prep_str.replace(" mL", ""))

    viales_alb = calc_albumin_tpe(alb_pct_vial, alb_pct_des, alb_prep_ml)
    st.metric("Número de viales necesarios", f"{viales_alb} viales",
              help=f"Fórmula: (%des × vol_prep) / (%vial × 50mL por vial)")
    st.info(f"📋 {viales_alb} viales de albúmina {alb_pct_vial}% (50mL c/u) aforados en {alb_prep_ml}mL "
            f"→ solución al {alb_pct_des:.1f}% de albúmina para reemplazo.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: KT/V POR OBJETIVOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ktv:
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
with tab_balance:
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
with tab_anticoag:
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
    st.caption("RCA es preferente si no hay contraindicaciones (ver Referencias). "
               "Para el cálculo detallado de citrato y calcio, ir a pestaña 🧪 Citrato RCA.")

    if ac.startswith("Heparina"):
        if hbpm_12h == "Sí":
            st.warning("HBPM reciente: considerar diferir HNF o iniciar con dosis reducida.")
        iu_h = peso * 5
        st.info(f"**Dosis inicial HNF sugerida:** {iu_h:.0f} UI/h (ajustar a aPTT objetivo).")
        st.session_state["anticoagulacion_tipo"] = "HNF"
        st.session_state["hnf_ui_h"] = float(iu_h)
    else:
        st.info("💡 Dirígete a la pestaña **🧪 Citrato RCA** para el cálculo completo de tasas y monitoreo.")
        st.session_state["anticoagulacion_tipo"] = "RCA"

# ══════════════════════════════════════════════════════════════════════════════
# TAB 9: FUNDAMENTO Y CÁLCULOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_fund:
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
with tab_resumen:
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
        vol_viales_rs = int(num_viales_rs) * 10
        vol_total_rs = prep_vol_rs + vol_viales_rs
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
        if st.button("📄 Generar y descargar PDF", key="btn_export_pdf", use_container_width=True):
            try:
                fn = export_pdf()
                with open(fn, "rb") as f:
                    st.download_button("⬇️ Descargar PDF", data=f, file_name=fn,
                                       mime="application/pdf", use_container_width=True,
                                       key="btn_download_pdf")
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 12: REFERENCIAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_refs:
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

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"© Dr. Josué Tapia Nefrólogo — TRRC360 {VERSION} — Uso académico exclusivo | "
    "Nefrología / Medicina Crítica | León, Gto., México"
)

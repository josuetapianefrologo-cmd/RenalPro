# app.py — TRRC360 by Dr. Tapia (v1.9.1)
import streamlit as st
from math import log
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

# ReportLab para PDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

VERSION = "v1.9.1"

st.set_page_config(page_title="TRRC360 by Dr. Tapia", layout="wide")

# ================== HELPERS PDF ==================
def _s_int(x):
    try:
        return str(int(round(float(x))))
    except Exception:
        return "—"

def _draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=11, leading=14):
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
    bloques = [
        "• Dosis objetivo: Qe = dosis (mL/kg/h) × peso (kg).",
        "• Qp = Qb × (1 − Hto). Qp·h = Qp × 60.",
        "• Límite convectivo: ≤25% de Qp·h para proteger el filtro (FF y coagulación).",
        "• Fracción convectiva (según modalidad): CVVHD=0, CVVHF=1, CVVHDF≈0.6.",
        "• Qr_total = min(Qp·h×0.25, max(Qe − UF, 0)) × fracción_convectiva.",
        "• División 70/30 (pre/post) para balancear depuración y protección de filtro.",
        "• Qd = max(Qe − (Qr_pre + Qr_post + UF), 0).",
        "• FF = (Qr_post + UF) / (Qp·h + Qr_pre). Recomendado mantener FF < 25%.",
        f"Contexto actual: Qb={_s_int(qb)} mL/min, Hto={hto:.2f}, Qp={_s_int(qp)} mL/min, Qp·h={_s_int(qp_h)} mL/h, "
        f"Qe={_s_int(qe)} mL/h, Qr_pre={_s_int(qr_pre)}, Qr_post={_s_int(qr_post)}, Qd={_s_int(qd)}, "
        f"UF={_s_int(uf)}, FF≈{ff_txt}."
    ]
    return bloques

def _fundamento_texto_extendido(na, k, ph, pam, vasopresor_alto, lactato_desc, albumina,
                                anticoag_tipo, r_targets, filtro_final):
    partes = [
        "— Selección de modalidad —",
        "• CVVHDF en sepsis/choque: mezcla convección (medianas) y difusión (pequeñas) para depurar mediadores y controlar urea/electrolitos.",
        "• CVVHD si la prioridad es difusión rápida (hiperK grave) o no hay capacidad convectiva.",
        "• CVVHF cuando se busca convección predominante (no típico si la hemodinamia es lábil).",
        "",
        "— Límite convectivo y FF —",
        "• Limitar convección a ≤25% de Qp·h disminuye hemoconcentración intrafiltro y riesgo de coagulación; ayuda a mantener FF <25%.",
        "• FF = (Qr_post + UF)/(Qp·h + Qr_pre). Si FF sube, aumenta predilución o reduce Qr_post/UF.",
        "",
        "— División 70/30 (pre/post) —",
        "• 70% predilución: reduce viscosidad intrafiltro → protege la membrana.",
        "• 30% postdilución: asegura depuración efectiva (menor dilución de solutos postfiltro).",
        "",
        "— Ajustes por laboratorio —",
        "• K ≥6.0 mmol/L: incrementar Qd (2–3 L/h) con solución de dializado K 0–2 mmol/L; repetir K cada 2–4 h hasta <5.5.",
        "• pH <7.20 y/o HCO3 bajo: usar soluciones con bicarbonato y subir Qd/Qe (2–3 L/h); evitar lactato.",
        "• Hiponatremia: no exceder 8–10 mmol/L en 24 h (≤8 si alto riesgo de ODS); ajustar Na en solución.",
        "• Hipernatremia: objetivo ≈ 0.5 mmol/L/h (8–10 mmol/día) con dializado de Na más alto; corrección gradual.",
        "• Amonio elevado: priorizar difusión continua (CVVHD) y buffer adecuado; la dosis/flujo es más determinante que la modalidad.",
        "• Rabdomiólisis: considerar membranas HCO si la albúmina lo permite; vigilar pérdidas proteicas.",
        "",
        "— Anticoagulación —",
        "• RCA si hay trombocitopenia, coagulopatía, sangrado o neuro-riesgo, HIT previa o HBPM reciente.",
        "• HNF si bajo riesgo hemorrágico y con monitoreo de aPTT confiable.",
        f"• Objetivos RCA: iCa post-filtro ≈ {r_targets.get('iCa_post','0.25–0.40')} mmol/L; iCa sistémico ≈ {r_targets.get('iCa_sist','1.0–1.2')} mmol/L (ajustes 10–20%).",
        "",
        "— Hemodinamia y UF —",
        "• PAM <60 mmHg o vasopresor en aumento: UF mínima o 0.",
        "• PAM ≥65 mmHg con lactato en descenso: escalar UF 25–50 mL/h cada 4–6 h.",
        "",
        "— Membranas y albúmina —",
        f"• Si se utiliza HCO y albúmina <3.0 g/dL (actual: {albumina:.2f} g/dL), vigilar pérdidas y/o reponer; si Alb <2.5 g/dL, cuestionar HCO.",
        f"• Filtro seleccionado/sugerido: {filtro_final or '—'}.",
        "",
        "— Reglas de bolsillo (operativas) —",
        "• Mantener FF <25%. Si sube: ↑ predilución, ↓ Qr_post/UF, y/o ↑ Qb.",
        "• Hiperkalemia: Qd alto + solución K baja + re-labs de K cada 2–4 h.",
        "• Acidosis: bicarbonato; evitar lactato; Qd/Qe 2–3 L/h.",
        "• Na: corrección guiada a 0.5 mmol/L/h aprox.; límites diarios según hipo/hiperNa.",
        "• UF: supeditada a PAM y tendencia del lactato.",
        "• RCA: iCa post 0.25–0.40; iCa sist 1.0–1.2; ajustes 10–20%.",
        "• HCO: vigilar pérdidas de albúmina y objetivos clínicos (mioglobina/citoquinas); beneficio en resultados duros incierto para filtros adsorptivos.",
    ]
    return partes

# ========== BIBLIOGRAFÍA Y UTILIDADES ==========
Ref = Dict[str, str]
BIBLIO: List[Ref] = [
    {"id": "dose_core_2024_statpearls", "yr": "2024",
     "title": "Continuous Renal Replacement Therapy - StatPearls",
     "where": "NCBI/StatPearls",
     "url": "https://www.ncbi.nlm.nih.gov/books/NBK556028/",
     "tags": "dosis,crrt,revision", "blurb": "Dosis entregada 20–25 mL/kg/h; sin beneficio claro >25."},
    {"id": "dose_review_2021_karger", "yr": "2021",
     "title": "Dose of Continuous Renal Replacement Therapy in Critically Ill Patients",
     "where": "Karger (Nephron)",
     "url": "https://karger.com/nef/article/145/2/91/227459/Dose-of-Continuous-Renal-Replacement-Therapy-in",
     "tags": "dosis,crrt,revision", "blurb": "Revisión de evidencia de dosis y métricas de calidad."},
    {"id": "rca_review_2023_pmc", "yr": "2023",
     "title": "Regional Citrate Anticoagulation in CRRT",
     "where": "PMC (Review)",
     "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10221969/",
     "tags": "rca,anticoagulacion,crrt,revision",
     "blurb": "RCA es segura/efectiva; recomendada como primera línea si no hay contraindicaciones."},
    {"id": "rca_consensus_2023_biomed", "yr": "2023",
     "title": "Management of RCA for CRRT", "where": "Military Medical Research",
     "url": "https://mmrjournal.biomedcentral.com/articles/10.1186/s40779-023-00457-9",
     "tags": "rca,anticoagulacion,consenso", "blurb": "Consenso operativo de RCA en CKRT."},
    {"id": "ff_practical_2025_openaccess", "yr": "2025",
     "title": "Renal replacement therapy in ICU (practical)", "where": "Annals of Intensive Care",
     "url": "https://annalsofintensivecare.springeropen.com/articles/10.1186/s13613-025-01517-0",
     "tags": "ff,crrt,practica", "blurb": "FF <25% como objetivo para proteger el filtro."},
]

def filtrar_refs_por_contexto(escenarios_sel: List[str], anticoag_tipo: str) -> List[Ref]:
    e = " ".join([s.lower() for s in escenarios_sel])
    tags_req = set(["dosis", "ff", "crrt", "revision"])
    if any(x in e for x in ["sepsis", "choque"]):
        tags_req.update(["sepsis", "adsorcion"])
    if "RCA" in (anticoag_tipo or ""):
        tags_req.update(["rca", "anticoagulacion"])
    out = []
    for ref in BIBLIO:
        rtags = set(ref.get("tags", "").split(","))
        if rtags & tags_req:
            out.append(ref)
    seen = set(); sel = []
    for r in out:
        if r["id"] not in seen:
            sel.append(r); seen.add(r["id"])
    return sel[:12]

# ========== LÓGICA BASE ==========
def prioridad_modalidad(m: str) -> int:
    if m in ["CVVHDF", "CVVHDF (flujos bajos)", "CVVHDF + HCO"]: return 3
    if m == "CVVHD": return 2
    if m == "CVVHF": return 1
    return 0

def prioridad_filtro(f: str) -> int:
    if f == "Alta adsorción/HCO": return 99
    if "M200" in f: return 3
    if "M150" in f or "M100–M150" in f: return 2
    if "M100" in f: return 1
    return 0

def sugerir_por_escenario(esc: str):
    if esc == "Sepsis / choque séptico":
        return ("CVVHDF", "Alta adsorción/HCO", "Mixto conv/dif; FF≤25%. Adsorción opcional; beneficio duro incierto.")
    if esc == "Choque cardiogénico":
        return ("CVVHDF", "M150 (~1.5 m²)", "Evitar cambios bruscos; UF conservadora; vigilar FF.")
    if esc == "Post infarto":
        return ("CVVHD", "M100–M150", "Difusivo; control fino de electrolitos; UF cauta.")
    if esc == "Neurocrítico / TCE":
        return ("CVVHDF (flujos bajos)", "M100 (~1.0 m²)", "Evitar oscilaciones osmóticas; corrección Na guiada.")
    if esc == "Sobrecarga hídrica aislada":
        return ("CVVHF", "M200 (~2.0 m²)", "Convectivo favorece UF; vigilar FF y tolerancia hemodinámica.")
    if esc == "Intoxicación / sobredosis":
        return ("CVVHD (alta dosis)", "M200 (~2.0 m²)", "Difusión alta; evaluar unión a proteínas. Considerar IHD si posible.")
    if esc == "Hiponatremia severa":
        return ("CVVHDF", "M100 (~1.0 m²)", "Dializado Na bajo; no exceder 8–10 mEq/L/24h (≤8 si alto riesgo ODS).")
    if esc == "Hipernatremia":
        return ("CVVHDF", "M100–M150", "Dializado Na alto; ≈0.5 mEq/L/h (8–10 mEq/L/día) de corrección.")
    if esc == "Hiperamonemia":
        return ("CVVHD", "M150 (~1.5 m²)", "Difusión continua; prioriza dosis/flujo; buffer adecuado.")
    if esc == "Rabdomiólisis":
        return ("CVVHDF", "M200 (~2.0 m²)", "Elimina mioglobina; considerar HCO con vigilancia de albúmina.")
    if esc == "Síndrome de liberación de citocinas":
        return ("CVVHDF + HCO", "Alta adsorción/HCO", "Adsorción de mediadores; beneficio duro incierto; usar en protocolos.")
    return ("", "", "")

def combinar_recomendaciones(escenarios_sel: List[str]):
    mods, filts, coments = [], [], []
    for e in escenarios_sel:
        m, f, c = sugerir_por_escenario(e)
        if m: mods.append(m)
        if f: filts.append(f)
        if c: coments.append(c)
    mod_final = ""
    if mods:
        prio = {m: prioridad_modalidad(m) for m in mods}
        mod_final = sorted(mods, key=lambda x: prio[x], reverse=True)[0]
    filtro_final = ""
    if filts:
        filtro_final = sorted(filts, key=lambda x: prioridad_filtro(x), reverse=True)[0]
    comentarios = " | ".join(coments)
    return mod_final, filtro_final, comentarios

def flows_and_ff(qb: int, hto: float, dosis_mlkg: int, peso: float, uf: int, modalidad: str):
    qp = qb * (1 - hto)
    qp_h = qp * 60
    qe = dosis_mlkg * peso
    if "CVVHD" in modalidad and "CVVHDF" not in modalidad:
        frac_conv = 0.0
    elif "CVVHF" in modalidad:
        frac_conv = 1.0
    else:
        frac_conv = 0.6  # CVVHDF default
    qr_total = 0 if frac_conv == 0 else max(min(qp_h * 0.25, max(qe - uf, 0)), 0) * frac_conv
    qr_pre = round(qr_total * 0.7)
    qr_post = round(qr_total * 0.3)
    qd = max(qe - (qr_pre + qr_post + uf), 0)
    denom = max(qp_h + qr_pre, 1e-9)
    ff = (qr_post + uf) / denom
    return qp, qp_h, qe, qr_pre, qr_post, qd, ff

# ========= Catálogo de filtros =========
@dataclass
class Filtro:
    nombre: str
    tags: list
    area_m2: Optional[float]
    comentarios: str

FILTROS: Dict[str, Filtro] = {
    "Oxiris (AN69-ST; adsorción alta)": Filtro(
        nombre="Oxiris (AN69-ST; adsorción alta)",
        tags=["adsorción","convectivo","difusivo","CVVHDF","endotoxinas","sepsis"],
        area_m2=1.5,
        comentarios="Membrana con capacidad de adsorción. Uso opcional/protocolo; beneficio en desenlaces duros incierto."
    ),
    "HCO 1100 (alta cut-off)": Filtro(
        nombre="HCO 1100 (alta cut-off)",
        tags=["HCO","convectivo","CVVH","CVVHDF","mioglobina"],
        area_m2=1.1,
        comentarios="Alta permeabilidad para medianas/mioglobina; vigilar pérdidas de albúmina."
    ),
    "HCO 730 (alta cut-off)": Filtro(
        nombre="HCO 730 (alta cut-off)",
        tags=["HCO","convectivo","CVVH","CVVHDF","mioglobina"],
        area_m2=0.7,
        comentarios="Similar a HCO 1100, menor área; mismas precauciones de albúmina."
    ),
    "Convectivo estándar (1.3 m²)": Filtro(
        nombre="Convectivo estándar (1.3 m²)",
        tags=["convectivo","CVVH","CVVHDF"],
        area_m2=1.3,
        comentarios="Uso general; alternativa cuando no hay HCO/adsorción."
    ),
    "Difusivo estándar (2.1 m²)": Filtro(
        nombre="Difusivo estándar (2.1 m²)",
        tags=["difusivo","CVVHD","CVVHDF"],
        area_m2=2.1,
        comentarios="Útil si se prioriza depuración difusiva (urea/K)."
    ),
}

def sugerir_filtro_por_escenarios(escenarios_sel: List[str]) -> str:
    e = " ".join([s.lower() for s in escenarios_sel])
    if any(x in e for x in ["sepsis", "choque", "síndrome de liberación de citocinas", "slc"]):
        return "Oxiris (AN69-ST; adsorción alta)"
    if any(x in e for x in ["rabdomiolisis", "rabdomiólisis", "mioglobina"]):
        return "HCO 1100 (alta cut-off)"
    if any(x in e for x in ["hiperamoniemia", "amonio"]):
        return "Difusivo estándar (2.1 m²)"
    if "cvvhd" in e:
        return "Difusivo estándar (2.1 m²)"
    return "Convectivo estándar (1.3 m²)"

def checar_contraindicaciones(filtro: str, albumina_gdl: Optional[float] = None, hit: Optional[bool] = None):
    alerts = []
    fname = filtro.lower()
    if "hco" in fname and albumina_gdl is not None and albumina_gdl < 2.5:
        alerts.append("⚠️ Con HCO y albúmina <2.5 g/dL: reconsiderar su uso por pérdidas de proteínas.")
    if "oxiris" in fname and hit is True:
        alerts.append("⚠️ Evitar Oxiris si hay antecedente de HIT.")
    return alerts

def sepsis_presente(escs: List[str]) -> bool:
    e = " ".join([s.lower() for s in escs or []])
    return any(x in e for x in ["sepsis", "séptico", "choque séptico", "shock séptico", "choque"])

def rec_mod_sepsis(disponibilidad_oxiris=True, disponibilidad_hco=True):
    rec = {"modalidad": "CVVHDF", "opciones": ["CVVHDF (preferente)", "CVVHD (si no hay convectivo alto)"], "filtros": []}
    if disponibilidad_oxiris: rec["filtros"].append("Oxiris® (adsorción; beneficio duro incierto)")
    if disponibilidad_hco:    rec["filtros"].append("HCO alta cut-off (mioglobina/medianas; vigilar albúmina)")
    return rec

def rec_dosis_trrc(peso_kg: Optional[float]):
    return {"inicio_mlkg_h": (25, 30), "mantenimiento_mlkg_h": (20, 25)}

def rec_uf(map_mmHg: Optional[float], vasopresor_alta_dosis: Optional[bool], lactato_baja: Optional[bool]):
    plan = {"inicio": "UF 0–50 mL/h (o 0 si choque franco)",
            "progresión": "↑ 25–50 mL/h cada 4–6 h si PAM ≥65 y lactato ↓",
            "suspender_si": "Suspender UF si PAM <60 o ↑ vasopresores"}
    if map_mmHg is not None:
        if map_mmHg < 60 or (vasopresor_alta_dosis is True):
            plan["estado"] = "Suspender/UF mínima"
        elif map_mmHg >= 65 and lactato_baja:
            plan["estado"] = "Puede aumentar UF gradualmente"
        else:
            plan["estado"] = "Mantener UF baja/neutra"
    return plan

def rec_labs(k: Optional[float], ph: Optional[float], na: Optional[float]):
    ajustes = []
    if k is not None and k >= 6.0: ajustes.append("Hiperkalemia: ↑ difusivo (Qd 2–3 L/h) y dializado K 0–2, hasta K <5.5.")
    if ph is not None and ph < 7.20: ajustes.append("Acidosis severa: solución con bicarbonato (no lactato) y ↑ Qd/Qe 2–3 L/h.")
    if na is not None and na < 125: ajustes.append("Hiponatremia: no exceder 8–10 mmol/L/24 h (≤8 si alto riesgo ODS).")
    if na is not None and na > 155: ajustes.append("Hipernatremia: ≈0.5 mmol/L/h (8–10 mmol/d) con dializado Na más alto.")
    return ajustes or ["Sin ajustes críticos automáticos por laboratorio."]

def rec_balance_predil_postdil(htc_alto: Optional[bool]):
    base = {"pre": 30, "post": 70, "nota": "Postdilución prioriza depuración; predilución protege el filtro."}
    if htc_alto: return {"pre": 50, "post": 50, "nota": "↑ predilución si Hto >35% o coagulación del filtro."}
    return base

def alertas_sepsis(ph: Optional[float], map_mmHg: Optional[float], na: Optional[float], k: Optional[float],
                   vasopresor_alta_dosis: Optional[bool]):
    al = []
    if ph is not None and ph < 7.20: al.append("Confirmar solución con bicarbonato (no lactato) si pH <7.20.")
    if (map_mmHg is not None and map_mmHg < 60) or vasopresor_alta_dosis: al.append("Suspender UF si PAM <60 mmHg o vasopresor en aumento.")
    if na is not None: al.append("Velocidades de Na: hipoNa ≤8–10 mmol/L/24h (≤8 si alto riesgo ODS); hiperNa ≈0.5 mmol/L/h.")
    if k is not None and k >= 6.0: al.append("K≥6: aumentar Qd a 2–3 L/h con dializado K 0–2; labs cada 2–4 h.")
    return al

def checklist_final(modalidad: str, dosis_txt: str, uf_txt: str, solucion: str, filtro: str,
                    balance_txt: str):
    return [
        f"Modalidad: {modalidad}",
        f"Dosis efectiva (ml/kg/h): {dosis_txt}",
        f"Ultrafiltración: {uf_txt}",
        f"Solución: {solucion}",
        f"Filtro: {filtro}",
        f"Pre/Post: {balance_txt}"
    ]

# ---------- Header / botones ----------
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        st.image("logo.png", width=100)
    except Exception:
        pass
with col_title:
    st.title(f"TRRC360 by Dr. Tapia — {VERSION}")
    st.caption("(uso académico)")

if st.button("🔁 Actualizar", help="Borrar caché y recargar", key="btn_refresh"):
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    st.rerun()

# ================== PRIVACY GATE ==================
if "aviso_ok" not in st.session_state:
    st.session_state.aviso_ok = False

if not st.session_state.aviso_ok:
    st.subheader("Aviso de Privacidad")
    st.write("""
Esta aplicación puede manejar información sensible de pacientes. 
El uso es académico y clínico; **no** almacena datos en servidores propios de la app.
Al hacer clic en **Aceptar y continuar**, confirmas que usarás la aplicación de forma responsable y conforme a tu normativa local.
    """)
    if st.button("Aceptar y continuar"):
        st.session_state.aviso_ok = True
        st.rerun()
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Modo")
    doc_mode = st.checkbox("Modo docente extendido (UI y PDF)",
        value=st.session_state.get("doc_mode", False),
        key="doc_mode")
    st.session_state["pdf_extendido"] = bool(doc_mode)
    st.session_state["mostrar_fund_extendido"] = bool(doc_mode)

    st.header("Parámetros básicos")
    peso = st.number_input("Peso (kg)", 10.0, 300.0, 70.0, 0.5, key="sb_peso")
    hto  = st.number_input("Hematocrito (fracción)", 0.10, 0.60, 0.30, 0.01, format="%.2f", key="sb_hto")
    qb   = st.number_input("Qb (mL/min)", 80, 300, 200, 10, key="sb_qb")
    uf   = st.number_input("UF (mL/h)", 0, 2000, 100, 10, key="sb_uf")
    dosis_mlkg = st.slider("Dosis objetivo (mL/kg/h)", 10, 45, 30, key="sb_dosis")

    st.subheader("Estado(s) clínico(s)")
    escenarios_catalogo = [
        "Sepsis / choque séptico","Choque cardiogénico","Post infarto","Neurocrítico / TCE",
        "Sobrecarga hídrica aislada","Intoxicación / sobredosis","Hiponatremia severa",
        "Hipernatremia","Hiperamonemia","Rabdomiólisis","Síndrome de liberación de citocinas"
    ]
    escenarios = st.multiselect("Selecciona hasta 3", escenarios_catalogo, max_selections=3,
                                default=["Sepsis / choque séptico"], key="sb_escenarios")

# ---------- Tabs (sin 'Tendencias de laboratorio') ----------
tab_main, tab_ktv, tab_balance, tab_anticoag, tab_fund, tab_rx, tab_refs = st.tabs([
    "Prescripción",
    "Dosis por objetivos (Kt/V)",
    "Balance dinámico",
    "Anticoagulación extendida",
    "Fundamento y Cálculos",
    "Resumen / PDF",
    "Referencias",
])
# ---------- Main (Prescripción) ----------
with tab_main:
    st.subheader("Recomendación combinada")

    cP1, cP2, cP3 = st.columns(3)
    with cP1:
        pam = st.number_input("PAM (mmHg)", 30.0, 130.0, 65.0, 1.0, key="pam")
    with cP2:
        vasopresor_alto = st.selectbox("Vasopresor en dosis altas", ["No", "Sí"], 0, key="vaso_alto_sel")
        vasopresor_alto_bool = (vasopresor_alto == "Sí")
    with cP3:
        lactato_desc = st.selectbox("Lactato en descenso", ["No", "Sí"], 0, key="lactato_desc_sel")
        lactato_desc_bool = (lactato_desc == "Sí")

    mod_final, filtro_final, comentarios = combinar_recomendaciones(st.session_state.get("sb_escenarios", []))
    filtro_sugerido = sugerir_filtro_por_escenarios(st.session_state.get("sb_escenarios", []))

    opciones_filtro = list(FILTROS.keys())
    idx_default = opciones_filtro.index(filtro_sugerido) if filtro_sugerido in opciones_filtro else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Modalidad", mod_final or "—")
    c2.metric("Filtro sugerido", filtro_sugerido or "—")
    filtro_elegido = c3.selectbox("Filtro (puedes cambiarlo)", opciones_filtro, index=idx_default, key="ui_filtro",
                                  help=FILTROS[opciones_filtro[idx_default]].comentarios)

    # Laboratorios (rápido)
    st.markdown("### Laboratorios (rápido)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        na = st.number_input("Na (mEq/L)", 100.0, 200.0, 140.0, 0.5, key="na_main")
        k  = st.number_input("K (mEq/L)", 1.0, 10.0, 4.0, 0.1, key="k_main")
    with col2:
        hco3    = st.number_input("HCO₃⁻ (mEq/L)", 5.0, 45.0, 20.0, 0.5, key="hco3_main")
        lactato = st.number_input("Lactato (mmol/L)", 0.0, 20.0, 2.0, 0.1, key="lac_main")
    with col3:
        amonio = st.number_input("Amonio (µmol/L)", 0.0, 1000.0, 80.0, 5.0, key="nh4_main")
        ck     = st.number_input("CK (U/L)", 0.0, 100000.0, 200.0, 50.0, key="ck_main")
    with col4:
        ph        = st.number_input("pH", 6.80, 7.80, 7.35, 0.01, format="%.2f", key="ph_main")
        uresis24  = st.number_input("Uresis 24 h (mL)", 0, 20000, 800, 50, key="ur_main")
        albumina  = st.number_input("Albúmina (g/dL)", 1.0, 5.5, 3.0, 0.1, key="alb_main")

    # Alertas por filtro
    hit_bool = bool(st.session_state.get("hit_previa_bool", False))
    alertas = checar_contraindicaciones(filtro_elegido, albumina_gdl=albumina, hit=hit_bool)
    extra_hco_note = []
    if "HCO" in filtro_elegido and albumina < 3.0:
        extra_hco_note.append("💡 HCO con Alb <3.0: considerar reposición de albúmina y reevaluación de objetivos.")
    if alertas or extra_hco_note:
        st.warning(" | ".join(alertas + extra_hco_note))

    # Flujos base
    qb = st.session_state.get("sb_qb", 200)
    hto = st.session_state.get("sb_hto", 0.30)
    peso = st.session_state.get("sb_peso", 70.0)
    uf = st.session_state.get("sb_uf", 100)
    dosis_mlkg = st.session_state.get("sb_dosis", 30)

    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")

    st.markdown("### Flujos sugeridos (base)")
    ca, cb, cc, cd = st.columns(4)
    ca.metric("Qb (mL/min)", qb); cb.metric("Qp (mL/min)", int(qp))
    cc.metric("Qe (mL/h)", int(qe)); cd.metric("UF (mL/h)", uf)
    ce, cf, cg = st.columns(3)
    ce.metric("Qr pre (mL/h)", qr_pre); cf.metric("Qr post (mL/h)", qr_post); cg.metric("Qd (mL/h)", int(qd))
    st.info(comentarios or "—")
    st.caption("Dosis objetivo 20–25 mL/kg/h; sin beneficio consistente por encima de 25 (ver Referencias).")
    st.caption("Usar FF <25% para proteger el filtro y mantener estabilidad (ver Referencias).")

    # Semáforo de FF
    st.markdown("#### Estado del filtro (FF)")
    ff_pct = ff * 100 if ff is not None else 0.0
    acciones = []
    if ff_pct <= 20:
        st.success(f"FF ≈ {ff_pct:.1f}% (Verde): óptima.")
        acciones = ["Mantener configuración.", "Monitorizar coagulación del filtro y presiones transmembrana."]
    elif 20 < ff_pct <= 25:
        st.warning(f"FF ≈ {ff_pct:.1f}% (Ámbar): límite prudencial.")
        acciones = ["Considerar ↑ predilución (mover de post a pre).", "Valorar ↑ Qb si tolera.", "Evitar ↑ de UF si no es indispensable."]
    else:
        st.error(f"FF ≈ {ff_pct:.1f}% (Rojo): alto riesgo de coagulación.")
        acciones = ["↑ predilución (↓ postdilución).", "↓ Qr_post y/o ↓ UF.", "↑ Qb si tolera.", "Revisar anticoagulación (RCA/HNF)."]
    st.caption("Acciones sugeridas: " + " · ".join(acciones))

    # Banner crítico
    cond_qd_alto = (k >= 6.0) or (ph < 7.20)
    if cond_qd_alto:
        st.warning("🔴 Condición crítica (K≥6.0 y/o pH<7.20) → **Qd 2,000–3,000 mL/h** con **K 0–2 mmol/L** y re-labs cada **2–4 h**.")
        aplicar_auto = st.checkbox("Aplicar autosugerencia Qd≥2000 mL/h (ajusta dosis efectiva)", value=False, key="chk_auto_qd")
        if aplicar_auto:
            qd_auto = max(2000, int(qd))
            qe_auto = qd_auto + qr_pre + qr_post + uf
            dosis_auto = qe_auto / max(peso, 1e-6)
            cA, cB, cC = st.columns(3)
            cA.metric("Qd (mL/h) autosugerido", qd_auto)
            cB.metric("Qe (mL/h) resultante", int(qe_auto))
            cC.metric("Dosis (mL/kg/h) resultante", f"{dosis_auto:.1f}")
            st.caption("Ajusta soluciones a **K 0–2 mmol/L** hasta K <5.5; confirma electrolitos cada 2–4 h.")

    # Bloque sepsis/choque
    if sepsis_presente(st.session_state.get("sb_escenarios", [])):
        st.divider()
        st.markdown("### Recomendaciones automáticas – Sepsis / choque séptico")

        colA, colB = st.columns([2, 1])
        with colA:
            rec_mod = rec_mod_sepsis(True, True)
            st.markdown(f"**Modalidad sugerida:** {rec_mod['modalidad']}")
            if rec_mod["opciones"]: st.caption("Alternativas: " + " · ".join(rec_mod["opciones"]))
            if rec_mod["filtros"]:  st.caption("Filtros opcionales: " + " · ".join(rec_mod["filtros"]))

            dosis = rec_dosis_trrc(peso)
            st.markdown(f"**Dosis:** Inicio {dosis['inicio_mlkg_h'][0]}–{dosis['inicio_mlkg_h'][1]} y mantenimiento {dosis['mantenimiento_mlkg_h'][0]}–{dosis['mantenimiento_mlkg_h'][1]} mL/kg/h.")

            plan_uf = rec_uf(pam, vasopresor_alta_dosis=vasopresor_alto_bool, lactato_baja=lactato_desc_bool)
            st.markdown(f"**UF – inicio:** {plan_uf['inicio']}")
            st.caption(f"Progresión: {plan_uf['progresión']}")
            st.caption(f"Suspender si: {plan_uf['suspender_si']}")
            if "estado" in plan_uf: st.info(f"Sugerencia dinámica UF: {plan_uf['estado']}")

            ajustes_lab = rec_labs(k, ph, na)
            with st.expander("Ajustes por laboratorio (automático)"):
                for a in ajustes_lab: st.write("- " + a)

            htc_alto = True if hto > 0.35 else False
            bal = rec_balance_predil_postdil(htc_alto)
            st.markdown(f"**Pre/Post sugerido:** {bal['pre']}% / {bal['post']}%")
            st.caption(bal["nota"])

        with colB:
            al = alertas_sepsis(ph, pam, na, k, vasopresor_alto_bool)
            if al: st.warning("**Alertas de seguridad:**\n\n- " + "\n- ".join(al))

        st.markdown("#### Checklist previo a validar")
        modalidad_txt = rec_mod['modalidad']
        dosis_txt = f"{dosis['inicio_mlkg_h'][0]}–{dosis['inicio_mlkg_h'][1]} / {dosis['mantenimiento_mlkg_h'][0]}–{dosis['mantenimiento_mlkg_h'][1]}"
        uf_txt = f"{plan_uf['inicio']} → {plan_uf['progresión']}"
        solucion_txt = "Con bicarbonato si pH<7.2; evitar lactato en acidosis"
        filtro_txt = (rec_mod['filtros'][0] if rec_mod['filtros'] else "Convencional")
        balance_txt = f"{bal['pre']}% pre / {bal['post']}% post"
        items = checklist_final(modalidad_txt, dosis_txt, uf_txt, solucion_txt, filtro_txt, balance_txt)
        st.write("\n".join([f"✅ {x}" for x in items]))

        st.session_state["sepsis_checklist_txt"] = items
        st.session_state["sepsis_alertas_txt"] = al if 'al' in locals() else []

# ---------- Kt/V ----------
with tab_ktv:
    st.subheader("Dosis por objetivos (Kt/V urea)")
    V = st.number_input("Volumen de distribución V (L) ≈ 0.6×peso", value=round(0.6*st.session_state.get("sb_peso",70.0),1), step=0.1)
    C0 = st.number_input("Urea inicial C0 (mg/dL)", value=150.0, step=1.0)
    Ct = st.number_input("Urea objetivo Ct (mg/dL)", value=100.0, step=1.0)
    horas = st.number_input("Tiempo de tratamiento (h)", value=24, step=1)
    E = st.number_input("Eficiencia del sistema (0.8–1.0)", value=0.9, step=0.05, min_value=0.5, max_value=1.0)
    ktv_req = log(C0/Ct) if (C0>0 and Ct>0 and C0>Ct) else None
    st.metric("Kt/V requerido", f"{ktv_req:.2f}" if ktv_req else "—")
    K_Lh = ((ktv_req*V)/horas)/E if ktv_req else None
    dosis_calc = (K_Lh*1000)/st.session_state.get("sb_peso",70.0) if K_Lh else None
    colx, coly = st.columns(2)
    colx.metric("K requerido (L/h)", f"{K_Lh:.2f}" if K_Lh else "—")
    coly.metric("Dosis estimada (mL/kg/h)", f"{dosis_calc:.1f}" if dosis_calc else "—")
    if dosis_calc:
        st.info("Sugerencia: " + ("Aumentar dosis (<20 mL/kg/h)" if dosis_calc<20 else ("Reducir dosis (>35 mL/kg/h)" if dosis_calc>35 else "Dentro de 20–35 mL/kg/h")))
    st.caption("Relación entre Kt/V objetivo y dosis de efluente para facilitar prescripción (ver Referencias).")
    
    # ---------- Balance dinámico ----------
with tab_balance:
    st.subheader("Balance dinámico y metas de UF")
    peso = st.session_state.get("sb_peso", 70.0)
    peso_seco = st.number_input("Peso seco objetivo (kg)", value=max(0.0, peso-5), step=0.5)
    fo_actual = (peso - peso_seco)/peso_seco if peso_seco>0 else 0.0
    fo_obj = st.number_input("FO% objetivo (p. ej. 5%)", value=0.05, step=0.01)
    horas_trrc = st.number_input("Horas de TRRC planificadas (h)", value=24, step=1)
    ingresos = st.number_input("Ingresos previstos (mL)", value=0, step=50)
    uresis_res = st.number_input("Uresis residual 24 h (mL)", value=st.session_state.get("ur_main", 0), step=50)
    uf_obj = ((peso - (1+fo_obj)*peso_seco) * 1000) if (peso_seco>0) else None
    uf_mant = (ingresos - uresis_res)
    uf_total = (uf_obj if uf_obj is not None else 0) + uf_mant
    uf_h = uf_total/horas_trrc if horas_trrc>0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("FO% actual", f"{fo_actual:.1%}")
    c2.metric("UF objetivo (mL)", f"{int(uf_obj) if uf_obj is not None else 0}")
    c3.metric("UF total (mL)", f"{int(uf_total)}")
    c4.metric("UF/h sugerida", f"{int(uf_h)}")
    # ✅ Evaluación segura de UF/h por kg (corregido)
    if peso is None or peso <= 0:
        st.info("Ingresa un peso válido para evaluar la UF/h por kg.")
    else:
        uf_mLkg_h = uf_h / peso  # mL/kg/h
        if uf_mLkg_h > 2:
            st.warning(f"⚠️ UF/h > 2 mL/kg/h (actual: {uf_mLkg_h:.2f} mL/kg/h)")
        else:
            st.success(f"OK (UF: {uf_mLkg_h:.2f} mL/kg/h)")

# ---------- Anticoagulación extendida ----------
with tab_anticoag:
    st.subheader("Anticoagulación – evaluación extendida")
    colA, colB, colC, colD = st.columns(4)
    plaquetas = colA.number_input("Plaquetas (mil/µL)", 0, 1000, 200, 5)
    fib = colB.number_input("Fibrinógeno (mg/dL)", 0, 1000, 300, 10)
    sangrado = colC.selectbox("Sangrado activo", ["No","Sí"])
    neuro = colD.selectbox("Post-op neuro / riesgo alto", ["No","Sí"])
    inr = colA.number_input("INR", 0.8, 5.0, 1.1, 0.1, key="inr_ext")
    aptt = colB.number_input("aPTT (s)", 20.0, 120.0, 35.0, 1.0, key="aptt_ext")
    hbpm_12h = colC.selectbox("HBPM en últimas 12 h", ["No","Sí"], index=0)
    hit_previa = colD.selectbox("Antecedente de HIT", ["No","Sí"], index=0)
    st.session_state["hit_previa_bool"] = (hit_previa == "Sí")
    usar_rca = (
        (plaquetas<50) or (fib<150) or (sangrado=="Sí") or (neuro=="Sí") or
        (inr>=1.5) or (aptt>=45) or (hbpm_12h=="Sí") or (hit_previa=="Sí")
    )
    ac = "RCA (citrato)" if usar_rca else "Heparina no fraccionada (HNF)"
    st.success(f"Anticoagulación sugerida: **{ac}**")
    st.caption("RCA suele ser preferente si no hay contraindicaciones (ver Referencias).")
    if ac == "Heparina no fraccionada (HNF)":
        if hbpm_12h == "Sí":
            st.warning("HBPM reciente: valora diferir HNF o iniciar con dosis reducida y vigilancia estrecha de aPTT.")
        iu_h = st.session_state.get("sb_peso",70.0) * 5  # base 5 UI/kg/h
        st.info(f"Dosis inicial HNF sugerida: **{iu_h:.0f} UI/h** (ajustar a aPTT objetivo).")
        st.session_state["anticoagulacion_tipo"] = "HNF"
        st.session_state["hnf_ui_h"] = float(iu_h)
    else:
        st.markdown("### RCA – citrato y calcio (configurable)")
        st.caption("Usa la concentración real de tus soluciones (como aparece en la etiqueta).")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            citrato_mmol_por_ml = st.number_input(
                "Concentración de citrato (mmol/mL)", min_value=0.05, max_value=0.25, value=0.136,
                step=0.001, format="%.3f"
            )
            objetivo_mmol_L_sangre = st.number_input(
                "Objetivo citrato (mmol/L sangre)", min_value=2.0, max_value=5.0, value=3.0, step=0.1
            )
        with rc2:
            post_filter_ica_obj = st.slider("iCa post-filtro diana (mmol/L)", 0.20, 0.50, 0.35, 0.01)
            system_ica_obj = st.slider("iCa sistémico diana (mmol/L)", 0.90, 1.30, 1.10, 0.01)
        with rc3:
            calcio_mmol_por_ml = st.number_input(
                "Concentración de calcio (mmol/mL)", min_value=0.05, max_value=1.00, value=0.5,
                step=0.01
            )
        qb = st.session_state.get("sb_qb", 200)
        citrato_ml_h = (qb * 60.0 * objetivo_mmol_L_sangre / 1000.0) / max(citrato_mmol_por_ml, 1e-6)
        citrato_mmol_h = qb * 60.0 * (objetivo_mmol_L_sangre / 1000.0)
        calcio_mmol_h_ini = 0.7 * citrato_mmol_h
        calcio_ml_h_ini = calcio_mmol_h_ini / max(calcio_mmol_por_ml, 1e-6)
        rca1, rca2, rca3 = st.columns(3)
        rca1.metric("Citrato inicial (mL/h)", f"{citrato_ml_h:.0f}")
        rca2.metric("Reposición Ca²⁺ (mL/h, estimado)", f"{calcio_ml_h_ini:.0f}")
        rca3.metric("Citrato (mmol/h)", f"{citrato_mmol_h:.1f}")
        st.caption("Ajustes: iCa post 0.25–0.40 → ±10–20% citrato; iCa sist 1.0–1.2 → ±10–20% calcio.")
        st.session_state["anticoagulacion_tipo"] = "RCA"
        st.session_state["rca_citrato_ml_h"] = float(citrato_ml_h)
        st.session_state["rca_calcio_ml_h"] = float(calcio_ml_h_ini)
        st.session_state["rca_targets"] = {
            "iCa_post": float(post_filter_ica_obj),
            "iCa_sist": float(system_ica_obj),
            "citrato_obj_mmolL": float(objetivo_mmol_L_sangre)
        }

# ---------- Fundamento y Cálculos (sin banner st.info molesto) ----------
with tab_fund:
    st.subheader("Fundamento y Cálculos")
    mostrar_ext = bool(st.session_state.get("mostrar_fund_extendido", False))
    qb = st.session_state.get("sb_qb", 200)
    hto = st.session_state.get("sb_hto", 0.30)
    peso = st.session_state.get("sb_peso", 70.0)
    uf = st.session_state.get("sb_uf", 100)
    dosis_mlkg = st.session_state.get("sb_dosis", 30)
    escenarios = st.session_state.get("sb_escenarios", ["Sepsis / choque séptico"])
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_txt = f"{ff:.2%}" if ff is not None else "—"
    st.markdown("**Resumen de cálculos**")
    st.code("\n".join(_fundamento_texto_resumen(qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt)))
    if mostrar_ext:
        st.markdown("**Explicación extendida**")
        na = st.session_state.get("na_main", 140.0)
        k  = st.session_state.get("k_main", 4.0)
        ph = st.session_state.get("ph_main", 7.35)
        pam = st.session_state.get("pam", 65.0)
        lactato_desc = True if st.session_state.get("lactato_desc_sel","No") == "Sí" else False
        albumina  = st.session_state.get("alb_main", 3.0)
        anticoag_tipo = st.session_state.get("anticoagulacion_tipo","—")
        r_targets = st.session_state.get("rca_targets", {})
        partes_ext = _fundamento_texto_extendido(na, k, ph, pam, False, lactato_desc, albumina, anticoag_tipo, r_targets, filtro_final)
        st.write("\n".join(["- " + p for p in partes_ext]))

# ---------- Export PDF ----------
def export_pdf():
    """Genera PDF con fundamento RESUMEN o EXTENDIDO + Referencias."""
    s = st.session_state
    # ===== Recoger parámetros desde sesión =====
    peso = float(s.get("sb_peso", 70.0))
    hto  = float(s.get("sb_hto", 0.30))
    qb   = int(s.get("sb_qb", 200))
    uf   = int(s.get("sb_uf", 100))
    dosis_mlkg = int(s.get("sb_dosis", 30))
    escenarios = s.get("sb_escenarios", s.get("escenarios", ["Sepsis / choque séptico"]))
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_txt = f"{ff:.2%}" if ff is not None else "—"
    # Labs/estado
    na = float(s.get("na_main", 140.0))
    k  = float(s.get("k_main", 4.0))
    ph = float(s.get("ph_main", 7.35))
    pam = float(s.get("pam", 65.0))
    vasopresor_alto = True if s.get("vaso_alto_sel","No") == "Sí" else False
    lactato_desc = True if s.get("lactato_desc_sel","No") == "Sí" else False
    albumina = float(s.get("alb_main", 3.0))
    anticoag_tipo = s.get("anticoagulacion_tipo","—")
    r_targets = s.get("rca_targets", {})
    # Datos de identificación
    unidad = s.get("rx_unidad", "")
    nombre_paciente = s.get("rx_nombre_paciente", "")
    fecha_nac = s.get("rx_fecha_nac", "")
    edad = s.get("rx_edad", "")
    sexo = s.get("rx_sexo", "")
    expediente = s.get("rx_expediente", "")
    nombre_medico = s.get("rx_nombre_medico", "")
    sello = s.get("rx_sello", "")
    # Nombre de archivo
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_name = "".join(ch for ch in (nombre_paciente or "").replace(" ", "") if ch.isalnum())
    base = f"TRRC360_{safe_name}_" if safe_name else "TRRC360_"
    filename = f"{base}{ts}.pdf"
    # ===== Construcción del PDF =====
    c = canvas.Canvas(filename, pagesize=letter)
    w, h = letter
    margin = 50
    y = h - margin
    # Logo (opcional)
    try:
        c.drawImage("logo.png", x=margin, y=y-35, width=120, height=85, preserveAspectRatio=True, mask="auto")
    except Exception:
        pass
    # Título y fecha
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Prescripción Terapia de Reemplazo Renal Continua")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - margin, y, datetime.now().strftime("%d/%m/%Y %H:%M"))
    y -= 28
    # Unidad hospitalaria
    if unidad:
        c.setFont("Helvetica", 12)
        c.drawString(margin, y, f"Unidad hospitalaria: {unidad}")
        y -= 20
    # Ficha de identificación
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Ficha de identificación")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin,     y, f"Nombre: {nombre_paciente}")
    c.drawString(margin+280, y, f"Fecha Nac: {fecha_nac}")
    y -= 16
    c.drawString(margin,     y, f"Edad: {edad}")
    c.drawString(margin+140, y, f"Sexo: {sexo}")
    c.drawString(margin+240, y, f"Expediente: {expediente}")
    y -= 22
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, "—"*95)
    y -= 16
    # Diagnóstico / escenarios
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Diagnóstico / escenarios")
    y -= 16
    c.setFont("Helvetica", 11)
    esc_text = ", ".join(escenarios) if escenarios else "—"
    y = _draw_wrapped_text(c, f"Escenarios: {esc_text}", margin, y, w-2*margin)
    # Prescripción básica
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Modalidad: {mod_final or '—'}")
    y -= 14
    c.drawString(margin, y, f"Filtro sugerido: {filtro_final or '—'}")
    y -= 14
    c.drawString(margin, y, f"FF (estimada): {ff_txt} (objetivo <25%)")
    y -= 18
    # Flujos
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Flujos y soluciones")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(margin,     y, f"Qb (mL/min): {_s_int(qb)}")
    c.drawString(margin+180, y, f"Qp (mL/min): {_s_int(qp)}")
    c.drawString(margin+360, y, f"Qe (mL/h): {_s_int(qe)}")
    y -= 16
    c.drawString(margin,     y, f"Qr pre (mL/h): {_s_int(qr_pre)}")
    c.drawString(margin+180, y, f"Qr post (mL/h): {_s_int(qr_post)}")
    c.drawString(margin+360, y, f"Qd (mL/h): {_s_int(qd)}    UF (mL/h): {_s_int(uf)}")
    y -= 22
    # Anticoagulación
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Anticoagulación")
    y -= 16
    c.setFont("Helvetica", 11)
    if anticoag_tipo == "HNF":
        iu_h = s.get("hnf_ui_h", max(1, int(peso*5)))
        c.drawString(margin, y, f"Tipo: Heparina no fraccionada (HNF)  |  Dosis inicial: {_s_int(iu_h)} UI/h")
        y -= 16
        c.drawString(margin, y, "Ajustar a aPTT según protocolo; considerar HBPM previa antes de escalar dosis.")
        y -= 16
    elif anticoag_tipo == "RCA":
        iCa_post = r_targets.get("iCa_post", "—")
        iCa_sist = r_targets.get("iCa_sist", "—")
        cit_ml = s.get("rca_citrato_ml_h", None)
        ca_ml  = s.get("rca_calcio_ml_h", None)
        c.drawString(margin, y, f"Tipo: RCA  |  Citrato: {_s_int(cit_ml)} mL/h  |  Calcio: {_s_int(ca_ml)} mL/h")
        y -= 16
        c.drawString(margin, y, f"Dianas: iCa post-filtro {iCa_post} mmol/L; iCa sistémico {iCa_sist} mmol/L (ajustes 10–20%)")
        y -= 16
        y = _draw_wrapped_text(c, "Vigilar Na, HCO₃⁻, pH, anión gap; sospechar acumulación de citrato si iCa bajo pese a ↑ Ca e incremento del anión gap.", margin, y, w-2*margin)
    else:
        c.drawString(margin, y, "—")
        y -= 16
    # Comentarios / recomendaciones
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Comentarios / recomendaciones")
    y -= 16
    c.setFont("Helvetica", 11)
    comentarios_txt = s.get("rx_comentarios", "") or s.get("comentarios", "") or "—"
    y = _draw_wrapped_text(c, comentarios_txt, margin, y, w-2*margin)
    # Firma
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Médico tratante:")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, nombre_medico or "")
    y -= 16
    if sello:
        y = _draw_wrapped_text(c, f"Sello / Notas: {sello}", margin, y, w-2*margin)
    # ===== Segunda página: Fundamento =====
    c.showPage()
    y = h - 50
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Fundamento y Cálculos")
    y -= 22
    c.setFont("Helvetica", 11)
    pdf_extendido = bool(s.get("pdf_extendido", False))
    if not pdf_extendido:
        for linea in _fundamento_texto_resumen(qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt):
            y = _draw_wrapped_text(c, linea, 50, y, w-100)
    else:
        bloques_resumen = _fundamento_texto_resumen(qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt)
        for linea in bloques_resumen:
            y = _draw_wrapped_text(c, linea, 50, y, w-100)
        y -= 8
        if y < 120:
            c.showPage(); y = h - 50; c.setFont("Helvetica", 11)
        partes_ext = _fundamento_texto_extendido(na, k, ph, pam, vasopresor_alto, lactato_desc, albumina,
                                                 anticoag_tipo, r_targets, filtro_final)
        for linea in partes_ext:
            y = _draw_wrapped_text(c, linea, 50, y, w-100)
            if y < 80:
                c.showPage(); y = h - 50; c.setFont("Helvetica", 11)
    # ===== Página final: Referencias seleccionadas =====
    try:
        refs_pdf = filtrar_refs_por_contexto(escenarios, anticoag_tipo)
    except Exception:
        refs_pdf = []
    if refs_pdf:
        c.showPage()
        w, h = letter
        y = h - 50
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Referencias")
        y -= 24
        c.setFont("Helvetica", 10)
        for idx, r in enumerate(refs_pdf, 1):
            linea = f"[{idx}] {r['title']} — {r['where']} ({r['yr']})"
            y = _draw_wrapped_text(c, linea, 50, y, w-100, font_size=10, leading=12)
            if r.get("url"):
                y = _draw_wrapped_text(c, f"URL: {r['url']}", 60, y, w-110, font_size=9, leading=11)
            y -= 4
            if y < 80:
                c.showPage(); y = h - 50; c.setFont("Helvetica", 10)
    c.showPage()
    c.save()
    return filename

# ---------- Resumen / PDF ----------
with tab_rx:
    st.subheader("Resumen / PDF")
    st.text_input("Unidad hospitalaria", key="rx_unidad", placeholder="Ej. HGR #xx, IMSS")
    st.text_input("Nombre del paciente", key="rx_nombre_paciente")
    st.text_input("Fecha de nacimiento (dd/mm/aaaa)", key="rx_fecha_nac")
    st.text_input("Edad", key="rx_edad")
    st.text_input("Sexo", key="rx_sexo")
    st.text_input("No. de expediente", key="rx_expediente")
    st.text_input("Médico tratante (firma)", key="rx_nombre_medico")
    st.text_area("Sello / Notas", key="rx_sello")
    st.text_area("Comentarios / recomendaciones", key="rx_comentarios", height=120)
    if st.button("📄 Exportar PDF"):
        filename = export_pdf()
        with open(filename, "rb") as f:
            st.download_button("Descargar PDF", data=f.read(), file_name=filename, mime="application/pdf")

# ---------- Referencias ----------
with tab_refs:
    st.subheader("Referencias")
    escenarios = st.session_state.get("sb_escenarios", ["Sepsis / choque séptico"])
    anticoag_tipo = st.session_state.get("anticoagulacion_tipo","—")
    refs = filtrar_refs_por_contexto(escenarios, anticoag_tipo)
    if not refs:
        st.info("Ajusta los escenarios o la anticoagulación para ver referencias relevantes.")
    for i, r in enumerate(refs, 1):
        st.markdown(f"**[{i}] {r['title']}** — {r['where']} ({r['yr']})")
        if r.get("blurb"): st.caption(r["blurb"])
        if r.get("url"): st.write(r["url"])
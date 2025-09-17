# TRRC360 by Dr. Tapia — app.py (v1.14.0)
# ---------------------------------------------------------------------------------
# Novedades vs v1.13.0
# - Selector de ESCENARIO CLÍNICO.
# - Recomendación automática de modalidad basada en ESCENARIO + LABS (docente y transparente).
# - Siempre editable manualmente por juicio clínico (override).
# - Conserva: guardado/carga de pacientes (JSON), gráficos, avisos, privacidad, referencias (DOI/PMID).
# - Sin ternarios que impriman DeltaGenerator; sin st.write(st.info/…).
# ---------------------------------------------------------------------------------

from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import io
import json
import os

import streamlit as st

# PDF opcional
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

# Charts (sin estilos/colores especificados; 1 gráfica por analito)
import matplotlib.pyplot as plt

VERSION = "v1.19.1"
DB_PATH = "patients_trrc360.json"

# --------------------------------- Utilidades de persistencia -------------------
def _load_db() -> Dict[str, Any]:
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_db(data: Dict[str, Any]) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def pack_patient_payload(nombre: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    keep_keys = [
        "nombre","peso_kg","hto","talla_cm","urea_pre","urea_post",
        "modalidad","qb","qp_mlkgh","qd_mlkgh","qe_mlkgh","qrep_mlkgh","uf_ml_h",
        "anticoag","tendencias_defaults","escenario"
    ]
    return {k: payload.get(k) for k in keep_keys}

def unpack_patient_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(payload or {})
    d.setdefault("peso_kg", 70.0)
    d.setdefault("hto", 30.0)
    d.setdefault("talla_cm", 170.0)
    d.setdefault("urea_pre", 140.0)
    d.setdefault("urea_post", 60.0)
    d.setdefault("modalidad", "CVVHDF")
    d.setdefault("qb", 150.0)
    d.setdefault("qp_mlkgh", 25.0)
    d.setdefault("qd_mlkgh", 15.0)
    d.setdefault("qe_mlkgh", 10.0)
    d.setdefault("qrep_mlkgh", 15.0)
    d.setdefault("uf_ml_h", 100.0)
    d.setdefault("anticoag", "Heparina")
    d.setdefault("escenario", "—")
    d.setdefault("tendencias_defaults", {
        "na": (140.0, 138.0, 139.0),
        "k": (4.8, 4.6, 4.4),
        "lact": (2.1, 2.0, 1.8),
        "nh4": (35.0, 40.0, 30.0),
        "ure": (150.0, 120.0, 100.0),
        "crn": (9.0, 8.5, 7.8),
    })
    return d

# --------------------------------- Cálculos ------------------------------------
def bsa_mosteller(kg: float, cm: float) -> float:
    return ((kg * cm) / 3600.0) ** 0.5

def dosis_crrt_total_mlkgh(qp: float, qd: float, qe: float, qr: float) -> float:
    return qp + qd + qe + qr

def dosis_l_h(mlkgh: float, kg: float) -> float:
    return (mlkgh * kg) / 1000.0

def fraccion_filtracion(qp_mlkgh: float, qb_ml_min: float, hto_pct: float, peso_kg: float) -> Optional[float]:
    try:
        qp_ml_min = (qp_mlkgh * peso_kg) / 60.0
        qb_plasma = qb_ml_min * (1.0 - (hto_pct / 100.0))
        if qb_plasma <= 0:
            return None
        return qp_ml_min / qb_plasma
    except Exception:
        return None

def urr(urea_pre: float, urea_post: float) -> Optional[float]:
    try:
        if urea_pre <= 0:
            return None
        return (1 - (urea_post / urea_pre)) * 100.0
    except Exception:
        return None

def divider():
    st.write("---")

# --------------------------------- Reglas de recomendación ---------------------
def recommend_modality_from_labs(na_t: Optional[float], k_t: Optional[float], lact_t: Optional[float],
                                 nh4_t: Optional[float], urea_t: Optional[float], cr_t: Optional[float],
                                 dose_mlkgh: Optional[float], ff: Optional[float]) -> str:
    """Reglas docentes basadas en LABS."""
    try:
        if k_t is not None and k_t >= 6.0:
            return "CVVHD"
        if urea_t is not None and urea_t >= 200.0:
            return "CVVHD"
        if (lact_t is not None and lact_t > 2.2) or (nh4_t is not None and nh4_t > 45.0):
            return "CVVHDF"
        if ff is not None and ff <= 0.25 and (dose_mlkgh or 0) >= 25.0:
            return "CVVH"
    except Exception:
        pass
    return "CVVHDF"

SCENARIOS = [
    "—",
    "Sepsis/AKI",
    "Intoxicación dializable",
    "Hiperpotasemia (crisis)",
    "Hiperamonemia",
    "Acidosis láctica",
    "Lesión cerebral aguda",
    "Síndrome hepatorrenal",
    "Inestabilidad hemodinámica",
    "Sobrecarga hídrica aislada",
    "Rabdomiólisis",
]

SCENARIO_REFS = {
    "—": [
        "**Marco general de TRRC/AKI**",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014; PMID: 36889692",
        "Bellomo/Ronco/Kellum — NEJM CRRT Review — DOI: 10.1056/NEJMra1814522; PMID: 31483967",
    ],
    "Sepsis/AKI": [
        "**Sepsis/AKI**",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014; PMID: 36889692",
        "Surviving Sepsis Campaign 2021 — DOI: 10.1007/s00134-021-06506-y; PMID: 34599691",
        "NEJM CRRT Review — DOI: 10.1056/NEJMra1814522; PMID: 31483967",
    ],
    "Intoxicación dializable": [
        "**Intoxicaciones dializables**",
        "EXTRIP Workgroup (2019) — DOI: 10.1097/CCM.0000000000003951; PMID: 31599846",
        "Principles of ECT in toxicology (KI 2019) — DOI: 10.1016/j.kint.2018.11.031; PMID: 30771662",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014",
    ],
    "Hiperpotasemia (crisis)": [
        "**Hiperpotasemia severa**",
        "NEJM Review (2021) — DOI: 10.1056/NEJMra2031459; PMID: 33369332",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014",
    ],
    "Hiperamonemia": [
        "**Hiperamonemia**",
        "Pediatric/Neonatal CRRT for hyperammonemia — DOI: 10.1007/s00467-010-1463-2; PMID: 20130899",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014",
    ],
    "Acidosis láctica": [
        "**Acidosis láctica**",
        "NEJM Review (2014) — DOI: 10.1056/NEJMra1309483; PMID: 24521108",
        "CRRT & lactate clearance (ICU) — DOI: 10.1007/s00134-014-3501-6; PMID: 25190002",
    ],
    "Lesión cerebral aguda": [
        "**Lesión cerebral aguda**",
        "Brain Trauma Foundation — DOI: 10.1227/NEU.0000000000001432; PMID: 27654000",
        "CRRT en neurocrítico (Nefrología 2020) — DOI: 10.1016/j.nefro.2020.07.005; PMID: 32800408",
    ],
    "Síndrome hepatorrenal": [
        "**Síndrome hepatorrenal**",
        "EASL/Diagnosis & Management of HRS — DOI: 10.1016/j.jhep.2019.07.002; PMID: 31326410",
        "Decompensated cirrhosis guidance — DOI: 10.1016/j.jhep.2018.03.024; PMID: 29653741",
    ],
    "Inestabilidad hemodinámica": [
        "**Inestabilidad hemodinámica**",
        "CRRT in shock/ICU (2020) — DOI: 10.1007/s00134-020-06089-3; PMID: 32056064",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014",
    ],
    "Sobrecarga hídrica aislada": [
        "**Sobrecarga hídrica**",
        "Fluid balance & CRRT (2010) — DOI: 10.1007/s00134-010-2071-7; PMID: 20458469",
    ],
    "Rabdomiólisis": [
        "**Rabdomiólisis**",
        "AKI from rhabdomyolysis (KI 2015) — DOI: 10.1016/j.kint.2014.12.017; PMID: 25662347",
        "KDIGO AKI 2023 — DOI: 10.1016/j.kint.2023.02.014",
    ],
}
def recommend_modality_from_scenario(escenario: str, dose_mlkgh: Optional[float], ff: Optional[float]) -> str:
    """Reglas docentes basadas en ESCENARIO."""
    if escenario == "Intoxicación dializable":
        return "CVVHD"          # difusión predominante
    if escenario == "Hiperpotasemia (crisis)":
        return "CVVHD"          # difusión rápida de K+
    if escenario in ("Hiperamonemia", "Acidosis láctica"):
        return "CVVHDF"         # mezcla difusivo-convectiva
    if escenario == "Lesión cerebral aguda":
        return "CVVHD"          # control difusivo estable (docente)
    if escenario == "Síndrome hepatorrenal":
        return "CVVHDF"
    if escenario == "Inestabilidad hemodinámica":
        return "CVVHDF"
    if escenario == "Sobrecarga hídrica aislada":
        return "CVVHDF"         # por balance cuidadoso
    if escenario == "Rabdomiólisis":
        # si se planea convección y FF permisible
        if ff is not None and ff <= 0.25 and (dose_mlkgh or 0) >= 25.0:
            return "CVVH"
        return "CVVHDF"
    if escenario == "Sepsis/AKI":
        return "CVVHDF"
    return "CVVHDF"

def combined_recommendation(escenario: str, na_t: Optional[float], k_t: Optional[float], lact_t: Optional[float],
                            nh4_t: Optional[float], urea_t: Optional[float], cr_t: Optional[float],
                            dose_mlkgh: Optional[float], ff: Optional[float]) -> Tuple[str, str]:
    """
    Combina ESCENARIO + LABS con prioridades claras.
    Prioridad (mayor a menor):
    1) Flags críticos de labs: K≥6 o Urea≥200 → CVVHD.
    2) Escenarios dominantes (Intoxicación, Crisis K, Hiperamonemia/Lactato, LCA, HRS, etc.).
    3) Heurística de convección por FF baja → CVVH.
    4) Default: CVVHDF.
    Devuelve (modalidad_sugerida, explicación).
    """
    # Paso 1: labs críticos
    if k_t is not None and k_t >= 6.0:
        return "CVVHD", "Prioridad laboratorio: K≥6 mmol/L → predominio difusivo"
    if urea_t is not None and urea_t >= 200.0:
        return "CVVHD", "Prioridad laboratorio: Urea≥200 mg/dL → predominio difusivo"

    # Paso 2: escenario
    esc_base = recommend_modality_from_scenario(escenario, dose_mlkgh, ff)

    # Paso 3: refuerzo por labs no críticos
    labs_base = recommend_modality_from_labs(na_t, k_t, lact_t, nh4_t, urea_t, cr_t, dose_mlkgh, ff)

    # Resolución: si cualquiera sugiere CVVHD por motivos docentes, preferir CVVHD;
    # si alguno sugiere CVVH por convección con FF≤0.25, respetar CVVH; en else → CVVHDF.
    if "CVVHD" in (esc_base, labs_base):
        return "CVVHD", f"Escenario/Labs orientan a difusión rápida ({escenario})"
    if "CVVH" in (esc_base, labs_base):
        return "CVVH", f"Convección razonable (FF≤0.25 y dosis adecuada) ({escenario})"
    return "CVVHDF", f"Combinación de escenario y labs sugiere mezcla (docente) ({escenario})"

# --------------------------------- Config y Sidebar ----------------------------
st.set_page_config(page_title=f"TRRC360 by Dr. Tapia — {VERSION}", layout="wide")

# -------- Aceptación legal obligatoria --------
if "accepted_legal" not in st.session_state:
    st.session_state.accepted_legal = False

if not st.session_state.accepted_legal:
    st.title("TRRC360 — Asistente para TRRC (CRRT)")
    st.warning("**Uso docente:** Esta herramienta es para **enseñanza médica** y apoyo a la decisión. "
               "**No sustituye** el juicio clínico. El uso e interpretación dependen exclusivamente de quien la utiliza.")
    with st.expander("Ver aviso legal completo", expanded=True):
        st.markdown("""
**Aviso legal (obligatorio):**  
TRRC360 se ofrece con fines educativos. No es dispositivo médico ni reemplaza el juicio clínico.  
Las decisiones terapéuticas son responsabilidad exclusiva de los profesionales tratantes y deben apegarse a guías y normativa aplicables.  
El autor no asume responsabilidad por daños derivados del uso o interpretación de esta herramienta.
""")
    st.checkbox("He leído y acepto el aviso legal anterior", key="accepted_legal")
    if not st.session_state.accepted_legal:
        st.info("Para continuar, marca la casilla de aceptación.")
        st.stop()




    st.stop()
# ---------------------------------------------------------------


with st.sidebar:
    st.header("🧮 Parámetros")
    st.caption(f"TRRC360 — {VERSION}")
    st.toggle("Modo docente (vista extendida)", key="modo_docente", value=False)

    # --- Gestión de pacientes + privacidad
    st.subheader("👤 Paciente")
    db = _load_db()
    existing = sorted(list(db.keys()))
    nombre = st.text_input("Nombre/ID", "Paciente 001")

    st.caption("**Aviso de privacidad (resumen):** Si capturas nombre/ID y otros datos, se guardarán localmente "
               "en este equipo dentro de `patients_trrc360.json`. No se comparten a terceros. Usa identificadores "
               "no nominales cuando sea posible. Adapta este aviso a tu normativa vigente.")
    consentimiento = st.checkbox("He leído y acepto el aviso de privacidad")

    col_save, col_load = st.columns([1,1])
    with col_save:
        save_click = st.button("💾 Guardar")
    with col_load:
        to_load = st.selectbox("Cargar existente", ["—"] + existing, index=0)
        load_click = st.button("⬇️ Cargar seleccionado")

    col_exp, col_imp = st.columns([1,1])
    with col_exp:
        if st.download_button(
            "Exportar DB (.json)",
            data=json.dumps(db, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="patients_trrc360.json",
            mime="application/json"
        ):
            pass
    with col_imp:
        up = st.file_uploader("Importar DB (.json)", type=["json"], accept_multiple_files=False)
        if up is not None:
            try:
                db_in = json.loads(up.read().decode("utf-8"))
                if isinstance(db_in, dict):
                    _save_db(db_in)
                    st.success("Base importada.")
                    db = db_in
                    existing = sorted(list(db.keys()))
                else:
                    st.error("Estructura inválida; se esperaba dict JSON.")
            except Exception as e:
                st.error(f"Error al importar: {e}")

    
    st.subheader("📄 Documentación")
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_data = f.read()
    except Exception:
        readme_data = "README no disponible."
    try:
        with open("LICENSE", "r", encoding="utf-8") as f:
            license_data = f.read()
    except Exception:
        license_data = "LICENSE no disponible."
    st.download_button("⬇️ Descargar README.md", data=readme_data, file_name="README.md", mime="text/markdown")
    st.download_button("⬇️ Descargar LICENSE (MIT)", data=license_data, file_name="LICENSE", mime="text/plain")

    st.subheader("Datos biométricos")
    colA, colB = st.columns(2)
    with colA:
        peso_kg = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=70.0, step=0.5)
        hto = st.number_input("Hematocrito (%)", min_value=0.0, max_value=80.0, value=30.0, step=0.5)
    with colB:
        talla_cm = st.number_input("Talla (cm)", min_value=40.0, max_value=250.0, value=170.0, step=0.5)
        urea_pre = st.number_input("Urea pre (mg/dL)", min_value=0.0, max_value=500.0, value=140.0, step=0.1)
        urea_post = st.number_input("Urea post (mg/dL)", min_value=0.0, max_value=500.0, value=60.0, step=0.1)

    st.subheader("Cálculo de CRRT")
    # Origen de modalidad (auto/manual)
    modo_modalidad = st.radio("Origen de modalidad", ["Recomendación automática", "Elegir manualmente"], index=0)
    if modo_modalidad == "Elegir manualmente":
        modalidad = st.selectbox("Modalidad", ["CVVH", "CVVHD", "CVVHDF"], index=2)
    else:
        modalidad = "AUTO"  # se resuelve en la sección principal

    # Escenario clínico
    escenario = st.selectbox("Escenario clínico (docente)", SCENARIOS, index=SCENARIOS.index("Sepsis/AKI"))

    col1, col2 = st.columns(2)
    with col1:
        qb = st.number_input("Qb (mL/min)", min_value=20.0, max_value=400.0, value=150.0, step=5.0)
        qp_mlkgh = st.number_input("Qp (mL/kg/h)", min_value=0.0, max_value=120.0, value=25.0, step=1.0)
        qd_mlkgh = st.number_input("Qd (mL/kg/h)", min_value=0.0, max_value=120.0, value=15.0, step=1.0)
    with col2:
        qe_mlkgh = st.number_input("Qe (mL/kg/h)", min_value=0.0, max_value=120.0, value=10.0, step=1.0)
        qrep_mlkgh = st.number_input("Reposición (mL/kg/h)", min_value=0.0, max_value=120.0, value=15.0, step=1.0)
        uf_ml_h = st.number_input("UF objetivo (mL/h)", min_value=0.0, max_value=5000.0, value=100.0, step=10.0)

    anticoag = st.selectbox("Anticoagulación", ["Sin anticoagulación", "Heparina", "Citrato", "Otros"], index=1)

    # Downtime para calcular dosis entregada
    st.subheader("Eficiencia de entrega")
    downtime_pct = st.number_input("Downtime estimado (%)", min_value=0.0, max_value=80.0, value=15.0, step=1.0)

    # Anticoagulación docente
    st.subheader("Anticoagulación (docente)")
    candidato_citrato = st.checkbox("Candidato a citrato", value=True)
    cc_falla_hepatica = st.checkbox("Falla hepática severa", value=False)
    cc_hipoperfusion = st.checkbox("Hipoperfusión/shock grave", value=False)
    cc_hipocalcemia = st.checkbox("Hipocalcemia refractaria", value=False)


# Cargar paciente (nota: para hidratar controles completos, habría que usar session_state; opcional)
if load_click and to_load != "—":
    payload = unpack_patient_payload(db.get(to_load, {}))
    st.info(f"Cargado: {to_load}. (Hidratación automática de controles completa disponible en versión futura).")

# Guardar paciente (requiere consentimiento)
if save_click and consentimiento:
    payload = {
        "nombre": nombre,
        "peso_kg": peso_kg,
        "hto": hto,
        "talla_cm": talla_cm,
        "urea_pre": urea_pre,
        "urea_post": urea_post,
        "modalidad": modalidad if modalidad != "AUTO" else None,
        "qb": qb,
        "qp_mlkgh": qp_mlkgh,
        "qd_mlkgh": qd_mlkgh,
        "qe_mlkgh": qe_mlkgh,
        "qrep_mlkgh": qrep_mlkgh,
        "uf_ml_h": uf_ml_h,
        "anticoag": anticoag,
        "escenario": escenario,
        "tendencias_defaults": {
            "na": (140.0, 138.0, 139.0),
            "k": (4.8, 4.6, 4.4),
            "lact": (2.1, 2.0, 1.8),
            "nh4": (35.0, 40.0, 30.0),
            "ure": (150.0, 120.0, 100.0),
            "crn": (9.0, 8.5, 7.8),
        }
    }
    db[nombre] = pack_patient_payload(nombre, payload)
    _save_db(db)
    st.success(f"Paciente '{nombre}' guardado.")
elif save_click and not consentimiento:
    st.error("Para guardar datos, primero acepta el aviso de privacidad.")

# --------------------------------- Main ---------------------------------------
st.title("TRRC360 — Asistente para TRRC (CRRT)")
st.caption("Diseñado por Dr. Tapia | Escenarios clínicos + recomendación docente (auto/manual)")
st.warning("**Aviso clínico:** Esta herramienta es para **enseñanza médica** y apoyo a la decisión. "
           "**No sustituye** el juicio clínico. El uso, interpretación y aplicación corresponden exclusivamente "
           "a quien la utiliza, aun cuando la app esté fundamentada en guías y literatura.")

# Mensaje de fundamentos sin ternario
if st.session_state.get("modo_docente", False):
    st.info("Vista extendida ACTIVADA (usa el switch en la barra lateral para ocultar).")
else:
    st.caption("Vista extendida DESACTIVADA (actívala en la barra lateral).")

divider()

# -------- Cálculos principales --------
st.header("⚙️ Prescripción y cálculos")
# Guardrails de entrada
if peso_kg <= 0:
    st.error("Peso inválido (≤0). Ajusta para continuar con cálculos.")
if qb <= 0:
    st.warning("Qb es 0 o negativo; FF y otros cálculos pueden no ser válidos.")


bsa = bsa_mosteller(peso_kg, talla_cm)
dosis_total_mlkgh = dosis_crrt_total_mlkgh(qp_mlkgh, qd_mlkgh, qe_mlkgh, qrep_mlkgh)
dosis_total_lh = dosis_l_h(dosis_total_mlkgh, peso_kg)
ff = fraccion_filtracion(qp_mlkgh, qb, hto, peso_kg)
urr_val = urr(urea_pre, urea_post)

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("BSA (Mosteller)", f"{bsa:.2f} m²")
with c2: st.metric("Dosis total", f"{dosis_total_mlkgh:.0f} mL/kg/h")
with c3: st.metric("Dosis (L/h)", f"{dosis_total_lh:.2f} L/h")
with c4: st.metric("URR (%)", f"{urr_val:.1f}%" if urr_val is not None else "—")

st.metric("Fracción de filtración (aprox)", f"{ff:.2f}" if ff is not None else "—")

# Dosis entregada (ajuste por downtime)
dosis_entregada_mlkgh = max(dosis_total_mlkgh * (1.0 - (downtime_pct/100.0)), 0.0)
st.metric("Dosis entregada (estimada)", f"{dosis_entregada_mlkgh:.0f} mL/kg/h")

# Alertas por FF
if ff is None:
    st.info("FF no calculable: revisa Qb y Hto.")
elif ff > 0.30:
    st.error("FF > 0.30: alto riesgo de hemoconcentración; considera ↓Qp o ↑Qb.")
elif ff >= 0.25:
    st.warning("FF 0.25–0.30: advertencia de hemoconcentración; optimiza parámetros.")
else:
    st.success("FF ≤ 0.25: objetivo docente razonable.")

# Sugerencia docente de anticoagulación
if candidato_citrato and not (cc_falla_hepatica or cc_hipoperfusion or cc_hipocalcemia):
    sug_anticoag = "Citrato"
    st.caption("Sugerencia docente de anticoagulación: Citrato (si hay experiencia y monitoreo adecuados).")
else:
    sug_anticoag = "Heparina"
    st.caption("Sugerencia docente de anticoagulación: Heparina (si citrato no es candidato o está contraindicado).")


# Alerta de UF/h con umbral de 2 mL/kg/h (sin ternario)
uf_por_kg_h = uf_ml_h / peso_kg if peso_kg > 0 else 0.0
if uf_por_kg_h > 2:
    st.warning("⚠️ UF/h > 2 mL/kg/h")
else:
    st.success("OK")

if st.session_state.get("modo_docente", False):
    with st.expander("Fundamentos y notas de cálculo"):
        st.markdown("""
**Dosis (mL/kg/h)** = Qp + Qd + Qe + Reposición.  
**Dosis (L/h)** = (mL/kg/h × peso)/1000.  
**FF** ≈ (Qp·peso/60) / [Qb·(1−Hto)].  
**URR** = (1 − Urea_post/Urea_pre) × 100.
        """)

divider()

# -------- Tendencias de laboratorio (T1–T3) --------
st.header("📈 Tendencias de laboratorio (T1–T3)")
st.caption("Cada gráfica muestra T1, T2, T3. Ajusta los valores para alimentar la recomendación.")

def num_input_safe(label: str, key: str, vmin: float, vmax: float, step: float = 0.5, default: float = None) -> float:
    default = vmin if default is None else max(vmin, min(default, vmax))
    return st.number_input(label, key=key, value=default, min_value=vmin, max_value=vmax, step=step)

def evaluar_tendencia(v1: float, v3: float, tag: str) -> Tuple[str, str]:
    rangos = {
        "na": (135.0, 145.0),
        "k": (3.5, 5.1),
        "lactato": (0.0, 2.2),
        "amonio": (0.0, 45.0),
        "urea": (0.0, 500.0),
        "creatinina": (0.0, 20.0),
    }
    low, high = rangos.get(tag, (None, None))
    if low is not None and high is not None:
        if tag == "lactato" and v3 > high:
            return ("warn", "Lactato elevado (>2.2 mmol/L)")
        if tag == "amonio" and v3 > high:
            return ("warn", "Amonio elevado")
        if tag in ("na", "k") and (v3 < low or v3 > high):
            return ("warn", f"{tag.upper()} fuera de rango")
    if v3 < v1: return ("good", f"{tag.capitalize()} en descenso")
    if v3 > v1: return ("warn", f"{tag.capitalize()} en ascenso")
    return ("ok", f"{tag.capitalize()} sin cambio")

def plot_trend(title: str, t1: float, t2: float, t3: float, y_label: str = ""):
    fig, ax = plt.subplots()
    xs = [1, 2, 3]
    ys = [t1, t2, t3]
    ax.plot(xs, ys, marker="o")
    ax.set_title(title)
    ax.set_xlabel("Tiempo")
    if y_label:
        ax.set_ylabel(y_label)
    ax.grid(True)
    st.pyplot(fig)
    plt.close(fig)

def fila_tendencia(etq: str, key: str, tag: str, vmin: float = 0.0, vmax: float = 1000.0, step: float = 0.5, defaults=(0.0, 0.0, 0.0)):
    st.markdown(f"**{etq}**")
    c1, c2, c3, _ = st.columns([1.2, 1.2, 2, 1.2])
    t1 = num_input_safe("T1", f"{key}_t1", vmin, vmax, step, defaults[0])
    t2 = num_input_safe("T2", f"{key}_t2", vmin, vmax, step, defaults[1])
    t3 = num_input_safe("T3", f"{key}_t3", vmin, vmax, step, defaults[2])

    d12 = t2 - t1
    d23 = t3 - t2
    c5, c6 = st.columns(2)
    c5.write(f"Δ12: {d12:+.1f}")
    c6.write(f"Δ23: {d23:+.1f}")

    level, msg = evaluar_tendencia(t1, t3, tag)
    if level == "warn":
        st.warning(msg)
    elif level == "good":
        st.success(msg)
    else:
        st.info(msg)

    plot_trend(etq, t1, t2, t3, etq)
    st.markdown("---")
    return None

# Defaults de tendencias
defaults = {
    "na": (140.0, 138.0, 139.0),
    "k": (4.8, 4.6, 4.4),
    "lact": (2.1, 2.0, 1.8),
    "nh4": (35.0, 40.0, 30.0),
    "ure": (150.0, 120.0, 100.0),
    "crn": (9.0, 8.5, 7.8),
}

_ = fila_tendencia("Na (mEq/L)", "na", "na", 100.0, 200.0, 0.5, defaults["na"])
_ = fila_tendencia("K (mEq/L)", "k", "k", 1.0, 10.0, 0.1, defaults["k"])
_ = fila_tendencia("Lactato (mmol/L)", "lact", "lactato", 0.0, 20.0, 0.1, defaults["lact"])
_ = fila_tendencia("Amonio (µmol/L)", "nh4", "amonio", 0.0, 1000.0, 0.5, defaults["nh4"])
_ = fila_tendencia("Urea (mg/dL)", "ure", "urea", 0.0, 500.0, 0.5, defaults["ure"])
_ = fila_tendencia("Creatinina (mg/dL)", "crn", "creatinina", 0.0, 20.0, 0.1, defaults["crn"])

# --- Recomendación automática de modalidad combinada (escenario + labs) ---
def _get_v(key):
    try:
        return float(st.session_state.get(f"{key}_t3"))
    except Exception:
        return None

na_t3  = _get_v("na")
k_t3   = _get_v("k")
lact_t3= _get_v("lact")
nh4_t3 = _get_v("nh4")
ure_t3 = _get_v("ure")
crn_t3 = _get_v("crn")

sugerida, motivo = combined_recommendation(
    escenario, na_t3, k_t3, lact_t3, nh4_t3, ure_t3, crn_t3, dosis_total_mlkgh, ff
)

if modalidad == "AUTO":
    modalidad = sugerida

st.caption(f"**Modalidad sugerida (escenario + labs):** {sugerida} — {motivo}. (Puedes cambiarla en la barra lateral)")


# ---- Sugerencias clínicas docentes por escenario ----
with st.expander("🧠 Sugerencias clínicas (docentes) para el escenario"):
    if escenario == "Lesión cerebral aguda":
        st.markdown(
            "- Evitar cambios osmolares rápidos; preferir CVVHD con metas estables de Na.\n"
            "- Corregir Na ≤ 8–10 mEq/L/24h; monitorear osmolaridad.\n"
            "- Revisar Brain Trauma Foundation (PMID: 27654000)."
        )
    elif escenario == "Intoxicación dializable":
        st.markdown(
            "- En tóxicos dializables, prioriza difusión (CVVHD) salvo inestabilidad extrema.\n"
            "- Consulta EXTRIP para molécula específica (PMID: 31599846)."
        )
    elif escenario == "Hiperamonemia":
        st.markdown(
            "- Objetivo docente: reducción rápida de NH4+ (p.ej., <100 μmol/L).\n"
            "- Considera CVVHDF/CVVHD según hemodinámica (refs pediátricas/adulto; PMID: 20130899)."
        )
    elif escenario == "Hiperpotasemia (crisis)":
        st.markdown(
            "- En K≥6, la difusión (CVVHD) acelera la depuración de K+.\n"
            "- Corregir causas subyacentes y monitorizar ritmo; ver revisión NEJM (PMID: 33369332)."
        )
    elif escenario == "Sepsis/AKI":
        st.markdown(
            "- Dosis entregada razonable 20–25 mL/kg/h (docente); optimiza balance y hemodinamia.\n"
            "- Apóyate en Surviving Sepsis y KDIGO AKI 2023 (PMID: 34599691; 36889692)."
        )
    elif escenario == "Síndrome hepatorrenal":
        st.markdown(
            "- Manejo hepático integral (vasoconstrictores/albumina) + TRRC si hay AKI/hiperazoemia.\n"
            "- Revisa guías EASL/JHEP (PMID: 31326410; 29653741)."
        )
    elif escenario == "Rabdomiólisis":
        st.markdown(
            "- Convección puede ayudar a depurar mioglobina si FF ≤0.25 y dosis ≥25 (CVVH).\n"
            "- Vigila K, Ca y CK; ref KI 2015 (PMID: 25662347)."
        )
    elif escenario == "Inestabilidad hemodinámica":
        st.markdown(
            "- Balance cuidadoso y dosis entregada conservadora al inicio.\n"
            "- Revisa Ostermann & Joannidis (PMID: 32056064)."
        )
    elif escenario == "Sobrecarga hídrica aislada":
        st.markdown(
            "- Meta docente de UF 1.0–1.5 mL/kg/h; hasta 2.0 mL/kg/h si buena tolerancia.\n"
            "- Monitoriza signos de hipoperfusión."
        )
    elif escenario == "Acidosis láctica":
        st.markdown(
            "- Metas de perfusión y control de fuente; TRRC como soporte.\n"
            "- Revisa NEJM 2014 y estudios ICU sobre lactato (PMID: 24521108; 25190002)."
        )
    else:
        st.markdown("- Selecciona un escenario para ver sugerencias docentes.")


divider()

# -------- Resumen y exportación --------
st.header("🧾 Resumen y exportación")
resumen = f"""
Paciente: {nombre}
Fecha/hora: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Escenario clínico: {escenario}
Modalidad final: {modalidad} (sugerida: {sugerida})
Anticoagulación: {anticoag}

Peso: {peso_kg:.1f} kg | Talla: {talla_cm:.1f} cm | BSA: {bsa:.2f} m²
Hto: {hto:.1f}% | Qb: {qb:.0f} mL/min
URR: {f"{urr_val:.1f}%" if urr_val is not None else "No calculable"} | FF: {f"{ff:.2f}" if ff is not None else "No calculable"}

Dosis total: {dosis_total_mlkgh:.0f} mL/kg/h ({dosis_total_lh:.2f} L/h)\nDosis entregada (est.): {dosis_entregada_mlkgh:.0f} mL/kg/h (downtime {downtime_pct:.0f}%)
Qp: {qp_mlkgh:.0f} | Qd: {qd_mlkgh:.0f} | Qe: {qe_mlkgh:.0f} | Reposición: {qrep_mlkgh:.0f} (mL/kg/h)
UF objetivo: {uf_ml_h:.0f} mL/h

TRRC360 {VERSION}
""".strip()

with st.expander("Ver resumen en texto"):
    st.code(resumen, language="markdown")

colL, colR = st.columns(2)
with colL:
    st.download_button(
        "💾 Descargar resumen .txt",
        data=resumen.encode("utf-8"),
        file_name=f"TRRC360_resumen_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain"
    )

with colR:
    if REPORTLAB_OK:
        if st.button("🖨️ Exportar PDF (sin logo)"):
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            w, h = letter
            y = h - 50
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"TRRC360 — Resumen de Prescripción ({VERSION})")
            y -= 20
            c.setFont("Helvetica", 10)
            for line in resumen.splitlines():
                if not line.strip():
                    y -= 8
                    continue
                c.drawString(50, y, line[:110])
                y -= 14
                if y < 50:
                    c.showPage()
                    y = h - 50
                    c.setFont("Helvetica", 10)
            c.showPage()
            c.save()
            buffer.seek(0)
            st.download_button(
                "Descargar PDF",
                data=buffer,
                file_name=f"TRRC360_resumen_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )
    else:
        st.caption("Para PDF instala reportlab: `pip install reportlab`")

divider()


# -------- Referencias y notas --------
st.header("📚 Referencias y notas")
st.caption("La app sugiere modalidad con fines docentes; **el clínico decide** y puede cambiarla. "
           "Se recomienda respaldar cada decisión con referencias locales/actualizadas.")

# Dinámicas por escenario
with st.expander(f"Referencias para el escenario: {escenario}"):
    refs = SCENARIO_REFS.get(escenario, SCENARIO_REFS["—"])
    st.markdown("\n".join([f"- {item}" for item in refs]))

# Marco general adicional
with st.expander("Marco general (siempre visible)"):
    st.markdown(
        """
- **KDIGO AKI 2023** — DOI: [10.1016/j.kint.2023.02.014](https://doi.org/10.1016/j.kint.2023.02.014) — PMID: [36889692](https://pubmed.ncbi.nlm.nih.gov/36889692)
- **NEJM — Continuous Renal Replacement Therapy in Critically Ill Patients** — DOI: [10.1056/NEJMra1814522](https://doi.org/10.1056/NEJMra1814522) — PMID: [31483967](https://pubmed.ncbi.nlm.nih.gov/31483967)
- **KDIGO BP in CKD (2021)** — DOI: [10.1016/j.kint.2021.05.021](https://doi.org/10.1016/j.kint.2021.05.021) — PMID: [34614362](https://pubmed.ncbi.nlm.nih.gov/34614362)
- **KDIGO Anemia (2025 borrador)** — https://kdigo.org/guidelines/anemia-in-ckd/
- **Protocolos locales/NOM** — agrega tus guías internas y GPC mexicanas aplicables.
        """
    )

st.info("**Divulgación:** Esta herramienta es para enseñanza médica y apoyo a la decisión. "
        "No sustituye el juicio clínico. El uso e interpretación dependen exclusivamente de quien la utiliza.")

with st.expander("📘 Manual de uso de TRRC360 (README)", expanded=False):
    st.markdown("""
# TRRC360 — CRRT Teaching Assistant (v1.18.0)

**Autor:** Dr. Josué Wigberto Tapia López  
**Licencia:** MIT (ver `LICENSE`)  
**Propósito:** Herramienta **docente** para apoyar la prescripción y seguimiento de **Terapia de Reemplazo Renal Continua (TRRC/CRRT)**. **No sustituye** el juicio clínico.

---

## 👟 Instalación rápida

Requisitos: Python 3.9+

```bash
pip install streamlit matplotlib reportlab
```

> `reportlab` es opcional (solo para exportar PDF).

---

## 🚀 Ejecución

```bash
streamlit run app.py
```

Al abrirse en el navegador:
1) Acepta el **aviso legal** (uso docente / no sustituye juicio clínico).  
2) Revisa la barra lateral (**Sidebar**) para configurar al paciente y la prescripción.

---

## 🧭 Flujo de uso (paso a paso)

### 1) Sidebar (parámetros y privacidad)
- **Paciente:** Nombre/ID (se recomienda usar identificadores no nominales).  
- **Privacidad:** Marca la casilla para **aceptar el aviso de privacidad** si quieres **guardar** datos localmente (archivo `patients_trrc360.json`).  
- **Datos biométricos:** `Peso (kg)`, `Talla (cm)`, `Hto (%)`, `Urea pre/post`.  
- **Cálculo TRRC:** `Qb`, `Qp`, `Qd`, `Qe`, `Reposición`, `UF objetivo`, **Anticoagulación**.  
- **Escenario clínico:** Selección docente (Sepsis/AKI, Intoxicación, HiperK, Hiperamonemia, Láctica, LCA, HRS, Inestabilidad, Sobrecarga hídrica, Rabdomiólisis…).  
- **Origen de modalidad:** `Recomendación automática` o `Elegir manualmente`.
- **Eficiencia de entrega:** `Downtime (%)` para **calcular la dosis entregada**.
- **Anticoagulación (docente):** *checkboxes* para evaluar si es **candidato a citrato** y **contraindicaciones** (falla hepática severa, hipoperfusión grave, hipocalcemia refractaria).
- **Guardar/Cargar:**  
  - Botón **Guardar** → guarda el paciente (si aceptaste privacidad).  
  - Combo **Cargar existente** → carga pacientes guardados.  
  - **Exportar/Importar DB** (`.json`) desde la barra lateral.

### 2) Prescripción y cálculos (panel principal)
- **Métricas:** `BSA`, `Dosis total (mL/kg/h)`, `Dosis (L/h)`, `URR`, `FF`.  
- **Dosis entregada (estimada):** `dosis total × (1 − downtime%)` (p.ej. 20–25 mL/kg/h **entregados**).  
- **Alertas FF:**  
  - `≤ 0.25` → ✅ objetivo docente razonable.  
  - `0.25–0.30` → ⚠️ advertencia (riesgo de hemoconcentración).  
  - `> 0.30` → 🚨 alto riesgo (considera ↓Qp o ↑Qb).  
- **Anticoagulación (docente):** sugerencia de `Citrato` (si candidato y sin contraindicaciones) o `Heparina`.

### 3) Tendencias de laboratorio (T1–T3)
- Captura `Na`, `K`, `Lactato`, `Amonio`, `Urea`, `Creatinina` en **T1–T3**.  
- Se grafican automáticamente (matplotlib).  
- La **recomendación de modalidad** usa los **valores T3** + **FF** + **dosis** y el **escenario**.

### 4) Recomendación de modalidad (docente)
- **Automática combinada (escenario + labs + FF + dosis)** con **motivo transparente**.  
  - Ejemplos:  
    - `K ≥ 6` o `Urea ≥ 200` → **CVVHD** (difusión rápida).  
    - `Lactato > 2.2` o `NH4 > 45` → **CVVHDF** (mixta).  
    - `Rabdomiólisis` con **FF ≤ 0.25** y **dosis ≥ 25** → **CVVH** (convección predominante).  
- **Override manual:** cambia a “Elegir manualmente” en la barra lateral para fijar la modalidad.

### 5) Sugerencias clínicas por escenario
- Expander “**🧠 Sugerencias clínicas (docentes) para el escenario**” con bullets y **PMID/DOI** (LCA, Intoxicación, Hiperamonemia, HiperK, Sepsis/AKI, HRS, Rabdomiólisis, Inestabilidad, Sobrecarga, Láctica).

### 6) Referencias y notas
- **Referencias dinámicas** por escenario (`SCENARIO_REFS`) con **DOI/PMID**.
- **Marco general** (KDIGO AKI 2023, NEJM CRRT, etc.) siempre visible.

### 7) Exportación
- **TXT**: descarga un resumen en texto plano.  
- **PDF (sin logo)**: descarga un PDF limpio con `reportlab` (solo texto).

---

## ✏️ Personalización rápida

### Editar referencias por escenario
En `app.py`, busca el diccionario `SCENARIO_REFS` y edita/agrega entradas.  
Formato recomendado por línea:  
`"Título — DOI: 10.xxxx/xxxxx; PMID: 12345678"`

### Ajustar reglas docentes
- **Recomendación por labs:** función `recommend_modality_from_labs(...)`  
- **Por escenario:** `recommend_modality_from_scenario(...)`  
- **Combinada:** `combined_recommendation(...)` (prioridad: labs críticos → escenario → heurística FF/dosis → default)

### PDF sin logo
La exportación usa `reportlab` con **solo texto**. No hay imágenes (`drawImage`).

---

## 🧪 Troubleshooting

- **No carga PDF:** instala `reportlab` → `pip install reportlab`  
- **Gráficas no se ven:** confirma `matplotlib` instalado.  
- **No guarda pacientes:** debes **aceptar el aviso de privacidad** en la barra lateral.  
- **FF no calculable:** revisa que `Qb > 0` y `Hto` estén definidos.  
- **URR “No calculable”:** `urea_pre` debe ser `> 0`.

---

## ⚖️ Avisos legales

- **Uso docente**: no es dispositivo médico ni sustituye el juicio clínico.  
- **Privacidad local**: los datos se guardan **solo** en tu equipo (`patients_trrc360.json`).  
- **Licencia**: MIT. El software se proporciona “**tal cual**” sin garantías (ver `LICENSE`).

---

## 📸 Capturas sugeridas (para tu repo)
1) Pantalla principal con métricas y recomendación.  
2) Barra lateral mostrando escenario, downtime y anticoagulación.  
3) Tendencias T1–T3 con una gráfica.  
4) Bloque de referencias dinámicas por escenario.  
5) Exportación PDF (sin logo) y TXT.

---

¿Dudas o mejoras? Abre un *issue* o envía PR en tu repositorio.

""")


with st.expander("⚖️ Licencia MIT", expanded=False):
    st.code("""
MIT License

Copyright (c) 2025 Dr. Josué Wigberto Tapia López

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

""", language="text")

st.caption("© Dr. Tapia | Ayuda a la decisión clínica; no sustituye el juicio médico.")




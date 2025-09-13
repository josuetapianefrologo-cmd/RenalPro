import streamlit as st
from math import log
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

VERSION = "v1.2.1"  # etiqueta visible para confirmar despliegue

st.set_page_config(page_title="TRRC360 by Dr. Tapia", layout="wide")

# -------- Password Gate (simple) --------
DEFAULT_PASSWORD = "TRRC360"  # cámbiala si vas a usar secrets
PW = st.secrets.get("APP_PASSWORD", DEFAULT_PASSWORD)

# Estado de sesión para login
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

# Sidebar: login siempre visible (con keys únicas)
with st.sidebar:
    st.subheader("Acceso")
    pw_input = st.text_input("Contraseña", type="password", key="login_pw")
    if st.button("Entrar", key="login_btn"):
        if pw_input == PW:
            st.session_state.auth_ok = True
            st.success("Acceso autorizado. Bienvenido")
        else:
            st.error("Contraseña incorrecta")

# Si aún no hay autenticación, mostrar bienvenida y salir
if not st.session_state.auth_ok:
    st.title(f"Bienvenido a TRRC360 by Dr. Tapia — {VERSION}")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua")
    try:
        st.image("logo.png", width=200)
    except Exception:
        pass
    st.warning("Por favor, ingresa la contraseña en el panel izquierdo para continuar.")
    st.stop()

# -------- Header --------
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        st.image("logo.png", width=100)
    except Exception:
        pass
with col_title:
    st.title(f"TRRC360 by Dr. Tapia — {VERSION}")
    st.caption("(uso académico)")

# Botón para limpiar caché y recargar
if st.button("🔁 Actualizar", help="Borrar caché y recargar", use_container_width=False, key="btn_refresh"):
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    st.rerun()

# ---------- Sidebar inputs ----------
with st.sidebar:
    st.header("Parámetros básicos")
    peso = st.number_input("Peso (kg)", min_value=10.0, max_value=300.0, value=70.0, step=0.5)
    hto = st.number_input("Hematocrito (fracción)", min_value=0.10, max_value=0.60, value=0.30, step=0.01, format="%.2f")
    qb = st.number_input("Qb (mL/min)", min_value=80, max_value=300, value=200, step=10)
    uf = st.number_input("UF (mL/h)", min_value=0, max_value=2000, value=100, step=10)
    dosis_mlkg = st.slider("Dosis objetivo (mL/kg/h)", 10, 45, 30)
    st.markdown("---")
    st.subheader("Estado(s) clínico(s)")
    escenarios_catalogo = [
        "Sepsis / choque séptico",
        "Choque cardiogénico",
        "Post infarto",
        "Neurocrítico / TCE",
        "Sobrecarga hídrica aislada",
        "Intoxicación / sobredosis",
        "Hiponatremia severa",
        "Hipernatremia",
        "Hiperamonemia",
        "Rabdomiólisis",
        "Síndrome de liberación de citocinas"
    ]
    escenarios = st.multiselect("Selecciona hasta 3", escenarios_catalogo, max_selections=3, default=["Sepsis / choque séptico"])

# ---------- Helper rules ----------
def prioridad_modalidad(m):
    if m in ["CVVHDF", "CVVHDF (flujos bajos)", "CVVHDF + HCO"]: return 3
    if m == "CVVHD": return 2
    if m == "CVVHF": return 1
    return 0

def prioridad_filtro(f):
    if f == "Alta adsorción/HCO": return 99
    if "M200" in f: return 3
    if "M150" in f or "M100–M150" in f: return 2
    if "M100" in f: return 1
    return 0

def sugerir_por_escenario(esc):
    if esc == "Sepsis / choque séptico":
        return ("CVVHDF", "Alta adsorción/HCO", "Mixto conv/dif; FF≤25%")
    if esc == "Choque cardiogénico":
        return ("CVVHDF", "M150 (~1.5 m²)", "Evitar cambios bruscos; UF conservadora")
    if esc == "Post infarto":
        return ("CVVHD", "M100–M150", "Difusivo; control fino de electrolitos")
    if esc == "Neurocrítico / TCE":
        return ("CVVHDF (flujos bajos)", "M100 (~1.0 m²)", "Evitar oscilaciones osmóticas")
    if esc == "Sobrecarga hídrica aislada":
        return ("CVVHF", "M200 (~2.0 m²)", "Convectivo favorece UF; vigilar FF")
    if esc == "Intoxicación / sobredosis":
        return ("CVVHD (alta dosis)", "M200 (~2.0 m²)", "Difusión alta; considerar unión a proteínas")
    if esc == "Hiponatremia severa":
        return ("CVVHDF", "M100 (~1.0 m²)", "Dializado Na bajo; corrección ≤10 mEq/L/24h")
    if esc == "Hipernatremia":
        return ("CVVHDF", "M100–M150", "Dializado Na alto; corrección ≤10–12 mEq/L/24h")
    if esc == "Hiperamonemia":
        return ("CVVHD", "M150 (~1.5 m²)", "Difusión continua; buffer adecuado")
    if esc == "Rabdomiólisis":
        return ("CVVHDF", "M200 (~2.0 m²)", "Elimina mioglobina; controlar K+")
    if esc == "Síndrome de liberación de citocinas":
        return ("CVVHDF + HCO", "Alta adsorción/HCO", "Aclaramiento de mediadores")
    return ("", "", "")

def combinar_recomendaciones(escenarios):
    mods, filts, coments = [], [], []
    for e in escenarios:
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

def flows_and_ff(qb, hto, dosis_mlkg, peso, uf, modalidad):
    qp = qb*(1-hto)
    qp_h = qp*60
    qe = dosis_mlkg*peso
    if "CVVHD" in modalidad and "CVVHDF" not in modalidad:
        frac_conv = 0.0
    elif "CVVHF" in modalidad:
        frac_conv = 1.0
    else:
        frac_conv = 0.6  # CVVHDF default
    qr_total = 0 if frac_conv == 0 else min(qp_h*0.25, max(qe - uf, 0)) * frac_conv
    qr_pre = round(qr_total * 0.7)
    qr_post = round(qr_total * 0.3)
    qd = max(qe - (qr_pre + qr_post + uf), 0)
    ff = (qr_post + uf) / max(qp_h + qr_pre, 1e-9)
    return qp, qp_h, qe, qr_pre, qr_post, qd, ff

# ---------- Tabs ----------
tab_main, tab_ktv, tab_balance, tab_anticoag, tab_trends, tab_rx = st.tabs([
    "Prescripción",
    "Dosis por objetivos (Kt/V)",
    "Balance dinámico",
    "Anticoagulación extendida",
    "Tendencias de laboratorio",
    "Resumen / PDF",
])
# ========= Catálogo de filtros y funciones =========

from dataclasses import dataclass

@dataclass
class Filtro:
    nombre: str
    tags: list[str]
    area_m2: float | None
    comentarios: str

# Catálogo de filtros disponibles
FILTROS: dict[str, Filtro] = {
    "Oxiris (AN69-ST; adsorción alta)": Filtro(
        nombre="Oxiris (AN69-ST; adsorción alta)",
        tags=["adsorción","convectivo","difusivo","CVVHDF","endotoxinas","sepsis"],
        area_m2=1.5,
        comentarios="Membrana AN69-ST con capacidad de adsorción; útil en sepsis/mediadores."
    ),
    "HCO 1100 (alta cut-off)": Filtro(
        nombre="HCO 1100 (alta cut-off)",
        tags=["HCO","convectivo","CVVH","CVVHDF","mioglobina"],
        area_m2=1.1,
        comentarios="Alta permeabilidad; riesgo de pérdidas de albúmina."
    ),
    "HCO 730 (alta cut-off)": Filtro(
        nombre="HCO 730 (alta cut-off)",
        tags=["HCO","convectivo","CVVH","CVVHDF","mioglobina"],
        area_m2=0.7,
        comentarios="Similar a HCO 1100, menor área."
    ),
    "Convectivo estándar (1.3 m²)": Filtro(
        nombre="Convectivo estándar (1.3 m²)",
        tags=["convectivo","CVVH","CVVHDF"],
        area_m2=1.3,
        comentarios="Uso general; buena opción si no hay HCO/adsorción."
    ),
    "Difusivo estándar (2.1 m²)": Filtro(
        nombre="Difusivo estándar (2.1 m²)",
        tags=["difusivo","CVVHD","CVVHDF"],
        area_m2=2.1,
        comentarios="Si priorizas depuración difusiva (urea/K)."
    ),
}

def sugerir_filtro_por_escenarios(escenarios: list[str]) -> str:
    e = " ".join([s.lower() for s in escenarios])
    if any(x in e for x in ["sepsis", "choque", "síndrome de liberación de citocinas", "slc"]):
        return "Oxiris (AN69-ST; adsorción alta)"
    if any(x in e for x in ["rabdomiolisis", "rabdomiólisis", "mioglobina"]):
        return "HCO 1100 (alta cut-off)"
    if any(x in e for x in ["hiperamoniemia", "amonio"]):
        return "Difusivo estándar (2.1 m²)"
    if "cvvhd" in e:
        return "Difusivo estándar (2.1 m²)"
    return "Convectivo estándar (1.3 m²)"

def checar_contraindicaciones(filtro: str,
                              albumina_gdl: float | None = None,
                              hit: bool | None = None) -> list[str]:
    alerts = []
    fname = filtro.lower()
    if "hco" in fname and albumina_gdl is not None and albumina_gdl < 2.5:
        alerts.append("⚠️ Con HCO vigilar pérdidas de albúmina (Alb < 2.5 g/dL).")
    if "oxiris" in fname and hit is True:
        alerts.append("⚠️ Evitar Oxiris si hay antecedente de HIT.")
    return alerts

# ---------- Main (Prescripción) ----------
with tab_main:
    st.subheader("Recomendación combinada")

    # Recomendaciones automáticas (modalidad + comentario)
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)

    # Sugerencia automática de filtro según escenarios
    filtro_sugerido = sugerir_filtro_por_escenarios(escenarios)

    # Catálogo de opciones disponibles (definido arriba en FILTROS)
    opciones_filtro = list(FILTROS.keys())
    idx_default = opciones_filtro.index(filtro_sugerido) if filtro_sugerido in opciones_filtro else 0

    # UI: mostrar sugerencia y permitir elegir otro filtro
    c1, c2, c3 = st.columns(3)
    c1.metric("Modalidad", mod_final or "—")
    c2.metric("Filtro sugerido", filtro_sugerido or "—")
    filtro_elegido = c3.selectbox("Filtro (puedes cambiarlo)", opciones_filtro, index=idx_default, key="ui_filtro")

    # (Opcional) Contraindicaciones: si en el futuro capturas albúmina o HIT, pásalos aquí.
    alertas = checar_contraindicaciones(filtro_elegido, albumina_gdl=None, hit=False)
    if alertas:
        st.warning(" | ".join(alertas))

    # Flujos (no dependen del filtro para el cálculo)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")

    st.markdown("### Flujos sugeridos")
    ca, cb, cc, cd = st.columns(4)
    ca.metric("Qb (mL/min)", qb)
    cb.metric("Qp (mL/min)", int(qp))
    cc.metric("Qe (mL/h)", int(qe))
    cd.metric("UF (mL/h)", uf)

    ce, cf, cg = st.columns(3)
    ce.metric("Qr pre (mL/h)", qr_pre)
    cf.metric("Qr post (mL/h)", qr_post)
    cg.metric("Qd (mL/h)", int(qd))

    st.info(comentarios or "—")

    st.markdown("### Laboratorios (rápido)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        na = st.number_input("Na (mEq/L)", min_value=100.0, max_value=200.0, value=140.0, step=0.5, key="na_main")
        k = st.number_input("K (mEq/L)", min_value=1.0, max_value=10.0, value=4.0, step=0.1, key="k_main")
    with col2:
        hco3 = st.number_input("HCO₃⁻ (mEq/L)", min_value=5.0, max_value=45.0, value=20.0, step=0.5, key="hco3_main")
        lactato = st.number_input("Lactato (mmol/L)", min_value=0.0, max_value=20.0, value=2.0, step=0.1, key="lac_main")
    with col3:
        amonio = st.number_input("Amonio (µmol/L)", min_value=0.0, max_value=1000.0, value=80.0, step=5.0, key="nh4_main")
        ck = st.number_input("CK (U/L)", min_value=0.0, max_value=100000.0, value=200.0, step=50.0, key="ck_main")
    with col4:
        ph = st.number_input("pH", min_value=6.80, max_value=7.80, value=7.35, step=0.01, format="%.2f", key="ph_main")
        uresis24 = st.number_input("Uresis 24 h (mL)", min_value=0, max_value=20000, value=800, step=50, key="ur_main")

    sugs = []
    if na < 125: sugs.append("Hiponatremia grave → dializado Na bajo (≤10 mEq/L/día)")
    if na > 155: sugs.append("Hipernatremia → dializado Na alto (≤10–12 mEq/L/día)")
    if k < 3.0: sugs.append("K<3 → corregir potasio; evitar altas dosis convectivas")
    if k > 5.5: sugs.append("K>5.5 → aumentar difusivo (CVVHD/CVVHDF)")
    if amonio > 150: sugs.append("Amonio alto → CVVHD alta dosis")
    if ck > 5000: sugs.append("CK alta → sospecha rabdomiólisis")
    st.markdown("**Sugerencias:** " + (" | ".join(sugs) if sugs else "—"))

# ---------- Kt/V ----------
with tab_ktv:
    st.subheader("Dosis por objetivos (Kt/V urea)")
    V = st.number_input("Volumen de distribución V (L) ≈ 0.6×peso", value=round(0.6*peso,1), step=0.1)
    C0 = st.number_input("Urea inicial C0 (mg/dL)", value=150.0, step=1.0)
    Ct = st.number_input("Urea objetivo Ct (mg/dL)", value=100.0, step=1.0)
    horas = st.number_input("Tiempo de tratamiento (h)", value=24, step=1)
    E = st.number_input("Eficiencia del sistema (0.8–1.0)", value=0.9, step=0.05, min_value=0.5, max_value=1.0)
    ktv_req = None
    if C0>0 and Ct>0 and C0>Ct:
        ktv_req = log(C0/Ct)
    st.metric("Kt/V requerido", f"{ktv_req:.2f}" if ktv_req else "—")
    K_Lh = ((ktv_req*V)/horas)/E if ktv_req else None
    dosis_calc = (K_Lh*1000)/peso if K_Lh else None
    colx, coly = st.columns(2)
    colx.metric("K requerido (L/h)", f"{K_Lh:.2f}" if K_Lh else "—")
    coly.metric("Dosis estimada (mL/kg/h)", f"{dosis_calc:.1f}" if dosis_calc else "—")
    if dosis_calc:
        st.info("Sugerencia: " + ("Aumentar dosis (<20 mL/kg/h)" if dosis_calc<20 else ("Reducir dosis (>35 mL/kg/h)" if dosis_calc>35 else "Dentro de 20–35 mL/kg/h")))

# ---------- Balance dinámico ----------
with tab_balance:
    st.subheader("Balance dinámico y metas de UF")
    peso_seco = st.number_input("Peso seco objetivo (kg)", value=max(0.0, peso-5), step=0.5)
    fo_actual = (peso - peso_seco)/peso_seco if peso_seco>0 else 0.0
    fo_obj = st.number_input("FO% objetivo (p. ej. 5%)", value=0.05, step=0.01)
    horas_trrc = st.number_input("Horas de TRRC planificadas (h)", value=24, step=1)
    ingresos = st.number_input("Ingresos previstos (mL)", value=0, step=50)
    uresis_res = st.number_input("Uresis residual 24 h (mL)", value=uresis24 if 'uresis24' in locals() else 0, step=50)
    uf_obj = ((peso - (1+fo_obj)*peso_seco) * 1000) if (peso_seco>0) else None
    uf_mant = (ingresos - uresis_res)
    uf_total = (uf_obj if uf_obj is not None else 0) + uf_mant
    uf_h = uf_total/horas_trrc if horas_trrc>0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("FO% actual", f"{fo_actual:.1%}")
    c2.metric("UF objetivo (mL)", f"{int(uf_obj) if uf_obj is not None else 0}")
    c3.metric("UF total (mL)", f"{int(uf_total)}")
    c4.metric("UF/h sugerida", f"{int(uf_h)}")
    msg = "OK"
    if (uf_h/peso) > 0.002:
        msg = "⚠️ UF/h > 2 mL/kg/h"
    if "⚠️" in msg:
        st.warning(msg)
    else:
        st.success(msg)

# ---------- Anticoagulación extendida ----------
with tab_anticoag:
    st.subheader("Anticoagulación – evaluación extendida")
    colA, colB, colC, colD = st.columns(4)
    plaquetas = colA.number_input("Plaquetas (mil/µL)", min_value=0, max_value=1000, value=200, step=5)
    fib = colB.number_input("Fibrinógeno (mg/dL)", min_value=0, max_value=1000, value=300, step=10)
    sangrado = colC.selectbox("Sangrado activo", ["No","Sí"])
    neuro = colD.selectbox("Post-op neuro / riesgo alto", ["No","Sí"])
    inr = colA.number_input("INR", min_value=0.8, max_value=5.0, value=1.1, step=0.1, key="inr_ext")
    aptt = colB.number_input("aPTT (s)", min_value=20.0, max_value=120.0, value=35.0, step=1.0, key="aptt_ext")

    usar_rca = (plaquetas<50) or (fib<150) or (sangrado=="Sí") or (neuro=="Sí") or (inr>=1.5) or (aptt>=45)
    ac = "RCA" if usar_rca else "Heparina"
    st.success(f"Anticoagulación sugerida: **{ac}**")
    if ac=="Heparina":
        iu_h = peso * 5  # base 5 UI/kg/h (ajustable)
        st.info(f"Heparina inicial sugerida: **{iu_h:.0f} UI/h** (ajustar a aPTT).")
    else:
        st.info("Usar anticoagulación regional con citrato (RCA).")


# ----------- Tendencias (robusto) -----------
def evaluar_tendencia(v1, v3, tag):
    """
    Devuelve (nivel, mensaje):
    nivel ∈ {"warn","ok","good"}
    - "warn": empeora / fuera de rango
    - "ok": normal / dentro de rango (no llamar "mejora")
    - "good": mejora clara (solo para urea/creatinina cuando bajan)
    """

    t = tag.lower().strip()

    # Rangos normales
    R_NA   = (135.0, 145.0)   # mEq/L
    R_K    = (3.5, 5.1)       # mEq/L
    R_LAC  = (0.5, 2.2)       # mmol/L
    R_NH4  = (15.0, 45.0)     # µmol/L
    R_UREA = (5.0, 45.0)      # mg/dL
    R_CREA = (0.6, 1.3)       # mg/dL

    # Sodio
    if t.startswith("na"):
        if v3 < R_NA[0] or v3 > R_NA[1]:
            return ("warn", "Empeora: Na fuera de 135-145 mEq/L")
        else:
            return ("ok", "Na dentro de 135-145 mEq/L")

    # Potasio
    if t.startswith("k"):
        if v3 < R_K[0] or v3 > R_K[1]:
            return ("warn", "Empeora: K fuera de 3.5-5.1 mEq/L")
        else:
            return ("ok", "K dentro de 3.5-5.1 mEq/L")

    # Lactato
    if t.startswith("lact"):
        if v3 > R_LAC[1]:
            return ("warn", "Empeora: lactato > 2.2 mmol/L")
        else:
            return ("ok", "Lactato ≤ 2.2 mmol/L")

    # Amonio
    if t.startswith("amonio"):
        if v3 > R_NH4[1]:
            return ("warn", "Empeora: amonio > 45 µmol/L")
        else:
            return ("ok", "Amonio ≤ 45 µmol/L")

    # Urea
    if t.startswith("urea"):
        if v3 < v1:
            return ("good", "Mejora: urea en descenso")
        elif v3 > v1:
            return ("warn", "Empeora: urea en ascenso")
        else:
            return ("ok", "Urea sin cambio")

    # Creatinina
    if t.startswith("creatinina"):
        if v3 < v1:
            return ("good", "Mejora: creatinina en descenso")
        elif v3 > v1:
            return ("warn", "Empeora: creatinina en ascenso")
        else:
            return ("ok", "Creatinina sin cambio")

    # Por defecto
    return ("ok", "Sin regla específica")

# -------- Tendencias de laboratorio (UI + reglas) --------
with tab_trends:
    st.subheader("Tendencias (T1–T3) | v1.2.2")

    # Valores por defecto (puedes cambiarlos si quieres)
    DEF = {
        "na":  (140.0, 130.0, 120.0),   # mEq/L
        "k":   (4.0,   3.0,   2.0),     # mEq/L
        "lact":(1.0,   0.8,   0.4),     # mmol/L
        "nh4": (80.0,  70.0,  60.0),    # µmol/L
        "ure": (130.0, 100.0, 80.0),    # mg/dL
        "crn": (4.0,   3.0,   2.0),     # mg/dL
    }

    # Helper: number_input con límites seguros
    def num_input_safe(label, key, vmin, vmax, step=0.5, default=None):
        if default is None:
            default = vmin
        default = max(vmin, min(default, vmax))
        return st.number_input(label, key=key, value=default,
                               min_value=vmin, max_value=vmax, step=step)

    # Helper: fila completa (T1,T2,T3 + Δ12,Δ23 + alerta)
    def fila_tendencia(etiqueta, base_key, tag, vmin=0.0, vmax=1000.0, step=0.5, defaults=(0.0,0.0,0.0)):
        st.markdown(f"**{etiqueta}**")
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 2, 1.2])

        t1 = num_input_safe("T1", key=f"{base_key}_t1", vmin=vmin, vmax=vmax, step=step, default=defaults[0])
        t2 = num_input_safe("T2", key=f"{base_key}_t2", vmin=vmin, vmax=vmax, step=step, default=defaults[1])
        t3 = num_input_safe("T3", key=f"{base_key}_t3", vmin=vmin, vmax=vmax, step=step, default=defaults[2])

        d12 = t2 - t1
        d23 = t3 - t2
        c5, c6 = st.columns(2)
        c5.write(f"Δ12: {d12:+.1f}")
        c6.write(f"Δ23: {d23:+.1f}")

        # Evalúa con las reglas clínicas
        level, msg = evaluar_tendencia(t1, t3, tag)
        if level == "warn":
            st.warning(msg)
        elif level == "good":
            st.success(msg)
        else:
            st.info(msg)

        st.markdown("---")

    # Rangos de entrada amplios (para evitar errores de límites de Streamlit)
    # y “tags” para las reglas clínicas:
    fila_tendencia("Na (mEq/L)",                "na",  "na",       vmin=100.0, vmax=200.0, step=0.5, defaults=DEF["na"])
    fila_tendencia("K (mEq/L)",                 "k",   "k",        vmin=1.0,   vmax=10.0,  step=0.1, defaults=DEF["k"])
    fila_tendencia("Lactato (mmol/L)",          "lact","lactato",  vmin=0.0,   vmax=20.0,  step=0.1, defaults=DEF["lact"])
    fila_tendencia("Amonio (µmol/L)",           "nh4", "amonio",   vmin=0.0,   vmax=1000.0,step=0.5, defaults=DEF["nh4"])
    fila_tendencia("Urea (mg/dL)",              "ure", "urea",     vmin=0.0,   vmax=500.0, step=0.5, defaults=DEF["ure"])
    fila_tendencia("Creatinina (mg/dL)",        "crn", "creatinina",vmin=0.0,  vmax=20.0,  step=0.1, defaults=DEF["crn"])

# ----------- Resumen / PDF -----------
with tab_rx:
    st.subheader("Resumen de prescripción")

    # ====== Datos administrativos (se quedan en session_state) ======
    st.markdown("#### Unidad hospitalaria y ficha de identificación")

    cU, _ = st.columns([3, 1])
    with cU:
        st.text_input(
            "Unidad hospitalaria",
            key="rx_unidad",
            value=st.session_state.get("rx_unidad", "")
        )

    r1c1, r1c2, r1c3 = st.columns([2, 1, 1])
    with r1c1:
        st.text_input(
            "Nombre del paciente",
            key="rx_nombre_paciente",
            value=st.session_state.get("rx_nombre_paciente", "")
        )
    with r1c2:
        st.text_input(  # puedes cambiar a date_input si luego quieres control de fecha
            "Fecha de nacimiento",
            key="rx_fecha_nac",
            value=st.session_state.get("rx_fecha_nac", "")
        )
    with r1c3:
        st.text_input(  # o number_input si prefieres numérico
            "Edad",
            key="rx_edad",
            value=st.session_state.get("rx_edad", "")
        )

    r2c1, r2c2 = st.columns([1, 2])
    with r2c1:
        _sexo_opts = ["", "F", "M"]
        _sexo_val = st.session_state.get("rx_sexo", "")
        st.selectbox(
            "Sexo",
            _sexo_opts,
            index=_sexo_opts.index(_sexo_val) if _sexo_val in _sexo_opts else 0,
            key="rx_sexo"
        )
    with r2c2:
        st.text_input(
            "Expediente",
            key="rx_expediente",
            value=st.session_state.get("rx_expediente", "")
        )

    st.markdown("#### Datos del médico tratante")
    st.text_input(
        "Nombre del médico",
        key="rx_nombre_medico",
        value=st.session_state.get("rx_nombre_medico", "")
    )
    st.text_input(
        "Sello / Notas (opcional)",
        key="rx_sello",
        value=st.session_state.get("rx_sello", "")
    )

    # ====== Resumen en pantalla (lo que ya calculó la app) ======
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")

    st.write(f"**Escenarios:** {', '.join(escenarios) if escenarios else '—'}")
    ff_txt = f"{ff:.2%}" if ff is not None else "—"
    st.write(f"**Modalidad:** {mod_final or '—'}  |  **Filtro sugerido:** {filtro_final or '—'}  |  **FF (estimada):** {ff_txt}")

    st.markdown("### Flujos sugeridos")
    ca, cb, cc, cd = st.columns(4)
    ca.metric("Qb (mL/min)", qb)
    cb.metric("Qp (mL/min)", int(qp))
    cc.metric("Qe (mL/h)", int(qe))
    cd.metric("UF (mL/h)", uf)

    ce, cf, cg = st.columns(3)
    ce.metric("Qr pre (mL/h)", qr_pre)
    cf.metric("Qr post (mL/h)", qr_post)
    cg.metric("Qd (mL/h)", int(qd))

    

# ---------------- Helpers PDF ----------------

def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=11, leading=14):
    """Dibuja texto con salto de línea simple dentro de max_width. Devuelve y final."""
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

# === Exportación a PDF con encabezados y ficha del paciente ===
def export_pdf(filename="TRRC360_prescripcion.pdf"):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from datetime import datetime

    s = st.session_state
    # Datos administrativos (persisten en session_state por los text_input)
    unidad           = s.get("unidad", "")
    nombre_paciente  = s.get("nombre_paciente", "")
    fecha_nac        = s.get("fecha_nac", "")
    edad             = s.get("edad", "")
    sexo             = s.get("sexo", "")
    expediente       = s.get("expediente", "")
    nombre_medico    = s.get("rx_nombre_medico", "") or s.get("nombre_medico", "")
    sello            = s.get("rx_sello", "") or s.get("sello", "")
    comentarios      = s.get("rx_comentarios", "") or s.get("comentarios", "")

    # Variables clínicas ya calculadas en la app
    global escenarios, mod_final, filtro_final, qb, qp, qe, qr_pre, qr_post, qd, ff

    # Lienzo
    c = canvas.Canvas(filename, pagesize=letter)
    w, h = letter
    margin = 50
    y = h - margin

    # (Opcional) Logo si existe en el repo
    try:
        c.drawImage("logo.png", x=margin, y=y-35, width=120, height=85, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    # Título y fecha/hora
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Prescripción Terapia de Reemplazo Renal Continuo")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - margin, y, datetime.now().strftime("%d/%m/%Y %H:%M"))
    y -= 28

    # Unidad hospitalaria
    if unidad:
        c.setFont("Helvetica", 12)
        c.drawString(margin, y, f"Unidad hospitalaria: {unidad}")
        y -= 20

    # Ficha de identificación (horizontal)
    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Ficha de identificación"); y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin,          y, f"Nombre: {nombre_paciente}")
    c.drawString(margin + 250,    y, f"Fecha Nac: {fecha_nac}")
    y -= 14
    c.drawString(margin,          y, f"Edad: {edad}")
    c.drawString(margin + 100,    y, f"Sexo: {sexo}")
    c.drawString(margin + 250,    y, f"Expediente: {expediente}")
    y -= 18

    # Separador
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, "—")
    y -= 16

    # Resumen de prescripción
    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Resumen de prescripción"); y -= 16
    c.setFont("Helvetica", 11)
    esc_text = ", ".join(escenarios) if escenarios else "—"
    c.drawString(margin, y, f"Escenarios: {esc_text}"); y -= 14
    ff_txt = f"{ff:.2%}" if ff is not None else "—"
    c.drawString(margin, y, f"Modalidad: {mod_final or '—'}  |  Filtro sugerido: {filtro_final or '—'}  |  FF (estimada): {ff_txt}")
    y -= 18

    # Flujos (2 renglones compactos)
    c.setFont("Helvetica-Bold", 11); c.drawString(margin, y, "Flujos sugeridos"); y -= 16
    c.setFont("Helvetica", 11)
    try_qb  = str(qb)
    try_qp  = str(int(qp))  if qp is not None else "—"
    try_qe  = str(int(qe))  if qe is not None else "—"
    try_qr0 = str(qr_pre)   if qr_pre is not None else "—"
    try_qr1 = str(qr_post)  if qr_post is not None else "—"
    try_qd  = str(int(qd))  if qd is not None else "—"

    c.drawString(margin,       y, f"Qb: {try_qb}")
    c.drawString(margin+150,   y, f"Qp: {try_qp}")
    c.drawString(margin+300,   y, f"Qe: {try_qe}")
    y -= 14
    c.drawString(margin,       y, f"Qr pre: {try_qr0}")
    c.drawString(margin+150,   y, f"Qr post: {try_qr1}")
    c.drawString(margin+300,   y, f"Qd: {try_qd}")
    y -= 22

    # Comentarios
    if comentarios:
        c.setFont("Helvetica-Bold", 11); c.drawString(margin, y, "Comentarios:"); y -= 14
        c.setFont("Helvetica", 11)
        c.drawString(margin, y, comentarios[:1000])  # simple; una línea
        y -= 18

    # Firma
    y -= 30
    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Médico tratante:"); y -= 18
    c.setFont("Helvetica", 11);      c.drawString(margin, y, (nombre_medico or "")); y -= 16
    if sello:
        c.drawString(margin, y, f"Sello / Notas: {sello}"); y -= 16

    # Guardar
    c.showPage()
    c.save()
    return filename

    st.info(comentarios or "—")
    # --- Botón Exportar a PDF ---
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("Exportar a PDF", key="btn_export_pdf"):
            try:
                fn = export_pdf()  # Genera el PDF
                with open(fn, "rb") as f:
                    st.download_button(
                        "Descargar PDF",
                        data=f,
                        file_name=fn,
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_download_pdf"
                    )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

# (Opcional) pie de página de la app
st.caption("© Tapia Nefrología — Uso académico | TRRC360 by Dr. Tapia")

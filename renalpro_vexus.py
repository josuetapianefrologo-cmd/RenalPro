"""
RenalPro (TRRC360) — Módulo: VExUS (Venous Excess Ultrasound)
=============================================================
Evaluación ecográfica de la congestión venosa sistémica.
Educativo + ilustraciones Doppler ORIGINALES (generadas) + calculadora de grado.

Integración:
    from renalpro_vexus import render
    render()

Standalone:
    streamlit run renalpro_vexus.py

Las ondas Doppler son esquemas generados (originales). No reproducen figuras
de artículos. Referencia conceptual: Beaubien-Souligny W, et al. The Ultrasound
Journal. 2020 (protocolo VExUS).

Autor: Josué Tapia Nefrólogo — Tapia Nefrología
"""

import streamlit as st
import numpy as np
import pandas as pd

try:
    import altair as alt
    _ALTAIR = True
except ImportError:
    _ALTAIR = False


# ---------------------------------------------------------------------------
# Generadores de ondas Doppler esquemáticas (originales)
# ---------------------------------------------------------------------------
def _onda_hepatica(grado, ciclos=3, n=600):
    """Vena suprahepática: flujo normal por debajo de la basal (hacia corazón)."""
    t = np.linspace(0, ciclos, n)
    ph = t % 1.0
    a = 0.18 * np.exp(-((ph - 0.05) ** 2) / (2 * 0.03 ** 2))       # onda A (retrógrada)
    if grado == "normal":
        s_amp, d_amp = -1.0, -0.6                                  # S más profunda que D
    elif grado == "leve":
        s_amp, d_amp = -0.5, -0.9                                  # S < D (ambas bajo basal)
    else:                                                          # grave: inversión de S
        s_amp, d_amp = 0.6, -0.8
    s = s_amp * np.exp(-((ph - 0.30) ** 2) / (2 * 0.05 ** 2))
    d = d_amp * np.exp(-((ph - 0.68) ** 2) / (2 * 0.06 ** 2))
    return t, a + s + d


def _onda_portal(grado, ciclos=3, n=600):
    """Vena porta: flujo continuo sobre la basal con pulsatilidad variable."""
    t = np.linspace(0, ciclos, n)
    ph = t % 1.0
    mean = 1.0
    pi = {"normal": 0.20, "leve": 0.40, "grave": 0.75}[grado]
    amp = pi * mean / (2 - pi)            # PI = (Vmax-Vmin)/Vmax
    return t, mean + amp * np.sin(2 * np.pi * ph - np.pi / 2)


def _onda_renal(grado, ciclos=3, n=600):
    """Vena intrarrenal: bajo la basal; continua / bifásica / monofásica D."""
    t = np.linspace(0, ciclos, n)
    ph = t % 1.0
    if grado == "normal":                                         # continuo monofásico
        return t, -0.6 + 0.04 * np.sin(2 * np.pi * ph)
    if grado == "leve":                                           # discontinuo bifásico (S y D)
        s = -0.7 * np.exp(-((ph - 0.30) ** 2) / (2 * 0.035 ** 2))
        d = -0.6 * np.exp(-((ph - 0.70) ** 2) / (2 * 0.035 ** 2))
        return t, s + d
    d = -0.85 * np.exp(-((ph - 0.65) ** 2) / (2 * 0.05 ** 2))     # discontinuo monofásico (D)
    return t, d


_GENERADORES = {"Suprahepática": _onda_hepatica,
                "Portal": _onda_portal,
                "Intrarrenal": _onda_renal}

_COLOR_GRADO = {"normal": "#10B981", "leve": "#F59E0B", "grave": "#EF4444"}
_TITULO_GRADO = {"normal": "Normal", "leve": "Levemente anormal", "grave": "Severamente anormal"}


def _chart_onda(vena, grado):
    t, v = _GENERADORES[vena](grado)
    df = pd.DataFrame({"Tiempo": t, "Velocidad": v})   # sin puntos en el nombre
    if _ALTAIR:
        area = alt.Chart(df).mark_area(opacity=0.85,
                                       color=_COLOR_GRADO[grado]).encode(
            x=alt.X("Tiempo:Q", axis=None),
            y=alt.Y("Velocidad:Q", axis=alt.Axis(title=None, labels=False, ticks=False)),
        )
        base = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            color="#475569", strokeDash=[3, 3]).encode(y="y:Q")
        return (area + base).properties(height=130)
    return None


# ---------------------------------------------------------------------------
# Lógica de graduación VExUS
# ---------------------------------------------------------------------------
def calcular_vexus(ivc_dilatada: bool, hepatica: str, portal: str, renal: str):
    """Devuelve (grado:int, titulo:str, color:str, detalle:str)."""
    if not ivc_dilatada:
        return (0, "Grado 0 — Sin congestión", "#10B981",
                "VCI < 2 cm: descarta congestión venosa significativa.")
    severos = sum(1 for x in (hepatica, portal, renal) if x == "grave")
    if severos == 0:
        return (1, "Grado 1 — Congestión leve", "#F59E0B",
                "VCI ≥ 2 cm con patrones normales o levemente anormales "
                "(ningún patrón severo).")
    if severos == 1:
        return (2, "Grado 2 — Congestión moderada", "#F97316",
                "VCI ≥ 2 cm con UN patrón severamente anormal.")
    return (3, "Grado 3 — Congestión severa", "#EF4444",
            f"VCI ≥ 2 cm con {severos} patrones severamente anormales (≥ 2).")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def _tab_que_es():
    st.subheader("¿Qué es VExUS?")
    st.markdown(
        "**VExUS** (*Venous Excess Ultrasound*) es un protocolo POCUS que "
        "cuantifica la **congestión venosa sistémica** combinando el diámetro "
        "de la **vena cava inferior (VCI)** con el patrón Doppler de tres "
        "territorios venosos: **suprahepática, porta e intrarrenal**. Sirve "
        "para guiar el manejo de volumen (descongestión, diuréticos) y se "
        "asocia con lesión renal aguda y peor respuesta natriurética."
    )
    st.markdown(
        "**Los 4 componentes:**\n"
        "1. **VCI:** puerta de entrada. < 2 cm → Grado 0 (sin congestión). "
        "≥ 2 cm → se evalúan los flujos.\n"
        "2. **Vena suprahepática:** normal S > D (ambas bajo la basal); leve "
        "S < D; severo **inversión de la S**.\n"
        "3. **Vena porta:** índice de pulsatilidad (IP). Normal < 30%; leve "
        "30-49%; severo **≥ 50%**.\n"
        "4. **Vena intrarrenal:** normal **continuo monofásico**; leve "
        "**discontinuo bifásico** (S y D); severo **discontinuo monofásico** "
        "(solo D)."
    )
    st.divider()
    st.subheader("Cómo adquirir el estudio")
    st.markdown(
        "- Paciente en decúbito supino; transductor curvilíneo (o sectorial) "
        "con Doppler color y pulsado.\n"
        "- **VCI:** mide el diámetro máximo en su segmento intrahepático, ~2 cm "
        "antes de la unión con la suprahepática, en plano ortogonal.\n"
        "- **Porta y suprahepática:** Doppler pulsado en línea medioaxilar.\n"
        "- **Intrarrenal:** Doppler en parénquima; suele verse arteria "
        "(positiva, pulsátil) y vena (bajo la línea cero) en paralelo."
    )
    st.info("⚠️ VExUS refleja la interacción entre función cardiaca, presiones "
            "de llenado y volumen — no es una medida pura de volemia.")


def _tab_patrones():
    st.subheader("🌊 Patrones Doppler por vena")
    st.caption("Esquemas generados para aprendizaje. La línea punteada es la "
               "basal (cero). Selecciona la vena y compara los tres grados.")
    vena = st.selectbox("Vena", list(_GENERADORES.keys()), key="vx_vena")

    descripciones = {
        "Suprahepática": {
            "normal": "S > D, ambas **por debajo** de la basal.",
            "leve": "S < D, pero ambas aún por debajo de la basal.",
            "grave": "**Inversión de la onda S** (pasa por encima de la basal).",
        },
        "Portal": {
            "normal": "Flujo casi continuo; **IP < 30%**.",
            "leve": "Pulsatilidad aumentada; **IP 30-49%**.",
            "grave": "Muy pulsátil; **IP ≥ 50%** (puede llegar a la basal).",
        },
        "Intrarrenal": {
            "normal": "**Continuo monofásico** (sin interrupción).",
            "leve": "**Discontinuo bifásico**: ondas S y D separadas.",
            "grave": "**Discontinuo monofásico**: solo onda D.",
        },
    }

    cols = st.columns(3)
    for col, grado in zip(cols, ("normal", "leve", "grave")):
        with col:
            st.markdown(f"**{_TITULO_GRADO[grado]}**")
            ch = _chart_onda(vena, grado)
            if ch is not None:
                st.altair_chart(ch, width='stretch')
            else:
                t, v = _GENERADORES[vena](grado)
                st.line_chart(pd.DataFrame({"Velocidad": v}), height=130)
            st.caption(descripciones[vena][grado])

    st.divider()
    st.markdown("**VCI (componente de entrada):** no es una onda sino un "
                "diámetro. **< 2 cm** → Grado 0. **≥ 2 cm** → habilita la "
                "graduación 1-3 según los flujos.")


def _tab_calculadora():
    st.subheader("🧮 Calculadora de grado VExUS")
    ivc = st.radio("Diámetro de la VCI", ["< 2 cm", "≥ 2 cm"], horizontal=True,
                   key="vx_ivc")
    ivc_dilatada = ivc == "≥ 2 cm"

    st.markdown("**Patrones Doppler** (se evalúan si la VCI ≥ 2 cm):")
    c1, c2, c3 = st.columns(3)
    hep = c1.selectbox("Suprahepática", ["normal", "leve", "grave"],
                       format_func=lambda x: {"normal": "Normal (S>D)",
                       "leve": "Leve (S<D)", "grave": "Grave (inversión S)"}[x],
                       disabled=not ivc_dilatada, key="vx_hep")
    por = c2.selectbox("Portal", ["normal", "leve", "grave"],
                       format_func=lambda x: {"normal": "Normal (IP<30%)",
                       "leve": "Leve (IP 30-49%)", "grave": "Grave (IP≥50%)"}[x],
                       disabled=not ivc_dilatada, key="vx_por")
    ren = c3.selectbox("Intrarrenal", ["normal", "leve", "grave"],
                       format_func=lambda x: {"normal": "Continuo monofásico",
                       "leve": "Discontinuo bifásico", "grave": "Discontinuo monofásico"}[x],
                       disabled=not ivc_dilatada, key="vx_ren")

    if st.button("Calcular grado VExUS", type="primary"):
        grado, titulo, color, detalle = calcular_vexus(
            ivc_dilatada, hep if ivc_dilatada else "normal",
            por if ivc_dilatada else "normal", ren if ivc_dilatada else "normal")
        st.markdown(
            f"<div style='padding:14px;border-radius:10px;background:{color}22;"
            f"border-left:6px solid {color};color:#1e293b;'>"
            f"<span style='font-size:1.3rem;font-weight:700;color:{color};'>"
            f"{titulo}</span><br>{detalle}</div>",
            unsafe_allow_html=True)


def _tab_interpretacion():
    st.subheader("📊 Interpretación clínica")
    filas = [
        ("Grado 0", "#10B981", "Sin congestión", "VCI < 2 cm."),
        ("Grado 1", "#F59E0B", "Congestión leve",
         "VCI ≥ 2 cm + patrones normales/leves. Vigilancia."),
        ("Grado 2", "#F97316", "Congestión moderada",
         "VCI ≥ 2 cm + 1 patrón severo. Considerar descongestión."),
        ("Grado 3", "#EF4444", "Congestión severa",
         "VCI ≥ 2 cm + ≥ 2 patrones severos. Asociado a LRA y resistencia "
         "diurética; descongestión activa."),
    ]
    for g, c, t, d in filas:
        st.markdown(
            f"<div style='padding:8px 12px;margin-bottom:6px;border-radius:8px;"
            f"background:{c}1A;border-left:5px solid {c};color:#1e293b;'>"
            f"<b style='color:{c};'>{g} — {t}.</b> {d}</div>",
            unsafe_allow_html=True)

    st.divider()
    st.subheader("⚠️ Limitaciones y trampas")
    st.markdown(
        "- **Porta:** en personas delgadas, jóvenes sanas o con malformaciones "
        "AV puede ser pulsátil **sin** congestión.\n"
        "- **Suprahepática:** puede no alterarse en insuficiencia tricuspídea "
        "severa si la aurícula derecha aún se distiende/contrae.\n"
        "- **VCI:** la presión intraabdominal elevada altera la medición.\n"
        "- **Enfermedad renal/hepática parenquimatosa** modifica los Doppler.\n"
        "- VExUS valora **congestión venosa**, no balance hídrico aislado: un "
        "balance positivo no siempre implica congestión orgánica."
    )
    st.caption("Referencia: Beaubien-Souligny W, et al. *The Ultrasound "
               "Journal* 2020 (protocolo VExUS).")


def render():
    st.title("🌊 VExUS — Congestión venosa")
    st.caption("RenalPro · TRRC360 — Evaluación ecográfica de la congestión venosa sistémica")
    tabs = st.tabs(["📖 Qué es", "🌊 Patrones Doppler", "🧮 Calculadora", "📊 Interpretación"])
    with tabs[0]:
        _tab_que_es()
    with tabs[1]:
        _tab_patrones()
    with tabs[2]:
        _tab_calculadora()
    with tabs[3]:
        _tab_interpretacion()
    st.divider()
    st.caption("⚠️ Apoyo educativo y a la decisión clínica. Ilustraciones "
               "Doppler esquemáticas (originales), no figuras de publicaciones.")


if __name__ == "__main__":
    st.set_page_config(page_title="VExUS — RenalPro", page_icon="🌊", layout="wide")
    render()

"""
RenalPro (TRRC360) — Módulo: Gamagrama Renal
=============================================
Referencia clínica + herramientas de cálculo interactivas.
Cobertura: nefrología general + trasplante renal.

Integración:
    from renalpro_gamagrama_renal import render
    render()  # llamar dentro de tu enrutador de páginas

Standalone (para probar):
    streamlit run renalpro_gamagrama_renal.py

Notas de evidencia: rangos y protocolos basados en guías de procedimiento
EANM / SNMMI de renografía dinámica y renograma diurético. Esta herramienta
es de APOYO a la decisión; no sustituye la lectura del especialista en
medicina nuclear ni la biopsia cuando esté indicada.

Autor: Josué Tapia Nefrólogo — Tapia Nefrología
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Constantes clínicas (rangos de referencia)
# ---------------------------------------------------------------------------
SPLIT_NORMAL = (45.0, 55.0)          # % función diferencial por riñón
TMAX_NORMAL_MAX = 5.0                # min (3-5 normal)
T12_NORMAL_MAX = 10.0                # min, renograma diurético
T12_EQUIVOCO_MAX = 20.0              # min

RADIOFARMACOS = [
    {
        "nombre": "MAG3 (Tc-99m mercaptoacetiltriglicina)",
        "mecanismo": "Secreción tubular proximal; extracción alta (~50-60%)",
        "evalua": "Flujo plasmático renal efectivo (FPRE), función tubular, excreción",
        "uso": "Agente de elección en renograma dinámico. Superior en función "
               "renal disminuida y en evaluación del injerto.",
    },
    {
        "nombre": "DTPA (Tc-99m dietilentriaminopentaacético)",
        "mecanismo": "Filtración glomerular pura; extracción baja (~20%)",
        "evalua": "TFG, perfusión",
        "uso": "TFG diferencial cuando la función está conservada.",
    },
    {
        "nombre": "DMSA (Tc-99m ácido dimercaptosuccínico)",
        "mecanismo": "Fijación cortical en células del túbulo proximal",
        "evalua": "Masa de parénquima funcional, cicatrices corticales",
        "uso": "Estudio ESTÁTICO. Pielonefritis/cicatriz, reflujo, riñón "
               "ectópico, función diferencial cortical.",
    },
    {
        "nombre": "EC (Tc-99m etilencisteína) / Glucoheptonato",
        "mecanismo": "Tubular (EC) / mixto filtración + cortical (GH)",
        "evalua": "Según agente",
        "uso": "Alternativas regionales a MAG3/DMSA.",
    },
]


# ---------------------------------------------------------------------------
# Lógica de interpretación (testeable, sin Streamlit)
# ---------------------------------------------------------------------------
def funcion_diferencial(captacion_izq: float, captacion_der: float):
    """Devuelve (%izq, %der, interpretacion)."""
    total = captacion_izq + captacion_der
    if total <= 0:
        return None, None, "Datos inválidos (captación total = 0)."
    pizq = captacion_izq / total * 100
    pder = captacion_der / total * 100
    menor = min(pizq, pder)
    lado_menor = "izquierdo" if pizq < pder else "derecho"
    if SPLIT_NORMAL[0] <= menor <= SPLIT_NORMAL[1]:
        interp = "Función diferencial simétrica (dentro de 45-55%)."
    elif 40 <= menor < SPLIT_NORMAL[0]:
        interp = (f"Asimetría leve a expensas del riñón {lado_menor} "
                  f"({menor:.1f}%). Correlacionar clínicamente.")
    else:
        interp = (f"Asimetría significativa: riñón {lado_menor} con "
                  f"{menor:.1f}% de la función total. Sugiere daño "
                  f"parenquimatoso relevante de ese lado.")
    return pizq, pder, interp


def tfg_dividida(tfg_total: float, pct_izq: float, pct_der: float):
    """TFG por riñón a partir de la TFG total y la función diferencial."""
    tizq = tfg_total * pct_izq / 100
    tder = tfg_total * pct_der / 100
    alertas = []
    for lado, val in (("izquierdo", tizq), ("derecho", tder)):
        if val < 20:
            alertas.append(f"TFG del riñón {lado} {val:.1f} mL/min: contribución "
                           f"baja. Relevante si se considera nefrectomía/donación.")
    return tizq, tder, alertas


def clasifica_t12_diuretico(t12_min: float):
    """Clasificación del lavado en renograma diurético."""
    if t12_min < T12_NORMAL_MAX:
        return ("Normal / no obstructivo",
                "T½ < 10 min: respuesta diurética adecuada, sin obstrucción.")
    if t12_min <= T12_EQUIVOCO_MAX:
        return ("Equívoco / indeterminado",
                "T½ 10-20 min: zona indeterminada. Considerar repetir con "
                "protocolo optimizado (F+20/F-15), hidratación y vaciamiento "
                "vesical adecuados.")
    return ("Patrón obstructivo",
            "T½ > 20 min: retención significativa, compatible con uropatía "
            "obstructiva. Correlacionar con imagen anatómica.")


def clasifica_tmax(tmax_min: float):
    if tmax_min <= TMAX_NORMAL_MAX:
        return "Normal", "Tiempo al pico dentro de 3-5 min."
    return "Prolongado", ("Tmax > 5 min: captación/tránsito enlentecido. "
                          "Puede verse en disfunción parenquimatosa, "
                          "deshidratación o retención.")


def patron_trasplante(perfusion: str, captacion: str, excrecion: str,
                      extravasacion: bool):
    """Asistente de patrones en el injerto renal. Devuelve (titulo, lista)."""
    sugerencias = []

    if perfusion == "Ausente":
        sugerencias.append(
            "🚨 URGENCIA: perfusión ausente → sospecha de trombosis "
            "vascular del injerto (arterial/venosa). Evaluación inmediata."
        )

    if extravasacion:
        sugerencias.append(
            "Extravasación de actividad fuera del sistema colector → "
            "fuga urinaria / urinoma. Correlacionar con uro-TC o pielografía."
        )

    if (perfusion in ("Conservada", "Normal") and captacion in ("Conservada", "Normal")
            and excrecion == "Retardada"):
        sugerencias.append(
            "Perfusión y captación conservadas con excreción retardada → "
            "patrón típico de NECROSIS TUBULAR AGUDA (NTA) en postrasplante "
            "temprano. Suele ser autolimitada."
        )

    if perfusion == "Reducida" and captacion == "Reducida":
        sugerencias.append(
            "Descenso de perfusión y función → compatible con RECHAZO agudo "
            "(u otra disfunción del injerto). El gamagrama NO distingue de "
            "forma fiable NTA vs rechazo: la BIOPSIA sigue siendo el estándar."
        )

    if excrecion == "Retardada" and not extravasacion and perfusion != "Ausente":
        sugerencias.append(
            "Excreción retardada con retención en sistema colector dilatado → "
            "considerar OBSTRUCCIÓN del injerto (estenosis ureteral, etc.)."
        )

    if not sugerencias:
        sugerencias.append("Patrón sin alertas específicas con los datos "
                           "introducidos. Correlacionar con clínica y laboratorio.")
    return "Interpretación orientativa del injerto", sugerencias


# ---------------------------------------------------------------------------
# UI — Streamlit
# ---------------------------------------------------------------------------
def _tab_referencia():
    st.subheader("Radiofármacos")
    st.caption("Regla práctica: **MAG3** cuando importa la excreción o la "
               "función está deteriorada (obstrucción, injerto); **DMSA** "
               "cuando importa la corteza (cicatriz, masa funcional).")
    for r in RADIOFARMACOS:
        with st.expander(r["nombre"]):
            st.markdown(f"**Mecanismo:** {r['mecanismo']}")
            st.markdown(f"**Evalúa:** {r['evalua']}")
            st.markdown(f"**Uso principal:** {r['uso']}")

    st.divider()
    st.subheader("Indicaciones centrales")
    st.markdown(
        "- Uropatía obstructiva → **renograma diurético** (furosemida)\n"
        "- Función renal diferencial (pre-nefrectomía, **donante vivo**)\n"
        "- HTA renovascular → **renograma con captopril**\n"
        "- Cicatrización / reflujo → **DMSA**\n"
        "- Evaluación funcional del **injerto renal**"
    )


def _tab_dinamico():
    st.subheader("Renograma dinámico — fases")
    st.markdown(
        "1. **Perfusión** (~primeros 60 s): llegada vascular; comparar con "
        "aorta/iliaca.\n"
        "2. **Captación / función** (1-3 min): acumulación parenquimatosa. "
        "Pico = **Tmax 3-5 min** normal.\n"
        "3. **Excreción / eliminación**: lavado hacia el sistema colector."
    )
    st.divider()
    st.subheader("Parámetros e interpretación")
    st.markdown(
        f"- **Función diferencial (split):** normal **{SPLIT_NORMAL[0]:.0f}-"
        f"{SPLIT_NORMAL[1]:.0f}%** por riñón (el dato más reproducible).\n"
        "- **Curva renográfica:** ascenso-pico-descenso. Meseta o curva "
        "ascendente → retención.\n"
        f"- **Renograma diurético (T½ lavado):** <{T12_NORMAL_MAX:.0f} min "
        f"normal · {T12_NORMAL_MAX:.0f}-{T12_EQUIVOCO_MAX:.0f} min equívoco · "
        f">{T12_EQUIVOCO_MAX:.0f} min obstrucción. Protocolos F0/F+20/F-15.\n"
        "- **Renograma con captopril:** tamizaje funcional de HTA renovascular."
    )


def _tab_calculadoras():
    st.subheader("🧮 Calculadoras")

    st.markdown("##### 1) Función diferencial relativa")
    c1, c2 = st.columns(2)
    cap_izq = c1.number_input("Captación riñón IZQUIERDO (cuentas o %)",
                              min_value=0.0, value=50.0, step=1.0, key="cap_izq")
    cap_der = c2.number_input("Captación riñón DERECHO (cuentas o %)",
                              min_value=0.0, value=50.0, step=1.0, key="cap_der")
    pizq = pder = None
    if st.button("Calcular función diferencial"):
        pizq, pder, interp = funcion_diferencial(cap_izq, cap_der)
        if pizq is None:
            st.error(interp)
        else:
            m1, m2 = st.columns(2)
            m1.metric("Riñón izquierdo", f"{pizq:.1f}%")
            m2.metric("Riñón derecho", f"{pder:.1f}%")
            st.info(interp)
            st.session_state["_pizq"], st.session_state["_pder"] = pizq, pder

    st.divider()
    st.markdown("##### 2) TFG dividida (split GFR)")
    st.caption("Combina la TFG total medida con la función diferencial.")
    tfg_total = st.number_input("TFG total (mL/min/1.73m²)", min_value=0.0,
                                value=90.0, step=1.0)
    c3, c4 = st.columns(2)
    pizq_in = c3.number_input("% función IZQ", min_value=0.0, max_value=100.0,
                              value=st.session_state.get("_pizq", 50.0), step=0.5)
    pder_in = c4.number_input("% función DER", min_value=0.0, max_value=100.0,
                              value=st.session_state.get("_pder", 50.0), step=0.5)
    if st.button("Calcular TFG dividida"):
        if abs((pizq_in + pder_in) - 100) > 1:
            st.warning("Los porcentajes no suman ~100%. Verifica los valores.")
        tizq, tder, alertas = tfg_dividida(tfg_total, pizq_in, pder_in)
        m3, m4 = st.columns(2)
        m3.metric("TFG izquierda", f"{tizq:.1f} mL/min")
        m4.metric("TFG derecha", f"{tder:.1f} mL/min")
        for a in alertas:
            st.warning(a)

    st.divider()
    st.markdown("##### 3) Renograma diurético — T½ de lavado")
    t12 = st.number_input("T½ (min)", min_value=0.0, value=8.0, step=0.5)
    if st.button("Clasificar lavado"):
        titulo, detalle = clasifica_t12_diuretico(t12)
        st.metric("Resultado", titulo)
        st.info(detalle)

    st.divider()
    st.markdown("##### 4) Tiempo al pico (Tmax)")
    tmax = st.number_input("Tmax (min)", min_value=0.0, value=4.0, step=0.5)
    if st.button("Evaluar Tmax"):
        titulo, detalle = clasifica_tmax(tmax)
        st.metric("Resultado", titulo)
        st.info(detalle)


def _tab_trasplante():
    st.subheader("🫘 Injerto renal — asistente de patrones")
    st.caption("Herramienta de apoyo. NTA vs rechazo NO se distinguen de forma "
               "fiable por gamagrama; la biopsia es el estándar.")
    perfusion = st.selectbox("Perfusión", ["Normal", "Conservada", "Reducida",
                                           "Ausente"])
    captacion = st.selectbox("Captación / función", ["Normal", "Conservada",
                                                     "Reducida"])
    excrecion = st.selectbox("Excreción", ["Normal", "Retardada"])
    extravasacion = st.checkbox("Extravasación de actividad fuera del colector")
    if st.button("Interpretar patrón"):
        titulo, sugs = patron_trasplante(perfusion, captacion, excrecion,
                                         extravasacion)
        st.markdown(f"**{titulo}:**")
        for s in sugs:
            if s.startswith("🚨"):
                st.error(s)
            else:
                st.info(s)


def render():
    """Punto de entrada del módulo. Llamar desde el enrutador de RenalPro."""
    st.title("🔬 Gamagrama Renal")
    st.caption("RenalPro · TRRC360 — Referencia clínica y herramientas de cálculo")

    tabs = st.tabs([
        "📖 Referencia",
        "📈 Renograma dinámico",
        "🧮 Calculadoras",
        "🫘 Trasplante",
    ])
    with tabs[0]:
        _tab_referencia()
    with tabs[1]:
        _tab_dinamico()
    with tabs[2]:
        _tab_calculadoras()
    with tabs[3]:
        _tab_trasplante()

    st.divider()
    st.caption("⚠️ Apoyo a la decisión clínica. No sustituye la lectura del "
               "especialista en medicina nuclear. Rangos según guías de "
               "procedimiento EANM/SNMMI de renografía.")


if __name__ == "__main__":
    st.set_page_config(page_title="Gamagrama Renal — RenalPro", page_icon="🔬",
                       layout="wide")
    render()

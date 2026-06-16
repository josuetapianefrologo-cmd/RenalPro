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
import numpy as np
import pandas as pd

try:
    import altair as alt
    _ALTAIR = True
except ImportError:                      # fallback a st.line_chart si no está
    _ALTAIR = False

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
        "uso": "Estudio ESTÁTICO. Pielonefritis, cicatriz/nefropatía por "
               "reflujo (el DAÑO, no el reflujo activo), riñón ectópico, "
               "función diferencial cortical.",
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
# Simulador de curvas renográficas (modelo fisiológico)
# ---------------------------------------------------------------------------
# Modelo de 1 compartimento: dQ/dt = entrada_plasmática(t) - kout·Q(t)
#   - entrada ∝ función (captación) y a la concentración plasmática decreciente
#   - kout = constante de excreción (alta = lavado rápido; ~0 = retención)
#   - kout_diur = kout tras furosemida SOLO en escenarios que responden
ESCENARIOS_CURVA = {
    "Normal": dict(
        uptake=1.0, tau_p=6.0, kout=0.30, perfusion=1.0,
        nota="Ascenso a Tmax 3-5 min y lavado normal (T½ < 10 min)."),
    "Obstrucción (NO responde a diurético)": dict(
        uptake=1.0, tau_p=7.0, kout=0.008, perfusion=1.0,
        nota="Curva ascendente/meseta sin lavado; furosemida NO la modifica."),
    "Dilatación no obstructiva (responde a diurético)": dict(
        uptake=1.0, tau_p=7.0, kout=0.03, perfusion=1.0, kout_diur=0.40,
        nota="Retiene hasta dar furosemida; entonces lava (T½ corto). "
             "Sin diurético es indistinguible de obstrucción."),
    "Función disminuida": dict(
        uptake=0.4, tau_p=12.0, kout=0.12, perfusion=0.6,
        nota="Amplitud baja, Tmax retrasado y eliminación lenta."),
    "NTA del injerto (trasplante)": dict(
        uptake=0.85, tau_p=8.0, kout=0.015, perfusion=0.95,
        nota="Perfusión y captación conservadas con excreción ausente/retardada."),
    "Rechazo agudo (trasplante)": dict(
        uptake=0.35, tau_p=9.0, kout=0.10, perfusion=0.45,
        nota="Perfusión y captación reducidas → curva achatada de baja amplitud."),
}


def simular_renograma(escenario, funcion=1.0, diuretico=False, t_diur=18.0,
                      dur=30.0, dt=0.05):
    """Integra el modelo y devuelve (tiempo, actividad) en unidades arbitrarias."""
    p = ESCENARIOS_CURVA[escenario]
    t = np.arange(0, dur + dt, dt)
    Q = np.zeros_like(t)
    up = p["uptake"] * funcion
    tau, kb = p["tau_p"], p["kout"]
    kd = p.get("kout_diur", kb)
    responde = "kout_diur" in p
    for i in range(1, len(t)):
        ti = t[i]
        cp = np.exp(-ti / tau) if ti >= 0.3 else 0.0          # plasma decreciente
        k = max(kb, kd) if (diuretico and ti >= t_diur and responde) else kb
        Q[i] = max(0.0, Q[i - 1] + (up * cp - k * Q[i - 1]) * dt)
    vasc = p["perfusion"] * 0.6 * np.exp(-((t - 0.5) ** 2) / (2 * 0.3 ** 2))
    return t, (Q + vasc) * 100.0


def metricas_renograma(t, counts):
    """Devuelve (Tmax, pico, T½_postpico). T½ = None si no hay lavado a la mitad."""
    mask = t >= 1.0                                           # ignora pico vascular
    idx = np.where(mask)[0][int(np.argmax(counts[mask]))]
    tmax, pico = float(t[idx]), float(counts[idx])
    t_half = None
    for i in range(idx, len(t)):
        if counts[i] <= pico / 2.0:
            t_half = round(float(t[i] - tmax), 1)
            break
    return round(tmax, 1), round(pico, 1), t_half


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
        "- **Cicatriz / nefropatía por reflujo** (el daño) → **DMSA**\n"
        "- **Reflujo vesicoureteral activo** → **cistografía** (ver abajo), "
        "**no DMSA**\n"
        "- Evaluación funcional del **injerto renal**"
    )

    st.divider()
    st.subheader("⚠️ Evaluación de reflujo vesicoureteral (VUR)")
    st.warning("Error frecuente: el **DMSA NO detecta reflujo activo** — solo "
               "muestra la cicatriz/nefropatía que el reflujo ya dejó. Para ver "
               "el reflujo en sí se usa una **cistografía**.")
    st.markdown(
        "**¿Qué estudio para ver el reflujo?**\n\n"
        "- **VCUG / CUMS (contraste):** cistouretrografía miccional seriada "
        "(*Voiding Cystourethrogram*) — radiografía con contraste yodado y "
        "sonda vesical, tomada durante el llenado y la micción. Estándar para "
        "**diagnóstico inicial y graduación (I-V)** y para ver la uretra "
        "(clave en varones). Mayor radiación.\n"
        "- **Cistografía isotópica DIRECTA:** se instila el trazador en vejiga "
        "por sonda. Muy sensible y de **baja dosis** → ideal para **seguimiento "
        "de VUR conocido**. No evalúa uretra ni gradúa con detalle.\n"
        "- **Cistografía isotópica INDIRECTA:** continuación de un renograma "
        "dinámico (**MAG3** preferido, o DTPA); el paciente orina y se observa "
        "el reflujo. **Sin sonda y fisiológica**, pero requiere continencia y "
        "buena función; menos sensible.\n"
        "- **DMSA:** solo para la **cicatriz/nefropatía** secundaria."
    )
    st.markdown(
        "**¿Cuál según la edad?**\n\n"
        "- **Niños:** VCUG para el diagnóstico inicial/graduación; "
        "**cistografía isotópica directa** para el seguimiento (baja "
        "radiación). La indirecta solo en niños mayores continentes.\n"
        "- **Adultos:** **cistografía isotópica indirecta** (sin sonda, vía "
        "renograma MAG3) es la opción práctica; VCUG si se necesita detalle "
        "anatómico/graduación.\n"
        "- **Injerto renal:** reflujo al injerto → cistografía (directa o "
        "VCUG); MAG3 para función/drenaje; DMSA solo para cicatriz/pielonefritis "
        "del injerto."
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


def _tab_simulador():
    st.subheader("📈 Simulador de curva renográfica")
    st.caption("Curva actividad-tiempo (cuentas vs minutos) generada con un modelo "
               "fisiológico. Cambia el escenario y observa cómo varían el ascenso, "
               "el Tmax y el lavado.")

    c1, c2 = st.columns([2, 1])
    escenario = c1.selectbox("Escenario clínico", list(ESCENARIOS_CURVA.keys()),
                             key="sim_esc")
    funcion = c2.slider("Función del riñón (×)", 0.2, 1.3, 1.0, 0.05,
                        key="sim_fun",
                        help="Multiplicador de captación; simula mejor/peor función.")

    c3, c4, c5 = st.columns([1, 1, 1])
    diuretico = c3.checkbox("💧 Administrar furosemida", key="sim_diur")
    t_diur = c4.slider("Minuto de furosemida", 5, 25, 18, 1, key="sim_tdiur",
                       disabled=not diuretico)
    comparar = c5.checkbox("Superponer curva normal", value=True, key="sim_cmp")

    # ── Simulación ──────────────────────────────────────────────────────────
    t, counts = simular_renograma(escenario, funcion=funcion,
                                  diuretico=diuretico, t_diur=float(t_diur))
    tmax, pico, t_half = metricas_renograma(t, counts)

    # OJO: el nombre de la columna NO debe llevar punto. En Vega-Lite/Altair
    # un "." se interpreta como acceso a campo anidado y la línea no se dibuja.
    df = pd.DataFrame({"Tiempo (min)": t, "Actividad (cuentas)": counts,
                       "Curva": escenario})
    if comparar and escenario != "Normal":
        tn, cn = simular_renograma("Normal", funcion=1.0)
        df = pd.concat([df, pd.DataFrame({"Tiempo (min)": tn,
                        "Actividad (cuentas)": cn, "Curva": "Normal (referencia)"})],
                       ignore_index=True)

    if _ALTAIR:
        base = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
            x=alt.X("Tiempo (min):Q"),
            y=alt.Y("Actividad (cuentas):Q"),
            color=alt.Color("Curva:N",
                            scale=alt.Scale(range=["#3B82F6", "#94A3B8"]),
                            legend=alt.Legend(orient="top", title=None)),
        )
        capas = [base]
        capas.append(alt.Chart(pd.DataFrame({"x": [tmax]})).mark_rule(
            strokeDash=[2, 2], color="#64748B").encode(x="x:Q"))
        if diuretico:
            capas.append(alt.Chart(pd.DataFrame({"x": [t_diur]})).mark_rule(
                color="#F59E0B", size=2).encode(x="x:Q"))
        st.altair_chart(alt.layer(*capas).properties(height=340),
                        use_container_width=True)
    else:
        pivot = df.pivot_table(index="Tiempo (min)", columns="Curva",
                               values="Actividad (cuentas)")
        st.line_chart(pivot, height=340)
        marca = f"Tmax ≈ {tmax} min"
        if diuretico:
            marca += f" · furosemida al min {t_diur}"
        st.caption(marca)

    # ── Métricas ────────────────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric("Tmax", f"{tmax} min",
              help="Tiempo al pico de actividad parenquimatosa (normal 3-5 min).")
    if t_half is None:
        m2.metric("T½ de lavado", "Sin lavado",
                  help="No alcanza la mitad del pico → retención.")
    else:
        m2.metric("T½ de lavado", f"{t_half} min")
    pico_rel = pico / (simular_renograma("Normal")[1].max()) * 100
    m3.metric("Amplitud vs normal", f"{pico_rel:.0f}%",
              help="Altura del pico relativa a un riñón normal.")

    # ── Interpretación del lavado ───────────────────────────────────────────
    if t_half is not None:
        titulo, detalle = clasifica_t12_diuretico(t_half)
        st.info(f"**Lavado:** {titulo}. {detalle}")
    else:
        st.warning("**Lavado:** sin descenso a la mitad del pico → patrón de "
                   "retención. Si es obstructivo, no responderá a la furosemida.")

    st.caption(f"ℹ️ {ESCENARIOS_CURVA[escenario]['nota']}")

    if escenario.startswith("Dilatación") and not diuretico:
        st.warning("💡 Activa la furosemida: verás cómo esta curva — idéntica a una "
                   "obstrucción sin diurético — sí lava. Ese es el fundamento del "
                   "renograma diurético.")


def render():
    """Punto de entrada del módulo. Llamar desde el enrutador de RenalPro."""
    st.title("🔬 Gamagrama Renal")
    st.caption("RenalPro · TRRC360 — Referencia clínica y herramientas de cálculo")

    tabs = st.tabs([
        "📖 Referencia",
        "📈 Renograma dinámico",
        "🌡️ Simulador",
        "🧮 Calculadoras",
        "🫘 Trasplante",
    ])
    with tabs[0]:
        _tab_referencia()
    with tabs[1]:
        _tab_dinamico()
    with tabs[2]:
        _tab_simulador()
    with tabs[3]:
        _tab_calculadoras()
    with tabs[4]:
        _tab_trasplante()

    st.divider()
    st.caption("⚠️ Apoyo a la decisión clínica. No sustituye la lectura del "
               "especialista en medicina nuclear. Rangos según guías de "
               "procedimiento EANM/SNMMI de renografía.")


if __name__ == "__main__":
    st.set_page_config(page_title="Gamagrama Renal — RenalPro", page_icon="🔬",
                       layout="wide")
    render()

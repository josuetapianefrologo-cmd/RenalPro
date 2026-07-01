"""
RenalPro (TRRC360) — Módulo: Herramientas de Trasplante Renal
=============================================================
Cuatro utilidades para el seguimiento del trasplante renal:

  1) Variabilidad intrapaciente de tacrolimus (CV%)  — calculadora propia.
  2) Conversión de inmunosupresión (IR→ER, CNI→belatacept, CNI→mTOR) — referencia.
  3) iBox (predicción de pérdida del injerto) — estructura de variables + enlace
     a la herramienta oficial (NO reproduce el modelo Cox propietario).
  4) Riesgo de ERC del donante vivo (Grams) — estructura de variables + enlace a
     la calculadora oficial (NO reproduce el modelo; es un modelo estadounidense).

Integración:
    from renalpro_tx_tools import render
    render()

Contenido clínico validado contra fuentes primarias (citadas en cada pestaña).
NO se inventan coeficientes ni cortes: iBox y Grams enlazan a su calculadora
oficial validada.

Autor: Josué Tapia Nefrólogo — Tapia Nefrología
"""

import re
import streamlit as st


# ---------------------------------------------------------------------------
# 1) Variabilidad intrapaciente de tacrolimus (CV%)
# ---------------------------------------------------------------------------
def _parse_niveles(txt: str):
    """Extrae números (float) de un texto con comas, espacios o saltos de línea."""
    vals = []
    for tok in re.findall(r"[-+]?\d*[.,]?\d+", txt or ""):
        tok = tok.replace(",", ".")
        try:
            v = float(tok)
            if 0 < v < 100:          # rango plausible de C0 de tacrolimus (ng/mL)
                vals.append(v)
        except ValueError:
            pass
    return vals


def _cv_muestral(vals):
    """CV% = DE muestral / media × 100 (DE con n-1)."""
    n = len(vals)
    media = sum(vals) / n
    var = sum((x - media) ** 2 for x in vals) / (n - 1)   # muestral (n-1)
    de = var ** 0.5
    cv = de / media * 100 if media > 0 else 0.0
    return media, de, cv


def _tab_tacro_cv():
    st.markdown("### 📈 Variabilidad intrapaciente de tacrolimus (CV%)")
    st.caption("La variabilidad intrapaciente (IPV) de los niveles valle (C0) de "
               "tacrolimus es un **marcador de riesgo modificable**: una IPV alta se "
               "asocia a rechazo, DSA *de novo* y pérdida del injerto.")

    st.info("**Fórmula:** CV% = (desviación estándar / media) × 100, sobre una serie "
            "de niveles valle (C0) del **mismo paciente** en estado estable.")

    default = "8.2, 6.1, 11.4, 7.0, 9.8, 5.3"
    txt = st.text_area(
        "Niveles C0 de tacrolimus (ng/mL) — separa por coma, espacio o salto de línea",
        value=default, height=90, key="txcv_input",
        help="Idealmente ≥3 niveles valle ambulatorios, en estado estable, misma "
             "formulación y mismo laboratorio.")

    vals = _parse_niveles(txt)

    if len(vals) < 3:
        st.warning("Ingresa al menos **3** niveles válidos (0–100 ng/mL) para calcular la variabilidad.")
    else:
        media, de, cv = _cv_muestral(vals)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("n niveles", len(vals))
        c2.metric("Media C0", f"{media:.1f} ng/mL")
        c3.metric("DE", f"{de:.2f}")
        c4.metric("CV%", f"{cv:.1f}%")
        st.caption(f"Rango: {min(vals):.1f}–{max(vals):.1f} ng/mL · "
                   f"valores usados: {', '.join(f'{v:.1f}' for v in vals)}")

        # Interpretación (umbral pragmático; los cortes varían entre estudios)
        if cv >= 30:
            st.error(
                f"🔴 **CV {cv:.1f}% — variabilidad ALTA.** Asociada a mayor riesgo de "
                "rechazo, DSA de novo y pérdida del injerto. Buscar y corregir causas "
                "(ver abajo).")
        elif cv >= 25:
            st.warning(
                f"🟡 **CV {cv:.1f}% — variabilidad limítrofe.** Vigilar tendencia y "
                "reforzar adherencia; reevaluar con más niveles.")
        else:
            st.success(f"🟢 **CV {cv:.1f}% — variabilidad aceptable.** Mantener adherencia y monitoreo habitual.")

        st.caption("⚠️ No existe un corte universal: los estudios usan umbrales de "
                   "**~25–40%** para 'alta variabilidad'. Es un marcador de riesgo, "
                   "no un diagnóstico. Interpretar junto con la clínica.")

    with st.expander("🔎 Cómo medirla bien y qué hacer si es alta"):
        st.markdown("""
**Buenas prácticas de medición**
- Usar **≥3 niveles valle (C0) ambulatorios** en estado estable.
- **Excluir** los primeros ~1–3 meses post-Tx (dosis en ajuste activo).
- Misma **formulación** de tacrolimus y mismo laboratorio/técnica.
- Extraer siempre a la misma hora relativa a la dosis (valle real, 12/24 h).

**Causas de variabilidad alta a investigar**
- **No adherencia** (la causa más frecuente y modificable).
- **Interacciones farmacológicas** (azoles, diltiazem/verapamilo, rifampicina,
  anticonvulsivantes, inductores/inhibidores de CYP3A4/P-gp).
- Cambios de **formulación** (IR ↔ ER, genéricos).
- **Diarrea/absorción variable**, alimentos, jugo de toronja.
- Errores de horario de toma o de extracción.

**Conducta**
- Reforzar educación y adherencia; simplificar régimen (considerar formulación de
  liberación prolongada de dosis única).
- Revisar y ajustar interacciones.
- Aumentar la frecuencia de monitoreo si la IPV persiste alta.
        """)
        st.caption("Ref: Shuker N, van Gelder T, Hesselink DA. *Transplant Rev* 2015. · "
                   "Rodrigo E et al. *Transplantation* 2016. · Vanhove T et al. "
                   "*Am J Transplant* 2016. · Gonzales HM et al. *Transplant Rev* 2020.")


# ---------------------------------------------------------------------------
# 2) Conversión de inmunosupresión (referencia)
# ---------------------------------------------------------------------------
def _tab_conversion():
    st.markdown("### 🔄 Conversión de inmunosupresión")
    st.caption("Referencia rápida de conversiones frecuentes. Ajustar siempre al "
               "**protocolo institucional**, al riesgo inmunológico y al monitoreo de niveles.")

    sub = st.radio("Selecciona la conversión",
                   ["Tacrolimus IR → liberación prolongada (ER)",
                    "CNI → Belatacept",
                    "CNI → inhibidor de mTOR (everolimus/sirolimus)"],
                   key="conv_sel")

    if sub.startswith("Tacrolimus IR"):
        st.markdown("#### Tacrolimus de liberación inmediata → prolongada")
        st.table({
            "Formulación destino": ["Tacrolimus OD (Advagraf®/Astagraf XL®)",
                                     "Tacrolimus LCP (Envarsus®)"],
            "Conversión de dosis total diaria": ["**1 : 1** (misma dosis total/día)",
                                                  "**≈ –30 %** (mayor biodisponibilidad)"],
            "Meta C0": ["Igual que con IR", "Igual que con IR"],
        })
        st.info("Recontrolar **C0 en 7–14 días** y titular a la meta. La misma meta de "
                "nivel valle aplica; cambia la **dosis**, no el objetivo. Vigilar de cerca "
                "en el cambio (riesgo de infra/supraexposición).")
        st.caption("Ref: información de prescripción de Advagraf®/Astagraf XL® y Envarsus® "
                   "(LCP-tacrolimus, ~30% menor dosis por mayor biodisponibilidad).")

    elif sub.startswith("CNI → Belatacept"):
        st.markdown("#### Inhibidor de calcineurina → Belatacept")
        st.error("🛑 **Requisito absoluto: EBV IgG POSITIVO (seropositivo).** "
                 "Belatacept está **contraindicado en EBV-seronegativos** por riesgo de "
                 "trastorno linfoproliferativo post-trasplante (PTLD/SNC).")
        st.markdown("""
**Perfil**
- **Ventajas:** mejor función del injerto (eGFR) a largo plazo, evita nefrotoxicidad
  por CNI, mejor perfil metabólico/cardiovascular (ensayos BENEFIT / BENEFIT-EXT).
- **Riesgos:** mayor tasa de **rechazo agudo** (sobre todo temprano y en conversión),
  infusión IV mensual, **PTLD** en EBV-negativos.
- **Precaución:** no de primera elección en **alto riesgo inmunológico**; la conversión
  suele hacerse en pacientes estables y bajo protocolo.
""")
        st.caption("Ref: Vincenti F et al. *N Engl J Med* 2016 (BENEFIT a 7 años). "
                   "Ficha técnica de belatacept (requisito EBV+).")

    else:
        st.markdown("#### Inhibidor de calcineurina → inhibidor de mTOR")
        st.markdown("""
**Indicaciones frecuentes**
- **Neoplasia** post-trasplante (especialmente cáncer de piel no melanoma, sarcoma de Kaposi).
- Nefrotoxicidad por CNI; estrategia de minimización de CNI.
- Reducción de eventos por CMV.

**Precauciones / contraindicaciones relativas**
- **Evitar en el post-Tx temprano** (mala cicatrización, linfocele, dehiscencia).
- **Proteinuria** (evitar/suspender si > ~0.8–1 g/día; empeora proteinuria).
- Úlceras orales, dislipidemia, edema, neumonitis, citopenias.
- **Suspender antes de cirugía** electiva (cicatrización).

**Metas orientativas (según protocolo y si se combina con CNI a dosis baja)**
- Everolimus: C0 ~3–8 ng/mL.
- Sirolimus: C0 ~5–15 ng/mL.
""")
        st.caption("Ref: KDIGO Transplant Recipient Guideline 2009; ensayos de conversión "
                   "(CONVERT, ZEUS). Ajustar metas al protocolo institucional.")


# ---------------------------------------------------------------------------
# 3) iBox — estructura de variables + enlace (NO reproduce el modelo)
# ---------------------------------------------------------------------------
def _tab_ibox():
    st.markdown("### 📊 iBox — predicción de pérdida del injerto")
    st.caption("Score integrativo validado internacionalmente (Loupy, Aubert et al., "
               "*BMJ* 2019). C-statistic ~0.81; estima el riesgo individual de pérdida "
               "del injerto **hasta ~7–10 años** desde el momento de la evaluación.")

    st.warning("ℹ️ **Este panel NO calcula el iBox.** El modelo de Cox exacto es "
               "propietario (plataforma Cibiltech/Predigraft) y sus coeficientes no se "
               "reproducen aquí para no introducir imprecisiones. Úsalo como **checklist "
               "de variables** y realiza el cálculo en la herramienta oficial.")

    st.markdown("#### Variables que integra el iBox (recolecta estos datos)")
    st.markdown("""
| Dominio | Parámetro |
|---|---|
| ⏱️ Tiempo | Tiempo desde el trasplante hasta la evaluación |
| 🩺 Funcional | eGFR (mL/min/1.73 m²) |
| 🧪 Funcional | Proteinuria (cociente proteína/creatinina urinaria) |
| 🧬 Inmunológico | Anticuerpos donante-específicos (DSA) anti-HLA + **MFI** |
| 🔬 Histológico (Banff) | Inflamación intersticial + tubulitis (i + t) |
| 🔬 Histológico (Banff) | Inflamación de la microcirculación (g + ptc) |
| 🔬 Histológico (Banff) | Fibrosis intersticial / atrofia tubular (IFTA) |
| 🔬 Histológico (Banff) | Glomerulopatía del trasplante (cg) |
""")
    st.info("Requiere una **biopsia del injerto** (para las lesiones Banff) y estudio de "
            "DSA. Un iBox más alto ⇒ mayor riesgo ⇒ intensificar monitoreo/estrategia; "
            "también se usa como desenlace subrogado en ensayos.")

    st.link_button("📄 Artículo original (BMJ 2019, l4923)",
                   "https://www.bmj.com/content/366/bmj.l4923")
    st.caption("Ref: Loupy A, Aubert O, et al. *BMJ* 2019;366:l4923. Cálculo oficial vía "
               "la plataforma propietaria (Predigraft/Cibiltech).")


# ---------------------------------------------------------------------------
# 4) Riesgo de ERC del donante vivo (Grams) — estructura + enlace
# ---------------------------------------------------------------------------
def _tab_donante_riesgo():
    st.markdown("### 🫀 Riesgo de ERC del donante vivo (proyección de por vida)")
    st.caption("Proyecta el riesgo de enfermedad renal terminal (ERC-T) **a 15 años y de "
               "por vida en ausencia de donación** (Grams et al., *N Engl J Med* 2016). "
               "Ayuda a hacer más empírica y transparente la aceptación del donante.")

    st.warning("ℹ️ **Este panel NO calcula el riesgo.** El modelo (riesgos competitivos, "
               "calibrado a la incidencia de ERC-T en EE. UU.) no se reproduce aquí. Usa "
               "la **calculadora oficial** y trae estos datos.")

    st.error("⚠️ **Aplicabilidad a México:** es un modelo **estadounidense y estratificado "
             "por raza (negro/blanco)**. Su transferencia a población mexicana/hispana es "
             "limitada — interpretar con cautela y complementar con el juicio clínico y el "
             "protocolo del centro.")

    st.markdown("#### Variables que necesita (10)")
    st.markdown("""
| # | Variable | Unidad / categoría |
|---|---|---|
| 1 | Edad | años |
| 2 | Sexo | hombre / mujer |
| 3 | Raza | negro / blanco (limitación del modelo) |
| 4 | eGFR | mL/min/1.73 m² |
| 5 | Cociente albúmina/creatinina (ACR) | mg/g |
| 6 | Presión arterial sistólica | mmHg |
| 7 | Uso de antihipertensivos | sí / no |
| 8 | Diabetes (no insulinodependiente) | sí / no |
| 9 | Tabaquismo | nunca / previo / actual |
| 10 | Índice de masa corporal (IMC) | kg/m² |
""")
    st.info("La proyección informa una decisión **individualizada** (no un rechazo por un "
            "solo factor). Muchos centros definen un **umbral de riesgo de por vida "
            "aceptable** (KDIGO Donante Vivo 2017); confróntalo con tu protocolo.")

    st.link_button("🧮 Calculadora oficial (transplantmodels.com)",
                   "http://www.transplantmodels.com/esrdrisk/")
    st.caption("Ref: Grams ME, et al. *N Engl J Med* 2016;374:411-421. "
               "KDIGO Living Kidney Donor Guideline 2017.")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def render():
    """Página 'Herramientas de Trasplante'. Llamar desde app.py."""
    st.subheader("🧰 Herramientas de Trasplante Renal")
    st.caption("Variabilidad de tacrolimus · conversión de inmunosupresión · iBox · "
               "riesgo del donante vivo. Contenido validado contra fuentes primarias.")
    tabs = st.tabs(["📈 Variabilidad Tacrolimus",
                    "🔄 Conversión IS",
                    "📊 iBox",
                    "🫀 Riesgo ERC Donante"])
    with tabs[0]:
        _tab_tacro_cv()
    with tabs[1]:
        _tab_conversion()
    with tabs[2]:
        _tab_ibox()
    with tabs[3]:
        _tab_donante_riesgo()


if __name__ == "__main__":
    st.set_page_config(page_title="Herramientas TR — RenalPro", page_icon="🧰",
                       layout="wide")
    render()

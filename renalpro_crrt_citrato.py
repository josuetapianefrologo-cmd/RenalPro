# ============================================================
# renalpro_crrt_citrato.py
# RenalPro v3.1.0 | TRRC360
# Módulo: Prescripción CRRT integrada con Citrato RCA
#
# Integra en app.py bajo TRRC/CRRT → "Prescripción con Citrato":
#   from renalpro_crrt_citrato import render_crrt_citrato_integrado
#   render_crrt_citrato_integrado()
# ============================================================

import streamlit as st
from datetime import date
from io import BytesIO
import base64

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage,
)

# ─── Catálogo de soluciones ─────────────────────────────────────────────────

SOLUCIONES_CITRATO = {
    "Prismocitrate 18/0 (18 mmol/L)":   18.0,
    "Prismocitrate 10/2 (10 mmol/L)":   10.0,
    "ACD-A Baxter (113 mmol/L)":        113.0,
    "Citrato trisódico 4% (136 mmol/L)": 136.0,
    "Preparación local — especificar":   None,
}

SOLUCIONES_CALCIO = {
    "Gluconato de calcio 10% (0.225 mmol/mL)": 0.225,
    "Cloruro de calcio 10% (0.68 mmol/mL)":    0.680,
    "Preparación local — especificar":          None,
}

MODALIDADES = ["CVVH", "CVVHD", "CVVHDF"]

# ─── Lógica de cálculo ───────────────────────────────────────────────────────

def calcular_prescripcion(peso, dosis_objetivo, qs, net_uf,
                           citrato_conc, target_citrato_sangre,
                           calcio_conc_mmol_ml, modalidad,
                           qd=0, fraccion_prefiltro=1.0):
    """
    Calcula la prescripción CRRT completa integrada con citrato RCA.

    Parámetros:
        peso                  kg
        dosis_objetivo        mL/kg/hr (efluente total objetivo)
        qs                    mL/min (flujo de sangre)
        net_uf                mL/hr (retiro neto de líquido al paciente)
        citrato_conc          mmol/L de la solución de citrato
        target_citrato_sangre mmol/L en sangre (default 3.0)
        calcio_conc_mmol_ml   mmol/mL de la solución de calcio
        modalidad             CVVH | CVVHD | CVVHDF
        qd                    mL/hr dializante (solo CVVHD/CVVHDF)
        fraccion_prefiltro    0-1, proporción de reposición prefiltro (no citrato)

    Retorna dict con todos los flujos calculados y alertas.
    """
    res = {}

    # ── Efluentes ──────────────────────────────────────────────────────────
    efluente_total     = dosis_objetivo * peso              # mL/hr
    res["efluente_total"]   = round(efluente_total, 1)
    res["dosis_objetivo"]   = dosis_objetivo
    res["peso"]             = peso

    # ── Citrato prefiltro ──────────────────────────────────────────────────
    # Fórmula: Qs (mL/min) × 60 × target_mmol/L ÷ concentración_mmol/L
    qs_ml_hr          = qs * 60
    citrato_flow      = (qs_ml_hr * target_citrato_sangre) / citrato_conc
    citrato_mmol_hr   = (citrato_flow * citrato_conc) / 1000

    res["citrato_flow"]     = round(citrato_flow, 1)        # mL/hr prefiltro
    res["citrato_mmol_hr"]  = round(citrato_mmol_hr, 2)     # mmol/hr
    res["citrato_sangre"]   = round(target_citrato_sangre, 2)  # mmol/L en sangre
    res["qs_ml_hr"]         = qs_ml_hr

    # ── Calcio postfiltro ──────────────────────────────────────────────────
    # Estándar: reponer ~50% del Ca quelado por citrato
    # (ajustar según iCa postfiltro objetivo 1.0-1.35 mmol/L)
    ca_mmol_hr        = citrato_mmol_hr * 0.5              # mmol/hr a reponer
    ca_flow           = ca_mmol_hr / calcio_conc_mmol_ml   # mL/hr
    res["ca_flow"]          = round(ca_flow, 1)
    res["ca_mmol_hr"]       = round(ca_mmol_hr, 2)

    # ── Flujos restantes ───────────────────────────────────────────────────
    # Efluente = citrato + reposición_post + dializante + UF_neta
    # (el citrato ya ES parte del efluente al pasar por el filtro)
    restante = efluente_total - citrato_flow - net_uf

    if modalidad == "CVVH":
        # Solo reposición. Citrato ya es prefiltro.
        # Reposición postfiltro adicional = restante
        q_rep_post = max(restante, 0)
        q_rep_pre_extra = 0
        q_dializante = 0
    elif modalidad == "CVVHD":
        # Solo dializante, sin reposición adicional
        q_rep_post = 0
        q_rep_pre_extra = 0
        q_dializante = max(restante, 0)
    else:  # CVVHDF
        # Dializante fijo (si se especificó) + reposición el resto
        q_dializante = min(qd, max(restante, 0))
        q_rep_post = max(restante - q_dializante, 0) * (1 - fraccion_prefiltro)
        q_rep_pre_extra = max(restante - q_dializante, 0) * fraccion_prefiltro

    res["q_rep_post"]       = round(q_rep_post, 1)
    res["q_rep_pre_extra"]  = round(q_rep_pre_extra, 1)
    res["q_dializante"]     = round(q_dializante, 1)
    res["net_uf"]           = round(net_uf, 1)

    # ── Fracción de filtración ─────────────────────────────────────────────
    # Con predilución citrato: FF = efluente / (Qs_ml_hr + citrato_flow)
    ff = efluente_total / (qs_ml_hr + citrato_flow) * 100
    res["ff"] = round(ff, 1)

    # ── Ratio citrato:sangre ───────────────────────────────────────────────
    res["ratio_cit_sangre"] = round(citrato_flow / qs_ml_hr * 100, 1)  # %

    # ── Dosis real entregada ───────────────────────────────────────────────
    dosis_real = efluente_total / peso
    res["dosis_real"] = round(dosis_real, 1)

    # ── Verificación del balance ───────────────────────────────────────────
    # Total en = citrato + rep_post + rep_pre_extra + ca_flow
    # Total out = efluente_total (incluye citrato que pasa por filtro) + UF_neta
    total_entrada = citrato_flow + q_rep_post + q_rep_pre_extra + ca_flow
    res["total_entrada"]    = round(total_entrada, 1)
    res["balance_neto"]     = round(net_uf, 1)  # retiro neto real

    # ── Alertas ────────────────────────────────────────────────────────────
    alertas = []
    if ff > 30:
        alertas.append(("error",
            f"⚠️ Fracción de filtración {ff:.1f}% > 30% — "
            "riesgo de coagulación del filtro. Aumentar Qs o reducir efluente."))
    if res["ratio_cit_sangre"] > 25:
        alertas.append(("warning",
            f"🟡 Citrato representa {res['ratio_cit_sangre']}% del flujo sanguíneo — "
            "dilución significativa."))
    if not (20 <= dosis_real <= 35):
        alertas.append(("warning",
            f"🟡 Dosis entregada {dosis_real:.1f} mL/kg/hr — "
            "rango recomendado KDIGO: 20-25 mL/kg/hr."))
    if target_citrato_sangre < 2.5 or target_citrato_sangre > 4.0:
        alertas.append(("warning",
            f"🟡 Target citrato en sangre {target_citrato_sangre} mmol/L — "
            "rango terapéutico recomendado: 2.5–4.0 mmol/L."))
    if restante < 0:
        alertas.append(("error",
            "❌ El citrato + UF neta supera el efluente objetivo. "
            "Reducir UF neta o aumentar dosis."))

    res["alertas"] = alertas
    return res


# ─── UI principal ────────────────────────────────────────────────────────────

def render_crrt_citrato_integrado(user_data=None, patient_data=None):
    """
    Renderiza el módulo integrado CRRT + Citrato RCA.
    Uso en app.py:
        from renalpro_crrt_citrato import render_crrt_citrato_integrado
        render_crrt_citrato_integrado(user_data=st.session_state.get("user"),
                                      patient_data=selected_patient)
    """
    st.markdown("## 💧 Prescripción CRRT — Citrato RCA Integrado")
    st.caption("El citrato prefiltro forma parte del cálculo de dosis y flujos.")

    # ── Inputs en dos columnas ─────────────────────────────────────────────
    col_izq, col_der = st.columns([1, 1], gap="large")

    with col_izq:
        st.markdown("#### 🧑‍⚕️ Paciente y objetivo")
        peso = st.number_input("Peso (kg)", min_value=20.0, max_value=200.0,
                               value=float(patient_data.get("peso", 70)) 
                               if patient_data else 70.0,
                               step=0.5, key="crrt_cit_peso")
        dosis_obj = st.number_input("Dosis CRRT objetivo (mL/kg/hr)",
                                    min_value=10.0, max_value=50.0,
                                    value=25.0, step=0.5, key="crrt_cit_dosis")
        net_uf = st.number_input("UF neta (retiro al paciente, mL/hr)",
                                  min_value=0.0, max_value=500.0,
                                  value=100.0, step=10.0, key="crrt_cit_uf")
        modalidad = st.selectbox("Modalidad", MODALIDADES, key="crrt_cit_mod")
        if modalidad in ("CVVHD", "CVVHDF"):
            qd = st.number_input("Flujo dializante Qd (mL/hr)",
                                  min_value=0.0, max_value=3000.0,
                                  value=500.0, step=50.0, key="crrt_cit_qd")
        else:
            qd = 0.0

        st.markdown("#### ⚙️ Circuito")
        qs = st.number_input("Flujo sanguíneo Qs (mL/min)",
                              min_value=50.0, max_value=300.0,
                              value=120.0, step=5.0, key="crrt_cit_qs")

    with col_der:
        st.markdown("#### 🍋 Citrato")
        cit_sel = st.selectbox("Solución de citrato", list(SOLUCIONES_CITRATO.keys()),
                                key="crrt_cit_sol")
        if SOLUCIONES_CITRATO[cit_sel] is None:
            citrato_conc = st.number_input("Concentración citrato (mmol/L)",
                                            min_value=1.0, max_value=200.0,
                                            value=18.0, key="crrt_cit_conc_custom")
        else:
            citrato_conc = SOLUCIONES_CITRATO[cit_sel]
            st.info(f"Concentración: **{citrato_conc} mmol/L**")

        target_cit = st.slider("Target citrato en sangre (mmol/L)",
                                min_value=2.0, max_value=5.0,
                                value=3.0, step=0.1, key="crrt_cit_target")
        st.caption("Rango terapéutico recomendado: 2.5–4.0 mmol/L")

        st.markdown("#### 🧪 Calcio postfiltro")
        ca_sel = st.selectbox("Solución de calcio", list(SOLUCIONES_CALCIO.keys()),
                               key="crrt_cit_ca_sol")
        if SOLUCIONES_CALCIO[ca_sel] is None:
            ca_conc = st.number_input("Concentración calcio (mmol/mL)",
                                       min_value=0.1, max_value=2.0,
                                       value=0.225, key="crrt_cit_ca_custom")
        else:
            ca_conc = SOLUCIONES_CALCIO[ca_sel]
            st.info(f"Concentración: **{ca_conc} mmol/mL** "
                    f"({ca_conc * 1000:.0f} mmol/L)")

    # ── Calcular ───────────────────────────────────────────────────────────
    st.markdown("---")
    r = calcular_prescripcion(
        peso=peso, dosis_objetivo=dosis_obj, qs=qs, net_uf=net_uf,
        citrato_conc=citrato_conc, target_citrato_sangre=target_cit,
        calcio_conc_mmol_ml=ca_conc, modalidad=modalidad, qd=qd,
    )

    # ── Alertas de seguridad ───────────────────────────────────────────────
    for nivel, msg in r["alertas"]:
        getattr(st, nivel)(msg)

    # ── Tabla de prescripción completa ─────────────────────────────────────
    st.markdown("### 📋 Prescripción completa")

    AZUL = "#1B4F72"
    VERDE = "#1E8449"

    # Tarjetas de métricas principales
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Efluente objetivo", f"{r['efluente_total']} mL/hr",
              f"{r['dosis_real']} mL/kg/hr")
    m2.metric("Dosis entregada", f"{r['dosis_real']} mL/kg/hr",
              delta="✅ OK" if 20 <= r["dosis_real"] <= 35 else "⚠️ Revisar",
              delta_color="off")
    m3.metric("Fracción filtración", f"{r['ff']}%",
              delta="✅ <30%" if r["ff"] <= 30 else "⚠️ Alta",
              delta_color="off")
    m4.metric("Citrato en sangre", f"{r['citrato_sangre']} mmol/L")

    st.markdown("---")

    # Tabla de flujos detallada
    st.markdown("#### Flujos del circuito")

    flujos = [
        ["📍 Lugar", "💉 Fluido", "➡️ Flujo (mL/hr)", "📌 Concepto"],
        ["PREFILTRO", f"Citrato ({citrato_conc} mmol/L)",
         f"**{r['citrato_flow']}**",
         f"= Qs ({qs} mL/min) × 10 → anticoagulación + predilución"],
    ]

    if r["q_rep_pre_extra"] > 0:
        flujos.append(["PREFILTRO", "Solución de reposición",
                       f"{r['q_rep_pre_extra']}",
                       "Reposición prefiltro adicional"])

    if r["q_rep_post"] > 0:
        flujos.append(["POSTFILTRO", "Solución de reposición",
                       f"{r['q_rep_post']}",
                       "Reposición postfiltro"])

    flujos.append(["POSTFILTRO", f"Calcio ({ca_sel.split('(')[0].strip()})",
                   f"**{r['ca_flow']}**",
                   f"= {r['ca_mmol_hr']} mmol/hr Ca²⁺ (50% del citrato)"])

    if r["q_dializante"] > 0:
        flujos.append(["FILTRO", "Dializante",
                       f"{r['q_dializante']}",
                       f"Qd {modalidad}"])

    flujos.append(["FILTRO", "⬇️ Efluente total",
                   f"**{r['efluente_total']}**",
                   f"= {r['dosis_real']} mL/kg/hr"])

    flujos.append(["PACIENTE", "💧 Retiro neto (UF)",
                   f"{r['net_uf']}",
                   "Balance negativo prescrito"])

    for row in flujos[1:]:  # header ya incluido
        pass

    df_display = []
    header = flujos[0]
    df_display.append(header)
    df_display.extend(flujos[1:])

    # Renderizar como tabla Streamlit
    st.table({
        "📍 Lugar":         [r[0] for r in flujos[1:]],
        "💉 Fluido":        [r[1] for r in flujos[1:]],
        "mL/hr":            [r[2] for r in flujos[1:]],
        "Concepto":         [r[3] for r in flujos[1:]],
    })

    # ── Resumen de mmol/hr ─────────────────────────────────────────────────
    st.markdown("#### Balance de citrato y calcio")
    bc1, bc2, bc3 = st.columns(3)
    bc1.metric("Citrato infundido", f"{r['citrato_mmol_hr']} mmol/hr",
               f"= {r['citrato_flow']} mL/hr × {citrato_conc} mmol/L")
    bc2.metric("Calcio repuesto", f"{r['ca_mmol_hr']} mmol/hr",
               f"= {r['ca_flow']} mL/hr")
    bc3.metric("Ratio citrato:sangre", f"{r['ratio_cit_sangre']}%",
               f"{r['citrato_flow']} / {r['qs_ml_hr']} mL/hr")

    # ── Monitoreo iCa ──────────────────────────────────────────────────────
    with st.expander("🔬 Monitoreo iCa (guía de ajuste)", expanded=False):
        st.markdown("""
| Medición | Objetivo | Acción si fuera de rango |
|---|---|---|
| **iCa postfiltro** | 0.25–0.35 mmol/L | ↑ citrato si >0.35 · ↓ citrato si <0.25 |
| **iCa sistémico** | 1.0–1.35 mmol/L | ↑ Ca postfiltro si <1.0 · ↓ si >1.35 |
| **Ratio iCa sistémico/postfiltro** | <2.5 | Si >2.5: acumulación de citrato (disfunción hepática) |

**Frecuencia:** Cada 6 h las primeras 24 h, luego cada 12–24 h si estable.
        """)

    with st.expander("📐 Fórmulas utilizadas", expanded=False):
        st.markdown(f"""
**Citrato prefiltro (mL/hr)**
```
= Qs ({qs} mL/min) × 60 × Target citrato ({target_cit} mmol/L)
  ÷ Concentración solución ({citrato_conc} mmol/L)
= {qs} × 60 × {target_cit} ÷ {citrato_conc}
= **{r['citrato_flow']} mL/hr**
```
→ Regla de cabecera cuando conc=18 y target=3: **Qs × 10** = {qs} × 10 = {qs*10}

**Calcio postfiltro (mL/hr)**
```
= Citrato mmol/hr ({r['citrato_mmol_hr']}) × 0.5
  ÷ Concentración Ca ({ca_conc} mmol/mL)
= {r['citrato_mmol_hr']} × 0.5 ÷ {ca_conc}
= **{r['ca_flow']} mL/hr**
```

**Fracción de filtración**
```
FF = Efluente total ÷ (Qs_mL/hr + Citrato_mL/hr)
   = {r['efluente_total']} ÷ ({r['qs_ml_hr']} + {r['citrato_flow']})
   = **{r['ff']}%**   (objetivo <30%)
```
        """)

    # ── Botón PDF ──────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🖨️ Generar PDF de prescripción", type="primary",
                 key="crrt_cit_pdf"):
        pdf = _generar_pdf_crrt(r, peso, dosis_obj, qs, net_uf,
                                citrato_conc, cit_sel, ca_conc, ca_sel,
                                target_cit, modalidad, user_data, patient_data)
        nombre = f"CRRT_Citrato_{date.today().strftime('%Y%m%d')}.pdf"
        st.download_button("⬇️ Descargar PDF", data=pdf,
                           file_name=nombre, mime="application/pdf")


# ─── Generador PDF ───────────────────────────────────────────────────────────

def _generar_pdf_crrt(r, peso, dosis_obj, qs, net_uf,
                      citrato_conc, cit_nombre, ca_conc, ca_nombre,
                      target_cit, modalidad, user_data=None, patient_data=None):
    buf = BytesIO()
    u = user_data or {}
    p = patient_data or {}

    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    AZUL  = colors.HexColor("#1B4F72")
    VERDE = colors.HexColor("#1E8449")
    GRIS  = colors.HexColor("#D5D8DC")
    GRIS_SEC = colors.HexColor("#EBF5FB")

    sn = ParagraphStyle("n", fontSize=8.5, leading=12, fontName="Helvetica")
    sb = ParagraphStyle("b", fontSize=8.5, leading=12, fontName="Helvetica-Bold")
    sh = ParagraphStyle("h", fontSize=10, leading=14,
                         fontName="Helvetica-Bold", textColor=AZUL)
    sc = ParagraphStyle("c", fontSize=7, leading=10, fontName="Helvetica",
                         textColor=colors.HexColor("#555555"))
    st_title = ParagraphStyle("t", fontSize=12, leading=16,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)

    story = []

    # Header
    logo_b64 = u.get("logo_b64") or u.get("logo")
    logo_img = None
    if logo_b64:
        try:
            logo_img = RLImage(BytesIO(base64.b64decode(logo_b64)),
                               width=3*cm, height=1.5*cm, kind="proportional")
        except Exception:
            pass

    hdr = [[
        logo_img or Paragraph("<b>RENALMEDIC / TRRC360</b>", st_title),
        Paragraph("<b>Prescripción CRRT — Citrato RCA Integrado</b>", st_title),
        Paragraph(f"<b>Fecha: {date.today().strftime('%d/%m/%Y')}</b><br/>"
                  f"Dr. {u.get('nombre','Josué W. Tapia López')}<br/>"
                  f"Nefr. Cédula {u.get('cedula_especialidad','9940966')}",
                  sc),
    ]]
    t_hdr = Table(hdr, colWidths=[4*cm, 10*cm, 5*cm])
    t_hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, AZUL),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_hdr)
    story.append(Spacer(1, 0.3*cm))

    # Datos del paciente
    nombre_p = p.get("nombre_completo", p.get("name", "—"))
    story.append(Paragraph(f"<b>Paciente:</b> {nombre_p}  |  "
                           f"<b>Peso:</b> {peso} kg  |  "
                           f"<b>Modalidad:</b> {modalidad}", sb))
    story.append(Spacer(1, 0.3*cm))

    def sec(titulo):
        t = Table([[Paragraph(titulo, sh)]], colWidths=[19*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRIS_SEC),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, AZUL),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.15*cm))

    # Sección: Objetivos
    sec("OBJETIVOS DE LA PRESCRIPCIÓN")
    obj_data = [
        [Paragraph("<b>Parámetro</b>", sb), Paragraph("<b>Valor</b>", sb),
         Paragraph("<b>Resultado</b>", sb)],
        [Paragraph("Dosis CRRT objetivo", sn),
         Paragraph(f"{dosis_obj} mL/kg/hr", sn),
         Paragraph(f"→ {r['efluente_total']} mL/hr efluente total", sn)],
        [Paragraph("Flujo sanguíneo Qs", sn),
         Paragraph(f"{qs} mL/min", sn),
         Paragraph(f"→ {r['qs_ml_hr']} mL/hr", sn)],
        [Paragraph("UF neta (retiro)", sn),
         Paragraph(f"{net_uf} mL/hr", sn),
         Paragraph(f"→ {net_uf * 24 / 1000:.1f} L/24h", sn)],
        [Paragraph("Target citrato en sangre", sn),
         Paragraph(f"{target_cit} mmol/L", sn),
         Paragraph("Rango terapéutico: 2.5–4.0 mmol/L", sn)],
        [Paragraph("Fracción de filtración", sn),
         Paragraph(f"{r['ff']}%", sn),
         Paragraph("Objetivo: <30%", sn)],
    ]
    t_obj = Table(obj_data, colWidths=[6*cm, 5*cm, 8*cm])
    t_obj.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_obj)
    story.append(Spacer(1, 0.4*cm))

    # Sección: Flujos del circuito
    sec("FLUJOS DEL CIRCUITO — PRESCRIPCIÓN COMPLETA")

    flujos_header = [
        Paragraph("<b>📍 Lugar</b>", sb),
        Paragraph("<b>💉 Fluido</b>", sb),
        Paragraph("<b>mL/hr</b>", sb),
        Paragraph("<b>Concepto</b>", sb),
    ]
    flujos_rows = [flujos_header]

    flujos_rows.append([
        Paragraph("PRE-FILTRO", sb),
        Paragraph(f"Citrato\n({cit_nombre.split('(')[0].strip()})", sn),
        Paragraph(f"<b>{r['citrato_flow']}</b>", sb),
        Paragraph(f"Anticoagulación + predilución\n"
                  f"= Qs×10 = {qs}×10 = {r['citrato_flow']}", sn),
    ])

    if r["q_rep_pre_extra"] > 0:
        flujos_rows.append([
            Paragraph("PRE-FILTRO", sn),
            Paragraph("Solución reposición", sn),
            Paragraph(f"{r['q_rep_pre_extra']}", sn),
            Paragraph("Reposición prefiltro adicional", sn),
        ])

    if r["q_rep_post"] > 0:
        flujos_rows.append([
            Paragraph("POST-FILTRO", sn),
            Paragraph("Solución reposición", sn),
            Paragraph(f"{r['q_rep_post']}", sn),
            Paragraph("Reposición postfiltro", sn),
        ])

    flujos_rows.append([
        Paragraph("POST-FILTRO", sb),
        Paragraph(f"Gluconato Ca 10%\n({ca_nombre.split('(')[0].strip()})", sn),
        Paragraph(f"<b>{r['ca_flow']}</b>", sb),
        Paragraph(f"{r['ca_mmol_hr']} mmol/hr Ca²⁺\n"
                  f"(50% citrato: {r['citrato_mmol_hr']} mmol/hr)", sn),
    ])

    if r["q_dializante"] > 0:
        flujos_rows.append([
            Paragraph("FILTRO", sn),
            Paragraph("Dializante", sn),
            Paragraph(f"{r['q_dializante']}", sn),
            Paragraph(f"Qd {modalidad}", sn),
        ])

    flujos_rows.append([
        Paragraph("FILTRO ↓", sb),
        Paragraph("EFLUENTE TOTAL", sb),
        Paragraph(f"<b>{r['efluente_total']}</b>", sb),
        Paragraph(f"= {r['dosis_real']} mL/kg/hr "
                  f"(objetivo {dosis_obj} mL/kg/hr)", sn),
    ])

    flujos_rows.append([
        Paragraph("PACIENTE", sn),
        Paragraph("Retiro neto (UF)", sn),
        Paragraph(f"{r['net_uf']}", sn),
        Paragraph(f"= {r['net_uf']*24/1000:.1f} L/24h balance negativo", sn),
    ])

    t_flujos = Table(flujos_rows, colWidths=[3*cm, 4*cm, 2.5*cm, 9.5*cm])
    t_flujos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EAF4FB")),  # citrato
        ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#EAFAF1")),  # efluente
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_flujos)
    story.append(Spacer(1, 0.4*cm))

    # Sección: Monitoreo
    sec("MONITOREO iCa — GUÍA DE AJUSTE")
    mon_data = [
        [Paragraph("<b>Medición</b>", sb),
         Paragraph("<b>Objetivo</b>", sb),
         Paragraph("<b>Acción si fuera de rango</b>", sb)],
        [Paragraph("iCa postfiltro", sn),
         Paragraph("0.25–0.35 mmol/L", sn),
         Paragraph("↑ citrato si >0.35  |  ↓ citrato si <0.25", sn)],
        [Paragraph("iCa sistémico", sn),
         Paragraph("1.0–1.35 mmol/L", sn),
         Paragraph("↑ Ca postfiltro si <1.0  |  ↓ Ca si >1.35", sn)],
        [Paragraph("Ratio sistémico/postfiltro", sn),
         Paragraph("<2.5", sn),
         Paragraph("Si >2.5: acumulación citrato → evaluar función hepática", sn)],
    ]
    t_mon = Table(mon_data, colWidths=[4.5*cm, 4*cm, 10.5*cm])
    t_mon.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_mon)
    story.append(Spacer(1, 0.3*cm))

    # Alertas en PDF
    for nivel, msg in r["alertas"]:
        emoji = "⚠️" if nivel == "error" else "🟡"
        story.append(Paragraph(f"{emoji} {msg}", sn))

    # Firma
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
    ced    = u.get("cedula_especialidad", "9940966")
    fila_firma = [[
        firma_img or Spacer(1, 1.5*cm),
        Paragraph(f"<i><b>{medico}</b></i><br/>"
                  f"Nefrología — Cédula: {ced}<br/>"
                  f"<font size='6'>RenalPro v3.1.0 / TRRC360 — "
                  f"{date.today().strftime('%d/%m/%Y')}</font>",
                  sn),
    ]]
    t_firma = Table(fila_firma, colWidths=[5*cm, 14*cm])
    t_firma.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(t_firma)

    doc.build(story)
    buf.seek(0)
    return buf.read()

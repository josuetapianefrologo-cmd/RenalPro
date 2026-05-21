# ============================================================
# renalpro_historia.py
# RenalPro v3.1.0 | TRRC360 — Módulo: Historia Clínica Completa
# Importar en app.py:
#   from renalpro_historia import render_historia_clinica_tab
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage,
)


# ─── DB helpers ─────────────────────────────────────────────────────────────

def get_historia_clinica(conn, patient_id):
    """Recupera la historia clínica guardada como JSONB."""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            "SELECT historia_clinica, historia_clinica_fecha FROM patients WHERE id = %s",
            (patient_id,),
        )
        row = cur.fetchone()
        if row and row["historia_clinica"]:
            return row["historia_clinica"]
    return {}


def save_historia_clinica(conn, patient_id, hc_data):
    """Guarda la historia clínica en la columna JSONB del paciente."""
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE patients
               SET historia_clinica = %s, historia_clinica_fecha = NOW()
               WHERE id = %s""",
            (json.dumps(hc_data, ensure_ascii=False, default=str), patient_id),
        )
    conn.commit()
    return True


# ─── UI principal ────────────────────────────────────────────────────────────

def render_historia_clinica_tab(conn, patient_id, patient_data, user_data):
    """
    Renderiza el tab completo de Historia Clínica.
    Incluye formulario, guardado en DB y generación de PDF.

    Uso en app.py (dentro del bloque de tabs del expediente):
        with tab_hc:
            render_historia_clinica_tab(conn, patient_id, patient_data, user_data)
    """
    hc = get_historia_clinica(conn, patient_id) or {}
    p = patient_data or {}

    def g(d, key, default=""):
        v = d.get(key, default)
        return v if v is not None else default

    kp = f"hc_{patient_id}"  # key prefix único por paciente

    st.markdown("### 📋 Historia Clínica — Formato Renalmedic / KDIGO")

    # ── Datos generales (pre-cargados, solo lectura) ──────────────────────
    with st.expander("📌 Datos Generales (precargados del expediente)", expanded=False):
        nombre = p.get("nombre_completo") or (
            f"{p.get('apellido_paterno','')} {p.get('apellido_materno','')}, "
            f"{p.get('nombres','')}"
        ).strip()
        st.markdown(f"**Paciente:** {nombre} &nbsp;|&nbsp; "
                    f"**Exp.:** {p.get('expediente_num', p.get('id', '—'))} &nbsp;|&nbsp; "
                    f"**Ingreso:** {p.get('fecha_ingreso_unidad', '—')}")
        st.markdown(f"**Médico:** Dr. Josué Wigberto Tapia López &nbsp;|&nbsp; "
                    f"**Especialidad:** Nefrología &nbsp;|&nbsp; "
                    f"**Cédula:** 9940966 (UNAM)")

    # ── Diagnósticos ─────────────────────────────────────────────────────
    with st.expander("🔴 Diagnósticos", expanded=True):
        dx_primario = st.text_input(
            "Diagnóstico primario (CIE-10)",
            value=g(hc, "dx_primario", "N185 — Enfermedad Renal Crónica G5"),
            key=f"{kp}_dx_prim",
            placeholder="Ej: N185 Enfermedad renal crónica et.5",
        )
        dx_secundarios = st.text_area(
            "Diagnósticos secundarios (uno por línea)",
            value=g(hc, "dx_secundarios"),
            key=f"{kp}_dx_sec",
            height=80,
            placeholder="Diabetes Mellitus Tipo 2\nHipertensión Arterial Sistémica",
        )

        c1, c2, c3 = st.columns(3)
        cardiopatia = c1.checkbox("Cardiopatía isquémica", value=hc.get("cardiopatia", False),
                                   key=f"{kp}_cardio")
        dm = c2.checkbox("Diabetes mellitus", value=hc.get("dm", False),
                          key=f"{kp}_dm")
        hta = c3.checkbox("Hipertensión arterial", value=hc.get("hta", False),
                           key=f"{kp}_hta")

        c1, c2 = st.columns(2)
        fecha_dx_irc = c1.text_input("Fecha diagnóstico IRC (mes/año)",
                                      value=g(hc, "fecha_dx_irc"),
                                      key=f"{kp}_fecha_irc",
                                      placeholder="Ej: 01/2026")
        etiologia_irc = c2.text_input("Etiología de ERC",
                                       value=g(hc, "etiologia_irc"),
                                       key=f"{kp}_etiol",
                                       placeholder="Ej: Nefropatía diabética, no determinada")

    # ── Viral / Serologías ────────────────────────────────────────────────
    with st.expander("🧪 Serología Viral y Otros", expanded=False):
        c1, c2, c3 = st.columns(3)
        hepb_opts = ["Negativo", "Positivo", "No determinado"]
        hepb = c1.selectbox("Hepatitis B", hepb_opts,
                             index=hepb_opts.index(g(hc, "hep_b", "Negativo")),
                             key=f"{kp}_hepb")
        hepc = c2.selectbox("Hepatitis C", hepb_opts,
                             index=hepb_opts.index(g(hc, "hep_c", "Negativo")),
                             key=f"{kp}_hepc")
        hiv = c3.selectbox("VIH", hepb_opts,
                            index=hepb_opts.index(g(hc, "hiv", "Negativo")),
                            key=f"{kp}_hiv")

        c1, c2, c3 = st.columns(3)
        biopsia = c1.selectbox("Biopsia renal", ["No", "Sí"],
                                index=["No", "Sí"].index(g(hc, "biopsia", "No")),
                                key=f"{kp}_biopsia")
        biopsia_res = c2.text_input("Resultado biopsia", value=g(hc, "biopsia_res"),
                                     key=f"{kp}_biop_res") if biopsia == "Sí" else ""
        alergias_hc = c3.text_input("Alergias", value=g(hc, "alergias", "Negadas"),
                                     key=f"{kp}_alerg")

        c1, c2, c3 = st.columns(3)
        transf = c1.selectbox("Transfusiones", ["No", "Sí"],
                               index=["No", "Sí"].index(g(hc, "transfusiones", "No")),
                               key=f"{kp}_transf")
        transf_n = c2.text_input("¿Cuántas?", value=g(hc, "transf_num"),
                                  key=f"{kp}_transf_n") if transf == "Sí" else ""
        transf_fecha = c3.text_input("Última transfusión", value=g(hc, "transf_fecha"),
                                      key=f"{kp}_transf_f") if transf == "Sí" else ""

    # ── Antecedentes ─────────────────────────────────────────────────────
    with st.expander("📖 Antecedentes", expanded=True):
        st.markdown("**Heredofamiliares**")
        heredo = st.text_area(value=g(hc, "heredo"), label="", key=f"{kp}_heredo",
                               height=60,
                               placeholder="Ej: Tío materno con ERC en HD. Padre con DM.")

        st.markdown("**No Patológicos**")
        no_pat = st.text_area(value=g(hc, "no_patologicos"), label="", key=f"{kp}_nopat",
                               height=80,
                               placeholder="Vivienda, alimentación, agua, actividad física, inmunizaciones…")

        st.markdown("**Patológicos**")
        patologicos = st.text_area(value=g(hc, "patologicos"), label="", key=f"{kp}_pat",
                                    height=120,
                                    placeholder="- DM T2 (diagnóstico 2013)\n- HAS (2025)\n- ERC G5 (2026)\n- Qx: colecistectomía 2013")

        c1, c2, c3 = st.columns(3)
        tabaquismo = c1.selectbox("Tabaquismo", ["No", "Sí", "Ex"],
                                   index=["No", "Sí", "Ex"].index(g(hc, "tabaquismo", "No")),
                                   key=f"{kp}_tab")
        alcoholismo = c2.selectbox("Alcoholismo", ["No", "Sí", "Ex"],
                                    index=["No", "Sí", "Ex"].index(g(hc, "alcoholismo", "No")),
                                    key=f"{kp}_alco")
        toxicomania = c3.selectbox("Toxicomanía", ["No", "Sí"],
                                    index=["No", "Sí"].index(g(hc, "toxicomania", "No")),
                                    key=f"{kp}_toxico")

        c1, c2, c3, c4 = st.columns(4)
        hd_previa = c1.selectbox("HD previa", ["No", "Sí"],
                                  index=["No", "Sí"].index(g(hc, "hd_previa", "No")),
                                  key=f"{kp}_hdprev")
        hd_meses = c2.text_input("Meses en HD", value=g(hc, "hd_meses", "0"),
                                  key=f"{kp}_hdmes")
        dp_previa = c3.selectbox("DP previa", ["No", "Sí"],
                                  index=["No", "Sí"].index(g(hc, "dp_previa", "No")),
                                  key=f"{kp}_dpprev")
        dp_meses = c4.text_input("Meses en DP", value=g(hc, "dp_meses", "0"),
                                  key=f"{kp}_dpmes")

        # Ginecobstétricos (solo si sexo femenino o no definido)
        sexo_p = p.get("sexo", "")
        if sexo_p in ("Femenino", "") or not sexo_p:
            st.markdown("**Ginecobstétricos**")
            gineco = st.text_area(value=g(hc, "gineco"), label="", key=f"{kp}_gineco",
                                   height=60,
                                   placeholder="G_ P_ C_ A_ · Último PAP: …")

    # ── Información médica ────────────────────────────────────────────────
    with st.expander("🏥 Información Médica / Trasplante", expanded=False):
        c1, c2 = st.columns(2)
        protocolo_tx = c1.selectbox("Protocolo de trasplante",
                                     ["No iniciado", "En proceso", "Completado", "No candidato"],
                                     index=["No iniciado", "En proceso", "Completado",
                                            "No candidato"].index(
                                         g(hc, "protocolo_tx", "No iniciado")),
                                     key=f"{kp}_proto_tx")
        candidato_tx = c2.selectbox("Candidato a trasplante",
                                     ["No", "Sí — riñón", "Sí — páncreas-riñón", "En evaluación"],
                                     index=["No", "Sí — riñón", "Sí — páncreas-riñón",
                                            "En evaluación"].index(
                                         g(hc, "candidato_tx", "No")),
                                     key=f"{kp}_cand_tx")

    # ── Interrogatorio por aparatos y sistemas ────────────────────────────
    with st.expander("🩺 Interrogatorio por Aparatos y Sistemas", expanded=False):
        SISTEMAS = [
            ("neurologico",      "Neurológico"),
            ("cardiovascular",   "Cardiovascular"),
            ("respiratorio",     "Respiratorio"),
            ("gastrointestinal", "Gastrointestinal"),
            ("urinario",         "Urinario"),
            ("endocrino",        "Endocrino"),
            ("hematologico",     "Hematológico / Linfático"),
            ("musculoesqueletico","Musculoesquelético"),
            ("nervioso",         "Sistema Nervioso"),
            ("sentidos",         "Órganos de los Sentidos"),
        ]
        interrogatorio = {}
        for key_sis, label_sis in SISTEMAS:
            stored = g(hc.get("interrogatorio", {}), key_sis)
            interrogatorio[key_sis] = st.text_input(
                label_sis,
                value=stored,
                key=f"{kp}_sis_{key_sis}",
                placeholder="Negado / Sin alteraciones — o describa hallazgos",
            )

    # ── Padecimiento actual ───────────────────────────────────────────────
    with st.expander("📝 Padecimiento Actual", expanded=True):
        padecimiento_actual = st.text_area(
            "",
            value=g(hc, "padecimiento_actual"),
            key=f"{kp}_pact",
            height=120,
            placeholder="Descripción cronológica del motivo de consulta/ingreso…",
        )

    # ── Laboratorios (texto libre) ────────────────────────────────────────
    with st.expander("🧬 Laboratorios", expanded=False):
        labs_texto = st.text_area(
            "",
            value=g(hc, "labs_texto"),
            key=f"{kp}_labs_txt",
            height=100,
            placeholder="Ej: 17/04/2026; Hb 13.3, Cr 7.6, K 4.5, Ca 8.5, P 6.9…",
        )

    # ── Gabinete ──────────────────────────────────────────────────────────
    with st.expander("📡 Gabinete y Complementarios", expanded=False):
        gabinete = st.text_area(
            "",
            value=g(hc, "gabinete"),
            key=f"{kp}_gabinete",
            height=80,
            placeholder="USG renal, Rx tórax, ECG, ecocardiograma…",
        )

    # ── Signos Vitales y Exploración Física ──────────────────────────────
    with st.expander("❤️ Signos Vitales y Exploración Física", expanded=True):
        sv_fecha = st.date_input("Fecha y hora de toma",
                                  value=date.today(),
                                  format="DD/MM/YYYY",
                                  key=f"{kp}_sv_fecha")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        sv_ta_sist = c1.text_input("TA Sist.", value=g(hc, "sv_ta_sist"), key=f"{kp}_sist",
                                    placeholder="mmHg")
        sv_ta_diast = c2.text_input("TA Diast.", value=g(hc, "sv_ta_diast"), key=f"{kp}_diast",
                                     placeholder="mmHg")
        sv_fc = c3.text_input("FC", value=g(hc, "sv_fc"), key=f"{kp}_fc",
                               placeholder="lpm")
        sv_fr = c4.text_input("FR", value=g(hc, "sv_fr"), key=f"{kp}_fr",
                               placeholder="rpm")
        sv_temp = c5.text_input("Temp", value=g(hc, "sv_temp"), key=f"{kp}_temp",
                                  placeholder="°C")
        sv_spo2 = c6.text_input("SpO₂", value=g(hc, "sv_spo2"), key=f"{kp}_spo2",
                                  placeholder="%")

        c1, c2 = st.columns(2)
        sv_peso = c1.text_input("Peso (kg)", value=g(hc, "sv_peso"), key=f"{kp}_peso")
        sv_talla = c2.text_input("Talla (cm)", value=g(hc, "sv_talla"), key=f"{kp}_talla")

        exploracion_fisica = st.text_area(
            "Exploración física",
            value=g(hc, "exploracion_fisica"),
            key=f"{kp}_efisica",
            height=100,
            placeholder="Consciente, orientado/a. Cardiológico rítmico sin agregados. "
                        "Pulmonar sin estertores. Abdomen blando. EI sin edema. "
                        "Acceso vascular: …",
        )

    # ── Plan de tratamiento ───────────────────────────────────────────────
    with st.expander("💊 Plan de Tratamiento", expanded=True):
        plan_tx = st.text_area(
            "",
            value=g(hc, "plan_tx"),
            key=f"{kp}_plan",
            height=120,
            placeholder="- Hemodiálisis 3/semana\n- Telmisartán 40 mg c/12h\n- Eritropoyetina alfa 4000 UI c/semana\n…",
        )

    # ── Pronóstico ────────────────────────────────────────────────────────
    with st.expander("📊 Pronóstico", expanded=False):
        PRONOSTICOS = [
            "Malo para la función, reservado para la vida por patología de base",
            "Reservado para la función y para la vida",
            "Regular para la función, reservado para la vida",
            "Bueno para la función y para la vida condicionado a apego terapéutico",
            "Personalizado (escribir abajo)",
        ]
        prog_sel = st.selectbox("Pronóstico", PRONOSTICOS,
                                 index=PRONOSTICOS.index(g(hc, "pronostico_sel", PRONOSTICOS[0])),
                                 key=f"{kp}_prog_sel")
        pronostico_text = prog_sel
        if prog_sel == "Personalizado (escribir abajo)":
            pronostico_text = st.text_area("", value=g(hc, "pronostico_custom"),
                                            key=f"{kp}_prog_cust", height=60)

    # ── Acceso vascular ───────────────────────────────────────────────────
    with st.expander("🩸 Acceso Vascular", expanded=False):
        av_opts = [
            "Catéter temporal yugular derecho", "Catéter temporal yugular izquierdo",
            "Catéter tunelizado yugular derecho", "Catéter tunelizado yugular izquierdo",
            "Catéter tunelizado femoral", "FAV radiocefálica izquierda",
            "FAV radiocefálica derecha", "FAV braquiocefálica", "FAV braquiobasílica",
            "Injerto (PTFE)", "Otro",
        ]
        acceso_vascular = st.selectbox("Tipo de acceso vascular", av_opts,
                                        index=av_opts.index(g(hc, "acceso_vascular", av_opts[0])),
                                        key=f"{kp}_av")
        av_fecha = st.text_input("Fecha de colocación/maduración",
                                  value=g(hc, "av_fecha"), key=f"{kp}_av_fecha",
                                  placeholder="DD/MM/AAAA")
        av_notas = st.text_area("Notas del acceso vascular", value=g(hc, "av_notas"),
                                 key=f"{kp}_av_notas", height=60)

    # ── Botones de acción ─────────────────────────────────────────────────
    st.markdown("---")
    col_save, col_pdf = st.columns(2)

    hc_data = {
        "dx_primario": dx_primario, "dx_secundarios": dx_secundarios,
        "cardiopatia": cardiopatia, "dm": dm, "hta": hta,
        "fecha_dx_irc": fecha_dx_irc, "etiologia_irc": etiologia_irc,
        "hep_b": hepb, "hep_c": hepc, "hiv": hiv,
        "biopsia": biopsia, "biopsia_res": biopsia_res, "alergias": alergias_hc,
        "transfusiones": transf, "transf_num": transf_n, "transf_fecha": transf_fecha,
        "heredo": heredo, "no_patologicos": no_pat, "patologicos": patologicos,
        "tabaquismo": tabaquismo, "alcoholismo": alcoholismo, "toxicomania": toxicomania,
        "hd_previa": hd_previa, "hd_meses": hd_meses,
        "dp_previa": dp_previa, "dp_meses": dp_meses,
        "gineco": gineco if sexo_p in ("Femenino", "") or not sexo_p else "NA",
        "protocolo_tx": protocolo_tx, "candidato_tx": candidato_tx,
        "interrogatorio": interrogatorio,
        "padecimiento_actual": padecimiento_actual,
        "labs_texto": labs_texto, "gabinete": gabinete,
        "sv_fecha": str(sv_fecha), "sv_ta_sist": sv_ta_sist, "sv_ta_diast": sv_ta_diast,
        "sv_fc": sv_fc, "sv_fr": sv_fr, "sv_temp": sv_temp, "sv_spo2": sv_spo2,
        "sv_peso": sv_peso, "sv_talla": sv_talla,
        "exploracion_fisica": exploracion_fisica,
        "plan_tx": plan_tx,
        "pronostico_sel": prog_sel, "pronostico_custom": pronostico_text,
        "acceso_vascular": acceso_vascular, "av_fecha": av_fecha, "av_notas": av_notas,
        "fecha_elaboracion": str(date.today()),
    }

    with col_save:
        if st.button("💾 Guardar Historia Clínica", use_container_width=True,
                     key=f"{kp}_save"):
            save_historia_clinica(conn, patient_id, hc_data)
            st.success("✅ Historia clínica guardada correctamente.")

    with col_pdf:
        if st.button("🖨️ Generar PDF Historia Clínica", use_container_width=True,
                     type="primary", key=f"{kp}_pdf"):
            save_historia_clinica(conn, patient_id, hc_data)
            pdf_bytes = generate_pdf_historia(hc_data, patient_data, user_data)
            nombre_archivo = (
                f"HC_{p.get('apellido_paterno','')}{p.get('apellido_materno','')}"
                f"_{date.today().strftime('%Y%m%d')}.pdf"
            )
            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=nombre_archivo,
                mime="application/pdf",
                use_container_width=True,
            )


# ─── Generador PDF Historia Clínica ─────────────────────────────────────────

def generate_pdf_historia(hc, p, user):
    """
    Genera el PDF de Historia Clínica en formato Renalmedic.
    hc: dict con datos de la historia (de hc_data)
    p:  dict con datos del paciente
    user: dict con datos del médico (logo_b64, firma_b64, etc.)
    Retorna bytes del PDF.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    # ── Estilos ────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    AZUL = colors.HexColor("#1B4F72")
    GRIS_HD = colors.HexColor("#D5D8DC")
    GRIS_SECCION = colors.HexColor("#EBF5FB")

    s_normal = ParagraphStyle("normal", fontSize=8, leading=11,
                               fontName="Helvetica")
    s_bold = ParagraphStyle("bold", fontSize=8, leading=11,
                             fontName="Helvetica-Bold")
    s_section = ParagraphStyle("sec", fontSize=8.5, leading=12,
                                fontName="Helvetica-Bold", textColor=AZUL)
    s_header = ParagraphStyle("hdr", fontSize=11, leading=14,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_small = ParagraphStyle("sm", fontSize=7, leading=10,
                              fontName="Helvetica", textColor=colors.HexColor("#555555"))

    story = []

    # ── Header ────────────────────────────────────────────────────────
    logo_img = None
    logo_b64 = user.get("logo_b64") or user.get("logo")
    if logo_b64:
        try:
            logo_bytes = base64.b64decode(logo_b64)
            logo_img = RLImage(BytesIO(logo_bytes), width=3*cm, height=1.5*cm,
                               kind="proportional")
        except Exception:
            pass

    direccion = (
        "Av. México #719, Col. Los Paraísos, León, Gto. C.P. 37328\n"
        "Tel: 477 299-8217 | 477 694-5392\n"
        f"Cédula Especialidad: {user.get('cedula_especialidad','9940966')} "
        f"| {user.get('universidad_especialidad','UNAM')}"
    )
    header_data = [
        [logo_img or Paragraph("<b>RENALMEDIC</b>", s_header),
         Paragraph("<b>Historia Clínica</b>", s_header),
         Paragraph(direccion, s_small)],
    ]
    t_hdr = Table(header_data, colWidths=[4*cm, 9*cm, 6*cm])
    t_hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_hdr)
    story.append(Spacer(1, 0.3*cm))

    # ── Función helper: fila de sección ───────────────────────────────
    def seccion(titulo):
        t = Table([[Paragraph(titulo, s_section)]], colWidths=[19*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRIS_SECCION),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, AZUL),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.1*cm))

    def fila_dos(lbl1, val1, lbl2="", val2=""):
        row = [
            Paragraph(f"<b>{lbl1}</b> {val1}", s_normal),
            Paragraph(f"<b>{lbl2}</b> {val2}", s_normal),
        ]
        t = Table([row], colWidths=[9.5*cm, 9.5*cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(t)

    def fila_uno(lbl, val):
        story.append(Paragraph(f"<b>{lbl}</b> {val}", s_normal))
        story.append(Spacer(1, 0.1*cm))

    def bloque(lbl, val):
        story.append(Paragraph(f"<b>{lbl}</b>", s_bold))
        for linea in (val or "").split("\n"):
            story.append(Paragraph(f"- {linea.lstrip('- ')}" if linea.strip() else " ",
                                   s_normal))
        story.append(Spacer(1, 0.2*cm))

    # ── Datos generales ────────────────────────────────────────────────
    seccion("DATOS GENERALES")
    nombre = p.get("nombre_completo") or (
        f"{p.get('apellido_paterno','')} {p.get('apellido_materno','')}, "
        f"{p.get('nombres','')}").strip()
    exp_num = str(p.get("expediente_num", p.get("id", "—")))
    fila_dos("Nombre:", nombre, "Expediente:", exp_num)
    fila_dos("Fecha ingreso:", p.get("fecha_ingreso_unidad", "—"),
             "Nacimiento:", str(p.get("fecha_nacimiento", "—")))
    fila_dos("Edad:", p.get("edad_display", "—"),
             "Sexo:", p.get("sexo", "—"))
    fila_dos("Peso:", f"{hc.get('sv_peso','—')} kg",
             "Talla:", f"{hc.get('sv_talla','—')} cm")
    fila_dos("Médico:", "Dr. Josué Wigberto Tapia López — Nefrología",
             "Cédula:", "9940966 UNAM")
    story.append(Spacer(1, 0.3*cm))

    # ── Diagnósticos ───────────────────────────────────────────────────
    seccion("DIAGNÓSTICOS")
    fila_uno("Primario:", hc.get("dx_primario", ""))
    coms = []
    if hc.get("cardiopatia"): coms.append("Cardiopatía isquémica")
    if hc.get("dm"):          coms.append("Diabetes mellitus")
    if hc.get("hta"):         coms.append("Hipertensión arterial")
    if coms:
        fila_uno("Comorbilidades:", " | ".join(coms))
    bloque("Secundarios:", hc.get("dx_secundarios", ""))
    fila_dos("Fecha diagnóstico IRC:", hc.get("fecha_dx_irc", "—"),
             "Etiología ERC:", hc.get("etiologia_irc", "—"))
    story.append(Spacer(1, 0.2*cm))

    # ── Serología ──────────────────────────────────────────────────────
    seccion("SEROLOGÍA VIRAL / OTROS")
    fila_dos("Hepatitis B:", hc.get("hep_b", "Negativo"),
             "Hepatitis C:", hc.get("hep_c", "Negativo"))
    fila_dos("VIH:", hc.get("hiv", "Negativo"),
             "Biopsia renal:", hc.get("biopsia", "No"))
    fila_dos("Alergias:", hc.get("alergias", "Negadas"),
             "Transfusiones:", hc.get("transfusiones", "No"))
    story.append(Spacer(1, 0.2*cm))

    # ── Antecedentes ───────────────────────────────────────────────────
    seccion("ANTECEDENTES")
    bloque("Heredofamiliares:", hc.get("heredo", "Negados"))
    bloque("No patológicos:", hc.get("no_patologicos", ""))
    bloque("Patológicos:", hc.get("patologicos", ""))
    fila_dos("Tabaquismo:", hc.get("tabaquismo", "No"),
             "Alcoholismo:", hc.get("alcoholismo", "No"))
    fila_dos("Toxicomanía:", hc.get("toxicomania", "No"),
             "HD previa:", f"{hc.get('hd_previa','No')} — {hc.get('hd_meses','0')} meses")
    if hc.get("gineco") and hc.get("gineco") != "NA":
        fila_uno("Ginecobstétricos:", hc.get("gineco", ""))
    story.append(Spacer(1, 0.2*cm))

    # ── Interrogatorio ─────────────────────────────────────────────────
    seccion("INTERROGATORIO POR APARATOS Y SISTEMAS")
    inter = hc.get("interrogatorio", {})
    SISTEMAS_LABELS = {
        "neurologico": "Neurológico", "cardiovascular": "Cardiovascular",
        "respiratorio": "Respiratorio", "gastrointestinal": "Gastrointestinal",
        "urinario": "Urinario", "endocrino": "Endocrino",
        "hematologico": "Hematológico", "musculoesqueletico": "Musculoesquelético",
        "nervioso": "Sistema Nervioso", "sentidos": "Órganos de los Sentidos",
    }
    for key_s, lbl_s in SISTEMAS_LABELS.items():
        val_s = inter.get(key_s, "Sin alteraciones")
        fila_uno(f"{lbl_s}:", val_s or "Sin alteraciones referidas")
    story.append(Spacer(1, 0.2*cm))

    # ── Padecimiento actual ────────────────────────────────────────────
    seccion("PADECIMIENTO ACTUAL")
    story.append(Paragraph(hc.get("padecimiento_actual", ""), s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Laboratorios ───────────────────────────────────────────────────
    seccion("LABORATORIOS")
    story.append(Paragraph(hc.get("labs_texto", ""), s_normal))
    story.append(Spacer(1, 0.1*cm))
    seccion("GABINETE Y COMPLEMENTARIOS")
    story.append(Paragraph(hc.get("gabinete", "No se cuenta") or "No se cuenta", s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Signos vitales ─────────────────────────────────────────────────
    seccion("SIGNOS VITALES Y EXPLORACIÓN FÍSICA")
    sv_row = [
        f"Fecha: {hc.get('sv_fecha','—')}",
        f"TA: {hc.get('sv_ta_sist','—')}/{hc.get('sv_ta_diast','—')} mmHg",
        f"FC: {hc.get('sv_fc','—')} lpm",
        f"FR: {hc.get('sv_fr','—')} rpm",
        f"Temp: {hc.get('sv_temp','—')} °C",
        f"SpO₂: {hc.get('sv_spo2','—')}%",
    ]
    sv_data = [[Paragraph(x, s_normal) for x in sv_row]]
    t_sv = Table(sv_data, colWidths=[3.2*cm]*6)
    t_sv.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_HD),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_sv)
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(hc.get("exploracion_fisica", ""), s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Plan ───────────────────────────────────────────────────────────
    seccion("PLAN DE TRATAMIENTO")
    for linea in (hc.get("plan_tx", "") or "").split("\n"):
        story.append(Paragraph(f"- {linea.lstrip('- ')}" if linea.strip() else " ",
                               s_normal))
    story.append(Spacer(1, 0.2*cm))

    # ── Pronóstico ─────────────────────────────────────────────────────
    seccion("PRONÓSTICO")
    prog = hc.get("pronostico_custom") or hc.get("pronostico_sel", "")
    story.append(Paragraph(prog, s_normal))
    story.append(Spacer(1, 0.5*cm))

    # ── Firma ──────────────────────────────────────────────────────────
    firma_b64 = user.get("firma_b64")
    firma_img = None
    if firma_b64:
        try:
            fb = base64.b64decode(firma_b64)
            firma_img = RLImage(BytesIO(fb), width=3*cm, height=1.5*cm,
                                kind="proportional")
        except Exception:
            pass

    medico_nombre = user.get("nombre", "Dr. Josué Wigberto Tapia López")
    cedula_esp = user.get("cedula_especialidad", "9940966")
    cedula_gen = user.get("cedula_general", "6446765")

    firma_data = [
        [firma_img if firma_img else Paragraph("", s_normal),
         Paragraph(
             f"<b>MÉDICO:</b> {medico_nombre}<br/>"
             f"Esp.: Nefrología — Cédula: {cedula_esp}<br/>"
             f"Med. General — Cédula: {cedula_gen}<br/>"
             f"<font size='7'>Fecha: {date.today().strftime('%d/%m/%Y')}</font>",
             s_normal,
         )],
    ]
    t_firma = Table(firma_data, colWidths=[5*cm, 14*cm])
    t_firma.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
    ]))
    story.append(t_firma)

    # Footer
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"<font size='6' color='grey'>HemoHL7 / RenalPro v3.1.0 — "
        f"Generado {datetime.now().strftime('%d/%m/%Y %H:%M')} — RENALMEDIC LEON</font>",
        ParagraphStyle("footer", fontSize=6, alignment=TA_CENTER,
                        textColor=colors.HexColor("#888888")),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

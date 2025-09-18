# app.py — TRRC360 by Dr. Tapia (v1.19.6)
import streamlit as st
from math import log
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

VERSION = "v1.19.6"
st.set_page_config(page_title=f"TRRC360 by Dr. Tapia — {VERSION}", layout="wide")

# ================== DEPENDENCIAS OPCIONALES ==================
REPORTLAB_OK = True
REPORTLAB_ERR = ""
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except Exception as e:
    REPORTLAB_OK = False
    REPORTLAB_ERR = str(e)

# ================== LANDING (LOGO + NOMBRE + AVISO PRIVACIDAD) ==================
if not st.session_state.get("acepto_privacidad", False):
    centL, centC, centR = st.columns([1,2,1])
    with centC:
        try:
            st.image("logo.png", width=180)
        except Exception:
            st.write("")
        st.title("TRRC360 — Prescripción integral de TRRC/CRRT")
        st.caption("(Uso docente — no sustituye el juicio clínico)")
        st.markdown("""
**Aviso de privacidad y uso**  
TRRC360 es una herramienta **docente** diseñada para apoyar la prescripción y seguimiento de TRRC/CRRT.  
No sustituye el **juicio clínico**, protocolos ni guías institucionales.  
El uso y aplicación de los resultados es **responsabilidad de quien la utiliza**.
""")
        if st.button("Acepto y entrar", type="primary"):
            st.session_state["acepto_privacidad"] = True
            st.rerun()
    st.stop()

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

# ======== BIBLIOGRAFÍA DINÁMICA ========
Ref = Dict[str, str]
BIBLIO: List[Ref] = [
    {"id":"dose_core_2024","yr":"2024","title":"Continuous Renal Replacement Therapy","where":"StatPearls/NCBI","url":"https://www.ncbi.nlm.nih.gov/books/NBK556028/","tags":"dosis,crrt,revision","blurb":"Dosis entregada 20–25 mL/kg/h; sin beneficio consistente >25."},
    {"id":"rca_review_2023","yr":"2023","title":"Regional Citrate Anticoagulation in CRRT","where":"Review/PMC","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC10221969/","tags":"rca,anticoagulacion,crrt,revision","blurb":"RCA segura/efectiva; primera línea si no hay contraindicaciones."},
    {"id":"ff_practical_2025","yr":"2025","title":"RRT in ICU (practical)","where":"Ann Intensive Care","url":"https://annalsofintensivecare.springeropen.com/articles/10.1186/s13613-025-01517-0","tags":"ff,crrt,practica","blurb":"Objetivo práctico: FF <25%."},
    {"id":"extript_2019","yr":"2019","title":"EXTRIP workgroup recommendations","where":"Clin Toxicol","url":"https://www.extrip-workgroup.org/","tags":"intoxicacion,revision","blurb":"Tóxicos dializables y modalidades."},
    {"id":"neuro_2016","yr":"2016","title":"Guidelines for severe TBI","where":"Brain Trauma Foundation","url":"https://braintrauma.org/guidelines/guidelines-for-the-management-of-severe-tbi-4th-ed#/", "tags":"neuro,osmolaridad","blurb":"Evitar cambios rápidos de Na/osmolaridad."},
    {"id":"ajkd_core_2025","yr":"2025","title":"CKRT Core Curriculum","where":"AJKD","url":"https://www.ajkd.org/","tags":"crrt,revision,general","blurb":"Cuándo y cómo prescribir CKRT."},
]
def filtrar_refs_por_contexto(escenarios_sel: List[str], anticoag_tipo: str) -> List[Ref]:
    e = " ".join([s.lower() for s in escenarios_sel])
    tags_req = {"crrt","revision","dosis","ff"}
    if any(x in e for x in ["sepsis","choque"]): tags_req.update({"sepsis"})
    if any(x in e for x in ["intoxicación","sobredosis"]): tags_req.update({"intoxicacion"})
    if any(x in e for x in ["neurocrítico","tce"]): tags_req.update({"neuro","osmolaridad"})
    if any(x in e for x in ["hiperamonemia","amonio"]): tags_req.update({"amonio","revision"})
    out = []; seen=set()
    for r in BIBLIO:
        rtags = set(r.get("tags","").split(","))
        if r["id"] not in seen and (rtags & tags_req):
            out.append(r); seen.add(r["id"])
    return out[:12]

# ================== LÓGICA CLÍNICA ==================
def prioridad_modalidad(m):
    return {"CVVHDF":3, "CVVHD":2, "CVVHF":1}.get(m.split()[0],0)

def prioridad_filtro(f):
    if "adsorción" in f.lower() or "HCO" in f: return 99
    if "2.1" in f: return 3
    if "1.5" in f or "1.3" in f: return 2
    return 1

def sugerir_por_escenario(esc):
    if esc == "Sepsis / choque séptico":
        return ("CVVHDF", "Oxiris (AN69-ST; adsorción alta)", "Mixto conv/dif; FF≤25%. Adsorción opcional; beneficio duro incierto.")
    if esc == "Neurocrítico / TCE":
        return ("CVVHDF", "M100 (~1.0 m²)", "Evitar oscilaciones osmóticas; corrección Na guiada.")
    if esc == "Sobrecarga hídrica aislada":
        return ("CVVHF", "M200 (~2.0 m²)", "Convectivo favorece UF; vigilar FF y tolerancia hemodinámica.")
    if esc == "Intoxicación / sobredosis":
        return ("CVVHD", "M200 (~2.0 m²)", "Difusión alta; considerar IHD si hemodinámicamente posible (EXTRIP).")
    if esc == "Hiponatremia severa":
        return ("CVVHDF", "M100 (~1.0 m²)", "Dializado Na bajo; no exceder 8–10 mEq/L/24h (≤8 si alto riesgo ODS).")
    if esc == "Hipernatremia":
        return ("CVVHDF", "M100–M150", "Dializado Na alto; ≈0.5 mEq/L/h (8–10 mEq/L/día) de corrección.")
    if esc == "Hiperamonemia":
        return ("CVVHD", "M150 (~1.5 m²)", "Difusión continua; prioriza dosis/flujo; buffer adecuado.")
    if esc == "Rabdomiólisis":
        return ("CVVHDF", "HCO 1100 (alta cut-off)", "Mioglobina; considerar HCO con vigilancia de albúmina.")
    if esc == "Choque cardiogénico":
        return ("CVVHDF", "M150 (~1.5 m²)", "Evitar cambios bruscos; UF conservadora; vigilar FF.")
    if esc == "Post infarto":
        return ("CVVHD", "M100–M150", "Difusivo; control fino de electrolitos; UF cauta.")
    if esc == "Síndrome de liberación de citocinas":
        return ("CVVHDF", "Alta adsorción/HCO", "Adsorción de mediadores (beneficio duro incierto); usar en protocolos.")
    return ("CVVHDF","M150 (~1.5 m²)","Configuración estándar")

def combinar_recomendaciones(escenarios_sel: List[str]):
    mods, filts, coments = [], [], []
    for e in escenarios_sel:
        m, f, c = sugerir_por_escenario(e)
        mods.append(m); filts.append(f); coments.append(c)
    mod_final = sorted(mods, key=lambda x: prioridad_modalidad(x), reverse=True)[0] if mods else "CVVHDF"
    filtro_final = sorted(filts, key=lambda x: prioridad_filtro(x), reverse=True)[0] if filts else "M150 (~1.5 m²)"
    return mod_final, filtro_final, " | ".join(coments)

def flows_and_ff(qb, hto, dosis_mlkg, peso, uf, modalidad):
    qp = qb * (1 - hto); qp_h = qp * 60; qe = dosis_mlkg * peso
    frac_conv = 0.0 if "CVVHD" in modalidad else (1.0 if "CVVHF" in modalidad else 0.6)
    qr_total = 0 if frac_conv == 0 else max(min(qp_h * 0.25, max(qe - uf, 0)), 0) * frac_conv
    qr_pre = round(qr_total * 0.7); qr_post = round(qr_total * 0.3); qd = max(qe - (qr_pre + qr_post + uf), 0)
    denom = max(qp_h + qr_pre, 1e-9); ff = (qr_post + uf) / denom
    return qp, qp_h, qe, qr_pre, qr_post, qd, ff

def flows_current_context():
    s = st.session_state
    peso = float(s.get("sb_peso", 70.0)); hto=float(s.get("sb_hto",0.30)); qb=int(s.get("sb_qb",200))
    uf=int(s.get("sb_uf",100)); dosis_mlkg=int(s.get("sb_dosis",30))
    mod_final, _, _ = combinar_recomendaciones(s.get("sb_escenarios",["Sepsis / choque séptico"]))
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_txt = f"{ff:.2%}" if ff is not None else "—"
    return qb, hto, qp, qp_h, qe, qr_pre, qr_post, qd, uf, ff_txt

# ================== HEADER ==================
col_logo, col_title = st.columns([1,6])
with col_logo:
    try:
        st.image("logo.png", width=90)
    except Exception:
        pass
with col_title:
    st.title(f"TRRC360 by Dr. Tapia — {VERSION}")
    st.caption("Uso docente — no sustituye el juicio clínico")

# ================== SIDEBAR ==================
with st.sidebar:
    st.subheader("Modo")
    doc_mode = st.checkbox("Modo docente extendido (UI y PDF)", value=st.session_state.get("doc_mode", False), key="doc_mode")
    st.session_state["pdf_extendido"] = bool(doc_mode)
    st.session_state["mostrar_fund_extendido"] = bool(doc_mode)

    st.header("Parámetros básicos")
    peso = st.number_input("Peso (kg)", 10.0, 300.0, 70.0, 0.5, key="sb_peso")
    hto  = st.number_input("Hematocrito (fracción)", 0.10, 0.60, 0.30, 0.01, format="%.2f", key="sb_hto")
    qb   = st.number_input("Qb (mL/min)", 80, 300, 200, 10, key="sb_qb")
    uf   = st.number_input("UF (mL/h)", 0, 2000, 100, 10, key="sb_uf")
    dosis_mlkg = st.slider("Dosis objetivo (mL/kg/h)", 10, 45, 30, key="sb_dosis")

    st.markdown("---")
    st.subheader("Estado(s) clínico(s)")
    escenarios_catalogo = [
        "Sepsis / choque séptico","Choque cardiogénico","Post infarto","Neurocrítico / TCE",
        "Sobrecarga hídrica aislada","Intoxicación / sobredosis","Hiponatremia severa","Hipernatremia",
        "Hiperamonemia","Rabdomiólisis","Síndrome de liberación de citocinas"
    ]
    escenarios = st.multiselect("Selecciona hasta 3", escenarios_catalogo, max_selections=3,
                                default=["Sepsis / choque séptico"], key="sb_escenarios")

# ================== TABS ==================
tab_main, tab_ktv, tab_balance, tab_anticoag, tab_trends, tab_fund, tab_rx, tab_refs = st.tabs([
    "Prescripción","Dosis (Kt/V)","Balance","Anticoagulación","Tendencias","Fundamento","Resumen / PDF","Referencias",
])

# ---------- Prescripción ----------
with tab_main:
    st.subheader("Recomendación combinada")
    pam = st.number_input("PAM (mmHg)", 30.0, 130.0, 65.0, 1.0, key="pam")
    vasopresor_alto = st.selectbox("Vasopresor en dosis altas", ["No","Sí"], 0, key="vaso_alto_sel") == "Sí"
    lactato_desc = st.selectbox("Lactato en descenso", ["No","Sí"], 0, key="lactato_desc_sel") == "Sí"

    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final)

    c1,c2,c3 = st.columns(3)
    c1.metric("Modalidad", mod_final)
    c2.metric("Filtro sugerido", filtro_final)
    c3.metric("FF (estimada)", f"{ff:.2%}" if ff is not None else "—")

    st.markdown("### Flujos sugeridos (base)")
    ca, cb, cc, cd = st.columns(4)
    ca.metric("Qb (mL/min)", qb); cb.metric("Qp (mL/min)", int(qp))
    cc.metric("Qe (mL/h)", int(qe)); cd.metric("UF (mL/h)", uf)
    ce, cf, cg = st.columns(3)
    ce.metric("Qr pre (mL/h)", qr_pre); cf.metric("Qr post (mL/h)", qr_post); cg.metric("Qd (mL/h)", int(qd))

    ff_pct = ff*100 if ff is not None else 0.0
    if ff_pct <= 25:
        st.success(f"FF ≈ {ff_pct:.1f}% — objetivo razonable (≤25%).")
    elif ff_pct <= 30:
        st.warning(f"FF ≈ {ff_pct:.1f}% — advertencia (0.25–0.30). Considera ↑ predilución / ↓ Qr_post / ↓ UF / ↑ Qb.")
    else:
        st.error(f"FF ≈ {ff_pct:.1f}% — alto riesgo de hemoconcentración; ajustar parámetros.")

    st.info(comentarios or "—")
    st.caption("Dosis objetivo 20–25 mL/kg/h como entregada; mantener FF <25% para proteger el filtro (ver Referencias).")

# ---------- Dosis / KtV ----------
with tab_ktv:
    st.subheader("Dosis por objetivos (Kt/V urea)")
    V = st.number_input("Volumen de distribución V (L) ≈ 0.6×peso", value=round(0.6*peso,1), step=0.1)
    C0 = st.number_input("Urea inicial C0 (mg/dL)", value=150.0, step=1.0)
    Ct = st.number_input("Urea objetivo Ct (mg/dL)", value=100.0, step=1.0)
    horas = st.number_input("Tiempo de tratamiento (h)", value=24, step=1)
    E = st.number_input("Eficiencia del sistema (0.8–1.0)", value=0.9, step=0.05, min_value=0.5, max_value=1.0)
    ktv_req = log(C0/Ct) if (C0>0 and Ct>0 and C0>Ct) else None
    st.metric("Kt/V requerido", f"{ktv_req:.2f}" if ktv_req else "—")
    K_Lh = ((ktv_req*V)/horas)/E if ktv_req else None
    dosis_calc = (K_Lh*1000)/peso if K_Lh else None
    colx, coly = st.columns(2)
    colx.metric("K requerido (L/h)", f"{K_Lh:.2f}" if K_Lh else "—")
    coly.metric("Dosis estimada (mL/kg/h)", f"{dosis_calc:.1f}" if dosis_calc else "—")

# ---------- Balance ----------
with tab_balance:
    st.subheader("Balance dinámico y metas de UF")
    peso_seco = st.number_input("Peso seco objetivo (kg)", value=max(0.0, peso-5), step=0.5)
    fo_actual = (peso - peso_seco)/peso_seco if peso_seco>0 else 0.0
    fo_obj = st.number_input("FO% objetivo (p. ej. 5%)", value=0.05, step=0.01)
    horas_trrc = st.number_input("Horas de TRRC planificadas (h)", value=24, step=1)
    ingresos = st.number_input("Ingresos previstos (mL)", value=0, step=50)
    uresis_res = st.number_input("Uresis residual 24 h (mL)", value=0, step=50)
    uf_obj = ((peso - (1+fo_obj)*peso_seco) * 1000) if (peso_seco>0) else None
    uf_mant = (ingresos - uresis_res)
    uf_total = (uf_obj if uf_obj is not None else 0) + uf_mant
    uf_h = uf_total/horas_trrc if horas_trrc>0 else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("FO% actual", f"{fo_actual:.1%}")
    c2.metric("UF objetivo (mL)", f"{int(uf_obj) if uf_obj is not None else 0}")
    c3.metric("UF total (mL)", f"{int(uf_total)}")
    c4.metric("UF/h sugerida", f"{int(uf_h)}")
    st.warning("⚠️ UF/h > 2 mL/kg/h") if (uf_h/peso) > 0.002 else st.success("OK")

# ---------- Anticoagulación ----------
with tab_anticoag:
    st.subheader("Anticoagulación (docente)")
    colA, colB, colC, colD = st.columns(4)
    plaquetas = colA.number_input("Plaquetas (mil/µL)", 0, 1000, 200, 5)
    fib = colB.number_input("Fibrinógeno (mg/dL)", 0, 1000, 300, 10)
    sangrado = colC.selectbox("Sangrado activo", ["No","Sí"]) == "Sí"
    neuro = colD.selectbox("Post-op neuro / riesgo alto", ["No","Sí"]) == "Sí"
    inr = colA.number_input("INR", 0.8, 5.0, 1.1, 0.1, key="inr_ext")
    aptt = colB.number_input("aPTT (s)", 20.0, 120.0, 35.0, 1.0, key="aptt_ext")
    hbpm_12h = colC.selectbox("HBPM en últimas 12 h", ["No","Sí"], index=0) == "Sí"
    hit_previa = colD.selectbox("Antecedente de HIT", ["No","Sí"], index=0) == "Sí"

    usar_rca = (plaquetas<50) or (fib<150) or sangrado or neuro or (inr>=1.5) or (aptt>=45) or hbpm_12h or hit_previa
    ac = "RCA (citrato)" if usar_rca else "Heparina no fraccionada (HNF)"
    st.success(f"Anticoagulación sugerida: **{ac}**")

    if ac == "Heparina no fraccionada (HNF)":
        if hbpm_12h: st.warning("HBPM reciente: valora diferir HNF o iniciar con dosis reducida y vigilancia de aPTT.")
        iu_h = peso * 5  # base docente
        st.info(f"Dosis inicial HNF sugerida: **{iu_h:.0f} UI/h** (ajustar a aPTT objetivo).")
        st.session_state["anticoagulacion_tipo"] = "HNF"
        st.session_state["hnf_ui_h"] = float(iu_h)
    else:
        st.markdown("### RCA – citrato/calcio (docente)")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            citrato_mmol_por_ml = st.number_input("Concentración citrato (mmol/mL)", 0.05, 0.25, 0.136, 0.001, format="%.3f")
            objetivo_mmol_L_sangre = st.number_input("Objetivo citrato (mmol/L sangre)", 2.0, 5.0, 3.0, 0.1)
        with rc2:
            post_filter_ica_obj = st.slider("iCa post-filtro (mmol/L)", 0.20, 0.50, 0.35, 0.01)
            system_ica_obj = st.slider("iCa sistémico (mmol/L)", 0.90, 1.30, 1.10, 0.01)
        with rc3:
            calcio_mmol_por_ml = st.number_input("Concentración calcio (mmol/mL)", 0.05, 1.00, 0.50, 0.01)

        citrato_ml_h = (qb * 60.0 * objetivo_mmol_L_sangre / 1000.0) / max(citrato_mmol_por_ml, 1e-6)
        citrato_mmol_h = qb * 60.0 * (objetivo_mmol_L_sangre / 1000.0)
        calcio_mmol_h_ini = 0.7 * citrato_mmol_h
        calcio_ml_h_ini = calcio_mmol_h_ini / max(calcio_mmol_por_ml, 1e-6)

        rca1, rca2, rca3 = st.columns(3)
        rca1.metric("Citrato (mL/h)", f"{citrato_ml_h:.0f}")
        rca2.metric("Calcio (mL/h)", f"{calcio_ml_h_ini:.0f}")
        rca3.metric("Citrato (mmol/h)", f"{citrato_mmol_h:.1f}")

        st.session_state["anticoagulacion_tipo"] = "RCA"
        st.session_state["rca_citrato_ml_h"] = float(citrato_ml_h)
        st.session_state["rca_calcio_ml_h"] = float(calcio_ml_h_ini)
        st.session_state["rca_targets"] = {"iCa_post": float(post_filter_ica_obj), "iCa_sist": float(system_ica_obj)}

# ---------- Tendencias (panel de barras + gráficas) ----------
with tab_trends:
    st.subheader("Panel rápido de tendencias (T1–T3)")

    import pandas as pd

    # Definimos analitos y rangos para normalizar (solo para barras estilo/validaciones)
    ANALITOS = [
        ("Na (mEq/L)", "na", 100.0, 200.0, 0.5, (140.0, 137.0, 135.0)),
        ("K (mEq/L)", "k", 1.0, 10.0, 0.1, (4.0, 4.8, 6.2)),
        ("Cl (mEq/L)", "cl", 70.0, 140.0, 0.5, (105.0, 110.0, 100.0)),
        ("Ca (mg/dL)", "ca", 5.0, 15.0, 0.1, (8.5, 8.2, 7.9)),
        ("P (mg/dL)", "p", 0.5, 15.0, 0.1, (5.0, 6.0, 7.0)),
        ("Mg (mg/dL)", "mg", 0.5, 5.0, 0.1, (2.0, 2.5, 3.0)),
        ("pH", "ph", 6.80, 7.80, 0.01, (7.35, 7.20, 7.15)),
        ("HCO₃⁻ (mEq/L)", "hco3", 5.0, 45.0, 0.5, (20.0, 18.0, 15.0)),
        ("CO₂ (mmHg)", "co2", 20.0, 80.0, 0.5, (40.0, 38.0, 45.0)),
        ("Lactato (mmol/L)", "lact", 0.0, 20.0, 0.1, (1.2, 2.6, 3.1)),
        ("Amonio (µmol/L)", "nh4", 0.0, 1000.0, 0.5, (60.0, 120.0, 180.0)),
        ("Urea (mg/dL)", "ure", 0.0, 500.0, 0.5, (130.0, 160.0, 210.0)),
        ("Creatinina (mg/dL)", "crn", 0.0, 20.0, 0.1, (3.2, 4.0, 4.5)),
    ]

    # Captura de T1-T2-T3 en una matriz estilo quick-grid
    cols = st.columns(len(ANALITOS))
    valores = {}
    for (label, key, vmin, vmax, step, defaults), col in zip(ANALITOS, cols):
        with col:
            st.markdown(f"**{label}**")
            t1 = st.number_input("T1", key=f"{key}_t1", value=float(defaults[0]), min_value=float(vmin), max_value=float(vmax), step=float(step))
            t2 = st.number_input("T2", key=f"{key}_t2", value=float(defaults[1]), min_value=float(vmin), max_value=float(vmax), step=float(step))
            t3 = st.number_input("T3", key=f"{key}_t3", value=float(defaults[2]), min_value=float(vmin), max_value=float(vmax), step=float(step))
            valores[key] = (t1, t2, t3)

    # Tabla estilo "barras en celda" (Styler.bar)
    df = pd.DataFrame({ k: list(v) for k,v in valores.items() }, index=["T1","T2","T3"])
    st.caption("Vista compacta (barras en celda):")
    st.dataframe(df.style.bar(subset=df.columns, align="left"))

    st.markdown("---")
    st.subheader("Gráficas por analito (barras)")
    # Render por filas de 3 columnas
    def chart_df(series):
        return pd.DataFrame({"valor": list(series)}, index=["T1","T2","T3"])
    rows = (len(ANALITOS)+2)//3
    idx = 0
    for _ in range(rows):
        cA, cB, cC = st.columns(3)
        for c in (cA, cB, cC):
            if idx >= len(ANALITOS): break
            label, key, *_ = ANALITOS[idx]
            with c:
                st.markdown(f"**{label}**")
                st.bar_chart(chart_df(valores[key]), height=160)
            idx += 1

# ---------- Fundamento ----------
with tab_fund:
    st.subheader("Fundamento y Cálculos")
    mostrar_ext = bool(st.session_state.get("mostrar_fund_extendido", False))
    st.caption("La vista extendida se controla desde el switch global en la barra lateral.")
    st.info("Vista extendida ACTIVADA.") if mostrar_ext else st.caption("Vista extendida desactivada.")
    # LaTeX de fórmulas base
    st.latex(r"Q_p = Q_b 	imes (1 - Hto)")
    st.latex(r"Q_{p,h} = Q_p 	imes 60")
    st.latex(r"Q_e = 	ext{dosis (mL/kg/h)} 	imes 	ext{peso (kg)}")
    st.latex(r"	ext{Límite convectivo} \le 0.25 	imes Q_{p,h}")
    st.latex(r"Q_d = \max\left(Q_e - (Q_{r,pre} + Q_{r,post} + UF),\ 0
ight)")
    st.latex(r"FF = \dfrac{Q_{r,post} + UF}{Q_{p,h} + Q_{r,pre}} \quad (<25\%)")

    qb_v, hto_v, qp_v, qp_h_v, qe_v, qr_pre_v, qr_post_v, qd_v, uf_v, ff_txt_v = flows_current_context()
    c1,c2,c3 = st.columns(3)
    with c1:
        st.write(f"**Qb** = {int(qb_v)}"); st.write(f"**Hto** = {hto_v:.2f}"); st.write(f"**Qp** = {int(qp_v)}")
    with c2:
        st.write(f"**Qp·h** = {int(qp_h_v)}"); st.write(f"**Qe** = {int(qe_v)}"); st.write(f"**UF** = {int(uf_v)}")
    with c3:
        st.write(f"**Qr_pre** = {int(qr_pre_v)}"); st.write(f"**Qr_post** = {int(qr_post_v)}"); st.write(f"**Qd** = {int(qd_v)}"); st.write(f"**FF** ≈ {ff_txt_v}")

    if mostrar_ext:
        st.markdown("""
**Puntos docentes clave**  
1) CVVHDF para perfiles mixtos (sepsis/choque) equilibra convección/difusión.  
2) Límite convectivo ≤25% de Qp·h protege el filtro (FF <25%).  
3) Predilución/postdilución 70/30 balancea protección de membrana y depuración.  
4) Ajustes por laboratorio: K≥6 → Qd alto 2–3 L/h con K 0–2; pH<7.20 → bicarbonato y Qd/Qe alto; Na hipo/hiper con límites de corrección.  
5) Anticoagulación: RCA preferente si sangrado/coagulopatía/HIT/HBPM reciente.
        """)

# ---------- Resumen / PDF ----------
def export_pdf(filename: Optional[str] = None):
    if not REPORTLAB_OK:
        raise RuntimeError("reportlab no disponible. Instala con: pip install reportlab")
    s = st.session_state
    peso = float(s.get("sb_peso", 70.0)); hto=float(s.get("sb_hto",0.30))
    qb=int(s.get("sb_qb",200)); uf=int(s.get("sb_uf",100)); dosis_mlkg=int(s.get("sb_dosis",30))
    escenarios = s.get("sb_escenarios", ["Sepsis / choque séptico"])
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")
    ff_txt = f"{ff:.2%}" if ff is not None else "—"
    # Identificación
    unidad=s.get("rx_unidad",""); nombre_paciente=s.get("rx_nombre_paciente","")
    fecha_nac=s.get("rx_fecha_nac",""); edad=s.get("rx_edad",""); sexo=s.get("rx_sexo","")
    expediente=s.get("rx_expediente",""); nombre_medico=s.get("rx_nombre_medico",""); sello=s.get("rx_sello","")

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_name = "".join(ch for ch in (nombre_paciente or "").replace(" ", "") if ch.isalnum())
    base = f"TRRC360_{safe_name}_" if safe_name else "TRRC360_"
    filename = filename or f"{base}{ts}.pdf"

    c = canvas.Canvas(filename, pagesize=letter)
    w, h = letter; margin = 50; y = h - margin

    # Título + fecha (sin logo)
    c.setFont("Helvetica-Bold", 14); c.drawString(margin, y, "Prescripción Terapia de Reemplazo Renal Continua (TRRC)")
    c.setFont("Helvetica", 10); c.drawRightString(w - margin, y, datetime.now().strftime("%d/%m/%Y %H:%M")); y -= 28

    if unidad:
        c.setFont("Helvetica", 12); c.drawString(margin, y, f"Unidad hospitalaria: {unidad}"); y -= 20

    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Ficha de identificación"); y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(margin,     y, f"Nombre: {nombre_paciente}")
    c.drawString(margin+280, y, f"Fecha Nac: {fecha_nac}"); y -= 16
    c.drawString(margin,     y, f"Edad: {edad}")
    c.drawString(margin+140, y, f"Sexo: {sexo}")
    c.drawString(margin+240, y, f"Expediente: {expediente}"); y -= 22
    c.drawString(margin, y, "—"*95); y -= 16

    c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Diagnóstico / escenarios"); y -= 16
    c.setFont("Helvetica", 11); esc_text = ", ".join(escenarios) if escenarios else "—"
    y = _draw_wrapped_text(c, f"Escenarios: {esc_text}", margin, y, w-2*margin)

    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Modalidad: {mod_final or '—'}"); y -= 14
    c.drawString(margin, y, f"Filtro sugerido: {filtro_final or '—'}"); y -= 14
    c.drawString(margin, y, f"FF (estimada): {ff_txt} (objetivo <25%)"); y -= 18

    c.setFont("Helvetica-Bold", 11); c.drawString(margin, y, "Flujos y soluciones"); y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(margin,     y, f"Qb (mL/min): {_s_int(qb)}")
    c.drawString(margin+180, y, f"Qp (mL/min): {_s_int(qp)}")
    c.drawString(margin+360, y, f"Qe (mL/h): {_s_int(qe)}"); y -= 16
    c.drawString(margin,     y, f"Qr pre (mL/h): {_s_int(qr_pre)}")
    c.drawString(margin+180, y, f"Qr post (mL/h): {_s_int(qr_post)}")
    c.drawString(margin+360, y, f"Qd (mL/h): {_s_int(qd)}    UF (mL/h): {_s_int(uf)}"); y -= 22

    c.setFont("Helvetica-Bold", 11); c.drawString(margin, y, "Comentarios / recomendaciones"); y -= 16
    c.setFont("Helvetica", 11); comentarios_txt = st.session_state.get("rx_comentarios","") or "—"
    y = _draw_wrapped_text(c, comentarios_txt, margin, y, w-2*margin)

    y -= 30; c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Médico tratante:"); y -= 18
    c.setFont("Helvetica", 11); c.drawString(margin, y, nombre_medico or ""); y -= 16
    if sello:
        y = _draw_wrapped_text(c, f"Sello / Notas: {sello}", margin, y, w-2*margin)

    # Fundamento breve/extendido (según modo)
    c.showPage(); y = h - 50
    c.setFont("Helvetica-Bold", 13); c.drawString(50, y, "Fundamento y Cálculos"); y -= 22
    c.setFont("Helvetica", 11)
    qb_v, hto_v, qp_v, qp_h_v, qe_v, qr_pre_v, qr_post_v, qd_v, uf_v, ff_txt_v = flows_current_context()
    bloques = [
        "• Dosis objetivo: Qe = dosis (mL/kg/h) × peso (kg).",
        "• Qp = Qb × (1 − Hto). Qp·h = Qp × 60.",
        "• Límite convectivo: ≤25% de Qp·h; FF <25% recomendado.",
        "• CVVHD=0, CVVHF=1, CVVHDF≈0.6 de fracción convectiva.",
        f"• Contexto: Qb={_s_int(qb_v)}, Hto={hto_v:.2f}, Qp={_s_int(qp_v)}, Qp·h={_s_int(qp_h_v)}, Qe={_s_int(qe_v)}, Qr_pre={_s_int(qr_pre_v)}, Qr_post={_s_int(qr_post_v)}, Qd={_s_int(qd_v)}, UF={_s_int(uf_v)}, FF≈{ff_txt_v}.",
    ]
    for linea in bloques:
        y = _draw_wrapped_text(c, linea, 50, y, w-100)
        if y < 80:
            c.showPage(); y = h - 50; c.setFont("Helvetica", 11)

    # Referencias dinámicas
    refs_pdf = filtrar_refs_por_contexto(escenarios, st.session_state.get("anticoagulacion_tipo","—"))
    if refs_pdf:
        c.showPage(); y = h - 50; c.setFont("Helvetica-Bold", 13); c.drawString(50, y, "Referencias"); y -= 24
        c.setFont("Helvetica", 10)
        for i, r in enumerate(refs_pdf, 1):
            y = _draw_wrapped_text(c, f"[{i}] {r['title']} — {r['where']} ({r['yr']})", 50, y, w-100, font_size=10, leading=12)
            if r.get("url"):
                y = _draw_wrapped_text(c, f"URL: {r['url']}", 60, y, w-110, font_size=9, leading=11)
            y -= 4
            if y < 80:
                c.showPage(); y = h - 50; c.setFont("Helvetica", 10)

    c.showPage(); c.save()
    return filename

with tab_rx:
    st.subheader("Resumen de prescripción")
    st.text_input("Unidad hospitalaria", key="rx_unidad", value=st.session_state.get("rx_unidad",""))
    r1c1,r1c2,r1c3 = st.columns([2,1,1])
    r1c1.text_input("Nombre del paciente", key="rx_nombre_paciente", value=st.session_state.get("rx_nombre_paciente",""))
    r1c2.text_input("Fecha de nacimiento", key="rx_fecha_nac", value=st.session_state.get("rx_fecha_nac",""))
    r1c3.text_input("Edad", key="rx_edad", value=st.session_state.get("rx_edad",""))
    r2c1,r2c2 = st.columns([1,2])
    r2c1.selectbox("Sexo", ["","F","M"], index=0 if st.session_state.get("rx_sexo","") not in ["","F","M"] else ["","F","M"].index(st.session_state.get("rx_sexo","")), key="rx_sexo")
    r2c2.text_input("Expediente", key="rx_expediente", value=st.session_state.get("rx_expediente",""))
    st.text_input("Nombre del médico", key="rx_nombre_medico", value=st.session_state.get("rx_nombre_medico",""))
    st.text_input("Sello / Notas (opcional)", key="rx_sello", value=st.session_state.get("rx_sello",""))

    mod_final, filtro_final, comentarios = combinar_recomendaciones(st.session_state.get("sb_escenarios",[]))
    qb_v, hto_v, qp_v, qp_h_v, qe_v, qr_pre_v, qr_post_v, qd_v, uf_v, ff_txt_v = flows_current_context()
    st.write(f"**Escenarios:** {', '.join(st.session_state.get('sb_escenarios', [])) or '—'}")
    st.write(f"**Modalidad:** {mod_final or '—'}  |  **Filtro sugerido:** {filtro_final or '—'}  |  **FF (estimada):** {ff_txt_v} (objetivo <25%)")
    st.markdown("### Flujos sugeridos")
    ca, cb, cc, cd = st.columns(4)
    ca.metric("Qb (mL/min)", int(st.session_state.get("sb_qb",200)))
    cb.metric("Qp (mL/min)", int(qp_v))
    cc.metric("Qe (mL/h)", int(qe_v))
    cd.metric("UF (mL/h)", int(st.session_state.get("sb_uf",100)))
    ce, cf, cg = st.columns(3)
    ce.metric("Qr pre (mL/h)", int(qr_pre_v)); cf.metric("Qr post (mL/h)", int(qr_post_v)); cg.metric("Qd (mL/h)", int(qd_v))
    st.info(comentarios or "—")
    st.text_area("Comentarios para el PDF", key="rx_comentarios", value=st.session_state.get("rx_comentarios",""), height=120)

    st.markdown("### Exportación")
    if not REPORTLAB_OK:
        st.warning("Exportar a PDF requiere reportlab. Instala con: pip install reportlab")
    else:
        if st.button("🖨️ Exportar PDF (sin logo)", key="btn_export_pdf"):
            try:
                fn = export_pdf()
                with open(fn, "rb") as f:
                    st.download_button("Descargar PDF", data=f, file_name=fn, mime="application/pdf", use_container_width=True, key="btn_download_pdf")
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

# ---------- Referencias ----------
with tab_refs:
    st.subheader("Referencias (dinámicas por escenario)")
    escenarios_sel = st.session_state.get("sb_escenarios", [])
    refs = filtrar_refs_por_contexto(escenarios_sel, st.session_state.get("anticoagulacion_tipo","—"))
    if not refs:
        st.info("No hay referencias que coincidan. Ajusta filtros o escenarios.")
    else:
        for i, r in enumerate(refs, 1):
            st.markdown(f"**[{i}] {r['title']}**  \n*{r['where']}* ({r['yr']}) — {r['blurb']}  \n[Ver fuente]({r['url']})")
            st.markdown("---")

st.caption("© Tapia Nefrología — Uso académico | TRRC360 by Dr. Tapia")

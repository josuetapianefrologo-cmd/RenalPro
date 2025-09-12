
import streamlit as st
from math import log
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

st.set_page_config(page_title="TRRC360 by Dr. Tapia", layout="wide")

# -------- Password Gate (simple) --------
DEFAULT_PASSWORD = "TRRC360"  # Cambia aquí si no usarás secrets
PW = st.secrets.get("APP_PASSWORD", DEFAULT_PASSWORD)

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state,auth_ok:
    st.title("Bienvenido a TRRC360 by Dr. Tapia")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua")
    st.image("logo.png", width=200) 
    st.warning("Por favor, ingresa la contraseña en el panel izquierdo para continuar.")
    st.stop()

with st.sidebar:
    st.subheader("Acceso")
    pw_input = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if pw_input == PW:
            st.session_state.auth_ok = True
        else:
            st.error("Contraseña incorrecta")

# ---------- Header ----------
col_logo, col_title = st.columns([1,6])
with col_logo:
    st.image("logo.png", width=100)
with col_title:
    st.title("TRRC360 by Dr. Tapia")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua (uso académico).")

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

# ---------- Main (Prescripción) ----------
with tab_main:
    st.subheader("Recomendación combinada")
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")

    c1, c2, c3 = st.columns(3)
    c1.metric("Modalidad", mod_final or "—")
    c2.metric("Filtro", filtro_final or "—")
    c3.metric("FF (estimada)", f"{ff:.2%}")

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
    if k > 6.5: sugs.append("K>6.5 → aumentar difusivo (CVVHD/CVVHDF)")
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
    fo_obj = st.number_input("FO% objetivo (p. ej. 5%)", value=0.05, step=0.01, min_value=0.0, max_value=0.5)
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

# ---------- Tendencias ----------
with tab_trends:
    st.subheader("Tendencias (T1–T3)")
    def row_trend(lbl, key):
        c1,c2,c3,c4,c5,c6,c7 = st.columns([2,1,1,1,1,1,3])
        c1.write(lbl)
        t1 = c2.number_input("T1", key=f"{key}_t1", value=0.0, step=0.1)
        t2 = c3.number_input("T2", key=f"{key}_t2", value=0.0, step=0.1)
        t3 = c4.number_input("T3", key=f"{key}_t3", value=0.0, step=0.1)
        d12 = t2 - t1
        d23 = t3 - t2
        c5.write(f"Δ12: {d12:.1f}")
        c6.write(f"Δ23: {d23:.1f}")
        interp = "—"
        if t1!=0 or t2!=0 or t3!=0:
            if (d12>0) or (d23>0): interp = "⬆️ Empeora: considerar ↑ dosis/flujo"
            else: interp = "⬇️ Mejora"
        c7.write(interp)

    row_trend("Na (mEq/L)","na")
    row_trend("K (mEq/L)","k")
    row_trend("Lactato (mmol/L)","lac")
    row_trend("Amonio (µmol/L)","nh4")
    row_trend("Urea (mg/dL)","urea")
    row_trend("Creatinina (mg/dL)","cr")

# ---------- Resumen / PDF ----------
with tab_rx:
    st.subheader("Resumen de prescripción")
    mod_final, filtro_final, comentarios = combinar_recomendaciones(escenarios)
    qp, qp_h, qe, qr_pre, qr_post, qd, ff = flows_and_ff(qb, hto, dosis_mlkg, peso, uf, mod_final or "CVVHDF")

    st.write(f"**Escenarios:** {', '.join(escenarios) if escenarios else '—'}")
    st.write(f"**Modalidad:** {mod_final or '—'} | **Filtro:** {filtro_final or '—'} | **FF:** {ff:.2%}")
    st.write(f"**Qb:** {qb} mL/min | **Qp:** {int(qp)} mL/min | **Qe:** {int(qe)} mL/h | **UF:** {uf} mL/h")
    st.write(f"**Qr pre:** {qr_pre} | **Qr post:** {qr_post} | **Qd:** {int(qd)}")
    st.write(f"**Comentarios:** {comentarios or '—'}")

    def export_pdf(filename="TRRC360_prescripcion.pdf"):
        c = canvas.Canvas(filename, pagesize=letter)
        w, h = letter
        y = h - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "TRRC360 by Dr. Tapia — Resumen de prescripción")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        y -= 20
        lines = [
            f"Escenarios: {', '.join(escenarios) if escenarios else '—'}",
            f"Modalidad: {mod_final or '—'}    Filtro: {filtro_final or '—'}    FF: {ff:.2%}",
            f"Qb: {qb} mL/min    Qp: {int(qp)} mL/min    Qe: {int(qe)} mL/h    UF: {uf} mL/h",
            f"Qr pre: {qr_pre}    Qr post: {qr_post}    Qd: {int(qd)}",
            f"Comentarios: {comentarios or '—'}",
            "— Uso académico; no sustituye juicio clínico —"
        ]
        for line in lines:
            c.drawString(50, y, line); y -= 16
        c.showPage(); c.save()
        return filename

    if st.button("Exportar a PDF"):
        fn = export_pdf()
        with open(fn, "rb") as f:
            st.download_button("Descargar PDF", data=f, file_name=fn, mime="application/pdf")

st.caption("© Tapia Nefrología – Uso académico | TRRC360 by Dr. Tapia")

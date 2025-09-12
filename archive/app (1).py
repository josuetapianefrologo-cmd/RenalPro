import streamlit as st

# ---------------- Configuración general ----------------
st.set_page_config(page_title="TRRC360 by Dr. Tapia", layout="wide")

# ---------------- Password Gate ----------------
DEFAULT_PASSWORD = "TRRC360"
PW = st.secrets.get("APP_PASSWORD", DEFAULT_PASSWORD)

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

# Sidebar: login primero
with st.sidebar:
    st.subheader("Acceso")
    pw_input = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if pw_input == PW:
            st.session_state.auth_ok = True
        else:
            st.error("Contraseña incorrecta")

# Si no está autenticado → mostrar bienvenida
if not st.session_state.auth_ok:
    st.title("Bienvenido a TRRC360 by Dr. Tapia")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua")
    st.image("logo.png", width=200)
    st.warning("Por favor, ingresa la contraseña en el panel izquierdo para continuar.")
    st.stop()

# ---------------- Header ----------------
col_logo, col_title = st.columns([1,6])
with col_logo:
    st.image("logo.png", width=100)
with col_title:
    st.title("TRRC360 by Dr. Tapia — v1.2")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua (uso académico).")

# ---------------- Parámetros básicos ----------------
with st.sidebar:
    st.header("Parámetros básicos")
    peso = st.number_input("Peso (kg)", min_value=10.0, max_value=300.0, value=70.0, step=0.5)
    hto = st.number_input("Hematocrito (fracción)", min_value=0.10, max_value=0.60, value=0.30, step=0.01, format="%.2f")
    qb = st.number_input("Qb (mL/min)", min_value=80, max_value=300, value=200, step=10)
    uf = st.number_input("UF (mL/h)", min_value=0, max_value=5000, value=100, step=50)
    dosis_obj = st.slider("Dosis objetivo (mL/kg/h)", 10, 45, 30)

# ---------------- Laboratorios ----------------
st.subheader("Tendencias (T1–T3)")

def trend_input(nombre, unidad, t1, t2, t3):
    c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
    v1 = c1.number_input(f"{nombre} T1", value=t1, step=0.1, format="%.2f")
    v2 = c2.number_input(f"{nombre} T2", value=t2, step=0.1, format="%.2f")
    v3 = c3.number_input(f"{nombre} T3", value=t3, step=0.1, format="%.2f")
    delta12 = v2 - v1
    delta23 = v3 - v2
    c4.metric("Δ12", f"{delta12:.1f}")
    c5.metric("Δ23", f"{delta23:.1f}")
    return v1, v2, v3

# Valores de ejemplo
na1, na2, na3 = trend_input("Na (mEq/L)", "mEq/L", 140.0, 130.0, 120.0)
k1, k2, k3 = trend_input("K (mEq/L)", "mEq/L", 4.0, 3.0, 2.0)
lact1, lact2, lact3 = trend_input("Lactato (mmol/L)", "mmol/L", 1.0, 1.0, 1.0)
urea1, urea2, urea3 = trend_input("Urea (mg/dL)", "mg/dL", 130.0, 100.0, 80.0)
cr1, cr2, cr3 = trend_input("Creatinina (mg/dL)", "mg/dL", 4.0, 3.0, 2.0)

# ---------------- Alertas clínicas ----------------
st.subheader("Alertas automáticas")

# Sodio
if na3 < 125 or na3 > 150:
    st.error(f"⚠️ Hiponatremia/Hipernatremia severa detectada (Na={na3:.1f} mEq/L) — revisar modalidad y líquidos.")
else:
    st.success(f"Sodio dentro de rango aceptable (Na={na3:.1f} mEq/L)")

# Potasio
if k3 < 3.0 or k3 > 5.5:
    st.error(f"⚠️ Alteración grave de potasio detectada (K={k3:.1f} mEq/L) — ajustar terapia.")
else:
    st.success(f"Potasio dentro de rango aceptable (K={k3:.1f} mEq/L)")

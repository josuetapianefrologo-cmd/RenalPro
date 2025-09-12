import streamlit as st

st.set_page_config(page_title="TRRC360 by Dr. Tapia", layout="wide")

# -------- Password Gate --------
DEFAULT_PASSWORD = "TRRC360"  # Puedes cambiarla aquí si no usarás secrets
PW = st.secrets.get("APP_PASSWORD", DEFAULT_PASSWORD)

# Estado inicial de autenticación
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

# ---------- Sidebar: LOGIN PRIMERO ----------
with st.sidebar:
    st.subheader("Acceso")
    pw_input = st.text_input("Contraseña", type="password", key="login_password")
    if st.button("Entrar", key="login_button"):
        if pw_input == PW:
            st.session_state.auth_ok = True
        else:
            st.error("Contraseña incorrecta")

# ---------- Mostrar bienvenida si no está autenticado ----------
if not st.session_state.auth_ok:
    st.title("Bienvenido a TRRC360 by Dr. Tapia")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua")
    st.image("logo.png", width=200)
    st.warning("Por favor, ingresa la contraseña en el panel izquierdo para continuar.")
    st.stop()

# ---------- Header ----------
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("logo.png", width=100)
with col_title:
    st.title("TRRC360 by Dr. Tapia")
    st.caption("Asistente clínico integral para prescripción de Terapias de Reemplazo Renal Continua (uso académico).")

# ---------- Aquí continúa tu app con todos los cálculos y pestañas ----------
# Ejemplo:
st.write("✅ Acceso autorizado. Bienvenido, Dr. Tapia.")

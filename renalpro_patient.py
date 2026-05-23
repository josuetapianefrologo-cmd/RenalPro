# ============================================================
# renalpro_patient.py
# RenalPro v3.1.0 | TRRC360 — Módulo: Ficha Ampliada de Paciente
# Importar en app.py:
#   from renalpro_patient import (render_patient_form_extended,
#       update_patient_extended_fields, get_patient_extended,
#       calcular_edad_exacta, edad_display)
# ============================================================

import calendar
import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import date, datetime


# ─── Utilidades de edad ─────────────────────────────────────────────────────

def calcular_edad_exacta(fecha_nac):
    """
    Calcula la edad exacta como (años, meses, días) sin dependencias externas.
    fecha_nac: date object o None
    """
    if not fecha_nac:
        return 0, 0, 0
    if isinstance(fecha_nac, str):
        try:
            fecha_nac = datetime.strptime(fecha_nac[:10], "%Y-%m-%d").date()
        except Exception:
            return 0, 0, 0

    hoy = date.today()

    # Años cumplidos
    años = hoy.year - fecha_nac.year
    if (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day):
        años -= 1

    # Mes del último cumpleaños
    try:
        ultimo_cumple = date(hoy.year if (hoy.month, hoy.day) >= (fecha_nac.month, fecha_nac.day)
                             else hoy.year - 1,
                             fecha_nac.month, fecha_nac.day)
    except ValueError:  # Feb 29 en año no bisiesto
        ultimo_cumple = date(hoy.year - 1, fecha_nac.month, 28)

    # Meses desde el último cumpleaños
    meses = (hoy.year - ultimo_cumple.year) * 12 + (hoy.month - ultimo_cumple.month)
    if hoy.day < ultimo_cumple.day:
        meses -= 1
    meses = max(meses % 12, 0)

    # Días
    if hoy.day >= fecha_nac.day:
        dias = hoy.day - fecha_nac.day
    else:
        prev_m = hoy.month - 1 if hoy.month > 1 else 12
        prev_y = hoy.year if hoy.month > 1 else hoy.year - 1
        dias_mes = calendar.monthrange(prev_y, prev_m)[1]
        dias = dias_mes - fecha_nac.day + hoy.day

    return años, meses, dias


def edad_display(fecha_nac):
    """Retorna string legible de edad exacta."""
    a, m, d = calcular_edad_exacta(fecha_nac)
    return f"{a} años, {m} meses, {d} días"


# ─── DB helpers ─────────────────────────────────────────────────────────────

EXTENDED_COLS = [
    "apellido_paterno", "apellido_materno", "nombres", "curp", "id_externo",
    "fecha_nacimiento", "sexo", "escolaridad", "ocupacion", "estado_civil",
    "religion", "grupo_etnico", "fecha_ingreso_unidad", "procedencia",
    "calle", "no_ext", "no_int", "referencia_dom", "colonia", "municipio",
    "estado_residencia", "cp", "pais", "telefono",
    "contacto_nombre", "contacto_parentesco", "contacto_telefono",
]


def get_patient_extended(conn, patient_id):
    """Devuelve dict completo del paciente incluyendo campos ampliados."""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        row = cur.fetchone()
        return dict(row) if row else {}


def update_patient_extended_fields(conn, patient_id, data):
    """
    Actualiza los campos ampliados del paciente en la DB.
    data: dict con las claves de EXTENDED_COLS.
    """
    available = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'patients'
        """)
        available = {r[0] for r in cur.fetchall()}

    cols = [c for c in EXTENDED_COLS if c in available]
    if not cols:
        return False

    set_clause = ", ".join(f"{c} = %s" for c in cols)
    values = [data.get(c) for c in cols]
    values.append(patient_id)

    with conn.cursor() as cur:
        cur.execute(f"UPDATE patients SET {set_clause} WHERE id = %s", values)
    conn.commit()
    return True


# ─── UI: Formulario ampliado ─────────────────────────────────────────────────

def render_patient_form_extended(key_prefix="epf", patient_data=None):
    """
    Renderiza el formulario completo ampliado del paciente.
    Retorna dict con todos los valores (siempre, sin botón de submit).
    El submit lo maneja app.py.

    Uso en app.py:
        form_data = render_patient_form_extended("edit", existing_patient)
        if st.button("Guardar"):
            update_patient_extended_fields(conn, patient_id, form_data)
    """
    p = patient_data or {}

    def g(field, default=""):
        v = p.get(field, default)
        return v if v is not None else default

    def gd(field):
        v = p.get(field)
        if not v:
            return None
        if isinstance(v, str):
            try:
                return datetime.strptime(v[:10], "%Y-%m-%d").date()
            except Exception:
                return None
        return v

    def sel_idx(opts, field, default=0):
        val = g(field)
        return opts.index(val) if val in opts else default

    # ── Identificación ────────────────────────────────────────────────────
    st.markdown("#### 🪪 Identificación")
    c1, c2, c3 = st.columns(3)
    ap_pat = c1.text_input("Apellido Paterno *", value=g("apellido_paterno"),
                            key=f"{key_prefix}_ap_pat").strip()
    ap_mat = c2.text_input("Apellido Materno", value=g("apellido_materno"),
                            key=f"{key_prefix}_ap_mat").strip()
    nombres = c3.text_input("Nombre(s) *", value=g("nombres"),
                             key=f"{key_prefix}_nombres").strip()

    c1, c2 = st.columns(2)
    curp = c1.text_input("CURP", value=g("curp"), max_chars=18,
                          key=f"{key_prefix}_curp",
                          placeholder="18 caracteres").strip().upper()
    id_ext = c2.text_input("ID Externo / NSS / Expediente previo",
                            value=g("id_externo"),
                            key=f"{key_prefix}_id_ext").strip()

    st.markdown("---")
    # ── Nacimiento y datos demográficos ───────────────────────────────────
    st.markdown("#### 🎂 Nacimiento y Datos Demográficos")

    c1, c2, c3 = st.columns(3)
    with c1:
        fecha_nac = st.date_input(
            "Fecha de Nacimiento *",
            value=gd("fecha_nacimiento") or date(1960, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY",
            key=f"{key_prefix}_fecha_nac",
        )
    with c2:
        años, meses, dias = calcular_edad_exacta(fecha_nac)
        st.markdown("**Edad calculada:**")
        st.success(f"**{años}** años · {meses} meses · {dias} días")
    with c3:
        sexo_opts = ["-- Seleccione --", "Femenino", "Masculino", "Indeterminado"]
        sexo = st.selectbox("Sexo *", sexo_opts,
                            index=sel_idx(sexo_opts, "sexo"),
                            key=f"{key_prefix}_sexo")

    c1, c2, c3 = st.columns(3)
    esc_opts = [
        "-- Seleccione --", "Sin escolaridad", "Primaria incompleta",
        "Primaria completa", "Secundaria", "Preparatoria/Bachillerato",
        "Técnico", "Licenciatura", "Posgrado",
    ]
    escolaridad = c1.selectbox("Escolaridad", esc_opts,
                                index=sel_idx(esc_opts, "escolaridad"),
                                key=f"{key_prefix}_esc")
    ocupacion = c2.text_input("Ocupación", value=g("ocupacion"),
                               key=f"{key_prefix}_ocup")
    ec_opts = [
        "-- Seleccione --", "Soltero/a", "Casado/a", "Unión libre",
        "Divorciado/a", "Viudo/a", "Separado/a",
    ]
    estado_civil = c3.selectbox("Estado Civil", ec_opts,
                                 index=sel_idx(ec_opts, "estado_civil"),
                                 key=f"{key_prefix}_ec")

    c1, c2 = st.columns(2)
    religion = c1.text_input("Religión", value=g("religion"), key=f"{key_prefix}_rel")
    grupo_etnico = c2.text_input("Grupo Étnico", value=g("grupo_etnico"),
                                  key=f"{key_prefix}_etnico",
                                  placeholder="Ej: Mestizo, indígena náhuatl…")

    st.markdown("---")
    # ── Ingreso a la unidad ───────────────────────────────────────────────
    st.markdown("#### 🏥 Ingreso a la Unidad")
    c1, c2 = st.columns(2)
    with c1:
        fecha_ing = st.date_input(
            "Fecha de Ingreso a Unidad",
            value=gd("fecha_ingreso_unidad") or date.today(),
            format="DD/MM/YYYY",
            key=f"{key_prefix}_fecha_ing",
        )
    procedencia = c2.text_input(
        "Procedencia", value=g("procedencia"),
        key=f"{key_prefix}_proc",
        placeholder="Ej: IMSS, Hospital General, consulta privada",
    )

    st.markdown("---")
    # ── Domicilio ─────────────────────────────────────────────────────────
    st.markdown("#### 📍 Domicilio")
    c1, c2, c3 = st.columns([4, 1, 1])
    calle = c1.text_input("Calle", value=g("calle"), key=f"{key_prefix}_calle")
    no_ext = c2.text_input("No. Ext.", value=g("no_ext"), key=f"{key_prefix}_noext")
    no_int = c3.text_input("No. Int.", value=g("no_int"), key=f"{key_prefix}_noint")

    c1, c2 = st.columns(2)
    colonia = c1.text_input("Colonia", value=g("colonia"), key=f"{key_prefix}_col")
    ref_dom = c2.text_input("Referencia", value=g("referencia_dom"),
                             key=f"{key_prefix}_ref",
                             placeholder="Entre calles, punto de referencia")

    c1, c2, c3, c4 = st.columns(4)
    municipio = c1.text_input("Municipio",
                               value=g("municipio") or "León",
                               key=f"{key_prefix}_mpio")
    estado_res = c2.text_input("Estado",
                                value=g("estado_residencia") or "Guanajuato",
                                key=f"{key_prefix}_edores")
    cp = c3.text_input("C.P.", value=g("cp"), max_chars=5, key=f"{key_prefix}_cp")
    pais = c4.text_input("País", value=g("pais") or "México", key=f"{key_prefix}_pais")

    telefono = st.text_input("Teléfono del paciente", value=g("telefono"),
                              key=f"{key_prefix}_tel", placeholder="10 dígitos")

    st.markdown("---")
    # ── Contacto de emergencia ────────────────────────────────────────────
    st.markdown("#### 🚨 Contacto de Emergencia")
    c1, c2, c3 = st.columns(3)
    cont_nombre = c1.text_input("Nombre completo", value=g("contacto_nombre"),
                                  key=f"{key_prefix}_cnombre").strip()
    par_opts = [
        "-- Seleccione --", "Cónyuge/Pareja", "Hijo/a", "Padre", "Madre",
        "Hermano/a", "Abuelo/a", "Nieto/a", "Tío/a", "Otro familiar", "Amigo/a", "Otro",
    ]
    cont_par = c2.selectbox("Parentesco", par_opts,
                             index=sel_idx(par_opts, "contacto_parentesco"),
                             key=f"{key_prefix}_cpar")
    cont_tel = c3.text_input("Teléfono", value=g("contacto_telefono"),
                              key=f"{key_prefix}_ctel", placeholder="10 dígitos")

    # ── Retorno ───────────────────────────────────────────────────────────
    nombre_completo = f"{ap_pat} {ap_mat}, {nombres}".strip().strip(",").strip()

    return {
        "apellido_paterno":     ap_pat,
        "apellido_materno":     ap_mat,
        "nombres":              nombres,
        "nombre_completo":      nombre_completo,
        "curp":                 curp,
        "id_externo":           id_ext,
        "fecha_nacimiento":     fecha_nac.isoformat() if fecha_nac else None,
        "edad_años":            años,
        "edad_meses":           meses,
        "edad_dias":            dias,
        "sexo":                 sexo if sexo != "-- Seleccione --" else None,
        "escolaridad":          escolaridad if escolaridad != "-- Seleccione --" else None,
        "ocupacion":            ocupacion.strip(),
        "estado_civil":         estado_civil if estado_civil != "-- Seleccione --" else None,
        "religion":             religion.strip(),
        "grupo_etnico":         grupo_etnico.strip(),
        "fecha_ingreso_unidad": fecha_ing.isoformat() if fecha_ing else None,
        "procedencia":          procedencia.strip(),
        "calle":                calle.strip(),
        "no_ext":               no_ext.strip(),
        "no_int":               no_int.strip(),
        "referencia_dom":       ref_dom.strip(),
        "colonia":              colonia.strip(),
        "municipio":            municipio.strip(),
        "estado_residencia":    estado_res.strip(),
        "cp":                   cp.strip(),
        "pais":                 pais.strip(),
        "telefono":             telefono.strip(),
        "contacto_nombre":      cont_nombre,
        "contacto_parentesco":  cont_par if cont_par != "-- Seleccione --" else None,
        "contacto_telefono":    cont_tel.strip(),
    }

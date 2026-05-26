"""
TRRC360 — Capa de base de datos (Railway PostgreSQL)
Maneja: usuarios, suscripciones, prescripciones guardadas, pagos MP
"""
import streamlit as st
import psycopg2
import psycopg2.extras
import bcrypt
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# ── CONEXIÓN ──────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_conn_resource():
    """Conexión cacheada a Railway. None si DATABASE_URL no está configurado."""
    try:
        db_url = st.secrets.get("DATABASE_URL", "")
        if not db_url:
            return None
        # Railway public endpoint requiere SSL
        if "sslmode" not in db_url:
            db_url += ("&sslmode=require" if "?" in db_url else "?sslmode=require")
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    except Exception:
        return None

def get_conn():
    """Retorna conexión activa o la reconecta si está cerrada."""
    conn = _get_conn_resource()
    if conn is None:
        return None
    try:
        if conn.closed:
            st.cache_resource.clear()
            conn = _get_conn_resource()
        # Ping
        conn.cursor().execute("SELECT 1")
        return conn
    except Exception:
        try:
            st.cache_resource.clear()
            return _get_conn_resource()
        except Exception:
            return None

def db_ok() -> bool:
    """True si la DB está disponible y conectada."""
    return get_conn() is not None


# ── INICIALIZAR TABLAS ────────────────────────────────────────────────────────
def init_tables() -> bool:
    """Crea las tablas si no existen. Ejecutar al inicio de la app."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                SERIAL PRIMARY KEY,
                username          VARCHAR(50)  UNIQUE NOT NULL,
                password_hash     VARCHAR(255) NOT NULL,
                nombre            VARCHAR(100),
                email             VARCHAR(100),
                rol               VARCHAR(20)  DEFAULT 'free',
                trial_end         TIMESTAMP,
                subscription_end  TIMESTAMP,
                grace_until       TIMESTAMP,
                created_at        TIMESTAMP    DEFAULT NOW(),
                last_login        TIMESTAMP,
                avatar            VARCHAR(20)  DEFAULT '👨‍⚕️',
                institucion       VARCHAR(200)
            );

            CREATE TABLE IF NOT EXISTS prescriptions (
                id            SERIAL PRIMARY KEY,
                user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
                alias         VARCHAR(100) DEFAULT 'Paciente sin nombre',
                modality      VARCHAR(50),
                peso          FLOAT,
                hto           FLOAT,
                qb            INTEGER,
                qeff          FLOAT,
                uf            INTEGER,
                dosis_mlkgh   FLOAT,
                anticoag      VARCHAR(50),
                escenarios    TEXT,
                notas         TEXT,
                datos_json    TEXT,
                created_at    TIMESTAMP DEFAULT NOW(),
                is_deleted    BOOLEAN   DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS payments (
                id                SERIAL PRIMARY KEY,
                user_id           INTEGER REFERENCES users(id),
                mp_payment_id     VARCHAR(100),
                mp_preference_id  VARCHAR(200),
                amount            FLOAT,
                status            VARCHAR(20) DEFAULT 'pending',
                meses             INTEGER     DEFAULT 1,
                created_at        TIMESTAMP   DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS patient_sessions (
                id                SERIAL PRIMARY KEY,
                prescription_id   INTEGER REFERENCES prescriptions(id) ON DELETE CASCADE,
                user_id           INTEGER REFERENCES users(id),
                session_label     VARCHAR(100) DEFAULT 'Sesión',
                horas_trrc        FLOAT DEFAULT 24,
                creatinina        FLOAT,
                bun               FLOAT,
                diuresis_ml       FLOAT,
                k_val             FLOAT,
                na_val            FLOAT,
                fosfato           FLOAT,
                mg_val            FLOAT,
                ph_val            FLOAT,
                hco3_val          FLOAT,
                lactato           FLOAT,
                sofa_val          INTEGER,
                pam_val           FLOAT,
                norepinefrina     FLOAT,
                qe_real           FLOAT,
                ff_real           FLOAT,
                tmp_mmhg          FLOAT,
                filtros_cambiados INTEGER DEFAULT 0,
                aptt_valor        FLOAT,
                hnf_dosis_actual  FLOAT,
                ica_post          FLOAT,
                ica_sist          FLOAT,
                notas_sesion      TEXT,
                created_at        TIMESTAMP DEFAULT NOW()
            );
        """)
        # Agregar columnas nuevas si ya existe la tabla (migración segura)
        for alter in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR(20) DEFAULT '👨‍⚕️'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS institucion VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cedula_profesional VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS universidad VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS domicilio_consultorio VARCHAR(300)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS telefono_consultorio VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cedula_general VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS universidad_general VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS especialidad VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cedula_especialidad VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS universidad_especialidad VARCHAR(200)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consejo_nombre VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consejo_numero VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS receta_folio_counter INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS diagnosticos_custom TEXT DEFAULT '[]'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS logo_b64 TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS firma_b64 TEXT DEFAULT ''",
        ]:
            try:
                cur.execute(alter)
            except Exception:
                pass
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prescriptions_user ON prescriptions(user_id, is_deleted);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_presc ON patient_sessions(prescription_id);")
        cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_mp_id ON payments(mp_payment_id)
            WHERE mp_payment_id IS NOT NULL;""")

        # ── Nuevas tablas — expediente clínico centrado en el paciente ─────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id               SERIAL PRIMARY KEY,
                user_id          INTEGER REFERENCES users(id) ON DELETE CASCADE,
                nombre           VARCHAR(100) NOT NULL,
                expediente       VARCHAR(50),
                fecha_nacimiento DATE,
                edad             INTEGER,
                sexo             VARCHAR(10),
                peso             FLOAT,
                diagnostico      TEXT,
                tipo             VARCHAR(50) DEFAULT 'general',
                notas            TEXT,
                created_at       TIMESTAMP DEFAULT NOW(),
                is_deleted       BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS clinical_records (
                id               SERIAL PRIMARY KEY,
                patient_id       INTEGER REFERENCES patients(id) ON DELETE CASCADE,
                user_id          INTEGER REFERENCES users(id),
                tipo             VARCHAR(50) NOT NULL,
                titulo           VARCHAR(200),
                fecha_consulta   DATE DEFAULT CURRENT_DATE,
                datos_json       TEXT,
                resumen          TEXT,
                receta_generada  BOOLEAN DEFAULT FALSE,
                notas            TEXT,
                created_at       TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_patients_user ON patients(user_id, is_deleted);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_patient ON clinical_records(patient_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_user ON clinical_records(user_id);")

        # ── Campos ampliados para patients (renalpro_patient.py) ─────────────
        for alter_pac in [
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS apellido_paterno VARCHAR(100)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS apellido_materno VARCHAR(100)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS nombres VARCHAR(150)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS curp VARCHAR(20)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS id_externo VARCHAR(50)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS escolaridad VARCHAR(100)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS ocupacion VARCHAR(150)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS estado_civil VARCHAR(30)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS religion VARCHAR(80)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS grupo_etnico VARCHAR(80)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS fecha_ingreso_unidad DATE",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS procedencia VARCHAR(150)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS calle VARCHAR(200)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS no_ext VARCHAR(20)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS no_int VARCHAR(20)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS referencia_dom VARCHAR(300)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS colonia VARCHAR(150)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS municipio VARCHAR(150)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS estado_residencia VARCHAR(100)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS cp VARCHAR(10)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS pais VARCHAR(80) DEFAULT 'México'",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS telefono VARCHAR(30)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS contacto_nombre VARCHAR(150)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS contacto_parentesco VARCHAR(50)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS contacto_telefono VARCHAR(30)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS talla FLOAT",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS historia_clinica JSONB",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS historia_clinica_fecha TIMESTAMP",
            # ── Dashboard TR — marcas manuales y metadata ─────────────────
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS es_trasplantado BOOLEAN DEFAULT FALSE",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS sede_principal VARCHAR(100)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tr_fecha_tx DATE",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tr_donador VARCHAR(50)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tr_etiologia_erc VARCHAR(200)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tr_grupo_sang VARCHAR(10)",
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tr_ultima_revision TIMESTAMP",
        ]:
            try:
                cur.execute(alter_pac)
            except Exception:
                pass

        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ── CONTRASEÑAS ───────────────────────────────────────────────────────────────
def hash_pwd(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_pwd(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ── USUARIOS ──────────────────────────────────────────────────────────────────
def get_user(username: str) -> Optional[Dict]:
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception:
        return None

def create_user(username: str, password: str, nombre: str,
                email: str = "", trial_days: int = 7) -> tuple:
    """Retorna (ok: bool, mensaje: str)"""
    conn = get_conn()
    if not conn:
        return False, "Base de datos no disponible"
    if get_user(username):
        return False, "El usuario ya existe"
    try:
        cur = conn.cursor()
        trial_end = datetime.utcnow() + timedelta(days=trial_days)
        cur.execute("""
            INSERT INTO users (username, password_hash, nombre, email, rol, trial_end)
            VALUES (%s, %s, %s, %s, 'trial', %s)
        """, (username, hash_pwd(password), nombre, email, trial_end))
        conn.commit()
        cur.close()
        return True, "Usuario creado correctamente"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)

def login_user(username: str, password: str) -> Optional[Dict]:
    """Retorna el dict del usuario si credenciales correctas, None si no."""
    user = get_user(username)
    if not user:
        return None
    if not verify_pwd(password, user["password_hash"]):
        return None
    # Update last_login
    conn = get_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user["id"],))
            conn.commit()
            cur.close()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    return user

def get_effective_rol(user: Dict) -> str:
    """Calcula el rol real basado en fechas de suscripción."""
    if user.get("rol") == "admin":
        return "admin"
    if user.get("rol") == "beca":
        # Beca indefinida o con fecha válida
        sub_end = user.get("subscription_end")
        if not sub_end or sub_end > datetime.utcnow():
            return "beca"
    now = datetime.utcnow()
    sub_end   = user.get("subscription_end")
    trial_end = user.get("trial_end")
    grace     = user.get("grace_until")
    if sub_end  and sub_end  > now: return "pro"
    if trial_end and trial_end > now: return "trial"
    if grace    and grace    > now: return "grace"
    return "free"

def get_dias_restantes(user: Dict) -> int:
    now = datetime.utcnow()
    for campo in ("subscription_end", "trial_end"):
        val = user.get(campo)
        if val and val > now:
            return max(0, (val - now).days)
    return 0

def update_subscription(user_id: int, meses: int = 1) -> bool:
    """Activa o extiende suscripción Pro."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT subscription_end FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        now = datetime.utcnow()
        current = row["subscription_end"] if row and row["subscription_end"] else now
        new_end  = max(current, now) + timedelta(days=30 * meses)
        grace    = new_end + timedelta(days=60)
        cur.execute("""
            UPDATE users SET rol='pro', subscription_end=%s, grace_until=%s WHERE id=%s
        """, (new_end, grace, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def grant_beca(user_id: int, meses: int = 0, nota: str = "") -> bool:
    """
    Otorga beca académica completa.
    meses = 0  → acceso indefinido (hasta 2099)
    meses > 0  → duración específica en meses
    """
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        now = datetime.utcnow()
        if meses == 0:
            sub_end = datetime(2099, 12, 31, 23, 59, 59)
        else:
            sub_end = now + timedelta(days=30 * meses)
        grace = sub_end + timedelta(days=60)
        cur.execute("""
            UPDATE users SET rol='beca', subscription_end=%s, grace_until=%s WHERE id=%s
        """, (sub_end, grace, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def revoke_beca(user_id: int) -> bool:
    """Revoca beca y devuelve al usuario a free."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET rol='free', subscription_end=NULL, grace_until=NULL WHERE id=%s
        """, (user_id,))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def update_user_password(user_id: int, new_password: str) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                    (hash_pwd(new_password), user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def deactivate_user(user_id: int) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET rol='free', subscription_end=NULL WHERE id=%s", (user_id,))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def get_all_users() -> List[Dict]:
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, nombre, email, rol,
                   trial_end, subscription_end, grace_until,
                   created_at, last_login
            FROM users ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── PRESCRIPCIONES ────────────────────────────────────────────────────────────
# ── PACIENTES ──────────────────────────────────────────────────────────────────
def create_patient(user_id: int, data: Dict) -> Optional[int]:
    """Crea un nuevo paciente. Retorna el ID o None."""
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO patients (user_id, nombre, expediente, edad, sexo,
                peso, talla, diagnostico, tipo, notas)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            user_id, data.get("nombre","Paciente"),
            data.get("expediente"), data.get("edad"),
            data.get("sexo"), data.get("peso"),
            data.get("talla"),
            data.get("diagnostico"), data.get("tipo","general"),
            data.get("notas",""),
        ))
        new_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        return new_id
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None

def get_patients(user_id: int) -> List[Dict]:
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM patients
            WHERE user_id=%s AND is_deleted=FALSE
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_patient(patient_id: int, user_id: int) -> Optional[Dict]:
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM patients WHERE id=%s AND user_id=%s", (patient_id, user_id))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception:
        return None

def update_patient(patient_id: int, user_id: int, data: Dict) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE patients SET nombre=%s, expediente=%s, edad=%s, sexo=%s,
                peso=%s, talla=%s, diagnostico=%s, tipo=%s, notas=%s
            WHERE id=%s AND user_id=%s
        """, (
            data.get("nombre"), data.get("expediente"), data.get("edad"),
            data.get("sexo"), data.get("peso"), data.get("talla"),
            data.get("diagnostico"),
            data.get("tipo","general"), data.get("notas",""),
            patient_id, user_id
        ))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def delete_patient(patient_id: int, user_id: int) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE patients SET is_deleted=TRUE WHERE id=%s AND user_id=%s",
                    (patient_id, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

# ── REGISTROS CLÍNICOS ─────────────────────────────────────────────────────────
def add_clinical_record(patient_id: int, user_id: int, data: Dict) -> Optional[int]:
    """Agrega un registro clínico vinculado al paciente."""
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO clinical_records
            (patient_id, user_id, tipo, titulo, fecha_consulta,
             datos_json, resumen, notas)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            patient_id, user_id,
            data.get("tipo","general"),
            data.get("titulo","Consulta"),
            data.get("fecha_consulta"),
            json.dumps(data.get("datos",{}), ensure_ascii=False, default=str),
            data.get("resumen",""),
            data.get("notas",""),
        ))
        new_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        return new_id
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None

def get_clinical_records(patient_id: int) -> List[Dict]:
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM clinical_records
            WHERE patient_id=%s
            ORDER BY created_at DESC
        """, (patient_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def delete_clinical_record(record_id: int, user_id: int) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM clinical_records WHERE id=%s AND user_id=%s",
                    (record_id, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def update_user_profile(user_id: int, nombre: str, email: str,
                        especialidad: str, institucion: str, avatar: str,
                        cedula: str = "", universidad: str = "",
                        domicilio: str = "", telefono: str = "",
                        cedula_general: str = "", universidad_general: str = "",
                        cedula_especialidad: str = "", universidad_especialidad: str = "",
                        consejo_nombre: str = "", consejo_numero: str = "") -> bool:
    """Actualiza perfil completo del usuario incluyendo credenciales COFEPRIS."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET
                nombre=%s, email=%s, avatar=%s, institucion=%s,
                especialidad=%s,
                cedula_profesional=%s, universidad=%s,
                domicilio_consultorio=%s, telefono_consultorio=%s,
                cedula_general=%s, universidad_general=%s,
                cedula_especialidad=%s, universidad_especialidad=%s,
                consejo_nombre=%s, consejo_numero=%s
            WHERE id=%s
        """, (nombre, email, avatar, institucion,
              especialidad,
              cedula, universidad,
              domicilio, telefono,
              cedula_general, universidad_general,
              cedula_especialidad, universidad_especialidad,
              consejo_nombre, consejo_numero,
              user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def save_user_logo(user_id: int, logo_b64: str) -> bool:
    """Guarda el logo del consultorio en la DB del usuario."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET logo_b64=%s WHERE id=%s", (logo_b64, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def save_user_firma(user_id: int, firma_b64: str) -> bool:
    """Guarda la firma digital del usuario para usar en recetas, notas e historias."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET firma_b64=%s WHERE id=%s", (firma_b64, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def get_next_folio(user_id: int) -> str:
    """Genera el siguiente folio de receta para el usuario."""
    conn = get_conn()
    if not conn:
        from datetime import datetime
        return f"SIN-{datetime.now().strftime('%y%m%d%H%M')}"
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET receta_folio_counter = receta_folio_counter + 1
            WHERE id=%s RETURNING receta_folio_counter
        """, (user_id,))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        counter = row["receta_folio_counter"] if row else 1
        from datetime import datetime
        return f"{datetime.now().strftime('%y%m')}-{counter:04d}"
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        from datetime import datetime
        return f"SIN-{datetime.now().strftime('%y%m%d')}"

def get_user_diagnosticos(user_id: int) -> list:
    """Obtiene los diagnósticos personalizados del usuario."""
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT diagnosticos_custom FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        if row and row["diagnosticos_custom"]:
            import json
            return json.loads(row["diagnosticos_custom"])
        return []
    except Exception:
        return []

def save_user_diagnosticos(user_id: int, diagnosticos: list) -> bool:
    """Guarda la lista de diagnósticos personalizados del usuario."""
    conn = get_conn()
    if not conn:
        return False
    try:
        import json
        cur = conn.cursor()
        cur.execute("UPDATE users SET diagnosticos_custom=%s WHERE id=%s",
                    (json.dumps(diagnosticos, ensure_ascii=False), user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def change_password(user_id: int, old_hash: str, new_hash: str) -> bool:
    """Cambia contraseña verificando la actual."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return False
        import bcrypt
        if not bcrypt.checkpw(old_hash.encode(), row["password_hash"].encode()):
            cur.close()
            return False
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def get_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception:
        return None

def update_prescription(presc_id: int, user_id: int, data: Dict) -> bool:
    """Actualiza una prescripción existente sin crear duplicado."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE prescriptions SET
                alias=%s, modality=%s, peso=%s, hto=%s, qb=%s, qeff=%s,
                uf=%s, dosis_mlkgh=%s, anticoag=%s, escenarios=%s,
                notas=%s, datos_json=%s
            WHERE id=%s AND user_id=%s AND is_deleted=FALSE
        """, (
            data.get("alias", "Paciente"),
            data.get("modality", "—"),
            data.get("peso"), data.get("hto"),
            data.get("qb"), data.get("qeff"),
            data.get("uf"), data.get("dosis_mlkgh"),
            data.get("anticoag", "—"),
            ", ".join(data.get("escenarios", [])) if isinstance(data.get("escenarios"), list) else data.get("escenarios", ""),
            data.get("notas", ""),
            json.dumps(data, ensure_ascii=False, default=str),
            presc_id, user_id
        ))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def save_prescription(user_id: int, data: Dict) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO prescriptions
            (user_id, alias, modality, peso, hto, qb, qeff, uf,
             dosis_mlkgh, anticoag, escenarios, notas, datos_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            user_id,
            data.get("alias", "Paciente"),
            data.get("modality", "—"),
            data.get("peso"),
            data.get("hto"),
            data.get("qb"),
            data.get("qeff"),
            data.get("uf"),
            data.get("dosis_mlkgh"),
            data.get("anticoag", "—"),
            ", ".join(data.get("escenarios", [])),
            data.get("notas", ""),
            json.dumps(data, ensure_ascii=False, default=str),
        ))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def get_prescriptions(user_id: int) -> List[Dict]:
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, alias, modality, peso, hto, qb, qeff, uf,
                   dosis_mlkgh, anticoag, escenarios, notas, created_at
            FROM prescriptions
            WHERE user_id=%s AND is_deleted=FALSE
            ORDER BY created_at DESC LIMIT 200
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def delete_prescription(presc_id: int, user_id: int) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE prescriptions SET is_deleted=TRUE
            WHERE id=%s AND user_id=%s
        """, (presc_id, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def count_prescriptions(user_id: int) -> int:
    conn = get_conn()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as n FROM prescriptions
            WHERE user_id=%s AND is_deleted=FALSE
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        return row["n"] if row else 0
    except Exception:
        return 0


# ── MERCADO PAGO ──────────────────────────────────────────────────────────────
def create_mp_preference(user_id: int, username: str) -> Optional[str]:
    """
    Genera un link de pago de Mercado Pago para el usuario.
    Retorna la URL de checkout o None si falla.
    Requiere MP_ACCESS_TOKEN y WEBHOOK_URL en Streamlit secrets.
    """
    try:
        import mercadopago
        access_token = st.secrets.get("MP_ACCESS_TOKEN", "")
        webhook_url  = st.secrets.get("WEBHOOK_URL", "")
        app_url      = st.secrets.get("APP_URL", "https://trrc360.streamlit.app")

        if not access_token:
            return None

        sdk = mercadopago.SDK(access_token)

        preference_data = {
            "items": [{
                "title": "TRRC360 Pro — 1 mes",
                "description": "Acceso completo: guardar prescripciones, historial clínico",
                "quantity": 1,
                "unit_price": 99.0,
                "currency_id": "MXN",
            }],
            "external_reference": f"user_{user_id}_{username}",
            "notification_url": f"{webhook_url}/mp-webhook" if webhook_url else "",
            "back_urls": {
                "success": f"{app_url}?payment=success",
                "failure": f"{app_url}?payment=failure",
                "pending": f"{app_url}?payment=pending",
            },
            "auto_return": "approved",
            "payment_methods": {"installments": 1},
        }

        result = sdk.preference().create(preference_data)
        pref   = result.get("response", {})
        pref_id = pref.get("id", "")

        # Registrar preferencia pendiente
        conn = get_conn()
        if conn and pref_id:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO payments (user_id, mp_preference_id, amount, status)
                    VALUES (%s,%s,99.0,'pending')
                """, (user_id, pref_id))
                conn.commit()
                cur.close()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        return pref.get("init_point")   # URL de producción
        # Para sandbox: pref.get("sandbox_init_point")

    except Exception:
        return None

def get_payment_history(user_id: int) -> List[Dict]:
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT mp_payment_id, amount, status, meses, created_at
            FROM payments WHERE user_id=%s
            ORDER BY created_at DESC LIMIT 20
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

# ── SESIONES DE SEGUIMIENTO ────────────────────────────────────────────────────
def add_session(prescription_id: int, user_id: int, data: Dict) -> bool:
    """Agrega una sesión de seguimiento a una prescripción."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO patient_sessions
            (prescription_id, user_id, session_label, horas_trrc,
             creatinina, bun, diuresis_ml, k_val, na_val, fosfato, mg_val,
             ph_val, hco3_val, lactato, sofa_val, pam_val, norepinefrina,
             qe_real, ff_real, tmp_mmhg, filtros_cambiados,
             aptt_valor, hnf_dosis_actual, ica_post, ica_sist, notas_sesion)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            prescription_id, user_id,
            data.get("label", "Sesión"),
            data.get("horas_trrc", 24),
            data.get("creatinina"), data.get("bun"), data.get("diuresis_ml"),
            data.get("k_val"), data.get("na_val"), data.get("fosfato"), data.get("mg_val"),
            data.get("ph_val"), data.get("hco3_val"), data.get("lactato"),
            data.get("sofa_val"), data.get("pam_val"), data.get("norepinefrina"),
            data.get("qe_real"), data.get("ff_real"), data.get("tmp_mmhg"),
            data.get("filtros_cambiados", 0),
            data.get("aptt_valor"), data.get("hnf_dosis_actual"),
            data.get("ica_post"), data.get("ica_sist"),
            data.get("notas_sesion", ""),
        ))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

def get_sessions(prescription_id: int) -> List[Dict]:
    """Retorna todas las sesiones de seguimiento de una prescripción."""
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM patient_sessions
            WHERE prescription_id = %s
            ORDER BY created_at ASC
        """, (prescription_id,))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def delete_session(session_id: int, user_id: int) -> bool:
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM patient_sessions WHERE id=%s AND user_id=%s",
                    (session_id, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD TR — Cohorte de pacientes trasplantados
# ══════════════════════════════════════════════════════════════════════════════

# Tipos de nota considerados "evidencia de trasplante"
TR_NOTE_TYPES = (
    "Nota evolución Post-TR",
    "Trasplante / Nota inicial post-TR",
)


def get_cohorte_tr(user_id: int) -> List[Dict]:
    """
    Devuelve la cohorte de pacientes TR de un médico.

    Un paciente entra a la cohorte si CUALQUIERA de:
      a) Tiene es_trasplantado = TRUE (marca manual)
      b) Tiene al menos una nota de tipo Post-TR (auto-detección)

    Para cada paciente devuelve:
      - id, nombre, edad, sexo, sede_principal
      - es_trasplantado_manual (bool)
      - tr_fecha_tx, tr_donador, tr_etiologia_erc, tr_grupo_sang
      - ultima_nota_post_tr (dict con datos_json de la última nota)
      - dias_desde_ultima_nota
      - alertas (list de strings)
    """
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        # Pacientes del médico, no borrados, que son TR (auto OR manual)
        cur.execute("""
            SELECT DISTINCT p.id
            FROM patients p
            LEFT JOIN clinical_records cr
              ON cr.patient_id = p.id AND cr.tipo IN %s
            WHERE p.user_id = %s
              AND p.is_deleted = FALSE
              AND (p.es_trasplantado = TRUE OR cr.id IS NOT NULL)
        """, (TR_NOTE_TYPES, user_id))
        ids = [r["id"] for r in cur.fetchall()]
        cur.close()

        if not ids:
            return []

        cohorte = []
        for pid in ids:
            datos = _build_cohorte_row(pid)
            if datos:
                cohorte.append(datos)

        # Ordenar por urgencia: alertas primero, después por días desde última nota
        def _orden_key(r):
            n_alertas = len(r.get("alertas", []))
            dias = r.get("dias_desde_ultima_nota") or 999
            return (-n_alertas, -dias)
        cohorte.sort(key=_orden_key)
        return cohorte
    except Exception as e:
        print(f"[db_v2] get_cohorte_tr error: {e}")
        return []


def _build_cohorte_row(patient_id: int) -> Optional[Dict]:
    """Arma un row del dashboard para un paciente específico."""
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        # Datos demográficos básicos
        cur.execute("""
            SELECT id, apellido_paterno, apellido_materno, nombres,
                   fecha_nacimiento, sexo, sede_principal,
                   es_trasplantado, tr_fecha_tx, tr_donador,
                   tr_etiologia_erc, tr_grupo_sang, tr_ultima_revision,
                   id_externo
            FROM patients WHERE id = %s
        """, (patient_id,))
        pac = cur.fetchone()
        if not pac:
            cur.close()
            return None

        # Última nota Post-TR
        cur.execute("""
            SELECT id, tipo, fecha_consulta, datos_json, resumen, created_at
            FROM clinical_records
            WHERE patient_id = %s AND tipo IN %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (patient_id, TR_NOTE_TYPES))
        ult_nota = cur.fetchone()

        # Para tendencias: últimas 5 notas Post-TR
        cur.execute("""
            SELECT fecha_consulta, datos_json
            FROM clinical_records
            WHERE patient_id = %s AND tipo IN %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (patient_id, TR_NOTE_TYPES))
        ult_5_notas = cur.fetchall()
        cur.close()

        # Parsear datos_json de la última nota
        datos = {}
        if ult_nota and ult_nota.get("datos_json"):
            try:
                datos = json.loads(ult_nota["datos_json"])
            except Exception:
                datos = {}

        # Calcular edad
        from datetime import date as _date
        edad = None
        if pac.get("fecha_nacimiento"):
            try:
                hoy = _date.today()
                fn = pac["fecha_nacimiento"]
                edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            except Exception:
                pass

        # Nombre completo
        nombre = " ".join(filter(None, [
            (pac.get("nombres") or "").strip(),
            (pac.get("apellido_paterno") or "").strip(),
            (pac.get("apellido_materno") or "").strip(),
        ])).strip() or f"Paciente #{patient_id}"

        # Días desde última nota
        dias_ult = None
        if ult_nota and ult_nota.get("created_at"):
            try:
                from datetime import datetime as _dt
                ult = ult_nota["created_at"]
                if isinstance(ult, _dt):
                    dias_ult = (_dt.now() - ult).days
            except Exception:
                pass

        # DPT (días post-trasplante) — preferir el de la nota si existe
        dpt = datos.get("dpt")
        if not dpt and pac.get("tr_fecha_tx"):
            try:
                hoy = _date.today()
                fx = pac["tr_fecha_tx"]
                dpt = (hoy - fx).days
            except Exception:
                pass

        # ── ALERTAS automáticas ─────────────────────────────────────────
        alertas = []

        # 1. Cr ascendente >25%
        delta_cr = datos.get("delta_cr_pct")
        if delta_cr is not None:
            try:
                d_val = float(delta_cr)
                if d_val > 25:
                    alertas.append(f"🔴 Cr ↑{d_val:.0f}% (sospechar rechazo/CNI/BK/obstrucción)")
                elif d_val > 15:
                    alertas.append(f"🟠 Cr ↑{d_val:.0f}% (vigilar)")
            except Exception:
                pass

        # 2. Tac C0 fuera de meta según DPT
        tac_c0 = datos.get("tac_c0")
        if tac_c0 is not None and dpt is not None:
            try:
                tac_val = float(tac_c0)
                dpt_val = int(dpt)
                # Metas por tiempo (KDIGO simplificadas)
                if dpt_val <= 30:
                    meta_min, meta_max = 8, 12
                elif dpt_val <= 180:
                    meta_min, meta_max = 6, 10
                else:
                    meta_min, meta_max = 5, 8
                if tac_val < meta_min:
                    alertas.append(f"🟠 Tac C0 {tac_val} ng/mL <meta ({meta_min}-{meta_max})")
                elif tac_val > meta_max + 3:
                    alertas.append(f"🟠 Tac C0 {tac_val} ng/mL >>meta ({meta_min}-{meta_max})")
            except Exception:
                pass

        # 3. Sin nota reciente
        if dias_ult is not None:
            if dias_ult > 60:
                alertas.append(f"🟡 Sin nota desde hace {dias_ult} días")
            elif dias_ult > 30 and dpt and dpt < 180:
                alertas.append(f"🟡 Sin nota reciente ({dias_ult}d) — primer 6 meses requiere seguimiento más estrecho")

        # 4. Sin nota Post-TR pero marcado manual
        if pac.get("es_trasplantado") and not ult_nota:
            alertas.append("🔵 Marcado como TR pero sin notas — pre-TR o pendiente nota inicial")

        # Estado global
        if any(a.startswith("🔴") for a in alertas):
            estado = "critico"
        elif any(a.startswith("🟠") for a in alertas):
            estado = "alerta"
        elif any(a.startswith("🟡") for a in alertas):
            estado = "vigilar"
        else:
            estado = "estable"

        return {
            "id": patient_id,
            "nombre": nombre,
            "edad": edad,
            "sexo": pac.get("sexo"),
            "sede_principal": pac.get("sede_principal") or "—",
            "expediente": pac.get("id_externo") or "",
            "es_trasplantado_manual": bool(pac.get("es_trasplantado")),
            "tr_fecha_tx": pac.get("tr_fecha_tx") or datos.get("fecha_tx"),
            "tr_donador": pac.get("tr_donador") or datos.get("donador") or "—",
            "tr_etiologia_erc": pac.get("tr_etiologia_erc") or "—",
            "tr_grupo_sang": pac.get("tr_grupo_sang") or "—",
            "dpt": dpt,
            "cr_hoy": datos.get("cr_hoy"),
            "delta_cr_pct": delta_cr,
            "tac_c0": tac_c0,
            "patron_func": datos.get("patron_func"),
            "diuresis_24h": datos.get("diuresis_24h"),
            "area": datos.get("area"),
            "ultima_nota_id": ult_nota.get("id") if ult_nota else None,
            "ultima_nota_fecha": ult_nota.get("fecha_consulta") if ult_nota else None,
            "ultima_nota_resumen": (ult_nota.get("resumen") or "")[:200] if ult_nota else "",
            "dias_desde_ultima_nota": dias_ult,
            "ultima_revision_marcada": pac.get("tr_ultima_revision"),
            "alertas": alertas,
            "estado": estado,
            "tendencia_5_notas": _parse_tendencia(ult_5_notas),
        }
    except Exception as e:
        print(f"[db_v2] _build_cohorte_row error pid={patient_id}: {e}")
        return None


def _parse_tendencia(notas_rows) -> List[Dict]:
    """Parsea últimas 5 notas para gráficas de tendencia."""
    out = []
    for r in (notas_rows or []):
        try:
            datos = json.loads(r["datos_json"]) if r.get("datos_json") else {}
            out.append({
                "fecha": r.get("fecha_consulta"),
                "cr": datos.get("cr_hoy"),
                "tac": datos.get("tac_c0"),
                "dpt": datos.get("dpt"),
            })
        except Exception:
            continue
    return list(reversed(out))  # cronológico ascendente


def marcar_paciente_tr(patient_id: int, user_id: int, datos: Dict) -> bool:
    """Marca un paciente como trasplantado manualmente con metadata opcional."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE patients SET
              es_trasplantado = TRUE,
              tr_fecha_tx = COALESCE(%s, tr_fecha_tx),
              tr_donador = COALESCE(%s, tr_donador),
              tr_etiologia_erc = COALESCE(%s, tr_etiologia_erc),
              tr_grupo_sang = COALESCE(%s, tr_grupo_sang),
              sede_principal = COALESCE(%s, sede_principal)
            WHERE id = %s AND user_id = %s
        """, (
            datos.get("fecha_tx"),
            datos.get("donador"),
            datos.get("etiologia_erc"),
            datos.get("grupo_sang"),
            datos.get("sede_principal"),
            patient_id, user_id,
        ))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"[db_v2] marcar_paciente_tr error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def desmarcar_paciente_tr(patient_id: int, user_id: int) -> bool:
    """Quita la marca manual de TR (auto-detección sigue funcionando si tiene notas)."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE patients SET es_trasplantado = FALSE
            WHERE id = %s AND user_id = %s
        """, (patient_id, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def marcar_visita_revisada(patient_id: int, user_id: int) -> bool:
    """Marca el paciente como revisado HOY (para el dashboard)."""
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE patients SET tr_ultima_revision = NOW()
            WHERE id = %s AND user_id = %s
        """, (patient_id, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def estadisticas_cohorte_tr(user_id: int) -> Dict:
    """Estadísticas agregadas de la cohorte TR de un médico."""
    cohorte = get_cohorte_tr(user_id)
    total = len(cohorte)
    if total == 0:
        return {"total": 0, "criticos": 0, "alertas": 0, "vigilar": 0, "estables": 0,
                "por_sede": {}, "por_tiempo_post_tr": {}, "por_donador": {}}

    criticos = sum(1 for c in cohorte if c["estado"] == "critico")
    alertas = sum(1 for c in cohorte if c["estado"] == "alerta")
    vigilar = sum(1 for c in cohorte if c["estado"] == "vigilar")
    estables = sum(1 for c in cohorte if c["estado"] == "estable")

    # Por sede
    por_sede = {}
    for c in cohorte:
        s = c.get("sede_principal") or "—"
        por_sede[s] = por_sede.get(s, 0) + 1

    # Por tiempo post-TR
    por_tiempo = {"≤30 días": 0, "31-180 días": 0, "181-365 días": 0, ">1 año": 0, "Sin fecha": 0}
    for c in cohorte:
        dpt = c.get("dpt")
        if dpt is None:
            por_tiempo["Sin fecha"] += 1
        elif dpt <= 30:
            por_tiempo["≤30 días"] += 1
        elif dpt <= 180:
            por_tiempo["31-180 días"] += 1
        elif dpt <= 365:
            por_tiempo["181-365 días"] += 1
        else:
            por_tiempo[">1 año"] += 1

    # Por donador
    por_donador = {}
    for c in cohorte:
        d = (c.get("tr_donador") or "—").lower()
        if "vivo" in d:
            key = "Vivo"
        elif "cad" in d or "fallec" in d:
            key = "Fallecido"
        else:
            key = "Sin clasificar"
        por_donador[key] = por_donador.get(key, 0) + 1

    return {
        "total": total,
        "criticos": criticos,
        "alertas": alertas,
        "vigilar": vigilar,
        "estables": estables,
        "por_sede": por_sede,
        "por_tiempo_post_tr": por_tiempo,
        "por_donador": por_donador,
    }

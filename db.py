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
                peso, diagnostico, tipo, notas)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            user_id, data.get("nombre","Paciente"),
            data.get("expediente"), data.get("edad"),
            data.get("sexo"), data.get("peso"),
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
                peso=%s, diagnostico=%s, tipo=%s, notas=%s
            WHERE id=%s AND user_id=%s
        """, (
            data.get("nombre"), data.get("expediente"), data.get("edad"),
            data.get("sexo"), data.get("peso"), data.get("diagnostico"),
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

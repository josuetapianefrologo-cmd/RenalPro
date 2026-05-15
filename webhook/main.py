"""
TRRC360 Webhook Service — FastAPI para Railway
Recibe notificaciones de pago de Mercado Pago y activa suscripciones.

Deploy en Railway como servicio separado al de Streamlit.
Variables de entorno requeridas:
  - DATABASE_URL  (misma que usa la app Streamlit)
  - MP_ACCESS_TOKEN
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import psycopg2
import psycopg2.extras
import os
import mercadopago
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trrc360-webhook")

app = FastAPI(title="TRRC360 Webhook", version="1.0.0")

DATABASE_URL    = os.getenv("DATABASE_URL")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")


# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def _update_subscription(user_id: int, meses: int = 1):
    """Activa o extiende la suscripción Pro del usuario."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT subscription_end FROM users WHERE id = %s", (user_id,))
    row  = cur.fetchone()
    now  = datetime.utcnow()
    current = row["subscription_end"] if row and row["subscription_end"] else now
    new_end  = max(current, now) + timedelta(days=30 * meses)
    grace    = new_end + timedelta(days=60)
    cur.execute("""
        UPDATE users
        SET rol='pro', subscription_end=%s, grace_until=%s
        WHERE id=%s
    """, (new_end, grace, user_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"✅ Suscripción actualizada: user_id={user_id}, nueva_fin={new_end}")


def _record_payment(user_id: int, mp_payment_id: str, amount: float):
    """Registra el pago en la tabla payments."""
    conn = get_db()
    cur  = conn.cursor()
    # Evitar duplicados
    cur.execute("SELECT id FROM payments WHERE mp_payment_id=%s", (str(mp_payment_id),))
    if cur.fetchone():
        cur.close()
        conn.close()
        return
    cur.execute("""
        INSERT INTO payments (user_id, mp_payment_id, amount, status, meses)
        VALUES (%s, %s, %s, 'approved', 1)
    """, (user_id, str(mp_payment_id), amount))
    conn.commit()
    cur.close()
    conn.close()


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"service": "TRRC360 Webhook", "status": "running"}


@app.get("/health")
def health():
    """Railway usa este endpoint para health checks."""
    try:
        conn = get_db()
        conn.cursor().execute("SELECT 1")
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}


@app.post("/mp-webhook")
async def mp_webhook(request: Request):
    """
    Recibe notificaciones IPN de Mercado Pago.
    MP envía POST cada vez que hay actividad en un pago.
    """
    try:
        data = await request.json()
        logger.info(f"Webhook recibido: type={data.get('type')} action={data.get('action')}")

        if data.get("type") != "payment":
            return JSONResponse({"status": "ignored", "type": data.get("type")})

        payment_id = data["data"]["id"]

        # Verificar el pago con la API de MP
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        result  = sdk.payment().get(payment_id)
        payment = result.get("response", {})

        status = payment.get("status", "")
        logger.info(f"Pago {payment_id}: status={status}")

        if status != "approved":
            return JSONResponse({"status": "ok", "payment_status": status})

        # Extraer user_id del external_reference (formato: "user_{id}_{username}")
        ext_ref = payment.get("external_reference", "")
        parts   = ext_ref.split("_")
        if len(parts) < 2 or parts[0] != "user":
            logger.warning(f"external_reference inválido: {ext_ref}")
            return JSONResponse({"status": "ok", "warning": "ref inválida"})

        user_id = int(parts[1])
        amount  = float(payment.get("transaction_amount", 99.0))

        _record_payment(user_id, payment_id, amount)
        _update_subscription(user_id, meses=1)

        return JSONResponse({"status": "ok", "user_id": user_id, "activated": True})

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        # MP reintenta si recibe error — retornamos 200 de todas formas
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=200)


@app.post("/activate-manual")
async def activate_manual(request: Request):
    """
    Endpoint para activación manual por admin (sin pasar por MP).
    Requiere header X-Admin-Key igual a ADMIN_SECRET en env.
    """
    admin_key = os.getenv("ADMIN_SECRET", "")
    req_key   = request.headers.get("X-Admin-Key", "")
    if not admin_key or req_key != admin_key:
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    try:
        data    = await request.json()
        user_id = int(data["user_id"])
        meses   = int(data.get("meses", 1))
        _update_subscription(user_id, meses)
        return JSONResponse({"status": "ok", "user_id": user_id, "meses": meses})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

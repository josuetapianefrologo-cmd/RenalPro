"""
RenalPro — Clinical Data Loader
================================
Centraliza el acceso a los datos clínicos (rangos KDIGO, protocolos, metas)
que están en archivos JSON separados del código de la aplicación.

Ventajas de este patrón:
  ✓ Las actualizaciones médicas (nuevas guías KDIGO, ajustes de rangos)
    se hacen editando JSON, sin tocar código Python.
  ✓ El Dr. Tapia puede editar los JSONs directamente desde GitHub web.
  ✓ Cada JSON lleva su propia metadata (fuente, fecha de revisión).
  ✓ La fecha de última revisión se muestra en la UI para transparencia.

Cómo agregar nuevos datos clínicos:
  1. Crear nuevo archivo `clinical_data/<tema>.json`
  2. Incluir bloque `_meta` con tema, referencia, fecha_revision
  3. En este loader, agregar una función `get_<tema>()` que use _load_json(...)
  4. En app.py, importar y usar como diccionario normal
"""
import json
import os
from functools import lru_cache
from pathlib import Path

# Carpeta donde están los JSONs (al lado de este archivo)
_DATA_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def _load_json(filename: str) -> dict:
    """Carga un JSON con cache para evitar relecturas en cada interacción."""
    path = _DATA_DIR / filename
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # Si hay error de parseo, devuelve dict vacío para no romper la app
        # (el código que consume debe tener fallbacks defensivos)
        print(f"[clinical_data] Error cargando {filename}: {e}")
        return {}


# ── API pública ─────────────────────────────────────────────────────────────

def get_meta() -> dict:
    """Metadata global del paquete clínico (versión, fecha global)."""
    return _load_json("_meta.json")


def get_kdigo_metas() -> dict:
    """Metas KDIGO post-trasplante: Tac C0, Cr, electrolitos, balance."""
    return _load_json("kdigo_metas.json")


def get_protocolos_iv() -> dict:
    """Protocolos de infusiones IV: gluconato Ca, etc."""
    return _load_json("protocolos_iv.json")


# ── Atajos de uso frecuente (para no tener que navegar dict anidados) ────────

def get_tac_c0_metas() -> list:
    """Lista de metas de Tacrolimus C0 por fase post-TX."""
    return get_kdigo_metas().get("tacrolimus_c0", {}).get("metas_por_fase", [])


def get_gluconato_ca_iv() -> dict:
    """Protocolo de gluconato de calcio IV completo."""
    return get_protocolos_iv().get("gluconato_calcio_iv", {})


def get_revision_info(tema: str) -> dict:
    """
    Devuelve la metadata de revisión de un tema específico.
    Útil para mostrar en la UI: 'Última revisión: 2026-05-23 · Fuente: KDIGO 2024'
    """
    map_temas = {
        "kdigo": get_kdigo_metas(),
        "protocolos_iv": get_protocolos_iv(),
    }
    data = map_temas.get(tema, {})
    return data.get("_meta", {})


def format_revision_caption(tema: str) -> str:
    """Genera un caption corto para Streamlit mostrando origen y fecha de revisión."""
    meta = get_revision_info(tema)
    if not meta:
        return ""
    parts = []
    if meta.get("referencia"):
        parts.append(meta["referencia"])
    if meta.get("fecha_revision"):
        parts.append(f"Revisado {meta['fecha_revision']}")
    return " · ".join(parts) if parts else ""


# ── Helpers para uso directo en el código ────────────────────────────────────

def tac_c0_evaluar(c0: float, dias_post_tx: int = 30) -> dict:
    """
    Dado un nivel de Tac C0 y los días post-TX, devuelve:
      - {'estado': 'meta'|'subterapeutico'|'supraterapeutico'|'toxico',
         'fase': nombre de la fase,
         'meta_min', 'meta_max',
         'color': 'verde'|'amarillo'|'rojo',
         'recomendacion': str}
    """
    fases = get_tac_c0_metas()
    if not fases:
        return {}

    # Seleccionar fase según días post-TX
    if dias_post_tx <= 30:
        fase = fases[0] if len(fases) > 0 else {}
    elif dias_post_tx <= 180:
        fase = fases[1] if len(fases) > 1 else fases[-1]
    else:
        fase = fases[-1]

    meta_min = fase.get("min", 0)
    meta_max = fase.get("max", 99)
    tac_data = get_kdigo_metas().get("tacrolimus_c0", {})
    toxico = tac_data.get("umbral_toxico", 15)
    sub_thresh = tac_data.get("umbral_subterapeutico", 6)

    if c0 > toxico:
        estado, color = "toxico", "rojo"
        rec = tac_data.get("ajustes_dosis", {}).get("toxico", "")
    elif c0 < sub_thresh:
        estado, color = "subterapeutico", "amarillo"
        rec = tac_data.get("ajustes_dosis", {}).get("subterapeutico", "")
    elif meta_min <= c0 <= meta_max:
        estado, color = "meta", "verde"
        rec = "En meta terapéutica — continuar dosis actual"
    elif c0 > meta_max:
        estado, color = "supraterapeutico", "amarillo"
        rec = tac_data.get("ajustes_dosis", {}).get("supraterapeutico_leve", "")
    else:
        estado, color = "subterapeutico", "amarillo"
        rec = tac_data.get("ajustes_dosis", {}).get("subterapeutico", "")

    return {
        "estado": estado,
        "fase": fase.get("fase", ""),
        "meta_min": meta_min,
        "meta_max": meta_max,
        "color": color,
        "recomendacion": rec,
    }

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
    """
    Carga un JSON con cache para evitar relecturas en cada interacción.
    Soporta subdirectorios: pasar 'educacion/casos_clinicos.json'.
    """
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
    # Soportar tanto "referencia" (singular string) como "referencias" (lista)
    if meta.get("referencia"):
        parts.append(meta["referencia"])
    elif meta.get("referencias"):
        refs = meta["referencias"]
        if isinstance(refs, list):
            parts.append(" · ".join(refs))
        else:
            parts.append(str(refs))
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


# ════════════════════════════════════════════════════════════════════════════
# EDUCACIÓN TR — Contenido pedagógico para fellow de trasplante
# ════════════════════════════════════════════════════════════════════════════

def get_casos_clinicos() -> dict:
    """Casos clínicos didácticos con razonamiento paso a paso."""
    return _load_json("educacion/casos_clinicos.json")


def get_banco_preguntas() -> dict:
    """Banco de preguntas tipo board con explicación."""
    return _load_json("educacion/banco_preguntas.json")


def get_fisiopatologia() -> dict:
    """Fisiopatología expandida — el porqué de cada tema clave."""
    return _load_json("educacion/fisiopatologia.json")


def get_tablas_comparativas() -> dict:
    """Tablas comparativas para diferenciar entidades similares."""
    return _load_json("educacion/tablas_comparativas.json")


def get_referencias_clave() -> dict:
    """Referencias clave — RCTs históricos y modernos."""
    return _load_json("educacion/referencias_clave.json")


def get_controversias() -> dict:
    """Controversias en TR — donde no hay consenso pleno."""
    return _load_json("educacion/controversias.json")


# ── Atajos de acceso rápido a contenido educativo ────────────────────────────

def get_lista_casos() -> list:
    """Lista de casos clínicos disponibles (solo metadata para selector UI)."""
    data = get_casos_clinicos()
    return data.get("casos", [])


def get_lista_preguntas() -> list:
    """Lista de preguntas del banco (para selector y autoevaluación)."""
    data = get_banco_preguntas()
    return data.get("preguntas", [])


def get_lista_temas_fisiopatologia() -> list:
    """Lista de temas de fisiopatología expandida."""
    data = get_fisiopatologia()
    return data.get("temas", [])


def get_lista_tablas() -> list:
    """Lista de tablas comparativas."""
    data = get_tablas_comparativas()
    return data.get("tablas", [])


def get_lista_referencias() -> list:
    """Lista de categorías de referencias clave."""
    data = get_referencias_clave()
    return data.get("categorias", [])


def get_lista_controversias() -> list:
    """Lista de controversias en TR."""
    data = get_controversias()
    return data.get("controversias", [])

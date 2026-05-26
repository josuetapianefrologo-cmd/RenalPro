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


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD TR — Configuración editable (umbrales, sedes, mensajes)
# ════════════════════════════════════════════════════════════════════════════

# Valores por defecto (fallback si el JSON falla o falta una clave)
_DASHBOARD_TR_DEFAULTS = {
    "tr_note_types": [
        "Nota evolución Post-TR",
        "Trasplante / Nota inicial post-TR",
    ],
    "tac_metas_por_dpt": [
        {"dpt_min": 0, "dpt_max": 30, "meta_min": 8, "meta_max": 12, "label": "Primer mes"},
        {"dpt_min": 31, "dpt_max": 180, "meta_min": 6, "meta_max": 10, "label": "1-6 meses"},
        {"dpt_min": 181, "dpt_max": 99999, "meta_min": 5, "meta_max": 8, "label": ">6 meses"},
    ],
    "umbrales_cr": {"critico_delta_pct": 25, "alerta_delta_pct": 15},
    "tac_alto_margen_extra": 3,
    "umbrales_sin_nota": {"primer_6m_dias": 30, "despues_6m_dias": 60},
    "sedes": [
        "UMAE Bajío N1", "Hospital General León",
        "Clínica Alba Diálisis y Trasplantes", "Clínica San Juan Diego", "Otra",
    ],
    "donadores": ["Vivo relacionado", "Vivo no relacionado", "Fallecido DBD", "Fallecido DCD"],
    "grupos_sanguineos": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
    "tiempo_post_tr_categorias": [
        {"label": "≤30 días", "min": 0, "max": 30},
        {"label": "31-180 días", "min": 31, "max": 180},
        {"label": "181-365 días", "min": 181, "max": 365},
        {"label": ">1 año", "min": 366, "max": 99999},
    ],
    "alertas_mensajes": {
        "cr_critico": "🔴 Cr ↑{delta:.0f}% (sospechar rechazo/CNI/BK/obstrucción)",
        "cr_alerta": "🟠 Cr ↑{delta:.0f}% (vigilar)",
        "tac_bajo": "🟠 Tac C0 {tac} ng/mL <meta ({min}-{max})",
        "tac_alto": "🟠 Tac C0 {tac} ng/mL >>meta ({min}-{max})",
        "sin_nota_largo": "🟡 Sin nota desde hace {dias} días",
        "sin_nota_primer_6m": "🟡 Sin nota reciente ({dias}d) — primer 6 meses requiere seguimiento más estrecho",
        "marcado_sin_nota": "🔵 Marcado como TR pero sin notas — pre-TR o pendiente nota inicial",
    },
}


def _validar_dashboard_config(cfg: dict) -> dict:
    """
    Valida config del dashboard y rellena con defaults las claves faltantes.
    Garantiza que el dashboard NUNCA se rompa por un JSON mal formado.
    """
    if not isinstance(cfg, dict):
        return _DASHBOARD_TR_DEFAULTS.copy()
    out = {}
    # Para cada clave en defaults, usar la del usuario si existe Y es válida
    for k, default_val in _DASHBOARD_TR_DEFAULTS.items():
        user_val = cfg.get(k)
        if user_val is None:
            out[k] = default_val
        elif isinstance(default_val, list) and not isinstance(user_val, list):
            out[k] = default_val
        elif isinstance(default_val, dict) and not isinstance(user_val, dict):
            out[k] = default_val
        else:
            out[k] = user_val
    # Validación adicional: tac_metas debe tener al menos un rango
    if not out.get("tac_metas_por_dpt"):
        out["tac_metas_por_dpt"] = _DASHBOARD_TR_DEFAULTS["tac_metas_por_dpt"]
    return out


def get_dashboard_tr_config() -> dict:
    """
    Configuración del Dashboard TR (umbrales, sedes, mensajes).
    Lee de dashboard_tr_config.json con fallback defensivo a defaults.
    """
    raw = _load_json("dashboard_tr_config.json")
    return _validar_dashboard_config(raw)


def tac_meta_por_dpt(dpt: int) -> tuple:
    """
    Devuelve (meta_min, meta_max, label) para un DPT dado.
    Lee config del JSON. Si no hay match, devuelve último rango configurado.
    """
    cfg = get_dashboard_tr_config()
    metas = cfg.get("tac_metas_por_dpt") or _DASHBOARD_TR_DEFAULTS["tac_metas_por_dpt"]
    for rango in metas:
        try:
            if int(rango.get("dpt_min", 0)) <= int(dpt) <= int(rango.get("dpt_max", 99999)):
                return (
                    float(rango.get("meta_min", 5)),
                    float(rango.get("meta_max", 10)),
                    str(rango.get("label", "")),
                )
        except (ValueError, TypeError):
            continue
    # Fallback: último rango
    ultimo = metas[-1]
    return (
        float(ultimo.get("meta_min", 5)),
        float(ultimo.get("meta_max", 10)),
        str(ultimo.get("label", "")),
    )

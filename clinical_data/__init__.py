"""
RenalPro Clinical Data Package
===============================
Datos clínicos centralizados (rangos KDIGO, protocolos, metas terapéuticas,
contenido educativo) en archivos JSON editables sin tocar código Python.
"""
from .loader import (
    # Núcleo clínico (existente)
    get_meta,
    get_kdigo_metas,
    get_protocolos_iv,
    get_tac_c0_metas,
    get_gluconato_ca_iv,
    get_revision_info,
    format_revision_caption,
    tac_c0_evaluar,
    # Educación TR (nuevo)
    get_casos_clinicos,
    get_banco_preguntas,
    get_fisiopatologia,
    get_tablas_comparativas,
    get_referencias_clave,
    get_controversias,
    get_lista_casos,
    get_lista_preguntas,
    get_lista_temas_fisiopatologia,
    get_lista_tablas,
    get_lista_referencias,
    get_lista_controversias,
)

__all__ = [
    # Núcleo clínico
    "get_meta",
    "get_kdigo_metas",
    "get_protocolos_iv",
    "get_tac_c0_metas",
    "get_gluconato_ca_iv",
    "get_revision_info",
    "format_revision_caption",
    "tac_c0_evaluar",
    # Educación TR
    "get_casos_clinicos",
    "get_banco_preguntas",
    "get_fisiopatologia",
    "get_tablas_comparativas",
    "get_referencias_clave",
    "get_controversias",
    "get_lista_casos",
    "get_lista_preguntas",
    "get_lista_temas_fisiopatologia",
    "get_lista_tablas",
    "get_lista_referencias",
    "get_lista_controversias",
]

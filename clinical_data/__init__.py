"""
RenalPro Clinical Data Package
===============================
Datos clínicos centralizados (rangos KDIGO, protocolos, metas terapéuticas)
en archivos JSON editables sin tocar código Python.
"""
from .loader import (
    get_meta,
    get_kdigo_metas,
    get_protocolos_iv,
    get_tac_c0_metas,
    get_gluconato_ca_iv,
    get_revision_info,
    format_revision_caption,
    tac_c0_evaluar,
)

__all__ = [
    "get_meta",
    "get_kdigo_metas",
    "get_protocolos_iv",
    "get_tac_c0_metas",
    "get_gluconato_ca_iv",
    "get_revision_info",
    "format_revision_caption",
    "tac_c0_evaluar",
]

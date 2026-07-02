"""
RenalPro (TRRC360) — Extensión de Prescripción CRRT: Selector por caso clínico
==============================================================================
Amplía la prescripción CRRT con:
  - Selector por caso clínico (intoxicaciones, sepsis/citoquinas, rabdomiólisis,
    electrolitos) → modalidad recomendada + razón + membrana + filtro a EVITAR.
  - Visualizador de aclaramiento por peso molecular (difusión/convección/adsorción).
  - Tabla de pesos moleculares de solutos, toxinas y fármacos.
  - Advertencias de membrana (qué NO usar y por qué).
  - Personalización básica de la prescripción.

Integración (dentro de la página de Prescripción CRRT existente):
    from renalpro_crrt_casos import render_selector_caso
    # agregar una pestaña y llamar render_selector_caso()

Base de evidencia (validar/citar): EXTRIP workgroup (litio, metformina,
salicilatos, valproato); literatura de reacción anafilactoide AN69+IECA
(bradicinina). Herramienta de APOYO; no sustituye el juicio clínico.

Autor: Josué Tapia Nefrólogo — Tapia Nefrología
"""

import streamlit as st
import numpy as np
import pandas as pd

try:
    import altair as alt
    _ALTAIR = True
except ImportError:
    _ALTAIR = False


# ---------------------------------------------------------------------------
# Tabla de pesos moleculares
# ---------------------------------------------------------------------------
# categoria: pequeña (<500 Da) · mediana (500–15,000 Da) · grande (>15,000 Da)
PESOS_MOLECULARES = [
    # nombre, PM (Da), categoría, unión proteica, nota
    ("Potasio (K+)", 39, "pequeña", "no", "Difusión muy eficaz"),
    ("Litio (Li+)", 7, "pequeña", "no", "Vd bajo → muy dializable; ojo rebote"),
    ("Urea", 60, "pequeña", "no", "Marcador de aclaramiento de pequeñas"),
    ("Metanol", 32, "pequeña", "no", "Muy dializable"),
    ("Etilenglicol", 62, "pequeña", "no", "Muy dializable"),
    ("Fosfato", 96, "pequeña", "no", "Puede requerir reposición en CRRT prolongada"),
    ("Creatinina", 113, "pequeña", "no", "Marcador clásico"),
    ("Metformina", 129, "pequeña", "no", "Dializable; ECTR corrige acidosis (MALA)"),
    ("Salicilato", 138, "pequeña", "media", "Dializable; HD aporta bicarbonato"),
    ("Ácido valproico", 144, "pequeña", "alta*", "*Saturable: ↑ fracción libre en sobredosis"),
    ("Vancomicina", 1449, "mediana", "media", "Se remueve por convección/alto flujo"),
    ("β2-microglobulina", 11800, "mediana", "no", "Molécula media clásica"),
    ("Mioglobina", 17000, "mediana", "no", "Rabdomiólisis; mejor por convección/HCO"),
    ("TNF-α (monómero)", 17000, "mediana", "no", "Citoquina; remoción sin beneficio probado"),
    ("Interleucina-6", 21000, "mediana", "no", "Citoquina; remoción sin beneficio probado"),
    ("Cadenas ligeras κ", 22500, "grande", "no", "Mieloma; requiere HCO"),
    ("Cadenas ligeras λ (dímero)", 45000, "grande", "no", "Requiere HCO"),
    ("Albúmina", 66000, "grande", "—", "NO debe removerse (pérdida indeseada)"),
]


# ---------------------------------------------------------------------------
# Biblioteca de casos clínicos
# ---------------------------------------------------------------------------
CASOS = {
    "Intoxicación por litio": dict(
        grupo="Intoxicación",
        molecula="Litio (~7 Da, sin unión proteica, Vd bajo)",
        modalidad="HD intermitente de 1ª línea (remoción rápida). CRRT "
                  "(CVVHD/CVVHDF) para PREVENIR REBOTE o si hay inestabilidad.",
        razon="Molécula pequeña y no unida a proteínas → altamente dializable "
              "(EXTRIP nivel A). Redistribuye desde el intracelular → riesgo de "
              "rebote tras HD; la CRRT continua lo controla.",
        dosis="Estándar 20-25 mL/kg/h; prolongar para cubrir el rebote.",
        membrana="Alto flujo estándar.",
        anticoag="Citrato regional (preferido) o heparina.",
        evitar="AN69 + IECA (bradicinina).",
        evitar_por="La AN69 (electronegativa) genera bradicinina y el IECA "
                   "bloquea su degradación → reacción anafilactoide.",
    ),
    "Intoxicación por metformina (MALA)": dict(
        grupo="Intoxicación",
        molecula="Metformina (129 Da, sin unión proteica)",
        modalidad="HD intermitente preferida; CVVHDF prolongada si hay "
                  "inestabilidad hemodinámica (frecuente en MALA con choque).",
        razon="Moderadamente dializable (EXTRIP). El ECTR remueve metformina y "
              "CORRIGE la acidosis láctica. Vigilar rebote por liberación tisular.",
        dosis="20-25 mL/kg/h; considerar dosis mayor si acidosis grave.",
        membrana="Alto flujo estándar.",
        anticoag="Citrato regional (cuidado si acidosis/hipoperfusión hepática).",
        evitar="AN69 + IECA (bradicinina).",
        evitar_por="Mismo mecanismo bradicinina; además muchos son cardiópatas "
                   "con IECA.",
    ),
    "Intoxicación por salicilatos": dict(
        grupo="Intoxicación",
        molecula="Salicilato (138 Da, unión proteica saturable)",
        modalidad="HD intermitente preferida (la más eficiente). CRRT solo si HD "
                  "no es posible o hay inestabilidad.",
        razon="Dializable (EXTRIP). La HD además aporta bicarbonato. La "
              "alcalinización urinaria es coadyuvante, no sustituye al ECTR "
              "en casos graves.",
        dosis="Máxima eficiencia; en CRRT usar dosis alta.",
        membrana="Alto flujo estándar.",
        anticoag="Según sangrado; citrato o heparina.",
        evitar="AN69 + IECA.",
        evitar_por="Bradicinina/reacción anafilactoide.",
    ),
    "Intoxicación por valproato": dict(
        grupo="Intoxicación",
        molecula="Ácido valproico (144 Da, unión proteica ALTA pero SATURABLE)",
        modalidad="HD intermitente preferida. Si no está disponible: "
                  "hemoperfusión o CRRT (2D).",
        razon="Moderadamente dializable: en sobredosis se satura la unión a "
              "proteínas y aumenta la fracción libre → más dializable de lo "
              "esperado. Considerar L-carnitina para la hiperamonemia.",
        dosis="Alta eficiencia; suspender al mejorar o VPA 50-100 mg/L.",
        membrana="Alto flujo estándar.",
        anticoag="Según sangrado.",
        evitar="AN69 + IECA.",
        evitar_por="Bradicinina/reacción anafilactoide.",
    ),
    "Intoxicación por metanol/etilenglicol": dict(
        grupo="Intoxicación",
        molecula="Metanol (32 Da) / Etilenglicol (62 Da)",
        modalidad="HD intermitente de 1ª línea; CRRT alternativa si inestable.",
        razon="Muy pequeñas y no unidas a proteínas → altamente dializables. "
              "Combinar con fomepizol/etanol y bicarbonato. Remueve también los "
              "metabolitos tóxicos (glicólico/fórmico).",
        dosis="Máxima eficiencia.",
        membrana="Alto flujo estándar.",
        anticoag="Según sangrado.",
        evitar="AN69 + IECA.",
        evitar_por="Bradicinina/reacción anafilactoide.",
    ),
    "Sepsis / choque séptico": dict(
        grupo="Sepsis / citoquinas",
        molecula="Citoquinas medianas (TNF-α ~17 kDa, IL-6 ~21 kDa)",
        modalidad="CRRT indicada por LRA, NO para 'limpiar citoquinas'. Si se "
                  "busca inmunomodulación: convección (CVVH) o adsorción "
                  "(oXiris/AN69ST); evidencia limitada.",
        razon="La remoción de citoquinas NO ha demostrado mejorar mortalidad "
              "(p. ej. alto volumen, IVOIRE negativo). No es estándar de cuidado.",
        dosis="20-25 mL/kg/h (el alto volumen no mejora desenlaces).",
        membrana="Estándar; oXiris/HCO solo en contextos seleccionados.",
        anticoag="Citrato regional preferido.",
        evitar="Adsorción/HCO sin ajustar antibióticos; AN69 + IECA.",
        evitar_por="Las membranas adsortivas/alto poro remueven antibióticos y "
                   "albúmina de forma impredecible → infradosificación.",
    ),
    "Rabdomiólisis / mioglobinuria": dict(
        grupo="Rabdomiólisis",
        molecula="Mioglobina (~17 kDa, molécula mediana)",
        modalidad="CRRT indicada por LRA/hiperK/acidosis. Para remover "
                  "mioglobina: convección (CVVH) o membrana de alto poro (HCO).",
        razon="La CRRT convencional depura mal la mioglobina; convección y HCO "
              "mejoran la remoción, pero SIN beneficio en mortalidad probado. "
              "La base sigue siendo hidratación agresiva.",
        dosis="20-25 mL/kg/h; mayor si se prioriza remoción de mioglobina.",
        membrana="Alto poro (HCO) o alto flujo con convección.",
        anticoag="Citrato regional.",
        evitar="AN69 + IECA; HCO sin vigilar albúmina/antibióticos.",
        evitar_por="Pérdida de albúmina y remoción de fármacos con HCO.",
    ),
    "Hiperkalemia grave con LRA": dict(
        grupo="Electrolitos",
        molecula="Potasio (39 Da)",
        modalidad="Difusión (CVVHD) muy eficaz; corrección GRADUAL.",
        razon="El K+ es pequeño → se depura muy bien por difusión. Evitar "
              "corrección demasiado rápida (arritmias).",
        dosis="20-25 mL/kg/h; ajustar K+ del líquido para descenso controlado.",
        membrana="Alto flujo estándar.",
        anticoag="Citrato regional.",
        evitar="AN69 + IECA.",
        evitar_por="Bradicinina/reacción anafilactoide.",
    ),
    "Síndrome de lisis tumoral": dict(
        grupo="Electrolitos",
        molecula="Ácido úrico, fósforo, potasio (pequeños)",
        modalidad="CRRT continua: control sostenido de la carga metabólica.",
        razon="La producción continua de solutos favorece la terapia continua "
              "sobre la intermitente para evitar rebotes.",
        dosis="Dosis estándar-alta según carga.",
        membrana="Alto flujo estándar.",
        anticoag="Citrato regional.",
        evitar="AN69 + IECA.",
        evitar_por="Bradicinina/reacción anafilactoide.",
    ),
    "Disnatremias (corrección lenta)": dict(
        grupo="Electrolitos",
        molecula="Sodio (23 Da)",
        modalidad="CRRT continua: control FINO del sodio (ajustando el líquido).",
        razon="Ventaja de la CRRT: permite corregir Na+ lentamente y evitar "
              "edema cerebral (hipernatremia) o desmielinización osmótica "
              "(hiponatremia).",
        dosis="Ajustar Na+ del líquido para ≤ 6-8 mEq/L/24 h.",
        membrana="Alto flujo estándar.",
        anticoag="Citrato regional.",
        evitar="AN69 + IECA.",
        evitar_por="Bradicinina/reacción anafilactoide.",
    ),
}


ADVERTENCIAS_FILTRO = [
    ("AN69 (no recubierta) + IECA",
     "Reacción anafilactoide por bradicinina: la membrana electronegativa la "
     "genera y el IECA bloquea su degradación. Evitar la combinación; usar otra "
     "membrana o suspender el IECA. La AN69ST (recubierta) reduce el riesgo."),
    ("AN69 en acidemia marcada",
     "El medio ácido potencia la liberación de bradicinina."),
    ("Membranas de alto poro (HCO) / adsortivas (oXiris)",
     "Pérdida de albúmina y remoción IMPREDECIBLE de antibióticos → riesgo de "
     "infradosificación. Vigilar niveles y ajustar dosis."),
    ("Membranas adsortivas (saturación)",
     "Se saturan con el tiempo → requieren recambio periódico para mantener el "
     "efecto."),
    ("Esterilización con óxido de etileno",
     "Puede causar hipersensibilidad en pacientes sensibilizados."),
]


# ---------------------------------------------------------------------------
# Visualizador de aclaramiento por peso molecular
# ---------------------------------------------------------------------------
def curva_aclaramiento(mecanismo, n=220):
    mw = np.logspace(1, 5, n)               # 10 Da → 100 kDa
    cutoff, steep = {"Difusión": (1500, 1.6),
                     "Convección": (22000, 2.6),
                     "Adsorción / HCO": (48000, 3.2)}[mecanismo]
    eff = 1.0 / (1.0 + (mw / cutoff) ** steep)
    return mw, eff * 100


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def _tab_caso():
    st.subheader("🧭 Selector por caso clínico")
    caso = st.selectbox("Escenario clínico", list(CASOS.keys()))
    c = CASOS[caso]

    st.markdown(f"**Molécula objetivo:** {c['molecula']}")
    st.success(f"**Modalidad recomendada:** {c['modalidad']}")
    st.markdown(f"**¿Por qué?** {c['razon']}")

    col1, col2 = st.columns(2)
    col1.markdown(f"**Dosis:** {c['dosis']}")
    col1.markdown(f"**Membrana:** {c['membrana']}")
    col2.markdown(f"**Anticoagulación:** {c['anticoag']}")

    st.error(f"**Filtro/terapia a EVITAR:** {c['evitar']}\n\n"
             f"**Por qué:** {c['evitar_por']}")

    st.caption("Apoyo a la decisión. En intoxicaciones dializables, la HD "
               "intermitente suele ser la más eficiente; la CRRT se elige por "
               "inestabilidad o para prevenir rebote.")


def _tab_aclaramiento():
    st.subheader("📉 Aclaramiento según peso molecular")
    st.caption("Cómo cae la eficiencia de remoción al aumentar el peso "
               "molecular, según el mecanismo. (Esquema didáctico.)")

    if _ALTAIR:
        dfs = []
        for mec in ("Difusión", "Convección", "Adsorción / HCO"):
            mw, eff = curva_aclaramiento(mec)
            dfs.append(pd.DataFrame({"PesoMolecular": mw, "Eficiencia": eff,
                                     "Mecanismo": mec}))
        df = pd.concat(dfs, ignore_index=True)
        linea = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
            x=alt.X("PesoMolecular:Q", scale=alt.Scale(type="log"),
                    title="Peso molecular (Da, escala log)"),
            y=alt.Y("Eficiencia:Q", title="Eficiencia de remoción (%)"),
            color=alt.Color("Mecanismo:N", legend=alt.Legend(orient="top", title=None)),
        )
        marcadores = pd.DataFrame([
            {"PesoMolecular": 60, "Eficiencia": 5, "sol": "Urea"},
            {"PesoMolecular": 1449, "Eficiencia": 5, "sol": "Vancomicina"},
            {"PesoMolecular": 17000, "Eficiencia": 5, "sol": "Mioglobina"},
            {"PesoMolecular": 66000, "Eficiencia": 5, "sol": "Albúmina"},
        ])
        pts = alt.Chart(marcadores).mark_rule(color="#94A3B8",
                                              strokeDash=[2, 2]).encode(
            x="PesoMolecular:Q")
        txt = alt.Chart(marcadores).mark_text(angle=270, dx=8, dy=0,
                                              color="#64748B", fontSize=10).encode(
            x="PesoMolecular:Q", y=alt.value(20), text="sol:N")
        st.altair_chart((linea + pts + txt).properties(height=320),
                        use_container_width=True)
    else:
        mw, e_dif = curva_aclaramiento("Difusión")
        _, e_con = curva_aclaramiento("Convección")
        _, e_ads = curva_aclaramiento("Adsorción / HCO")
        st.line_chart(pd.DataFrame({"Difusión": e_dif, "Convección": e_con,
                                    "Adsorción/HCO": e_ads}, index=mw.round(0)))

    st.markdown(
        "- **Difusión (CVVHD):** máxima para **pequeñas** (urea, K, litio, "
        "tóxicos); cae pronto con el tamaño.\n"
        "- **Convección (CVVH):** mantiene remoción de **medianas** "
        "(vancomicina, mioglobina, citoquinas).\n"
        "- **Adsorción / alto poro (HCO, oXiris):** alcanza **grandes**, pero "
        "con riesgo de perder albúmina y fármacos."
    )


def _tab_pesos():
    st.subheader("⚖️ Tabla de pesos moleculares")
    df = pd.DataFrame(PESOS_MOLECULARES,
                      columns=["Soluto", "PM (Da)", "Categoría",
                               "Unión proteica", "Nota"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("Categoría: pequeña < 500 Da · mediana 500–15,000 Da · "
               "grande > 15,000 Da. La dializabilidad depende también de la "
               "unión a proteínas y el volumen de distribución.")


def _tab_filtros():
    st.subheader("⛔ Membranas: qué NO usar y por qué")
    for titulo, motivo in ADVERTENCIAS_FILTRO:
        with st.expander(f"⚠️ {titulo}"):
            st.markdown(motivo)
    st.caption("Referencia: literatura de reacción anafilactoide AN69+IECA "
               "(bradicinina). Herramienta de apoyo, no sustituye el juicio "
               "clínico ni la ficha técnica de cada membrana.")


def render_selector_caso():
    """Punto de entrada. Llamar dentro de la página de Prescripción CRRT."""
    st.markdown("### 🧪 CRRT según el caso clínico")
    st.caption("Apoyo a la decisión. Los parámetros (peso, dosis, Qb, filtro) "
               "se ajustan abajo en tu prescripción.")
    tabs = st.tabs(["🧭 Por caso", "📉 Aclaramiento", "⚖️ Pesos moleculares",
                    "⛔ Filtros a evitar"])
    with tabs[0]:
        _tab_caso()
    with tabs[1]:
        _tab_aclaramiento()
    with tabs[2]:
        _tab_pesos()
    with tabs[3]:
        _tab_filtros()


if __name__ == "__main__":
    st.set_page_config(page_title="CRRT por caso — RenalPro", page_icon="🧪",
                       layout="wide")
    render_selector_caso()

# app.py — TRRC360 by Dr. Tapia (v1.8.0)
    ca.metric("Qb (mL/min)", qb); cb.metric("Qp (mL/min)", int(qp))
    cc.metric("Qe (mL/h)", int(qe)); cd.metric("UF (mL/h)", uf)
    ce, cf, cg = st.columns(3)
    ce.metric("Qr pre (mL/h)", qr_pre); cf.metric("Qr post (mL/h)", qr_post); cg.metric("Qd (mL/h)", int(qd))
    st.info(comentarios or "—")

    # Anticoagulación (resumen)
    st.markdown("### Anticoagulación (resumen)")
    ac_tipo = st.session_state.get("anticoagulacion_tipo", "—")
    if ac_tipo == "HNF":
        st.write(f"**Tipo:** HNF  |  **Dosis inicial sugerida:** {int(st.session_state.get('hnf_ui_h', max(1,int(peso*5))))} UI/h (ajustar a aPTT)")
    elif ac_tipo == "RCA":
        rca_cit = st.session_state.get("rca_citrato_ml_h", None)
        rca_ca  = st.session_state.get("rca_calcio_ml_h", None)
        r_targets = st.session_state.get("rca_targets", {})
        st.write("**Tipo:** RCA")
        st.write(f"**Citrato inicial:** {int(rca_cit) if rca_cit else '—'} mL/h  |  **Calcio inicial:** {int(rca_ca) if rca_ca else '—'} mL/h")
        st.write(f"**Dianas:** iCa post-filtro {r_targets.get('iCa_post','—')} mmol/L · iCa sistémico {r_targets.get('iCa_sist','—')} mmol/L (ajustes 10–20%)")
        st.caption("Monitorizar iCa a 30–60 min y luego cada 4–6 h; vigilar Na, HCO₃⁻, pH y anión gap.")
    else:
        st.write("—")

    # Comentarios para exportar
    st.text_area("Comentarios para el PDF", key="rx_comentarios", value=st.session_state.get("rx_comentarios",""), height=120)

    # Opciones de PDF (ligadas al switch global)
    st.markdown("### Opciones de PDF")
    st.caption("El PDF extendido se controla con el switch global en la barra lateral.")
    st.write(f"PDF extendido: **{'Sí' if st.session_state.get('pdf_extendido', False) else 'No'}**")

    # Botón Exportar a PDF
    col_btn,_ = st.columns([1,3])
    with col_btn:
        if st.button("Exportar a PDF", key="btn_export_pdf"):
            try:
                fn = export_pdf()
                with open(fn, "rb") as f:
                    st.download_button("Descargar PDF", data=f, file_name=fn, mime="application/pdf",
                                       use_container_width=True, key="btn_download_pdf")
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

# ---------- Referencias (pestaña nueva) ----------
with tab_refs:
    st.subheader("Referencias (filtradas por tu contexto)")
    escenarios_sel = st.session_state.get("sb_escenarios", [])
    anticoag_tipo = st.session_state.get("anticoagulacion_tipo", "—")

    colf1, colf2 = st.columns([2,1])
    query = colf1.text_input("Buscar en títulos/resumen (opcional)", "")
    solo_contexto = colf2.checkbox("Solo relevantes al contexto actual", value=True)

    refs = filtrar_refs_por_contexto(escenarios_sel, anticoag_tipo) if solo_contexto else BIBLIO

    if query.strip():
        ql = query.lower()
        refs = [r for r in refs if ql in r["title"].lower() or ql in r["blurb"].lower() or ql in r["where"].lower()]

    if not refs:
        st.info("No hay referencias que coincidan. Ajusta filtros o añade más términos.")
    else:
        for i, r in enumerate(refs, 1):
            st.markdown(f"**[{i}] {r['title']}**  \n*{r['where']}* ({r['yr']}) — {r['blurb']}  \n[Ver fuente]({r['url']})")
            st.markdown("---")

    st.caption("Las referencias se actualizan al cambiar escenarios, anticoagulación o parámetros clave.")

# Pie
st.caption("© Tapia Nefrología — Uso académico | TRRC360 by Dr. Tapia")

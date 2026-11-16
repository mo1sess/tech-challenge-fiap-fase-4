"""Apresentação de resultados persistidos, inclusive jobs anteriores à evolução."""
import streamlit as st

STATUS = {"completed": "Concluída", "partial": "Parcial", "error": "Erro no serviço",
          "not_configured": "Não configurada", "empty_text": "Texto vazio",
          "disabled": "Desabilitada", "model_unavailable": "Modelo local indisponível",
          "dependency_unavailable": "Dependência não instalada", "no_pose": "Nenhuma pose identificável"}


def render_job_report(job):
    analysis = (job.get("result") or {}).get("analysis") or {}
    if not analysis:
        st.info("Job sem relatório de análise disponível.")
        return
    st.caption(f"Job {job['id']} · {job.get('status')} · {job.get('created_at', '')}")
    if job.get("job_type") == "audio_analysis":
        st.markdown("**Transcrição**")
        st.write((analysis.get("transcription") or {}).get("text") or "Sem fala reconhecida")
        language = analysis.get("azure_language") or {}
        st.markdown("**Azure AI Language**")
        st.write(STATUS.get(language.get("status"), "Sem análise Azure neste job histórico"))
        sentiment = language.get("sentiment") or {}
        if sentiment:
            st.write({"positive": "Positivo", "negative": "Negativo", "neutral": "Neutro", "mixed": "Misto"}.get(sentiment.get("label"), sentiment.get("label")))
            st.dataframe([sentiment.get("confidence_scores", {})], width="stretch", hide_index=True)
        if language.get("entities"):
            st.dataframe(language["entities"], width="stretch", hide_index=True)
        st.caption(language.get("disclaimer", ""))
        st.markdown("**Expressões demonstrativas e contexto local**")
        st.dataframe((analysis.get("text_analysis") or {}).get("findings", []), width="stretch", hide_index=True)
        acoustic = analysis.get("acoustic") or {}
        st.markdown("**Métricas acústicas observáveis**")
        names = {"duration_seconds": "Duração (s)", "rms": "RMS", "peak_amplitude": "Pico", "silence_ratio": "Proporção de silêncio", "clipping_ratio": "Clipping", "intensity_std": "Desvio de intensidade", "pause_count": "Intervalos silenciosos", "longest_pause_seconds": "Maior intervalo silencioso (s)"}
        st.dataframe([{"Métrica": label, "Valor": str(acoustic[key])} for key, label in names.items() if key in acoustic], width="stretch", hide_index=True)
        if acoustic.get("window_energy"):
            st.line_chart(acoustic["window_energy"], x="start_seconds", y="rms", width="stretch")
        st.caption(acoustic.get("limitations", "Métricas acústicas sem interpretação clínica."))
    else:
        st.markdown("**Relatório visual**")
        names = {"width": "Largura", "height": "Altura", "fps": "Quadros/s", "duration_seconds": "Duração (s)", "analyzed_frame_count": "Quadros analisados", "mean_motion_percent": "Movimento médio (%)", "peak_motion_percent": "Pico de movimento (%)"}
        st.dataframe([{"Métrica": label, "Valor": str(analysis[key])} for key, label in names.items() if key in analysis], width="stretch", hide_index=True)
        pose = analysis.get("pose") or {}
        st.write("Pose: " + STATUS.get(pose.get("status"), "Sem análise neste job histórico"))
        if pose.get("peak_displacement") is not None:
            st.write(f"Pico de deslocamento normalizado: {pose['peak_displacement']} · limiar: {pose.get('threshold')}")
        if pose.get("landmarks"):
            with st.expander("Pontos corporais da última pose válida"):
                st.dataframe(pose["landmarks"], width="stretch", hide_index=True)
        st.markdown("**Evidências e limiares demonstrativos**")
        st.dataframe([*analysis.get("anomalies", []), *pose.get("anomalies", [])], width="stretch", hide_index=True)
        st.caption(pose.get("disclaimer", ""))
    st.warning(analysis.get("disclaimer", "Revisão humana obrigatória. Dados sintéticos, sem diagnóstico."))

import os
import sys
from typing import Any

import requests
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_summary import audio_jobs_options, build_audio_summary, compact_audio_events  # noqa: E402
from media_summary import build_upload_summary, compact_jobs  # noqa: E402
from operations_summary import (  # noqa: E402
    build_movement_summary,
    build_prescription_summary,
    compact_operation_events,
)
from overview_summary import build_demo_summary, compact_alerts, open_alerts_by_severity  # noqa: E402
from patients_summary import compact_patients  # noqa: E402
from video_summary import build_video_summary, compact_video_events, video_jobs_options  # noqa: E402
from vitals_summary import build_vitals_summary  # noqa: E402


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_V1 = f"{API_BASE_URL}/api/v1"

st.set_page_config(page_title="MedGuard AI", page_icon="🛡️", layout="wide")


def api_request(method: str, path: str, timeout: float = 20, **kwargs: Any) -> Any:
    try:
        response = requests.request(method, f"{API_V1}{path}", timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) is not None else ""
        st.error(f"Nao foi possivel acessar a API. {detail or exc}")
        return None


def load_patients() -> list[dict[str, Any]]:
    return api_request("GET", "/patients") or []


def raw_expander(data: Any, label: str = "Ver registro bruto") -> None:
    """Registro bruto (JSON da API) recolhido, para conferencia tecnica."""
    with st.expander(label):
        st.json(data)


def table_with_raw(rows: list[dict], raw: Any, empty_message: str) -> None:
    """Tabela compacta na frente; registro bruto no expander."""
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        raw_expander(raw)
    else:
        st.info(empty_message)


def render_conclusion(text: str, highlight: bool) -> None:
    (st.success if highlight else st.info)(text)


def render_vitals_summary(summary: dict) -> None:
    cols = st.columns(len(summary["values"]))
    for col, (label, value) in zip(cols, summary["values"].items()):
        col.metric(label, value)
    if summary["rules"]:
        st.markdown("**Regras disparadas**")
        st.dataframe(summary["rules"], use_container_width=True, hide_index=True)
    if summary["trends"]:
        st.markdown("**Tendências identificadas**")
        st.dataframe(summary["trends"], use_container_width=True, hide_index=True)
    if summary["triggered"]:
        st.error(summary["conclusion"])
    else:
        st.success(summary["conclusion"])


def render_inconsistencies(summary: dict) -> None:
    if summary["inconsistencies"]:
        st.dataframe(summary["inconsistencies"], use_container_width=True, hide_index=True)
        st.warning(summary["conclusion"])
    else:
        st.success(summary["conclusion"])


def render_video_summary(summary: dict) -> None:
    head = st.columns(3)
    head[0].metric("Status", summary["status"])
    head[1].metric("Paciente", summary["patient"])
    head[2].metric("Atividade", summary["metrics"]["Atividade"])
    if summary["error"]:
        st.error(f"Erro no job: {summary['error']}")
    metrics = {k: v for k, v in summary["metrics"].items() if k != "Atividade"}
    for col, (label, value) in zip(st.columns(len(metrics)), metrics.items()):
        col.metric(label, value)
    st.markdown("**Anomalias detectadas**")
    if summary["anomalies"]:
        st.dataframe(summary["anomalies"], use_container_width=True, hide_index=True)
    else:
        st.caption("Nenhuma anomalia.")
    render_conclusion(summary["conclusion"], bool(summary["anomalies"] and summary["event_count"]))
    if summary["disclaimer"]:
        st.caption(summary["disclaimer"])


st.title("🛡️ MedGuard AI")
st.caption("Tech Challenge FIAP - Fase 4 | Etapa 4: monitoramento sintetico multimodal")
st.warning(
    "Ambiente educacional. Use apenas pacientes, midias e medicoes ficticias. "
    "Os limites da demonstracao nao sao referencia clinica e o sistema nao realiza diagnosticos."
)

overview_tab, patients_tab, vitals_tab, video_tab, audio_tab, operations_tab, media_tab = st.tabs(
    [
        "Visao geral",
        "Pacientes ficticios",
        "Sinais vitais",
        "Analise de video",
        "Analise de audio",
        "Prescricoes e movimentacoes",
        "Midia e jobs",
    ]
)

with overview_tab:
    st.subheader("Fluxo demonstravel")
    st.write("Paciente sintetico → medicao anomala → evento normalizado → alerta aberto")
    if st.button("Executar demonstracao de alerta", type="primary", use_container_width=True):
        result = api_request("POST", "/demo/vital-alert")
        if result:
            st.success("Fluxo executado e persistido.")
            demo = build_demo_summary(result)
            cols = st.columns(4)
            cols[0].metric("Paciente", demo["patient"])
            cols[1].metric("Severidade", demo["severity"])
            cols[2].metric("Eventos", demo["event_count"])
            cols[3].metric("Alertas", demo["alert_count"])
            render_vitals_summary(demo)
            raw_expander(result)

    alerts = api_request("GET", "/alerts?limit=20") or []
    overview_patients = load_patients()
    st.subheader("Alertas abertos por severidade")
    for col, (label, count) in zip(st.columns(4), open_alerts_by_severity(alerts).items()):
        col.metric(label, count)
    st.subheader("Alertas recentes")
    table_with_raw(
        compact_alerts(alerts, overview_patients), alerts, "Ainda nao ha alertas. Execute a demonstracao acima."
    )

with patients_tab:
    st.subheader("Cadastrar paciente ficticio")
    with st.form("patient_form", clear_on_submit=True):
        code = st.text_input("Codigo sintetico", value="MG-TESTE-001")
        alias = st.text_input("Alias", value="Paciente Ficticio Beta")
        birth_year = st.number_input("Ano de nascimento ficticio", min_value=1900, max_value=2100, value=1990)
        notes = st.text_area("Observacoes", value="Registro educacional sem dados pessoais reais.")
        submitted = st.form_submit_button("Cadastrar")
        if submitted:
            created = api_request(
                "POST",
                "/patients",
                json={
                    "code": code,
                    "alias": alias,
                    "birth_year": int(birth_year),
                    "notes": notes,
                    "is_synthetic": True,
                },
            )
            if created:
                st.success(f"Paciente {created['code']} cadastrado.")

    patients = load_patients()
    st.subheader("Pacientes cadastrados")
    table_with_raw(compact_patients(patients), patients, "Nenhum paciente cadastrado.")

with vitals_tab:
    st.subheader("Registrar medicao sintetica")
    patients = load_patients()
    if not patients:
        st.info("Cadastre um paciente ficticio antes de registrar medicoes.")
    else:
        options = {f"{item['code']} - {item['alias']}": item["id"] for item in patients}
        selected = st.selectbox("Paciente", list(options))
        with st.form("vitals_form"):
            cols = st.columns(4)
            heart_rate = cols[0].number_input("Batimentos (bpm)", min_value=0.0, max_value=300.0, value=82.0)
            spo2 = cols[1].number_input("SpO2 (%)", min_value=0.0, max_value=100.0, value=97.0)
            systolic = cols[2].number_input("Pressao sistolica", min_value=0.0, max_value=350.0, value=120.0)
            diastolic = cols[3].number_input("Pressao diastolica", min_value=0.0, max_value=250.0, value=80.0)
            submitted = st.form_submit_button("Registrar e avaliar")
            if submitted:
                result = api_request(
                    "POST",
                    f"/patients/{options[selected]}/measurements",
                    json={
                        "heart_rate_bpm": heart_rate,
                        "spo2_percent": spo2,
                        "systolic_mmhg": systolic,
                        "diastolic_mmhg": diastolic,
                        "source": "streamlit_dashboard",
                        "is_synthetic": True,
                    },
                )
                if result:
                    render_vitals_summary(build_vitals_summary(result))
                    raw_expander(result)

with media_tab:
    st.subheader("Registrar audio ou video ficticio")
    st.info("Videos e audios WAV sinteticos podem ser processados nesta etapa.")
    patients = load_patients()
    if not patients:
        st.info("Cadastre um paciente ficticio antes de enviar midia.")
    else:
        options = {f"{item['code']} - {item['alias']}": item["id"] for item in patients}
        selected = st.selectbox("Paciente da midia", list(options), key="media_patient")
        uploaded = st.file_uploader("Arquivo ficticio", type=["wav", "mp4", "mov", "avi", "mkv"])
        if st.button("Registrar midia", disabled=uploaded is None):
            if uploaded is not None:
                result = api_request(
                    "POST",
                    f"/patients/{options[selected]}/media",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                    data={"is_synthetic": "true"},
                )
                if result:
                    st.success("Midia e job registrados.")
                    upload = build_upload_summary(result, patients)
                    cols = st.columns(4)
                    cols[0].metric("Arquivo", upload["filename"])
                    cols[1].metric("Tipo", upload["kind"])
                    cols[2].metric("Tamanho", upload["size"])
                    cols[3].metric("SHA-256", upload["sha256"])
                    st.write(f"Job: **{upload['job_status']}** ({upload['progress']})")
                    if upload["steps"]:
                        st.markdown("**Etapas do pipeline**")
                        steps_md = "\n".join(f"{i}. {step}" for i, step in enumerate(upload["steps"], 1))
                        st.markdown(steps_md)
                    if result["media"]["kind"] == "video":
                        st.session_state["last_video_job_id"] = result["job"]["id"]
                    else:
                        st.session_state["last_audio_job_id"] = result["job"]["id"]
                    raw_expander(result)

    jobs = api_request("GET", "/jobs?limit=20") or []
    st.subheader("Jobs recentes")
    table_with_raw(compact_jobs(jobs, patients), jobs, "Nenhum job registrado.")

with video_tab:
    st.subheader("Fluxo demonstravel de video")
    st.write("Video geometrico sintetico → OpenCV → metricas de movimento → evento → alerta")
    st.caption("A analise mede mudancas entre quadros e nao identifica pessoas nem produz diagnostico.")

    video_patients = load_patients()
    if st.button("Executar demonstracao de video sintetico", type="primary", use_container_width=True):
        result = api_request("POST", "/demo/video-alert")
        if result:
            st.success("Video sintetico criado, processado e persistido.")
            video_patients = load_patients()
            render_video_summary(build_video_summary(result["processing"]["job"], video_patients))
            raw_expander(result)

    last_job_id = st.session_state.get("last_video_job_id")
    if last_job_id:
        st.divider()
        st.write(f"Ultimo job de video enviado: `{last_job_id}`")
        if st.button("Processar ultimo video enviado", use_container_width=True):
            result = api_request("POST", f"/jobs/{last_job_id}/process")
            if result:
                st.success("Analise concluida.")
                st.session_state["video_selected_job_id"] = last_job_id
                render_video_summary(build_video_summary(result["job"], video_patients))
                raw_expander(result)

    st.subheader("Análises de vídeo concluídas")
    video_options = video_jobs_options(api_request("GET", "/jobs?limit=100") or [], video_patients)
    if video_options:
        video_ids = [job_id for _, job_id in video_options]
        video_labels = {job_id: label for label, job_id in video_options}
        preferred_video = st.session_state.get("video_selected_job_id")
        video_index = video_ids.index(preferred_video) if preferred_video in video_ids else 0
        chosen_video = st.selectbox(
            "Análises de vídeo concluídas", video_ids, index=video_index, format_func=video_labels.get
        )
        video_detail = api_request("GET", f"/jobs/{chosen_video}")
        if video_detail:
            render_video_summary(build_video_summary(video_detail, video_patients))
            raw_expander(video_detail)
    else:
        st.info("Ainda nao ha analises de video concluidas.")

    all_video_events = api_request("GET", "/events?limit=100") or []
    video_events = [item for item in all_video_events if item.get("source") == "video_analysis"]
    st.subheader("Eventos recentes de video")
    table_with_raw(
        compact_video_events(video_events, video_patients),
        video_events,
        "Ainda nao ha eventos de video. Execute a demonstracao ou envie um video ficticio.",
    )


with audio_tab:
    st.subheader("Fluxo de audio sintetico")
    st.write("Audio WAV sintetico → transcricao (faster-whisper local) → metricas acusticas → analise textual → evento de revisao")
    st.caption(
        "A transcricao e local (faster-whisper, sem credenciais) por padrao; Azure Speech e opcional via SPEECH_PROVIDER=azure. Os achados sao educacionais, "
        "exigem revisao humana e nao geram diagnostico automatico."
    )

    def render_audio_summary(summary: dict) -> None:
        head = st.columns(3)
        head[0].metric("Status", summary["status"])
        head[1].metric("Transcritor", summary["provider"])
        head[2].metric("Paciente", summary["patient"])
        if summary["error"]:
            st.error(f"Erro no job: {summary['error']}")
        st.markdown("**Transcrição**")
        if summary["transcription_text"]:
            st.info(f"“{summary['transcription_text']}”")
        else:
            st.warning(summary["transcription_warning"])
        metric_cols = st.columns(len(summary["metrics"]))
        for col, (label, value) in zip(metric_cols, summary["metrics"].items()):
            col.metric(label, value)
        st.markdown("**Achados**")
        if summary["findings"]:
            st.dataframe(summary["findings"], use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum achado.")
        if summary["findings"] and summary["event_count"]:
            st.success(summary["conclusion"])
        else:
            st.info(summary["conclusion"])
        if summary["disclaimer"]:
            st.caption(summary["disclaimer"])

    audio_patients = load_patients()
    last_audio_job_id = st.session_state.get("last_audio_job_id")
    if last_audio_job_id:
        st.write(f"Ultimo job de audio enviado: `{last_audio_job_id}`")
        if st.button("Processar ultimo audio enviado", use_container_width=True):
            with st.spinner("Transcrevendo e analisando o audio (pode levar alguns minutos na primeira vez)..."):
                result = api_request("POST", f"/jobs/{last_audio_job_id}/process", timeout=180)
            if result:
                st.success("Analise de audio concluida.")
                st.session_state["audio_selected_job_id"] = last_audio_job_id
    else:
        st.info("Envie um WAV sintetico na aba Midia e jobs para iniciar a analise.")

    audio_events = api_request("GET", "/events?limit=100") or []
    audio_options = audio_jobs_options(api_request("GET", "/jobs?limit=100") or [], audio_patients)
    st.subheader("Análises de áudio concluídas")
    if audio_options:
        ids = [job_id for _, job_id in audio_options]
        labels = {job_id: label for label, job_id in audio_options}
        preferred = st.session_state.get("audio_selected_job_id")
        index = ids.index(preferred) if preferred in ids else 0
        chosen = st.selectbox("Análises de áudio concluídas", ids, index=index, format_func=labels.get)
        job_detail = api_request("GET", f"/jobs/{chosen}")
        if job_detail:
            render_audio_summary(build_audio_summary(job_detail, audio_events, audio_patients))
            raw_expander(job_detail)
    else:
        st.info("Ainda nao ha analises de audio concluidas.")

    st.subheader("Eventos recentes de áudio")
    compact_events = compact_audio_events(audio_events, audio_patients)
    audio_raw_events = [item for item in audio_events if item.get("source") == "audio_analysis"]
    table_with_raw(compact_events, audio_raw_events, "Ainda nao ha eventos de audio processados.")


with operations_tab:
    st.subheader("Regras demonstrativas da Etapa 4")
    st.caption(
        "As regras verificam somente sequencias de dados ficticios. "
        "Nao realizam validacao farmacologica, rastreamento real ou diagnostico."
    )
    patients = load_patients()
    if not patients:
        st.info("Cadastre um paciente ficticio antes de executar os fluxos.")
    else:
        options = {f"{item['code']} - {item['alias']}": item["id"] for item in patients}
        selected = st.selectbox("Paciente da Etapa 4", list(options), key="phase4_patient")
        patient_id = options[selected]

        prescription_col, movement_col = st.columns(2)
        with prescription_col:
            st.markdown("#### Prescricao sintetica")
            with st.form("prescription_evaluation_form"):
                medication_code = st.text_input("Codigo ficticio", value="MED-SYNTH-001")
                action = st.selectbox("Acao", ["started", "changed", "stopped"])
                submitted = st.form_submit_button("Registrar e avaliar prescricao")
                if submitted:
                    result = api_request(
                        "POST",
                        f"/patients/{patient_id}/prescriptions/evaluate",
                        json={
                            "medication_code": medication_code,
                            "action": action,
                            "is_synthetic": True,
                        },
                    )
                    if result:
                        st.success("Prescricao sintetica avaliada.")
                        summary = build_prescription_summary(result)
                        st.write(
                            f"**{summary['action']}** do medicamento `{summary['medication']}` "
                            f"registrada em {summary['recorded_at']}."
                        )
                        render_inconsistencies(summary)
                        raw_expander(result)

        with movement_col:
            st.markdown("#### Movimentacao sintetica")
            with st.form("movement_evaluation_form"):
                from_location = st.text_input("Origem ficticia", value="ala-a-sintetica")
                to_location = st.text_input("Destino ficticio", value="ala-b-sintetica")
                submitted = st.form_submit_button("Registrar e avaliar movimentacao")
                if submitted:
                    result = api_request(
                        "POST",
                        f"/patients/{patient_id}/movements",
                        json={
                            "from_location": from_location,
                            "to_location": to_location,
                            "is_synthetic": True,
                        },
                    )
                    if result:
                        st.success("Movimentacao sintetica avaliada.")
                        summary = build_movement_summary(result)
                        st.write(
                            f"Movimentação de **{summary['from']}** para **{summary['to']}** "
                            f"registrada em {summary['recorded_at']}."
                        )
                        render_inconsistencies(summary)
                        raw_expander(result)

    phase4_events = api_request("GET", "/events?limit=100") or []
    phase4_sources = {"vital_trends", "prescription_analysis", "movement_analysis"}
    phase4_events = [item for item in phase4_events if item.get("source") in phase4_sources]
    st.subheader("Eventos recentes da Etapa 4")
    table_with_raw(
        compact_operation_events(phase4_events, load_patients()),
        phase4_events,
        "Ainda nao ha eventos temporais, de prescricao ou de movimentacao.",
    )


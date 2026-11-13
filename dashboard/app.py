import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_V1 = f"{API_BASE_URL}/api/v1"

st.set_page_config(page_title="MedGuard AI", page_icon="🛡️", layout="wide")


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = requests.request(method, f"{API_V1}{path}", timeout=20, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) is not None else ""
        st.error(f"Nao foi possivel acessar a API. {detail or exc}")
        return None


def load_patients() -> list[dict[str, Any]]:
    return api_request("GET", "/patients") or []


st.title("🛡️ MedGuard AI")
st.caption("Tech Challenge FIAP - Fase 4 | Etapa 4: monitoramento sintetico multimodal")
st.warning(
    "Ambiente educacional. Use apenas pacientes, midias e medicoes ficticias. "
    "Os limites da demonstracao nao sao referencia clinica e o sistema nao realiza diagnosticos."
)

(
    overview_tab,
    patients_tab,
    vitals_tab,
    video_tab,
    audio_tab,
    operations_tab,
    media_tab,
    multimodal_tab,
) = st.tabs(
    [
        "Visao geral",
        "Pacientes ficticios",
        "Sinais vitais",
        "Analise de video",
        "Analise de audio",
        "Prescricoes e movimentacoes",
        "Midia e jobs",
        "Monitoramento multimodal",
    ]
)

with overview_tab:
    st.subheader("Fluxo demonstravel")
    st.write("Paciente sintetico → medicao anomala → evento normalizado → alerta aberto")
    if st.button("Executar demonstracao de alerta", type="primary", width="stretch"):
        result = api_request("POST", "/demo/vital-alert")
        if result:
            st.success("Fluxo executado e persistido.")
            cols = st.columns(3)
            cols[0].metric("Paciente", result["patient"]["code"])
            cols[1].metric("Eventos", len(result["result"]["events"]))
            cols[2].metric("Alertas", len(result["result"]["alerts"]))
            st.json(result)

    alerts = api_request("GET", "/alerts?limit=20") or []
    st.subheader("Alertas recentes")
    if alerts:
        st.dataframe(alerts, width="stretch", hide_index=True)
    else:
        st.info("Ainda nao ha alertas. Execute a demonstracao acima.")

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
    if patients:
        st.dataframe(patients, width="stretch", hide_index=True)
    else:
        st.info("Nenhum paciente cadastrado.")

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
                    if result["alerts"]:
                        st.error("A medicao gerou um alerta demonstrativo.")
                    else:
                        st.success("Medicao registrada sem evento pelas regras demonstrativas.")
                    st.json(result)

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
                    if result["media"]["kind"] == "video":
                        st.session_state["last_video_job_id"] = result["job"]["id"]
                    else:
                        st.session_state["last_audio_job_id"] = result["job"]["id"]
                    st.json(result)

    jobs = api_request("GET", "/jobs?limit=20") or []
    st.subheader("Jobs recentes")
    if jobs:
        st.dataframe(jobs, width="stretch", hide_index=True)
    else:
        st.info("Nenhum job registrado.")

with video_tab:
    st.subheader("Fluxo demonstravel de video")
    st.write("Video geometrico sintetico → OpenCV → metricas de movimento → evento → alerta")
    st.caption("A analise mede mudancas entre quadros e nao identifica pessoas nem produz diagnostico.")

    if st.button("Executar demonstracao de video sintetico", type="primary", width="stretch"):
        result = api_request("POST", "/demo/video-alert")
        if result:
            analysis = result["processing"]["job"]["result"]["analysis"]
            st.success("Video sintetico criado, processado e persistido.")
            cols = st.columns(4)
            cols[0].metric("Quadros analisados", analysis["analyzed_frame_count"])
            cols[1].metric("Movimento medio", f"{analysis['mean_motion_percent']:.3f}%")
            cols[2].metric("Eventos", len(result["processing"]["events"]))
            cols[3].metric("Alertas", len(result["processing"]["alerts"]))
            st.json(result)

    last_job_id = st.session_state.get("last_video_job_id")
    if last_job_id:
        st.divider()
        st.write(f"Ultimo job de video enviado: `{last_job_id}`")
        if st.button("Processar ultimo video enviado", width="stretch"):
            result = api_request("POST", f"/jobs/{last_job_id}/process")
            if result:
                st.success("Analise concluida.")
                st.json(result)

    video_events = api_request("GET", "/events?limit=50") or []
    video_events = [item for item in video_events if item.get("source") == "video_analysis"]
    st.subheader("Eventos recentes de video")
    if video_events:
        st.dataframe(video_events, width="stretch", hide_index=True)
    else:
        st.info("Ainda nao ha eventos de video. Execute a demonstracao ou envie um video ficticio.")


with audio_tab:
    st.subheader("Fluxo de audio sintetico")
    st.write("Audio WAV sintetico → Azure Speech → metricas acusticas → analise textual → evento de revisao")
    st.caption(
        "A transcricao exige credenciais Azure configuradas. Os achados sao educacionais, "
        "exigem revisao humana e nao geram diagnostico automatico."
    )

    last_audio_job_id = st.session_state.get("last_audio_job_id")
    if last_audio_job_id:
        st.write(f"Ultimo job de audio enviado: `{last_audio_job_id}`")
        if st.button("Processar ultimo audio enviado", width="stretch"):
            result = api_request("POST", f"/jobs/{last_audio_job_id}/process")
            if result:
                st.success("Analise de audio concluida.")
                st.json(result)
    else:
        st.info("Envie um WAV sintetico na aba Midia e jobs para iniciar a analise.")

    audio_events = api_request("GET", "/events?limit=50") or []
    audio_events = [item for item in audio_events if item.get("source") == "audio_analysis"]
    st.subheader("Eventos recentes de audio")
    if audio_events:
        st.dataframe(audio_events, width="stretch", hide_index=True)
    else:
        st.info("Ainda nao ha eventos de audio processados.")


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
                        st.json(result)

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
                        st.json(result)

    phase4_events = api_request("GET", "/events?limit=100") or []
    phase4_sources = {"vital_trends", "prescription_analysis", "movement_analysis"}
    phase4_events = [item for item in phase4_events if item.get("source") in phase4_sources]
    st.subheader("Eventos recentes da Etapa 4")
    if phase4_events:
        st.dataframe(phase4_events, width="stretch", hide_index=True)
    else:
        st.info("Ainda nao ha eventos temporais, de prescricao ou de movimentacao.")


# ============================================================
# MULTIMODAL MONITORING DASHBOARD V2
# ============================================================

from multimodal_v2 import render_multimodal_dashboard

with multimodal_tab:
    render_multimodal_dashboard(
        api_request=api_request,
        load_patients=load_patients,
    )
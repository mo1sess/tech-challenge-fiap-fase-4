import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_V1 = f"{API_BASE_URL}/api/v1"

JOB_LABELS = {
    "queued": "Na fila",
    "processing": "Em processamento",
    "completed": "Concluída",
    "failed": "Falhou",
}
MEDIA_LABELS = {"audio": "Áudio", "video": "Vídeo"}

SENTIMENT_LABELS = {
    "positive": "Positivo",
    "neutral": "Neutro",
    "negative": "Negativo",
    "mixed": "Misto",
}
SENTIMENT_REASONS = {
    "speech_not_recognized": "Nenhuma fala reconhecida na transcrição.",
    "empty_text": "A transcrição está vazia.",
    "missing_configuration": "Configure o endpoint e a chave do Azure AI Language na API.",
    "document_too_large": "A transcrição excede o limite do Azure AI Language.",
    "service_error": "A chamada ao Azure AI Language falhou.",
    "document_error": "O Azure AI Language rejeitou o documento.",
    "invalid_response": "O Azure AI Language retornou uma resposta inesperada.",
}
CLINICAL_MENTION_REASONS = {
    "speech_not_recognized": SENTIMENT_REASONS["speech_not_recognized"],
    "empty_text": SENTIMENT_REASONS["empty_text"],
    "missing_configuration": SENTIMENT_REASONS["missing_configuration"],
    "document_too_large": "A transcrição excede o limite do Text Analytics for Health.",
    "service_error": "A chamada ao Text Analytics for Health falhou.",
    "document_error": "O Text Analytics for Health rejeitou o documento.",
    "invalid_response": "O Text Analytics for Health retornou uma resposta inesperada.",
    "timeout": "O serviço excedeu o tempo de espera.",
}

st.set_page_config(page_title="MedGuard AI", page_icon="🛡️", layout="wide")


def api_request(
    method: str, path: str, *, timeout: int = 20, binary: bool = False, **kwargs: Any
) -> Any:
    try:
        response = requests.request(method, f"{API_V1}{path}", timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.content if binary else response.json()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) is not None else ""
        st.error(f"Não foi possível acessar a API. {detail or exc}")
        return None


def load_records(path: str, **filters: Any) -> list[dict[str, Any]]:
    records = []
    page_size = 100
    while True:
        page = api_request("GET", path, params={**filters, "limit": page_size, "offset": len(records)})
        if page is None:
            return records
        records.extend(page)
        if len(page) < page_size:
            return records


def show_clinical_mentions(result: dict[str, Any] | None) -> None:
    st.markdown("**Menções clínicas na transcrição**")
    if not result:
        st.info("Este job não tem uma extração de menções clínicas registrada.")
        return

    st.caption(result["disclaimer"])
    status = result["status"]
    reason = CLINICAL_MENTION_REASONS.get(result.get("reason"), "")
    if status == "skipped":
        st.info(f"Extração não executada (skipped). {reason}")
    elif status == "unavailable":
        st.warning(f"Extração indisponível (unavailable). {reason}")
    elif status == "succeeded":
        st.caption(f"Resultado do Azure Text Analytics for Health · {result['language']}")
        if not result["mentions"]:
            st.info("O Azure não identificou menções a sintomas ou sinais.")
            return
        st.caption("Campos vazios indicam contexto sem modificador explícito na resposta do serviço.")
        st.dataframe(
            [
                {
                    "Trecho": mention["text"],
                    "Categoria": mention["category"],
                    "Certeza": mention["context"]["certainty"],
                    "Pessoa citada": mention["context"]["association"],
                    "Condição": mention["context"]["conditionality"],
                    "Confiança da extração": mention["confidence_score"],
                }
                for mention in result["mentions"]
            ],
            hide_index=True,
        )


def show_audio_analysis(analysis: dict[str, Any]) -> None:
    st.markdown("**Transcrição**")
    st.text(analysis["transcription"].get("text") or "Sem texto reconhecido.")
    show_clinical_mentions(analysis.get("clinical_mentions"))
    st.markdown("**Análise de sentimento**")
    sentiment = analysis.get("sentiment_analysis")
    if not sentiment:
        st.info("Este job foi processado sem um resultado de sentimento registrado.")
        return

    st.caption(sentiment["disclaimer"])
    status = sentiment["status"]
    reason = SENTIMENT_REASONS.get(sentiment.get("reason"), "")
    if status == "skipped":
        st.info(f"Análise não executada (skipped). {reason}")
    elif status == "unavailable":
        st.warning(f"Análise indisponível (unavailable). {reason}")
    elif status == "succeeded":
        st.caption(f"Resultado do Azure AI Language · {sentiment['language']}")
        label = sentiment["sentiment"]
        st.metric("Sentimento geral", SENTIMENT_LABELS.get(label, label))

        st.markdown("**Confiança do modelo**")
        for column, key in zip(st.columns(3), ("positive", "neutral", "negative")):
            column.metric(SENTIMENT_LABELS[key], f"{sentiment['confidence_scores'][key]:.2f}")

        if sentiment["sentences"]:
            st.markdown("**Sentimento por sentença**")
            st.dataframe(
                [
                    {
                        "Sentença": sentence["text"],
                        "Sentimento": SENTIMENT_LABELS.get(sentence["sentiment"], sentence["sentiment"]),
                        "Positivo": sentence["confidence_scores"]["positive"],
                        "Neutro": sentence["confidence_scores"]["neutral"],
                        "Negativo": sentence["confidence_scores"]["negative"],
                    }
                    for sentence in sentiment["sentences"]
                ],
                hide_index=True,
            )


def show_video_analysis(analysis: dict[str, Any]) -> None:
    st.caption(analysis.get("disclaimer", "Análise educacional de movimento em vídeo sintético."))
    frames, average, peak = st.columns(3)
    frames.metric("Quadros analisados", analysis.get("analyzed_frame_count", "—"))
    average.metric("Movimento médio", format_measure(analysis.get("mean_motion_percent"), "%"))
    peak.metric("Pico de movimento", format_measure(analysis.get("peak_motion_percent"), "%"))
    for anomaly in analysis.get("anomalies", []):
        st.warning(f"{anomaly['title']} · {anomaly['description']}")


def format_measure(value: float | None, unit: str = "") -> str:
    return f"{value:g} {unit}".strip() if value is not None else "—"


def format_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def register_patient() -> None:
    with st.expander("Cadastrar paciente"):
        with st.form("patient_form", clear_on_submit=True):
            columns = st.columns([2, 3, 2])
            code = columns[0].text_input("Código", placeholder="MG-001")
            alias = columns[1].text_input("Nome fictício", placeholder="Paciente Exemplo")
            birth_year = columns[2].number_input("Ano de nascimento", value=None, min_value=1900, max_value=2100)
            notes = st.text_area("Observações", max_chars=1000)
            if st.form_submit_button("Cadastrar", type="primary"):
                created = api_request(
                    "POST",
                    "/patients",
                    json={
                        "code": code.strip(),
                        "alias": alias.strip(),
                        "birth_year": birth_year,
                        "notes": notes.strip() or None,
                        "is_synthetic": True,
                    },
                )
                if created:
                    st.session_state["patient_id"] = created["id"]
                    st.session_state["notice"] = f"Paciente {created['code']} cadastrado."
                    st.rerun()


def show_registry() -> None:
    st.title("Pacientes")
    st.caption("Pesquise pelo nome fictício ou código para abrir o prontuário.")
    register_patient()

    query = st.text_input("Buscar paciente", placeholder="Nome ou código").strip().casefold()
    patients = load_records("/patients")
    matches = [
        patient for patient in patients
        if query in f"{patient['code']} {patient['alias']}".casefold()
    ]
    if not matches:
        st.info("Nenhum paciente encontrado." if query else "Nenhum paciente cadastrado.")
        return

    st.dataframe(
        [
            {
                "Código": patient["code"],
                "Paciente": patient["alias"],
                "Nascimento": patient.get("birth_year"),
                "Cadastro": format_date(patient.get("created_at")),
            }
            for patient in matches
        ],
        hide_index=True,
    )
    options = {patient["id"]: patient for patient in matches}
    patient_id = st.selectbox(
        "Selecionar paciente",
        list(options),
        key="registry_patient",
        format_func=lambda key: f"{options[key]['alias']} · {options[key]['code']}",
    )
    if st.button("Abrir prontuário", type="primary"):
        st.session_state["patient_id"] = patient_id
        st.rerun()


def show_media_file(media: dict[str, Any]) -> None:
    with st.expander("Reproduzir ou baixar arquivo"):
        if st.button("Carregar arquivo", key=f"load_file_{media['id']}"):
            content = api_request("GET", f"/media/{media['id']}/content", binary=True)
            if content is not None:
                st.session_state["media_preview"] = (media["id"], content)

        preview = st.session_state.get("media_preview")
        if not preview or preview[0] != media["id"]:
            return
        filename = media["original_filename"]
        if media["kind"] == "audio":
            st.audio(preview[1], format="audio/wav")
        elif Path(filename).suffix.lower() == ".mp4":
            st.video(preview[1], format="video/mp4")
        else:
            st.caption("Baixe o arquivo para reproduzir este formato.")
        st.download_button("Baixar arquivo", preview[1], file_name=filename)


def show_job(job: dict[str, Any]) -> None:
    status = job["status"]
    st.markdown(f"**{JOB_LABELS.get(status, status)}**")
    st.caption(f"Job {job['id']} · {format_date(job.get('updated_at'))}")
    if status in {"queued", "failed"}:
        label = "Tentar novamente" if status == "failed" else "Processar mídia"
        if job.get("error"):
            st.error(job["error"])
        if st.button(label, type="primary", key=f"process_{job['id']}"):
            with st.spinner("Processando mídia sintética..."):
                result = api_request("POST", f"/jobs/{job['id']}/process", timeout=90)
            if result:
                st.session_state["notice"] = "Análise registrada no prontuário."
                st.rerun()
    elif status == "processing":
        st.progress(min(max(float(job.get("progress") or 0) / 100, 0), 1))
    elif status == "completed":
        result = job.get("result") or {}
        analysis = result.get("analysis") or {}
        if job["job_type"] == "audio_analysis" and analysis.get("transcription"):
            show_audio_analysis(analysis)
            acoustic = analysis.get("acoustic") or {}
            if acoustic:
                duration, rms, silence = st.columns(3)
                duration.metric("Duração", format_measure(acoustic.get("duration_seconds"), "s"))
                rms.metric("Energia RMS", format_measure(acoustic.get("rms")))
                ratio = acoustic.get("silence_ratio")
                silence.metric("Silêncio", format_measure(round(ratio * 100, 1) if ratio is not None else None, "%"))
            local_analysis = analysis.get("text_analysis") or {}
            if local_analysis:
                expressions = ", ".join(local_analysis.get("matched_expressions", []))
                st.markdown("**Termos encontrados pelas regras locais**")
                st.write(expressions or "Nenhum termo encontrado.")
        elif job["job_type"] == "video_analysis" and analysis:
            show_video_analysis(analysis)
        with st.expander("Resultado completo da análise"):
            st.json(result)


def show_media(patient_id: str) -> None:
    with st.expander("Adicionar áudio ou vídeo"):
        st.caption("Para áudio, use WAV PCM de 16 bits. Envie somente mídias fictícias.")
        with st.form(f"upload_{patient_id}", clear_on_submit=True):
            uploaded = st.file_uploader("Arquivo sintético", type=["wav", "mp4", "mov", "avi", "mkv"])
            if st.form_submit_button("Registrar mídia"):
                if uploaded is None:
                    st.warning("Selecione um arquivo para registrar.")
                else:
                    result = api_request(
                        "POST",
                        f"/patients/{patient_id}/media",
                        files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                        data={"is_synthetic": "true"},
                    )
                    if result:
                        st.session_state["selected_media"] = result["media"]["id"]
                        st.session_state["notice"] = "Mídia registrada e disponível para análise."
                        st.rerun()

    files = load_records("/media", patient_id=patient_id)
    jobs = load_records("/jobs", patient_id=patient_id)
    if not files:
        st.info("Este paciente ainda não tem mídias registradas.")
        return

    jobs_by_file = defaultdict(list)
    for job in jobs:
        jobs_by_file[job["media_file_id"]].append(job)

    st.dataframe(
        [
            {
                "Arquivo": media["original_filename"],
                "Tipo": MEDIA_LABELS.get(media["kind"], media["kind"]),
                "Enviado em": format_date(media.get("created_at")),
                "Análises": len(jobs_by_file[media["id"]]),
                "Último status": JOB_LABELS.get(jobs_by_file[media["id"]][0]["status"], "—")
                if jobs_by_file[media["id"]] else "—",
            }
            for media in files
        ],
        hide_index=True,
    )
    options = {media["id"]: media for media in files}
    selected_id = st.session_state.pop("selected_media", None)
    if selected_id in options:
        st.session_state[f"media_{patient_id}"] = selected_id
    media_id = st.selectbox(
        "Arquivo no prontuário",
        list(options),
        key=f"media_{patient_id}",
        format_func=lambda key: f"{options[key]['original_filename']} · {format_date(options[key].get('created_at'))} · {key[:8]}",
    )
    with st.container(border=True):
        st.subheader(options[media_id]["original_filename"])
        show_media_file(options[media_id])
        media_jobs = jobs_by_file[media_id]
        if not media_jobs:
            st.info("Nenhum job associado a este arquivo.")
        elif len(media_jobs) == 1:
            show_job(media_jobs[0])
        else:
            media_jobs_by_id = {job["id"]: job for job in media_jobs}
            job_id = st.selectbox(
                "Análises do arquivo",
                list(media_jobs_by_id),
                key=f"job_{media_id}",
                format_func=lambda key: f"{format_date(media_jobs_by_id[key].get('created_at'))} · "
                f"{JOB_LABELS.get(media_jobs_by_id[key]['status'], media_jobs_by_id[key]['status'])} · {key[:8]}",
            )
            show_job(media_jobs_by_id[job_id])


def show_vitals(patient_id: str) -> None:
    with st.expander("Registrar medição"):
        with st.form(f"vitals_{patient_id}"):
            cols = st.columns(4)
            heart_rate = cols[0].number_input("Batimentos (bpm)", min_value=0.0, max_value=300.0, value=82.0)
            spo2 = cols[1].number_input("SpO₂ (%)", min_value=0.0, max_value=100.0, value=97.0)
            systolic = cols[2].number_input("Pressão sistólica", min_value=0.0, max_value=350.0, value=120.0)
            diastolic = cols[3].number_input("Pressão diastólica", min_value=0.0, max_value=250.0, value=80.0)
            if st.form_submit_button("Registrar e avaliar", type="primary"):
                result = api_request(
                    "POST",
                    f"/patients/{patient_id}/measurements",
                    json={
                        "heart_rate_bpm": heart_rate, "spo2_percent": spo2,
                        "systolic_mmhg": systolic, "diastolic_mmhg": diastolic,
                        "source": "streamlit_dashboard", "is_synthetic": True,
                    },
                )
                if result:
                    if result["alerts"]:
                        st.warning("A medição gerou alerta demonstrativo.")
                    else:
                        st.success("Medição registrada.")
                    st.json(result, expanded=False)

    measurements = api_request("GET", f"/patients/{patient_id}/measurements") or []
    if measurements:
        latest = measurements[0]
        pulse, oxygen, pressure = st.columns(3)
        pulse.metric("Últimos batimentos", format_measure(latest["heart_rate_bpm"], "bpm"))
        oxygen.metric("Última SpO₂", format_measure(latest["spo2_percent"], "%"))
        pressure.metric(
            "Última pressão",
            f"{format_measure(latest['systolic_mmhg'])}/{format_measure(latest['diastolic_mmhg'])} mmHg",
        )
        st.dataframe(
            [
                {
                    "Data": format_date(item["measured_at"]), "Batimentos (bpm)": item["heart_rate_bpm"],
                    "SpO₂ (%)": item["spo2_percent"], "Sistólica (mmHg)": item["systolic_mmhg"],
                    "Diastólica (mmHg)": item["diastolic_mmhg"],
                }
                for item in measurements
            ],
            hide_index=True,
        )
    else:
        st.info("Nenhuma medição registrada.")


def show_operations(patient_id: str) -> None:
    st.caption("Registros fictícios para avaliar regras demonstrativas de sequência e continuidade.")
    prescription_col, movement_col = st.columns(2)
    with prescription_col:
        with st.expander("Registrar prescrição"):
            with st.form(f"prescription_{patient_id}"):
                code = st.text_input("Código fictício", value="MED-SYNTH-001")
                labels = {"started": "Iniciar", "changed": "Alterar", "stopped": "Suspender"}
                action = st.selectbox("Ação", list(labels), format_func=labels.__getitem__)
                if st.form_submit_button("Registrar e avaliar prescrição"):
                    result = api_request(
                        "POST",
                        f"/patients/{patient_id}/prescriptions/evaluate",
                        json={"medication_code": code, "action": action, "is_synthetic": True},
                    )
                    if result:
                        st.success("Prescrição avaliada.")
                        st.json(result, expanded=False)
        records = api_request("GET", f"/patients/{patient_id}/prescriptions") or []
        if records:
            st.dataframe(
                [
                    {"Medicamento": item["medication_code"], "Ação": labels.get(item["action"], item["action"]),
                     "Data": format_date(item["recorded_at"])}
                    for item in records
                ],
                hide_index=True,
            )
        else:
            st.info("Nenhuma prescrição registrada.")
    with movement_col:
        with st.expander("Registrar movimentação"):
            with st.form(f"movement_{patient_id}"):
                origin = st.text_input("Origem fictícia", value="ala-a-sintetica")
                destination = st.text_input("Destino fictício", value="ala-b-sintetica")
                if st.form_submit_button("Registrar e avaliar movimentação"):
                    result = api_request(
                        "POST",
                        f"/patients/{patient_id}/movements",
                        json={"from_location": origin, "to_location": destination, "is_synthetic": True},
                    )
                    if result:
                        st.success("Movimentação avaliada.")
                        st.json(result, expanded=False)
        records = api_request("GET", f"/patients/{patient_id}/movements") or []
        if records:
            st.dataframe(
                [
                    {"Origem": item["from_location"], "Destino": item["to_location"],
                     "Data": format_date(item["recorded_at"])}
                    for item in records
                ],
                hide_index=True,
            )
        else:
            st.info("Nenhuma movimentação registrada.")


def show_events(patient_id: str) -> None:
    labels = {
        "audio_analysis": "Áudio",
        "video_analysis": "Vídeo",
        "vital_signs": "Sinais vitais",
        "vital_trends": "Tendências de sinais vitais",
        "prescription_analysis": "Prescrições",
        "movement_analysis": "Movimentações",
        "multimodal_correlation": "Correlação",
    }
    events = api_request("GET", "/events", params={"patient_id": patient_id, "limit": 100}) or []
    if not events:
        st.info("Nenhum evento registrado neste prontuário.")
        return
    origins = sorted({event["source"] for event in events}, key=lambda source: labels.get(source, source))
    source = st.selectbox("Filtrar por origem", ["", *origins], format_func=lambda key: labels.get(key, key or "Todas"))
    rows = [event for event in events if not source or event["source"] == source]
    st.dataframe(
        [
            {
                "Data": format_date(event["occurred_at"]),
                "Origem": labels.get(event["source"], event["source"]),
                "Evento": event["title"],
                "Severidade": event["severity"],
                "Descrição": event["description"],
            }
            for event in rows
        ],
        hide_index=True,
    )


def show_alerts(patient_id: str | None = None) -> None:
    params = {"limit": 100}
    if patient_id is not None:
        params["patient_id"] = patient_id
    alerts = api_request("GET", "/alerts", params=params) or []
    if not alerts:
        st.info("Nenhum alerta registrado.")
        return
    status_labels = {"open": "Aberto", "acknowledged": "Reconhecido", "resolved": "Resolvido"}
    patients = {patient["id"]: patient["code"] for patient in load_records("/patients")} if patient_id is None else {}
    st.dataframe(
        [
            {
                **({"Paciente": patients.get(alert["patient_id"], "—")} if patient_id is None else {}),
                "Alerta": alert["message"],
                "Severidade": alert["severity"],
                "Status": status_labels.get(alert["status"], alert["status"]),
                "Data": format_date(alert["created_at"]),
            }
            for alert in alerts
        ],
        hide_index=True,
    )


def show_patient(patient_id: str) -> None:
    if st.button("← Voltar à lista de pacientes"):
        st.session_state.pop("patient_id", None)
        st.session_state.pop("media_preview", None)
        st.rerun()
    patient = api_request("GET", f"/patients/{patient_id}")
    if patient is None:
        return
    with st.container(border=True, key="patient_header"):
        st.caption("PRONTUÁRIO SINTÉTICO")
        st.title(patient["alias"])
        birth_year = patient.get("birth_year")
        st.write(f"**{patient['code']}**" + (f" · Ano de nascimento: {birth_year}" if birth_year else ""))
        if patient.get("notes"):
            st.caption(patient["notes"])

    media, vitals, operations, events, alerts = st.tabs(
        ["Mídias e análises", "Sinais vitais", "Prescrições e movimentações", "Eventos", "Alertas"]
    )
    with media:
        show_media(patient_id)
    with vitals:
        show_vitals(patient_id)
    with operations:
        show_operations(patient_id)
    with events:
        show_events(patient_id)
    with alerts:
        show_alerts(patient_id)


def show_demos() -> None:
    st.title("Demonstrações")
    vitals, video = st.columns(2)
    with vitals, st.container(border=True):
        st.subheader("Alerta de sinais vitais")
        st.caption("Registra uma medição anômala e gera um alerta demonstrativo.")
        if st.button("Executar demonstração de alerta", type="primary"):
            result = api_request("POST", "/demo/vital-alert")
            if result:
                st.success("Medição e alerta registrados.")
                st.json(result, expanded=False)
    with video, st.container(border=True):
        st.subheader("Análise de vídeo")
        st.caption("Gera um vídeo geométrico e analisa o movimento dos quadros.")
        if st.button("Executar demonstração de vídeo", type="primary"):
            result = api_request("POST", "/demo/video-alert", timeout=90)
            if result:
                st.success("Vídeo criado, analisado e registrado.")
                show_video_analysis(result["processing"]["job"]["result"]["analysis"])
                st.json(result, expanded=False)


st.markdown(
    f"<style>{Path(__file__).with_name('erp.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)
with st.sidebar:
    st.markdown(
        '<div class="medguard-brand"><span class="medguard-mark" aria-hidden="true">+</span>'
        '<div><strong>MedGuard AI</strong><span>Gestão hospitalar</span></div></div>',
        unsafe_allow_html=True,
    )
    page = st.radio("Menu principal", ["Pacientes", "Alertas", "Demonstrações"], label_visibility="collapsed")
    st.divider()
    st.caption("Ambiente educacional · somente dados fictícios. Os resultados não orientam decisões clínicas.")

notice = st.session_state.pop("notice", None)
if notice:
    st.toast(notice)

if page == "Pacientes":
    active_patient = st.session_state.get("patient_id")
    if active_patient:
        show_patient(active_patient)
    else:
        show_registry()
elif page == "Alertas":
    st.title("Alertas")
    st.caption("Alertas demonstrativos recentes de todos os pacientes.")
    show_alerts()
else:
    show_demos()

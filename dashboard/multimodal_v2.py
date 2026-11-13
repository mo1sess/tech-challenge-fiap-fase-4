"""MedGuard AI – Multimodal Monitoring Dashboard v2.

Drop this file in dashboard/multimodal_v2.py.
Call render_multimodal_dashboard(api_request, load_patients) inside an existing
Streamlit tab. Displays only synthetic/educational temporal co-occurrence.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import pandas as pd
import streamlit as st

SOURCES = {
    "audio_analysis": "Áudio",
    "video_analysis": "Vídeo",
    "vital_signs": "Sinais vitais",
    "vital_trends": "Tendências vitais",
    "prescription_analysis": "Prescrições",
    "movement_analysis": "Movimentações",
    "multimodal_correlation": "Correlação",
}
SEVERITIES = {"critical": "Crítica", "high": "Alta", "medium": "Média", "low": "Baixa"}


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _fmt_date(value: Any) -> str:
    parsed = _date(value)
    return parsed.astimezone().strftime("%d/%m/%Y %H:%M:%S") if parsed else "—"


def _filtered(items: list[dict[str, Any]], field: str, since: datetime | None) -> list[dict[str, Any]]:
    if since is None:
        return items
    return [item for item in items if (stamp := _date(item.get(field))) is not None and stamp >= since]


def _source(event: dict[str, Any]) -> str:
    return SOURCES.get(event.get("source"), event.get("source") or "Desconhecida")


def _vital_chart(measurements: list[dict[str, Any]], metric: str, heading: str, unit: str) -> None:
    rows = []
    for entry in measurements:
        value = entry.get(metric)
        when = _date(entry.get("measured_at"))
        if isinstance(value, (float, int)) and when is not None:
            rows.append({"Horário": when, heading: float(value)})
    st.markdown(f"**{heading} ({unit})**")
    if not rows:
        st.caption("Sem medições disponíveis para este indicador no período.")
        return
    frame = pd.DataFrame(rows).sort_values("Horário").set_index("Horário")
    st.line_chart(frame, height=200, width="stretch")
    st.caption(f"Última medição no período: {frame.iloc[-1, 0]:g} {unit}")


def _linked_sources(payload: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> None:
    supplied = payload.get("source_events", [])
    indexed = {str(item.get("event_id")): item for item in supplied if isinstance(item, dict)}
    for event_id in payload.get("source_event_ids", []):
        source_event = lookup.get(event_id)
        snapshot = indexed.get(str(event_id), {})
        info = source_event or snapshot
        with st.container(border=True):
            st.markdown(f"**{SOURCES.get(info.get('source'), info.get('source', 'Evento'))}** · `{info.get('event_type', 'sem tipo')}`")
            st.caption(f"{_fmt_date(info.get('occurred_at'))} · ID `{event_id}`")
            if source_event:
                st.write(source_event.get("title") or source_event.get("description") or "Evento registrado")
                with st.expander("Payload do evento", expanded=False):
                    st.json(source_event.get("payload") or {})
            else:
                st.caption("Detalhes obtidos da correlação; evento original fora da consulta atual.")


def render_multimodal_dashboard(
    api_request: Callable[..., Any],
    load_patients: Callable[[], list[dict[str, Any]]],
) -> None:
    """Render the replacement content inside `with multimodal_tab:`."""
    st.header("Centro de monitoramento multimodal")
    st.caption("Dados exclusivamente sintéticos · coocorrência temporal não indica causalidade nem diagnóstico")

    patients = load_patients()
    if not patients:
        st.info("Cadastre um paciente fictício na aba Pacientes para iniciar o monitoramento.")
        return

    options = {f"{p['code']} · {p['alias']}": p["id"] for p in patients}
    top_left, top_middle, top_right = st.columns([2.7, 1.4, 1])
    with top_left:
        selection = st.selectbox("Paciente sintético", list(options), key="v2_selected_patient")
    with top_middle:
        period = st.selectbox("Período", ["Todos", "Últimas 24h", "Últimos 7 dias", "Últimos 30 dias"], key="v2_period")
    with top_right:
        st.write("")
        st.write("")
        if st.button("Atualizar dados", width="stretch", key="v2_refresh"):
            st.rerun()

    patient_id = options[selection]
    since = {
        "Todos": None,
        "Últimas 24h": timedelta(days=1),
        "Últimos 7 dias": timedelta(days=7),
        "Últimos 30 dias": timedelta(days=30),
    }[period]
    since = datetime.now(timezone.utc) - since if since is not None else None

    events_raw = api_request("GET", "/events", params={"patient_id": patient_id, "limit": 500})
    alerts_raw = api_request("GET", "/alerts", params={"patient_id": patient_id, "limit": 500})
    measurements_raw = api_request("GET", f"/patients/{patient_id}/measurements", params={"limit": 500})
    if any(x is None for x in (events_raw, alerts_raw, measurements_raw)):
        st.error("Não foi possível carregar os dados do paciente. Verifique se a API está disponível.")
        return

    events = _filtered(events_raw, "occurred_at", since)
    alerts = _filtered(alerts_raw, "created_at", since)
    measurements = _filtered(measurements_raw, "measured_at", since)
    correlations = [e for e in events if e.get("source") == "multimodal_correlation"]
    source_events = [e for e in events if e.get("source") != "multimodal_correlation"]
    triples = [e for e in correlations if (e.get("payload") or {}).get("source_count") == 3]
    open_alerts = [a for a in alerts if a.get("status") == "open"]

    if any(len(x) == 500 for x in (events_raw, alerts_raw, measurements_raw)):
        st.info("A API retornou o limite de 500 registros em ao menos uma consulta. Valores e gráficos podem representar apenas os mais recentes.")

    kpis = [
        ("Eventos de origem", len(source_events)),
        ("Correlações", len(correlations)),
        ("Correlações de 3 fontes", len(triples)),
        ("Alertas abertos", len(open_alerts)),
        ("Medições", len(measurements)),
    ]
    for column, (label, value) in zip(st.columns(5), kpis):
        column.metric(label, value)

    summary_tab, vitals_tab, correlation_tab, timeline_tab, alerts_tab = st.tabs([
        "Visão executiva", "Tendências vitais", "Explorador de correlações", "Linha do tempo", "Alertas"
    ])

    with summary_tab:
        st.subheader("Distribuição dos eventos")
        left, right = st.columns([1.4, 1])
        with left:
            counts = Counter(_source(e) for e in source_events)
            if counts:
                frame = pd.DataFrame([{"Origem": name, "Eventos": count} for name, count in sorted(counts.items())])
                st.bar_chart(frame, x="Origem", y="Eventos", height=310, width="stretch")
            else:
                st.info("Nenhum evento de origem no período selecionado.")
        with right:
            severity_counts = Counter(SEVERITIES.get(e.get("severity"), e.get("severity") or "N/D") for e in source_events)
            st.markdown("**Severidade dos eventos de origem**")
            if severity_counts:
                frame = pd.DataFrame([{"Severidade": k, "Eventos": v} for k, v in severity_counts.items()])
                st.bar_chart(frame, x="Severidade", y="Eventos", height=275, width="stretch")
            else:
                st.caption("Sem eventos para análise de severidade.")
        st.markdown("**Atividade recente**")
        recent = sorted(source_events, key=lambda e: _date(e.get("occurred_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:8]
        if recent:
            st.dataframe([{"Quando": _fmt_date(e.get("occurred_at")), "Origem": _source(e), "Evento": e.get("title") or e.get("event_type"), "Severidade": SEVERITIES.get(e.get("severity"), e.get("severity"))} for e in recent], hide_index=True, width="stretch")
        else:
            st.info("Nenhuma atividade recente.")

    with vitals_tab:
        st.subheader("Evolução dos sinais vitais")
        st.caption("Valores fictícios provenientes de medições persistidas; gráficos não constituem interpretação clínica.")
        c1, c2 = st.columns(2)
        with c1:
            _vital_chart(measurements, "heart_rate_bpm", "Frequência cardíaca", "bpm")
            _vital_chart(measurements, "systolic_mmhg", "Pressão sistólica", "mmHg")
        with c2:
            _vital_chart(measurements, "spo2_percent", "Saturação de oxigênio", "%")
            _vital_chart(measurements, "diastolic_mmhg", "Pressão diastólica", "mmHg")
        with st.expander("Consultar medições", expanded=False):
            st.dataframe(measurements, width="stretch", hide_index=True)

    with correlation_tab:
        st.subheader("Correlação temporal")
        st.caption("A análise relaciona eventos de um mesmo paciente dentro da janela selecionada. Não determina causa ou risco clínico.")
        action_col, slider_col = st.columns([1, 2])
        with slider_col:
            window = st.slider("Janela de correlação (minutos)", 1, 60, 5, key="v2_window")
        with action_col:
            st.write("")
            if st.button("Executar correlação v2", type="primary", width="stretch", key="v2_run"):
                result = api_request("POST", f"/patients/{patient_id}/correlations/run-v2", params={"window_minutes": window})
                if result is not None:
                    st.session_state["v2_last_run"] = {"patient": patient_id, "new": len(result)}
                    st.rerun()
        last = st.session_state.get("v2_last_run")
        if last and last.get("patient") == patient_id:
            if last["new"]:
                st.success(f"Última execução criou {last['new']} correlação(ões).")
            else:
                st.info("Última execução não criou novas correlações. Os eventos podem já ter sido correlacionados ou estar fora da janela.")
        if not correlations:
            st.info("Nenhuma correlação registrada no período. Processe fontes sintéticas e execute a correlação.")
        else:
            only_triples = st.checkbox("Somente correlações com 3 fontes", key="v2_only_triples")
            visible = [c for c in correlations if (c.get("payload") or {}).get("source_count") == 3] if only_triples else correlations
            visible = sorted(visible, key=lambda e: _date(e.get("occurred_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            st.dataframe([{
                "Data": _fmt_date(c.get("occurred_at")),
                "Fontes": " + ".join((c.get("payload") or {}).get("sources") or []),
                "Qtd.": (c.get("payload") or {}).get("source_count", "—"),
                "Intervalo (s)": (c.get("payload") or {}).get("time_span_seconds", "—"),
                "Regra": (c.get("payload") or {}).get("rule_version", "—"),
            } for c in visible], width="stretch", hide_index=True)
            if visible:
                chosen = st.selectbox(
                    "Detalhar correlação",
                    options=list(range(len(visible))),
                    format_func=lambda i: f"{_fmt_date(visible[i].get('occurred_at'))} · {' + '.join((visible[i].get('payload') or {}).get('sources') or [])} · {visible[i]['id'][:8]}",
                    key="v2_correlation_choice",
                )
                item = visible[chosen]
                payload = item.get("payload") or {}
                st.markdown("**Eventos que compõem a correlação**")
                lookup = {e["id"]: e for e in source_events}
                _linked_sources(payload, lookup)
                with st.expander("Metadados da correlação", expanded=False):
                    st.json({"id": item["id"], "event_type": item.get("event_type"), "occurred_at": item.get("occurred_at"), "payload": payload})

    with timeline_tab:
        st.subheader("Linha do tempo unificada")
        selected_sources = st.multiselect("Filtrar origens", sorted({_source(e) for e in events}), default=sorted({_source(e) for e in events}), key="v2_timeline_sources")
        rows = [e for e in events if _source(e) in selected_sources]
        rows.sort(key=lambda e: _date(e.get("occurred_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        if not rows:
            st.info("Nenhum evento com esses filtros.")
        else:
            st.dataframe([{
                "Quando": _fmt_date(e.get("occurred_at")),
                "Origem": _source(e),
                "Severidade": SEVERITIES.get(e.get("severity"), e.get("severity")),
                "Evento": e.get("title") or e.get("event_type"),
                "Tipo técnico": e.get("event_type"),
                "ID": e.get("id"),
            } for e in rows], width="stretch", hide_index=True)
            with st.expander("Examinar evento individual", expanded=False):
                pick = st.selectbox("Evento", range(len(rows)), format_func=lambda i: f"{_fmt_date(rows[i].get('occurred_at'))} · {rows[i].get('event_type')}", key="v2_event_choice")
                st.json(rows[pick])

    with alerts_tab:
        st.subheader("Alertas registrados")
        if not alerts:
            st.info("Nenhum alerta registrado no período.")
        else:
            status = st.selectbox("Status", ["Todos", "open", "acknowledged", "resolved"], key="v2_alert_status")
            chosen = [a for a in alerts if status == "Todos" or a.get("status") == status]
            st.dataframe([{
                "Criado em": _fmt_date(a.get("created_at")),
                "Severidade": SEVERITIES.get(a.get("severity"), a.get("severity")),
                "Status": a.get("status"),
                "Mensagem": a.get("message"),
                "ID evento": a.get("event_id"),
            } for a in chosen], width="stretch", hide_index=True)

    st.caption("Escopo: no máximo 500 registros recentes por recurso. Períodos aplicam filtros aos dados retornados pela API.")

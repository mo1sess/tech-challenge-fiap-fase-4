--
-- PostgreSQL database dump
--

\restrict 1Zi6WC2h9ipCvNkwAcJ805AVpresNoGUSyQ6TbSSVpFfYeFSyEPmGjSC8buc6hL

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.alerts (
    id character varying(36) NOT NULL,
    event_id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    severity character varying(20) NOT NULL,
    status character varying(30) NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    acknowledged_at timestamp with time zone
);


ALTER TABLE public.alerts OWNER TO medguard;

--
-- Name: clinical_events; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.clinical_events (
    id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    measurement_id character varying(36),
    source character varying(50) NOT NULL,
    event_type character varying(80) NOT NULL,
    severity character varying(20) NOT NULL,
    title character varying(180) NOT NULL,
    description text NOT NULL,
    payload json NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.clinical_events OWNER TO medguard;

--
-- Name: clinical_measurements; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.clinical_measurements (
    id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    measured_at timestamp with time zone NOT NULL,
    heart_rate_bpm double precision,
    spo2_percent double precision,
    systolic_mmhg double precision,
    diastolic_mmhg double precision,
    source character varying(80) NOT NULL,
    is_synthetic boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.clinical_measurements OWNER TO medguard;

--
-- Name: media_files; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.media_files (
    id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    kind character varying(20) NOT NULL,
    original_filename character varying(255) NOT NULL,
    content_type character varying(120) NOT NULL,
    storage_path character varying(500) NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    is_synthetic boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.media_files OWNER TO medguard;

--
-- Name: patient_movements; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.patient_movements (
    id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    from_location character varying(80) NOT NULL,
    to_location character varying(80) NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    is_synthetic boolean NOT NULL
);


ALTER TABLE public.patient_movements OWNER TO medguard;

--
-- Name: patients; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.patients (
    id character varying(36) NOT NULL,
    code character varying(50) NOT NULL,
    alias character varying(120) NOT NULL,
    birth_year integer,
    notes text,
    is_synthetic boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.patients OWNER TO medguard;

--
-- Name: prescriptions; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.prescriptions (
    id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    medication_code character varying(80) NOT NULL,
    action character varying(30) NOT NULL,
    notes text,
    recorded_at timestamp with time zone NOT NULL,
    is_synthetic boolean NOT NULL
);


ALTER TABLE public.prescriptions OWNER TO medguard;

--
-- Name: processing_jobs; Type: TABLE; Schema: public; Owner: medguard
--

CREATE TABLE public.processing_jobs (
    id character varying(36) NOT NULL,
    patient_id character varying(36) NOT NULL,
    media_file_id character varying(36),
    job_type character varying(50) NOT NULL,
    status character varying(30) NOT NULL,
    progress double precision NOT NULL,
    result json NOT NULL,
    error text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.processing_jobs OWNER TO medguard;

--
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.alerts (id, event_id, patient_id, severity, status, message, created_at, acknowledged_at) FROM stdin;
b7f695ad-b51e-44ab-b04f-bb4fb1de1f41	583894af-bfc1-42b6-9c5a-7a11770a2996	88523c7e-5ae1-4091-ae11-1332ad555f9b	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-10 19:07:13.542764+00	\N
0b8b4d07-83aa-44c9-958b-c66364d2cc05	8341651a-64a6-4699-9c77-f6fa0ce668d3	88523c7e-5ae1-4091-ae11-1332ad555f9b	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-12 17:28:25.342736+00	\N
01679a98-9b60-4ccf-aa62-ba0b24152547	ec744039-9e8a-4dad-b3fb-90af5532e7f2	88523c7e-5ae1-4091-ae11-1332ad555f9b	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-12 17:47:45.834057+00	\N
4a3c96c1-e103-4dd0-8c13-e41fc6fc52de	cc6f1191-6f7a-4d57-abf3-0bdf81d6fc16	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Baixa variacao de movimento no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-12 18:24:07.256713+00	\N
c13d0bd8-d0c2-4c21-9f3e-9e9e37eeaa63	d9e9cc87-0c48-417d-82a8-166e5f5b52bd	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Baixa variacao de movimento no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-13 01:53:24.038856+00	\N
ce556e75-b56e-4efb-a919-c0eb2c1813b9	cb33712e-cfa7-4122-bae0-4e814bf446c9	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Baixa variacao de movimento no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-13 01:53:38.105039+00	\N
4800c90a-356b-477a-b01f-c41d90ec4f7b	e390e06b-822e-417d-b964-8e6356c1f6c5	88523c7e-5ae1-4091-ae11-1332ad555f9b	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-13 01:53:58.310087+00	\N
6936f3cc-f076-4971-ab67-ebbca8f79130	ce404752-5a88-4aaa-96ea-30716e2f2a63	88523c7e-5ae1-4091-ae11-1332ad555f9b	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-13 01:54:47.046942+00	\N
0964767b-993c-4f6e-9552-1ffa81f2dbd6	729e5424-d46e-4da7-8f40-7bc9299d1436	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Baixa variacao de movimento no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-13 01:57:26.02422+00	\N
5e9c69ea-6f33-4636-8423-10729bea3098	30d3e95c-b0ec-41cd-8234-b814f3f0d31f	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Mudanca visual abrupta no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-13 01:57:26.028474+00	\N
27d705d7-01ac-4a46-ac88-40ad1f06b5d9	52224c4f-6e2a-459f-a98f-3c722e48738f	88523c7e-5ae1-4091-ae11-1332ad555f9b	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-13 01:59:11.104641+00	\N
88346f57-9459-477b-98c9-bf8e4e9d54ef	8e6ac4d0-27e6-4c95-ba3f-7c83c0838470	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Baixa variacao de movimento no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-13 02:05:01.955903+00	\N
3bc2af74-c0b5-4376-ab87-e3f218e961ee	15f49f57-a890-4580-b875-c4846ea73642	5d0f19a5-2537-4b32-a95b-186221f450fb	high	open	Revisar evento demonstrativo de video: Mudanca visual abrupta no video sintetico. Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude.	2026-11-13 02:05:01.962874+00	\N
af965bc9-4a96-498a-9c75-a18af1bb02a9	36f39ab2-1083-4158-a83c-61f1558ca973	5d0f19a5-2537-4b32-a95b-186221f450fb	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-13 02:06:04.683991+00	\N
4e942f41-7fd2-4b99-8d07-f699051f76eb	39e15a99-71fd-4522-aecd-b05c131ec524	5d0f19a5-2537-4b32-a95b-186221f450fb	critical	open	Revisar evento sintetico de sinais vitais (critical). Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos.	2026-11-13 02:06:08.394212+00	\N
\.


--
-- Data for Name: clinical_events; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.clinical_events (id, patient_id, measurement_id, source, event_type, severity, title, description, payload, occurred_at, created_at) FROM stdin;
583894af-bfc1-42b6-9c5a-7a11770a2996	88523c7e-5ae1-4091-ae11-1332ad555f9b	585354db-ac6f-47b1-ad90-4f8179ee0e78	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 4 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "spo2_percent", "value": 84.0, "severity": "critical", "reason": "abaixo do limite critico demonstrativo"}, {"metric": "systolic_mmhg", "value": 78.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 48.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-10 19:07:13.52954+00	2026-11-10 19:07:13.538982+00
8341651a-64a6-4699-9c77-f6fa0ce668d3	88523c7e-5ae1-4091-ae11-1332ad555f9b	33963304-03a0-414d-9977-a88d85d8bea8	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 4 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "spo2_percent", "value": 84.0, "severity": "critical", "reason": "abaixo do limite critico demonstrativo"}, {"metric": "systolic_mmhg", "value": 78.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 48.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-12 17:28:25.272613+00	2026-11-12 17:28:25.331173+00
514a6f6f-d5bc-442a-beb5-26c3fc3ab3a9	88523c7e-5ae1-4091-ae11-1332ad555f9b	\N	audio_analysis	audio_help_request_review	low	Solicitação de ajuda identificada em áudio sintético	Expressão identificada por regras determinísticas em áudio sintético. Requer avaliação contextual e não representa diagnóstico.	{"job_id": "738cf6f9-3dc0-4aa8-9c9e-a66486081167", "media_file_id": "19d522d2-1ffb-44ca-b473-1c4d08717070", "signal": "help_request", "context": "affirmed", "findings": [{"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}], "requires_human_review": true, "analyzer": "deterministic_context_rules_v2", "disclaimer": "Evento demonstrativo. N\\u00e3o utilizar para decis\\u00f5es cl\\u00ednicas."}	2026-11-12 17:46:19.447454+00	2026-11-12 17:46:19.447462+00
ec744039-9e8a-4dad-b3fb-90af5532e7f2	88523c7e-5ae1-4091-ae11-1332ad555f9b	af96ab8c-11b0-4c7c-94e5-d076e0632dfa	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 3 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 300.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "systolic_mmhg", "value": 350.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 250.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-12 17:47:21.864+00	2026-11-12 17:47:45.828648+00
94dd5e02-ca6f-4ea5-9102-26395e00f9ca	88523c7e-5ae1-4091-ae11-1332ad555f9b	\N	multimodal_correlation	synthetic_audio_vital_correlation	low	Correlação demonstrativa entre áudio e sinais vitais	Eventos sintéticos de áudio e sinais vitais foram identificados para o mesmo paciente dentro da janela temporal configurada. A correlação não representa diagnóstico ou relação causal.	{"rule_version": "audio_vital_temporal_v1", "audio_event_id": "514a6f6f-d5bc-442a-beb5-26c3fc3ab3a9", "vital_event_id": "ec744039-9e8a-4dad-b3fb-90af5532e7f2", "source_event_ids": ["514a6f6f-d5bc-442a-beb5-26c3fc3ab3a9", "ec744039-9e8a-4dad-b3fb-90af5532e7f2"], "source_types": ["audio_help_request_review", "synthetic_vital_sign_anomaly"], "audio_signal": "help_request", "audio_occurred_at": "2026-11-12T17:46:19.447454+00:00", "vital_occurred_at": "2026-11-12T17:47:21.864000+00:00", "time_difference_seconds": 62.417, "window_minutes": 5, "requires_human_review": true, "correlation_type": "temporal_cooccurrence", "disclaimer": "Correla\\u00e7\\u00e3o educacional de dados sint\\u00e9ticos. N\\u00e3o representa diagn\\u00f3stico ou avalia\\u00e7\\u00e3o de risco cl\\u00ednico."}	2026-11-12 17:47:21.864+00	2026-11-12 17:48:11.518284+00
cc6f1191-6f7a-4d57-abf3-0bdf81d6fc16	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	sustained_low_motion	high	Baixa variacao de movimento no video sintetico	A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.	{"job_id": "906e7541-9214-45b7-a5de-15e8214cf97e", "media_file_id": "2c62beec-f6f2-4f82-b349-04394d694b94", "observed_value": 0.0671, "threshold": 0.35, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-12 18:24:07.245471+00	2026-11-12 18:24:07.245476+00
911e88b2-3301-4f60-8dce-96be202c7d48	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	audio_analysis	audio_help_request_review	low	Solicitação de ajuda identificada em áudio sintético	Expressão identificada por regras determinísticas em áudio sintético. Requer avaliação contextual e não representa diagnóstico.	{"job_id": "06999c67-d385-422f-b228-04a4a92b7461", "media_file_id": "2611c028-31ad-45e7-8fc1-317b01d76e43", "signal": "help_request", "context": "affirmed", "findings": [{"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}], "requires_human_review": true, "analyzer": "deterministic_context_rules_v2", "disclaimer": "Evento demonstrativo. N\\u00e3o utilizar para decis\\u00f5es cl\\u00ednicas."}	2026-11-12 19:02:20.57553+00	2026-11-12 19:02:20.575542+00
501857b5-fd47-421c-95dd-027ac508e9aa	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	audio_analysis	audio_help_request_review	low	Solicitação de ajuda identificada em áudio sintético	Expressão identificada por regras determinísticas em áudio sintético. Requer avaliação contextual e não representa diagnóstico.	{"job_id": "168f37c9-eb88-4286-b82e-37bbe8b2ef68", "media_file_id": "01defa4c-e549-4c3f-9768-c1840c8219c7", "signal": "help_request", "context": "affirmed", "findings": [{"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}], "requires_human_review": true, "analyzer": "deterministic_context_rules_v2", "disclaimer": "Evento demonstrativo. N\\u00e3o utilizar para decis\\u00f5es cl\\u00ednicas."}	2026-11-13 01:52:49.06945+00	2026-11-13 01:52:49.069454+00
d9e9cc87-0c48-417d-82a8-166e5f5b52bd	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	sustained_low_motion	high	Baixa variacao de movimento no video sintetico	A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.	{"job_id": "c1268633-fbc7-483e-b8ee-c35d92955faf", "media_file_id": "5daa47fa-1713-441a-a140-13dd94c1c609", "observed_value": 0.0671, "threshold": 0.35, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-13 01:53:24.035643+00	2026-11-13 01:53:24.03565+00
cb33712e-cfa7-4122-bae0-4e814bf446c9	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	sustained_low_motion	high	Baixa variacao de movimento no video sintetico	A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.	{"job_id": "6cc4c70a-3db2-4184-b642-bc9cead422d5", "media_file_id": "cd12c996-7a3e-47c4-a5f3-59b8814a9c48", "observed_value": 0.0671, "threshold": 0.35, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-13 01:53:38.10282+00	2026-11-13 01:53:38.102826+00
e390e06b-822e-417d-b964-8e6356c1f6c5	88523c7e-5ae1-4091-ae11-1332ad555f9b	add938de-933a-4f07-b02d-c726d26f5a69	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 4 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "spo2_percent", "value": 84.0, "severity": "critical", "reason": "abaixo do limite critico demonstrativo"}, {"metric": "systolic_mmhg", "value": 78.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 48.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-13 01:53:58.297659+00	2026-11-13 01:53:58.308372+00
49b3f4f1-1b0a-4b84-884e-d79119603cd9	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["501857b5-fd47-421c-95dd-027ac508e9aa", "cb33712e-cfa7-4122-bae0-4e814bf446c9"], "sources": ["audio", "video"], "source_events": [{"event_id": "501857b5-fd47-421c-95dd-027ac508e9aa", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:52:49.069450+00:00"}, {"event_id": "cb33712e-cfa7-4122-bae0-4e814bf446c9", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T01:53:38.102820+00:00"}], "source_count": 2, "time_span_seconds": 49.033, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:53:38.10282+00	2026-11-13 01:54:28.710819+00
48a143ec-0ae8-4c0c-9da3-749d1c1b6550	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["501857b5-fd47-421c-95dd-027ac508e9aa", "d9e9cc87-0c48-417d-82a8-166e5f5b52bd"], "sources": ["audio", "video"], "source_events": [{"event_id": "501857b5-fd47-421c-95dd-027ac508e9aa", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:52:49.069450+00:00"}, {"event_id": "d9e9cc87-0c48-417d-82a8-166e5f5b52bd", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T01:53:24.035643+00:00"}], "source_count": 2, "time_span_seconds": 34.966, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:53:24.035643+00	2026-11-13 01:54:28.713255+00
ce404752-5a88-4aaa-96ea-30716e2f2a63	88523c7e-5ae1-4091-ae11-1332ad555f9b	e5caad93-a94e-4d36-adf3-99deb010e4e2	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 4 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "spo2_percent", "value": 84.0, "severity": "critical", "reason": "abaixo do limite critico demonstrativo"}, {"metric": "systolic_mmhg", "value": 78.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 48.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-13 01:54:47.040566+00	2026-11-13 01:54:47.044877+00
43f7d7b5-dc40-4088-b651-9cf29fe9a7ef	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	audio_analysis	audio_help_request_review	low	Solicitação de ajuda identificada em áudio sintético	Expressão identificada por regras determinísticas em áudio sintético. Requer avaliação contextual e não representa diagnóstico.	{"job_id": "30bb52dc-5196-4aa2-a510-800c69b6d209", "media_file_id": "e80b83ef-b9e2-44cf-b606-8965f6056bab", "signal": "help_request", "context": "affirmed", "findings": [{"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}], "requires_human_review": true, "analyzer": "deterministic_context_rules_v2", "disclaimer": "Evento demonstrativo. N\\u00e3o utilizar para decis\\u00f5es cl\\u00ednicas."}	2026-11-13 01:55:40.354099+00	2026-11-13 01:55:40.354108+00
729e5424-d46e-4da7-8f40-7bc9299d1436	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	sustained_low_motion	high	Baixa variacao de movimento no video sintetico	A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.	{"job_id": "01e42c3b-a7d2-46a3-b51a-891914816041", "media_file_id": "18e61944-1194-438f-93a8-37a075a8c635", "observed_value": 0.3348, "threshold": 0.35, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-13 01:57:26.019931+00	2026-11-13 01:57:26.019941+00
30d3e95c-b0ec-41cd-8234-b814f3f0d31f	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	abrupt_visual_change	high	Mudanca visual abrupta no video sintetico	Um intervalo apresentou variacao visual acima do limite demonstrativo configurado.	{"job_id": "01e42c3b-a7d2-46a3-b51a-891914816041", "media_file_id": "18e61944-1194-438f-93a8-37a075a8c635", "observed_value": 52.0486, "threshold": 20.0, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-13 01:57:26.026651+00	2026-11-13 01:57:26.026656+00
52224c4f-6e2a-459f-a98f-3c722e48738f	88523c7e-5ae1-4091-ae11-1332ad555f9b	2c9c262b-c67a-49dc-b53a-443582a4fb17	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 4 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 148.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "spo2_percent", "value": 84.0, "severity": "critical", "reason": "abaixo do limite critico demonstrativo"}, {"metric": "systolic_mmhg", "value": 78.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 48.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-13 01:59:11.092957+00	2026-11-13 01:59:11.102573+00
a35a7a7d-982e-4b0d-be4f-3a0a59e0c212	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["30d3e95c-b0ec-41cd-8234-b814f3f0d31f", "43f7d7b5-dc40-4088-b651-9cf29fe9a7ef"], "sources": ["audio", "video"], "source_events": [{"event_id": "43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:55:40.354099+00:00"}, {"event_id": "30d3e95c-b0ec-41cd-8234-b814f3f0d31f", "source": "video_analysis", "event_type": "abrupt_visual_change", "severity": "high", "occurred_at": "2026-11-13T01:57:26.026651+00:00"}], "source_count": 2, "time_span_seconds": 105.673, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:57:26.026651+00	2026-11-13 01:59:43.307838+00
5c204500-6e9a-441c-9ee8-46cb70ce30f2	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "729e5424-d46e-4da7-8f40-7bc9299d1436"], "sources": ["audio", "video"], "source_events": [{"event_id": "43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:55:40.354099+00:00"}, {"event_id": "729e5424-d46e-4da7-8f40-7bc9299d1436", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T01:57:26.019931+00:00"}], "source_count": 2, "time_span_seconds": 105.666, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:57:26.019931+00	2026-11-13 01:59:43.316189+00
200f7b25-21dd-4b24-9e01-5b2294bffef1	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "cb33712e-cfa7-4122-bae0-4e814bf446c9"], "sources": ["audio", "video"], "source_events": [{"event_id": "cb33712e-cfa7-4122-bae0-4e814bf446c9", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T01:53:38.102820+00:00"}, {"event_id": "43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:55:40.354099+00:00"}], "source_count": 2, "time_span_seconds": 122.251, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:55:40.354099+00	2026-11-13 01:59:43.31986+00
a3b13703-5514-466b-a368-000c0436abd9	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "d9e9cc87-0c48-417d-82a8-166e5f5b52bd"], "sources": ["audio", "video"], "source_events": [{"event_id": "d9e9cc87-0c48-417d-82a8-166e5f5b52bd", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T01:53:24.035643+00:00"}, {"event_id": "43f7d7b5-dc40-4088-b651-9cf29fe9a7ef", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:55:40.354099+00:00"}], "source_count": 2, "time_span_seconds": 136.318, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:55:40.354099+00	2026-11-13 01:59:43.323517+00
b7446046-3740-4ed1-bd02-bb93face220b	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["30d3e95c-b0ec-41cd-8234-b814f3f0d31f", "501857b5-fd47-421c-95dd-027ac508e9aa"], "sources": ["audio", "video"], "source_events": [{"event_id": "501857b5-fd47-421c-95dd-027ac508e9aa", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:52:49.069450+00:00"}, {"event_id": "30d3e95c-b0ec-41cd-8234-b814f3f0d31f", "source": "video_analysis", "event_type": "abrupt_visual_change", "severity": "high", "occurred_at": "2026-11-13T01:57:26.026651+00:00"}], "source_count": 2, "time_span_seconds": 276.957, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:57:26.026651+00	2026-11-13 01:59:43.326788+00
0dd859b1-89e7-4dc4-a75b-71ead4a71720	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["501857b5-fd47-421c-95dd-027ac508e9aa", "729e5424-d46e-4da7-8f40-7bc9299d1436"], "sources": ["audio", "video"], "source_events": [{"event_id": "501857b5-fd47-421c-95dd-027ac508e9aa", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T01:52:49.069450+00:00"}, {"event_id": "729e5424-d46e-4da7-8f40-7bc9299d1436", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T01:57:26.019931+00:00"}], "source_count": 2, "time_span_seconds": 276.95, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 01:57:26.019931+00	2026-11-13 01:59:43.330506+00
8e6ac4d0-27e6-4c95-ba3f-7c83c0838470	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	sustained_low_motion	high	Baixa variacao de movimento no video sintetico	A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.	{"job_id": "3b7fb409-f3c5-47ad-aebd-a7713bf38c41", "media_file_id": "1b3531a8-aaa1-45c2-a5c0-9ba39e9ad0bc", "observed_value": 0.3348, "threshold": 0.35, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-13 02:05:01.949977+00	2026-11-13 02:05:01.949988+00
15f49f57-a890-4580-b875-c4846ea73642	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	video_analysis	abrupt_visual_change	high	Mudanca visual abrupta no video sintetico	Um intervalo apresentou variacao visual acima do limite demonstrativo configurado.	{"job_id": "3b7fb409-f3c5-47ad-aebd-a7713bf38c41", "media_file_id": "1b3531a8-aaa1-45c2-a5c0-9ba39e9ad0bc", "observed_value": 52.0486, "threshold": 20.0, "unit": "percent_changed_pixels", "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}	2026-11-13 02:05:01.958431+00	2026-11-13 02:05:01.958438+00
74805335-f876-4675-a4c5-a6e1db1403a1	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	audio_analysis	audio_help_request_review	low	Solicitação de ajuda identificada em áudio sintético	Expressão identificada por regras determinísticas em áudio sintético. Requer avaliação contextual e não representa diagnóstico.	{"job_id": "579a7f17-d7b4-4b7e-ab6f-17ca02ae1e15", "media_file_id": "d429f99b-76d5-4e07-a34b-ad189d5742e5", "signal": "help_request", "context": "affirmed", "findings": [{"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}], "requires_human_review": true, "analyzer": "deterministic_context_rules_v2", "disclaimer": "Evento demonstrativo. N\\u00e3o utilizar para decis\\u00f5es cl\\u00ednicas."}	2026-11-13 02:05:38.091705+00	2026-11-13 02:05:38.091715+00
36f39ab2-1083-4158-a83c-61f1558ca973	5d0f19a5-2537-4b32-a95b-186221f450fb	04cd9d9c-bf2f-4208-ace2-17f1ef0e6934	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 3 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 300.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "systolic_mmhg", "value": 350.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 250.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-13 02:06:00.981+00	2026-11-13 02:06:04.682464+00
39e15a99-71fd-4522-aecd-b05c131ec524	5d0f19a5-2537-4b32-a95b-186221f450fb	a827a160-8c56-4741-b3d5-b4d9fe732b64	vital_signs	synthetic_vital_sign_anomaly	critical	Anomalia demonstrativa em sinais vitais	Foram identificadas 3 condicoes fora das faixas educacionais configuradas.	{"detections": [{"metric": "heart_rate_bpm", "value": 300.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "systolic_mmhg", "value": 350.0, "severity": "critical", "reason": "fora da faixa critica demonstrativa"}, {"metric": "diastolic_mmhg", "value": 250.0, "severity": "high", "reason": "fora da faixa de atencao demonstrativa"}], "disclaimer": "Dados e limites exclusivamente sinteticos e educacionais. O MedGuard AI nao e um dispositivo medico e nao realiza diagnosticos."}	2026-11-13 02:06:00.981+00	2026-11-13 02:06:08.392068+00
dfeb204f-46be-4068-8c52-b4a1b928202d	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["15f49f57-a890-4580-b875-c4846ea73642", "36f39ab2-1083-4158-a83c-61f1558ca973", "74805335-f876-4675-a4c5-a6e1db1403a1"], "sources": ["audio", "video", "vital"], "source_events": [{"event_id": "15f49f57-a890-4580-b875-c4846ea73642", "source": "video_analysis", "event_type": "abrupt_visual_change", "severity": "high", "occurred_at": "2026-11-13T02:05:01.958431+00:00"}, {"event_id": "74805335-f876-4675-a4c5-a6e1db1403a1", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T02:05:38.091705+00:00"}, {"event_id": "36f39ab2-1083-4158-a83c-61f1558ca973", "source": "vital_signs", "event_type": "synthetic_vital_sign_anomaly", "severity": "critical", "occurred_at": "2026-11-13T02:06:00.981000+00:00"}], "source_count": 3, "time_span_seconds": 59.023, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 02:06:00.981+00	2026-11-13 02:06:31.617263+00
dc85ad8d-9115-450c-9b5e-bb6fc051052f	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["15f49f57-a890-4580-b875-c4846ea73642", "39e15a99-71fd-4522-aecd-b05c131ec524", "74805335-f876-4675-a4c5-a6e1db1403a1"], "sources": ["audio", "video", "vital"], "source_events": [{"event_id": "15f49f57-a890-4580-b875-c4846ea73642", "source": "video_analysis", "event_type": "abrupt_visual_change", "severity": "high", "occurred_at": "2026-11-13T02:05:01.958431+00:00"}, {"event_id": "74805335-f876-4675-a4c5-a6e1db1403a1", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T02:05:38.091705+00:00"}, {"event_id": "39e15a99-71fd-4522-aecd-b05c131ec524", "source": "vital_signs", "event_type": "synthetic_vital_sign_anomaly", "severity": "critical", "occurred_at": "2026-11-13T02:06:00.981000+00:00"}], "source_count": 3, "time_span_seconds": 59.023, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 02:06:00.981+00	2026-11-13 02:06:31.620528+00
9d195cc0-989b-419b-bb28-b76d71610480	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["36f39ab2-1083-4158-a83c-61f1558ca973", "74805335-f876-4675-a4c5-a6e1db1403a1", "8e6ac4d0-27e6-4c95-ba3f-7c83c0838470"], "sources": ["audio", "video", "vital"], "source_events": [{"event_id": "8e6ac4d0-27e6-4c95-ba3f-7c83c0838470", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T02:05:01.949977+00:00"}, {"event_id": "74805335-f876-4675-a4c5-a6e1db1403a1", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T02:05:38.091705+00:00"}, {"event_id": "36f39ab2-1083-4158-a83c-61f1558ca973", "source": "vital_signs", "event_type": "synthetic_vital_sign_anomaly", "severity": "critical", "occurred_at": "2026-11-13T02:06:00.981000+00:00"}], "source_count": 3, "time_span_seconds": 59.031, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 02:06:00.981+00	2026-11-13 02:06:31.622844+00
48f02a54-79f9-4d30-974a-65b5b4958cb7	5d0f19a5-2537-4b32-a95b-186221f450fb	\N	multimodal_correlation	synthetic_multimodal_correlation_v2	low	Correlação multimodal sintética	Eventos de diferentes fontes foram identificados para o mesmo paciente dentro de uma janela temporal. Não implica causalidade ou diagnóstico.	{"rule_version": "multimodal_temporal_v2", "source_event_ids": ["39e15a99-71fd-4522-aecd-b05c131ec524", "74805335-f876-4675-a4c5-a6e1db1403a1", "8e6ac4d0-27e6-4c95-ba3f-7c83c0838470"], "sources": ["audio", "video", "vital"], "source_events": [{"event_id": "8e6ac4d0-27e6-4c95-ba3f-7c83c0838470", "source": "video_analysis", "event_type": "sustained_low_motion", "severity": "high", "occurred_at": "2026-11-13T02:05:01.949977+00:00"}, {"event_id": "74805335-f876-4675-a4c5-a6e1db1403a1", "source": "audio_analysis", "event_type": "audio_help_request_review", "severity": "low", "occurred_at": "2026-11-13T02:05:38.091705+00:00"}, {"event_id": "39e15a99-71fd-4522-aecd-b05c131ec524", "source": "vital_signs", "event_type": "synthetic_vital_sign_anomaly", "severity": "critical", "occurred_at": "2026-11-13T02:06:00.981000+00:00"}], "source_count": 3, "time_span_seconds": 59.031, "window_minutes": 5, "correlation_type": "temporal_cooccurrence", "requires_human_review": true, "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."}	2026-11-13 02:06:00.981+00	2026-11-13 02:06:31.624171+00
\.


--
-- Data for Name: clinical_measurements; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.clinical_measurements (id, patient_id, measured_at, heart_rate_bpm, spo2_percent, systolic_mmhg, diastolic_mmhg, source, is_synthetic, created_at) FROM stdin;
585354db-ac6f-47b1-ad90-4f8179ee0e78	88523c7e-5ae1-4091-ae11-1332ad555f9b	2026-11-10 19:07:13.52954+00	148	84	78	48	demo_button	t	2026-11-10 19:07:13.533066+00
33963304-03a0-414d-9977-a88d85d8bea8	88523c7e-5ae1-4091-ae11-1332ad555f9b	2026-11-12 17:28:25.272613+00	148	84	78	48	demo_button	t	2026-11-12 17:28:25.30145+00
af96ab8c-11b0-4c7c-94e5-d076e0632dfa	88523c7e-5ae1-4091-ae11-1332ad555f9b	2026-11-12 17:47:21.864+00	300	100	350	250	synthetic_simulator	t	2026-11-12 17:47:45.819846+00
add938de-933a-4f07-b02d-c726d26f5a69	88523c7e-5ae1-4091-ae11-1332ad555f9b	2026-11-13 01:53:58.297659+00	148	84	78	48	demo_button	t	2026-11-13 01:53:58.299862+00
e5caad93-a94e-4d36-adf3-99deb010e4e2	88523c7e-5ae1-4091-ae11-1332ad555f9b	2026-11-13 01:54:47.040566+00	148	84	78	48	demo_button	t	2026-11-13 01:54:47.041578+00
2c9c262b-c67a-49dc-b53a-443582a4fb17	88523c7e-5ae1-4091-ae11-1332ad555f9b	2026-11-13 01:59:11.092957+00	148	84	78	48	demo_button	t	2026-11-13 01:59:11.096189+00
04cd9d9c-bf2f-4208-ace2-17f1ef0e6934	5d0f19a5-2537-4b32-a95b-186221f450fb	2026-11-13 02:06:00.981+00	300	100	350	250	synthetic_simulator	t	2026-11-13 02:06:04.678101+00
a827a160-8c56-4741-b3d5-b4d9fe732b64	5d0f19a5-2537-4b32-a95b-186221f450fb	2026-11-13 02:06:00.981+00	300	100	350	250	synthetic_simulator	t	2026-11-13 02:06:08.390183+00
\.


--
-- Data for Name: media_files; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.media_files (id, patient_id, kind, original_filename, content_type, storage_path, sha256, size_bytes, is_synthetic, created_at) FROM stdin;
b0129ffc-0086-450e-9d45-5027932b32a4	7f3ff26e-0065-4cb6-84cb-1ccaeccd595b	audio	test_audio.wav	audio/wav	/app/storage/uploads/b0129ffc-0086-450e-9d45-5027932b32a4.wav	9709d1690bcbc7bff43bd19915efc5a1f1f418bad992e9bd446538e6a5920c61	590814	t	2026-11-10 02:04:14.85565+00
21ffe317-3788-408c-bfb4-b02ac1831527	7f3ff26e-0065-4cb6-84cb-1ccaeccd595b	audio	test_audio.wav	audio/wav	/app/storage/uploads/21ffe317-3788-408c-bfb4-b02ac1831527.wav	9709d1690bcbc7bff43bd19915efc5a1f1f418bad992e9bd446538e6a5920c61	590814	t	2026-11-10 19:08:30.852326+00
2ba4103e-73be-45ea-937e-3652bd717bd3	88523c7e-5ae1-4091-ae11-1332ad555f9b	audio	test_audio.wav	audio/wav	/app/storage/uploads/2ba4103e-73be-45ea-937e-3652bd717bd3.wav	9709d1690bcbc7bff43bd19915efc5a1f1f418bad992e9bd446538e6a5920c61	590814	t	2026-11-10 19:35:51.529801+00
1ea4926b-1b8e-40d5-8008-e182223d83cf	88523c7e-5ae1-4091-ae11-1332ad555f9b	audio	test_audio.wav	audio/wav	/app/storage/uploads/1ea4926b-1b8e-40d5-8008-e182223d83cf.wav	9709d1690bcbc7bff43bd19915efc5a1f1f418bad992e9bd446538e6a5920c61	590814	t	2026-11-10 19:35:52.734972+00
760a426b-042d-41fd-bbae-7327181eae3a	88523c7e-5ae1-4091-ae11-1332ad555f9b	audio	test_audio.wav	audio/wav	/app/storage/uploads/760a426b-042d-41fd-bbae-7327181eae3a.wav	9709d1690bcbc7bff43bd19915efc5a1f1f418bad992e9bd446538e6a5920c61	590814	t	2026-11-10 19:53:18.369583+00
0beb5cdd-f778-4326-a8c8-0bf1adc3ae4b	88523c7e-5ae1-4091-ae11-1332ad555f9b	audio	test_audio.wav	audio/wav	/app/storage/uploads/0beb5cdd-f778-4326-a8c8-0bf1adc3ae4b.wav	9709d1690bcbc7bff43bd19915efc5a1f1f418bad992e9bd446538e6a5920c61	590814	t	2026-11-10 19:53:25.178356+00
8f5c8f04-6ec2-46d4-84c7-9fba086729cf	5955b1f1-8b81-44ae-9ed4-4b7109bf20f0	audio	test_audio2.wav	audio/wav	/app/storage/uploads/8f5c8f04-6ec2-46d4-84c7-9fba086729cf.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-12 16:30:44.885823+00
123c02d4-a557-4137-9b0e-35dad7d19a26	5955b1f1-8b81-44ae-9ed4-4b7109bf20f0	audio	test_audio2.wav	audio/wav	/app/storage/uploads/123c02d4-a557-4137-9b0e-35dad7d19a26.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-12 16:41:01.941121+00
f06aaa17-0c40-4185-b756-aae4a69c9781	88523c7e-5ae1-4091-ae11-1332ad555f9b	audio	test_audio2.wav	audio/wav	/app/storage/uploads/f06aaa17-0c40-4185-b756-aae4a69c9781.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-12 17:28:53.619503+00
19d522d2-1ffb-44ca-b473-1c4d08717070	88523c7e-5ae1-4091-ae11-1332ad555f9b	audio	test_audio2.wav	audio/wav	/app/storage/uploads/19d522d2-1ffb-44ca-b473-1c4d08717070.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-12 17:45:51.394275+00
2c62beec-f6f2-4f82-b349-04394d694b94	5d0f19a5-2537-4b32-a95b-186221f450fb	video	movimento_geometrico_sintetico.avi	video/x-msvideo	/app/storage/uploads/video_demo_b5cae1a9e6f84085a59121cb235a71cb.avi	bacf1e532116e5cd3c67895816aa2f2524f3c881070a3e5a03b1d9a3a1c3280e	58944	t	2026-11-12 18:24:07.166582+00
2611c028-31ad-45e7-8fc1-317b01d76e43	5d0f19a5-2537-4b32-a95b-186221f450fb	audio	test_audio2.wav	audio/wav	/app/storage/uploads/2611c028-31ad-45e7-8fc1-317b01d76e43.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-12 19:01:57.238737+00
01defa4c-e549-4c3f-9768-c1840c8219c7	5d0f19a5-2537-4b32-a95b-186221f450fb	audio	test_audio2.wav	audio/wav	/app/storage/uploads/01defa4c-e549-4c3f-9768-c1840c8219c7.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-13 01:52:29.750385+00
5daa47fa-1713-441a-a140-13dd94c1c609	5d0f19a5-2537-4b32-a95b-186221f450fb	video	movimento_geometrico_sintetico.avi	video/x-msvideo	/app/storage/uploads/video_demo_0efba6a117a34d15881369afaf1a08f9.avi	bacf1e532116e5cd3c67895816aa2f2524f3c881070a3e5a03b1d9a3a1c3280e	58944	t	2026-11-13 01:53:23.975311+00
cd12c996-7a3e-47c4-a5f3-59b8814a9c48	5d0f19a5-2537-4b32-a95b-186221f450fb	video	movimento_geometrico_sintetico.avi	video/x-msvideo	/app/storage/uploads/video_demo_b0634ebc161b408d83bbf857814dca31.avi	bacf1e532116e5cd3c67895816aa2f2524f3c881070a3e5a03b1d9a3a1c3280e	58944	t	2026-11-13 01:53:38.068083+00
e80b83ef-b9e2-44cf-b606-8965f6056bab	5d0f19a5-2537-4b32-a95b-186221f450fb	audio	test_audio2.wav	audio/wav	/app/storage/uploads/e80b83ef-b9e2-44cf-b606-8965f6056bab.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-13 01:55:24.128797+00
18e61944-1194-438f-93a8-37a075a8c635	5d0f19a5-2537-4b32-a95b-186221f450fb	video	2025-05-15 13-25-29.mkv	video/matroska	/app/storage/uploads/18e61944-1194-438f-93a8-37a075a8c635.mkv	fb4a22954aec209fb469e0342158ffc805c0a92ce533de2de6e123b53c408cc1	7038582	t	2026-11-13 01:56:49.427572+00
1b3531a8-aaa1-45c2-a5c0-9ba39e9ad0bc	5d0f19a5-2537-4b32-a95b-186221f450fb	video	2025-05-15 13-25-29.mkv	video/matroska	/app/storage/uploads/1b3531a8-aaa1-45c2-a5c0-9ba39e9ad0bc.mkv	fb4a22954aec209fb469e0342158ffc805c0a92ce533de2de6e123b53c408cc1	7038582	t	2026-11-13 02:04:30.499918+00
d429f99b-76d5-4e07-a34b-ad189d5742e5	5d0f19a5-2537-4b32-a95b-186221f450fb	audio	test_audio2.wav	audio/wav	/app/storage/uploads/d429f99b-76d5-4e07-a34b-ad189d5742e5.wav	743c0de17a474f297d433bbe002aeee0ed68c949926bdb6504a9b0fcf52c4578	579294	t	2026-11-13 02:05:25.654797+00
\.


--
-- Data for Name: patient_movements; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.patient_movements (id, patient_id, from_location, to_location, recorded_at, is_synthetic) FROM stdin;
\.


--
-- Data for Name: patients; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.patients (id, code, alias, birth_year, notes, is_synthetic, created_at) FROM stdin;
40d56324-ae31-4356-b6f8-2bdc085e0726	Bm926XKPwLVN3ZmPckYuxIP7qLxuRtZf	string	1990	string	t	2026-11-10 01:50:11.104123+00
5955b1f1-8b81-44ae-9ed4-4b7109bf20f0	VVV	string	1990	string	t	2026-11-10 01:54:08.242991+00
7f3ff26e-0065-4cb6-84cb-1ccaeccd595b	M107-gAoRfHodHf7k3fr3noUlX4Q-7Ct76XG_05I8D	string	1900	string	t	2026-11-10 02:01:07.149855+00
88523c7e-5ae1-4091-ae11-1332ad555f9b	MG-DEMO-001	Paciente Sintetico Alfa	1985	Registro criado automaticamente para demonstracao.	t	2026-11-10 19:07:13.521742+00
5d0f19a5-2537-4b32-a95b-186221f450fb	MG-VIDEO-DEMO-001	Paciente Geometrico Sintetico	1990	Registro educacional associado a formas geometricas geradas por codigo.	t	2026-11-12 18:24:07.096007+00
\.


--
-- Data for Name: prescriptions; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.prescriptions (id, patient_id, medication_code, action, notes, recorded_at, is_synthetic) FROM stdin;
\.


--
-- Data for Name: processing_jobs; Type: TABLE DATA; Schema: public; Owner: medguard
--

COPY public.processing_jobs (id, patient_id, media_file_id, job_type, status, progress, result, error, created_at, updated_at) FROM stdin;
93b3ec8e-fc57-4598-92e6-bcadadcf9168	7f3ff26e-0065-4cb6-84cb-1ccaeccd595b	b0129ffc-0086-450e-9d45-5027932b32a4	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "Ideia do que que ele \\u00e9 usado teste 123, Michael Jordan \\u00e9 o Ghost do basquete."}, "disclaimer": "Resultado educacional de transcricao de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": [], "alert_ids": []}	\N	2026-11-10 02:04:14.878638+00	2026-11-10 02:06:39.118085+00
29c21ae2-d3a7-45c5-acbf-1de49e3d8bb0	7f3ff26e-0065-4cb6-84cb-1ccaeccd595b	21ffe317-3788-408c-bfb4-b02ac1831527	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "Ideia do que que ele \\u00e9 usado teste 123, Michael Jordan \\u00e9 o Ghost do basquete."}, "disclaimer": "Resultado educacional de transcricao de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": [], "alert_ids": []}	\N	2026-11-10 19:08:30.877348+00	2026-11-10 19:09:43.172841+00
96db5cf4-5088-48a4-a107-03fadacc9df0	88523c7e-5ae1-4091-ae11-1332ad555f9b	2ba4103e-73be-45ea-937e-3652bd717bd3	audio_analysis	queued	0	{"pipeline": {"status": "prepared_not_executed", "media_path": "/app/storage/uploads/2ba4103e-73be-45ea-937e-3652bd717bd3.wav", "components": ["azure_speech_to_text", "azure_ai_language", "librosa"], "note": "Implementacao analitica prevista para a Etapa 3; nenhum diagnostico e produzido aqui."}}	\N	2026-11-10 19:35:51.552618+00	2026-11-10 19:35:51.552622+00
a91118f2-9b40-4162-be96-b1b023cf7bc7	88523c7e-5ae1-4091-ae11-1332ad555f9b	1ea4926b-1b8e-40d5-8008-e182223d83cf	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "Ideia do que que ele \\u00e9 usado teste 123, Michael Jordan \\u00e9 o Ghost do basquete."}, "acoustic": {"duration_seconds": 6.154, "sample_rate": 48000, "channels": 1, "rms": 0.093844, "peak_amplitude": 0.998871, "silence_ratio": 0.0, "clipping_ratio": 0.0}, "disclaimer": "Resultado educacional de transcricao de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": [], "alert_ids": []}	\N	2026-11-10 19:35:52.747569+00	2026-11-10 19:36:31.144238+00
8ad567b6-4bde-43b7-a1f9-aae8bde7bc59	88523c7e-5ae1-4091-ae11-1332ad555f9b	760a426b-042d-41fd-bbae-7327181eae3a	audio_analysis	queued	0	{"pipeline": {"status": "prepared_not_executed", "media_path": "/app/storage/uploads/760a426b-042d-41fd-bbae-7327181eae3a.wav", "components": ["azure_speech_to_text", "azure_ai_language", "librosa"], "note": "Implementacao analitica prevista para a Etapa 3; nenhum diagnostico e produzido aqui."}}	\N	2026-11-10 19:53:18.395954+00	2026-11-10 19:53:18.39596+00
f986034b-df04-4f26-afe9-e16f20ae93e5	88523c7e-5ae1-4091-ae11-1332ad555f9b	0beb5cdd-f778-4326-a8c8-0bf1adc3ae4b	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "Ideia do que que ele \\u00e9 usado teste 123, Michael Jordan \\u00e9 o Ghost do basquete."}, "acoustic": {"duration_seconds": 6.154, "sample_rate": 48000, "channels": 1, "rms": 0.093844, "peak_amplitude": 0.998871, "silence_ratio": 0.0, "clipping_ratio": 0.0}, "text_analysis": {"analyzer": "deterministic_rules_v1", "matched_signals": [], "matched_expressions": [], "requires_review": false}, "disclaimer": "Resultado educacional de transcricao de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": [], "alert_ids": []}	\N	2026-11-10 19:53:25.191676+00	2026-11-10 19:53:43.059558+00
14a7b332-89ff-407e-84c2-22ca92fed97f	5955b1f1-8b81-44ae-9ed4-4b7109bf20f0	8f5c8f04-6ec2-46d4-84c7-9fba086729cf	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_rules_v1", "matched_signals": ["help_request", "pain_report"], "matched_expressions": ["preciso de ajuda", "estou com dor", "dor de cabeca"], "requires_review": true}, "disclaimer": "Resultado educacional de transcricao de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": [], "alert_ids": []}	\N	2026-11-12 16:30:44.995807+00	2026-11-12 16:31:42.068583+00
17f09b36-8405-497c-9a2f-a34bfad4892e	5955b1f1-8b81-44ae-9ed4-4b7109bf20f0	123c02d4-a557-4137-9b0e-35dad7d19a26	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_context_rules_v2", "matched_signals": ["help_request"], "matched_expressions": ["preciso de ajuda"], "requires_review": true, "findings": [{"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "nao estou com dor de cabeca eu preciso de ajuda"}, {"signal": "pain_report", "expression": "estou com dor", "context": "negated", "evidence": "nao estou com dor de cabeca eu preciso de ajuda"}, {"signal": "pain_report", "expression": "dor de cabeca", "context": "negated", "evidence": "nao estou com dor de cabeca eu preciso de ajuda"}]}, "disclaimer": "Resultado educacional de transcricao de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": [], "alert_ids": []}	\N	2026-11-12 16:41:01.991396+00	2026-11-12 16:41:21.963754+00
adc3918f-859f-4b0c-9fbb-d98ea10111b0	88523c7e-5ae1-4091-ae11-1332ad555f9b	f06aaa17-0c40-4185-b756-aae4a69c9781	audio_analysis	queued	0	{"pipeline": {"status": "prepared_not_executed", "media_path": "/app/storage/uploads/f06aaa17-0c40-4185-b756-aae4a69c9781.wav", "components": ["azure_speech_to_text", "azure_ai_language", "librosa"], "note": "Implementacao analitica prevista para a Etapa 3; nenhum diagnostico e produzido aqui."}}	\N	2026-11-12 17:28:53.662535+00	2026-11-12 17:28:53.662543+00
738cf6f9-3dc0-4aa8-9c9e-a66486081167	88523c7e-5ae1-4091-ae11-1332ad555f9b	19d522d2-1ffb-44ca-b473-1c4d08717070	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_context_rules_v2", "matched_signals": ["help_request"], "matched_expressions": ["preciso de ajuda"], "requires_review": true, "findings": [{"signal": "pain_report", "expression": "estou com dor", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "pain_report", "expression": "dor de cabeca", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}]}, "disclaimer": "Resultado educacional de analise de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": ["514a6f6f-d5bc-442a-beb5-26c3fc3ab3a9"], "alert_ids": []}	\N	2026-11-12 17:45:51.449832+00	2026-11-12 17:46:19.458438+00
906e7541-9214-45b7-a5de-15e8214cf97e	5d0f19a5-2537-4b32-a95b-186221f450fb	2c62beec-f6f2-4f82-b349-04394d694b94	video_analysis	completed	100	{"analysis": {"decoder": "opencv", "width": 320, "height": 240, "fps": 10.0, "duration_seconds": 2.0, "source_frame_count": 20, "analyzed_frame_count": 7, "sample_every_n_frames": 3, "mean_motion_percent": 0.0671, "peak_motion_percent": 0.4028, "activity_label": "very_low_motion", "anomalies": [{"code": "sustained_low_motion", "severity": "high", "title": "Baixa variacao de movimento no video sintetico", "description": "A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.", "observed_value": 0.0671, "threshold": 0.35, "unit": "percent_changed_pixels"}], "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}, "event_ids": ["cc6f1191-6f7a-4d57-abf3-0bdf81d6fc16"], "alert_ids": [null]}	\N	2026-11-12 18:24:07.178888+00	2026-11-12 18:24:07.266897+00
06999c67-d385-422f-b228-04a4a92b7461	5d0f19a5-2537-4b32-a95b-186221f450fb	2611c028-31ad-45e7-8fc1-317b01d76e43	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_context_rules_v2", "matched_signals": ["help_request"], "matched_expressions": ["preciso de ajuda"], "requires_review": true, "findings": [{"signal": "pain_report", "expression": "estou com dor", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "pain_report", "expression": "dor de cabeca", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}]}, "disclaimer": "Resultado educacional de analise de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": ["911e88b2-3301-4f60-8dce-96be202c7d48"], "alert_ids": []}	\N	2026-11-12 19:01:57.506611+00	2026-11-12 19:02:20.587702+00
168f37c9-eb88-4286-b82e-37bbe8b2ef68	5d0f19a5-2537-4b32-a95b-186221f450fb	01defa4c-e549-4c3f-9768-c1840c8219c7	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_context_rules_v2", "matched_signals": ["help_request"], "matched_expressions": ["preciso de ajuda"], "requires_review": true, "findings": [{"signal": "pain_report", "expression": "estou com dor", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "pain_report", "expression": "dor de cabeca", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}]}, "disclaimer": "Resultado educacional de analise de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": ["501857b5-fd47-421c-95dd-027ac508e9aa"], "alert_ids": []}	\N	2026-11-13 01:52:29.802052+00	2026-11-13 01:52:49.078642+00
c1268633-fbc7-483e-b8ee-c35d92955faf	5d0f19a5-2537-4b32-a95b-186221f450fb	5daa47fa-1713-441a-a140-13dd94c1c609	video_analysis	completed	100	{"analysis": {"decoder": "opencv", "width": 320, "height": 240, "fps": 10.0, "duration_seconds": 2.0, "source_frame_count": 20, "analyzed_frame_count": 7, "sample_every_n_frames": 3, "mean_motion_percent": 0.0671, "peak_motion_percent": 0.4028, "activity_label": "very_low_motion", "anomalies": [{"code": "sustained_low_motion", "severity": "high", "title": "Baixa variacao de movimento no video sintetico", "description": "A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.", "observed_value": 0.0671, "threshold": 0.35, "unit": "percent_changed_pixels"}], "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}, "event_ids": ["d9e9cc87-0c48-417d-82a8-166e5f5b52bd"], "alert_ids": [null]}	\N	2026-11-13 01:53:23.977807+00	2026-11-13 01:53:24.044623+00
6cc4c70a-3db2-4184-b642-bc9cead422d5	5d0f19a5-2537-4b32-a95b-186221f450fb	cd12c996-7a3e-47c4-a5f3-59b8814a9c48	video_analysis	completed	100	{"analysis": {"decoder": "opencv", "width": 320, "height": 240, "fps": 10.0, "duration_seconds": 2.0, "source_frame_count": 20, "analyzed_frame_count": 7, "sample_every_n_frames": 3, "mean_motion_percent": 0.0671, "peak_motion_percent": 0.4028, "activity_label": "very_low_motion", "anomalies": [{"code": "sustained_low_motion", "severity": "high", "title": "Baixa variacao de movimento no video sintetico", "description": "A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.", "observed_value": 0.0671, "threshold": 0.35, "unit": "percent_changed_pixels"}], "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}, "event_ids": ["cb33712e-cfa7-4122-bae0-4e814bf446c9"], "alert_ids": [null]}	\N	2026-11-13 01:53:38.069617+00	2026-11-13 01:53:38.105917+00
30bb52dc-5196-4aa2-a510-800c69b6d209	5d0f19a5-2537-4b32-a95b-186221f450fb	e80b83ef-b9e2-44cf-b606-8965f6056bab	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_context_rules_v2", "matched_signals": ["help_request"], "matched_expressions": ["preciso de ajuda"], "requires_review": true, "findings": [{"signal": "pain_report", "expression": "estou com dor", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "pain_report", "expression": "dor de cabeca", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}]}, "disclaimer": "Resultado educacional de analise de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": ["43f7d7b5-dc40-4088-b651-9cf29fe9a7ef"], "alert_ids": []}	\N	2026-11-13 01:55:24.143386+00	2026-11-13 01:55:40.356195+00
01e42c3b-a7d2-46a3-b51a-891914816041	5d0f19a5-2537-4b32-a95b-186221f450fb	18e61944-1194-438f-93a8-37a075a8c635	video_analysis	completed	100	{"analysis": {"decoder": "opencv", "width": 1920, "height": 1080, "fps": 60.0, "duration_seconds": 32.95, "source_frame_count": 1977, "analyzed_frame_count": 658, "sample_every_n_frames": 3, "mean_motion_percent": 0.3348, "peak_motion_percent": 52.0486, "activity_label": "very_low_motion", "anomalies": [{"code": "sustained_low_motion", "severity": "high", "title": "Baixa variacao de movimento no video sintetico", "description": "A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.", "observed_value": 0.3348, "threshold": 0.35, "unit": "percent_changed_pixels"}, {"code": "abrupt_visual_change", "severity": "high", "title": "Mudanca visual abrupta no video sintetico", "description": "Um intervalo apresentou variacao visual acima do limite demonstrativo configurado.", "observed_value": 52.0486, "threshold": 20.0, "unit": "percent_changed_pixels"}], "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}, "event_ids": ["729e5424-d46e-4da7-8f40-7bc9299d1436", "30d3e95c-b0ec-41cd-8234-b814f3f0d31f"], "alert_ids": ["0964767b-993c-4f6e-9552-1ffa81f2dbd6", null]}	\N	2026-11-13 01:56:49.556507+00	2026-11-13 01:57:26.030308+00
3b7fb409-f3c5-47ad-aebd-a7713bf38c41	5d0f19a5-2537-4b32-a95b-186221f450fb	1b3531a8-aaa1-45c2-a5c0-9ba39e9ad0bc	video_analysis	completed	100	{"analysis": {"decoder": "opencv", "width": 1920, "height": 1080, "fps": 60.0, "duration_seconds": 32.95, "source_frame_count": 1977, "analyzed_frame_count": 658, "sample_every_n_frames": 3, "mean_motion_percent": 0.3348, "peak_motion_percent": 52.0486, "activity_label": "very_low_motion", "anomalies": [{"code": "sustained_low_motion", "severity": "high", "title": "Baixa variacao de movimento no video sintetico", "description": "A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.", "observed_value": 0.3348, "threshold": 0.35, "unit": "percent_changed_pixels"}, {"code": "abrupt_visual_change", "severity": "high", "title": "Mudanca visual abrupta no video sintetico", "description": "Um intervalo apresentou variacao visual acima do limite demonstrativo configurado.", "observed_value": 52.0486, "threshold": 20.0, "unit": "percent_changed_pixels"}], "disclaimer": "Analise educacional de video sintetico. Os resultados descrevem variacao visual, nao representam avaliacao clinica e nao devem orientar cuidados de saude."}, "event_ids": ["8e6ac4d0-27e6-4c95-ba3f-7c83c0838470", "15f49f57-a890-4580-b875-c4846ea73642"], "alert_ids": ["88346f57-9459-477b-98c9-bf8e4e9d54ef", null]}	\N	2026-11-13 02:04:30.635042+00	2026-11-13 02:05:01.964866+00
579a7f17-d7b4-4b7e-ab6f-17ca02ae1e15	5d0f19a5-2537-4b32-a95b-186221f450fb	d429f99b-76d5-4e07-a34b-ad189d5742e5	audio_analysis	completed	100	{"analysis": {"transcription": {"provider": "azure_speech", "language": "pt-BR", "status": "recognized", "text": "N\\u00e3o estou com dor de cabe\\u00e7a, eu preciso de ajuda."}, "acoustic": {"duration_seconds": 6.034, "sample_rate": 48000, "channels": 1, "rms": 0.092432, "peak_amplitude": 1.0, "silence_ratio": 0.081967, "clipping_ratio": 7e-06}, "text_analysis": {"analyzer": "deterministic_context_rules_v2", "matched_signals": ["help_request"], "matched_expressions": ["preciso de ajuda"], "requires_review": true, "findings": [{"signal": "pain_report", "expression": "estou com dor", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "pain_report", "expression": "dor de cabeca", "context": "negated", "evidence": "nao estou com dor de cabeca"}, {"signal": "help_request", "expression": "preciso de ajuda", "context": "affirmed", "evidence": "eu preciso de ajuda"}]}, "disclaimer": "Resultado educacional de analise de audio sintetico. Nao constitui diagnostico ou recomendacao clinica."}, "event_ids": ["74805335-f876-4675-a4c5-a6e1db1403a1"], "alert_ids": []}	\N	2026-11-13 02:05:25.669091+00	2026-11-13 02:05:38.095507+00
\.


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: clinical_events clinical_events_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.clinical_events
    ADD CONSTRAINT clinical_events_pkey PRIMARY KEY (id);


--
-- Name: clinical_measurements clinical_measurements_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.clinical_measurements
    ADD CONSTRAINT clinical_measurements_pkey PRIMARY KEY (id);


--
-- Name: media_files media_files_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.media_files
    ADD CONSTRAINT media_files_pkey PRIMARY KEY (id);


--
-- Name: patient_movements patient_movements_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.patient_movements
    ADD CONSTRAINT patient_movements_pkey PRIMARY KEY (id);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (id);


--
-- Name: prescriptions prescriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_pkey PRIMARY KEY (id);


--
-- Name: processing_jobs processing_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_pkey PRIMARY KEY (id);


--
-- Name: ix_alerts_created_at; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_alerts_created_at ON public.alerts USING btree (created_at);


--
-- Name: ix_alerts_event_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE UNIQUE INDEX ix_alerts_event_id ON public.alerts USING btree (event_id);


--
-- Name: ix_alerts_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_alerts_patient_id ON public.alerts USING btree (patient_id);


--
-- Name: ix_alerts_severity; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_alerts_severity ON public.alerts USING btree (severity);


--
-- Name: ix_alerts_status; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_alerts_status ON public.alerts USING btree (status);


--
-- Name: ix_clinical_events_event_type; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_events_event_type ON public.clinical_events USING btree (event_type);


--
-- Name: ix_clinical_events_occurred_at; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_events_occurred_at ON public.clinical_events USING btree (occurred_at);


--
-- Name: ix_clinical_events_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_events_patient_id ON public.clinical_events USING btree (patient_id);


--
-- Name: ix_clinical_events_severity; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_events_severity ON public.clinical_events USING btree (severity);


--
-- Name: ix_clinical_events_source; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_events_source ON public.clinical_events USING btree (source);


--
-- Name: ix_clinical_measurements_measured_at; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_measurements_measured_at ON public.clinical_measurements USING btree (measured_at);


--
-- Name: ix_clinical_measurements_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_clinical_measurements_patient_id ON public.clinical_measurements USING btree (patient_id);


--
-- Name: ix_media_files_kind; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_media_files_kind ON public.media_files USING btree (kind);


--
-- Name: ix_media_files_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_media_files_patient_id ON public.media_files USING btree (patient_id);


--
-- Name: ix_patient_movements_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_patient_movements_patient_id ON public.patient_movements USING btree (patient_id);


--
-- Name: ix_patient_movements_recorded_at; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_patient_movements_recorded_at ON public.patient_movements USING btree (recorded_at);


--
-- Name: ix_patients_code; Type: INDEX; Schema: public; Owner: medguard
--

CREATE UNIQUE INDEX ix_patients_code ON public.patients USING btree (code);


--
-- Name: ix_prescriptions_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_prescriptions_patient_id ON public.prescriptions USING btree (patient_id);


--
-- Name: ix_processing_jobs_job_type; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_processing_jobs_job_type ON public.processing_jobs USING btree (job_type);


--
-- Name: ix_processing_jobs_patient_id; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_processing_jobs_patient_id ON public.processing_jobs USING btree (patient_id);


--
-- Name: ix_processing_jobs_status; Type: INDEX; Schema: public; Owner: medguard
--

CREATE INDEX ix_processing_jobs_status ON public.processing_jobs USING btree (status);


--
-- Name: alerts alerts_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.clinical_events(id);


--
-- Name: alerts alerts_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinical_events clinical_events_measurement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.clinical_events
    ADD CONSTRAINT clinical_events_measurement_id_fkey FOREIGN KEY (measurement_id) REFERENCES public.clinical_measurements(id);


--
-- Name: clinical_events clinical_events_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.clinical_events
    ADD CONSTRAINT clinical_events_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: clinical_measurements clinical_measurements_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.clinical_measurements
    ADD CONSTRAINT clinical_measurements_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: media_files media_files_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.media_files
    ADD CONSTRAINT media_files_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: patient_movements patient_movements_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.patient_movements
    ADD CONSTRAINT patient_movements_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: prescriptions prescriptions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: processing_jobs processing_jobs_media_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_media_file_id_fkey FOREIGN KEY (media_file_id) REFERENCES public.media_files(id);


--
-- Name: processing_jobs processing_jobs_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: medguard
--

ALTER TABLE ONLY public.processing_jobs
    ADD CONSTRAINT processing_jobs_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 1Zi6WC2h9ipCvNkwAcJ805AVpresNoGUSyQ6TbSSVpFfYeFSyEPmGjSC8buc6hL


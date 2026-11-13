# Arquitetura técnica

[README](../README.md) · [Diagramas](DIAGRAMS.md) · [API](API_REFERENCE.md) · [Demonstração](DEMO_GUIDE.md) · [Testes](TESTING.md)

## Visão geral e responsabilidades

Base: código da branch `feature/multimodal-dashboard`, versão declarada `0.4.0`. O sistema é um **monólito modular** educacional. A API reúne rotas, contratos, serviços e processadores no mesmo processo; Streamlit consome REST em processo separado. PostgreSQL persiste entidades e o sistema de arquivos guarda mídia. Azure Speech é a integração externa ativa. Não há fila, broker, worker distribuído, modelo treinado pelo projeto ou inferência clínica.

| Camada | Código | Responsabilidade |
|---|---|---|
| Inicialização | [app/main.py](../app/main.py) | Configuração, engine, CORS e ciclo de vida |
| HTTP | [router.py](../app/api/router.py), [routes](../app/api/routes/) | Agregação de pacientes, clínico, mídia, demos e correlação |
| Contratos | [schemas](../app/schemas/) | Pydantic, limites e serialização ORM |
| Aplicação | [services](../app/services/) | Orquestração, regras, transações, eventos e alertas |
| Processadores | [modules](../app/modules/) | Áudio e vídeo sem dependência da interface |
| Dados | [models.py](../app/db/models.py) | Oito entidades SQLAlchemy |
| Apresentação | [app.py](../dashboard/app.py), [multimodal_v2.py](../dashboard/multimodal_v2.py) | Formulários e consultas HTTP |

Fluxo ponta a ponta: cadastrar paciente → ingerir medição ou mídia → validar contrato/dependências → avaliar regras → persistir eventos e eventuais alertas → correlacionar eventos existentes → consultar pelo dashboard. Upload e processamento são requisições separadas. O dashboard não acessa o banco diretamente.

## Camada de apresentação

`dashboard/app.py` contém oito abas: `Visao geral`, `Pacientes ficticios`, `Sinais vitais`, `Analise de video`, `Analise de audio`, `Prescricoes e movimentacoes`, `Midia e jobs` e `Monitoramento multimodal`. A última integra `render_multimodal_dashboard()`; v2 não é um serviço independente.

`api_request()` usa `requests`, timeout de 20 segundos e apresenta falhas no Streamlit. Acrescenta `/api/v1` fixo a `API_BASE_URL`. Não há cache, WebSocket ou atualização periódica. Interações reexecutam o script; `Atualizar dados` chama `st.rerun()`. As abas compartilham a execução, incluindo consultas de abas fora de foco.

### Dashboard v2

- Seleção por código e alias. `load_patients()` consulta o padrão de 100 pacientes; registros além desse recorte não aparecem no seletor.
- Consulta até 500 eventos, 500 alertas e 500 medições por paciente, sem paginação adicional.
- Períodos `Todos`, `Últimas 24h`, `Últimos 7 dias` e `Últimos 30 dias` filtram localmente por `occurred_at`, `created_at` e `measured_at`, respectivamente.
- KPIs: eventos de origem, correlações, correlações de três fontes, alertas abertos e medições. Eventos de origem excluem `multimodal_correlation`; correlações incluem v1 e v2, mas somente v2 tem `source_count=3`.
- Visão executiva: barras por origem/severidade e até oito eventos de origem recentes.
- Tendências: frequência cardíaca, SpO2 e pressões sistólica/diastólica, ordenadas por data; valores ausentes não são plotados. Uma medição isolada não demonstra tendência.
- Explorador: janela inteira de 1–60 minutos, padrão 5; executa `run-v2` e informa quantas correlações foram criadas. O período visual não restringe a consulta do algoritmo.
- Detalhamento: resolve `source_event_ids` nos eventos consultados; se estiverem fora do recorte, usa os resumos de `source_events` no payload.
- Linha do tempo: reúne eventos originais e correlações, com filtro de origem e inspeção JSON.
- Alertas: tabela filtrável por status. A v2 não oferece mudança de status; a API oferece.

A interface avisa quando recebe exatamente 500 registros em algum recurso. KPIs representam o recorte consultado, não totais globais garantidos. Datas são normalizadas para UTC; a formatação usa o fuso local do processo Streamlit, que pode diferir do navegador.

## Camada de API

`create_app()` cria engine com `pool_pre_ping=True`, fábrica de sessões com `autoflush=False` e `expire_on_commit=False`. No início cria diretório de mídia, chama `Base.metadata.create_all()` e `check_schema()`; ao terminar libera a engine. SQLite usa `check_same_thread=False`; memória usa `StaticPool`.

[get_db()](../app/api/deps.py) abre sessão por requisição e fecha no `finally`. Rotas/serviços controlam commits; não há commit automático na dependência. Rotas são majoritariamente síncronas. O upload é assíncrono, mas grava diretamente no disco.

Schemas de resposta usam `from_attributes=True`. `Literal[True]` restringe entradas sintéticas de pacientes, medições, prescrições e movimentações. A marca não comprova a origem dos dados. IDs das rotas são strings, sem validação UUID. Não há autenticação/autorização.

Pydantic retorna 422; rotas usam 404 para dependências ausentes, 409 para conflitos conhecidos, 413 para tamanho e 415 para extensão. Cadastro de paciente trata `IntegrityError` com rollback e 409. Correlação v2 usa savepoint. Não existe tratador global de erros de domínio: exceções não previstas podem resultar em 500. Contratos completos em [API](API_REFERENCE.md).

## Processamento multimodal

### 1. Sinais vitais sintéticos

[clinical_flow.py](../app/services/clinical_flow.py) persiste a medição e chama [vital_signs.py](../app/services/vital_signs.py). Todos os valores podem ser nulos, conforme o schema. Regras pontuais, por prioridade:

| Campo | Condição demonstrativa | Severidade |
|---|---|---|
| `heart_rate_bpm` | `<40` ou `>140`; senão `<50` ou `>120` | `critical`; `high` |
| `spo2_percent` | `<88`; senão `<92` | `critical`; `high` |
| `systolic_mmhg` | `<80` ou `>200`; senão `<90` ou `>180` | `critical`; `high` |
| `diastolic_mmhg` | `<50` ou `>130`; senão `<60` ou `>120` | `high`; `medium` |

Detecções geram um único evento `synthetic_vital_sign_anomaly`, fonte `vital_signs`, com maior severidade e todas as detecções no payload, além de um alerta aberto.

[temporal_analysis.py](../app/services/temporal_analysis.py) consulta quatro medições sintéticas mais recentes por data e as reordena cronologicamente. Com quatro valores presentes por métrica: frequência não decrescente com aumento ≥25 gera `high`; SpO2 não crescente com queda ≥4 gera `high`; amplitude sistólica ≥35 gera `medium`. Não há duração máxima entre amostras. Consolida em `synthetic_vital_trend_anomaly`, fonte `vital_trends`, com alerta próprio. Esse tipo não é elegível na correlação v2.

Inserções podem produzir eventos para janelas sobrepostas; ingestão não é idempotente. Dados retroativos não provocam recomputação integral do histórico. Nenhuma faixa é referência clínica.

### 2. Vídeo com OpenCV

[processor.py](../app/modules/video/processor.py) usa `VideoCapture`, coleta resolução, fps, duração e quantidade de quadros. Amostra a cada três quadros, até 900 **quadros analisados**, por padrão. Não é limite de 900 quadros lidos da origem. Converte para cinza, reduz para 160×90, aplica GaussianBlur 5×5 e calcula diferença absoluta entre amostras. Binariza diferenças no limiar 25 e calcula porcentagem de pixels alterados.

Média ≤0,35% produz `sustained_low_motion`; pico ≥20% produz `abrupt_visual_change`, ambos `high`. Limiares são configuráveis e as duas anomalias podem coexistir. São necessários ao menos dois quadros analisáveis. [video_flow.py](../app/services/video_flow.py) gera evento e alerta por anomalia, guardando job, mídia, valor, limiar e unidade. Não identifica pessoas, postura, dor ou queda.

O gerador cria por padrão AVI MJPG de 2 segundos, 10 fps, 320×240, com retângulo e marca `SYNTHETIC`. Demonstra processamento visual real sem imagem pessoal.

### 3. Áudio, Azure Speech e análise local

[audio_flow.py](../app/services/audio_flow.py) executa transcrição → acústica → análise textual → eventos. [azure_speech.py](../app/modules/audio/azure_speech.py) valida extensão, arquivo e credenciais; usa `SpeechRecognizer`, idioma `pt-BR`, `recognize_once_async().get()`. `RecognizedSpeech` retorna texto; `NoMatch` retorna vazio e pode concluir sem evento. Cancelamento ou resultado inesperado gera `AudioTranscriptionError`. Não há transcrição contínua ou diarização.

[acoustic.py](../app/modules/audio/acoustic.py) exige WAV PCM 16 bits sem compressão e amostras válidas. Normaliza por 32768 e calcula duração, taxa, canais, RMS global, pico, silêncio e clipping. Silêncio usa RMS de janelas de 100 ms abaixo de 0,01, com média dos canais; clipping usa amplitude absoluta ≥0,999. Métricas não geram eventos por si mesmas. A validação acústica acontece depois da chamada Azure no serviço atual.

[text_analysis.py](../app/modules/audio/text_analysis.py) separa sentenças, normaliza caixa/acentos e procura expressões fixas de `help_request`, `pain_report` e `breathing_report`. Não usa LLM. Classifica negação nos cinco tokens anteriores e marcadores de terceiros/histórico na sentença. `nao consigo respirar` é afirmativa por regra especial anterior às demais verificações. São heurísticas limitadas em ambiguidades e contexto.

[audio_event_flow.py](../app/services/audio_event_flow.py) cria um evento `low` por categoria afirmativa no job: `audio_help_request_review`, `audio_pain_report_review`, `audio_breathing_report_review`. Guarda achados, job, mídia e revisão humana. Negação, histórico e terceiros não geram esses eventos. Terceiros podem marcar `requires_review` na análise textual, sem evento persistido. Áudio não cria alertas. Transcrição e métricas ficam em `ProcessingJob.result.analysis`.

### 4. Prescrições fictícias

[prescription_flow.py](../app/services/prescription_flow.py) compara com o último registro do paciente para o mesmo `medication_code`, por `recorded_at`. `started`/`changed` significam ativo. `started` sobre ativo produz `duplicate_start`; `changed`/`stopped` sem ativo produz `action_without_active_prescription`. Cria evento `synthetic_prescription_sequence_anomaly`, fonte `prescription_analysis`, e alerta `medium`.

`POST /prescriptions` somente registra; `/prescriptions/evaluate` registra e avalia. Não há dosagem, interações ou validação farmacológica. Códigos são comparados como enviados. Não há reconstrução histórica para dados retroativos.

### 5. Movimentações fictícias

[movement_flow.py](../app/services/movement_flow.py) remove espaços das extremidades e compara locais com `casefold()`. Detecta origem igual a destino (`medium`), origem diferente do destino anterior (`high`) e intervalo não negativo menor que 120 segundos (`medium`). Consolida em evento `synthetic_movement_sequence_anomaly`, fonte `movement_analysis`, com maior severidade e um alerta. Não rastreia sensores/localização real. Usa o último registro por data, sem reconstrução histórica para inserções retroativas.

### 6. Normalização de eventos

`ClinicalEvent` reúne paciente, fonte, tipo, severidade, título, descrição, payload e datas. `measurement_id` é FK opcional. Jobs, mídias, prescrições, movimentos e eventos de origem são referenciados em JSON, sem FKs nesses vínculos.

Medições usam sua data; eventos de mídia usam o horário padrão de criação do evento, não um instante capturado do conteúdo. Correlações usam a data da origem mais recente. Isso limita a interpretação de mídias antigas carregadas posteriormente.

### 7. Gerenciamento de alertas

`Alert` referencia evento e paciente, com status inicial `open`; `event_id` único permite no máximo um alerta por evento. Sinais vitais, tendências, vídeo e anomalias operacionais geram alertas. Áudio e correlações v1/v2 não geram alertas. Não há envio de e-mail/SMS.

`PATCH /alerts/{alert_id}` aceita `acknowledged` ou `resolved`, sem máquina de transições. Reconhecer define `acknowledged_at`; resolver não cria `resolved_at` nem remove reconhecimento anterior. Não existe identificação de operador ou histórico completo.

## Correlação multimodal v2

Implementação: [correlation_v2.py](../app/services/correlation_v2.py). Representa **coocorrência temporal**, sem inferência de causalidade, risco ou diagnóstico.

### Elegibilidade

Exige paciente existente e sintético; janela inteira 1–60 minutos, padrão 5. Consulta até 30 eventos elegíveis por fonte, do mesmo paciente, por data decrescente e ID crescente:

| Fonte | Tipos |
|---|---|
| `audio_analysis` | `audio_help_request_review`, `audio_pain_report_review`, `audio_breathing_report_review` |
| `video_analysis` | `sustained_low_motion`, `abrupt_visual_change` |
| `vital_signs` | `synthetic_vital_sign_anomaly` |

Exclui tendências, prescrições, movimentações e correlações como origens. A janela compara eventos entre si; não significa os últimos cinco minutos em relação ao instante atual. Eventos históricos próximos entre si podem ser correlacionados, se estiverem no recorte.

### Deduplicação, trios e pares

Após limitar a consulta a 30, agrupa vídeo por `payload.job_id`. Escolhe maior severidade (`critical > high > medium > low`), depois ocorrência mais recente e menor ID em empate. Eventos sem job ficam independentes. Não remove eventos originais ou alertas. Limitar antes de agrupar pode reduzir o número de jobs representados.

Enumera áudio × vídeo × sinais vitais. Aceita trio quando `max(occurred_at) - min(occurred_at) <= window_minutes * 60`, incluindo a borda. Datas sem fuso são interpretadas como UTC; demais são convertidas para UTC.

Depois enumera áudio–vídeo e vídeo–sinais vitais; descarta pares que sejam subconjuntos de trio elegível nessa execução. Áudio–sinais vitais sem vídeo pertence à **v1**, em [correlation_flow.py](../app/services/correlation_flow.py), que consulta até 100 por fonte e deduplica logicamente pelo par, sem chave única v2.

A escolha é determinística para os mesmos dados, datas e IDs. Não seleciona apenas o vizinho mais próximo: múltiplas combinações podem ser persistidas. Novas origens podem alterar as combinações elegíveis.

### Fingerprint, SHA-256 e unicidade

`source_event_ids` guarda IDs de origem ordenados. O fingerprint serializa JSON compacto com separadores `(',', ':')`:

```text
["synthetic_multimodal_correlation_v2", patient_id, sorted(source_event_ids)]
```

Aplica SHA-256 aos bytes UTF-8 e guarda 64 caracteres hexadecimais em `ClinicalEvent.correlation_key`. É identidade da combinação, não assinatura de segurança ou análise do conteúdo. A janela não participa da chave: mudar a janela não duplica o mesmo conjunto.

A coluna tem índice único e permite `NULL` em outros eventos e duplicatas históricas. É interna: **não aparece em `EventRead`**. A API expõe rastreabilidade por `payload.source_event_ids` e resumos `source_events`. O payload inclui `rule_version=multimodal_temporal_v2`, `sources` (`audio`, `video`, `vital`), `source_count`, `time_span_seconds`, `window_minutes`, revisão humana e `correlation_type=temporal_cooccurrence`.

Evento derivado: fonte `multimodal_correlation`, tipo `synthetic_multimodal_correlation_v2`, severidade `low`, data da origem mais recente. Não soma severidades e não cria alerta.

### Repetição e conflitos concorrentes

Consulta correlações v2 anteriores e monta conjuntos pelos IDs dos payloads. Ignora combinações existentes. Cada inserção usa `begin_nested()`/`flush()`: se outra requisição inserir primeiro, o índice único provoca `IntegrityError`; o savepoint é revertido e a transação externa continua. Ao final faz commit e retorna só eventos novos. `[]` pode significar repetição, ausência de fontes ou distância temporal excessiva.

O tratamento captura `IntegrityError` de forma ampla, sem distinguir a restrição. Os testes demonstram unicidade, mas não provam concorrência PostgreSQL sob carga. Se já houver um par e depois surgir uma terceira fonte, pode criar o trio e manter o par histórico. Não exclui nem funde correlações anteriores.

### Limitações

- Até 30 eventos por fonte, sem paginação; histórico mais antigo pode ficar de fora.
- Até 27.000 trios candidatos antes de filtrar; nenhum benchmark foi medido nesta documentação.
- Não cruza semanticamente texto e imagem nem sincroniza amostras/dispositivos.
- Usa datas de persistência para mídia; não alinha o instante de captura original.
- Só vídeo tem deduplicação por job. Diferentes categorias de áudio no mesmo job podem gerar combinações distintas.
- Reingestões com novos IDs não são deduplicadas pelo conteúdo.
- Não atualiza correlações antigas quando janela, regra ou fontes mudam.

## Persistência e migração

PostgreSQL 16 via psycopg é o banco do Compose; sem configuração `Settings` usa SQLite local. IDs UUID são gerados pela aplicação em `String(36)`. Datas usam `DateTime(timezone=True)` e payloads usam JSON genérico. Status e severidade são strings: enums Python não constituem automaticamente restrições enum PostgreSQL. Não há `relationship()` ORM ou política explícita de cascata.

| Entidade/tabela | Dados e vínculos |
|---|---|
| `Patient` / `patients` | Código único, alias, ano fictício, marca sintética |
| `ClinicalMeasurement` / `clinical_measurements` | FK paciente, valores, data |
| `MediaFile` / `media_files` | FK paciente, caminho, tipo, SHA-256, tamanho |
| `ProcessingJob` / `processing_jobs` | FK paciente e mídia opcional, progresso, JSON e erro |
| `Prescription` / `prescriptions` | FK paciente, código e ação |
| `PatientMovement` / `patient_movements` | FK paciente, origem/destino e data |
| `ClinicalEvent` / `clinical_events` | FK paciente e medição opcional, payload e chave única |
| `Alert` / `alerts` | FK paciente e evento único, status e reconhecimento |

Hash de mídia não é único. Reenvio cria novo recurso. `storage_path` não aparece em `MediaFileRead`, mas descrições de pipeline em jobs podem mostrar caminhos. Não há download de mídia. Disco e SQL não formam transação atômica: falhas podem deixar arquivos sem registro.

### Ciclo de vida dos jobs

Upload → `queued`, 0 → processamento explícito → `processing`, 10 e commit → `completed`, 100 com resultados. Erros previstos revertem resultados em andamento e persistem `failed`, 100 e erro. Jobs `failed` podem ser tentados novamente; `processing`/`completed` retornam 409. Não há fila automática, retomada de jobs presos ou lock de banco que garanta exclusão de processamento concorrente. Exceções inesperadas podem deixar o job em `processing`.

### Migração explícita

[migrate_correlation_keys.py](../app/db/migrate_correlation_keys.py) usa transação. No PostgreSQL adquire `ACCESS EXCLUSIVE`, adiciona coluna se ausente, lê correlações v2 por `created_at, id`, limpa suas chaves e atribui fingerprint à primeira ocorrência de cada conjunto. Preserva duplicatas históricas e registros sem origens com `NULL`; cria `ix_clinical_events_correlation_key` único. O lock bloqueia acesso à tabela durante a migração.

No SQLite usa `PRAGMA table_info` e `ALTER TABLE`; outros dialetos são rejeitados. Pressupõe tabela existente, não substituindo migrações gerais versionadas. [schema.py](../app/db/schema.py) verifica coluna e índice único nessa coluna; não audita todos os tipos/dados/tabelas. Procedimento operacional no [README](../README.md#migração-segura-de-postgresql-existente), sem remoção de volumes.

## Infraestrutura

| Serviço | Configuração | Dependência/saúde |
|---|---|---|
| `db` | `postgres:16-alpine`, volume `postgres_data`, sem porta publicada | `pg_isready`, intervalo 5 s, timeout 5 s, 10 tentativas |
| `api` | Build local, porta 8000, `./storage:/app/storage` | Aguarda banco saudável; `/health`, intervalo 10 s, timeout 5 s, 10 tentativas |
| `dashboard` | Mesmo build, Streamlit, porta 8501 | Aguarda API saudável; sem health check próprio |

[docker-compose.yml](../docker-compose.yml): todos usam `restart: unless-stopped`. [Dockerfile](../Dockerfile): `python:3.12-slim`, instala `.[dev]`, copia aplicação, dashboard, testes e scripts. Código não é montado no Compose: mudanças exigem rebuild. Mídia é bind mount e PostgreSQL usa volume distinto. Parar containers preserva ambos. `/health` não consulta o banco.

### Variáveis de ambiente

| Variáveis | Uso/padrão |
|---|---|
| `APP_NAME`, `APP_ENV`, `API_PREFIX` | `MedGuard AI`, `development`, `/api/v1` |
| `DATABASE_URL` | SQLite no código; Compose constrói URL PostgreSQL com host `db` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Configuração do banco; padrões do exemplo só para desenvolvimento |
| `STORAGE_DIR` | `storage/uploads` local; `/app/storage/uploads` fixado no Compose |
| `MAX_UPLOAD_MB` | 25; leitura limitada a máximo + 1 byte |
| `VIDEO_SAMPLE_EVERY_N_FRAMES`, `VIDEO_MAX_FRAMES` | 3 e 900, validados positivos |
| `VIDEO_LOW_MOTION_THRESHOLD`, `VIDEO_ABRUPT_MOTION_THRESHOLD` | 0,35 e 20,0, em porcentagem de pixels |
| `CORS_ORIGINS` | `http://localhost:8501`; validador admite lista/string por vírgula |
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Obrigatórias para transcrição fora de mocks |
| `AZURE_LANGUAGE_ENDPOINT`, `AZURE_LANGUAGE_KEY` | Configurações sem integração ativa |
| `API_BASE_URL` | Dashboard: `http://api:8000` no Compose, localhost no código |

[Settings](../app/core/config.py) lê `.env`, ignora extras e é armazenado em cache por `get_settings()`. Alterações exigem reiniciar processos. Compose injeta variáveis explicitamente. Não publique saídas de configuração contendo segredos.

Testes usam SQLite temporário/em memória. Não demonstram integralmente locks, dialeto PostgreSQL, fusos, concorrência ou persistência de volumes. Consulte [Testes](TESTING.md).

## Decisões arquiteturais

| Escolha atual | Vantagem | Limitação/evolução possível |
|---|---|---|
| Monólito modular | Execução simples e responsabilidades legíveis | Compartilha escala/falhas; separar workers se houver necessidade medida |
| REST | OpenAPI, script e dashboard com mesmo contrato | Sem fluxo contínuo; evoluir paginação e filtros por período |
| Banco relacional | FKs, transações e unicidade | Arquivos fora da transação; testar PostgreSQL e versionar migrações |
| Streamlit | Formulários/gráficos diretos | Reexecução ampla e timeout; testar interface |
| Processamento síncrono | Resultado imediato | Requisição ocupada; fila/workers seriam implementação futura |
| Regras determinísticas | Critérios inspecionáveis e reproduzíveis | Semântica limitada; versionar e ampliar avaliação |
| Dados sintéticos | Demonstração sem dados pessoais | Não prova validade clínica ou desempenho assistencial |

Prioridades: autenticação, autorização, retenção, segredos, logs estruturados sem conteúdo sensível, testes PostgreSQL/concorrência/UI e dependências diretas travadas. Novos modelos, infraestrutura de produção e qualquer uso clínico exigem implementação e validação futuras.

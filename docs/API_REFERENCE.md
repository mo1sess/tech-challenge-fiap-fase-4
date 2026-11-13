# Referência prática da API

[README](../README.md) · [Arquitetura](ARCHITECTURE.md) · [Demonstração](DEMO_GUIDE.md)

## Convenções e contratos

Base padrão: `http://localhost:8000/api/v1`. Os caminhos abaixo são relativos a essa base, exceto `/health`. Consulte os contratos gerados em `http://localhost:8000/docs` e `http://localhost:8000/openapi.json`. Fonte: [rotas](../app/api/routes/) e [schemas](../app/schemas/).

Não há autenticação. Envie JSON com `Content-Type: application/json`, exceto upload multipart. IDs são strings geradas como UUID; substitua os valores dos exemplos pelos IDs retornados. Datas usam ISO 8601; prefira UTC explícito, como `2026-11-13T15:00:00Z`.

As listas são arrays, sem envelope ou total. Onde há `limit`, padrão 100, mínimo 1 e máximo 500; não existe `offset`/cursor. Pacientes, mídia, jobs e alertas são ordenados por criação decrescente; eventos por ocorrência; medições, prescrições e movimentos por suas datas. Empates não têm desempate uniforme em todas as rotas.

Entradas de pacientes, medições, prescrições e movimentações aceitam somente `is_synthetic=true`, com padrão verdadeiro; não é obrigatório enviar a marca explicitamente. Upload também tem padrão verdadeiro e rejeita falso. Essa declaração não verifica automaticamente se o conteúdo é fictício.

### Respostas compartilhadas

| Schema | Campos retornados |
|---|---|
| `PatientRead` | `id`, `code`, `alias`, `birth_year`, `notes`, `is_synthetic`, `created_at` |
| `MeasurementRead` | `id`, `patient_id`, `measured_at`, quatro métricas, `source`, `is_synthetic`, `created_at` |
| `EventRead` | `id`, `patient_id`, `measurement_id`, `source`, `event_type`, `severity`, `title`, `description`, `payload`, `occurred_at`, `created_at` |
| `AlertRead` | `id`, `event_id`, `patient_id`, `severity`, `status`, `message`, `created_at`, `acknowledged_at` |
| `PrescriptionRead` | `id`, `patient_id`, `medication_code`, `action`, `notes`, `recorded_at`, `is_synthetic` |
| `MovementRead` | `id`, `patient_id`, `from_location`, `to_location`, `recorded_at`, `is_synthetic` |
| `MediaFileRead` | `id`, `patient_id`, `kind`, `original_filename`, `content_type`, `sha256`, `size_bytes`, `is_synthetic`, `created_at` |
| `ProcessingJobRead` | `id`, `patient_id`, `media_file_id`, `job_type`, `status`, `progress`, `result`, `error`, `created_at`, `updated_at` |

`correlation_key` e `storage_path` não integram os schemas de evento/mídia. IDs em `payload` são referências JSON. `result` e `payload` variam por fluxo; consulte [Arquitetura](ARCHITECTURE.md).

### Erros comuns

Erros tratados pela rota usam `{"detail":"mensagem"}`; erros de validação FastAPI usam `detail` com lista de problemas. 422 inclui contrato inválido, dados não sintéticos e erros previstos de processamento. 404 significa recurso/dependência ausente nas rotas que fazem essa checagem. Exceções não previstas podem retornar 500; não há conversor global de todos os erros.

## Saúde

| Método e caminho absoluto | Objetivo | Entrada | Sucesso |
|---|---|---|---|
| `GET /health` | Identificar estado da aplicação | Nenhuma | 200, `HealthResponse` |

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Resposta ilustrativa, com data variável:

```json
{"status":"ok","service":"MedGuard AI","environment":"development","timestamp":"2026-11-13T15:00:00Z"}
```

Não consulta o banco e não substitui sua verificação de saúde.

## Pacientes

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| POST | `/patients` | Cadastrar, corpo `PatientCreate` | 201; 409 código duplicado; 422 |
| GET | `/patients` | Listar; query `limit` | 200; 422 |
| GET | `/patients/{patient_id}` | Buscar por ID obrigatório no caminho | 200; 404 |

`PatientCreate`: obrigatórios `code` (3–50 caracteres, padrão `^[A-Za-z0-9_-]+$`) e `alias` (2–120). Opcionais `birth_year` (1900–2100), `notes` (até 1000) e marca sintética.

Preparação de exemplos PowerShell:

```powershell
$base = "http://localhost:8000/api/v1"
$codigo = "MG-DOC-" + [guid]::NewGuid().ToString("N").Substring(0,8)
$body = @{code=$codigo; alias="Paciente Fictício"; birth_year=1990; is_synthetic=$true} | ConvertTo-Json
$paciente = Invoke-RestMethod -Method Post -Uri "$base/patients" -ContentType "application/json" -Body $body
$pacienteId = $paciente.id
Invoke-RestMethod "$base/patients?limit=100"
Invoke-RestMethod "$base/patients/$pacienteId"
```

POST e GET individual retornam `PatientRead`; listagem retorna array desse schema. Não há exclusão/atualização de paciente implementada.

## Medições

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| POST | `/patients/{patient_id}/measurements` | Registrar e avaliar; `MeasurementCreate` | 201; 404; 422 |
| GET | `/patients/{patient_id}/measurements` | Listar; query `limit` | 200; 404; 422 |

Todos os campos do corpo são opcionais:

| Campo | Restrição/padrão |
|---|---|
| `measured_at` | Data/hora; ausente ou nulo usa horário atual |
| `heart_rate_bpm` | Número 0–300 ou nulo |
| `spo2_percent` | Número 0–100 ou nulo |
| `systolic_mmhg` | Número 0–350 ou nulo |
| `diastolic_mmhg` | Número 0–250 ou nulo |
| `source` | Até 80 caracteres; `synthetic_simulator` |
| `is_synthetic` | Somente verdadeiro |

```powershell
$body = @{heart_rate_bpm=145; spo2_percent=90; systolic_mmhg=125; diastolic_mmhg=80; source="documentacao_sintetica"; is_synthetic=$true} | ConvertTo-Json
$resultado = Invoke-RestMethod -Method Post -Uri "$base/patients/$pacienteId/measurements" -ContentType "application/json" -Body $body
Invoke-RestMethod "$base/patients/$pacienteId/measurements?limit=100"
```

POST retorna `MeasurementIngestResponse`: `measurement`, `events`, `alerts`, `disclaimer`; GET retorna `MeasurementRead[]`. Sem anomalia, arrays podem ser vazios. O exemplo gera anomalia pontual; tendências adicionais dependem do histórico. Aceitar `{}` não implica medição útil. Repetir POST insere novo registro.

## Eventos

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| GET | `/events` | Listar eventos, query `patient_id` opcional e `limit` | 200; 422 para limite inválido |

```powershell
$eventos = Invoke-RestMethod "$base/events?patient_id=$pacienteId&limit=500"
$eventos | ConvertTo-Json -Depth 12
```

Retorna `EventRead[]`. Um filtro de paciente inexistente retorna `[]`, sem 404. Não há criação manual, edição, exclusão nem busca individual de eventos por rota própria. Severidades produzidas pelos fluxos: `low`, `medium`, `high`, `critical`.

## Alertas

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| GET | `/alerts` | Query `patient_id`, `status` opcionais e `limit` | 200; 422 para limite inválido |
| PATCH | `/alerts/{alert_id}` | Atualizar, corpo `AlertStatusUpdate` | 200; 404; 422 |

Filtro `status` é string livre; valores desconhecidos normalmente retornam lista vazia. Status persistidos pelos fluxos: `open`, `acknowledged`, `resolved`. PATCH exige `status` em `acknowledged` ou `resolved`; não aceita `open`.

```powershell
$alertas = Invoke-RestMethod "$base/alerts?patient_id=$pacienteId&status=open&limit=100"
if ($alertas.Count -gt 0) {
    $alertaId = $alertas[0].id
    Invoke-RestMethod -Method Patch -Uri "$base/alerts/$alertaId" -ContentType "application/json" -Body '{"status":"acknowledged"}'
}
```

GET retorna `AlertRead[]`; PATCH retorna `AlertRead`. Reconhecimento define `acknowledged_at`. Resolver não cria data de resolução nem apaga reconhecimento anterior; não há máquina de transições ou auditoria de operador. Áudio e correlações não criam alertas.

## Prescrições fictícias

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| POST | `/patients/{patient_id}/prescriptions` | Somente registrar, `PrescriptionCreate` | 201; 404; 422 |
| GET | `/patients/{patient_id}/prescriptions` | Listar todos do paciente, sem `limit` | 200; 404 |
| POST | `/patients/{patient_id}/prescriptions/evaluate` | Registrar e avaliar sequência | 201; 404; 422 |

Obrigatórios: `medication_code` (2–80 caracteres) e `action` (`started`, `changed`, `stopped`). Opcionais: `notes` (até 1000), `recorded_at` (atual se ausente/nulo), marca sintética. Não existem campos de dose ou fármaco real.

```powershell
$body = '{"medication_code":"MED-FICTICIO-01","action":"started","is_synthetic":true}'
Invoke-RestMethod -Method Post -Uri "$base/patients/$pacienteId/prescriptions/evaluate" -ContentType "application/json" -Body $body
Invoke-RestMethod -Method Post -Uri "$base/patients/$pacienteId/prescriptions/evaluate" -ContentType "application/json" -Body $body
Invoke-RestMethod "$base/patients/$pacienteId/prescriptions"
```

A segunda avaliação detecta início duplicado se o último estado continuar ativo. Registro simples retorna `PrescriptionRead`; avaliação retorna `prescription`, `events`, `alerts`, `disclaimer`; GET retorna `PrescriptionRead[]`. Usar `/prescriptions` sem `/evaluate` não executa o detector.

## Movimentações fictícias

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| POST | `/patients/{patient_id}/movements` | Registrar e avaliar, `MovementCreate` | 201; 404; 422 |
| GET | `/patients/{patient_id}/movements` | Listar; query `limit` | 200; 404; 422 |

Obrigatórios `from_location` e `to_location`, 2–80 caracteres cada. Opcionais `recorded_at` (atual se ausente/nulo) e marca sintética. Os limites de tamanho são validados antes do `strip()` aplicado no serviço.

```powershell
$body = '{"from_location":"ala-ficticia-a","to_location":"ala-ficticia-b","is_synthetic":true}'
Invoke-RestMethod -Method Post -Uri "$base/patients/$pacienteId/movements" -ContentType "application/json" -Body $body
Invoke-RestMethod "$base/patients/$pacienteId/movements?limit=100"
```

POST retorna `movement`, `events`, `alerts`, `disclaimer`; GET retorna `MovementRead[]`. Pode detectar origem/destino iguais, quebra de continuidade ou intervalo de transferência inferior a 120 segundos, conforme histórico. Não representa rastreamento real.

## Mídia

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| POST | `/patients/{patient_id}/media` | Upload multipart | 201; 404; 413; 415; 422 |
| GET | `/media` | Query `patient_id` opcional e `limit` | 200; 422 para limite inválido |

Multipart: `file` obrigatório; `kind` opcional (`audio`/`video`); `is_synthetic` opcional, padrão verdadeiro. Sem `kind`, infere pelo MIME e depois pela extensão. Extensões: áudio `.wav`; vídeo `.mp4`, `.mov`, `.avi`, `.mkv`. Limite padrão 25 MiB (`MAX_UPLOAD_MB * 1024 * 1024`). Extensão e declaração são verificadas no upload, não a validade integral do conteúdo.

Exemplo PowerShell com `curl.exe` (o caminho deve existir localmente):

```powershell
curl.exe -X POST "$base/patients/$pacienteId/media" -F "file=@storage/test_audio2.wav;type=audio/wav" -F "kind=audio" -F "is_synthetic=true"
Invoke-RestMethod "$base/media?patient_id=$pacienteId&limit=100"
```

Upload retorna `MediaUploadResponse`, com `media: MediaFileRead`, `job: ProcessingJobRead` em `queued` e `note`. Salva o arquivo e calcula SHA-256. Não processa automaticamente nem deduplica por hash. GET retorna `MediaFileRead[]`; filtro inexistente retorna `[]`. Sem rota de download/remoção. WAV deve ser PCM de 16 bits sem compressão para o pipeline atual; conteúdo inválido pode ser aceito no upload e falhar no processamento.

## Jobs

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| GET | `/jobs` | Query `patient_id` opcional e `limit` | 200; 422 para limite inválido |
| GET | `/jobs/{job_id}` | Buscar ID | 200; 404 |
| POST | `/jobs/{job_id}/process` | Processar de forma síncrona, sem corpo | 200; 404; 409; 422 |

```powershell
$jobs = Invoke-RestMethod "$base/jobs?patient_id=$pacienteId&limit=100"
# Escolha o ID retornado pelo upload; não reprocesse um job completed.
$jobId = "SUBSTITUA_PELO_ID_DO_UPLOAD"
Invoke-RestMethod "$base/jobs/$jobId"
Invoke-RestMethod -Method Post "$base/jobs/$jobId/process"
```

GET retorna `ProcessingJobRead` ou array. Processamento retorna `VideoJobProcessResponse` **para áudio e vídeo**, com `job`, `events`, `alerts`, `disclaimer`. Tipos aceitos: `audio_analysis` e `video_analysis`; outros retornam 422. `processing`/`completed` retornam 409; dependências ausentes também retornam 409. `failed` pode ser tentado novamente. Erros previstos de mídia/Azure retornam 422 com mensagem e job persistido como `failed`; exceções inesperadas podem gerar 500. Sem corpo, parâmetros de processamento usam configurações do servidor.

Vídeo salva `result.analysis` com metadados e métricas; áudio salva `analysis.transcription`, `analysis.acoustic`, `analysis.text_analysis`. `result.event_ids` e `result.alert_ids` referenciam recursos produzidos. Estados/progresso: `queued`/0, `processing`/10, `completed` ou `failed`/100. Progresso 100 em falha não significa sucesso.

## Correlação v1 e v2

| Método | Caminho | Objetivo/entrada | Status |
|---|---|---|---|
| POST | `/patients/{patient_id}/correlations/run` | Áudio–sinais vitais v1 | 200; 404; 422 |
| POST | `/patients/{patient_id}/correlations/run-v2` | Trios e pares com vídeo v2 | 200; 404; 422 |

Sem corpo. Query `window_minutes`: inteiro 1–60, padrão 5. Exige paciente sintético. Retorna somente `EventRead[]` **novos**, inclusive `[]` quando nada novo é elegível.

```powershell
Invoke-RestMethod -Method Post "$base/patients/$pacienteId/correlations/run?window_minutes=5"
$novas = Invoke-RestMethod -Method Post "$base/patients/$pacienteId/correlations/run-v2?window_minutes=5"
$repetidas = Invoke-RestMethod -Method Post "$base/patients/$pacienteId/correlations/run-v2?window_minutes=5"
```

A v1 consulta até 100 eventos por fonte; a v2 até 30, deduplicando vídeo por job. A v2 prioriza áudio+vídeo+vital; aceita pares áudio+vídeo e vídeo+vital não contidos em trios elegíveis. Não cria par áudio+vital sem vídeo. Ambas geram eventos `low`, sem alertas, por proximidade temporal e mesmo paciente, sem causalidade/diagnóstico.

Exemplo de **payload ilustrativo** de uma correlação v2, não uma resposta completa `EventRead`:

```json
{
  "rule_version": "multimodal_temporal_v2",
  "source_event_ids": ["id-audio", "id-video", "id-vital"],
  "sources": ["audio", "video", "vital"],
  "source_events": [
    {"event_id":"id-audio","source":"audio_analysis","event_type":"audio_help_request_review","severity":"low","occurred_at":"2026-11-13T15:00:00+00:00"},
    {"event_id":"id-video","source":"video_analysis","event_type":"sustained_low_motion","severity":"high","occurred_at":"2026-11-13T15:00:10+00:00"},
    {"event_id":"id-vital","source":"vital_signs","event_type":"synthetic_vital_sign_anomaly","severity":"critical","occurred_at":"2026-11-13T15:00:20+00:00"}
  ],
  "source_count": 3,
  "time_span_seconds": 20.0,
  "window_minutes": 5,
  "correlation_type": "temporal_cooccurrence",
  "requires_human_review": true,
  "disclaimer": "Correlacao educacional de dados sinteticos. Nao representa diagnostico ou risco clinico."
}
```

O índice único por fingerprint protege a v2; a v1 só verifica pares existentes na aplicação. Repetir v2 com as mesmas origens retorna `[]`; adicionar uma origem pode gerar novos conjuntos e não remove pares históricos. Detalhamento em [Arquitetura](ARCHITECTURE.md#correlação-multimodal-v2).

## Demonstrações

| Método | Caminho | Comportamento | Status |
|---|---|---|---|
| POST | `/demo/vital-alert` | Cria/reutiliza `MG-DEMO-001`; ingere medição anômala | 200 |
| POST | `/demo/video-alert` | Cria/reutiliza `MG-VIDEO-DEMO-001`; gera e processa AVI geométrico | 200 |

Sem corpo/parâmetros. Cada chamada cria novos registros de medição ou mídia/job; demos não são idempotentes. Falhas inesperadas podem gerar 500; essas rotas não possuem a mesma conversão de erros do processamento de jobs.

```powershell
Invoke-RestMethod -Method Post "$base/demo/vital-alert"
Invoke-RestMethod -Method Post "$base/demo/video-alert"
```

Vital retorna `DemoFlowResponse`: `patient`, `result` com medição/eventos/alertas/disclaimer. Vídeo retorna `VideoDemoResponse`: `patient`, `media`, `processing` com job/eventos/alertas/disclaimer. A medição da demo usa frequência 148, SpO2 84, sistólica 78 e diastólica 48. A demo multimodal completa é um [script](../scripts/demo_multimodal.py), não uma rota adicional.

## Limites da referência

Os comandos que gravam dados são exemplos para ambiente educacional; não são executados automaticamente por esta documentação. Não há endpoints implementados para exclusão, exportação, login, envio de notificações ou ingestão direta de eventos. OpenAPI e código são a fonte operacional dos contratos; qualquer mudança de prefixo, schema ou rota exige revisar esta referência.

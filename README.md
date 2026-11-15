# MedGuard AI

Implementação das Etapas 1 a 4 do Tech Challenge FIAP - Fase 4. O projeto oferece uma API modular em FastAPI, persistência PostgreSQL, dashboard Streamlit e fluxos ponta a ponta de sinais vitais, vídeo, áudio, prescrições e movimentações sintéticas.

> **Uso exclusivamente educacional.** O projeto aceita somente dados fictícios ou sintéticos, não é um dispositivo médico, não oferece diagnóstico e não deve apoiar decisões clínicas reais. Os limites usados no detector são exemplos de software, não referências clínicas universais.

## O que as Etapas 1–4 entregam

- API REST FastAPI com Swagger em `http://localhost:8000/docs`.
- PostgreSQL e ambiente completo via Docker Compose.
- Dashboard Streamlit em `http://localhost:8501`.
- Modelos persistentes para pacientes fictícios, mídia, jobs, medições, prescrições, eventos e alertas.
- Upload controlado de áudio e vídeo fictícios, com hash SHA-256 e job rastreável.
- Primeiro fluxo demonstrável: medição sintética → regras ilustrativas → evento → alerta.
- Processamento real de vídeo com OpenCV, extração de metadados e amostragem de quadros.
- Métricas determinísticas de movimento por diferença entre quadros, sem identificação de pessoas.
- Detecção demonstrativa de baixa variação ou mudança visual abrupta → evento → alerta.
- Job de vídeo rastreável nos estados `queued`, `processing`, `completed` e `failed`.
- Vídeo geométrico sintético gerado por código para uma demonstração reproduzível.
- Transcrição de áudio WAV sintético com Azure Speech, sem credenciais no repositório.
- Análise de sentimento da transcrição em português com Azure AI Language, com resultados por sentença.
- Extração de menções a sintomas e sinais da transcrição com Azure Text Analytics for Health, incluindo contexto quando disponível.
- Métricas acústicas locais de duração, RMS, pico, silêncio e clipping.
- Análise textual determinística com tratamento de negação, contexto histórico e terceiros.
- Eventos de revisão humana para achados afirmativos, sem alerta ou diagnóstico automático.
- Correlação temporal preliminar entre eventos sintéticos de áudio e sinais vitais.
- Análise temporal das quatro medições sintéticas mais recentes, com regras transparentes para tendências de frequência cardíaca, SpO2 e pressão sistólica.
- Verificação demonstrativa da sequência de prescrições fictícias, incluindo início duplicado e alteração ou encerramento sem registro ativo.
- Verificação demonstrativa da continuidade de movimentações fictícias, incluindo origem/destino iguais, quebra de continuidade e transferências muito próximas.
- Eventos e alertas rastreáveis para anomalias temporais e operacionais, sempre sujeitos a revisão humana.
- Testes básicos da API, proteção contra dados não sintéticos, alertas e upload.

## Arquitetura

```mermaid
flowchart LR
    UI[Dashboard Streamlit] -->|REST| API[FastAPI]
    API --> DB[(PostgreSQL)]
    API --> FS[Storage local de mídia]
    API --> VITAL[Regras sintéticas de sinais vitais]
    VITAL --> EVENT[Evento clínico normalizado]
    EVENT --> ALERT[Alerta persistido]
    API --> VIDEO[OpenCV + análise de movimento]
    VIDEO --> EVENT
    API --> AUDIO[Azure Speech + análise acústica e textual]
    AUDIO --> EVENT
    AUDIO --> LANGUAGE[Azure AI Language para sentimento e menções clínicas]
    API --> TEMPORAL[Regras temporais sintéticas]
    API --> OPERATIONS[Prescrições e movimentações fictícias]
    TEMPORAL --> EVENT
    OPERATIONS --> EVENT
```

O desenho é um monólito modular: fácil de executar agora e com limites claros para substituir cada processador por implementação assíncrona nas etapas seguintes.

## Estrutura principal

```text
app/
  api/routes/        endpoints REST
  core/              configuração
  db/                modelos SQLAlchemy
  modules/audio/     Azure Speech, Azure AI Language, análise acústica e regras textuais
  modules/video/     leitura de quadros e análise de movimento com OpenCV
  schemas/           validação e contratos da API
  services/          fluxos multimodais, temporais e operacionais até eventos/alertas
dashboard/           interface Streamlit
samples/             dados sintéticos de exemplo
storage/uploads/     mídia local ignorada pelo Git
tests/               testes automatizados
```

## Execução recomendada com Docker

Pré-requisitos: Docker Desktop e Docker Compose.

1. Crie o arquivo local de ambiente:

   PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   Linux/macOS:

   ```bash
   cp .env.example .env
   ```

2. Suba todos os serviços:

   ```bash
   docker compose up --build
   ```

3. Abra:

   - Dashboard: <http://localhost:8501>
   - Swagger: <http://localhost:8000/docs>
   - Health check: <http://localhost:8000/health>

4. Encerre sem apagar o banco:

   ```bash
   docker compose down
   ```

Para recriar também o volume PostgreSQL, use `docker compose down -v`. Isso apaga os dados locais do projeto.

## Demonstrações

No dashboard, use **Pacientes** para cadastrar ou buscar um paciente fictício. Selecione o paciente e abra seu prontuário. Em **Mídias e análises**, escolha um arquivo para consultar e processar os jobs associados. A aba também permite reproduzir WAV e MP4 compatíveis com o navegador ou baixar o arquivo original. Os registros de sinais vitais, prescrições, movimentações, eventos e alertas ficam nas demais abas do prontuário.

### Áudio sintético e sentimento

1. No portal Azure, obtenha a chave e a região do recurso **Speech** e o endpoint HTTPS e a chave do recurso **Language**. No `.env` local, preencha `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_LANGUAGE_ENDPOINT` e `AZURE_LANGUAGE_KEY`. O Docker Compose repassa as quatro variáveis à API. Execute `docker compose up --build` para aplicar a configuração. [Configuração oficial do Azure Language](https://learn.microsoft.com/en-us/azure/ai-services/language-service/sentiment-opinion-mining/how-to/call-api)
2. Gere áudios curtos com voz sintetizada em português do Brasil e exporte em WAV PCM de 16 bits. Use apenas frases inventadas. O Azure Speech reconhece uma única fala por arquivo neste fluxo, então evite pausas longas entre as frases. [Reconhecimento de fala única](https://learn.microsoft.com/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechrecognizer)

   Exemplos para exercitar diferentes tons:

   | Tom do exemplo | Frase sintética |
   |---|---|
   | Positivo | Adorei o passeio. Foi maravilhoso. |
   | Neutro | A sala fica no segundo andar. |
   | Negativo | O passeio foi horrível. |
   | Misto | Adorei o passeio. A comida foi péssima. |

3. Abra o prontuário de um paciente fictício, envie um WAV em **Mídias e análises** e selecione o arquivo. Clique em **Processar mídia** e confira a transcrição, a identificação do Azure AI Language, o sentimento geral, os três escores e a tabela de sentenças quando disponível. Os rótulos e os escores podem variar com a transcrição e com o modelo.
4. Consulte `GET /api/v1/jobs/{id}` no Swagger. Em `result.analysis.sentiment_analysis`, confira `provider: azure_ai_language`, `language: pt-BR`, `status: succeeded`, `sentiment`, `confidence_scores` e `sentences`. Atualize o dashboard e selecione o mesmo job para conferir a leitura do resultado persistido. O exemplo negativo isolado mantém `alert_ids` vazio.
5. Para verificar a degradação, deixe `AZURE_LANGUAGE_KEY` vazia, mantenha o Speech configurado, aplique a configuração e processe um novo job. O job deve concluir com transcrição, métricas acústicas e regras locais, e o painel deve indicar `unavailable` com motivo `missing_configuration`. Um áudio sem fala reconhecida deve exibir `skipped`. A API bloqueia o reprocessamento de jobs concluídos.

O Azure AI Language classifica o tom do texto transcrito como positivo, neutro, negativo ou misto. Os escores representam a confiança do modelo na classificação, entre 0 e 1. O resultado tem finalidade educacional. Um tom negativo não indica risco clínico, dor, depressão ou emergência. Os escores não estimam a probabilidade de doença e o sentimento não gera alertas clínicos.

`analysis.text_analysis` registra a identificação de termos críticos por regras locais. Por exemplo, a frase fictícia “Estou com dor” pode acionar `requires_review` nessa análise mesmo com o sentimento indisponível. As métricas de áudio ficam em `analysis.acoustic`.

O adaptador usa `TextAnalyticsClient.analyze_sentiment` com um documento por chamada e solicita a desativação dos logs de entrada no serviço. Transcrições acima de 5.120 elementos de texto Unicode ou que excedam o tamanho da requisição síncrona de 1 MB ficam com `unavailable` e motivo `document_too_large`. A aplicação preserva o texto completo. Texto vazio ou fala sem reconhecimento ficam com `skipped` e dispensam a chamada. Erros de serviço, rejeições do documento e respostas inesperadas ficam com `unavailable` e um código de motivo seguro. O dashboard exibe a origem Azure somente para resultados com `succeeded`. [SDK oficial](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-textanalytics-readme) · [Limites do serviço](https://learn.microsoft.com/en-us/azure/ai-services/language-service/concepts/data-limits)

A Microsoft anunciou a descontinuação dessa funcionalidade do Azure Language para 31 de março de 2029. [Ciclo de vida da funcionalidade](https://learn.microsoft.com/en-us/azure/ai-services/language-service/sentiment-opinion-mining/overview?tabs=prebuilt)

### Menções clínicas na transcrição

A análise usa o mesmo endpoint e a mesma chave do Azure AI Language, em um recurso que aceite Text Analytics for Health. A API envia a transcrição sintética em português (`pt`) com os logs de entrada desativados e guarda entidades da categoria `SymptomOrSign` em `result.analysis.clinical_mentions`. Cada menção inclui o trecho, a posição e o comprimento no texto, a categoria, a confiança da extração e os modificadores de certeza, associação e condicionalidade retornados pelo SDK. Um campo vazio indica ausência de modificador explícito. [Configuração do recurso](https://learn.microsoft.com/en-us/azure/ai-services/language-service/text-analytics-for-health/quickstart) · [Contexto das entidades](https://learn.microsoft.com/en-us/azure/ai-services/language-service/text-analytics-for-health/concepts/assertion-detection)

Para validar, gere e processe WAVs sintéticos curtos com “Estou com falta de ar”, “Não estou com falta de ar” e “Minha irmã está com falta de ar”. Compare os trechos e o contexto em **Mídias e análises** e no job consultado via `GET /api/v1/jobs/{id}`. Confira a marca de negação no segundo exemplo e a associação no terceiro quando o serviço a retornar. Use “O passeio foi horrível” para exercitar uma resposta sem menções a sintomas.

Uma resposta sem sintomas tem status `succeeded` e lista vazia. Sem fala reconhecida ou com texto vazio, a extração fica `skipped`. Configuração ausente, erro do Azure, documento acima dos limites ou operação que exceda 20 segundos recebem `unavailable` com motivo seguro. O job registra as demais análises disponíveis. Os eventos de revisão continuam baseados nas regras locais. As menções extraídas são educacionais e os escores medem a confiança na extração do trecho.

### Séries temporais e operações — Etapa 4

No prontuário de um paciente fictício, abra **Prescrições e movimentações** e registre sequências deliberadamente inconsistentes. Para demonstrar uma tendência de sinais vitais, use a aba **Sinais vitais** e registre quatro medições sintéticas com valores crescentes de frequência cardíaca, por exemplo `70`, `82`, `94` e `106` bpm.

A aplicação:

1. analisa uma janela recente de quatro medições sintéticas;
2. registra eventos para tendências configuradas e transparentes;
3. compara cada ação de prescrição fictícia com o último estado do mesmo código;
4. compara cada movimentação fictícia com o destino anterior;
5. cria alertas demonstrativos e mantém no evento os motivos que exigem revisão humana.

As regras comprovam o fluxo de software e não representam limites clínicos, validação farmacológica ou rastreamento real.

### Áudio — Etapa 3

Na aba **Mídias e análises** do prontuário, envie um WAV inteiramente sintético e processe o job associado. A aplicação:

1. valida o paciente e a mídia sintéticos;
2. transcreve o WAV em português com Azure Speech;
3. calcula métricas acústicas locais;
4. aplica regras textuais contextuais;
5. persiste eventos de revisão humana, sem criar diagnóstico ou alerta clínico automático.

As credenciais `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` devem existir apenas no arquivo local `.env`.

### Vídeo — Etapa 2

No dashboard, abra **Demonstrações** e clique em **Executar demonstração de vídeo**. A aplicação:

1. cria um paciente fictício específico da demonstração;
2. gera um arquivo AVI com formas geométricas e a marca `SYNTHETIC`;
3. registra a mídia e o job;
4. decodifica e amostra quadros com OpenCV;
5. calcula a porcentagem de pixels alterados entre quadros;
6. persiste o evento e o alerta produzidos pelas regras educacionais.

O mesmo fluxo pode ser executado pela API:

```bash
curl -X POST http://localhost:8000/api/v1/demo/video-alert
```

### Sinais vitais — Etapa 1

No dashboard, abra **Demonstrações** e clique em **Executar demonstração de alerta**. A aplicação:

1. cria ou reutiliza o paciente `MG-DEMO-001`;
2. registra uma medição deliberadamente anômala e sintética;
3. aplica regras ilustrativas;
4. persiste um evento de severidade crítica;
5. cria um alerta aberto;
6. mostra o resultado no painel.

O mesmo fluxo pode ser executado pela API:

```bash
curl -X POST http://localhost:8000/api/v1/demo/vital-alert
```

Depois, consulte:

```bash
curl http://localhost:8000/api/v1/events
curl http://localhost:8000/api/v1/alerts
```

## Endpoints iniciais

| Método | Rota | Finalidade |
|---|---|---|
| `GET` | `/health` | Estado da API |
| `POST/GET` | `/api/v1/patients` | Cadastrar/listar pacientes fictícios |
| `POST` | `/api/v1/patients/{id}/measurements` | Registrar e avaliar medição sintética |
| `GET` | `/api/v1/patients/{id}/measurements` | Consultar medições |
| `POST/GET` | `/api/v1/patients/{id}/prescriptions` | Registrar/listar prescrição fictícia |
| `POST` | `/api/v1/patients/{id}/prescriptions/evaluate` | Registrar e avaliar sequência de prescrição fictícia |
| `POST/GET` | `/api/v1/patients/{id}/movements` | Registrar, avaliar e listar movimentações fictícias |
| `POST` | `/api/v1/patients/{id}/media` | Enviar áudio ou vídeo fictício |
| `GET` | `/api/v1/media` | Consultar mídias, com filtro por paciente e paginação por `offset` e `limit` |
| `GET` | `/api/v1/media/{id}/content` | Baixar mídia sintética pelo ID |
| `GET` | `/api/v1/jobs` | Consultar jobs, com filtro por paciente e paginação por `offset` e `limit` |
| `POST` | `/api/v1/jobs/{id}/process` | Processar um job de áudio ou vídeo pendente |
| `POST` | `/api/v1/patients/{id}/correlations/run` | Correlacionar eventos sintéticos próximos no tempo |
| `GET` | `/api/v1/events` | Consultar eventos normalizados |
| `GET/PATCH` | `/api/v1/alerts` e `/api/v1/alerts/{id}` | Consultar e atualizar alertas |
| `POST` | `/api/v1/demo/vital-alert` | Executar fluxo demonstrável |
| `POST` | `/api/v1/demo/video-alert` | Gerar e analisar vídeo geométrico sintético |

## Upload de mídia nesta etapa

Formatos aceitos:

- Áudio: `.wav` PCM de 16 bits.
- Vídeo: `.mp4`, `.mov`, `.avi`, `.mkv`.

O upload salva o arquivo, calcula o hash, cria `media_files` e registra um `processing_job` com status `queued`. Jobs de áudio e vídeo são processados por `POST /api/v1/jobs/{id}/process`.

### Como a análise de áudio funciona

O adaptador Azure Speech transcreve o WAV sintético em `pt-BR`. Em seguida, o pipeline calcula métricas acústicas e aplica regras contextuais transparentes sobre o texto. Expressões afirmativas podem criar eventos de baixa severidade para revisão humana; não são gerados diagnósticos nem alertas clínicos automáticos. Os testes substituem a chamada Azure por mocks e geram áudio sintético em memória.

### Como a análise de vídeo funciona

O processador reduz cada quadro amostrado para uma matriz em tons de cinza e mede a proporção de pixels cuja intensidade mudou. Duas regras configuráveis criam eventos demonstrativos:

- movimento médio abaixo de `VIDEO_LOW_MOTION_THRESHOLD`;
- pico de mudança acima de `VIDEO_ABRUPT_MOTION_THRESHOLD`.

Esses indicadores não representam postura, dor, queda, condição clínica nem identidade. São métricas visuais genéricas para comprovar o pipeline de software com dados sintéticos. MediaPipe/YOLO podem ser adicionados posteriormente como analisadores opcionais, mantendo o mesmo contrato de eventos.

## Testes

Com os containers ativos:

```bash
docker compose exec api pytest
```

Para executar localmente com Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Os testes usam SQLite temporário e mocks para chamadas Azure. O Docker Compose usa PostgreSQL na execução da aplicação.
O workflow `.github/workflows/ci.yml` repete essa validação automaticamente em cada push ou pull request para `main` usando Python 3.12.

## Variáveis de ambiente

Consulte `.env.example`. Configure no `.env` local `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` para transcrição e `AZURE_LANGUAGE_ENDPOINT` e `AZURE_LANGUAGE_KEY` para sentimento. Nunca envie chaves, gravações pessoais ou dados médicos reais ao Git.

## Correspondência com o Tech Challenge

| Requisito final | Estado após a Etapa 4 |
|---|---|
| Vídeo clínico e eventos fora do padrão | Pipeline OpenCV, métricas de movimento, eventos e alertas demonstrativos implementados com vídeo sintético |
| Áudio, transcrição e análise textual | Azure Speech, métricas acústicas, regras locais contextuais, sentimento e extração de menções clínicas via Azure AI Language para WAV sintético |
| Anomalias em sinais vitais | Regras pontuais e análise temporal transparente sobre janelas de medições sintéticas |
| Prescrições e movimentação | Detectores demonstrativos de sequência e continuidade implementados com dados fictícios |
| Alertas automáticos | Eventos e alertas persistidos nos fluxos de sinais vitais, vídeo, prescrições e movimentações |
| Fusão multimodal | Correlação temporal preliminar implementada; evolução e validação continuam nas próximas etapas |
| Relatório e vídeo final | Planejados para a Etapa 8 |

## Próximas etapas

1. Evoluir o analisador de vídeo com pose opcional e validação sobre material inteiramente sintético.
2. Ampliar a correlação multimodal e consolidar eventos relacionados em uma linha do tempo.
3. Aprimorar alertas, métricas de qualidade, observabilidade e validação para a entrega final.


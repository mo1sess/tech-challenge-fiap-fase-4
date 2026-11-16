# MedGuard AI

Plataforma educacional de monitoramento multimodal para o **Tech Challenge FIAP — Fase 4**. Integra vídeo, fala sintética, sinais vitais fictícios, prescrições e movimentações em eventos rastreáveis, alertas demonstrativos e uma linha do tempo por paciente.

O problema abordado é a fragmentação de informações provenientes de fontes distintas. O objetivo é reunir essas informações em uma arquitetura reproduzível, permitir a inspeção de regras e evidências e demonstrar coocorrências temporais entre modalidades.

> Uso exclusivamente educacional, com dados fictícios ou sintéticos. O sistema não é um dispositivo médico, não estabelece diagnóstico e não deve orientar decisões clínicas. Correlação significa coocorrência temporal, sem comprovar causalidade. Limiares e severidades são regras demonstrativas de software.

## Documentação

| Documento | Conteúdo |
|---|---|
| [Arquitetura](docs/ARCHITECTURE.md) | Componentes, algoritmos, persistência, integrações e decisões técnicas |
| [Diagramas](docs/DIAGRAMS.md) | Dez diagramas Mermaid dos componentes e fluxos implementados |
| [Referência da API](docs/API_REFERENCE.md) | Rotas, contratos, parâmetros, respostas e exemplos |
| [Guia de demonstração](docs/DEMO_GUIDE.md) | Configuração, modelo de pose, preparação das mídias e roteiro |
| [Testes](docs/TESTING.md) | Comandos, cobertura funcional e evidências de validação |
| [Prontidão técnica](docs/READINESS.md) | Resultados consolidados, limitações e verificações de entrega |

## Funcionalidades

- Cadastro de pacientes fictícios e avaliação pontual e temporal de sinais vitais.
- Envio de mídia sintética, identificação SHA-256 e tarefas de processamento rastreáveis (`jobs`).
- Análise de variação visual com OpenCV e inferência opcional de pose com MediaPipe Tasks.
- Transcrição WAV com Azure Speech-to-Text em `pt-BR`, métricas acústicas e regras textuais contextuais.
- Análise opcional de sentimento e entidades gerais com Azure AI Language em português (`pt`).
- Verificação de sequências de prescrições fictícias e continuidade de movimentações.
- Eventos e alertas nos fluxos de sinais vitais, vídeo e anomalias operacionais; áudio e correlação não criam alertas.
- Correlação v1 entre áudio e sinais vitais; correlação v2 entre áudio, vídeo e sinais vitais, com deduplicação e unicidade persistente.
- Dashboard com indicadores, gráficos, relatórios de mídia, linha do tempo e revisão de alertas com histórico.

## Arquitetura e tecnologias

Monólito modular: **Streamlit → REST → FastAPI → serviços e processadores → SQLAlchemy → PostgreSQL**. As mídias permanecem no sistema de arquivos. O processamento ocorre durante a requisição HTTP, sem fila ou processo executor externo.

| Tecnologia | Responsabilidade |
|---|---|
| Python 3.11+; imagem Python 3.12 | Linguagem e ambiente de execução |
| FastAPI e Pydantic | API REST, OpenAPI e validação de contratos |
| SQLAlchemy, psycopg e PostgreSQL 16 | Persistência relacional |
| Streamlit e pandas | Interface, relatórios e gráficos |
| OpenCV e NumPy | Decodificação de vídeo, variação visual e métricas acústicas |
| MediaPipe Pose Landmarker 0.10.31 | Inferência opcional de 33 pontos corporais em CPU |
| Azure Speech SDK | Transcrição de fala sintética |
| Azure AI Language | Sentimento e reconhecimento de entidades gerais |
| Docker e Docker Compose | Serviços, armazenamento e verificações de saúde |
| Pytest, HTTPX e Streamlit AppTest | Testes automatizados e verificações operacionais da interface |

As dependências estão em [pyproject.toml](pyproject.toml). MediaPipe está fixado em `0.10.31`; as demais dependências usam faixas de versões. Não há arquivo completo de versões travadas.

```text
app/api/routes/     rotas de pacientes, mídia, eventos, alertas e correlação
app/core/           configuração
app/db/             modelos, verificação e migrações aditivas
app/modules/audio/  Azure Speech, Azure AI Language, acústica e análise textual
app/modules/video/  OpenCV e MediaPipe Pose
app/schemas/        contratos Pydantic
app/services/       orquestração, regras, eventos e alertas
dashboard/          aplicação Streamlit e relatórios
scripts/            demonstrações e validação operacional
samples/            exemplo de medições sintéticas
storage/            dados e modelos locais, fora do versionamento
tests/              testes automatizados
docs/               documentação técnica
.github/workflows/  integração contínua
```

## Instalação e configuração

Requisitos: Docker Desktop com contêineres Linux e Docker Compose. A transcrição real e o enriquecimento textual exigem recursos Azure, rede e credenciais locais. A pose exige preparação explícita, descrita no [guia](docs/DEMO_GUIDE.md#12-preparar-e-demonstrar-pose-real).

Na raiz, crie `.env` somente se ainda não existir:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Revise [.env.example](.env.example). Configure `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` para transcrição; `AZURE_LANGUAGE_ENDPOINT` e `AZURE_LANGUAGE_KEY` habilitam sentimento e entidades. Os padrões de banco são apenas para desenvolvimento. Não versione credenciais nem exiba `.env` durante a apresentação.

Para um banco novo:

```powershell
docker compose up -d --build
docker compose ps
```

| Recurso | Endereço padrão |
|---|---|
| Dashboard | http://localhost:8501 |
| Swagger | http://localhost:8000/docs |
| OpenAPI | http://localhost:8000/openapi.json |
| API | http://localhost:8000/api/v1 |
| Saúde da aplicação | http://localhost:8000/health |

`/health` não consulta o banco. O dashboard acrescenta `/api/v1` a `API_BASE_URL`; alterar somente `API_PREFIX` rompe essa integração. Alterações no código exigem reconstruir a imagem; alterações no `.env` exigem recriar o serviço correspondente. Para parar sem remover volumes, execute `docker compose down`, sem a opção `-v`.

### Migração segura de PostgreSQL existente

`create_all()` cria tabelas ausentes, mas não altera tabelas antigas. Para um volume anterior à coluna `clinical_events.correlation_key`, mantenha uma cópia de segurança local e execute em janela de manutenção:

```powershell
docker compose up -d db
docker compose stop api dashboard
docker compose build api dashboard
docker compose run --rm --no-deps api python -m app.db.migrate_correlation_keys
docker compose up -d
docker compose ps
```

Aguarde o banco saudável antes da migração. O procedimento é transacional e repetível: adiciona a coluna, preenche identificadores de correlação e cria o índice único. Duplicatas históricas permanecem com chave `NULL`; nenhum registro é excluído. No PostgreSQL, o bloqueio `ACCESS EXCLUSIVE` impede acesso concorrente à tabela durante a operação. Um banco vazio deve ser inicializado pela API, não por essa migração.

A tabela aditiva `alert_review_actions` é criada na inicialização quando ausente. Há também o comando `python -m app.db.migrate_alert_reviews`, repetível e dependente da tabela `alerts` já existente. Consulte [persistência e migração](docs/ARCHITECTURE.md#persistência-e-migração).

### Execução local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:DATABASE_URL = "sqlite:///./medguard.db"
$env:STORAGE_DIR = "storage/uploads"
python -m uvicorn app.main:app --reload
```

Em outro terminal, com o ambiente virtual ativo:

```powershell
$env:API_BASE_URL = "http://localhost:8000"
python -m streamlit run dashboard/app.py
```

SQLite permite desenvolvimento e testes, mas não reproduz integralmente PostgreSQL. O nome `db` é exclusivo da rede interna do Compose; conexões locais precisam de uma URL acessível pelo computador.

## Testes e demonstração

```powershell
docker compose exec -T api python -m pytest
```

Localmente, após instalar as dependências: `python -m pytest`. A validação consolidada registrou **77 testes aprovados**, **26 verificações da API** e **21 etapas com Streamlit AppTest**, além de Azure e pose reais. Testes com simulações e inferência real são evidências distintas; detalhes em [Testes](docs/TESTING.md).

Após preparar um WAV inteiramente sintético, PCM de 16 bits sem compressão:

```powershell
docker compose exec -T api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1
```

O WAV não é distribuído pelo Git. O script cria paciente e vídeo geométrico próprios, processa as fontes, verifica um trio e repete a correlação para conferir idempotência. A demonstração positiva de MediaPipe utiliza vídeos de avatar separados, conforme o [guia](docs/DEMO_GUIDE.md).

## Segurança e limitações

A marca sintética é declarada pelo remetente; não há detecção automática de dados pessoais. Não envie dados reais, vozes pessoais ou imagens de pacientes. Credenciais, cópias de banco, modelos e mídias geradas ficam fora do Git. Não há autenticação, autorização, TLS configurado pelo projeto, retenção automática ou auditoria de identidade real. Este ambiente não deve ser exposto à internet.

As tarefas são síncronas; não há recuperação automática de processamento interrompido nem transação atômica entre disco e banco. O dashboard consulta recortes recentes, sem paginação integral ou atualização periódica automática. A unicidade da correlação foi verificada, mas não houve ensaio de concorrência PostgreSQL sob carga.

MediaPipe utiliza CPU e modo `IMAGE`, sem rastreamento temporal de identidade. A métrica mede deslocamento normalizado de ombros e quadris; não representa velocidade física, queda, dor ou risco clínico. O modelo oficial Lite é instalado separadamente. `pip check` apresenta uma exceção de metadados do wheel oficial `0.10.31`, apesar de importação e inferência real funcionarem no ambiente validado. Essa falha permanece documentada em [Prontidão técnica](docs/READINESS.md#exceção-de-empacotamento-do-mediapipe).

Antes da apresentação, inspecione o navegador, prepare o roteiro e confira os materiais de entrega. Não há alegação de validação clínica, execução em tempo real ou conformidade integral com critérios de avaliação não fornecidos.

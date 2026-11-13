# MedGuard AI

Plataforma educacional de monitoramento multimodal para o **Tech Challenge FIAP — Fase 4**. Integra medições sintéticas, vídeo, áudio fictício, prescrições e movimentações em eventos rastreáveis, alertas demonstrativos e uma linha do tempo por paciente.

O objetivo de software é reunir fontes distintas e tornar sua análise temporal inspecionável, permitindo reprodução do ambiente, demonstração e continuidade do desenvolvimento.

> Uso exclusivamente educacional com dados fictícios ou sintéticos. Não é um dispositivo médico e não deve orientar decisões clínicas. Correlação significa **coocorrência temporal**, sem estabelecer causalidade ou diagnóstico. Limites e severidades são exemplos de regras de software.

## Documentação

| Documento                           | Conteúdo                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| [Arquitetura](docs/ARCHITECTURE.md) | Componentes, fluxos, regras, correlação v2, dados e decisões                   |
| [Diagramas](docs/DIAGRAMS.md)       | Oito diagramas Mermaid de arquitetura, processamento, entidades e demonstração |
| [API](docs/API_REFERENCE.md)        | Endpoints, parâmetros, contratos, exemplos e erros                             |
| [Demonstração](docs/DEMO_GUIDE.md)  | Preparação, execução, interpretação e roteiro de 5–8 minutos                   |
| [Testes](docs/TESTING.md)           | Estratégia, comandos reproduzíveis, evidências e lacunas                       |

## Funcionalidades implementadas

- Cadastro de pacientes fictícios; avaliação pontual de medições e tendências de quatro registros.
- Upload de mídia sintética, hash SHA-256 e jobs rastreáveis.
- Análise de variação visual com OpenCV, sem identificação de pessoas ou interpretação clínica.
- Transcrição WAV com Azure Speech em `pt-BR`, métricas acústicas e regras textuais contextuais.
- Verificação de sequências de prescrições fictícias e continuidade de movimentações.
- Eventos e alertas nos fluxos demonstrativos; áudio e correlação não criam alertas.
- Correlação v1 de áudio–sinais vitais e v2 de áudio, vídeo e sinais vitais com deduplicação e unicidade persistente.
- Dashboard v2 com KPIs, gráficos, explorador de correlações, linha do tempo e alertas.

## Arquitetura e tecnologias

Monólito modular: Streamlit → REST → FastAPI → serviços → processadores e SQLAlchemy → PostgreSQL. Mídias ficam no sistema de arquivos. O processamento ocorre durante a requisição HTTP, sem fila ou worker externo.

| Tecnologia                       | Responsabilidade                          |
| -------------------------------- | ----------------------------------------- |
| Python 3.11+; imagem Python 3.12 | Linguagem e ambiente                      |
| FastAPI e Pydantic               | API REST, OpenAPI e contratos             |
| SQLAlchemy e psycopg             | Acesso relacional e conexão PostgreSQL    |
| PostgreSQL 16                    | Persistência no Compose                   |
| Streamlit 1.52+ e pandas         | Interface e gráficos                      |
| OpenCV e NumPy                   | Vídeo e métricas acústicas                |
| Azure Speech SDK                 | Transcrição externa de fala sintética     |
| Docker e Docker Compose          | Serviços, volumes e verificações de saúde |
| Pytest e HTTPX                   | Testes de regras, banco e API             |

Versões efetivas em [pyproject.toml](pyproject.toml). Não há arquivo de versões travadas. O dashboard importa `pandas`, disponível como dependência transitiva do Streamlit, sem declaração direta no projeto.

## Estrutura

```text
app/
  api/routes/       pacientes, fluxos clínicos, mídia, jobs, demos e correlação
  core/             configuração
  db/               modelos, verificação e migração de esquema
  modules/audio/    Azure Speech, acústica e regras textuais
  modules/video/    OpenCV e vídeo geométrico
  schemas/          contratos Pydantic
  services/         orquestração, regras, eventos e alertas
dashboard/          app.py e multimodal_v2.py
scripts/            demo_multimodal.py
samples/            vitals_demo.csv
storage/            mídia local
tests/              testes automatizados
docs/               documentação técnica
.github/workflows/  CI para main
```

## Pré-requisitos e configuração

Execução recomendada: Docker Desktop ativo com containers Linux e Docker Compose. Azure Speech e rede são necessários para transcrição fora dos mocks. Desenvolvimento local: Python 3.11+, `pip` e ambiente virtual.

Na raiz, crie `.env` somente se ainda não existir:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Revise [.env.example](.env.example). Use valores próprios de banco localmente; os padrões são de desenvolvimento. Nunca versione segredos. Não exponha este ambiente na internet: não há autenticação implementada.

### Docker Compose

Para um banco novo:

```powershell
docker compose up -d --build
docker compose ps
```

| Acesso    | Endereço padrão                    |
| --------- | ---------------------------------- |
| Dashboard | http://localhost:8501              |
| Swagger   | http://localhost:8000/docs         |
| OpenAPI   | http://localhost:8000/openapi.json |
| API       | http://localhost:8000/api/v1       |
| Saúde     | http://localhost:8000/health       |

`/health` informa o estado da aplicação sem consultar o banco. O dashboard acrescenta `/api/v1` a `API_BASE_URL`: alterar somente `API_PREFIX` quebra essa integração.

Para parar preservando os volumes:

```powershell
docker compose down
```

### Migração segura de PostgreSQL existente

`create_all()` não altera tabelas antigas. Para volume anterior à coluna `clinical_events.correlation_key`, mantenha uma cópia de segurança sob responsabilidade do operador e execute em janela de manutenção:

```powershell
docker compose up -d db
docker compose stop api dashboard
docker compose build api dashboard
docker compose run --rm --no-deps api python -m app.db.migrate_correlation_keys
docker compose up -d
docker compose ps
```

Aguarde o banco saudável antes da migração. Ela é transacional e repetível. No PostgreSQL usa `ACCESS EXCLUSIVE`, bloqueando o acesso concorrente à tabela. Adiciona a coluna anulável, preenche fingerprints e cria índice único. Duplicatas históricas ficam com chave `NULL`; nenhum registro é excluído. O comando pressupõe a tabela existente; um banco vazio deve ser inicializado pela API. A API recusa esquema pendente. Detalhes em [Arquitetura](docs/ARCHITECTURE.md#persistência-e-migração).

O procedimento anterior também registrava, para problemas específicos de build legado, `$env:DOCKER_BUILDKIT = "0"` e `$env:COMPOSE_DOCKER_CLI_BUILD = "0"` antes do build; não são requisitos gerais.

### Azure Speech

Preencha apenas no `.env` local `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` com os valores do recurso Speech. Para aplicar mudanças:

```powershell
docker compose up -d --force-recreate api
```

O adaptador usa `recognize_once_async()` em `pt-BR`, sem transcrição contínua. `AZURE_LANGUAGE_ENDPOINT` e `AZURE_LANGUAGE_KEY` são configurações reservadas, sem integração ativa. A análise textual é local e determinística. Use WAV inteiramente sintético, PCM de 16 bits sem compressão.

### Execução local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:DATABASE_URL = "sqlite:///./medguard.db"
$env:STORAGE_DIR = "storage/uploads"
python -m uvicorn app.main:app --reload
```

SQLite permite desenvolvimento e testes, mas não reproduz integralmente PostgreSQL. Para PostgreSQL local, use uma URL acessível pela máquina; `db` é o host interno do Compose. Em outro terminal com o ambiente virtual ativo:

```powershell
$env:API_BASE_URL = "http://localhost:8000"
python -m streamlit run dashboard/app.py
```

## Testes e demonstração

```powershell
docker compose exec api python -m pytest
```

Localmente, após instalar dependências: `python -m pytest`. Prefira invocação por módulo para resolver imports entre arquivos de `tests/`. Consulte [Testes](docs/TESTING.md) para evidências e limitações.

A demonstração usa endpoints públicos e gera paciente e vídeo próprios. O WAV é uma preparação local, não um arquivo garantido pelo Git:

```powershell
docker compose exec api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1
```

O [guia](docs/DEMO_GUIDE.md) explica preparação, resultado histórico `PASS`, Dashboard v2 e idempotência. Demos isoladas: `POST /api/v1/demo/vital-alert` e `POST /api/v1/demo/video-alert`; usam pacientes próprios e não substituem o cenário integrado.

## Segurança, limitações e próximos passos

A marca sintética é declarada pelo remetente; não há detecção automática de dados pessoais. Não envie dados reais, segredos, gravações pessoais ou backups ao Git. Não há autenticação, autorização, TLS configurado pelo projeto, retenção automática ou auditoria completa. CORS não é controle de acesso.

Uploads têm limite de tamanho e extensão; o conteúdo é validado na decodificação. Não há antivírus, deduplicação de mídia por hash ou transação atômica entre arquivo e banco. Jobs são síncronos; falhas inesperadas podem exigir intervenção. O dashboard consulta recortes recentes, sem atualização periódica automática.

Evoluções: dependências diretas e versões travadas, autenticação, testes PostgreSQL/concorrência, paginação, processamento assíncrono, observabilidade e testes da interface. Pose, YOLO e MediaPipe não estão integrados. A equipe ainda deve preparar apresentação e vídeo final da FIAP.

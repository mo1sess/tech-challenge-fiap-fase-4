# Estratégia de testes e validação

[README](../README.md) · [Arquitetura](ARCHITECTURE.md) · [Demonstração](DEMO_GUIDE.md)

## Escopo e evidências

O projeto usa Pytest, HTTPX/ASGITransport, SQLAlchemy e fixtures de dados sintéticos. [pyproject.toml](../pyproject.toml) configura `testpaths=tests` e `addopts=-q`. Não há marcadores que separem formalmente unitários e integração; a classificação abaixo descreve o comportamento dos testes existentes.

A equipe informou **57 testes aprovados** em execução anterior, como evidência histórica. Na revisão documental de **13/11/2026**, o comando `docker compose exec -T api python -m pytest` também concluiu com **57 passed in 22.81s**. A duração descreve somente essa execução, sem constituir benchmark ou garantia de contagem permanente.

O comando direto `docker compose exec -T api pytest` falhou na coleta de `tests/test_correlation_v2.py`, que importa `tests.test_correlation`, com `ModuleNotFoundError: No module named 'tests'`. A invocação por módulo resolveu a coleta na imagem examinada. O Python local disponível não tinha Pytest instalado; não houve execução local da suíte nesta revisão.

A imagem ativa pode diferir de alterações locais não reconstruídas. A comparação do conteúdo Python e da configuração de testes deve preceder a atribuição do resultado ao checkout atual; registre divergências se existirem. Arquivos de documentação não alteram a lógica dos testes.

## Organização e garantias

| Categoria | Arquivos | O que verifica |
|---|---|---|
| Unidade: acústica | [test_acoustic_analysis.py](../tests/test_acoustic_analysis.py) | Métricas de seno sintético, silêncio e arquivo inválido |
| Unidade: texto | [test_audio_text_analysis.py](../tests/test_audio_text_analysis.py) | Padrões, acentos, negação, terceiros, histórico e separação de sentenças |
| Integração de áudio/API | [test_audio_analysis.py](../tests/test_audio_analysis.py), [test_audio_events.py](../tests/test_audio_events.py) | Transcrição simulada, persistência de resultado/eventos e consolidação por categoria |
| Saúde e pacientes | [test_health_and_patients.py](../tests/test_health_and_patients.py) | Resposta de saúde e rejeição de paciente não sintético |
| Upload e jobs | [test_media_jobs.py](../tests/test_media_jobs.py) | Job queued após upload e rejeição de extensão de áudio incompatível |
| Sinais e alertas | [test_vital_alert_flow.py](../tests/test_vital_alert_flow.py) | Medição sem anomalia e demo com evento/alerta crítico |
| Operações/tendências | [test_phase4_detection.py](../tests/test_phase4_detection.py) | Série crescente, prescrição duplicada e quebra de continuidade |
| Vídeo | [test_video_analysis.py](../tests/test_video_analysis.py) | Fluxos com mocks, bloqueio de reprocessamento e OpenCV real sobre vídeo geométrico |
| Correlação v1 | [test_correlation.py](../tests/test_correlation.py) | Áudio–vital, idempotência, janela e paciente ausente |
| Correlação v2 por API | [test_correlation_v2.py](../tests/test_correlation_v2.py) | Pares com vídeo, trio, evento antigo e isolamento entre pacientes |
| Bordas/unicidade v2 | [test_correlation_v2_edge_cases.py](../tests/test_correlation_v2_edge_cases.py) | Limite exato, amplitude total, prioridade, deduplicação, repetição e chave única |
| Esquema | [test_schema_migration.py](../tests/test_schema_migration.py) | Migração SQLite legada, histórico preservado, repetição e índice único |

## Isolamento e integração de API

[conftest.py](../tests/conftest.py) configura backend AnyIO `asyncio`, SQLite em arquivo temporário e storage temporário por teste. Cria aplicação com `create_app(settings)`, tabelas por `Base.metadata.create_all()` e cliente assíncrono HTTPX com ASGITransport, sem abrir porta de rede. A fixture `patient` cria registro fictício via API.

Os testes de borda usam SQLite em memória e `StaticPool`, exercitando diretamente o serviço. O transporte ASGI usado nas fixtures não aciona automaticamente o lifespan; tabelas são criadas explicitamente. Assim, saúde/API não equivalem a validar toda a inicialização operacional. A checagem de esquema é chamada diretamente no teste de migração.

## Correlação: casos de borda e idempotência

A suíte cobre janela exata de 300 segundos e rejeição em 301 segundos no padrão de cinco minutos. O trio precisa caber na amplitude total: eventos em 0, 180 e 360 segundos não formam trio de cinco minutos, embora os pares vizinhos sejam elegíveis. Testa que trios suprimem pares contidos, pacientes distintos não se misturam e somente o representante de maior severidade do job de vídeo entra na combinação do caso testado.

Repetir o mesmo conjunto retorna lista vazia; depois de um par existente, adicionar a terceira fonte permite novo trio. Janelas 0 e 61 e paciente ausente são rejeitados. Não se deve inferir que todos os desempates, todos os limites de consulta ou todas as combinações de entrada estejam cobertos.

### Unicidade e concorrência

O teste tenta inserir manualmente um evento com `correlation_key` já usada e espera `IntegrityError`. Isso demonstra proteção do índice no SQLite e manutenção do original. O código usa savepoint para tratar disputa de inserção, mas não existe teste com duas requisições concorrentes ao PostgreSQL real. Logo, não há evidência de carga concorrente, deadlocks, isolamento PostgreSQL ou throughput.

### Migração do esquema

O teste constrói uma tabela SQLite legada sem a coluna, insere duas correlações históricas equivalentes, confirma falha do verificador e executa migração. Confere preservação das linhas, fingerprint no registro mais antigo, `NULL` no duplicado, repetibilidade mesmo com chave atribuída ao duplicado posterior e rejeição de nova chave duplicada.

Não testa `LOCK TABLE ... IN ACCESS EXCLUSIVE MODE` no PostgreSQL, tempo de bloqueio, backup/restauração ou bancos de grande porte. Não execute migração no banco operacional como parte da suíte; siga o procedimento de manutenção do [README](../README.md#migração-segura-de-postgresql-existente).

## Mocks e integrações externas

Áudio gera WAV sintético e usa `monkeypatch` para substituir `app.services.audio_flow.transcribe_wav`. Isso testa o fluxo posterior sem chave, rede ou custo Azure. Não comprova precisão de reconhecimento, disponibilidade, cancelamento de conta, limites do SDK ou qualidade de transcrição real.

Vários testes de vídeo simulam `analyze_video`; há também teste real do processador OpenCV com vídeo geométrico. Esse caso comprova geração/decodificação básica no ambiente testado, sem abranger todos os codecs, arquivos corrompidos, câmeras, iluminação ou material real.

## Executar localmente

Na raiz, com Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Os testes definem SQLite isolado; não precisam do PostgreSQL nem de Azure configurado. Para selecionar grupos:

```powershell
python -m pytest tests/test_correlation.py tests/test_correlation_v2.py tests/test_correlation_v2_edge_cases.py
python -m pytest tests/test_schema_migration.py
python -m pytest tests/test_video_analysis.py
```

Para relatório de cobertura opcional, sem percentual mínimo configurado:

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

Não há percentual de cobertura medido ou garantido nesta entrega. Não remova diretórios de dados ou volumes para repetir os testes.

## Executar no Docker

Com API ativa e imagem correspondente ao checkout:

```powershell
docker compose exec api python -m pytest
```

Sem iniciar o servidor, depois de construir a imagem:

```powershell
docker compose build api
docker compose run --rm --no-deps api python -m pytest
```

`--no-deps` não sobe PostgreSQL; os testes usam SQLite próprio. Não executam reset do banco da aplicação. Diretórios temporários podem ser criados pelo Pytest, independentemente de o container compartilhar o volume de mídia operacional.

## CI

[ci.yml](../.github/workflows/ci.yml) executa em pushes para `main` e pull requests destinados a `main`, com Ubuntu, Python 3.12, instalação editável `.[dev]` e comando `pytest`. Não há PostgreSQL, Azure real, teste de UI, lint, validação Mermaid ou limiar de cobertura nesse workflow.

A diferença entre `pytest` configurado no CI e `python -m pytest` validado nesta revisão é uma observação de reprodutibilidade. O workflow não foi alterado no escopo documental. Um push isolado em `feature/multimodal-dashboard` não corresponde ao gatilho de push em `main`.

## Dashboard: validação manual

Não há testes automatizados Streamlit/AppTest na suíte atual. A equipe informou confirmação visual anterior da demonstração no Dashboard v2; isso é evidência histórica, sem garantia de regressão.

Checklist reproduzível:

1. Abrir `http://localhost:8501` e aba **Monitoramento multimodal**.
2. Selecionar paciente do resumo do script, período **Todos**, atualizar.
3. Comparar KPIs com `GET /events`, `/alerts` e medições por paciente.
4. Conferir gráficos vazios, amostra isolada e série com múltiplas medições.
5. Abrir trio e verificar IDs, origens, janela e amplitude temporal.
6. Repetir correlação sem novas origens e observar zero novos eventos.
7. Conferir linha do tempo, filtro de origem e tabela de alertas por status.
8. Considerar aviso de 500 registros, períodos locais e fallback para resumos de origens fora do recorte.

Esse checklist não foi reaplicado visualmente nesta revisão documental; permanece um ensaio recomendado antes da apresentação.

## Cenário ponta a ponta

O [guia de demonstração](DEMO_GUIDE.md) usa `scripts/demo_multimodal.py`, API real, PostgreSQL, mídia local, OpenCV e Azure. É uma validação operacional distinta da suíte isolada e requer preparação de WAV e credenciais. O `PASS` exige trio e repetição vazia, não contagens fixas de eventos/alertas. Sua execução cria dados educacionais persistentes; não é realizada automaticamente pela CI.

## O que ainda não é garantido

- Validade clínica, diagnóstico, causalidade ou detecção de risco.
- Disponibilidade/performance Azure, precisão textual ou qualidade de fala.
- Concorrência real PostgreSQL, recuperação de jobs presos ou consistência atômica entre disco e banco.
- Segurança de produção, autenticação, retenção e tratamento automático de dados pessoais.
- Compatibilidade de todos os codecs, plataformas, fusos ou versões futuras de dependências.
- Todos os endpoints/erros, todas as regras operacionais e limites de 30/100/500 registros.
- Interface sem regressão, migração em produção, backup/restauração e desempenho sob carga.

Prioridades recomendadas: corrigir a invocação CI após decisão da equipe, testes PostgreSQL/concorrência, testes automatizados de UI e falhas de integração. Não ampliar alegações com base apenas no número total de testes aprovados.

## Revis?o desta documenta??o

Em 13/11/2026, foram realizadas tamb?m:

- Confer?ncia dos 22 endpoints de dom?nio extra?dos dos decoradores de rotas e da rota de sa?de, com a refer?ncia escrita.
- Valida??o dos exemplos de entrada de paciente, medi??o, prescri??o, movimenta??o, status de alerta e resposta de sa?de pelos schemas Pydantic no container.
- Execu??o de `python -m scripts.demo_multimodal --help` no container, sem criar dados.
- Confer?ncia de links relativos, ?ncoras Markdown e exist?ncia dos destinos citados nos links.
- Valida??o sint?tica dos oito diagramas com o parser Mermaid 11 em ambiente tempor?rio, sem adicionar depend?ncias ao projeto.
- An?lise sint?tica dos 31 blocos PowerShell, sem erros.
- Consulta somente de leitura ao OpenAPI ativo: 23 opera??es, incluindo sa?de; `/health` retornou `ok`.
- Verifica??o de espa?os/finais de linha e `git diff --check`.

N?o foram repetidos build completo, migra??o sobre PostgreSQL operacional, cria??o de um novo cen?rio Azure ou inspe??o visual da interface. Os comandos de instala??o/subida/migra??o foram revisados contra a configura??o e o c?digo, mas n?o foram todos executados nesta revis?o. O teste de migra??o executado pela su?te usa SQLite isolado. N?o houve altera??o de l?gica, esquema operacional, frontend, commits ou push.

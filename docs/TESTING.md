# Testes e validação técnica

[README](../README.md) · [Arquitetura](ARCHITECTURE.md) · [Demonstração](DEMO_GUIDE.md) · [Prontidão técnica](READINESS.md)

## Estratégia e evidências

O projeto utiliza Pytest, HTTPX/ASGITransport, SQLAlchemy e dados sintéticos. [pyproject.toml](../pyproject.toml) define `testpaths=tests` e `addopts=-q`. A suíte contém **77 testes**; não há marcadores formais que separem testes unitários e de integração.

Na validação operacional de 15/11/2026, a suíte retornou **77 passed in 21.39s**. Também foram aprovadas **26 verificações da API real** e **21 etapas com Streamlit AppTest**, em execução separada. Os números descrevem uma execução específica, não uma garantia de cobertura completa ou desempenho.

Após a consolidação documental para entrega, a suíte foi novamente executada sobre os arquivos atuais, montados somente para leitura na imagem validada: **77 passed in 20.42s**. O comando foi `docker compose run --rm --no-deps --volume 'C:/dev/tech-challenge-fiap-fase-4:/review:ro' --workdir /review api python -m pytest -p no:cacheprovider`. O caminho absoluto corresponde ao computador do ensaio e deve ser substituído pela raiz local ao repetir essa montagem. A opção desabilita apenas o cache do Pytest; não exclui testes.

Testes com simulações verificam contratos e regras sem acessar Azure ou carregar um modelo de pose. A evidência de integração externa provém das demonstrações reais, explicitamente identificadas neste documento. Não se deve inferir precisão clínica do total de testes aprovados.

## Organização da suíte

| Área | Arquivos | Verificações principais |
|---|---|---|
| Saúde e pacientes | [test_health_and_patients.py](../tests/test_health_and_patients.py) | Saúde da aplicação e rejeição de paciente não sintético |
| Mídia e tarefas | [test_media_jobs.py](../tests/test_media_jobs.py) | Registro de mídia, tarefa em `queued` e extensão incompatível |
| Acústica | [test_acoustic_analysis.py](../tests/test_acoustic_analysis.py), [test_extended_acoustics.py](../tests/test_extended_acoustics.py) | Tom, silêncio, energia por janela, variabilidade e intervalos silenciosos |
| Texto contextual | [test_audio_text_analysis.py](../tests/test_audio_text_analysis.py) | Expressões, acentos, negação, terceiros, histórico e sentenças |
| Áudio integrado | [test_audio_analysis.py](../tests/test_audio_analysis.py), [test_audio_events.py](../tests/test_audio_events.py) | Transcrição simulada, resultados e eventos persistidos |
| Azure AI Language | [test_azure_language.py](../tests/test_azure_language.py) | SDK simulado, sentimentos, entidades, falhas e resultados parciais |
| Vídeo OpenCV | [test_video_analysis.py](../tests/test_video_analysis.py) | Vídeo geométrico real, contratos com simulações e bloqueio de reprocessamento |
| Pose | [test_pose_analysis.py](../tests/test_pose_analysis.py), [test_video_pose_flow.py](../tests/test_video_pose_flow.py) | Pose simulada, indisponibilidade e integração de eventos/alertas |
| Sinais vitais e operações | [test_vital_alert_flow.py](../tests/test_vital_alert_flow.py), [test_phase4_detection.py](../tests/test_phase4_detection.py) | Anomalias, tendências, prescrições duplicadas e continuidade de movimentações |
| Correlação v1 | [test_correlation.py](../tests/test_correlation.py) | Áudio–sinais vitais, janela, paciente ausente e idempotência |
| Correlação v2 | [test_correlation_v2.py](../tests/test_correlation_v2.py), [test_correlation_v2_edge_cases.py](../tests/test_correlation_v2_edge_cases.py) | Pares, trios, bordas, prioridade, isolamento, deduplicação e unicidade |
| Migração | [test_schema_migration.py](../tests/test_schema_migration.py) | Esquema SQLite legado, histórico preservado e repetição |
| Revisão de alertas | [test_review_workflow.py](../tests/test_review_workflow.py) | Transições, idempotência, histórico, isolamento e migração aditiva |

## Isolamento e execução

[conftest.py](../tests/conftest.py) utiliza SQLite e armazenamento temporários por teste, cliente HTTPX e `create_app(settings)`. O Azure AI Language e a pose ficam explicitamente desabilitados na configuração da aplicação de teste. Os adaptadores externos são simulados nos testes que os exercitam. Não há chamadas pagas nem download automático de modelos no Pytest.

O transporte ASGI não inicia automaticamente o ciclo de vida da aplicação; as tabelas de teste são criadas explicitamente. Portanto, a suíte isolada não substitui a verificação de inicialização dos serviços e do PostgreSQL real.

Com a API ativa e a imagem correspondente ao código:

```powershell
docker compose exec -T api python -m pytest
```

Sem iniciar o servidor, após construir a imagem:

```powershell
docker compose build api
docker compose run --rm --no-deps api python -m pytest
```

Esses testes usam SQLite temporário; `--no-deps` não inicia PostgreSQL. Não remova volumes ou dados para repetir a suíte.

Localmente, na raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

Seleção de grupos e cobertura opcional:

```powershell
python -m pytest tests/test_correlation.py tests/test_correlation_v2.py tests/test_correlation_v2_edge_cases.py
python -m pytest tests/test_schema_migration.py tests/test_review_workflow.py
python -m pytest tests/test_video_analysis.py tests/test_pose_analysis.py tests/test_video_pose_flow.py
python -m pytest --cov=app --cov-report=term-missing
```

Não há percentual mínimo configurado nem percentual de cobertura garantido. A invocação por módulo evita o problema de importação entre arquivos de `tests/` observado com o comando direto `pytest` na imagem examinada.

## Correlação, migração e concorrência

A suíte cobre a borda de 300 segundos e a rejeição em 301 segundos na janela de cinco minutos. Um trio em 0, 180 e 360 segundos é rejeitado porque a amplitude total supera a janela, mesmo que os pares vizinhos sejam elegíveis. Trios suprimem pares contidos; pacientes distintos não se misturam. A representação de vídeo considera severidade, data e ID conforme o algoritmo.

Repetir o mesmo conjunto retorna lista vazia. Acrescentar uma terceira fonte após um par permite um novo trio sem apagar o par histórico. Janelas fora do intervalo 1–60 e pacientes ausentes são rejeitados.

O índice único foi exercitado com inserção duplicada em SQLite, esperando `IntegrityError`. A migração constrói um esquema legado e verifica coluna, índice, preservação das duplicatas históricas e repetibilidade. Essas verificações não demonstram isolamento, bloqueios, concorrência ou desempenho sob carga no PostgreSQL. Não execute migrações no banco operacional como parte da suíte; siga o [procedimento de manutenção](../README.md#migração-segura-de-postgresql-existente).

## Validação real de Azure e da demonstração multimodal

O comando abaixo foi executado com serviços Azure reais e retornou `PASS`:

```powershell
docker compose exec -T api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1
```

O paciente `MG-MULTI-7F34EB6D` teve um evento de áudio, um de vídeo, um de sinais vitais e uma correlação de três fontes: **quatro eventos e dois alertas persistidos**. A repetição da correlação criou zero eventos. O resultado do áudio continha transcrição real e `azure_language.status=completed`, sentimento `positive` e uma operação de entidades concluída com lista vazia para a frase utilizada. Não foram fabricadas entidades nem resultados do provedor.

O vídeo geométrico retornou `pose.status=no_pose`, preservando OpenCV e a correlação. A validação positiva de pose foi realizada separadamente com avatar. O WAV é uma preparação sintética local, não um arquivo garantido pelo Git; consulte o [guia](DEMO_GUIDE.md).

## MediaPipe Pose: inferência real

Ambiente: Docker Linux x86_64/WSL2, Python 3.12, MediaPipe 0.10.31, NumPy 2.5.5 e `opencv-python-headless` 4.14.0.94. O modelo oficial **Pose Landmarker Lite, float16, versão 1** executou em CPU com TensorFlow Lite XNNPACK. O adaptador utiliza Tasks em modo `IMAGE`, uma pessoa por amostra, sem rastreamento temporal de identidade.

Modelo: `storage/models/pose_landmarker_lite.task`, 5.777.746 bytes; SHA-256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`. A instalação, as variáveis e os comandos estão no [guia de pose](DEMO_GUIDE.md#12-preparar-e-demonstrar-pose-real).

A arte de referência do avatar foi gerada por IA, sem fotografia ou filmagem de pessoa real. [create_pose_avatar.py](../scripts/create_pose_avatar.py) aplica articulação 2D determinística por triangulação. Os dois vídeos têm 960×864, 72 quadros, 12 fps e seis segundos. O caso `smooth` contém movimento suave; `abrupt` acrescenta uma translação horizontal descontínua de 240 pixels. Trata-se de um estímulo de teste conhecido, não de uma queda clínica simulada.

O comando de validação real foi:

```powershell
docker compose exec -T api python -m scripts.validate_pose_runtime --folder /app/storage/validation/final-readiness/pose
```

| Medida observada | Movimento suave | Translação abrupta |
|---|---:|---:|
| Status | `completed` | `completed` |
| Amostras aceitas/processadas | 24/24 | 24/24 |
| Pontos corporais por pose | 33 | 33 |
| Pares comparados | 23 | 23 |
| Pico de deslocamento normalizado | 0.009745 | 0.250457 |
| Limiar preservado | 0.15 | 0.15 |
| Tempo da análise direta | 3.341 s | 4.471 s |
| Tempo HTTP do processamento completo | 3.214 s | 2.935 s |
| Eventos/alertas persistidos | 0/0 | 2/2 |

O caso abrupto gerou `abrupt_visual_change` no OpenCV e `pose_displacement_review` no MediaPipe. Análises diretas e resultados da API coincidiram; a releitura confirmou persistência e o reprocessamento retornou 409. Uma segunda passagem real gerou registros por amostra e vídeos com os pontos sobrepostos. O controle geométrico não produziu pose ou anomalia de pose e continuou produzindo a anomalia OpenCV esperada.

O paciente de pose foi `MG-POSE-A5D36EBB`. Os dados detalhados permanecem no diretório local ignorado `storage/validation/final-readiness/pose/`. Os tempos são observações específicas, influenciadas por inicialização, cache e CPU; não demonstram execução em tempo real.

`compared_pairs` conta apenas pares consecutivos aceitos. Poses separadas por falhas de detecção não são comparadas; sem pares, `peak_displacement` é `null`. O teste dessa condição utiliza simulações, sem se confundir com o ensaio real acima.

## API, dashboard e preservação

As 26 verificações contra a API real cobriram pacientes, medições, mídia, tarefas, relatórios em `result.analysis`, correlação, reprocessamento, entradas inválidas e revisão de alertas. Foram observados os códigos esperados 200, 201, 404, 409, 415 e 422, conforme o contrato. Não existe uma rota `/reports`; os relatórios são obtidos de `GET /jobs` e `GET /jobs/{job_id}`.

As 21 etapas com Streamlit AppTest executaram o aplicativo completo contra a API real: seleção de paciente, indicadores, filtros de período e origem, repetição da correlação, relatórios de áudio/vídeo/pose, reconhecimento e resolução de alertas e estado vazio. Não houve exceções ou elementos de erro. Essas etapas não integram a contagem dos 77 testes Pytest.

Hashes de conteúdo confirmaram a preservação de **221 registros originais em nove tabelas**. As validações acrescentaram apenas cenários sintéticos próprios. Não houve exclusão de dados, reinicialização de volumes ou migração nessa revisão operacional. Os comandos e resultados completos estão em [Prontidão técnica](READINESS.md).

## Integração contínua

[ci.yml](../.github/workflows/ci.yml) utiliza Ubuntu, Python 3.12, instalação editável `.[dev]` e `python -m pytest`, em envios e solicitações de integração destinados a `main`. Não executa Azure real, PostgreSQL, modelo de pose, AppTest operacional, inspeção visual, análise estática ou limiar de cobertura. A configuração foi conferida localmente; não se declara execução remota do GitHub Actions nesta validação.

## Limitações e inspeção manual

- `pip check` retorna 1 pela inconsistência de tag no wheel oficial MediaPipe 0.10.31. A [investigação](READINESS.md#exceção-de-empacotamento-do-mediapipe) preserva esse resultado, sem alterar metadados do fornecedor.
- A pose foi validada em um avatar frontal com fundo claro. Não há evidência de generalização para oclusões, outros enquadramentos ou múltiplas pessoas.
- A métrica utiliza ombros/quadris normalizados; não mede velocidade física, articulação de membros ou risco clínico. Câmera, perspectiva e amostragem influenciam o resultado.
- Os pontos persistidos são os da última pose aceita, não uma trajetória completa. Os registros detalhados do ensaio são artefatos locais separados.
- Não houve ensaio de carga, concorrência PostgreSQL, restauração integral de cópia de segurança ou compatibilidade de todos os formatos e versões.
- Inspecione manualmente disposição visual, textos, tabelas, gráficos, navegação por teclado, envio de arquivo pelo navegador e legibilidade dos vídeos externos antes de apresentar.

Não há validação clínica, garantia de segurança de produção, diagnóstico ou demonstração de causalidade entre modalidades.
'''

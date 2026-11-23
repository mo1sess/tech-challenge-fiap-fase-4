# Relatório técnico da Fase 4 — MedGuard AI

O MedGuard AI demonstra monitoramento multimodal com pacientes e dados sintéticos. A referência deste relatório é `origin/main` no commit `7028726`. Os limiares e as severidades são parâmetros educacionais de software. A aplicação destina-se exclusivamente a demonstrações acadêmicas.

## Descrição do fluxo multimodal

1. **Entrada.** O dashboard Streamlit usa a API REST FastAPI para cadastrar pacientes fictícios e registrar medições, prescrições e movimentações. O upload de áudio ou vídeo guarda o arquivo em disco, calcula o SHA-256 e persiste os metadados e um job `queued` no banco.
2. **Processamento.** As regras de sinais vitais e movimentações rodam na ingestão. A avaliação de prescrições usa a rota `/evaluate`. O processamento de mídia é síncrono, acionado por `POST /api/v1/jobs/{job_id}/process`, com estados `queued`, `processing`, `completed` e `failed`. A saída de áudio ou vídeo fica em `job.result.analysis`, acompanhada dos identificadores dos eventos e alertas gerados.
3. **Eventos e alertas.** Sinais vitais, vídeo e inconsistências operacionais podem gerar eventos e alertas persistidos. Achados afirmativos de áudio geram eventos de baixa severidade para revisão humana, com lista vazia de alertas. A API lista alertas, permite filtrá-los por paciente e estado e recebe `acknowledged` ou `resolved` via `PATCH /api/v1/alerts/{alert_id}`. O reconhecimento registra `acknowledged_at`.
4. **Correlação temporal.** A rota `POST /api/v1/patients/{patient_id}/correlations/run` compara até 100 eventos recentes elegíveis de cada origem para o mesmo paciente. Ela combina pedidos de ajuda, relatos de dor ou de dificuldade respiratória com anomalias pontuais de sinais vitais. A diferença absoluta deve caber na janela configurável de 1 a 60 minutos, com padrão de 5 minutos. O resultado é um evento de coocorrência de baixa severidade, com os IDs das fontes e sem alerta. A repetição sequencial ignora pares já persistidos. A correlação mede proximidade temporal, sem atribuição causal.
5. **Consulta.** O PostgreSQL é o banco do ambiente Docker Compose. O painel apresenta alertas abertos e resumos em português para pacientes, sinais vitais, mídia e jobs, vídeo, áudio, prescrições e movimentações. Os registros brutos ficam disponíveis para inspeção. A correlação e a atualização de estado dos alertas são operações da API.

Implementação da integração e da apresentação. [Correlação](../app/services/correlation_flow.py) · [Rotas de eventos e alertas](../app/api/routes/clinical.py) · [Dashboard](../dashboard/app.py) · [Execução e demonstrações](../README.md#execução-recomendada-com-docker).

## Modelos utilizados em cada modalidade

| Modalidade | Modelo ou técnica aplicada | Saída |
|---|---|---|
| Fala em áudio | Modelo Whisper `base` por padrão, executado por faster-whisper em CPU com `int8`. O idioma é fixado como `pt` na inferência. Azure Speech é a alternativa configurável, com reconhecimento único em `pt-BR` e modelo interno gerenciado pelo serviço. | Texto, provedor e estado do reconhecimento. |
| Sinal acústico | Métricas determinísticas sobre WAV PCM de 16 bits, com duração, taxa de amostragem, canais, RMS, pico, proporção de silêncio e clipping. | Resumo acústico do arquivo. |
| Texto transcrito | Regras locais de expressões e contexto para diferenciar afirmação, negação, histórico e relato de terceiros. O fluxo executa transcrição, análise acústica e análise textual, nessa ordem. | Achados contextuais e eventos de revisão para menções afirmativas elegíveis. |
| Vídeo | Visão computacional determinística com OpenCV e NumPy. Quadros amostrados viram imagens em tons de cinza de 160 × 90 pixels, com filtro gaussiano. A diferença absoluta entre quadros consecutivos conta pixels com variação de intensidade superior a 25. | Metadados, média e pico de movimento. A média ≤ 0,35% ou o pico ≥ 20% disparam, respectivamente, baixa variação ou mudança abrupta, com os limiares padrão. |
| Sinais vitais | Regras pontuais de frequência cardíaca, SpO₂ e pressão arterial. Na janela das quatro medições sintéticas mais recentes, as regras procuram aumento não decrescente de frequência cardíaca de pelo menos 25 bpm, queda não crescente de SpO₂ de pelo menos 4 pontos percentuais ou amplitude sistólica de pelo menos 35 mmHg. | Detecções pontuais e de tendência, com eventos e alertas. |
| Prescrições e movimentações | Regras de sequência por código de medicamento e de continuidade entre origem e destino das movimentações. | Eventos e alertas para inconsistências, como início duplicado ou quebra de continuidade. |

O reconhecimento de fala é a etapa que usa um modelo de aprendizado de máquina. Seu resultado textual alimenta regras determinísticas. O provedor local dispensa credenciais e precisa obter os pesos na primeira utilização se estiverem ausentes do cache. O Azure Speech requer rede e configuração local das variáveis `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION`. [Transcrição local](../app/modules/audio/local_speech.py) · [Adaptador Azure](../app/modules/audio/azure_speech.py) · [Processador de vídeo](../app/modules/video/processor.py) · [Regras de tendência](../app/services/temporal_analysis.py).

## Resultados obtidos e exemplos de anomalias

Uma verificação dos serviços da `main` executada para este relatório, com SQLite em memória, confirmou um evento vital crítico e um alerta aberto para 148 bpm, SpO₂ de 84% e pressão de 78/48 mmHg. Em outro paciente, a sequência de 70, 82, 94 e 106 bpm gerou um evento de tendência de severidade alta e um alerta na quarta medição. Com o texto sintético “Preciso de ajuda” fornecido diretamente ao analisador, o serviço criou um evento de áudio para revisão. A correlação desse evento com a anomalia pontual de sinais vitais criou um evento, devolveu uma lista vazia na repetição e manteve a contagem de alertas. Esse ensaio executou os serviços diretamente, incluindo persistência em memória.

A tabela detalha os resultados esperados pelas regras e as evidências versionadas. Ela inclui cenários de vídeo e operações que não foram executados neste ensaio.

| Cenário | Resultado esperado | Evidência versionada |
|---|---|---|
| Demonstração com 148 bpm, SpO₂ de 84% e pressão de 78/48 mmHg | Evento `synthetic_vital_sign_anomaly` de severidade crítica e alerta aberto. | [Demonstração da API](../app/api/routes/demo.py) e [teste do fluxo vital](../tests/test_vital_alert_flow.py) |
| Quatro medições de 70, 82, 94 e 106 bpm, em ordem cronológica | Aumento de 36 bpm na janela, com evento de tendência `synthetic_vital_trend_anomaly` e alerta na quarta medição. | [Cenário no README](../README.md#séries-temporais-e-operações--etapa-4) e [teste das regras temporais](../tests/test_phase4_detection.py) |
| Vídeo geométrico com baixa variação entre quadros | Evento `sustained_low_motion` e alerta aberto. A suíte inclui um teste direto de leitura pelo OpenCV e testes do fluxo da API. | [Testes de vídeo](../tests/test_video_analysis.py) |
| Pedido de ajuda afirmativo em transcrição simulada | Evento de revisão `audio_help_request_review`, sem alerta. | [Testes de áudio](../tests/test_audio_analysis.py) e [testes de eventos](../tests/test_audio_events.py) |
| Evento elegível de áudio e anomalia pontual de sinais vitais próximos, para o mesmo paciente | Evento `synthetic_audio_vital_correlation`. Repetir o cruzamento devolve uma lista vazia. | [Testes de correlação](../tests/test_correlation.py) |
| Início duplicado de prescrição ou origem diferente do destino da movimentação anterior | Eventos de inconsistência e alertas demonstrativos. | [Testes de regras operacionais](../tests/test_phase4_detection.py) |

### Escopo das evidências

A suíte da `main` usa SQLite e armazenamento temporários, com simulações para os provedores de transcrição. O Python disponível nesta revisão não tinha Pytest nem todas as dependências da aplicação, e o serviço Docker estava indisponível para executar a suíte. A execução real do Whisper, do Azure Speech e do OpenCV, a operação em PostgreSQL, o uso do dashboard no navegador e métricas de precisão ou desempenho ficam fora das evidências desta revisão.

Os documentos históricos da branch `feature/multimodal-dashboard` (`71cc495`) registram 77 testes aprovados, 26 verificações contra a API e 21 etapas com Streamlit AppTest, além de ensaios com Azure e MediaPipe. Esses resultados foram relatados para aquela implementação e permanecem evidência histórica daquela branch.

## Comparação das branches

A comparação usa as referências locais `origin/main` (`7028726`) e `origin/feature/multimodal-dashboard` (`71cc495`).

| Área | Implementação da `main` | Diferença na branch de funcionalidades |
|---|---|---|
| Áudio e texto | faster-whisper local por padrão, Azure Speech opcional, métricas acústicas e regras contextuais. | Remove os adaptadores local e de seleção de provedor, usa Azure Speech e acrescenta métricas acústicas e enriquecimento com sentimento e entidades via Azure AI Language. Na `main`, as variáveis `AZURE_LANGUAGE_*` estão declaradas, sem integração no fluxo. |
| Vídeo | OpenCV calcula variação visual entre quadros. | Acrescenta pose opcional com MediaPipe Pose Landmarker e regra de deslocamento corporal. |
| Sinais vitais e anomalias | Regras pontuais e janela recente de quatro medições, além de detectores operacionais. | Nos dois detectores de sinais vitais, as diferenças se limitam às docstrings. A branch acrescenta saídas associadas à pose e à correlação ampliada. |
| Correlação | Pares áudio–sinais vitais e deduplicação por IDs dos eventos no serviço. | Mantém a v1 e acrescenta v2 com pares e trios incluindo vídeo, chave de correlação e unicidade no banco. |
| Alertas | Listagem e atualização simples de estado pela API. | Acrescenta fluxo de revisão simulada, histórico persistido e ações no dashboard. |
| Dashboard | Sete abas com resumos por domínio e dados brutos sob demanda. | Reorganiza a interface em torno do paciente, com filtros, linha do tempo multimodal, relatórios e revisão de alertas. |
| Dependências e ambiente | faster-whisper, PyAV com faixa `>=11,<19`, Azure Speech SDK e cache Docker `whisper_models`. | Troca faster-whisper e PyAV por Azure Text Analytics e pandas na lista de dependências, sobe o mínimo de Streamlit e acrescenta o extra `pose`, configuração de modelo e procedimentos de migração próprios. |

O README da `main` já concentra instruções de execução, demonstrações e rotas. O relatório reúne a arquitetura, o diagrama do README, os cenários e as evidências relevantes para a entrega. Os guias históricos de API, arquitetura, demonstração, diagramas, testes e prontidão descrevem contratos e ensaios da outra branch.

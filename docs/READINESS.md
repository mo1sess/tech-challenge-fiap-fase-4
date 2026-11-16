# Prontidão técnica para entrega

[README](../README.md) · [Testes](TESTING.md) · [Arquitetura](ARCHITECTURE.md) · [Referência da API](API_REFERENCE.md)

## Resultado consolidado

A demonstração educacional foi aprovada nas verificações de execução em Docker Linux x86_64/Python 3.12. Não foi reproduzido impedimento funcional nos fluxos exercitados. Permanece uma exceção documentada de empacotamento do MediaPipe. Inspeção visual em navegador e preparação dos materiais de entrega continuam necessárias.

O escopo abrange integração de fontes sintéticas, rastreabilidade, processamento e persistência. Não há certificação de critérios de avaliação não fornecidos, validade clínica, diagnóstico ou aptidão para produção.

| Verificação de 15/11/2026 | Resultado registrado |
|---|---|
| Construção Docker sem cache e inicialização | Aprovadas; API e PostgreSQL saudáveis, dashboard em execução |
| Suíte Pytest | **77 passed in 21.39s** |
| API real | **26 verificações aprovadas** |
| Aplicativo completo com Streamlit AppTest | **21 etapas aprovadas** |
| Azure Speech e Azure AI Language reais | Transcrição e análises concluídas |
| Modelo MediaPipe real | Dois vídeos de avatar processados, sem simulações do detector |
| Correlação multimodal | Trio persistido e zero duplicatas na repetição |
| Preservação de dados | **221 registros originais com hashes de conteúdo idênticos** |
| `pip check` | Código 1; exceção de metadados detalhada abaixo |

Os resultados operacionais detalhados constam em [Testes](TESTING.md). A revisão documental para entrega não reclassifica testes simulados como inferência real nem altera as evidências anteriores.

Na preparação final do commit, os arquivos atuais passaram novamente pelos **77 testes em 20.42s**, com o repositório montado somente para leitura. Essa execução posterior valida o código revisado; as 26 verificações da API e 21 etapas AppTest continuam sendo evidências da validação operacional identificada acima. Os dez diagramas Mermaid e os exemplos documentais foram verificados separadamente.

A revisão documental conferiu sete arquivos Markdown, 114 links relativos, os caminhos das 24 operações OpenAPI, dez diagramas Mermaid, 33 blocos PowerShell e dois exemplos JSON, sem erros. A comparação dos 71 arquivos Python com a imagem validada não encontrou diferenças na AST executável após desconsiderar docstrings, textos de ajuda e descrição de procedência. Comandos, identificadores, contratos e mensagens operacionais literais foram preservados.

## Comandos e condições da validação

Os comandos foram executados a partir da raiz em PowerShell. Operações de demonstração criam novos pacientes e registros sintéticos; não excluem cenários anteriores.

| Comando | Resultado |
|---|---|
| `docker compose build --no-cache --build-arg INSTALL_POSE=true api dashboard` | Código 0; dependências reinstaladas sem reutilizar as camadas de instalação |
| `docker compose up -d --no-deps --force-recreate api dashboard` | Código 0; apenas API/dashboard recriados, com o banco e o volume existentes preservados |
| `docker compose ps` | API e PostgreSQL saudáveis; dashboard em execução |
| `docker compose exec -T api python -m pytest` | Código 0; 77 testes aprovados |
| `docker compose exec -T api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1` | Código 0 e `PASS`; quatro eventos, dois alertas e repetição sem nova correlação |
| `docker compose exec -T api python -m scripts.validate_pose_runtime --folder /app/storage/validation/final-readiness/pose` | Código 0 e `PASS`; modelo real, API, persistência e relatórios verificados |
| `docker compose exec -T api python -m pip check` | Código 1; falha de tag do wheel MediaPipe |

Uma rotina operacional local, não distribuída como dependência do projeto, registrou as 26 verificações da API, as 21 etapas AppTest e a comparação dos registros originais. Seus resultados permanecem em `storage/validation/final-readiness/runtime_review_final.json` e `records_all_preserved.json`, fora do Git. A reprodução das funcionalidades públicas utiliza os scripts versionados e o [guia](DEMO_GUIDE.md); as rotinas locais de auditoria não são pré-requisito para executar o sistema.

Base examinada: `python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`. Versões instaladas: MediaPipe 0.10.31, OpenCV sem interface gráfica 4.14.0.94, NumPy 2.5.5, Azure Speech SDK 1.53.1 e Azure Text Analytics 5.4.0.

A construção sem cache demonstrou instalação e inicialização, não reprodução binária idêntica. As imagens e a maioria das dependências ainda usam referências mutáveis ou faixas de versões. Um novo ambiente requer credenciais locais, modelo oficial, mídias sintéticas e eventual migração de esquema legado. Esses dados não são incluídos na imagem nem no Git.

## Exceção de empacotamento do MediaPipe

A investigação consultou os [metadados oficiais da versão 0.10.31 no PyPI](https://pypi.org/pypi/mediapipe/0.10.31/json) e conferiu o SHA-256 do wheel Linux:

| Item | Valor observado |
|---|---|
| Arquivo | `mediapipe-0.10.31-py3-none-manylinux_2_28_x86_64.whl` |
| SHA-256 | `360de896205822419b14d7574c2812e08946769228f7548c31dd871b150d9bcc` |
| Tag interna de `WHEEL` | `cp39-cp39-linux_x86_64` |
| Biblioteca nativa | `mediapipe/tasks/c/libmediapipe.so` |

A tag interna `cp39` não é compatível com as tags declaradas pelo interpretador Python 3.12, embora o nome do arquivo indique `py3`. A inconsistência existe no pacote oficial e no instalado. `pip check` retorna a mensagem literal `mediapipe 0.10.31 is not supported on this platform` e código 1.

Instalação, importação e inferência real em CPU funcionaram no ambiente examinado. Os metadados não foram modificados para suprimir o erro. A versão foi mantida porque versões posteriores examinadas instalaram `opencv-contrib-python` gráfico sobre `cv2`, resultando em falha de bibliotecas de sistema no contêiner mínimo.

Trata-se de uma **exceção de empacotamento documentada**, sem falha funcional reproduzida neste ambiente. Uma verificação que exija `pip check` sem erros continuará reprovada. Outras plataformas e versões de Python não foram certificadas. Evidências locais: `official_wheel.json` e `pip_check.json`, no diretório de validação.

## Evidências de execução real

No cenário `MG-MULTI-7F34EB6D`, a transcrição real não foi vazia e `azure_language.status=completed`. O sentimento retornado foi `positive`; a operação de entidades concluiu com lista vazia para a frase utilizada. Lista vazia é um resultado válido, não uma entidade omitida ou fabricada. OpenCV, sinais vitais e correlação produziram quatro eventos e dois alertas persistidos. Repetir a correlação retornou `[]`.

No cenário `MG-POSE-A5D36EBB`, ambos os vídeos tiveram 24/24 amostras aceitas, 33 pontos corporais e 23 pares comparáveis. O deslocamento máximo foi 0.009745 no movimento suave e 0.250457 na translação abrupta, diante do limiar 0.15. O segundo gerou um alerta OpenCV e um alerta de revisão de pose. Os tempos e a procedência sintética estão documentados em [Testes](TESTING.md#mediapipe-pose-inferência-real).

As verificações da API incluíram leitura de pacientes, medições, mídias, tarefas e relatórios; rejeição de reprocessamento; correlação idempotente; entradas inválidas; reconhecimento/resolução de alertas; histórico e isolamento por paciente. Os códigos 200, 201, 404, 409, 415 e 422 corresponderam aos contratos. A API não possui rota `/reports`; o dashboard utiliza `ProcessingJob.result.analysis`.

O aplicativo completo executou com AppTest contra a API real, sem simular as requisições. Foram exercitados indicadores, filtros, correlação, relatórios de áudio/vídeo/pose, ações de revisão e um paciente vazio, sem exceções ou elementos de erro.

## Preservação dos registros

A comparação utilizou hashes dos valores de todas as colunas dos registros originais. Nenhum registro anterior foi removido ou alterado; apenas os cenários novos receberam ações de revisão.

| Tabela | Antes da validação | Após os cenários novos | Registros originais ausentes/alterados |
|---|---:|---:|---:|
| `patients` | 15 | 18 | 0 |
| `media_files` | 38 | 42 | 0 |
| `processing_jobs` | 38 | 42 | 0 |
| `clinical_measurements` | 17 | 18 | 0 |
| `prescriptions` | 2 | 2 | 0 |
| `patient_movements` | 1 | 1 | 0 |
| `clinical_events` | 71 | 77 | 0 |
| `alerts` | 37 | 41 | 0 |
| `alert_review_actions` | 2 | 6 | 0 |

Não foram removidos volumes nem executadas migrações nessa validação operacional. A limpeza para entrega remove o backup SQL apenas do rastreamento do Git, preservando a cópia local, o banco e os modelos instalados.

## Organização e segurança do repositório

O conjunto de entrega inclui fontes, testes, migrações aditivas, scripts, configurações sem credenciais e documentação em PT-BR. Foram retiradas instruções textuais de modelo que não descreviam o projeto; não foram alteradas autorias de commits anteriores ou atribuídas contribuições individuais. A origem por IA da arte sintética foi mantida como informação de procedência dos dados, não de autoria do software.

`.env`, cópias de banco, arquivos de modelo, vídeos e evidências locais ficam fora do versionamento. `.dockerignore` também exclui armazenamento, evidências e bytecode. As mídias e o pacote de modelo oficial continuam exigindo preparação local explícita. A cópia `medguard-backup.sql` permanece disponível localmente, mas não integra o novo estado versionado; o histórico anterior do Git não foi reescrito.

A auditoria heurística dos arquivos selecionados não detectou credenciais ou artefatos gerados indevidos. Isso não representa uma análise forense exaustiva de todos os objetos históricos do Git. Nomes de bibliotecas, identificadores, rotas, estados, comandos e saídas literais foram preservados, mesmo quando estão em inglês, para manter a correspondência com o código.

## Pendências e melhorias opcionais

Antes de apresentar, inspecione manualmente:

1. Disposição visual, tabelas, gráficos, textos em português e comportamento em janela estreita.
2. Envio de arquivos no navegador, navegação por teclado e interações dos gráficos.
3. Legibilidade dos pontos corporais nos vídeos AVI externos; o dashboard não oferece reprodução embutida ou uma API de download de mídia.
4. Roteiro, apresentação e vídeo final exigidos pela equipe responsável pela entrega.

AppTest verifica execução e comportamento dos controles, mas não comprova apresentação visual ou acessibilidade. Os resultados não certificam precisão clínica ou execução em tempo real. Pose permanece um ensaio com avatar frontal, modo `IMAGE` e métrica de deslocamento de ombros/quadris normalizados, influenciada por câmera, perspectiva e amostragem.

Melhorias opcionais: travamento completo de versões e imagens, adoção de um wheel oficial corrigido após nova validação, testes de concorrência PostgreSQL, ensaio de restauração, automação de navegador mais ampla, paginação e recuperação de tarefas interrompidas. Autenticação, TLS e controles de produção não estão implementados.
'''

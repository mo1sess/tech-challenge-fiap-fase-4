# Guia de demonstração multimodal

[README](../README.md) · [API](API_REFERENCE.md) · [Testes](TESTING.md)

## Objetivo e resultado validado

Demonstrar paciente sintético → vídeo → áudio → medição anômala → correlação de três fontes → repetição sem duplicata → consulta persistida no Dashboard v2. A correlação é **coocorrência temporal**, sem causalidade, diagnóstico ou determinação de risco clínico.

A validação operacional de 15/11/2026 executou o comando abaixo com Azure real, persistência PostgreSQL e verificações separadas do dashboard por Streamlit AppTest:

```powershell
docker compose exec api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1
```

| Resultado observado | Quantidade |
|---|---|
| Paciente sintético criado | 1 |
| Evento de vídeo | 1 |
| Evento de áudio | 1 |
| Evento anômalo de sinais vitais | 1 |
| Correlação com três fontes | 1 |
| Novas correlações na repetição | 0 |
| Eventos persistidos | 4 |
| Alertas persistidos | 2 |
| Resultado | `PASS` |

Esses números descrevem uma execução específica, não uma garantia para qualquer WAV ou configuração. Consulte [Testes](TESTING.md) e [Prontidão técnica](READINESS.md) para as evidências de Azure e pose reais. O script [demo_multimodal.py](../scripts/demo_multimodal.py) exige a presença de um trio e a ausência de novas correlações na segunda chamada; não exige exatamente quatro eventos e dois alertas.

## 1. Preparar o ambiente

Na raiz do projeto, siga [instalação e configuração](../README.md#instalação-e-configuração). Para banco antigo, faça a migração segura antes de iniciar a aplicação. Não remova volumes ou resete o banco para demonstrar.

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Use o comando de subida acima depois de resolver eventual migração pendente. API e banco devem estar saudáveis; dashboard disponível em `http://localhost:8501`. O código de scripts precisa estar na imagem: o Dockerfile atual copia `scripts/`. Não há bind mount do código.

## 2. Pré-requisitos da demonstração

- Docker com API, PostgreSQL e dashboard ativos.
- OpenCV/NumPy instalados pela imagem e suporte ao codec MJPG para gerar o AVI.
- Recurso Azure Speech válido, rede e credenciais locais; Azure AI Language configurado para demonstrar o enriquecimento textual real.
- Arquivo WAV de fala **inteiramente sintética**, com frase afirmativa reconhecível em português brasileiro.
- Janela de correlação suficiente para o intervalo entre o evento de vídeo e a medição final; padrão 5 minutos.

O script e a interface usam `requests` com tempo limite de 90 segundos por chamada. Uma análise demorada pode ultrapassar esse limite sem que a API interrompa automaticamente o processamento.

## 3. Configurar os serviços Azure com segurança

No `.env` local, preencha `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` conforme o recurso Speech da conta. Para demonstrar sentimento e entidades gerais, configure também `AZURE_LANGUAGE_ENDPOINT` e `AZURE_LANGUAGE_KEY`. Não mostre o arquivo durante a apresentação nem inclua valores em capturas de tela ou registros compartilhados. As regras textuais locais continuam funcionando sem Azure AI Language, com estado explícito `not_configured` no enriquecimento.

```powershell
docker compose up -d --force-recreate api
```

A aplicação lê configurações no processo; somente editar `.env` não atualiza um contêiner existente. O adaptador faz um reconhecimento único em `pt-BR`, não transcrição contínua. Azure pode ter custos e limites da conta; eles não foram medidos pelo projeto.

## 4. Preparar o WAV sintético

`storage/test_audio2.wav` é um arquivo **local**, sem presença garantida no Git. Não inclua gravação de paciente ou voz pessoal. Gere a fala em uma ferramenta de síntese de voz de sua escolha e exporte como WAV PCM de 16 bits sem compressão, preferencialmente mono, 16 kHz, com frase curta e clara:

> Preciso de ajuda.

Essa frase é um padrão afirmativo exato de `help_request`. Use uma única categoria para facilitar a reprodução de um evento de áudio. Tom puro ou silêncio gerados com NumPy não substituem fala para esta demonstração. Frases negadas/históricas ou sem padrões reconhecidos podem concluir sem evento. Outras frases podem produzir múltiplas categorias e contagens diferentes.

Salve o arquivo em `storage/test_audio2.wav`. O bind mount `./storage:/app/storage` torna esse caminho acessível dentro do contêiner. O WAV fonte não precisa ficar em `uploads/`; o upload via API cria sua cópia gerenciada.

Verifique existência e formato sem revelar conteúdo:

```powershell
Test-Path .\storage\test_audio2.wav
docker compose exec api python -c "import wave; w=wave.open('/app/storage/test_audio2.wav','rb'); print(w.getparams()); w.close()"
```

Espere `sampwidth=2`, `comptype='NONE'` e frames positivos. Essa inspeção não comprova qualidade de fala ou reconhecimento Azure. O limite de upload é 25 MiB por padrão. Arquivos de áudio locais em `storage/` são ignorados pelas regras atuais; ainda assim confira os arquivos selecionados antes de qualquer commit.

## 5. Executar o script

```powershell
docker compose exec api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1
```

`localhost` nesse comando é o próprio contêiner `api`, que executa o servidor. Para executar o script no host com dependências instaladas, use caminho local no argumento `--audio` e a mesma URL pública.

| Argumento | Contrato |
|---|---|
| `--audio` | Obrigatório, arquivo WAV existente no ambiente onde o script roda |
| `--api-url` | Padrão `http://localhost:8000/api/v1`; deve incluir o prefixo |
| `--window` | Inteiro 1–60, padrão 5 minutos |
| `--patient-code` | Opcional; novo código válido e único, senão cadastro retorna 409 |

O script cria `MG-MULTI-XXXXXXXX` com sufixo aleatório por padrão. Anote `patient_id` e `patient_code` mostrados no terminal. Não reutilize o mesmo `--patient-code` esperando retomada: o script sempre tenta cadastrar um novo paciente.

## 6. Resultado esperado e rastreabilidade

O script faz sete etapas: cria paciente; gera/processa vídeo temporário; envia/processa o WAV; insere medição com frequência 145, SpO2 90, sistólica 125 e diastólica 80; executa v2; repete v2; consulta eventos e alertas persistidos.

Com uma categoria de áudio reconhecida e limiares padrão, o cenário histórico foi de três eventos de origem, um derivado e dois alertas (vídeo e sinais vitais). Áudio e correlação não geram alertas. Os resultados reais dependem de reconhecimento, histórico, parâmetros e duração da execução.

O resumo JSON mostra `patient_id`, `patient_code`, contagens por fonte, `created_correlations`, `three_source_correlations`, `repeat_created_correlations`, `persisted_events`, `persisted_alerts`, `correlation_ids` e `result`. Sucesso exige pelo menos um trio com `sources` igual a áudio/vídeo/vital e repetição vazia. O processo termina com código 0 em sucesso; `DemoError` gera mensagem `DEMO FAILED` e código 1. Argumentos inválidos são rejeitados pelo parser.

O script só usa REST, sem alteração direta no banco. Não faz rollback global nem limpa dados em caso de falha: etapas anteriores podem estar persistidas. Não exclua esses registros para esconder falhas; identifique o novo paciente em uma próxima execução.

## 7. Encontrar o paciente e abrir o Dashboard v2

Abra `http://localhost:8501`, entre na aba **Monitoramento multimodal** e selecione o código anotado. Use **Atualizar dados** e período **Todos** inicialmente. A v2 é parte de `dashboard/app.py`; não é necessário executar `multimodal_v2.py` separadamente.

Se o paciente não aparecer, o seletor consulta os 100 mais recentes; confirme código/ID com `GET /api/v1/patients?limit=500` e confira se host, API e banco correspondem ao ambiente demonstrado.

## 8. Interpretar a interface

1. **KPIs**: no cenário histórico, três eventos de origem, uma correlação, um trio, dois alertas abertos e uma medição. Não confunda eventos de origem com todos os eventos persistidos.
2. **Visão executiva**: barras mostram origens e severidades dos eventos de origem, sem somar correlações na distribuição.
3. **Tendências vitais**: uma amostra confirma persistência, mas não caracteriza evolução. Para demonstrar séries, use outro paciente com pelo menos quatro medições sintéticas; frequência 70, 82, 94 e 106 exemplifica a regra temporal.
4. **Explorador de correlações**: filtre trios, selecione o derivado e examine `source_event_ids`, `source_events`, `source_count`, `time_span_seconds` e `window_minutes`.
5. **Linha do tempo**: mostre as três origens e o evento de coocorrência; origens podem compartilhar horários próximos de processamento.
6. **Alertas**: diferencie severidade do evento de origem do estado operacional do alerta. Na fila v2, informe responsável fictício e nota; use **Reconhecer alerta** e **Resolver alerta** e confira o histórico persistido. Resolvido é um estado terminal.
7. **Relatórios de mídia**: alterne entre áudio e vídeo para conferir transcrição, Azure AI Language, acústica, OpenCV e o estado de pose. O vídeo geométrico da demonstração deve retornar `no_pose`; use o cenário de avatar para evidenciar inferência positiva.

O dashboard filtra período localmente sobre até 500 registros recentes por recurso. Não são totais globais garantidos. Se a origem estiver fora do recorte, o explorador usa seu resumo persistido na correlação. O horário formatado depende do fuso do processo Streamlit.

## 9. Demonstrar idempotência

O próprio script chama a correlação duas vezes sobre o mesmo paciente: a segunda retorna zero novos eventos. No explorador, clique novamente em **Executar correlação v2** sem ingerir novas origens; espere mensagem sem novas correlações e KPI estável.

Também é possível verificar por API:

```powershell
$base = "http://localhost:8000/api/v1"
$pacienteId = "SUBSTITUA_PELO_PATIENT_ID_DO_RESUMO"
Invoke-RestMethod -Method Post "$base/patients/$pacienteId/correlations/run-v2?window_minutes=5"
```

A idempotência vale para os mesmos IDs de origem. Reexecutar o script inteiro cria outro paciente e novas origens; não testa a mesma combinação. Ingerir novos eventos pode criar novos trios. Ampliar a janela não duplica conjuntos já existentes, pois a janela não compõe o fingerprint.

## 10. Solução de erros frequentes

| Sintoma | Verificação e ação |
|---|---|
| `Audio fixture not found` | Confirme `Test-Path`, bind mount e caminho interno `/app/storage/...` |
| `No module named scripts.demo_multimodal` | Confirme que a imagem foi reconstruída com o Dockerfile atual e contém `scripts/` |
| 422 de credenciais/cancelamento Azure | Confira chave/região no ambiente local, recrie API e verifique rede/recurso; não publique segredos |
| Job conclui sem evento de áudio | Inspecione transcrição no resultado; use fala clara `Preciso de ajuda.`; confirme categoria afirmativa |
| WAV inválido | Verifique PCM 16 bits sem compressão, frames e ausência de truncamento |
| 413/415 no upload | Confira limite e extensão; mudar extensão não converte o conteúdo |
| Sem evento de vídeo | Confira limiares e resultado OpenCV; restaure valores padrão no ambiente de demonstração se foram alterados |
| Sem trio | Confirme mesmo paciente, tipos elegíveis e amplitude temporal; use `--window` maior se necessário, até 60 |
| 409 no paciente | Use novo código; `--patient-code` não significa reutilizar paciente |
| 409 no processamento | Job já está `processing` ou `completed`; consulte seu estado antes de repetir |
| API não inicia por migração | Execute a migração segura do README; não apague volumes |
| Tempo limite no dashboard | Consulte o job pela API; o processamento pode continuar após os 90 s da interface |
| Erro de conexão | Confira `docker compose ps`, portas e URL; `http://api:8000` serve ao dashboard dentro do Compose |
| KPI inesperado | Confira paciente, período, recorte e categorias de áudio; não presuma contagens fixas |

Logs podem conter transcrição e detalhes de erro. Consulte-os localmente com cuidado, sem projetar segredos ou compartilhar conteúdo pessoal.

## 11. Roteiro de apresentação de 5–8 minutos

| Tempo aproximado | Ação e mensagem |
|---|---|
| 0:00–0:45 | Apresentar problema de integração e escopo exclusivamente sintético |
| 0:45–1:30 | Mostrar arquitetura: Streamlit, FastAPI modular, PostgreSQL, disco, OpenCV e Azure |
| 1:30–3:00 | Executar script preparado; acompanhar etapas e anotar paciente; manter resultado anterior disponível se a rede falhar |
| 3:00–4:00 | Selecionar paciente e explicar KPIs, origens e medição |
| 4:00–5:15 | Abrir trio, mostrar IDs de origem, janela e resumo; explicar coocorrência sem causalidade |
| 5:15–6:00 | Repetir correlação e demonstrar zero novos eventos |
| 6:00–7:00 | Mostrar linha do tempo, dois alertas e resumo dos testes |
| 7:00–8:00 | Explicar limites: regras, síncrono, recortes, simulações e evolução |

Ensaie com antecedência e prepare uma captura local sem segredos do cenário histórico. Não atribua à execução atual um resultado anterior. Se não houver rede Azure, explique a limitação e demonstre os resultados já persistidos, identificando sua origem. Separe a demonstração de tendência em outro paciente para não alterar as contagens do cenário principal.


## 12. Preparar e demonstrar pose real

O MediaPipe é opcional e utiliza o pacote de modelo oficial **Pose Landmarker Lite, float16, versão 1**. A configuração preserva a análise OpenCV. Faça o download explícito no computador; não há obtenção automática de pesos pela aplicação:

```powershell
New-Item -ItemType Directory -Force storage/models | Out-Null
$modeloPose = "storage/models/pose_landmarker_lite.task"
if (-not (Test-Path $modeloPose)) {
    Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" -OutFile $modeloPose
}
$hashModeloPose = (Get-FileHash $modeloPose -Algorithm SHA256).Hash.ToLower()
if ($hashModeloPose -ne "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a") {
    throw "O arquivo local difere do modelo oficial validado; verifique-o antes de continuar."
}
```

No `.env` local, além das demais opções do ambiente:

```dotenv
INSTALL_POSE=true
VIDEO_POSE_ENABLED=true
VIDEO_POSE_MODEL_PATH=/app/storage/models/pose_landmarker_lite.task
VIDEO_POSE_DISPLACEMENT_THRESHOLD=0.15
```

Reconstrua e recrie somente os serviços de aplicação:

```powershell
docker compose build api dashboard
docker compose up -d --no-deps api dashboard
docker compose ps
```

O extra fixa `mediapipe==0.10.31`. `pip check` apresenta uma [exceção documentada de metadados](READINESS.md#exceção-de-empacotamento-do-mediapipe), sem impedir a inferência real no ambiente validado. O modelo fica no diretório local ignorado `storage/models/`; verifique a licença antes de redistribuir os pesos.

Para o ensaio positivo, prepare arte **inteiramente sintética** em PNG, 1024×1536, com um avatar humanoide de corpo inteiro em posição frontal, braços afastados do tronco, membros visíveis e fundo claro. A referência da validação foi gerada por IA, sem fotografia de pessoa real. Salve sua referência local em `storage/validation/avatar_source.png`.

O gerador foi calibrado para a arte utilizada no ensaio. Outra imagem pode exigir adaptação dos pontos de controle e produzir resultados diferentes; não se garante detecção positiva ou reprodução exata dos números com qualquer avatar. Os arquivos originais não são distribuídos pelo Git. Preserve-os localmente para repetir exatamente aquela execução. Não substitua essa preparação por filmagem real.

Para gerar novos arquivos sem sobrescrever os anteriores, use uma pasta própria para cada ensaio:

```powershell
docker compose exec -T api python -m scripts.create_pose_avatar --source /app/storage/validation/avatar_source.png --output /app/storage/validation/ensaio-pose/avatar_smooth.avi
docker compose exec -T api python -m scripts.create_pose_avatar --source /app/storage/validation/avatar_source.png --output /app/storage/validation/ensaio-pose/avatar_abrupt.avi --abrupt
docker compose exec -T api python -m scripts.validate_pose_runtime --folder /app/storage/validation/ensaio-pose
```

Use uma pasta ainda inexistente ao repetir o ensaio, pois os scripts gravam vídeos e relatórios nos caminhos fornecidos. O validador carrega o modelo real, faz inferência direta, envia os vídeos pela API, verifica eventos/alertas, relê os resultados persistidos e executa AppTest nos relatórios. Ele cria um novo paciente sintético e não altera os registros anteriores. Testes com simulações não substituem essa execução.

Na execução validada, ambos os vídeos tiveram 24 amostras aceitas e 33 pontos por pose. O movimento suave ficou abaixo de 0.15; a translação abrupta excedeu o limiar e gerou revisão. Esse resultado não representa detecção de queda, velocidade física ou precisão clínica. A métrica utiliza ombros e quadris, não a amplitude isolada de mãos ou joelhos.

## 13. Conferência antes da apresentação

Na aba **Relatórios de mídia**, confira resultados reais e estados explícitos de indisponibilidade. Na aba **Alertas**, filtre severidade e estado, reconheça um alerta novo e resolva-o com responsável fictício; confira as duas ações com horários. Não use nomes de profissionais reais.

Antes de uma migração necessária, faça uma cópia com `pg_dump -Fc`, mantenha-a em diretório local ignorado e verifique o catálogo com `pg_restore --list`. A migração de revisões é aditiva e repetível; a tabela nova também é criada por `create_all()` na inicialização. Não remova volumes nem recrie o banco para demonstrar.

Inspecione o navegador e os vídeos com antecedência. Se não houver rede Azure, apresente os resultados já persistidos como evidência de uma execução anterior, identificando sua origem. Não atribua resultados anteriores a uma tentativa atual malsucedida.

# Guia de demonstração multimodal

[README](../README.md) · [API](API_REFERENCE.md) · [Testes](TESTING.md)

## Objetivo e evidência histórica

Demonstrar paciente sintético → vídeo → áudio → medição anômala → correlação de três fontes → repetição sem duplicata → consulta persistida no Dashboard v2. A correlação é **coocorrência temporal**, sem causalidade, diagnóstico ou determinação de risco clínico.

A equipe informou execução anterior bem-sucedida do comando abaixo, seguida de confirmação visual no Dashboard v2:

```powershell
docker compose exec api python -m scripts.demo_multimodal --audio /app/storage/test_audio2.wav --api-url http://localhost:8000/api/v1
```

| Resultado histórico informado | Quantidade |
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

Esses números são uma evidência histórica específica, não garantia para qualquer WAV ou configuração. Esta revisão documental não repetiu chamadas pagas do Azure nem criou outro paciente para reproduzir esse cenário. O script [demo_multimodal.py](../scripts/demo_multimodal.py) valida a presença de trio e a ausência de novas correlações na segunda chamada; não exige exatamente quatro eventos e dois alertas.

## 1. Preparar o ambiente

Na raiz do projeto, siga [instalação e configuração](../README.md#pré-requisitos-e-configuração). Para banco antigo, faça a migração segura antes de iniciar a aplicação. Não remova volumes ou resete o banco para demonstrar.

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Use o comando de subida acima depois de resolver eventual migração pendente. API e banco devem estar saudáveis; dashboard disponível em `http://localhost:8501`. O código de scripts precisa estar na imagem: o Dockerfile atual copia `scripts/`. Não há bind mount do código.

## 2. Pré-requisitos da demonstração

- Docker com API, PostgreSQL e dashboard ativos.
- OpenCV/NumPy instalados pela imagem e suporte ao codec MJPG para gerar o AVI.
- Recurso Azure Speech válido, rede e credenciais locais.
- Arquivo WAV de fala **inteiramente sintética**, com frase afirmativa reconhecível em português brasileiro.
- Janela de correlação suficiente para o intervalo entre o evento de vídeo e a medição final; padrão 5 minutos.

O script usa `requests` com timeout de 90 segundos por chamada. A interface usa 20 segundos; uma transcrição pode exceder o timeout visual, mesmo se a API continuar trabalhando.

## 3. Configurar Azure Speech com segurança

No `.env` local, preencha `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION` conforme o recurso Speech da conta. Não mostre o arquivo durante a apresentação e não inclua valores em screenshots/logs compartilhados. Não é preciso configurar Azure Language: a análise textual é local.

```powershell
docker compose up -d --force-recreate api
```

A aplicação lê configurações no processo; somente editar `.env` não atualiza um container existente. O adaptador faz um reconhecimento único em `pt-BR`, não transcrição contínua. Azure pode ter custos e limites da conta; eles não foram medidos pelo projeto.

## 4. Preparar o WAV sintético

`storage/test_audio2.wav` é um arquivo **local**, sem presença garantida no Git. Não inclua gravação de paciente ou voz pessoal. Gere a fala em uma ferramenta de síntese de voz de sua escolha e exporte como WAV PCM de 16 bits sem compressão, preferencialmente mono, 16 kHz, com frase curta e clara:

> Preciso de ajuda.

Essa frase é um padrão afirmativo exato de `help_request`. Use uma única categoria para facilitar a reprodução de um evento de áudio. Tom puro ou silêncio gerados com NumPy não substituem fala para esta demonstração. Frases negadas/históricas ou sem padrões reconhecidos podem concluir sem evento. Outras frases podem produzir múltiplas categorias e contagens diferentes.

Salve o arquivo em `storage/test_audio2.wav`. O bind mount `./storage:/app/storage` torna esse caminho acessível dentro do container. O WAV fonte não precisa ficar em `uploads/`; o upload via API cria sua cópia gerenciada.

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

`localhost` nesse comando é o próprio container `api`, que executa o servidor. Para executar o script no host com dependências instaladas, use caminho local no argumento `--audio` e a mesma URL pública.

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
6. **Alertas**: diferencie severidade do evento de origem do status operacional do alerta. A tabela v2 é consultiva; reconhecer/resolver é feito pela API.

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
| Timeout no dashboard | Consulte o job pela API; processamento pode continuar após os 20 s da interface |
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
| 7:00–8:00 | Explicar limites: regras, síncrono, recortes, mocks e evolução |

Ensaie com antecedência e prepare uma captura local sem segredos do cenário histórico. Não atribua à execução atual um resultado anterior. Se não houver rede Azure, explique a limitação e demonstre os resultados já persistidos, identificando sua origem. Separe a demonstração de tendência em outro paciente para não alterar as contagens do cenário principal.

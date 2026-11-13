# Diagramas da implementação

[README](../README.md) · [Arquitetura](ARCHITECTURE.md)

Os diagramas usam Mermaid para visualização no GitHub. Representam dados sintéticos e processamento síncrono. Setas indicam chamadas ou fluxo de dados; não indicam causalidade clínica.

## 1. Arquitetura geral

```mermaid
flowchart LR
    U[Usuário] --> UI[Dashboard Streamlit]
    UI -->|REST| API[API FastAPI]
    CLI[Script demo_multimodal] -->|REST| API
    API --> S[Serviços e regras determinísticas]
    S --> DB[(PostgreSQL)]
    API --> FS[Storage local de mídia]
    S --> FS
    S --> V[OpenCV e NumPy]
    S --> A[Adaptador Azure Speech]
    A --> AZ[Azure Speech-to-Text]
```

## 2. Componentes e integrações

```mermaid
flowchart TD
    MAIN[app.main: create_app] --> ROUTER[app.api.router]
    ROUTER --> P[patients]
    ROUTER --> C[clinical]
    ROUTER --> M[media]
    ROUTER --> D[demo]
    ROUTER --> R[correlation]
    SCH[Schemas Pydantic] --> ROUTER
    DEP[get_db: sessão por requisição] --> ROUTER
    C --> CF[clinical_flow e temporal_analysis]
    C --> OP[prescription_flow e movement_flow]
    M --> AF[audio_flow]
    M --> VF[video_flow]
    D --> CF
    D --> VF
    R --> COR[correlation_flow e correlation_v2]
    AF --> AUDIO[Azure Speech, acústica e regras textuais]
    VF --> VIDEO[OpenCV: diferença entre quadros]
    CF --> ORM[Modelos SQLAlchemy]
    OP --> ORM
    AF --> ORM
    VF --> ORM
    COR --> ORM
    ORM --> DB[(Banco relacional)]
```

## 3. Processamento de áudio

```mermaid
flowchart TD
    UP[Upload WAV sintético] --> VAL[Paciente, extensão e tamanho]
    VAL --> STORE[Arquivo, SHA-256, mídia e job queued]
    STORE --> POST[POST jobs por ID: process]
    POST --> STATE[processing e progresso 10]
    STATE --> AZ[Azure Speech: reconhecimento único pt-BR]
    AZ --> AC[PCM 16 bits: métricas acústicas locais]
    AC --> TXT[Regras textuais e classificação de contexto]
    TXT --> YES{Categoria afirmativa?}
    YES -->|Sim| EV[Evento low por categoria e job]
    YES -->|Não| EMPTY[Sem evento de revisão]
    EV --> DONE[completed: resultado, progresso 100 e commit]
    EMPTY --> DONE
    AZ -->|Erro previsto| FAIL[Rollback e job failed]
    AC -->|Erro previsto| FAIL
    TXT -->|Erro previsto| FAIL
```

O áudio não cria alertas. `NoMatch` pode concluir sem eventos. Detalhes em [Arquitetura](ARCHITECTURE.md#3-áudio-azure-speech-e-análise-local).

## 4. Processamento de vídeo

```mermaid
flowchart TD
    IN[Upload ou gerador geométrico] --> JOB[Mídia e job queued]
    JOB --> RUN[Processamento explícito: processing]
    RUN --> CV[OpenCV VideoCapture e metadados]
    CV --> SAMPLE[Amostragem e limite de quadros analisados]
    SAMPLE --> GRAY[Cinza 160x90 e GaussianBlur]
    GRAY --> DIFF[Diferença absoluta e limiar 25]
    DIFF --> MET[Média e pico de pixels alterados]
    MET --> RULE[Baixa variação ou mudança abrupta]
    RULE --> EV[Evento e alerta por anomalia]
    EV --> OK[completed com análise e IDs]
    CV -->|Erro previsto| FAIL[Rollback e failed]
    SAMPLE -->|Menos de dois quadros| FAIL
```

Ausência de anomalia permite conclusão sem eventos/alertas. Não há reconhecimento de pessoas.

## 5. Ingestão de sinais vitais

```mermaid
flowchart TD
    REQ[POST measurements por paciente] --> VAL[Pydantic e existência do paciente]
    VAL --> SAVE[Medição sintética e flush]
    SAVE --> POINT[Regras pontuais demonstrativas]
    POINT --> PEV[Se houver detecção: evento vital_signs e alerta]
    POINT --> TREND[Consultar quatro medições mais recentes]
    PEV --> TREND
    TREND --> TR[Regras de frequência, SpO2 e sistólica]
    TR --> TEV[Se houver detecção: evento vital_trends e alerta]
    TR --> COMMIT[Commit e resposta com medição, eventos e alertas]
    TEV --> COMMIT
```

## 6. Correlação multimodal v2

```mermaid
flowchart TD
    RUN[POST run-v2] --> CHECK[Paciente sintético e janela de 1 a 60 minutos]
    CHECK --> LOAD[Até 30 eventos elegíveis por fonte]
    LOAD --> DEDUP[Um representante por job de vídeo]
    DEDUP --> TRIPLE[Enumerar áudio x vídeo x sinais vitais]
    TRIPLE --> WIN[Validar amplitude temporal total]
    WIN --> PAIR[Pares áudio-vídeo e vídeo-vitais]
    PAIR --> PRIOR[Suprimir pares contidos em trios elegíveis]
    PRIOR --> IDS[IDs de origem ordenados]
    IDS --> OLD{Conjunto já persistido?}
    OLD -->|Sim| SKIP[Ignorar combinação]
    OLD -->|Não| HASH[JSON compacto e fingerprint SHA-256]
    HASH --> INSERT[Savepoint e inserção com correlation_key única]
    INSERT -->|Conflito de integridade| SKIP
    INSERT --> NEW[Evento de coocorrência low sem alerta]
    SKIP --> FIN[Commit e retorno somente de eventos novos]
    NEW --> FIN
```

A janela é a diferença entre o primeiro e o último evento do conjunto. A v2 não cria par áudio–sinais vitais sem vídeo; esse par pertence à v1.

## 7. Entidades persistidas

```mermaid
erDiagram
    patients ||--o{ clinical_measurements : possui
    patients ||--o{ media_files : possui
    patients ||--o{ processing_jobs : possui
    patients ||--o{ prescriptions : possui
    patients ||--o{ patient_movements : possui
    patients ||--o{ clinical_events : possui
    patients ||--o{ alerts : possui
    media_files o|--o{ processing_jobs : referencia
    clinical_measurements o|--o{ clinical_events : referencia
    clinical_events ||--o| alerts : origina
    patients {
        string id PK
        string code UK
        string alias
        boolean is_synthetic
    }
    clinical_measurements {
        string id PK
        string patient_id FK
        datetime measured_at
        float heart_rate_bpm
        float spo2_percent
    }
    media_files {
        string id PK
        string patient_id FK
        string storage_path
        string sha256
        string kind
    }
    processing_jobs {
        string id PK
        string patient_id FK
        string media_file_id FK
        string status
        float progress
        json result
    }
    prescriptions {
        string id PK
        string patient_id FK
        string medication_code
        string action
    }
    patient_movements {
        string id PK
        string patient_id FK
        string from_location
        string to_location
    }
    clinical_events {
        string id PK
        string patient_id FK
        string measurement_id FK
        string correlation_key UK
        string source
        string event_type
        json payload
    }
    alerts {
        string id PK
        string patient_id FK
        string event_id FK, UK
        string status
    }
```

Modelo simplificado: campos opcionais e demais métricas estão em [models.py](../app/db/models.py). IDs de origem em payloads não são FKs; o arquivo binário não fica no banco.

## 8. Sequência da demonstração multimodal

```mermaid
sequenceDiagram
    actor Operador
    participant Script as demo_multimodal.py
    participant API as FastAPI e serviços
    participant Disco as Storage local
    participant Azure as Azure Speech
    participant DB as PostgreSQL
    participant UI as Dashboard v2
    Operador->>Script: Executar com WAV sintético local
    Script->>API: POST patients
    API->>DB: Persistir paciente único
    API-->>Script: patient_id e code
    Script->>Script: Gerar vídeo geométrico temporário
    Script->>API: Upload de vídeo
    API->>Disco: Salvar vídeo
    API->>DB: Mídia e job queued
    Script->>API: Processar job de vídeo
    API->>Disco: Ler e analisar com OpenCV
    API->>DB: Resultado, evento e alerta
    Script->>API: Upload e processamento do WAV
    API->>Disco: Salvar e ler WAV
    API->>Azure: Reconhecimento pt-BR
    Azure-->>API: Texto ou erro
    API->>API: Métricas e regras textuais
    API->>DB: Resultado e eventos de revisão
    Script->>API: POST measurements com valores anômalos
    API->>DB: Medição, evento e alerta
    Script->>API: POST run-v2
    API->>DB: Consultar origens e persistir correlação
    API-->>Script: Correlações novas
    Script->>API: POST run-v2 novamente
    API-->>Script: Lista vazia para as mesmas origens
    Script->>API: GET events e alerts por paciente
    API-->>Script: Recursos persistidos
    Script-->>Operador: Resumo, IDs e PASS ou falha
    Operador->>UI: Selecionar o paciente gerado
    UI->>API: Consultar eventos, alertas e medições
    API-->>UI: Dados do paciente
    UI-->>Operador: KPIs, gráficos e rastreabilidade
```

O fluxo de sucesso depende do WAV, reconhecimento, limiares e proximidade temporal. Contagens históricas e condições de reprodução estão no [guia](DEMO_GUIDE.md).

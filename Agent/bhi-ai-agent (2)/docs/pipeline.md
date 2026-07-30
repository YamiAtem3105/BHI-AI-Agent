# BHI AI Agent - Pipeline Architecture

## 1. System Architecture

```mermaid
flowchart LR
    subgraph Frontend
        GC[Google Chat\n18 users BHI]
    end

    subgraph Backend["Python Backend (FastAPI + Cloud Run)"]
        WH[Webhook\n/api/google-chat]
        AUTH[Auth Service\nemail → user mapping]
        AGENT[Agent Service\nGemini 2.0 Flash\nFunction Calling]
        TOOLS[Tools Layer\n6 tools]
    end

    subgraph DB["PostgreSQL / SQLite"]
        USERS[(users\n18 records)]
        CONV[(conversations)]
        MSG[(messages)]
        TC[(tool_calls)]
        CACHE[(task_cache)]
        AUDIT[(audit_logs)]
    end

    subgraph Sheets["Google Sheets"]
        GAS[Apps Script\nWeb App API]
        KH[KẾ HOẠCH\n737 rows × 19 cols]
        AR[_ARCHIVE_LOG\n4016 rows × 11 cols]
        NS[Danh sách nhân sự\n18 người]
    end

    subgraph Admin["Admin Dashboard"]
        DASH[/admin/\nJWT Auth]
    end

    GC -->|chat message| WH
    WH --> AUTH
    AUTH -->|lookup| USERS
    AUTH --> AGENT
    AGENT -->|function calling| TOOLS
    TOOLS -->|HTTP GET/POST| GAS
    GAS -->|read/write| KH
    GAS -->|read| AR
    GAS -->|read| NS
    AGENT -->|save| CONV
    AGENT -->|save| MSG
    TOOLS -->|log| TC
    TOOLS -->|cache| CACHE
    TOOLS -->|audit| AUDIT
    AGENT -->|response| GC
    DASH -->|JWT protected| DB
```

## 2. Message Processing Flow

```mermaid
sequenceDiagram
    participant U as User (Google Chat)
    participant W as Webhook (FastAPI)
    participant A as Auth Service
    participant AG as Agent (Gemini 2.0 Flash)
    participant T as Tools Layer
    participant GAS as Apps Script
    participant DB as Database

    U->>W: Chat message
    W->>A: sender.email
    A->>DB: SELECT user WHERE email=?
    DB-->>A: User{name, role, department}

    alt User not found
        A-->>U: "⚠️ Chưa đăng ký. Liên hệ Admin."
    end

    A->>DB: Load conversation (last 10 msgs)
    A->>AG: message + history + system_prompt + tools_schema

    AG-->>T: function_call: search_tasks(...)

    Note over T: Permission filter applied
    Note over T: member → only own tasks

    T->>GAS: GET /exec?action=search&...
    GAS-->>T: {tasks: [...], count: N}
    T->>DB: Log tool_call

    T-->>AG: function_response: {tasks}
    AG-->>W: Natural language response

    W->>DB: Save messages (user + assistant)
    W-->>U: Response text
```

## 3. Write Operation (Confirmation Flow)

```mermaid
sequenceDiagram
    participant U as User
    participant AG as Agent
    participant DB as Database
    participant GAS as Apps Script

    U->>AG: "Tạo kế hoạch X gồm 3 task..."
    AG->>AG: Parse intent → create_wbs tool

    Note over AG: KHÔNG ghi ngay → Preview

    AG-->>U: "📋 Tôi sẽ tạo WBS:\n**X** (Level 1)\n├─ Task A | 3 ngày | Ngọc\n├─ Task B | 1 ngày | Vân\n└─ Task C | 5 ngày | Chiến\n\n✅ 'ok' | ❌ 'hủy'"

    AG->>DB: Save pending_action to conversation.context

    U->>AG: "ok"
    AG->>DB: Load pending_action

    AG->>GAS: POST /exec {action: "create", tasks: [...]}
    GAS-->>AG: {created: 3}

    AG->>DB: Log audit_log
    AG->>DB: Clear pending_action
    AG-->>U: "✅ Đã tạo hạng mục X với 3 task con"
```

## 4. Authentication & Authorization

```mermaid
flowchart TD
    EVENT[Google Chat Event] --> EXTRACT[Extract sender.email]
    EXTRACT --> LOOKUP{DB: users\nWHERE email=?}

    LOOKUP -->|Found| PERM{Check role}
    LOOKUP -->|Not Found| MATCH{Match by\ndisplay_name?}

    MATCH -->|Found| UPDATE[Update google_chat_id] --> PERM
    MATCH -->|Not Found| REJECT[❌ Chưa đăng ký]

    PERM -->|admin| ALL[No filter\nXem tất cả 737 rows]
    PERM -->|manager| DEPT[Filter: department]
    PERM -->|member| SELF[Filter: user = masterplan_name\nChỉ xem task mình]

    ALL --> QUERY[Apply to search_tasks params]
    DEPT --> QUERY
    SELF --> QUERY
```

## 5. Tools Available (6 tools)

```mermaid
flowchart TD
    subgraph READ["🔍 Read Tools"]
        T1[search_tasks\nFilter: user, status, date, keyword, zone\nReturn: 19 fields/task, max 50]
        T2[get_task_detail\nInput: task_id\nReturn: full 19 fields]
        T3[get_subtasks\nInput: parent_id\nReturn: all children]
        T4[search_archive\nFilter: user, project, date\nReturn: 11 fields/report, max 50]
    end

    subgraph WRITE["✏️ Write Tools (need confirmation)"]
        T5[create_wbs\nInput: parent_name + children\nFields: name, pic, support, reviewer,\nduration, predecessor, zone]
        T6[update_task\nInput: task_id + any fields\nUpdatable: status, note, pic, support,\nreviewer, duration, predecessor,\nstart_date, end_date, zone]
    end
```

## 6. Data Schema

```mermaid
erDiagram
    users {
        int id PK
        string google_chat_id UK
        string display_name
        string email UK
        string role "admin|manager|member"
        string department
        string masterplan_name
        string personal_sheet_id
        timestamp created_at
    }

    conversations {
        int id PK
        int user_id FK
        timestamp started_at
        timestamp last_message_at
        json context "pending_action stored here"
        boolean is_active
    }

    messages {
        int id PK
        int conversation_id FK
        string role "user|assistant"
        text content
        timestamp created_at
    }

    tool_calls {
        int id PK
        int conversation_id FK
        string tool_name
        json parameters
        json result
        string status "success|error"
        int duration_ms
        timestamp created_at
    }

    task_cache {
        int id PK
        string task_id
        string sheet_name
        json data
        timestamp cached_at
        timestamp expires_at
    }

    audit_logs {
        int id PK
        int user_id FK
        string action "read|create|update|delete"
        string target_task_id
        json payload
        timestamp timestamp
    }

    users ||--o{ conversations : has
    conversations ||--o{ messages : contains
    conversations ||--o{ tool_calls : triggers
    users ||--o{ audit_logs : generates
```

## 7. Admin Dashboard

```mermaid
flowchart TD
    ADMIN[/admin/] --> LOGIN[POST /admin/login\nusername + password]
    LOGIN --> JWT[JWT Token 24h]
    JWT --> TABS

    subgraph TABS["Protected APIs"]
        STATS[GET /admin/api/stats\nusers, conversations, messages count]
        USERS_API[GET /admin/api/users\nPUT /admin/api/users/:id\nDELETE /admin/api/users/:id]
        CONV_API[GET /admin/api/conversations\nGET /admin/api/conversations/:id/messages]
        AUDIT_API[GET /admin/api/audit-logs]
    end
```

## 8. Tech Stack

```mermaid
flowchart LR
    subgraph Runtime
        PY[Python 3.11+]
        FAST[FastAPI]
        GEMINI[google-genai\nGemini 2.0 Flash]
        HTTPX[httpx\nAsync HTTP]
        SA[SQLAlchemy 2.0]
        JWT_LIB[PyJWT]
    end

    subgraph Data
        SQLITE[SQLite\nlocal dev]
        PG[PostgreSQL\nproduction]
    end

    subgraph Google
        GCHAT[Google Chat\nWebhook]
        GAS_DEPLOY[Apps Script\nWeb App]
        GSHEETS[Google Sheets\nMasterplan QLXD]
    end

    subgraph Deploy
        DOCKER[Docker]
        CLOUD_RUN[Cloud Run]
    end
```

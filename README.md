# 🐉 PROJECT DRAGON - Ultimate Email AI Agent

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

**AI-Powered Email Management System that acts as your Executive Assistant, Chief of Staff, Inbox Manager, and Relationship Manager.**

[🚀 Quick Start](#-quick-start) • [📋 Features](#-features) • [🏗️ Architecture](#️-architecture) • [📦 Installation](#-installation) • [🎮 Usage](#-usage) • [🔌 API](#-api) • [🔒 Security](#-security)

</div>

---

## 🎯 Overview

Project Dragon is a production-grade Email AI Agent that transforms how you manage email. It combines advanced AI capabilities with enterprise-grade architecture to provide:

- **Executive Assistant** - Manages your inbox with intelligence
- **Chief of Staff** - Handles priority and follow-ups automatically
- **Inbox Manager** - Organizes, classifies, and prioritizes emails
- **Relationship Manager** - Tracks contacts and communication patterns
- **Voice Assistant** - Hands-free email management

---

## 🎤 Voice Commands

Dragon supports natural language voice commands:

```
"Hey Dragon, read my important emails"
"Hey Dragon, show my unread emails"  
"Hey Dragon, reply to Rahul"
"Hey Dragon, summarize my inbox"
"Hey Dragon, what's my inbox status?"
"Hey Dragon, search for internship emails"
```

### 🎤 Voice Features

| Feature | Description |
|---------|-------------|
| Wake Word Detection | Listen for "Hey Dragon" activation phrase |
| Speech Recognition | Convert spoken commands to text using Google Speech API |
| Text-to-Speech | Speak email summaries, alerts, and confirmations |
| Voice Navigation | Navigate inbox using voice commands |
| Voice Summaries | Get audio briefings of important emails |
| Voice Alerts | Emergency and escalation notifications via voice |

### 📝 Text Commands

Dragon also supports text-based commands for those who prefer typing:

```
@dragon read important emails
@dragon show unread
@dragon reply to rahul
@dragon summarize inbox
@dragon inbox status
@dragon search internship
@dragon draft professional response
@dragon create follow-up
```

### 📝 Text Format Commands (Detailed)

| Command | Description | Example |
|---------|-------------|---------|
| `@dragon read [filter]` | Read emails with optional filter | `@dragon read important emails` |
| `@dragon show [filter]` | Show emails matching filter | `@dragon show unread` |
| `@dragon reply to [contact]` | Start reply to contact | `@dragon reply to rahul` |
| `@dragon summarize` | Summarize inbox | `@dragon summarize inbox` |
| `@dragon status` | Show inbox status | `@dragon inbox status` |
| `@dragon search [query]` | Search emails | `@dragon search internship` |
| `@dragon draft [type]` | Create email draft | `@dragon draft professional response` |
| `@dragon follow-up` | Create follow-up reminder | `@dragon create follow-up` |
| `@dragon contacts` | List contacts | `@dragon contacts` |
| `@dragon analytics` | Show productivity stats | `@dragon analytics` |

---

## 📋 Features

### 📨 Email Intelligence

- [x] **Email Classification** - Automatic categorization into 11 categories
  - Emergency, Critical, Important, Work, Personal, Finance, College, Spam, Newsletter, Promotions, Normal
  
- [x] **Priority Scoring** - Every email gets a 0-100 importance score based on:
  - Sender importance
  - Keywords and deadlines
  - Attachments
  - Relationship history
  - Urgency indicators

- [x] **Priority Detection** - Automatic P0-P4 priority assignment
  - P0: Emergency (legal, security, financial emergencies)
  - P1: Critical (client, faculty, internship opportunities)
  - P2: Important (team discussions, project updates)
  - P3: Normal (routine emails)
  - P4: Low Priority

### ⚡ Automation

- [x] **Smart Pinning** - Automatically pin important emails
- [x] **Follow-up Detection** - Detect pending replies and create reminders
- [x] **Escalation System** - 5-level escalation for ignored emails
  - Level 1: Desktop notification
  - Level 2: Voice reminder
  - Level 3: Fullscreen alert
  - Level 4: Dragon voice announcement
  - Level 5: Trigger Calling Agent
- [x] **Rule Engine** - Customizable automation rules
- [x] **Email Drafting** - Professional, formal, and casual email templates

### 👥 Relationship Management

- [x] **Contact Memory** - Remembers communication history
- [x] **VIP Tracking** - Always prioritize VIP contacts
- [x] **Interaction History** - Track all communications
- [x] **Preference Storage** - Remember contact preferences

### 🔍 Semantic Search

- [x] **RAG System** - Retrieval Augmented Generation with ChromaDB
- [x] **Semantic Search** - Natural language email search
- [x] **Context Retrieval** - Historical memory access

### 📊 Analytics

- [x] **Daily Briefing** - Morning email summary
- [x] **Productivity Metrics** - Track inbox health
- [x] **Trend Analysis** - Email volume trends
- [x] **Contact Activity** - Monitor engagement

### 🗄️ Integrations

- [x] **Gmail API** - Full Gmail integration via OAuth2
- [x] **IMAP** - Support for any IMAP provider
- [x] **SMTP** - Send emails via SMTP
- [x] **Outlook** - Microsoft Graph API support (planned)
- [x] **Agent Integration** - Connect with Dragon Core agents

### 🔒 Security

- [x] **OAuth 2.0** - Secure authentication
- [x] **Encryption** - Fernet encryption for sensitive data
- [x] **Audit Logging** - Complete action audit trail
- [x] **Secure Tokens** - Encrypted token storage

---

## 🏗️ Architecture

```
dragon_email_agent/
├── core/                 # Core configuration and base classes
├── database/            # SQLite/PostgreSQL models and managers
├── email_engine/       # Email processing, classification, scoring
├── voice/              # Voice recognition, TTS, command parsing
├── memory/             # Contact and relationship memory
├── rag/                # RAG system with ChromaDB
├── security/           # Authentication and encryption
├── automation/         # Rules, escalations, scheduling
├── analytics/          # Metrics and reporting
├── integrations/       # Gmail, IMAP, SMTP, Outlook
├── api/               # FastAPI REST endpoints
├── utils/             # Utility functions
├── logs/              # Application logs
├── data/              # Database and attachments
├── main.py            # Main entry point
└── requirements.txt   # Dependencies
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DRAGON CORE                             │
│                     (Main Controller)                        │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Voice   │  │  Email   │  │  Memory  │  │   RAG    │    │
│  │  System  │  │  Engine  │  │  System  │  │  System  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │            │
│       └─────────────┴─────────────┴─────────────┘            │
│                         │                                      │
│       ┌─────────────────┴─────────────────┐                   │
│       ▼                                   ▼                   │
│  ┌──────────┐                    ┌──────────┐                │
│  │Analytics│                    │Automation│                │
│  └────┬─────┘                    └────┬─────┘                 │
│       │                             │                         │
│       └─────────────┬───────────────┘                         │
│                     ▼                                          │
│              ┌──────────┐                                     │
│              │Database  │◄──── Security                        │
│              │ (SQLite) │       Module                         │
│              └────┬─────┘                                     │
│                   │                                            │
│       ┌───────────┴───────────┐                               │
│       ▼                       ▼                               │
│  ┌──────────┐           ┌──────────┐                         │
│  │ Gmail API│           │  IMAP    │                         │
│  │ SMTP     │           │  Outlook │                         │
│  └──────────┘           └──────────┘                         │
│      Integrations                                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  FastAPI     │
                    │  REST API    │
                    └──────────────┘
```

---

## 📦 Installation

### Prerequisites

- Python 3.12+
- pip or uv package manager
- OpenSSL (for TLS)
- PortAudio (for voice features)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/your-repo/dragon-email-agent.git
cd dragon-email-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or use uv for faster installation
uv pip install -r requirements.txt
```

### Configuration

Create `config.yaml` in the project root:

```yaml
# Application Settings
app_name: Dragon Email Agent
app_version: 1.0.0
debug: false
log_level: INFO

# Database
db_path: data/dragon_email.db
use_sqlite: true

# LLM Settings
llm_provider: ollama
llm_model: llama3.2
llm_base_url: http://localhost:11434

# Voice Settings
voice_enabled: true
wake_word: hey dragon
voice_language: en-US

# Email Settings
default_account: gmail
sync_interval: 60  # seconds

# Escalation Levels
escalation_levels:
  1: {name: notification, delay_minutes: 0}
  2: {name: voice_reminder, delay_minutes: 15}
  3: {name: fullscreen_alert, delay_minutes: 30}
  4: {name: dragon_announce, delay_minutes: 60}
  5: {name: calling_agent, delay_minutes: 120}

# VIP Contacts
vip_contacts:
  - important@client.com
  - mentor@university.edu
```

### Gmail API Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the JSON credentials file
6. Set path in config:
   ```yaml
   gmail_credentials_path: path/to/credentials.json
   ```

---

## 🎮 Usage

### Start the Agent (Interactive Mode)

```bash
python main.py
```

### Start with Voice

```bash
python main.py --voice
```

### Start API Server Only

```bash
python main.py --api --port 8000
```

### Command-Line Interface

```
Dragon> help

╔══════════════════════════════════════════════════════════════════╗
║             DRAGON EMAIL AGENT - COMMAND REFERENCE             ║
╠══════════════════════════════════════════════════════════════════╣
║  help, h          - Show this help message                      ║
║  status           - Show system status                          ║
║  sync             - Sync emails from all accounts              ║
║  briefing         - Generate daily briefing                     ║
║  emails [filter]  - List emails (unread, important, urgent)     ║
║  contacts         - List contacts                                ║
║  search <query>   - Search emails and contacts                  ║
║  analytics        - Show productivity analytics                 ║
║  voice            - Toggle voice system                         ║
║  exit, quit       - Shut down the agent                         ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🔌 API

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication

Include API key in header:
```
Authorization: Bearer your-api-key
```

### Endpoints

#### Emails

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/emails` | List emails |
| GET | `/emails/{id}` | Get email by ID |
| POST | `/emails/send` | Send email |
| POST | `/emails/{id}/reply` | Reply to email |
| POST | `/emails/sync` | Trigger sync |

#### Contacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contacts` | List contacts |
| GET | `/contacts/{id}` | Get contact |
| POST | `/contacts/{id}/vip` | Set VIP status |

#### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/search` | Semantic search |
| GET | `/search/context` | Get search context |

#### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/briefing` | Daily briefing |
| GET | `/analytics/full` | Full report |
| GET | `/analytics/health` | Inbox health |

#### Voice

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/voice_command` | Process voice command |

### Example Requests

```bash
# Get unread emails
curl -X GET "http://localhost:8000/emails?unread_only=true&limit=10"

# Send email
curl -X POST "http://localhost:8000/emails/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Test Email",
    "body": "Hello from Dragon!"
  }'

# Search emails
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "internship opportunity",
    "limit": 10
  }'
```

---

## 🔒 Security

### Authentication

- OAuth 2.0 for Gmail/Outlook
- API key authentication for REST API
- Secure token storage with encryption

### Data Protection

- Fernet symmetric encryption for sensitive data
- Encrypted token storage
- Secure password handling with bcrypt

### Audit Trail

- Complete action logging
- Security event tracking
- Database audit logs

### Best Practices

- Never commit credentials to version control
- Use environment variables for secrets
- Enable audit logging in production
- Regular security audits

---

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_email_engine.py -v

# Run with coverage
pytest tests/ --cov=dragon_email_agent --cov-report=html
```

### Test Coverage

Current test coverage includes:
- Database operations
- Email classification
- Priority scoring
- API endpoints
- Security module

---

## 📊 Database Schema

### Core Tables

#### contacts
- id (PK)
- email (unique, indexed)
- name, display_name
- category, importance_level
- relationship_type
- is_vip, is_blocked
- first_contact_at, last_contact_at
- total_emails, unread_count
- preferences (JSON)
- metadata (JSON)

#### emails
- id (PK)
- message_id (unique)
- sender_email, recipient_email
- subject, body_plain, body_html
- category, priority (enum)
- importance_score (0-100)
- direction (incoming/outgoing/draft)
- is_read, is_starred, is_pinned
- has_attachments, attachment_count
- action_required, action_deadline
- is_replied, is_forwarded
- summary, keywords (JSON)
- embedding_id

#### threads
- id (PK)
- thread_id (unique)
- subject, participant_emails (JSON)
- message_count, last_message_date
- max_priority, max_importance_score
- action_required

#### escalations
- id (PK)
- email_id (FK)
- escalation_level (1-5)
- triggered_at, acknowledged_at, resolved_at
- notification_type

#### follow_ups
- id (PK)
- email_id, contact_id (FK)
- scheduled_date, reminder_date
- completed, reminder_sent
- status

#### rules
- id (PK)
- name, trigger_type
- trigger_conditions (JSON)
- actions (JSON)
- priority, is_enabled, is_system
- execution_count, last_executed_at

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | SQLite default |
| `LLM_PROVIDER` | LLM provider (ollama/deepseek/mistral) | ollama |
| `LLM_BASE_URL` | LLM API URL | localhost:11434 |
| `GMAIL_CREDENTIALS_PATH` | Path to Gmail credentials | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `DEBUG` | Enable debug mode | false |

### Config Options

```yaml
# Voice
voice_enabled: bool
wake_word: str
voice_language: str
tts_rate: float

# Email
sync_interval: int (seconds)
max_email_age_days: int
batch_size: int

# Escalation
response_thresholds:
  emergency: 0.5 (hours)
  client: 6
  faculty: 4
  work: 24
  personal: 48
  other: 72
```

---

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  dragon:
    build: docker dragon:dragon-email-agent .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dragon
```

### Systemd Service

```ini
[Unit]
 description=Dragon Email Agent
 After=network.target

[Service]
 Type=simple
 User=dragon
 WorkingDirectory=/opt/dragon
 ExecStart=/opt/dragon/venv/bin/python main.py
 Restart=on-failure
 RestartSec=10

[Install]
 WantedBy=multi-user.target
```

---

## 🤝 Integration with Dragon Core

Dragon Email Agent integrates with other Dragon agents through events:

```python
# Event types
events.emit("email_new", email=email)
events.emit("escalation_trigger", email=email, level=5)
events.emit("daily_briefing_requested")
events.emit("forward_to_agent", email=email, agent="ca")
events.emit("voice_alert", message="...", email=email)
```

---

## 📝 Logging

Logs are stored in:
- `logs/dragon.log` - General logs
- `logs/dragon_error.log` - Error logs
- `logs/audit.log` - Security audit logs

Log format:
```
2024-01-15 10:30:45 | INFO | module.function:line - Message
```

---

## 🔄 Changelog

### v1.0.0 (2024-01-15)
- Initial release
- Core email management
- Voice commands
- RAG search
- Automation rules
- Analytics dashboard
- Gmail/IMAP integration

---

## 🙏 Acknowledgments

- OpenAI for GPT models
- Hugging Face for sentence transformers
- ChromaDB team for vector storage
- Allen Institute for speech recognition
- FastAPI for the excellent REST framework

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤖 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<div align="center">

**Built with 🐉 and ❤️ for productivity**

</div>

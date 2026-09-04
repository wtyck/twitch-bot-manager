<p align="center">
  <img src="assets/hero.png" width="100%" alt="Twitch Bot Manager product overview">
</p>

<h1 align="center">Twitch Bot Manager</h1>

<p align="center">
  <a href="https://github.com/wtyck/twitch-bot-manager/actions/workflows/ci.yml"><img alt="Build Status" src="https://github.com/wtyck/twitch-bot-manager/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-6366f1">
  <a href="https://github.com/wtyck/twitch-bot-manager/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/wtyck/twitch-bot-manager?style=flat"></a>
</p>

<p align="center"><strong>Manage bot profiles, channels, runtime state, and shared settings from one API.</strong></p>

> **Open-source portfolio edition.** This clean-room implementation recreates the core idea of an earlier personal project. It runs in local demo mode and does not connect to Twitch or require Twitch credentials.

## ✨ Features

- Create, read, update, and delete bot profiles.
- Assign multiple Twitch-style channel names to each bot.
- Start and stop enabled bots in a deterministic demo runtime.
- Prevent duplicate bot usernames and duplicate channel assignments.
- Persist profiles, channels, and manager settings in SQLite.
- Configure command prefix, reconnect policy, response delay, and whispers.
- Validate all payloads with Pydantic.
- Run locally without OAuth tokens, external services, or network calls.
- Test API behavior against isolated temporary databases.

No production performance metrics are claimed for this portfolio edition.

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| API | Python 3.11+, FastAPI, Pydantic |
| Persistence | SQLite via `sqlite3` |
| Server | Uvicorn |
| Testing | pytest, HTTPX |
| Quality | Ruff, GitHub Actions |

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or newer
- `pip`

### Installation

```bash
git clone https://github.com/wtyck/twitch-bot-manager.git
cd twitch-bot-manager
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

### Usage

Check the service:

```bash
curl http://127.0.0.1:8000/api/health
```

Create a bot profile:

```bash
curl -X POST http://127.0.0.1:8000/api/bots \
  -H 'Content-Type: application/json' \
  -d '{"name":"Community Helper","username":"demo_helper","command_prefix":"!","enabled":true}'
```

Assign a channel and start the bot (replace `1` with the returned ID):

```bash
curl -X POST http://127.0.0.1:8000/api/channels \
  -H 'Content-Type: application/json' \
  -d '{"bot_id":1,"name":"demo_channel","enabled":true}'

curl -X POST http://127.0.0.1:8000/api/bots/1/start
```

Run checks:

```bash
ruff check .
pytest -q
```

## 📚 API Reference / Configuration

### API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Return service and demo-mode status. |
| `GET/POST` | `/api/bots` | List or create bot profiles. |
| `GET/PATCH/DELETE` | `/api/bots/{bot_id}` | Read, update, or delete one bot. |
| `POST` | `/api/bots/{bot_id}/start` | Set an enabled bot to `running`. |
| `POST` | `/api/bots/{bot_id}/stop` | Set a bot to `stopped`. |
| `GET/POST` | `/api/channels` | List or create channel assignments. |
| `GET/PATCH/DELETE` | `/api/channels/{channel_id}` | Manage one assignment. |
| `GET/PATCH` | `/api/config` | Read or update shared manager settings. |

### Environment variables

| Property | Type | Description | Default |
|---|---|---|---|
| `TBM_DATABASE_PATH` | string | SQLite database file path. | `data/twitch_bot_manager.db` |
| `TBM_MODE` | string | Runtime label returned by health checks. | `demo` |

### Manager configuration

| Property | Type | Description | Default |
|---|---|---|---|
| `default_prefix` | string | Default command prefix for new integrations. | `!` |
| `auto_reconnect` | boolean | Whether an adapter should reconnect after interruption. | `true` |
| `response_delay_ms` | integer | Delay budget for command responses. | `250` |
| `respond_to_whispers` | boolean | Whether private messages are eligible for responses. | `false` |

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/short-description`.
3. Add or update tests.
4. Run `ruff check . && pytest -q`.
5. Push your branch and open a focused pull request.

Keep demo mode credential-free and document any new configuration.

## 📄 License

Released under the [MIT License](LICENSE). Copyright © 2026 wtyck.

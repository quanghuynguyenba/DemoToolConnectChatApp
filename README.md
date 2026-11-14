# DemoToolConnectChatApp — Telegram Broadcast MVP

Phase 1 MVP: admin enters a notification in Streamlit and broadcasts it to every Telegram account stored in **Neon PostgreSQL**.

Telegram bot token and Neon credentials are **placeholders** — fill them in when ready.

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
# Edit .env: DATABASE_URL (Neon), TELEGRAM_BOT_TOKEN, DRY_RUN
```

### Neon PostgreSQL setup (CLI)

```bash
npm i -g neon@latest
neon init -y --org-id <org> --project-id <project> --branch production --services postgres
neon login          # if link was offline / needs auth
neon deploy         # applies neon.ts + pulls DATABASE_URL into .env
npm run build       # verifies Neon env wiring
python -m scripts.init_schema
```

Or paste a Neon URI into `.env` manually, then run `python -m scripts.init_schema`.

```bash
streamlit run app/main.py
```

Optional bot listener (employee auth on `/start`):

```bash
python -m app.telegram.bot_listener
```

Auth flow: `/start` → share Telegram contact → employee phone lookup → **email OTP** → type OTP in Telegram chat → Active link. Broadcasts only go to Active authenticated links.

In Streamlit, add employees first (phone E.164 + company email). Configure `SMTP_*` so OTP can be emailed.

## Environment variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `DATABASE_URL` | Neon URI, e.g. `postgresql://…@ep-….neon.tech/neondb?sslmode=require` |
| `DRY_RUN` | `true` (default) = log recipients without calling Telegram |
| `OTP_PEPPER` | HMAC pepper for OTP hashes |
| `SMTP_HOST` / `SMTP_FROM` / `SMTP_USER` / `SMTP_PASSWORD` | Required to email OTP |

## Docs

- [Codebase structure](docs/STRUCTURE.md)
- [Project phases](docs/PHASES.md)
- [Employee authentication design](docs/update_authen_v1.0.md)

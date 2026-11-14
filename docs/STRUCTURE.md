# Codebase structure

```
DemoToolConnectChatApp/
├── README.md                 # Quick start and env overview
├── requirements.txt          # Python dependencies
├── package.json              # Neon CLI deps + `npm run build` verify
├── neon.ts                   # Neon IaC (Postgres on production branch)
├── .neon                     # Linked org/project/branch
├── .env.example              # Placeholder config (copy to .env)
├── .gitignore
├── docs/
│   ├── STRUCTURE.md          # This file
│   └── PHASES.md             # Phase 1–4 roadmap
├── sql/
│   └── schema.sql            # Neon PostgreSQL tables for Phase 1
├── scripts/
│   └── init_schema.py        # Apply schema.sql via DATABASE_URL (Neon)
└── app/
    ├── __init__.py
    ├── config.py             # Load TELEGRAM_BOT_TOKEN, DATABASE_URL, DRY_RUN
    ├── main.py               # Streamlit admin UI entrypoint
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py     # Neon/psycopg2 connect (sslmode=require) + health check
    │   └── repository.py     # telegram_users + notifications CRUD
    ├── telegram/
    │   ├── __init__.py
    │   ├── client.py         # Bot API: sendMessage, getUpdates, broadcast
    │   └── bot_listener.py   # Optional long-poll: /start → register user
    └── services/
        ├── __init__.py
        └── broadcast.py      # Orchestrate list users → send → log result
```

## Module responsibilities

| Module | Role |
|--------|------|
| `app/config.py` | Single place for env settings |
| `app/db/connection.py` | Connect to Neon PostgreSQL (TLS); clear errors if URL missing/placeholder |
| `scripts/init_schema.py` | Apply `sql/schema.sql` to the Neon database |
| `app/db/repository.py` | Persist connected chats and notification history |
| `app/telegram/client.py` | HTTP calls to Telegram Bot API |
| `app/telegram/bot_listener.py` | Background process to auto-register users |
| `app/services/broadcast.py` | Business logic for admin broadcast (incl. dry-run) |
| `app/main.py` | Admin UI: compose message, manage users, view history |

## Data model (Phase 1)

**telegram_users** — one row per connected Telegram chat (`chat_id` unique).

**notifications** — one row per admin send attempt (`sent` / `dry_run` / `failed` / `partial`).

See [`sql/schema.sql`](../sql/schema.sql).

## How to run

From the project root (so `app` is importable):

```bash
streamlit run app/main.py
python -m app.telegram.bot_listener
```

## Extension points (later phases)

- Swap or extend `services/` for AI filtering and scheduled digests.
- Add Discord ingest workers beside `telegram/`.
- Keep Streamlit as admin surface or split API + UI in Phase 4 packaging.

---

# Update: Employee Authentication v1.0

**Update name:** `update_authen_v1.0`  
**Update datetime:** 2026-11-14 16:05 (UTC+7)

## Structure after auth update

```
DemoToolConnectChatApp/
├── README.md
├── requirements.txt          # + phonenumbers
├── package.json
├── neon.ts
├── .neon
├── .env.example              # + AUTH_DEV_MODE, OTP_*, SMTP_*, PHONE_DEFAULT_REGION
├── .gitignore
├── docs/
│   ├── STRUCTURE.md
│   ├── PHASES.md
│   └── update_authen_v1.0.md # Auth / security design source
├── sql/
│   └── schema.sql            # + employees, telegram_accounts,
│                             #   employee_telegram_links,
│                             #   authentication_sessions,
│                             #   authentication_logs
├── scripts/
│   └── init_schema.py
└── app/
    ├── __init__.py
    ├── config.py             # + OTP / SMTP / AUTH_DEV_MODE settings
    ├── main.py               # Admin: broadcast, employees, links, revoke, audit
    ├── auth/
    │   ├── __init__.py
    │   ├── phone.py          # E.164 normalize + email mask
    │   ├── otp.py            # CSPRNG OTP + HMAC hash/verify
    │   └── messages.py       # Vietnamese bot copy
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py
    │   ├── repository.py     # Legacy telegram_users + notifications
    │   └── auth_repository.py# Employees, accounts, links, sessions, logs
    ├── telegram/
    │   ├── __init__.py
    │   ├── client.py         # + request_contact keyboard helpers
    │   └── bot_listener.py   # Auth flow: /start → contact → OTP → link
    └── services/
        ├── __init__.py
        ├── audit.py          # AuthenticationLog writer
        ├── authentication.py # Contact verify, employee lookup, OTP, linking
        └── broadcast.py      # Sends only to Active employee–Telegram links
```

## Auth module responsibilities

| Module | Role |
|--------|------|
| `app/auth/phone.py` | Normalize phone to E.164 (`phonenumbers`) |
| `app/auth/otp.py` | Generate/hash/verify OTP (no plaintext storage) |
| `app/auth/messages.py` | User-facing Telegram auth messages |
| `app/services/authentication.py` | Orchestrate contact → employee → OTP → link |
| `app/services/audit.py` | Write security audit events |
| `app/db/auth_repository.py` | Persist employees, links, sessions, logs |
| `app/telegram/bot_listener.py` | Long-poll updates through auth service |
| `app/services/broadcast.py` | Notification access control (Active only) |

## Data model additions

**employees** — HR roster (`employee_code` unique, normalized `phone_number`, company `email`, `active`/`inactive`).

**telegram_accounts** — Telegram identity (`telegram_user_id` unique).

**employee_telegram_links** — Link status (`pending`/`verified`/`active`/`rejected`/`suspended`/`revoked`); unique filtered indexes for one Active link per employee and per Telegram account.

**authentication_sessions** — OTP session with `otp_hash`, attempts, expiry.

**authentication_logs** — Audit trail (no OTP/token plaintext).

Legacy **telegram_users** remains for Phase 1 compatibility and is synced when a link becomes Active.

## How to run (auth)

```bash
python -m scripts.init_schema
streamlit run app/main.py
python -m app.telegram.bot_listener
```

1. Add employees in Streamlit (phone + company email).  
2. User sends `/start` → shares contact → enters OTP.  
3. Broadcast reaches only Active authenticated links.

---

# Update: Email OTP authentication flow

**Update name:** `email_otp_flow`  
**Update datetime:** 2026-11-14 16:25 (UTC+7)

## Change summary

OTP is no longer shown in Telegram. After employee phone match:

1. Backend emails OTP via SMTP (`app/services/email_otp.py`)
2. Bot tells user to open email and copy the 6-digit code
3. User types OTP in the Telegram chat to complete linking

Added module: `app/services/email_otp.py`  
Required env: `SMTP_HOST`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD` (typical Gmail App Password setup)

---

# Update: Gmail SMTP OTP verified

**Update name:** `gmail_smtp_otp_v1.1`  
**Update datetime:** 2026-11-14 16:35 (UTC+7)

- Verified OTP send via `smtp.gmail.com:587` + App Password.
- Auth design doc updated: `docs/update_authen_v1.0.md` → v1.1 Implemented (section 4.6 + 23).
- Runtime flow: contact → employee active → Gmail email OTP → type OTP in Telegram chat.

-- Phase 1 schema: connected Telegram users + notification send log
-- Auth v1.0: employees, telegram accounts, links, sessions, audit logs

CREATE TABLE IF NOT EXISTS telegram_users (
    id              SERIAL PRIMARY KEY,
    chat_id         BIGINT NOT NULL UNIQUE,
    username        TEXT,
    display_name    TEXT,
    connected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_telegram_users_active
    ON telegram_users (is_active)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS notifications (
    id                SERIAL PRIMARY KEY,
    content           TEXT NOT NULL,
    sent_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recipient_count   INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL CHECK (status IN ('sent', 'dry_run', 'failed', 'partial')),
    error_detail      TEXT
);

-- ---------------------------------------------------------------------------
-- Employee Authentication & Security (update_authen_v1.0)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_code   VARCHAR(64) NOT NULL UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    phone_number    VARCHAR(32) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    department      VARCHAR(128),
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_employees_phone
    ON employees (phone_number);

CREATE INDEX IF NOT EXISTS idx_employees_status
    ON employees (status);

CREATE TABLE IF NOT EXISTS telegram_accounts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id    BIGINT NOT NULL UNIQUE,
    telegram_chat_id    BIGINT NOT NULL,
    telegram_username   VARCHAR(255),
    phone_number        VARCHAR(32),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telegram_accounts_chat
    ON telegram_accounts (telegram_chat_id);

CREATE TABLE IF NOT EXISTS employee_telegram_links (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id             UUID NOT NULL REFERENCES employees(id),
    telegram_account_id     UUID NOT NULL REFERENCES telegram_accounts(id),
    status                  TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN (
                                    'pending', 'verified', 'active',
                                    'rejected', 'suspended', 'revoked'
                                )),
    verified_at             TIMESTAMPTZ,
    linked_at               TIMESTAMPTZ,
    revoked_at              TIMESTAMPTZ,
    revoked_reason          VARCHAR(512),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_links_employee
    ON employee_telegram_links (employee_id);

CREATE INDEX IF NOT EXISTS idx_links_telegram_account
    ON employee_telegram_links (telegram_account_id);

CREATE INDEX IF NOT EXISTS idx_links_status
    ON employee_telegram_links (status);

-- At most one Active link per employee / telegram account
CREATE UNIQUE INDEX IF NOT EXISTS uq_links_employee_active
    ON employee_telegram_links (employee_id)
    WHERE status = 'active';

CREATE UNIQUE INDEX IF NOT EXISTS uq_links_telegram_active
    ON employee_telegram_links (telegram_account_id)
    WHERE status = 'active';

CREATE TABLE IF NOT EXISTS authentication_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id    BIGINT NOT NULL,
    telegram_chat_id    BIGINT NOT NULL,
    employee_id         UUID REFERENCES employees(id),
    phone_number        VARCHAR(32),
    otp_hash            VARCHAR(128),
    status              TEXT NOT NULL DEFAULT 'pending_otp'
                            CHECK (status IN (
                                'pending_otp', 'verified', 'expired',
                                'locked', 'completed', 'rejected'
                            )),
    expires_at          TIMESTAMPTZ NOT NULL,
    attempts            INTEGER NOT NULL DEFAULT 0,
    resend_count        INTEGER NOT NULL DEFAULT 0,
    last_otp_sent_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_telegram
    ON authentication_sessions (telegram_user_id, status);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires
    ON authentication_sessions (expires_at);

CREATE TABLE IF NOT EXISTS authentication_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id    BIGINT,
    employee_id         UUID REFERENCES employees(id),
    action              VARCHAR(64) NOT NULL,
    result              VARCHAR(32) NOT NULL,
    reason              VARCHAR(512),
    actor               VARCHAR(128),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_logs_created
    ON authentication_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_logs_telegram
    ON authentication_logs (telegram_user_id);

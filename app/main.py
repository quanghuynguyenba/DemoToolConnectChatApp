"""Streamlit admin UI for Telegram broadcast + employee authentication."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

# Allow `streamlit run app/main.py` from project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from app.auth.phone import PhoneNormalizationError, normalize_phone
from app.config import get_settings
from app.db.auth_repository import (
    AuthLogRepository,
    AuthorizationRepository,
    EmployeeRepository,
    LinkRepository,
)
from app.db.connection import DatabaseError, check_connection
from app.db.repository import NotificationRepository
from app.services.authentication import AuthenticationService
from app.services.broadcast import broadcast_notification

st.set_page_config(
    page_title="Telegram Broadcast Admin",
    page_icon="📨",
    layout="centered",
)


def _status_badge(ok: bool, label: str) -> None:
    icon = "OK" if ok else "—"
    color = "green" if ok else "orange"
    st.markdown(f":{color}[{icon}] {label}")


def render_sidebar() -> None:
    settings = get_settings()
    st.sidebar.header("System status")

    db_ok, db_msg = check_connection()
    _status_badge(db_ok, "Neon PostgreSQL")
    st.sidebar.caption(db_msg)
    if settings.neon_branch:
        st.sidebar.caption(f"Branch: `{settings.neon_branch}`")

    token_ok = settings.has_telegram_token
    _status_badge(token_ok, "Telegram token")
    if not token_ok:
        st.sidebar.caption("Set TELEGRAM_BOT_TOKEN in .env when ready.")

    _status_badge(settings.dry_run, f"DRY_RUN={'true' if settings.dry_run else 'false'}")
    if settings.dry_run:
        st.sidebar.caption("Messages are not sent to Telegram while DRY_RUN is true.")

    _status_badge(settings.has_smtp, "SMTP (email OTP)")
    if not settings.has_smtp:
        st.sidebar.caption(
            "Set SMTP_HOST / SMTP_FROM / SMTP_USER / SMTP_PASSWORD in .env "
            "so OTP can be emailed after phone match."
        )
    else:
        st.sidebar.caption(f"SMTP host: `{settings.smtp_host}`")

    if db_ok:
        try:
            count = len(AuthorizationRepository().list_active_recipients())
            st.sidebar.metric("Authorized recipients", count)
        except DatabaseError as exc:
            st.sidebar.warning(str(exc))
    else:
        st.sidebar.info(
            "Run `neon login` then `neon deploy`, or set DATABASE_URL in `.env`. "
            "Then apply schema: `python -m scripts.init_schema`."
        )


def render_broadcast_form(db_ok: bool) -> None:
    st.header("Send notification")
    st.write(
        "Broadcasts only to **Active** employee–Telegram links "
        "(contact verified + OTP completed)."
    )

    with st.form("broadcast_form"):
        content = st.text_area(
            "Notification content",
            height=160,
            placeholder="Type the announcement to send…",
        )
        submitted = st.form_submit_button("Send", type="primary", disabled=not db_ok)

    if not db_ok:
        st.warning("Database is not connected. Fix DATABASE_URL before sending.")
        return

    if submitted:
        with st.spinner("Sending…"):
            result = broadcast_notification(content)

        if result.status == "dry_run":
            st.info(
                f"Dry-run complete for **{result.recipient_count}** recipient(s). "
                f"({result.error_detail})"
            )
        elif result.status == "sent":
            st.success(
                f"Sent to **{result.success_count}/{result.recipient_count}** recipient(s)."
            )
        elif result.status == "partial":
            st.warning(
                f"Partial send: **{result.success_count}** ok, "
                f"**{result.failure_count}** failed."
            )
            if result.error_detail:
                st.code(result.error_detail)
        else:
            st.error(result.error_detail or "Send failed.")

        if result.results:
            st.subheader("Per-recipient result")
            st.dataframe(
                [
                    {
                        "chat_id": r.chat_id,
                        "ok": r.ok,
                        "detail": r.detail,
                    }
                    for r in result.results
                ],
                use_container_width=True,
            )


def render_employees_section(db_ok: bool) -> None:
    st.header("Employees")
    st.caption("HR roster used for phone lookup during Telegram authentication.")

    if not db_ok:
        st.caption("Connect PostgreSQL to manage employees.")
        return

    settings = get_settings()
    with st.form("add_employee_form"):
        st.subheader("Add / update employee")
        c1, c2 = st.columns(2)
        with c1:
            code = st.text_input("Employee code", placeholder="NV001")
            full_name = st.text_input("Full name")
            phone = st.text_input("Phone", placeholder="0912345678 or +84912345678")
        with c2:
            email = st.text_input("Company email", placeholder="name@company.com")
            department = st.text_input("Department (optional)")
            status = st.selectbox("Status", ["active", "inactive"])
        submitted = st.form_submit_button("Save employee")

    if submitted:
        if not code.strip() or not full_name.strip() or not phone.strip() or not email.strip():
            st.error("Employee code, full name, phone, and email are required.")
        else:
            try:
                normalized = normalize_phone(phone, settings.phone_default_region)
                emp = EmployeeRepository().upsert(
                    employee_code=code.strip(),
                    full_name=full_name.strip(),
                    phone_number=normalized,
                    email=email.strip().lower(),
                    department=department.strip() or None,
                    status=status,
                )
                st.success(
                    f"Saved {emp.employee_code} · {emp.full_name} · {emp.phone_number}"
                )
            except PhoneNormalizationError as exc:
                st.error(str(exc))
            except DatabaseError as exc:
                st.error(str(exc))

    try:
        employees = EmployeeRepository().list_all()
    except DatabaseError as exc:
        st.error(str(exc))
        return

    if not employees:
        st.info("No employees yet. Add roster rows above before users can authenticate.")
        return

    st.dataframe(
        [
            {
                "code": e.employee_code,
                "name": e.full_name,
                "phone": e.phone_number,
                "email": e.email,
                "department": e.department or "",
                "status": e.status,
                "id": str(e.id),
            }
            for e in employees
        ],
        use_container_width=True,
    )


def render_links_section(db_ok: bool) -> None:
    st.header("Telegram links")
    if not db_ok:
        return

    try:
        rows = LinkRepository().list_all_with_details()
        recipients = AuthorizationRepository().list_active_recipients()
    except DatabaseError as exc:
        st.error(str(exc))
        return

    st.subheader("Authorized recipients (will receive broadcasts)")
    if not recipients:
        st.info(
            "No Active links. Run `python -m app.telegram.bot_listener` and complete "
            "/start → share contact → OTP."
        )
    else:
        st.dataframe(
            [
                {
                    "employee": r.employee_code,
                    "name": r.full_name,
                    "department": r.department or "",
                    "chat_id": r.chat_id,
                    "telegram_user_id": r.telegram_user_id,
                    "username": r.username or "",
                }
                for r in recipients
            ],
            use_container_width=True,
        )

    st.subheader("All links")
    if not rows:
        st.caption("No link history yet.")
    else:
        st.dataframe(
            [
                {
                    "status": r["status"],
                    "employee": r["employee_code"],
                    "name": r["full_name"],
                    "employee_status": r["employee_status"],
                    "telegram_user_id": r["telegram_user_id"],
                    "chat_id": r["telegram_chat_id"],
                    "username": r["telegram_username"] or "",
                    "linked_at": str(r["linked_at"] or ""),
                    "revoked_at": str(r["revoked_at"] or ""),
                    "reason": r["revoked_reason"] or "",
                    "link_id": str(r["link_id"]),
                }
                for r in rows
            ],
            use_container_width=True,
        )

    st.subheader("Revoke Active link")
    with st.form("revoke_form"):
        link_id_raw = st.text_input("link_id (UUID)")
        reason = st.text_input("Reason", value="Admin revoked")
        revoke_submitted = st.form_submit_button("Revoke")

    if revoke_submitted:
        try:
            link_id = UUID(link_id_raw.strip())
        except ValueError:
            st.error("link_id must be a valid UUID.")
            return

        match = next((r for r in rows if str(r["link_id"]) == str(link_id)), None)
        if match is None:
            st.warning("Link not found.")
            return
        if match["status"] != "active":
            st.warning("Only Active links can be revoked.")
            return

        count = AuthenticationService().revoke_link_by_id(
            link_id=link_id,
            reason=reason.strip() or "Admin revoked",
            actor="admin_ui",
            telegram_user_id=match["telegram_user_id"],
            chat_id=match["telegram_chat_id"],
        )
        if count:
            st.success("Link revoked.")
            st.rerun()
        else:
            st.warning("Nothing revoked.")


def render_auth_logs(db_ok: bool) -> None:
    st.header("Authentication audit log")
    if not db_ok:
        return
    try:
        logs = AuthLogRepository().list_recent(40)
    except DatabaseError as exc:
        st.error(str(exc))
        return
    if not logs:
        st.caption("No auth events yet.")
        return
    st.dataframe(
        [
            {
                "at": str(r.created_at),
                "action": r.action,
                "result": r.result,
                "telegram_user_id": r.telegram_user_id or "",
                "employee_id": str(r.employee_id) if r.employee_id else "",
                "reason": r.reason or "",
                "actor": r.actor or "",
            }
            for r in logs
        ],
        use_container_width=True,
    )


def render_history(db_ok: bool) -> None:
    st.header("Recent notifications")
    if not db_ok:
        return
    try:
        rows = NotificationRepository().list_recent(15)
    except DatabaseError as exc:
        st.error(str(exc))
        return
    if not rows:
        st.caption("No notifications logged yet.")
        return
    st.dataframe(
        [
            {
                "id": r.id,
                "sent_at": str(r.sent_at),
                "status": r.status,
                "recipients": r.recipient_count,
                "content": r.content[:80] + ("…" if len(r.content) > 80 else ""),
                "error": r.error_detail or "",
            }
            for r in rows
        ],
        use_container_width=True,
    )


def main() -> None:
    st.title("Telegram Broadcast Admin")
    st.caption("Employee authentication required before notifications")

    render_sidebar()
    db_ok, _ = check_connection()

    render_broadcast_form(db_ok)
    st.divider()
    render_employees_section(db_ok)
    st.divider()
    render_links_section(db_ok)
    st.divider()
    render_auth_logs(db_ok)
    st.divider()
    render_history(db_ok)


if __name__ == "__main__":
    main()

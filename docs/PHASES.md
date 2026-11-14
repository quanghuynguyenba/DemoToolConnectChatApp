# Project phases

## Bài toán tổng quan

- **MVP:** Ứng dụng Python có UI để admin nhập nội dung thông báo; khi bấm gửi, tin được đẩy tới các tài khoản Telegram đang kết nối.
- **Final:** Bổ sung thuật toán sàng lọc dữ liệu, trả về các thông báo quan trọng trong ngày cho người dùng Telegram.

Công nghệ mục tiêu: **Python**, **Neon PostgreSQL**, **Streamlit**.

---

## Phase 1 — MVP broadcast (hiện tại)

**Mục tiêu:** Chưa có pipeline data/AI. Chỉ tính năng tối thiểu: admin nhập tin → gửi cho toàn bộ Telegram đã kết nối.

**Đã có trong codebase:**

- Streamlit admin UI (`app/main.py`)
- Neon PostgreSQL schema + repository lưu `telegram_users` / `notifications`
- Telegram Bot API client + broadcast service (hỗ trợ `DRY_RUN`)
- Form thêm `chat_id` thủ công; optional `bot_listener` đăng ký qua `/start`
- Credential để placeholder (`.env.example`)

**Chưa làm:** AI, mock digest, Discord, packaging.

---

## Phase 2 — Mở rộng MVP + mock data + AI gửi tự động

**Mục tiêu:**

- Bổ sung mock data (tin / sự kiện giả lập trong ngày)
- Tích hợp AI tạo hoặc chọn nội dung thông báo từ data
- Tự động gửi (theo lịch hoặc trigger) tới các tài khoản Telegram đã kết nối

**Hướng mở rộng dự kiến:** module `app/services/ai_notify.py`, job scheduler, bảng/mock nguồn tin.

---

## Phase 3 — Discord + học theo user + sàng lọc trong ngày

**Mục tiêu:**

- Kết nối Discord, nạp tin nhắn vào PostgreSQL
- AI tự học / cá nhân hóa từ dữ liệu gắn với từng tài khoản Telegram
- Giải thuật sàng lọc → list thông báo quan trọng nhất trong ngày cho từng user

**Hướng mở rộng dự kiến:** Discord bot/ingest, bảng `discord_messages`, ranking/filter pipeline, digest gửi Telegram.

---

## Phase 4 — Đóng gói và build sản phẩm

**Mục tiêu:**

- Đóng gói chạy ổn định (Docker / script deploy / binary tùy yêu cầu)
- Cấu hình môi trường production, tài liệu vận hành
- Kiểm thử end-to-end và checklist release

---

## Mapping phase → thư mục hiện tại

| Phase | Tập trung chính |
|-------|-----------------|
| 1 | `app/main.py`, `app/telegram/`, `app/db/`, `app/services/broadcast.py` |
| 2 | Thêm `services` AI + mock data (chưa có) |
| 3 | Discord ingest + schema mở rộng + filter (chưa có) |
| 4 | Docker/build scripts (chưa có) |

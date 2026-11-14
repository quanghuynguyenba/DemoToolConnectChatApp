"""User-facing Telegram auth messages (Vietnamese, per update_authen_v1.0)."""

from __future__ import annotations

WELCOME_START = (
    "Xin chào!\n\n"
    "Để sử dụng hệ thống thông báo nội bộ,\n"
    "bạn cần xác thực danh tính nhân viên.\n\n"
    "👉 Nhấn nút « Chia sẻ số điện thoại » "
    "ở thanh bàn phím bên dưới.\n\n"
    "Nếu không thấy nút: trên Telegram Desktop/Web, "
    "bấm biểu tượng bàn phím cạnh ô nhập tin nhắn "
    "để mở custom keyboard.\n\n"
    "Không nhập số điện thoại bằng chữ."
)

ALREADY_LINKED = (
    "Tài khoản Telegram của bạn đã được liên kết và đang hoạt động.\n"
    "Bạn có thể nhận thông báo nội bộ."
)

PRIVATE_CHAT_REQUIRED = (
    "Vui lòng mở chat riêng với bot để xác thực.\n"
    "Không hỗ trợ xác thực trong nhóm."
)

CONTACT_REQUIRED = (
    "Vui lòng nhấn nút « Chia sẻ số điện thoại » bên dưới.\n"
    "Không chấp nhận số điện thoại nhập bằng chữ."
)

CONTACT_NOT_OWNED = (
    "Không thể xác thực thông tin.\n\n"
    "Vui lòng kiểm tra lại hoặc liên hệ\n"
    "bộ phận quản trị hệ thống."
)

GENERIC_AUTH_FAILED = (
    "Không thể xác thực thông tin.\n\n"
    "Vui lòng kiểm tra lại hoặc liên hệ\n"
    "bộ phận quản trị hệ thống."
)

DUPLICATE_PHONE = (
    "Không thể xác thực tự động.\n"
    "Vui lòng liên hệ bộ phận quản trị hệ thống để được hỗ trợ."
)

OTP_PROMPT = (
    "Đã tìm thấy hồ sơ nhân viên của bạn.\n\n"
    "Chúng tôi đã gửi mã OTP (6 chữ số) đến email:\n"
    "{masked_email}\n\n"
    "Cách hoàn tất xác thực:\n"
    "1) Mở hộp thư email (kiểm tra cả Spam/Junk)\n"
    "2) Sao chép mã OTP trong email\n"
    "3) Quay lại chat này và nhập đúng 6 chữ số\n\n"
    "Mã có hiệu lực trong vài phút."
)

OTP_SEND_FAILED = (
    "Hệ thống chưa gửi được email OTP.\n"
    "Vui lòng liên hệ quản trị để kiểm tra cấu hình SMTP,\n"
    "rồi gửi /start lại."
)

OTP_INVALID = (
    "Mã OTP không đúng. Vui lòng nhập lại 6 chữ số từ email."
)

OTP_EXPIRED = (
    "Mã OTP đã hết hạn hoặc chưa có phiên xác thực.\n"
    "Gửi /start để nhận mã mới qua email."
)

OTP_LOCKED = (
    "Bạn đã nhập sai quá nhiều lần.\n"
    "Phiên xác thực tạm khóa. Gửi /start sau vài phút."
)

AUTH_SUCCESS = (
    "Xác thực thành công!\n\n"
    "Tài khoản Telegram đã được liên kết\n"
    "với hồ sơ nhân viên của bạn.\n\n"
    "Bạn đã có thể nhận thông báo nội bộ."
)

EMPLOYEE_ALREADY_LINKED = (
    "Hồ sơ nhân viên này đã liên kết với một tài khoản Telegram khác.\n"
    "Vui lòng liên hệ quản trị để đổi tài khoản."
)

TELEGRAM_ALREADY_LINKED = (
    "Tài khoản Telegram này đã liên kết với nhân viên khác."
)

SHARE_PHONE_BUTTON = "Chia sẻ số điện thoại"


# Telegram Bot Employee Authentication & Security

**Phiên bản:** 1.1  
**Trạng thái:** Implemented (DemoToolConnectChatApp)  
**Loại tài liệu:** Technical Design / Security Proposal + Implementation Notes  
**Phạm vi:** Xác thực nhân viên và bảo mật kết nối Telegram Bot trong doanh nghiệp.  
**Cập nhật:** 2026-11-14 — chọn **Email OTP qua Gmail SMTP**; người dùng nhập lại OTP trong chat Telegram.

---

# 1. Tổng quan dự án

## 1.1. Bối cảnh

Doanh nghiệp đang phát triển hệ thống gửi thông báo nội bộ thông qua Telegram Bot.

Hiện tại, người dùng chỉ cần:
1. Tìm kiếm đúng tên Telegram Bot.
2. Nhấn `/start`.
3. Bot ghi nhận tài khoản Telegram và bắt đầu kết nối với hệ thống.

Quy trình hiện tại chưa có cơ chế xác minh người dùng có thực sự là nhân viên của doanh nghiệp hay không.

Điều này tạo ra nguy cơ người ngoài doanh nghiệp có thể tự ý kết nối với Bot và có khả năng tiếp nhận các thông báo nội bộ.

## 1.2. Mục tiêu

Xây dựng cơ chế xác thực và quản lý danh tính người dùng trước khi cho phép tài khoản Telegram kết nối với hệ thống.

Các mục tiêu chính:

- Chỉ cho phép nhân viên hợp lệ kết nối Telegram Bot.
- Xác minh tài khoản Telegram đang tương tác.
- Đối chiếu thông tin với dữ liệu nhân sự của doanh nghiệp.
- Xác thực danh tính thông qua một kênh do doanh nghiệp kiểm soát.
- Liên kết duy nhất hoặc có kiểm soát giữa Employee ID và Telegram User ID.
- Ngăn chặn tài khoản không hợp lệ nhận thông báo.
- Thu hồi quyền khi nhân viên nghỉ việc hoặc không còn đủ điều kiện.
- Lưu lịch sử xác thực và các hoạt động bảo mật.

## 1.3. Phạm vi

Tài liệu tập trung vào:

1. Employee Authentication.
2. Telegram Contact Verification.
3. Employee Verification.
4. Telegram Account Linking.
5. Authorization.
6. Account Revocation.
7. Security Logging.
8. Notification Access Control.

Không bao gồm thiết kế nghiệp vụ nội dung thông báo hoặc giao diện quản trị toàn bộ hệ thống.

---

# 2. Phân tích hiện trạng và rủi ro

## 2.1. Hiện trạng

Quy trình hiện tại:

```text
User
 |
 v
Search Telegram Bot
 |
 v
Send /start
 |
 v
Backend receives Telegram Update
 |
 v
Save Telegram User Information
 |
 v
Connection Successful
 |
 v
Receive Notifications
```

Hạn chế:

- Không xác minh người dùng có thuộc doanh nghiệp hay không.
- Không có dữ liệu đối chiếu với danh sách nhân sự.
- Không có cơ chế xác thực danh tính độc lập.
- Không kiểm soát việc một nhân viên kết nối nhiều tài khoản.
- Không có quy trình thu hồi quyền truy cập.
- Không có nhật ký đầy đủ về hoạt động xác thực.

## 2.2. Security Risks

| ID | Rủi ro | Mức độ |
|---|---|---|
| R01 | Người ngoài tự kết nối Bot | Critical |
| R02 | Giả mạo số điện thoại | High |
| R03 | Liên kết Telegram với sai nhân viên | High |
| R04 | Một nhân viên liên kết nhiều tài khoản trái phép | Medium |
| R05 | Nhân viên nghỉ việc vẫn nhận thông báo | High |
| R06 | Brute force OTP | High |
| R07 | Chiếm quyền tài khoản Telegram | High |
| R08 | Lộ Bot Token | Critical |
| R09 | Webhook giả mạo request | High |
| R10 | Gửi thông báo sai đối tượng | High |

## 2.3. Threat Model

Các đối tượng có thể gây ra rủi ro:

- External User: Người không thuộc doanh nghiệp.
- Malicious Employee: Nhân viên cố tình sử dụng sai quyền.
- Account Attacker: Người chiếm quyền tài khoản Telegram.
- Compromised System: Hệ thống backend hoặc Bot Token bị lộ.
- Data Manipulator: Người sửa đổi dữ liệu nhân sự trái phép.

Nguyên tắc:

Không được xem việc người dùng biết tên Bot, gửi `/start` hoặc cung cấp một số điện thoại là bằng chứng đủ để xác nhận danh tính nhân viên.

---

# 3. Security Design Principles

## 3.1. Identity Verification

Mỗi tài khoản Telegram phải được liên kết với một Employee ID hợp lệ.

## 3.2. Least Privilege

Người dùng chỉ được nhận những thông báo mà họ có quyền truy cập.

## 3.3. Defense in Depth

Không phụ thuộc vào một phương thức xác thực duy nhất.

## 3.4. Fail Secure

Khi xảy ra lỗi xác thực hoặc không thể kiểm tra trạng thái nhân sự, hệ thống không được tự động cho phép kết nối.

## 3.5. Revocable Access

Mọi liên kết Telegram phải có khả năng thu hồi.

## 3.6. Auditability

Các hành động quan trọng phải được ghi nhận để phục vụ kiểm tra và điều tra sự cố.

---

# 4. Proposed Authentication Flow

## 4.1. Tổng quan

Quy trình xác thực đề xuất:

```text
START
  |
  v
User sends /start
  |
  v
Bot requests Telegram Contact
  |
  v
Verify Contact Ownership
  |
  v
Normalize Phone Number
  |
  v
Lookup Employee Database
  |
  v
Employee Exists?
  |
  +---- NO ----> Reject
  |
  v
Employee Active?
  |
  +---- NO ----> Reject
  |
  v
Company Identity Verification
  |
  v
Email OTP / SSO
  |
  v
Verification Successful?
  |
  +---- NO ----> Reject / Retry
  |
  v
Check Existing Telegram Link
  |
  v
Create Employee-Telegram Link
  |
  v
Set Status = ACTIVE
  |
  v
Allow Notifications
  |
  v
END
```

## 4.2. Step 1 - User Initialization

Người dùng tìm Bot và gửi:

```text
/start
```

Bot phản hồi:

```text
Xin chào!

Để sử dụng hệ thống thông báo nội bộ,
bạn cần xác thực danh tính nhân viên.

Vui lòng chia sẻ số điện thoại Telegram
để bắt đầu quá trình xác thực.
```

## 4.3. Step 2 - Telegram Contact Verification

Sử dụng Telegram Bot API:

`KeyboardButton.request_contact = true`

Bot hiển thị nút:

```text
[ Chia sẻ số điện thoại ]
```

Khi người dùng nhấn nút, Telegram gửi Contact về Backend.

### Security Requirements

MUST:

- Chỉ xử lý yêu cầu xác thực trong Private Chat.
- Kiểm tra Contact có tồn tại.
- Kiểm tra `contact.user_id`.
- Kiểm tra `contact.user_id == message.from.id`.
- Không chấp nhận số điện thoại được nhập dưới dạng văn bản thông thường.
- Không chấp nhận Contact của người khác.

Ví dụ pseudocode:

```csharp
if (message.Chat.Type != ChatType.Private)
{
    return Reject("PRIVATE_CHAT_REQUIRED");
}

var contact = message.Contact;

if (contact == null)
{
    return Reject("CONTACT_REQUIRED");
}

if (contact.UserId != message.From.Id)
{
    return Reject("CONTACT_NOT_OWNED_BY_SENDER");
}
```

Lưu ý:

Việc kiểm tra `contact.user_id` giúp xác nhận Contact được chia sẻ thuộc tài khoản Telegram đang tương tác.

Tuy nhiên, đây không phải bằng chứng xác thực danh tính nhân viên hoặc chứng minh quyền sở hữu số điện thoại theo chuẩn viễn thông.

Vì vậy, cần tiếp tục xác thực thông qua hệ thống doanh nghiệp.

## 4.4. Step 3 - Normalize Phone Number

Chuẩn hóa số điện thoại trước khi truy vấn dữ liệu nhân sự.

Khuyến nghị sử dụng chuẩn E.164.

Ví dụ:

```text
Input:
0912345678

Normalized:
+84912345678
```

Không nên chỉ xóa ký tự đặc biệt bằng cách xử lý chuỗi đơn giản.

Nên sử dụng thư viện xử lý số điện thoại có hỗ trợ mã quốc gia.

## 4.5. Step 4 - Employee Lookup

Đối chiếu số điện thoại với danh sách nhân sự.

Employee Database:

| EmployeeCode | FullName | PhoneNumber | Status |
|---|---|---|---|
| NV001 | Nguyen Van A | +84912345678 | Active |
| NV002 | Tran Van B | +84987654321 | Active |
| NV003 | Le Van C | +84901234567 | Inactive |

Business Rules:

- Không tìm thấy nhân viên: Reject.
- Nhân viên Inactive: Reject.
- Nhiều nhân viên sử dụng cùng số điện thoại: Manual Review.
- Chỉ có một nhân viên Active phù hợp: Continue.

Không tự động chọn nhân viên đầu tiên khi có dữ liệu trùng lặp.

## 4.6. Step 5 - Company Identity Verification

Sau khi xác định được Employee ID **Active**, hệ thống xác thực thêm bằng **Email OTP**.

### Implemented choice: Email OTP (Gmail SMTP)

**Quyết định triển khai (v1.1):** dùng Email OTP. SSO giữ là hướng mở rộng sau.

Luồng đã triển khai:

```text
Employee matched (Active)
        |
        v
Generate 6-digit OTP (CSPRNG)
        |
        v
Store only HMAC hash in authentication_sessions
        |
        v
Send OTP email via Gmail SMTP (smtp.gmail.com:587 + STARTTLS)
        |
        v
Bot tells user: check email → copy OTP → type OTP in Telegram chat
        |
        v
User sends 6 digits in chat
        |
        v
Verify hash / expiry / attempt limit → Link Active
```

Bot thông báo (tóm tắt):

```text
Đã tìm thấy hồ sơ nhân viên.
Đã gửi mã OTP đến email (đã mask).
1) Mở email (kể cả Spam)
2) Sao chép mã 6 chữ số
3) Quay lại chat Telegram và nhập mã
```

OTP Requirements:

| Thuộc tính | Giá trị triển khai |
|---|---|
| OTP Length | 6 digits |
| Expiration | 300 seconds (5 minutes) |
| Maximum Attempts | 5 |
| Single Use | Yes (hash cleared on success) |
| Delivery | Gmail SMTP only (không gửi OTP qua Telegram) |
| Storage | HMAC-SHA256 với `OTP_PEPPER` |

MUST:

- OTP được sinh bằng Cryptographically Secure Random Generator.
- Không lưu OTP dạng plaintext.
- Giới hạn số lần nhập sai.
- Không cho phép sử dụng lại OTP.
- Hết hạn phải từ chối.
- Không ghi OTP vào Application Log.
- Không hiện OTP trong tin nhắn Telegram.

### Gmail SMTP configuration (`.env`)

| Biến | Ý nghĩa | Ví dụ |
|---|---|---|
| `SMTP_HOST` | Máy chủ SMTP Gmail | `smtp.gmail.com` |
| `SMTP_PORT` | Port STARTTLS | `587` |
| `SMTP_USER` | Tài khoản Gmail gửi | `sender@gmail.com` |
| `SMTP_PASSWORD` | **App Password** (không dùng mật khẩu đăng nhập) | 16 ký tự |
| `SMTP_FROM` | Địa chỉ From | cùng `SMTP_USER` |
| `SMTP_USE_TLS` | Bật STARTTLS | `true` |

Cách lấy App Password: bật 2-Step Verification trên Google Account → tạo App Password cho Mail.

Email **người nhận** lấy từ cột `employees.email` (email trong hồ sơ nhân sự), không phải bắt buộc trùng `SMTP_FROM`.

### Option B - Single Sign-On (chưa triển khai)

Giữ làm Phase sau nếu doanh nghiệp có Microsoft Entra ID / Google Workspace / Internal SSO.

## 4.7. Step 6 - Telegram Account Linking

Sau khi xác thực thành công, hệ thống liên kết:

```text
Employee ID
      |
      |
      v
Telegram Account
      |
      +-- Telegram User ID
      |
      +-- Telegram Chat ID
      |
      +-- Telegram Username
      |
      +-- Verified At
```

Không sử dụng Telegram Username làm khóa định danh.

Telegram User ID mới là định danh chính cần sử dụng.

Thông tin cần lưu:

| Field | Description |
|---|---|
| EmployeeId | ID nhân viên |
| TelegramUserId | ID Telegram |
| TelegramChatId | ID chat |
| PhoneNumber | Số điện thoại đã đối chiếu |
| VerifiedAt | Thời điểm xác thực |
| Status | Trạng thái liên kết |

## 4.8. Step 7 - Activate Connection

Khi toàn bộ xác thực thành công:

```text
Employee Status = Active
Identity Verification = Success
Telegram Account = Valid
Linking Policy = Passed

Result:
Connection Status = Active
```

Bot thông báo:

```text
Xác thực thành công!

Tài khoản Telegram đã được liên kết
với hồ sơ nhân viên của bạn.

Bạn đã có thể nhận thông báo nội bộ.
```

---

# 5. Alternative: Deep Linking Authentication

## 5.1. Overview

Telegram hỗ trợ Deep Linking.

Ví dụ:

```text
https://t.me/company_bot?start=RANDOM_TOKEN
```

Có thể sử dụng cơ chế này để khởi tạo liên kết từ hệ thống nội bộ.

## 5.2. Proposed Flow

```text
Employee
    |
    v
Login Company Portal
    |
    v
Click Connect Telegram
    |
    v
Backend Generates One-Time Token
    |
    v
Generate Telegram Deep Link
    |
    v
Employee Opens Link
    |
    v
Telegram Bot receives /start TOKEN
    |
    v
Backend validates token
    |
    v
Link Telegram User ID
```

## 5.3. Token Requirements

MUST:

- Token phải được sinh ngẫu nhiên bằng CSPRNG.
- Token chỉ được sử dụng một lần.
- Token có thời hạn ngắn.
- Token phải gắn với Employee ID.
- Token phải gắn với mục đích liên kết Telegram.
- Chỉ lưu hash của token.
- Không cho phép tái sử dụng token.

Ví dụ:

```text
Token:
Random 256-bit value

Expiration:
5-10 minutes

Usage:
One-time
```

Lưu ý:

Deep Linking chỉ truyền thông tin khởi tạo liên kết. Bản thân Deep Link không xác thực danh tính người dùng.

Cần đảm bảo token được cấp sau khi nhân viên đã xác thực với hệ thống nội bộ.

---

# 6. Account Linking Policy

## 6.1. Default Policy

Đề xuất:

Một nhân viên chỉ được liên kết với một tài khoản Telegram đang hoạt động.

Một Telegram User ID chỉ được liên kết với một Employee ID đang hoạt động.

## 6.2. Conflict Handling

| Trường hợp | Xử lý |
|---|---|
| Employee chưa có Telegram | Cho phép liên kết |
| Employee đã có Telegram | Từ chối hoặc yêu cầu đổi tài khoản |
| Telegram đã liên kết Employee khác | Từ chối |
| Employee Inactive | Từ chối |
| Telegram Link Revoked | Cho phép xác thực lại |
| Dữ liệu nhân sự bị trùng | Manual Review |

## 6.3. Change Telegram Account

Quy trình đổi tài khoản:

1. Nhân viên đăng nhập hệ thống nội bộ.
2. Truy cập chức năng quản lý Telegram.
3. Hủy liên kết cũ.
4. Xác thực tài khoản mới.
5. Tạo liên kết mới.
6. Ghi nhận Audit Log.

---

# 7. Connection Status Management

Không chỉ sử dụng IsVerified Boolean.

Đề xuất trạng thái:

| Status | Description |
|---|---|
| Pending | Đang chờ xác thực |
| Verified | Đã xác thực danh tính |
| Active | Được phép nhận thông báo |
| Rejected | Xác thực thất bại |
| Suspended | Tạm khóa |
| Revoked | Đã thu hồi quyền |

Business Rules:

- Chỉ Active mới được nhận thông báo.
- Pending không được nhận thông báo.
- Suspended không được nhận thông báo.
- Revoked không được nhận thông báo.
- Rejected không được nhận thông báo.

---

# 8. Authorization - Notification Access Control

Xác thực thành công không đồng nghĩa với việc người dùng được nhận tất cả thông báo.

Cần phân quyền theo:

- Phòng ban.
- Chức vụ.
- Nhóm nhân viên.
- Loại thông báo.
- Mức độ bảo mật.
- Phạm vi dữ liệu.

Ví dụ:

| Notification Type | Authorized Group |
|---|---|
| Company Announcement | All Active Employees |
| HR Announcement | HR Department |
| IT Maintenance | IT Department |
| Management Report | Management |
| Confidential Information | Authorized Users |

Trước khi gửi thông báo:

```text
Notification Request
       |
       v
Get Target Employees
       |
       v
Check Employee Status
       |
       v
Check Telegram Link Status
       |
       v
Check Authorization
       |
       v
Send Notification
```

MUST:

- Không gửi đến tài khoản chưa Active.
- Kiểm tra quyền tại thời điểm gửi.
- Không tin tưởng danh sách người nhận được truyền trực tiếp từ client.
- Ghi nhận kết quả gửi.

---

# 9. Account Revocation

## 9.1. Employee Resignation

Khi nhân viên nghỉ việc:

```text
HR System
    |
    v
Employee Status Changed
    |
    v
Employee = Inactive
    |
    v
Notification System
    |
    v
Revoke Telegram Link
    |
    v
Stop Notifications
```

## 9.2. Synchronization

Có thể sử dụng:

- Event-driven synchronization.
- Scheduled synchronization.
- HR API integration.

Đề xuất kết hợp:

1. Đồng bộ ngay khi HR phát sinh sự kiện.
2. Có tác vụ định kỳ đối soát dữ liệu.
3. Nếu không xác minh được trạng thái nhân sự, tạm dừng gửi thông báo nhạy cảm.

## 9.3. Manual Revocation

Admin có thể:

- Hủy liên kết Telegram.
- Khóa tài khoản.
- Kích hoạt lại sau khi xác thực.
- Xem lịch sử liên kết.

Mọi thao tác phải có Audit Log.

---

# 10. Rate Limiting & Anti-Abuse

## 10.1. OTP Protection

| Rule | Value |
|---|---|
| OTP Length | 6 digits |
| OTP Expiration | 3-5 minutes |
| Maximum Attempts | 5 |
| Resend Cooldown | 60 seconds |
| OTP Reuse | Not Allowed |

## 10.2. Rate Limit

Giới hạn theo:

- Telegram User ID.
- Employee ID.
- IP Address khi sử dụng web verification.
- Verification Session.

Ví dụ:

```text
Maximum OTP Requests:
5 requests / 15 minutes

Maximum Failed Attempts:
5 attempts / session

Temporary Lock:
15 minutes
```

Các giá trị cần được điều chỉnh theo quy mô và lưu lượng thực tế.

## 10.3. Anti-Brute Force

MUST:

- Rate limiting.
- Temporary lock.
- OTP expiration.
- Single-use token.
- Security logging.
- Generic error messages để tránh tiết lộ thông tin nhân sự.

---

# 11. Audit Log

## 11.1. Logging Requirements

Ghi nhận:

- Telegram User ID.
- Employee ID nếu xác định được.
- Action.
- Result.
- Timestamp.
- IP Address nếu có.
- Failure Reason.
- Actor thực hiện thao tác quản trị.

## 11.2. Important Events

| Event | Description |
|---|---|
| TELEGRAM_START | Người dùng bắt đầu kết nối |
| CONTACT_RECEIVED | Nhận Contact |
| CONTACT_VERIFIED | Contact hợp lệ |
| EMPLOYEE_FOUND | Tìm thấy nhân viên |
| OTP_SENT | OTP đã gửi |
| OTP_SUCCESS | OTP thành công |
| OTP_FAILED | OTP thất bại |
| ACCOUNT_LINKED | Liên kết thành công |
| ACCOUNT_REVOKED | Thu hồi liên kết |
| ACCOUNT_SUSPENDED | Tạm khóa |
| NOTIFICATION_SENT | Gửi thông báo |

## 11.3. Security Rules

Không ghi vào log:

- OTP plaintext.
- Bot Token.
- Access Token.
- Refresh Token.
- One-Time Token nguyên bản.
- Thông tin xác thực nhạy cảm.

Cần xác định thời hạn lưu Audit Log theo chính sách bảo mật và lưu trữ của doanh nghiệp.

---

# 12. Telegram Bot Security

## 12.1. Webhook Security

MUST:

- Sử dụng HTTPS.
- Cấu hình Telegram Webhook Secret Token.
- Kiểm tra header `X-Telegram-Bot-Api-Secret-Token`.
- Không xử lý request không hợp lệ.
- Chống xử lý trùng Telegram Update.

Ví dụ:

```csharp
var secret = Request.Headers[
    "X-Telegram-Bot-Api-Secret-Token"
].ToString();

if (!CryptographicOperations.FixedTimeEquals(
    Encoding.UTF8.GetBytes(secret),
    Encoding.UTF8.GetBytes(expectedSecret)))
{
    return Unauthorized();
}
```

Cần kiểm tra cả việc header có tồn tại và có đúng độ dài trước khi so sánh.

## 12.2. Bot Token Security

MUST:

- Không hard-code Bot Token.
- Không commit Bot Token lên GitHub.
- Sử dụng Secret Manager hoặc Environment Variables.
- Hạn chế quyền truy cập.
- Có quy trình rotate token khi nghi ngờ bị lộ.

## 12.3. Update Validation

Backend cần:

- Kiểm tra nguồn request.
- Kiểm tra loại Update.
- Kiểm tra Chat Type.
- Kiểm tra User ID.
- Kiểm tra nội dung dữ liệu.
- Xử lý idempotency.

---

# 13. Database Design

Đề xuất tối thiểu 5 bảng.

## 13.1. Employee

Quản lý thông tin nhân sự.

| Column | Type | Description |
|---|---|---|
| Id | UUID | Primary Key |
| EmployeeCode | VARCHAR | Employee Code |
| FullName | VARCHAR | Full Name |
| PhoneNumber | VARCHAR | Normalized Phone |
| Email | VARCHAR | Company Email |
| Status | INT | Employee Status |
| CreatedAt | DATETIME | Created Time |
| UpdatedAt | DATETIME | Updated Time |

## 13.2. TelegramAccount

Lưu thông tin Telegram.

| Column | Type | Description |
|---|---|---|
| Id | UUID | Primary Key |
| TelegramUserId | BIGINT | Telegram User ID |
| TelegramChatId | BIGINT | Telegram Chat ID |
| TelegramUsername | VARCHAR | Username |
| PhoneNumber | VARCHAR | Verified Contact |
| CreatedAt | DATETIME | Created Time |

## 13.3. EmployeeTelegramLink

Quản lý liên kết.

| Column | Type | Description |
|---|---|---|
| Id | UUID | Primary Key |
| EmployeeId | UUID | Employee FK |
| TelegramAccountId | UUID | Telegram FK |
| Status | INT | Link Status |
| VerifiedAt | DATETIME | Verification Time |
| LinkedAt | DATETIME | Link Time |
| RevokedAt | DATETIME | Revocation Time |
| RevokedReason | VARCHAR | Reason |

## 13.4. AuthenticationSession

Quản lý phiên xác thực.

| Column | Type | Description |
|---|---|---|
| Id | UUID | Primary Key |
| TelegramUserId | BIGINT | Telegram ID |
| EmployeeId | UUID | Employee FK |
| TokenHash | VARCHAR | Token Hash |
| OTPHash | VARCHAR | OTP Hash |
| Status | INT | Session Status |
| ExpiresAt | DATETIME | Expiration |
| Attempts | INT | Failed Attempts |
| CreatedAt | DATETIME | Created Time |

Không lưu OTP hoặc token dạng plaintext.

## 13.5. AuthenticationLog

Lưu lịch sử xác thực.

| Column | Type | Description |
|---|---|---|
| Id | UUID | Primary Key |
| TelegramUserId | BIGINT | Telegram ID |
| EmployeeId | UUID | Employee FK |
| Action | VARCHAR | Action |
| Result | VARCHAR | Result |
| Reason | VARCHAR | Reason |
| CreatedAt | DATETIME | Timestamp |

## 13.6. Database Constraints

MUST:

- Unique EmployeeCode.
- Unique TelegramUserId trong bảng TelegramAccount.
- Kiểm soát một Employee có tối đa một liên kết Active.
- Kiểm soát một Telegram chỉ liên kết một Employee Active.
- Tạo index cho EmployeeId, TelegramUserId, Status.
- Sử dụng Transaction khi tạo hoặc thay đổi liên kết.

Nếu hỗ trợ lưu lịch sử nhiều liên kết, sử dụng unique filtered index hoặc cơ chế tương đương tùy hệ quản trị database.

---

# 14. System Architecture

```text
                  EMPLOYEE
                      |
                      v
                TELEGRAM BOT
                      |
                      v
               TELEGRAM WEBHOOK
                      |
                      v
             AUTHENTICATION SERVICE
                      |
          +-----------+-----------+
          |                       |
          v                       v
   CONTACT VERIFICATION    EMPLOYEE LOOKUP
          |                       |
          v                       v
   TELEGRAM API DATA       EMPLOYEE DATABASE
                                  |
                                  v
                         COMPANY IDENTITY
                            VERIFICATION
                                  |
                             +----+----+
                             |         |
                             v         v
                            OTP       SSO
                             |         |
                             +----+----+
                                  |
                                  v
                         ACCOUNT LINKING
                                  |
                                  v
                         AUTHORIZATION
                                  |
                                  v
                        NOTIFICATION SERVICE
                                  |
                                  v
                            TELEGRAM API
```

## 14.1. Module Responsibilities

| Module | Responsibility |
|---|---|
| Telegram Bot Handler | Receive Telegram Updates |
| Authentication Service | Verify user identity |
| Employee Service | Employee information |
| Account Linking Service | Manage Telegram links |
| Authorization Service | Control notification access |
| Notification Service | Send notifications |
| Audit Service | Record security events |

Không bắt buộc phải triển khai thành Microservices.

Có thể triển khai Modular Monolith trong giai đoạn đầu.

---

# 15. API Design

Các API dưới đây là đề xuất để đội phát triển tham khảo.

## 15.1. Telegram Webhook

```http
POST /api/telegram/webhook
```

Chức năng:

- Nhận Telegram Update.
- Xác thực Webhook Secret.
- Xử lý `/start`.
- Xử lý Contact.
- Điều phối Authentication Flow.

## 15.2. Start Authentication

```http
POST /api/auth/telegram/start
```

Request:

```json
{
  "telegramUserId": 123456789,
  "telegramChatId": 123456789
}
```

Response:

```json
{
  "success": true,
  "status": "PENDING_CONTACT"
}
```

## 15.3. Verify Contact

```http
POST /api/auth/telegram/verify-contact
```

Request:

```json
{
  "telegramUserId": 123456789,
  "phoneNumber": "+84912345678",
  "contactUserId": 123456789
}
```

Backend phải đối chiếu các thông tin này với Telegram Update thực tế đã nhận.

Không được tin tưởng một API client có thể tự gửi `contactUserId` hoặc `telegramUserId` tùy ý.

## 15.4. Send OTP

```http
POST /api/auth/telegram/send-otp
```

Request:

```json
{
  "sessionId": "verification-session-id"
}
```

## 15.5. Verify OTP

```http
POST /api/auth/telegram/verify-otp
```

Request:

```json
{
  "sessionId": "verification-session-id",
  "otp": "123456"
}
```

## 15.6. Account Linking

```http
POST /api/auth/telegram/link
```

Request:

```json
{
  "sessionId": "verification-session-id"
}
```

Backend tự lấy Employee ID và Telegram User ID từ phiên đã xác thực.

Không cho client tự quyết định Employee ID cần liên kết.

## 15.7. Revoke Account

```http
POST /api/admin/telegram/revoke
```

Request:

```json
{
  "employeeId": "employee-uuid",
  "reason": "Employee resigned"
}
```

API này chỉ dành cho Admin có quyền phù hợp.

---

# 16. Business Rules

| ID | Rule | Priority |
|---|---|---|
| BR01 | Chỉ nhân viên Active được kết nối | MUST |
| BR02 | Phải xác minh Telegram Contact | MUST |
| BR03 | Contact User ID phải khớp người gửi | MUST |
| BR04 | Phải xác thực qua kênh công ty | MUST |
| BR05 | Telegram User ID phải duy nhất | MUST |
| BR06 | Không cho phép tài khoản chưa Active nhận thông báo | MUST |
| BR07 | Có thể thu hồi liên kết | MUST |
| BR08 | Ghi Audit Log | MUST |
| BR09 | Giới hạn OTP | MUST |
| BR10 | Tự động thu hồi khi nhân viên nghỉ việc | SHOULD |
| BR11 | Hỗ trợ quản lý kết nối qua Admin Portal | SHOULD |
| BR12 | Phát hiện hành vi bất thường | OPTIONAL |

---

# 17. Error Handling

| Error Code | Description | Action |
|---|---|---|
| CONTACT_REQUIRED | Chưa chia sẻ Contact | Yêu cầu gửi lại |
| CONTACT_NOT_OWNED_BY_SENDER | Contact không thuộc người gửi | Reject |
| EMPLOYEE_NOT_FOUND | Không tìm thấy nhân viên | Reject |
| EMPLOYEE_INACTIVE | Nhân viên không hoạt động | Reject |
| DUPLICATE_PHONE | Số điện thoại trùng | Manual Review |
| OTP_EXPIRED | OTP hết hạn | Yêu cầu OTP mới |
| OTP_INVALID | OTP sai | Retry trong giới hạn |
| OTP_LOCKED | Vượt số lần thử | Temporary Lock |
| TELEGRAM_ALREADY_LINKED | Telegram đã liên kết | Reject |
| EMPLOYEE_ALREADY_LINKED | Nhân viên đã có Telegram | Conflict Handling |
| SESSION_EXPIRED | Phiên hết hạn | Restart |
| ACCOUNT_REVOKED | Tài khoản bị thu hồi | Reject |

Thông báo cho người dùng không nên tiết lộ quá nhiều thông tin nhân sự.

Ví dụ, thay vì trả lời chi tiết rằng số điện thoại này thuộc nhân viên nào, chỉ nên thông báo:

```text
Không thể xác thực thông tin.

Vui lòng kiểm tra lại hoặc liên hệ
bộ phận quản trị hệ thống.
```

---

# 18. Non-Functional Requirements

## 18.1. Security

- HTTPS.
- Secure Secret Management.
- OTP Protection.
- Rate Limiting.
- Audit Logging.
- Database Access Control.
- Secure Webhook.
- Input Validation.

## 18.2. Reliability

- Không xử lý trùng Telegram Update.
- Có retry khi Telegram API lỗi.
- Có cơ chế theo dõi lỗi gửi thông báo.
- Không gửi thông báo khi trạng thái xác thực không hợp lệ.

## 18.3. Performance

- Có index cho các trường tìm kiếm.
- Không truy vấn toàn bộ Employee Database khi xác thực.
- Sử dụng cache có kiểm soát cho dữ liệu ít thay đổi.
- Không cache trạng thái thu hồi theo cách khiến quyền đã bị thu hồi vẫn tiếp tục có hiệu lực quá lâu.

## 18.4. Scalability

- Hỗ trợ nhiều nhân viên kết nối đồng thời.
- Có thể mở rộng số lượng Telegram Update.
- Có thể tách Notification Service khi lưu lượng tăng.

---

# 19. Testing & Acceptance Criteria

## 19.1. Contact Verification

| Test Case | Expected Result |
|---|---|
| Contact hợp lệ | Continue |
| Không có Contact | Reject |
| Contact User ID khác Sender ID | Reject |
| Chat là Group | Reject |
| Phone Number không hợp lệ | Reject |

## 19.2. Employee Verification

| Test Case | Expected Result |
|---|---|
| Nhân viên Active | Continue |
| Không tìm thấy nhân viên | Reject |
| Nhân viên Inactive | Reject |
| Trùng số điện thoại | Manual Review |
| Email không hợp lệ | Reject |

## 19.3. OTP Testing

| Test Case | Expected Result |
|---|---|
| OTP đúng | Success |
| OTP sai | Reject |
| OTP hết hạn | Reject |
| OTP sử dụng lần hai | Reject |
| Nhập sai quá giới hạn | Lock |
| Gửi OTP quá nhiều | Rate Limit |

## 19.4. Account Linking

| Test Case | Expected Result |
|---|---|
| Employee chưa liên kết | Success |
| Employee đã liên kết | Conflict |
| Telegram đã thuộc Employee khác | Reject |
| Session hết hạn | Reject |
| Token đã sử dụng | Reject |

## 19.5. Notification Authorization

| Test Case | Expected Result |
|---|---|
| Employee Active + Link Active | Allow |
| Employee Inactive | Deny |
| Link Revoked | Deny |
| Link Suspended | Deny |
| Không đủ quyền nhận thông báo | Deny |

## 19.6. Acceptance Criteria

Tính năng được xem là đạt yêu cầu khi:

- Người ngoài không thể tự do kết nối.
- Người dùng phải hoàn thành các bước xác thực.
- Telegram ID được liên kết chính xác với Employee ID.
- Không có tài khoản chưa xác thực nhận được thông báo.
- Có thể thu hồi liên kết.
- Không thể sử dụng lại OTP hoặc token.
- Các hoạt động xác thực đều có Audit Log.
- Các tình huống lỗi được xử lý an toàn.

---

# 20. Implementation Roadmap

## Phase 1 - Basic Authentication

Mục tiêu: Ngăn chặn người ngoài tự do kết nối.

Tasks:

- [x] Chuẩn hóa Employee Database.
- [x] Yêu cầu Telegram Contact.
- [x] Kiểm tra Contact User ID.
- [x] Chuẩn hóa số điện thoại (E.164 / `phonenumbers`).
- [x] Đối chiếu Employee Database.
- [x] Kiểm tra trạng thái nhân viên (`active` only).
- [x] Lưu Telegram User ID.
- [x] Tạo EmployeeTelegramLink (`active`).
- [x] Chặn tài khoản chưa Active nhận thông báo.

## Phase 2 - Enhanced Security

Mục tiêu: Tăng độ tin cậy của xác thực.

Tasks:

- [x] Tích hợp Email OTP qua **Gmail SMTP**.
- [x] Quản lý Authentication Session.
- [x] Chống Brute Force (max attempts / lock session).
- [ ] Rate Limiting nâng cao (IP / resend window đầy đủ).
- [x] Kiểm soát liên kết trùng (unique Active link).
- [x] Audit Log (`authentication_logs`).
- [x] Chức năng hủy liên kết (Admin Streamlit).
- [x] Quản lý trạng thái kết nối.

## Phase 3 - Enterprise Security

Mục tiêu: Quản trị tập trung.

Tasks:

- [ ] Đồng bộ dữ liệu HR.
- [ ] Tự động thu hồi khi nghỉ việc.
- [ ] Admin Management Portal (hiện chỉ Streamlit MVP).
- [ ] Phân quyền thông báo theo phòng ban.
- [ ] Security Monitoring.
- [ ] Anomaly Detection.
- [ ] Báo cáo lịch sử kết nối.
- [ ] Quy trình xử lý sự cố bảo mật.
- [ ] SSO thay / bổ sung Email OTP.

---

# 21. Open Questions

Các vấn đề cần doanh nghiệp xác nhận trước khi triển khai.

## 21.1. Employee Data

- Dữ liệu nhân sự đang được quản lý ở đâu?
- Có API đồng bộ từ HRM không?
- Số điện thoại có duy nhất cho từng nhân viên không?
- Email công ty có đầy đủ không?
- Có dữ liệu trạng thái nhân viên Active/Inactive không?

## 21.2. Identity Verification

- Doanh nghiệp có SSO không?
- Có thể gửi OTP qua email công ty không?
- Có cần xác thực lại khi đổi Telegram không?

## 21.3. Account Linking Policy

- Một nhân viên được phép có bao nhiêu Telegram?
- Có cho phép dùng Telegram cá nhân không?
- Có cần Admin duyệt khi đổi tài khoản không?

## 21.4. Notification Policy

- Có những nhóm thông báo nào?
- Có thông báo chứa dữ liệu nhạy cảm không?
- Có cần phân quyền theo phòng ban không?

## 21.5. Operations

- Ai có quyền thu hồi liên kết?
- Ai chịu trách nhiệm xử lý nhân viên không xác thực được?
- Thời gian đồng bộ trạng thái nghỉ việc là bao lâu?
- Thời hạn lưu Audit Log là bao lâu?

---

# 22. Final Recommendation

Kiến trúc xác thực **đã chọn và triển khai (v1.1)**:

```text
Telegram /start
      |
      v
Telegram Contact Verification (request_contact button)
      |
      v
Employee Database Lookup (E.164 phone)
      |
      v
Employee Status Validation (active only)
      |
      v
Company Email OTP via Gmail SMTP
      |
      v
User re-enters OTP in Telegram chat
      |
      v
Telegram Account Linking (status = active)
      |
      v
Authorization (broadcast chỉ Active links)
      |
      v
Notification Enabled
```

Các yêu cầu bảo mật quan trọng nhất:

1. Không cho phép kết nối chỉ bằng `/start`.
2. Không tin tưởng số điện thoại do người dùng tự nhập.
3. Kiểm tra Contact User ID phải khớp Telegram Sender ID.
4. Xác thực danh tính qua kênh email độc lập (Gmail SMTP).
5. Sử dụng Telegram User ID làm định danh tài khoản.
6. Kiểm tra trạng thái nhân sự trước khi cho phép nhận thông báo.
7. Có cơ chế thu hồi quyền.
8. Bảo vệ Bot Token trong `.env`.
9. Có Audit Log.
10. Chỉ Active link nhận thông báo.

**Approach đã áp dụng:** Email OTP + Telegram Contact Verification (chưa dùng SSO).

Không xem số điện thoại là yếu tố xác thực duy nhất.

---

# 23. Implemented Runtime Flow (v1.1 — Gmail OTP)

**Update datetime:** 2026-11-14 16:35 (UTC+7)

## 23.1. End-to-end user steps

1. Admin thêm nhân viên trong Streamlit (`employee_code`, phone E.164, email, `status=active`).
2. User mở bot Telegram → `/start`.
3. Bot hiện nút **« Chia sẻ số điện thoại »** (ReplyKeyboard `request_contact`).
4. User chia sẻ contact; backend kiểm tra `contact.user_id == from.id`.
5. Normalize phone → lookup `employees` → phải **active** và không trùng mơ hồ.
6. Tạo `authentication_sessions`, hash OTP, **gửi email qua Gmail SMTP**.
7. Bot báo đã gửi mail; **không** gửi OTP trong Telegram.
8. User mở email → copy 6 số → gõ vào chat bot.
9. Verify OTP → tạo `employee_telegram_links` status `active`.
10. Broadcast chỉ gửi tới các link Active + employee Active.

## 23.2. Code mapping

| Bước | Module |
|---|---|
| Long-poll `/start`, contact, OTP text | `app/telegram/bot_listener.py` |
| Orchestration | `app/services/authentication.py` |
| Gmail SMTP send | `app/services/email_otp.py` |
| OTP crypto | `app/auth/otp.py` |
| Phone E.164 | `app/auth/phone.py` |
| Persistence | `app/db/auth_repository.py` + `sql/schema.sql` |
| Admin UI | `app/main.py` |
| Broadcast ACL | `app/services/broadcast.py` |

## 23.3. Failure behavior

| Tình huống | Kết quả |
|---|---|
| SMTP chưa cấu hình / gửi mail lỗi | Bot: không gửi được OTP; session hết hiệu lực |
| Employee inactive / not found | Reject generic (không lộ HR) |
| OTP sai | Retry tới max attempts rồi lock |
| OTP hết hạn | Yêu cầu `/start` lại |
| Link Active đã tồn tại | Conflict / reject theo policy |

---

**Document End**

**Document Name:** `update_authen_v1.0.md`  
**Version:** 1.1  
**Status:** Implemented (Gmail Email OTP)

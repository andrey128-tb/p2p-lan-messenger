# LAN Chat & File Sharing

Ứng dụng **chat và chia sẻ file ngang hàng (Peer-to-Peer)** trong cùng mạng LAN/Wi-Fi, viết bằng Python, có giao diện đồ họa PyQt6. Không cần máy chủ trung tâm, không cần internet: các máy trong cùng mạng tự tìm thấy nhau và liên lạc trực tiếp.

## 1. Giới thiệu

Mỗi máy chạy một bản của chương trình và đồng thời đóng ba vai trò:

- **UDP broadcaster/listener:** quảng bá sự hiện diện của mình và phát hiện các peer khác (peer discovery).
- **TCP server:** chấp nhận kết nối chat hoặc nhận file từ peer khác.
- **TCP client:** chủ động kết nối tới peer mà người dùng chọn.

Đồ án tập trung vào lập trình mạng ở mức Socket: tự thiết kế giao thức tầng ứng dụng (framing trên TCP, discovery bằng UDP broadcast), xử lý đa luồng và truyền file an toàn. Chương trình chỉ dùng thư viện chuẩn của Python (`socket`, `threading`, `struct`, `json`...) cho phần mạng; không dùng framework mạng hay server bên ngoài. Hai thư viện ngoài là PyQt6 (giao diện) và prompt_toolkit.

## 2. Chức năng

| Chức năng | Mô tả |
| --- | --- |
| Tự động tìm peer | Mỗi 3 giây gửi UDP broadcast `HELLO`; peer mới xuất hiện trong danh sách bên trái |
| Phát hiện peer rời mạng | Không nhận `HELLO` trong 10 giây thì peer bị đánh dấu offline và xóa khỏi danh sách |
| Chat hai chiều | Mỗi cuộc chat là một kết nối TCP riêng, có một luồng nhận cho mỗi kết nối |
| Nhiều cuộc chat song song | Giữ nhiều kết nối đồng thời, chuyển qua lại giữa các peer |
| Tin chưa đọc | Tin từ peer không phải cuộc chat đang mở được lưu lại và hiển thị số lượng |
| Trạng thái "Đã xem" | Khi bên kia đang mở khung chat, người gửi thấy "✓ Đã xem" |
| Gửi file | Mỗi lần gửi mở một kết nối TCP riêng nên không chặn luồng chat; có thanh tiến độ 0–100% |
| Nhận file | Ghi vào `downloads/`, dùng file `.part` và chỉ đổi tên khi nhận đủ dữ liệu; thông báo hiện trong khung chat |
| Giới hạn độ dài tin nhắn | Tin vượt giới hạn (mặc định 4096 ký tự) bị chặn gửi, có cảnh báo trên giao diện và log trên console, nội dung đang nhập được giữ nguyên |
| Tìm kiếm peer | Ô tìm kiếm lọc danh sách người online theo tên |
| Tự kết nối lại | Nếu gửi tin thất bại do mất kết nối, chương trình thử kết nối lại một lần |

## 3. Cấu trúc project

```text
<project-folder>/
├── run.py                  # điểm khởi chạy
├── requirements.txt        # danh sách thư viện cần cài
├── README.md
├── .gitignore
├── downloads/              # thư mục chứa file nhận được (tạo tự động)
└── lanchat/
    ├── __init__.py
    ├── app.py              # lớp điều phối chính, tham số dòng lệnh, hàm main()
    ├── config.py           # cấu hình: port, chu kỳ broadcast, timeout, giới hạn...
    ├── protocol.py         # framing TCP: frame JSON có header độ dài 4 byte
    ├── peer_manager.py     # bảng peer tìm thấy qua UDP, cập nhật và hết hạn
    ├── discovery.py        # UDP broadcaster, UDP listener, peer cleaner
    ├── tcp_server.py       # nhận kết nối TCP, phân loại chat/file
    ├── connection_manager.py  # quản lý các kết nối chat, luồng nhận tin
    ├── chat_manager.py     # lịch sử chat và bộ đếm tin chưa đọc
    ├── file_transfer.py    # gửi file và nhận file an toàn
    ├── ui.py               # giao diện PyQt6
    └── icons/              # logo.png, find.png, file.png, send.png
```

Thư mục `__pycache__/` và môi trường ảo (`.venv/`) sinh ra khi chạy, không thuộc mã nguồn.

### Trách nhiệm từng module

- `app.py`: ghép các dịch vụ lại với nhau, xử lý callback (tin nhắn đến, peer online/offline, nhận file) và truyền sự kiện lên giao diện.
- `config.py`: kiểu dữ liệu cấu hình bất biến (`dataclass(frozen=True)`) cùng hàm `validate()` kiểm tra tính hợp lệ.
- `protocol.py`: `send_frame()`, `recv_frame()`, `recv_exact()`. Đảm bảo nhận đủ từng frame dù TCP là luồng byte.
- `peer_manager.py`: dữ liệu peer, bảo vệ bằng `threading.Lock`.
- `discovery.py`: phân tích gói `HELLO`, bỏ qua gói do chính máy mình gửi.
- `tcp_server.py`: đọc frame `HI` đầu tiên để biết kết nối là `chat` hay `file`, kiểm tra port hợp lệ rồi bàn giao.
- `connection_manager.py`: `PeerConnection` (một kết nối chat hai chiều) và `ConnectionManager` (sổ đăng ký kết nối, xử lý trường hợp hai bên cùng kết nối cho nhau).
- `file_transfer.py`: làm sạch tên file nhận được, tránh ghi đè file trùng tên, gửi và nhận theo từng khối 64 KiB.
- `ui.py`: cửa sổ chính, danh sách peer, bong bóng chat, thanh tiến độ gửi file.

## 4. Yêu cầu

- **Python 3.10 trở lên** (mã dùng cú pháp kiểu `dict[str, Any]`).
- Hai hoặc nhiều máy trong **cùng mạng LAN/Wi-Fi**, cùng subnet.
- Thư viện Python (nằm trong `requirements.txt`): `PyQt6` và `prompt_toolkit`.
- Cho phép **UDP 9999** và **TCP 5000** (hoặc port bạn chọn) đi vào qua tường lửa.
- Router/Access Point không bật "client isolation" (cách ly thiết bị), vì khi đó các máy không thấy nhau.

## 5. Cài đặt

Các bước chung trên mọi hệ điều hành:

1. Cài Python 3.10+.
2. Tải hoặc clone mã nguồn, mở terminal tại thư mục gốc của project (nơi có `run.py`).
3. Tạo môi trường ảo (virtual environment) và cài thư viện từ `requirements.txt`.
4. Cấu hình tường lửa cho phép các port của ứng dụng.
5. Chạy `python run.py --name <tên-của-bạn>` trên mỗi máy.

Hãy luôn chạy lệnh từ **thư mục gốc project**, vì thư mục `downloads/` mặc định được tạo theo thư mục làm việc hiện tại.

### 5.1. Windows (10/11)

**Bước 1. Cài Python.** Tải bản cài từ <https://www.python.org/downloads/> và tích chọn **"Add python.exe to PATH"** ở màn hình đầu tiên. Hoặc dùng `winget`:

```powershell
winget install Python.Python.3.12
```

Kiểm tra:

```powershell
py --version
```

**Bước 2. Tạo môi trường ảo và cài thư viện** (PowerShell):

```powershell
cd <project-folder>

py -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell báo không cho chạy script (`running scripts is disabled`), chạy lệnh sau một lần rồi kích hoạt lại:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Nếu dùng Command Prompt (cmd), kích hoạt bằng `.venv\Scripts\activate.bat`.

**Bước 3. Tường lửa.** Lần chạy đầu tiên, Windows Defender Firewall thường hiện hộp thoại hỏi quyền cho Python. Hãy chọn **Private networks** rồi Allow. Nếu không thấy hộp thoại, mở PowerShell **với quyền Administrator** và tạo rule:

```powershell
New-NetFirewallRule -DisplayName "LAN Chat TCP 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Private
New-NetFirewallRule -DisplayName "LAN Chat UDP 9999" -Direction Inbound -Protocol UDP -LocalPort 9999 -Action Allow -Profile Private
```

Mạng Wi-Fi phải được đặt ở hồ sơ **Private** (Settings → Network & internet → Wi-Fi → thuộc tính mạng → Network profile type). Ở hồ sơ Public, Windows chặn kết nối đến nên các máy khác sẽ không kết nối được tới bạn.

Xóa rule khi không cần nữa:

```powershell
Remove-NetFirewallRule -DisplayName "LAN Chat TCP 5000"
Remove-NetFirewallRule -DisplayName "LAN Chat UDP 9999"
```

**Bước 4. Chạy:**

```powershell
python run.py --name Andrey
```

### 5.2. Linux

**Bước 1. Cài Python, pip và venv** theo bản phân phối:

```bash
# Arch Linux / Manjaro
sudo pacman -S python python-pip

# Debian / Ubuntu / Linux Mint
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

# Fedora
sudo dnf install -y python3 python3-pip
```

**Bước 2. Tạo môi trường ảo và cài thư viện:**

```bash
cd <project-folder>

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Trên Debian/Ubuntu, PyQt6 cần thêm thư viện hệ thống cho plugin xcb của Qt. Nếu khi chạy gặp lỗi `Could not load the Qt platform plugin "xcb"`, cài:

```bash
sudo apt install -y libxcb-cursor0
```

**Bước 3. Tường lửa.** Chọn công cụ bạn đang dùng.

*firewalld* (Fedora, Arch có cài firewalld), ví dụ zone `public`:

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --zone=public --add-port=9999/udp
sudo firewall-cmd --zone=public --add-port=5000/tcp
```

Lưu qua lần khởi động lại:

```bash
sudo firewall-cmd --permanent --zone=public --add-port=9999/udp
sudo firewall-cmd --permanent --zone=public --add-port=5000/tcp
sudo firewall-cmd --reload
```

*ufw* (Ubuntu):

```bash
sudo ufw allow 5000/tcp
sudo ufw allow 9999/udp
```

Kiểm tra cổng đang lắng nghe sau khi chạy ứng dụng:

```bash
ss -lntup | grep -E '5000|9999'
```

**Bước 4. Chạy:**

```bash
python run.py --name Andrey
```

Nếu dùng Wayland và cửa sổ không hiển thị đúng, thử chỉ định nền tảng Qt:

```bash
QT_QPA_PLATFORM=wayland python run.py --name Andrey
# hoặc
QT_QPA_PLATFORM=xcb python run.py --name Andrey
```

### 5.3. macOS

**Bước 1. Cài Python 3.10+.** Dùng Homebrew hoặc bản cài từ python.org:

```bash
brew install python
python3 --version
```

**Bước 2. Tạo môi trường ảo và cài thư viện:**

```bash
cd <project-folder>

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Bước 3. Quyền mạng.**

- Lần chạy đầu, macOS có thể hỏi *"Do you want the application "Python" to accept incoming network connections?"*. Chọn **Allow**.
- Nếu Firewall của macOS đang bật và bạn đã từ chối trước đó: System Settings → Network → Firewall → Options, rồi cho phép Python nhận kết nối đến.
- Trên các phiên bản macOS mới (từ macOS 15), hệ thống có thể yêu cầu quyền **Local Network** cho ứng dụng đang chạy lệnh (Terminal, iTerm, VS Code...). Nếu không thấy peer nào, kiểm tra tại System Settings → Privacy & Security → Local Network và bật cho ứng dụng terminal bạn dùng.

**Bước 4. Chạy:**

```bash
python run.py --name Andrey
```

Nếu discovery không hoạt động với địa chỉ broadcast mặc định, xem mục 6.3 để dùng địa chỉ broadcast của subnet.

## 6. Chạy chương trình

### 6.1. Cách chạy cơ bản

Trên mỗi máy, kích hoạt môi trường ảo rồi chạy:

```bash
python run.py --name Andrey
```

Máy thứ hai:

```bash
python run.py --name Minh
```

Mỗi tên hiển thị trên LAN nên khác nhau và **không chứa ký tự `|`**. Cửa sổ ứng dụng mở ra, tiêu đề hiển thị tên, IP và TCP port của máy bạn. Terminal vẫn in log hoạt động (peer online/offline, tiến độ gửi file, tin nhắn bị từ chối...).

### 6.2. Tham số dòng lệnh

| Tham số | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `--name` | (bắt buộc) | Tên hiển thị trên LAN |
| `--tcp-port` | `5000` | Cổng TCP lắng nghe |
| `--udp-port` | `9999` | Cổng UDP dùng cho discovery |
| `--broadcast` | `255.255.255.255` | Địa chỉ broadcast IPv4 |
| `--downloads` | `downloads` | Thư mục lưu file nhận được |

Port hợp lệ nằm trong khoảng 1024–49151. Xem tất cả tùy chọn:

```bash
python run.py --help
```

Các giá trị khác nằm trong `lanchat/config.py`: chu kỳ broadcast 3 giây, timeout peer 10 giây, khối đọc/ghi file 64 KiB, kích thước tối đa của một frame điều khiển 1 MiB, và `max_message_chars` (giới hạn độ dài một tin nhắn, mặc định 4096 ký tự).

### 6.3. Địa chỉ broadcast theo subnet

Một số mạng không chuyển tiếp gói gửi tới `255.255.255.255`. Khi đó dùng địa chỉ broadcast của subnet, ví dụ mạng `192.168.1.0/24` thì là `192.168.1.255`:

```bash
python run.py --name Andrey --broadcast 192.168.1.255
```

Cách xem địa chỉ IP và subnet của máy:

```bash
# Windows
ipconfig
# Linux
ip -4 addr
# macOS
ifconfig | grep broadcast
```

### 6.4. Chạy nhiều bản trên cùng một máy

Để thử nhanh khi chỉ có một máy, phải dùng **TCP port khác nhau** cho mỗi bản:

```bash
python run.py --name Andrey --tcp-port 5000
python run.py --name Test    --tcp-port 5001 --downloads downloads_test
```

Lưu ý: nhiều hệ điều hành không phân phối broadcast tới nhiều socket cùng bind một UDP port trên cùng một máy, nên discovery giữa hai bản trên cùng máy có thể không hoạt động. Cách thử đáng tin cậy nhất là **hai máy thật trong cùng LAN**.

## 7. Hướng dẫn sử dụng

1. Mở ứng dụng trên hai máy. Sau khoảng 3–6 giây, tên của nhau xuất hiện trong danh sách bên trái (`Online: n`).
2. Có thể gõ vào ô **Tìm kiếm người online** để lọc theo tên.
3. Bấm vào một người để mở cuộc chat. Chương trình kết nối TCP tới họ, thanh trên cùng hiển thị trạng thái kết nối.
4. Gõ tin nhắn rồi nhấn **Enter** hoặc bấm nút gửi.
5. Để gửi file, bấm biểu tượng **kẹp giấy / file**, chọn file; thanh tiến độ hiện trong khung chat. Bên nhận thấy thông báo `📁 Đã gửi file: <tên file>` và file nằm trong `downloads/`.
6. Tin nhắn từ người khác khi bạn đang mở cuộc chat khác hiển thị dưới dạng số tin chưa đọc cạnh tên người đó.
7. Nếu tin nhắn dài hơn giới hạn, một thông báo đỏ hiện phía trên ô nhập (ví dụ `Tin nhắn quá dài: 5000/4096 ký tự`), nút gửi không có tác dụng và nội dung bạn đã gõ **không bị xóa**; hãy rút gọn rồi gửi lại. Sự kiện này cũng được ghi trong terminal.
8. Đóng cửa sổ để thoát; chương trình gửi `BYE` tới các peer đang kết nối và dừng các dịch vụ.

> Phiên bản này khởi chạy giao diện đồ họa (`run_gui()` trong hàm `main()` của `app.py`). Chế độ dòng lệnh với các lệnh `/list`, `/chat`, `/send`, `/status`, `/leave`, `/quit` vẫn còn trong lớp `LANChatApp` (`run()`); để dùng, đổi `run_gui()` thành `run()` trong `main()`. Việc đổi trạng thái `online/away` hiện chỉ có ở chế độ dòng lệnh.

## 8. Giao thức ứng dụng

### 8.1. UDP discovery

Mỗi peer broadcast một datagram:

```text
HELLO|<name>|<tcp_port>|<status>
```

Ví dụ: `HELLO|Andrey|5000|online`

- Gửi mỗi 3 giây tới `<broadcast>:<udp_port>`.
- Bên nghe lấy **IP nguồn** từ `recvfrom()` và TCP port từ nội dung gói.
- Gói sai định dạng (sai số trường, tên rỗng, status lạ, port ngoài 1024–49151) bị bỏ qua.
- Gói do chính máy mình gửi (cùng IP và TCP port) bị bỏ qua.
- Không nhận `HELLO` trong 10 giây thì peer bị xóa.

### 8.2. TCP control framing

TCP là luồng byte, một lần `recv()` không đảm bảo ứng với đúng một tin nhắn. Vì vậy mọi control frame có dạng:

```text
+----------------------+-----------------------------+
| 4-byte unsigned size | JSON payload (UTF-8)        |
+----------------------+-----------------------------+
```

`size` là số byte của phần JSON, viết theo big-endian (network byte order). Bên nhận đọc chính xác 4 byte header, kiểm tra `0 < size <= 1 MiB`, rồi đọc đúng `size` byte và giải mã JSON. Frame sai độ dài, sai UTF-8 hoặc không phải JSON object bị từ chối và đóng kết nối.

Các frame chính:

```json
{"type":"HI","kind":"chat","name":"Andrey","port":5000,"peer_id":"192.168.1.10:5000"}
{"type":"MSG","text":"Xin chào"}
{"type":"BYE"}
```

Frame đầu tiên của mọi kết nối phải là `HI` (với `kind` là `chat` hoặc `file`); kết nối sai quy tắc bị server từ chối.

Dấu "Đã xem" được truyền bằng một tin `MSG` mang chuỗi đánh dấu đặc biệt (`\x00SEEN\x00`), không được lưu vào lịch sử chat, nên không cần thay đổi giao thức.

### 8.3. TCP file transfer

Mỗi lần gửi file mở một kết nối TCP riêng, không dùng chung socket chat:

1. Gửi frame `HI` với `kind=file`.
2. Gửi frame `FILE_META` gồm tên file và kích thước byte, ví dụ `{"type":"FILE_META","name":"report.pdf","size":123456}`.
3. Gửi đúng `size` byte nội dung theo từng khối 64 KiB.
4. Bên nhận ghi vào `<tên>.part`, chỉ đổi tên thành file hoàn chỉnh khi nhận đủ; nếu kết nối đứt giữa chừng thì file `.part` bị xóa.

Phía nhận làm sạch tên file (chỉ giữ phần tên cuối, bỏ ký tự điều khiển và dấu phân cách đường dẫn, tối đa 200 ký tự) để tránh bị ghi ra ngoài thư mục `downloads/`, và thêm hậu tố `_1`, `_2`... nếu trùng tên với file đã có.

### 8.4. Giới hạn độ dài tin nhắn

Giới hạn `max_message_chars` được kiểm tra ở phía gửi, cả trên giao diện lẫn ở `LANChatApp.validate_message()`. `Config.validate()` đảm bảo giới hạn này luôn nhỏ hơn dung lượng tối đa của một frame, nên tin hợp lệ không bao giờ vượt giới hạn 1 MiB của giao thức.

## 9. Mô hình luồng

| Thread | Công việc |
| --- | --- |
| Main thread (Qt) | Vẽ giao diện, xử lý thao tác người dùng |
| UDP broadcaster | Gửi `HELLO` theo chu kỳ |
| UDP listener | Nhận `HELLO` và cập nhật bảng peer |
| Peer cleaner | Xóa peer hết hạn mỗi giây |
| TCP acceptor | Chờ kết nối đến |
| Incoming handler (mỗi kết nối) | Đọc `HI`, phân loại chat/file |
| Chat receiver × N | Nhận tin nhắn từ từng peer |
| File sender × N | Gửi file ở luồng riêng |
| File receiver × N | Nhận file từ kết nối riêng |

Các luồng nền gửi sự kiện lên giao diện qua tín hiệu của Qt (`pyqtSignal`), tránh thao tác widget trực tiếp từ luồng khác. Dữ liệu dùng chung (danh sách peer, sổ kết nối, lịch sử chat, bộ đếm chưa đọc) được bảo vệ bằng `threading.Lock`.

## 10. Kiểm thử thủ công

**Discovery**
1. Chạy ứng dụng trên hai máy, đợi 3–6 giây và kiểm tra cả hai thấy nhau.
2. Tắt hẳn một máy (hoặc ngắt mạng), sau hơn 10 giây người đó biến mất khỏi danh sách.

**Chat**
1. Mở chat từ A sang B, nhắn qua lại hai chiều.
2. Nếu có máy C: gửi tin từ B trong lúc A đang mở chat với C, kiểm tra số tin chưa đọc, rồi chuyển lại sang B.
3. Nhập tin dài hơn giới hạn, kiểm tra có cảnh báo, gửi bị chặn và nội dung vẫn còn trong ô nhập.

**File**
1. Gửi một file từ A sang B và theo dõi thanh tiến độ.
2. Kiểm tra file trong `downloads/` của B, so sánh checksum:

```bash
# Linux / macOS
sha256sum sample.pdf downloads/sample.pdf     # macOS: shasum -a 256 ...
# Windows (PowerShell)
Get-FileHash sample.pdf, downloads\sample.pdf -Algorithm SHA256
```

3. Gửi lại cùng một file, kiểm tra file mới có hậu tố `_1`.
4. Ngắt mạng giữa lúc đang gửi, kiểm tra không còn file `.part` dở dang phía nhận.

**Lỗi**
- Tắt peer giữa lúc chat: kết nối bị đóng và giao diện báo ngắt kết nối.
- Gửi dữ liệu không đúng định dạng tới TCP port: kết nối đó bị từ chối, ứng dụng vẫn chạy.

### Wireshark

Bắt gói trên card mạng Wi-Fi/Ethernet thật khi chạy hai máy.

| Mục tiêu | Display filter |
| --- | --- |
| UDP discovery | `udp.port == 9999` |
| TCP handshake | `tcp.port == 5000 && tcp.flags.syn == 1` |
| FIN/RST | `tcp.flags.fin == 1 \|\| tcp.flags.reset == 1` |
| Theo dõi luồng chat | Chọn gói → Follow → TCP Stream |

Header 4 byte của mỗi frame có thể hiện thành ký tự không in được khi xem raw stream. Đó là length prefix, không phải dữ liệu rác.

## 11. Xử lý sự cố

| Hiện tượng | Nguyên nhân thường gặp và cách xử lý |
| --- | --- |
| Không thấy peer nào | Tường lửa chặn UDP 9999; hai máy khác subnet; Wi-Fi bật client isolation; thử `--broadcast <địa chỉ subnet>`; trên Windows kiểm tra mạng đang ở hồ sơ Private; trên macOS kiểm tra quyền Local Network |
| Thấy peer nhưng không kết nối được | Tường lửa chặn TCP port của máy kia; nhập sai `--tcp-port`; máy kia chưa mở port |
| `Address already in use` | Port đã bị chương trình khác (hoặc bản khác của chính ứng dụng) chiếm; đổi `--tcp-port` hoặc `--udp-port` |
| `ModuleNotFoundError: PyQt6` hoặc `prompt_toolkit` | Chưa kích hoạt môi trường ảo hoặc chưa chạy `pip install -r requirements.txt` |
| `ImportError: attempted relative import` | Chạy trực tiếp file trong `lanchat/`; hãy chạy `python run.py` từ thư mục gốc |
| Lỗi plugin `xcb` trên Linux | Cài `libxcb-cursor0` (Debian/Ubuntu), hoặc đặt `QT_QPA_PLATFORM=wayland`/`xcb` |
| Font trông khác mẫu | Giao diện chọn font Calibri; nếu máy không có (Linux, macOS), Qt tự dùng font thay thế |
| File nhận không thấy | File nằm trong `downloads/` tính theo thư mục bạn chạy lệnh, hoặc thư mục đặt bằng `--downloads` |

## 12. Giới hạn đã biết và hướng phát triển

Đây là sản phẩm học tập, dùng trong mạng LAN tin cậy, **chưa an toàn để dùng trên mạng công cộng**.

**Bảo mật**
- Chưa có xác thực hay mã hóa (TLS): người cùng LAN có thể nghe lén, giả mạo gói `HELLO` hoặc kết nối giả danh.
- Tên peer không phải định danh bảo mật; `peer_id` dựa trên IP và TCP port.
- Phía nhận tự động lưu file mà không hỏi xác nhận, không giới hạn dung lượng và không kiểm tra nội dung.
- Giới hạn độ dài tin nhắn chỉ được kiểm tra ở phía gửi; phía nhận chỉ được bảo vệ bởi giới hạn 1 MiB của frame.
- Dấu "Đã xem" đi trong cùng kênh với tin nhắn bằng một chuỗi đánh dấu cố định, nên một peer cố ý gửi chuỗi đó có thể giả lập trạng thái "Đã xem".

**Chức năng**
- Một chuỗi ký tự rất dài **không có khoảng trắng** (hợp lệ về độ dài) vẫn được gửi và lưu đầy đủ, nhưng bong bóng chat không tự xuống dòng nên phần hiển thị bị tràn/cắt. Đây là lỗi hiển thị, không ảnh hưởng dữ liệu.
- Lịch sử chat chỉ lưu trong bộ nhớ, mất khi tắt ứng dụng.
- Chưa có resume khi truyền file, chưa có kiểm tra toàn vẹn (hash) sau khi nhận.
- Chỉ hỗ trợ IPv4; broadcast có thể bị router chặn.

**Hướng phát triển**
- TLS và xác thực peer; xác nhận trước khi nhận file; giới hạn dung lượng.
- Kiểm tra SHA-256 sau khi nhận file; resume truyền file.
- Lưu lịch sử chat bằng SQLite.
- Tự động ngắt dòng cho chuỗi dài liên tục.
- Kiểm thử tự động nhiều peer và kiểm thử tải.

## 13. Đối chiếu module và chức năng

| Chức năng | Module |
| --- | --- |
| UDP `HELLO` mỗi 3 giây, timeout 10 giây | `discovery.py`, `peer_manager.py` |
| TCP chat, nhiều peer | `tcp_server.py`, `connection_manager.py` |
| TCP framing | `protocol.py` |
| Tin chưa đọc, lịch sử chat | `chat_manager.py`, `app.py` |
| Gửi/nhận file trên socket riêng, tiến độ | `file_transfer.py` |
| Cấu hình và kiểm tra hợp lệ | `config.py` |
| Giao diện, cảnh báo tin quá dài | `ui.py`, `app.py` |
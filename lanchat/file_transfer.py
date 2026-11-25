# import file hệ thống
import socket
import threading
from pathlib import Path
# import file .py của dự án
from .protocol import recv_frame, send_frame
# hàm xử lí tên file được gửi đến
def safe_filename(name: str) -> str:
    """Không bao giờ tin tưởng path từ xa; chỉ giữ tên cuối cùng."""
    cleaned = Path(name.replace("\\", "/")).name # chuyển "\" -> "/", thống nhất giữa window và unix, lấy tên cuối cùng của path.
    cleaned = "".join(c for c in cleaned if c.isprintable() and c not in "/\\") # duyệt chuỗi cleaned, chỉ chọn kí tự in được và không phải "/" hay "\"
    return cleaned[:200] or "received_file" # trả ra 200 kí tự đầu tiên hoặc tên mặc định nếu chuỗi rỗng
# hàm xử lí khi file có tên trùng lặp
def unique_destination(directory: Path, filename: str) -> Path:
    destination = directory / filename # tạo đường dẫn đích
    if not destination.exists(): # nếu chưa có file trùng tên
        return destination
    stem, suffix = destination.stem, destination.suffix
    index = 1
    while True: # gán thêm index vào tên đến khi thỏa
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1
# hàm nhận và ghi file stream
def receive_file_stream(sock, metadata: dict, download_dir: Path, chunk_size: int, print_fn = print):
    name = safe_filename(str(metadata.get("name", "received_file")))
    size = metadata.get("size")
    if not isinstance(size, int) or size < 0: # kiểm tra size hợp lệ
        raise ValueError("Invalid file size.")
    download_dir.mkdir(parents= True, exist_ok= True) # chuẩn bị thư mục lưu file, tạo các thư mục cha còn thiếu, không báo lỗi nếu thư mục đã tồn tại
    destination = unique_destination(download_dir, name) # đường dẫn file đích
    partial = destination.with_name(destination.name + ".part") # .part báo file này chưa hoàn thiện
    received = 0
    try:
        with partial.open("wb") as output: # wb: ghi nhị phân
            while received < size: # bắt đầu nhận dữ liệu
                chunk = sock.recv(min(chunk_size, size - received))
                if not chunk:
                    raise ConnectionError("Connection lost during file transfer.")
                output.write(chunk)
                received += len(chunk)
        partial.replace(destination) # đặt lại tên file (bỏ .part) khi truyền xong
        print_fn(f"[FILE] Received {name} ({size} bytes) -> {destination}")
    except Exception:
        try:
            partial.unlink(missing_ok= True) # gặp lỗi -> xóa file .part, không báo lỗi nếu file không tồn tại
        except OSError: # bỏ qua nếu đang xóa thì lỗi hệ điều hành
            pass
        raise # trả lỗi cho tầng bên ngoài xử lí
# tạo lớp xử lí truyền file:
class FileTransfer:
    def __init__(self, config, local_ip: str, print_fn = print):
        self.config = config
        self.local_ip = local_ip
        self.print = print_fn
        self._threads = []
    # hàm yêu cầu gửi file
    def send(self, peer: dict, file_path: str):
        path = Path(file_path).expanduser() # trên linux, chuyển '~' thành đường dẫn thật
        if not path.is_file():
            self.print(f"[!] File not found: {path}")
            return False
        thread = threading.Thread(
            target= self._send_worker,
            args= (peer, path),
            name= f"file-send-{path.name}",
            daemon= True,
        ) # bàn giao việc cho _send_worker
        self._threads.append(thread)
        thread.start()
        return True
    # Hàm chịu trách nhiệm gửi file
    def _send_worker(self, peer, path: Path):
        size = path.stat().st_size # lấy kích thước file cần gửi
        sent = 0
        try:
            with socket.create_connection((peer["ip"], peer["tcp_port"]), timeout= 8) as sock:
                sock.settimeout(None)
                send_frame(sock, {
                    "type": "HI", 
                    "kind": "file",
                    "name": self.config.username,
                    "port": self.config.tcp_port,
                    "peer_id": f"{self.local_ip}:{self.config.tcp_port}"})
                send_frame(sock, {"type": "FILE_META", "name": path.name, "size": size})
                with path.open("rb") as source: # đọc file nhị phân
                    while True: # đọc 1 chunk rồi gửi đến khi xong
                        chunk = source.read(self.config.recv_chunk_size)
                        if not chunk:
                            break
                        sock.sendall(chunk)
                        sent += len(chunk)
                        percent = 100 if size == 0 else int(sent * 100 / size) # tiến độ gửi file
                        self.print(f"[FILE] Sending {path.name}: {percent}%")
                    self.print(f"[FILE] Sent {path.name} to {peer['name']} successfully.")
        except (OSError, ValueError) as exc:
            self.print(f"[FILE] Transfer to {peer['name']} failed: {exc}")
    # hàm chịu trách nhiệm nhận file
    def handle_incoming(self, sock, peer_info):
        try:
            metadata = recv_frame(sock, self.config.max_control_frame) # nhận FILE_META
            if metadata.get("type") != "FILE_META":
                raise ValueError("Expected FILE_META frame.")
            self.print(f"[FILE] Receiving {metadata.get('name', 'file')} from {peer_info['name']} ...")
            receive_file_stream(
                sock, metadata, Path(self.config.download_dir),
                self.config.recv_chunk_size, self.print) # nhận file
        except (OSError, ValueError) as exc:
            self.print(f"[FILE] Receive from {peer_info.get('name', 'unknown')} failed: {exc}")
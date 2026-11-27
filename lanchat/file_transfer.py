import socket
import threading
from pathlib import Path
from .protocol import recv_frame, send_frame

def safe_filename(name: str) -> str:
    """Không bao giờ tin tưởng path từ xa; chỉ giữ tên cuối cùng."""
    cleaned = Path(name.replace('\\', '/')).name
    cleaned = ''.join((c for c in cleaned if c.isprintable() and c not in '/\\'))
    return cleaned[:200] or 'received_file'

def unique_destination(directory: Path, filename: str) -> Path:
    """Tạo đường dẫn đích không trùng tên với tệp hiện có."""
    destination = directory / filename
    if not destination.exists():
        return destination
    stem, suffix = (destination.stem, destination.suffix)
    index = 1
    while True:
        candidate = directory / f'{stem}_{index}{suffix}'
        if not candidate.exists():
            return candidate
        index += 1

def receive_file_stream(sock, metadata: dict, download_dir: Path, chunk_size: int, print_fn=print) -> Path:
    """Nhận luồng byte của tệp và lưu vào thư mục đích."""
    name = safe_filename(str(metadata.get('name', 'received_file')))
    size = metadata.get('size')
    if not isinstance(size, int) or size < 0:
        raise ValueError('Invalid file size.')
    download_dir.mkdir(parents=True, exist_ok=True)
    destination = unique_destination(download_dir, name)
    partial = destination.with_name(destination.name + '.part')
    received = 0
    try:
        with partial.open('wb') as output:
            while received < size:
                chunk = sock.recv(min(chunk_size, size - received))
                if not chunk:
                    raise ConnectionError('Connection lost during file transfer.')
                output.write(chunk)
                received += len(chunk)
        partial.replace(destination)
        print_fn(f'[FILE] Received {name} ({size} bytes) -> {destination}')
        return destination
    except Exception:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        raise

class FileTransfer:

    def __init__(self, config, local_ip: str, print_fn=print, on_file_received=None):
        """Khởi tạo đối tượng và thiết lập các thuộc tính ban đầu."""
        self.config = config
        self.local_ip = local_ip
        self.print = print_fn
        self.on_file_received = on_file_received
        self._threads = []

    def send(self, peer: dict, file_path: str, on_progress=None, on_complete=None):
        """Khởi tạo luồng nền để gửi tệp đến peer."""
        path = Path(file_path).expanduser()
        if not path.is_file():
            self.print(f'[!] File not found: {path}')
            if on_complete:
                on_complete(False, f'Không tìm thấy file: {path}')
            return False
        thread = threading.Thread(target=self._send_worker, args=(peer, path, on_progress, on_complete), name=f'file-send-{path.name}', daemon=True)
        self._threads.append(thread)
        thread.start()
        return True

    def _send_worker(self, peer, path: Path, on_progress=None, on_complete=None):
        """Thực hiện gửi dữ liệu tệp qua kết nối TCP."""
        size = path.stat().st_size
        sent = 0
        last_percent = -1
        try:
            with socket.create_connection((peer['ip'], peer['tcp_port']), timeout=8) as sock:
                sock.settimeout(None)
                send_frame(sock, {'type': 'HI', 'kind': 'file', 'name': self.config.username, 'port': self.config.tcp_port, 'peer_id': f'{self.local_ip}:{self.config.tcp_port}'})
                send_frame(sock, {'type': 'FILE_META', 'name': path.name, 'size': size})
                if on_progress:
                    on_progress(0)
                with path.open('rb') as source:
                    while True:
                        chunk = source.read(self.config.recv_chunk_size)
                        if not chunk:
                            break
                        sock.sendall(chunk)
                        sent += len(chunk)
                        percent = 100 if size == 0 else int(sent * 100 / size)
                        if percent != last_percent:
                            last_percent = percent
                            self.print(f'[FILE] Sending {path.name}: {percent}%')
                            if on_progress:
                                on_progress(percent)
                    if on_progress and last_percent < 100:
                        on_progress(100)
                    self.print(f"[FILE] Sent {path.name} to {peer['name']} successfully.")
                    if on_complete:
                        on_complete(True, '')
        except (OSError, ValueError) as exc:
            self.print(f"[FILE] Transfer to {peer['name']} failed: {exc}")
            if on_complete:
                on_complete(False, str(exc))

    def handle_incoming(self, sock, peer_info):
        """Tiếp nhận metadata và xử lý luồng tệp từ peer gửi đến."""
        try:
            metadata = recv_frame(sock, self.config.max_control_frame)
            if metadata.get('type') != 'FILE_META':
                raise ValueError('Expected FILE_META frame.')
            self.print(f"[FILE] Receiving {metadata.get('name', 'file')} from {peer_info['name']} ...")
            saved_path = receive_file_stream(sock, metadata, Path(self.config.download_dir), self.config.recv_chunk_size, self.print)
            if self.on_file_received:
                self.on_file_received(peer_info, saved_path, metadata.get('size', 0))
        except (OSError, ValueError) as exc:
            self.print(f"[FILE] Receive from {peer_info.get('name', 'unknown')} failed: {exc}")

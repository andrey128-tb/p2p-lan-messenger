#inport file hệ thống
import socket
import threading
# Tạo lớp UDP discovery
class DiscoveryService:
    """UDP Broadcast theo cấu trúc: HELLO|name|tcp_port|status."""
    def __init__(self, config, peer_manager, local_ip, on_peer_event, print_fn = print):
        self.config = config
        self.peer_manager = peer_manager
        self.local_ip = local_ip
        self.on_peer_event = on_peer_event
        self.print = print_fn
        self.status = "online"
        self._status_lock = threading.Lock()
        self._stop = threading.Event()
        self._changed = threading.Event()
        self._threads = []
        self._listener_socket = None
    # Hàm khởi chạy service
    def start(self):
        broadcaster = threading.Thread(
            target= self._broadcast_loop,
            name= "udp-broadcaster",
            daemon= True
        )
        listener = threading.Thread(
            target= self._listen_loop,
            name= "udp-listener",
            daemon= True
        )
        cleaner = threading.Thread(
            target= self._clean_loop,
            name= "peer-cleaner",   
            daemon= True
        )
        self._threads = [broadcaster, listener, cleaner]
        for thread in self._threads:
            thread.start()
    # hàm thiết lập trạng thái
    def set_status(self, status: str):
        if status not in ("online", "away"):
            raise ValueError("Status must be online or away.")
        with self._status_lock:
            self.status = status
        self._changed.set()
    # hàm lấy trạng thái
    def get_status(self):
        with self._status_lock:
            return self.status
    # hàm dừng dịch vụ
    def stop(self):
        self._stop.set()
        self._changed.set()
        if self._listener_socket:
            try:
                self._listener_socket.close()
            except OSError:
                pass
    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP, IPv4
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            while not self._stop.is_set():
                status = self.get_status()
                payload = f"HELLO|{self.config.username}|{self.config.tcp_port}|{status}".encode("utf-8")
                try:
                    sock.sendto(payload, (self.config.broadcast_ip, self.config.udp_port))
                except OSError as exc:
                    self.print(f"[UDP] Broadcast error: {exc}")
                self._changed.wait(self.config.broadcast_interval) # đợi một lúc mới gửi tiếp
                self._changed.clear()
        finally:
            sock.close()
    # hàm xử lí chuỗi HELLO|name|tcp_port|status
    def _parse_hello(self, data: bytes):
        try:
            parts = data.decode("utf-8").split("|")
            if len(parts) != 4 or parts[0] != "HELLO":
                return None
            _, name, port_text, status = parts
            port = int(port_text)
            if not name.strip():
                return None
            if status not in ("online", "away"):
                return None
            if not 1024 <= port <= 49151:
                return None
            return name, port, status
        except ValueError:
            return None
    # hàm xử lí địa chỉ, cập nhật peer manager
    def _handle_hello(self, addr, data):
        parsed = self._parse_hello(data) # bàn giao việc cho _parse_hello làm
        if parsed is None:
            return
        name, port, status = parsed
        ip = addr[0]
        if self.peer_manager.is_self(ip, port, self.local_ip, self.config.tcp_port): # nếu nhận UDP BR từ chính nó thì bỏ qua
            return
        is_new = self.peer_manager.update(ip, port, name, status) # kiểm tra xem phải peer mới không
        self.on_peer_event(
            "online" if is_new else "update",
            {
                "ip": ip,
                "tcp_port": port,
                "name": name,
                "status": status,
            },
        )
    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._listener_socket = sock
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", self.config.udp_port))
            sock.settimeout(1.0)
            self.print(f"[*] UDP discovery listening on port {self.config.udp_port}")
            while not self._stop.is_set():
                try:
                    data, addr = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                except OSError:
                    break
                self._handle_hello(addr, data) # bàn giao việc cho _handle_hello làm
        except OSError as exc:
            if not self._stop.is_set():
                self.print(f"[UDP] Listener error: {exc}")
        finally:
            sock.close()
    def _clean_loop(self):
            while not self._stop.wait(1.0):
                for peer in self.peer_manager.remove_expired(self.config.peer_timeout):
                    self.on_peer_event("offline", peer)
import socket
import threading
from .protocol import send_frame, recv_frame

class PeerConnection:
    """Quản lí 1 kết nối TCP hai chiều."""

    def __init__(self, sock, peer: dict, initiator_id: str, on_message, on_closed):
        """Khởi tạo đối tượng và thiết lập các thuộc tính ban đầu."""
        self.sock = sock
        self.peer = peer
        self.key = (peer['ip'], int(peer['tcp_port']))
        self.initiator_id = initiator_id
        self._on_message = on_message
        self._on_closed = on_closed
        self._send_lock = threading.Lock()
        self._closed = threading.Event()
        self._thread = None

    def start(self):
        """Khởi động các dịch vụ mạng và chuẩn bị ứng dụng."""
        self._thread = threading.Thread(target=self._receive_loop, name=f"receiver-{self.peer['name']}", daemon=True)
        self._thread.start()

    def send_message(self, message: str):
        """Mô tả chức năng của hàm send_message."""
        if self._closed.is_set():
            raise ConnectionError('Chat connection is closed.')
        send_frame(self.sock, {'type': 'MSG', 'text': message}, self._send_lock)

    def close(self, send_bye: bool=False):
        """Mô tả chức năng của hàm close."""
        if self._closed.is_set():
            return
        if send_bye:
            try:
                send_frame(self.sock, {'type': 'BYE'}, self._send_lock)
            except OSError:
                pass
        self._closed.set()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def _receive_loop(self):
        """Mô tả chức năng của hàm _receive_loop."""
        reason = 'connection closed'
        try:
            while not self._closed.is_set():
                frame = recv_frame(self.sock)
                kind = frame.get('type')
                if kind == 'MSG':
                    text = frame.get('text')
                    if isinstance(text, str):
                        self._on_message(self, text)
                elif kind == 'BYE':
                    reason = 'peer left the chat'
                    break
                else:
                    reason = f'unexpected frame: {kind!r}'
                    break
        except (OSError, ValueError) as exc:
            reason = str(exc) or 'connection lost'
        finally:
            was_closed = self._closed.is_set()
            self.close()
            self._on_closed(self, reason, was_closed)

class ConnectionManager:
    """Đăng kí và quản lí các kết nối, luồng an toàn."""

    def __init__(self):
        """Khởi tạo đối tượng và thiết lập các thuộc tính ban đầu."""
        self._connections = {}
        self._lock = threading.Lock()

    def get(self, peer_key):
        """Lấy kết nối TCP tương ứng với khóa peer."""
        with self._lock:
            return self._connections.get(peer_key)

    def register(self, connection: PeerConnection) -> bool:
        """Đăng ký kết nối mới và xử lý trường hợp kết nối trùng lặp."""
        old = None
        with self._lock:
            old = self._connections.get(connection.key)
            if old is None:
                self._connections[connection.key] = connection
                return True
            if connection.initiator_id < old.initiator_id:
                self._connections[connection.key] = connection
                accepted = True
            else:
                accepted = False
        if accepted:
            old.close()
        else:
            connection.close()
        return accepted

    def remove(self, connection):
        """Xóa kết nối khỏi danh sách nếu đúng đối tượng được quản lý."""
        with self._lock:
            if self._connections.get(connection.key) is connection:
                self._connections.pop(connection.key, None)
                return True
        return False

    def all(self):
        """Trả về danh sách các kết nối hiện tại."""
        with self._lock:
            return list(self._connections.values())

    def close_all(self):
        """Đóng toàn bộ các kết nối đang được quản lý."""
        for connection in self.all():
            connection.close(send_bye=True)

#import file hệ thống
import socket
import threading
#import file .py của dự án
from .protocol import send_frame, recv_frame
# tạo lớp quản lí 1 kết nối TCP hai chiều
class PeerConnection:
    """Quản lí 1 kết nối TCP hai chiều."""
    def __init__(self, sock, peer: dict, initiator_id: str, on_message, on_closed):
        self.sock = sock
        self.peer = peer
        self.key = (peer["ip"], int(peer["tcp_port"]))
        self.initiator_id = initiator_id
        self._on_message = on_message
        self._on_closed = on_closed
        self._send_lock = threading.Lock()
        self._closed = threading.Event()
        self._thread = None
    # hàm tạo một thread mới nhận dữ liệu
    def start(self):
        self._thread = threading.Thread(
            target= self._receive_loop,
            name= f"receiver-{self.peer['name']}",
            daemon= True,
        )
        self._thread.start()
    # hàm gửi message
    def send_message(self, message: str):
        if self._closed.is_set():
            raise ConnectionError("Chat connection is closed.")
        send_frame(self.sock, {"type": "MSG", "text": message}, self._send_lock)
    # hàm đóng kết nối
    def close(self, send_bye: bool = False):
        if self._closed.is_set(): # nếu nhận cờ đóng thì quay lại
            return
        if send_bye: # nếu nhận cờ chào tạm biệt
            try:
                send_frame(self.sock, {"type": "BYE"}, self._send_lock)
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
    # hàm nhận tin nhắn
    def _receive_loop(self):
        reason = "connection closed"
        try:
            while not self._closed.is_set():
                frame = recv_frame(self.sock)
                kind = frame.get("type")
                if kind == "MSG":
                    text = frame.get("text")
                    if isinstance(text, str):
                        self._on_message(self, text)
                elif kind == "BYE":
                    reason = "peer left the chat"
                    break
                else:
                    reason = f"unexpected frame: {kind!r}" # !r: thêm dấu nháy cho chuỗi
                    break
        except (OSError, ValueError) as exc:
            reason = str(exc) or "connection lost"
        finally:
            was_closed = self._closed.is_set()
            self.close()
            self._on_closed(self, reason, was_closed)
# tạo lớp quản lí các kết nối
class ConnectionManager:
    """Đăng kí và quản lí các kết nối, luồng an toàn."""
    def __init__(self):
        self._connections = {} # danh sách các kết nối
        self._lock = threading.Lock()
    # hàm tìm kết nối tcp theo địa chỉ của peer
    def get(self, peer_key):
        with self._lock:
            return self._connections.get(peer_key)
    # hàm đăng kí kết nối mới
    def register(self, connection: PeerConnection) -> bool:
        old = None
        with self._lock:
            old = self._connections.get(connection.key) # tìm xem đã có kết nối đó chưa
            if old is None:
                self._connections[connection.key] = connection # chưa có thì thêm
                return True
            # nếu đã có kết nối, so sánh initiator id theo thứ tự từ điển
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
    # hàm xóa kết nối
    def remove(self, connection):
        with self._lock:
            if self._connections.get(connection.key) is connection:
                self._connections.pop(connection.key, None)
                return True
        return False
    # hàm trả về danh sách các peer connection
    def all(self):
        with self._lock:
            return list(self._connections.values())
    # hàm đóng tất cả các kết nối
    def close_all(self):
        for connection in self.all():
            connection.close(send_bye= True)

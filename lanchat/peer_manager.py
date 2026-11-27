import threading
import time

class PeerManager:
    """Quản lí các peer tìm thấy qua UDP."""

    def __init__(self):
        """Khởi tạo đối tượng và thiết lập các thuộc tính ban đầu."""
        self._peers = {}
        self._lock = threading.Lock()

    def update(self, ip: str, tcp_port: int, name: str, status: str) -> bool:
        """Thêm peer mới hoặc cập nhật thông tin của peer đã tồn tại."""
        key = (ip, tcp_port)
        now = time.monotonic()
        with self._lock:
            is_new = key not in self._peers
            self._peers[key] = {'ip': ip, 'tcp_port': tcp_port, 'name': name, 'status': status, 'last_seen': now}
        return is_new

    def remove_expired(self, timeout: float):
        """Loại bỏ và trả về các peer đã quá thời gian chờ."""
        now = time.monotonic()
        expired = []
        with self._lock:
            for key, peer in list(self._peers.items()):
                if now - peer['last_seen'] > timeout:
                    expired.append(self._peers.pop(key))
            return expired

    def snapshot(self):
        """Trả về bản sao danh sách peer hiện tại."""
        with self._lock:
            return [dict(peer) for peer in self._peers.values()]

    def find(self, query: str):
        """Tìm peer theo số thứ tự hoặc tên hiển thị."""
        peers = sorted(self.snapshot(), key=lambda p: (p['name'].casefold(), p['ip'], p['tcp_port']))
        if query.isascii() and query.isdecimal():
            index = int(query) - 1
            return peers[index] if 0 <= index < len(peers) else None
        matches = [p for p in peers if p['name'].casefold() == query.casefold()]
        return matches[0] if len(matches) == 1 else None

    def is_self(self, ip: str, tcp_port: int, local_ip: str, local_port: int) -> bool:
        """Kiểm tra địa chỉ peer có trùng với máy hiện tại hay không."""
        return ip == local_ip and tcp_port == local_port

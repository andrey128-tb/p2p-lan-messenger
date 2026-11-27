import threading
from collections import defaultdict

class ChatManager:
    """Lưu lịch sử tin nhắn và đếm số tin nhắn chưa đọc của từng peer."""

    def __init__(self):
        """Khởi tạo đối tượng và thiết lập các thuộc tính ban đầu."""
        self._history = defaultdict(list)
        self._unread = defaultdict(int)
        self._lock = threading.Lock()

    def add(self, peer_key, direction: str, text: str, unread: bool=False):
        """Thêm tin nhắn vào lịch sử và cập nhật bộ đếm chưa đọc."""
        with self._lock:
            self._history[peer_key].append((direction, text))
            if unread:
                self._unread[peer_key] += 1

    def history(self, peer_key):
        """Lấy bản sao lịch sử hội thoại của một peer."""
        with self._lock:
            return list(self._history[peer_key])

    def unread_count(self, peer_key) -> int:
        """Trả về số tin nhắn chưa đọc của một peer."""
        with self._lock:
            return self._unread[peer_key]

    def clear_unread(self, peer_key) -> int:
        """Đánh dấu toàn bộ tin nhắn của peer là đã đọc và trả về số lượng."""
        with self._lock:
            count = self._unread[peer_key]
            self._unread[peer_key] = 0
            return count

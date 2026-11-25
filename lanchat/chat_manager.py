#import file hệ thống
import threading
from collections import defaultdict # tự tạo giá trị mặc định nếu như key chưa có
# tạo lớp quản lí tin nhắn
class ChatManager:
    """Lưu lịch sử tin nhắn và đếm số tin nhắn chưa đọc của từng peer."""
    def __init__(self):
        self._history = defaultdict(list)
        self._unread = defaultdict(int)
        self._lock = threading.Lock()
    # hàm thêm tin đã nhắn vào lịch sử
    def add(self, peer_key, direction: str, text: str, unread: bool = False):
        with self._lock:
            self._history[peer_key].append((direction, text)) # thêm vào lịch sử chat
            if unread:
                self._unread[peer_key] += 1 # chưa đọc thì tăng lên
    # hàm lấy lịch sử chat
    def history(self, peer_key):
        with self._lock:
            return list(self._history[peer_key])
    # hàm đếm số tin nhắn chưa đọc
    def unread_count(self, peer_key) -> int:
        with self._lock:
            return self._unread[peer_key]
    # hàm đánh dấu đã đọc toàn bộ tin nhắn
    def clear_unread(self, peer_key) -> int:
        with self._lock:
            count = self._unread[peer_key]
            self._unread[peer_key] = 0
            return count


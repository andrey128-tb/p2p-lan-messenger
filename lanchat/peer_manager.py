# import file hệ thống
import threading
import time
# tạo lớp quản lí peer
class PeerManager:
    """Quản lí các peer tìm thấy qua UDP."""
    def __init__(self):
        self._peers = {} # danh sách các peer đã đăng kí
        self._lock = threading.Lock() # có khóa luồng, chỉ cho phép 1 luồng cùng tiến trình chạy trong 1 thời điểm
    # hàm cập nhật danh sách các peer
    def update(self, ip: str, tcp_port: int, name: str, status: str) -> bool:
        key = (ip, tcp_port)
        now = time.monotonic()
        with self._lock:
            is_new = key not in self._peers
            # không có trong ds peer thì thêm vào
            # nếu đã có trong danh sách thì cập nhật lại các giá trị
            self._peers[key] = {
                "ip": ip,
                "tcp_port": tcp_port,
                "name":  name,
                "status": status,
                "last_seen": now,
            }
        return is_new
    # hàm loại bỏ những peer hết hạn khỏi ds
    def remove_expired(self, timeout: float):
        now = time.monotonic()
        expired = []
        with self._lock:
            for key, peer in list(self._peers.items()):
                if now - peer["last_seen"] > timeout:
                    expired.append(self._peers.pop(key))
            return expired
    # hàm hiển thị thông tin peer
    def snapshot(self):
        with self._lock:
            return [dict(peer) for peer in self._peers.values()]
    # hàm tìm kiếm (theo số thứ tự và tên peer)
    def find(self, query: str):
        peers = sorted(self.snapshot(), key= lambda p: (
            p["name"].casefold(), # ưu tiên 1: sort theo tên không phân biệt chữ hoa, thg
            p["ip"], # ưu tiên 2: sort theo ip
            p["tcp_port"] # ưu tiên 3: sort theo tcp port
        ))
        if query.isdigit(): # nếu chuỗi là số (tìm theo id)
            index = int(query) - 1
            return peers[index] if 0 <= index < len(peers) else None
        matches = [p for p in peers if p["name"].casefold() == query.casefold()] # tìm các tên tương ứng với query
        return matches[0] if len(matches) == 1 else None # không trả về nếu tìm thấy nhiều peer cùng tên
    # hàm kiểm tra xem một peer có là chính máy hiện tại không
    def is_self(self, ip: str, tcp_port: int, local_ip: str, local_port: int) -> bool:
        return ip == local_ip and tcp_port == local_port
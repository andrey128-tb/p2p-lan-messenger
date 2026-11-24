# Quản lý danh sách Peer trong mạng LAN và trạng thái người dùng hiện tại

import threading
import time
from dataclasses import dataclass

from lanchat.config import PEER_TIMEOUT, VALID_STATUSES


@dataclass
class PeerInfo:
    name: str
    ip: str
    tcp_port: int
    status: str
    last_seen: float


class PeerManager:
    # Quản lý trạng thái bản thân và bảng danh sách các Peer đang hoạt động.
    def __init__(self, my_name: str, my_tcp_port: int):
        self.my_name = my_name
        self.my_tcp_port = my_tcp_port
        self.status = "online"
        self.running = True
        self._peers: dict[str, PeerInfo] = {}
        self._lock = threading.Lock()

    def set_status(self, new_status: str) -> bool:
        # Cập nhật trạng thái của bản thân ('online' hoặc 'away').
        if new_status not in VALID_STATUSES:
            return False
        with self._lock:
            self.status = new_status
        return True

    def get_status(self) -> str:
        # Lấy trạng thái hiện tại của bản thân.
        with self._lock:
            return self.status

    def update_peer(self, name: str, ip: str, tcp_port: int, status: str) -> bool:
        # Thêm Peer mới hoặc cập nhật thông tin Peer đã tồn tại. Trả về True nếu là Peer mới.
        now = time.time()
        with self._lock:
            is_new = name not in self._peers
            self._peers[name] = PeerInfo(
                name=name,
                ip=ip,
                tcp_port=tcp_port,
                status=status,
                last_seen=now,
            )
            return is_new

    def remove_timed_out_peers(self, timeout: float = PEER_TIMEOUT) -> list[PeerInfo]:
        # Xóa và trả về danh sách các Peer quá thời gian timeout không gửi tín hiệu.
        now = time.time()
        removed_peers: list[PeerInfo] = []
        with self._lock:
            expired_names = [
                name for name, peer in self._peers.items()
                if now - peer.last_seen > timeout
            ]
            for name in expired_names:
                removed_peers.append(self._peers.pop(name))
        return removed_peers

    def get_all_peers(self) -> list[PeerInfo]:
        # Trả về bản sao danh sách tất cả Peer đang online.
        with self._lock:
            return list(self._peers.values())

    def get_peer(self, identifier: str) -> PeerInfo | None:
        # Tìm Peer theo tên hoặc số thứ tự (bắt đầu từ 1) hiển thị trong /list.
        with self._lock:
            if identifier in self._peers:
                return self._peers[identifier]
            if identifier.isdigit():
                index = int(identifier) - 1
                peers_list = list(self._peers.values())
                if 0 <= index < len(peers_list):
                    return peers_list[index]
        return None
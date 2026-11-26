# import file hệ thống
from dataclasses import dataclass
#khởi tạo dữ liệu cố định
@dataclass(frozen= True)
class Config:
    username: str
    host: str = "0.0.0.0" # lắng nghe trên tất cả IPv4 interfaces
    tcp_port: int = 5000
    udp_port: int = 9999
    broadcast_ip: str = "255.255.255.255"
    broadcast_interval: float = 3.0 # thời gian giữa mỗi lần gửi broadcast
    peer_timeout: float = 10.0 # thời gian chờ trước khi báo peer mất kết nối
    download_dir: str = "downloads"
    recv_chunk_size: int = 64 * 1024 # 64 KiB, dữ liệu chương trình đọc mỗi lần nhận
    max_control_frame: int = 1024 * 1024 # 1 MiB, kích thước tối đa 1 control frame
    max_message_chars: int = 4096  # số ký tự tối đa của 1 tin nhắn chat
    def validate(self) -> None: 
        """Kiểm tra tính hợp lệ của dữ liệu."""
        name = self.username.strip() # bỏ khoảng trắng đầu và cuối chuỗi
        if not name:
            raise ValueError("Username cannot be empty.")
        if "|" in name: # tên không được chứa khi tự chia trong frame
            raise ValueError("Username cannot contain '|'.")
        if not 1024 <= self.tcp_port <= 49151:
            raise ValueError("TCP port must be between 1 and 65535.")
        if not 1024 <= self.udp_port <= 49151:
            raise ValueError("UDP port must be between 1 and 65535.")
        if self.broadcast_interval <= 0:
            raise ValueError("Broadcast interval must be positive.")
        if self.peer_timeout <= 0:
            raise ValueError("Peer timeout must be positive.")
        if self.recv_chunk_size <= 0:
            raise ValueError("Receive chunk size must be positive.")
        if self.max_control_frame <= 0:
            raise ValueError("Max control frame must be positive.")
        if self.max_message_chars <= 0:
            raise ValueError("Max message chars must be positive.")
        # Trường hợp xấu nhất mỗi ký tự chiếm ~6 byte trong JSON (ký tự điều khiển -> \uXXXX),
        # cộng thêm phần overhead của frame; tổng phải còn nằm trong giới hạn frame.
        if self.max_message_chars * 6 + 256 > self.max_control_frame:
            raise ValueError("max_message_chars is too large for max_control_frame.")
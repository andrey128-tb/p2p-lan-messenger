# Cấu hình hằng số dùng chung cho ứng dụng LAN Chat & File Sharing

UDP_PORT = 9999
BROADCAST_ADDR = "255.255.255.255"
BROADCAST_INTERVAL = 3.0  # Chu kỳ gửi gói HELLO (giây)
PEER_TIMEOUT = 10.0       # Thời gian chờ tối đa trước khi xóa peer offline (giây)

DEFAULT_TCP_PORT = 5000
BUFFER_SIZE = 4096
ENCODING = "utf-8"

VALID_STATUSES = ("online", "away")
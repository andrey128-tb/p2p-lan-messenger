# Định nghĩa giao thức đóng gói và phân tích bản tin mạng

from lanchat.config import ENCODING, VALID_STATUSES


def build_hello(name: str, tcp_port: int, status: str) -> bytes:
    # Đóng gói bản tin HELLO|<name>|<tcp_port>|<status> thành bytes.
    clean_name = name.replace("|", "_").strip()
    clean_status = status if status in VALID_STATUSES else "online"
    packet_str = f"HELLO|{clean_name}|{tcp_port}|{clean_status}"
    return packet_str.encode(ENCODING)


def parse_hello(data: bytes) -> tuple[str, int, str] | None:
    # Phân tích gói tin UDP nhận được. Trả về (name, tcp_port, status) hoặc None.
    try:
        text = data.decode(ENCODING).strip()
        parts = text.split("|")
        if len(parts) != 4 or parts[0] != "HELLO":
            return None

        name = parts[1].strip()
        tcp_port = int(parts[2])
        status = parts[3].strip()

        if not name or not (1 <= tcp_port <= 65535) or status not in VALID_STATUSES:
            return None

        return name, tcp_port, status
    except (UnicodeDecodeError, ValueError):
        return None
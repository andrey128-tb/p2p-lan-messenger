"""Dùng lenght-prefixed JSON frame cho quản lí tin nhắn TCP.
Do TCP là gửi theo luồng byte, hàm revc() không đảm bảo tương ứng với toàn bộ một tin nhắn.
Hướng giải quyết là dùng control frame: 
    4 byte đầu: độ dài frame - là số nguyên không dấu, quy ước biểu diễn theo big-endian chuẩn giao tiếp mạng.
    n byte sau: dữ liệu cấu trúc JSON mã hóa UTF-8.
Đối với dữ liệu file, được gửi trực tiếp (raw) mà không chuyển thành JSON, chỉ được gửi sau khi nhận FILE_META frame thông báo size.
"""
# import file hệ thống
import json # chuyển đổi python dict <=> JSON
import struct # đóng gói và giải mã dữ liệu nhị phân theo cấu trúc xác định
from typing import Any

_HEADER = struct.Struct("!I") # Khai báo header, !:big-endian, I: unsigned int 4 byte

# class exception cho giao thức của dự án
class ProtocolError(ValueError):
    """Raised when a peer sends an invalid or oversized frame."""
# hàm nhận chính xác số bytes
def recv_exact(sock, size: int) -> bytes:
    """Read exactly size bytes, or raise ConnectionError if the peer closes."""
    chunks = bytearray() # tạo vùng dữ liệu dạng byte có thể thay đổi (mở rộng được).
    while len(chunks) < size: # đọc đến khi nhận đủ byte
        chunk = sock.recv(size - len(chunks)) # 1 chunk nhận tối đa số byte còn phải nhận
        if not chunk:
            raise ConnectionError("Peer closed the connection")
        chunks.extend(chunk) 
    return bytes(chunks)
# hàm gửi frame
def send_frame(sock, payload: dict[str, Any], lock = None):
    """Đóng gói dict <=> JSON và gửi 1 frame."""
    body = json.dumps(payload, ensure_ascii= False, separators= (",", ":")).encode("utf-8")
    packet = _HEADER.pack(len(body)) + body # tạo packet gồm header và body
    if lock is None:
        sock.sendall(packet)
    else: # nếu có lock, mỗi thời điểm chỉ có 1 thread gửi (cùng socket)
        with lock:
            sock.sendall(packet)
# hàm nhận frame, giới hạn frame khoảng 1 MiB (1024 byte * 1024 byte)
def recv_frame(sock, max_size: int = 1024 * 1024) -> dict[str, Any]:
    """Nhận và giải mã JSON frame."""
    header = recv_exact(sock, _HEADER.size) # nhận và giải mã header
    (length,) = _HEADER.unpack(header)
    if length == 0 or length > max_size:
        raise ProtocolError(f"Invalid control frame length: {length}")
    body = recv_exact(sock, length) # nhận và giải mã body
    try: 
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError): # xử lí lỗi khi mã hóa không phải UTF-8 hoặc không phải định dạng JSON
        raise ProtocolError("Invalid UTF-8 JSON frame.")
    if not isinstance(value, dict): # kiểm tra xem value phải là JSON object (thuộc dạng python dict)
        raise ProtocolError("A control frame must be a JSON object.")
    return value
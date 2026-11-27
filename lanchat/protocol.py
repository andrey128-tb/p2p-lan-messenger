"""Dùng lenght-prefixed JSON frame cho quản lí tin nhắn TCP.
Do TCP là gửi theo luồng byte, hàm revc() không đảm bảo tương ứng với toàn bộ một tin nhắn.
Hướng giải quyết là dùng control frame: 
    4 byte đầu: độ dài frame - là số nguyên không dấu, quy ước biểu diễn theo big-endian chuẩn giao tiếp mạng.
    n byte sau: dữ liệu cấu trúc JSON mã hóa UTF-8.
Đối với dữ liệu file, được gửi trực tiếp (raw) mà không chuyển thành JSON, chỉ được gửi sau khi nhận FILE_META frame thông báo size.
"""
import json
import struct
from typing import Any
_HEADER = struct.Struct('!I')

class ProtocolError(ValueError):
    """Raised when a peer sends an invalid or oversized frame."""

def recv_exact(sock, size: int) -> bytes:
    """Read exactly size bytes, or raise ConnectionError if the peer closes."""
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError('Peer closed the connection')
        chunks.extend(chunk)
    return bytes(chunks)

def send_frame(sock, payload: dict[str, Any], lock=None):
    """Đóng gói dict <=> JSON và gửi 1 frame."""
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    packet = _HEADER.pack(len(body)) + body
    if lock is None:
        sock.sendall(packet)
    else:
        with lock:
            sock.sendall(packet)

def recv_frame(sock, max_size: int=1024 * 1024) -> dict[str, Any]:
    """Nhận và giải mã JSON frame."""
    header = recv_exact(sock, _HEADER.size)
    length, = _HEADER.unpack(header)
    if length == 0 or length > max_size:
        raise ProtocolError(f'Invalid control frame length: {length}')
    body = recv_exact(sock, length)
    try:
        value = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProtocolError('Invalid UTF-8 JSON frame.')
    if not isinstance(value, dict):
        raise ProtocolError('A control frame must be a JSON object.')
    return value

# Module khám phá thiết bị trong mạng LAN qua giao thức UDP Broadcast

import socket
import threading
from typing import Callable

from lanchat.config import BROADCAST_ADDR, BROADCAST_INTERVAL, BUFFER_SIZE, UDP_PORT
from lanchat.peer_manager import PeerManager
from lanchat.protocol import build_hello, parse_hello


class UDPDiscovery:
    # Điều phối luồng gửi Broadcast định kỳ và luồng lắng nghe gói tin HELLO.
    def __init__(
        self,
        peer_manager: PeerManager,
        udp_port: int = UDP_PORT,
        on_notify: Callable[[str], None] | None = None,
    ):
        self.peer_manager = peer_manager
        self.udp_port = udp_port
        self.on_notify = on_notify or print
        self._wake_event = threading.Event()

    def start(self) -> None:
        # Khởi chạy đồng thời 2 luồng Broadcaster và Listener.
        broadcaster_thread = threading.Thread(
            target=self._broadcaster_loop,
            name="UDPBroadcaster",
            daemon=True,
        )
        listener_thread = threading.Thread(
            target=self._listener_loop,
            name="UDPListener",
            daemon=True,
        )
        broadcaster_thread.start()
        listener_thread.start()

    def trigger_broadcast_now(self) -> None:
        """Đánh thức luồng Broadcaster gửi gói HELLO ngay lập tức khi đổi trạng thái."""
        self._wake_event.set()

    def stop(self) -> None:
        """Dừng hoạt động khám phá mạng."""
        self.peer_manager.running = False
        self._wake_event.set()

    def _broadcaster_loop(self) -> None:
        """Gửi gói HELLO định kỳ mỗi 3 giây tới địa chỉ Broadcast."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            while self.peer_manager.running:
                pkt = build_hello(
                    self.peer_manager.my_name,
                    self.peer_manager.my_tcp_port,
                    self.peer_manager.get_status(),
                )
                try:
                    sock.sendto(pkt, (BROADCAST_ADDR, self.udp_port))
                except OSError:
                    pass

                # Chờ 3 giây hoặc thức dậy ngay nếu có lệnh đổi /status
                self._wake_event.wait(BROADCAST_INTERVAL)
                self._wake_event.clear()
        finally:
            sock.close()

    def _listener_loop(self) -> None:
        """Lắng nghe gói HELLO từ các máy khác và dọn dẹp Peer quá hạn 10 giây."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass

        sock.bind(("0.0.0.0", self.udp_port))
        sock.settimeout(1.0)  # Định kỳ 1 giây thức dậy để kiểm tra timeout

        try:
            while self.peer_manager.running:
                try:
                    data, addr = sock.recvfrom(BUFFER_SIZE)
                    parsed = parse_hello(data)
                    if parsed is not None:
                        name, tcp_port, status = parsed
                        # Bỏ qua gói tin do chính mình phát ra
                        if (
                            name == self.peer_manager.my_name
                            and tcp_port == self.peer_manager.my_tcp_port
                        ):
                            continue

                        sender_ip = addr[0]
                        is_new = self.peer_manager.update_peer(
                            name, sender_ip, tcp_port, status
                        )
                        if is_new:
                            self.on_notify(
                                f"\n[*] {name} is online ({sender_ip}:{tcp_port})"
                            )
                except socket.timeout:
                    pass
                except OSError:
                    break

                # Kiểm tra và xóa các Peer im lặng quá 10 giây
                offline_peers = self.peer_manager.remove_timed_out_peers()
                for peer in offline_peers:
                    self.on_notify(f"\n[*] {peer.name} is offline")
        finally:
            sock.close()
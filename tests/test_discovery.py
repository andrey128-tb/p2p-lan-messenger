# Kiểm thử độc lập chức năng UDP Discovery, /list và /status

from lanchat.discovery import UDPDiscovery
from lanchat.peer_manager import PeerManager


def run_test() -> None:
    my_name = input("Nhập tên người dùng của bạn: ").strip() or "User"
    port_input = input("Nhập cổng TCP giả lập (vd 5000): ").strip()
    my_tcp_port = int(port_input) if port_input.isdigit() else 5000

    peer_manager = PeerManager(my_name=my_name, my_tcp_port=my_tcp_port)
    discovery = UDPDiscovery(peer_manager=peer_manager)
    discovery.start()

    print(f"[*] Đang chạy UDP Discovery cho '{my_name}' (TCP {my_tcp_port})...")
    print("[*] Lệnh hỗ trợ: /list | /status online | /status away | /quit")

    try:
        while True:
            cmd = input("> ").strip()
            if cmd == "/list":
                peers = peer_manager.get_all_peers()
                if not peers:
                    print("Chưa tìm thấy thiết bị nào khác trong mạng LAN.")
                else:
                    print("Danh sách thiết bị đang hoạt động:")
                    for idx, peer in enumerate(peers, start=1):
                        print(f"  {idx}. {peer.name} - {peer.ip}:{peer.tcp_port} [{peer.status}]")
            elif cmd.startswith("/status "):
                new_status = cmd.split(maxsplit=1)[1].strip()
                if peer_manager.set_status(new_status):
                    discovery.trigger_broadcast_now()
                    print(f"[*] Đã đổi trạng thái sang '{new_status}' và phát UDP ngay.")
                else:
                    print("[!] Trạng thái chỉ nhận 'online' hoặc 'away'.")
            elif cmd == "/quit":
                break
    finally:
        discovery.stop()
        print("[*] Đã dừng UDP Discovery.")


if __name__ == "__main__":
    run_test()
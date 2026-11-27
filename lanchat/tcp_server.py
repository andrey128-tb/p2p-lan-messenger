import socket
import threading
from .connection_manager import PeerConnection
from .file_transfer import FileTransfer
from .protocol import recv_frame

class TCPServer:
    """Accepts incoming chat and file TCP connections."""

    def __init__(self, config, local_ip, connection_manager, on_message, on_close, print_fn=print, on_file_received=None):
        """Constructor."""
        self.config = config
        self.local_ip = local_ip
        self.connections = connection_manager
        self.on_message = on_message
        self.on_closed = on_close
        self.print = print_fn
        self.file_transfer = FileTransfer(config, local_ip, print_fn, on_file_received=on_file_received)
        self._server = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        """Start TCP Server."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.config.host, self.config.tcp_port))
        server.listen(32)
        server.settimeout(1.0)
        self._server = server
        self._thread = threading.Thread(target=self._accept_loop, name='tcp-acceptor', daemon=True)
        self._thread.start()
        self.print(f'[*] TCP Server listening on {self.config.host}:{self.config.tcp_port}')

    def stop(self):
        """Stop TCP Server"""
        self._stop.set()
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass

    def _accept_loop(self):
        """Accept connections until receive STOP flag."""
        while not self._stop.is_set():
            try:
                sock, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_new_connection, args=(sock, addr), name=f'tcp-incoming-{addr[0]}', daemon=True).start()

    def _handle_new_connection(self, sock, addr):
        """Handle new connection."""
        handed_off = False
        try:
            sock.settimeout(8.0)
            hello = recv_frame(sock, self.config.max_control_frame)
            if hello.get('type') != 'HI':
                raise ValueError('First frame must be HI.')
            name = str(hello.get('name', 'Unknown'))[:64]
            port = int(hello.get('port', 0))
            kind = hello.get('kind')
            peer = {'name': name, 'ip': addr[0], 'tcp_port': port, 'status': 'online', 'peer_id': str(hello.get('peer_id', f'{addr[0]}'))}
            if not 1024 <= port <= 49151:
                raise ValueError('Invalid peer TCP port.')
            if kind == 'file':
                sock.settimeout(300.0)
                self.file_transfer.handle_incoming(sock, peer)
                return
            if kind != 'chat':
                raise ValueError('Unknown connection kind.')
            sock.settimeout(None)
            connection = PeerConnection(sock, peer, peer['peer_id'], self.on_message, self.on_closed)
            if self.connections.register(connection):
                handed_off = True
                self.print(f'[*] Chat connection from {name} ({addr[0]}:{port})')
                connection.start()
        except (OSError, ValueError, TypeError) as exc:
            self.print(f'[TCP] Rejected connection from {addr}: {exc}')
        finally:
            if not handed_off:
                try:
                    sock.close()
                except OSError:
                    pass

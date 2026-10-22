import socket

class MockPubSub:
    def __init__(self, client):
        self.client = client

    def subscribe(self, channel):
        self.client._ensure_connection()
        if self.client._sock:
            self.client._sock.sendall(f"SUBSCRIBE {channel}\r\n".encode())
            self.client._sock.recv(1024) # Consume verification payload

    def listen(self):
            while True:
                try:
                    if not self.client._sock:
                        break
                    data = self.client._sock.recv(4096)
                    if not data:
                        break
                    decoded = data.decode('utf-8', errors='ignore')
                    if "message" in decoded:
                        parts = decoded.strip().split('\r\n')
                        # Index 5 is the length header, Index 6 is the actual payload!
                        if len(parts) >= 7:
                            msg_data = parts[6]
                            yield {"type": "message", "data": msg_data.encode('utf-8')}
                except Exception:
                    break




class CAClient:
    def __init__(self, host='127.0.0.1', port=6379, db=0, decode_responses=True, **kwargs):
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses
        self._sock = None

    def _ensure_connection(self):
        if not self._sock:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self.host, self.port))
            except Exception:
                self._sock = None

    @classmethod
    def from_url(cls, url="redis://localhost:6379", **kwargs):
        host, port = '127.0.0.1', 6379
        if "://" in url:
            netloc = url.split("://")[1]
            if ":" in netloc:
                host, port = netloc.split(":")
                port = int(port)
            else:
                host = netloc
        return cls(host, port, **kwargs)

    def set(self, key, value, *args, **kwargs):
        self._ensure_connection()
        if not self._sock:
            return False
        try:
            self._sock.sendall(f"SET {key} {value}\r\n".encode())
            resp = self._sock.recv(1024)
            return b"+OK" in resp
        except Exception:
            self._sock = None
            return False

    def get(self, key):
        self._ensure_connection()
        if not self._sock:
            return None
        try:
            self._sock.sendall(f"GET {key}\r\n".encode())
            resp = self._sock.recv(4096)
            if resp.startswith(b"$-1"):
                return None
            parts = resp.split(b"\r\n")
            if len(parts) >= 2:
                val = parts[1]
                return val.decode('utf-8') if self.decode_responses else val
            return None
        except Exception:
            self._sock = None
            return None

    def publish(self, channel, message):
        self._ensure_connection()
        if not self._sock:
            return b""
        try:
            self._sock.sendall(f"PUBLISH {channel} {message}\r\n".encode())
            return self._sock.recv(1024)
        except Exception:
            self._sock = None
            return b""

    def pubsub(self):
        sub_client = CAClient(self.host, self.port, db=self.db, decode_responses=self.decode_responses)
        return MockPubSub(sub_client)

# Layout mapping for redis namespace (Synchronous version)
class redis:
    Redis = CAClient

    @staticmethod
    def from_url(url=None, **kwargs):
        return CAClient.from_url(url, **kwargs)
    
    asyncio = None

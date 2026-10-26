import asyncio

class MockPubSub:
    def __init__(self, client):
        self.client = client

    async def subscribe(self, channel):
        # Now an async function that sends the subscription right away
        await self.client._ensure_connection()
        if self.client.writer:
            self.client.writer.write(f"SUBSCRIBE {channel}\r\n".encode())
            await self.client.writer.drain()
            await self.client.reader.read(1024) # Consume verification payload

    async def listen(self):
            while True:
                try:
                    if not self.client.reader:
                        break
                    data = await self.client.reader.read(4096)
                    if not data:
                        break
                    decoded = data.decode('utf-8', errors='ignore')
                    if "message" in decoded:
                        parts = decoded.strip().split('\r\n')
                        # Index 5 is the length header (e.g., '$15'), Index 6 is the actual payload!
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
        self.reader = None
        self.writer = None

    async def _ensure_connection(self):
        if not self.writer:
            try:
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            except Exception:
                self.reader, self.writer = None, None

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

    async def set(self, key, value, *args, **kwargs):
        await self._ensure_connection()
        if not self.writer:
            return False
        try:
            self.writer.write(f"SET {key} {value}\r\n".encode())
            await self.writer.drain()
            resp = await self.reader.read(1024)
            return b"+OK" in resp
        except Exception:
            self.writer = None
            return False

    async def get(self, key):
        await self._ensure_connection()
        if not self.writer:
            return None
        try:
            self.writer.write(f"GET {key}\r\n".encode())
            await self.writer.drain()
            resp = await self.reader.read(4096)
            if resp.startswith(b"$-1"):
                return None
            parts = resp.split(b"\r\n")
            if len(parts) >= 2:
                val = parts[1]
                return val.decode('utf-8') if self.decode_responses else val
            return None
        except Exception:
            self.writer = None
            return None

    async def incr(self, key):
        val = await self.get(key)
        try:
            num = int(val) if val is not None else 0
        except ValueError:
            num = 0
        num += 1
        await self.set(key, str(num))
        return num

    async def publish(self, channel, message):
        await self._ensure_connection()
        if not self.writer:
            return b""
        try:
            self.writer.write(f"PUBLISH {channel} {message}\r\n".encode())
            await self.writer.drain()
            return await self.reader.read(1024)
        except Exception:
            self.writer = None
            return b""

    def pubsub(self):
        sub_client = CAClient(self.host, self.port, db=self.db, decode_responses=self.decode_responses)
        return MockPubSub(sub_client)

class redis:
    Redis = CAClient

    @staticmethod
    def from_url(url=None, **kwargs):
        return CAClient.from_url(url, **kwargs)
    
    asyncio = None

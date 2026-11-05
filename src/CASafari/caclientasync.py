import asyncio

class MockPubSub:
    def __init__(self, client):
        self.client = client
        self.channels = set()
        self.reader = None
        self.writer = None

    async def subscribe(self, channel):
        self.channels.add(channel)
        if not self.writer:
            try:
                self.reader, self.writer = await asyncio.open_connection(self.client.host, self.client.port)
            except Exception:
                return
        try:
            self.writer.write(f"SUBSCRIBE {channel}\r\n".encode())
            await self.writer.drain()
            await self.reader.read(1024)
        except Exception:
            self.writer, self.reader = None, None

    async def listen(self):
        while True:
            try:
                if not self.writer or not self.reader:
                    self.reader, self.writer = await asyncio.open_connection(self.client.host, self.client.port)
                    for ch in self.channels:
                        self.writer.write(f"SUBSCRIBE {ch}\r\n".encode())
                        await self.writer.drain()
                        await self.reader.read(1024)
                
                data = await self.reader.read(4096)
                if not data:
                    break
                decoded = data.decode('utf-8', errors='ignore')
                if "message" in decoded:
                    parts = decoded.strip().split('\r\n')
                    if len(parts) >= 7:
                        msg_data = parts[6]
                        yield {"type": "message", "data": msg_data.encode('utf-8')}
            except Exception:
                self.reader, self.writer = None, None
                await asyncio.sleep(1)


class CAClient:
    def __init__(self, host='127.0.0.1', port=6379, db=0, decode_responses=True, **kwargs):
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses

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
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.write(f"SET {key} {value}\r\n".encode())
            await writer.drain()
            resp = await reader.read(1024)
            writer.close()
            await writer.wait_closed()
            return b"+OK" in resp
        except Exception:
            return False

    async def get(self, key):
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.write(f"GET {key}\r\n".encode())
            await writer.drain()
            
            line = await reader.readline()
            if not line or line.startswith(b"$-1"):
                writer.close()
                await writer.wait_closed()
                return None
            
            if line.startswith(b"$"):
                length = int(line[1:].strip())
                data = await reader.readexactly(length + 2)
                writer.close()
                await writer.wait_closed()
                val = data[:-2]
                return val.decode('utf-8') if self.decode_responses else val
            
            writer.close()
            await writer.wait_closed()
            return None
        except Exception:
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
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.write(f"PUBLISH {channel} {message}\r\n".encode())
            await writer.drain()
            resp = await reader.read(1024)
            writer.close()
            await writer.wait_closed()
            return resp
        except Exception:
            return b""

    def pubsub(self):
        return MockPubSub(self)

class redis:
    Redis = CAClient

    @staticmethod
    def from_url(url=None, **kwargs):
        return CAClient.from_url(url, **kwargs)
    
    asyncio = None

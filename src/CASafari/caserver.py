import asyncio

class CAServer:
    def __init__(self, host='127.0.0.1', port=6379):
        self.host = host
        self.port = port
        self.store = {}
        self.subscribers = {} # channel -> set of client writers

    async def handle_client(self, reader, writer):
        client_channels = set()
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                
                parts = data.decode('utf-8', errors='ignore').strip().split()
                if not parts:
                    continue
                
                cmd = parts[0].upper()
                
                # --- PROCESS COMMAND SELECTION ---
                if cmd == "PING":
                    writer.write(b"+PONG\r\n")
                elif cmd == "SET" and len(parts) >= 3:
                    key = parts[1]
                    val = " ".join(parts[2:])
                    self.store[key] = val.encode('utf-8')
                    writer.write(b"+OK\r\n")
                elif cmd == "GET" and len(parts) == 2:
                    key = parts[1]
                    if key in self.store:
                        val = self.store[key]
                        writer.write(f"${len(val)}\r\n".encode() + val + b"\r\n")
                    else:
                        writer.write(b"$-1\r\n")
                elif cmd == "PUBLISH" and len(parts) >= 3:
                    channel = parts[1]
                    msg = " ".join(parts[2:])
                    # RESP structural multi-bulk string format wrapper for pubsub
                    resp_msg = f"*3\r\n$7\r\nmessage\r\n${len(channel)}\r\n{channel}\r\n${len(msg)}\r\n{msg}\r\n".encode()
                    count = 0
                    if channel in self.subscribers:
                        for w in list(self.subscribers[channel]):
                            try:
                                w.write(resp_msg)
                                await w.drain()
                                count += 1
                            except Exception:
                                self.subscribers[channel].discard(w)
                    writer.write(f":{count}\r\n".encode())
                elif cmd == "SUBSCRIBE" and len(parts) == 2:
                    channel = parts[1]
                    if channel not in self.subscribers:
                        self.subscribers[channel] = set()
                    self.subscribers[channel].add(writer)
                    client_channels.add(channel)
                    writer.write(f"*3\r\n$9\r\nsubscribe\r\n${len(channel)}\r\n{channel}\r\n:1\r\n".encode())
                else:
                    writer.write(b"-ERR unknown or unsupported command\r\n")
                
                await writer.drain()
        except Exception:
            pass
        finally:
            # Client disconnected, prune channels cleanly
            for channel in client_channels:
                if channel in self.subscribers:
                    self.subscribers[channel].discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"CAServer running natively on {self.host}:{self.port}...")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(CAServer().start())

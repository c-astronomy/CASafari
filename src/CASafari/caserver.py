import asyncio
import time

class CAServer:
    def __init__(self, host='127.0.0.1', port=6379):
        self.host = host
        self.port = port
        self.store = {}
        self.subscribers = {} # channel -> set of client writers

    async def handle_client(self, reader, writer):
        client_address = writer.get_extra_info('peername')
        print(f"[CASERVER] Client connected from {client_address}")
        client_channels = set()
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                
                raw_data = data.decode('utf-8', errors='ignore').strip()
                if not raw_data:
                    continue
                
                # Use maxsplit=2 so spaces inside JSON values/messages are preserved intact
                parts = raw_data.split(maxsplit=2)
                cmd = parts[0].upper()
                
                # --- PROCESS COMMAND SELECTION ---
                if cmd == "PING":
                    print(f"[CASERVER] PING from {client_address}")
                    writer.write(b"+PONG\r\n")
                    
                elif cmd == "SET" and len(parts) >= 3:
                    key = parts[1]
                    val = parts[2]
                    self.store[key] = val.encode('utf-8')
                    print(f"[CASERVER] SET -> key: '{key}' | value: {val}")
                    writer.write(b"+OK\r\n")
                    
                elif cmd == "GET" and len(parts) >= 2:
                    key = parts[1]
                    if key in self.store:
                        val = self.store[key]
                        print(f"[CASERVER] GET -> key: '{key}' | Found ({len(val)} bytes)")
                        writer.write(f"${len(val)}\r\n".encode() + val + b"\r\n")
                    else:
                        print(f"[CASERVER] GET -> key: '{key}' | Not Found (nil)")
                        writer.write(b"$-1\r\n")
                        
                elif cmd == "PUBLISH" and len(parts) >= 3:
                    channel = parts[1]
                    msg = parts[2]
                    print(f"[CASERVER] PUBLISH -> channel: '{channel}' | message: {msg}")
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
                    
                elif cmd == "SUBSCRIBE" and len(parts) >= 2:
                    channel = parts[1]
                    if channel not in self.subscribers:
                        self.subscribers[channel] = set()
                    self.subscribers[channel].add(writer)
                    client_channels.add(channel)
                    print(f"[CASERVER] SUBSCRIBE -> client {client_address} subscribed to channel: '{channel}'")
                    writer.write(f"*3\r\n$9\r\nsubscribe\r\n${len(channel)}\r\n{channel}\r\n:1\r\n".encode())
                    
                else:
                    print(f"[CASERVER] ⚠️ ERR unknown or unsupported command: {raw_data}")
                    writer.write(b"-ERR unknown or unsupported command\r\n")
                
                await writer.drain()
        except Exception as e:
            print(f"[CASERVER] ❌ Error handling client {client_address}: {e}")
        finally:
            print(f"[CASERVER] Client disconnected: {client_address}")
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
        print(f"CAServer running natively on {self.host}:{self.port} with full terminal logging...")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(CAServer().start())

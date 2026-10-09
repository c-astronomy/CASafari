import asyncio
import json
import time
import redis.asyncio as redis
import aiohttp
import math

# --- CONFIG ---
NINA_API = "http://192.168.0.41:1888/v2/api" #This needs to be the machine ip for NINA, not local 
#NINA_API = "http://localhost:1888/v2/api" #This needs to be the machine ip for NINA, not local 
REDIS_URL = "redis://localhost:6379"
HEARTBEAT_INTERVAL = 2 # Seconds

# Global state tracker to avoid NameErrors in your heartbeat
state = {
    "is_slewing": False,
    "camera_busy": False
}




# 1. The function MUST be defined here
async def update_nina_state():
    # Your websocket logic here
    print("Listening to NINA...") #Hide this or slow down for now, dont need to see eahc iteration
    await asyncio.sleep(1)




async def nina_heartbeat(r_client):
    async with aiohttp.ClientSession() as session:
        while True:
            is_online = False
            try:
                # 1. Check Mount for Slewing
                async with session.get(f"{NINA_API}/equipment/mount/info", timeout=2) as resp:
                    if resp.status == 200:
                        mount_data = await resp.json()
                        state["is_slewing"] = mount_data.get("Response", {}).get("Slewing", False)
                        is_online = True # If we can talk to the mount, NINA is online

                # 2. Check Camera for Imaging
                async with session.get(f"{NINA_API}/equipment/camera/info", timeout=2) as resp:
                    if resp.status == 200:

                        c_data = await resp.json()
                        state["camera_busy"] = c_data.get("Response", {}).get("IsExposing", False)





            except Exception as e:
                # If the network fails, assume it's offline
                is_online = False
                state["is_slewing"] = False
                state["camera_busy"] = False

            # 3. Update Redis
            status_data = {
                "online": is_online,
                "is_slewing": state["is_slewing"],
                "camera_busy": state["camera_busy"],
                "busy": state["is_slewing"] or state["camera_busy"]
            }
            await r_client.set("nina:status", json.dumps(status_data))
            
            await asyncio.sleep(HEARTBEAT_INTERVAL)







async def redis_listener(r_client):
    """Listens for commands from Redis and forwards them to NINA."""
    print("Redis Listener active. Waiting for commands...")
    pubsub = r_client.pubsub()
    await pubsub.subscribe("nina:commands")
    
    async for message in pubsub.listen():
        # Only process actual messages (ignore subscription confirmations)
        if message["type"] == "message":
            try:
                # 1. Decode the data from bytes to string
                raw_payload = message["data"]
                if isinstance(raw_payload, bytes):
                    raw_payload = raw_payload.decode('utf-8')
                
                # 2. Ignore plain text signals like "!list" or "list_ready"
                if raw_payload.startswith('!') or "list_ready" in raw_payload:
                    # These are for the Twitch bot/Casafari logic, ignore them here
                    continue

                # 3. Parse JSON
                cmd_data = json.loads(raw_payload)
                
                # 4. Process Slew Command
                #Process Any Valid Action Command
                if isinstance(cmd_data, dict) and "action" in cmd_data:
                    print(f"Received command: {cmd_data.get('action')} ({cmd_data.get('name', 'no-name')})")
                    await execute_nina_command(cmd_data, r_client)
                else:
                    print(f"Ignored non-action payload: {cmd_data}")







            except json.JSONDecodeError:
                # This captures any non-JSON strings so the script doesn't crash
                print(f"Ignored non-JSON message: {message['data']}")
            except Exception as e:
                print(f"❌ Error in listener loop: {e}")





def convert_for_slew(ra, ra_min, dec, dec_min):
    ra_total_hours = float(ra) + (float(ra_min) / 60.0)
    slewRa_degrees = ra_total_hours * 15.0

    dec_d = float(dec)
    dec_m = float(dec_min)
    
    is_negative = dec_d < 0 or math.copysign(1.0, dec_d) < 0

    if is_negative:
        slewDec_degrees = dec_d - (dec_m / 60.0)
    else:
        slewDec_degrees = dec_d + (dec_m / 60.0)

    return slewRa_degrees, slewDec_degrees


async def execute_nina_command(cmd_data, r_client):
    """The safety-gated execution logic."""


    #Automatic start safarimode test
    if not cmd_data.get("is_safari"):
        print("User action detected. Resetting Safari idle timer.")
        await r_client.set("nina:last_user_action", time.time())
        # Force Safari OFF temporarily if you want manual control to stay on
        # await r_client.set("safari:active", "false")


    # 1. Ignore strings like "!list" (Casafari handles those)
    if not isinstance(cmd_data, dict):
        return

    # 2. Check if NINA is online via the status we just set in heartbeat
    status_raw = await r_client.get("nina:status")
    if not status_raw or not json.loads(status_raw).get("online"):
        print("❌ Command rejected: NINA is offline.")
        return



    action = cmd_data.get("action")
    target_name = cmd_data.get("name", "Unknown Target")

    # 3. Safety Gate (Option A: Drop if busy)
    if action != "abort" and (state["is_slewing"] or state["camera_busy"]):
        print(f"🚫 Target/Command rejected: System busy with another operation (Target: {target_name}).")
        return  # Drop command immediately, don't queue or wait

    # 4. Immediate State Lock
    if action == "slew":
        state["is_slewing"] = True
        state["camera_busy"] = True #Uncomment if problematic
    elif action in ["exposure", "sequence"]:
        state["camera_busy"] = True
    #Add sequence? and camera busy?





    async with aiohttp.ClientSession() as session:

        if action == "slew":
            # 1. Get raw values (Hours for RA, Degrees for Dec) with minutes included
            raw_ra_h = float(cmd_data.get('ra', 0))
            raw_ra_m = float(cmd_data.get('ra_min', 0))
            
            raw_dec_d = float(cmd_data.get('dec', 0))
            raw_dec_m = float(cmd_data.get('dec_min', 0))
            
            # 2. Convert to Precise Decimal Degrees using robust conversion
            precise_ra, precise_dec = convert_for_slew(raw_ra_h, raw_ra_m, raw_dec_d, raw_dec_m)
            
            # 3. Prepare the URL
            endpoint = f"{NINA_API}/equipment/mount/slew"
            params = {
                "ra": precise_ra,
                "dec": precise_dec
            }


            print(f"Sending GET Slew to NINA: {endpoint} with RA:{precise_ra}, DEC:{precise_dec}")

#START TEST


            try:
                # 1. PREPARE NINA (Tabs and Coordinates)
                await session.get(f"{NINA_API}/application/switch-tab?tab=framing")
                await asyncio.sleep(0.5)
                await session.get(f"{NINA_API}/framing/set-coordinates?RAangle={precise_ra}&DecAngle={precise_dec}")
                await asyncio.sleep(0.5)

                # 2. TRIGGER THE ACTUAL SLEW (Move this UP!)
                print(f"Triggering Mount Slew to {precise_ra}, {precise_dec}...")
                async with session.get(endpoint, params=params) as resp:
                    if resp.status not in [200, 204]:
                        print("❌ Slew rejected by NINA!")
                        return
                    else:
                        await r_client.publish("twitch:chat_queue", f"CASafari is slewing to {cmd_data['name']}")
                        await r_client.publish("nina:speech", f"Slewing to {cmd_data['name']}")

                # 3. WAIT FOR MOUNT TO START MOVING
                # We wait 3 seconds to give the NINA Heartbeat/WebSocket time to see 'IsSlewing: True'
                await asyncio.sleep(3) 

                # 4. MONITOR THE MOVE
                print("⏳ Waiting for mount to finish moving...")
                while state["is_slewing"]:
                    await asyncio.sleep(1) 
                
                print("Slew complete. Settling for 3 seconds...")
                await asyncio.sleep(3)

                # 5. SWITCH TO IMAGING AND CAPTURE
                await session.get(f"{NINA_API}/application/switch-tab?tab=imaging")
                await asyncio.sleep(0.5)
                
                #5 sec usually, ill up ot now for test
                print("Taking 5s preview...")
                async with session.get(f"{NINA_API}/equipment/camera/capture?duration=5") as resp:
                    print("Preview triggered!")
                    await asyncio.sleep(5) #ILL HARDCODE THIS TO PREVIEW TIME ATM

            except Exception as e:
                print(f"❌ Error in slew chain: {e}")
            finally:
                # IMPORTANT: Release the locks so the next command can come in
                state["is_slewing"] = False
                state["camera_busy"] = False


#END TEST


        #SEQUENCE TEST

        # SEQUENCE HANDLER
        if action == "sequence":
            state["camera_busy"] = True
            print("NINA: Resetting and starting sequence...")

            try:
                # 1. Switch tab to Imaging
                async with session.get(f"{NINA_API}/application/switch-tab?tab=imaging") as resp:
                    if resp.status not in [200, 202, 204]:
                        text = await resp.text()
                        print(f"❌ Switch-tab failed ({resp.status}): {text}")

                await asyncio.sleep(0.5)

                # 2. Reset Sequence
                async with session.get(f"{NINA_API}/sequence/reset") as resp:
                    if resp.status in [200, 202, 204]:
                        print("✅ NINA sequence reset!")
                    else:
                        text = await resp.text()
                        print(f"❌ Sequence reset failed ({resp.status}): {text}")

                await asyncio.sleep(0.5)

                # 3. Start Sequence
                async with session.get(f"{NINA_API}/sequence/start") as resp:
                    if resp.status in [200, 202, 204]:
                        print("🚀 NINA sequence started successfully!")
                    else:
                        text = await resp.text()
                        print(f"❌ Sequence start failed ({resp.status}): {text}")

            except Exception as e:
                print(f"❌ Network Error during sequence chain: {e}")
            finally:
                # Note: If your heartbeat doesn't catch 'camera_busy' via IsExposing or Sequence Status,
                # you may want to keep state["camera_busy"] = True until a WebSocket/heartbeat clears it.
                pass


        #SEQUENCE END




        #elif action =="exposure":
        if action == "exposure":
            seconds = cmd_data.get("exposure", 30) # Default to 30 if not sent
            endpoint = f"{NINA_API}/equipment/camera/capture"

            # NINA usually expects a JSON body for capture
            payload = {
                "ExposureTime": float(seconds),
                "Binning": 1,
                "ImageType": "LIGHT"
            }

            tmppayload = {
                    "?duration=20"
            }


            print(f"NINA: Taking {seconds}s exposure...")



            try:
                # We use POST for actions that 'create' or 'start' something like an image
                #async with session.post(endpoint, json=payload) as resp:
                #async with session.post(endpoint, json=tmppayload) as resp:
                #async with session.post("192.168.0.41:1888/v2/api/equipment/camera/capture") as resp:
                #async with session.get("http://192.168.0.41:1888/v2/api/equipment/camera/capture") as resp:




                async with session.get(f"{NINA_API}/application/switch-tab?tab=imaging") as resp:
                    if resp.status in [200, 202, 204]:
                        print(f"Switch-tab to imaging!")
                        # You could set state["camera_busy"] = True here if you want
                    else:
                        text = await resp.text()
                        print(f"❌ Switch-tab failed. Status: {resp.status}, Body: {text}")
            #except Exception as e:
            #    print(f"❌ Network Error on exposure: {e}")




                await asyncio.sleep(0.5)




                async with session.get(f"{NINA_API}/sequence/reset") as resp:
                    if resp.status in [200, 202, 204]:
                        print(f"NINA sequence reset!")
                        # You could set state["camera_busy"] = True here if you want
                    else:
                        text = await resp.text()
                        print(f"❌ Sequence failed. Status: {resp.status}, Body: {text}")
            #except Exception as e:
            #    print(f"❌ Network Error on exposure: {e}")




                await asyncio.sleep(0.5)




                async with session.get(f"{NINA_API}/sequence/start") as resp:
                    if resp.status in [200, 202, 204]:
                        print(f"NINA sequence started!")
                        # You could set state["camera_busy"] = True here if you want
                    else:
                        text = await resp.text()
                        print(f"❌ Sequence failed. Status: {resp.status}, Body: {text}")
            except Exception as e:
                print(f"❌ Network Error during sequence chain: {e}")






async def main():
    r = redis.from_url(REDIS_URL)
    
    # Run three things at once:
    # 1. The Event Listener (WebSocket)
    # 2. The Heartbeat (HTTP Polling)
    # 3. The Redis Command Subscriber
    await asyncio.gather(
        update_nina_state(),  # Your WebSocket listener
        nina_heartbeat(r),    # The new health checker
        redis_listener(r)     # The command receiver
    )

if __name__ == "__main__":
    #asyncio.run(main())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping NINA bridge...")

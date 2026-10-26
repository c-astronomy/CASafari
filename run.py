import sys
import os
import time
import multiprocessing

# Add src to python path so package imports work cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src/CASafari')))

from caserver import CAServer
import asyncio
from casafari import main as casafari_main, load_and_format_targets
from twitch import main as twitch_main
from nina import main as nina_main
from webserver import app
from caclient import redis

def setup_process_logging(name):
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", f"{name}.log")
    f = open(log_path, "w", buffering=1)
    sys.stdout = f
    sys.stderr = f

def run_caserver():
    #setup_process_logging("caserver")    #Comment out to make CASafari output in terminal
    print("🚀 Starting Built-in CAServer (Redis-compatible)...")
    try:
        asyncio.run(CAServer().start())
    except Exception as e:
        print(f"❌ CAServer error: {e}")

def run_nina():
    setup_process_logging("nina")
    print("🚀 Starting NINA Bridge...")
    try:
        asyncio.run(nina_main())
    except Exception as e:
        print(f"❌ NINA Bridge error: {e}")

def run_twitch():
    setup_process_logging("twitch")
    print("🚀 Starting Twitch Bot...")
    try:
        twitch_main()
    except Exception as e:
        print(f"❌ Twitch Bot error: {e}")

def run_casafari():
    setup_process_logging("casafari")
    print("🚀 Starting Automation Engine (CASafari)...")
    time.sleep(2) # Give CAServer a moment to start up
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        casafari_main(r)
    except Exception as e:
        print(f"❌ Automation Engine error: {e}")

def run_webserver():
    setup_process_logging("webserver")
    print("🚀 Starting Flask Web Dashboard on http://0.0.0.0:5000 ...")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Webserver error: {e}")

def init_session():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        if not r.get("session:start_time"):
            r.set("session:start_time", time.time())
        if not r.get("session:targets_slewed"):
            r.set("session:targets_slewed", "0")
        if not r.get("session:captures"):
            r.set("session:captures", "0")
        if not r.get("session:commands_processed"):
            r.set("session:commands_processed", "0")
    except Exception as e:
        print(f"⚠️ Could not initialize session stats in Redis: {e}")

if __name__ == '__main__':
    print("==================================================")
    print("        CASAFARI TELESCOPE ECOSYSTEM STARTUP      ")
    print("==================================================")

    init_session()

    processes = []

    # 1. Start CAServer (Redis)
    p_redis = multiprocessing.Process(target=run_caserver, daemon=True)
    processes.append(p_redis)
    p_redis.start()

    # Give CAServer a moment to bind port 6379
    time.sleep(1)

    # 2. Start NINA Bridge
    p_nina = multiprocessing.Process(target=run_nina, daemon=True)
    processes.append(p_nina)
    p_nina.start()

    # 3. Start Twitch Bot
    p_twitch = multiprocessing.Process(target=run_twitch, daemon=True)
    processes.append(p_twitch)
    p_twitch.start()

    # 4. Start Automation Engine
    p_casa = multiprocessing.Process(target=run_casafari, daemon=True)
    processes.append(p_casa)
    p_casa.start()

    # 5. Start Web Server
    try:
        run_webserver()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down CASafari Ecosystem...")
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join()
        print("👋 CASafari shutdown complete.")

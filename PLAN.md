# CASafari Project Plan 🚀

CASafari is an integrated, Twitch-chat-controlled telescope automation and web dashboard ecosystem built with Python, Flask, TwitchIO, and Redis (supporting both standard Redis and `caserver.py`, a built-in Python Redis-compatible server).

---

## 🏗️ System Architecture & Components

1. **Web Dashboard (`webserver.py`)**
   - Flask-based web interface running on port 5000.
   - Manages location settings, Twitch credentials, target lists (RA/DEC coordinates and trigger phrases), and system master controls.
   - Polls NINA telescope status via Redis (`nina:status`) for real-time indicator lights (online, slewing, camera imaging).

2. **Automation Engine (`casafari.py`)**
   - Core runtime hub for autonomous telescope target rotation when Twitch chat is idle.
   - Filters target lists based on altitude/azimuth horizon limits (`targetlist.json`).
   - Communicates with NINA via HTTP/WebSocket commands and Redis pub/sub (`nina:commands`, `nina:speech`, `twitch:chat_queue`).

3. **Twitch Chat Bot (`twitch.py`)**
   - TwitchIO-based bot handling interactive chat commands (`!slew`, `!list`, `!safari`, `!stopsafari`, etc.).
   - Relays messages and updates through Redis channels (`twitch:chat_queue`, `twitch:updates`).

4. **NINA Bridge (`nina.py`)**
   - Background worker service bridging CASafari with the N.I.N.A. (Nighttime Imaging 'N' Astronomy) astrophotography software API via HTTP and WebSockets.

5. **Built-in Redis Server (`caserver.py`)**
   - Pure Python lightweight Redis-compatible server implementation for message broker and state storage without requiring external Redis binaries on Windows/Linux.

---

## 🎯 Task Breakdown & Execution Plan

### 1. Web Dashboard Updates (`webserver.py`)
- **Remove Twitch Bot Status Buttons:** Clean up the "Twitch Bot Status" card/buttons from the UI and their corresponding backend action handlers, as Twitch bot lifecycle management is integrated into the unified runner or managed externally.

### 2. Automation Engine Integration (`casafari.py` & `webserver.py`)
- **Tie Automation Engine Button to `casafari.py`:**
  - The web dashboard "Automation Engine (Casafari)" START/STOP buttons set the Redis key `status:casa_enabled` (`true`/`false`).
  - Update `casafari.py` main loop to read `status:casa_enabled` from Redis on every iteration.
  - If `status:casa_enabled` is `"false"`, pause/disable the automation engine loop (`auto_safari = False`). When `"true"`, re-enable automatic target rotation according to user idle timers and commands.

### 3. Single Start Runner Script (`run.py`)
- Create a unified Python startup script (`run.py`) in the root directory that orchestrates the entire CASafari ecosystem concurrently using threads/processes:
  - Built-in Redis server (`caserver.py`)
  - NINA Bridge (`nina.py`)
  - Twitch Bot (`twitch.py`)
  - Automation Engine (`casafari.py`)
  - Flask Web Dashboard (`webserver.py`)
- Allows starting the entire project with a single command: `python run.py`.

---

## 💡 Future Enhancement Ideas
1. **Real-time WebSocket / SSE Dashboard:** Replace polling in `webserver.py` with Server-Sent Events (SSE) or WebSockets for instant status updates.
2. **Unified System Log Viewer:** Add a log stream tab in the web dashboard showing live logs from NINA, Twitch chat, and the Automation Engine.
3. **Automated Unit Tests:** Add test suites for coordinate conversion (`convert_for_slew`), horizon filtering (`filter_targets`), and Redis state synchronization.

# CASafari 🚀

A robust, modern web dashboard and interactive telescope automation ecosystem combining **Flask**, **TwitchIO**, and **N.I.N.A. (Nighttime Imaging 'N' Astronomy)**. 

CASafari features a custom, lightweight, native Python **`caserver`** and **`caclient`** backend pipeline imported seamlessly as `redis` to mimic standard Redis libraries—making the entire application 100% cross-platform without requiring external redis-server installations.

---

## 🛡️ License & Copyleft Protection

This project is proudly licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**.

### What this means for users and developers:
* **Open & Collaborative:** You are free to fork, clone, modify, and contribute back to this repository.
* **No Closed-Source Exploitation:** If you modify this project and host it on a network or cloud server as a web application, API, or service, **you are legally required to make your entire modified source code available to your users under the exact same AGPLv3 license**.

---

## 📦 Installation & Setup

### Developer Installation (Via Git)
Clone the repository and install it locally in **editable mode**:
```bash
git clone https://github.com/c-astronomy/CASafari
cd CASafari
pip install -e .
```

---

## ⚙️ Configuration Files

Before running the application, ensure your configuration files are properly populated in the root folder:

### 1. `credentials.json`
Used by the Twitch bot and web dashboard for API access:
```json
{
  "client_id": "your_twitch_client_id",
  "client_secret": "your_twitch_client_secret",
  "owner_id": "your_owner_id",
  "bot_id": "your_bot_id",
  "token": "your_oauth_token"
}
```

### 2. `casafari-config.json`
Defines your geographic coordinates, mount tracking boundaries, and N.I.N.A. integration endpoint (Note: N.I.N.A. API port defaults to `1888`):
```json
{
  "lat": 59.6,
  "lon": 16.4903,
  "AltLim": 30,
  "AltLimMax": 75,
  "AzLim": 230,
  "AzLimMax": 350,
  "expo": 30,
  "ip": "localhost:1888",
  "platesolve": "false",
  "sequence_mode": "false"
}
```

### 3. `targetlist.json`
Contains your celestial targets list, coordinates, and chat trigger commands (e.g., `!slew_andromeda`).

---

## 🎛️ New Features & Master Control Toggles

CASafari includes powerful toggle controls managed directly via the Web Dashboard **System Master Control** card:

1. **Automation Engine (Casafari)** (`ON` / `OFF`): Manages autonomous target rotation when Twitch chat is idle.
2. **Plate Solve & Center** (`ON` / `OFF`): When enabled, both auto-safari and triggered slews (`!slew_...`) automatically trigger N.I.N.A. plate solving and centering (`/framing/center`) after slewing.
3. **Sequence Mode** (`ON` / `OFF`): When enabled, N.I.N.A. executes full target sequences (`/sequence/reset` and `/sequence/start`) instead of standard 5-second preview captures. When disabled, the legacy preview capture method is used.
4. **Chat Command `!stats`**: Live session telemetry tracking uptime, targets slewed, captures taken, current target, and automation status.

---

## 🛠️ Project Architecture

```text
CASafari/
├── .github/
├── src/
│   └── CASafari/
│       ├── __init__.py             # Python package initializer
│       ├── caclient.py             # Synchronous custom Redis client wrapper
│       ├── caclientasync.py        # Asynchronous custom Redis client wrapper
│       ├── casafari-config.json    # Observer location, coordinates, and limits
│       ├── casafari.py             # Main automation hub & auto-safari loop
│       ├── caserver.py             # Native cross-platform Redis-compatible server
│       ├── nina.py                 # N.I.N.A. API bridge and equipment monitor
│       ├── targetlist.json         # Celestial target database & chat triggers
│       ├── tts.py                  # Experimental Pocket-TTS audio worker
│       ├── twitch.py               # TwitchIO chat bot and command router
│       └── webserver.py            # Flask master control dashboard UI
├── LICENSE                         # GNU AGPLv3 License text
├── README.md                       # Documentation and usage guide
├── pyproject.toml                  # Package metadata & dependencies
└── requirements.txt                # Legacy/additional requirements backup
```

## 🚀 Execution & Startup Order

You can start the entire ecosystem with a single command (`python run.py`), which spawns all background workers and keeps CASafari's terminal output visible for real-time visual monitoring:

```bash
python run.py
```

Or start processes individually:
1. **Built-in Redis Server (`caserver.py`)**: `python caserver.py`
2. **Web Dashboard (`webserver.py`)**: `python webserver.py` (runs on http://0.0.0.0:5000)
3. **N.I.N.A. Automation Bridge (`nina.py`)**: `python nina.py` (communicates with N.I.N.A. on port `1888`)
4. **Automation Engine (`casafari.py`)**: `python casafari.py`
5. **Twitch Chat Bot (`twitch.py`)**: `python twitch.py`

---

## 🤝 Contributing

We welcome community collaborations! Feel free to open a Pull Request or fork the project. All contributions remain protected under the AGPLv3 license.

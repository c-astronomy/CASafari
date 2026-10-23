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
git clone https://github.com/your-username/CASafari
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
Defines your geographic coordinates, mount tracking boundaries, and N.I.N.A. integration endpoint:
```json
{
  "lat": 59.6,
  "lon": 16.4903,
  "AltLim": 30,
  "AltLimMax": 75,
  "AzLim": 230,
  "AzLimMax": 350,
  "expo": 30,
  "ip": "localhost:1888"
}
```

### 3. `targetlist.json`
Contains your celestial targets list, coordinates, and chat trigger commands (e.g., `!slew_andromeda`).

---

## 🛠️ Project Architecture

```text
CASafari/
├── pyproject.toml                  # Package metadata & dependencies
├── LICENSE                         # GNU AGPLv3 License text
├── README.md                       # Documentation and usage guide
├── credentials.json                # Twitch authentication credentials
├── casafari-config.json            # Observer location and mount limits
├── targetlist.json                 # Celestial target database
├── caclient.py                     # Synchronous custom Redis client
├── caclientasync.py                # Asynchronous custom Redis client
├── caserver.py                     # Native cross-platform Redis-compatible server
├── casafari.py                     # Main runtime hub & auto-safari loop
├── nina.py                         # N.I.N.A. API bridge and equipment monitor
├── twitch.py                       # TwitchIO chat bot and command router
├── tts.py                          # Experimental Pocket-TTS audio worker
└── webserver.py                    # Flask master control dashboard UI
```

---

## 🚀 Execution & Startup Order

⚠️ **Important:** The startup order is critical for proper inter-process communication.

1. **Step 1 (Mandatory First): Start `caserver.py`**
   ```bash
   python caserver.py
   ```
2. **Step 2 (Recommended Second): Start `webserver.py`**
   ```bash
   python webserver.py
   ```
3. **Steps 3–5 (Remaining Order is Flexible):**
   * **Start the N.I.N.A. Automation Bridge:**
     ```bash
     python nina.py
     ```
   * **Start the Core Automation Hub (Casafari):**
     ```bash
     python casafari.py
     ```
   * **Start the Twitch Chat Bot:**
     ```bash
     python twitch.py
     ```

---

## 🤝 Contributing

We welcome community collaborations! Feel free to open a Pull Request or fork the project. All contributions remain protected under the AGPLv3 license.

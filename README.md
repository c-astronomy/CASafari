***For Windows users, you need to find a way to install redis-server, you could run everything under WSL or add a Docker!***


# CASafari 🚀

A robust, modern web dashboard and interactive chat bot ecosystem combining **Flask** and **TwitchIO**. 

This application lets you manage interactive automation, track twitch chat components, host local assets, and process data using asynchronous pipelines backed by **Redis** and **SQLite**.

---

## 🛡️ License & Copyleft Protection

This project is proudly licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. 

### What this means for users and developers:
* **Open & Collaborative:** You are free to fork, clone, modify, and contribute back to this repository.
* **No Closed-Source Exploitation:** If you modify this project and host it on a network or cloud server (such as AWS, Heroku, or a private server) as a web application, API, or service, **you are legally required to make your entire modified source code available to your users under the exact same AGPLv3 license**. You cannot lock this code behind a closed-source proprietary paid service.

---

## 📦 Installation

### Option 1: Standard Installation (Via PyPI)
For users who just want to download and run the package without modifying the core files, install it globally using `pip`:
```bash
pip install CASafari
```
*`pip` will automatically download and install all required external dependencies (`Flask`, `twitchio`, `redis`, `asqlite`, and `aiohttp`) in the background.*

### Option 2: Developer Installation (Via Git)
If you want to view, customize, or contribute to the project layout:
1. Clone the repository:
   ```bash
   git clone https://github.com
   cd CASafari
   ```
2. Install the package locally in **editable mode** so changes take effect immediately:
   ```bash
   pip install -e .
   ```

---

## ⚙️ Configuration Setup

Before running the application, you must fill out your local configuration blueprints sitting in the root folder.

### 1. `credentials.json`
Open this file and replace the placeholders with your authentic Twitch and database access tokens:
```json
{
  "TWITCH_CLIENT_ID": "your_client_id_here",
  "TWITCH_OAUTH_TOKEN": "your_oauth_token_here",
  "REDIS_HOST": "localhost",
  "REDIS_PORT": 6379
}
```

### 2. `targetlist.json`
Populate this file with your targeting metrics, channels, or initial list filters used by the tracking scripts.

---

## 🛠️ Project Architecture

This repository uses a structured, standardized Python layout:

```text
CASafari/
├── .github/workflows/release.yml   # Secure automated publishing to PyPI
├── pyproject.toml                  # Single-source-of-truth metadata & dependencies
├── LICENSE                         # GNU AGPLv3 License text
├── README.md                       # Documentation and usage guide
├── credentials.json                # User credentials template (Do not push secrets!)
├── targetlist.json                 # Core system configuration data
└── src/
    └── CASafari/
        ├── __init__.py             # Python package initializer
        ├── casafari.py             # Main runtime hub
        ├── nina.py                 # Bot automation sub-routines
        ├── tts.py                  # Experimental Audio/TTS handlers (Unused in core)
        ├── twitch.py               # TwitchIO listener and chat connection pipeline
        └── webserver.py            # Flask UI router and data endpoints
```

---

## 🤝 Contributing

We welcome community collaborations to make CASafari better! To contribute:
1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a **Pull Request**.

All contributions will remain protected under the project's original AGPLv3 license.

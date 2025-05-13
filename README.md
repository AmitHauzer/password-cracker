# 🔎 Distributed MD5 Phone Number Cracker 🔎

A simple **master–minion** system for distributed MD5 brute‑forcing of phone‑number preimages. Currently specialized for Israeli phone‑number formats (`05X-XXXXXXX`), but easily extensible to other formats.

---

## Table of Contents

* [Architecture](#architecture)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Configuration](#configuration)
* [Directory Structure](#directory-structure)
* [Running Instructions](#running-instructions)
  * [Starting the Master](#starting-the-master)
  * [Starting a Minion](#starting-a-minion)
  * [Uploading Hashes](#uploading-hashes)
  * [Monitoring Tasks](#monitoring-tasks)
* [Logging](#logging)
* [Extending Formats](#extending-formats)
* [License](#license)

---

## 🏛 Architecture

* **Master** (`master_server.py`):

  * Accepts hash‑files via `POST /upload-hashes`.
  * Splits work into numeric ranges per registered minion using configured `FormatStrategy`.
  * Exposes endpoints: `/get-task`, `/task-status`, `/submit-result`, `/all-tasks`, `/heartbeat`, `/register`, `/disconnect-minion`.


* **Minion** (`minion_server.py`):

  * Registers itself and sends periodic heartbeats.
  * Polls `/get-task` for work, runs `crack_range()`, and reports back via `/submit-result`.
  * Supports graceful shutdown and automatic resumption.

---

## ✅ Prerequisites

* Python 3.11 or newer
* `pip` for package installation
* `uv` CLI tool (install with `pip install uv`)

## 📦 Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/AmitHauzer/password-cracker.git
   cd password-cracker
   ```
2. Initialize and sync dependencies using `uv` (creates a virtual environment and installs deps from `pyproject.toml`):

   ```bash
   # python version >= 3.8
   pip install uv 
   uv venv   # create and activate a virtual environment
   uv sync   # install dependencies
   
   # linux and MacOS
   source .venv/bin/activate

   # Windows
   .\.venv\Scripts\activate
   ```
3. (Alternative) Manually create a virtual environment and install with `pip`:

   ```bash
   # python version >= 3.11
   python -m venv .venv
   
   # for Linux and MacOS
   source .venv/bin/activate
   # for Windows
   source .venv/bin/activate

   pip install -r requirements.txt
   ```
---
## ⚙️ Configuration

Edit `config.py` to adjust:

| Variable                | Description                                     | Default                 |   
| ----------------------- | ----------------------------------------------- | ----------------------- | 
| `MASTER_SERVER_HOST`    | Host/IP for the master server                   | `"localhost"`           |
| `MASTER_SERVER_PORT`    | Port for the master server                      | `8000`                  |   
| `MASTER_SERVER_URL`     | Base URL for master (computed from host & port) | `http://localhost:8000` |   
| `MINION_HOST`           | Host/IP for the minion server                   | `"localhost"`           |   
| `FORMATTER_TASK_NAME`   | Key for phone‑number format in `formatters`     | `"israel_phone"`        |  
| `TASKS_DB_FILE`         | Path to persisted tasks JSON                    | `tasks_db.json`         |
| `LOG_DIR`               | Directory for log files                         | `logs/`                
| `LOG_PROGRESS_INTERVAL` | # of attempts between progress logs             | `100_000`            |
| `CANCEL_CHECK_INTERVAL` | # of attempts between cancellation polls        | `10_000`                |

## 📂 Directory Structure

```
password-cracker
├── src/
│   ├── master_server.py
│   ├── minion_server.py
│   ├── config.py
│   ├── models.py           # domain models
|   ├── models/
│   │   └──schemas/         # API request/response schemas
│   │      ├── request.py
│   │      └── response.py
│   ├── utils/
│   │   ├── master_utils.py
│   │   └── minion_utils.py
│   └── formatters/
│       ├── base.py         # FormatStrategy ABC
│       ├── israel_phone.py
│       └── example.py
├── requirements.txt        # dependency list
├── pyproject.toml          # dependency list
├── hashes.txt              # for help
├── create_hash_md5.py      # for help
└── README.md
```
---

## 🚀 Running Instructions:

#### ▶️ Starting the Master:

```bash
# activate venv
python src/master_server.py
```

### 🤖 Starting Minions:
Minions auto-register and begin polling for tasks.
```bash
# terminal 1 (activate venv)
python src/minion_server.py --port 8001
# terminal 2 (activate venv)
python src/minion_server.py --port 8002
# terminal 3 (activate venv)
python src/minion_server.py --port <PORT_NUMBER>
```

### 📤 Uploading Hashes

Send an MD5‑hash file (one per line) to the master via a POST to `/upload-hashes`. For example, with `curl`:

```bash
curl -X POST "http://localhost:8000/upload-hashes" -F "file=@hashes.txt"
```

If the master is still processing previous tasks, you will receive a `429 Server is busy` response.

### 📊 Monitoring Tasks and Health

* **API Docs**: Browse interactive documentation at [/docs](http://localhost:8000/docs).
* **Server Status**: Check the master’s health with: [http://localhost:8000/status](http://localhost:8000/status)
    
## 📈 Logging

Both master and minion use standard Python `logging`. By default, you’ll see INFO logs on stdout. Logs are also saved to the `logs/` directory. Adjust levels in `master_server.py` or `minion_server.py`

You can the `--log-level debug`
``` bash
python src/minion_server.py --port 8001 --log-level debug
```

---

## ⚡ Extending Formats

1. Create a new file in `formatters/`, inherit from `FormatStrategy` in `base.py`, implement `min_value`, `max_value`, and `number_to_string()`.
2. Register it in `formatters/__init__.py` under a unique key.
3. Update `FORMATTER_TASK_NAME` in `config.py`.

---

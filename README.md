# Samsung Innovation Campus: Stage 3 Assignment

| Group Informations  |   |
|---------------|---------------|
| Group Code  | UNI422  |
| Group Name  | rarevolution  |
| Team  | - Adeline Charlotte Augustinne<br>- Angeline Rachel<br>- Anastashia Ellena Widjaja<br>- Rowen Nicholas    |

---

# 🐾 PawPal Iot Setup Guide

Welcome to the **PawPal IoT**! This guide will walk you through everything you need to set up the configuration for running the arduino for intended purposes.

## Board: ESP32 A1S  
The speaker is connected to the ESP32 A1S via the built-in port on the board using cables.

## 🔧 IoT Setup Steps

### 1. Install the Arduino IDE  
Download and install the Arduino IDE from the official website:  
👉 [https://www.arduino.cc/en/software](https://www.arduino.cc/en/software)

### 2. Add Required Arduino Libraries  
The following libraries are used in the project:

- [Adafruit_BusIO](https://github.com/adafruit/Adafruit_BusIO)  
- [Arduino Audio Tools by P. Schatzmann](https://github.com/pschatzmann/arduino-audio-tools)  
- [Arduino_DebugUtils](https://github.com/arduino-libraries/Arduino_DebugUtils)  
- [Arduino RS485](https://github.com/arduino-libraries/ArduinoRS485)  
- [Arduino_SerialUpdater](https://github.com/arduino-libraries/Arduino_SerialUpdater)  
- [ES8388 by thaaraak](https://github.com/thaaraak/es8388)  
- [Arduino WebSockets by Markus Sattler](https://github.com/Links2004/arduinoWebSockets)
- [ArduinoJSON](https://arduinojson.org)
- [Arduino FreeRTOS](https://www.arduinolibraries.info/libraries/free-rtos)
- [WiFi Manager](https://github.com/tzapu/WiFiManager)

Library files can be found in the project directory:  
📁 `IoT/libraries`

Copy these folders into your local Arduino libraries directory:  
📁 `~/Arduino/libraries` (for Linux; you may have to find the equivalent folder if you are using a different OS)

### 3. Import the Sketch into Arduino IDE  
Open the required `.ino` sketch file using the Arduino IDE.


### 4. Configure the Board and Port  
In the Arduino IDE, set the board to:  
🛠 **ESP32 Dev Module**

Then select the appropriate port your device is connected to.

### 5. Verify the Sketch  
Click the ✅ **check mark** icon in the top-right corner of the IDE to verify the code.

### 6. Upload the Sketch & Run It  
Click the ➡️ **arrow icon** (next to the check mark) to upload the sketch to your board and run it.

### 7. Setup Wi-Fi Manager
On another device, open Wi-Fi settings and connect to the 'PawPal-WifiManager' network.
Then, follow the on-screen instructions to select a Wi-Fi network to connect the IoT board to.

---

# 🐾 PawPal Backend Setup Guide

Welcome to the **PawPal Backend**! This guide will walk you through everything you need to set up the development environment, from installing dependencies like Ollama and MongoDB, to running the FastAPI app locally.

## 🚀 Prerequisites

Before starting, make sure the following tools are installed on your system:

### ✅ Required Tools

- [Python 3.10+](https://www.python.org/downloads/) (Python 3.11 is used in development)
- [Ollama](https://ollama.com/) — for running local LLMs
- [MongoDB Community Server](https://www.mongodb.com/try/download/community) — for data persistence

## 📦 Clone the Repository

```bash
git clone https://github.com/MrPokemons/sic6-stage3.git
cd pawpal-backend
```

## ⚙️ Environment Setup

### 1. 🧪 Configure Environment Variables

Duplicate the example environment file and fill the necessary fields:

```bash
cp config/.env.example config/.env
```

### 2. 🔑 Load the Environment File

Set the following environment variable **before running your app**, so it can locate the config file:

#### On **Linux/macOS** (bash):

```bash
export ENV_FILE=config/.env
```

#### On **Windows CMD**:

```cmd
set ENV_FILE=config/.env
```

#### On **PowerShell**:

```powershell
$env:ENV_FILE = "config/.env"
```

> ✅ This step is critical. Your app reads `ENV_FILE` to load the correct configuration.

## 🐍 Python Environment Setup

#### Option A: Using `venv` (Recommended)

```bash
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

#### Option B: Using `conda`

```bash
conda create -n pawpal python=3.11
conda activate pawpal
```

### 3. 📥 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## ▶️ Running the App

Make sure MongoDB and Ollama are both running, then run the app with:

```bash
python app.py
```

> 🌍 Visit the app at: `http://localhost:11080`

## 🧠 Notes

- To pull and run the Ollama model (example):

  ```bash
  ollama run qwen2.5:3b
  ```

- MongoDB should be listening on the default port (`27017`) unless configured otherwise.

---

# 🖼️ PawPal Frontend

This is the **Streamlit-based dashboard** for **PawPal**, providing an intuitive interface to start the session and view the summarize dashboard.

## ⚙️ Prerequisites

### ✅ Backend Must Be Running

The frontend **requires the backend FastAPI server to be up and running** to enable full functionality.  
If the backend is not running, you’ll be limited to **read-only access** to data from MongoDB (demo mode).

Start the backend with:

```bash
python app.py
```

## 📦 Environment Setup

No need to create a separate environment. The frontend uses the **same Python environment** as the backend.

## 🚀 Running the Frontend

To launch the dashboard, simply run:

```bash
streamlit run dashboard.py
```

> Make sure you run this command **after activating the backend environment**.

## 📇 Registering Your Device

To interact with PawPal via the frontend, you'll need your **IoT device's `device_id`**.

### 🔍 Where to Find `device_id`

- The `device_id` is currently **hardcoded in the IoT firmware/script**.
- You can view it from the **device metadata** or by checking the sketch code used for deployment.

This `device_id` is required during the registration or usage process to associate interactions with the correct device in the backend system.

## 🧠 Features

- **Device-Linked Sessions**  
  Each device has its own conversation history, progress, and logs.

- **Conversation Management**  
  Start new chats, list past conversations by device ID, and view detailed message history.

- **User Progress Tracking**  
  Monitor session milestones, completed stages, and personalized feedback.

- **Logs & Metrics**  
  Track message logs, response metadata, and per-session measurements like engagement and tone.

- **Demo Mode**  
  Enables read-only view of a sample session if the backend is offline.

---

# 🐾 PawPal Backend & Frontend – Dockerized Deployment

This guide walks you through running both the backend (FastAPI) and frontend (Streamlit) using **Docker Compose**, with support for **MongoDB** and optional **Cloudflare Tunnel** integration for domain exposure.

---

## 🚀 Requirements

Ensure the following tools are installed **on your host machine**:

* [Docker & Docker Compose](https://docs.docker.com/get-docker/)
* [Ollama](https://ollama.com/) – must be run separately outside Docker
* A registered domain (if using Cloudflare Tunnel)

---

## 📁 Project Structure

```
.
├── config/
│   └── .env.prod         # Environment variables used by backend & frontend
├── docker-compose.yaml    # Basic setup (backend + frontend + MongoDB)
├── docker-compose-tunnel.yaml  # Adds Cloudflare Tunnel
├── dashboard.py          # Streamlit frontend app
├── app.py                # FastAPI backend app
└── ...
```

---

## 🔐 Environment Setup

1. Copy the example environment file:

```bash
cp config/.env.example config/.env.prod
```

2. Fill in the required values, such as database connection, API keys, etc.

> Ensure `MODEL__URL` if it's hosted locally, use `host.docker.internal` host instead `localhost`

---

## 🐳 Running with Docker Compose

### 🔧 Standard Local Setup

This starts the backend, frontend, and MongoDB locally:

```bash
docker compose up --build
```

> 🧠 Ollama must still be running outside the container:
>
> ```bash
> ollama run qwen2.5:3b
> ```

* **FastAPI backend**: [http://localhost:11080](http://localhost:11080)
* **Streamlit frontend**: [http://localhost:8501](http://localhost:8501)
* **MongoDB** is internal-only (not exposed)

---

## 🌐 Running with Domain (Cloudflare Tunnel)

To expose your app via a domain, you can use the extended compose file:

1. Ensure your `.env.prod` is ready in the `config/` folder.

2. Run:

```bash
docker compose -f docker-compose-tunnel.yaml --env-file config/.env.prod up --build
```

3. The tunnel will start using your **Cloudflare token** set in the environment variable `CF_TUNNEL_TOKEN`.

> If `CF_TUNNEL_TOKEN` is empty or missing, the tunnel service will not run.

---

## 🔗 Custom Domain Setup

You must:

* Own a domain connected to Cloudflare
* Generate a Tunnel Token via [Cloudflare Dashboard → Zero Trust → Access → Tunnels](https://one.dash.cloudflare.com/)
* Add the token to your `.env.prod`:

  ```env
  CF_TUNNEL_TOKEN=eyJh...your_token_here...
  ```

---

## ⚙️ Backend & Frontend Configuration

* **Environment Variables**:
  Set via `.env.prod`, and passed automatically by Compose.

* **Shared Volumes**:
  Hugging Face cache and source code volumes are shared with the container.

* **Networks**:

  * `backend` for internal service-to-service communication and do connect to Cloudflare for IoT device,
  * `frontend` for public-facing services (e.g., Streamlit, Cloudflare)

---

## 🧪 Development Tips

* To shut down:

```bash
docker compose down
```

---

## 🧠 Features Recap

✅ Fully containerized
✅ Optional cloud exposure via Cloudflare Tunnel
✅ Ollama-compatible (run outside container)
✅ Shared environment for backend & frontend
✅ Secure MongoDB — isolated in `backend` network only

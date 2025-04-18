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
- WebSockets  

Library files can be found in the project directory:  
📁 `IoT/libraries`

Copy these folders into your local Arduino libraries directory:  
📁 `~/Arduino/libraries` (or equivalent on your OS)

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

Use the provided `.env.example` file to configure your environment variables:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` as needed:

```env
ENV_TYPE="local"

APP__CONTAINER_NAME="pawpal"

MONGODB__CONN_URI="mongodb://localhost:27017"
MONGODB__DB_NAME="pawpal_v2"

MODEL__NAME="qwen2.5:3b"
MODEL__URL="http://localhost:11434/"
```

### 2. 🔑 Make Sure Your App Loads the `.env` File

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
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
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
uvicorn app:app --host 0.0.0.0 --port 11080
```

> 🌍 Visit the app at: `http://localhost:11080`

## 🧠 Notes

- To pull and run the Ollama model (example):

  ```bash
  ollama run qwen2.5:3b
  ```

- MongoDB should be listening on the default port (`27017`) unless configured otherwise.

Great addition! Here's the updated and polished `README.md` for the **frontend setup**, now including instructions regarding the `device_id` from the IoT device:

---

# 🖼️ PawPal Frontend

This is the **Streamlit-based dashboard** for **PawPal**, providing an intuitive interface to start the session and view the summarize dashboard.

## ⚙️ Prerequisites

### ✅ Backend Must Be Running

The frontend **requires the backend FastAPI server to be up and running** to enable full functionality.  
If the backend is not running, you’ll be limited to **read-only access** to data from MongoDB (demo mode).

Start the backend with:

```bash
uvicorn app:app --host 0.0.0.0 --port 11080
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

- Live communication with PawPal via the backend
- Device-linked chat and metadata display
- Demo mode with read-only database view if backend is offline
- Logs, interaction records, and response insights

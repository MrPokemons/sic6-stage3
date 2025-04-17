# Samsung Innovation Campus: Stage 3 Assignment

| Group Informations  |   |
|---------------|---------------|
| Group Code  | UNI422  |
| Group Name  | rarevolution  |
| Team  | - Adeline Charlotte Augustinne<br>- Angeline Rachel<br>- Anastashia Ellena Widjaja<br>- Rowen Nicholas    |

---

# Setting Up IoT
Board: ESP32 A1S 
Speaker terkoneksi ke ESP32 A1S dengan kabel melalui port yang sudah ada di board.

Langkah-langkah setup IoT:
1. Menginstall Arduino IDE dari situs resmi (https://www.arduino.cc/en/software) 
2. Menambahkan file-file library Arduino yang digunakan.
    Library-library yang digunakan meliputi:
        - Adafruit_BusIO (https://github.com/adafruit/Adafruit_BusIO)
        - Arduino Audio Tools by P Schatzmann (https://github.com/pschatzmann/arduino-audio-tools)
        - Arduino_DebugUtils (https://github.com/arduino-libraries/Arduino_DebugUtils)
        - Arduino RS458 (https://github.com/arduino-libraries/ArduinoRS485)
        - Arduino_SerialUpdater (https://github.com/arduino-libraries/Arduino_SerialUpdater)
        - ES8388 by thaaraak (https://github.com/thaaraak/es8388)
        - WebSockets 
    File-file dapat diakses pada folder: `IoT/libraries.`
    Di copy-paste ke folder: `~/Arduino/libraries`
3. Di dalam Arduino IDE, import file sketch yang dibutuhkan
4. Konfigurasi board (pilih ESP32 Dev Module) & port yang tersambung
5. Verify sketch
    Diakses melalui ombol atas kanan dengan icon centang
6. Upload sketch to board & menjalankan sketch 
    Diakses melalui tombol atas kanan dengan icon panah

---

# Setting Up Backend


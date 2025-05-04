#include <Arduino.h>
#include <driver/i2s.h>
#include "es8388.h"
#include "Wire.h"
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <freertos/task.h>
#include <ArduinoJson.h>


// ============ WIFI & WEBSOCKET CONFIGS ============

// === WiFi Config ===
const char* ssid = "DOWNEY";
const char* password = "r4ch3lkh0";

// === WebSocket Config ===
const char* websocket_server_address = "192.168.198.120";
const uint16_t websocket_server_port = 11080;
const char* websocket_path = "/api/v1/pawpal/conversation/cincayla?stream_audio=device";

WebSocketsClient webSocket;
bool shouldReconnect = false;
unsigned long lastReconnectAttempt = 0;
const unsigned long reconnectInterval = 5000; // 5 seconds


// ============ I2S & RECORDING CONFIGS ============

// === I2S Config ====
#define I2S_PORT I2S_NUM_0
#define I2S_WS 25 
#define I2S_SCK 27      // SCK = BCLK
#define I2S_SD_IN 35    

// Recording Parameters
// use 16khz for recording
#define I2S_REC_SAMPLE_RATE 16000 
#define I2S_REC_BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_16BIT
#define I2S_REC_CHANNELS 1 // mono for voice rec

es8388 codec;

// buffers for reading audio samples
#define AUDIO_CHUNK_SAMPLES 1024
#define AUDIO_CHUNK_SIZE_BYTES (AUDIO_CHUNK_SAMPLES * (I2S_REC_BITS_PER_SAMPLE / 8) * I2S_REC_CHANNELS)
#define RECORD_BUFFER_SIZE (AUDIO_CHUNK_SIZE_BYTES * 2)
uint8_t recordBuffer[RECORD_BUFFER_SIZE];

// === Recording Control Flags ===
volatile bool isRecording = false;
unsigned long recordingStartTime = 0;

// --- Recording Duration Limit ---
const unsigned long MAX_RECORDING_DURATION_MS = 10000; // Limit recording to 10 seconds



// ============ WEBSOCKET DATA CHUNKING CONFIGS ============

// === WS Data Chunking ====
// based on backend logic
const char* JSON_DELIMITER = "---ENDJSON---";
#define JSON_DELIMITER_LEN 13 

// buffers for data chunking
#define JSON_MAX_SIZE 256
#define SEND_BUFFER_SIZE (JSON_MAX_SIZE + JSON_DELIMITER_LEN + AUDIO_CHUNK_SIZE_BYTES)
uint8_t sendBuffer[SEND_BUFFER_SIZE];

volatile int outgoingSequence = 1;


// ============ MULTITHREADING WITH FREERTOS ============

// --- FreeRTOS Task Handle ---
TaskHandle_t audioRecordTaskHandle = NULL;



// --- Forward declarations ---
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);
void codecInitRecording();
void I2SinitRecording();
void audioRecordTask(void* parameter);
void connectWiFi();

// Function to handle WebSocket events
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("[WSc] Disconnected");
            shouldReconnect = true;
            lastReconnectAttempt = millis();
            // stop recording on disconnect
            if (isRecording) {
                Serial.println("[WSc] Disconnected during recording. Signaling recording task to stop.");
                isRecording = false;
            }
            break;

        case WStype_CONNECTED:
            Serial.println("[WSc] Connected to server");
            shouldReconnect = false;
            break;

        case WStype_TEXT: {
            String message = String((char*)payload, length);
            Serial.printf("[WSc] Received Text: %s\n", message.c_str());

            if (message.equalsIgnoreCase("microphone")) {
                if (!isRecording) {
                    Serial.println("[WSc] Received 'microphone'. Signaling recording task to start.");
                    isRecording = true; // signal task to start recording
                    outgoingSequence = 1; // reset seq
                    recordingStartTime = millis(); // start timer 
                } else {
                    Serial.println("[WSc] Received 'microphone', but already recording.");
                }
            } else if (message.equalsIgnoreCase("speaker")) {
                 if (isRecording) {
                    Serial.println("[WSc] Received 'speaker'. Signaling recording task to stop.");
                    isRecording = false;
                 } else {
                    Serial.println("[WSc] Received 'speaker', but not currently recording.");
                 }
            } else {
                Serial.printf("[WSc] Received unknown text command: %s\n", message.c_str());
            }
            break;
        }

        case WStype_BIN:
            Serial.printf("[WSc] Received BIN message (%zu bytes)\n", length);
            break;

        case WStype_ERROR:
            Serial.printf("[WSc] Error occurred, code: %d\n", payload ? *payload : -1);
            shouldReconnect = true;
            lastReconnectAttempt = millis();
            // stop recording on error
            if (isRecording) {
                Serial.println("[WSc] Error during recording. Signaling recording task to stop.");
                isRecording = false;
            }
            break;
        default:
            break;
    }
}

// init codec for recording mode
void codecInitRecording() {
    TwoWire wire(0);
    wire.setPins(33, 32);
    codec.begin(&wire);

    // configure for recording: ADC enabled, DAC disabled
    es_dac_output_t dac_output_rec = DAC_OUTPUT_MIN;
    es_adc_input_t adc_input_rec = ADC_INPUT_LINPUT2_RINPUT2;
    codec.config(I2S_REC_SAMPLE_RATE, dac_output_rec, adc_input_rec, 90);
    Serial.println("Codec configured for recording (ADC enabled, DAC disabled).");
}

// init I2S peripherals
void I2SinitRecording() {
    i2s_config_t i2s_rx_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX), // I2S mode master
        .sample_rate = I2S_REC_SAMPLE_RATE,
        .bits_per_sample = I2S_REC_BITS_PER_SAMPLE,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT, // Or I2S_CHANNEL_FMT_RIGHT if using right channel
        .communication_format = I2S_COMM_FORMAT_STAND_I2S, 
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 6, 
        .dma_buf_len = 512,
        .use_apll = false, 
        .tx_desc_auto_clear = false, 
        .fixed_mclk = 0
    };

    i2s_pin_config_t i2s_rx_pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = -1,
        .data_in_num = I2S_SD_IN
    };

    // install I2S driver
    esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_rx_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("Error installing I2S RX driver: %d\n", err);
    } else {
        Serial.println("I2S RX driver installed.");
    }

    // set I2S pins
    err = i2s_set_pin(I2S_PORT, &i2s_rx_pin_config);
    if (err != ESP_OK) {
        Serial.printf("Error setting I2S RX pins: %d\n", err);
    } else {
        Serial.println("I2S RX pins set.");
    }

    // set clock for recording rate
    err = i2s_set_clk(I2S_PORT, i2s_rx_config.sample_rate, i2s_rx_config.bits_per_sample, (i2s_channel_t)I2S_REC_CHANNELS);
    if (err != ESP_OK) {
        Serial.printf("Error setting I2S RX clock: %d\n", err);
    } else {
        Serial.printf("I2S RX clock set to %lu Hz.\n", i2s_rx_config.sample_rate);
    }
}

// --- FreeRTOS Task for Audio Recording and Sending ---
void audioRecordTask(void* parameter) {
    Serial.println("Audio recording task started. Waiting for 'microphone' command...");

    for (;;) {
        if (isRecording) {
            Serial.println("Recording task: 'isRecording' is true. Preparing for recording session.");

            // --- Configure I2S and Codec for Recording ---
            // These must be initialized *after* isRecording becomes true
            // because the driver needs to be active only when recording.
            I2SinitRecording();
            codecInitRecording();

            // --- Start Recording Loop ---
            Serial.println("Recording task: Entering active recording loop.");
            size_t bytes_read = 0;
            // Calculate bytes to read based on samples per chunk * bytes per sample * channels
            size_t bytes_to_read = AUDIO_CHUNK_SAMPLES * (I2S_REC_BITS_PER_SAMPLE / 8) * I2S_REC_CHANNELS;

            while (isRecording && WiFi.status() == WL_CONNECTED && webSocket.isConnected()) {

                bool isLastChunk = false;
                if (millis() - recordingStartTime >= MAX_RECORDING_DURATION_MS) {
                    isLastChunk = true;
                    Serial.printf("Recording duration (%lu ms) reached. Preparing final chunk.\n", MAX_RECORDING_DURATION_MS);
                }

                esp_err_t read_err = i2s_read(I2S_PORT, recordBuffer, bytes_to_read, &bytes_read, pdMS_TO_TICKS(50));

                if (read_err != ESP_OK && read_err != ESP_ERR_TIMEOUT) {
                    Serial.printf("Error reading from I2S RX: %d\n", read_err);
                    continue;
                }

                if (bytes_read > 0) {

                    // --- Prepare JSON Metadata ---
                    StaticJsonDocument<JSON_MAX_SIZE> jsonDoc;
                    jsonDoc["seq"] = outgoingSequence;
                    jsonDoc["sample_rate"] = I2S_REC_SAMPLE_RATE;
                    jsonDoc["channels"] = I2S_REC_CHANNELS;
                    jsonDoc["dtype"] = "int16";

                    // set total_seq = current_seq only if it is the last chunk
                    if (isLastChunk) {
                        jsonDoc["total_seq"] = outgoingSequence;
                        Serial.printf("Setting total_seq = %d for chunk %d (FINAL)\n", outgoingSequence, outgoingSequence);
                    } else {
                         jsonDoc["total_seq"] = 30000;
                    }

                    // serialize JSON
                    size_t json_len = serializeJson(jsonDoc, sendBuffer, JSON_MAX_SIZE);
                    if (json_len == 0 || json_len >= JSON_MAX_SIZE) {
                        Serial.println("Error serializing JSON or JSON too large for send buffer. Stopping recording.");
                        isRecording = false; 
                        continue;
                    }

                    // copy delimiter into the send buffer after the JSON
                    memcpy(sendBuffer + json_len, JSON_DELIMITER, JSON_DELIMITER_LEN);

                    // copy audio chunk into the send buffer after the delimiter
                    memcpy(sendBuffer + json_len + JSON_DELIMITER_LEN, recordBuffer, bytes_read);

                    // calculate total size of the message
                    size_t total_msg_size = json_len + JSON_DELIMITER_LEN + bytes_read;

                    // send the combined JSON, delimiter, and audio data
                    if (webSocket.sendBIN(sendBuffer, total_msg_size)) {
                        Serial.printf("Sent chunk %d (%zu bytes audio, %zu bytes total)%s\n",
                                      outgoingSequence, bytes_read, total_msg_size, isLastChunk ? " (FINAL)" : "");
                        outgoingSequence++;

                        // stop recording if last chunk 
                        if (isLastChunk) {
                             isRecording = false;
                             Serial.println("Recording task: Final chunk sent. Signaling stop.");
                        }

                    } else {
                        Serial.println("Failed to send WebSocket chunk. Signaling recording task to stop.");
                        isRecording = false;
                    }

                } else {
                    // bytes_read was 0 (likely due to timeout)
                    if (isLastChunk) {
                         Serial.println("Recording task: Duration reached, but 0 bytes read. Signaling stop.");
                         isRecording = false;
                    }
                }

                vTaskDelay(pdMS_TO_TICKS(1)); // Yield within the active loop
            }

            Serial.println("Recording task: Active recording loop ended.");


            // ======== TODO: CODEC.CONFIG DEBUG, SYNTAX CAUSES BOARD RESET! ========

            // --- Clean up I2S and Codec ---
            // These are done when the inner while loop condition becomes false
            // (either isRecording is false, WiFi disconnected, or WS disconnected)

            // Configure codec for idle state: Disable ADC and DAC
            // es_dac_output_t dac_output_idle = DAC_OUTPUT_MIN;
            // es_adc_input_t adc_input_idle = ADC_INPUT_MIN;
            // codec.config(16000, dac_output_idle, adc_input_idle, 0);
            // Serial.println("Codec configured for idle state (ADC/DAC disabled).");

            i2s_driver_uninstall(I2S_PORT);
            Serial.println("I2S RX driver uninstalled.");

            Serial.println("Recording task: Finished recording session cleanup.");


        } 
        
        // yield task
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}


// Connect to WiFi
void connectWiFi() {
    Serial.printf("Connecting to WiFi %s\n", ssid);
    WiFi.begin(ssid, password);

    unsigned long startAttemptTime = millis();
    const unsigned long timeout = 40000; // 40 seconds

    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < timeout) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ Connected to Wi-Fi!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ Failed to connect to Wi-Fi.");
        Serial.print("WiFi status code: ");
        Serial.println(WiFi.status());
    }
}


void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("ESP32 Audio Recorder & Sender (Streaming)");

    connectWiFi();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Initializing Codec I2C...");

        // Initialize codec I2C communication in setup
        TwoWire wire(0);
        wire.setPins(33, 32);
        codec.begin(&wire);
        Serial.println("Codec I2C communications initialized.");

        // Codec config and I2S init are moved into the task, triggered by isRecording

        // WebSocket server setup for main loop
        Serial.println("Connecting to WebSocket...");
        webSocket.onEvent(webSocketEvent);
        // webSocket.setReconnectInterval(reconnectInterval); // Optional: WebSocket library can handle some reconnects
        webSocket.begin(websocket_server_address, websocket_server_port, websocket_path);

        xTaskCreatePinnedToCore(
            audioRecordTask,      // Task function
            "AudioRecordTask",    // Name of the task
            8192,                 // Stack size (bytes) - increase if needed for complex processing
            NULL,                 // Parameter to pass to the task
            5,                    // Task priority (higher number = higher priority)
            &audioRecordTaskHandle, // Task handle (optional)
            0                     // Core to run the task on (0 or 1) - Core 0 is often used for WiFi/BT
        );
        if (audioRecordTaskHandle == NULL) {
            Serial.println("Error creating Audio Record Task!");
        } else {
            Serial.println("Audio Record Task created, waiting for command.");
        }

    } else {
        Serial.println("WiFi connection failed. Audio recording task will not start.");
    }

    Serial.println("Setup finished.");
}

void loop() {
    webSocket.loop();

    if (shouldReconnect && millis() - lastReconnectAttempt >= reconnectInterval) {
        Serial.println("Attempting WebSocket reconnection...");
        if (WiFi.status() == WL_CONNECTED) {
            webSocket.begin(websocket_server_address, websocket_server_port, websocket_path);
            lastReconnectAttempt = millis(); 
        } else {
            Serial.println("WiFi not connected, cannot attempt WebSocket reconnection.");
            Serial.printf("Attempting Wi-Fi reconnection.")
            connectWiFi()
        }
    }

    vTaskDelay(pdMS_TO_TICKS(1));
}
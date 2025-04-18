#include <Arduino.h>
#include <WebSocketsServer.h>
#include <WiFi.h>
#include <driver/i2s.h>
#include "es8388.h"
#include "Wire.h"

// --- Device Metadata ---
const char* device_id = "2b129436-1a2d-11f0-9045-6ac49b7e4ceb";

// --- WiFi Setup ---
const char* ssid = "";
const char* password = "";

// --- I2S / Audio Config ---
#define I2S_PORT        I2S_NUM_0
#define I2S_WS          25
#define I2S_SCK         27
#define I2S_SD_OUT      26
#define I2S_SD_IN       35
#define I2S_MCK         0 // optional

#define SAMPLE_RATE         16000
#define BITS_PER_SAMPLE     I2S_BITS_PER_SAMPLE_16BIT
#define CHANNELS            2
#define I2S_BUFFER_LEN      1024

// --- WebSocket Setup ---
WebSocketsServer webSocket = WebSocketsServer(81);
bool realtimePassthrough = true;
String currentCommand = "";

es8388 codec;

void initCodec() {
  TwoWire wire(0);
  wire.setPins(33, 32); // SDA, SCL
  codec.begin(&wire);
  es_adc_input_t adc_input = ADC_INPUT_LINPUT2_RINPUT2;
  es_dac_output_t dac_output = (es_dac_output_t)(DAC_OUTPUT_LOUT1 | DAC_OUTPUT_ROUT1);
  codec.config(16, dac_output, adc_input, 90);
}

void initI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = BITS_PER_SAMPLE,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S_MSB,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = I2S_BUFFER_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_SD_OUT,
    .data_in_num = I2S_SD_IN
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_set_clk(I2S_PORT, SAMPLE_RATE, BITS_PER_SAMPLE, (i2s_channel_t)CHANNELS);
}

// --- Record 2 seconds of audio ---
void recordAudio(uint8_t** buffer, size_t* length) {
  const int durationInSeconds = 5;
  const size_t bytesToRecord = SAMPLE_RATE * (BITS_PER_SAMPLE / 8) * CHANNELS * durationInSeconds;

  *buffer = (uint8_t*) malloc(bytesToRecord);  // Correctly assign to *buffer

  if (!*buffer) {
    Serial.println("Failed to allocate audio buffer!");
    *length = 0;
    return;
  }

  size_t totalRead = 0;
  size_t bytesRead = 0;
  while (totalRead < bytesToRecord) {
    i2s_read(I2S_PORT, *buffer + totalRead, bytesToRecord - totalRead, &bytesRead, portMAX_DELAY);
    totalRead += bytesRead;
  }
  *length = totalRead;
}


// --- Play audio received via WebSocket ---
void playAudio(uint8_t* buffer, size_t length) {
  size_t bytesWritten = 0;
  size_t totalWritten = 0;
  while (totalWritten < length) {
    i2s_write(I2S_PORT, buffer + totalWritten, length - totalWritten, &bytesWritten, portMAX_DELAY);
    totalWritten += bytesWritten;
  }
}

// --- WebSocket Event Handler ---
void webSocketEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_TEXT: {
      String msg = (char*)payload;
      Serial.println("WS Command: " + msg);

      if (msg == "microphone") {
        realtimePassthrough = false;
        uint8_t* audioBuffer;
        size_t len;
        recordAudio(&audioBuffer, &len);
        if (len > 0) {
          webSocket.sendBIN(num, audioBuffer, len);
        }
        free(audioBuffer);
        realtimePassthrough = true;
      } else if (msg == "speaker") {
        realtimePassthrough = false;
        currentCommand = "speaker";
      }
      break;
    }

    case WStype_BIN:
      if (currentCommand == "speaker") {
        Serial.println("Received audio to play");
        playAudio(payload, length);
        currentCommand = "";
        realtimePassthrough = true;
      }
      break;
  }
}

// --- Setup ---
void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());

  initCodec();
  initI2S();

  webSocket.begin();
  webSocket.onEvent(webSocketEvent);

  Serial.println("WebSocket server started on port 81");
}

// --- Main Loop ---
void loop() {
  webSocket.loop();

  if (realtimePassthrough) {
    static uint8_t buffer[I2S_BUFFER_LEN];
    size_t bytes_read, bytes_written;
    i2s_read(I2S_PORT, buffer, I2S_BUFFER_LEN, &bytes_read, portMAX_DELAY);
    i2s_write(I2S_PORT, buffer, bytes_read, &bytes_written, portMAX_DELAY);
  }
}
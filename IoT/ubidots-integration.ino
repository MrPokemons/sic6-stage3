#include <Arduino.h>
#include <driver/i2s.h>
#include "es8388.h"
#include "Wire.h"
#include <WiFi.h>
#include <HTTPClient.h>

// config connect ke wifi & ubidots
const char* ssid = "C-C2.4";
const char* password = "QweR1357";
const char* UBIDOTS_TOKEN = "BBUS-2cYGjwEINDF6954ftBsKh7HhIlrbI8";
const char* UBIDOTS_DEVICE = "esp32-a1s-voice-input";
const char* UBIDOTS_VARIABLE = "voice_level";

#define VOICE_THRESHOLD 100     // hanya akan send data apabila audio input level > 100
#define SEND_INTERVAL 5000

#define I2S_PORT        I2S_NUM_0
#define I2S_WS          25
#define I2S_SCK         27
#define I2S_SD_OUT      26  
#define I2S_SD_IN       35
#define I2S_MCK         0

#define SAMPLE_RATE         16000
#define BITS_PER_SAMPLE     I2S_BITS_PER_SAMPLE_16BIT
#define CHANNELS            2
#define I2S_BUFFER_LEN      1024

es8388 codec;

void codecInit() {
  TwoWire wire(0);
  wire.setPins(33, 32)
  codec.begin(&wire);
  es_adc_input_t adc_input = ADC_INPUT_LINPUT2_RINPUT2;
  es_dac_output_t dac_output = (es_dac_output_t)(DAC_OUTPUT_LOUT1 | DAC_OUTPUT_ROUT1);
  codec.config(16, dac_output, adc_input, 90);
}

void I2Sinit() {
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

// untuk connect ke wifi
void connectWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
  }
  Serial.println("Connected to Wi-Fi lokal");
}

// kirim input audio level ke ubidots
void sendToUbidots(float voiceLevel) {
  if (WiFi.status() != WL_CONNECTED){
    Serial.println("Wi-Fi belum terhubung");
    return
  }

  HTTPClient http;
  http.begin("http://industrial.api.ubidots.com/api/v1.6/devices/" + String(UBIDOTS_DEVICE));
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Auth-Token", UBIDOTS_TOKEN);
  String payload = "{\"" + String(UBIDOTS_VARIABLE) + "\":" + String(voiceLevel) + "}";
  int httpResponseCode = http.POST(payload);
  Serial.printf("Ubidots Response: %d\n", httpResponseCode);
  http.end();
}

void setup() {
  Serial.begin(115200);
  connectWiFi();
  initCodec();
  initI2S();
}

void loop() {
  static int16_t buffer[I2S_BUFFER_LEN];
  static size_t bytes_read, bytes_written;
  static unsigned long lastUbidotsTime = 0;

  // melakukan playback semua audio yang masuk ke mic dengan di-output speaker
  i2s_read(I2S_PORT, &buffer, sizeof(buffer), &bytes_read, portMAX_DELAY);
  i2s_write(I2S_PORT, &buffer, bytes_read, &bytes_written, portMAX_DELAY);

  // menghitung level input 
  int sampleCount = bytes_read / sizeof(int16_t);
  double sumSq = 0;

  for (int i = 0; i < sampleCount; i += CHANNELS) {
    int16_t sample = buffer[i];
    sumSq += sample * sample;
  }

  float rms = sqrt(sumSq / (sampleCount / CHANNELS));
  Serial.printf("Voice Level (RMS): %.2f\n", rms);

  // apabila audio level melebihi threshold 100 maka akan dikirim ke Ubidots
  if (rms > VOICE_THRESHOLD && millis() - lastUbidotsTime > UBIDOTS_INTERVAL) {
    sendToUbidots(rms);
    lastUbidotsTime = millis();
  }
}
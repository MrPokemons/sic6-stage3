#include "AudioKitHAL.h"
#include "SineWaveGenerator.h"

AudioKit kit;
SineWaveGenerator wave;
const int BUFFER_SIZE = 1024;
uint8_t buffer[BUFFER_SIZE];

void setup() {
  Serial.begin(115200);
  // open in write mode
  auto cfg = kit.defaultConfig(KitOutput);
  cfg.sample_rate = AUDIO_HAL_22K_SAMPLES;
  kit.begin(cfg);

  // 1000 hz
  wave.setFrequency(1000);
  wave.setSampleRate(cfg.sampleRate());
}

void loop() {
  size_t l = wave.read(buffer, BUFFER_SIZE);
  kit.write(buffer, l);
}

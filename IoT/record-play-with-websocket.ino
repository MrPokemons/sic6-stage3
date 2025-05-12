#include <Arduino.h>
#include <driver/i2s.h>
#include "es8388.h"
#include "Wire.h"
#include <WiFi.h>
#include <WiFiManager.h>
#include <WebSocketsClient.h>
#include <freertos/task.h>
#include <ArduinoJson.h>

// ==== WiFi Configs ====
const char* ssid = "First Home";
const char* password = "tanyaAdeline";

const char* websocket_server_address = "192.168.68.113";
const uint16_t websocket_server_port = 11080;
const char* websocket_path = "/api/v1/pawpal/conversation/cincayla?stream_audio=websocket";

WebSocketsClient webSocket;
bool shouldReconnect = false;
unsigned long lastReconnectAttempt = 0;
const unsigned long reconnectInterval = 5000;

#define COMMON_SAMPLE_RATE 16000
#define COMMON_BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_16BIT

// ==== PINOUTS ====

#define I2S_PORT        I2S_NUM_0
#define I2S_WS          25
#define I2S_SCK         27
#define I2S_SD_OUT      26
#define I2S_SD_IN       35
#define TEST_LED_PIN    5

es8388 codec;

// ==== Task Control Flags ====
volatile bool startRecording = false;
volatile bool isRecordingActive = false; 


// ==== Recording Params and Buffers ====
#define REC_DURATION_MS 5000
// record reads 16khz, 16bit, mono --> convert to stereo

// --> BUFFERS FOR STEREO
#define REC_I2S_READ_SAMPLES 1024 // read this many stereo samples from I2S RX
#define REC_I2S_READ_BYTES (REC_I2S_READ_SAMPLES * (COMMON_BITS_PER_SAMPLE / 8) * 2)
uint8_t recordStereoBuffer[REC_I2S_READ_BYTES]; // buffer for reading stereo 

// --> BUFFERS FOR EXTRACTED MONO
#define REC_MONO_DATA_BYTES (REC_I2S_READ_SAMPLES * (COMMON_BITS_PER_SAMPLE / 8) * 1)
uint8_t recordMonoBuffer[REC_MONO_DATA_BYTES];


// --- WebSocket & JSON Serialization Configs ---
const char* JSON_DELIMITER = "---ENDJSON---";
#define JSON_DELIMITER_LEN 13
#define JSON_MAX_SIZE 256
#define WS_SEND_BUFFER_SIZE (JSON_MAX_SIZE + JSON_DELIMITER_LEN + REC_MONO_DATA_BYTES)
uint8_t wsSendBuffer[WS_SEND_BUFFER_SIZE];

volatile int outgoingSequence = 0; // sequence number for total chunks being sent to server

// --- Playback Reception and Streaming (Incorporating logic from the second code) ---
const char* PLAYBACK_JSON_DELIMITER = "---ENDJSON---"; 
const size_t PLAYBACK_JSON_DELIMITER_LEN = strlen(PLAYBACK_JSON_DELIMITER);

volatile int currentExpectedSequence = 1;
volatile int currentTotalSeq = -1;
volatile uint32_t currentSampleRate = 0;
volatile uint16_t currentChannels = 0;
volatile uint16_t currentBitsPerSample = 0;
volatile bool isPlayingSegment = false; // currently processing a playback segment or not

// Buffer for audio data conversion before writing to I2S TX
#define PLAYBACK_OUTPUT_BUFFER_CHUNK_BYTES 2048
uint8_t playbackConversionBuffer[PLAYBACK_OUTPUT_BUFFER_CHUNK_BYTES];


// --- FreeRTOS task handles & forward declarations ---
TaskHandle_t audioRecordTaskHandle = NULL;

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);
void initCodecSingleConfig();
void initI2SDualMode();
void audioRecordTask(void* parameter);
bool parseAndProcessBinaryMessage(const uint8_t* data, size_t dataLength);
bool convertAndWriteAudioChunk(const uint8_t* audioData, size_t audioDataSize, uint16_t sourceBitsPerSample, uint16_t sourceChannels);


void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("[WSc] Disconnected");
            shouldReconnect = true;
            lastReconnectAttempt = millis();
            if (isRecordingActive) {
                Serial.println("[WSc] WS Disconnected during recording. Signaling task to stop.");
                startRecording = false;
            }

            // reset playback state vars
            currentExpectedSequence = 1;
            currentTotalSeq = -1;
            currentSampleRate = 0;
            currentChannels = 0;
            currentBitsPerSample = 0;
            isPlayingSegment = false;
            break;

        case WStype_CONNECTED:
            Serial.println("[WSc] Connected to server");
            shouldReconnect = false;

            // reset playback state vars
            currentExpectedSequence = 1;
            currentTotalSeq = -1;
            currentSampleRate = 0;
            currentChannels = 0;
            currentBitsPerSample = 0;
            isPlayingSegment = false;
            break;

        case WStype_TEXT: {
            String message = String((char*)payload, length);
            Serial.printf("[WSc] Received Text: %s\n", message.c_str());

            if (message.startsWith("microphone")) {
                Serial.println("[WSc] Received 'microphone;'. Signaling recording task to start.");
                if (isPlayingSegment) {
                     Serial.println("Signaling playback segment to stop.");
                     // stop processing next incoming chunks for this segment
                     // signal that this is the last chunk
                     currentExpectedSequence = 1;
                     currentTotalSeq = -1;
                     currentSampleRate = 0;
                     currentChannels = 0;
                     currentBitsPerSample = 0;
                     isPlayingSegment = false;
                }
                // signal record task to start when already stop recording
                if (!isRecordingActive) {
                     outgoingSequence = 0;
                     startRecording = true;
                } else {
                    Serial.println("Recording already active.");
                }

            }
            else {
                Serial.printf("[WSc] Received unknown text command: %s\n", message.c_str());
            }
            break;
        }

        case WStype_BIN:
            // Serial.printf("[WSc] Received BIN message (%zu bytes). Processing for playback.\n", length);
             if (isRecordingActive) {
                // Serial.println("[WSc] Received BIN during recording. Signaling recording task to stop.");
                startRecording = false;
                vTaskDelay(pdMS_TO_TICKS(50));
             }
            parseAndProcessBinaryMessage(payload, length);
            isPlayingSegment = (currentTotalSeq != -1 && currentExpectedSequence <= currentTotalSeq);
            break;


        case WStype_ERROR:
           Serial.printf("[WSc] Error occurred, code: %d\n", payload ? *payload : -1);
           shouldReconnect = true;
           lastReconnectAttempt = millis();
           // signal tasks to stop
           if (isRecordingActive) {
               Serial.println("[WSc] WS Error during recording. Signaling task to stop.");
               startRecording = false;
           }
           // reset playback state vars
           currentExpectedSequence = 1;
           currentTotalSeq = -1;
           currentSampleRate = 0;
           currentChannels = 0;
           currentBitsPerSample = 0;
           isPlayingSegment = false;
          break;
        default:
          break;
    }
}


// parse binary message, delimit JSON 
bool parseAndProcessBinaryMessage(const uint8_t* data, size_t dataLength) {
    // Serial.println("Parsing binary message...");
    const uint8_t* delimiterPos = (uint8_t*)memmem(data, dataLength, PLAYBACK_JSON_DELIMITER, PLAYBACK_JSON_DELIMITER_LEN);

    if (!delimiterPos) {
        Serial.println("[WSc] Error: Delimiter not found in binary chunk.");
        isPlayingSegment = false; // stop playback processing 
        return false;
    }

    size_t jsonLength = delimiterPos - data;
    size_t audioDataOffset = delimiterPos - data + PLAYBACK_JSON_DELIMITER_LEN;
    size_t audioDataLength = dataLength - audioDataOffset;


    // ERROR HANDLING for missing data
    if (jsonLength == 0) {
         Serial.println("[WSc] Error: JSON metadata is missing before delimiter.");
         isPlayingSegment = false;
         return false;
    }
     if (audioDataLength == 0) {
         Serial.println("[WSc] Warning: Binary chunk has metadata but no audio data.");
         // continue processing metadata because segment might end with an empty chunk
         // no stopping 
     }


     // extract and parse JSON
     StaticJsonDocument<JSON_MAX_SIZE> doc;

    if (jsonLength >= 256) {
        Serial.println("[WSc] Error: JSON metadata too large for buffer.");
        isPlayingSegment = false;
        return false;
    }
    char jsonString[jsonLength + 1];
    memcpy(jsonString, data, jsonLength);
    jsonString[jsonLength] = '\0';

    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
        Serial.printf("[WSc] JSON parsing failed: %s\n", error.c_str());
         isPlayingSegment = false;
        return false;
    }

    // extract metadata
    int seq = doc["seq"] | -1;
    int total_seq = doc["total_seq"] | -1;
    uint32_t sample_rate = doc["sample_rate"] | 0;
    uint16_t channels = doc["channels"] | 0;
    const char* dtype_str = doc["dtype"] | "";

    if (seq == -1 || total_seq == -1 || sample_rate == 0 || channels == 0 || strlen(dtype_str) == 0) {
        Serial.println("[WSc] Error: Missing metadata keys in JSON.");
        isPlayingSegment = false;
        return false;
    }

    uint16_t bitsPerSample = 0;
    if (strcmp(dtype_str, "int16") == 0) {
        bitsPerSample = 16;
    } else if (strcmp(dtype_str, "float32") == 0) {
         bitsPerSample = 32;
    } 

    if (bitsPerSample == 0) {
        Serial.printf("[WSc] Error: Unsupported dtype: %s\n", dtype_str);
        isPlayingSegment = false;
        return false;
    }

    // STREAMING LOGIC 
    if (seq == 1 && currentExpectedSequence == 1) {
        Serial.printf(
          "[WSc] Starting new playback segment. Seq %d/%d. Rate=%lu, Ch=%u, Bits=%u\n",
          seq,
          total_seq,
          sample_rate,
          channels,
          bitsPerSample
        );

        currentTotalSeq = total_seq;
        currentSampleRate = sample_rate;
        currentChannels = channels;
        currentBitsPerSample = bitsPerSample;

        // set the I2S clock to match the received audio sample rate
        esp_err_t clk_err = i2s_set_clk(I2S_PORT, currentSampleRate, COMMON_BITS_PER_SAMPLE, (i2s_channel_t)2);
        if (clk_err != ESP_OK) {
            Serial.printf("[WSc] Error setting I2S clock to %lu Hz: %d. Cannot play segment.\n", currentSampleRate, clk_err);
             // reset state vars on error
            currentExpectedSequence = 1;
            currentTotalSeq = -1;
            currentSampleRate = 0;
            currentChannels = 0;
            currentBitsPerSample = 0;
            isPlayingSegment = false;
            return false;
        }
         Serial.printf("[WSc] I2S clock set to %lu Hz (16-bit stereo).\n", currentSampleRate);
         isPlayingSegment = true; // segment is being processed

    } else if (seq != currentExpectedSequence) {
        // out-of-order / missing chunk
        if (currentExpectedSequence == 1) {
             Serial.printf("[WSc] Warning: Received seq %d but expected 1 (new segment). Discarding chunk.\n", seq);
        } else {
             Serial.printf("[WSc] Warning: Received seq %d but expected %d. Discarding chunk.\n", seq, currentExpectedSequence);
        }

        if (currentExpectedSequence == 1) {
             // if client expected 1 and got something else
             // assume this is not the start of a valid segment
             isPlayingSegment = false;
         }
        return false;
    } else {
        // received the next expected chunk in sequence (for a multi-chunk segment)

        // validate metadata against the first chunk's metadata
         if (total_seq != currentTotalSeq) {
             Serial.println("[WSc] Warning: Subsequent chunk total_seq metadata mismatch! Segment might be corrupt.");
         }
          if (sample_rate != currentSampleRate || channels != currentChannels || bitsPerSample != currentBitsPerSample) {
              Serial.println("[WSc] Warning: Subsequent chunk audio format metadata mismatch!");
          }
         isPlayingSegment = true; // still processing the segment
    }

    // process and write the audio data for the current chunk 
    if (audioDataLength > 0 && isPlayingSegment) { // only process if data exists and segment is valid
        bool write_success = convertAndWriteAudioChunk(
          data + audioDataOffset, 
          audioDataLength,
          currentBitsPerSample,
          currentChannels
        );

        if (!write_success) {
            Serial.println("[WSc] Error writing audio chunk to I2S. Playback stopped for this segment.");
            isPlayingSegment = false; // stop processing segment on write error
        }

    } else if (audioDataLength == 0 && seq == currentTotalSeq && currentTotalSeq != -1) {
         Serial.println("[WSc] Received expected last (empty) chunk.");
         isPlayingSegment = false;
    } else if (audioDataLength > 0 && !isPlayingSegment) {
         Serial.println("[WSc] Received data but isPlayingSegment is false. Discarding data.");
         return false;
    }


    if (isPlayingSegment) {
        currentExpectedSequence++;
    }


    // check if the segment is complete
    if (currentTotalSeq != -1 && currentExpectedSequence > currentTotalSeq) {
        Serial.printf("[WSc] Playback Segment completed (processed %d chunks).\n", currentTotalSeq);

        // reset state vars for next segment
        currentExpectedSequence = 1;
        currentTotalSeq = -1;
        currentSampleRate = 0;
        currentChannels = 0;
        currentBitsPerSample = 0;
        isPlayingSegment = false;
    } else if (!isPlayingSegment && currentTotalSeq != -1 && currentExpectedSequence <= currentTotalSeq) {
        // isPlayingSegment became false due to error before segment is finished
        Serial.printf("[WSc] Playback Segment stopped prematurely due to error (at seq %d/%d).\n", seq, currentTotalSeq);
    }


    return isPlayingSegment || (currentTotalSeq != -1 && currentExpectedSequence > currentTotalSeq);
}


// convert received audio to 16-bit stereo
// write to speaker as output
bool convertAndWriteAudioChunk(const uint8_t* audioData, size_t audioDataSize, uint16_t sourceBitsPerSample, uint16_t sourceChannels) {

    if (audioDataSize == 0) return true;

    size_t sourceBytesPerSample = sourceBitsPerSample / 8;
    size_t sourceBytesPerFrame = sourceBytesPerSample * sourceChannels; // bytes per frame in source data
    size_t playbackBytesPerOutputFrame = (COMMON_BITS_PER_SAMPLE / 8) * 2; // 16bit stereo = 4 bytes per frame for I2S output

    if (sourceBytesPerFrame == 0 || playbackBytesPerOutputFrame == 0) {
         Serial.println("Error: Invalid sample/channel size calculation during conversion.");
         return false;
    }

    const uint8_t* currentInputPtr = audioData;
    size_t bytesRemaining = audioDataSize;

    // process incoming large audio chunk in smaller segments
    while (bytesRemaining > 0) {

        size_t availableSourceFrames = bytesRemaining / sourceBytesPerFrame;
        if (availableSourceFrames == 0) {
             Serial.printf("Warning: Remaining bytes (%zu) is less than a full source frame size (%zu).\n", bytesRemaining, sourceBytesPerFrame);
             break;
        }

        size_t targetOutputFrames = PLAYBACK_OUTPUT_BUFFER_CHUNK_BYTES / playbackBytesPerOutputFrame;
        size_t sourceFramesNeeded = (targetOutputFrames * playbackBytesPerOutputFrame) / sourceBytesPerFrame;

        // ensure we don't read more source frames than are available
        size_t framesToProcess = min(availableSourceFrames, sourceFramesNeeded);

        if (framesToProcess == 0) {
            Serial.println("Warning: Cannot process any frames in this iteration.");
            break;
        }

        size_t inputBytesToProcess = framesToProcess * sourceBytesPerFrame;
        size_t outputBytesToProduce = framesToProcess * playbackBytesPerOutputFrame;

        if (outputBytesToProduce > PLAYBACK_OUTPUT_BUFFER_CHUNK_BYTES) {
             Serial.printf("Error: Calculated outputBytesToProduce (%zu) exceeds buffer size (%zu).\n", outputBytesToProduce, PLAYBACK_OUTPUT_BUFFER_CHUNK_BYTES);
             return false;
        }

        // data conversion

        // target format 16-bit Stereo (COMMON_BITS_PER_SAMPLE=16, 2 channels)
        int16_t* outputSamples = (int16_t*)playbackConversionBuffer;
        size_t numOutputSamples = outputBytesToProduce / sizeof(int16_t);
        memset(playbackConversionBuffer, 0, PLAYBACK_OUTPUT_BUFFER_CHUNK_BYTES);

        //  convert 16-bit mono -> 16-bit stereo
        if (sourceBitsPerSample == 16 && sourceChannels == 1 && COMMON_BITS_PER_SAMPLE == 16 && 2 == 2) {
            const int16_t* inputSamples = (const int16_t*)currentInputPtr;
            size_t numInputSamples = inputBytesToProcess / sizeof(int16_t); // number of 16-bit mono samples

            for (size_t i = 0; i < numInputSamples; ++i) {
                int16_t sample = inputSamples[i];
                *outputSamples++ = sample; // left channel
                *outputSamples++ = sample; // right channel
            }
        }

        // convert 32-bit Float mono -> 16-bit stereo
        else if (sourceBitsPerSample == 32 && sourceChannels == 1 && COMMON_BITS_PER_SAMPLE == 16 && 2 == 2) {
             const float* inputSamples = (const float*)currentInputPtr;
             size_t numInputSamples = inputBytesToProcess / sizeof(float); // number of float32 mono samples

             for (size_t i = 0; i < numInputSamples; ++i) {
                 float sample_f32 = inputSamples[i];

                 // clipping and scaling from -1.0 to 1.0 range to 16-bit signed integer range
                 long sample_i32 = (long)(sample_f32 * 32767.0f); // scale to max 16-bit value
                 if (sample_i32 > 32767) sample_i32 = 32767;
                 else if (sample_i32 < -32768) sample_i32 = -32768; // correct min 16-bit value

                 int16_t sample = (int16_t)sample_i32;

                 *outputSamples++ = sample; // left channel
                 *outputSamples++ = sample; // right channel
             }
         }

         // convert 16-bit Stereo Source -> 16-bit Stereo Output
         // (no conversion, just copy
         // // assuming source data is already L/R interleaved 16-bit samples)
         else if (sourceBitsPerSample == 16 && sourceChannels == 2 && COMMON_BITS_PER_SAMPLE == 16 && 2 == 2) {
             memcpy(playbackConversionBuffer, currentInputPtr, inputBytesToProcess);
         }

         else {
            Serial.printf("Error: Conversion from Bits=%u, Ch=%u to 16-bit Stereo not implemented.\n",
                           sourceBitsPerSample, sourceChannels);
            isPlayingSegment = false;
            return false;
        }


        size_t bytes_written = 0;
        esp_err_t result = i2s_write(I2S_PORT, playbackConversionBuffer, outputBytesToProduce, &bytes_written, pdMS_TO_TICKS(100)); // Use a timeout

        if (result != ESP_OK) {
            Serial.printf("Error writing to I2S (converted chunk): Result %d\n", result);
            isPlayingSegment = false;
            return false;
        }
        if (bytes_written != outputBytesToProduce) {
             Serial.printf("Warning: Partial I2S write (converted chunk): Wrote %zu/%zu bytes.\n", bytes_written, outputBytesToProduce);
        }

        currentInputPtr += inputBytesToProcess;
        bytesRemaining -= inputBytesToProcess;

        vTaskDelay(pdMS_TO_TICKS(1));
    }

    // If the loop finished, all data was processed successfully (or with warnings)
    return isPlayingSegment; // Return current segment state
}


// ======= IMMEDIATELY SETUP BOARD FOR BOTH RX AND TX =======
// CODEC FUNCTIONS WILL NOT BE CALLED ANYWHERE ELSE OTHER THAN SETUP
// WILL CAUSE CONNECTION TO BREAK (IOT BOARD RESET)
void initCodecSingleConfig() {
    Serial.println("Initializing Codec with single config...");
    TwoWire wire(0);
    wire.setPins(33, 32);
    wire.begin();
    codec.begin(&wire);

    es_adc_input_t adc_input_config = ADC_INPUT_LINPUT2_RINPUT2;
    es_dac_output_t dac_output_config = (es_dac_output_t)(DAC_OUTPUT_LOUT1 | DAC_OUTPUT_ROUT1);

    Serial.printf("Codec config: Sample Rate=%lu, Output=%u, Input=%u, Volume=90\n",
                  (uint32_t)COMMON_SAMPLE_RATE, dac_output_config, adc_input_config);

    codec.config(COMMON_SAMPLE_RATE, dac_output_config, adc_input_config, 90);
    Serial.println("Codec Initialized with dual capability.");
}

// INIT I2S PERIPHERAL FOR BOTH RX AND TX
// NO MODE CONVERSION IN THE MIDDLE OF THE CODE
void initI2SDualMode() {
    Serial.println("Initializing I2S for TX|RX...");
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_RX),
        .sample_rate = COMMON_SAMPLE_RATE,
        .bits_per_sample = COMMON_BITS_PER_SAMPLE,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // use stereo format for I2S bus (L/R)
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 512, 
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_SD_OUT, // TX pin
        .data_in_num = I2S_SD_IN    // RX pin
    };

    esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
     if (err != ESP_OK) {
        Serial.printf("Error installing I2S driver: %d\n", err);
        while(1) { delay(100); }
    }
    err = i2s_set_pin(I2S_PORT, &pin_config);
     if (err != ESP_OK) {
        Serial.printf("Error setting I2S pins: %d\n", err);
         while(1) { delay(100); }
    }

    // set initial clock (redundant after install but good practice/debug)
    err = i2s_set_clk(I2S_PORT, i2s_config.sample_rate, i2s_config.bits_per_sample, (i2s_channel_t)2); // 2 channels (stereo)
     if (err != ESP_OK) {
        Serial.printf("Error setting initial I2S clock: %d\n", err);
         while(1) { delay(100); }
    }
    Serial.println("I2S TX|RX Initialized (16-bit Stereo).");
}


// FreeRTOS Task for Audio Recording & Sending
// Ensure outgoingSequence is declared ONLY ONCE globally:
// volatile int outgoingSequence = 0; // Example global declaration (initialize in setup or top-level)
void audioRecordTask(void* parameter) {
    Serial.println("Audio recording task started. Waiting for 'microphone;' command...");

    // Define a large number constant for the sequence number of non-final chunks
    const int LARGE_SEQ_NUMBER = 300000; // Used for total_seq on non-final chunks

    for (;;) { // Task loop runs forever
        // --- Debug Print 1 ---
        // outgoingSequence should be reset to 0 in webSocketEvent before startRecording is set true
        // Serial.printf("Task loop: Waiting for startRecording. outgoingSequence = %d\n", outgoingSequence);

        // This block executes when the webSocketEvent handler sets startRecording = true
        // The reset (outgoingSequence = 0;) is handled in the webSocketEvent's microphone case
        if (startRecording) {
            Serial.println("Task loop: startRecording is true. Entering session setup.");
            isRecordingActive = true;
            digitalWrite(TEST_LED_PIN, HIGH); // turn LED on
            startRecording = false; // Consume the start command

            // --- Debug Print 2 ---
            // This print helps confirm the value of outgoingSequence *after* the reset in webSocketEvent
            // and *before* the loop starts. It should be 0 if the reset worked correctly.
            Serial.printf("Task loop: Initial outgoingSequence upon entering setup = %d\n", outgoingSequence);


            // Calculate estimated total chunks for the *current* session duration
            unsigned long recordingStartTime = millis();
            size_t bytesReadStereo = 0;
            size_t bytesWrittenMono = 0;

            size_t totalExpectedMonoBytes = (COMMON_SAMPLE_RATE * (COMMON_BITS_PER_SAMPLE / 8) * 1 * REC_DURATION_MS) / 1000;
            int estimatedTotalSeq = (totalExpectedMonoBytes + REC_MONO_DATA_BYTES - 1) / REC_MONO_DATA_BYTES;
             if (estimatedTotalSeq == 0 && REC_DURATION_MS > 0) estimatedTotalSeq = 1; // Ensure at least 1 chunk for positive duration
            else if (estimatedTotalSeq == 0 && REC_DURATION_MS == 0) estimatedTotalSeq = 0; // 0 chunks for 0 duration


            Serial.printf("Recording task: Starting %lu ms recording. Estimated total chunks (for duration): %d\n", REC_DURATION_MS, estimatedTotalSeq);


            // The main recording loop:
            // Continue as long as active, connected, AND time not elapsed.
            // We no longer use (outgoingSequence < estimatedTotalSeq) to *stop* sending chunks.
            // The loop will run for the duration, and we'll send whatever chunks we can read/process.
            while (isRecordingActive && webSocket.isConnected() &&
                   (millis() - recordingStartTime < REC_DURATION_MS)) // Loop condition simplified
            {
                // Read stereo data from I2S RX (timeout added)
                esp_err_t readErr = i2s_read(I2S_PORT, recordStereoBuffer, REC_I2S_READ_BYTES, &bytesReadStereo, pdMS_TO_TICKS(50));
                if (readErr != ESP_OK && readErr != ESP_ERR_TIMEOUT) {
                    Serial.printf("Recording task: Error reading from I2S RX: %s (%d)\n", esp_err_to_name(readErr), readErr);
                    // Consider stopping on persistent errors if readErr is not timeout
                    // isRecordingActive = false; break;
                }
                 if (readErr == ESP_ERR_TIMEOUT){
                    // Serial.println("Recording task: I2S read timeout."); // Can be noisy, uncomment if needed
                }


                // only process and send if we read some stereo data successfully
                if (bytesReadStereo > 0) {

                    // --- START: Digital Gain and Mono Conversion ---
                    float digital_gain_factor = 3.5f; // ADJUST THIS VALUE!
                    int clip_counter = 0;

                    size_t numStereoSamplesRead = bytesReadStereo / (COMMON_BITS_PER_SAMPLE / 8) / 2;
                    size_t numMonoBytesExpected = numStereoSamplesRead * (COMMON_BITS_PER_SAMPLE / 8);

                     // Ensure mono buffer has enough space BEFORE processing
                    if (numMonoBytesExpected > sizeof(recordMonoBuffer)) {
                        Serial.printf("Recording task: Error: Extracted mono data size (%zu) would exceed buffer size (%zu).\n", numMonoBytesExpected, sizeof(recordMonoBuffer));
                        isRecordingActive = false; // Critical error, stop recording
                        digitalWrite(TEST_LED_PIN, LOW);
                        break; // Exit while loop
                    }

                    int16_t* stereo_ptr = (int16_t*)recordStereoBuffer;
                    int16_t* mono_ptr = (int16_t*)recordMonoBuffer;
                    bytesWrittenMono = 0; // Reset bytesWrittenMono for this chunk

                    for (size_t i = 0; i < numStereoSamplesRead; ++i) {
                        // Get the left channel sample
                        int16_t current_sample = stereo_ptr[0]; // Left channel (adjust if using right/stereo mix)

                        // Apply digital gain with clamping
                        float amplified_sample_float = (float)current_sample * digital_gain_factor;

                        if (amplified_sample_float > 32767.0f) {
                            current_sample = 32767;
                            clip_counter++;
                        } else if (amplified_sample_float < -32768.0f) {
                            current_sample = -32768;
                            clip_counter++;
                        } else {
                            current_sample = (int16_t)amplified_sample_float;
                        }

                        // Store the processed sample
                        *mono_ptr++ = current_sample;

                        // Advance pointers
                        stereo_ptr += 2; // Stereo (L+R)
                        bytesWrittenMono += (COMMON_BITS_PER_SAMPLE / 8); // Add size of one mono sample
                    }

                    // Optional: Log clipping if significant
                    // if (clip_counter > numStereoSamplesRead / 10) { // Log if > 10% samples clipped
                    //     Serial.printf("Recording task: Warning: Clipped %d/%zu samples in chunk (Gain: %.1f).\n", clip_counter, numStereoSamplesRead, digital_gain_factor);
                    // }
                    // --- END: Digital Gain and Mono Conversion ---


                    // prepare metadata JSON
                    StaticJsonDocument<JSON_MAX_SIZE> jsonDoc;

                    // *** MODIFIED LOGIC: Set incremental seq and large total_seq for data chunks ***
                    // outgoingSequence is 0-indexed count *before* sending the current chunk
                    // outgoingSequence + 1 is the 1-indexed count for the current chunk
                    jsonDoc["seq"] = outgoingSequence + 1; // Incremental sequence number (1, 2, 3, ...)
                    jsonDoc["total_seq"] = LARGE_SEQ_NUMBER; // Total seq is a large number for non-final chunks

                    Serial.printf("Recording task: Sending data chunk. seq=%d, total_seq=%d\n", outgoingSequence + 1, LARGE_SEQ_NUMBER);

                    jsonDoc["sample_rate"] = COMMON_SAMPLE_RATE;
                    jsonDoc["channels"] = 1;
                    jsonDoc["dtype"] = "int16";


                    // serialize JSON into send buffer
                    size_t json_len = serializeJson(jsonDoc, wsSendBuffer, JSON_MAX_SIZE);
                    if (json_len == 0 || json_len >= JSON_MAX_SIZE) {
                        Serial.println("Recording task: Error serializing JSON or JSON too large. Signaling stop.");
                        isRecordingActive = false; // Critical error, stop recording
                        digitalWrite(TEST_LED_PIN, LOW);
                        continue; // Skip sending this chunk
                    }

                    // Copy JSON, delimiter, and audio data into the final send buffer
                    memcpy(wsSendBuffer + json_len, JSON_DELIMITER, JSON_DELIMITER_LEN);
                    memcpy(wsSendBuffer + json_len + JSON_DELIMITER_LEN, recordMonoBuffer, bytesWrittenMono);
                    size_t total_msg_size = json_len + JSON_DELIMITER_LEN + bytesWrittenMono;

                    // Send the binary message over WebSocket
                   if (webSocket.sendBIN(wsSendBuffer, total_msg_size)) {
                        outgoingSequence++; // Increment ONLY AFTER successful send
                        // --- Debug Print 3 ---
                        // Print outgoingSequence *after* incrementing
                        Serial.printf("Recording task: Sent chunk successfully. outgoingSequence (data chunks sent) is now %d.\n", outgoingSequence);
                     } else {
                        Serial.println("Recording task: Failed to send WebSocket chunk. Signaling stop.");
                        isRecordingActive = false; // Stop recording on send failure
                        digitalWrite(TEST_LED_PIN, LOW);
                     }
                } else {
                    // bytesReadStereo was 0 (likely due to timeout or nothing in DMA buffer)
                    // Loop continues, will check duration/status in the next iteration
                }

                // Yield the task briefly
                vTaskDelay(pdMS_TO_TICKS(1));
            } // End of while loop (exits when inactive, disconnected, or time elapsed)

            Serial.println("Recording task: Active recording loop ended.");

            // Print the reason the loop exited (optional, but helpful)
            if (millis() - recordingStartTime >= REC_DURATION_MS) {
                Serial.println("Recording task: Duration limit reached.");
            } else if (!webSocket.isConnected()) {
                 Serial.println("Recording task: WebSocket disconnected.");
            } else if (!isRecordingActive) { // isRecordingActive set false due to send error or other signal
                 Serial.println("Recording task: Stop signal received (isRecordingActive false).");
            }


            // --- Debug Print 4 ---
            // This shows the final count of successfully sent *data* chunks for the session
            Serial.printf("Recording task: outgoingSequence value after while loop (total data chunks sent): %d\n", outgoingSequence);


            // --- MODIFIED LOGIC: Final metadata sending logic ---
            // Send a final chunk to signal the end of the session.
            // This chunk contains metadata indicating the actual total number of data chunks sent.
            // It should be sent if the WebSocket is still connected AND at least one data chunk was sent.
             if (webSocket.isConnected() && outgoingSequence > 0) {
                  Serial.printf("Recording task: Sending final empty chunk metadata. Actual total data chunks sent: %d.\n", outgoingSequence);
                  // Use the actual total count of data chunks sent (outgoingSequence) for both seq and total_seq
                  // This signals the absolute end of the session where N data chunks were sent.
                  Serial.printf("Recording task: Final metadata seq=%d, total_seq=%d\n", outgoingSequence, outgoingSequence);
                  StaticJsonDocument<JSON_MAX_SIZE> jsonDoc;
                  jsonDoc["seq"] = outgoingSequence; // The sequence number matching the total count of data chunks
                  jsonDoc["total_seq"] = outgoingSequence; // Indicate the actual total for this clean end
                  jsonDoc["sample_rate"] = COMMON_SAMPLE_RATE;
                  jsonDoc["channels"] = 1;
                  jsonDoc["dtype"] = "int16";


                  size_t json_len = serializeJson(jsonDoc, wsSendBuffer, JSON_MAX_SIZE);
                   if (json_len > 0 && json_len < JSON_MAX_SIZE) {
                       // No audio data in this final chunk, just metadata and delimiter
                       memcpy(wsSendBuffer + json_len, JSON_DELIMITER, JSON_DELIMITER_LEN);
                       size_t total_msg_size = json_len + JSON_DELIMITER_LEN; // Only metadata + delimiter

                       if (webSocket.sendBIN(wsSendBuffer, total_msg_size)) {
                           Serial.println("Recording task: Sent final chunk metadata successfully.");
                           // IMPORTANT: Do NOT increment outgoingSequence after sending the final metadata chunk.
                           // outgoingSequence tracks the count of *data* chunks sent.
                       } else {
                           Serial.println("Recording task: Failed to send final chunk metadata.");
                       }
                  } else {
                      Serial.println("Recording task: Error serializing final chunk metadata.");
                  }
             } else {
                 // This else covers cases where WS is disconnected OR no data chunks were sent.
                  Serial.printf("Recording task: Not sending final metadata (disconnected or no data sent). Connected=%d, outgoingSeq=%d.\n", webSocket.isConnected(), outgoingSequence);
             }
            // End of final metadata sending logic


            isRecordingActive = false; // Ensure this is false after the session block finishes
            Serial.println("Recording task: Session block finished. isRecordingActive = false.");
            digitalWrite(TEST_LED_PIN, LOW);

        } // End of if (startRecording)

        // Yield the task briefly to allow other tasks (like WebSocket) to run
        vTaskDelay(pdMS_TO_TICKS(100));
    } // End of for(;;) loop (task runs forever)
}


void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("ESP32 Audio Recorder/Player (Combined - WS Playback)");

    // WifiManager setup
    WiFiManager wm;

    // reset saved settings (for testing) 
    // comment on production!!!!!
    wm.resetSettings();
    Serial.println("Attempting WiFi connection using WiFiManager...");

    bool res = wm.autoConnect("PawPal-WiFiManager");

    if (res == true) { // check if wm.autoConnect was successful
        Serial.println("\n✅ Connected to Wi-Fi!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());

        // LED pinout setup 
        pinMode(TEST_LED_PIN, OUTPUT);
        Serial.println("LED pin mode set to OUTPUT.");
        digitalWrite(TEST_LED_PIN, LOW); // start with LED off


        initCodecSingleConfig();
        initI2SDualMode();
        delay(500);

        // ==== WS setup ====
        Serial.println("Connecting to WebSocket...");
        webSocket.onEvent(webSocketEvent);
        webSocket.begin(websocket_server_address, websocket_server_port, websocket_path);

        // ==== FreeRTOS task for audio ====
        xTaskCreatePinnedToCore(
            audioRecordTask,            // task function
            "AudioRecordTask",          // name
            8192,                       // stack size
            NULL,                       // parameter
            5,                          // priority
            &audioRecordTaskHandle,     // handle
            0                           // core (core 0 for network/ID)
        );
        if (audioRecordTaskHandle == NULL) {
            Serial.println("Error creating Audio Record Task!");
        } else {
            Serial.println("Audio Record Task created.");
        }

        // audioPlaybackTask removed - playback is event driven in webSocketEvent

    } else {
        Serial.println("WiFi connection failed. Audio tasks will not start.");
    }

    Serial.println("Setup finished.");
}

void loop() {
    webSocket.loop();

    if (shouldReconnect && millis() - lastReconnectAttempt >= reconnectInterval) {
        Serial.println("Attempting WebSocket reconnection...");
        if (WiFi.status() == WL_CONNECTED) {
            // reset playback state first
            currentExpectedSequence = 1;
            currentTotalSeq = -1;
            currentSampleRate = 0;
            currentChannels = 0;
            currentBitsPerSample = 0;
            isPlayingSegment = false;

            webSocket.begin(websocket_server_address, websocket_server_port, websocket_path);
            lastReconnectAttempt = millis(); 
        } else {
            Serial.println("WiFi not connected, cannot attempt WebSocket reconnection.");
        }
    }

    vTaskDelay(pdMS_TO_TICKS(1));
}
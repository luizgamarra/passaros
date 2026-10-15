// SPDX-License-Identifier: Apache-2.0
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include "driver/i2s_std.h"
#include "driver/uart.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "labels.h"
#include "preprocess.h"

// The pinned ESP-NN dense kernel ignores per-channel multipliers. Use the
// corresponding TFLM reference kernel for dense layers; convolutions stay ESP-NN.
namespace tflite { TFLMRegistration Register_LOCAL_FULLY_CONNECTED(); }

extern const uint8_t model_start[] asm("_binary_model_tflite_start");
extern const uint8_t reference_audio_start[] asm("_binary_reference_audio_pcm_start");
extern const uint8_t reference_input_start[] asm("_binary_reference_input_bin_start");
extern const uint8_t reference_output_start[] asm("_binary_reference_output_bin_start");

namespace {
constexpr int Samples = 72000, Rate = 24000, Features = 5320;
constexpr size_t Arena = 512 * 1024;
const char* TAG = "passaros";
i2s_chan_handle_t microphone = nullptr;
int16_t* pcm = nullptr;

bool capture() {
    // Start each clip with an empty DMA queue: inference leaves a gap between clips.
    if (i2s_channel_enable(microphone) != ESP_OK) return false;
    int32_t slots[512];
    int count = 0;
    while (count < Samples) {
        size_t received = 0;
        auto result = i2s_channel_read(microphone, slots, sizeof(slots), &received, 1000);
        if (result != ESP_OK || received == 0 || received % sizeof(int32_t)) {
            i2s_channel_disable(microphone);
            ESP_LOGE(TAG, "Falha/timeout I2S: %s", esp_err_to_name(result));
            return false;
        }
        for (size_t i = 0; i < received / sizeof(int32_t) && count < Samples; ++i) {
            pcm[count++] = std::clamp<int32_t>(slots[i] >> CONFIG_BIRD_PCM_SHIFT, -32768, 32767);
        }
    }
    return i2s_channel_disable(microphone) == ESP_OK;
}

void microphone_init() {
    i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&channel, nullptr, &microphone));
    i2s_std_config_t config = {};
    config.clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(Rate);
    config.slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO);
#ifdef CONFIG_BIRD_I2S_RIGHT
    config.slot_cfg.slot_mask = I2S_STD_SLOT_RIGHT;
#else
    config.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;
#endif
    config.gpio_cfg.mclk = I2S_GPIO_UNUSED;
    config.gpio_cfg.bclk = static_cast<gpio_num_t>(CONFIG_BIRD_I2S_BCLK);
    config.gpio_cfg.ws = static_cast<gpio_num_t>(CONFIG_BIRD_I2S_WS);
    config.gpio_cfg.dout = I2S_GPIO_UNUSED;
    config.gpio_cfg.din = static_cast<gpio_num_t>(CONFIG_BIRD_I2S_DATA);
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(microphone, &config));
}

bool selftest(tflite::MicroInterpreter& interpreter) {
    auto* input = interpreter.input(0);
    memcpy(pcm, reference_audio_start, Samples * sizeof(int16_t));
    if (!preprocess(pcm, input->data.int8, input->params.scale, input->params.zero_point)) return false;
    int errors = 0;
    for (int i = 0; i < Features; ++i) {
        if (input->data.int8[i] != reinterpret_cast<const int8_t*>(reference_input_start)[i]) ++errors;
    }
    ESP_LOGI(TAG, "SELFTEST_FEATURES: divergencias=%d/%d", errors, Features);
    if (errors) return false;
    if (interpreter.Invoke() != kTfLiteOk) return false;
    auto* output = interpreter.output(0);
    const auto* reference = reinterpret_cast<const int8_t*>(reference_output_start);
    int max_error = 0;
    for (int i = 0; i < 11; ++i) max_error = std::max(max_error, std::abs(int(output->data.int8[i]) - int(reference[i])));
    int predicted = std::max_element(output->data.int8, output->data.int8 + 11) - output->data.int8;
    int expected = std::max_element(reference, reference + 11) - reference;
    ESP_LOGI(TAG, "SELFTEST_MODEL: erro_max_LSB=%d previsto=%s esperado=%s", max_error, kLabels[predicted], kLabels[expected]);
    return max_error <= 2 && predicted == expected;
}
}

extern "C" void app_main() {
    ESP_LOGI(TAG, "BirdNET Tiny exemplo N16R8; especies europeias, sem gralha-azul");
    ESP_LOGI(TAG, "PSRAM livre=%u", unsigned(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)));
    auto* arena = static_cast<uint8_t*>(heap_caps_aligned_alloc(16, Arena, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    pcm = static_cast<int16_t*>(heap_caps_malloc(Samples * sizeof(int16_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (!arena || !pcm) { ESP_LOGE(TAG, "PSRAM indisponivel; confirme placa N16R8 e PSRAM octal"); return; }
    const tflite::Model* model = tflite::GetModel(model_start);
    if (model->version() != TFLITE_SCHEMA_VERSION) { ESP_LOGE(TAG, "Schema incompativel"); return; }
    tflite::MicroMutableOpResolver<8> resolver;
    if (resolver.AddConv2D() != kTfLiteOk || resolver.AddDepthwiseConv2D() != kTfLiteOk ||
        resolver.AddFullyConnected(tflite::Register_LOCAL_FULLY_CONNECTED()) != kTfLiteOk || resolver.AddReshape() != kTfLiteOk ||
        resolver.AddTranspose() != kTfLiteOk || resolver.AddSum() != kTfLiteOk ||
        resolver.AddMaxPool2D() != kTfLiteOk || resolver.AddSoftmax() != kTfLiteOk) return;
    tflite::MicroInterpreter interpreter(model, resolver, arena, Arena);
    if (interpreter.AllocateTensors() != kTfLiteOk) { ESP_LOGE(TAG, "AllocateTensors falhou"); return; }
    auto* input = interpreter.input(0);
    auto* output = interpreter.output(0);
    if (input->type != kTfLiteInt8 || input->bytes != Features || output->type != kTfLiteInt8 || output->bytes != 11) {
        ESP_LOGE(TAG, "Contrato de entrada/saida incompativel"); return;
    }
    ESP_LOGI(TAG, "Arena utilizada=%u", unsigned(interpreter.arena_used_bytes()));
    if (!selftest(interpreter)) { ESP_LOGE(TAG, "SELFTEST_FAIL: captura bloqueada; investigar paridade"); return; }
    ESP_LOGI(TAG, "SELFTEST_OK: iniciando captura autonoma I2S GPIO%d/%d/%d", CONFIG_BIRD_I2S_BCLK, CONFIG_BIRD_I2S_WS, CONFIG_BIRD_I2S_DATA);
    microphone_init();
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0, 256, 0, 0, nullptr, 0));
    ESP_LOGI(TAG, "Comandos UART: p=pausar, m=retomar, t=autoteste, a=exportar PCM (pausa)");
    bool running = true;
    while (true) {
        uint8_t command = 0;
        if (uart_read_bytes(UART_NUM_0, &command, 1, 0) == 1) {
            if (command == 'p') running = false;
            if (command == 'm') running = true;
            if (command == 't') {
                bool passed = selftest(interpreter);
                if (!passed) running = false;
                ESP_LOGI(TAG, "%s", passed ? "SELFTEST_OK" : "SELFTEST_FAIL");
            }
            if (command == 'a') {
                running = false;
                if (capture()) {
                    printf("\nPCM_BEGIN 144000 24000\n"); fflush(stdout);
                    uart_write_bytes(UART_NUM_0, pcm, Samples * sizeof(int16_t));
                    uart_wait_tx_done(UART_NUM_0, pdMS_TO_TICKS(30000));
                    printf("\nPCM_END\n"); fflush(stdout);
                }
            }
        }
        if (!running) { vTaskDelay(pdMS_TO_TICKS(100)); continue; }
        if (!capture()) { vTaskDelay(pdMS_TO_TICKS(1000)); continue; }
        int peak = 0, clipped = 0;
        double sum_squares = 0;
        for (int i = 0; i < Samples; ++i) {
            peak = std::max(peak, std::abs(int(pcm[i])));
            clipped += pcm[i] == INT16_MIN || pcm[i] == INT16_MAX;
            sum_squares += double(pcm[i]) * pcm[i];
        }
        double rms = sqrt(sum_squares / Samples);
        if (rms < 8) { ESP_LOGW(TAG, "Audio quase nulo rms=%.1f: conferir microfone, pinos e L/R", rms); continue; }
        int64_t started = esp_timer_get_time();
        preprocess(pcm, input->data.int8, input->params.scale, input->params.zero_point);
        int64_t preprocessed = esp_timer_get_time();
        if (interpreter.Invoke() != kTfLiteOk) { ESP_LOGE(TAG, "Invoke falhou"); continue; }
        int index = std::max_element(output->data.int8, output->data.int8 + 11) - output->data.int8;
        // Baseline outputs logits. A softmax is a relative score, not calibrated confidence.
        double denominator = 0;
        for (int i = 0; i < 11; ++i) denominator += exp(double(output->data.int8[i] - output->data.int8[index]) * output->params.scale);
        ESP_LOGI(TAG, "classe=%s score_relativo=%.3f rms=%.1f pico=%d clipping=%d DSP_ms=%lld ML_ms=%lld",
                 kLabels[index], 1.0 / denominator, rms, peak, clipped,
                 (preprocessed - started)/1000, (esp_timer_get_time() - preprocessed)/1000);
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

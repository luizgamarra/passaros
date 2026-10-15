// Copyright 2024 fold ecosystemics, 2025 BirdNET team, 2026 local contributors.
// SPDX-License-Identifier: Apache-2.0
// Scalar port of BioDCASE-Tiny-2026's nb_fft/nb_mel/nb_log32/nb_isqrt.
// The same file is compiled on Windows to compare with the Python reference.
#include "preprocess.h"
#include "feature_constants.h"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace {
constexpr int N = 4096, Frames = 133, Channels = 40;
int16_t fft[2 * N];
uint32_t energy[N / 2];
uint32_t mel[Channels * Frames];

int bits(uint64_t value) {
    int count = 0;
    while (value) { value >>= 1; ++count; }
    return count;
}

uint32_t square_root(uint64_t value) {
    if (!value) return 0;
    const bool small = (value >> 32) == 0;
    const int width = small ? 32 : 64;
    int leading = (width - bits(value)) | 1;
    uint64_t bit = uint64_t{1} << (width - 1 - leading);
    uint64_t result = 0;
    for (int iterations = (width - 1 - leading) / 2 + 1; iterations > 0; --iterations) {
        if (value >= result + bit) {
            value -= result + bit;
            result = (result >> 1) + bit;
        } else { result >>= 1; }
        bit >>= 2;
    }
    if (value > result && result != (small ? 0xFFFFULL : 0xFFFFFFFFULL)) ++result;
    return static_cast<uint32_t>(result);
}

uint32_t logarithm(uint32_t value) {
    if (!value) return 0;
    uint32_t integer = bits(value) - 1;
    uint32_t fraction = value - (uint32_t{1} << integer);
    if (integer < 16) fraction <<= 16 - integer;
    else fraction >>= integer - 16;
    uint32_t base = fraction >> 9;
    int32_t c0 = kLogLut[base], c1 = kLogLut[base + 1];
    int32_t relative = ((c1 - c0) * (int32_t(fraction) - int32_t(512 * base))) >> 16;
    uint32_t log2 = (integer << 16) + fraction + c0 + relative;
    uint32_t loge = ((uint64_t{45426} * log2) + 32768) >> 16;
    uint32_t scaled = ((uint64_t{64} * loge) + 32768) >> 16;
    return scaled >= 65535 ? 0 : scaled;
}

void transform() {
    for (int groups = 1, half = N / 2; half > 0; groups <<= 1, half >>= 1) {
        int position = 0;
        for (int j = 0; j < groups; ++j) {
            int64_t wr = kTwiddle[2 * j], wi = kTwiddle[2 * j + 1];
            for (int i = 0; i < half; ++i, ++position) {
                int m = position + half;
                int64_t ar = fft[2 * position], ai = fft[2 * position + 1];
                int64_t br = fft[2 * m], bi = fft[2 * m + 1];
                fft[2 * m] = (ar * 32767 - wr * br - wi * bi + 32767) >> 16;
                fft[2 * m + 1] = (ai * 32767 - wr * bi + wi * br + 32767) >> 16;
                fft[2 * position] = (ar * 32767 + wr * br + wi * bi + 32767) >> 16;
                fft[2 * position + 1] = (ai * 32767 + wr * bi - wi * br + 32767) >> 16;
            }
            position += half;
        }
    }
    for (int i = 1, j = 0; i < N - 1; ++i) {
        int k = N >> 1;
        while (k <= j) { j -= k; k >>= 1; }
        j += k;
        if (i < j) { std::swap(fft[2*i], fft[2*j]); std::swap(fft[2*i+1], fft[2*j+1]); }
    }
    int tmp = fft[0];
    fft[0] = (tmp + fft[1]) >> 1;
    fft[1] = (tmp - fft[1]) >> 1;
    for (int k = 1; k <= N / 2; ++k) {
        int64_t ar = fft[2*k], ai = fft[2*k+1];
        int64_t br = fft[2*(N-k)], bi = fft[2*(N-k)+1];
        unsigned reversed = 0;
        for (unsigned x = k, b = 0; b < 12; ++b, x >>= 1) reversed = (reversed << 1) | (x & 1);
        int64_t wr = kTwiddle[2*reversed], wi = kTwiddle[2*reversed+1];
        int64_t tr = (wr * (ai + bi) - wi * (ar - br)) >> 15;
        int64_t ti = (wr * (ar - br) + wi * (ai + bi)) >> 15;
        fft[2*k] = (ar + br + tr) >> 2;
        fft[2*k+1] = (ai - bi - ti) >> 2;
        fft[2*(N-k)] = (ar + br - tr) >> 2;
        fft[2*(N-k)+1] = -(ai - bi + ti) >> 2;
    }
}
}

bool preprocess(const int16_t* audio, int8_t* features, float scale, int zero) {
    if (!audio || !features || scale <= 0) return false;
    uint32_t low = UINT32_MAX, high = 0;
    for (int frame = 0; frame < Frames; ++frame) {
        int maximum = 0;
        for (int i = 0; i < N; ++i) {
            fft[2*i] = (int32_t(audio[frame * 512 + i]) * kHanning[i]) >> 12;
            fft[2*i+1] = 0;
            // np.abs(int16(-32768)) remains negative in the reference.
            int absolute = fft[2*i] == INT16_MIN ? INT16_MIN : std::abs(int(fft[2*i]));
            maximum = std::max(maximum, absolute);
        }
        int shift = std::max(0, 15 - bits(maximum));
        for (int i = 0; i < N; ++i) fft[2*i] = int32_t(fft[2*i]) * (1 << shift);
        transform();
        for (int i = 0; i < N / 2; ++i) {
            int32_t re = fft[2*i], im = fft[2*i+1];
            energy[i] = (i < kFftStart || i > kFftEnd) ? 0 : uint32_t(int64_t(re)*re + int64_t(im)*im);
        }
        uint64_t accumulated = 0;
        for (int channel = 0; channel <= Channels; ++channel) {
            uint64_t remainder = 0;
            for (int j = 0; j < kWidth[channel]; ++j) {
                int weight = kWeightStart[channel] + j;
                uint32_t e = energy[kFrequency[channel] + j];
                accumulated += uint64_t(kWeights[weight]) * e;
                remainder += uint64_t(kUnweights[weight]) * e;
            }
            if (channel > 0) {
                uint32_t value = logarithm(square_root(accumulated) >> shift);
                mel[(channel - 1) * Frames + frame] = value;
                low = std::min(low, value); high = std::max(high, value);
            }
            accumulated = remainder;
        }
    }
    for (int i = 0; i < Frames * Channels; ++i) {
        float normalized = high == low ? 0.0f : float(mel[i] - low) / float(high - low);
        float quantized = normalized / scale + float(zero);
        features[i] = static_cast<int8_t>(std::clamp(quantized, -128.0f, 127.0f));
    }
    return true;
}

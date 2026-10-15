#include "preprocess.h"
#include <fstream>
#include <vector>
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::ifstream input(argv[1], std::ios::binary);
    std::vector<int16_t> pcm(72000);
    input.read(reinterpret_cast<char*>(pcm.data()), 144000);
    if (input.gcount() != 144000) return 3;
    std::vector<int8_t> features(5320);
    if (!preprocess(pcm.data(), features.data(), 0.003921568859368563f, -128)) return 4;
    std::ofstream output(argv[2], std::ios::binary);
    output.write(reinterpret_cast<const char*>(features.data()), features.size());
    return output.good() ? 0 : 5;
}

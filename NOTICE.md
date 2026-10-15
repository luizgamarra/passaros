O modelo de demonstracao e a referencia Python sao do repositorio oficial
birdnet-team/BioDCASE-Tiny-2026, commit a62675704019fc8a0bcc4e2f64346698ea501a32.
O processamento C++ local deriva dos algoritmos nb_fft, nb_mel, nb_shift_scale,
nb_isqrt e nb_log32 desse repositorio, sob Apache-2.0.
Os arquivos originais foram preservados em upstream/.
Os WAV de exemplo mantem a origem e os avisos do repositorio/dataset BioDCASE;
consultar upstream/BioDCASE-Tiny-2026/NOTICE e as condicoes do dataset antes de redistribuir.
O firmware local e uma adaptacao para ESP32-S3 N16R8 com microfone I2S externo;
nao e um firmware oficial certificado pelo BirdNET.

fully_connected_reference.cpp preserva a licenca Apache-2.0 dos autores do
TensorFlow e foi copiado do kernel de referencia do ESP-TFLM commit
416d3713e9312025df434d6f33600ec490705b3d. Foram renomeadas as funcoes de
registro para usar esse kernel nas camadas densas sem alterar as convolucoes.
train_tiny.py e uma CNN local treinada do zero com a referencia DSP BioDCASE;
nao utiliza os pesos do modelo completo BirdNET-Analyzer.

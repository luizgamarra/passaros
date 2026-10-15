# Autoria e licencas de terceiros

Este repositorio e uma adaptacao local para ESP32-S3 N16R8. Nao e um produto
oficial certificado pelo BirdNET. Publicar o repositorio nao altera as licencas
dos componentes e dados de terceiros.

## BioDCASE-Tiny 2026

Origem: https://github.com/birdnet-team/BioDCASE-Tiny-2026

Commit: `a62675704019fc8a0bcc4e2f64346698ea501a32`.

Copyright 2026 BirdNET-Team. Copyright 2026 fold ecosystemics.

O codigo e o baseline fornecidos nesse projeto seguem os avisos Apache-2.0 do
repositorio original. O texto da licenca esta em [firmware/LICENSE](firmware/LICENSE)
e os avisos originais podem ser consultados no submodulo `upstream/BioDCASE-Tiny-2026`.
Os arquivos `models/biodcase_baseline.tflite` e `firmware/main/model.tflite`
sao copias do baseline. O DSP C++ e os scripts locais sao adaptacoes identificadas
em [NOTICE.md](NOTICE.md).

Referencia do framework: Christian Walter, Yasmine Benhamadi, Tom Seidel,
Giovanni Carmantini e Stefan Kahl (2026), BioDCASE-Tiny 2026: A Framework for
Bird Species Recognition on Resource-Constrained Hardware.

## Audio de exemplo e referencia

O audio `data/example_blackbird.wav` foi copiado do exemplo
`submission/test_wav_files/Eurasian Blackbird/BioDCASE26_TEST_0155_Eurasian_Blackbird.wav`
do submodulo BioDCASE. `firmware/main/reference_audio.pcm` contem suas amostras
PCM sem o cabecalho WAV; `reference_input.bin` e `reference_output.bin` sao
vetores calculados para o autoteste.

Fonte do dataset indicada pelo projeto: Stefan Kahl e Ralph Martin (2026),
**BioDCASE 2026 Task 3: Bioacoustics for Tiny Hardware Development Set**,
https://doi.org/10.5281/zenodo.19453065.
As gravacoes foram realizadas na Alemanha com unidades eciPi da OekoFor e
anotadas por Ralph Martin, conforme a descricao do dataset.

O dataset e distribuido sob **Creative Commons Attribution-ShareAlike 4.0
International**, https://creativecommons.org/licenses/by-sa/4.0/.
Preserve a atribuicao e essas condicoes ao redistribuir o audio e suas adaptacoes.
Nao foi aplicado tratamento acustico ao exemplo; a referencia PCM apenas remove
o conteiner WAV. Esse aviso sobre os dados nao relicencia o codigo do projeto.

## TensorFlow Lite Micro

`firmware/main/fully_connected_reference.cpp` deriva do kernel de referencia do
ESP-TFLM, commit `416d3713e9312025df434d6f33600ec490705b3d`, e preserva os avisos
Apache-2.0 dos autores TensorFlow no cabecalho. Os nomes de registro foram
adaptados localmente para usar esse kernel nas camadas densas.

## Outros repositorios

BirdNET-Analyzer, BirdNET-Tiny-Forge e seu template Korvo2 sao referencias externas
via submodulos. Consulte os arquivos de licenca de cada um. Os pesos grandes do
Analyzer nao sao incluidos neste repositorio; as condicoes desses modelos devem
ser consultadas na origem quando baixados.

# BirdNET no ESP32-S3 N16R8

Projeto de reconhecimento de aves com **BioDCASE-Tiny no ESP32-S3** e teste
em Python pelo microfone do PC. O baseline identifica **10 especies + fundo**.
O BirdNET completo do desktop e um modelo separado; os limites estao abaixo.

## Clonar e testar no Windows

Requisitos para Python: Git e [uv](https://docs.astral.sh/uv/getting-started/installation/).
O setup cria uma `.venv` Python 3.11. Para compilar o firmware, tambem e necessario
ESP-IDF 5.5.2; o launcher atual usa `C:\Espressif\frameworks\esp-idf-v5.5.2`.

```powershell
git clone --recurse-submodules https://github.com/luizgamarra/passaros.git
cd passaros
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
.\.venv\Scripts\python.exe scripts\listen_tiny.py
```

Para testar sem microfone: `.\.venv\Scripts\python.exe scripts\infer_tiny.py`.
Para ouvir pelo microfone, reproduza um canto pelos alto-falantes; `Ctrl+C` encerra.
Detalhes no [manual PDF](Manual_BirdNET_ESP32S3_Treinamento_Compilacao.pdf).

As quatro pastas `upstream/` sao submodulos Git fixados nos commits usados aqui.
Se clonou sem `--recurse-submodules`, execute `git submodule update --init`;
o setup tambem faz essa etapa. Cada projeto externo mantem sua propria licenca.

O repositorio publica fontes, scripts, manual, modelo pequeno e vetores de
referencia. Ambientes, backups, gravacoes pessoais, modelos grandes, builds,
resultados locais e releases de bancada ficam fora do Git. Os caminhos de
backups, resultados e releases citados no registro abaixo descrevem a bancada
original; esses arquivos nao acompanham um clone. Os scripts geram novas saidas.
Consulte [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) para autoria e licencas
do baseline e do audio de exemplo.

## Estado confirmado em 14/10/2026

Firmware gravado e verificado na **COM46** (ESP32-S3 v0.2, flash 16 MB,
PSRAM 8 MB). O autoteste embarcado passou: 0 divergencias nas 5.320 features,
classe Eurasian Blackbird correta e erro maximo de 1 LSB na saida INT8.
O usuario confirmou que ainda nao ha microfone nem cartao SD. O cartao nao e
necessario neste firmware; o teste de audio real fica para a chegada do microfone.

- [Manual PDF: microfone do PC, treinamento e compilacao](Manual_BirdNET_ESP32S3_Treinamento_Compilacao.pdf)
- [Manual em Markdown](docs/Manual_BirdNET_ESP32S3_Treinamento_Compilacao.md): secoes 2A/2B para testar no PC; 3/3A a 8 para treinar uma nova especie e compilar.
- Imagem exata gravada: `releases/20261014-COM46-validado/flash-full.bin`, em `0x0`.
- Aplicacao isolada: `releases/20261014-COM46-validado/passaros_tiny.bin`, em `0x10000`.
- Fontes e configuracao dessa imagem: `releases/20261014-COM46-validado/source/`.
- Backup anterior: `backups/COM46-20261014-antes.bin`, 16 MB completos.
- Recibo e hashes: `results/hardware/receipt.json` e `releases/20261014-COM46-validado/hashes.json`.

O kernel ESP-NN das camadas densas do commit utilizado nao aplicava a quantizacao
por canal do baseline. O firmware usa nessas camadas o kernel de referencia TFLM,
copiado para `fully_connected_reference.cpp`; convolucoes permanecem ESP-NN.
O modelo e as features nao foram alterados para corrigir essa incompatibilidade.

Novo caminho executavel de treinamento:

```powershell
.\.venv\Scripts\python.exe scripts\train_tiny.py --dataset data\dataset --output models\custom\gralha-v1 --epochs 30
.\.venv\Scripts\python.exe scripts\prepare_custom.py --bundle models\custom\gralha-v1 --output-firmware firmware-custom\gralha-v1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -Action build -FirmwareDir firmware-custom\gralha-v1 -BuildName gralha-v1 -ArtifactsDir artifacts-custom\gralha-v1
```

Esses comandos exigem dataset real, dividido por gravacao, e `metadata.csv`,
como explicado no manual. A CNN local e treinada do zero com o DSP BioDCASE;
nao transfere os pesos do BirdNET grande. O caminho foi testado com dados
sinteticos em `technical-smoke-v2-20261014`; nao existe treinamento real de
gralha-azul nesta preparacao. O exemplo baseline e o firmware na placa foram
preservados em sua propria release.

Exemplo para reconhecer sons **dentro do ESP32**, sem PC ou rede durante o uso.
O PC serve para preparar o modelo, compilar, gravar e observar o primeiro teste.

O firmware local usa um modelo pequeno do projeto oficial **BioDCASE-Tiny-2026**,
do time BirdNET. O BirdNET-Analyzer completo fica no computador para estudo e
comparacao. Nao basta copiar o modelo grande do Analyzer para o ESP32.

## O que foi preparado

- Python 3.11 em `.venv`, com BirdNET-Analyzer, TensorFlow, LiteRT, NumPy,
  librosa, SoundFile, Numba, pyserial e esptool; versoes em `requirements.lock.txt`.
- ESP-IDF nativo existente em `C:\Espressif\frameworks\esp-idf-v5.5.2`, validado
  e usado na compilacao. FFmpeg e GCC/G++ do PC tambem foram encontrados e reutilizados.
- Modelo INT8 `models/biodcase_baseline.tflite`, 111.408 bytes, dez especies + fundo.
- Firmware em `firmware/`, configurado para flash 16 MB e PSRAM octal 8 MB.
- Scripts de preparo, comparacao Python/C++, compilacao, gravacao e captura WAV.
- Fontes oficiais preservadas em `upstream/`; rastreabilidade em `results/manifest.json`.

O Tiny Forge e seu template Korvo2 foram baixados para referencia. A instalacao
completa do Forge, que pede Ubuntu e um wheel customizado de TFLite Micro, nao foi
executada. A stack operacional escolhida e o baseline oficial BioDCASE com ESP-IDF
nativo e uma adaptacao local para microfone externo. Os requirements do BioDCASE
nao foram instalados literalmente: incluem nomes incorretos (`sklearn`, `tdqm`) e
dependencias que este exemplo nao usa. O ambiente reproduzivel esta no lock local.

## Limite importante do exemplo

Este modelo **nao reconhece gralha-azul nem especies brasileiras em geral**. As
classes sao: Background, Common Chaffinch, Common Chiffchaff, Eurasian Blackbird,
Eurasian Blackcap, Eurasian Blue Tit, Great Spotted Woodpecker, Great Tit, Mallard,
Song Thrush e Tawny Owl.

Nos 11 WAV incluidos no repositorio, o modelo acertou 9. Essa amostra serve para
testar a execucao; nao mede a precisao em campo. Uma especie desconhecida pode
receber o nome de uma classe conhecida. O `score_relativo` do firmware e uma
softmax dos logits, sem calibracao de confianca. Antes do projeto de campo sera
necessario treinar e avaliar um modelo com as especies locais e ruido de fundo.

## 1. Usar agora, sem a placa

Abra PowerShell nesta pasta. O ambiente ja esta instalado; nao precisa refazer a
instalacao. Para escutar pelo microfone do PC com o mesmo modelo Tiny do ESP32:

```powershell
.\.venv\Scripts\python.exe scripts\listen_tiny.py
```

De play pelos alto-falantes em um canto isolado, por exemplo `Eurasian Blackbird
song` (`Turdus merula`, melro). O programa analisa blocos de 3 segundos e mostra
classe, score relativo, RMS, pico e clipping. `Ctrl+C` encerra. Para escolher a
entrada, rode `--list-devices` e depois `--device ID`. O listen mostra no terminal;
nao salva audio nem CSV. As secoes 2A e 2B do manual explicam uso e diagnostico.

Para testar os 11 WAVs com o Tiny e gerar `results/tiny_python.csv`:

```powershell
.\.venv\Scripts\python.exe scripts\infer_tiny.py
```

Os dois scripts usam o baseline em `firmware/main/model.tflite`; nao selecionam
automaticamente modelos novos em `models/custom/`. O treinamento de uma nova
especie e a avaliacao do novo modelo estao nas secoes 3 a 8 do manual.

Para conferir o preparo e comparar com o BirdNET completo de desktop:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_example.py
.\.venv\Scripts\python.exe scripts\check_preprocessing.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\analyze.ps1
```

O primeiro comando prepara modelo, labels e vetores de teste. O segundo compila
**o mesmo processamento C++ do firmware** no Windows e compara cada byte com a
referencia Python em 15 casos. O terceiro analisa o WAV usando o modelo completo
BirdNET 2.4 no desktop; os modelos ficam em `models/analyzer/` e o CSV em
`results/analyzer/`. O cache de execucao fica em
`C:\Users\luizf\birdnet-build\analyzer-cache`: o loader nativo do TensorFlow no
Windows falha ao abrir modelos em caminhos com acentos. A copia baixada nesta
pasta e preservada; o launcher usa o cache de caminho curto. Os labels em
portugues ja acompanham o download do modelo.

Sao 14 comparacoes exatas com a referencia oficial e um teste adicional de
silencio total. Neste ultimo caso o firmware define features constantes; a
normalizacao original dividiria por zero. Isso evita uma entrada indefinida.

Para seu proprio WAV:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\analyze.ps1 -Audio data\meu_audio.wav
```

Para converter audio de celular, usando o FFmpeg instalado (nome de saida novo):

```powershell
ffmpeg -i data\gravacao.m4a -ac 1 -ar 48000 data\gravacao.wav
```

## 2. Compilar o exemplo

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -Action build
```

O script copia as fontes para `C:\Users\luizf\birdnet-build\passaros`, um caminho
curto sem espacos/acentos para o ESP-IDF. O projeto principal permanece nesta pasta.
Os arquivos prontos ficam em `artifacts/`: aplicacao, ELF, bootloader, particoes,
configuracao e argumentos de gravacao. `flash-full.bin` combina bootloader,
particoes e aplicacao, para gravacao a partir de `0x0`. O `passaros_tiny.bin`
isolado e apenas a aplicacao e vai em `0x10000`. **A compilacao nao grava a placa.**

O firmware usa TensorFlow Lite Micro com convolucoes ESP-NN e camadas densas de referencia. A arena reservada e
512 KiB de PSRAM, mais 144.000 bytes para 3 segundos de audio. O tamanho de arena
realmente usado e exibido na placa: o baseline usou 202.444 bytes na COM46.
Os tempos de captura/inferencia de audio real ainda precisam do microfone.

## 3. Montar o microfone quando a placa estiver disponivel

O exemplo foi preparado para **INMP441**, seguindo o componente citado no PDF.
O usuario confirmou ESP32-S3 N16R8; o modelo do microfone ainda precisa ser confirmado.
Com a placa desligada, a ligacao proposta e:

| INMP441 | ESP32-S3 N16R8 |
|---|---|
| VDD/VCC | 3V3 |
| GND | GND |
| SCK/BCLK | GPIO4 |
| WS/LRCLK | GPIO5 |
| SD/DOUT | GPIO6 |
| L/R | GND (canal esquerdo) |

O INMP441 e alimentado em **3,3 V**, com I2S de 24 bits em slots de 32 bits.
Confirme que os GPIOs 4, 5 e 6 estao expostos e livres na sua placa. Esse exemplo
nao usa o codec de audio da Korvo2. N16R8 nao e a variante N16R8V de flash octal;
a configuracao preparada usa flash DIO e PSRAM octal. Conferir o codigo real do
modulo antes da primeira gravacao.

Para trocar pinos/canal/shift, use `-Action menuconfig`, menu
`Passaros - microfone I2S externo`. Depois recompile. As escolhas ficam no
`sdkconfig` da pasta de build; as fontes nao apagam essa configuracao.

## 4. Identificar a porta e gravar (somente com a placa conectada)

Use um cabo USB de dados e, se houver duas entradas, inicialmente a entrada
**USB-UART**. A configuracao atual usa UART0 a 115200 baud; a entrada USB nativa
pode aparecer como outra COM e nao e o console deste build.

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
```

Identifique a COM que apareceu ao conectar a placa. Nao use as portas Bluetooth.
O `COM7` abaixo e apenas um exemplo: substitua pela porta real.

```powershell
.\.venv\Scripts\python.exe -m esptool --chip esp32s3 --port COM7 flash-id
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -Action flash -Port COM7
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -Action monitor -Port COM7
```

`flash-id` le a identificacao/tamanho da flash. `flash` escreve nas particoes do
exemplo, substituindo o programa anterior nos enderecos gravados. Se a placa
ja tiver firmware importante, fazer backup antes. A gravacao realizada na COM46
esta documentada no recibo e no manual acima. Se a conexao automatica falhar, usar BOOT/RESET
conforme a placa. Para sair do monitor IDF, `Ctrl+]`.

## 5. Primeiro teste na bancada

Ao ligar, a placa faz dois testes com um audio embutido:

1. Processa os 3 segundos e compara 5.320 valores INT8 com a referencia do PC.
2. Executa o modelo e compara a classe e a saida com a referencia.

Procure `SELFTEST_FEATURES: divergencias=0/5320`, `SELFTEST_MODEL` e
`SELFTEST_OK`. Se falhar, o firmware interrompe a inicializacao da captura.
Se passar, inicia automaticamente o microfone, sem depender de comando do PC.

A cada ciclo ele grava 3 segundos, calcula features, roda o modelo e escreve
classe, score relativo, RMS, pico, clipping e tempos. Ha uma **lacuna de captura
durante o processamento**; esse exemplo nao implementa captura continua com
buffer duplo. A taxa efetiva precisa ser medida na placa.

Reproduza `data/example_blackbird.wav` no celular perto do microfone. Verifique
RMS/pico e a classe (esse clip foi reconhecido no host). Se o audio ficar quase
nulo, revisar alimentacao, SD, WS, BCLK e L/R. Se houver clipping, revisar o shift
e a intensidade do som. Concluir aceite somente depois de ouvir uma captura WAV
real e confirmar a execucao na placa. Depois o ESP32 pode funcionar apenas com
alimentacao e microfone: nao usa Wi-Fi, servidor, chave de API ou PC.

Comandos pelo monitor: `p` pausa, `m` retoma, `t` repete o autoteste. Nao envie
`a` em um monitor de texto: esse comando transmite audio binario. Para salvar WAV,
feche o monitor (somente um processo pode abrir a COM) e execute:

```powershell
.\.venv\Scripts\python.exe scripts\capture_serial.py --port COM7 --output data\microfone.wav
```

A captura deixa a placa pausada. Reabra o monitor e envie `m`, ou reinicie a placa.

## Fontes e relacao com o mestrado

O PDF local `Projeto BirdNet - PPGCIS.pdf`, p. 1, propoe ESP32-S3 e microfone I2S;
p. 2 propoe testar modelos no desktop e embarcar TinyML. Este exemplo prepara
essas etapas. Telemetria, LoRa/4G, sensores ambientais, bateria, caixa e camera
sao etapas posteriores descritas na p. 3 e nao foram implementadas aqui.

- [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer)
- [BirdNET Tools](https://birdnet.cornell.edu/tools/?lang=pt-BR)
- [BirdNET-Tiny na documentacao oficial](https://birdnet-team.github.io/BirdNET-Analyzer/dev/birdnet-tiny.html)
- [BirdNET-Tiny Forge](https://github.com/birdnet-team/BirdNET-Tiny-Forge)
- [BioDCASE-Tiny-2026: baseline e limites](https://github.com/birdnet-team/BioDCASE-Tiny-2026)
- [INMP441: datasheet TDK](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf)
- [ESP32-S3 DevKitC: guia Espressif](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)

Licencas e atribuicao em `NOTICE.md`, `firmware/LICENSE` e nos repositorios originais.
Para reinstalar o ambiente Python nesta mesma pasta: `scripts/setup.ps1`.

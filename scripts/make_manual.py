"""Generate the project handbook directly in the project root, as requested."""
import html
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Manual_BirdNET_ESP32S3_Treinamento_Compilacao.pdf'
RECEIPT = json.loads((ROOT / 'results/hardware/receipt.json').read_text())

pages = []


def page(title, blocks):
    pages.append((title, blocks))


page('BirdNET no ESP32-S3', [
    ('subtitle', 'Manual de teste no PC, treinamento, compilação e gravação'),
    ('p', 'Projeto de identificação acústica de aves | ESP32-S3 N16R8 | Windows / PowerShell | 14 de outubro de 2026'),
    ('diagram', ''),
    ('h', 'O que já foi feito nesta placa'),
    ('p', 'A imagem final foi gravada na COM46 e comparada com o conteúdo da flash. O ESP32 iniciou, reconheceu 8 MB de PSRAM e passou no autoteste do processamento de áudio e da inferência. O autoteste usa um WAV embutido no firmware.'),
    ('table', [['Verificação', 'Resultado observado'], ['Flash / PSRAM', '16 MB / 8 MB; teste da PSRAM OK'], ['Features do áudio embutido', '0 divergências em 5.320 valores INT8'], ['Inferência INT8', 'Classe correta; diferença máxima de 1 LSB'], ['Classe do autoteste', 'Eurasian Blackbird / Turdus merula'], ['Memória da arena utilizada', '202.444 bytes'], ['Microfone / cartão SD', 'Ainda não conectados; SD não é necessário']]),
    ('callout', 'Este é um exemplo de bancada com 10 espécies e uma classe Background. Não inclui gralha-azul. O reconhecimento de aves locais exige dados rotulados, treinamento e avaliação de um modelo novo.'),
    ('p', 'O objetivo deste manual é permitir repetir o que foi feito e criar uma nova versão sem substituir silenciosamente a versão validada. O caminho de treinamento foi testado com áudio sintético; isso valida as ferramentas, não a precisão de um classificador de aves reais.'),
])

page('1. Arquivos, versão gravada e mapa do projeto', [
    ('p', 'A pasta principal do projeto é:'),
    ('path', str(ROOT)),
    ('h', 'Imagem exata gravada na COM46'),
    ('path', RECEIPT['firmware_path']),
    ('p', f"Imagem completa: {RECEIPT['firmware_bytes']:,} bytes. Endereço de gravação: 0x0. Ela reúne bootloader, tabela de partições e aplicação."),
    ('p', 'SHA-256 da imagem completa:'),
    ('path', RECEIPT['firmware_sha256']),
    ('p', f"A aplicação isolada é releases/20261014-COM46-validado/passaros_tiny.bin ({RECEIPT['application_bytes']:,} bytes); seu endereço é 0x10000. Não gravar a aplicação isolada em 0x0."),
    ('table', [['Pasta / arquivo', 'Função'], ['firmware/', 'Fontes do exemplo baseline, com correção das camadas densas'], ['releases/20261014-COM46-validado/', 'Cópia da imagem, fontes, configuração, hashes e recibo'], ['models/custom/<versão>/', 'Modelo treinado, labels, referência e avaliação'], ['firmware-custom/<versão>/', 'Projeto C++ gerado para um modelo novo'], ['artifacts-custom/<versão>/', 'Binários compilados desse projeto'], ['scripts/', 'Ferramentas locais descritas neste manual'], ['upstream/', 'Repositórios oficiais preservados'], ['results/hardware/', 'Logs da gravação, verificação e boot']]),
    ('p', 'O primeiro build, que falhou na inferência embarcada, está preservado em releases/20261014-COM46-baseline para diagnóstico. A versão final é a pasta com o sufixo validado.'),
    ('p', 'Backup completo anterior à primeira gravação:'),
    ('path', RECEIPT['backup_path']),
])

page('2. Entender o caminho e preparar o ambiente', [
    ('p', 'Modelo e firmware são coisas diferentes: o modelo contém pesos aprendidos e a ordem das classes; o firmware contém captura I2S, processamento do som, execução do modelo e saída serial. Para trocar as aves reconhecidas é necessário trocar o modelo, os labels e os vetores do autoteste, e recompilar.'),
    ('p', 'O BirdNET-Analyzer é a ferramenta de desktop para analisar gravações. O caminho embarcado usa o processamento do projeto BirdNET/BioDCASE-Tiny e TensorFlow Lite Micro. O script local de treinamento aprende uma CNN pequena do zero; não transfere pesos nem destila o modelo grande do BirdNET.'),
    ('h', 'Ferramentas deste PC'),
    ('table', [['Ferramenta', 'Uso'], ['Python 3.11 / .venv', 'Extração de features, treinamento e geração'], ['TensorFlow 2.21 / LiteRT 2.3', 'Treinar, converter e executar INT8 no host'], ['ESP-IDF 5.5.2', 'Compilar para ESP32-S3'], ['esptool 5.5 / pyserial', 'Gravar, verificar e ler a COM46'], ['GCC/G++', 'Comparar o DSP C++ com a referência Python'], ['FFmpeg', 'Converter e recortar gravações'], ['ReportLab / Poppler', 'Gerar e revisar este PDF']]),
    ('p', 'Abra o PowerShell na pasta principal do projeto. Os comandos seguintes partem dessa pasta. A instalação está pronta. Se precisar reinstalar o ambiente Python nesta mesma cópia:'),
    ('code', 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\setup.ps1\nuv pip check --python .venv/Scripts/python.exe'),
    ('p', 'setup.ps1 instala as versões do lock e prepara o exemplo baseline. Ele não instala o ESP-IDF do zero: usa a instalação existente em C:\\Espressif\\frameworks\\esp-idf-v5.5.2. Em outro computador será necessário instalar esse SDK e adaptar o caminho no launcher.'),
    ('callout', 'O projeto não inicia servidor, banco ou container e não precisa de Wi-Fi para inferir. O cartão SD não participa deste exemplo; modelo na flash, amostras na RAM e logs pela UART.'),
])

page('2A. Escutar pelo microfone do PC', [
    ('p', 'É possível testar o modelo Tiny diretamente no computador, sem conectar o ESP32 ou seu microfone I2S. Abra o PowerShell na pasta principal deste projeto e execute:'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\listen_tiny.py'),
    ('p', 'Espere a mensagem Escutando blocos de 3 segundos. O programa abre o microfone padrão do Windows, analisa blocos de 3 segundos e imprime uma classe por bloco. A primeira inicialização pode demorar mais para carregar o processamento. Ctrl+C encerra e libera o microfone.'),
    ('h', 'Experimentar com um canto do YouTube'),
    ('p', 'Procure Eurasian Blackbird song ou Turdus merula canto: é o melro do áudio de exemplo. Prefira um canto isolado, sem música ou narração. Dê play pelos alto-falantes para que o microfone do PC capte o som. Com fones de ouvido, o microfone pode não ouvir a reprodução. Ajuste o volume para captar o canto sem distorção.'),
    ('p', 'O script lê o microfone; não captura diretamente a faixa de áudio do navegador. A acústica da sala, distância, vento, fala e volume podem mudar a classificação. O resultado esperado para um canto reconhecido do melro é classe=Eurasian Blackbird, mas isso não é garantido para qualquer vídeo.'),
    ('h', 'Escolher outro microfone'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\listen_tiny.py --list-devices\n.\\.venv\\Scripts\\python.exe scripts\\listen_tiny.py --device 9'),
    ('p', '9 é apenas um exemplo: use o ID de uma entrada com canais in na listagem atual. Os IDs podem mudar. Sem --device, o programa usa a entrada padrão. Para um teste limitado a dois blocos, cerca de 6 segundos de áudio:'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\listen_tiny.py --windows 2'),
    ('h', 'Dependência e problemas de captura'),
    ('p', 'sounddevice 0.5.6 já está instalado e registrado no requirements.lock.txt. Se faltar ao reutilizar uma .venv antiga, instale somente essa dependência:'),
    ('code', 'uv pip install --python .venv/Scripts/python.exe sounddevice==0.5.6'),
    ('p', 'Sem entrada ou sem sinal: confira o microfone selecionado, mute, volume e a permissão de microfone para aplicativos de área de trabalho nas configurações do Windows. Audio quase nulo indica RMS menor que 8; esse bloco não é classificado. Se houver perda de amostras, o programa avisa e descarta o bloco.'),
])

page('2B. Entender o teste no PC e seus resultados', [
    ('h', 'O PC usa os mesmos pesos do ESP32?'),
    ('p', 'Sim, neste teste Tiny. listen_tiny.py e infer_tiny.py carregam diretamente firmware/main/model.tflite e a ordem das classes de models/labels.json. Os pesos são os valores aprendidos pela rede durante o treinamento e estão dentro do arquivo .tflite. Escutar ou analisar um WAV executa o modelo sem treinar nem alterar esses pesos.'),
    ('p', 'Os hashes SHA-256 de models/biodcase_baseline.tflite, firmware/main/model.tflite e do modelo preservado em releases/20261014-COM46-validado/source/main/model.tflite coincidiram. O PC usa LiteRT; a placa usa TensorFlow Lite Micro. Os kernels podem gerar pequenas diferenças numéricas: o autoteste registrado da placa manteve a classe e teve erro máximo de 1 unidade INT8.'),
    ('h', 'Do som até a classe'),
    ('p', 'No PC: microfone -> bloco de 3 segundos -> conversão para mono PCM16 a 24 kHz -> features [1,1,40,133] -> modelo INT8 -> classe de maior pontuação. O script captura na taxa padrão do dispositivo e reamostra quando necessário; neste PC foi observada captura a 44.100 Hz. No ESP32, a origem é o microfone I2S e o DSP é executado em C++.'),
    ('h', 'Ler a saída do listen'),
    ('code', 'classe=Eurasian Blackbird score_relativo=0.854\n  rms=850.4 pico=4200 clipping=0'),
    ('p', 'Exemplo ilustrativo, dividido em duas linhas para caber na página; o programa imprime em uma linha. classe é o rótulo vencedor; score_relativo é a softmax entre as classes e não uma probabilidade calibrada de acerto; rms indica nível médio; pico é a maior amplitude; clipping conta amostras saturadas. Há 10 espécies e Background. Sons de aves desconhecidas podem receber uma classe conhecida.'),
    ('h', 'Testar arquivos e consultar o CSV'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\infer_tiny.py\n.\\.venv\\Scripts\\python.exe scripts\\infer_tiny.py `\n  --audio data\\meu_audio.wav'),
    ('p', 'Sem --audio, roda os 11 WAVs de exemplo: o teste registrado acertou 9, o que verifica a execução e não estima precisão em campo. O WAV próprio deve ter exatamente 3 segundos, mono, 24 kHz e PCM16. A saída padrão é results/tiny_python.csv, com resumo em results/tiny_python.json; outra execução substitui esses dois relatórios. Use --output results/meu_teste.csv para separá-los.'),
    ('callout', 'listen_tiny.py mostra resultados no terminal e não salva WAV ou CSV. scripts/analyze.ps1 usa outro modelo: BirdNET 2.4 completo no PC, com saída em results/analyzer/BirdNET_CombinedTable.csv. Esse CSV não é o resultado do Tiny embarcado.'),
])

page('3. Definir classes e organizar gravações', [
    ('p', 'Comece definindo uma lista pequena de aves de interesse e uma classe Background. Background deve incluir ruídos relevantes do local e sons que não sejam das espécies-alvo. Acrescentar o nome de uma espécie a labels.json não ensina seu canto ao modelo.'),
    ('p', 'Gralha-azul pode ser uma classe Cyanocorax_caeruleus, mas só será treinada depois que houver gravações verificadas dessa espécie. Revisar a identidade da ave, a qualidade da gravação e as condições de uso de cada fonte. Guardar procedência, local, data, autoria e licença.'),
    ('h', 'Estrutura exigida por train_tiny.py'),
    ('code', 'data/dataset/\n  metadata.csv\n  Train/\n    Background/*.wav\n    Cyanocorax_caeruleus/*.wav\n  Validation/\n    Background/*.wav\n    Cyanocorax_caeruleus/*.wav\n  Test/\n    Background/*.wav\n    Cyanocorax_caeruleus/*.wav'),
    ('p', 'A pasta define a classe: um WAV em Cyanocorax_caeruleus recebe esse rótulo, qualquer que seja seu nome. Train ajusta pesos, Validation orienta a escolha do modelo e Test mede o resultado final. Todas as classes devem ter WAVs nos três conjuntos.'),
    ('callout', 'Divida por gravação original antes de cortar os trechos. Janelas da mesma gravação, indivíduo ou sessão não devem cair em conjuntos diferentes. Separar também locais/datas quando possível torna a avaliação mais próxima do uso em campo.'),
    ('h', 'Arquivo metadata.csv obrigatório'),
    ('code', 'path,recording_id\nTrain/Background/bg001_000.wav,bg001\nTrain/Background/bg001_001.wav,bg001\nValidation/Background/bg002_000.wav,bg002\nTest/Background/bg003_000.wav,bg003'),
    ('p', 'Liste todos os WAV de todas as classes. path é relativo a data/dataset e usa barras /. recording_id identifica a gravação original, repetindo o mesmo ID para seus recortes. O script bloqueia IDs ou PCM idênticos em conjuntos diferentes e arquivos ausentes/duplicados. Isso não substitui a revisão da origem dos dados.'),
])

page('3A. Como ensinar o canto de uma nova espécie', [
    ('p', 'O fluxo de treinamento já está implementado em scripts/train_tiny.py; as etapas detalhadas estão nas seções 3 a 8. Para ensinar gralha-azul, por exemplo, é preciso reunir áudios reais dessa espécie e ruídos do ambiente. Reproduzir um vídeo no listen apenas testa o modelo atual; não ensina um canto novo.'),
    ('h', 'Classes e arquivos'),
    ('p', '1. Escolha as espécies-alvo. Para reconhecer uma espécie independentemente de seu tipo de vocalização, coloque exemplos revisados dos cantos e chamados desejados na mesma pasta da espécie. Este script usa uma classe por arquivo; evite trechos com identificação ambígua ou várias espécies-alvo simultâneas.'),
    ('p', '2. Reúna gravações independentes, com variação de indivíduos, distâncias e ambientes. Inclua Background com ruídos e sons fora das espécies-alvo. Um único vídeo recortado em muitas janelas não equivale a muitas gravações independentes. A quantidade necessária depende da diversidade e da avaliação; não há mínimo de áudios validado neste projeto.'),
    ('p', '3. Separe as gravações originais entre Train, Validation e Test antes dos cortes. Depois extraia os trechos de 3 segundos no formato da seção 4 e revise seus rótulos. Coloque os WAVs nas pastas de cada classe da seção 3.'),
    ('h', 'Preencher data/dataset/metadata.csv'),
    ('code', 'path,recording_id\nTrain/Cyanocorax_caeruleus/g001_000.wav,g001\nTrain/Cyanocorax_caeruleus/g001_001.wav,g001\nValidation/Cyanocorax_caeruleus/g002_000.wav,g002\nTest/Cyanocorax_caeruleus/g003_000.wav,g003'),
    ('p', '4. Liste todos os WAVs, inclusive Background. O path é relativo a data/dataset, usando /. recording_id identifica a gravação original; repita o mesmo ID em seus recortes e mantenha todos no mesmo conjunto. Esses nomes são exemplos: g001 e bg001 não são áudios reais já fornecidos. O CSV registra a origem; a classe vem da pasta.'),
    ('h', 'Treinar, avaliar e levar para a placa'),
    ('p', '5. Execute o comando da seção 5 em uma pasta de saída nova. Consulte evaluation.json e compare FP32 e INT8 conforme a seção 6. Quando o resultado for adequado, gere firmware-custom com prepare_custom.py, compile e valide na placa conforme as seções 7 a 11.'),
    ('callout', 'O treino local cria uma CNN do zero com as classes do seu dataset. Background + gralha-azul produz um modelo dessas duas classes; não acrescenta automaticamente gralha às dez espécies do baseline. Para manter outras espécies, inclua seus dados no novo treino. Os scripts listen_tiny.py e infer_tiny.py atuais continuam apontando para o baseline e não selecionam um bundle customizado automaticamente. O treino avalia o novo modelo no PC e prepare_custom.py executa sua referência antes da compilação.'),
])

page('4. Preparar WAV e manter o mesmo processamento', [
    ('p', 'Cada entrada de treinamento deve ter exatamente 3 segundos, um canal, 24.000 amostras por segundo e PCM de 16 bits: 72.000 amostras por arquivo. O script rejeita duração, número de canais ou taxa diferentes.'),
    ('h', 'Converter um trecho de 3 segundos'),
    ('code', 'ffmpeg -n -ss 12 -i data\\original.m4a -t 3 `\n  -ac 1 -ar 24000 -c:a pcm_s16le data\\trecho.wav'),
    ('p', 'O exemplo começa no segundo 12. -n impede sobrescrever um arquivo existente. A gravação precisa ter duração suficiente para produzir os 3 segundos completos.'),
    ('h', 'Cortar vários trechos após escolher o conjunto'),
    ('code', 'ffmpeg -n -i data\\original.wav -ac 1 -ar 24000 `\n  -c:a pcm_s16le -f segment -segment_time 3 `\n  data\\dataset\\Train\\Cyanocorax_caeruleus\\g001_%03d.wav'),
    ('p', 'Criar a pasta antes. O último trecho pode ter menos de 3 segundos: não o inclua no dataset nem no metadata.csv. Preserve o original e revise quais trechos realmente contêm a classe rotulada. Não confundir uma pasta de arquivos com rótulos confiáveis.'),
    ('h', 'Contrato DSP preservado'),
    ('table', [['Parâmetro', 'Valor'], ['Áudio', '3 s / 24 kHz / mono / int16'], ['Janela / passo', '4.096 / 512 amostras'], ['Features', '40 bandas, 133 janelas'], ['Faixa mel', '125 a 7.500 Hz'], ['Normalização', 'Min-max por trecho; silêncio tem tratamento explícito'], ['Entrada INT8', '[1, 1, 40, 133]']]),
    ('p', 'As features resumem como a energia do som se distribui ao longo do tempo e das frequências. O modelo aprende padrões nessa matriz. Se o PC e o ESP32 produzirem matrizes diferentes para o mesmo som, o comportamento aprendido não se transfere corretamente.'),
    ('callout', 'Não mudar sample rate, FFT, mel, layout, normalização ou quantização só no Python. Qualquer mudança desse contrato exige adaptar o DSP C++ e repetir a comparação de referência.'),
])

page('5. Treinar uma nova versão', [
    ('p', 'Com o dataset e metadata.csv revisados, execute o treinamento. Use um nome de saída novo para cada experimento; o script recusa uma pasta já existente.'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\train_tiny.py `\n  --dataset data\\dataset --output models\\custom\\gralha-v1 `\n  --epochs 30 --batch-size 16 --seed 42'),
    ('p', '30 épocas é uma configuração inicial do comando, não uma garantia de convergência ou qualidade. O script monitora val_loss, usa EarlyStopping com paciência de 5 épocas e restaura os melhores pesos. O treinamento usa CPU no Windows nativo; este fluxo não configura CUDA/WSL.'),
    ('h', 'O que o script faz'),
    ('p', '1. Verifica gravações, classes, split por origem e duplicatas. 2. Extrai as mesmas features da referência BioDCASE. 3. Treina uma CNN pequena com convoluções, pooling e camadas densas. 4. Ajusta o peso das classes conforme a quantidade de exemplos. 5. Salva o modelo e converte para INT8. 6. Avalia FP32 e INT8 no conjunto Test.'),
    ('p', 'A rede recebe a matriz [1, 40, 133], rearranja para o layout usado nas convoluções e devolve logits, um número por classe. Os labels são ordenados e salvos junto do modelo. A posição de cada label precisa permanecer ligada à posição da saída.'),
    ('h', 'Teste das ferramentas sem dataset real'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\train_tiny.py `\n  --smoke --epochs 1 --output models\\custom\\smoke-novo'),
    ('p', 'Este comando gera áudio sintético com duas classes: Background e Demo_chirp. Foi usado para validar o encadeamento treinamento -> conversão -> exportação -> compilação. Não é um modelo treinado para aves e não deve substituir o firmware de identificação em campo.'),
    ('h', 'Interpretar o treinamento'),
    ('p', 'Loss mede o erro usado para ajustar os pesos. Accuracy mede a fração de acertos naquele conjunto. Se o erro de Train cai e Validation piora, há sinal de overfitting. Para comparar configurações use Validation; só consulte Test após fixar a escolha.'),
])

page('6. Conversão INT8 e avaliação', [
    ('p', 'A quantização representa pesos e ativações com inteiros menores, reduzindo armazenamento e custo de processamento. O treino acontece em ponto flutuante; a etapa INT8 aproxima os valores usando scale e zero_point.'),
    ('code', 'q = clip(x / scale + zero_point, -128, 127)\nx_aproximado = (q - zero_point) * scale'),
    ('p', 'Neste projeto, a conversão da entrada para int8 preserva o truncamento da referência BioDCASE. Não trocar silenciosamente por outra regra de arredondamento. O conversor usa até 200 exemplos de Train para calibração, exige operações INT8 e entrada/saída INT8. Ele não usa Test para calibrar.'),
    ('table', [['Arquivo no bundle', 'Conteúdo'], ['model.keras', 'Rede e pesos em ponto flutuante'], ['model.int8.tflite', 'Modelo convertido para embarcar'], ['labels.json', 'Ordem das classes'], ['metadata.json', 'DSP, quantização, operadores, hash e seed'], ['reference.wav', 'Áudio de Validation usado no autoteste'], ['evaluation.json', 'Métricas FP32/INT8, matriz de confusão e inventário']]),
    ('h', 'Consultar o resultado'),
    ('code', '.\\.venv\\Scripts\\python.exe -c "import json; `\n+  from pathlib import Path; `\n+  p=Path(\'models/custom/gralha-v1/evaluation.json\'); `\n+  print(json.loads(p.read_text())[\'test_int8\'])"'.replace('\n+','\n')),
    ('p', 'A matriz de confusão mostra quais classes se confundem. Precision indica a proporção de avisos de uma classe que estavam corretos; recall indica a proporção dos exemplos dessa classe encontrados. Inspecione também falsos positivos em ruído e aves fora da lista. Defina critérios de aprovação antes de coletar os números.'),
    ('callout', 'Compare FP32 e INT8. Se a conversão reduzir muito as métricas, revise a calibração, os dados e a arquitetura. Um arquivo pequeno que compila não prova qualidade acústica, e a softmax dos logits não é uma confiança calibrada.'),
    ('p', 'Compatibilidade das camadas densas: o treinamento local desabilita quantização por canal nessas camadas. O firmware também usa o kernel de referência TFLM para suportar o modelo oficial já quantizado por canal. As convoluções mantêm kernels ESP-NN.'),
])

page('7. Gerar o projeto C++ do novo modelo', [
    ('p', 'Não substituir apenas model.tflite. Labels, PCM de referência, entrada INT8 e saída esperada devem ser gerados junto dele. prepare_custom.py cria uma pasta de firmware separada e preserva o baseline.'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\prepare_custom.py `\n  --bundle models\\custom\\gralha-v1 `\n  --output-firmware firmware-custom\\gralha-v1'),
    ('p', 'O script confere hash, DSP, tipo/layout da entrada, quantidade de classes, logits e operadores. Executa o novo modelo no PC e compara o DSP C++ com Python para o WAV de referência. Se houver incompatibilidade, interrompe a exportação.'),
    ('h', 'Arquivos gerados em firmware-custom/gralha-v1/main'),
    ('table', [['Arquivo', 'Função'], ['model.tflite', 'Bytes do novo modelo'], ['labels.h', 'Nomes na ordem da saída'], ['reference_audio.pcm', '3 segundos usados no autoteste'], ['reference_input.bin', 'Features INT8 esperadas'], ['reference_output.bin', 'Saída INT8 esperada no host'], ['feature_constants.h', 'Constantes do DSP mantido'], ['main.cpp', 'Captura e inferência com número de classes adaptado'], ['fully_connected_reference.cpp', 'Kernel denso com suporte por canal']]),
    ('p', 'training_bundle.json registra os metadados usados. O projeto usa a mesma arena de 512 KiB; se um modelo novo exigir mais, revisar o orçamento de RAM antes de aumentar. O teste na placa deve confirmar a alocação e os tempos.'),
    ('h', 'Problemas que bloqueiam exportação'),
    ('p', 'Hash mudou; labels não correspondem à saída; input shape diferente de [1,1,40,133]; modelo não INT8; operador não suportado; contrato DSP modificado; faixa de quantização inesperada; referência inválida; comparação C++/Python falhou. Corrija a causa e crie uma saída nova.'),
    ('callout', 'Não editar o autoteste para aceitar uma classe errada. Ele existe para detectar diferenças de execução antes de analisar o microfone. Avaliação do dataset e autoteste embarcado verificam problemas diferentes.'),
])

page('8. Compilar para a N16R8', [
    ('p', 'Compile o projeto gerado com um BuildName exclusivo. Assim o ESP-IDF usa um diretório curto separado e não mistura o build do baseline com o do modelo novo.'),
    ('code', 'powershell -NoProfile -ExecutionPolicy Bypass `\n  -File scripts\\build.ps1 -Action build `\n  -FirmwareDir firmware-custom\\gralha-v1 `\n  -BuildName gralha-v1 -ArtifactsDir artifacts-custom\\gralha-v1'),
    ('p', 'Neste exemplo, o build fica em C:\\Users\\luizf\\birdnet-build\\gralha-v1. As fontes permanecem na pasta do projeto. O launcher reutiliza o ESP-IDF 5.5.2 e exporta os binários ao diretório indicado.'),
    ('table', [['Saída', 'Uso'], ['flash-full.bin', 'Imagem completa, gravação a partir de 0x0'], ['passaros_tiny.bin', 'Aplicação isolada, endereço 0x10000'], ['bootloader.bin', 'Inicialização, endereço 0x0'], ['partition-table.bin', 'Mapa da flash, endereço 0x8000'], ['passaros_tiny.elf', 'Símbolos para diagnóstico'], ['sdkconfig / dependencies.lock', 'Configuração e dependências efetivas'], ['flasher_args.json / flash_args', 'Endereços e argumentos da imagem']]),
    ('h', 'Configuração de hardware'),
    ('p', 'ESP32-S3; flash quad DIO de 16 MB a 80 MHz; PSRAM octal de 8 MB a 80 MHz; CPU de 240 MHz; console UART0 a 115200 baud. Essa combinação foi conferida na COM46. Para outra placa, verificar a variante real antes de gravar.'),
    ('p', 'Para trocar GPIOs ou canal do microfone, use -Action menuconfig com os mesmos FirmwareDir e BuildName, no menu Passaros - microfone I2S externo. Depois repita -Action build. As escolhas ficam no sdkconfig do diretório de build.'),
    ('callout', 'A mensagem Project build complete prova que a compilação terminou. Ela não grava a placa. Depois confira o tamanho, os hashes, o autoteste embarcado e a avaliação acústica.'),
])

page('9. Backup, gravação e verificação', [
    ('p', 'A placa deste projeto está em COM46, identificada como USB-Enhanced-SERIAL CH343. Só um programa pode abrir a COM por vez. Feche monitores seriais antes de usar esptool. O exemplo usa o conector USB-UART, não depende de USB nativo.'),
    ('h', 'Confirmar placa e salvar backup'),
    ('code', '.\\.venv\\Scripts\\python.exe -m esptool `\n  --chip esp32s3 --port COM46 flash-id\n.\\.venv\\Scripts\\python.exe -m esptool `\n  --chip esp32s3 --port COM46 --baud 921600 `\n  read-flash 0 ALL backups\\COM46-antes-gralha-v1.bin'),
    ('p', 'Use nome de backup novo. Nesta preparação foi salvo o conteúdo inteiro de 16 MB antes da primeira escrita. A imagem completa escreve também os intervalos preenchidos entre as regiões e pode substituir dados nesses endereços; o backup permite preservar o estado anterior.'),
    ('h', 'Gravar a nova imagem e compará-la'),
    ('code', '.\\.venv\\Scripts\\python.exe -m esptool `\n  --chip esp32s3 --port COM46 --baud 921600 `\n  write-flash --flash-mode dio --flash-size 16MB `\n  --flash-freq 80m 0x0 artifacts-custom\\gralha-v1\\flash-full.bin\n\n.\\.venv\\Scripts\\python.exe -m esptool `\n  --chip esp32s3 --port COM46 --baud 921600 `\n  verify-flash 0x0 artifacts-custom\\gralha-v1\\flash-full.bin'),
    ('p', 'write-flash deve concluir a escrita e verificar o hash. verify-flash compara novamente a imagem com a placa e deve retornar Verification successful. Se houver timeout, revisar cabo, COM e BOOT/RESET, ou reduzir o baudrate a 460800.'),
    ('h', 'Ler o boot por um tempo limitado'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\read_serial.py `\n  --port COM46 --reset --seconds 30 `\n  --output results\\hardware\\gralha-v1-boot.log'),
    ('p', 'O script abre a serial, faz reset e salva o boot. Não roda para sempre. Para recuperar o estado anterior, use write-flash 0x0 com o backup completo correspondente, mantendo a placa correta. Não use um backup de outra placa.'),
])

page('10. Testes que funcionam só com o ESP32', [
    ('p', 'Neste momento não há microfone nem cartão SD. Isso não impede testar flash, PSRAM, processamento e modelo. O arquivo reference_audio.pcm vem embutido na aplicação e reproduz a entrada do autoteste.'),
    ('h', 'Sequência esperada no boot'),
    ('code', 'Found 8MB PSRAM device\nSPI SRAM memory test OK\nArena utilizada=202444\nSELFTEST_FEATURES: divergencias=0/5320\nSELFTEST_MODEL: erro_max_LSB=1\n  previsto=Eurasian Blackbird esperado=Eurasian Blackbird\nSELFTEST_OK: iniciando captura autonoma I2S GPIO4/5/6'),
    ('p', 'Esses resultados foram observados na COM46 com a imagem final. Para um novo modelo, a classe, a arena e os tempos podem mudar, mas o teste precisa continuar comparando features e saída com a referência correspondente.'),
    ('p', 'O firmware aceita erro máximo de 2 LSB na saída INT8, desde que a classe seja a mesma. LSB é uma unidade do inteiro quantizado. Ele exige comparação exata das features. Se falhar, a inicialização da captura é bloqueada.'),
    ('h', 'Correção necessária encontrada na bancada'),
    ('p', 'A primeira imagem tinha features corretas, mas devolveu Background para o exemplo Eurasian Blackbird. A leitura do kernel mostrou que a implementação ESP-NN das camadas densas desse commit não aplicava os multiplicadores por canal exigidos pelo modelo. A versão final registra nessas camadas o kernel de referência TFLM, que aplica a quantização por canal; as convoluções mantêm ESP-NN.'),
    ('p', 'Depois da correção, a classe coincidiu com a referência e o erro máximo caiu de 156 para 1 unidade INT8. Não foi necessário mudar os pesos nem relaxar o autoteste.'),
    ('callout', 'Sem microfone, Audio quase nulo rms=0.0 é esperado. Não é evidência de falha do modelo. O teste de captura acústica só poderá ser aprovado depois da ligação do microfone.'),
])

page('11. Quando o microfone chegar', [
    ('p', 'O exemplo está configurado para um microfone digital INMP441 externo. Desligue a alimentação antes de fazer as conexões. Não é necessário cartão SD.'),
    ('table', [['INMP441', 'ESP32-S3'], ['VDD / VCC', '3V3'], ['GND', 'GND'], ['SCK / BCLK', 'GPIO4'], ['WS / LRCLK', 'GPIO5'], ['SD / DOUT', 'GPIO6'], ['L/R', 'GND, canal esquerdo']]),
    ('p', 'O INMP441 fornece I2S de 24 bits; o firmware usa slots de 32 bits e desloca 16 bits para formar PCM16. Se outro microfone for usado, conferir formato, alimentação, canal e shift. Não ligar VCC do INMP441 ao 5V.'),
    ('h', 'Teste de áudio real'),
    ('p', '1. Ligue a placa e confirme SELFTEST_OK. 2. Fale ou reproduza um WAV conhecido próximo do microfone. 3. Confira RMS, pico e clipping. 4. Salve um WAV real e ouça a gravação. 5. Teste as aves-alvo e ruídos fora da lista. 6. Meça tempo de DSP, tempo de inferência e consumo com a alimentação prevista.'),
    ('code', '.\\.venv\\Scripts\\python.exe scripts\\capture_serial.py `\n  --port COM46 --output data\\microfone.wav'),
    ('p', 'Feche o monitor antes da captura. Esse script envia o comando binário de exportação de 3 segundos e salva o WAV. A placa fica pausada após a exportação; reabra o monitor e envie m, ou reinicie. No monitor: p pausa, m retoma, t repete autoteste. Não envie a em um monitor textual porque a saída é PCM binário.'),
    ('p', 'O ciclo atual captura 3 segundos, depois processa e infere. Há uma lacuna durante o processamento: não é captura contínua com buffer duplo. A inferência é autônoma, sem PC ou rede, mas os resultados deste exemplo só aparecem na serial; não há armazenamento persistente de eventos.'),
    ('callout', 'Se RMS ficar zerado com o microfone instalado, conferir 3V3, GND, SCK, WS, SD e L/R. Se houver clipping, revisar intensidade e shift. Uma espécie fora dos labels pode ser atribuída à classe mais parecida; não interpretar isso como identificação válida.'),
])

page('12. Repetição, diagnóstico e fontes', [
    ('h', 'Sequência para cada versão nova'),
    ('p', 'Dados rotulados e separados por origem -> WAV padronizados -> treinamento -> avaliação FP32/INT8 -> exportação com referência -> compilação em build separado -> backup -> gravação/verificação -> autoteste no ESP32 -> teste acústico e energético. Guarde dados, configuração, avaliação, bundle, fontes, ELF, binários, hashes e logs.'),
    ('h', 'Falhas comuns'),
    ('table', [['Sintoma', 'Próxima verificação'], ['Pasta de saída já existe', 'Escolher versão nova; preservar a anterior'], ['Vazamento de recording_id', 'Refazer a divisão por gravação original'], ['WAV com tamanho incorreto', 'Taxa, canais, 3 s exatos e último segmento'], ['Modelo/operador incompatível', 'Metadata, input shape, INT8 e resolver'], ['Erro de caminho com acento', 'Usar launcher e diretório de build curto'], ['PSRAM não encontrada', 'Variante N16R8, modo octal e alimentação'], ['SELFTEST_FEATURES falhou', 'Contrato DSP, quantização e referência'], ['SELFTEST_MODEL falhou', 'Modelo, kernels, labels e referência'], ['COM46 ocupada', 'Fechar o monitor que abriu essa COM'], ['Áudio zerado sem microfone', 'Resultado esperado; instalar microfone depois']]),
    ('h', 'Fontes primárias e arquivos locais'),
    ('link', ('BioDCASE-Tiny-2026 - modelo e referência DSP', 'https://github.com/birdnet-team/BioDCASE-Tiny-2026')),
    ('link', ('BirdNET-Analyzer - análise de desktop', 'https://github.com/birdnet-team/BirdNET-Analyzer')),
    ('link', ('BirdNET-Tiny Forge - rota oficial alternativa', 'https://github.com/birdnet-team/BirdNET-Tiny-Forge')),
    ('link', ('Google LiteRT - quantização inteira', 'https://developers.google.com/edge/litert/conversion/tensorflow/quantization/post_training_integer_quant')),
    ('link', ('Espressif - TensorFlow Lite Micro', 'https://github.com/espressif/esp-tflite-micro')),
    ('link', ('python-sounddevice - captura pelo microfone do PC', 'https://python-sounddevice.readthedocs.io/en/latest/api/streams.html')),
    ('link', ('TDK - datasheet INMP441', 'https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf')),
    ('p', 'Origem do baseline: BioDCASE commit a62675704019fc8a0bcc4e2f64346698ea501a32. Runtime ESP-TFLM: 416d3713e9312025df434d6f33600ec490705b3d. O modelo baseline segue os labels oficiais; a CNN do script local é uma adaptação para treinamento, não um novo modelo oficial BirdNET.'),
    ('p', 'Projeto BirdNet - PPGCIS.pdf, páginas 1-2: ESP32-S3, microfone I2S, estudo no desktop e TinyML. Recibo desta bancada: results/hardware/receipt.json. Logs: flash-final.log, verify-final.log e serial-final.log. Licenças: NOTICE.md e firmware/LICENSE.'),
])


def main():
    for name, filename in [('Body','segoeui.ttf'), ('Bold','segoeuib.ttf'), ('Mono','consola.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / filename)))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyLocal', fontName='Body', fontSize=9.7, leading=14.2, spaceAfter=9))
    styles.add(ParagraphStyle(name='HeadingLocal', fontName='Bold', fontSize=12.3, leading=16, textColor=colors.HexColor('#194C46'), spaceBefore=8, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle(name='TitleLocal', fontName='Bold', fontSize=21, leading=26, textColor=colors.HexColor('#163E38'), spaceAfter=13))
    styles.add(ParagraphStyle(name='SubtitleLocal', fontName='Body', fontSize=14, leading=19, spaceAfter=16))
    styles.add(ParagraphStyle(name='CodeLocal', fontName='Mono', fontSize=7.8, leading=10.5, backColor=colors.HexColor('#F0F4F3'), borderPadding=9, spaceBefore=5, spaceAfter=12))
    styles.add(ParagraphStyle(name='PathLocal', fontName='Mono', fontSize=8, leading=11, wordWrap='CJK', backColor=colors.HexColor('#F0F4F3'), borderPadding=7, spaceAfter=12))
    styles.add(ParagraphStyle(name='CellLocal', fontName='Body', fontSize=8.4, leading=11.6))
    styles.add(ParagraphStyle(name='CalloutLocal', fontName='Body', fontSize=9.5, leading=13.8, textColor=colors.HexColor('#194C46'), backColor=colors.HexColor('#EAF4EF'), borderPadding=9, spaceBefore=7, spaceAfter=14))
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=43, leftMargin=43, topMargin=48, bottomMargin=47,
                            title='Manual BirdNET ESP32-S3: treinamento ate compilacao', author='Projeto Passaros / Luiz')
    story = []
    source_md = []
    for number, (title, blocks) in enumerate(pages):
        if number:
            story.append(PageBreak())
        story.append(Paragraph(html.escape(title), styles['TitleLocal']))
        source_md.append('# ' + title + '\n')
        for kind, value in blocks:
            if kind == 'diagram':
                drawing = Drawing(490, 76)
                for i, label in enumerate(['Áudio / I2S', 'Features DSP', 'Modelo INT8', 'Classe / serial']):
                    x = i * 124
                    drawing.add(Rect(x, 22, 114, 35, rx=6, ry=6, fillColor=colors.HexColor('#EAF4EF'), strokeColor=colors.HexColor('#5A8878')))
                    drawing.add(String(x+57, 36, label, fontName='Body', fontSize=9, textAnchor='middle', fillColor=colors.HexColor('#194C46')))
                    if i < 3:
                        drawing.add(Line(x+115, 40, x+123, 40, strokeColor=colors.HexColor('#194C46')))
                story.append(drawing)
                continue
            if kind == 'table':
                cells = [[Paragraph(html.escape(cell), styles['CellLocal']) for cell in row] for row in value]
                table = Table(cells, colWidths=[189, doc.width-189], hAlign='LEFT', repeatRows=1)
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEBE4')),
                                          ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F6F8F7')]),
                                          ('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING',(0,0),(-1,-1),8),
                                          ('RIGHTPADDING',(0,0),(-1,-1),8), ('TOPPADDING',(0,0),(-1,-1),6),
                                          ('BOTTOMPADDING',(0,0),(-1,-1),6),
                                          ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#5A8878'))]))
                story.extend([table, Spacer(1,12)])
                source_md.append('| ' + ' | '.join(value[0]) + ' |')
                source_md.append('| ' + ' | '.join('---' for _ in value[0]) + ' |')
                source_md.extend('| ' + ' | '.join(row) + ' |' for row in value[1:])
                source_md.append('')
                continue
            if kind == 'link':
                label, url = value
                story.append(Paragraph(f'<link href="{html.escape(url)}" color="#245D85">{html.escape(label)}</link>', styles['BodyLocal']))
                source_md.append(f'[{label}]({url})\n')
                continue
            if kind == 'code':
                for line in value.splitlines():
                    if pdfmetrics.stringWidth(line, 'Mono', 7.8) > doc.width-18:
                        raise ValueError(f'Linha de comando excede a largura: {line}')
                story.append(Preformatted(value, styles['CodeLocal']))
                source_md.append('```powershell\n'+value+'\n```\n')
                continue
            style = {'p':'BodyLocal','h':'HeadingLocal','subtitle':'SubtitleLocal','path':'PathLocal','callout':'CalloutLocal'}[kind]
            story.append(Paragraph(html.escape(value), styles[style]))
            source_md.append(('## ' if kind == 'h' else '') + value + '\n')
    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor('#DCEBE4'))
        canvas.line(43, 36, A4[0]-43, 36)
        canvas.setFont('Body', 8)
        canvas.setFillColor(colors.HexColor('#56736A'))
        canvas.drawString(43, 23, 'Passaros | ESP32-S3 N16R8 | 14/10/2026')
        canvas.drawRightString(A4[0]-43, 23, str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    (ROOT / 'docs/Manual_BirdNET_ESP32S3_Treinamento_Compilacao.md').write_text('\n'.join(source_md), encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()

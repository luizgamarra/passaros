"""Export a compatible trained bundle into a separate firmware project."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from train_tiny import CONTRACT, ROOT, read_clip, extract, FeatureHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output-firmware', required=True, type=Path)
    args = parser.parse_args()
    metadata = json.loads((args.bundle / 'metadata.json').read_text())
    labels = json.loads((args.bundle / 'labels.json').read_text(encoding='utf-8'))
    if metadata['preprocessing'] != CONTRACT:
        raise ValueError('O contrato DSP do bundle difere do firmware')
    if labels != metadata['labels'] or len(labels) < 2 or len(set(labels)) != len(labels):
        raise ValueError('Labels inconsistentes')
    binary = (args.bundle / 'model.int8.tflite').read_bytes()
    if hashlib.sha256(binary).hexdigest() != metadata['model_sha256']:
        raise ValueError('Hash do modelo difere dos metadados')
    interpreter = Interpreter(model_content=binary, num_threads=1)
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    if input_detail['shape'].tolist() != [1,1,40,133] or input_detail['dtype'] != np.int8:
        raise ValueError('Entrada precisa ser INT8 [1,1,40,133]')
    if output_detail['shape'].tolist() != [1,len(labels)] or output_detail['dtype'] != np.int8:
        raise ValueError('Saida INT8/classes incompativeis')
    operations = {item['op_name'] for item in interpreter._get_ops_details()} - {'DELEGATE'}
    allowed = {'CONV_2D','DEPTHWISE_CONV_2D','FULLY_CONNECTED','RESHAPE','TRANSPOSE','SUM','MEAN','MAX_POOL_2D','SOFTMAX'}
    if not operations <= allowed:
        raise ValueError(f'Operadores nao suportados: {operations-allowed}')
    pcm = read_clip(args.bundle / 'reference.wav')
    handler = FeatureHandler(add_batch_dimension=False)
    features = extract(pcm, handler)[np.newaxis]
    scale, zero = input_detail['quantization']
    quantized = np.clip(features/scale+zero, -128,127).astype(np.int8)
    interpreter.set_tensor(input_detail['index'], quantized)
    interpreter.invoke()
    reference_output = interpreter.get_tensor(output_detail['index'])[0]
    # Match the already verified portable C++ DSP with this model's input range.
    if not np.isclose(scale, 1/255, rtol=1e-6) or zero != -128:
        raise ValueError('Faixa de calibracao inesperada; revisar gerador/teste de paridade')
    subprocess.run(['g++','-std=c++20','-O2','-Ifirmware/main','scripts/preprocess_host.cpp',
                    'firmware/main/preprocess.cpp','-o','results/preprocess_host.exe'], cwd=ROOT, check=True)
    (ROOT / 'results/custom_reference.pcm').write_bytes(pcm.astype('<i2').tobytes())
    subprocess.run(['results/preprocess_host.exe','results/custom_reference.pcm','results/custom_reference.bin'], cwd=ROOT, check=True)
    actual = (ROOT / 'results/custom_reference.bin').read_bytes()
    if actual != quantized.tobytes():
        raise ValueError('Paridade C++/Python falhou para o audio de referencia do novo modelo')
    # A new directory preserves the baseline and avoids silently replacing a candidate.
    shutil.copytree(ROOT / 'firmware', args.output_firmware, dirs_exist_ok=False)
    main_dir = args.output_firmware / 'main'
    (main_dir / 'model.tflite').write_bytes(binary)
    (main_dir / 'reference_audio.pcm').write_bytes(pcm.astype('<i2').tobytes())
    (main_dir / 'reference_input.bin').write_bytes(quantized.tobytes())
    (main_dir / 'reference_output.bin').write_bytes(reference_output.tobytes())
    (main_dir / 'labels.h').write_text('#pragma once\ninline constexpr const char* kLabels[] = {' +
                                      ','.join(json.dumps(label) for label in labels) + '};\n', encoding='utf-8')
    source_path = main_dir / 'main.cpp'
    source = source_path.read_text(encoding='utf-8')
    source = source.replace('constexpr size_t Arena =', 'constexpr int kClassCount = sizeof(kLabels)/sizeof(kLabels[0]);\nconstexpr size_t Arena =')
    source = source.replace('i < 11', 'i < kClassCount').replace('+ 11', '+ kClassCount').replace('bytes != 11', 'bytes != kClassCount')
    source = source.replace('MicroMutableOpResolver<8>', 'MicroMutableOpResolver<9>')
    source = source.replace('resolver.AddSum() != kTfLiteOk ||', 'resolver.AddSum() != kTfLiteOk || resolver.AddMean() != kTfLiteOk ||')
    source = source.replace('BirdNET Tiny exemplo N16R8; especies europeias, sem gralha-azul', 'BirdNET/BioDCASE Tiny CNN local N16R8; conferir labels do bundle')
    if 'i < 11' in source or '+ 11' in source or 'bytes != 11' in source:
        raise ValueError('Template de firmware precisa de revisao')
    source_path.write_text(source, encoding='utf-8')
    (args.output_firmware / 'training_bundle.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps({'firmware': str(args.output_firmware.resolve()), 'classes': len(labels),
                      'model_bytes': len(binary), 'host_parity': 'exact', 'smoke_only': metadata['smoke_only']}))


if __name__ == '__main__':
    main()

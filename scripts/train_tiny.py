"""Local BirdNET/BioDCASE-derived TinyML training path for the fixed firmware DSP.

This trains a small CNN from the supplied labels; it does not transfer or distil
the large BirdNET-Analyzer model. --smoke uses synthetic audio for tool testing.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
import numpy as np
import soundfile as sf
import tensorflow as tf
from ai_edge_litert.interpreter import Interpreter
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'upstream/BioDCASE-Tiny-2026'))
from feature_handler import FeatureHandler

CONTRACT = {'sample_rate': 24000, 'samples': 72000, 'input_shape': [1, 1, 40, 133],
            'window_len': 4096, 'window_stride': 512, 'window_scaling_bits': 12,
            'mel_n_channels': 40, 'mel_low_hz': 125, 'mel_high_hz': 7500,
            'mel_post_scaling_bits': 6, 'normalization': 'per_clip_minmax', 'output': 'logits'}


def read_clip(path):
    pcm, rate = sf.read(path, dtype='int16')
    if rate != 24000 or pcm.shape != (72000,):
        raise ValueError(f'{path}: WAV deve ter 3 s, mono, 24000 Hz; recebido {rate}, {pcm.shape}')
    return pcm


def extract(pcm, handler):
    if not np.any(pcm):
        return np.zeros((1, 40, 133), dtype=np.float32)
    features = handler.extract(pcm).astype(np.float32)
    if not np.isfinite(features).all():
        raise ValueError('Features indefinidas: revisar PCM/normalizacao')
    return features


def synthetic_dataset(destination):
    rng = np.random.default_rng(42)
    times = np.arange(72000) / 24000
    rows = []
    for split, count in [('Train', 8), ('Validation', 3), ('Test', 3)]:
        for label in ['Background', 'Demo_chirp']:
            folder = destination / split / label
            folder.mkdir(parents=True)
            for index in range(count):
                audio = rng.normal(0, 0.02, 72000)
                if label != 'Background':
                    frequency = rng.uniform(1000, 3000)
                    envelope = np.square(np.sin(np.pi * 3 * times))
                    audio += 0.25 * envelope * np.sin(2*np.pi*(frequency*times + 300*times**2))
                pcm = np.clip(audio*32767, -32768, 32767).astype(np.int16)
                path = folder / f'{index:03}.wav'
                sf.write(path, pcm, 24000, subtype='PCM_16')
                rows.append({'path': path.relative_to(destination).as_posix(),
                             'recording_id': f'{split}-{label}-{index}'})
    with (destination / 'metadata.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['path', 'recording_id'])
        writer.writeheader()
        writer.writerows(rows)


def load_dataset(dataset):
    metadata_path = dataset / 'metadata.csv'
    if not metadata_path.is_file():
        raise ValueError('Falta metadata.csv com colunas path e recording_id; separar por gravacao original')
    with metadata_path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    metadata = {row['path'].replace('\\', '/'): row['recording_id'] for row in rows}
    if len(metadata) != len(rows) or any(not value.strip() for value in metadata.values()):
        raise ValueError('Metadata duplicada ou recording_id vazio')
    labels = sorted(path.name for path in (dataset / 'Train').iterdir() if path.is_dir())
    if 'Background' not in labels or len(labels) < 2:
        raise ValueError('Incluir Background e ao menos uma especie')
    handler = FeatureHandler(add_batch_dimension=False)
    outputs, recording_split, pcm_split, used_paths = {}, {}, {}, set()
    inventory = []
    for split in ('Train', 'Validation', 'Test'):
        actual_labels = sorted(path.name for path in (dataset / split).iterdir() if path.is_dir())
        if labels != actual_labels:
            raise ValueError(f'{split}: classes devem ser identicas a Train')
        x, y, paths = [], [], []
        for index, label in enumerate(labels):
            wavs = sorted((dataset / split / label).glob('*.wav'))
            if not wavs:
                raise ValueError(f'{split}/{label}: classe vazia')
            for wav in wavs:
                relative = wav.relative_to(dataset).as_posix()
                recording = metadata.get(relative)
                if recording is None:
                    raise ValueError(f'{relative}: ausente em metadata.csv')
                if recording in recording_split and recording_split[recording] != split:
                    raise ValueError(f'Vazamento de dados: gravacao {recording} em dois splits')
                recording_split[recording] = split
                pcm = read_clip(wav)
                sha = hashlib.sha256(pcm.astype('<i2').tobytes()).hexdigest()
                if sha in pcm_split and pcm_split[sha] != split:
                    raise ValueError(f'Audio duplicado entre splits: {relative}')
                pcm_split[sha] = split
                used_paths.add(relative)
                x.append(extract(pcm, handler)); y.append(index); paths.append(wav)
                inventory.append({'path': relative, 'recording_id': recording, 'pcm_sha256': sha})
        outputs[split] = (np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.int32), paths)
    if used_paths != set(metadata):
        raise ValueError('metadata.csv precisa listar exatamente os WAV usados')
    return labels, outputs, inventory


def make_model(classes):
    inputs = tf.keras.Input(shape=(1, 40, 133))
    x = tf.keras.layers.Permute((2, 3, 1))(inputs)
    x = tf.keras.layers.Conv2D(8, 3, activation='relu')(x)
    x = tf.keras.layers.MaxPool2D(2)(x)
    x = tf.keras.layers.DepthwiseConv2D(3, activation='relu')(x)
    x = tf.keras.layers.Conv2D(16, 1, activation='relu')(x)
    x = tf.keras.layers.MaxPool2D(2)(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(16, activation='relu')(x)
    logits = tf.keras.layers.Dense(classes)(x)
    model = tf.keras.Model(inputs, logits, name='passaros_tiny_cnn')
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    return model


def evaluation(labels, truth, prediction):
    indices = list(range(len(labels)))
    return {'confusion_matrix': confusion_matrix(truth, prediction, labels=indices).tolist(),
            'classification': classification_report(truth, prediction, labels=indices, target_names=labels,
                                                    output_dict=True, zero_division=0)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1:
        parser.error('epochs e batch-size precisam ser positivos')
    if not args.smoke and args.dataset is None:
        parser.error('Informe --dataset ou use --smoke para teste sintetico')
    args.output.mkdir(parents=True, exist_ok=False)
    dataset = args.dataset
    if args.smoke:
        dataset = args.output / 'technical_dataset'
        synthetic_dataset(dataset)
    tf.config.threading.set_intra_op_parallelism_threads(2)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    tf.keras.utils.set_random_seed(args.seed)
    labels, splits, inventory = load_dataset(dataset)
    x_train, y_train, _ = splits['Train']
    x_val, y_val, val_paths = splits['Validation']
    x_test, y_test, _ = splits['Test']
    model = make_model(len(labels))
    counts = np.bincount(y_train, minlength=len(labels))
    class_weight = {i: len(y_train)/(len(labels)*int(count)) for i, count in enumerate(counts)}
    history = model.fit(x_train, y_train, validation_data=(x_val, y_val), epochs=args.epochs,
                        batch_size=args.batch_size, class_weight=class_weight,
                        callbacks=[tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5,
                                                                    restore_best_weights=True)], verbose=2)
    model.save(args.output / 'model.keras')
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    def representative():
        for features in x_train[:min(200, len(x_train))]:
            yield [features[np.newaxis].astype(np.float32)]
    converter.representative_dataset = representative
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter._experimental_disable_per_channel_quantization_for_dense_layers = True
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    binary = converter.convert()
    (args.output / 'model.int8.tflite').write_bytes(binary)
    interpreter = Interpreter(model_content=binary, num_threads=1)
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    assert input_detail['shape'].tolist() == CONTRACT['input_shape'] and input_detail['dtype'] == np.int8
    assert output_detail['dtype'] == np.int8
    ops = sorted({item['op_name'] for item in interpreter._get_ops_details()} - {'DELEGATE'})
    allowed = {'CONV_2D','DEPTHWISE_CONV_2D','FULLY_CONNECTED','RESHAPE','TRANSPOSE','SUM','MEAN','MAX_POOL_2D','SOFTMAX'}
    if not set(ops) <= allowed:
        raise ValueError(f'Operadores nao suportados pelo firmware: {set(ops)-allowed}')
    int8_predictions = []
    scale, zero = input_detail['quantization']
    for features in x_test:
        quantized = np.clip(features[np.newaxis]/scale+zero, -128, 127).astype(np.int8)
        interpreter.set_tensor(input_detail['index'], quantized)
        interpreter.invoke()
        int8_predictions.append(int(np.argmax(interpreter.get_tensor(output_detail['index']))))
    fp32_predictions = np.argmax(model.predict(x_test, verbose=0), axis=-1)
    val_predictions = np.argmax(model.predict(x_val, verbose=0), axis=-1)
    reference_index = next(i for i, path in enumerate(val_paths) if path.parent.name != 'Background')
    shutil.copyfile(val_paths[reference_index], args.output / 'reference.wav')
    (args.output / 'labels.json').write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding='utf-8')
    metadata = {'preprocessing': CONTRACT, 'labels': labels, 'operators': ops,
                'input_quantization': input_detail['quantization'], 'output_quantization': output_detail['quantization'],
                'model_bytes': len(binary), 'model_sha256': hashlib.sha256(binary).hexdigest(),
                'seed': args.seed, 'smoke_only': args.smoke,
                'note': 'Local CNN trained from scratch using BirdNET/BioDCASE DSP; no large BirdNET weights.'}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    report = {'validation_fp32': evaluation(labels,y_val,val_predictions),
              'test_fp32': evaluation(labels,y_test,fp32_predictions),
              'test_int8': evaluation(labels,y_test,int8_predictions),
              'history': history.history, 'samples': {name: len(values[1]) for name, values in splits.items()},
              'smoke_only': args.smoke, 'inventory': inventory}
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'bundle': str(args.output.resolve()), 'model_bytes': len(binary),
                      'operators': ops, 'smoke_only': args.smoke}))


if __name__ == '__main__':
    main()

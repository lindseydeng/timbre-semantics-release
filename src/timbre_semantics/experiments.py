"""Inference entry points; write new outputs without overwriting reference results."""

import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import analyze_ratings, cosine_similarity
from .design import scan_audio, text_prompt
from .models import Encoder


def run_experiment1(model, data_root, output_dir, batch_size=16):
    """Compare whole-recording audio/text similarities with human timbre ratings."""
    # 1. Read human ratings and match each instrument to its recording.
    root = Path(data_root)
    ratings = []
    descriptors = None
    audio_paths = []
    for split in ("Chinese", "Western"):
        frame = pd.read_csv(root / f"{split}.csv")
        current = frame.columns[2:].tolist()
        if descriptors is not None and descriptors != current:
            raise ValueError("Chinese and Western descriptor columns differ.")
        descriptors = current
        if frame.instrument_id.duplicated().any() or frame.instrument_name.duplicated().any():
            raise ValueError(f"Duplicate instruments in {split}.")
        for instrument_id in frame.instrument_id:
            path = root / "audio" / split / f"{int(instrument_id)}.wav"
            if not path.is_file():
                raise FileNotFoundError(path)
            audio_paths.append(path)
        ratings.append(frame.assign(split=split))
    ratings = pd.concat(ratings, ignore_index=True)
    output = prepare_output(output_dir)

    # 2. Encode clips and descriptor words in the same row/column order.
    encoder = Encoder(model)
    text_embeddings = encoder.encode_text(descriptors)
    audio_embeddings = encoder.encode_audio(audio_paths, batch_size)

    # 3. Correlate each descriptor column and each instrument row with human ratings.
    similarities = cosine_similarity(audio_embeddings, text_embeddings)
    descriptors_df, instruments_df = analyze_ratings(ratings, similarities, descriptors)

    # 4. Save scores, correlations, and the installed package versions.
    descriptors_df.to_csv(output / "descriptors.csv", index=False)
    instruments_df.to_csv(output / "instruments.csv", index=False)
    pd.DataFrame(similarities, columns=descriptors, index=ratings.instrument_name).to_csv(
        output / "similarities.csv", index_label="instrument"
    )
    save_environment(
        output,
        model,
        1,
        {"descriptors": descriptors, "muq_sample_rate": 24000 if model == "muq-mulan" else None},
    )
    return descriptors_df, instruments_df


def run_experiment2(model, data_root, output_dir, design, batch_size=16):
    """Measure how EQ/reverb changes cosine similarity to a target descriptor."""
    # 1. Read and check the source × effect × descriptor × strength inventory.
    originals, frame = scan_audio(data_root, design)
    output = prepare_output(output_dir)

    # 2. Encode originals, processed clips, and descriptor prompts.
    encoder = Encoder(model)
    texts = sorted({text_prompt(d) for ds in design["descriptors"].values() for d in ds})
    text_embeddings = encoder.encode_text(texts)
    original_embeddings = encoder.encode_audio(list(originals.values()), batch_size)
    manipulated_embeddings = encoder.encode_audio(frame.path.tolist(), batch_size)

    # 3. Compare each processed clip with its own source baseline and target word.
    original_sim = cosine_similarity(original_embeddings, text_embeddings)
    manipulated_sim = cosine_similarity(manipulated_embeddings, text_embeddings)
    source_index = {source: i for i, source in enumerate(originals)}
    text_index = {text: i for i, text in enumerate(texts)}
    original_scores = []
    manipulated_scores = []
    for audio_index, row in enumerate(frame.itertuples()):
        source = source_index[row.source_type]
        target = text_index[row.target_text]
        original_scores.append(original_sim[source, target])
        manipulated_scores.append(manipulated_sim[audio_index, target])
    frame["orig_target_sim"] = original_scores
    frame["manip_target_sim"] = manipulated_scores
    frame["delta_target_sim"] = frame.manip_target_sim - frame.orig_target_sim

    # 4. Save the per-condition results and labeled embeddings.
    results = frame.drop(columns="path")
    results.to_csv(output / f"{model}.csv", index=False)
    np.save(output / "text_embeddings.npy", text_embeddings)
    np.save(output / "original_audio_embeddings.npy", original_embeddings)
    np.save(output / "manipulated_audio_embeddings.npy", manipulated_embeddings)
    pd.DataFrame({"text": texts}).to_csv(output / "text_labels.csv", index=False)
    pd.DataFrame({"source_type": list(originals)}).to_csv(
        output / "original_sources.csv", index=False
    )
    save_environment(output, model, 2, {"design": design})
    return results


# File-writing helpers used by both experiments.


def prepare_output(path):
    output = Path(path)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Use a new or empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    return output


def save_environment(output, model, experiment, extra):
    packages = [
        "numpy",
        "pandas",
        "scipy",
        "torch",
        "librosa",
        "laion-clap",
        "msclap",
        "muq",
        "openflam",
    ]
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    (output / "run.json").write_text(
        json.dumps(
            dict(
                model=model,
                experiment=experiment,
                package_versions=versions,
                **extra,
            ),
            indent=2,
        )
        + "\n"
    )

"""Shared statistics, retaining the original experiment definitions."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from .design import MODEL_LABELS, MODELS, text_prompt, validate_conditions


def correlations(x, y):
    """Return Pearson r and Spearman rho; a constant vector has no correlation."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError("Correlation inputs must be finite.")
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return np.nan, np.nan
    return float(pearsonr(x, y).statistic), float(spearmanr(x, y).statistic)


def cosine_similarity(audio, text):
    """Return a (number of clips, number of descriptors) cosine-similarity matrix."""
    audio, text = np.asarray(audio), np.asarray(text)
    for array in (audio, text):
        if array.ndim != 2 or not np.isfinite(array).all():
            raise ValueError("Embeddings must be finite 2D arrays.")
        if np.any(np.linalg.norm(array, axis=1) == 0):
            raise ValueError("Zero embedding cannot define cosine similarity.")
    audio = audio / np.linalg.norm(audio, axis=1, keepdims=True)
    text = text / np.linalg.norm(text, axis=1, keepdims=True)
    return audio @ text.T


def analyze_experiment2(input_dir, output_dir, design):
    """Summarize saved model scores; this function does not load models or audio."""
    # 1. Load each model's CSV and verify its conditions and baseline differences.
    frames = []
    for model in MODELS:
        frame = pd.read_csv(Path(input_dir) / f"{model}.csv")
        validate_conditions(frame, design)
        required = ["orig_target_sim", "manip_target_sim", "delta_target_sim"]
        if not np.isfinite(frame[required].to_numpy(dtype=float)).all():
            raise ValueError(f"Nonfinite similarity in {model}.")
        if not np.allclose(
            frame.manip_target_sim - frame.orig_target_sim,
            frame.delta_target_sim,
            atol=1e-7,
            rtol=1e-5,
        ):
            raise ValueError(f"Inconsistent baseline delta in {model}.")
        if not frame.target_text.equals(frame.descriptor.map(text_prompt)):
            raise ValueError(f"Target text does not match descriptor in {model}.")
        # The original audio baseline must not change with manipulation strength.
        baseline_span = frame.groupby(
            ["effect_type", "source_type", "descriptor"]
        ).orig_target_sim.agg(lambda s: s.max() - s.min())
        if (baseline_span > 1e-7).any():
            raise ValueError(f"Baseline changes across scales in {model}.")
        frames.append(frame.assign(model=MODEL_LABELS[model]))
    combined = pd.concat(frames, ignore_index=True)
    # 2. One trajectory = one model, effect, source, and descriptor at five strengths.
    trajectory_columns = ["model", "effect_type", "source_type", "descriptor"]
    rows = []
    for (model, effect, source, descriptor), group in combined.groupby(
        trajectory_columns, sort=True
    ):
        group = group.sort_values("scale")
        x, y = group.scale.to_numpy(), group.delta_target_sim.to_numpy()
        pearson, spearman = correlations(x, y)
        slope = float(np.polyfit(x, y, 1)[0])
        rows.append(
            {
                "model": model,
                "effect_type": effect,
                "source_type": source,
                "descriptor": descriptor,
                "slope": slope,
                "final_delta": y[-1],
                "pearson_r": pearson,
                "spearman_rho": spearman,
                "positive_slope": slope > 0,
                "positive_final_delta": y[-1] > 0,
            }
        )
    trends = pd.DataFrame(rows)
    # 3. A descriptor/effect is consistent only if every source has a positive slope.
    consistency = trends.groupby(["model", "effect_type", "descriptor"]).positive_slope.all()
    summary = trends.groupby("model").agg(
        pos_slope_rate=("positive_slope", "mean"),
        pos_final_delta_rate=("positive_final_delta", "mean"),
        mean_pearson_r=("pearson_r", "mean"),
        mean_spearman_rho=("spearman_rho", "mean"),
    )
    summary["all_source_consistency"] = consistency.groupby("model").mean()
    effects = trends.groupby(["effect_type", "model"]).agg(
        positive_slope_rate=("positive_slope", "mean"),
        positive_final_delta_rate=("positive_final_delta", "mean"),
        mean_slope=("slope", "mean"),
        mean_final_delta=("final_delta", "mean"),
        mean_pearson_r=("pearson_r", "mean"),
        mean_spearman_rho=("spearman_rho", "mean"),
    )
    effects["all_source_consistency"] = consistency.groupby(["effect_type", "model"]).mean()
    # 4. Write trajectory details, model summaries (Table 1), and effect summaries (Table 2).
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    trends.to_csv(output / "group_trends.csv", index=False)
    summary.to_csv(output / "summary.csv")
    effects.to_csv(output / "effects.csv")
    return summary


def analyze_ratings(ratings, similarities, descriptors):
    """Correlate already aligned instrument rows along both matrix axes."""
    values = ratings[descriptors].to_numpy(dtype=float)
    similarities = np.asarray(similarities)
    if values.shape != similarities.shape:
        raise ValueError("Ratings and similarity matrix shapes differ.")
    descriptor_rows = []
    for i, descriptor in enumerate(descriptors):
        pearson, spearman = correlations(values[:, i], similarities[:, i])
        descriptor_rows.append({"descriptor": descriptor, "pearson": pearson, "spearman": spearman})
    instrument_rows = []
    for i, (_, row) in enumerate(ratings.iterrows()):
        pearson, spearman = correlations(values[i], similarities[i])
        instrument_rows.append(
            {
                "instrument": row.instrument_name,
                "split": row["split"],
                "pearson": pearson,
                "spearman": spearman,
            }
        )
    return pd.DataFrame(descriptor_rows), pd.DataFrame(instrument_rows)

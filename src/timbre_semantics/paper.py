"""Generate paper tables and figures from saved scores; no encoder or audio is loaded."""

from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import analyze_experiment2
from .design import MODEL_LABELS, MODELS, load_design

EXP1_LABELS = {
    "LAION_CLAP": "LAION-CLAP",
    "MSCLAP": "MSCLAP",
    "MuQ_MuLan": "MuQ-MuLan",
    "OpenFLAM": "OpenFLAM",
}


def reproduce_paper(reference_root, output_dir, config, figures=False):
    reference, output = Path(reference_root), Path(output_dir)
    overall = analyze_experiment2(
        reference / "experiment2", output / "experiment2", load_design(config)
    )
    effects = pd.read_csv(output / "experiment2/effects.csv").set_index(["effect_type", "model"])
    overall_columns = [
        "pos_slope_rate",
        "pos_final_delta_rate",
        "all_source_consistency",
        "mean_pearson_r",
        "mean_spearman_rho",
    ]
    effect_columns = [
        "positive_slope_rate",
        "positive_final_delta_rate",
        "all_source_consistency",
        "mean_pearson_r",
        "mean_spearman_rho",
    ]
    descriptors = pd.read_csv(reference / "experiment1/descriptors.csv")
    descriptors["model"] = descriptors.model.map(EXP1_LABELS)
    if descriptors.model.isna().any() or descriptors.duplicated(["model", "descriptor"]).any():
        raise ValueError("Unknown models or duplicate descriptor rows in experiment 1 reference.")
    if not np.isfinite(descriptors.pearson).all():
        raise ValueError("Nonfinite experiment 1 descriptor reference.")
    descriptor_summary = descriptors.groupby("model").pearson.agg(
        n="size", positive=lambda x: (x > 0).sum(), mean="mean"
    )
    instruments = []
    for key in (f"{model}_{split}" for model in MODELS for split in ("chinese", "western")):
        frame = pd.read_csv(reference / f"experiment1/{key}.csv")
        if frame.instrument.duplicated().any() or not np.isfinite(frame.pearson).all():
            raise ValueError(f"Invalid instrument profile reference: {key}")
        model, split = key.rsplit("_", 1)
        instruments.append(frame.assign(model=MODEL_LABELS[model], split=split))
    instruments = pd.concat(instruments, ignore_index=True)
    instrument_summary = instruments.groupby(["model", "split"]).pearson.agg(
        n="size", positive=lambda x: (x > 0).sum(), mean="mean", std="std"
    )
    instrument_summary["ci95_half_width"] = (
        1.96 * instrument_summary["std"] / np.sqrt(instrument_summary.n)
    )

    # Preserve original units internally; display Table 1/2 rates as percentages.
    table1 = overall[overall_columns].copy()
    table2 = effects[effect_columns].copy()
    for table in [table1, table2]:
        for column in table.columns[:3]:
            table[column] = table[column].map(lambda x: f"{100 * x:.1f}%")
        for column in table.columns[3:]:
            table[column] = table[column].map(lambda x: f"{x:.3f}")
    table1.to_csv(output / "table1.csv")
    table2.to_csv(output / "table2.csv")
    descriptor_summary.to_csv(output / "experiment1_descriptor_summary.csv")
    instrument_summary.to_csv(output / "experiment1_instrument_summary.csv")
    scores = pd.concat(
        [
            pd.read_csv(reference / f"experiment2/{m}.csv").assign(model=MODEL_LABELS[m])
            for m in MODELS
        ],
        ignore_index=True,
    )
    figure4 = (
        scores[scores.descriptor.isin(["haunting", "deep"])]
        .groupby(["descriptor", "effect_type", "model", "scale"])
        .delta_target_sim.mean()
        .reset_index()
    )
    figure4.to_csv(output / "figure4_trajectories.csv", index=False)
    # Ordering is taken from the supplied find_best_encode notebook. The paper
    # describes the aggregate criteria without specifying this exact tie-break order.
    trends = pd.read_csv(output / "experiment2/group_trends.csv")
    trends["positive_pearson"] = trends.pearson_r > 0
    trends["positive_spearman"] = trends.spearman_rho > 0
    ranking = trends.groupby("descriptor").agg(
        mean_slope=("slope", "mean"),
        mean_final_delta=("final_delta", "mean"),
        mean_pearson_r=("pearson_r", "mean"),
        mean_spearman_rho=("spearman_rho", "mean"),
        positive_slope_rate=("positive_slope", "mean"),
        positive_final_rate=("positive_final_delta", "mean"),
        positive_pearson_rate=("positive_pearson", "mean"),
        positive_spearman_rate=("positive_spearman", "mean"),
    )
    consistency = (
        trends.groupby(["descriptor", "model", "effect_type"])[
            ["positive_slope", "positive_final_delta"]
        ]
        .all()
        .groupby("descriptor")
        .mean()
    )
    ranking["source_consistency_slope"] = consistency.positive_slope
    ranking["source_consistency_final"] = consistency.positive_final_delta
    ranking = ranking.sort_values(list(ranking.columns), ascending=False)
    ranking.to_csv(output / "descriptor_ranking.csv")

    if figures:
        render_figures(descriptors, instrument_summary, figure4, output)
    return output


def render_figures(descriptors, instruments, trajectories, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = list(MODEL_LABELS.values())
    display = [x.replace("MSCLAP", "MS-CLAP") for x in labels]
    pivot = descriptors.pivot(index="descriptor", columns="model", values="pearson")[labels]
    fig, ax = plt.subplots(figsize=(7, 8), layout="constrained")
    limit = float(np.abs(pivot.to_numpy()).max())
    im = ax.imshow(pivot, cmap="RdBu", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(4), display)
    ax.set_yticks(range(len(pivot)), pivot.index)
    for i in range(len(pivot)):
        for j in range(4):
            value = pivot.iloc[i, j]
            ax.text(
                j,
                i,
                f"{value:.2f}",
                ha="center",
                va="center",
                color="white" if abs(value) > limit * 0.7 else "black",
                fontsize=9,
            )
    ax.set_title("Descriptor-level agreement with human ratings")
    fig.colorbar(im, ax=ax, label="Pearson r")
    fig.savefig(output / "figure2.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    for split, offset in [("chinese", -0.10), ("western", 0.10)]:
        sub = instruments.xs(split, level="split").loc[labels]
        ax.errorbar(
            np.arange(4) + offset,
            sub["mean"],
            yerr=sub.ci95_half_width,
            fmt="o",
            capsize=4,
            label=split.title(),
        )
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xticks(range(4), display)
    ax.set_ylabel("Mean instrument-profile Pearson r")
    ax.set_title("Instrument profiles: mean ± 1.96 × SEM")
    ax.legend()
    fig.savefig(output / "figure3.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(7, 7), layout="constrained")
    for ax, desc in zip(axes, ["haunting", "deep"]):
        for model, label in zip(labels, display):
            sub = trajectories[(trajectories.descriptor == desc) & (trajectories.model == model)]
            ax.plot(sub.scale, sub.delta_target_sim, marker="o", label=label)
        ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.set(title=desc, xlabel="Manipulation strength", ylabel="Mean target-similarity Δ")
        ax.legend(fontsize=8)
    fig.savefig(output / "figure4.png", dpi=180)
    plt.close(fig)

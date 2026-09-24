# Methods and validation

## Experiment 1: human-rating agreement

The experiment compares 37 Chinese and 24 Western instrument recordings across
16 timbre descriptors. The text inputs are the descriptor column names from the
rating tables, without a sentence template. Each complete recording is encoded
once; no note segmentation or averaging is used.

Audio/text cosine similarities form a 61 × 16 matrix aligned with the human
ratings. Correlations are computed down each descriptor column across instruments
and across each instrument row over descriptors. Pearson is the paper statistic;
Spearman is supplemental. Constant vectors yield `NaN`.

## Experiment 2: effect response

Three sources (guitar, piano, and an ensemble identified as `mixture`) × two
effects × 20 descriptors × five strengths yield 600 processed clips, plus three
original baselines. Words and strengths are in `configs/experiment2.json`.
Text inputs are `a <descriptor> sound`, except `an echo sound`.

```text
delta_target_sim = cosine(processed_audio, target_text)
                 - cosine(original_audio, target_text)
```

For each of 120 source/effect/descriptor groups, fit a linear slope and compute
Pearson/Spearman correlations over the five strengths. Final Δ is the value at
strength 1.0. Overall positive rates use all 120 groups. All-source consistency
uses 40 effect/descriptor pairs and requires positive slopes in all three sources.
Per-effect summaries use 60 groups and 20 pairs.

These are descriptive statistics, not significance tests. Positive slope and
positive final Δ are distinct measures. Cross-model cosine magnitudes are not
calibrated perceptual distances.

## Model preprocessing

| Model | Implementation |
|---|---|
| LAION-CLAP | Fusion disabled; default checkpoint; library audio file loader |
| MSCLAP | Version 2023; library audio/text embedding methods |
| MuQ-MuLan | `OpenMuQ/MuQ-MuLan-large`; whole recordings, mono 24 kHz in both experiments |
| OpenFLAM | `v1-base`; mono 48 kHz; truncate or zero-pad to 10 seconds |

The shared runner computes explicit cosine similarity. Historical MSCLAP scores
used the library similarity helper; raw-score scales may differ. The original
MuQ notebook used `calc_similarity`; fresh inference equivalence with this runner
has not been established. Runs record installed package versions; original
checkpoint hashes and complete environment locks are not available.

## Paper outputs

| Paper output | Implementation |
|---|---|
| Figure 2 | Descriptor correlation summaries in `paper.py` |
| Figure 3 | Instrument profile summaries in `paper.py` |
| Tables 1–2 | Effect-response statistics in `analysis.py`, formatted in `paper.py` |
| Figure 4 | Source-mean trajectories for haunting and deep in `paper.py` |

Figure 3 uses mean ± 1.96 × SEM, following the original plotting code; the caption
does not specify the estimator. Figures preserve the data, not identical page
layout. Figure 4 follows the paper's choice of haunting/deep. The original
mean-slope-first ranking yields the same six leading words in a different order
(deep is sixth); these two words are not claimed to be the top two by mean slope.

## Validation scope

`timbre paper --figures` generates tables and figures from saved scores without
model inference. It does not automatically compare outputs against transcribed
paper values. The reference statistics were previously checked against Figures
2–3 and Tables 1–2 within published rounding.

Fresh model inference on the final paper audio and the live Audealize generation
workflow have not been validated for this release. Descriptor-frequency selection
has not been independently rerun. Saved-score agreement does not establish
end-to-end reproduction. Generation instructions and parameter snapshot limitations
are in [the running guide](running.md#generate-audio-with-audealize).

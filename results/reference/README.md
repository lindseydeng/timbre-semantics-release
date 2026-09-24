# Reference results

These are saved outputs from the study, not new model inference. Keep them
unchanged and write new experiment outputs to a separate directory.

| Files | Contents |
|---|---|
| `experiment1/descriptors.csv` | Descriptor-level correlations for four models |
| `experiment1/*_chinese.csv`, `*_western.csv` | Instrument-level correlations by model and instrument group |
| `experiment2/{laion-clap,msclap,muq-mulan,openflam}.csv` | 600 per-condition similarity results per model |
| `experiment2/summary.csv`, `effects.csv` | Historical aggregate statistics |

`timbre paper --figures` summarizes experiment 1 correlations and recomputes
experiment 2 statistics from these tables. Results match Figures 2–3 and
Tables 1–2 within published rounding. See [methods and validation](../../docs/methods.md)
for the distinction between saved-score analysis and fresh model inference.

# Running experiments

Run commands from the repository root after installing the project. The actual
paper audio is not bundled. Follow [the data layout](../data/README.md) and use
an explicit `--data-root`.

## Choose a model

First create and activate a virtual environment, then install the base requirements
from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
The base install supports saved-score analysis and paper figures, without PyTorch
or model weights. For inference, install one model extra, preferably in its own
virtual environment:

| `--model` | Install command | Audio handling |
|---|---|---|
| `laion-clap` | `python -m pip install -e '.[laion]'` | LAION-CLAP file loader, fusion disabled |
| `msclap` | `python -m pip install -e '.[msclap]'` | MS-CLAP 2023 file loader |
| `muq-mulan` | `python -m pip install -e '.[muq]'` | Full recording, mono, 24 kHz |
| `openflam` | `python -m pip install -e '.[openflam]'` | Mono, 48 kHz, truncate/pad to 10 seconds |

Constructing an encoder downloads its model weights when needed. These model
extras are not tested environment locks. Package versions are saved with each run.

Optional tools:

- Notebooks: `python -m pip install -e '.[notebooks]'`

You do not need these optional tools to run `timbre paper --figures`.

## Experiment 1: agreement with human ratings

```bash
timbre experiment1 --model muq-mulan --data-root data/experiment1 --output outputs/experiment1/muq-mulan
```

The runner reads both rating tables and their whole instrument recordings,
computes audio/text cosine similarity, and correlates each descriptor column and
each instrument row with the human-rating matrix. It writes:

- `similarities.csv`: one row per instrument, one column per descriptor.
- `descriptors.csv`: correlations across instruments for each descriptor.
- `instruments.csv`: correlations across descriptors for each instrument.
- `run.json`: model name, package versions and descriptor order.

Pearson is the paper's reported statistic. Spearman is saved as supplemental output.

## Experiment 2: changes caused by effects

```bash
timbre validate --data-root data/experiment2
timbre experiment2 --model laion-clap --data-root data/experiment2 --output outputs/experiment2/laion-clap
```

The runner reads the sources and manipulated clips, then calculates:

```text
delta_target_sim = cosine(manipulated clip, target text)
                 - cosine(original source, target text)
```

It saves a `<model>.csv` with one row per condition, embeddings with row labels,
and `run.json`. Use `--batch-size 8` if you need a smaller encoding batch. Each
inference run requires a new or empty output directory.

To summarize new results, collect all four `<model>.csv` files in one directory:

```bash
timbre analyze --input outputs/new_scores --output outputs/new_summary
```

This produces `group_trends.csv`, `summary.csv` (model-level statistics), and
`effects.csv` (EQ/reverb statistics). For saved reference results, simply run
`timbre paper --figures`; that command generates the paper tables and figures from saved scores.

## Generate audio with Audealize

The paper's experiment 2 audio was generated with
[Audealize](https://audealize.appspot.com/). For a new experiment, prepare your
own source WAVs. With the default configuration, name them `guitar.wav`,
`piano.wav`, and `mixture.wav` and place them in `data/experiment2/test_audio/`.
Keep these originals as similarity baselines.

Apply each of the 20 EQ and 20 reverb descriptors separately at strengths
0.2, 0.4, 0.6, 0.8, and 1.0. You can import audio, select the effect/descriptor,
adjust its strength, and export manually on the website, or use the batch wrapper
below (Node.js 18+). The default design produces 600 processed clips.


```bash
cd tools/audealize
npm ci
npx playwright install chromium
node audealize_batch.js --input ../../data/experiment2/test_audio \
  --output ../../data/experiment2/manipulated_audio --effect eq
```

Repeat with `--effect reverb`. Both use `configs/experiment2.json`. The tool relies
on the external Audealize site, whose UI/renderer may change. It has not been
validated for this release. New exports are trimmed to 11 seconds by default; use
`--trim-seconds` to choose a limit. Existing WAV files are not overwritten.
Newly generated stimuli are not certified as identical to the paper recordings.
The supplied [parameter snapshots](../tools/audealize/data/README.md) are reference
data; this wrapper does not read them into the renderer. For the exact paper
audio, contact the author through a repository issue; availability depends on
source recording permissions. Your own recordings and new renders constitute a
new experiment and are not expected to reproduce the saved paper scores exactly.

After generation, return to the repository root and run `timbre validate` and
`timbre experiment2` as shown above. If changing source identifiers or descriptors,
update the experiment configuration and pass `--config` to generation, validation,
inference, and analysis commands. Follow [the data layout](../data/README.md).


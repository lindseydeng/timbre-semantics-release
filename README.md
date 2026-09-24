# Timbre Semantics — ISMIR 2026

Research code for **Do Joint Language-Audio Embeddings Encode Perceptual Timbre
Semantics?** — Qixin Deng, Bryan Pardo, and Thrasyvoulos N. Pappas.

We compare LAION-CLAP, MS-CLAP, MuQ-MuLan, and OpenFLAM in two experiments:

- **Experiment 1:** compare model similarities with human ratings for 61 instruments
  and 16 timbre descriptors.
- **Experiment 2:** measure how target-descriptor similarity changes after EQ/reverb:
  3 sources × 20 descriptors per effect × 2 effects × 5 strengths = 600 clips.

## Start here: reproduce the paper tables

Python 3.10+. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
timbre paper --figures
```

Results appear in `outputs/paper/`: `table1.csv`, `table2.csv`, `figure2.png`,
`figure3.png`, and `figure4.png`.

This uses **saved model scores**. It needs no audio or model download and does
not rerun model inference. Fresh inference with the final experiment audio has
not yet been validated; that audio is not included.

`requirements.txt` installs the analysis and plotting dependencies plus the `timbre`
command. Install a model extra only when you need inference (below). Package versions
are defined in `pyproject.toml`; there is no second dependency list to keep in sync.

## Read the code

Start with these three files, in order:

| File | What to read |
|---|---|
| [experiments.py](src/timbre_semantics/experiments.py) | Two functions: load data → encode → compare → save |
| [models.py](src/timbre_semantics/models.py) | `Encoder.encode_audio()` and `Encoder.encode_text()` for four models |
| [analysis.py](src/timbre_semantics/analysis.py) | Cosine similarity, human-rating correlations, and effect trends |

The experiment functions contain the complete main workflows. Each uses four
numbered steps. `design.py` checks input conditions, `paper.py` makes the paper
report, and `cli.py` connects terminal commands to these functions.

Prefer notebooks? Start with [experiment 2](notebooks/02_effect_response.ipynb)
for a worked example using saved scores, or [experiment 1](notebooks/01_human_agreement.ipynb)
for the human-rating workflow. Install `'.[notebooks]'` to use Jupyter.

## Run an experiment on audio

Prepare the files described in [data/README.md](data/README.md). For example:

```bash
python -m pip install -e '.[laion]'
timbre experiment1 --model laion-clap --data-root data/experiment1 --output outputs/exp1
timbre experiment2 --model laion-clap --data-root data/experiment2 --output outputs/exp2
```

Use a new output directory for each run. Model names and installation options,
output files, and audio generation are explained in [running experiments](docs/running.md).
MuQ uses complete recordings resampled to 24 kHz in both experiments.

## Experiment 2 audio and settings

The paper's experiment 2 audio was generated using
[Audealize](https://audealize.appspot.com/). To run your own experiment, generate
processed audio from your own source recordings using the same descriptor lists
and five strength levels. See [the audio guide](docs/running.md#generate-audio-with-audealize).

We provide [the full and selected Audealize parameter snapshots](tools/audealize/data/README.md).
The original experiment audio is not bundled. For the exact audio used in the
paper, please contact the author by opening a repository issue; availability is
subject to the source recordings' redistribution terms. New source recordings or
new renders are not expected to reproduce the saved paper scores exactly.

## Further information

- [Methods and validation](docs/methods.md)
- [Reference result provenance](results/reference/README.md)
- [Audio and generation](docs/running.md#generate-audio-with-audealize) · [Third-party notices](docs/third-party.md)

Code: [MIT](LICENSE). Audio, datasets, and model weights have separate terms.

## Citation

If you use this code or the reference results in your research, please cite:

```bibtex
@inproceedings{deng2026timbre,
  author    = {Deng, Qixin and Pardo, Bryan and Pappas, Thrasyvoulos N.},
  title     = {Do Joint Language-Audio Embeddings Encode Perceptual Timbre Semantics?},
  booktitle = {Proceedings of the 27th International Society for Music Information Retrieval Conference},
  year      = {2026}
}
```

Citation metadata is also available in [CITATION.cff](CITATION.cff).

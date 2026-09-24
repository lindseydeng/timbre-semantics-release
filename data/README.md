# Local research data

Audio, human rating files, and model checkpoints are not
distributed with the source release. Acquire them from their original providers
under their respective terms. For experiment 2, generate audio from your own
recordings with Audealize; see [the audio guide](../docs/running.md#generate-audio-with-audealize).
For the exact paper audio, contact the author through a repository issue,
subject to the source recordings' redistribution terms.

## Experiment 1

Obtain the instrument timbre dataset from
[ccmusic-database/instrument_timbre](https://huggingface.co/datasets/ccmusic-database/instrument_timbre).
Arrange its files as:

```text
data/experiment1/
  Chinese.csv
  Western.csv
  audio/Chinese/<instrument_id>.wav
  audio/Western/<instrument_id>.wav
```

The first two CSV columns must be `instrument_id,instrument_name`, followed by
the same ordered 16 numeric descriptors in each split. IDs must match the filenames;
do not renumber them. The actual historical CSV labels, rather than translations
in dataset prose, define the model prompts.

The final MuQ experiment 1 notebook encodes these complete WAV recordings at
24 kHz. The dataset source rate is 44.1 kHz; model input resampling is separate.
No note segmentation or averaging is part of this final pipeline.

## Experiment 2

```text
data/experiment2/
  test_audio/{guitar,piano,mixture}.wav
  manipulated_audio/EQ/guitar_eq/guitar_EQ_bright_0.2.wav
  manipulated_audio/EQ/piano_eq/...
  manipulated_audio/EQ/mixture_eq/...
  manipulated_audio/RVB/guitar_rvb/guitar_Reverb_echo_0.2.wav
  manipulated_audio/RVB/piano_rvb/...
  manipulated_audio/RVB/mixture_rvb/...
```

Each effect/source directory must contain every descriptor × scale combination
in `configs/experiment2.json` (100 files with the default design). EQ and
reverb/rvb filename effect tokens are case-insensitive. Run `timbre validate --data-root data/experiment2`
before inference. Substituting your own source audio defines a new run; it will
not reproduce the historical scores.

The historical piano reverb files use the stem `test_piano`. This is explicitly
accepted by `source_stems` in the shared configuration; it is still the piano
source, not an additional condition.

Original guitar, piano, and mixture recording provenance/redistribution permission
has not been established in the supplied code. Obtain that information before
publishing recordings or offering exact audio-level reproduction.

The paper design contains 600 manipulated clips and 3 originals. The actual
paper waveforms are not included; filename validation alone does not establish
that files are the original paper stimuli.

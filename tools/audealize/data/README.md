# Audealize parameter snapshots

These four JSON files were supplied by the study author from the Audealize
experiment materials and are retained without modification.
Source platform: [Audealize](https://audealize.appspot.com/), developed by the
Interactive Audio Lab at Northwestern University.

| File | Contents |
|---|---|
| `eqpoints.json` | Full supplied EQ snapshot: 394 records, 40 settings per record |
| `reverbpoints.json` | Full supplied reverb snapshot: 369 records, 5 settings per record |
| `top20_eqpoints.json` | 20 selected EQ records |
| `top20_reverbpoints.json` | 20 selected reverb records |

Each selected record is an exact member of its corresponding full snapshot.
The selected word sets match `configs/experiment2.json`; their ordering differs.
The files contain `word`, `lang`, `settings`, `agreement`, `num`, `x`, and `y`.
Upstream metadata and parameter order are preserved; these files do not include
waveforms or a standalone DSP renderer. The original snapshot date and an explicit
upstream data license have not been established. These third-party snapshots are
not covered by the repository's MIT source-code license.

## How these files relate to audio generation

The snapshots document descriptor-associated settings. The current
`audealize_batch.js` reads descriptor names and strengths from
`configs/experiment2.json` and operates the live Audealize website; it does **not**
load these JSON snapshots into the renderer. The live site's settings may differ
from the saved snapshots. Including these files does not establish identical
rendering or independently verify the original word-selection procedure.

For a new experiment, use your own source recordings and follow
[the audio guide](../../../docs/running.md#generate-audio-with-audealize). For the exact audio used in
the paper, contact the author through a repository issue.

# Third-party material

The MIT license applies to this project's source code. It does not grant rights
to external data, recordings, model weights, dependencies, or hosted services.

| Material | Source | Release handling |
|---|---|---|
| Instrument timbre dataset | [ccmusic-database](https://huggingface.co/datasets/ccmusic-database/instrument_timbre); dataset README declares `CC-BY-NC-ND` without a version | No source audio or human-rating tables included; obtain upstream terms |
| Experiment 2 source recordings | Original filenames guitar, piano, mixture; provenance absent | Recordings and derivatives excluded pending provenance |
| Audealize | [Hosted service](https://audealize.appspot.com), Interactive Audio Lab, Northwestern University | Project automation wrapper and four author-supplied parameter snapshots included; see [snapshot provenance](../tools/audealize/data/README.md). No explicit upstream data license established; snapshots are not relicensed under MIT. |
| Model weights/libraries | LAION-CLAP, MSCLAP, MuQ-MuLan, OpenFLAM | Installed/downloaded separately under upstream terms |

Reference tables are historical project analysis outputs, not a redistribution
of the source audio, human ratings, or model weights. Retain their provenance.
Before distributing any additional data, establish its source and applicable terms.

Dataset reference:
Jiang W, Liu J, Zhang X, Wang S, Jiang Y. *Analysis and Modeling of Timbre Perception
Features in Musical Sounds*. Applied Sciences, 2020, 10(3):789.
This citation describes the instrument dataset.

The paper carries a CC BY 4.0 notice for the article.
That notice is not evidence of licensing for the three experiment 2 recordings.
No audio license has been assigned here; source provenance is still pending.

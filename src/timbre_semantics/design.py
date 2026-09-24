"""Experiment design and strict stimulus inventory validation."""

import json
import re
from itertools import product
from pathlib import Path

import pandas as pd

MODELS = ("laion-clap", "msclap", "muq-mulan", "openflam")
MODEL_LABELS = dict(zip(MODELS, ("LAION-CLAP", "MSCLAP", "MuQ-MuLan", "OpenFLAM")))
KEYS = ["effect_type", "source_type", "descriptor", "scale"]
FILE_PATTERN = re.compile(
    r"^(?P<stem>.+?)_(?P<effect>eq|rvb|reverb)_(?P<desc>[a-z0-9-]+)_"
    r"(?P<scale>[0-9.]+)\.wav$",
    re.IGNORECASE,
)


def load_design(path):
    design = json.loads(Path(path).read_text())
    if set(design["descriptors"]) != {"eq", "reverb"}:
        raise ValueError("Design must define eq and reverb descriptors.")
    for values in [design["sources"], design["scales"], *design["descriptors"].values()]:
        if not values or len(set(values)) != len(values):
            raise ValueError("Design lists must be nonempty and unique.")
    if any(not isinstance(x, (int, float)) or not 0 < x <= 1 for x in design["scales"]):
        raise ValueError("Scales must be finite numbers in (0, 1].")
    return design


def text_prompt(descriptor):
    # Preserve the historical prompts, including 'an echo sound'.
    return f"{'an' if descriptor == 'echo' else 'a'} {descriptor} sound"


def validate_conditions(frame, design):
    missing_columns = set(KEYS) - set(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")
    if frame.duplicated(KEYS).any():
        raise ValueError("Duplicate experiment conditions.")
    expected = {
        (effect, source, desc, float(scale))
        for effect, descriptors in design["descriptors"].items()
        for source, desc, scale in product(design["sources"], descriptors, design["scales"])
    }
    actual = set(frame[KEYS].itertuples(index=False, name=None))
    if actual != expected:
        raise ValueError(
            f"Incomplete or unexpected design: {len(expected - actual)} missing, "
            f"{len(actual - expected)} unexpected conditions."
        )


def scan_audio(data_root, design):
    root = Path(data_root)
    originals = {source: root / "test_audio" / f"{source}.wav" for source in design["sources"]}
    for path in originals.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    rows = []
    for effect in design["descriptors"]:
        folder, suffix = ("EQ", "eq") if effect == "eq" else ("RVB", "rvb")
        for source in design["sources"]:
            directory = root / "manipulated_audio" / folder / f"{source}_{suffix}"
            if not directory.is_dir():
                raise FileNotFoundError(directory)
            for path in sorted(directory.glob("*.wav")):
                match = FILE_PATTERN.fullmatch(path.name)
                if not match:
                    raise ValueError(f"Unrecognized audio filename: {path.name}")
                parsed = match.groupdict()
                parsed_effect = "eq" if parsed["effect"].lower() == "eq" else "reverb"
                valid_stems = design.get("source_stems", {}).get(source, [source])
                if parsed["stem"] not in valid_stems or parsed_effect != effect:
                    raise ValueError(f"Filename conflicts with source/effect directory: {path}")
                rows.append(
                    {
                        "effect_type": effect,
                        "source_type": source,
                        "descriptor": parsed["desc"],
                        "scale": float(parsed["scale"]),
                        "target_text": text_prompt(parsed["desc"]),
                        "filename": path.name,
                        "path": str(path),
                    }
                )
    frame = pd.DataFrame(rows)
    validate_conditions(frame, design)
    return originals, frame

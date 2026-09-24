"""Small adapters extracted from the research notebooks.

Install each model in its own environment if its dependencies conflict with others.
"""

from pathlib import Path

import numpy as np

from .design import MODELS


def as_numpy(value):
    return value.detach().cpu().numpy() if hasattr(value, "detach") else np.asarray(value)


class Encoder:
    def __init__(self, name):
        if name not in MODELS:
            raise ValueError(f"Unknown model: {name}")
        import torch

        self.torch = torch
        self.name = name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if name == "laion-clap":
            from laion_clap import CLAP_Module

            self.model = CLAP_Module(enable_fusion=False, device=self.device)
            self.model.load_ckpt()
        elif name == "msclap":
            from msclap import CLAP

            self.model = CLAP(version="2023", use_cuda=self.device == "cuda")
        elif name == "muq-mulan":
            from muq import MuQMuLan

            self.model = MuQMuLan.from_pretrained("OpenMuQ/MuQ-MuLan-large")
            self.model = self.model.to(self.device).eval()
        else:
            import openflam

            self.model = (
                openflam.OpenFLAM(
                    model_name="v1-base",
                    default_ckpt_path=str(Path.home() / ".cache/timbre-semantics/openflam"),
                )
                .to(self.device)
                .eval()
            )

    def encode_text(self, texts):
        """Return one embedding per text prompt, in input order: (texts, dimensions)."""
        with self.torch.no_grad():
            if self.name == "laion-clap":
                result = self.model.get_text_embedding(texts, use_tensor=False)
            elif self.name == "msclap":
                result = self.model.get_text_embeddings(texts)
            elif self.name == "muq-mulan":
                result = self.model(texts=texts)
            else:
                result = self.model.get_text_features(texts)
        return as_numpy(result)

    def encode_audio(self, paths, batch_size=16):
        """Return one embedding per audio file, in input order: (files, dimensions)."""
        paths = [str(path) for path in paths]
        if not paths or batch_size < 1:
            raise ValueError("Audio paths must be nonempty and batch size positive.")
        batches = []
        with self.torch.no_grad():
            for start in range(0, len(paths), batch_size):
                batch = paths[start : start + batch_size]
                if self.name == "laion-clap":
                    result = self.model.get_audio_embedding_from_filelist(x=batch, use_tensor=False)
                elif self.name == "msclap":
                    result = self.model.get_audio_embeddings(batch)
                else:
                    import librosa

                    vectors = []
                    for path in batch:
                        # Final experiment-one notebook and official MuQ input rate.
                        sr = 48000 if self.name == "openflam" else 24000
                        wav, _ = librosa.load(path, sr=sr, mono=True)
                        if not len(wav) or not np.isfinite(wav).all():
                            raise ValueError(f"Empty or nonfinite audio: {path}")
                        if self.name == "openflam":
                            wav = wav[: sr * 10]
                            wav = np.pad(wav, (0, sr * 10 - len(wav)))
                        tensor = self.torch.tensor(wav, dtype=self.torch.float32)
                        tensor = tensor.unsqueeze(0).to(self.device)
                        vector = (
                            self.model(wavs=tensor)
                            if self.name == "muq-mulan"
                            else self.model.get_global_audio_features(tensor)
                        )
                        vectors.append(as_numpy(vector)[0])
                    result = np.stack(vectors)
                batches.append(as_numpy(result))
        return np.vstack(batches)

"""Fixed local MiniLM encoding and exact cosine ranking."""

from pathlib import Path

import numpy as np

from . import model_assets
from .lexical import RankedDocument

CONFIG = {
    "batch_size": 16,
    "max_length": 256,
    "truncation": "right, including special tokens",
    "padding": "right, batch longest, PAD id 0",
    "pooling": "attention-mask mean, including attended special tokens",
    "normalize": "L2",
    "dtype": "float32",
    "provider": "CPUExecutionProvider",
    "ort_telemetry": "disabled",
    "execution_mode": "sequential",
    "intra_op_threads": 1,
    "inter_op_threads": 1,
    "score": "unit-vector dot product via numpy.einsum optimize=False",
    "positive_scores_only": False,
    "tie_break": "doc_id ascending",
    "text": "title + newline + text",
    "exclude_same_id": True,
    "k": 10,
}


def mean_pool_normalize(hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    hidden = np.asarray(hidden, dtype=np.float32)
    mask = np.asarray(mask)
    if (
        hidden.ndim != 3
        or mask.shape != hidden.shape[:2]
        or not np.isfinite(hidden).all()
        or not np.isin(mask, [0, 1]).all()
        or np.any(mask.sum(axis=1) == 0)
    ):
        raise ValueError("finite token embeddings and nonempty binary attention masks required")
    weights = mask.astype(np.float32)[..., None]
    pooled = (hidden * weights).sum(axis=1) / weights.sum(axis=1)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 0):
        raise ValueError("cannot normalize zero/nonfinite sentence embedding")
    return pooled / norms


class MiniLMEncoder:
    def __init__(self, root: Path):
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise ValueError(
                "install semantic dependencies: uv sync --frozen --extra semantic"
            ) from exc
        raw = model_assets.load_verified_model(root)
        ort.disable_telemetry_events()
        tokenizer_json = raw["tokenizer.json"].decode("utf-8")
        self.tokenizer = Tokenizer.from_str(tokenizer_json)
        self.tokenizer.enable_truncation(max_length=256, direction="right")
        self.tokenizer.enable_padding(direction="right", pad_id=0, pad_token="[PAD]")
        self.counter = Tokenizer.from_str(tokenizer_json)
        self.counter.no_truncation()
        self.counter.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(
            raw["onnx/model.onnx"], sess_options=options, providers=["CPUExecutionProvider"]
        )
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        if (
            {item.name for item in inputs} != {"input_ids", "attention_mask", "token_type_ids"}
            or any(item.type != "tensor(int64)" or len(item.shape) != 2 for item in inputs)
            or len(outputs) != 1
            or outputs[0].name != "last_hidden_state"
            or outputs[0].type != "tensor(float)"
            or len(outputs[0].shape) != 3
            or outputs[0].shape[-1] != 384
            or self.session.get_providers() != ["CPUExecutionProvider"]
        ):
            raise ValueError("unexpected ONNX signature/provider; token-level output required")
        self.last_stats = {}

    def encode(self, texts: list[str], progress=None) -> np.ndarray:
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("nonempty list of nonblank texts required")
        blocks = []
        self.last_stats = {
            "text_count": len(texts),
            "truncated_texts": 0,
            "max_untruncated_tokens": 0,
        }
        for start in range(0, len(texts), 16):
            batch = texts[start : start + 16]
            lengths = [len(row.ids) for row in self.counter.encode_batch(batch)]
            self.last_stats["truncated_texts"] += sum(length > 256 for length in lengths)
            self.last_stats["max_untruncated_tokens"] = max(
                self.last_stats["max_untruncated_tokens"], max(lengths)
            )
            tokens = self.tokenizer.encode_batch(batch)
            inputs = {
                "input_ids": np.array([row.ids for row in tokens], dtype=np.int64),
                "attention_mask": np.array([row.attention_mask for row in tokens], dtype=np.int64),
                "token_type_ids": np.array([row.type_ids for row in tokens], dtype=np.int64),
            }
            hidden = self.session.run(["last_hidden_state"], inputs)[0]
            if hidden.shape != (*inputs["input_ids"].shape, 384):
                raise ValueError("unexpected runtime token-embedding shape")
            blocks.append(mean_pool_normalize(hidden, inputs["attention_mask"]))
            if progress is not None:
                progress(min(start + 16, len(texts)), len(texts))
        return np.concatenate(blocks)


class DenseIndex:
    def __init__(self, ids: list[str], vectors: np.ndarray):
        self.vectors = np.asarray(vectors, dtype=np.float32)
        if (
            not ids
            or any(not isinstance(item, str) or not item.strip() for item in ids)
            or len(set(ids)) != len(ids)
            or self.vectors.ndim != 2
            or self.vectors.shape[0] != len(ids)
            or not np.isfinite(self.vectors).all()
            or not np.allclose(np.linalg.norm(self.vectors, axis=1), 1, atol=1e-5)
        ):
            raise ValueError("unique IDs and corresponding finite unit vectors required")
        self.ids = list(ids)

    def rank(
        self, query: np.ndarray, k: int = 10, exclude_id: str | None = None
    ) -> list[RankedDocument]:
        query = np.asarray(query, dtype=np.float32)
        if (
            type(k) is not int
            or not 1 <= k <= 1000
            or query.shape != self.vectors.shape[1:]
            or not np.isfinite(query).all()
            or not np.isclose(np.linalg.norm(query), 1, atol=1e-5)
        ):
            raise ValueError("positive ranking k and finite compatible unit query vector required")
        scores = np.einsum("ij,j->i", self.vectors, query, optimize=False)
        return sorted(
            (
                RankedDocument(doc_id, float(score))
                for doc_id, score in zip(self.ids, scores)
                if doc_id != exclude_id
            ),
            key=lambda row: (-row.score, row.doc_id),
        )[:k]

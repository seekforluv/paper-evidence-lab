import importlib
from types import SimpleNamespace

import numpy as np
import pytest


def semantic():
    return importlib.import_module("paper_evidence_lab.semantic")


def test_masked_pooling_normalizes_and_ignores_padding():
    hidden = np.array([[[3, 0], [0, 4], [999, 999]]], dtype=np.float32)
    actual = semantic().mean_pool_normalize(hidden, np.array([[1, 1, 0]]))
    np.testing.assert_allclose(actual, [[0.6, 0.8]], atol=1e-7)
    assert actual.dtype == np.float32


@pytest.mark.parametrize("mask", [[[0, 0]], [[1, -1]], [[1, 2]]])
def test_invalid_attention_mask_rejected(mask):
    with pytest.raises(ValueError):
        semantic().mean_pool_normalize(np.ones((1, 2, 2), dtype=np.float32), np.array(mask))


def test_zero_or_nonfinite_embeddings_rejected():
    for hidden in (np.zeros((1, 1, 2)), np.full((1, 1, 2), np.nan)):
        with pytest.raises(ValueError):
            semantic().mean_pool_normalize(hidden, np.ones((1, 1)))


def test_dense_rank_uses_all_scores_stable_ids_and_excludes_before_cutoff():
    index = semantic().DenseIndex(["b", "a", "c"], np.array([[1, 0], [1, 0], [-1, 0]]))
    rows = index.rank(np.array([1, 0]), k=3)
    assert [(r.doc_id, r.score) for r in rows] == [("a", 1.0), ("b", 1.0), ("c", -1.0)]
    assert [r.doc_id for r in index.rank(np.array([1, 0]), k=2, exclude_id="a")] == ["b", "c"]
    with pytest.raises(ValueError):
        semantic().DenseIndex(["a", "a"], np.array([[1, 0], [0, 1]]))
    with pytest.raises(ValueError):
        index.rank(np.array([3, 0]))


def fake_encoder(monkeypatch):
    import onnxruntime as ort
    from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors

    mod = semantic()
    vocabulary = {"[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3, "alpha": 4, "beta": 5}
    tokenizer = Tokenizer(models.WordPiece(vocabulary, unk_token="[UNK]"))
    tokenizer.normalizer = normalizers.Lowercase()
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.post_processor = processors.BertProcessing(("[SEP]", 3), ("[CLS]", 2))
    monkeypatch.setattr(
        mod.model_assets,
        "load_verified_model",
        lambda _: {"tokenizer.json": tokenizer.to_str().encode(), "onnx/model.onnx": b"synthetic"},
    )

    class FakeSession:
        def get_inputs(self):
            return [
                SimpleNamespace(name=n, type="tensor(int64)", shape=[None, None])
                for n in ("input_ids", "attention_mask", "token_type_ids")
            ]

        def get_outputs(self):
            return [
                SimpleNamespace(
                    name="last_hidden_state", type="tensor(float)", shape=[None, None, 384]
                )
            ]

        def get_providers(self):
            return ["CPUExecutionProvider"]

        def run(self, outputs, inputs):
            assert outputs == ["last_hidden_state"]
            assert set(inputs) == {"input_ids", "attention_mask", "token_type_ids"}
            assert all(a.dtype == np.int64 for a in inputs.values())
            ids = inputs["input_ids"]
            values = np.ones((*ids.shape, 384), dtype=np.float32)
            values[:, :, 0] = ids
            return [values]

    monkeypatch.setattr(ort, "InferenceSession", lambda *a, **kw: FakeSession())
    return mod.MiniLMEncoder(None)


def test_encoder_batch_padding_truncation_and_stats(monkeypatch):
    encoder = fake_encoder(monkeypatch)
    texts = ["alpha", "beta " * 300, "alpha beta"] * 6
    vectors = encoder.encode(texts)
    assert vectors.shape == (18, 384)
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-6)
    assert encoder.last_stats["text_count"] == 18
    assert encoder.last_stats["truncated_texts"] == 6
    assert encoder.last_stats["max_untruncated_tokens"] == 302
    encoding = encoder.tokenizer.encode("beta " * 300)
    assert len(encoding.ids) == 256
    assert encoding.ids[0] == 2 and encoding.ids[-1] == 3
    first = encoder.encode(["alpha"])[0]
    second = encoder.encode(["alpha", "beta " * 200])[0]
    np.testing.assert_allclose(first, second, atol=1e-7)

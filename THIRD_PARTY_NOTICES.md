# Third-party notices

Project code and original synthetic fixtures: MIT; see LICENSE. No third-party package source or binary is vendored here. Installers retrieve distributions with their own license files; those licenses continue to apply.

| Locked dependency | Declared license |
| --- | --- |
| bm25s 0.3.13 | MIT |
| NumPy 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (distribution metadata) |
| pytest 8.4.2 | MIT |
| iniconfig 2.3.1, pluggy 1.7.0 | MIT |
| packaging 26.3 | Apache-2.0 OR BSD-2-Clause |
| Pygments 2.21.0 | BSD-2-Clause |
| Ruff 0.14.0 | MIT |
| Hatchling 1.27.0 (build backend) | MIT |
| pathspec 1.1.1 (build dependency) | MPL-2.0 |
| trove-classifiers 2026.9.21.13 (build dependency) | Apache-2.0 |
| pytrec-eval-terrier 0.5.11 (development reference evaluator) | MIT wrapper; bundled trec_eval is separately licensed |
| SciPy 1.17.1 (transitive development dependency) | BSD-3-Clause core; additional bundled component licenses |

Dependency declarations checked against installed distribution metadata, including build dependencies. The build backend is installed from the same lockfile; documented builds disable build isolation so transitive build dependencies are locked too. NumPy distributions can include separately licensed components: retain their bundled notices when redistributing binaries. This repository does not vendor, modify, or relicense these dependencies.

arXiv paper versions and metadata terms are documented separately in [data/README.md](data/README.md). The public repository deliberately excludes real abstracts and raw response caches. Synthetic fixtures use reserved example.org addresses and are not real publications.

BM25 implementation: [BM25S official repository](https://github.com/xhluca/bm25s), [version 0.3.13](https://pypi.org/project/bm25s/0.3.13/). Source API: [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html).

The [pytrec-eval-terrier wrapper](https://github.com/terrierteam/pytrec_eval/blob/v0.5.11/LICENSE) is copyright (c) 2017 Christophe Van Gysel under MIT. Its [README](https://github.com/terrierteam/pytrec_eval/blob/v0.5.11/README.md#license) explicitly distinguishes trec_eval's license. The [v0.5.11 build recipe](https://github.com/terrierteam/pytrec_eval/blob/v0.5.11/setup.py) fetches trec_eval v9.0.8 when its submodule is absent; [that historical source](https://github.com/usnistgov/trec_eval/blob/v9.0.8/m_ndcg_cut.c) retains Chris Buckley's 2008 permission for research, non-commercial use. Do not describe all bundled evaluator code as MIT or substitute the different notice on current trec_eval main. This project uses it only as a local/development metric oracle and does not redistribute its source or binaries.

[SciPy 1.17.1](https://github.com/scipy/scipy/blob/v1.17.1/LICENSE.txt) has [separately licensed components](https://github.com/scipy/scipy/blob/v1.17.1/LICENSES_bundled.txt). The inspected macOS arm64 wheel uses Apple's Accelerate and includes GCC runtime libraries under GPL-3.0-or-later WITH GCC-exception-3.1 and libquadmath under LGPL-2.1-or-later. Other platform wheels can include OpenBLAS/LAPACK and other components. Preserve the installed distribution's complete LICENSE.txt and component notices when redistributing binaries; this repository does not include those binaries.

SciFact component attribution, differing upstream labels, and the local-only data policy are documented in [data/scifact.md](data/scifact.md).

The optional `semantic` extra adds the following locked distributions. These are retrieved by installers, not vendored in this repository.

| Optional dependency / version | Declared license |
| --- | --- |
| onnxruntime 1.31.0 | MIT core; separate third-party component notices |
| tokenizers 0.23.3 | Apache-2.0 core; native component licenses in bundled SBOM |
| flatbuffers 25.12.19, huggingface-hub 2.2.0, hf-xet 1.7.0 | Apache-2.0 |
| protobuf 7.36.2 | BSD-3-Clause |
| click 8.5.0, fsspec 2026.9.0, httpcore2 2.13.1, httpx2 2.13.1, idna 3.20 | BSD-3-Clause |
| anyio 4.15.1, filelock 4.2.0, h11 0.16.0, PyYAML 6.0.3, truststore 0.10.5 | MIT |
| tqdm 4.70.1 | MPL-2.0 AND MIT |
| typing-extensions 4.16.0 | PSF-2.0; retain complete distribution LICENSE |

Preserve ONNX Runtime's full `LICENSE` and `ThirdPartyNotices.txt` when redistributing binaries. Its notices span components across builds, including separately licensed material such as Eigen (MPL-2.0); inclusion in that list does not prove that every component is present in a particular wheel. Tokenizers' bundled CycloneDX SBOM records 127 Rust components for the inspected wheel, including `unicode-ident` with Unicode-3.0 terms and `target-lexicon` with LLVM-exception terms. Their notices are not replaced by the project-level Apache-2.0 label. The lock also includes conditional `httpx2-jsfetch 1.0` for Emscripten/Python >=3.12; it was not installed or license-audited in the validated macOS/Python3.11 environment, which is not an Emscripten support claim.

The selected MiniLM model is attributed separately in [data/minilm.md](data/minilm.md); model weights and source-card copies remain local. Local tokenization/ONNX byte loading do not require a service account. ONNX telemetry is explicitly disabled; real evaluation was additionally run with OS network access denied.

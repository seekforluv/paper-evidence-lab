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

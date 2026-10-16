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

Dependency declarations checked against installed distribution metadata, including build dependencies. The build backend is installed from the same lockfile; documented builds disable build isolation so transitive build dependencies are locked too. NumPy distributions can include separately licensed components: retain their bundled notices when redistributing binaries. This repository does not vendor, modify, or relicense these dependencies.

arXiv paper versions and metadata terms are documented separately in [data/README.md](data/README.md). The public repository deliberately excludes real abstracts and raw response caches. Synthetic fixtures use reserved example.org addresses and are not real publications.

BM25 implementation: [BM25S official repository](https://github.com/xhluca/bm25s), [version 0.3.13](https://pypi.org/project/bm25s/0.3.13/). Source API: [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html).

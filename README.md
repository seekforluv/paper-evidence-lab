# Paper Evidence Lab

**输入英文问题，在给定文献集合里找相关论文，保留原始摘要与出处。**

这是一个可复现的论文检索实验，面向逐步开展研究的学生。已实现本地BM25检索、严格数据校验、来源获取、JSON / Markdown 报告，以及固定 SciFact 数据上的BM25与轻量MiniLM评测。无需 API key、在线大模型或 GPU。

> **检索相关不等于结论已证实。** 某篇论文包含更多查询词，可能排得更靠前；这不说明它的实验更可靠，也不说明结论适用于所有人。

## 5 分钟运行

需要 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。第一次安装会联网下载 Python 和依赖；之后查询与测试完全在本地运行。

```bash
git clone https://github.com/seekforluv/paper-evidence-lab.git
cd paper-evidence-lab
uv sync --frozen
uv run --frozen python -m paper_evidence_lab search \
  --corpus tests/fixtures/synthetic.jsonl \
  --query 'developer productivity'
```

这条命令使用**原创合成数据**，不是论文或实验结果。它返回两条命中，第一条为 `synthetic-developer`；第二条没有摘要，会显示 `abstract: null` 和 `abstract_missing: true`。可直接阅读[合成 JSON](reports/synthetic-example.json)和[合成阅读报告](reports/synthetic-example.md)。

环境固定为 Python 3.11.14，`uv.lock` 固定全部解析依赖；主要依赖为 bm25s 0.3.13、NumPy 2.4.6。CI 使用同一个锁文件。Python 声明兼容范围为 3.11–3.14，当前实际验证环境是 3.11.14。

## 用真实论文演示

演示主题：**AI 编程助手在什么条件下提高开发效率，什么条件下拖慢？**

先获取两篇固定版本的 arXiv 预印本文献。脚本一次请求两个 ID，校验返回版本；保存原始 Atom 响应、SHA-256 获取凭据和严格 JSONL。失败退出 2，不生成假数据。已有本地语料可反复查询，无需重新下载。

```bash
uv run --frozen python scripts/fetch_seed.py
mkdir -p reports/local
uv run --frozen python -m paper_evidence_lab search \
  --corpus data/local/seeds.jsonl \
  --query 'AI coding assistants developer productivity' \
  > reports/local/real-demo.json
uv run --frozen python -m paper_evidence_lab search \
  --corpus data/local/seeds.jsonl \
  --query 'AI coding assistants developer productivity' \
  --format markdown > reports/local/real-demo.md
```

英文查询的中文释义是“AI 编程助手与开发效率”。查询只做词项匹配，不自动翻译问题、不判断支持或反驳。真实演示已获取并命中两篇来源，见[书目与演示记录](reports/real-demo-sources.md)。它们只是演示种子，**不是覆盖该领域的文献库或科研评测集**。

`data/local/` 与 `reports/local/` 已忽略，不随仓库上传。获取快照不覆盖：重复运行会提示路径已存在；需要重新获取时使用 `--output data/local/seeds-refresh.jsonl`，并在查询中使用新路径。请遵守 [arXiv API 使用条款](https://info.arxiv.org/help/api/tou.html)，缓存获取结果；整台机器保持单连接，API 请求至少间隔 3 秒。脚本只执行一次有界请求，不自动重试。

## 输入与输出约定

```bash
# 最多 5 条，只取正分命中；不够不会补零分论文
uv run --frozen paper-evidence-lab search \
  --corpus tests/fixtures/synthetic.jsonl --query 'quantum' --top-k 3

# 真正无命中：stdout 为 []、退出码 0，解释在 stderr
uv run --frozen paper-evidence-lab search \
  --corpus tests/fixtures/synthetic.jsonl --query 'zzzznomatch'
```

- M0 仅面向英文。包含中日韩字符、空白或不含英文字母的查询报错，退出 2；不会伪装成正常零命中。它没有完整的语言识别或跨语言能力。
- 查询经分词后只剩停用词时，返回空列表与解释。
- `--top-k` 只接受 1–5 的整数，默认 5。
- stdout 只输出 JSON 或 Markdown；错误与无命中解释写到 stderr。
- 对全部正分结果先按 `score` 降序、再按 `doc_id` 升序排序，最后截断；边界同分也确定。
- 结果保留题名、摘要、版本来源、类型、语言、论文许可和获取时间，另有 `title_missing`、`abstract_missing` 与 `score`。
- 摘要是原始来源字段，不是模型生成总结。报告只显示查询、结果字段和固定模板；文献中的 HTML/Markdown 标记被转义。
- 同一环境、语料与查询得到确定性输出；查询不修改 `fetched_at`。重新获取则会记录新的来源获取时间。

JSONL 每行恰有以下字段，未知字段也拒绝。错误含行号；重复 ID、重复 JSON key、NaN、空行、非法类型都不会被悄悄跳过。

| 字段 | 约束 |
| --- | --- |
| `doc_id` | 唯一非空字符串，无控制字符 |
| `title`, `abstract` | 非空白字符串或 `null`；不能同时为 `null`；缺失必须用 `null` |
| `source_url` | 有主机名的 HTTP(S) URL，无凭据或空白 |
| `source_type` | `paper` 或 `preprint`；博客拒绝进入索引 |
| `language` | `en` |
| `license_url` | 论文许可链接，HTTP(S) 或 `null`；不是项目代码许可 |
| `fetched_at` | 带时区的 ISO 8601 来源获取时间 |

只索引 `title + abstract`。预处理固定为小写、ASCII 正则 `[a-z]+` 分词、不做词干化，停用词固定为：

```text
a an and are as at be by for from in is it of on or that the to was with
```

`BM25(method="lucene", idf_method="lucene", k1=1.5, b=0.75)`，NumPy 后端、float32；参数未在种子上调优。保留重复查询词；重复出现会累加贡献。全为停用词的文献仍保留在语料中，但本身无词项命中。当前每次查询重新建小型索引、遍历并排序全部命中，尚未作大规模性能承诺。

## 固定 SciFact 评测

独立于两篇演示种子，M1 在官方 BEIR SciFact 的 5,183 篇文献、300 条查询上实际得到 **nDCG@10 = 0.67246、Recall@10 = 0.78561**。BEIR test 对应原 SciFact 公开 dev。完整参数、600 个逐查询指标参考核对、确定性复跑和错误样本分析见[评测报告](reports/scifact/bm25.md)。它衡量检索相关性，不是事实正确率。

```bash
# 只在首次运行时获取；已有目录不会覆盖
uv run --frozen paper-evidence-lab fetch-scifact --output data/local/scifact
mkdir -p reports/local
uv run --frozen paper-evidence-lab evaluate \
  --dataset data/local/scifact > reports/local/bm25.json
uv run --frozen python scripts/check_evaluation.py \
  --dataset data/local/scifact --result reports/local/bm25.json
```

输入 ZIP 和成员文件必须匹配固定哈希；原始数据留在忽略目录。组件许可和不同来源标签的差异见[数据说明](data/scifact.md)。评测使用独立 top-10 接口，展示用的 `search` 仍限 1–5。参数没有在本测试集调优，后续模型也使用同样的划分和指标。

## 一个固定语义模型的比较

唯一预选的 `all-MiniLM-L6-v2` 使用官方固定版本ONNX权重，在本地CPU推理。没有尝试多个模型择优；本次结果中，BM25平均nDCG更高。

| 方法 | nDCG@10 | Recall@10 |
| --- | ---: | ---: |
| BM25 | 0.67246 | 0.78561 |
| MiniLM（ONNX） | 0.64508 | 0.78333 |

```bash
uv sync --frozen --extra semantic
uv run --frozen --extra semantic paper-evidence-lab fetch-model --output data/local/minilm
uv run --frozen --extra semantic paper-evidence-lab evaluate-semantic \
  --dataset data/local/scifact --model data/local/minilm > reports/local/minilm.json
uv run --frozen --extra semantic python scripts/check_evaluation.py \
  --dataset data/local/scifact --result reports/local/minilm.json
```

3,681/5,183篇文献超过模型256-token上限，查询均未截断。未进行截断消融，不能将分数差距确定归因于截断。模型预训练与SciFact的具体重叠未核实。完整配置、真实运行边界及校验见[MiniLM报告](reports/scifact/minilm.md)；[来源与许可](data/minilm.md)单独记录。推理加载本地已验证文件，不向服务端发送原文。

## 冻结结果的离线对比页

[技术报告](reports/scifact/comparison.md)保留全部配对统计、改善与下降案例及解释边界。[单文件对比页](reports/scifact/comparison.html)下载后可直接用浏览器打开：默认展示全部300条查询，支持按ID和指标变化筛选、比较两套前10排名、下载完整配对JSON。它展示已保存的实验结果，不在浏览器里运行新检索。

无需数据或模型即可重新生成页面：

```bash
uv run --frozen python scripts/build_comparison.py
```

生成器核对查询覆盖、数据来源、@10截断值和均值；CI重新生成并检查提交的JSON/HTML是否一致。页面无外部脚本、字体或分析服务，查看与筛选完全离线。

## 测试和项目结构

```bash
uv sync --frozen --extra semantic
uv run --frozen --extra semantic pytest -q
uv run --frozen --extra semantic ruff check .
uv run --frozen --extra semantic ruff format --check .
uv build --no-sources --no-build-isolation
```

测试仅用原创夹具，网络连接在测试中被禁止；来源测试以受控 Atom 响应覆盖版本不符、缺摘要、异常响应和 HTTP/超时失败。真实获取另行运行，不能用离线测试通过代替来源获取成功。

```text
src/paper_evidence_lab/  校验、检索、CLI、报告、来源获取
data/seed_sources.json  固定版本书目（无摘要）
data/local/             原始响应、获取凭据、真实语料（忽略）
tests/fixtures/         原创合成数据
reports/                合成输出与真实书目链接
reports/local/          真实检索报告（忽略）
.github/workflows/      离线检查和构建
```

## 已完成的范围与研究边界

- **M0：** 来源可追溯的 BM25 检索原型；不产生准确率、证据强度或支持/反驳判决。
- **M1：** 固定 SciFact 输入、独立 top-10 评测、nDCG@10 / Recall@10 参考核对和有限错误分析，完整结果与复现命令已保存。
- **M2：** 一个预先固定的轻量英文语义模型，在同样的数据划分与指标下比较；完整结果和独立校验已保存。
- **M3：** 基于冻结结果形成配对技术报告和可离线分享的交互对比页，覆盖全部300条查询。

软件工程两篇种子与 SciFact 的领域不同，基准结果也不能直接说明本演示问题已得到可靠回答。METR 的[后续实验设计更新](https://metr.org/blog/2026-02-24-uplift-update/)仅作为背景链接，不作为第三篇论文、摘要或评测样本。

## 许可与来源

原创代码和合成夹具采用 [MIT](LICENSE)。第三方依赖、arXiv 元数据、论文全文与模型各自适用其条款，详见[数据说明](data/README.md)和[第三方说明](THIRD_PARTY_NOTICES.md)。模型权重下载后仅保留本地；未发布原始语料、模型权重、私人会话或账户信息，未下载论文PDF。

本项目由 Codex 实现与实测，真实 ZCode 参与候选代码审查；模型审查不代替可执行测试或科学证据。发布只代表可复现原型，不代表论文创新、录用或基准领先。

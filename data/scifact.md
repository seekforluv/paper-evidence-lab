# SciFact 固定来源与组成部分

使用 [BEIR 官方 scifact.zip](https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip)，不混用原始 SciFact 与镜像文件。包没有版本化文件名，以下校验值固定本次输入。完整清单在安装包内的 [scifact_source.json](../src/paper_evidence_lab/scifact_source.json)，wheel 安装也可读取。

| 项目 | 固定值 |
| --- | --- |
| 压缩包大小 | 2,816,079 bytes |
| 官方公布 MD5 | `5f7d1de60b170fc8027bb7898e2efca1` |
| 本次读取 SHA-256 | `536e14446a0ba56ed1398ab1055f39fe852686ecad24a6306c80c490fa8e0165` |
| Corpus | 5,183 篇 |
| 包内全部 queries | 1,109 条 |
| test qrels 覆盖 queries | 300 条 |
| test qrel pairs | 339 对，均为标签 1 |

MD5 对照 [BEIR 固定版本 README](https://github.com/beir-cellar/beir/blob/ef83d29307061c65d04b035b4f4e7c18bd8374af/README.md)。SHA-256、字节数、成员文件哈希与计数由本次实际下载解析得到；不能把官方 MD5 误称为官方公布 SHA-256。

**BEIR test 是原 SciFact 的公开 dev。** [BEIR 论文 Appendix D.9](https://arxiv.org/html/2104.08663)明确说明此转换；它不是原数据集隐藏测试集。本项目只按 `qrels/test.tsv` 选择查询，不使用其余 queries 或 train labels 调参。qrel 1 表示检索相关性，不是支持/反驳标签或结论正确性的判定。数据集归属为 Wadden 等人的 [SciFact](https://github.com/allenai/scifact) 和 Thakur 等人的 [BEIR](https://github.com/beir-cellar/beir)；本项目没有创建这些标注。

## 许可记录

[原 SciFact 固定版本许可](https://github.com/allenai/scifact/blob/68b98a56d93e0f9da0d2aab4e6c3294699a0f72e/LICENSE.md)按组件声明：

| 组成部分 | 原作者声明 |
| --- | --- |
| Claims、evidence annotations | CC BY 4.0 |
| Corpus abstracts | ODC-By 1.0 |
| 原项目代码 | Apache 2.0 |

[HF scifact 数据卡](https://huggingface.co/datasets/BeIR/scifact/blob/b3b5335604bf5ee3c4447671af975ea25143d4f5/README.md)及 [qrels 数据卡](https://huggingface.co/datasets/BeIR/scifact-qrels/blob/2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029/README.md)标 CC BY-SA 4.0；2021 BEIR 论文 Appendix E 还标 CC BY-NC 2.0。未找到统一这些标签的官方解释，差异保持未解决；不能把某个镜像标签直接当作所有内容的唯一许可。[ODC-By](https://opendatacommons.org/licenses/by/1-0/)对数据库的许可也不自动覆盖每个独立内容项的版权。

本仓库发布代码、来源链接、哈希、汇总指标和 ID/分数结果。原 ZIP、摘要、查询、qrels 和文本索引留在忽略目录 `data/local/`；这是一项项目发布范围选择，不是宣称所有数据都禁止再分发。项目 MIT 仅用于本项目原创代码与合成测试材料。

## 获取与完整性

```bash
uv run --frozen paper-evidence-lab fetch-scifact --output data/local/scifact
# 若已通过浏览器/curl 下载官方 ZIP，可以导入同一字节内容：
uv run --frozen paper-evidence-lab fetch-scifact \
  --archive /path/to/scifact.zip --output data/local/scifact
```

二者都核对固定大小、MD5、SHA-256、精确成员列表、每个被使用文件的 SHA-256、引用完整性和精确计数。程序只按固定成员名读取，无 `extractall`；train.tsv 不被读入评测。网络请求为单次、socket 超时 90 秒、响应最多 5 MiB，不自动重试。官方源内容若改变会失败，不静默换数据。

目标目录必须不存在，保存原 ZIP 和三份实际输入，最后写 `receipt.json` 完成标记；导入时间不是论文发表时间或原文件创建时间。普通写入失败清理本次新建目录，不覆盖旧快照；掉电/强制终止可能留下不完整目录，应保留检查并改用新路径。每次评测重验完成凭据、原 ZIP 和输入文件，解析刚刚验过的同一份字节。哈希记录不能代替许可授权或数据标注质量保证。

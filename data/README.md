# 数据与许可

`seed_sources.json` 只含人工核对的书目信息和版本化链接。获取脚本从 arXiv Atom API 读取题名和摘要，保留 XML 解码后的字符串，包括原始空白；索引分词是另一层操作，不改展示文本。缺少字段或只有空白时写 `null`。题名、摘要同时缺失则拒绝。

| 固定论文版本 | 论文许可（`license_url`） |
| --- | --- |
| [Peng et al., 2302.06590v1](https://arxiv.org/abs/2302.06590v1) | [arXiv non-exclusive distribution](https://arxiv.org/licenses/nonexclusive-distrib/1.0/license.html) |
| [Becker et al., 2507.09089v2](https://arxiv.org/abs/2507.09089v2) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

上述论文许可于 2026-10-16 从指定版本页面核对；来源脚本不会从 API 推断或自动更新许可。arXiv 入口在本数据集中标为 `preprint`，不据此断言作者没有正式发表或同行评审版本。

[arXiv API 条款](https://info.arxiv.org/help/api/tou.html)将包含题名、摘要、作者等的描述性元数据按 CC0 提供。它和论文全文许可不同：`license_url` 指论文许可，获取凭据中的 `metadata_terms_url` 指元数据条款。项目代码 MIT 许可不替代这些条款。

本仓库采用保守发布范围：真实摘要、Atom 缓存、获取凭据与含摘要报告留在本地忽略目录；公共内容是必要书目与链接、原创合成数据和程序。合成数据中的 `example.org` 是占位域名，`fetched_at` 是测试时间，不代表下载过实际论文。

脚本仅作单次有界请求，最长 30 秒、最大响应 1 MiB，无自动重试。先校验完整响应中的版本 ID 集合、重复项和文本，拒绝 DTD/实体声明，再写本地缓存与语料。快照不覆盖；目标或其伴生文件已存在时直接拒绝，重新获取须选择新的 `--output`。

缓存名追加在完整文件名后，如 `seeds.jsonl.atom.xml` 和 `seeds.jsonl.receipt.json`。凭据包含请求 URL、获取时间、版本 ID、原始响应及语料 SHA-256。先暂存三份内容，再用同文件系统硬链接独占发布，语料最后出现；普通 I/O 错误会撤回本次已发布文件。这不是掉电安全的多文件事务；进程被强制终止后可能留下没有语料的伴生文件，应保留检查并换新路径。正常发布不修改已有快照。查询不访问网络。

这两篇只是功能演示，不构成系统检索、完整综述或标准基准。M1 使用独立的 [SciFact 固定快照与许可记录](scifact.md)，没有把演示种子混入评测。

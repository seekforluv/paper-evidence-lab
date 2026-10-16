# SciFact：固定 MiniLM 语义基线

预先选定的 `all-MiniLM-L6-v2` 在相同 SciFact 输入上得到 **nDCG@10 = 0.64508、Recall@10 = 0.78333**。在本次300条查询上，BM25的平均nDCG更高；不据此修改模型或参数再报一个测试成绩。

| 指标 | MiniLM 原值 | BM25 原值 | MiniLM − BM25 |
| --- | ---: | ---: | ---: |
| nDCG@10 | 0.6450816521455776 | 0.6724627519030216 | −0.02738109975744413 |
| Recall@10 | 0.7833333333333333 | 0.7856111111111111 | −0.002277777777777778 |

输入为 BEIR test（原 SciFact **公开dev**）300查询、5,183篇文献、339相关性对。两份结果的压缩包/输入文件SHA-256完全相同，文献拼接规则同为标题+换行+摘要。BM25读取完整文本，MiniLM按预定256-token上限截断，**有效上下文覆盖不同**。

模型revision、权重及tokenizer哈希、官方池化规则与许可见[模型说明](../../data/minilm.md)；规格在首次语义运行前的提交 `ded2c97` 已冻结。没有尝试多个模型、微调或根据本测试集选择参数。预训练数据与SciFact的具体重叠未核实，不声称无污染零样本。

## 复现命令

```bash
uv sync --frozen --extra semantic
# 初次运行按 data/scifact.md 与 data/minilm.md 获取固定快照，已有数据不重复下载
mkdir -p reports/local
HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
uv run --frozen --extra semantic paper-evidence-lab evaluate-semantic \
  --dataset data/local/scifact --model data/local/minilm \
  > reports/local/minilm.json
uv run --frozen --extra semantic python scripts/check_evaluation.py \
  --dataset data/local/scifact --result reports/local/minilm.json
```

真实运行在macOS arm64、Python3.11.14、ONNX Runtime1.31.0、Tokenizers0.23.3、NumPy2.4.6完成；CPUExecutionProvider，sequential，单线程，batch16。ONNX遥测关闭。两次完整推理都额外使用macOS `sandbox-exec` 的 `deny network*` 规则阻断进程网络；普通跨平台复现命令如上，不依赖该macOS工具。

实际图签名为3个int64输入及 `[batch, sequence, 384]` token向量输出；按attention mask均值池化、L2归一化，再精确余弦排序。特殊tokens按实际mask计入均值，PAD不计入。无量化、分块、ANN或提示词，所有前10名按分数降序/ID升序确定，不滤负分。

原始数字、逐查询ID/分数及实现哈希见 [minilm.json](minilm.json)。独立评测器对600个指标核对，最大误差 **0.0**，见[参考校验](minilm-reference-check.json)。两个独立进程全部重新编码，结果文件字节一致。原创合成句子的维度、范数、截断与不同padding检查见[运行检查](minilm-runtime-check.json)；它不证明科学问题回答能力，也不声称与PyTorch逐位等价。

## 截断与限制

| 输入 | 总数 | 超过256 tokens并截断 | 未截断时最大长度 |
| --- | ---: | ---: | ---: |
| 文献 | 5,183 | 3,681（71.0206%） | 1,939 |
| 查询 | 300 | 0 | 64 |

长度包含特殊tokens。采用模型官方默认上限，未为了本数据结果改长。没有做截断消融，因此**不能把性能差距确定归因于截断**；训练来源、领域覆盖、词项与实体处理等解释也未作因果验证。

指标仅评价既有qrels下的文档检索，不评价证据句、支持/反驳、事实真假或全文质量。完整配对分析见[M3技术报告](comparison.md)，全部查询可在[离线对比页](comparison.html)查看。原始查询、摘要、标签文件、模型权重未随公共仓库分发。

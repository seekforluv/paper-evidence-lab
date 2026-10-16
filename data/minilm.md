# MiniLM 模型来源与本地推理

唯一预选模型为 [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md)，固定 revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`。模型卡声明 Apache-2.0，384维英文句向量。该许可与本项目 MIT 代码许可、SciFact 数据许可分别记录。

采用官方未量化 `onnx/model.onnx`，90,405,214 bytes，SHA-256 `6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452`，本地下载已与官方权重元数据核对。`tokenizer.json` 为466,247 bytes，SHA-256 `be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037`；同时核对 Git blob ID `cb202bfe2e3c98645018a6d12f182a434c9d3e02`。Git blob ID 不是文件 SHA-256。

[完整清单](../src/paper_evidence_lab/minilm_source.json)还固定模型卡、模型配置、句向量长度、池化、模块顺序、tokenizer配置、特殊tokens和训练来源配置，共10份文件。它们保存在本地模型快照中，公共仓库只保存校验值和来源链接。

```bash
uv sync --frozen --extra semantic
uv run --frozen --extra semantic paper-evidence-lab fetch-model \
  --output data/local/minilm
# 已下载这些固定文件时，可导入目录，仍逐文件核对哈希：
uv run --frozen --extra semantic paper-evidence-lab fetch-model \
  --from-directory /path/to/downloaded-files --output data/local/minilm
```

目标必须不存在。单文件请求 socket 超时90秒，最多读取清单所列大小加1字节，无自动重试；源内容不同则失败。完整验证后创建快照，最后写完成凭据；普通写入失败清理本次目录。此过程不是掉电安全事务，意外中止后保留现场并选择新路径。推理只加载已验证的同一份模型和 tokenizer 字节，不调用远程推理接口，不把文献文本发送给模型供应商。

编码规则在[首次评测前的规格](../docs/m2-spec.md)固定。实际ONNX输出已核实为 `[batch, sequence, 384]` 的 `last_hidden_state`，不是已经池化的句向量；外部按attention mask作均值池化再L2归一化。[官方ONNX说明](https://sbert.net/docs/sentence_transformer/usage/efficiency.html#onnx)要求外部调用者自行完成这些步骤。

显式最大长度256，含CLS/SEP；来自 `sentence_bert_config.json`，不采用 tokenizer_config 中的512值。保留完整tokenizer的小写WordPiece规则、右截断和右侧动态padding。单线程CPU、batch16、float32，精确全库余弦排序。没有量化、近似索引、分块、提示词、微调或测试集选模。

模型的[训练配置](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/data_config.json)包含S2ORC、SPECTER；SciFact也来自科学文献语料。**具体训练记录与SciFact的重叠尚未核实**。本项目没有进行SciFact微调或按测试分数选模，这不等于已验证无污染零样本。

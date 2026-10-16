# M2：预先固定一个语义检索模型

此规格在任何本项目语义评测分数产生前冻结；不根据 SciFact test 结果选择模型或修改参数。M1 基线已合并于 `3838e2c`，M2 只使用一个预选模型，不尝试候选集择优。

- 模型：`sentence-transformers/all-MiniLM-L6-v2`，revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`，官方未量化 `onnx/model.onnx`；384维。权重 SHA-256 `6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452`，90,405,214 bytes。
- 完整官方 `tokenizer.json`，右截断256 tokens（含特殊tokens），右侧动态padding到batch最长，[PAD] id0。保留WordPiece、lowercase与special token规则，不加提示词、不分块、不翻译。
- 标题+换行+摘要，查询使用原文；与M1使用同一份已验证SciFact数据及300条查询。不做微调。
- ONNX Runtime1.31.0、Tokenizers0.23.3、锁定NumPy；CPUExecutionProvider，sequential，单线程，batch16，float32。Transformer token output按attention mask均值池化，再L2归一化；mask=1的特殊tokens包含在均值中。无在线推理服务。
- 单位向量点积作余弦；全5,183篇精确排序；score降序、ID字符串升序；排除query/doc同ID。本数据实际无ID重叠。dense取top10，不滤负分；M1正分规则保持原样，本次BM25全部300条都有10个正分命中。
- 指标与M1相同，全部300条宏平均，参考校验传递保序的严格递减序数分数。结果只公开ID、分数、哈希、配置、版本与指标；原文、模型权重和向量缓存保留本地。
- 先测试mask、截断、归一化、批边界、同分排序和哈希失配，再跑真实模型。核对实际ONNX输入输出、shape、finite、单位范数。两个独立进程重算验证；不声称与PyTorch后端逐位一致。
- 同时报告两种方法的胜/平/负查询数、均值差和固定样本差异；不通过选取成功案例暗示普遍改进。语义模型可能更差，照实保存结果。

训练来源包含S2ORC/SPECTER，SciFact也来自科学文献语料；具体训练重叠未核实。因此仅声称本项目未做SciFact微调/按test结果选模，不声称已验证无污染零样本。

来源：[固定模型卡](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md)、[256长度配置](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/sentence_bert_config.json)、[池化配置](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/1_Pooling/config.json)、[模块顺序](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/modules.json)、[官方ONNX使用说明](https://sbert.net/docs/sentence_transformer/usage/efficiency.html#onnx)、[训练来源](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/data_config.json)。

实施顺序：固定文件清单→受控下载/导入与完整性测试→纯数值池化与排序测试→本地编码和CLI→真实评测/独立核对/复跑→有限差异分析→ZCode设计审查验收与独立代码审查→GitHubCI与报告。M3整理实际结果和可复现演示，不另造创新声明。

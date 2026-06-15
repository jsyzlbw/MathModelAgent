# MathModelAgent 成熟化路线规划

## 1. 文档目标

本文档用于把当前 MathModelAgent 从 **GUI MVP + 工作区基础设施** 推进到 **可稳定完成 MCM/ICM 任务的成熟产品阶段**。

当前项目已经具备：

- `/studio` GUI 工作台。
- 统一 JSON 配置与逐项 API 通断测试。
- 工作区、题目上传、输入清单、进度事件、产物预览。
- RAG 范文知识库结构、扫描、轻量索引。
- 交互式 Planning/HIL。
- 持久化对话与修订请求。
- 最终产物提交包打包。

但这些能力还主要是“产品壳 + 数据契约 + MVP 服务”。成熟阶段的核心任务是：把这些契约真正接入一个可靠、可观察、可回退、可验收的端到端数学建模 Agent Pipeline。

---

## 2. 成熟版本的目标定义

成熟版本不是“能偶尔跑出一篇论文”，而是满足以下标准：

1. 用户通过 GUI 完成本次任务输入、API 配置、RAG 导入和计划确认。
2. 系统能解析题目 PDF、附件数据、图片、表格和格式要求。
3. 系统能结合 RAG 范文、搜索结果、官方数据源和用户意见，生成可审查的建模计划。
4. 系统能自动选择合适的模型路线，执行代码实验，生成结果表和图表。
5. 系统能把所有关键 claim 绑定到证据来源，减少编造结论。
6. 系统能生成 LaTeX/PDF/DOCX/Markdown 等论文产物。
7. 系统能自动做格式 QA、引用 QA、数值一致性 QA 和 reviewer-style 审查。
8. 用户能在 GUI 中看到 Agent 当前阶段、失败原因、待确认事项和最终提交包。
9. 多个样例题能重复跑通，失败时能定位到具体环节，而不是静默卡死。

---

## 3. 当前缺口总览

| 模块 | 当前状态 | 成熟阶段缺口 |
| --- | --- | --- |
| GUI | 已有 Studio MVP | 需要更强的任务状态机、阶段确认、失败恢复、产物审阅体验 |
| 配置 | 已有 ignored JSON 和 example | 需要所有 Agent、provider、pipeline 都从该 JSON 读取 |
| Provider Smoke | 已有单 provider 测试框架 | 需要真实 OpenAI/搜索/文档解析/官方数据/embedding/rerank smoke |
| 输入解析 | 已有 input manifest | 需要 PDF/OCR/图片/Office/表格深度解析 |
| RAG | 已有结构化案例库和 keyword index | 需要 embedding、chunking、rerank、引用回溯、方法检索 |
| Planning/HIL | 已有 plan.json 和六动作 | 需要计划驱动真实 pipeline，支持阶段回退 |
| 对话修订 | 已有 messages/revision queue | 需要 Revision Agent 消费队列并局部重跑 |
| 建模求解 | 仍偏 MVP | 需要题型识别、模型选择、solver 模块、验证与敏感性分析 |
| 论文写作 | 仍需增强 | 需要 claim-aware 写作、证据链、章节级质量控制 |
| LaTeX/排版 | 未完整闭环 | 需要编译、页数、溢出、图表位置、自动修复 |
| 评估体系 | 未完整建立 | 需要 benchmark case、自动评审、回归测试 |

---

## 4. 需要新增或强化的 API 能力

成熟阶段建议把 API 需求分成“强依赖”“强烈建议”“可选增强”三类。

### 4.1 强依赖 API

这些能力如果没有外部 API，也必须用本地模型或本地工具替代。

| 能力 | 是否需要 API | 用途 | 备注 |
| --- | --- | --- | --- |
| Chat / Reasoning LLM | 需要 | Coordinator、Modeler、Coder、Writer、Reviewer | 已有 LLM 配置框架，但要确保所有角色从 JSON 读取 |
| Embedding 模型 | 需要或本地替代 | RAG 范文、方法笔记、题面解析结果向量化 | 成熟 RAG 必需 |
| 文档解析 / OCR | 需要或本地替代 | 解析题目 PDF、扫描图片、表格、公式 | MinerU、OCR、本地 PDF 工具都可做 provider |
| Web Search | 需要 | 找现实背景、政策、论文、数据源 | Tavily/Brave/Exa/Firecrawl 等可组合 |
| 代码执行环境 | 可本地，但必须有 | 运行 Python 求解、画图、生成数据表 | 本地 Jupyter 已有基础，云端 E2B/Daytona 可选 |

### 4.2 强烈建议 API

这些不是第一天必须有，但成熟体验会明显依赖。

| 能力 | 用途 | 是否必须付费 |
| --- | --- | --- |
| Rerank 模型 | 对 RAG 召回结果重排，减少噪声 | 可用 API 或本地 reranker |
| Academic API | 查论文、引用、方法资料 | OpenAlex/Crossref/arXiv 多数可低成本使用，Semantic Scholar 可能需要 key |
| Official Data API | 自动获取真实数据 | World Bank/Open-Meteo 可低门槛；FRED、US Census、NOAA 等可能需要 key |
| Geospatial API | 地理题、路径、POI、区域数据 | OSM/Overpass 可用，商业地图 API 可选 |
| Vision LLM | 图片题、图表理解、截图 QA | 可选，但对多模态题体验提升很大 |

### 4.3 可选增强 API

| 能力 | 用途 | 建议 |
| --- | --- | --- |
| Humanizer / Writing Polish | 改善英文表达自然度 | 只能做合规润色，不做规避检测 |
| Grammar / Readability API | 英文语法和可读性检查 | 可由 LLM reviewer 替代 |
| Managed Vector DB | 大规模 RAG 存储 | MVP 可先用本地 Chroma/SQLite/FAISS |
| Cloud Object Storage | 多用户部署时保存上传文件和产物 | 单机版暂不需要 |
| Authentication / Billing | SaaS 化时需要 | 当前个人本地版暂不需要 |

### 4.4 最小推荐 API 组合

如果只想先做成熟单机版，最低配置建议：

1. 一个强模型 API：用于 coordinator/modeler/writer/reviewer。
2. 一个代码能力较强的模型 API：用于 coder/debugger。
3. 一个 embedding 模型 API 或本地 embedding 模型。
4. 一个 web search API。
5. 一个文档解析/OCR provider，优先支持 PDF 和扫描版题面。

如果要进一步提高论文质量，再加：

1. rerank 模型。
2. academic API。
3. FRED / World Bank / Open-Meteo / US Census / NOAA / OSM 等官方数据 provider。
4. vision LLM。

---

## 5. 成熟化实施路线

## R 路线：Runtime Config 全链路接入

目标：让 GUI JSON 配置真正驱动所有 Agent 和 Provider。

需要完成：

- 定义统一 `RuntimeConfig` schema。
- 把 coordinator/modeler/coder/writer/reviewer 的模型选择全部接入 JSON。
- 把 search、RAG、document parser、official data、humanizer、sandbox 配置全部接入 JSON。
- 增强 provider smoke：不仅检查 key 是否存在，还能做最小真实请求。
- GUI 设置页显示 provider 状态、最后测试时间、错误原因。

验收标准：

- 改 JSON 后无需改 `.env.dev` 即可切换主要 provider。
- 每个 provider 行的测试按钮能返回 `ok / missing_config / auth_error / quota_error / network_error / not_implemented`。
- 后端测试覆盖配置脱敏、保存、读取、smoke 错误映射。

---

## S 路线：Document Extraction 与多模态解析

目标：把 `input_manifest.json` 从“文件清单”升级为“可被 Agent 使用的解析结果”。

需要完成：

- 为 PDF、图片、DOCX、XLSX、PPTX 建立 provider adapter。
- 对题目 PDF 提取 Markdown、公式、表格、图片、页码映射。
- 对附件表格建立 data profile：列名、类型、缺失率、样例值。
- 对图片建立 OCR/vision summary。
- 生成 `input/parsed/problem.md`、`input/parsed/tables/*.csv`、`input/parsed/assets/*`。
- 增加解析 QA：页数是否一致、表格是否为空、公式是否丢失、OCR 置信度。

验收标准：

- 上传一份 PDF 赛题后，Studio 能显示解析文本和表格清单。
- Planning 使用解析后的题面，而不是只用用户粘贴文本。
- 解析失败会显示具体 provider 和错误原因。

需要 API：

- 文档解析/OCR provider。
- 可选 Vision LLM。

---

## T 路线：RAG v2 知识库

目标：让 RAG 从 keyword index 变成真正可检索、可引用、可解释的方法库。

需要完成：

- 支持用户范文 ingest：题目、论文、数据说明、方法笔记。
- Chunk schema：题目背景、模型方法、假设、求解步骤、图表表达、摘要/引言写法。
- Embedding 生成与本地向量存储。
- Rerank 与 metadata filter。
- 检索日志 `rag/retrieval_log.jsonl`。
- 引用回溯：Writer 引用 RAG 内容时必须记录 case_id、chunk_id、原文路径。
- GUI 展示 RAG 命中结果与可用性。

验收标准：

- 用户导入 5 篇范文后，Planning 能检索相似题型和可借鉴模型。
- Writer 能引用方法库，但不会把范文内容直接复制进论文。
- 每次 RAG 检索有日志可查。

需要 API：

- Embedding 模型强依赖。
- Rerank 模型强烈建议。

---

## U 路线：Plan 驱动的 Agent Pipeline

目标：让 `planning/plan.json` 成为真实 pipeline 的入口，而不是只展示在 GUI。

需要完成：

- 定义 pipeline 状态机：intake、parse、understand、plan、search、rag、model、solve、write、qa、export。
- 每个阶段读取上游 artifact，写入下游 artifact。
- 阶段产物进入 `artifact_registry.json`。
- 每个阶段写 progress event。
- HIL 动作能改变 pipeline：confirm 继续，edit 更新 plan，abort 停止，regenerate 回到 planning。
- 支持阶段重跑：用户修改 plan 后只重跑受影响阶段。

验收标准：

- Studio 点击开始后，右侧进度不是单个后台任务，而是阶段事件流。
- 任意阶段失败，都能看到失败 artifact、错误类型和可重试按钮。
- Pipeline 可以从已有 workspace 恢复。

需要 API：

- 无新增强依赖，但依赖 R/S/T 路线中的 provider。

---

## V 路线：Search、Academic、Official Data Provider

目标：让系统能主动获取真实外部数据和可靠来源。

需要完成：

- Query Planner：从题目生成搜索计划。
- Source Registry：记录外部网页、论文、官方数据来源。
- Search provider adapters：Tavily、Brave、Exa、Firecrawl 等。
- Academic provider adapters：OpenAlex、Crossref、arXiv、Semantic Scholar。
- Official data adapters：World Bank、OECD、UNData、FRED、US Census、NOAA、NASA、Open-Meteo、OSM/Overpass。
- Source verifier：检查时间、来源类型、是否可引用、是否与题目口径一致。

验收标准：

- 每个外部数字都有 source_id。
- Writer 不能引用未登记来源。
- GUI 能展示“本论文使用了哪些外部数据/论文来源”。

需要 API：

- Web search API。
- Academic API。
- Official data API，按题型可选。

---

## W 路线：真实建模能力增强

目标：从固定 MVP solver 升级为题型驱动的建模系统。

需要完成：

- 题型识别：预测、优化、评价、分类、网络、仿真、排队、博弈、地理、时空、风险。
- 模型候选库：AHP/TOPSIS、回归、时间序列、优化、图模型、聚类、仿真、蒙特卡洛、元启发式等。
- Model Council：生成多套方案。
- Model Judge：基于题目目标、数据可用性、解释性、可实现性选择方案。
- Solver templates：每类模型有可运行代码骨架。
- Validation：交叉验证、敏感性分析、鲁棒性分析、误差分析。
- Results registry：所有关键数值写入 JSON，供论文引用。

验收标准：

- 至少覆盖 8 类常见 MCM/ICM 题型。
- 每个模型输出都有代码、结果表、图表和解释。
- Writer 只引用 results registry 中存在的数值。

需要 API：

- 主要依赖 LLM 和代码执行环境。
- 某些题型可能需要官方数据或地理 API。

---

## X 路线：Claim-Aware Paper Generation

目标：把论文写作从模板填充升级为证据链驱动写作。

需要完成：

- 建立 `claim_plan.json`：每个关键论点、对应证据、图表、数据来源、章节位置。
- 分章节写作：abstract、introduction、assumptions、model、results、limitations、conclusion。
- Evidence linker：把 claim 链接到 results、figures、source_registry、rag chunks。
- Citation manager：生成 bib 或引用列表。
- Writing QA：检查空泛段落、无证据结论、数值不一致、引用缺失。
- 多轮 reviewer：结构审查、数学建模审查、英文表达审查、比赛评分视角审查。

验收标准：

- 每个关键结果都能追踪到数据或代码输出。
- 不允许凭空编造参考文献和数值。
- `claim_plan.json` 覆盖论文主要段落。

需要 API：

- 强 LLM。
- RAG embedding/rerank。
- Academic/search provider 可增强引用质量。

---

## Y 路线：LaTeX / 排版 QA

目标：让最终论文不止有内容，还能稳定编译和满足比赛格式要求。

需要完成：

- LaTeX 模板管理：MCM/ICM 默认模板、自定义模板。
- 编译器封装：latexmk 或 tectonic。
- 编译错误解析与自动修复。
- 页数检查、页边距检查、表格溢出、公式溢出、图片位置检查。
- PDF 页面截图 QA。
- Figure/table caption QA。
- 最终导出 PDF、LaTeX 源码、图表、数据表和提交包。

验收标准：

- 常见 LaTeX 错误能自动定位并修复。
- PDF 页数、图表、表格不明显溢出。
- GUI 可以预览编译日志和最终 PDF。

需要 API：

- 本地 LaTeX 工具即可。
- 可选 Vision LLM 做 PDF 页面视觉 QA。

---

## Z 路线：Benchmark、回归测试与产品稳定性

目标：让系统从“能跑”变成“可持续迭代且不容易退化”。

需要完成：

- 建立样例题 benchmark：至少 10 个不同类型题。
- 每个样例记录期望产物和最低质量标准。
- Provider smoke 一键检查命令。
- GUI e2e smoke：配置、上传、生成 plan、运行 demo、打包。
- Pipeline replay：给定 workspace 可以重放每个阶段。
- 成本记录：每次运行 token、API 次数、耗时。
- 错误分类：配置错误、provider 错误、解析错误、建模错误、写作错误、排版错误。

验收标准：

- 每次核心改动后能跑回归测试。
- 至少 3 个样例题能端到端生成可审查论文包。
- 失败任务能定位到阶段和原因。

需要 API：

- 与前面路线相同。
- 不建议 benchmark 默认消耗昂贵 API，可使用 fake provider 和小样例分层测试。

---

## 6. 建议实施顺序

推荐顺序：

1. R：Runtime Config 全链路接入。
2. S：Document Extraction 与多模态解析。
3. T：RAG v2 embedding/rerank。
4. U：Plan 驱动 pipeline。
5. W：建模 solver 和验证能力。
6. X：Claim-aware paper generation。
7. V：Search/Academic/Official Data provider 扩展。
8. Y：LaTeX / PDF QA。
9. Z：Benchmark、回归测试、成本与稳定性。

其中 R、S、T、U 是成熟化的地基。没有这四步，后面的写作和建模会继续停留在“看起来像 Agent，但不够可靠”的阶段。

---

## 7. API 采购/配置建议

第一阶段建议先准备：

1. LLM API：至少一个强推理模型，一个适合代码的模型。
2. Embedding API：RAG v2 必需。
3. Search API：Tavily、Brave、Exa、Firecrawl 任取一到两个。
4. Document Parser/OCR：MinerU 或等价方案。
5. 可选 Rerank API：RAG 质量会明显提升。

第二阶段再补：

1. Academic API。
2. FRED / US Census / NOAA / World Bank / Open-Meteo / OSM 等官方数据 provider。
3. Vision LLM，用于图像题、截图 QA 和 PDF 页面 QA。
4. 云端 code sandbox，用于隔离执行或多用户部署。

不建议一开始就采购：

- Managed vector database。
- SaaS 用户系统。
- 商业地图 API。
- 多个 humanizer API。

原因：当前最重要的是把 pipeline 跑通，避免 API 太多导致配置复杂度上升。

---

## 8. 成熟阶段最终验收标准

成熟阶段完成时，应满足：

1. 用户只通过 GUI 即可完成配置、导入范文、上传题目、确认计划、运行、审阅和下载提交包。
2. 所有 provider 都能通过 GUI 或命令行 smoke 检查。
3. RAG 能基于 embedding 检索范文和方法笔记。
4. PDF/图片/表格能解析为 Agent 可消费的 Markdown/JSON/CSV。
5. Pipeline 阶段可见、可重试、可恢复。
6. 至少 3 个 MCM/ICM 样例题端到端跑通。
7. 最终论文包包含 PDF、源码、图表、数据表、日志、artifact manifest。
8. 每个关键 claim 有证据来源。
9. LaTeX 编译和基础排版 QA 自动完成。
10. 后端测试、前端构建、GUI smoke、provider smoke 都通过。

---

## 9. 下一步建议

建议下一步先执行 **R 路线：Runtime Config 全链路接入**。

原因：

- 用户已经明确要求所有 API 和 LLM 选择都在一个 JSON 中配置。
- 当前 GUI 已经有配置入口，但 pipeline 内部还需要彻底消除 `.env` 和硬编码 provider。
- 后续 embedding、rerank、document parser、search、official data 都会依赖统一配置层。

R 路线完成后，再做 S/T，会更顺畅。

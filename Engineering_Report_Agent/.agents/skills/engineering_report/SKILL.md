---
name: generate-water-soil-conservation-report
description: 面向水土保持方案编制的样式驱动报告生成技能，具备人工确认触发排版机制。
tools:
  - web_search
  - execute_bash_command
outputs:
  - ./output_report.docx
---

# 📜 水土保持报告生成思考与执行 SOP

你必须严格按照以下五个阶段的流程，完成“自动构建项目上下文、检索、撰写、输出JSON、等待人类确认、运行排版”的半自动协同流水线。

开始编写前，必须先读取同目录下的 `DATA_COLLECTION_CHECKLIST.md`，按清单核对资料完备性。缺少清单中的硬核资料时，不再暂停等待用户补充材料，应继续生成缺失标注版初稿；对应章节按缺失拦截机制显式标注，不得以常识补写。

---

## 零、 自动项目上下文构建（必须优先执行）

`PROJECT_CONTEXT.md` 是自动生成文件，不再作为主要人工写入入口。执行本技能时必须先运行：

```bash
python .agents/skills/engineering_report/context_builder.py
```

如需新建项目隔离目录，可先运行：

```bash
python .agents/skills/engineering_report/project_manager.py 项目简称
```

若 `standards_templates/` 中新增或替换了报告模板 PDF，应先运行：

```bash
python .agents/skills/engineering_report/template_profile_builder.py
```

该脚本会生成 `REPORT_TEMPLATE_PROFILE.json`。若模板 PDF 为扫描件或无法抽取文字，应先 OCR 后再重新运行。

生成 `temp_report.json` 前，必须读取 `REPORT_TEMPLATE_PROFILE.json`。如该文件包含模板标题序列，`report_generator.py` 必须优先按模板标题顺序生成报告结构；不得仅按 `chapter_gates.json` 的粗粒度章节顺序生成。模板画像中的每个标题应包含 `template_instruction` 和 `requirements`，用于判断该小节需要的字段、资料分项、优先补充资料、可补充资料和内容规范。`chapter_gates.json` 仅作为兜底资料门禁和缺失项判断依据。

章节写作规范不直接硬编码在 `report_generator.py` 中。每个章节的写作目标、正文模板、应追加的缺失资料项、需要插入的表格，统一维护在同目录 `section_writing_specs.json` 中。该文件包含 `section_specs_by_number` 和 `section_specs` 两层：生成器优先按模板章节编号读取 `section_specs_by_number`，用于区分同名但不同位置的章节；标题规范仅作为兜底。调整某一章节写法时，优先修改该 JSON；`report_generator.py` 只作为执行器，负责读取项目上下文、模板标题和章节规范，渲染 `temp_report.json`。

自动构建规则：
- 脚本会扫描项目根目录、`projects/`、`standards_templates/` 及 `.agents/skills/engineering_report/knowledge/` 中的 PDF、DOCX、TXT、MD 资料。
- `projects/<项目简称>/raw/` 用于放置项目原始资料，`work/` 和 `output/` 为自动生成文件目录，扫描时会跳过。
- `standards_templates/` 用于存放长期复用的水土保持规范、标准、地方文件、报告模板和优秀样例；具体项目资料仍放项目根目录。
- 对无法直接抽取文字或文字量过少的 PDF，脚本会标记为需要 OCR，并写入 `MATERIAL_GAP_REPORT.md` 和 `PROJECT_CONTEXT_SOURCES.json`。
- 脚本会生成 `PROJECT_CONTEXT.md`、`PROJECT_CONTEXT_SOURCES.json` 和 `MATERIAL_GAP_REPORT.md`，其中包含资料源、关键字段、分项覆盖度、证据摘录、预检查状态和缺口提示。
- 如需人工修正自动抽取结果，只允许写入根目录 `PROJECT_CONTEXT_OVERRIDE.md`；脚本会在下次生成时自动附加该文件内容。
- 人工补充资料优先级最高。可写入根目录 `PROJECT_CONTEXT_OVERRIDE.md`，也可写入 `projects/<项目简称>/override/PROJECT_CONTEXT_OVERRIDE.md`；其中的字段会覆盖自动抽取字段。
- 报告正文中出现的工程量、投资、预测结果、自然概况、行政信息等数字，应优先来自自动生成的 `PROJECT_CONTEXT.md` 中带来源的字段或证据摘录。
- 若自动上下文显示某资料分项为“缺失”或“不足”，不得直接补写成品深度内容，应按缺失拦截机制处理。

### 资料不足自动续行机制（必须执行）
运行 `context_builder.py` 后，必须读取 `PROJECT_CONTEXT_SOURCES.json` 中的 `preflight` 字段：
- 无论 `preflight.blocked` 为 `true` 或 `false`，均继续进入报告撰写流程，生成缺失标注版初稿。
- 若存在 `missing_critical_sections`、`missing_required_fields`、`template_chapter_gaps` 或 `ocr_required_sources`，应在报告对应章节和末尾“待补充资料清单”中保留缺失标注。
- 不再向用户提供“继续运行/补充材料”的中断选择；资料缺口只作为报告生成深度提示和待补充清单依据。
- 若 `preflight.ocr_required_sources` 非空，即使 `preflight.blocked` 为 `false`，也应提示用户这些 PDF 需要 OCR；涉及规范或模板依据的章节不得引用未 OCR 的扫描件内容。

### 章节级资料门禁（必须执行）
进入正文生成前，必须读取 `chapter_gates.json`：
- 每个章节均有 `required_fields` 和 `required_sections`。
- 任一章节门禁不满足时，不得整章空置；应先写入已有资料能够支撑的内容，再在对应小节或段落位置输出缺失标注块。
- 对于缺少字段、缺少计算表、缺少措施工程量等内容，只跳过该具体项目，不跳过整章。
- 章节门禁结果应体现在 `temp_report.json` 中，供人工审查。
- 报告末尾必须输出“待补充资料清单”，并区分“优先补充资料”和“可补充资料”。优先补充资料用于支撑缺失章节的基本编写，可补充资料用于提高报批深度、图表完整度和评审通过率。

### 正式章节生成器
完成资料预检查后，无论资料是否完整，均优先运行：

```bash
python .agents/skills/engineering_report/report_generator.py
```

该脚本根据 `PROJECT_CONTEXT_SOURCES.json`、`chapter_gates.json` 和章节模板生成 `temp_report.json`。除非用户明确要求人工改写，否则不得绕过该生成器手写整份 `temp_report.json`。

资料不足时只需提示：已生成 `MATERIAL_GAP_REPORT.md`，本次将继续生成缺失标注版初稿；不得暂停等待用户选择。

---

## 一、 信息检索三漏斗机制（严格递进）

在撰写任何一个水保报告章节前，必须像漏斗一样层层过滤、获取数据：

### 🛑 轨道 1：自动项目上下文（最高优先级）
1. 确认已运行 `context_builder.py` 并完整读取根目录下的 `PROJECT_CONTEXT.md`。
2. 检查其中是否已经包含当前章节的核心水保硬核参数、证据摘录和资料覆盖状态。
3. **评估判定**：如果数据全面且人工结论明确，则停止检索，直接使用该硬核数据撰写专业中文技术段落。若信息有缺口，进入轨道 2。

### 🛑 轨道 2：本地局部知识库（第一兜底）
1. 提取当前章节缺少的关键字，对 `.agents/skills/engineering_report/knowledge/` 目录下的原始文件进行检索。
2. **评估判定**：结合人工资料与本地库提取的数据，若信息已足够支撑写出深度水保技术段落，则停止检索。若缺少通用规范、新材料行业标准、或最新的国家/地方强制条文，进入轨道 3。

### 🛑 轨道 3：全局联网搜索（终极拦截）
1. 提取依然缺失的内容核心（如：最新的水土流失防治标准编号等）。
2. **⚠️ 强力拦截要求**：在调用 `web_search` 工具前，必须立即暂停自动化流水线，在终端/聊天界面输出以下精确提示语，等待用户输入：
   > ⚠️ **Agent提示**：正在编写 [具体章节名称]，本地水保资料不足。我计划联网检索关键词：`[拟检索的关键词]`，是否允许？(Y/N)
3. **根据用户反馈执行**：
   - 用户输入 **Y / yes**：使用 `web_search` 检索权威行业网站或国家标准系统。
   - 用户输入 **N / no**：放弃联网，直接进入下方的【缺失拦截机制】。

---

## 二、 严格撰写铁律与缺失拦截机制

在文本合成阶段，你必须像一个严谨的注册水保工程师一样对待数据，坚决执行以下三条底线：

### 1. 严格内容对齐（无据不写）
- 报告中出现的每一个数字（占地、土石方、投资额、流失量）必须在 `PROJECT_CONTEXT.md` 或本地知识库中拥有唯一且绝对精确的文本依据。
- 严禁基于模糊常识推理编写数据，严禁为了迎合段落完整性而私自编造任何技术指标。

### 2. 严禁 AI 废话与套话（零容忍）
- 坚决过滤无实质工程意义的宏观政治套话与文学修辞。
- 严禁出现诸如：“本项目将积极响应生态文明建设，因地制宜构建绿色矩阵，为城市高质量发展赋能注入新活力，勾勒人与自然和谐共生的美丽画卷……”等典型 AI 腔调。

### 3. 核心：资料缺失时“标注后跳过”
如果在历经三个轨道的检索后，当前章节或某项图表所需的关键数据/编制依据依然缺失，你必须执行以下操作：
- **停止编造**：立刻停止对该章节后续所有正文内容的撰写。
- **显性标注**：在 `blocks` 列表中，为该章节仅输出一个特殊的文本块，格式固定为：
  {"type": "text", "style": "正文", "text": "【❌ 本节因本地原始资料及人工上下文缺失相关硬核数据，智能体自动跳过，请人工核对后在此补全具体内容。】", "source": "normal"}
- **直接移交**：写完这个特殊标注块后，直接跳过本节，开始评估和撰写下一个章节。

---

## 三、 扁平化数据结构化输出规范（Style-Driven）

完成各章节内容的思考与融合后，将整篇报告解构为一维的扁平列表（`blocks`），严格对应用户在 Word 中预设好的中文样式名称。最终生成并保存在项目根目录下的 `temp_report.json`。

### 样式映射字典
- 章级大标题 -> "style": "标题一"
- 节级标题 -> "style": "标题二"
- 子节级标题 -> "style": "标题三"
- 具体措施/细分标题 -> "style": "标题四"
- 普通技术正文段落 -> "style": "正文"
- 表格上方的标题 -> "style": "表名"
- 图片下方的标题 -> "style": "图名"
- 结构化表格数据 -> 设置 "type": "table"

### 标题编号约束（必须执行）
- Word 模板中的“标题一、标题二、标题三、标题四”样式已绑定多级列表自动编号。
- 所有标题块的 `text` 字段只写标题名称，不得手工添加 `1`、`1.1`、`1.1.1`、`一、`、`（一）` 等章节编号。
- 正确示例：`{"type": "text", "style": "标题一", "text": "综合说明"}`。
- 错误示例：`{"type": "text", "style": "标题一", "text": "1 综合说明"}`。
- 表名、图名如需编号，应按模板或人工审定规则处理；不得与标题多级列表编号混用。

---

## 四、 人工交互确认与排版脚本触发（Human-in-the-Loop）

当 `temp_report.json` 成功输出并在磁盘上生成完毕后，你必须立刻暂停一切后续动作，在聊天界面向人类发出显式确认请求：

### 1. 弹出人工会签请求
在界面中一字不差地输出以下提示语：
> 📁 **Agent提示**：中间数据 `temp_report.json` 已写入完毕并关闭。
> 🚀 **请您确认该文件未被占用或已保存，并在此回复 "Y"** 允许我开始调用 Word 样式排版引擎。

### 2. 等待人工授权
- 严禁私自提前运行任何终端命令。
- 当且仅当用户在聊天框中回复 "Y" 或 "yes" 时，无缝调用 `execute_bash_command` 工具在本地终端静默运行以下最终排版命令：

```bash
python .agents/skills/engineering_report/docx_builder.py
3. 结果交付
监控排版脚本返回代码。若返回 exit code 0，在聊天界面向用户汇报：
>🎉 最终成品 Word 已自动生成在：./output_report.docx
>🔍 联网参考段落已自动染成深蓝色，缺失资料已自动加粗标红跳过，请直接打开审阅！

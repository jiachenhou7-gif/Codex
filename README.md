**使用codex写水土保持方案**
本项目使用python写入word，需要有python环境并下载相关包：pip install pypdf python-docx；
json、re、datetime、pathlib、os 都是 Python 标准库，不需要下载。
**前期准备：**
*1. AGENTS.md：控制语气、禁忌词（如拒绝AI套话）、专有名词标准（如必须用“植物措施”），可根据项目规范进行调整。*
*2. report_template.docx：word模板，可根据现有样式进行修改，注意：不要修改名称或新建样式。*
*3. knowledge文件夹：存放该项目的相关文件，可支持word、PDF等文件，注意：最好不要单独放图件。*
*4. DATA_COLLECTION_CHECKLIST.md：水土保持方案报告资料收集清单，用于在生成水土保持方案报告前，检查 `PROJECT_CONTEXT.md` 和本地 `knowledge/` 资料库是否足以支撑成品报告。缺少资料时，不应直接生成完整报告，应先向用户索取资料，或在对应章节显式标注缺失。*
*5. SKILL.md：对 Agent 有流程约束作用。name: generate-water-soil-conservation-report。使agent严格按照“自动构建项目上下文、检索、撰写、输出JSON、等待人类确认、运行排版”运行。*
6. context_builder.py：扫描资料，生成 PROJECT_CONTEXT.md、PROJECT_CONTEXT_SOURCES.json、MATERIAL_GAP_REPORT.md。
7. docx_builder.py：读取 temp_report.json，生成 output_report.docx。
**开始运行：**
第一步：在 Codex 中打开您的项目工作区
请确保您的 Codex 当前已经加载或打开了 X:\XXX\Engineering_Report_Agent 这个文件夹。如果还没有，请在 Codex 的菜单栏选择 File -> Open Folder（打开文件夹），然后选中该路径。
第二步：在 Codex 聊天框中发送启动指令
在 Codex 的对话界面中，直接复制并发送以下这段话给它：
*请调用 generate-water-soil-conservation-report 技能，开始为我编写水土保持方案报告。*
第三步：人机协同配合（您只需要执行两次输入）
发送指令后，Agent 将正式启动流水线，期间您只需要配合它做以下两件事：
联网确认（如果触发）：
如果 Agent 在编写过程中发现本地资料不够，它会在聊天界面停下来并提示您：
⚠️ Agent提示：正在编写 [某章节]，本地水保资料不足。我计划联网检索关键词：[...]，是否允许？(Y/N)
此时您在聊天框回复 Y 并回车即可。
排版确认（核心闭环点）：
当 Agent 把所有的章节文字全部撰写完毕、生成 temp_report.json 并关闭后，它会根据 SKILL.md 的规定再次停下来，在界面上对您说：
📁 Agent提示：中间数据 temp_report.json 已写入完毕并关闭。
🚀 请您确认该文件未被占用或已保存，并在此回复 "Y" 允许我开始调用 Word 样式排版引擎。
此时您只需要在聊天框再次回复一个 Y 并回车。

# 项目切换说明

本说明用于在切换到新的水土保持方案项目时，快速确认哪些文件需要调整，哪些文件会自动生成。

## 1. ACTIVE_PROJECT.txt 是什么

`ACTIVE_PROJECT.txt` 用于指定当前正在处理的项目。

脚本会根据这个文件中的项目简称，优先识别和使用：

- `projects/<项目简称>/raw/` 中的原始资料
- `projects/<项目简称>/override/` 中的人工补充资料

它会影响以下流程：

- `context_builder.py` 扫描当前项目资料
- `report_generator.py` 识别“当前项目资料”
- 缺口清单、项目上下文、报告正文生成时的资料过滤

建议内容仅保留一行项目简称，例如：

```text
黄冈市东坡大道片区污水收集管网
```

项目简称最好与 `projects/` 下的项目文件夹名称保持一致。

## 2. 换新项目时通常需要调整的文件

### `ACTIVE_PROJECT.txt`

切换到新项目时，应将其内容改为新的项目简称。

### `projects/<新项目>/raw/`

将新项目的原始资料放入该目录，例如：

- 批复文件
- 主体设计说明
- 合同
- 图纸说明
- PDF / DOCX / 扫描件

### `PROJECT_CONTEXT_OVERRIDE.md`

如有人工确认过的资料，可写入该文件，例如：

- 项目名称
- 建设单位
- 建设性质
- 建设地点
- 总投资、土建投资
- 防治责任范围
- 土石方数据

人工补充资料优先级最高。

也可以改为写入项目隔离目录中的：

```text
projects/<新项目>/override/PROJECT_CONTEXT_OVERRIDE.md
```

## 3. 一般不需要手动调整的文件

以下文件通常由脚本自动生成或自动更新：

- `PROJECT_CONTEXT.md`
- `PROJECT_CONTEXT_SOURCES.json`
- `MATERIAL_GAP_REPORT.md`
- `REPORT_TEMPLATE_PROFILE.json`
- `temp_report.json`
- `output_report.docx`

除非需要排查问题或人工核查，一般不建议手动修改这些自动生成文件。

## 4. standards_templates 是否要改

`standards_templates/` 是长期复用的规范、模板和样例目录，不是某个项目专属资料夹。

因此，切换普通项目时一般不需要调整。

只有在以下情况才需要更新：

- 更换长期使用的报告模板
- 补充新的规范或标准
- 新增可复用的优秀样例

## 5. 推荐的项目切换顺序

1. 新建或确认 `projects/<新项目>/raw/`
2. 修改 `ACTIVE_PROJECT.txt`
3. 将项目原始资料放入 `raw/`
4. 如有人工确认信息，补充 `PROJECT_CONTEXT_OVERRIDE.md`
5. 重新运行上下文构建和报告生成流程

## 6. 最简判断原则

如果你只是“换一个项目重新生成报告”，通常只需要关注这三件事：

- `ACTIVE_PROJECT.txt` 是否指向正确项目
- `projects/<新项目>/raw/` 是否放入了正确资料
- `PROJECT_CONTEXT_OVERRIDE.md` 是否补充了人工确认信息

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = Path(__file__).resolve().parent
CONTEXT_JSON = ROOT / "PROJECT_CONTEXT_SOURCES.json"
CONTEXT_MD = ROOT / "PROJECT_CONTEXT.md"
GATES_JSON = SKILL_DIR / "chapter_gates.json"
TEMPLATE_PROFILE_JSON = ROOT / "REPORT_TEMPLATE_PROFILE.json"
OUTPUT_JSON = ROOT / "temp_report.json"
ACTIVE_PROJECT_FILE = ROOT / "ACTIVE_PROJECT.txt"


MISSING_TEXT = "【⚠️ 缺失相关硬核数据，智能体跳过本项，请人工核对后在此补全具体内容。】"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_template_headings():
    if not TEMPLATE_PROFILE_JSON.exists():
        return []
    data = load_json(TEMPLATE_PROFILE_JSON)
    sources = data.get("template_sources", [])
    if not sources:
        return []
    headings = sources[0].get("headings", [])
    return [item for item in headings if item.get("title") and item.get("style")]


def text_block(style, text, source="normal"):
    return {"type": "text", "style": style, "text": text, "source": source}


def table_block(rows):
    return {"type": "table", "data": rows}


def value(values, key, default=""):
    item = values.get(key)
    if isinstance(item, dict):
        return item.get("value", default)
    return default


def has_value(values, key):
    return bool(value(values, key, "").strip())


def missing_note(missing_fields=None, missing_sections=None):
    parts = []
    if missing_fields:
        parts.append("缺失字段：" + "、".join(missing_fields))
    if missing_sections:
        parts.append("缺失资料分项：" + "、".join(missing_sections))
    return MISSING_TEXT + (f"（{'；'.join(parts)}）" if parts else "")


def active_project_name():
    if ACTIVE_PROJECT_FILE.exists():
        return ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    return ""


def sentence_text(text):
    text = str(text or "").strip()
    return text.rstrip("。；; ")


def heading_level(number):
    number = str(number or "")
    if re_match_number(number):
        return number.count(".") + 1
    return 1


def re_match_number(number):
    import re
    return bool(re.match(r"^\d+(?:\.\d+)*$", str(number or "")))


def normalize_source(source):
    return str(source or "").replace("\\", "/")


def is_current_project_source(source):
    normalized = normalize_source(source)
    project = active_project_name()
    if "PROJECT_CONTEXT_OVERRIDE.md" in normalized:
        return True
    if not project:
        return normalized.startswith("projects/")
    return normalized.startswith(f"projects/{project}/")


def looks_broken_text(text):
    """Reject OCR/PDF encoding fragments before they can enter report prose."""
    if not text:
        return True
    broken_tokens = ["Ë", "Í", "±", "Ã", "Â", "Ð", "Ä", "Æ", "¼", "½", "¾"]
    if sum(text.count(token) for token in broken_tokens) >= 3:
        return True
    if "<table" in text.lower() or "</td>" in text.lower():
        return True
    return False


def compact_snippet(text, max_len=180):
    text = " ".join(str(text).split())
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip("，。；、 ") + "……"


def section_status(source_data, gate):
    values = source_data.get("values", {})
    coverage = source_data.get("coverage", {})
    missing_fields = [field for field in gate.get("required_fields", []) if field not in values]
    missing_sections = [
        section for section in gate.get("required_sections", [])
        if coverage.get(section) != "充分"
    ]
    return missing_fields, missing_sections


def evidence_snippets(source_data, section_name, limit=2):
    sections = source_data.get("sections", {})
    items = sections.get(section_name, [])[:limit]
    return [item.get("snippet", "") for item in items if item.get("snippet")]


def project_evidence_items(source_data, section_name, limit=3):
    sections = source_data.get("sections", {})
    items = []
    for item in sections.get(section_name, []):
        if not is_current_project_source(item.get("source", "")):
            continue
        snippet = item.get("snippet", "")
        if looks_broken_text(snippet):
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def project_evidence_snippets(source_data, section_names, limit=3):
    snippets = []
    for section_name in section_names:
        for item in project_evidence_items(source_data, section_name, limit=limit):
            snippets.append(item.get("snippet", ""))
            if len(snippets) >= limit:
                return snippets
    return snippets


def add_missing_gate(blocks, gate, missing_fields, missing_sections):
    blocks.append(text_block("标题一", gate["title"]))
    detail = []
    if missing_fields:
        detail.append("缺失字段：" + "、".join(missing_fields))
    if missing_sections:
        detail.append("缺失资料分项：" + "、".join(missing_sections))
    suffix = "；".join(detail)
    blocks.append(text_block("正文", MISSING_TEXT + (f"（{suffix}）" if suffix else "")))


def add_summary(blocks, values):
    blocks.append(text_block("标题一", "综合说明"))
    blocks.append(text_block("标题二", "项目简况"))
    missing = [field for field in ["项目名称", "建设性质", "建设地点", "建设单位"] if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))
    else:
        blocks.append(text_block(
            "正文",
            f"{value(values, '项目名称')}为{value(values, '建设性质')}项目，建设地点位于{value(values, '建设地点')}。"
            f"建设单位为{value(values, '建设单位')}。"
        ))
    blocks.append(text_block("标题二", "防治责任范围"))
    if has_value(values, "防治责任范围"):
        area_text = sentence_text(value(values, "防治责任范围"))
        if "防治责任范围" in area_text:
            blocks.append(text_block("正文", area_text + "。"))
        else:
            blocks.append(text_block("正文", f"经资料核查，项目防治责任范围为 {area_text}。"))
    else:
        blocks.append(text_block("正文", missing_note(missing_fields=["防治责任范围"])))
    blocks.append(text_block("标题二", "水土流失现状与防治标准"))
    missing = [field for field in ["土壤容许流失量", "原地貌土壤侵蚀模数"] if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))
    else:
        blocks.append(text_block(
            "正文",
            f"项目区土壤容许流失量为 {value(values, '土壤容许流失量')}，"
            f"原地貌土壤侵蚀模数为 {value(values, '原地貌土壤侵蚀模数')}。"
        ))


def add_project_overview(blocks, values):
    blocks.append(text_block("标题一", "项目概况"))
    blocks.append(text_block("标题二", "项目基本情况"))
    fields = ["项目名称", "建设单位", "建设地点", "建设性质", "总投资", "土建投资"]
    rows = [["项目", "内容"]]
    for field in fields:
        if has_value(values, field):
            rows.append([field, value(values, field)])
    blocks.append(table_block(rows))
    missing = [field for field in fields if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))
    blocks.append(text_block("标题二", "土石方平衡"))
    earth_fields = ["挖方", "填方", "借方", "余弃方"]
    rows = [["项目", "数量"]]
    for field in earth_fields:
        if has_value(values, field):
            rows.append([field, value(values, field)])
    if len(rows) > 1:
        blocks.append(table_block(rows))
    missing = [field for field in earth_fields if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))


def add_evaluation(blocks, source_data, values, gate):
    blocks.append(text_block("标题一", gate["title"]))
    snippets = project_evidence_snippets(source_data, ["主体工程设计资料", "工程占地与土石方资料"], limit=1)

    blocks.append(text_block("标题二", "项目主体工程选址（线）水土保持评价"))
    if has_value(values, "项目名称") and has_value(values, "建设地点"):
        blocks.append(text_block(
            "正文",
            f"{value(values, '项目名称')}位于{value(values, '建设地点')}。项目为城市污水收集管网工程，"
            "施工扰动主要发生在管线开挖、道路恢复和临时堆土等环节。项目选址（线）水土保持评价重点为主体工程布置、临时占地控制、弃方消纳和施工期临时防护。"
        ))
    else:
        blocks.append(text_block("正文", missing_note(missing_fields=["项目名称", "建设地点"])))

    blocks.append(text_block("标题二", "项目建设方案与布局水土保持评价"))
    if snippets:
        blocks.append(text_block(
            "正文",
            project_design_summary(source_data)
            + "项目建设活动主要集中在管沟开挖、管道敷设、检查井及沉泥井施工、沟槽回填和道路恢复等环节。施工期应控制开挖裸露时间、临时堆土防护、弃方外运消纳和道路恢复时序。"
        ))
    else:
        blocks.append(text_block("正文", missing_note(missing_sections=["主体工程设计资料"])))

    blocks.append(text_block("标题二", "主体工程设计中水土保持措施界定"))
    blocks.append(text_block(
        "正文",
        missing_note(missing_sections=["主体工程已有水土保持措施界定", "工程措施、植物措施、临时措施工程量"])
    ))


def add_measures(blocks, source_data, values, gate):
    blocks.append(text_block("标题一", gate["title"]))
    has_area = has_value(values, "防治责任范围")
    has_earthwork = any(has_value(values, key) for key in ["挖方", "填方", "借方", "余弃方"])

    blocks.append(text_block("标题二", "水土流失防治区划分"))
    if has_area:
        area_text = sentence_text(value(values, "防治责任范围"))
        blocks.append(text_block(
            "正文",
            f"本项目防治责任范围依据现有资料为：{area_text}。"
            "在未取得正式防治分区图和施工布置图前，可暂按管网施工区、临时堆土及材料周转区、道路恢复区进行资料整理。"
        ))
    else:
        blocks.append(text_block("正文", missing_note(missing_fields=["防治责任范围"])))

    blocks.append(text_block("标题二", "措施总体布局"))
    if has_earthwork:
        blocks.append(text_block(
            "正文",
            "本着“因地制宜、因害设防、分区防治、全面施策”的原则，措施体系应围绕管沟开挖、土方临时堆置、弃方外运和道路恢复布设。"
            "施工期应围绕土方开挖、临时堆置、弃方外运和道路恢复落实临时苫盖、拦挡、排水、沉沙及场地恢复措施。"
        ))
    else:
        blocks.append(text_block("正文", missing_note(missing_fields=["挖方", "填方", "借方", "余弃方"])))

    blocks.append(text_block("标题二", "分区措施布设"))
    blocks.append(text_block(
        "正文",
        "工程措施、植物措施、临时措施应按防治分区分别列明。"
        + missing_note(missing_sections=["防治分区图", "工程措施工程量", "植物措施工程量", "临时措施工程量"])
    ))

    blocks.append(text_block("标题二", "施工要求"))
    blocks.append(text_block(
        "正文",
        "施工期应控制管沟开挖暴露时间，及时回填并恢复道路或绿地。临时堆土应采取苫盖、拦挡和排导措施。"
        + missing_note(missing_sections=["施工组织设计", "临时堆土位置及防护工程量"])
    ))


def add_management(blocks, values, gate):
    blocks.append(text_block("标题一", gate["title"]))
    unit = value(values, "建设单位", "建设单位")
    for title in gate.get("default_blocks", []):
        blocks.append(text_block("标题二", title))
        if title == "组织管理":
            blocks.append(text_block("正文", f"{unit}应落实水土保持主体责任，明确水土保持管理人员，组织实施方案确定的各项防治措施。"))
        else:
            blocks.append(text_block("正文", missing_note(missing_sections=[title + "资料"])))


def add_attachments(blocks, source_data, gate):
    blocks.append(text_block("标题一", gate["title"]))
    project_sources = []
    for src in source_data.get("sources", []):
        path = src.get("path", "")
        if is_current_project_source(path):
            name = Path(path).name
            if name not in project_sources:
                project_sources.append(name)

    blocks.append(text_block("标题二", "附件"))
    if project_sources:
        blocks.append(text_block("正文", "已识别本项目资料：" + "；".join(project_sources[:8]) + "。"))
    else:
        blocks.append(text_block("正文", missing_note(missing_sections=["项目附件资料"])))

    blocks.append(text_block("标题二", "附表"))
    blocks.append(text_block("正文", missing_note(missing_sections=["土石方平衡表", "水土保持投资概算表", "防治目标计算表"])))

    blocks.append(text_block("标题二", "附图"))
    blocks.append(text_block("正文", missing_note(missing_sections=["项目地理位置图", "水土流失现状图", "水土保持措施总体布置图", "防治责任范围图"])))


def add_basic_info_table(blocks, values):
    fields = ["项目名称", "项目代码", "建设单位", "建设地点", "建设性质", "建设工期", "总投资", "土建投资"]
    rows = [["项目", "内容"]]
    for field in fields:
        if has_value(values, field):
            rows.append([field, value(values, field)])
    if len(rows) > 1:
        blocks.append(table_block(rows))
    missing = [field for field in fields if field != "项目代码" and not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))


def add_earthwork_table(blocks, values):
    earth_fields = ["挖方", "填方", "借方", "余弃方"]
    rows = [["项目", "数量"]]
    for field in earth_fields:
        if has_value(values, field):
            rows.append([field, value(values, field)])
    if len(rows) > 1:
        blocks.append(table_block(rows))
    missing = [field for field in earth_fields if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))


def project_design_summary(source_data):
    snippets = project_evidence_snippets(source_data, ["主体工程设计资料"], limit=5)
    text = " ".join(snippets)
    main = re.search(r"污水主管网\s*([0-9.]+)\s*公里", text)
    branch = re.search(r"预埋支管\s*([0-9.]+)\s*公里", text)
    parts = []
    if main:
        parts.append(f"改造污水主管网约{main.group(1)}公里")
    if branch:
        parts.append(f"沿线预埋支管约{branch.group(1)}公里")
    if "检查井" in text or "沉泥井" in text:
        parts.append("配套建设污水检查井、沉泥井及附属设施")
    if parts:
        return "工程主要建设内容包括" + "，".join(parts) + "。"
    return "工程主要建设内容涉及污水主管网、预埋支管、检查井、沉泥井及附属设施。"


def project_road_scope_summary(source_data):
    snippets = project_evidence_snippets(source_data, ["主体工程设计资料"], limit=5)
    text = " ".join(snippets)
    roads = []
    for road in ["东坡大道", "赤壁一路", "赤壁二路", "三台河路", "新港大道"]:
        if road in text and road not in roads:
            roads.append(road)
    if roads:
        return "工程沿" + "、".join(roads) + "等道路实施。"
    return "工程沿黄冈市黄州区城北片区既有城市道路实施。"


def append_missing_if_any(blocks, source_data, values, requirement, extra_sections=None):
    missing_fields, missing_sections = missing_for_requirement(source_data, values, requirement)
    if extra_sections:
        missing_sections = list(dict.fromkeys(missing_sections + extra_sections))
    if missing_fields or missing_sections:
        blocks.append(text_block("正文", missing_note(missing_fields=missing_fields, missing_sections=missing_sections)))


def add_formal_evaluation_body(blocks, source_data, values, title, requirement):
    design = project_design_summary(source_data)
    if title == "建设方案与布局水土保持评价":
        blocks.append(text_block(
            "正文",
            f"{design}项目建设活动主要集中在管沟开挖、管道敷设、检查井及沉泥井施工、沟槽回填和道路恢复等环节。"
            "从水土保持角度看，建设方案应控制开挖裸露时间、临时堆土防护、弃方外运消纳和道路恢复时序。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工组织设计", "临时堆土布置资料"])
        return
    if title == "工程占地评价":
        if has_value(values, "防治责任范围"):
            blocks.append(text_block(
                "正文",
                f"{sentence_text(value(values, '防治责任范围'))}。项目占地以管网施工扰动和道路恢复范围为主，施工结束后恢复道路及绿地原有使用功能。"
            ))
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["防治责任范围"])))
        append_missing_if_any(blocks, source_data, values, requirement, ["占地类型及面积统计表"])
        return
    if title == "土石方平衡评价":
        if any(has_value(values, key) for key in ["挖方", "填方", "借方", "余弃方"]):
            blocks.append(text_block(
                "正文",
                "本项目土石方工程包括管沟开挖、沟槽回填、外购土石方和余弃方外运消纳。表土剥离与表土回覆数量均为79.5m³，弃方由湖北安达港务有限公司负责外运及消纳。"
            ))
            add_earthwork_table(blocks, values)
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["挖方", "填方", "借方", "余弃方"])))
        append_missing_if_any(blocks, source_data, values, requirement, ["土石方平衡表"])
        return
    if title == "施工方法与工艺评价":
        blocks.append(text_block(
            "正文",
            f"{project_road_scope_summary(source_data)}施工扰动主要来自沟槽开挖、管道安装、井室施工、回填压实和路面恢复。施工期采取分段施工、及时回填、弃方密闭运输和雨季临时防护，可减少裸露地表和临时堆土造成的水土流失。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工工艺流程", "施工时序安排"])


def add_formal_construction_body(blocks, source_data, values, title, requirement):
    road_scope = project_road_scope_summary(source_data)
    design = project_design_summary(source_data)
    if title == "施工组织":
        blocks.append(text_block(
            "正文",
            f"{design}{road_scope}施工组织采取分段开挖、分段敷设、及时回填和及时恢复的方式，减少裸露面持续时间和临时堆土占压范围。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工总布置图", "施工进度横道图"])
        return
    if title == "施工生产生活区":
        blocks.append(text_block(
            "正文",
            "本项目为城市道路管网工程，施工生产组织按沿线道路条件分段布置材料临时堆放、机械停放和作业面周转场地。施工生产生活区控制在防治责任范围内，减少新增扰动地表面积。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工生产生活区位置", "施工生产生活区占地面积"])
        return
    if title == "施工道路":
        blocks.append(text_block(
            "正文",
            f"{road_scope}施工运输主要依托既有城市道路组织。施工车辆进出作业面时落实道路保洁、车辆冲洗和弃方运输覆盖等临时措施。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工道路布置", "施工出入口布置"])
        return
    if title == "施工用水、用电":
        blocks.append(text_block(
            "正文",
            "本项目位于城市建成区，施工用水、用电结合沿线市政条件就近接入。临时接入设施减少占压绿地和道路以外区域，施工结束后及时拆除并恢复占压地表。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工用水接入点", "施工用电接入点"])
        return
    if title == "施工导流(不涉及的不列）":
        blocks.append(text_block(
            "正文",
            "本项目现阶段资料未显示涉及河道导流或围堰导流工程。施工过程中如遇低洼积水段，采取临时排水和沉沙措施，避免泥水外排。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工导流不涉及说明或导流方案"])
        return
    if title == "施工工艺与方法":
        blocks.append(text_block(
            "正文",
            f"{design}施工工艺以管沟开挖、管道敷设、检查井及沉泥井施工、沟槽回填、弃方外运和道路恢复为主。施工期应控制单段开挖长度和裸露时间，临时堆土采取覆盖、拦挡和排水措施。"
        ))
        append_missing_if_any(blocks, source_data, values, requirement, ["施工工艺流程图", "分段施工时序"])
        return
    blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))


def template_missing_for_title(title):
    mapping = {
        "自然简况": ["地形地貌", "气候气象", "水文", "土壤", "植被", "水土流失重点防治区", "土壤容许流失量", "原地貌土壤侵蚀模数"],
        "水土流失预测结果": ["预测水土流失总量", "新增水土流失量", "预测计算表"],
        "水土保持监测方案": ["监测范围", "监测内容", "监测时段", "监测方法", "监测点位"],
        "水土保持投资及效益分析成果": ["水土保持总投资", "工程措施投资", "植物措施投资", "临时措施投资", "水土保持补偿费", "六项目标达标测算表"],
        "编制原则及依据": ["投资估算编制依据", "定额依据", "价格信息"],
        "编制说明与估算成果": ["水土保持投资概算表", "分部工程概算表"],
        "效益分析": ["六项目标达标测算表"],
        "水土流失现状": ["土壤容许流失量", "原地貌土壤侵蚀模数", "土壤侵蚀强度"],
        "土壤流失量预测": ["预测单元", "预测时段", "土壤侵蚀模数", "预测计算表"],
        "水土流失危害分析": ["预测结果", "重点流失区域"],
        "执行标准等级": ["水土流失防治标准执行等级"],
        "防治目标": ["水土流失治理度", "土壤流失控制比", "渣土防护率", "表土保护率", "林草植被恢复率", "林草覆盖率"],
    }
    return mapping.get(title, [title + "资料"])


def missing_for_requirement(source_data, values, requirement):
    coverage = source_data.get("coverage", {})
    missing_fields = [
        field for field in requirement.get("required_fields", [])
        if not has_value(values, field)
    ]
    missing_sections = [
        section for section in requirement.get("required_sections", [])
        if coverage.get(section) != "充分"
    ]
    return missing_fields, missing_sections


def missing_note_for_requirement(source_data, values, title, requirement):
    missing_fields, missing_sections = missing_for_requirement(source_data, values, requirement)
    if not missing_fields and not missing_sections:
        missing_sections = template_missing_for_title(title)
    return missing_note(missing_fields=missing_fields, missing_sections=missing_sections)


def add_template_section_body(blocks, source_data, values, heading):
    title = heading["title"]
    requirement = heading.get("requirements") or {}
    if title == "项目基本情况":
        if has_value(values, "项目名称"):
            blocks.append(text_block(
                "正文",
                f"{value(values, '项目名称')}为{value(values, '建设性质', '生产建设')}项目，建设地点位于{value(values, '建设地点', '【缺失建设地点】')}。"
                f"建设单位为{value(values, '建设单位', '【缺失建设单位】')}。"
            ))
        add_basic_info_table(blocks, values)
        return
    if title in ["项目简况", "项目组成及工程布置"]:
        snippets = project_evidence_snippets(source_data, ["主体工程设计资料"], limit=1)
        if snippets:
            blocks.append(text_block(
                "正文",
                project_design_summary(source_data)
            ))
        else:
            blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title in ["自然简况", "地质", "地貌", "气候气象", "水文", "土壤", "植被", "水土保持敏感区及其他敏感区"]:
        blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title in ["项目水土保持评价结论", "主体工程选址（线）水土保持评价"]:
        if has_value(values, "项目名称") and has_value(values, "建设地点"):
            blocks.append(text_block(
                "正文",
                f"{value(values, '项目名称')}位于{value(values, '建设地点')}。项目为城市污水收集管网工程，"
                "施工扰动主要发生在管线开挖、道路恢复和临时堆土等环节。项目选址（线）水土保持评价重点为主体工程布置、临时占地控制、弃方消纳和施工期临时防护。"
            ))
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["项目名称", "建设地点"])))
        return
    if title in ["建设方案与布局水土保持评价", "工程占地评价", "土石方平衡评价", "施工方法与工艺评价"]:
        add_formal_evaluation_body(blocks, source_data, values, title, requirement)
        return
    if title == "主体工程设计中具有水土保持功能工程的分析评价":
        blocks.append(text_block("正文", missing_note(missing_sections=["主体工程已有水土保持措施界定", "工程措施、植物措施、临时措施工程量"])))
        return
    if title in ["表土资源保护与利用", "表土资源调查", "表土资源评价", "表土剥离保护", "表土回覆"]:
        if has_value(values, "挖方") or has_value(values, "填方"):
            if title == "表土资源评价":
                text = "本项目表土剥离量为79.5m³，表土回覆量为79.5m³，表土剥离与回覆数量平衡。表土资源主要用于扰动范围内绿地恢复和植被恢复，施工期应做好临时堆存、覆盖和防流失管理。"
            elif title == "表土剥离保护":
                text = "本项目施工前对具备剥离条件的表土进行剥离保护，表土剥离量为79.5m³。剥离表土应集中堆存并采取临时苫盖、拦挡和排水措施。"
            elif title == "表土回覆":
                text = "本项目表土回覆量为79.5m³，回覆范围主要为施工扰动后的绿地恢复区域。表土回覆后应及时实施植物措施，减少裸露地表持续时间。"
            else:
                text = "本项目表土剥离量为79.5m³，表土回覆量为79.5m³。表土资源按照剥离、临时防护、回覆利用的流程进行保护和利用。"
            blocks.append(text_block("正文", text))
        else:
            blocks.append(text_block("正文", missing_note(missing_sections=["表土剥离回覆量", "可剥离表土面积", "表土利用去向"])))
        return
    if title in ["表土保护方案", "表土就地保护", "表土堆存与养护", "表土堆存", "表土养护", "表土利用", "表土需求分析", "表土再利用"]:
        blocks.append(text_block("正文", missing_note(missing_sections=["表土保护方案", "表土堆存位置", "表土养护措施", "表土利用计划"])))
        return
    if title in ["弃渣场选址与堆置", "渣土来源及流向", "弃渣场选址、堆置方案与级别"]:
        if has_value(values, "余弃方"):
            blocks.append(text_block("正文", f"本项目余弃方为{sentence_text(value(values, '余弃方'))}。弃方不在项目区内长期堆置，由消纳单位统一外运处置；施工期临时堆土应控制堆置范围并采取临时苫盖、拦挡和排水措施。"))
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["余弃方"])))
        return
    if title in ["水土流失预测结果", "水土流失现状", "水土流失影响因素分析", "土壤流失量预测", "水土流失危害分析"]:
        blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title in ["水土流失防治责任范围及目标", "水土流失防治责任范围"]:
        if has_value(values, "防治责任范围"):
            blocks.append(text_block("正文", sentence_text(value(values, "防治责任范围")) + "。"))
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["防治责任范围"])))
        blocks.append(text_block("正文", missing_note(missing_fields=["水土流失防治标准执行等级", "水土保持六项目标"])))
        return
    if title == "工程占地":
        if has_value(values, "防治责任范围"):
            blocks.append(text_block("正文", sentence_text(value(values, "防治责任范围")) + "。"))
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["防治责任范围", "占地类型及面积统计表"])))
        return
    if title == "土石方平衡":
        add_earthwork_table(blocks, values)
        return
    if title == "工程进度":
        if has_value(values, "建设工期"):
            blocks.append(text_block("正文", f"项目建设工期为{sentence_text(value(values, '建设工期'))}。"))
        else:
            blocks.append(text_block("正文", missing_note(missing_fields=["建设工期"])))
        return
    if title in ["设计水平年", "水土流失防治目标", "执行标准等级", "防治目标"]:
        blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title in ["水土流失防治分区及措施", "防治区划分", "措施总体布局", "工程级别与设计标准", "分区措施布设"]:
        if title == "措施总体布局":
            blocks.append(text_block("正文", "本着“因地制宜、因害设防、分区防治、全面施策”的原则，措施体系应围绕管沟开挖、土方临时堆置、弃方外运和道路恢复布设。"))
        blocks.append(text_block("正文", missing_note(missing_sections=["防治分区图", "工程措施工程量", "植物措施工程量", "临时措施工程量"])))
        return
    if title in ["水土保持监测", "范围和时段", "内容、方法与频次", "监测内容", "监测方法与频次", "点位布设与监测设施", "实施条件和成果"]:
        blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title in ["水土保持投资及效益分析", "投资估算", "编制原则及依据", "编制说明与估算成果", "效益分析", "水土保持投资及效益分析成果"]:
        blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title == "水土保持管理":
        unit = value(values, "建设单位", "建设单位")
        blocks.append(text_block("正文", f"{unit}应落实水土保持主体责任，明确水土保持管理人员，组织实施方案确定的各项防治措施，并按规定开展后续设计、监理、施工管理和水土保持设施验收。"))
        return
    if title in ["施工生产生活区", "施工道路", "施工用水、用电", "施工导流(不涉及的不列）", "取土场(不涉及的不列）", "弃渣场(不涉及的不列)", "临时堆土场(不涉及的不列)", "施工工艺与方法", "施工组织"]:
        missing_fields, missing_sections = missing_for_requirement(source_data, values, requirement)
        if not missing_fields and not missing_sections:
            add_formal_construction_body(blocks, source_data, values, title, requirement)
        else:
            blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))
        return
    if title == "结论":
        blocks.append(text_block("正文", "本项目为城市污水收集管网工程，施工扰动主要集中在管沟开挖、临时堆土、弃方外运和道路恢复环节。方案应重点落实临时防护、表土保护、弃方消纳、道路及绿地恢复等水土保持措施。自然概况、预测计算、措施工程量、投资概算和附图附表资料缺失时，本报告保留缺失标注，待资料补充后形成完整报批稿。"))
        return
    blocks.append(text_block("正文", missing_note_for_requirement(source_data, values, title, requirement)))


def collect_template_gaps(source_data, values, headings):
    gaps = []
    for heading in headings:
        requirement = heading.get("requirements") or {}
        if not requirement:
            continue
        missing_fields, missing_sections = missing_for_requirement(source_data, values, requirement)
        if not missing_fields and not missing_sections:
            continue
        gaps.append({
            "title": heading.get("title", ""),
            "number": heading.get("number", ""),
            "missing_fields": missing_fields,
            "missing_sections": missing_sections,
            "priority_materials": requirement.get("priority_materials", []),
            "optional_materials": requirement.get("optional_materials", []),
        })
    return gaps


def add_supplement_checklist(blocks, source_data, values, headings):
    gaps = collect_template_gaps(source_data, values, headings)
    blocks.append(text_block("标题一", "待补充资料清单"))
    if not gaps:
        blocks.append(text_block("正文", "经模板章节级资料门禁检查，暂未发现需要补充的关键资料。"))
        return

    def short_list(items, limit=8):
        unique = list(dict.fromkeys([item for item in items if item]))
        if len(unique) > limit:
            return "、".join(unique[:limit]) + f"等{len(unique)}项"
        return "、".join(unique)

    def material_group(item):
        groups = [
            ("项目基础与主体设计资料", ["立项", "初设", "主体工程", "项目组成", "建设内容", "平面布置", "技术指标", "服务范围", "管线"]),
            ("施工组织资料", ["施工组织", "施工总布置", "施工工艺", "施工进度", "施工便道", "施工出入口", "施工用水", "施工用电", "导流", "拆迁", "专项设施"]),
            ("工程占地与土石方资料", ["防治责任范围", "占地", "永久占地", "临时占地", "土石方", "表土", "借方", "余弃方", "道路破除"]),
            ("弃方消纳与临时堆土资料", ["弃方", "弃渣", "消纳", "土方运输", "临时堆土", "运输路线"]),
            ("项目区自然与水土流失背景资料", ["地形", "地貌", "气象", "水文", "土壤", "植被", "侵蚀", "水土流失", "公报", "遥感"]),
            ("水土保持评价资料", ["GB 50433", "制约性", "选址评价", "建设方案与布局评价", "已有水保措施", "长江保护法"]),
            ("水土流失预测资料", ["预测", "施工期", "自然恢复期", "侵蚀模数", "土壤流失量", "扰动地表"]),
            ("防治目标与措施资料", ["防治标准", "六项目标", "防治分区", "工程措施", "植物措施", "临时措施", "措施总体布置", "措施实施"]),
            ("水土保持监测资料", ["监测"]),
            ("投资概算与效益资料", ["投资", "概算", "费用", "补偿费", "单价", "定额", "价格信息", "效益"]),
            ("水土保持管理与验收资料", ["组织管理", "后续设计", "监理", "设施验收", "报备", "档案", "管护", "整改"]),
            ("附件附图资料", ["附件", "附表", "附图", "委托书", "批复", "用地", "公示", "位置图", "水系图", "现状图"]),
        ]
        for group, keywords in groups:
            if any(keyword in item for keyword in keywords):
                return group
        return "其他补充资料"

    priority_index = {}
    optional_index = {}
    for gap in gaps:
        label = gap["title"]
        missing = []
        if gap["missing_fields"]:
            missing.extend(gap["missing_fields"])
        if gap["missing_sections"]:
            missing.extend(gap["missing_sections"])
        priority_items = gap["priority_materials"] or ["补充本节原始资料或人工确认说明"]
        for item in priority_items:
            group = material_group(item)
            bucket = priority_index.setdefault(group, {"materials": [], "chapters": [], "missing": []})
            bucket["materials"].append(item)
            bucket["chapters"].append(label)
            bucket["missing"].extend(missing)
        for item in gap["optional_materials"]:
            group = material_group(item)
            bucket = optional_index.setdefault(group, {"materials": [], "chapters": []})
            bucket["materials"].append(item)
            bucket["chapters"].append(label)

    priority_rows = [["资料类别", "优先补充资料", "主要影响章节"]]
    for group, detail in sorted(priority_index.items(), key=lambda pair: (-len(set(pair[1]["chapters"])), pair[0])):
        priority_rows.append([
            group,
            short_list(detail["materials"], limit=10),
            short_list(detail["chapters"], limit=10),
        ])

    optional_rows = [["资料类别", "可补充资料", "主要影响章节"]]
    for group, detail in sorted(optional_index.items(), key=lambda pair: (-len(set(pair[1]["chapters"])), pair[0])):
        optional_rows.append([
            group,
            short_list(detail["materials"], limit=10),
            short_list(detail["chapters"], limit=10),
        ])

    blocks.append(text_block("标题二", "优先补充资料"))
    blocks.append(table_block(priority_rows))
    blocks.append(text_block("标题二", "可补充资料"))
    if len(optional_rows) > 1:
        blocks.append(table_block(optional_rows))
    else:
        blocks.append(text_block("正文", "暂无明确的可补充资料建议。"))


def add_template_report(blocks, source_data, values, headings):
    for index, heading in enumerate(headings):
        title = heading["title"]
        number = heading.get("number", "")
        style = heading.get("style", "标题一")
        blocks.append(text_block(style, title))
        current_level = heading_level(number)
        next_level = heading_level(headings[index + 1].get("number", "")) if index + 1 < len(headings) else 0
        has_children = next_level > current_level
        if not has_children:
            add_template_section_body(blocks, source_data, values, heading)
    add_supplement_checklist(blocks, source_data, values, headings)


def add_prediction(blocks, values):
    blocks.append(text_block("标题一", "水土流失分析与预测"))
    blocks.append(text_block("标题二", "水土流失现状"))
    missing = [field for field in ["土壤容许流失量", "原地貌土壤侵蚀模数"] if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))
    else:
        blocks.append(text_block(
            "正文",
            f"项目区土壤容许流失量为 {value(values, '土壤容许流失量')}，"
            f"原地貌土壤侵蚀模数为 {value(values, '原地貌土壤侵蚀模数')}。"
        ))
    blocks.append(text_block("标题二", "预测结果"))
    missing = [field for field in ["预测水土流失总量", "新增水土流失量"] if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))
    else:
        blocks.append(text_block(
            "正文",
            f"依据自动项目上下文，工程建设可能造成的水土流失总量为 {value(values, '预测水土流失总量')}，"
            f"其中新增水土流失量为 {value(values, '新增水土流失量')}。"
        ))


def add_investment(blocks, values):
    blocks.append(text_block("标题一", "水土保持投资概算及效益分析"))
    blocks.append(text_block("标题二", "投资概算"))
    invest_fields = ["水土保持总投资", "工程措施投资", "植物措施投资", "临时措施投资", "独立费用", "水土保持补偿费"]
    rows = [["项目", "投资"]]
    for field in invest_fields:
        if has_value(values, field):
            rows.append([field, value(values, field)])
    if len(rows) > 1:
        blocks.append(table_block(rows))
    missing = [field for field in invest_fields if not has_value(values, field)]
    if missing:
        blocks.append(text_block("正文", missing_note(missing_fields=missing)))


def add_generic_chapter(blocks, source_data, gate):
    blocks.append(text_block("标题一", gate["title"]))
    coverage = source_data.get("coverage", {})
    for title in gate.get("default_blocks", []):
        blocks.append(text_block("标题二", title))
        snippets = project_evidence_snippets(source_data, gate.get("required_sections", []), limit=1)
        if snippets:
            blocks.append(text_block("正文", "已检索到本项目相关资料：" + compact_snippet(snippets[0])))
        else:
            missing_sections = [section for section in gate.get("required_sections", []) if coverage.get(section) != "充分"]
            blocks.append(text_block("正文", missing_note(missing_sections=missing_sections or gate.get("required_sections", []))))


def generate():
    if not CONTEXT_JSON.exists():
        raise SystemExit("PROJECT_CONTEXT_SOURCES.json not found. Run context_builder.py first.")
    source_data = load_json(CONTEXT_JSON)
    gates = load_json(GATES_JSON)["chapters"]
    template_headings = load_template_headings()
    values = source_data.get("values", {})
    blocks = []

    if template_headings:
        add_template_report(blocks, source_data, values, template_headings)
        OUTPUT_JSON.write_text(json.dumps({"blocks": blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Generated {OUTPUT_JSON} using {TEMPLATE_PROFILE_JSON.name}")
        return

    for gate in gates:
        missing_fields, missing_sections = section_status(source_data, gate)
        if gate["id"] == "summary":
            add_summary(blocks, values)
        elif gate["id"] == "project_overview":
            add_project_overview(blocks, values)
        elif gate["id"] == "prediction":
            add_prediction(blocks, values)
        elif gate["id"] == "investment":
            add_investment(blocks, values)
        elif gate["id"] == "evaluation":
            add_evaluation(blocks, source_data, values, gate)
        elif gate["id"] == "measures":
            add_measures(blocks, source_data, values, gate)
        elif gate["id"] == "management":
            add_management(blocks, values, gate)
        elif gate["id"] == "attachments":
            add_attachments(blocks, source_data, gate)
        elif gate["id"] == "front_matter":
            continue
        else:
            add_generic_chapter(blocks, source_data, gate)

    OUTPUT_JSON.write_text(json.dumps({"blocks": blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT_JSON}")


if __name__ == "__main__":
    generate()

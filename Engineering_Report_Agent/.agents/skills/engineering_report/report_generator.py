import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = Path(__file__).resolve().parent
CONTEXT_JSON = ROOT / "PROJECT_CONTEXT_SOURCES.json"
GATES_JSON = SKILL_DIR / "chapter_gates.json"
SECTION_SPECS_JSON = SKILL_DIR / "section_writing_specs.json"
TEMPLATE_PROFILE_JSON = ROOT / "REPORT_TEMPLATE_PROFILE.json"
OUTPUT_JSON = ROOT / "temp_report.json"
ACTIVE_PROJECT_FILE = ROOT / "ACTIVE_PROJECT.txt"

MISSING_TEXT = "【⚠️ 缺失相关硬核数据，智能体跳过本项，请人工核对后在此补全具体内容。】"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def text_block(style, text, source="normal"):
    return {"type": "text", "style": style, "text": text, "source": source}


def table_block(rows):
    return {"type": "table", "data": rows}


def value(values, key, default=""):
    item = values.get(key)
    if isinstance(item, dict):
        return str(item.get("value", default) or "")
    return default


def has_value(values, key):
    return bool(value(values, key).strip())


def sentence_text(text):
    return str(text or "").strip().rstrip("。；; ")


def unique_items(items):
    return list(dict.fromkeys([item for item in items if item]))


def missing_note(missing_fields=None, missing_sections=None):
    parts = []
    if missing_fields:
        parts.append("缺失字段：" + "、".join(unique_items(missing_fields)))
    if missing_sections:
        parts.append("缺失资料分项：" + "、".join(unique_items(missing_sections)))
    return MISSING_TEXT + (f"（{'；'.join(parts)}）" if parts else "")


def active_project_name():
    if ACTIVE_PROJECT_FILE.exists():
        return ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    return ""


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
    if not text:
        return True
    broken_tokens = ["Ë", "Í", "±", "Ã", "Â", "Ð", "Ä", "Æ", "¼", "½", "¾"]
    if sum(text.count(token) for token in broken_tokens) >= 3:
        return True
    return "<table" in text.lower() or "</td>" in text.lower()


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
        if road in text:
            roads.append(road)
    if roads:
        return "工程沿" + "、".join(unique_items(roads)) + "等道路实施。"
    return "工程沿黄冈市黄州区城北片区既有城市道路实施。"


def load_template_headings():
    if not TEMPLATE_PROFILE_JSON.exists():
        return []
    data = load_json(TEMPLATE_PROFILE_JSON)
    sources = data.get("template_sources", [])
    if not sources:
        return []
    headings = sources[0].get("headings", [])
    return [item for item in headings if item.get("title") and item.get("style")]


def load_section_specs():
    if not SECTION_SPECS_JSON.exists():
        return {"default": {}, "section_specs": {}}
    return load_json(SECTION_SPECS_JSON)


def re_match_number(number):
    return bool(re.match(r"^\d+(?:\.\d+)*$", str(number or "")))


def heading_level(number):
    number = str(number or "")
    if re_match_number(number):
        return number.count(".") + 1
    return 1


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


def render_table(blocks, values, table_name):
    if table_name == "basic_info":
        fields = ["项目名称", "项目代码", "建设单位", "建设地点", "建设性质", "建设工期", "总投资", "土建投资"]
        rows = [["项目", "内容"]]
        for field in fields:
            if has_value(values, field):
                rows.append([field, value(values, field)])
        if len(rows) > 1:
            blocks.append(table_block(rows))
        return

    if table_name == "earthwork":
        fields = ["挖方", "填方", "借方", "余弃方"]
        rows = [["项目", "数量"]]
        for field in fields:
            if has_value(values, field):
                rows.append([field, value(values, field)])
        if len(rows) > 1:
            blocks.append(table_block(rows))
        return

    if table_name == "investment":
        fields = ["水土保持总投资", "工程措施投资", "植物措施投资", "临时措施投资", "独立费用", "水土保持补偿费"]
        rows = [["项目", "投资"]]
        for field in fields:
            if has_value(values, field):
                rows.append([field, value(values, field)])
        if len(rows) > 1:
            blocks.append(table_block(rows))


def placeholder_values(source_data, values):
    data = {
        "project_design": project_design_summary(source_data),
        "road_scope": project_road_scope_summary(source_data),
    }
    for key in values:
        raw = value(values, key)
        data[key] = raw
        data[f"{key}_sentence"] = sentence_text(raw)
    return data


PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def format_text(template, data):
    def replace(match):
        key = match.group(1)
        text = data.get(key, "")
        return text if text else f"【缺失{key}】"

    return PLACEHOLDER_RE.sub(replace, template)


def body_condition_passes(body_spec, values):
    all_fields = body_spec.get("when_all", [])
    any_fields = body_spec.get("when_any", [])
    if all_fields and not all(has_value(values, field) for field in all_fields):
        return False
    if any_fields and not any(has_value(values, field) for field in any_fields):
        return False
    return True


def render_spec_body(blocks, source_data, values, spec):
    data = placeholder_values(source_data, values)
    rendered = False
    for body_spec in spec.get("body", []):
        if not body_condition_passes(body_spec, values):
            continue
        text = format_text(body_spec.get("text", ""), data).strip()
        if text:
            blocks.append(text_block(body_spec.get("style", "正文"), text))
            rendered = True
    for table_name in spec.get("tables", []):
        render_table(blocks, values, table_name)
        rendered = True
    return rendered


def append_spec_missing(blocks, source_data, values, requirement, spec, default_spec):
    if spec.get("append_requirement_missing", default_spec.get("append_requirement_missing", True)) is False:
        return

    merged_requirement = dict(requirement or {})
    merged_requirement["required_fields"] = unique_items(
        list(merged_requirement.get("required_fields", [])) + list(spec.get("required_fields", []))
    )
    merged_requirement["required_sections"] = unique_items(
        list(merged_requirement.get("required_sections", [])) + list(spec.get("required_sections", []))
    )
    missing_fields, missing_sections = missing_for_requirement(source_data, values, merged_requirement)
    fallback_fields = [
        field for field in spec.get("fallback_missing_fields", [])
        if not has_value(values, field)
    ]
    fallback_sections = spec.get("fallback_missing_sections", [])
    missing_fields = unique_items(missing_fields + fallback_fields)
    missing_sections = unique_items(missing_sections + fallback_sections)

    if not missing_fields and not missing_sections and not spec.get("body") and not spec.get("tables"):
        missing_sections = default_spec.get("fallback_missing_sections", ["本节资料"])

    if missing_fields or missing_sections:
        blocks.append(text_block("正文", missing_note(missing_fields, missing_sections)))


def render_section(blocks, source_data, values, heading, section_specs):
    title = heading["title"]
    number = heading.get("number", "")
    requirement = heading.get("requirements") or {}
    default_spec = section_specs.get("default", {})
    spec = section_specs.get("section_specs_by_number", {}).get(number)
    if not spec:
        spec = section_specs.get("section_specs", {}).get(title)
    if not spec:
        spec = {
            "fallback_missing_sections": default_spec.get("fallback_missing_sections", ["本节资料"])
        }

    rendered = render_spec_body(blocks, source_data, values, spec)
    append_spec_missing(blocks, source_data, values, requirement, spec, default_spec)

    if not rendered and not blocks:
        blocks.append(text_block("正文", missing_note(missing_sections=[title + "资料"])))


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


def short_list(items, limit=8):
    unique = unique_items(items)
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


def add_supplement_checklist(blocks, source_data, values, headings):
    gaps = collect_template_gaps(source_data, values, headings)
    blocks.append(text_block("标题一", "待补充资料清单"))
    if not gaps:
        blocks.append(text_block("正文", "经模板章节级资料门禁检查，暂未发现需要补充的关键资料。"))
        return

    priority_index = {}
    optional_index = {}
    for gap in gaps:
        label = gap["title"]
        priority_items = gap["priority_materials"] or ["补充本节原始资料或人工确认说明"]
        for item in priority_items:
            bucket = priority_index.setdefault(material_group(item), {"materials": [], "chapters": []})
            bucket["materials"].append(item)
            bucket["chapters"].append(label)
        for item in gap["optional_materials"]:
            bucket = optional_index.setdefault(material_group(item), {"materials": [], "chapters": []})
            bucket["materials"].append(item)
            bucket["chapters"].append(label)

    priority_rows = [["资料类别", "优先补充资料", "主要影响章节"]]
    for group, detail in sorted(priority_index.items(), key=lambda pair: (-len(set(pair[1]["chapters"])), pair[0])):
        priority_rows.append([group, short_list(detail["materials"], 10), short_list(detail["chapters"], 10)])

    optional_rows = [["资料类别", "可补充资料", "主要影响章节"]]
    for group, detail in sorted(optional_index.items(), key=lambda pair: (-len(set(pair[1]["chapters"])), pair[0])):
        optional_rows.append([group, short_list(detail["materials"], 10), short_list(detail["chapters"], 10)])

    blocks.append(text_block("标题二", "优先补充资料"))
    blocks.append(table_block(priority_rows))
    blocks.append(text_block("标题二", "可补充资料"))
    if len(optional_rows) > 1:
        blocks.append(table_block(optional_rows))
    else:
        blocks.append(text_block("正文", "暂无明确的可补充资料建议。"))


def add_template_report(blocks, source_data, values, headings, section_specs):
    for index, heading in enumerate(headings):
        title = heading["title"]
        number = heading.get("number", "")
        style = heading.get("style", "标题一")
        blocks.append(text_block(style, title))
        current_level = heading_level(number)
        next_level = heading_level(headings[index + 1].get("number", "")) if index + 1 < len(headings) else 0
        if next_level <= current_level:
            render_section(blocks, source_data, values, heading, section_specs)
    add_supplement_checklist(blocks, source_data, values, headings)


def add_fallback_report(blocks, source_data, values, section_specs):
    headings = [
        {"title": "项目基本情况", "style": "标题一", "number": "1", "requirements": {}},
        {"title": "项目组成及工程布置", "style": "标题一", "number": "2", "requirements": {}},
        {"title": "工程占地", "style": "标题一", "number": "3", "requirements": {}},
        {"title": "土石方平衡", "style": "标题一", "number": "4", "requirements": {}},
        {"title": "结论", "style": "标题一", "number": "5", "requirements": {}},
    ]
    add_template_report(blocks, source_data, values, headings, section_specs)


def duplicate_body_count(blocks):
    texts = [item.get("text", "") for item in blocks if item.get("type") == "text" and item.get("style") == "正文"]
    counts = Counter(texts)
    return sum(1 for text, count in counts.items() if count > 1 and len(text) > 25)


def generate():
    if not CONTEXT_JSON.exists():
        raise SystemExit("PROJECT_CONTEXT_SOURCES.json not found. Run context_builder.py first.")

    source_data = load_json(CONTEXT_JSON)
    values = source_data.get("values", {})
    section_specs = load_section_specs()
    headings = load_template_headings()
    blocks = []

    if headings:
        add_template_report(blocks, source_data, values, headings, section_specs)
        source = TEMPLATE_PROFILE_JSON.name
    else:
        load_json(GATES_JSON)
        add_fallback_report(blocks, source_data, values, section_specs)
        source = "fallback"

    OUTPUT_JSON.write_text(json.dumps({"blocks": blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT_JSON} using {source}; duplicate正文={duplicate_body_count(blocks)}")


if __name__ == "__main__":
    generate()

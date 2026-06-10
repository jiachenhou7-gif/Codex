import json
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


ROOT = Path(__file__).resolve().parents[3]
STANDARDS_TEMPLATE_DIR = ROOT / "standards_templates"
OCR_MD_DIR = STANDARDS_TEMPLATE_DIR / "work" / "template_ocr"
OUTPUT = ROOT / "REPORT_TEMPLATE_PROFILE.json"
OCR_THRESHOLD = 500


HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*|[一二三四五六七八九十]+、|第[一二三四五六七八九十]+章)\s*(.{2,80})$")


def extract_pdf_text(path):
    if PdfReader is None:
        return ""
    chunks = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                chunks.append(text)
    except Exception:
        return ""
    return "\n".join(chunks)


def style_for_number(number):
    if number.startswith("第") or number.count(".") == 0:
        return "标题一"
    if number.count(".") == 1:
        return "标题二"
    if number.count(".") == 2:
        return "标题三"
    return "标题四"


def read_ocr_markdown():
    if not OCR_MD_DIR.exists():
        return ""
    chunks = []
    for path in sorted(OCR_MD_DIR.glob("*.md")):
        chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def report_book_content(text):
    start_match = re.search(r"(?m)^#+\s*生产建设项目水土保持方案报告书编制内容\s*$", text)
    if not start_match:
        return text
    start = start_match.start()
    end = len(text)
    end_match = re.search(
        r"(?m)^#+\s*(生产建设项目水土保持方案报告书编制格式|生产建设项目水土保持方案报告表编制|附件3)\s*$",
        text[start_match.end():],
    )
    if end_match:
        end = start_match.end() + end_match.start()
    return text[start:end]


def extract_headings(text):
    headings = []
    seen = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("#"):
            continue
        line = re.sub(r"^#+\s*", "", line).strip()
        if not line or len(line) > 90:
            continue
        line = re.sub(r"\.{3,}\s*\d+$", "", line).strip()
        match = HEADING_RE.match(line)
        if not match:
            continue
        number, title = match.groups()
        title = title.strip(" .．\t")
        key = (number, title)
        if not title or key in seen:
            continue
        seen.add(key)
        headings.append({
            "number": number,
            "title": title,
            "style": style_for_number(number),
        })
    return headings


def clean_instruction(text, max_len=420):
    text = re.sub(r"<table>.*?</table>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"^#+\s*.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len].rstrip(" ，。；、") + "。"
    return text


def heading_pattern(heading):
    number = re.escape(heading["number"])
    title = re.escape(heading["title"])
    return re.compile(rf"(?m)^#+\s*{number}\s*{title}\s*$")


def attach_template_instructions(text, headings):
    positions = []
    for heading in headings:
        match = heading_pattern(heading).search(text)
        if match:
            positions.append((match.start(), match.end(), heading))
    positions.sort(key=lambda item: item[0])
    for index, (_, end, heading) in enumerate(positions):
        next_start = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        heading["template_instruction"] = clean_instruction(text[end:next_start])
        heading["requirements"] = requirements_for_heading(heading["title"], heading["template_instruction"])
    return headings


def requirements_for_heading(title, instruction):
    text = title
    req = {
        "required_fields": [],
        "required_sections": [],
        "priority_materials": [],
        "optional_materials": [],
        "content_norm": instruction or "按模板标题要求编写；资料不足时在本节标注缺失，不得编造。",
    }

    def need_fields(*items):
        req["required_fields"].extend(items)

    def need_sections(*items):
        req["required_sections"].extend(items)

    def priority(*items):
        req["priority_materials"].extend(items)

    def optional(*items):
        req["optional_materials"].extend(items)

    if any(k in text for k in ["项目基本情况", "项目简况", "项目组成", "工程布置"]):
        need_fields("项目名称", "建设单位", "建设地点", "建设性质", "建设工期", "总投资", "土建投资")
        need_sections("主体工程设计资料")
        priority("立项/初设批复", "主体工程设计说明", "项目组成及建设内容表", "工程平面布置资料")
        optional("项目服务范围说明", "主要技术指标表", "管线平面布置图")
    if any(k in text for k in ["自然简况", "自然概况", "地质", "地貌", "气候", "水文", "土壤", "植被", "敏感区"]):
        need_fields("土壤容许流失量", "原地貌土壤侵蚀模数")
        need_sections("项目区自然与水土流失背景资料")
        priority("地形地貌资料", "气象水文资料", "土壤和植被资料", "水土流失重点防治区划", "土壤容许流失量和原地貌侵蚀模数依据")
        optional("区域地质资料", "水土保持公报", "现场照片或遥感影像")
    if any(k in text for k in ["施工组织", "施工生产生活区", "施工道路", "施工用水", "施工导流", "施工工艺"]):
        need_sections("主体工程设计资料")
        priority("施工组织设计", "施工总布置图", "施工工艺流程", "施工进度安排")
        optional("施工便道和施工出入口布置", "施工用水用电方案")
    if any(k in text for k in ["拆迁", "专项设施改"]):
        need_sections("主体工程设计资料")
        priority("拆迁安置说明或不涉及说明", "专项设施改迁建说明")
        optional("专项设施迁改协议", "拆迁安置工程量表")
    if any(k in text for k in ["取土场"]):
        need_sections("主体工程设计资料", "工程占地与土石方资料")
        priority("取土场设置说明或不设置说明", "取土来源证明")
        optional("取土场位置图", "取土场水土保持防护资料")
    if any(k in text for k in ["弃渣场", "临时堆土场", "渣土来源", "堆置"]):
        need_fields("余弃方")
        need_sections("工程占地与土石方资料")
        priority("弃方去向证明", "土方运输合同或消纳协议", "临时堆土场位置和占地资料")
        optional("弃渣综合利用说明", "运输路线和防护要求")
    if any(k in text for k in ["工程占地", "防治责任范围"]):
        need_fields("防治责任范围")
        need_sections("工程占地与土石方资料")
        priority("防治责任范围表", "占地类型及面积统计表", "永久占地和临时占地说明")
        optional("用地预审或规划审查意见", "防治责任范围图")
    if any(k in text for k in ["土石方", "表土"]):
        need_fields("挖方", "填方")
        need_sections("工程占地与土石方资料")
        priority("土石方平衡表", "表土剥离和回覆量", "借方来源", "余弃方去向")
        optional("土石方调运图", "道路破除和恢复工程量")
    if any(k in text for k in ["水土保持评价", "选址", "建设方案与布局", "施工方法与工艺评价", "具有水土保持功能"]):
        need_fields("项目名称", "防治责任范围")
        need_sections("水土保持评价资料", "主体工程设计资料", "工程占地与土石方资料")
        priority("GB 50433 制约性因素分析", "主体工程选址评价资料", "建设方案与布局评价资料", "主体工程已有水保措施界定")
        optional("长江保护法等区域管控符合性资料", "工程占地和土石方水土保持评价表")
    if any(k in text for k in ["水土流失现状", "水土流失影响", "土壤流失量预测", "预测结果", "危害分析"]):
        need_fields("防治责任范围", "土壤容许流失量", "原地貌土壤侵蚀模数", "预测水土流失总量")
        need_sections("水土流失预测资料", "项目区自然与水土流失背景资料")
        priority("预测单元划分", "施工期和自然恢复期预测时段", "土壤侵蚀模数取值依据", "土壤流失量预测计算表")
        optional("水土流失危害分析说明", "扰动地表面积分区表")
    if any(k in text for k in ["设计水平年", "防治目标", "执行标准", "防治区划分", "措施总体布局", "分区措施", "工程级别"]):
        need_fields("防治责任范围")
        need_sections("水土保持措施资料")
        priority("水土流失防治标准执行等级", "六项目标计算表", "防治分区", "工程措施、植物措施、临时措施工程量", "措施总体布置图")
        optional("措施实施时序", "施工组织和管护要求")
    if any(k in text for k in ["水土保持监测", "范围和时段", "内容、方法与频次", "监测内容", "监测方法", "点位布设", "实施条件和成果"]):
        need_sections("水土保持监测资料")
        priority("监测范围和时段", "监测内容、方法与频次", "监测点位布设", "重点监测区域")
        optional("监测设施布设图", "监测成果提交要求")
    if any(k in text for k in ["投资", "估算", "效益分析", "编制原则及依据", "编制说明与估算成果"]):
        need_fields("水土保持总投资", "工程措施投资", "植物措施投资", "临时措施投资", "水土保持补偿费")
        need_sections("投资概算与效益资料")
        priority("水土保持投资概算表", "分部工程概算表", "独立费用和预备费", "水土保持补偿费计算", "六项目标达标测算表")
        optional("单价分析表", "价格信息和定额依据")
    if text == "结论":
        need_sections("水土保持评价资料", "水土保持措施资料", "水土流失预测资料", "投资概算与效益资料")
        priority("项目水土保持评价结论", "水土流失预测结果", "措施和投资摘要", "下一步工作建议")
        optional("专家审查意见", "建设管理承诺")
    if any(k in text for k in ["水土保持管理", "后续设计", "水土保持监理", "水土保持施工", "设施验收"]):
        need_fields("建设单位")
        need_sections("水土保持管理资料")
        priority("组织管理要求", "后续设计要求", "水土保持监理要求", "设施验收和报备要求")
        optional("档案管理和运行管护要求", "监督检查整改要求")
    if any(k in text for k in ["附件", "附表", "附图"]):
        need_sections("附件、附表与附图资料")
        priority("委托书、批复、用地意见、土方合同等附件", "土石方平衡表、预测计算表、投资估算表", "项目位置图、水系图、现状图、措施布置图")
        optional("公示截图", "主体设计图", "遥感影像图")

    for key in ["required_fields", "required_sections", "priority_materials", "optional_materials"]:
        req[key] = list(dict.fromkeys(req[key]))
    return req


def build_profile():
    profiles = []
    ocr_required = []
    ocr_text = read_ocr_markdown()
    if ocr_text.strip():
        content = report_book_content(ocr_text)
        headings = extract_headings(content)
        if headings:
            headings = attach_template_instructions(content, headings)
            profiles.append({
                "path": str(OCR_MD_DIR.relative_to(ROOT)),
                "source": "ocr_markdown",
                "chars": len(content),
                "headings": headings,
            })
    for path in STANDARDS_TEMPLATE_DIR.glob("*.pdf"):
        text = extract_pdf_text(path)
        if len(text.strip()) < OCR_THRESHOLD:
            ocr_required.append({
                "path": str(path.relative_to(ROOT)),
                "reason": "模板 PDF 可抽取文字过少，可能为扫描件，需要先 OCR 后才能提取章节结构。",
                "chars": len(text.strip()),
            })
            continue
        profiles.append({
            "path": str(path.relative_to(ROOT)),
            "source": "pdf_text",
            "chars": len(text),
            "headings": attach_template_instructions(report_book_content(text), extract_headings(report_book_content(text))),
        })
    result = {
        "template_sources": profiles,
        "ocr_required_templates": ocr_required,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT}")
    if ocr_required:
        print("Template OCR required:")
        for item in ocr_required:
            print(f"- {item['path']}")


if __name__ == "__main__":
    build_profile()

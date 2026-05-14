import html
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SRC = DOCS / "桌面宠物系统UML设计图.docx"
OUT = DOCS / "桌面宠物系统UML设计图_讲解注释版.docx"

NOTES = {
    "图 1": "讲解注释：该图展示系统总体功能边界，用户作为主要参与者，可以完成桌宠查看、互动、状态查看、背包喂养、任务成长和系统设置等操作。答辩时可说明该图用于概括整个北极熊桌宠系统的核心用例。",
    "图 2": "讲解注释：该图展示系统总体运行流程，从用户启动应用开始，系统初始化桌宠窗口、加载状态数据、响应用户互动，并将状态变化、任务结果和日志反馈给用户。答辩时可用它说明各模块之间的调用顺序。",
    "图 3": "讲解注释：该用例图对应桌宠形象与桌面交互模块，重点体现用户查看北极熊桌宠、拖拽移动、点击互动和触发动作反馈等功能，是系统最直观的入口模块。",
    "图 4": "讲解注释：该顺序图描述用户与桌宠交互的过程。用户操作桌宠后，桌宠窗口接收事件，调用动作控制逻辑，更新显示效果，并将互动事件写入通知或日志模块。",
    "图 5": "讲解注释：该用例图对应宠物状态管理模块，主要体现用户查看饱食度、心情值、好感度、成长值等状态，以及系统根据互动和时间变化更新宠物状态。",
    "图 6": "讲解注释：该顺序图展示状态更新流程。用户触发互动、投喂或任务操作后，状态管理模块计算属性变化，再同步到界面显示和本地存档中。",
    "图 7": "讲解注释：该用例图对应背包与喂养模块，体现用户查看背包、选择食物、投喂桌宠和管理物品数量等功能。该模块与宠物状态模块存在直接联动。",
    "图 8": "讲解注释：该顺序图展示投喂流程。用户选择物品后，背包模块扣减物品数量，桌宠模块播放投喂反馈，状态模块更新饱食度或好感度，日志模块记录本次操作。",
    "图 9": "讲解注释：该用例图对应任务与成长模块，体现用户查看每日任务、执行专注任务、完成任务并获得经验奖励等功能，用于增强桌宠的养成感和持续使用价值。",
    "图 10": "讲解注释：该顺序图展示任务完成流程。用户开始或完成任务后，任务模块校验任务状态，更新成长经验和等级信息，并向通知日志模块发送任务完成反馈。",
    "图 11": "讲解注释：该用例图对应系统设置与数据管理模块，体现用户修改置顶、缩放、声音、主题、开机自启以及保存和读取本地数据等功能。",
    "图 12": "讲解注释：该顺序图展示设置保存与数据恢复流程。用户修改设置后，系统写入本地配置文件；应用再次启动时读取配置和存档，恢复桌宠状态、窗口位置和用户偏好。",
}

PARA_TEMPLATE = (
    '<w:p>'
    '<w:pPr><w:spacing w:before="120" w:after="160"/><w:ind w:firstLine="420"/></w:pPr>'
    '<w:r><w:rPr><w:sz w:val="21"/><w:color w:val="44546A"/></w:rPr>'
    '<w:t>{}</w:t>'
    '</w:r>'
    '</w:p>'
)


def paragraph_text(block: str) -> str:
    values = re.findall(r"<w:t[^>]*>(.*?)</w:t>", block)
    return "".join(html.unescape(value) for value in values).strip()


def make_paragraph(text: str) -> str:
    return PARA_TEMPLATE.format(html.escape(text, quote=False))


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)

    with zipfile.ZipFile(SRC, "r") as zin:
        xml = zin.read("word/document.xml").decode("utf-8")
        parts = re.split(r"(<w:p[\s\S]*?</w:p>)", xml)
        new_parts = []
        inserted = []

        for part in parts:
            new_parts.append(part)
            if not part.startswith("<w:p"):
                continue

            text = paragraph_text(part)
            for key, note in sorted(NOTES.items(), key=lambda item: len(item[0]), reverse=True):
                if text.startswith(key):
                    new_parts.append(make_paragraph(note))
                    inserted.append(key)
                    break

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    data = "".join(new_parts).encode("utf-8")
                zout.writestr(item, data)

    print(f"输出文件: {OUT}")
    print(f"已添加注释数量: {len(inserted)}")
    print("已添加:", "、".join(inserted))


if __name__ == "__main__":
    main()

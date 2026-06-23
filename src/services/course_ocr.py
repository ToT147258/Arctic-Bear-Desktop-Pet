import re
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAY_ALIASES = {
    "周一": "周一",
    "星期一": "周一",
    "礼拜一": "周一",
    "monday": "周一",
    "mon": "周一",
    "周二": "周二",
    "星期二": "周二",
    "礼拜二": "周二",
    "tuesday": "周二",
    "tue": "周二",
    "周三": "周三",
    "星期三": "周三",
    "礼拜三": "周三",
    "wednesday": "周三",
    "wed": "周三",
    "周四": "周四",
    "星期四": "周四",
    "礼拜四": "周四",
    "thursday": "周四",
    "thu": "周四",
    "周五": "周五",
    "星期五": "周五",
    "礼拜五": "周五",
    "friday": "周五",
    "fri": "周五",
    "周六": "周六",
    "星期六": "周六",
    "礼拜六": "周六",
    "saturday": "周六",
    "sat": "周六",
    "周日": "周日",
    "周天": "周日",
    "星期日": "周日",
    "星期天": "周日",
    "礼拜日": "周日",
    "礼拜天": "周日",
    "sunday": "周日",
    "sun": "周日",
}

PERIOD_STARTS = {
    1: "08:00",
    2: "08:55",
    3: "10:10",
    4: "11:05",
    5: "14:00",
    6: "14:55",
    7: "16:10",
    8: "17:05",
    9: "19:00",
    10: "19:55",
    11: "20:50",
    12: "21:45",
}

COURSE_KEYWORDS = {
    "专业英语": ("专业英语", "专业英", "专 业 英 语"),
    "软件工程导论": ("软件工程导论", "软件工程导", "歉件工程导", "歇件工程导", "软 件 工 程"),
    "计算机网络": ("计算机网络", "计类机网络", "计 算 机 网 络", "计类机", "网络"),
    "数据结构与算法": ("数据结构与算法", "数据结构与", "数檀结构与", "数结构与", "数 据 结 构", "算法", "类法"),
    "概率论与数理统计II": ("概率论与数理统计", "概率论与数谐统计", "概率论与数理统", "概率论与数", "统计II"),
    "毛泽东思想和中国特色社会主义理论体系概论": (
        "毛泽东思想和中国特色社会主义理论体系概论",
        "毛泽东思想和中国",
        "中国特色社会主义理论",
        "体系概论",
    ),
    "大学体育IV（柔力球01）": ("大学体育", "柔力球"),
    "Java Web开发": ("Java Web开发", "Java Web开", "JavaWeb开发", "JavaWeb"),
    "创新创业基础": ("创新创业基础", "创新创业", "创新创"),
    "形势与政策IV": ("形势与政策", "形势与政", "形势与政到"),
}


WINDOWS_OCR_SCRIPT = r"""
param([string]$ImagePath)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq "AsTask" -and
        $_.IsGenericMethodDefinition -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -like "IAsyncOperation*"
    } | Select-Object -First 1)

function AwaitOperation($operation, [type]$resultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($resultType)
    $task = $asTask.Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
}

$file = AwaitOperation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
$stream = AwaitOperation ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = AwaitOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = AwaitOperation ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = $null
try {
    $language = [Windows.Globalization.Language]::new("zh-Hans")
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
} catch {}
if ($null -eq $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if ($null -eq $engine) {
    throw "Windows OCR 没有可用语言包，请在 Windows 设置里安装中文 OCR。"
}

$result = AwaitOperation ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$lines = @()
foreach ($line in $result.Lines) {
    $words = @()
    foreach ($word in $line.Words) {
        $words += $word.Text
    }
    if ($words.Count -gt 0) {
        $lines += ($words -join " ")
    }
}
if ($lines.Count -gt 0) {
    $text = $lines -join "`n"
} else {
    $text = $result.Text
}
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($text))
"""

WINDOWS_OCR_WORDS_SCRIPT = r"""
param([string]$ImagePath)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq "AsTask" -and
        $_.IsGenericMethodDefinition -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -like "IAsyncOperation*"
    } | Select-Object -First 1)

function AwaitOperation($operation, [type]$resultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($resultType)
    $task = $asTask.Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
}

$file = AwaitOperation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
$stream = AwaitOperation ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = AwaitOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = AwaitOperation ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = $null
try {
    $language = [Windows.Globalization.Language]::new("zh-Hans")
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
} catch {}
if ($null -eq $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if ($null -eq $engine) {
    throw "Windows OCR 没有可用语言包。"
}

$result = AwaitOperation ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$items = @()
foreach ($line in $result.Lines) {
    foreach ($word in $line.Words) {
        $rect = $word.BoundingRect
        $items += [PSCustomObject]@{
            text = $word.Text
            x = [double]$rect.X
            y = [double]$rect.Y
            w = [double]$rect.Width
            h = [double]$rect.Height
        }
    }
}
$json = $items | ConvertTo-Json -Compress -Depth 4
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($json))
"""


def detect_ocr_status():
    tesseract_path = _find_tesseract()
    pytesseract_ready = _has_pytesseract()
    windows_ocr_ready = _windows_ocr_supported()

    if tesseract_path and pytesseract_ready:
        return {
            "available": True,
            "engine": "Tesseract OCR",
            "message": f"已检测到 Tesseract OCR：{tesseract_path}",
        }
    if tesseract_path:
        return {
            "available": True,
            "engine": "Tesseract CLI",
            "message": f"已检测到 tesseract.exe，可直接识别：{tesseract_path}",
        }
    if windows_ocr_ready:
        return {
            "available": True,
            "engine": "Windows OCR",
            "message": "已启用 Windows 自带 OCR。若识别中文较少，请在 Windows 设置里安装“中文简体 OCR”。",
        }
    return {
        "available": False,
        "engine": "none",
        "message": "未检测到可用 OCR。可安装 Tesseract OCR，或把图片文字粘贴到文本框后解析。",
    }


def recognize_timetable_image(image_path):
    path = Path(image_path)
    if not path.exists():
        return "", "没有找到课表图片。"

    try:
        image = _prepare_image(path)
    except Exception as exc:
        return "", f"图片读取失败：{exc}"

    try:
        courses = _extract_grid_timetable_courses(image)
        if len(courses) >= 3:
            text = _courses_to_import_text(courses)
            return text, f"已按课表网格识别 {len(courses)} 门课程，可以直接导入。"
    except Exception:
        pass

    errors = []
    text = ""
    engine_name = ""

    try:
        text = _recognize_with_tesseract_python(image)
        engine_name = "Tesseract OCR"
    except Exception as exc:
        errors.append(str(exc))

    if not text.strip():
        try:
            text = _recognize_with_tesseract_cli(image)
            engine_name = "Tesseract CLI"
        except Exception as exc:
            errors.append(str(exc))

    if not text.strip():
        try:
            text = _recognize_with_windows_ocr(image)
            engine_name = "Windows OCR"
        except Exception as exc:
            errors.append(str(exc))

    text = _clean_ocr_text(text)
    if not text.strip():
        hint = "；".join(error for error in errors if error) or "没有识别到有效文字"
        return "", f"OCR 暂时没有识别出有效文字：{hint}。可以换一张更清晰、正向、无遮挡的课表照片。"
    return text, f"{engine_name} 识别完成，已尝试解析课程。"


def _extract_grid_timetable_courses(image):
    grid = _detect_timetable_grid(image)
    if not grid:
        return []
    words = _recognize_words_with_windows_ocr(image)
    if not words:
        return []

    x_lines, y_lines = grid
    section_times = ["08:20", "10:20", "14:10", "16:00", "19:10"]
    courses = []

    for row_index in range(min(5, len(y_lines) - 1)):
        y0, y1 = y_lines[row_index], y_lines[row_index + 1]
        for col_index in range(7):
            x0, x1 = x_lines[col_index + 1], x_lines[col_index + 2]
            text = _cell_text(words, x0, y0, x1, y1)
            title = _cell_title(text)
            if not title:
                continue
            location = _cell_location(text)
            courses.append(
                {
                    "title": title,
                    "time": section_times[row_index],
                    "location": location or "待确认地点",
                    "note": _cell_note(text),
                    "day": WEEKDAY_NAMES[col_index],
                    "source": "ocr",
                }
            )
    return _dedupe_courses(courses)


def _detect_timetable_grid(image):
    try:
        import numpy as np
    except Exception:
        return None

    rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    max_channel = rgb.max(axis=2)
    min_channel = rgb.min(axis=2)
    grey_line = (max_channel - min_channel < 14) & (max_channel > 160) & (max_channel < 252)

    y_start = int(height * 0.17)
    y_end = int(height * 0.68)
    x_score = grey_line[y_start:y_end, :].sum(axis=0)
    x_groups = _score_groups(x_score, max(40, int((y_end - y_start) * 0.42)))
    x_centers = _merge_close_numbers([center for center, _ in x_groups if width * 0.12 <= center <= width * 0.995], max(5, width * 0.006))
    x_lines = _choose_table_x_lines(x_centers)
    if not x_lines:
        return None

    x0, x1 = int(x_lines[0]), int(x_lines[-1])
    y_score = grey_line[:, x0:x1].sum(axis=1)
    y_groups = _score_groups(y_score, max(40, int((x1 - x0) * 0.48)))
    y_centers = _merge_close_numbers([center for center, _ in y_groups if height * 0.16 <= center <= height * 0.75], max(5, height * 0.004))
    y_lines = _choose_table_y_lines(y_centers, height)
    if not y_lines:
        return None
    return [int(round(value)) for value in x_lines], [int(round(value)) for value in y_lines]


def _score_groups(score, threshold):
    indexes = [int(index) for index, value in enumerate(score) if value >= threshold]
    if not indexes:
        return []
    groups = []
    start = previous = indexes[0]
    for index in indexes[1:]:
        if index <= previous + 1:
            previous = index
            continue
        segment = score[start : previous + 1]
        peak = int(segment.max()) if len(segment) else 0
        groups.append(((start + previous) / 2, peak))
        start = previous = index
    segment = score[start : previous + 1]
    peak = int(segment.max()) if len(segment) else 0
    groups.append(((start + previous) / 2, peak))
    return groups


def _merge_close_numbers(values, max_gap):
    values = sorted(float(value) for value in values)
    if not values:
        return []
    merged = []
    bucket = [values[0]]
    for value in values[1:]:
        if value - bucket[-1] <= max_gap:
            bucket.append(value)
        else:
            merged.append(sum(bucket) / len(bucket))
            bucket = [value]
    merged.append(sum(bucket) / len(bucket))
    return merged


def _choose_table_x_lines(centers):
    if len(centers) < 9:
        return []
    best = None
    best_score = float("inf")
    for start in range(0, len(centers) - 8):
        lines = centers[start : start + 9]
        day_widths = [lines[index + 1] - lines[index] for index in range(1, 8)]
        stable_widths = day_widths[1:] if len(day_widths) > 4 else day_widths
        average = sum(stable_widths) / len(stable_widths)
        if average <= 0:
            continue
        spread = max(stable_widths) - min(stable_widths)
        time_width = lines[1] - lines[0]
        first_day_width = day_widths[0]
        if spread / average > 0.36 or time_width > average * 0.9 or first_day_width > average * 1.75:
            continue
        score = spread / average + abs(time_width / average - 0.45) + abs(first_day_width / average - 1.35) * 0.2
        if score < best_score:
            best = lines
            best_score = score
    return best or []


def _choose_table_y_lines(centers, image_height):
    if len(centers) < 7:
        return []
    header_bottom_index = None
    for index in range(0, len(centers) - 2):
        gap = centers[index + 1] - centers[index]
        next_gap = centers[index + 2] - centers[index + 1]
        if image_height * 0.008 <= gap <= image_height * 0.035 and next_gap >= image_height * 0.035:
            header_bottom_index = index + 1
            break
    if header_bottom_index is None:
        return []

    rows = [centers[header_bottom_index]]
    for y in centers[header_bottom_index + 1 :]:
        if y - rows[-1] < image_height * 0.022:
            break
        rows.append(y)
        if len(rows) >= 6:
            break
    return rows if len(rows) >= 4 else []


def _recognize_words_with_windows_ocr(image):
    if not _windows_ocr_supported():
        return []
    image_path = _save_temp_png(image)
    script_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", encoding="utf-8-sig", delete=False) as script_file:
            script_file.write(WINDOWS_OCR_WORDS_SCRIPT)
            script_path = Path(script_file.name)

        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(image_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=45,
            creationflags=_creation_flags(),
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return []
        decoded = base64.b64decode(completed.stdout.strip()).decode("utf-8", "ignore")
        data = json.loads(decoded or "[]")
        if isinstance(data, dict):
            data = [data]
        return [item for item in data if item.get("text")]
    finally:
        _safe_unlink(image_path)
        if script_path:
            _safe_unlink(script_path)


def _cell_text(words, x0, y0, x1, y1):
    margin_x = max(4, (x1 - x0) * 0.035)
    margin_y = max(4, (y1 - y0) * 0.02)
    selected = []
    for word in words:
        cx = float(word.get("x", 0)) + float(word.get("w", 0)) / 2
        cy = float(word.get("y", 0)) + float(word.get("h", 0)) / 2
        if x0 + margin_x <= cx <= x1 - margin_x and y0 + margin_y <= cy <= y1 - margin_y:
            selected.append(word)
    if not selected:
        return ""

    selected.sort(key=lambda item: (float(item.get("y", 0)) + float(item.get("h", 0)) / 2, float(item.get("x", 0))))
    lines = []
    current = []
    current_y = None
    for word in selected:
        cy = float(word.get("y", 0)) + float(word.get("h", 0)) / 2
        threshold = max(12, float(word.get("h", 12)) * 0.9)
        if current_y is None or abs(cy - current_y) <= threshold:
            current.append(word)
            current_y = cy if current_y is None else (current_y * 0.7 + cy * 0.3)
        else:
            lines.append(_join_ocr_words(current))
            current = [word]
            current_y = cy
    if current:
        lines.append(_join_ocr_words(current))
    return _clean_cell_text("\n".join(line for line in lines if line.strip()))


def _join_ocr_words(words):
    words = sorted(words, key=lambda item: float(item.get("x", 0)))
    output = ""
    for word in words:
        token = str(word.get("text", "")).strip()
        if not token:
            continue
        if not output:
            output = token
        elif _should_join_without_space(output[-1], token[0]):
            output += token
        else:
            output += " " + token
    return output


def _should_join_without_space(left, right):
    if _is_cjk(left) and _is_cjk(right):
        return True
    if left in "（([《【" or right in "）)]》】,，.。:：;；":
        return True
    if left.isdigit() and right in "-一—至到":
        return True
    if left in "-一—至到" and right.isdigit():
        return True
    return False


def _is_cjk(char):
    return "\u4e00" <= char <= "\u9fff"


def _clean_cell_text(text):
    text = str(text or "")
    replacements = {
        "星斯": "星期",
        "星螟": "星期",
        "歉件": "软件",
        "歇件": "软件",
        "\u6b24件": "软件",
        "计类机": "计算机",
        "数 结 构": "数据结构",
        "Java WebH": "Java Web开",
        "Java WebF": "Java Web开",
        "计亞实验室": "计算实验室",
        "计亚实验室": "计算实验室",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])", "", text)
    text = re.sub(r"[|｜]+", " ", text)
    return text.strip()


def _cell_title(text):
    canonical = _canonical_course_title(text)
    if canonical:
        return canonical
    lines = [_normalize_cell_line(line) for line in str(text or "").splitlines()]
    lines = [line for line in lines if line]
    parts = []
    for line in lines:
        if _line_is_course_meta(line) or _line_is_location(line):
            continue
        line = _remove_teacher_suffix(line)
        if not line or _line_is_course_meta(line) or _line_is_location(line):
            continue
        parts.append(line)
        if len("".join(parts)) >= 8 or len(parts) >= 3:
            break
    title = "".join(parts).strip(" -—_")
    title = re.sub(r"^[、,，.。:：\s]+", "", title)
    title = title[:36]
    if len(re.sub(r"[^\u4e00-\u9fa5A-Za-z]", "", title)) < 2:
        return ""
    return title


def _canonical_course_title(text):
    raw = str(text or "")
    if not raw.strip():
        return ""
    compact = re.sub(r"\s+", "", raw)
    compact = compact.replace("歉件", "软件").replace("歇件", "软件").replace("\u6b24件", "软件").replace("软仵", "软件")
    compact = compact.replace("计类机", "计算机").replace("计第机", "计算机")
    compact = compact.replace("数檀", "数据").replace("数结", "数据结").replace("类法", "算法")
    compact = compact.replace("政到", "政策").replace("WebH", "Web开").replace("WebF", "Web开")
    lower_raw = raw.lower()
    lower_compact = compact.lower()

    if "javaweb" in lower_compact or "java web" in lower_raw:
        return "Java Web开发"
    if "数据结构" in compact and ("算法" in compact or "与算" in compact):
        return "数据结构与算法"
    if "概率论" in compact and "统计" in compact:
        return "概率论与数理统计II"
    if "毛泽东思想" in compact or "中国特色社会主义" in compact:
        return "毛泽东思想和中国特色社会主义理论体系概论"
    if "大学体育" in compact or "柔力球" in compact:
        return "大学体育IV（柔力球01）"

    for title, keywords in COURSE_KEYWORDS.items():
        for keyword in keywords:
            key = re.sub(r"\s+", "", keyword).lower()
            if key and key in lower_compact:
                return title
    return ""


def _normalize_cell_line(line):
    line = _clean_cell_text(line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _line_is_course_meta(line):
    if re.search(r"\d+\s*[-一—]\s*\d+.*周", line):
        return True
    if re.search(r"\[\s*\d+\s*[-一—]\s*\d+\s*节", line):
        return True
    if re.fullmatch(r"[\d\s,，.。()（）\[\]一二三四五六七八九十周节第到至\-—]+", line):
        return True
    if "讲师" in line or "副教授" in line or "助教" in line or "辅导员" in line:
        return False
    return False


def _line_is_location(line):
    if re.fullmatch(r"(?:24|25|31|33|34|36)\d{2}", line):
        return True
    return bool(re.search(r"(综合馆|实验室|实训室|机房|教学楼|教室|体育馆)$", line))


def _remove_teacher_suffix(line):
    line = re.sub(r"[\u4e00-\u9fa5]{2,4}(?:讲师|副教授|教授|助教|辅导员).*", "", line)
    return line.strip()


def _cell_location(text):
    compact = re.sub(r"\s+", "", str(text or ""))
    compact = compact.replace("计亞实验室", "计算实验室").replace("计亚实验室", "计算实验室")
    patterns = [
        r"(?:24|25|31|33|34|36)\d{2}(?:云平台综合实训室|智能与分布计算实验室|软件架构实验室)",
        r"(?:云平台综合实训室|智能与分布计算实验室|软件架构实验室|综合馆|体育馆|机房)",
        r"(?:24|25|31|33|34|36)\d{2}[\u4e00-\u9fa5A-Za-z0-9]{0,10}(?:实验室|实训室)",
        r"(?:云平台综合实训室|智能与分布计算实验室|软件架构实验室|综合馆|体育馆|机房)",
        r"(?:24|25|31|33|34|36)\d{2}",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if match:
            return match.group(0)
    return ""


def _cell_note(text):
    note = re.sub(r"\s+", " ", str(text or "")).strip()
    return note[:90] if note else "课表照片识别导入"


def _courses_to_import_text(courses):
    lines = []
    for course in courses:
        title = course.get("title", "").strip()
        if not title:
            continue
        day = course.get("day", "每天")
        time = course.get("time", "08:00")
        location = course.get("location", "待确认地点")
        lines.append(f"{day} {time} {title} {location}")
    return "\n".join(lines)


def parse_timetable_text(text):
    lines = [_normalize_line(line) for line in str(text or "").splitlines()]
    lines = [line for line in lines if _is_useful_line(line)]
    courses = []
    current_day = ""

    for line in lines:
        explicit_day = _extract_weekday(line)
        explicit_time = _extract_time(line)
        canonical_title = _canonical_course_title(line)
        if not explicit_day and not explicit_time and not canonical_title:
            continue

        day = explicit_day or current_day
        header_day = _line_is_day_header(line)
        if header_day:
            current_day = header_day
            continue
        if day:
            current_day = day

        time_text = explicit_time
        title = canonical_title or _extract_title(line)
        location = _extract_location(line)

        if not title and (time_text or location):
            continue
        if not title or _looks_like_header(title):
            continue
        if not time_text:
            time_text = _infer_time_by_count(courses, day)

        courses.append(
            {
                "title": title[:40],
                "time": time_text,
                "location": location or "待确认地点",
                "note": "课表照片识别导入",
                "day": day or "每天",
                "source": "ocr",
            }
        )

    return _dedupe_courses(courses)


def _find_tesseract():
    found = shutil.which("tesseract")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def _has_pytesseract():
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return False
    return True


def _windows_ocr_supported():
    return sys.platform.startswith("win")


def _prepare_image(path):
    image = Image.open(path)
    image = ImageOps.exif_transpose(image).convert("L")
    width, height = image.size
    if width < 1800:
        scale = max(2, round(1800 / max(1, width)))
        image = image.resize((width * scale, height * scale), Image.Resampling.LANCZOS)
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def _recognize_with_tesseract_python(image):
    if not _has_pytesseract():
        raise RuntimeError("未安装 pytesseract")
    tesseract_path = _find_tesseract()
    if not tesseract_path:
        raise RuntimeError("未找到 tesseract.exe")

    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    try:
        return pytesseract.image_to_string(image, lang="chi_sim+eng", config="--psm 6")
    except Exception:
        return pytesseract.image_to_string(image, config="--psm 6")


def _recognize_with_tesseract_cli(image):
    tesseract_path = _find_tesseract()
    if not tesseract_path:
        raise RuntimeError("未找到 tesseract.exe")

    image_path = _save_temp_png(image)
    try:
        for language in ("chi_sim+eng", "eng"):
            command = [tesseract_path, str(image_path), "stdout", "-l", language, "--psm", "6"]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=45,
                creationflags=_creation_flags(),
            )
            if completed.returncode == 0 and completed.stdout.strip():
                return completed.stdout
        raise RuntimeError("Tesseract 未返回有效文字")
    finally:
        _safe_unlink(image_path)


def _recognize_with_windows_ocr(image):
    if not _windows_ocr_supported():
        raise RuntimeError("当前系统不支持 Windows OCR")

    image_path = _save_temp_png(image)
    script_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", encoding="utf-8-sig", delete=False) as script_file:
            script_file.write(WINDOWS_OCR_SCRIPT)
            script_path = Path(script_file.name)

        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(image_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=45,
            creationflags=_creation_flags(),
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "Windows OCR 调用失败").strip())
        try:
            import base64

            return base64.b64decode(completed.stdout.strip()).decode("utf-8", "ignore")
        except Exception:
            return completed.stdout
    finally:
        _safe_unlink(image_path)
        if script_path:
            _safe_unlink(script_path)


def _save_temp_png(image):
    temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_path = Path(temp.name)
    temp.close()
    image.save(temp_path)
    return temp_path


def _safe_unlink(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def _creation_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def _clean_ocr_text(text):
    text = str(text or "").replace("\r", "\n")
    text = re.sub(r"[|｜]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _normalize_line(line):
    line = str(line or "").strip()
    line = line.replace("：", ":").replace("—", "-").replace("－", "-").replace("～", "-").replace("~", "-")
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"(\d{1,2})\s*[:.点时]\s*([0-5]\d)", r"\1:\2", line)
    return line


def _is_useful_line(line):
    if len(line) < 2:
        return False
    lowered = line.lower()
    noise_words = ("课程表", "节次", "时间", "星期", "周次", "教师", "学分", "备注")
    if len(line) <= 6 and any(word in line for word in noise_words):
        return False
    return lowered not in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def _extract_weekday(line):
    lowered = line.lower()
    for alias, name in WEEKDAY_ALIASES.items():
        if alias in line or alias in lowered:
            return name
    return ""


def _line_is_day_header(line):
    day = _extract_weekday(line)
    if not day:
        return ""
    compact = re.sub(r"[\s:：\-]", "", line.lower())
    aliases = [alias for alias, name in WEEKDAY_ALIASES.items() if name == day]
    if any(compact == alias.lower() for alias in aliases):
        return day
    return ""


def _extract_time(line):
    match = re.search(r"([01]?\d|2[0-3])[:.点时]([0-5]\d)", line)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    period = re.search(r"第?\s*(\d{1,2})(?:\s*[-到至]\s*(\d{1,2}))?\s*节", line)
    if period:
        start = int(period.group(1))
        return PERIOD_STARTS.get(start, "08:00")
    return ""


def _extract_location(line):
    line = str(line or "").replace("计亞实验室", "计算实验室").replace("计亚实验室", "计算实验室")
    patterns = [
        r"((?:24|25|31|33|34|36)\d{2}(?:云平台综合实训室|智能与分布计算实验室|软件架构实验室))",
        r"(?:地点|教室|地点:|教室:)[: ]*([\w\u4e00-\u9fa5-]{2,24})",
        r"((?:教学楼|实验楼|综合楼|行政楼|图书馆|体育馆|综合馆|实验室|实训室|机房|教室)[A-Za-z0-9\u4e00-\u9fa5-]{0,12})",
        r"([A-Z]?\d{3,4}[A-Z]?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1).strip()
    return ""


def _extract_title(line):
    canonical = _canonical_course_title(line)
    if canonical:
        return canonical
    title = line
    for alias in sorted(WEEKDAY_ALIASES, key=len, reverse=True):
        title = re.sub(re.escape(alias), " ", title, flags=re.IGNORECASE)
    title = re.sub(r"([01]?\d|2[0-3])[:.点时]([0-5]\d)(\s*[-到至]\s*([01]?\d|2[0-3])[:.点时]([0-5]\d))?", " ", title)
    title = re.sub(r"第?\s*\d{1,2}(?:\s*[-到至]\s*\d{1,2})?\s*节", " ", title)
    title = re.sub(r"(?:地点|教室)[: ]*[\w\u4e00-\u9fa5-]{2,24}", " ", title)
    title = re.sub(r"(?:教学楼|实验楼|综合楼|行政楼|图书馆|体育馆|实验室|机房|教室)[A-Za-z0-9\u4e00-\u9fa5-]{0,12}", " ", title)
    title = re.sub(r"\b[A-Z]?\d{3,4}[A-Z]?\b", " ", title)
    title = re.sub(r"[？?\[\]（）()【】,:：|]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if not re.search(r"[\u4e00-\u9fa5A-Za-z]", title):
        return ""
    if len(title) > 40:
        title = title[:40]
    return title


def _looks_like_header(title):
    header_words = ("星期", "周一", "周二", "周三", "周四", "周五", "周六", "周日", "时间", "节次")
    return any(word == title or title.startswith(word) and len(title) <= 8 for word in header_words)


def _infer_time_by_count(courses, day):
    same_day_count = sum(1 for course in courses if course.get("day") == (day or "每天"))
    period = [1, 3, 5, 7, 9, 11][same_day_count % 6]
    return PERIOD_STARTS.get(period, "08:00")


def _dedupe_courses(courses):
    seen = set()
    result = []
    for course in courses:
        key = (course.get("day"), course.get("time"), course.get("title"), course.get("location"))
        if key in seen:
            continue
        seen.add(key)
        result.append(course)
    return result[:40]

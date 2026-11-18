"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |
"""
from collections import defaultdict
from pathlib import Path

import yaml

from ..common import ERROR, parse_yolo_line


def fix(ds, issues, cfg):
    fixes = []
    # Chỉ xử lý các lỗi có severity ERROR
    err_issues = [i for i in issues if i.severity == ERROR or i.severity == "error"]
    if not err_issues:
        return fixes

    # 1. BAD_CLASS_NAME (cấp data.yaml)
    yaml_errs = [i for i in err_issues if i.code == "BAD_CLASS_NAME"]
    if yaml_errs:
        before_names = ""
        if ds.yaml_path.exists():
            try:
                data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
                before_names = str(data.get("names", ""))
            except Exception:
                data = {}
        else:
            data = {}
        data["names"] = list(cfg["classes"])
        ds.yaml_path.parent.mkdir(parents=True, exist_ok=True)
        ds.yaml_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        fixes.append({
            "image": "data.yaml",
            "line": "",
            "action": "rename_classes",
            "before": before_names,
            "after": str(cfg["classes"]),
        })

    # 2. Xoá ảnh + nhãn: DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE
    remove_codes = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}
    removed_stems = set()
    for i in err_issues:
        if i.code in remove_codes or i.code.startswith("DUP_IMAGE_"):
            stem = i.image
            if stem not in removed_stems:
                removed_stems.add(stem)
                img_p = ds.image_path(stem)
                if img_p and img_p.exists():
                    img_p.unlink()
                else:
                    for ext in [".jpg", ".jpeg", ".png", ".JPG", ".PNG"]:
                        p = ds.images_dir / f"{stem}{ext}"
                        if p.exists():
                            p.unlink()
                lbl_p = ds.label_path(stem)
                if lbl_p and lbl_p.exists():
                    lbl_p.unlink()
                ds._size_cache.pop(stem, None)
                fixes.append({
                    "image": stem,
                    "line": "",
                    "action": "remove_image",
                    "before": i.code,
                    "after": "(đã xoá ảnh và nhãn)",
                })

    # 3. MISSING_LABEL_FILE: máy không bịa nhãn, chuyển người gán
    missing_stems = set()
    for i in err_issues:
        if i.code == "MISSING_LABEL_FILE":
            stem = i.image
            if stem not in removed_stems and stem not in missing_stems:
                missing_stems.add(stem)
                fixes.append({
                    "image": stem,
                    "line": "",
                    "action": "needs_label",
                    "before": "(không có file)",
                    "after": "chuyển người gán",
                })

    # 4. Gom lỗi cấp dòng theo file nhãn (chỉ trên những ảnh chưa bị xoá)
    line_errs_by_stem = defaultdict(list)
    drop_codes = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
    for i in err_issues:
        if i.line is not None and i.image not in removed_stems:
            line_errs_by_stem[i.image].append(i)

    for stem in sorted(line_errs_by_stem):
        lbl_p = ds.label_path(stem)
        if not lbl_p.exists():
            continue

        raw_lines = lbl_p.read_text(encoding="utf-8", errors="replace").splitlines()
        line_issues_map = defaultdict(list)
        for i in line_errs_by_stem[stem]:
            line_issues_map[i.line].append(i)

        line_actions = {}
        for line_no, iss_list in line_issues_map.items():
            if line_no < 1 or line_no > len(raw_lines):
                continue

            line_text = raw_lines[line_no - 1]
            has_drop = any(i.code in drop_codes for i in iss_list)

            if has_drop:
                line_actions[line_no] = {
                    "action": "drop_line",
                    "before": line_text,
                    "after": "(đã xoá)",
                }
            else:
                out_of_img = [i for i in iss_list if i.code == "BOX_OUT_OF_IMAGE"]
                if out_of_img:
                    try:
                        cls_id, cx, cy, w, h = parse_yolo_line(line_text)
                        x1, y1 = cx - w / 2.0, cy - h / 2.0
                        x2, y2 = cx + w / 2.0, cy + h / 2.0
                        nx1, nx2 = max(0.0, min(1.0, x1)), max(0.0, min(1.0, x2))
                        ny1, ny2 = max(0.0, min(1.0, y1)), max(0.0, min(1.0, y2))
                        nw, nh = nx2 - nx1, ny2 - ny1
                        if nw <= 0.0 or nh <= 0.0:
                            line_actions[line_no] = {
                                "action": "drop_line",
                                "before": line_text,
                                "after": "(đã xoá vì box nằm hẳn ngoài ảnh)",
                            }
                        else:
                            ncx = (nx1 + nx2) / 2.0
                            ncy = (ny1 + ny2) / 2.0
                            new_line = f"{int(cls_id)} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                            line_actions[line_no] = {
                                "action": "clip_box",
                                "before": line_text,
                                "after": new_line,
                            }
                    except Exception:
                        line_actions[line_no] = {
                            "action": "drop_line",
                            "before": line_text,
                            "after": "(đã xoá dòng lỗi)",
                        }

        new_lines = []
        for line_no, line_text in enumerate(raw_lines, 1):
            if line_no in line_actions:
                act = line_actions[line_no]
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": act["action"],
                    "before": act["before"],
                    "after": act["after"],
                })
                if act["action"] == "clip_box":
                    new_lines.append(act["after"])
            else:
                new_lines.append(line_text)

        lbl_p.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")

    return fixes

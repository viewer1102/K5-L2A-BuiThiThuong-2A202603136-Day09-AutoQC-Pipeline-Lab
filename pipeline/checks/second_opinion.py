"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    issues = []
    so_cfg = cfg.get("second_opinion", {})
    conf_thresh = so_cfg.get("conf", 0.25)
    min_area_px = so_cfg.get("min_area_px", 600)
    fp_conf = so_cfg.get("fp_conf", 0.1)
    iou_missing = so_cfg.get("iou_missing", 0.3)
    iou_match = so_cfg.get("iou_match", 0.5)
    iou_loose = so_cfg.get("iou_loose", 0.5)

    for img_p in ds.image_files():
        stem = img_p.stem
        if stem not in preds:
            continue
        if not ds.label_path(stem).exists():
            continue
        img_size = ds.image_size(stem)
        if not img_size:
            continue
        W, H = img_size

        raw_lines = ds.read_label_lines(stem)
        if raw_lines is None:
            continue

        valid_label_lines = []
        for line_no, text in raw_lines:
            try:
                c, x, y, w, h = parse_yolo_line(text)
                if 0 <= c < len(ds.classes):
                    valid_label_lines.append((line_no, c, (x, y, w, h)))
            except ValueError:
                continue

        valid_boxes = [(c, box) for _, c, box in valid_label_lines]
        stem_preds = preds.get(stem, [])

        # 1. Kiểm tra các dự đoán của model (MISSING, LOOSE_BOX, WRONG_CLASS)
        for p in stem_preds:
            p_cls, p_conf, p_cx, p_cy, p_w, p_h = p[0], p[1], p[2], p[3], p[4], p[5]
            if p_conf < conf_thresh:
                continue
            area_px = (p_w * W) * (p_h * H)
            if area_px < min_area_px:
                continue

            p_box = (p_cx, p_cy, p_w, p_h)
            cands = []
            for l_cls, l_box in valid_boxes:
                iou = iou_xywh(p_box, l_box)
                if iou >= iou_missing:
                    cands.append((l_cls, iou))

            cls_name = ds.classes[p_cls] if 0 <= p_cls < len(ds.classes) else f"lớp {p_cls}"

            if not cands:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"model phát hiện {cls_name} (conf={p_conf:.2f}) nhưng nhãn thiếu",
                        line=None,
                        extra={"conf": p_conf},
                    )
                )
            else:
                same_cands = [iou for l_cls, iou in cands if l_cls == p_cls]
                if same_cands:
                    best_same_iou = max(same_cands)
                    if best_same_iou < iou_loose:
                        issues.append(
                            Issue(
                                "second_opinion",
                                WARN,
                                "POSSIBLE_LOOSE_BOX",
                                stem,
                                f"box nhãn {cls_name} lỏng/lệch (IoU={best_same_iou:.2f} < {iou_loose})",
                                line=None,
                                extra={"conf": p_conf, "iou": best_same_iou},
                            )
                        )
                else:
                    diff_cands = [iou for l_cls, iou in cands if l_cls != p_cls]
                    if diff_cands:
                        best_diff_iou = max(diff_cands)
                        if best_diff_iou >= iou_match:
                            issues.append(
                                Issue(
                                    "second_opinion",
                                    WARN,
                                    "POSSIBLE_WRONG_CLASS",
                                    stem,
                                    f"model phát hiện {cls_name} (conf={p_conf:.2f}), nghi gán nhầm lớp",
                                    line=None,
                                    extra={"conf": p_conf, "iou": best_diff_iou},
                                )
                            )

        # 2. Kiểm tra các dòng nhãn có thể là false positive (POSSIBLE_FALSE_POS)
        # Xét các dự đoán có conf >= fp_conf (không lọc diện tích)
        fp_preds = [p for p in stem_preds if p[1] >= fp_conf]
        for line_no, l_cls, l_box in valid_label_lines:
            is_fp = True
            for p in fp_preds:
                p_box = (p[2], p[3], p[4], p[5])
                if iou_xywh(l_box, p_box) >= iou_missing:
                    is_fp = False
                    break
            if is_fp:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"box nhãn không khớp vật nào model phát hiện",
                        line=line_no,
                        extra={"line": line_no},
                    )
                )

    return issues

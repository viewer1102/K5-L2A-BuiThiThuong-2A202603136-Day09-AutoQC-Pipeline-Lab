"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    issues = []
    fmt_cfg = cfg.get("label_format", {})
    overflow_tol = fmt_cfg.get("overflow_tol", 0.0)
    min_box_px = fmt_cfg.get("min_box_px", 12)
    max_box_frac = fmt_cfg.get("max_box_frac", 0.95)
    dup_box_iou = fmt_cfg.get("dup_box_iou", 0.9)

    for lf in ds.label_files():
        stem = lf.stem
        lines = ds.read_label_lines(stem)
        if not lines:
            continue

        img_size = ds.image_size(stem)
        valid_boxes_seen = []

        for line_no, text in lines:
            try:
                cls_id, cx, cy, w, h = parse_yolo_line(text)
            except ValueError:
                issues.append(
                    Issue("label_format", ERROR, "BAD_FORMAT", stem, "sai định dạng dòng YOLO (cần 5 số)", line=line_no)
                )
                continue

            if cls_id < 0 or cls_id >= len(ds.classes):
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BAD_CLASS_ID",
                        stem,
                        f"ID lớp {cls_id} ngoài phạm vi 0..{len(ds.classes)-1}",
                        line=line_no,
                    )
                )
                continue

            if w <= 0 or h <= 0:
                issues.append(
                    Issue("label_format", ERROR, "BOX_ZERO", stem, f"kích thước box <= 0 (w={w}, h={h})", line=line_no)
                )
                continue

            # Kiểm tra tràn ảnh
            x1 = cx - w / 2.0
            y1 = cy - h / 2.0
            x2 = cx + w / 2.0
            y2 = cy + h / 2.0
            max_overflow = max(-x1, x2 - 1.0, -y1, y2 - 1.0)
            if max_overflow > overflow_tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn mép ảnh quá ngưỡng ({max_overflow:.4f} > {overflow_tol})",
                        line=line_no,
                        extra={"overflow": max_overflow},
                    )
                )

            # Kiểm tra trùng box (DUP_BOX) với các box hợp lệ trước đó trong cùng file
            curr_box = (cx, cy, w, h)
            for prev_cls, prev_box, _ in valid_boxes_seen:
                if prev_cls == cls_id and iou_xywh(curr_box, prev_box) > dup_box_iou:
                    issues.append(
                        Issue(
                            "label_format",
                            ERROR,
                            "DUP_BOX",
                            stem,
                            f"box trùng với một box trước đó (IoU > {dup_box_iou})",
                            line=line_no,
                        )
                    )
                    break

            valid_boxes_seen.append((cls_id, curr_box, line_no))

            # Kiểm tra BOX_TINY
            if img_size:
                img_w, img_h = img_size
                short_px = min(w * img_w, h * img_h)
                if short_px < min_box_px:
                    issues.append(
                        Issue(
                            "label_format",
                            WARN,
                            "BOX_TINY",
                            stem,
                            f"cạnh ngắn của box ({short_px:.1f}px) < {min_box_px}px",
                            line=line_no,
                            extra={"short_px": short_px},
                        )
                    )

            # Kiểm tra BOX_HUGE
            if w * h > max_box_frac:
                issues.append(
                    Issue(
                        "label_format",
                        WARN,
                        "BOX_HUGE",
                        stem,
                        f"diện tích box ({w*h:.3f}) > {max_box_frac}",
                        line=line_no,
                    )
                )

    return issues

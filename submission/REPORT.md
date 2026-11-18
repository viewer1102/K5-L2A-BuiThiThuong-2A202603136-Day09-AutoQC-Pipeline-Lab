# Báo cáo Day 09 — Bùi Thị Thường:

## 1. Kết luận trước
Pipeline đưa ra kết luận **Hold** (mã thoát 10). Lô dữ liệu đầu vào gồm **224 ảnh thô**, qua bước tiếp nhận (intake) đã loại bỏ **21 ảnh** (8 ảnh trùng byte, 3 ảnh trùng gần đúng, 5 ảnh rò rỉ tập test/val, 3 ảnh kích thước nhỏ dưới 250px và 2 ảnh hỏng không đọc được). Nhận **203 ảnh** vào quy trình QC và xuất ra **203 ảnh** tại `submission/export/clean_v1/` (dưới dạng bản nháp để thử nghiệm).

Lý do giữ ở trạng thái Hold: Toàn bộ lỗi bắt buộc nghiêm trọng đã được giải quyết triệt để (`n_errors = 0`), tuy nhiên tỷ lệ ảnh còn cảnh báo ngữ nghĩa chưa được người duyệt là **21.67% (44/203 ảnh)**, vượt quá ngưỡng an toàn **10.00%** (`warn_ratio_hold = 0.10`).

## 2. Lỗi và phân việc
Dưới đây là thống kê toàn bộ 228 lỗi/cảnh báo được phát hiện ở vòng QC 1 (`02_error_list_v1.csv`):

| Mã lỗi | Số lượng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy (autofix) | Trùng từng byte (khớp MD5); máy tự động loại bỏ an toàn để tránh trùng lặp dữ liệu. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (autofix) | Box tràn ra ngoài mép ảnh; máy tự động cắt (clip) về [0, 1] hoặc xoá dòng nếu box nằm hẳn ngoài ảnh. |
| `DUP_BOX` | 7 dòng | Máy (autofix) | Hai box cùng lớp có IoU > 0.9; máy tự động xoá box trùng lặp xuất hiện ở dòng sau. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (hàng đợi) | Ảnh không có file nhãn đi kèm; máy tuyệt đối không được tự bịa nhãn, phải chuyển người gán (`needs_label`). |
| `BAD_CLASS_ID` | 6 dòng | Máy (autofix) | ID lớp ngoài phạm vi 0..3 (ví dụ ID 93); máy tự xoá dòng lỗi vì sai cú pháp. |
| `LEAK_TEST` | 5 ảnh | Máy (autofix) | Ảnh trùng với tập test hoặc gold_val; máy tự động xoá để chống rò rỉ dữ liệu (metric đẹp giả). |
| `BOX_ZERO` | 4 dòng | Máy (autofix) | Chiều rộng hoặc chiều cao box bằng 0; máy tự động xoá dòng vì box không có diện tích. |
| `BAD_SIZE` | 3 ảnh | Máy (autofix) | Cạnh ngắn ảnh nhỏ hơn 250px; máy loại ảnh vì không đạt độ phân giải yêu cầu của dự án. |
| `DUP_IMAGE_NEAR` | 3 ảnh | Máy (autofix) | Ảnh gần trùng qua perceptual hash (khoảng cách Hamming ≤ 8); máy tự động loại ảnh biến thể. |
| `BAD_FORMAT` | 3 dòng | Máy (autofix) | Dòng nhãn không đủ 5 cột số hoặc chứa ký tự lạ/NaN; máy tự động xoá dòng sai cú pháp. |
| `CORRUPT_IMAGE` | 2 ảnh | Máy (autofix) | File ảnh bị cắt cụt/hỏng không thể load dữ liệu; máy tự động loại bỏ. |
| `BAD_CLASS_NAME` | 2 | Máy (autofix) | Tên lớp trong `data.yaml` bị viết hoa sai; máy tự ghi lại đúng chuẩn `[car, person, truck, bus]`. |
| `POSSIBLE_MISSING` | 68 cảnh báo | Người (hàng đợi) | Model yolo26l thấy vật thể nhưng nhãn thiếu; cần mắt người xác nhận có phải vật thật hay báo động giả. |
| `POSSIBLE_LOOSE_BOX` | 31 cảnh báo | Người (hàng đợi) | Box nhãn vẽ quá lỏng/lệch so với vật thể (IoU < 0.5); cần người chỉnh lại tọa độ mép box. |
| `POSSIBLE_FALSE_POS` | 29 cảnh báo | Người (hàng đợi) | Box nhãn không khớp vật thể nào model phát hiện; cần người kiểm tra xem nhãn vẽ thừa hay vật khó. |
| `POSSIBLE_WRONG_CLASS` | 18 cảnh báo | Người (hàng đợi) | Cùng vị trí nhưng nhãn khác lớp model (vd. xe tải gán nhầm thành bus); cần người phân định ngữ nghĩa. |
| `EMPTY_LABEL` | 12 ảnh | Người (hàng đợi) | File nhãn rỗng 0 byte; cần người kiểm tra đây là ảnh nền (background) hay bị sót nhãn. |
| `BOX_TINY` | 6 box | Người (hàng đợi) | Cạnh ngắn box < 12px; cần người kiểm tra xem vật quá nhỏ có cần gán theo guideline không. |
| `CLASS_RARE` | 4 cảnh báo | Người (hàng đợi) | Lớp xuất hiện quá ít trong lô; cảnh báo mất cân bằng dữ liệu cho người quản lý dataset. |
| `BOX_HUGE` | 3 box | Người (hàng đợi) | Box bao phủ trên 95% diện tích ảnh; cần người xem lại có vẽ bao cả nền không. |

**Giải thích hàng đợi `05_review_queue.csv`:**
* Hàng đợi có tổng cộng **130 ảnh** cần xem xét. Thứ tự ưu tiên được tính dựa trên tổng trọng số rủi ro:
  * Đứng đầu là các ảnh có nhiều lỗi kết hợp (vừa bị máy cắt/xoá dòng, vừa có cảnh báo sai lớp và thiếu nhãn như `img_0020` priority 14.528, `img_0185` priority 10.052).
  * Ngay tiếp theo là toàn bộ **6 ảnh thiếu file nhãn** (`img_0031`, `img_0053`, `img_0126`, `img_0135`, `img_0170`, `img_0219`) được gán trọng số ưu tiên tối đa `NEEDS_LABEL = 10.0` để ép người duyệt phải gán nhãn trước.
* Với ngân sách duyệt **80 ảnh**, người duyệt mô phỏng đã xử lý thành công toàn bộ 6 ảnh thiếu nhãn (đưa số lỗi bắt buộc về 0) và sửa hầu hết các lỗi ngữ nghĩa nghiêm trọng nhất (`WRONG_CLASS`, `MISSING_BOX`). Còn lại 50 ảnh trong hàng đợi (trong đó 44 ảnh còn cảnh báo nhẹ), chiếm 21.67% tổng số ảnh.

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **8** | `DUP_IMAGE_NEAR`: `1.00 / 0.50` → **`1.00 / 0.67`** (F1: 0.67 → 0.80) | `phash_dist` là lỗi bắt buộc tự động xóa ảnh nên ưu tiên Precision tuyệt đối 1.00. Ngưỡng 8 giúp tăng Recall từ 50% lên 67% mà vẫn an toàn. Không chọn ngưỡng 16 vì khoảng cách 16 bit là quá lỏng, dễ xóa nhầm ảnh thật trên dữ liệu lớn. |
| `second_opinion.conf` | 0.25 | **0.5** | `POSSIBLE_MISSING`: `0.50 / 1.00` → **`0.57 / 1.00`** (F1: 0.67 → 0.73) | Ngưỡng cảnh báo cho người cần cân đối để hàng đợi không tràn ngân sách 80 ảnh. Mức 0.5 giúp tăng Precision từ 0.50 lên 0.57 (giảm báo động giả từ 8 xuống 6 ca) trong khi vẫn giữ Recall bắt thiếu nhãn đạt 100%. Không tăng lên 0.7–0.8 vì sẽ làm Recall rớt xuống 75%–88%. |

**Điểm calibration có thể đánh lừa:**
Tập `data/calib/` chỉ có **39 ảnh**, kích thước mẫu rất nhỏ (chẳng hạn lỗi gần trùng `DUP_IMAGE_NEAR` chỉ có đúng 6 ca chèn). Do đó, mỗi bức ảnh đúng/sai làm metric nhảy bước lớn (1 ca tương đương ~16.7% recall).
Nếu nhìn vào bảng sweep thấy `phash_dist = 16` cho F1 cao nhất (0.91, bắt được 5/6 ca) mà vội chọn 16 thì trên tập `raw` 203 ảnh, khoảng cách Hamming 16 sẽ khiến các bức ảnh có bố cục đường phố tương tự nhau (nhưng góc máy hoặc xe cộ khác nhau) bị phán nhầm là ảnh trùng và bị máy xóa oan. Việc giữ ở mức 8 đảm bảo tính tổng quát và an toàn cao hơn cho dữ liệu thật.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**(a) Thực nghiệm chứng minh Gate chặn đúng:**
* Khi chạy thử nghiệm với `--budget 0` (giả định không có người duyệt gán nhãn):
  ```powershell
  python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb
  ```
* Kết quả: Do ngân sách bằng 0, 6 ảnh thiếu file nhãn không được gán, dẫn đến còn nguyên 6 lỗi bắt buộc (`n_errors = 6`). Cửa chặn đã chặn đứng quy trình, đưa ra kết luận **REWORK** (mã thoát 20) và **hoàn toàn KHÔNG xuất dataset** (`work/exp_nb` không được tạo, `Test-Path work/exp_nb` trả về `False`). Điều này chứng minh cửa chặn hoạt động nghiêm ngặt, không cho phép phát hành dữ liệu khi còn lỗi cú pháp nghiêm trọng.

**(b) Các điểm mù pipeline KHÔNG bắt được (kèm bằng chứng):**
1. **Box lỏng nhẹ hoặc lệch góc nhưng IoU vẫn $\ge 0.5$**: Ngưỡng `iou_loose` được đặt là 0.5; nếu người gán nhãn vẽ lệch mép hoặc dư khoảng trống mà IoU với vật thể đạt 0.52 thì máy vẫn coi là khớp và không gắn cờ cảnh báo.
2. **Sai lệch ngữ nghĩa ở các ca khó mà cả model lớn cũng nhầm**: Khi gặp các vật thể bị che khuất một phần (occlusion) hoặc xe bán tải (pickup truck) dễ gây tranh cãi giữa `car` và `truck`, nếu model `yolo26l` cũng đưa ra dự đoán sai giống nhãn thì pipeline sẽ im lặng bỏ qua.
3. **Ảnh trùng bị biến đổi hình học phi tuyến**: Các trường hợp ảnh bị crop sâu trên 50%, xoay góc hoặc chỉnh sáng cục bộ làm thay đổi phân bố tần số khiến hàm pHash có khoảng cách Hamming vượt quá 8 thì máy không thể bắt được.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

### 5.1 Kết quả số liệu

Đã train bằng **YOLO26n (`yolo26n.pt`)**, **20 epochs**, với **2 seed (0, 1)** cho mỗi biến thể `raw` và `clean` (tổng cộng 4 lần train).

Bảng từ `submission/results/comparison.md`:

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 203 | 2 | 0.695 ± 0.010 | 0.482 ± 0.007 | 0.726 ± 0.005 | 0.619 ± 0.016 |

Chênh mAP50 (clean − raw) = **−0.031**.

### 5.2 Phân tích

**Câu 1 — Chênh `mAP50(clean) − mAP50(raw)` so với độ lệch chuẩn giữa các seed? Kết luận được đến đâu với 2 seed?**

mAP50 trung bình của raw là **0.7258 (SD 0.0002)** và clean là **0.6947 (SD 0.0095)**. Mức chênh **−0.0311** lớn hơn độ lệch chuẩn quan sát được ở cả hai nhóm; hai lần chạy raw đạt 0.7256/0.7259, còn clean đạt 0.6880/0.7015. Điều này cho thấy clean kém raw trong **cả hai seed đã thử**, nhưng **chỉ 2 seed/biến thể** không đủ để kết luận về ý nghĩa thống kê, độ ổn định qua nhiều seed hay quan hệ nhân quả. Không sử dụng quy tắc `3 × SD` như một kiểm định thống kê. Nên chạy thêm seed, ưu tiên so sánh ghép cặp cùng seed, và giữ nguyên tập test/cấu hình để đánh giá độ tin cậy.

**Câu 2 — `raw` thật sự train trên bao nhiêu ảnh?**

Tập raw được chuẩn bị với **224 file ảnh**, nhưng log Ultralytics của **cả seed 0 và seed 1** đều ghi `Using 213 train, 40 val images for fraction=1.0 at imgsz=640`: **213 ảnh thực sự được dùng trong tập train**. Như vậy có **11 ảnh đầu vào không được sử dụng**. Log có cảnh báo ảnh/nhãn hỏng (`ignoring corrupt image/label`), song chưa đủ để quy chính xác cả 11 ảnh cho từng mã lỗi nếu chưa đối chiếu toàn bộ log/cache. Tập clean có **203 ảnh đầu vào và 203 ảnh được dùng train** ở cả hai seed. Do đó, chênh lệch số ảnh train thực tế là **10 ảnh (213 so với 203)**, không phải 21 ảnh như khi so sánh file đầu vào.

**Câu 3 — `raw` có ảnh trùng tập test không? Nếu có, điểm bị thổi phồng bao nhiêu và kiểm bằng cách nào?**

Có. `submission/reports/02_error_list_v1.csv` ghi nhận **5 lỗi `LEAK_TEST`**:

| Ảnh raw | Ảnh trùng trong tập test |
|---|---|
| `img_0049` | `test/test_033.jpg` |
| `img_0101` | `test/test_039.jpg` |
| `img_0167` | `test/test_044.jpg` |
| `img_0174` | `test/test_085.jpg` |
| `img_0221` | `test/test_009.jpg` |

Đây là **nguy cơ data leakage** có thể khiến metric của raw lạc quan. Tuy nhiên, **chưa đo được raw bị thổi phồng bao nhiêu điểm mAP50**: không thể suy ra `+0.02–0.04` từ số ảnh trùng, cũng không thể mặc định cả 5 ảnh đều đã được dùng train sau khi Ultralytics lọc mẫu lỗi. Cần đối chiếu danh sách 213 ảnh train thực tế với 5 ảnh trên. Để định lượng ảnh hưởng, tạo một biến thể `raw_no_leak` chỉ loại các ảnh rò rỉ (giữ nguyên các yếu tố khác), train cùng seed/cấu hình, và đánh giá trên cùng tập test độc lập; so sánh `mAP50(raw) − mAP50(raw_no_leak)`. Với test hiện tại đã có nguy cơ trùng dữ liệu, nên ưu tiên một tập holdout mới không trùng lặp để kiểm chứng khả năng tổng quát hóa. **Chênh lệch −0.0311 giữa clean và raw không thể quy hoàn toàn cho leakage**, vì quá trình QC còn thay đổi nhiều thành phần khác.

**Câu 4 — Lớp nào (car/person/truck/bus) được lợi nhất? Giải thích bằng lỗi nhãn trong `02_error_list_v1`.**

Từ `ap50_per_class` của bốn file JSON, AP50 trung bình theo hai seed là:

| Lớp | Raw seed 0 / 1 | Clean seed 0 / 1 | Raw TB | Clean TB | Clean − Raw |
|---|---|---|---:|---:|---:|
| car | 0.7511 / 0.7239 | 0.7282 / 0.7396 | 0.7375 | 0.7339 | **−0.0036** |
| person | 0.8126 / 0.8315 | 0.8325 / 0.8031 | 0.8221 | 0.8178 | **−0.0043** |
| truck | 0.6574 / 0.6395 | 0.4813 / 0.5658 | 0.6485 | 0.5236 | **−0.1249** |
| bus | 0.6811 / 0.7087 | 0.7099 / 0.6975 | 0.6949 | 0.7037 | **+0.0088** |

**Bus là lớp duy nhất tăng AP50 trung bình sau QC** (+0.0088, tương đương +0.88 điểm phần trăm); **truck giảm mạnh nhất** (−0.1249). Không thể kết luận truck được lợi nhất như khi chỉ suy đoán từ thống kê box. Lưu ý: ở seed 0 bus tăng, nhưng ở seed 1 bus lại giảm nhẹ; vì vậy lợi ích trung bình của bus **chưa chứng minh được tính ổn định**.

`02_error_list_v1.csv` cho thấy các lỗi có khả năng ảnh hưởng chất lượng học: `BAD_CLASS_ID` (6 dòng), `BAD_CLASS_NAME` (2), `POSSIBLE_WRONG_CLASS` (18 cảnh báo), `POSSIBLE_MISSING` (68), `POSSIBLE_FALSE_POS` (29), cùng lỗi box. `class_stats.csv` của clean ghi car 100, person 574, truck 41 và bus 30 box; truck/bus có tương đối ít box nên dễ nhạy với thay đổi dữ liệu. **Đây là cơ chế giải thích khả dĩ, chưa phải bằng chứng nhân quả**: `BAD_CLASS_ID` không cho biết lớp đúng vốn là gì, còn cảnh báo `POSSIBLE_WRONG_CLASS` là nghi vấn từ model, không phải ground truth. Muốn khẳng định lỗi nào làm bus tăng hay truck giảm cần phân nhóm các lỗi theo lớp sau xác nhận của người duyệt và làm ablation/per-class evaluation.

**Câu 5 — `clean` còn lỗi gì? Hàng đợi có vượt ngân sách không? Đây đã là chặn trên của dữ liệu sạch chưa?**

Theo `07_error_list_v3.csv`, sau QC vẫn còn các cảnh báo:

| Mã cảnh báo | Số lượng | Ý nghĩa |
|---|---:|---|
| `POSSIBLE_MISSING` | 26 | Nghi thiếu nhãn, chưa được người duyệt xác nhận |
| `POSSIBLE_LOOSE_BOX` | 24 | Nghi box lỏng/lệch |
| `POSSIBLE_FALSE_POS` | 20 | Nghi box thừa |
| `BOX_TINY` | 7 | Box quá nhỏ theo ngưỡng guideline |
| `POSSIBLE_WRONG_CLASS` | 4 | Nghi sai lớp |
| `EMPTY_LABEL` | 4 | Cần xác nhận ảnh nền hay thiếu nhãn |
| `BOX_HUGE` | 3 | Box chiếm diện tích quá lớn |

Hàng đợi có **130 ảnh**, vượt ngân sách review **80 ảnh** nên còn **50 ảnh chưa được duyệt**. Sau review mô phỏng, `08_summary.json` ghi **0 lỗi bắt buộc**, nhưng còn **44/203 ảnh có cảnh báo chưa được duyệt (21.67%)**, vượt ngưỡng Hold 10% ⇒ **quyết định Hold**. Số cảnh báo có thể nhiều hơn số ảnh vì một ảnh có nhiều lỗi.

Vì vậy `clean_v1` chỉ là **dữ liệu được làm sạch một phần**, **không phải dữ liệu sạch tối ưu và không phải chặn trên (upper bound)** của hiệu năng sau QC. Đồng thời, việc review thêm cũng **không bảo đảm** mAP50 tăng; muốn biết phải hoàn tất review, chạy lại gate và train/đánh giá đối chứng.

### 5.3 Kết luận tổng thể

Trong 4 lần train (raw/clean × seed 0/1), **raw đạt mAP50 trung bình 0.7258, clean đạt 0.6947**, chênh **−0.0311**. Đây là kết quả thực nghiệm, không nên làm đẹp hay diễn giải thành clean tốt hơn. **Bus** là lớp duy nhất tăng AP50 trung bình (+0.0088), trong khi **truck** giảm mạnh (−0.1249); hai seed chưa đủ để khẳng định hiệu ứng ổn định.

Có ba giới hạn cần tách bạch: **(i)** raw chứa 5 ảnh bị gắn cờ `LEAK_TEST` nhưng chưa đo được mức ảnh hưởng thực sự; **(ii)** clean còn 44/203 ảnh chưa được duyệt hết cảnh báo và đang **Hold**; **(iii)** chỉ có 2 seed cho mỗi biến thể. Ngoài ra, raw thực train **213 ảnh**, clean **203 ảnh**, nên khác biệt về quy mô và nội dung dữ liệu cũng có thể ảnh hưởng kết quả.

**Hướng kiểm chứng tiếp:** xác nhận 5 ảnh leak có nằm trong 213 ảnh raw được train hay không; chạy đối chứng `raw_no_leak` với cùng seed/cấu hình; hoàn tất review và gate cho clean; bổ sung seed và so sánh AP theo lớp trên tập test độc lập. **Chưa có đủ bằng chứng để dự đoán clean sẽ ngang hoặc tốt hơn raw sau các bước này.**

## 6. Quyết định và ghi chú AI
**(a) Quyết định cuối cùng:**
Quyết định của lô dữ liệu là **Hold**.
* Để chuyển thành **Release**, cần:
  1. Cấp thêm ngân sách duyệt người (tăng từ 80 lên khoảng 130 ảnh) để đội ngũ chuyên viên duyệt nốt 50 ảnh còn lại trong hàng đợi `05_review_queue.csv`.
  2. Khi số ảnh có cảnh báo chưa duyệt giảm từ 44 xuống dưới 20 ảnh (đưa tỷ lệ cảnh báo $< 10.00\%$), pipeline sẽ tự động cấp quyền Release.

**(b) Ghi chú sử dụng AI:**
* **Prompt chính:** "Đọc kỹ docstring và các bài test TDD để triển khai 4 module (label_format, gate, autofix, second_opinion), đảm bảo xử lý ngoại lệ an toàn, bảo toàn số dòng gốc và không ghi đè dữ liệu raw."
* **Cách kiểm tra code AI:** Chạy toàn bộ 79 bài test tự động qua `pytest`, so sánh kết quả thực tế trên các ảnh trực quan hóa (`viz_labels.py`), và chạy thực nghiệm đối chứng cửa chặn `--budget 0`.
* **Một lần AI làm chưa tối ưu:** Ở module `autofix`, ban đầu việc xoá từng dòng trực tiếp theo chỉ số trong vòng lặp làm lệch số dòng của các lỗi phía sau trong cùng một file; sau đó đã được sửa chuẩn bằng cách gom toàn bộ lỗi theo file rồi ghi đè một lần duy nhất dựa trên số dòng gốc.

# Báo cáo Day 09 — <Họ và tên>, <MSHV>

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
Chưa chạy (Phần train so sánh là phần tùy chọn chấm riêng 15 điểm trên Google Colab; trong phạm vi phiên làm việc này, bài làm tập trung hoàn thiện và kiểm định toàn diện chất lượng của bộ kiểm tự động và pipeline theo đúng chuẩn rubric cốt lõi).

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

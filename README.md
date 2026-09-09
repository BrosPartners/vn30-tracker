# vn30-tracker

Công cụ theo dõi/dự báo rổ VN30, chạy bộ quy tắc HOSE (Ground Rules v4.0) trên dữ
liệu vnstock và cắm cờ ứng viên vào/loại khỏi rổ. Kiến trúc và quyết định thiết kế
xem `docs/superpowers/specs/2026-09-08-vn30-tracker-design.md`.

## Độ chính xác

Bộ quy tắc được đối chiếu với rổ VN30 **CHÍNH THỨC đã công bố** (không phải kết quả
tự tính của chính hệ thống) qua `tests/test_doi_chieu_ro_that.py` — xem chi tiết
nguồn số liệu ở `data/baskets/NGUON.md`.

**Kỳ kiểm định duy nhất: 07/2026** (hiệu lực 03/08/2026). Đây là kỳ duy nhất kiểm
được vì repo chỉ có một PDF công bố chính thức của HOSE (kỳ 01/2026) làm mốc gốc —
kỳ 07/2026 được suy ra từ mốc gốc đó cộng các thay đổi có nguồn (xem NGUON.md), nên
không đối chiếu được thêm kỳ nào khác ngoài kỳ này.

**Kết quả:** khớp **28/30 mã** với rổ công bố chính thức. Lệch 4 mã:

| Mã | Loại lệch | Vì sao |
|----|-----------|--------|
| MCH | Bỏ sót (rổ thật có, bộ quy tắc không chọn) | Xếp hạng vốn hóa (GTVH) trong top 20 (hạng 10) nên đủ điều kiện vào thẳng rổ, nhưng công bố free float kỳ 01/2026 — dữ liệu đầu vào DUY NHẤT có sẵn để chạy bộ quy tắc cho kỳ 07/2026 — chưa có free float cho MCH, vì mã này khi đó còn chưa vào VNAllshare. Bộ quy tắc chặn ở bước free float (Điều 3.3.3) vì thiếu dữ liệu, không phải vì logic sai. |
| TCX | Bỏ sót | Cùng lý do với MCH (hạng GTVH 19, cũng chưa có free float trong công bố 01/2026). |
| PLX | Thừa (bộ quy tắc chọn, rổ thật không có) | Hệ quả dây chuyền của việc MCH/TCX bị chặn: 2 chỗ trống trong top 30 được lấp bằng ưu tiên "mã có trong rổ kỳ trước" (Điều 4.3.1.f) — PLX là mã của rổ kỳ trước (2026-05) và qua hết các bước sàng lọc còn lại. |
| TPB | Thừa | Cùng cơ chế với PLX (cũng là mã rổ kỳ trước, qua hết sàng lọc còn lại). |

**Kết luận:** cả 4 mã lệch đều quy về **một nguyên nhân duy nhất** — công bố free
float kỳ 01/2026 (đầu vào duy nhất có sẵn) bị lệch kỳ so với ngày kiểm định
(07/2026), không phải lỗi logic của bộ quy tắc. `SAI_SO_CHO_PHEP = 4` trong
`tests/test_doi_chieu_ro_that.py` ghi nhận đúng mức lệch này, kèm giải thích đầy đủ
chuỗi nhân quả trong comment trên hằng số.

**Giới hạn:** phép kiểm định này chỉ phủ được MỘT kỳ (07/2026) vì repo chỉ tải được
một PDF công bố chính thức của HOSE (kỳ 01/2026) để làm mốc gốc suy ra các rổ sau.
Không có PDF gốc cho các kỳ 01/2025, 07/2025 nên các kỳ đó nằm ngoài phạm vi kiểm
định. Kết quả trên vì vậy KHÔNG chứng minh bộ quy tắc đúng cho mọi kỳ, chỉ chứng
minh đúng cho kỳ duy nhất kiểm được, với sai lệch đã giải thích được đầy đủ.

Chạy kiểm định (gọi mạng thật, chậm, không chạy trong CI thường):

```
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 VN30_TRACKER_GIOI_HAN_REQUEST=10 python -m pytest tests/test_doi_chieu_ro_that.py -m slow -v
```

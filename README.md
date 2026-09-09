# vn30-tracker

Công cụ theo dõi/dự báo rổ VN30, chạy bộ quy tắc HOSE (Ground Rules v4.0) trên dữ
liệu vnstock và cắm cờ ứng viên vào/loại khỏi rổ. Kiến trúc và quyết định thiết kế
xem `docs/superpowers/specs/2026-09-08-vn30-tracker-design.md`.

## Độ chính xác

Bộ quy tắc được đối chiếu với rổ VN30 **CHÍNH THỨC đã công bố** (không phải kết quả
tự tính của chính hệ thống) qua `tests/test_doi_chieu_ro_that.py` — xem chi tiết
nguồn số liệu ở `data/baskets/NGUON.md`.

**Kỳ kiểm định duy nhất: 07/2026** (hiệu lực 03/08/2026). Đây là kỳ duy nhất kiểm
được vì repo chỉ có PDF công bố chính thức của HOSE cho 2 kỳ (01/2026 và 07/2026) —
kỳ 07/2026 được kiểm trực tiếp bằng chính công bố free float đúng kỳ của nó, nên
không đối chiếu được thêm kỳ nào khác ngoài kỳ này.

**Kết quả:** khớp **TOÀN BỘ 30/30 mã** với rổ công bố chính thức, không còn lệch mã
nào. `SAI_SO_CHO_PHEP = 0` trong `tests/test_doi_chieu_ro_that.py`.

Trước đây (khi repo chỉ có PDF công bố kỳ 01/2026), phép kiểm định phải tạm dùng
free float của kỳ 01/2026 để đối chiếu rổ kỳ 07/2026 — lệch kỳ này khiến MCH và TCX
(khi đó chưa vào VNAllshare tại kỳ 01/2026 nên chưa có free float) bị chặn ở bước
free float (Điều 3.3.3), kéo theo PLX/TPB lấp vào qua Điều 4.3.1.f, khớp chỉ 28/30
mã. Sau khi bổ sung PDF công bố chính thức kỳ 07/2026
(`data/hose_index/cbtt_hose_index_2026-07.pdf`) và sửa lỗi đọc PDF ở
`collectors/hose_disclosure.py` (xác định vùng VNAllshare bằng tiêu đề mục thay vì
số trang hard-code — số trang khác nhau giữa các kỳ), free float đúng kỳ 07/2026 có
đủ MCH (0.20) và TCX (0.15), và kết quả đối chiếu khớp toàn bộ 30/30 mã.

**Giới hạn:** phép kiểm định này chỉ phủ được MỘT kỳ (07/2026) vì repo mới có PDF
gốc cho 2 kỳ (01/2026, 07/2026). Không có PDF gốc cho các kỳ 01/2025, 07/2025 nên
các kỳ đó nằm ngoài phạm vi kiểm định. Kết quả trên vì vậy KHÔNG chứng minh bộ quy
tắc đúng cho mọi kỳ, chỉ chứng minh đúng cho kỳ duy nhất kiểm được.

Chạy kiểm định (gọi mạng thật, chậm, không chạy trong CI thường):

```
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 VN30_TRACKER_GIOI_HAN_REQUEST=10 python -m pytest tests/test_doi_chieu_ro_that.py -m slow -v
```

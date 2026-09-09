# Nguồn của các file `data/baskets/*.json`

Mỗi file là mảng 30 mã của rổ VN30 **chính thức đã công bố** tại kỳ tương ứng
(dữ liệu chuẩn để đối chiếu ở `tests/test_doi_chieu_ro_that.py`, không phải kết
quả tự tính của bộ quy tắc).

## `2026-01.json` — SỐ GỐC, lấy trực tiếp từ PDF công bố chính thức

Nguồn: `data/hose_index/cbtt_hose_index_2026-01.pdf` (Công bố thông tin chính
thức của HOSE), đã bóc bằng `collectors/hose_disclosure.py` +
`scripts/cap_nhat_cbtt.py` → `data/hose_index/2026-01.yaml` (mục `vn30`).
Đây là kỳ **duy nhất** có PDF công bố gốc trong repo — các kỳ 01/2025 và
07/2025 dự kiến đối chiếu ban đầu không tìm được PDF nên bị loại khỏi phạm vi.

30 mã: ACB, BID, CTG, DGC, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MSN, MWG, PLX,
SAB, SHB, SSB, SSI, STB, TCB, TPB, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

## `2026-07.json` — SUY RA từ delta có nguồn báo, KHÔNG có PDF gốc

HOSE công bố thay đổi cơ cấu kỳ 07/2026 ngày 15/07/2026, hiệu lực từ
03/08/2026: **loại PLX và TPB, thêm MCH và TCX**. Không tìm được PDF công bố
chính thức kỳ này, nên rổ 07/2026 được suy ra bằng cách áp delta đó lên
`2026-01.json`:

    2026-07 = 2026-01 − {PLX, TPB} + {MCH, TCX}

30 mã: ACB, BID, CTG, DGC, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MCH, MSN, MWG,
SAB, SHB, SSB, SSI, STB, TCB, TCX, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

Nguồn của delta (báo chí, không phải PDF HOSE):
- https://vietstock.vn/2026/07/mch-tcx-vao-ro-vn30-3358-1466674.htm
- https://phapluatplus.baophapluat.vn/hose-cong-bo-danh-muc-vn30-ky-thang-7-2026.html

## Hệ quả cho việc kiểm định (xem `tests/test_doi_chieu_ro_that.py`)

- Free float dùng để chạy bộ quy tắc cho kỳ 07/2026 chỉ có bản công bố
  01/2026 (không có free float đúng kỳ 07/2026) — free float của MCH/TCX
  KHÔNG có trong công bố 01/2026 (hai mã này khi đó chưa vào VN30), nên
  bộ quy tắc **chắc chắn không thể dự báo MCH/TCX vào rổ** dù mọi logic khác
  đúng. Đây là giới hạn dữ liệu đã biết, không phải lỗi quy tắc.

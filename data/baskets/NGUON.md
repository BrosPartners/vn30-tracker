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

Các kỳ sau đây (2026-05, 2026-07) KHÔNG có PDF công bố gốc trong repo — được
SUY RA từ mốc gốc 2026-01 cộng dồn các thay đổi có nguồn báo/quyết định HOSE.
Cách suy ra này CHỈ ĐÚNG khi đã tính hết mọi thay đổi giữa các kỳ, kể cả điều
chỉnh GIỮA KỲ theo Điều 8 Ground Rules (không chỉ thay đổi ở các kỳ review định
kỳ 6 tháng) — bài học rút ra sau khi phát hiện thiếu chính xác điều chỉnh
13/5/2026 (xem mục dưới): trước khi dùng số suy ra làm dữ liệu chuẩn, phải rà
soát riêng các quyết định giữa kỳ, không được mặc định "giữa hai kỳ review
không có thay đổi nào".

## `2026-05.json` — SUY RA, có điều chỉnh GIỮA KỲ theo Điều 8

Ngày 06/5/2026 HOSE ra quyết định (hiệu lực **13/5/2026**) loại **DGC** khỏi
VN30 (và VN100, VNAllshare cùng 3 chỉ số khác), do DGC bị chuyển sang **diện
kiểm soát** vì chậm nộp báo cáo tài chính năm 2025 đã kiểm toán quá 30 ngày.
**BSR** thay thế, được đôn lên từ **vị trí ưu tiên số 1 trong danh mục dự
phòng** VN30. Đây là điều chỉnh giữa kỳ theo Điều 8 Ground Rules, KHÔNG phải
kỳ review định kỳ (kỳ review định kỳ gần nhất là 01/2026, gần nhất sau đó là
07/2026).

    2026-05 = 2026-01 − {DGC} + {BSR}

30 mã: ACB, BID, BSR, CTG, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MSN, MWG, PLX,
SAB, SHB, SSB, SSI, STB, TCB, TPB, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

Nguồn:
- https://baodautu.vn/dgc-bi-hose-loai-khoi-hang-loat-bo-chi-so-lon-bsr-the-cho-vao-vn30-d589225.html
- https://thitruongtaichinhtiente.vn/tai-co-cau-danh-muc-quy-etf-ky-quy-ii-2026-dgc-chinh-thuc-bi-loai-khoi-vn30-bsr-thay-the-82757.html

## `2026-07.json` — SUY RA từ delta review định kỳ có nguồn báo, áp lên mốc 2026-05

HOSE công bố thay đổi cơ cấu kỳ 07/2026 ngày 15/07/2026, hiệu lực từ
03/08/2026: **loại PLX và TPB, thêm MCH và TCX**. Không tìm được PDF công bố
chính thức kỳ này, nên rổ 07/2026 được suy ra bằng cách áp delta đó lên
`2026-05.json` (mốc liền kề trước đó, đã tính điều chỉnh giữa kỳ 13/5/2026) —
KHÔNG áp trực tiếp lên `2026-01.json` vì như vậy sẽ bỏ sót thay đổi DGC→BSR:

    2026-07 = 2026-05 − {PLX, TPB} + {MCH, TCX}

30 mã: ACB, BID, BSR, CTG, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MCH, MSN, MWG,
SAB, SHB, SSB, SSI, STB, TCB, TCX, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

Nguồn của delta (báo chí, không phải PDF HOSE):
- https://vietstock.vn/2026/07/mch-tcx-vao-ro-vn30-3358-1466674.htm
- https://phapluatplus.baophapluat.vn/hose-cong-bo-danh-muc-vn30-ky-thang-7-2026.html

## Hệ quả cho việc kiểm định (xem `tests/test_doi_chieu_ro_that.py`)

- Free float dùng để chạy bộ quy tắc cho kỳ 07/2026 chỉ có bản công bố
  01/2026 (không có free float đúng kỳ 07/2026) — free float của MCH/TCX
  KHÔNG có trong công bố 01/2026 (hai mã này khi đó chưa vào VNAllshare), nên
  bộ quy tắc **chắc chắn không thể dự báo MCH/TCX vào rổ** dù mọi logic khác
  đúng. Đây là giới hạn dữ liệu đã biết, không phải lỗi quy tắc.
- `previous_basket` dùng để kiểm kỳ 07/2026 phải là rổ **liền kề trước đó**
  (`2026-05`, đã tính điều chỉnh giữa kỳ), KHÔNG phải `2026-01` — nếu dùng
  `2026-01` thì Điều 4.3.1.f (ưu tiên mã có trong rổ kỳ trước) sẽ được kiểm với
  đầu vào sai (DGC thay vì BSR).

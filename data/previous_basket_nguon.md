# Nguồn của `data/previous_basket.json`

Rổ VN30 ghi trong `previous_basket.json` là rổ **đang hiệu lực tại thời điểm build**,
dùng làm "rổ kỳ trước" cho các phép so sánh của bộ quy tắc (buffer 20/40, kiểm tra
`in_previous_basket`).

## Rổ hiện dùng: kỳ 07/2026, hiệu lực từ 03/08/2026

30 mã: ACB, BID, CTG, DGC, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MCH, MSN, MWG, SAB,
SHB, SSB, SSI, STB, TCB, TCX, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

## Cách suy ra

Mốc neo là **công bố chính thức kỳ 01/2026 của HOSE**
(`data/hose_index/cbtt_hose_index_2026-01.pdf`, đã bóc bằng
`collectors/hose_disclosure.py`), gồm 30 mã VN30:

ACB, BID, CTG, DGC, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MSN, MWG, **PLX**, SAB,
SHB, SSB, SSI, STB, TCB, **TPB**, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

Kỳ tháng 7/2026 (hiệu lực 03/08/2026), HOSE công bố thay đổi cơ cấu: **loại PLX và
TPB, thêm MCH và TCX**. Áp thay đổi này lên danh mục kỳ 01/2026 ra đúng 30 mã ở
trên.

## Vì sao KHÔNG dùng file cũ (dựng từ Google Sheet người dùng)

File cũ ghi BSR có trong rổ VN30 — sai: theo công bố chính thức kỳ 01/2026, BSR chỉ
nằm trong **danh mục dự phòng** VN30 (`vn30_du_phong`), không nằm trong rổ chính
thức 30 mã. File cũ cũng thiếu DGC, vốn có mặt trong rổ chính thức từ kỳ 01/2026.

## Nguồn tham chiếu thay đổi kỳ 07/2026

- https://vietstock.vn/2026/07/mch-tcx-vao-ro-vn30-3358-1466674.htm
- https://phapluatplus.baophapluat.vn/hose-cong-bo-danh-muc-vn30-ky-thang-7-2026.html

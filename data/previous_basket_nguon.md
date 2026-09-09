# Nguồn của `data/previous_basket.json`

Rổ VN30 ghi trong `previous_basket.json` là rổ **đang hiệu lực tại thời điểm build**,
dùng làm "rổ kỳ trước" cho các phép so sánh của bộ quy tắc (buffer 20/40, kiểm tra
`in_previous_basket`).

## Rổ hiện dùng: kỳ 07/2026, hiệu lực từ 03/08/2026

30 mã: ACB, BID, BSR, CTG, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MCH, MSN, MWG, SAB,
SHB, SSB, SSI, STB, TCB, TCX, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

## Cách suy ra (đã sửa sau khi phát hiện bỏ sót điều chỉnh giữa kỳ)

Mốc neo là **công bố chính thức kỳ 01/2026 của HOSE**
(`data/hose_index/cbtt_hose_index_2026-01.pdf`, đã bóc bằng
`collectors/hose_disclosure.py`), gồm 30 mã VN30:

ACB, BID, CTG, **DGC**, FPT, GAS, GVR, HDB, HPG, LPB, MBB, MSN, MWG, **PLX**, SAB,
SHB, SSB, SSI, STB, TCB, **TPB**, VCB, VHM, VIB, VIC, VJC, VNM, VPB, VPL, VRE.

Bước 1 — điều chỉnh GIỮA KỲ ngày 13/5/2026 (Điều 8 Ground Rules, không phải kỳ
review định kỳ): HOSE loại **DGC** (chuyển sang diện kiểm soát do chậm nộp BCTC
2025 kiểm toán quá 30 ngày), thay bằng **BSR** (vị trí ưu tiên số 1 danh mục dự
phòng VN30) → ra `data/baskets/2026-05.json`.

Bước 2 — kỳ review định kỳ tháng 7/2026 (hiệu lực 03/08/2026): HOSE công bố
thay đổi cơ cấu **loại PLX và TPB, thêm MCH và TCX**. Áp lên kết quả bước 1
(KHÔNG áp trực tiếp lên bản 01/2026, vì như vậy bỏ sót thay đổi DGC→BSR) →
ra `data/baskets/2026-07.json`, cũng là rổ hiện dùng ở đây.

    previous_basket = 2026-01 − {DGC} + {BSR}   (buoc 1, hieu luc 13/5/2026)
                              − {PLX, TPB} + {MCH, TCX}   (buoc 2, hieu luc 3/8/2026)

## Bài học: đừng suy rổ hiện hành chỉ bằng cách cộng dồn thay đổi của các kỳ review định kỳ

Bản trước của file này suy trực tiếp `2026-01 − {PLX,TPB} + {MCH,TCX}` mà bỏ sót
điều chỉnh giữa kỳ 13/5/2026 → previous_basket chứa DGC (đã bị loại khỏi VN30 từ
13/5/2026) và thiếu BSR (đã vào rổ từ 13/5/2026). Rổ VN30 có thể thay đổi GIỮA
KỲ theo Điều 8 (mã bị đưa vào diện cảnh báo/kiểm soát bị loại ngay, mã dự phòng
số 1 thay thế ngay, không chờ kỳ review định kỳ tiếp theo) — mọi lần suy rổ từ
mốc gốc phải rà soát riêng các quyết định giữa kỳ, không chỉ cộng dồn kết quả
review 6 tháng.

## Vì sao KHÔNG dùng file cũ hơn nữa (dựng từ Google Sheet người dùng)

File cũ hơn ghi BSR có trong rổ nhưng KHÔNG qua bước suy luận có nguồn (chỉ chép
từ Google Sheet người dùng), và thiếu DGC/không giải thích được nguồn gốc thay
đổi. Bản hiện tại (ở trên) suy BSR ra từ đúng quyết định HOSE 06/5/2026 (hiệu lực
13/5/2026), có nguồn kiểm chứng được.

## Nguồn

- https://baodautu.vn/dgc-bi-hose-loai-khoi-hang-loat-bo-chi-so-lon-bsr-the-cho-vao-vn30-d589225.html
- https://thitruongtaichinhtiente.vn/tai-co-cau-danh-muc-quy-etf-ky-quy-ii-2026-dgc-chinh-thuc-bi-loai-khoi-vn30-bsr-thay-the-82757.html
- https://vietstock.vn/2026/07/mch-tcx-vao-ro-vn30-3358-1466674.htm
- https://phapluatplus.baophapluat.vn/hose-cong-bo-danh-muc-vn30-ky-thang-7-2026.html

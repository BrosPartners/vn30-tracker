# VN30 Tracker — Thiết kế

Ngày: 2026-09-08
Trạng thái: đã duyệt (chờ lập kế hoạch triển khai)

## 1. Mục tiêu

Theo dõi hằng ngày những cổ phiếu có khả năng **được thêm vào** hoặc **bị loại khỏi** rổ VN30
tại kỳ review kế tiếp (07/2026), thay cho Google Sheet nhập tay hiện nay
(`15ae9uVQ8QX0_xFBfD1ekSoNXnzpHtHudkjySOZ6B_eE`), và công bố dưới dạng một dashboard trong
cổng dữ liệu `bp-data-portal` của Bros Partners.

Câu hỏi trang web phải trả lời, theo thứ tự ưu tiên:

1. Kỳ tới **ai vào, ai ra**, và mỗi mã đang **vướng tiêu chí nào, thiếu bao nhiêu**.
2. Bảng xếp hạng đầy đủ top 50 để tra cứu.
3. Diễn biến thứ hạng/thanh khoản của từng mã theo thời gian (mức nhẹ: sparkline).

## 2. Vì sao không dùng tiếp Google Sheet

Sheet hiện tại có 5 tab: 1 tab bộ lọc (~106 mã), 1 tab tỷ trọng VN30, và 3 tab dán thô bảng giá
từ priceboard BSC. Ba vấn đề khiến nó không dùng lại được:

- **Cột KLGD/GTGD bình quân toàn `#N/A`** → tiêu chí thanh khoản, thứ thực sự quyết định
  hạng 21–40, chưa từng được tính.
- **Trùng dòng mâu thuẫn**: MCH (free float 30% vs 95%), VPL (3 dòng), BSR (2 dòng), TCX (3 dòng)
  — khác nhau cả free float lẫn ngày niêm yết.
- **Áp sai quy tắc 2.000/2.500 tỷ** (xem mục 3.2) — áp cho mọi mã thay vì chỉ mã free float < 10%.

Sheet vẫn hữu ích như tài liệu tham chiếu lịch sử, nhưng không phải nguồn của hệ thống mới.

## 3. Nguồn quy tắc

**Ground Rules for Management of the HOSE-Index Series, Version 4.0** — Quyết định
747/QĐ-SGDHCM ngày 30/12/2024, hiệu lực từ tháng 03/2025. Bản gốc tiếng Anh tải từ
`staticfile.hsx.vn`. Toàn bộ logic phải trích dẫn được về điều khoản cụ thể; mọi ngưỡng nằm
trong file cấu hình, không rải rác trong code.

### 3.1. Định nghĩa (Điều 3.1) — khác Sheet ở những chỗ quan trọng

| Ký hiệu | Định nghĩa gốc | Sheet đang làm |
|---|---|---|
| GTVH | Bình quân vốn hóa **hằng ngày trong 12 tháng** gần nhất tới ngày chốt dữ liệu. Mã niêm yết dưới 12 tháng: bình quân từ ngày niêm yết. | Vốn hóa tại một thời điểm |
| GTVH_f | GTVH × tỷ lệ free float | market cap × free float |
| GTGD | **Bình quân của trung vị** GTGD ngày theo từng tháng, trong 12 tháng. Gồm **khớp lệnh + thỏa thuận**. | không tính |
| GTGD_KL | Như GTGD nhưng **chỉ khớp lệnh** | không tính |
| KLGD_KL | Như trên, tính theo khối lượng | không tính |
| f | (SLCP lưu hành − CP hạn chế chuyển nhượng) / SLCP lưu hành | nhập tay từ DNSE |
| LNST | LNST từ BCTC **soát xét bán niên hoặc kiểm toán năm** gần nhất; công ty mẹ thì lấy LNST của cổ đông công ty mẹ trên BCTC hợp nhất | không tính |

Làm tròn free float (Điều 3.3.5): f ≤ 15% làm tròn lên bội số 1%; f > 15% làm tròn lên bội số 5%.

### 3.2. Thứ tự sàng lọc

Bộ máy chạy đúng 7 bước, **mỗi bước ghi lại lý do đỗ/trượt của từng mã**:

1. **Điều kiện tham gia (3.2)** — loại mã bị vi phạm công bố thông tin, kiểm soát, hạn chế
   giao dịch, tạm ngừng giao dịch trong 3 tháng tới ngày chốt dữ liệu (trừ tạm ngừng do sự kiện
   doanh nghiệp dưới 30 phiên); loại mã niêm yết HOSE **dưới 6 tháng**, trừ mã có GTVH thuộc
   **top 5** và đã niêm yết trên 3 tháng.
2. **Free float (3.3.3)** — f ≥ 10%: đạt. f < 10%: **không đạt**, trừ khi
   GTVH_f ≥ **2.000 tỷ** (mã đang trong rổ kỳ trước) hoặc ≥ **2.500 tỷ** (mã mới).
   *Đây là ngoại lệ cho mã free float thấp, không phải điều kiện chung — Sheet đang hiểu sai.*
3. **Thanh khoản (3.4)** — Turnover Ratio = GTGD / GTVH_f. Mã ngoài rổ < **0,05%**: loại.
   Mã đang trong rổ < **0,04%**: bị loại khỏi chỉ số.
   → Tập đi qua bước 1–3 chính là **VNAllshare**.
4. **VN30 4.3.1.a–b** — loại mã KLGD_KL < **300.000 cp**; rồi loại mã GTGD_KL < **30 tỷ**.
   Nếu chưa đủ 50 mã thì lấy tiếp theo GTGD_KL giảm dần cho đủ 50 (đồng hạng thì ưu tiên GTVH).
5. **VN30 4.3.1.c–d** — loại mã bị cảnh báo trong 3 tháng tính tới ngày chốt hoặc tới ngày hiệu lực;
   loại mã **LNST âm**. Chỉ xét BCTC có ý kiến kiểm toán chấp nhận toàn phần.
6. **VN30 4.3.1.e–f** — xếp GTVH giảm dần (đồng hạng ưu tiên GTGD_KL). Hạng ≤ **20**: vào thẳng.
   Hạng **21–40**: ưu tiên mã đã có trong rổ kỳ trước, sau đó tới mã mới, cho đủ 30 mã.
7. **VN30 4.3.1.g** — 5 mã GTVH lớn nhất còn lại = **danh sách dự phòng**.

Giới hạn tỷ trọng (Điều 7: 10% một mã, 15% nhóm liên quan, 40% cùng ngành GICS) **không ảnh hưởng
tư cách thành viên** — nằm ngoài phạm vi bản này.

### 3.3. Lịch review (Index Summary)

- Thay đổi rổ: **thứ Tư tuần thứ 3 của tháng 1 và tháng 7**.
- Điều chỉnh SLCP và free float: thứ Tư tuần thứ 3 của tháng 1, 4, 7, 10.
- Hiệu lực: **thứ Hai đầu tiên của tháng 2, 5, 8, 11**.

Trang web hiển thị đếm ngược tới ngày chốt dữ liệu và ngày hiệu lực kế tiếp.

## 4. Dữ liệu

### 4.1. Tự động (vnstock — đã kiểm chứng chạy được)

| Cần | Cách lấy | Đã xác nhận |
|---|---|---|
| Vũ trụ HOSE | `Listing().symbols_by_exchange()`, lọc `exchange=HOSE`, `type=stock` | 715 mã |
| Giá & khối lượng ngày | `Quote(symbol).history(interval='1D')` → `close`, `volume` | OK, 12 tháng |
| SLCP lưu hành | `shares_data.fetch_listed_shares_batch` (mượn từ `my-stock-dashboard`) | có sẵn |
| LNST (số liệu thô) | vnstock BCTC | cần xác nhận cờ kiểm toán bằng tay |

### 4.2. Nhập tay trong repo — `data/manual.yaml`, sửa qua git

Đúng quyết định của user: free float **không** scrape, để người xác nhận.

```yaml
VIC:
  free_float: 0.30          # nguồn + ngày cập nhật bắt buộc
  free_float_source: "DNSE 2026-09-05"
  listing_date: 2018-05
  warning_status: none      # none | warning | control | restricted | suspended
  lnst_positive: true
  audit_opinion: unqualified
```

Phạm vi bảo trì: **top 50 vốn hóa HOSE**. Thứ hạng GTVH vẫn tính trên **toàn bộ HOSE**;
chỉ free float và kết luận giới hạn trong top 50. Khi một mã lọt vào top 50 mà chưa có free float,
bot **cảnh báo trong output và trên web** ("thiếu dữ liệu free float"), không đoán.

### 4.3. Xấp xỉ phải công bố rõ trên web

1. **GTGD thiếu phần thỏa thuận** — quy tắc gốc tính cả khớp lệnh và thỏa thuận; vnstock chỉ có
   khối lượng khớp lệnh. Turnover Ratio vì vậy là **ước tính cận dưới**. Adapter tách riêng phần
   thỏa thuận để cắm nguồn khác sau mà không đụng bộ quy tắc.
2. **GTVH 12 tháng dùng SLCP hiện tại** cho toàn bộ chuỗi giá quá khứ (không có chuỗi SLCP lịch sử)
   → lệch với mã có phát hành thêm/chia thưởng trong 12 tháng qua. Ghi chú trên từng mã bị ảnh hưởng.
3. **Ý kiến kiểm toán** không đọc được bằng máy → cờ nhập tay, mặc định là "chưa xác nhận" và
   hiển thị như vậy chứ không mặc định là đạt.

## 5. Kiến trúc

Theo đúng khuôn các dashboard đang chạy của portal (`liquidity-crawler`, `hp-ship-schedule`):

```
BrosPartners/vn30-tracker  (repo mới)
├── collectors/         # vnstock → dữ liệu thô, có cache theo ngày
├── rules/              # bộ máy quy tắc — HÀM THUẦN, không I/O
│   ├── definitions.py  # GTVH, GTGD, GTGD_KL, KLGD_KL, turnover, làm tròn free float
│   ├── screens.py      # 7 bước của mục 3.2
│   └── thresholds.yaml # mọi con số ngưỡng, trích dẫn điều khoản
├── data/
│   ├── manual.yaml     # free float + cờ nhập tay
│   ├── latest.json     # kết quả mới nhất (web đọc file này)
│   └── history/YYYY-MM-DD.json
├── site/               # trang tĩnh, không framework, đồng bộ style portal
└── .github/workflows/refresh.yml   # cron 17:00 hằng ngày
```

Ranh giới rõ ràng: collector chỉ lấy số; `rules/` nhận vào một bảng số liệu và trả ra
rổ dự kiến + **lý do từng mã**, không biết gì về mạng hay file; `site/` chỉ đọc JSON.
Nhờ vậy bộ máy quy tắc test được độc lập, và đây cũng là phần dễ sai nhất.

Deploy: GitHub Pages của `vn30-tracker`, rồi gắn vào portal bằng **1 object trong
`bp-data-portal/dashboards.js`** (`id: "vn30"`, group "Thị trường") + **1 file `vn30.html`**
copy từ `vi-mo.html`. Portal không đọc và không sửa dữ liệu của repo này — giữ nguyên
nguyên tắc sẵn có của portal.

## 6. Màn hình

1. **Đầu trang** — kỳ review kế tiếp, ngày chốt dữ liệu, ngày hiệu lực, ngày cập nhật dữ liệu.
2. **Hai danh sách chính**:
   - *Ứng viên vào rổ* — mã ngoài VN30 đã qua hết bước 1–5 và có hạng GTVH ≤ 40.
   - *Nguy cơ bị loại* — mã trong VN30 trượt một bước bất kỳ, hoặc hạng GTVH > 40.
   Mỗi mã ghi **bước trượt và khoảng cách còn thiếu**: "GTGD_KL 24 tỷ — thiếu 6 tỷ so với ngưỡng 30 tỷ".
3. **Bảng đầy đủ top 50** — lọc/sắp xếp, đủ cột GTVH, hạng, f, GTVH_f, GTGD_KL, KLGD_KL,
   turnover, tháng niêm yết, LNST, kết luận.
4. **Chi tiết từng mã** — sparkline thứ hạng GTVH và GTGD_KL dựng từ `data/history/`
   (rỗng lúc mới chạy, dày lên theo ngày).
5. **Chân trang** — nêu rõ 3 xấp xỉ ở mục 4.3, dẫn nguồn quy tắc v4.0, và ghi đây là ước tính
   của Bros Partners chứ không phải công bố của HOSE.

## 7. Nghiệm thu

Thước đo chính: **tái tạo đúng rổ VN30 đã công bố** của kỳ **07/2025** và **01/2026** khi
chạy bộ máy trên dữ liệu tại ngày chốt tương ứng. Sai lệch mã nào phải giải thích được bằng
một trong ba xấp xỉ ở mục 4.3, hoặc là lỗi phải sửa.

Ngoài ra:
- Test đơn vị cho từng định nghĩa ở 3.1 (đặc biệt "bình quân của trung vị" và làm tròn free float)
  bằng số liệu dựng tay.
- Test cho từng bước sàng lọc, gồm các ca biên: f đúng 10%, mã top-5 niêm yết 4 tháng,
  turnover giữa 0,04% và 0,05% (khác nhau tùy mã có trong rổ hay không), rổ chưa đủ 50 mã sau bước b.
- Mã thiếu free float phải hiện "thiếu dữ liệu", không bao giờ bị đoán.

## 8. Ngoài phạm vi

- Tỷ trọng và capping factor (Điều 7) — chỉ ảnh hưởng trọng số, không ảnh hưởng thành viên.
- VNMidcap, VN100, VNSmallcap, chỉ số ngành.
- Cảnh báo qua Telegram/email khi có mã đổi trạng thái — cân nhắc sau khi chạy ổn định.
- Scrape free float tự động.

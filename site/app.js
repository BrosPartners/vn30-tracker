/* Doc data/latest.json va dung giao dien. Khong thu vien ngoai. */
const $ = (id) => document.getElementById(id);

// Chuoi lich su thu hang GTVH theo ma (d.lich_su), gan trong .then() truoc khi dung the.
let LICH_SU = {};

const soTy = (v) => (v === null || v === undefined) ? "—" :
  Number(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 });
const soNguyen = (v) => (v === null || v === undefined) ? "—" :
  Number(v).toLocaleString("vi-VN");
const phanTram = (v) => (v === null || v === undefined) ? "—" :
  (v * 100).toFixed(3) + "%";
const phanTramTron = (v) => (v === null || v === undefined) ? "—" :
  Math.round(v * 100) + "%";

const COT = [
  ["symbol", "Mã"], ["gtvh_rank", "Hạng"], ["gtvh_ty", "GTVH (tỷ)"],
  ["gtvh_f_ty", "GTVH free-float (tỷ)"], ["gtgd_kl_ty", "GTGD khớp lệnh (tỷ)"],
  ["klgd_kl", "KLGD khớp lệnh"], ["turnover", "Turnover"],
  ["free_float", "Free float"], ["ket_luan", "Kết luận"],
];

function sparkline(chuoi) {
  // Chi ve khi co tu 2 diem tro len - 1 diem khong noi len xu huong gi.
  if (!chuoi || chuoi.length < 2) return "";
  const hang = chuoi.map((d) => d.gtvh_rank);
  const min = Math.min(...hang), max = Math.max(...hang);
  const bien = max - min || 1;
  const diem = hang.map((v, i) =>
    `${(i / (hang.length - 1)) * 100},${((v - min) / bien) * 20}`).join(" ");
  return `<svg viewBox="0 0 100 20" width="120" height="24" role="img"
            aria-label="Thứ hạng vốn hóa từ ${hang[0]} tới ${hang[hang.length - 1]}">
            <polyline points="${diem}" fill="none" stroke="#00728d" stroke-width="1.5"/>
          </svg>`;
}

function the(s, loaiThe) {
  // loaiThe: "" (binh thuong) | "canh-bao" (nguy co that su) | "thieu-du-lieu" (chua ket luan)
  const el = document.createElement("div");
  el.className = "the" + (loaiThe ? " " + loaiThe : "");
  const truot = (s.screens || []).filter((x) => !x.passed);
  const dsHien = truot.length ? truot : (s.screens || []);
  const lyDo = dsHien.map((x) => {
    const shortfall = (x.shortfall === null || x.shortfall === undefined)
      ? "" : ` — còn thiếu ${soTy(x.shortfall)}`;
    return `<li class="${x.passed ? "dat" : "truot"}">${x.message}${shortfall}
             <small>(Điều ${x.rule_ref})</small></li>`;
  }).join("");
  const canhBaoRieng = (s.canh_bao || [])
    .map((c) => `<li class="truot">${c}</li>`).join("");
  el.innerHTML = `<b>${s.symbol}</b> — hạng ${s.gtvh_rank} vốn hóa,
                  GTVH ${soTy(s.gtvh_ty)} tỷ ${sparkline(LICH_SU[s.symbol])}
                  <ul>${lyDo}${canhBaoRieng}</ul>`;
  return el;
}

// Phan loai mau cho tung dong bang top 50. Khoa la CHINH XAC chuoi ket_luan do
// build._ket_luan sinh ra (xem tests/test_site_smoke.py giu hai ben khong lech nhau).
// Mau chi la lop bo tro: cot "Kết luận" bang chu van luon hien, de trang con doc
// duoc khi in den trang hoac voi nguoi mu mau.
const MAU_KET_LUAN = {
  "Trong rổ dự kiến": "kl-trong-ro",
  "Dự phòng": "kl-du-phong",
  "Không đạt": "kl-khong-dat",
  "Đạt tiêu chí, ngoài rổ": "kl-dat-ngoai-ro",
  "Thiếu dữ liệu": "kl-thieu-du-lieu",
  "HOSE loại khỏi VNAllshare": "kl-hose-loai",
};

function dungBang(stocks) {
  $("bang").querySelector("thead").innerHTML =
    "<tr>" + COT.map(([, ten]) => `<th>${ten}</th>`).join("") + "</tr>";
  const top50 = stocks.slice().sort((a, b) => (a.gtvh_rank ?? 9999) - (b.gtvh_rank ?? 9999)).slice(0, 50);
  const ve = (loc) => {
    const tbody = $("bang").querySelector("tbody");
    tbody.innerHTML = "";
    top50.filter((s) => s.symbol.includes(loc.toUpperCase())).forEach((s) => {
      const tr = document.createElement("tr");
      tr.className = MAU_KET_LUAN[s.ket_luan] || "";
      tr.innerHTML = COT.map(([khoa]) => {
        let v = s[khoa];
        if (khoa === "turnover") v = phanTram(v);
        else if (khoa === "free_float") v = phanTramTron(v);
        else if (khoa === "klgd_kl") v = soNguyen(v);
        else if (typeof v === "number") v = soTy(v);
        if (khoa === "ket_luan") return `<td><span class="nhan">${v ?? "—"}</span></td>`;
        return `<td>${v ?? "—"}</td>`;
      }).join("");
      tbody.appendChild(tr);
    });
  };
  $("loc").addEventListener("input", (e) => ve(e.target.value));
  ve("");
}

fetch("./data/latest.json")
  .then((r) => {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  })
  .then((d) => {
    LICH_SU = d.lich_su || {};

    if (d.lich) {
      const conLai = Math.ceil((new Date(d.lich.ngay_chot) - new Date(d.as_of)) / 86400000);
      $("meta").textContent =
        `Kỳ review ${d.lich.ky} · chốt dữ liệu ${d.lich.ngay_chot} (còn ${conLai} ngày) · ` +
        `hiệu lực ${d.lich.ngay_hieu_luc} · dữ liệu tới ${d.as_of} · ` +
        `${d.constituents.length} mã trong rổ dự kiến`;
    } else {
      $("meta").textContent =
        `Kỳ review ${d.ky_review} · Dữ liệu tới ${d.as_of} · ${d.constituents.length} mã trong rổ dự kiến`;
    }

    if (d.canh_bao && d.canh_bao.length) {
      const cb = $("canh-bao-goc");
      cb.hidden = false;
      cb.innerHTML = d.canh_bao.map((c) => `<p>⚠ ${c}</p>`).join("");
    }

    const trongRo = new Set(d.constituents);

    // Mot ma chi "chua ket luan duoc" khi TAT CA cac buoc sang loc ma no truot deu
    // co thieu_du_lieu=true (danh dau o tang du lieu - rules/models.ScreenResult -
    // KHONG do chuoi tieng Viet trong message, cach do de vo). Neu khong truot
    // buoc nao (bi loai vi ly do khac, vd thu hang) thi KHONG phai thieu du lieu.
    const chiThieuDuLieu = (s) => {
      const truot = (s.screens || []).filter((x) => !x.passed);
      return truot.length > 0 && truot.every((x) => x.thieu_du_lieu === true);
    };

    const ungVien = d.stocks.filter((s) => !s.in_previous_basket && trongRo.has(s.symbol));
    const raKhongTrongRo = d.stocks.filter((s) => s.in_previous_basket && !trongRo.has(s.symbol));
    // Nguy co bi loai: CHI gom ma truot vi ly do THUC CHAT (khong phai thieu du lieu).
    const nguyCo = raKhongTrongRo.filter((s) => !chiThieuDuLieu(s));
    // Chua ket luan duoc: ma trong ro ky truoc nhung moi buoc truot deu la thieu du lieu.
    const chuaKetLuan = raKhongTrongRo.filter((s) => chiThieuDuLieu(s));

    if (ungVien.length) {
      ungVien.forEach((s) => $("vao").appendChild(the(s, "")));
    } else {
      $("vao").innerHTML = '<p class="rong">Chưa có mã nào đủ điều kiện thêm mới trong kỳ này.</p>';
    }

    if (nguyCo.length) {
      nguyCo.forEach((s) => $("ra").appendChild(the(s, "canh-bao")));
    } else {
      $("ra").innerHTML = '<p class="rong">Chưa có mã nào trong rổ hiện tại bị đe dọa loại vì lý do thực chất.</p>';
    }

    if (chuaKetLuan.length) {
      chuaKetLuan.forEach((s) => $("chua-ket-luan").appendChild(the(s, "thieu-du-lieu")));
    } else {
      $("chua-ket-luan").innerHTML =
        '<p class="rong">Không có mã nào trong rổ hiện tại bị bỏ sót chỉ vì thiếu dữ liệu.</p>';
    }

    dungBang(d.stocks);

    const md = d.missing_data || [];
    if (md.length) {
      $("thieu-du-lieu").innerHTML =
        `<h2>Thiếu dữ liệu</h2>
         <details>
           <summary>${md.length} mã chưa đủ dữ liệu để kết luận (bấm để xem danh sách)</summary>
           <p>Các mã sau chưa có free float, lợi nhuận đã xác nhận, hoặc dữ liệu giao dịch đầy đủ,
              nên không thể kết luận có đủ điều kiện vào rổ hay không:</p>
           <p>${md.join(", ")}</p>
         </details>`;
    } else {
      $("thieu-du-lieu").innerHTML = "<h2>Thiếu dữ liệu</h2><p>Không có mã nào thiếu dữ liệu.</p>";
    }

    // Dinh nghia chi tieu: mo ta va MOI CON SO nguong den tu build.py (noi suy tu
    // rules/thresholds.yaml), khong go tay vao HTML - xem tests/test_site_smoke.py.
    if (d.dinh_nghia) {
      $("dinh-nghia-cot").innerHTML = d.dinh_nghia.cot.map((c) =>
        `<dt>${c.ten}</dt><dd>${c.mo_ta} <small>(Điều ${c.rule_ref})</small></dd>`).join("");
      $("dinh-nghia-nhan").innerHTML = d.dinh_nghia.nhan.map((n) => {
        const lop = MAU_KET_LUAN[n.nhan] || "";
        return `<dt class="${lop}">${n.nhan}</dt><dd>${n.mo_ta}</dd>`;
      }).join("");
    } else {
      $("dinh-nghia").hidden = true;
    }

    $("xap-xi").innerHTML = (d.xap_xi || []).map((x) => `<li>${x}</li>`).join("")
      || "<li>Không có ghi chú xấp xỉ nào cho kỳ này.</li>";
    $("nguon").textContent = "Nguồn quy tắc: " + d.nguon_quy_tac;
  })
  .catch((e) => {
    $("meta").textContent = "Không tải được dữ liệu: " + e.message +
      ". Vui lòng tải lại trang hoặc liên hệ quản trị hệ thống.";
  });

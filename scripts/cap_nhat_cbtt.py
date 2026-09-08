"""Doc moi file PDF cong bo chinh thuc HOSE (CBTT) trong data/hose_index/ va ghi
ra file YAML tuong ung <ky>.yaml - file YAML nay duoc commit vao git de co lich su
va de review, KHONG duoc sua tay (muon doi thi sua PDF nguon roi chay lai script nay).

Chay tay: python scripts/cap_nhat_cbtt.py
"""
import logging
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.hose_disclosure import HoseDisclosureError, doc_cbtt  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "hose_index"


def _ghi_yaml(kq: dict, pdf_path: Path) -> Path:
    out_path = DATA_DIR / f"{kq['ky']}.yaml"

    header = (
        f"# TU DONG SINH tu {pdf_path.name} boi scripts/cap_nhat_cbtt.py - KHONG SUA TAY.\n"
        f"# Nguon: Cong bo thong tin chinh thuc cua HOSE (Sở Giao dịch Chứng khoán TP.HCM)\n"
        f"# ve danh muc va co cau chi so ky {kq['ky']}, tai tu static2.vietstock.vn.\n"
        f"# Muon sua du lieu: sua file PDF nguon (hoac thay file PDF ky moi vao\n"
        f"# data/hose_index/) roi chay lai: python scripts/cap_nhat_cbtt.py\n"
        f"# Sinh luc: {date.today().isoformat()}\n"
    )

    payload = {
        "ky": kq["ky"],
        "vn30": kq["vn30"],
        "vn30_du_phong": kq["vn30_du_phong"],
        "free_float": {ma: round(ty_le, 4) for ma, ty_le in sorted(kq["free_float"].items())},
    }

    with out_path.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    return out_path


def main() -> None:
    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        logger.warning("Không tìm thấy file PDF nào trong %s", DATA_DIR)
        return

    for pdf_path in pdfs:
        try:
            kq = doc_cbtt(pdf_path)
        except HoseDisclosureError as e:
            logger.error("Bỏ qua %s do lỗi đọc PDF: %s", pdf_path.name, e)
            continue

        out_path = _ghi_yaml(kq, pdf_path)
        logger.info(
            "Kỳ %s: %d mã VN30, %d mã dự phòng, %d mã VNAllshare có free-float -> %s",
            kq["ky"], len(kq["vn30"]), len(kq["vn30_du_phong"]),
            kq["so_ma_vnallshare"], out_path.name,
        )


if __name__ == "__main__":
    main()

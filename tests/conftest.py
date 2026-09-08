import pytest

import collectors.market_data as md


@pytest.fixture(autouse=True)
def tat_throttle_mac_dinh(monkeypatch):
    """Tat dieu tiet request mac dinh cho toan bo test - test khong duoc ngu that.

    Test nao muon kiem tra chinh co che throttle thi tu bat lai bang
    monkeypatch.setenv(md.ENV_TAT_THROTTLE, "0") va tiem time_fn/sleep_fn gia.
    """
    monkeypatch.setenv(md.ENV_TAT_THROTTLE, "1")

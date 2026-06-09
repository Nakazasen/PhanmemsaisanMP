from pathlib import Path


def test_universal_app_does_not_render_exchange_rate_input():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "Tỷ giá (USD/VND)" not in source
    assert "USD/VND" not in source
    assert "self.exchange_rate" not in source
    assert "textvariable=self.exchange_rate" not in source


def test_universal_app_preserves_backend_exchange_rate_default():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "from src.config import EXCHANGE_RATE_USD_VND" in source
    assert "exchange_rate = float(EXCHANGE_RATE_USD_VND)" in source

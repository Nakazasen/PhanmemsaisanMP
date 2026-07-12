from pathlib import Path


def test_universal_app_renders_exchange_rate_input():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "Tỷ giá (USD/VND)" in source
    assert "self.exchange_rate" in source
    assert "textvariable=self.exchange_rate" in source


def test_universal_app_uses_the_entered_exchange_rate_for_pipeline():
    source = Path("src/universal_app.py").read_text(encoding="utf-8")

    assert "validate_exchange_rate(self.exchange_rate.get())" in source
    assert "EXCHANGE_RATE_USD_VND" not in source

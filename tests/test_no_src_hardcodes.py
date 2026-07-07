from pathlib import Path


PROHIBITED_SRC_TOKENS = (
    "1412000040",
    "16.KDTVN",
    "KDTVN",
    "髮ｻ豌苓｣ｽ騾謚陦楢ｪｲ",
)


def test_src_does_not_contain_gate15_cost_center_hardcodes():
    offenders = []
    for path in Path("src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in PROHIBITED_SRC_TOKENS:
            if token in text:
                offenders.append(f"{path}:{token}")

    assert offenders == []

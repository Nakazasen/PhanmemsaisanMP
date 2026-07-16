"""Canonical uniform/cup entitlement and allocation-rule identities."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata


def normalize_uniform_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("\n", " ").replace("\u3000", " ").strip().lower()
    return " ".join(text.split())


@dataclass(frozen=True)
class UniformItemSpec:
    key: str
    header: str
    rule_tokens: tuple[str, ...]
    rule_excludes: tuple[str, ...] = ()
    quantity_per_hire: int = 1
    timing: str = "monthly"

    def matches_rule(self, item_name: object) -> bool:
        normalized = normalize_uniform_text(item_name)
        tokens = tuple(normalize_uniform_text(token) for token in self.rule_tokens)
        excludes = tuple(normalize_uniform_text(token) for token in self.rule_excludes)
        return all(token in normalized for token in tokens) and not any(token in normalized for token in excludes)


UNIFORM_ITEM_SPECS: tuple[UniformItemSpec, ...] = (
    UniformItemSpec("pants", "Quần", ("制服ズボン",), ("妊婦", "保安課"), 2),
    UniformItemSpec("security_pants", "Quần phòng an ninh", ("保安課", "ズボン"), quantity_per_hire=2),
    UniformItemSpec("long_sleeve", "Đồng phục dài tay", ("制服（冬）",), ("一括支給", "保安課"), 2, "long_sleeve"),
    UniformItemSpec("short_sleeve", "Đồng phục ngắn tay", ("制服（夏）",), ("一括支給", "保安課"), 2, "summer_shirt"),
    UniformItemSpec("security_long_sleeve", "Áo dài tay phòng an ninh", ("保安課", "長袖"), quantity_per_hire=2, timing="long_sleeve"),
    UniformItemSpec("security_short_sleeve", "Áo ngắn tay phòng an ninh", ("保安課", "半袖"), quantity_per_hire=2, timing="summer_shirt"),
    UniformItemSpec("polo", "Áo polo", ("ポロ制服",), quantity_per_hire=2, timing="summer_shirt"),
    UniformItemSpec("coat", "Áo khoác xanh kyocera", ("コート制服",), ("保安課",), 1),
    UniformItemSpec("security_coat", "Áo khoác có lót phòng an ninh", ("保安課", "コート"), quantity_per_hire=1),
    UniformItemSpec("mens_shoes", "Giày vải nam", ("シューズ（男性）",), quantity_per_hire=1),
    UniformItemSpec("safety_shoes_type_2", "Giày bảo hộ loại 2", ("タイプ2", "安全靴"), quantity_per_hire=1),
    UniformItemSpec("security_shoes", "Giày phòng an ninh", ("保安課", "靴"), quantity_per_hire=1),
    UniformItemSpec("white_hat", "Mũ trắng", ("帽子（白）",), ("金型", "保安課"), 2),
    UniformItemSpec("color_hat", "Mũ màu", ("帽子（カラー）",), quantity_per_hire=2),
    UniformItemSpec("security_hat", "Mũ phòng an ninh", ("保安課", "帽子"), quantity_per_hire=2),
    UniformItemSpec("collapsible_cup", "Cốc xếp", ("折りたたみコップ",), quantity_per_hire=1, timing="cup"),
)

UNIFORM_ITEM_SPEC_BY_KEY = {spec.key: spec for spec in UNIFORM_ITEM_SPECS}
SUMMER_SHIRT_KEYS = frozenset({"short_sleeve", "polo", "security_short_sleeve"})
LONG_SLEEVE_KEYS = frozenset({"long_sleeve", "security_long_sleeve"})


def uniform_item_key_for_rule(item_name: object) -> str | None:
    matches = [spec.key for spec in UNIFORM_ITEM_SPECS if spec.matches_rule(item_name)]
    return matches[0] if len(matches) == 1 else None

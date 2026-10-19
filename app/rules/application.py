"""The application data a label is checked against."""

from dataclasses import dataclass
from enum import StrEnum


class BeverageType(StrEnum):
    DISTILLED_SPIRITS = "distilled_spirits"
    WINE = "wine"
    MALT_BEVERAGE = "malt_beverage"

    @classmethod
    def from_text(cls, text: str) -> "BeverageType":
        """Read a beverage type as people write it, such as "Distilled spirits" or "Beer"."""
        key = " ".join(text.replace("_", " ").casefold().split())
        if key in BEVERAGE_TYPE_NAMES:
            return BEVERAGE_TYPE_NAMES[key]
        raise ValueError(
            f'Unknown beverage type "{text}". Use distilled spirits, wine, or malt beverage.'
        )


BEVERAGE_TYPE_NAMES = {
    "distilled spirits": BeverageType.DISTILLED_SPIRITS,
    "spirits": BeverageType.DISTILLED_SPIRITS,
    "wine": BeverageType.WINE,
    "malt beverage": BeverageType.MALT_BEVERAGE,
    "malt beverages": BeverageType.MALT_BEVERAGE,
    "beer": BeverageType.MALT_BEVERAGE,
}


@dataclass(frozen=True)
class Application:
    beverage_type: BeverageType
    brand_name: str
    class_type: str
    alcohol_content: str
    net_contents: str
    bottler_name_address: str
    country_of_origin: str = ""  # blank means a domestic product

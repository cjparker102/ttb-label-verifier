"""The application data a label is checked against."""

from dataclasses import dataclass
from enum import StrEnum


class BeverageType(StrEnum):
    DISTILLED_SPIRITS = "distilled_spirits"
    WINE = "wine"
    MALT_BEVERAGE = "malt_beverage"


@dataclass(frozen=True)
class Application:
    beverage_type: BeverageType
    brand_name: str
    class_type: str
    alcohol_content: str
    net_contents: str
    bottler_name_address: str
    country_of_origin: str = ""  # blank means a domestic product

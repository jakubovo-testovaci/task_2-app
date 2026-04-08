from typing import Dict, Optional
from .product_type import StockValue, Color, ProductTransformed
from pydantic import BaseModel, field_validator, model_validator
import json
from hashlib import md5

vat_rate = 0.21

class Attributes(BaseModel):
    color: Optional[str] = None

#zvaliduje a upravi data z erp, upravena data v prop transformed
class Product(BaseModel):
    id: str
    title: str
    price_vat_excl: float
    stocks: Dict[str, StockValue]
    attributes: Optional[Attributes]

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        if len(v) < 3 or len(v) > 100:
            raise ValueError("title length must be 3-100")
        return v

    @field_validator("stocks")
    @classmethod
    def validate_stocks(cls, v: Dict[str, StockValue]):
        for key, value in v.items():
            if not (isinstance(value, int) or value == "N/A"):
                raise ValueError(f"stocks['{key}'] musí být int nebo 'N/A'")
        return v
    
    @field_validator("price_vat_excl")
    @classmethod
    def validate_price_vat_excl(cls, v: float):
        if v < 0:
            raise ValueError("price_vat_excl cannot be negative")
        return v

    @model_validator(mode="after")
    def validate_attributes(self):
        return self
    
    @property
    def sum_stocks(self) -> int:
        total = 0
        for value in self.stocks.values():
            if isinstance(value, int):
                total += value
        return total
    
    @property
    def color(self) -> Color:
        if self.attributes and self.attributes.color:
            return self.attributes.color
        return "N/A"
    
    @property
    def price(self) -> float:
        return round(self.price_vat_excl * (1 + vat_rate), 2)
    
    @property
    def transformed(self) -> ProductTransformed:
        result = {
            "source_id": self.id,
            "title": self.title,
            "price": self.price,
            "stocks": self.sum_stocks,
            "color": self.color
        }
        result["hash"] = md5(json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()
        return result
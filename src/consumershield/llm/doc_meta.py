"""The record we want for every document of ConsumerShield.

This class is a contract. The extraction prompt, database and search
filters rely on it: add a field freely, but rename or remove one only
on purpose.
"""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

Short = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]

Values = Annotated[list[Short], Field(default_factory=list, max_length=8)]

Kind = Literal[
    "guideline",
    "rule",
    "notice",
    "list",
    "report",
    "faq",
    "form",
    "tutorial",
    "reference",
    "other",
]

Issue = Literal[
    "defective_product",
    "refund",
    "replacement",
    "delivery",
    "misleading_advertisement",
    "unfair_trade_practice",
    "service_deficiency",
    "e_commerce",
    "other",
]


class DocMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_kind: Kind
    year: int | None = Field(default=None, ge=1950, le=2027)
    language: Literal["en", "ta", "hi", "other"]
    summary: str = Field(min_length=20, max_length=300)
    topics: Annotated[list[Short], Field(min_length=1, max_length=6)]

    case_no: Values
    commission: Values
    product_category: Values
    issue: Annotated[list[Issue], Field(default_factory=list, max_length=8)]
    outcome: Values

    @field_validator("topics")
    @classmethod
    def _tidy(cls, value: list[str]) -> list[str]:
        """Lowercase and remove repeated topics."""
        return list(dict.fromkeys(topic.lower() for topic in value))

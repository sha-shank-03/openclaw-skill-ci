"""Shared result types; categories distinguish policy from native syntax."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    rule: str
    category: str
    location: str
    message: str
    severity: str = "error"

    def to_dict(self):
        return asdict(self)


class InputError(Exception):
    """A caller-selected input cannot be read or has an invalid v1 schema."""

    def __init__(self, rule, location, message):
        super().__init__(message)
        self.finding = Finding(rule, "operational", location, message)


def has_errors(findings):
    return any(f.severity == "error" for f in findings)

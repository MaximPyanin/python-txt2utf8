from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConversionReport:
    input_path: Path
    output_path: Path
    detected_encoding: str
    confidence: float
    bytes_in: int
    bytes_out: int


@dataclass(frozen=True)
class BatchItemResult:
    path: Path
    ok: bool
    report: ConversionReport | None
    error: str | None

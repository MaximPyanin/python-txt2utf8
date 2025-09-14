from dataclasses import dataclass
from pathlib import Path

from charset_normalizer import from_bytes


@dataclass(frozen=True)
class ConversionReport:
    input_path: Path
    output_path: Path
    detected_encoding: str
    confidence: float
    bytes_in: int
    bytes_out: int


class TxtToUtf8Converter:
    """
    Single-file TXT -> UTF-8 converter with auto-encoding detection.

    - Принимает .txt
    - Определяет кодировку (charset-normalizer)
    - Если источник UTF-8 с BOM — BOM уберётся (чтение через 'utf-8-sig')
    - Записывает строго UTF-8 (без BOM)
    """

    def __init__(self, input_path: str | Path, output_path: str | Path, *, overwrite: bool = False) -> None:
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.overwrite = overwrite

    def convert(self) -> ConversionReport:
        # --- валидация путей ---
        if not self.input_path.is_file():
            raise FileNotFoundError(self.input_path)
        if self.input_path.suffix.lower() != ".txt":
            raise ValueError("Only .txt files are supported")

        out_path = (
            self.output_path / self.input_path.name
            if self.output_path.suffix == "" or self.output_path.is_dir()
            else Path(self.output_path)
        )
        if out_path.exists() and not self.overwrite:
            raise FileExistsError(f"Output exists: {out_path}")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # --- два with: читаем -> пишем ---
        with self.input_path.open("rb") as f_in:
            raw = f_in.read()

        match = from_bytes(raw).best()
        if not match or not match.encoding:
            raise ValueError("Failed to detect text encoding (file may be binary)")

        enc = match.encoding
        conf = float(getattr(match, "confidence", 0.0))

        # если детектировался UTF-8, читаем через utf-8-sig, чтобы «съесть» BOM
        dec_enc = "utf-8-sig" if "utf-8" in enc.lower().replace("_", "-") else enc
        text = raw.decode(dec_enc, errors="strict")

        with out_path.open("w", encoding="utf-8", newline="") as f_out:
            f_out.write(text)

        return ConversionReport(
            input_path=self.input_path,
            output_path=out_path,
            detected_encoding=enc,
            confidence=conf,
            bytes_in=len(raw),
            bytes_out=out_path.stat().st_size,
        )

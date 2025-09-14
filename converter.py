from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from charset_normalizer import from_bytes
from tqdm import tqdm

from models import ConversionReport, BatchItemResult


class Converter:
    DETECT_MAX_BYTES = 1 * 1024 * 1024
    READ_CHARS = 1 * 1024 * 1024

    def __init__(
        self, input_path: str | Path, output_path: str | Path, overwrite: bool = False
    ) -> None:
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.overwrite = overwrite

    def convert(self, show_progress: bool = False) -> ConversionReport:
        self._ensure_input_txt(self.input_path)
        out_path = self._make_output_path(
            self.input_path, self.output_path, expect_dir=False
        )
        if out_path.exists() and not self.overwrite:
            raise FileExistsError(f"Output exists: {out_path}")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        source_enc, enc_conf = self._detect_encoding(self.input_path)

        bytes_in = self._stream_copy(
            in_file=self.input_path,
            out_file=out_path,
            src_encoding=source_enc,
            show_progress=show_progress,
        )

        return ConversionReport(
            input_path=self.input_path,
            output_path=out_path,
            detected_encoding=source_enc,
            confidence=enc_conf,
            bytes_in=bytes_in,
            bytes_out=out_path.stat().st_size,
        )

    @staticmethod
    def batch_convert(
        inputs_root: Path | str,
        output_dir: Path | str,
        overwrite: bool = False,
        workers: int = 4,
        recursive: bool = True,
    ) -> list[BatchItemResult]:
        root = Path(inputs_root)
        out_dir = Path(output_dir)

        files = Converter._collect_txt_files(root, recursive=recursive)
        if not files:
            raise ValueError("No .txt files found for batch")
        out_dir.mkdir(parents=True, exist_ok=True)

        def convert_single(file_path: Path) -> BatchItemResult:
            try:
                converter = Converter(
                    input_path=file_path,
                    output_path=Converter._make_output_path(
                        file_path, out_dir, expect_dir=True
                    ),
                    overwrite=overwrite,
                )
                report = converter.convert(show_progress=False)
                return BatchItemResult(
                    path=file_path, ok=True, report=report, error=None
                )
            except Exception as e:
                return BatchItemResult(
                    path=file_path, ok=False, report=None, error=str(e)
                )

        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(convert_single, f): f for f in files}

            for future in tqdm(
                as_completed(futures), total=len(files), desc="Converting"
            ):
                results.append(future.result())

        return results

    @staticmethod
    def _ensure_input_txt(path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".txt":
            raise ValueError("Only .txt files are supported")

    @staticmethod
    def _make_output_path(
        input_path: Path, output_spec: Path, expect_dir: bool
    ) -> Path:
        if expect_dir:
            base = output_spec if output_spec.suffix == "" else output_spec.parent
            return base / input_path.name
        return (
            (output_spec / input_path.name)
            if (output_spec.suffix == "" or output_spec.is_dir())
            else output_spec
        )

    @classmethod
    def _detect_encoding(cls, file_path: Path) -> tuple[str, float]:
        with file_path.open("rb") as f:
            sample = f.read(cls.DETECT_MAX_BYTES)

        fallback_encodings = ["utf-8-sig", "utf-8", "cp1251", "latin-1"]

        match = from_bytes(sample).best()
        if match and match.encoding:
            return match.encoding, 0.8

        for encoding in fallback_encodings:
            try:
                sample.decode(encoding)
                return encoding, 0.8
            except UnicodeDecodeError:
                continue

        return "latin-1", 0.5

    @classmethod
    def _stream_copy(
        cls, in_file: Path, out_file: Path, src_encoding: str, show_progress: bool
    ) -> int:
        total_bytes = in_file.stat().st_size

        with (
            in_file.open("r", encoding=src_encoding, errors="replace") as f_in,
            out_file.open("w", encoding="utf-8") as f_out,
        ):
            if show_progress:
                with tqdm(
                    total=total_bytes, unit="B", unit_scale=True, desc=f"{in_file.name}"
                ) as pbar:
                    while True:
                        chunk = f_in.read(cls.READ_CHARS)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        pbar.update(len(chunk.encode("utf-8")))
            else:
                while True:
                    chunk = f_in.read(cls.READ_CHARS)
                    if not chunk:
                        break
                    f_out.write(chunk)

        return total_bytes

    @staticmethod
    def _collect_txt_files(root: Path, recursive: bool) -> list[Path]:
        if not root.exists():
            raise FileNotFoundError(root)
        if root.is_file():
            return [root] if root.suffix.lower() == ".txt" else []
        pattern = "**/*.txt" if recursive else "*.txt"
        return [p for p in root.glob(pattern) if p.is_file()]

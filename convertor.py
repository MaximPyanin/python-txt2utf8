from asyncio import Semaphore, to_thread
from pathlib import Path
from io import TextIOWrapper
from charset_normalizer import from_bytes
from tqdm import tqdm as pbar
from tqdm.asyncio import tqdm

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
        stream_enc = (
            "utf-8-sig"
            if "utf-8" in source_enc.lower().replace("_", "-")
            else source_enc
        )

        bytes_in = self._stream_copy(
            in_file=self.input_path,
            out_file=out_path,
            src_encoding=stream_enc,
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

    @classmethod
    async def batch_convert(
        cls,
        inputs_root: Path | str,
        output_dir: Path | str,
        overwrite: bool = False,
        workers: int = 4,
        recursive: bool = True,
    ) -> list[BatchItemResult]:
        root = Path(inputs_root)
        out_dir = Path(output_dir)

        files = cls._collect_txt_files(root, recursive=recursive)
        if not files:
            raise ValueError("No .txt files found for batch")
        out_dir.mkdir(parents=True, exist_ok=True)

        sem = Semaphore(max(1, workers))

        async def run_one(p: Path) -> BatchItemResult:
            try:
                async with sem:
                    rep = await to_thread(
                        lambda: cls(
                            input_path=p,
                            output_path=cls._make_output_path(
                                p, out_dir, expect_dir=True
                            ),
                            overwrite=overwrite,
                        ).convert(show_progress=False)
                    )
                return BatchItemResult(path=p, ok=True, report=rep, error=None)
            except Exception as e:
                return BatchItemResult(path=p, ok=False, report=None, error=str(e))

        coros = [run_one(p) for p in files]

        results: list[BatchItemResult] = []
        for fut in tqdm.as_completed(coros, total=len(coros), desc="Converting"):
            results.append(await fut)
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
        match = from_bytes(sample).best()
        if not match or not match.encoding:
            raise ValueError("Failed to detect text encoding (file may be binary)")
        return match.encoding, float(getattr(match, "confidence", 0.0))

    @classmethod
    def _stream_copy(
        cls, in_file: Path, out_file: Path, src_encoding: str, show_progress: bool
    ) -> int:
        total_bytes = in_file.stat().st_size
        read_bytes = 0

        with (
            in_file.open("rb") as raw_in,
            out_file.open("w", encoding="utf-8", newline="") as f_out,
        ):
            reader = TextIOWrapper(raw_in, encoding=src_encoding, newline="")

            if show_progress:
                last_pos = 0
                with pbar(
                    total=total_bytes, unit="B", unit_scale=True, desc=f"{in_file.name}"
                ) as bar:
                    while True:
                        chunk = reader.read(cls.READ_CHARS)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        pos = raw_in.tell()
                        bar.update(pos - last_pos)
                        last_pos = pos
                    read_bytes = raw_in.tell()
            else:
                while True:
                    chunk = reader.read(cls.READ_CHARS)
                    if not chunk:
                        break
                    f_out.write(chunk)
                read_bytes = raw_in.tell()

        return int(read_bytes)

    @staticmethod
    def _collect_txt_files(root: Path, recursive: bool) -> list[Path]:
        if not root.exists():
            raise FileNotFoundError(root)
        if root.is_file():
            return [root] if root.suffix.lower() == ".txt" else []
        pattern = "**/*.txt" if recursive else "*.txt"
        return [p for p in root.glob(pattern) if p.is_file()]

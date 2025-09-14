from argparse import ArgumentParser
from asyncio import run
from pathlib import Path

from convertor import Converter


def _parser() -> ArgumentParser:
    p = ArgumentParser(prog="txt2utf8", description="TXT → UTF-8 converter.")
    p.add_argument(
        "-i", "--input", required=True, help="Path to .txt file or directory"
    )
    p.add_argument("-o", "--output", required=True, help="Output file or directory")
    p.add_argument(
        "--overwrite", action="store_true", help="Overwrite output if exists"
    )
    p.add_argument("--workers", type=int, default=8, help="Workers for batch (I/O)")
    p.add_argument("--no-recursive", action="store_true", help="Do not scan subfolders")
    return p


def main() -> None:
    a = _parser().parse_args()
    src = Path(a.input)
    dst = Path(a.output)

    if src.is_dir():
        results = run(
            Converter.batch_convert(
                inputs_root=src,
                output_dir=dst,
                overwrite=a.overwrite,
                workers=max(1, a.workers),
                recursive=not a.no_recursive,
            )
        )
        ok = sum(r.ok for r in results)
        fail = len(results) - ok
        print(f"Batch: {ok} ok, {fail} failed → {dst}")
        if fail:
            for r in results:
                if not r.ok:
                    print(f"  - {r.path}: {r.error}")
    else:
        rep = Converter(src, dst, overwrite=a.overwrite).convert(show_progress=True)
        print(
            f"OK: {rep.input_path.name} [{rep.detected_encoding}] "
            f"→ {rep.output_path} ({rep.bytes_in}→{rep.bytes_out} bytes)"
        )


if __name__ == "__main__":
    main()

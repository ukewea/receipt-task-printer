"""Extract only Traditional Chinese faces and copy the receipt symbol fallback."""

import argparse
import shutil
from pathlib import Path

from fontTools.ttLib import TTCollection


def prepare_fonts(source: Path, destination: Path, fallback: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for weight in ("Regular", "Bold"):
        with TTCollection(source / f"NotoSansCJK-{weight}.ttc") as collection:
            for face in collection.fonts:
                families = [n.toUnicode() for n in face["name"].names if n.nameID in (1, 16)]
                if "Noto Sans CJK TC" in families:
                    face.save(destination / f"NotoSansCJKTC-{weight}.otf")
                    break
            else:
                raise ValueError(f"Traditional Chinese {weight} face missing")
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        shutil.copyfile(fallback / name, destination / name)
    # Preserve font license notices alongside the extracted font programs.
    for package in ("fonts-noto-cjk", "fonts-dejavu-core"):
        notice = Path("/usr/share/doc") / package / "copyright"
        if notice.exists():
            shutil.copyfile(notice, destination / f"{package}-copyright")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/usr/share/fonts/opentype/noto"))
    parser.add_argument("--destination", type=Path, default=Path("/usr/local/share/receipt-fonts"))
    parser.add_argument("--fallback", type=Path, default=Path("/usr/share/fonts/truetype/dejavu"))
    args = parser.parse_args()
    prepare_fonts(args.source, args.destination, args.fallback)

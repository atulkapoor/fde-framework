"""Draw the README banners and the social-preview card.

Run with the repository's own interpreter (`.venv/bin/python assets/brand.py`).
The three images carried "seven gates" for fifteen releases after the eighth
gate shipped, because they had been drawn once by hand; an outside reader
found the banner contradicting the README it headed. The gate count is now
read off the gates module, as the diagram's is, so the words on the images
are the code's words. The social-preview card is also the one uploaded to
the repository's settings, which has no API: re-upload it by hand when it
changes.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parent.parent
FONT = "/System/Library/Fonts/Menlo.ttc"
WORDS = {8: "eight", 7: "seven", 6: "six", 9: "nine", 10: "ten"}


def gates() -> int:
    from fde.gates import input_status
    from fde.models.profile import Profile

    return len(input_status(Profile()).gates)


def pipeline() -> str:
    return f"statement -> typed facts -> {WORDS[gates()]} gates -> deployable project"


def save(image: Image.Image, path: Path) -> None:
    """The words the image carries, stamped into it, so a test can hold the
    picture to the code without reading pixels."""
    info = PngInfo()
    info.add_text("fde:words", pipeline())
    image.save(path, optimize=True, pnginfo=info)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def centred(draw, y, text, fnt, fill, width):
    draw.text(((width - draw.textlength(text, font=fnt)) / 2, y), text, font=fnt, fill=fill)


def banner(path: Path, bg: str, name: str, text: str, dim: str) -> None:
    """1520x300: `fde` in blue, the tagline, the pipeline in one line."""
    width, height = 1520, 300
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    draw.text((70, 85), "fde", font=font(118), fill=name)
    draw.text((322, 110), "a framework for Forward Deployed Engineers", font=font(44), fill=text)
    draw.text((322, 196), pipeline(), font=font(28), fill=dim)
    save(image, path)


def social_preview(path: Path) -> None:
    """1280x640: a terminal card with the install line and the refusal that
    is the product working."""
    width, height = 1280, 640
    bg, edge, text, dim, blue = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#58a6ff"
    green, amber = "#3fb950", "#d29922"
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 40, width - 40, height - 40), radius=18, outline=edge, width=2)
    for x, colour in ((82, "#ff5f56"), (116, "#ffbd2e"), (150, "#27c93f")):
        draw.ellipse((x - 10, 67, x + 10, 87), fill=colour)
    centred(draw, 112, "fde-framework", font(74), text, width)
    centred(draw, 214, "for Forward Deployed Engineers", font(36), blue, width)
    centred(draw, 289, pipeline(), font(26), dim, width)
    lines = (("$ pip install fde-framework", green), ("$ fde build acme --out project", text),
             ("refused: [hard] data_access -- promised", amber),
             ("access is not access.", amber))
    for i, (line, colour) in enumerate(lines):
        draw.text((120, 388 + i * 50), line, font=font(32), fill=colour)
    centred(draw, 580, "decisions traced to facts * byte-identical rebuilds * Apache-2.0",
            font(22), dim, width)
    save(image, path)


def main() -> None:
    assets = ROOT / "assets"
    banner(assets / "banner-light.png", "#ffffff", "#0969da", "#24292f", "#57606a")
    banner(assets / "banner-dark.png", "#0d1117", "#58a6ff", "#e6edf3", "#8b949e")
    social_preview(assets / "social-preview.png")
    print(f"drew three images saying '{pipeline()}'")


if __name__ == "__main__":
    main()

"""Draw assets/how-it-fits.png: the pipeline as eight boxes and three lines.

Run with the repository's own interpreter (`.venv/bin/python assets/how-it-fits.py`).
The registry counts are read off framework/ so the image cannot drift from
the corpus; the gate count is read off the gates module for the same reason.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/System/Library/Fonts/Menlo.ttc"
BG, BOX, EDGE, TEXT, DIM, BLUE = ("#0d1117", "#161b22", "#30363d", "#e6edf3", "#8b949e",
                                  "#58a6ff")


def counts() -> dict[str, int]:
    return {kind: len(list((ROOT / "framework" / kind).glob("*.md")))
            for kind in ("dimensions", "approaches", "patterns", "stacks")}


def gates() -> tuple[int, int]:
    from fde.gates import input_status
    from fde.models.profile import Profile

    status = input_status(Profile())
    hard = sum(1 for g in status.gates if g.hard)
    return len(status.gates), hard


WORDS = {8: "eight", 7: "seven", 6: "six", 9: "nine", 1: "one", 2: "two"}


def main() -> None:
    total, hard = gates()
    reg = counts()
    width, height = 1600, 600
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    big = ImageFont.truetype(FONT, 26)
    small = ImageFont.truetype(FONT, 18)
    body = ImageFont.truetype(FONT, 20)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=12, outline=EDGE, width=2)

    def box(x, y, w, h, title, sub):
        draw.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=BOX, outline=EDGE,
                               width=2)
        tw = draw.textlength(title, font=big)
        sw = draw.textlength(sub, font=small)
        draw.text((x + (w - tw) / 2, y + 22), title, font=big, fill=TEXT)
        draw.text((x + (w - sw) / 2, y + 60), sub, font=small, fill=DIM)

    def arrow(x1, y, x2):
        draw.line((x1, y, x2 - 10, y), fill=EDGE, width=2)
        draw.polygon([(x2, y), (x2 - 12, y - 6), (x2 - 12, y + 6)], fill=EDGE)

    row1 = [("statement", "prose, PDFs, pairs", 265),
            ("typed facts", "provenance-ordered", 265),
            ("answer space", "what remains possible", 300),
            (f"{WORDS[total]} gates", f"{WORDS[hard]} hard, {WORDS[total - hard]} waivable", 315)]
    x, y, h = 48, 80, 105
    edges = []
    for i, (title, sub, w) in enumerate(row1):
        box(x, y, w, h, title, sub)
        edges.append((x, x + w))
        if i < len(row1) - 1:
            arrow(x + w, y + h / 2, x + w + 55)
        x += w + 55
    row2 = [("decide", "simplest wins, cited", 290),
            ("architect", "fingerprinted design", 290),
            ("emit", "code, evals, runbooks", 300),
            ("implement", "agent loop, fenced exam", 325)]
    x2, y2 = 48, 300
    last_x = edges[-1][1] - 100
    draw.line((last_x, y + h, last_x, 220), fill=EDGE, width=2)
    draw.line((last_x, 220, 140, 220), fill=EDGE, width=2)
    draw.line((140, 220, 140, y2 - 12), fill=EDGE, width=2)
    draw.polygon([(140, y2), (134, y2 - 12), (146, y2 - 12)], fill=EDGE)
    for i, (title, sub, w) in enumerate(row2):
        box(x2, y2, w, h, title, sub)
        if i < len(row2) - 1:
            arrow(x2 + w, y2 + h / 2, x2 + w + 55)
        x2 += w + 55
    lines = [
        (f"registry as data: {reg['dimensions']} dimensions * {reg['approaches']} approaches * "
         f"{reg['patterns']} patterns * {reg['stacks']} stacks * locales", BLUE),
        ("every decision cites its evidence -- overrides honoured, waivers shipped in RISKS.md",
         DIM),
        ("deterministic: same facts, byte-identical project. LLMs propose at every seam, "
         "decide at none.", DIM),
    ]
    for i, (text, colour) in enumerate(lines):
        draw.text((48, 465 + i * 40), text, font=body, fill=colour)
    out = ROOT / "assets" / "how-it-fits.png"
    image.save(out, optimize=True)
    print(f"wrote {out} ({total} gates, {hard} hard)")


if __name__ == "__main__":
    main()

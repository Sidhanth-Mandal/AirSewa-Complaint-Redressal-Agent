import sys
import pymupdf

src = sys.argv[1] if len(sys.argv) > 1 else "Scope of Work (1).pdf"
out = sys.argv[2] if len(sys.argv) > 2 else "scope of work.md"

doc = pymupdf.open(src)
with open(out, "w", encoding="utf-8") as f:
    f.write(f"# Scope of Work (extracted from {src})\n\n")
    for i, page in enumerate(doc, start=1):
        f.write(f"\n\n<!-- Page {i} -->\n\n")
        f.write(page.get_text("text", sort=True))

print(f"Extracted {len(doc)} pages -> {out}")

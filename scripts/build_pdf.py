#!/usr/bin/env python3
"""Build a single, plain PDF containing every question and answer in this repo.

The output is meant for straight-through reading (for example as an audiobook via
text-to-speech): no cover page, no table of contents, no module or section
headings, no page headers or footers. Just the numbered questions and answers,
module after module in README order.

Requires: pandoc and Node with Playwright (Chromium) available.

Usage:  python3 scripts/build_pdf.py [output.pdf]
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Module order mirrors the table in the top-level README.
MODULES = [
    "core-concepts",
    "ci-cd",
    "containers",
    "cloud",
    "infrastructure-as-code",
    "monitoring-logging",
    "networking-security",
    "automation-scripting",
    "linux-system-admin",
    "version-control",
    "best-practices",
    "mock-interviews",
]

# Emoji / pictographs / variation selectors — no emoji font is guaranteed at render time.
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF"
    "\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF⌀-⏿←-⇿"
    "‍️⃣✅❌✔✖⭐✨‼⁉ℹ〰〽]"
)

QUESTION_RE = re.compile(r"^### ")

CSS = """
@page { size: A4; margin: 18mm 16mm; }
html { font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1b1f23; }
body { margin: 0; }
h3 { font-size: 11.5pt; margin: 18px 0 6px 0; page-break-after: avoid; }
h4, h5 { font-size: 10.5pt; margin-top: 12px; page-break-after: avoid; }
p { margin: 5px 0 9px 0; }
code { font-family: "DejaVu Sans Mono", "Liberation Mono", monospace; font-size: 8.6pt; background: #f3f5f8; padding: 1px 3px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #d9dee5; border-radius: 4px; padding: 8px 10px; white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.3pt; line-height: 1.35; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px 0; font-size: 9.3pt; }
th, td { border: 1px solid #cfd6e0; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #e8eef8; }
tr { page-break-inside: avoid; }
blockquote { border-left: 4px solid #c8d3e6; margin: 8px 0; padding: 2px 12px; color: #444; }
ul, ol { margin: 4px 0 8px 0; padding-left: 22px; }
li { margin: 2px 0; }
li > p { margin: 2px 0; }
a { color: inherit; text-decoration: none; }
img { max-width: 100%; }
"""


def strip_to_qa(text: str) -> str:
    """Keep only question headings (###) and their answers.

    Drops the module title, intro paragraph, Part/Round headings and horizontal
    rules, but leaves fenced code blocks untouched (shell comments start with #).
    """
    out = []
    in_fence = False
    started = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if started:
                out.append(line)
            continue
        if in_fence:
            if started:
                out.append(line)
            continue
        if QUESTION_RE.match(line):
            started = True
        if not started:
            continue
        if re.match(r"^#{1,2} ", line) or re.match(r"^-{3,}\s*$", stripped) or re.match(r"^\*{3,}\s*$", stripped):
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"


def clean(text: str) -> str:
    text = EMOJI_RE.sub("", text)
    # Links to other module READMEs point nowhere inside a PDF: keep just the link text.
    text = re.sub(r"\[([^\]]+)\]\((?:\.\./)?[\w-]+/README\.md[^)]*\)", r"\1", text)
    # Collapse doubled spaces left behind by removed emoji in headings.
    text = re.sub(r"(#+ \*\*)\s+", r"\1", text)
    return text


def count_questions(text: str) -> int:
    return len(re.findall(r"^### \*{0,2}(?:Scenario )?\d+[.:]", text, flags=re.M))


def main() -> None:
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
        ROOT, "DevOps-Interview-Questions-and-Answers.pdf")

    parts = []
    total = 0
    for mod in MODULES:
        with open(os.path.join(ROOT, mod, "README.md"), encoding="utf-8") as fh:
            body = strip_to_qa(clean(fh.read()))
        total += count_questions(body)
        parts.append(body)

    with tempfile.TemporaryDirectory() as tmp:
        md_path = os.path.join(tmp, "all.md")
        css_path = os.path.join(tmp, "style.css")
        html_path = os.path.join(tmp, "all.html")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(parts))
        with open(css_path, "w", encoding="utf-8") as fh:
            fh.write(CSS)

        subprocess.run(
            [
                "pandoc", md_path, "-f", "gfm+tex_math_dollars", "-t", "html5",
                "--standalone", "--embed-resources", "--mathml",
                "--metadata", "title=DevOps Interview Questions and Answers",
                "--css", css_path, "-o", html_path,
            ],
            check=True,
        )
        # Pandoc emits a <header> title block; drop it so the text starts at question 1.
        with open(html_path, encoding="utf-8") as fh:
            html = fh.read()
        html = re.sub(r"<header id=\"title-block-header\">.*?</header>", "", html, flags=re.S)
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)

        js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://{html_path}', {{ waitUntil: 'load' }});
  await page.pdf({{ path: {out!r}, format: 'A4', printBackground: true, preferCSSPageSize: true }});
  await browser.close();
}})();
"""
        js_path = os.path.join(tmp, "print.js")
        with open(js_path, "w") as fh:
            fh.write(js)
        subprocess.run(["node", js_path], check=True)

    print(f"Wrote {out} ({total} questions, {len(MODULES)} modules)")


if __name__ == "__main__":
    main()

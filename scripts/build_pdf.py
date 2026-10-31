#!/usr/bin/env python3
"""Build a single PDF containing every question-and-answer module in this repo.

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

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
html { font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1b1f23; }
body { max-width: 100%; margin: 0; }
h1 { font-size: 22pt; color: #0b3d91; border-bottom: 3px solid #0b3d91; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 15pt; color: #0b3d91; border-bottom: 1px solid #c8d3e6; padding-bottom: 3px; margin-top: 26px; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 18px; margin-bottom: 6px; page-break-after: avoid; }
h4, h5 { font-size: 10.5pt; margin-top: 12px; page-break-after: avoid; }
p { margin: 5px 0 9px 0; }
code { font-family: "DejaVu Sans Mono", "Liberation Mono", monospace; font-size: 8.6pt; background: #f3f5f8; padding: 1px 3px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #d9dee5; border-radius: 4px; padding: 8px 10px; overflow-x: hidden; white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.3pt; line-height: 1.35; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px 0; font-size: 9.3pt; page-break-inside: auto; }
th, td { border: 1px solid #cfd6e0; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #e8eef8; }
tr { page-break-inside: avoid; }
blockquote { border-left: 4px solid #c8d3e6; margin: 8px 0; padding: 2px 12px; color: #444; background: #fafbfd; }
ul, ol { margin: 4px 0 8px 0; padding-left: 22px; }
li { margin: 2px 0; }
li > p { margin: 2px 0; }
hr { border: 0; border-top: 1px solid #d9dee5; margin: 16px 0; }
a { color: #0b3d91; text-decoration: none; }
img { max-width: 100%; }
.module { page-break-before: always; }
.cover { page-break-after: always; text-align: center; padding-top: 220px; }
.cover h1 { border: 0; font-size: 34pt; }
.cover .sub { font-size: 14pt; color: #444; margin-top: 12px; }
.cover .meta { font-size: 10pt; color: #666; margin-top: 60px; }
#TOC { page-break-after: always; }
#TOC > ul { list-style: none; padding-left: 0; }
#TOC > ul > li { margin: 6px 0; font-weight: bold; }
#TOC > ul > li > ul { font-weight: normal; margin: 2px 0 6px 0; list-style: none; padding-left: 18px; }
#TOC ul ul ul { display: none; }
#TOC a { color: #1b1f23; }
.toc-title { font-size: 22pt; color: #0b3d91; border-bottom: 3px solid #0b3d91; padding-bottom: 6px; }
"""


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
            body = clean(fh.read())
        total += count_questions(body)
        parts.append('<div class="module"></div>\n\n' + body.strip() + "\n")

    cover = (
        '<div class="cover">\n\n'
        "<h1>DevOps, SRE &amp; Platform Engineering<br>Interview Questions &amp; Answers</h1>\n\n"
        f'<p class="sub">{total:,} questions with detailed answers across {len(MODULES)} modules</p>\n\n'
        '<p class="meta">Compiled from the DevOps-Interview-Questions repository.<br>'
        "Source: https://github.com/NotHarshhaa/DevOps-Interview-Questions</p>\n\n</div>\n\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        md_path = os.path.join(tmp, "all.md")
        css_path = os.path.join(tmp, "style.css")
        html_path = os.path.join(tmp, "all.html")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(cover + "\n".join(parts))
        with open(css_path, "w", encoding="utf-8") as fh:
            fh.write(CSS)

        subprocess.run(
            [
                "pandoc", md_path, "-f", "gfm+tex_math_dollars", "-t", "html5",
                "--standalone", "--embed-resources", "--mathml",
                "--toc", "--toc-depth=2", "--metadata", "title=DevOps Interview Questions & Answers",
                "--css", css_path, "-o", html_path,
            ],
            check=True,
        )
        # Pandoc emits a <header> title block; drop it so the cover page stands alone, and label the TOC.
        with open(html_path, encoding="utf-8") as fh:
            html = fh.read()
        html = re.sub(r"<header id=\"title-block-header\">.*?</header>", "", html, flags=re.S)
        html = html.replace('<nav id="TOC" role="doc-toc">',
                            '<nav id="TOC" role="doc-toc"><div class="toc-title">Table of Contents</div>')
        # Move the TOC after the cover page.
        toc_match = re.search(r"<nav id=\"TOC\".*?</nav>", html, flags=re.S)
        cover_end = html.index("</div>", html.index('<div class="cover">')) + len("</div>")
        if toc_match and toc_match.start() < cover_end:
            toc_html = toc_match.group(0)
            html = html[:toc_match.start()] + html[toc_match.end():]
            cover_end = html.index("</div>", html.index('<div class="cover">')) + len("</div>")
            html = html[:cover_end] + "\n" + toc_html + html[cover_end:]
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)

        js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://{html_path}', {{ waitUntil: 'load' }});
  await page.pdf({{
    path: {out!r}, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<div style="font-size:7.5pt;color:#777;width:100%;padding:0 16mm;">DevOps Interview Questions &amp; Answers</div>',
    footerTemplate: '<div style="font-size:7.5pt;color:#777;width:100%;text-align:center;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
  }});
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

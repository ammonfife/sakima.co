#!/usr/bin/env python3
"""
md_to_html.py — Convert one or more Markdown files to styled HTML and open in browser.
Usage: python3 md_to_html.py file1.md [file2.md ...]
"""
import sys
import os
import subprocess

try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "-q"])
    import markdown

CSS = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.7;
    color: #1a1a2e;
    background: #f0f2f5;
    padding: 40px 20px;
  }
  .page {
    max-width: 1100px;
    margin: 0 auto;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 24px rgba(0,0,0,0.09);
    padding: 52px 64px;
  }
  .nav {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 32px;
    padding-bottom: 20px;
    border-bottom: 1px solid #e0e4f0;
  }
  .nav a {
    padding: 6px 16px;
    background: #2c3e8c;
    color: #fff;
    border-radius: 5px;
    text-decoration: none;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.01em;
  }
  .nav a:hover { background: #1a2a6c; }
  h1 {
    font-size: 24px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 6px;
    padding-bottom: 14px;
    border-bottom: 3px solid #2c3e8c;
    margin-top: 0;
  }
  h2 {
    font-size: 17px;
    font-weight: 700;
    color: #2c3e8c;
    margin-top: 38px;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 1px solid #dde1f0;
  }
  h3 {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
    margin-top: 26px;
    margin-bottom: 6px;
  }
  h4 { font-size: 14px; font-weight: 700; margin-top: 18px; margin-bottom: 4px; }
  p { margin: 10px 0 14px; }
  hr { border: none; border-top: 1px solid #e4e7f0; margin: 30px 0; }
  strong { font-weight: 700; }
  em { font-style: italic; }
  a { color: #2c3e8c; }
  ul, ol { padding-left: 24px; margin: 8px 0 14px; }
  li { margin-bottom: 5px; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
    margin: 16px 0 24px;
    table-layout: auto;
  }
  thead tr { background: #2c3e8c; color: #fff; }
  th {
    padding: 9px 13px;
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
  }
  td {
    padding: 8px 13px;
    border-bottom: 1px solid #e8eaf4;
    vertical-align: top;
    overflow-wrap: break-word;
    word-break: break-word;
  }
  /* Date-like cells — keep on one line */
  td:nth-child(3) { white-space: nowrap; }
  /* Code links in tables — allow wrap at path separators */
  td code, td a code { overflow-wrap: anywhere; word-break: break-all; }
  tbody tr:nth-child(even) { background: #f5f7ff; }
  tbody tr:hover { background: #eceffe; }
  code {
    background: #eef0f8;
    color: #2d2d8a;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 13px;
    font-family: "SFMono-Regular", "Fira Code", Consolas, monospace;
  }
  pre {
    background: #1a1a2e;
    color: #e8eaf4;
    padding: 18px 20px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 14px 0 20px;
    font-size: 13px;
    line-height: 1.6;
  }
  pre code {
    background: none;
    color: inherit;
    padding: 0;
    font-size: inherit;
  }
  blockquote {
    border-left: 4px solid #2c3e8c;
    padding: 8px 18px;
    color: #444;
    background: #f5f7ff;
    border-radius: 0 5px 5px 0;
    margin: 14px 0;
  }
  @media print {
    body { background: #fff; padding: 0; }
    .page { box-shadow: none; padding: 20px; }
    .nav { display: none; }
  }
</style>
"""


def convert(md_paths):
    html_paths = []
    basenames = [os.path.basename(p).replace(".md", ".html") for p in md_paths]

    for i, md_path in enumerate(md_paths):
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        body = markdown.markdown(
            md_content,
            extensions=["tables", "fenced_code"]
        )

        # Cross-nav bar when multiple files
        nav = ""
        if len(md_paths) > 1:
            links = "".join(
                f'<a href="{basenames[j]}">{basenames[j].replace(".html","")}</a>'
                for j in range(len(md_paths))
            )
            nav = f'<div class="nav">{links}</div>'

        title = os.path.basename(md_path).replace(".md", "").replace("_", " ")
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{CSS}
</head>
<body>
<div class="page">
{nav}
{body}
</div>
</body>
</html>"""

        out_path = os.path.splitext(md_path)[0] + ".html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Written: {out_path}")
        html_paths.append(out_path)

    return html_paths


def main():
    if len(sys.argv) < 2:
        print("Usage: md_to_html.py file1.md [file2.md ...]")
        sys.exit(1)

    md_paths = [os.path.abspath(p) for p in sys.argv[1:] if p.endswith(".md")]
    if not md_paths:
        print("No .md files provided.")
        sys.exit(1)

    html_paths = convert(md_paths)

    # Open in browser
    if sys.platform == "darwin":
        subprocess.run(["open"] + html_paths)
    else:
        for p in html_paths:
            subprocess.run(["xdg-open", p])


if __name__ == "__main__":
    main()

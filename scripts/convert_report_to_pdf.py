#!/usr/bin/env python3
"""
Convert technical_report.md to PDF using markdown2 + weasyprint.

Usage:
    python scripts/convert_report_to_pdf.py

Output:
    docs/technical_report.pdf
"""

import subprocess
import sys
from pathlib import Path


def convert_with_pandoc_html():
    """Convert markdown to PDF via HTML intermediate (no LaTeX needed)."""

    md_path = Path("docs/technical_report.md")
    html_path = Path("docs/technical_report.html")
    pdf_path = Path("docs/technical_report.pdf")

    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)

    print("Step 1: Converting markdown to HTML with pandoc...")

    # Pandoc markdown → HTML with nice styling
    pandoc_cmd = [
        "pandoc",
        str(md_path),
        "-o", str(html_path),
        "--standalone",
        "--toc",
        "--number-sections",
        "--css=https://cdn.jsdelivr.net/npm/water.css@2/out/water.css",
        "--metadata", "title=Technical Report: RAG-Based Cultural Events System",
    ]

    try:
        subprocess.run(pandoc_cmd, check=True)
        print(f"✓ HTML created: {html_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error running pandoc: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: pandoc not found. Install with: brew install pandoc")
        sys.exit(1)

    print("\nStep 2: Converting HTML to PDF with weasyprint...")
    print("Checking if weasyprint is installed...")

    try:
        import weasyprint
        print("✓ weasyprint found")
    except ImportError:
        print("✗ weasyprint not found")
        print("\nInstall with:")
        print("  pip install weasyprint")
        print("\nOr try option 4 in the script comments")
        sys.exit(1)

    try:
        weasyprint.HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        print(f"✓ PDF created: {pdf_path}")

        # Cleanup HTML
        html_path.unlink()
        print(f"✓ Cleaned up: {html_path}")

        print(f"\n🎉 Success! PDF report created at: {pdf_path}")

    except Exception as e:
        print(f"Error creating PDF: {e}")
        sys.exit(1)


def print_alternative_methods():
    """Print alternative conversion methods if weasyprint fails."""

    print("\n" + "="*70)
    print("ALTERNATIVE METHODS IF WEASYPRINT FAILS:")
    print("="*70)

    print("""
Option 1: Install BasicTeX (recommended for best quality)
---------------------------------------------------------
brew install --cask basictex
eval "$(/usr/libexec/path_helper)"
pandoc docs/technical_report.md -o docs/technical_report.pdf \\
  --pdf-engine=pdflatex --toc --number-sections \\
  -V geometry:margin=1in -V fontsize=11pt


Option 2: Use VS Code Extension
--------------------------------
1. Install "Markdown PDF" extension in VS Code
2. Open docs/technical_report.md
3. Cmd+Shift+P → "Markdown PDF: Export (pdf)"
4. PDF saved in same directory


Option 3: Use Typora (if installed)
------------------------------------
1. Open docs/technical_report.md in Typora
2. File → Export → PDF
3. Adjust page settings as needed


Option 4: Online Conversion
----------------------------
Upload to: https://www.markdowntopdf.com/
or: https://md2pdf.netlify.app/


Option 5: Copy to Google Docs
------------------------------
1. Copy markdown content from technical_report.md
2. Paste into Google Docs
3. Apply formatting (headings, code blocks, tables)
4. File → Download → PDF
""")


if __name__ == "__main__":
    print("Technical Report Markdown → PDF Converter")
    print("=" * 70)

    try:
        convert_with_pandoc_html()
    except Exception as e:
        print(f"\nConversion failed: {e}")
        print_alternative_methods()
        sys.exit(1)

"""Open the built document in Microsoft Word, update every field (contents, lists of figures and tables, page numbers),
save it, export a PDF copy, and render page previews for checking.

Usage: python finalize.py [--pages 1-5,12] [--no-pdf]
"""
import argparse
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
DOCX = BUILD.parent / 'Multi-Modal_GraphRAG_Project_Documentation.docx'
PDF = BUILD.parent / 'Multi-Modal_GraphRAG_Project_Documentation.pdf'
PREVIEW = BUILD / '_preview'

PS = r'''
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open("%(docx)s", $false, $false)
  $doc.Repaginate()
  foreach ($t in $doc.TablesOfContents) { $t.Update() }
  foreach ($t in $doc.TablesOfFigures) { $t.Update() }
  $null = $doc.Fields.Update()
  foreach ($t in $doc.TablesOfContents) { $t.UpdatePageNumbers() }
  foreach ($t in $doc.TablesOfFigures) { $t.UpdatePageNumbers() }
  $doc.Save()
  if ("%(pdf)s" -ne "") { $doc.ExportAsFixedFormat("%(pdf)s", 17) }
  Write-Output ("pages=" + $doc.ComputeStatistics(2))
  $doc.Close()
} finally { $word.Quit() }
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', default='')
    ap.add_argument('--no-pdf', action='store_true')
    a = ap.parse_args()
    script = PS % {'docx': str(DOCX), 'pdf': '' if a.no_pdf else str(PDF)}
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True, timeout=1800)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr[-2000:], file=sys.stderr)
        sys.exit(r.returncode)
    if a.pages and not a.no_pdf:
        import fitz
        PREVIEW.mkdir(exist_ok=True)
        doc = fitz.open(str(PDF))
        want = set()
        for part in a.pages.split(','):
            if '-' in part:
                x, y = part.split('-')
                want.update(range(int(x), int(y) + 1))
            elif part:
                want.add(int(part))
        for n in sorted(want):
            if 1 <= n <= doc.page_count:
                pix = doc[n - 1].get_pixmap(dpi=70)
                pix.save(str(PREVIEW / ('page-%03d.png' % n)))
        print('previews in', PREVIEW, 'pages', doc.page_count)


if __name__ == '__main__':
    main()

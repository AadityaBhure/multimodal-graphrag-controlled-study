"""Open the built IEEE paper in Microsoft Word, turn its equation markup into native Word equations, save it, export a PDF,
and render page previews for checking.

Display equations are paragraphs in the style "IEEE Equation" holding UnicodeMath text that ends in '#(n)'; inline
math is UnicodeMath between the delimiters U+27EA and U+27EB. Both are built up with Word's own math engine. Word can
silently swallow the text after an equation (for example an unquoted "min" read as a function), so the text that
follows every equation is compared before and after it is built, and no delimiter, unbuilt equation number or n-ary
placeholder may remain; any violation stops the script with an error.

Usage: python finalize_ieee.py [--pages 1-5,12] [--dpi 80] [--no-pdf]
"""
import argparse
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
DOCX = BUILD.parent / 'Multi-Modal_GraphRAG_IEEE.docx'
PDF = BUILD.parent / 'Multi-Modal_GraphRAG_IEEE.pdf'
PREVIEW = BUILD / '_preview'

PS = r'''
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $null
  $doc = $word.Documents.Open("%(docx)s", $false, $false)
  $warn = @()
  $eqs = @()
  foreach ($p in @($doc.Paragraphs)) { if ($p.Style.NameLocal -eq "IEEE Equation") { $eqs += $p } }
  $display = 0
  foreach ($p in $eqs) {
    $display++
    $follow = ""
    $nx = $p.Next(1)
    if ($nx) { $follow = $nx.Range.Text }
    $r = $p.Range
    $null = $r.MoveEnd(1, -1)
    $m = $doc.OMaths.Add($r)
    $m.OMaths.Item(1).BuildUp()
    $after = ""
    $nx = $p.Next(1)
    if ($nx) { $after = $nx.Range.Text }
    if ($after -ne $follow -or $p.Style.NameLocal -ne "IEEE Equation") { $warn += ("display equation " + $display) }
  }
  $MathL = [string][char]0x27EA
  $MathR = [string][char]0x27EB
  $inline = 0
  while ($true) {
    $r = $doc.Content
    $f = $r.Find
    $f.ClearFormatting()
    $f.Text = $MathL
    $f.Forward = $true
    $f.Wrap = 0
    $f.MatchWildcards = $false
    if (-not $f.Execute()) { break }
    $start = $r.Start
    $r2 = $doc.Range($start + 1, $doc.Content.End)
    $f2 = $r2.Find
    $f2.ClearFormatting()
    $f2.Text = $MathR
    $f2.Forward = $true
    $f2.Wrap = 0
    if (-not $f2.Execute()) { throw ("unmatched inline math at " + $start) }
    $end = $r2.Start
    $follow = $doc.Range($end + 1, [Math]::Min($end + 13, $doc.Content.End)).Text
    $cut = $follow.IndexOfAny([char[]]@([char]13, [char]7))
    if ($cut -ge 0) { $follow = $follow.Substring(0, $cut) }
    $null = $doc.Range($end, $end + 1).Delete()
    $null = $doc.Range($start, $start + 1).Delete()
    $mr = $doc.Range($start, $end - 1)
    $m = $doc.OMaths.Add($mr)
    $o = $m.OMaths.Item(1)
    $o.BuildUp()
    $inline++
    $ze = $o.Range.End
    $after = $doc.Range($ze, [Math]::Min($ze + $follow.Length + 1, $doc.Content.End)).Text
    $ok = $after.StartsWith($follow)
    if ($ok -and $cut -ge 0) { $ok = $after.Length -gt $follow.Length -and ($after[$follow.Length] -eq [char]13 -or $after[$follow.Length] -eq [char]7) }
    if (-not $ok) { $warn += ("inline equation " + $inline + " before '" + $follow + "'") }
  }
  $text = $doc.Content.Text
  foreach ($bad in @($MathL, $MathR, "#(", [string][char]0x2592)) { if ($text.Contains($bad)) { $warn += ("leftover " + $bad) } }
  $doc.Repaginate()
  if ($doc.Fields.Count -gt 0) { $null = $doc.Fields.Update(); $doc.Repaginate() }
  $doc.Save()
  if ("%(pdf)s" -ne "") { $doc.ExportAsFixedFormat("%(pdf)s", 17) }
  Write-Output ("display=" + $display + " inline=" + $inline + " omaths=" + $doc.OMaths.Count + " pages=" + $doc.ComputeStatistics(2))
  foreach ($w in $warn) { Write-Output ("WARNING " + $w) }
  $doc.Close()
  $doc = $null
} finally {
  if ($doc) { try { $doc.Close(0) } catch {} }
  $word.Quit()
}
'''


def pages_arg(spec, n):
    if not spec or spec == 'all':
        return list(range(1, n + 1))
    want = set()
    for part in spec.split(','):
        if '-' in part:
            x, y = part.split('-')
            want.update(range(int(x), int(y) + 1))
        elif part:
            want.add(int(part))
    return sorted(p for p in want if 1 <= p <= n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', default='all')
    ap.add_argument('--dpi', type=int, default=80)
    ap.add_argument('--no-pdf', action='store_true')
    ap.add_argument('--docx', default=str(DOCX), help='document to finalize (default: the IEEE paper)')
    ap.add_argument('--preview', default=None, help='folder for page previews (default: build/_preview next to the docx)')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    docx = Path(a.docx).resolve()
    pdf = docx.with_suffix('.pdf')
    preview = Path(a.preview) if a.preview else (PREVIEW if docx == DOCX else docx.parent / 'build' / '_preview')
    script = PS % {'docx': str(docx), 'pdf': '' if a.no_pdf else str(pdf)}
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=1800)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr[-3000:], file=sys.stderr)
        sys.exit(r.returncode)
    if 'WARNING' in r.stdout:
        print('equation build-up changed the surrounding text; fix the equations listed above', file=sys.stderr)
        sys.exit(3)
    if not a.no_pdf:
        import pymupdf
        preview.mkdir(parents=True, exist_ok=True)
        for old in preview.glob('page-*.png'):
            old.unlink()
        doc = pymupdf.open(str(pdf))
        for n in pages_arg(a.pages, doc.page_count):
            doc[n - 1].get_pixmap(dpi=a.dpi).save(str(preview / ('page-%02d.png' % n)))
        print('previews in', preview, '| pages', doc.page_count)


if __name__ == '__main__':
    main()

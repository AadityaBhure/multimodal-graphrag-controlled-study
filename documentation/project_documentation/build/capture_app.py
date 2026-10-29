"""Capture the showcase app page by page with headless Chrome over the DevTools protocol.

Usage (needs an interpreter with websocket-client and Pillow; the app must be running):
    python capture_app.py [--url http://localhost:8610] [--out ../screens] [--only problem,try]

For every capture it writes:
    <name>__view.png          the first screen as a visitor sees it (sidebar included)
    <name>__full.png          the whole page
    <name>__NN.png            crops of the main column, one per page section (long sections split at element boundaries)
and screens/manifest.json listing every image with its page, section and size.
"""
import argparse, base64, io, json, os, subprocess, sys, time, urllib.request
from pathlib import Path
from PIL import Image
from websocket import create_connection

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9333
WIDTH, HEIGHT, DPR = 1440, 900, 1.25
MAX_CROP = 1250          # CSS pixels: longest crop before a section is split at an element boundary

# (name, url path + query, actions run after the first render, caption of the capture)
CAPTURES = [
    ('p01_problem', '', [], 'The problem'),
    ('p02_parts', 'parts', [], 'Four parts'),
    ('p03_data', 'data', ['expand:Graph relations by type'], 'Data and benchmark'),
    ('p03_data_conflict', 'data', ['tab:Conflict'], 'Data and benchmark (conflict variant tab)'),
    ('p04_metrics', 'metrics', [], 'Metrics and statistics'),
    ('p05_rq1', 'context', [], 'Part 1 · Context management'),
    ('p06_rq2', 'fusion', [], 'Part 2 · Fusion'),
    ('p07_rq3', 'retrieval-control', ['expand:Failure labels per policy'], 'Part 3 · Retrieval control'),
    ('p08_rq4', 'combined', ['expand:The pre-registered selection rule'], 'Part 4 · Combined system'),
    ('p09_summary', 'conclusions', [], 'Conclusions'),
    ('p10_try', 'try', [], 'Try a question (recorded runs)'),
    ('p10_try_live', 'try', ['button:Live run'], 'Try a question (live run builder)'),
    ('p11_repro', 'reproducibility', [], 'Reproducibility'),
    ('p01_present', '?present=1', [], 'Presentation mode'),
    ('p10_try_compare', 'try', ['select:Compare with|AR-03'], 'Try a question (two recorded pipelines side by side)'),
    ('p10_try_expanded', 'try', ['expand:Model calls', 'expand:Exact context'], 'Try a question (model calls and exact context opened)'),
    ('p07_rq3_compare', 'retrieval-control', ['select:Compare side by side with|AR-03'], 'Part 3 explorer, two policies side by side'),
    ('p10_try_liverun', 'try', ['button:Live run', 'button:Run the pipeline'], 'Try a question (a live run)'),
]


class CDP:
    def __init__(self, url):
        self.ws = create_connection(url, suppress_origin=True, timeout=300, max_size=None)
        self.n = 0

    def call(self, method, **params):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == mid:
                if 'error' in msg:
                    raise RuntimeError('%s: %s' % (method, msg['error']))
                return msg.get('result', {})

    def js(self, expr):
        r = self.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=True)
        if 'exceptionDetails' in r:
            raise RuntimeError(json.dumps(r['exceptionDetails'])[:600])
        return r.get('result', {}).get('value')


STATE_JS = r"""(() => {
  const main = document.querySelector('[data-testid="stMain"]');
  const block = document.querySelector('[data-testid="stMainBlockContainer"]');
  const running = [...document.querySelectorAll('[data-testid="stStatusWidget"]')].some(e => /running/i.test(e.innerText));
  const spinners = document.querySelectorAll('[data-testid="stSpinner"]').length;
  const charts = [...document.querySelectorAll('[data-testid="stVegaLiteChart"]')];
  const drawn = charts.filter(c => c.querySelector('canvas, svg')).length;
  const frames = [...document.querySelectorAll('iframe')];
  const framesReady = frames.every(f => { try { return f.contentDocument && f.contentDocument.readyState === 'complete'; } catch (e) { return true; } });
  return {ok: !!(main && block && block.innerText.length > 50), running, spinners, charts: charts.length, drawn, framesReady,
          height: main ? main.scrollHeight : 0, fonts: document.fonts.status};
})()"""

GEOMETRY_JS = r"""(() => {
  const main = document.querySelector('[data-testid="stMain"]');
  const sb = document.querySelector('[data-testid="stSidebar"]');
  const block = document.querySelector('[data-testid="stMainBlockContainer"]');
  const top = main.getBoundingClientRect().top - main.scrollTop;
  const y = e => Math.round(e.getBoundingClientRect().top - top);
  const vb = block.querySelector('[data-testid="stVerticalBlock"]');
  const kids = [...vb.children].filter(e => e.getBoundingClientRect().height > 0);
  const sbw = sb && getComputedStyle(sb).display !== 'none' && sb.getAttribute('aria-expanded') !== 'false' ? Math.round(sb.getBoundingClientRect().right) : 0;
  return {sidebar: Math.max(0, sbw), height: main.scrollHeight, blockTop: y(block),
          sections: [...block.querySelectorAll('h2[id]')].map(h => ({id: h.id, title: h.innerText.trim(), y: y(h.closest('[data-testid="stElementContainer"]') || h)})),
          bounds: kids.map(k => [y(k), Math.round(y(k) + k.getBoundingClientRect().height)]),
          title: (document.querySelector('h1') || {innerText: ''}).innerText.trim()};
})()"""


CENTER = """(() => { const el = %s; if (!el) return null; el.scrollIntoView({block: 'center'});
                const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()"""


def finder(kind, arg):
    a = json.dumps(arg)
    if kind == 'expand':
        return "[...document.querySelectorAll('[data-testid=\"stExpander\"] summary')].find(x => x.innerText.includes(%s))" % a
    if kind == 'tab':
        return "[...document.querySelectorAll('[role=\"tab\"]')].find(x => x.innerText.trim() === %s)" % a
    if kind == 'button':
        return "[...document.querySelectorAll('button')].find(x => x.innerText.trim() === %s)" % a
    if kind == 'selectbox':
        return ("(([...document.querySelectorAll('[data-testid=\"stSelectbox\"]')].find(x => x.innerText.includes(%s)) || {querySelector: () => null})"
                ".querySelector('[role=\"combobox\"]'))" % a)
    if kind == 'option':
        return "[...document.querySelectorAll('[role=\"option\"]')].find(x => x.innerText.includes(%s))" % a
    raise ValueError(kind)


def click(cdp, kind, arg):
    xy = cdp.js(CENTER % finder(kind, arg))
    if not xy:
        return False
    time.sleep(0.4)
    xy = cdp.js(CENTER % finder(kind, arg))
    for t in ('mouseMoved', 'mousePressed', 'mouseReleased'):
        cdp.call('Input.dispatchMouseEvent', type=t, x=xy[0], y=xy[1], button='left', clickCount=1)
    return True


def act(cdp, a):
    kind, _, arg = a.partition(':')
    if kind == 'select':
        label, _, option = arg.partition('|')
        if not click(cdp, 'selectbox', label):
            return False
        time.sleep(0.8)
        cdp.call('Input.insertText', text=option)
        time.sleep(1.2)
        for t in ('keyDown', 'keyUp'):
            cdp.call('Input.dispatchKeyEvent', type=t, key='Enter', code='Enter', windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
        return True
    return click(cdp, kind, arg)


def wait_ready(cdp, timeout=150, settle=3):
    t0, last, stable = time.time(), None, 0
    while time.time() - t0 < timeout:
        s = cdp.js(STATE_JS)
        ready = s['ok'] and not s['running'] and not s['spinners'] and s['drawn'] == s['charts'] and s['framesReady'] and s['fonts'] == 'loaded'
        key = (s['height'], s['charts'], s['drawn'])
        stable = stable + 1 if ready and key == last else 0
        last = key
        if stable >= settle:
            return s
        time.sleep(0.7)
    print('  warning: page did not settle', s, file=sys.stderr)
    return s


def shot(cdp):
    data = cdp.call('Page.captureScreenshot', format='png', fromSurface=True)['data']
    return Image.open(io.BytesIO(base64.b64decode(data))).convert('RGB')


def metrics(cdp, h):
    cdp.call('Emulation.setDeviceMetricsOverride', width=WIDTH, height=int(h), deviceScaleFactor=DPR, mobile=False)


def chunks(start, end, bounds):
    """Split [start, end) at element boundaries into pieces of at most MAX_CROP (a single taller element stays whole)."""
    cuts = sorted({b for b, _ in bounds if start < b < end})
    out, a = [], start
    while end - a > MAX_CROP:
        fit = [c for c in cuts if a + 250 < c <= a + MAX_CROP]
        if not fit:
            nxt = [c for c in cuts if c > a + 250]
            if not nxt:
                break
            fit = [nxt[0]]
        out.append((a, fit[-1]))
        a = fit[-1]
    out.append((a, end))
    return out


def capture(cdp, base, name, path, actions, caption, outdir):
    metrics(cdp, HEIGHT)
    cdp.call('Page.navigate', url=base.rstrip('/') + '/' + path)
    time.sleep(2.5)
    wait_ready(cdp)
    for a in actions:
        ok = act(cdp, a)
        print('  action', a, '->', ok)
        time.sleep(2.0)
        wait_ready(cdp, timeout=420)
    cdp.js("document.querySelector('[data-testid=\"stMain\"]').scrollTo(0, 0)")
    time.sleep(0.6)
    view = shot(cdp)
    view.save(outdir / ('%s__view.png' % name), optimize=True)
    g = cdp.js(GEOMETRY_JS)
    for _ in range(4):                      # grow the viewport until the whole page fits without inner scrolling
        metrics(cdp, g['height'] + 40)
        time.sleep(1.2)
        wait_ready(cdp, settle=2)
        g2 = cdp.js(GEOMETRY_JS)
        if abs(g2['height'] - g['height']) < 4:
            g = g2
            break
        g = g2
    time.sleep(1.0)
    full = shot(cdp)
    full.save(outdir / ('%s__full.png' % name), optimize=True)
    sx = g['sidebar']
    secs = g['sections']
    end = max(b for _, b in g['bounds']) + 24 if g['bounds'] else g['height']
    pieces = [('header', 'Page header', max(0, g['blockTop'] - 8), secs[0]['y'] - 14 if secs else end)]
    for i, s in enumerate(secs):
        stop = secs[i + 1]['y'] - 6 if i + 1 < len(secs) else end
        pieces.append((s['id'], s['title'], s['y'] - 2, stop))
    items, k = [], 0
    for sid, title, a, b in pieces:
        parts = chunks(a, b, g['bounds'])
        for j, (y0, y1) in enumerate(parts):
            k += 1
            box = (int(sx * DPR), int(y0 * DPR), int(WIDTH * DPR), int(min(y1, g['height'] + 40) * DPR))
            if box[3] - box[1] < 30:
                continue
            img = full.crop(box)
            fn = '%s__%02d.png' % (name, k)
            img.save(outdir / fn, optimize=True)
            items.append({'file': fn, 'section_id': sid, 'section': title, 'part': j + 1, 'parts': len(parts), 'size': list(img.size)})
    print('  %s: %d crops, page height %d px' % (name, len(items), g['height']))
    return {'name': name, 'path': path, 'caption': caption, 'title': g['title'], 'view': '%s__view.png' % name, 'full': '%s__full.png' % name,
            'sidebar_px': sx, 'height_px': g['height'], 'crops': items, 'sections': [s['title'] for s in secs]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://localhost:8610')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'screens'))
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    prof = Path(os.environ.get('TEMP', '.')) / 'mmg_doc_chrome_profile'
    proc = subprocess.Popen([CHROME, '--headless=new', '--remote-debugging-port=%d' % PORT, '--user-data-dir=%s' % prof, '--remote-allow-origins=*',
                             '--window-size=%d,%d' % (WIDTH, HEIGHT), '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
                             '--force-color-profile=srgb', '--lang=en-US', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=2))
                break
            except Exception:
                time.sleep(0.5)
        page = [t for t in tabs if t['type'] == 'page'][0]
        cdp = CDP(page['webSocketDebuggerUrl'])
        cdp.call('Page.enable')
        cdp.call('Runtime.enable')
        cdp.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'light'}])
        manifest_path = out / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
        only = set(x for x in a.only.split(',') if x)
        for name, path, actions, caption in CAPTURES:
            if only and name not in only:
                continue
            print('capture', name, path)
            manifest[name] = capture(cdp, a.url, name, path, actions, caption, out)
            manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')
    finally:
        proc.terminate()


if __name__ == '__main__':
    main()

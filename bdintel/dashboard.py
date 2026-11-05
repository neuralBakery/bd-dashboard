import json
import os
import re
import tempfile
from pathlib import Path
from .engine import ROOT, local_date, assess


def briefing(state):
    records = [r for r in state['records'] if r.get('verification') == 'source checked']
    records.sort(key=lambda r: (r.get('assessment', {}).get('score', 0), r.get('date', '')), reverse=True)
    recent = [r for r in records if r.get('change') in ('New', 'Updated') and r.get('assessment', {}).get('ageDays') is not None and 0 <= r['assessment']['ageDays'] <= 45]
    lines = ['REGIONAL VICTORIA — WEEKLY INTELLIGENCE', 'Generated: ' + local_date(),
             'Last successful bounded research run: ' + (state['lastSuccessfulRun'] or 'None'),
             'Latest run: ' + (state['runs'][-1]['status'] if state['runs'] else 'Not run'),
             'Direct employer hiring does not confirm external provider demand.', '']
    if not recent:
        lines.append('No verified recent new or materially updated findings available. This does not establish that no developments occurred.')
    for r in recent[:5]:
        lines += [f"{r['company']} — {r['headline']} [{r['priority']}; {r['change']}]", r['summary'],
                  'Why it matters / next step (inference): ' + r['angle'], 'Source: ' + r['url'],
                  'Assessment: ' + '; '.join(r['assessment']['reasons']), '']
    lines += ['COVERAGE / FAILURES']
    for item in (state['runs'][-1].get('sources', []) if state['runs'] else []):
        lines.append(item['name'] + ': ' + item['status'] + (' — ' + item.get('error', '') if item.get('error') else ''))
    return '\n'.join(lines)


def render(state, root=ROOT):
    state = json.loads(json.dumps(state))
    for r in state['records']:
        r['assessment'] = assess(r)
        r['priority'] = r['assessment']['priority']
    template = (root / 'assets/dashboard-template.html').read_text()
    css = re.search(r'<style>(.*?)</style>', template, re.S)[1]
    css += '\n.filters{display:flex;flex-wrap:wrap}.filters>*{max-width:100%;min-width:140px;flex:1 1 140px}.filters #search{flex:1 1 100%;width:100%;min-width:200px}.notice.failed{background:#fff1e8;border-color:#db9b78}.notice{margin-bottom:16px}.detailsection pre{white-space:pre-wrap}.navlink{cursor:pointer}.signal{cursor:pointer}.risk{background:#fff0e8}.small{overflow-wrap:anywhere}button:focus-visible,a:focus-visible{outline:3px solid #579426}.stale{color:#a44b00}#detail{max-width:900px}textarea{width:100%;min-height:100px}.metric-num{font-size:30px}\n'
    payload = json.dumps({'state': state, 'brief': briefing(state)}, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    body = (root / 'assets/app.html').read_text()
    js = (root / 'assets/app.js').read_text()
    document = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Regional Market Intelligence</title><style>' + css + '</style></head><body>' + body + '<script id="payload" type="application/json">' + payload + '</script><script>' + js + '</script></body></html>'
    target = root / 'dashboard.html'
    fd, tmp = tempfile.mkstemp(dir=root, prefix='.dashboard-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(document)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    (root / 'data/weekly-brief.txt').write_text(briefing(state) + '\n')

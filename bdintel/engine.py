from __future__ import annotations
import copy
import hashlib
import html
import json
import os
import re
import tempfile
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = [
 ('Closure & restructuring', r'clos(?:ure|ing|ed)|redundan|restructur|receivership|administration'),
 ('Competitor activity', r'labour hire|recruitment agency|staffing agency'),
 ('Ownership & M&A', r'acquisit|merger|acquir|ownership'),
 ('Hiring & workforce', r'vacanc|recruit|hiring|seasonal|workforce shortage'),
 ('Expansion & investment', r'expan|invest|new facilit|production capacity|new factory'),
 ('Tenders & contracts', r'tender|contract award|procurement'),
 ('Infrastructure & construction', r'construction|infrastructure|industrial precinct|enterprise park'),
 ('Market trends', r'employment|unemployment|economic|labour market'),
]
RELEVANT = re.compile('|'.join(p for _, p in CATEGORIES), re.I)
INDUSTRIAL = re.compile(r'manufactur|process|factory|warehouse|logistics|agricultur|harvest|production|industrial|construction|food|transport|trade', re.I)

def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

def local_date(timestamp=None):
    return (datetime.fromisoformat(timestamp) if timestamp else datetime.now(timezone.utc)).astimezone(ZoneInfo('Australia/Melbourne')).date().isoformat()

def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(str(value)).date().isoformat()
        except (ValueError, TypeError, OverflowError):
            return None

def canonical(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Only credential-free HTTPS evidence URLs are supported')
    q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    q = [(k, v) for k, v in q if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urllib.parse.urlunsplit(('https', p.netloc.lower(), p.path.rstrip('/') or '/', urllib.parse.urlencode(sorted(q)), ''))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def initialise(root=ROOT):
    path = root / 'data/state.json'
    if path.exists():
        return json.loads(path.read_text())
    records = json.loads((root / 'data/legacy.json').read_text())
    for r in records:
        r.update(verification='unverified legacy', firstDiscovered=None, lastChecked=None,
                 relationship='Unverified', history=[], evidence=[], priority='Monitor',
                 originalPriority=r['priority'], originalDate=r['date'], change='Legacy',
                 contact='Relevant operations / HR role — name unverified', contactUrl='',
                 originalContact=r.get('contact', ''), originalContactUrl=r.get('contactUrl', ''),
                 confidence='Unverified imported research — not checked against live source')
        r['summary'] = 'UNVERIFIED IMPORT: ' + r['summary']
        r['assessment'] = assess(r)
    state = {'schema': 'psw-regional-bd-v2', 'revision': 0, 'lastSuccessfulRun': None,
             'records': records, 'runs': []}
    atomic_json(path, state)
    return state

def assess(r, today=None):
    today = date.fromisoformat(today or local_date())
    d = parse_date(r.get('date'))
    age = (today - date.fromisoformat(d)).days if d else None
    verified = r.get('verification') == 'source checked'
    fresh = verified and age is not None and 0 <= age <= 45
    text = r.get('summary', '')
    demand = 4 if re.search(r'\b(?:jobs|vacanc\w*|recruit\w*|hiring|workers|operators)\b', text, re.I) else (2 if r.get('type') == 'Expansion & investment' else 0)
    fit = 3 if INDUSTRIAL.search(text + ' ' + r.get('sector', '')) else 0
    timing = 2 if fresh else 0
    volume = 2 if re.search(r'\b\d+\s+(?:new\s+)?(?:jobs|workers|positions)|seasonal|multiple shifts|ongoing', text, re.I) else 0
    strength = (3 if r.get('primarySource') else 2) if fresh else (1 if verified else 0)
    points = {'workforceDemand': demand, 'serviceRelevance': fit, 'timing': timing, 'commercialPotential': volume, 'evidenceStrength': strength}
    total = sum(points.values())
    separate = r.get('type') in ('Closure & restructuring', 'Market trends', 'Competitor activity')
    priority = 'High' if fresh and total >= 11 and demand >= 2 else ('Medium' if fresh and total >= 7 else 'Monitor')
    if separate or not verified or r.get('company') == 'Organisation unverified':
        priority = 'Monitor'
    reasons = [f'{k}: {v}' for k, v in points.items()]
    reasons += ['Published direct recruitment does not confirm external provider demand.']
    if not verified:
        reasons.append('Source not verified: no actionable priority assigned.')
    if age is None:
        reasons.append('Publication date unknown; freshness cannot be established.')
    elif age < 0:
        reasons.append('Future publication date: excluded from current opportunities.')
    elif age > 45:
        reasons.append('Older than 45 days: current demand requires rechecking.')
    if separate:
        reasons.append('Risk, competitor or economic context: separated from sales opportunities.')
    return {'score': total, 'maximum': 14, 'criteria': points, 'priority': priority, 'reasons': reasons, 'ageDays': age}

def geography(text, config):
    results = []
    for branch, towns in config['catchments'].items():
        for town in towns:
            if re.search(r'(?<!\w)' + re.escape(town) + r'(?!\w)', text, re.I):
                results.append((branch, town))
    if not results:
        for town in config.get('outside_catchment_locations', []):
            if re.search(r'(?<!\w)' + re.escape(town) + r'(?!\w)', text, re.I):
                results.append(('Outside catchment', town))
    return results

def candidate(article, source, config, legacy):
    title, paragraphs = article['title'], article['paragraphs']
    # Keep source text verbatim; a matched phrase is a signal, never proof of labour-hire demand.
    meaningful = [p for p in paragraphs if len(p) >= 60]
    text = title + '\n' + '\n'.join(meaningful)
    if not RELEVANT.search(text):
        return []
    places = geography(text, config)
    if not places:
        return []
    category = next((c for c, pattern in CATEGORIES if re.search(pattern, title, re.I)), None)
    category = category or next(c for c, pattern in CATEGORIES if re.search(pattern, text, re.I))
    quotes = [p for p in meaningful if RELEVANT.search(p) or INDUSTRIAL.search(p)][:4]
    if not quotes:
        return []
    organisations = {}
    for old in legacy:
        # Exact documented names only, without inventing named people or conflating projects.
        name = old['company']
        if name.lower() in text.lower():
            organisations[name] = old
    for name in article.get('organisations', []):
        if isinstance(name, str) and 2 <= len(name) <= 180 and name.lower() in text.lower():
            organisations.setdefault(name, {})
    if not organisations:
        organisations['Organisation unverified'] = {}
    out = []
    for company, old in organisations.items():
        branch, town = next((p for p in places if p[0] == old.get('region')), places[0])
        url = canonical(article['url'])
        identity = digest([url, company.casefold()])[:20]
        company_quotes = [p for p in quotes if company.lower() in p.lower()]
        # Do not attach another company's workforce numbers to this business.
        selected_quotes = company_quotes or (quotes if company.lower() in title.lower() or company == 'Organisation unverified' else [])
        if not selected_quotes:
            continue
        summary = '\n\n'.join(selected_quotes)
        r = dict(id='A' + identity, company=company, region=branch, town=town,
                 geographicMatches=[{'branch': b, 'town': t} for b, t in places],
                 sector=old.get('sector', 'Industry unverified'), type=category,
                 date=article.get('date') or '', headline=title, summary=summary,
                 source=source['name'], url=url, state='New', note='',
                 contact='Operations / HR / procurement role — name unverified', contactUrl='',
                 relationship='Unverified', primarySource=source.get('primary', False),
                 verification='source checked', confidence='Source text checked; commercial relevance is inference',
                 firstDiscovered=now(), lastChecked=now(), change='New', history=[],
                 evidence=[{'url': url, 'publisher': source['name'], 'publicationDate': article.get('date'),
                            'retrievedAt': now(), 'sha256': article['sha256'], 'snapshot': article['snapshot'],
                            'quotes': selected_quotes}],
                 angle='Inference: investigate site timing, workforce plans and existing supplier arrangements. External recruitment demand is unconfirmed.')
        r['assessment'] = assess(r)
        r['priority'] = r['assessment']['priority']
        out.append(r)
    return out

def merge(records, candidates):
    out = copy.deepcopy(records)
    keys = {(canonical(r['url']), r['company'].casefold()): r for r in out}
    added = updated = 0
    for r in candidates:
        key = (canonical(r['url']), r['company'].casefold())
        existing = keys.get(key)
        if existing:
            material = any(existing.get(k) != r.get(k) for k in ('headline', 'summary', 'date', 'type'))
            if material:
                snapshot = {k: copy.deepcopy(v) for k, v in existing.items() if k != 'history'}
                history = existing.get('history', []) + [snapshot]
                retained = {k: existing.get(k) for k in ('id', 'firstDiscovered', 'note', 'state', 'relationship')}
                evidence = existing.get('evidence', []) + r['evidence']
                existing.update(r)
                existing.update(retained)
                existing['firstDiscovered'] = retained['firstDiscovered'] or r['firstDiscovered']
                existing['history'], existing['evidence'] = history, evidence
                existing['change'], existing['changedAt'] = 'Updated', now()
                updated += 1
            else:
                existing['lastChecked'] = r['lastChecked']
                existing['change'] = 'Unchanged'
        else:
            r = copy.deepcopy(r)
            r['changedAt'] = now()
            out.append(r)
            keys[key] = r
            added += 1
    return out, added, updated

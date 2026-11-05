"""Bounded, robots-aware public-source collection. No browser automation or paywall bypass."""
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from .engine import canonical, parse_date, now, digest

AGENT = 'RegionalBDResearch/1.0'
MAX_BYTES = 3_000_000

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.date = None
        self.paragraphs = []
        self.links = []
        self._capture = None
        self._buffer = []
        self._skip = 0
        self._json = False
        self._jsonbuf = []
        self.structured = []
        self.organisations = []
        self.restricted = False
        self._main = 0
        self._body_finished = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('main', 'article'):
            self._main += 1
            self._body_finished = False
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            if tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
                self._json = True
                self._jsonbuf = []
            self._skip += 1
        if tag == 'meta':
            key = a.get('property', a.get('name', '')).lower()
            if key in ('article:published_time', 'datepublished', 'date', 'dc.date.issued', 'dcterms.issued'):
                self.date = parse_date(a.get('content')) or self.date
            if key in ('robots', 'regionalbdresearch') and any(x in a.get('content', '').lower() for x in ('noarchive', 'nosnippet', 'noai')):
                self.restricted = True
        if tag == 'time' and not self.date:
            self.date = parse_date(a.get('datetime'))
        if tag == 'h1' and not self._skip:
            self.paragraphs = []
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if not self._skip and not self._body_finished and (tag in ('h1', 'title', 'p') or (tag == 'li' and self._main)) and self._capture is None:
            self._capture = tag
            self._buffer = []

    def handle_data(self, data):
        if self._json:
            self._jsonbuf.append(data)
        elif not self._skip and self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if tag in ('main', 'article'):
            self._main = max(0, self._main - 1)
            self._body_finished = not self._main
        if tag == 'script' and self._json:
            try:
                self.structured.append(json.loads(''.join(self._jsonbuf)))
            except (ValueError, TypeError):
                pass
            self._json = False
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self._skip = max(0, self._skip - 1)
        if tag == self._capture:
            value = re.sub(r'\s+', ' ', ''.join(self._buffer)).strip()
            if tag == 'h1' or (tag == 'title' and not self.title):
                self.title = value
            elif value and tag in ('p', 'li'):
                self.paragraphs.append(value)
            self._capture = None

    def finish(self):
        def walk(obj):
            if isinstance(obj, dict):
                for field in ('hiringOrganization', 'about'):
                    values = obj.get(field, [])
                    for value in values if isinstance(values, list) else [values]:
                        if isinstance(value, dict) and value.get('@type') in ('Organization', 'Corporation', 'LocalBusiness') and isinstance(value.get('name'), str):
                            self.organisations.append(value['name'])
                if obj.get('isAccessibleForFree') in (False, 'False', 'false'):
                    self.restricted = True
                if not self.date and obj.get('datePublished'):
                    self.date = parse_date(obj['datePublished'])
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        for obj in self.structured:
            walk(obj)
        return self

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, host):
        self.host = host
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).hostname != self.host or not newurl.startswith('https://'):
            raise ValueError('Cross-host or non-HTTPS redirect: configure the final source explicitly')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Collector:
    def __init__(self, root, config):
        self.root, self.config = Path(root), config
        self.robots = {}
        self.last_request = {}
        self.audit = []

    def _request(self, url, delay=0):
        url = canonical(url)
        host = urllib.parse.urlsplit(url).hostname
        interval = max(self.config.get('request_interval_seconds', 2), delay)
        time.sleep(max(0, self.last_request.get(host, 0) + interval - time.monotonic()))
        self.last_request[host] = time.monotonic()
        opener = urllib.request.build_opener(SafeRedirect(host))
        req = urllib.request.Request(url, headers={'User-Agent': AGENT, 'Accept': 'text/html,application/rss+xml,application/xml'})
        with opener.open(req, timeout=25) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Source exceeds safe size limit')
            return raw, response.headers.get_content_charset() or 'utf-8'

    def fetch(self, url):
        url = canonical(url)
        p = urllib.parse.urlsplit(url)
        origin = f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            robot_url = origin + '/robots.txt'
            parser = urllib.robotparser.RobotFileParser(robot_url)
            try:
                raw, enc = self._request(robot_url)
                parser.parse(raw.decode(enc, errors='replace').splitlines())
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise ValueError(f'Robots access failed ({e.code}); collection stopped') from e
                parser.parse([])
            self.robots[origin] = parser
        parser = self.robots[origin]
        if not parser.can_fetch(AGENT, url):
            raise ValueError('Robots disallows this URL')
        raw, enc = self._request(url, parser.crawl_delay(AGENT) or 0)
        text = raw.decode(enc, errors='replace')
        visible = Page()
        visible.feed(text)
        visible.finish()
        challenge_text = visible.title + '\n' + '\n'.join(visible.paragraphs)
        if re.search(r'checking your browser|verify you are human|complete the captcha|just a moment\.\.\.', challenge_text, re.I):
            raise ValueError('Access protection encountered; not bypassed')
        sha = hashlib.sha256(raw).hexdigest()
        rel = f'data/evidence/{sha}.txt'
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
        self.audit.append({'url': url, 'retrievedAt': now(), 'sha256': sha, 'snapshot': rel})
        return text, sha, rel

    def article(self, url):
        text, sha, snapshot = self.fetch(url)
        p = Page()
        p.feed(text)
        p.finish()
        if p.restricted:
            raise ValueError('Publisher restricts access or reuse; not collected')
        if not p.title or not p.paragraphs:
            raise ValueError('No readable title/article text; source adapter needs review')
        return {'url': canonical(url), 'title': p.title, 'date': p.date,
                'paragraphs': p.paragraphs, 'organisations': p.organisations, 'sha256': sha, 'snapshot': snapshot}

    def source(self, source, extra_urls=()):
        text, sha, snapshot = self.fetch(source['url'])
        page = Page()
        page.feed(text)
        page.finish()
        if page.restricted:
            raise ValueError('Publisher restricts source reuse')
        links = []
        try:
            doc = ET.fromstring(text.lstrip())
            for item in list(doc.findall('.//item')) + list(doc.findall('.//{http://www.w3.org/2005/Atom}entry')):
                for el in item:
                    if el.tag.split('}')[-1] == 'link':
                        links.append(el.get('href') or el.text or '')
        except ET.ParseError:
            links = page.links
        host = urllib.parse.urlsplit(source['url']).hostname
        selected = []
        for link in links:
            try:
                u = canonical(urllib.parse.urljoin(source['url'], link))
            except ValueError:
                continue
            parts = urllib.parse.urlsplit(u)
            if (not parts.query and parts.hostname == host and u != canonical(source['url']) and
                any(parts.path.startswith(prefix) for prefix in source['paths']) and
                not re.search(r'\.(?:jpg|png|pdf|zip)$|/page/|/tag/|/category/', parts.path, re.I) and u not in selected):
                selected.append(u)
        limit = self.config.get('max_articles_per_source', 12)
        urls = list(dict.fromkeys(list(extra_urls) + selected[:limit]))
        # Career pages can themselves contain multiple vacancies.
        if '/jobs' in source['url']:
            urls.insert(0, source['url'])
        if not urls:
            raise ValueError('Discovery returned no article links; not evidence of no developments')
        results, errors = [], []
        for url in urls:
            try:
                results.append(self.article(url))
            except Exception as exc:
                errors.append({'url': url, 'error': safe_error(exc)})
        return results, errors, {'discoveredLinks': len(selected), 'checkedPages': len(results),
                                 'windowLimit': limit, 'boundedCoverage': len(selected) > limit}

def safe_error(exc):
    # Never persist headers, environment variables, credential URLs or response bodies.
    if isinstance(exc, urllib.error.HTTPError):
        return f'HTTP {exc.code}'
    if isinstance(exc, urllib.error.URLError):
        return 'Network/proxy connection failed: ' + re.sub(r'https?://\S+', '[URL]', str(exc.reason))[:200]
    return re.sub(r'https?://\S+', '[URL]', str(exc))[:240]

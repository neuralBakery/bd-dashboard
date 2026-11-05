import argparse
import contextlib
import copy
import fcntl
import json
import shutil
import sys
from pathlib import Path
from .engine import ROOT, atomic_json, initialise, now, candidate, merge, canonical, assess
from .collector import Collector, safe_error
from .dashboard import render

@contextlib.contextmanager
def locked(root):
    (root / 'data').mkdir(exist_ok=True)
    with (root / 'data/.refresh.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another research or recovery process is running')
        yield

def refresh(root=ROOT, collector_type=Collector):
    with locked(root):
        state = initialise(root)
        config = json.loads((root / 'config/sources.json').read_text())
        collector = collector_type(root, config)
        started = now()
        report = {'startedAt': started, 'finishedAt': None, 'sources': [], 'added': 0, 'updated': 0}
        candidates = []
        completed_candidates = []
        for source in config['sources']:
            outcome = {'name': source['name'], 'url': source['url']}
            print('Checking ' + source['name'] + '...', flush=True)
            # Revisit imported evidence only on explicitly configured source hosts.
            from urllib.parse import urlsplit
            extra = sorted({r['url'] for r in state['records'] if urlsplit(r['url']).hostname == urlsplit(source['url']).hostname})
            try:
                articles, errors, coverage = collector.source(source, extra)
                if errors:
                    outcome.update(status='incomplete', errors=errors, coverage=coverage,
                                   error=f'{len(errors)} article checks failed')
                else:
                    outcome.update(status='success', coverage=coverage)
                source_candidates = []
                for article in articles:
                    source_candidates.extend(candidate(article, source, config, state['records']))
                candidates.extend(source_candidates)
                if not errors:
                    completed_candidates.extend(source_candidates)
            except Exception as exc:
                outcome.update(status='failed', error=safe_error(exc))
            report['sources'].append(outcome)
            print(source['name'] + ': ' + outcome['status'], flush=True)
        failed = any(s['status'] != 'success' for s in report['sources'])
        # Atomic promotion: do not silently publish partial research as a valid weekly update.
        if not config['sources'] or failed:
            report['status'] = 'failed' if all(s['status'] == 'failed' for s in report['sources']) else 'incomplete'
            quarantine = root / 'data/staging' / (started.replace(':', '-') + '.json')
            partial, count, changed = merge(state.get('partialRecords', []), completed_candidates)
            state['partialRecords'] = partial
            original_by_key = {(canonical(r['url']), r['company'].casefold()): r for r in state['records']}
            for r in state['partialRecords']:
                r['coverageStatus'] = 'Partial coverage — completed source only'
                previous = original_by_key.get((canonical(r['url']), r['company'].casefold()))
                if previous:
                    r['id'] = previous['id']
                    if not r.get('history'):
                        r['history'] = [copy.deepcopy(previous)]
            report['partialAdded'], report['partialUpdated'] = count, changed
            if count or changed:
                state['lastPartialUpdate'] = now()
            atomic_json(quarantine, {'candidates': candidates, 'audit': collector.audit, 'report': report})
        else:
            combined, _, _ = merge(state['records'], state.get('partialRecords', []))
            state['records'], report['added'], report['updated'] = merge(combined, candidates)
            state['partialRecords'] = []
            for record in state['records']:
                record['assessment'] = assess(record)
                record['priority'] = record['assessment']['priority']
            report['status'] = 'success'
            state['lastSuccessfulRun'] = started
            state['revision'] += 1
        report['finishedAt'] = now()
        backup = root / 'data/backups' / (started.replace(':', '-') + '.json')
        atomic_json(backup, json.loads((root / 'data/state.json').read_text()))
        state['runs'].append(report)
        atomic_json(root / 'data/state.json', state)
        atomic_json(root / 'data/runs' / (started.replace(':', '-') + '.json'), {**report, 'audit': collector.audit})
        render(state, root)
        print(json.dumps(report, indent=2))
        return 0 if report['status'] == 'success' else 2

def recover(root, backup):
    obj = json.loads(Path(backup).read_text())
    # Browser export has a wrapper; backend backups are bare state.
    obj = obj.get('state', obj)
    if obj.get('schema') != 'psw-regional-bd-v2' or not isinstance(obj.get('records'), list) or not isinstance(obj.get('runs'), list):
        raise ValueError('Invalid state backup')
    seen = set()
    for r in obj['records']:
        for key in ('id', 'company', 'headline', 'summary', 'region', 'url'):
            if not isinstance(r.get(key), str) or not r[key]:
                raise ValueError('Invalid record: ' + key)
        canonical(r['url'])
        if r['id'] in seen:
            raise ValueError('Duplicate record ID')
        seen.add(r['id'])
    with locked(root):
        if (root / 'data/state.json').exists():
            atomic_json(root / 'data/backups' / ('pre-recovery-' + now().replace(':', '-') + '.json'), json.loads((root / 'data/state.json').read_text()))
        atomic_json(root / 'data/state.json', obj)
        render(obj, root)
    print('Research recovered; restore browser notes separately using dashboard Restore notes.')

def main():
    p = argparse.ArgumentParser(description='Private local regional business intelligence')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='Import historical records without claiming verification and render HTML')
    sub.add_parser('build', help='Regenerate dashboard from accepted JSON, without research')
    sub.add_parser('refresh', help='Run public-source checks, preserve previous data on incomplete coverage')
    sub.add_parser('status', help='Show last research outcome')
    restore = sub.add_parser('recover', help='Restore a validated research backup after making a recovery backup')
    restore.add_argument('backup')
    args = p.parse_args()
    if args.command == 'refresh':
        return refresh()
    if args.command == 'recover':
        recover(ROOT, args.backup)
        return 0
    with locked(ROOT):
        state = initialise(ROOT)
        if args.command == 'status':
            print(json.dumps({'lastSuccessfulRun': state['lastSuccessfulRun'], 'lastRun': state['runs'][-1] if state['runs'] else None}, indent=2))
        else:
            render(state)
            print('Built dashboard.html. ' + str(len(state['records'])) + ' accepted records; ' + str(len(state.get('partialRecords', []))) + ' separately labelled partial findings.')
    return 0

if __name__ == '__main__':
    sys.exit(main())

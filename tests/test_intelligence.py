import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bdintel.engine import ROOT, assess, candidate, canonical, initialise, merge, parse_date, geography
from bdintel.collector import Page, Collector
from bdintel.__main__ import refresh, recover
from bdintel.dashboard import render

class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for directory in ('assets', 'config'):
            shutil.copytree(ROOT / directory, self.root / directory)
        (self.root / 'data').mkdir()
        shutil.copy(ROOT / 'data/legacy.json', self.root / 'data/legacy.json')
        self.config = json.loads((self.root / 'config/sources.json').read_text())
        self.source = self.config['sources'][0]
        self.article = {'url':'https://www.rdv.vic.gov.au/news/test-article', 'title':'Bentrol expands Bendigo factory',
            'date':'2026-11-03', 'paragraphs':['Bentrol is investing in a new manufacturing factory at Bendigo with 85 new jobs and ongoing production work.'], 'sha256':'abc', 'snapshot':'data/evidence/abc.txt'}
    def tearDown(self):
        self.tmp.cleanup()
    def rows(self):
        return candidate(self.article, self.source, self.config, json.loads((self.root / 'data/legacy.json').read_text()))
    def test_initial_import_not_fresh_or_actionable(self):
        s = initialise(self.root)
        self.assertEqual(len(s['records']), 27)
        self.assertTrue(all(r['verification']=='unverified legacy' and r['priority']=='Monitor' and r['lastChecked'] is None for r in s['records']))
        self.assertTrue(all(r['originalPriority'] in ('High','Medium','Monitor') for r in s['records']))
        self.assertEqual(initialise(self.root), s)
    def test_duplicate_tracking_and_history_preserve_notes(self):
        row = self.rows()[0]
        rows, added, updated = merge([], [row, copy.deepcopy(row)])
        self.assertEqual((len(rows), added, updated), (1,1,0))
        rows[0]['note']='Private user note'
        changed = copy.deepcopy(row); changed['summary'] += ' Source has changed.'
        new, added, updated = merge(rows, [changed])
        self.assertEqual((added,updated), (0,1))
        self.assertEqual(new[0]['note'], 'Private user note')
        self.assertEqual(new[0]['history'][0]['summary'], row['summary'])
        self.assertEqual(len(new[0]['evidence']), 2)
    def test_url_canonicalisation_keeps_event_query(self):
        self.assertEqual(canonical('https://example.com/a/?utm_source=x&event=4#top'), 'https://example.com/a?event=4')
        self.assertNotEqual(canonical('https://example.com/a?event=4'), canonical('https://example.com/a?event=5'))
        with self.assertRaises(ValueError): canonical('javascript:alert(1)')
        with self.assertRaises(ValueError): canonical('https://name:password@example.com/')
    def test_unknown_future_stale_and_risk_never_high(self):
        row = self.rows()[0]
        self.assertEqual(assess(row,'2026-11-05')['priority'], 'High')
        for dt in ('', '2027-11-05', '2025-11-05', 'not a date'):
            row['date']=dt
            self.assertEqual(assess(row,'2026-11-05')['priority'], 'Monitor')
        row['date']='2026-11-03'; row['type']='Closure & restructuring'
        self.assertEqual(assess(row,'2026-11-05')['priority'], 'Monitor')
        self.assertIsNone(parse_date('2026-02-30'))
        self.assertEqual(parse_date('Tue, 03 Nov 2026 09:00:00 +1100'), '2026-11-03')
    def test_no_location_or_no_business_signal_is_not_a_finding(self):
        self.article['paragraphs']=['An unrelated annual public celebration taking place near the local gardens has been announced to residents.']
        self.article['title']='Community day'
        self.assertEqual(self.rows(), [])
        self.assertEqual(geography('Bentrol expands London factory',self.config), [])
    def test_new_structured_employer_and_outside_catchment(self):
        self.article['title']='RiverWorks announces Bendigo factory expansion'
        self.article['paragraphs']=['RiverWorks is investing in a new Bendigo manufacturing factory with 20 new jobs and ongoing production work.']
        self.article['organisations']=['RiverWorks']
        rows=self.rows()
        self.assertEqual(rows[0]['company'],'RiverWorks')
        self.config['outside_catchment_locations']=['Ballarat']
        self.assertEqual(geography('Ballarat factory investment',self.config), [('Outside catchment','Ballarat')])
    def test_company_excerpt_does_not_take_other_company_jobs(self):
        self.article['title']='Bendigo investment announcements'
        self.article['paragraphs']=['Bentrol is investing in manufacturing equipment at the Bendigo site to improve existing production operations.', 'Hazeldenes is expanding its Bendigo food processing factory with 140 new jobs and seasonal recruitment.']
        rows=self.rows()
        bentrol=next(r for r in rows if r['company']=='Bentrol')
        self.assertNotIn('140',bentrol['summary'])
        self.assertNotIn('Hazeldenes',bentrol['summary'])
    def test_parser_dates_scripts_restrictions(self):
        p=Page();p.feed('<title>Title</title><h1>Actual title</h1><script>invented content</script><p>A genuine company source paragraph.</p><meta property="article:published_time" content="2026-11-03T07:00:00+11:00">');p.finish()
        self.assertEqual(p.title,'Actual title');self.assertEqual(p.date,'2026-11-03')
        self.assertNotIn('invented content',p.paragraphs)
        p=Page();p.feed('<script type="application/ld+json">{"isAccessibleForFree":false}</script>');p.finish();self.assertTrue(p.restricted)
    def test_robots_denial_prevents_article_request(self):
        c=Collector(self.root,self.config)
        with patch.object(c,'_request',return_value=(b'User-agent: *\nDisallow: /private', 'utf-8')) as request:
            with self.assertRaisesRegex(ValueError,'Robots disallows'):
                c.fetch('https://example.com/private/article')
            self.assertEqual(request.call_count,1)
    def test_refresh_failure_preserves_valid_dataset_and_backups(self):
        state=initialise(self.root)
        records=copy.deepcopy(state['records'])
        class Fail:
            def __init__(self,*args):self.audit=[]
            def source(self,*args):raise ValueError('Test source unavailable')
        with patch('builtins.print'):
            self.assertEqual(refresh(self.root, Fail),2)
        after=json.loads((self.root/'data/state.json').read_text())
        self.assertEqual(after['records'],records);self.assertIsNone(after['lastSuccessfulRun'])
        self.assertEqual(after['runs'][-1]['status'],'failed')
        backup=next((self.root/'data/backups').glob('*.json'))
        self.assertEqual(json.loads(backup.read_text())['records'], records)
        with patch('builtins.print'):recover(self.root,backup)
        self.assertEqual(json.loads((self.root/'data/state.json').read_text())['records'], records)
    def test_success_then_incomplete_does_not_promote_partial(self):
        article = self.article
        class Good:
            def __init__(self,*args):self.audit=[]
            def source(self,*args):return [article],[],{'checkedPages':1}
        class Partial:
            def __init__(self,*args):self.audit=[]
            def source(self,*args):return [{**article,'title':'New title'}],[{'error':'HTTP 403'}],{'checkedPages':1}
        with patch('builtins.print'):
            self.assertEqual(refresh(self.root, Good),0)
        good=json.loads((self.root/'data/state.json').read_text())
        self.assertEqual(len(good['records']),28)
        self.assertIsNotNone(good['lastSuccessfulRun'])
        with patch('builtins.print'):
            self.assertEqual(refresh(self.root, Partial),2)
        failed=json.loads((self.root/'data/state.json').read_text())
        self.assertEqual(failed['records'],good['records'])
        self.assertEqual(failed['lastSuccessfulRun'],good['lastSuccessfulRun'])
    def test_script_injection_cannot_escape_payload(self):
        s=initialise(self.root);s['records'][0]['summary']='</script><script>alert(1)</script>'
        render(s,self.root)
        doc=(self.root/'dashboard.html').read_text()
        self.assertNotIn('</script><script>alert(1)</script>',doc)
        self.assertIn('\\u003c/script',doc)
    def test_recovery_rejects_corrupt_backup_before_mutation(self):
        original=initialise(self.root)
        bad=copy.deepcopy(original);bad['records'][0]['url']='javascript:alert(1)'
        f=self.root/'bad.json';f.write_text(json.dumps(bad))
        with self.assertRaises(ValueError):recover(self.root,f)
        self.assertEqual(json.loads((self.root/'data/state.json').read_text()),original)

if __name__=='__main__':unittest.main()

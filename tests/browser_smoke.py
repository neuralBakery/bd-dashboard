"""Run with the optional environment-provided Playwright and Chromium. Uses an ephemeral loopback server because managed Chromium blocks file://."""
import json
import tempfile
import functools
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
from bdintel.engine import ROOT

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        context=browser.new_context(accept_downloads=True,viewport={'width':1440,'height':1000})
        page=context.new_page();errors=[];requests=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.on('request',lambda req: requests.append(req.url))
        page.goto(f'http://127.0.0.1:{server.server_port}/dashboard.html');page.wait_for_selector('#results .signal')
        assert int(page.locator('#staleCount').inner_text())>=0
        assert int(page.locator('#highCount').inner_text())>=0
        page.get_by_role('button',name='↗ Market intelligence').click()
        page.locator('#search').fill('Bentrol');assert page.locator('#results .signal').count()==1
        page.locator('#results .signal').click();page.locator('#note').fill('Private smoke test note')
        page.get_by_role('button',name='Save notes',exact=True).click()
        page.reload();page.get_by_role('button',name='↗ Market intelligence').click();page.locator('#search').fill('Bentrol');page.locator('#results .signal').click()
        assert page.locator('#note').input_value()=='Private smoke test note'
        page.get_by_role('button',name='Close',exact=True).click()
        with page.expect_download() as download:page.get_by_role('button',name='Export backup + notes').click()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'backup.json';download.value.save_as(path)
            obj=json.loads(path.read_text());assert obj['notes']['B01']['note']=='Private smoke test note';assert len(obj['state']['records'])>=27
        page.get_by_role('button',name='Reset',exact=True).click()
        page.locator('#from').fill('2099-01-01');assert page.locator('#results .signal').count()==0
        page.get_by_role('button',name='◷ Weekly briefing').click();assert 'REGIONAL VICTORIA' in page.locator('#briefText').inner_text()
        page.get_by_role('button',name='☷ Research runs & sources').click();assert 'failed' in page.locator('#runs').inner_text()
        page.get_by_role('button',name='Manual refresh',exact=True).click();assert page.locator('#refreshHelp').is_visible()
        page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='◫ Overview').click()
        assert page.locator('#heading').is_visible()
        assert not errors,errors
        assert not [r for r in requests if r.startswith(('http://','https://')) and not r.startswith(f'http://127.0.0.1:{server.server_port}/')], requests
        (ROOT/'docs').mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT/'docs/dashboard-mobile.png'),full_page=True)
        print('PASS: loopback rendering (file navigation blocked by managed-browser policy), filters, navigation, source status, notes persistence, backup download, mobile layout, zero external requests, zero JavaScript errors')
        browser.close()
    server.shutdown()
if __name__=='__main__':main()

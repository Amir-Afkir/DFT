"""Browser regression tests. No real form is submitted; geocoder responses are mocked.
Run: pip install playwright==1.57.0 && playwright install chromium webkit
     python tests/address_autocomplete.py
"""
from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse
import json
import traceback
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests/screenshots'
OUT.mkdir(parents=True, exist_ok=True)
API = 'https://data.geopf.fr/geocodage/**'
COMPLETION = {'country': 'StreetAddress', 'kind': 'street', 'street': 'rue de la République', 'zipcode': '45000', 'city': 'Orléans'}
ADDRESS = '12 rue de la République, 45000 Orléans'
FEATURE = {'type': 'Feature', 'properties': {'type': 'housenumber', 'housenumber': '12', 'street': 'rue de la République', 'postcode': '45000', 'city': 'Orléans'}}
SECOND = deepcopy(FEATURE)
SECOND['properties']['housenumber'] = '12 bis'
FEATURES = [
    {'properties': {'type': 'municipality', 'label': 'Orléans'}},
    {'properties': {'type': 'street', 'street': 'rue de la République', 'postcode': '45000', 'city': 'Orléans'}},
    {'properties': {'type': 'housenumber', 'housenumber': '12', 'street': 'rue sans commune'}},
    None, FEATURE, SECOND, FEATURE,
]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{server.server_port}/'
results = []


def open_form(page, mobile):
    page.goto(URL)
    page.locator('.hero [data-diagnostic-open]').click()
    if mobile:
        expect(page.locator('[data-diagnostic-sheet]')).to_be_visible()
    page.locator('input[name=situation][value="Fuite active"]').check()
    return page.locator('#diagnostic-address')


def scenarios(context, mobile, prefix):
    def run(name, action, init=None, response=FEATURES, error_status=None, completion=None):
        page = context.new_page()
        errors, requests = [], []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        page.set_default_timeout(6000)
        def mock(route):
            requests.append(parse_qs(urlparse(route.request.url).query))
            route.fulfill(status=error_status or 200, content_type='application/json', body=json.dumps({'results': completion if completion is not None else [COMPLETION]} if '/completion/' in route.request.url else {'features': response}))
        page.route(API, mock)
        if init:
            page.add_init_script(init)
        try:
            field = open_form(page, mobile)
            action(page, field, requests)
            assert not errors, errors
            results.append({'browser_viewport': prefix, 'test': name, 'passed': True})
            print('PASS', prefix, name, flush=True)
        except Exception:
            failure = traceback.format_exc()
            try:
                page.screenshot(path=str(OUT / f'{prefix}-{name}-failure.png'), full_page=False)
            except Exception:
                pass
            results.append({'browser_viewport': prefix, 'test': name, 'passed': False, 'error': failure})
            print('FAIL', prefix, name, results[-1]['error'], flush=True)
        finally:
            page.close()

    def city(page, field, requests):
        field.fill('Orléans')
        page.locator('[data-next-step]').click()
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
        expect(field).to_have_attribute('aria-invalid', 'true')
        expect(page.locator('#diagnostic-address-error')).to_contain_text('Ajoutez le numéro et la rue')
    run('city-rejected', city)

    def keyboard(page, field, requests):
        field.fill('12 rue de la République Orléans')
        expect(page.get_by_role('option')).to_have_count(2)
        assert requests[-1]['type'] == ['housenumber']
        assert requests[-1]['index'] == ['address']
        expect(field).to_have_attribute('aria-activedescendant', 'diagnostic-address-option-0')
        field.press('Enter')
        expect(field).to_have_value(ADDRESS)
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
        field.fill('12 rue de la République Orléans')
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('ArrowDown')
        expect(page.get_by_role('option').nth(1)).to_have_attribute('aria-selected', 'true')
        field.press('ArrowUp')
        field.press('Enter')
        expect(field).to_have_value(ADDRESS)
        expect(field).to_have_attribute('aria-invalid', 'false')
        expect(field).to_have_attribute('aria-expanded', 'false')
        assert field.evaluate('(el) => el.validity.valid')
        page.locator('[data-next-step]').click()
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '2')
        page.locator('[data-prev-step]').click()
        expect(field).to_have_value(ADDRESS)
        field.fill('Orléans')
        page.locator('[data-next-step]').click()
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
        # Restoring the same text by typing is NOT a new selection.
        field.fill(ADDRESS)
        page.locator('[data-next-step]').click()
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
    run('keyboard-selection-and-edit', keyboard)

    def pointer(page, field, requests):
        field.fill('12 rue de la République Orléans')
        expect(page.get_by_role('option')).to_have_count(2)
        first = page.get_by_role('option').first
        first.scroll_into_view_if_needed()
        box = first.bounding_box()
        assert box and box['height'] >= 44
        assert box['x'] >= 0 and box['x'] + box['width'] <= page.viewport_size['width'] + 1
        page.screenshot(path=str(OUT / f'{prefix}-suggestions.png'), full_page=False)
        if mobile:
            # A touch press / scroll start must not select anything.
            first.dispatch_event('pointerdown', {'pointerType': 'touch'})
            expect(field).not_to_have_value(ADDRESS)
            first.tap()
        else:
            first.click()
        expect(field).to_have_value(ADDRESS)
        page.locator('[data-next-step]').click()
        for name, value in [('first_name', 'Test'), ('last_name', 'DFT'), ('phone', '0600000000'), ('email', 'test@example.invalid')]:
            page.locator(f'[name={name}]').fill(value)
        page.locator('[name=privacy]').check()
        page.evaluate('''() => document.querySelector('[data-diagnostic-form]').addEventListener('submit', event => {
          window.__submission = { blocked: event.defaultPrevented, data: Object.fromEntries(new FormData(event.target)) };
          event.preventDefault();
        })''')
        page.locator('[data-diagnostic-form] button[type=submit]').click()
        submitted = page.evaluate('window.__submission')
        assert submitted['blocked'] is False, submitted
        assert submitted['data']['address'] == ADDRESS
        assert submitted['data']['form-name'] == 'diagnostic-dft'
        # Final submission must recheck an address changed while step 1 is hidden.
        field.evaluate('(el) => el.value = "Olivet"')
        page.locator('[data-diagnostic-form] button[type=submit]').click()
        assert page.evaluate('window.__submission.blocked') is True
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
    run('pointer-and-final-payload', pointer)

    def unavailable(page, field, requests):
        field.fill('12 rue de la République Orléans')
        retry = page.locator('#diagnostic-address-retry')
        expect(retry).to_be_visible()
        expect(page.locator('#diagnostic-address-assistance a')).to_have_attribute('href', 'tel:+33688046639')
        assert not field.evaluate('(el) => el.validity.valid')
        page.unroute(API)
        page.route(API, lambda r: r.fulfill(content_type='application/json', body=json.dumps({'features': [FEATURE]})))
        retry.tap() if mobile else retry.click()
        expect(page.get_by_role('option')).to_have_count(1)
        page.get_by_role('option').click()
        expect(field).to_have_value(ADDRESS)
    run('outage-and-retry', unavailable, error_status=503)

    def empty(page, field, requests):
        field.fill('999 rue introuvable Orléans')
        expect(page.locator('#diagnostic-address-status')).to_contain_text('Aucune adresse complète')
        expect(page.get_by_role('option')).to_have_count(0)
        expect(page.locator('#diagnostic-address-assistance')).to_be_visible()
        page.locator('[data-next-step]').click()
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
    run('no-result', empty, response=[])

    pending_fetch = '''(() => {
      const original = window.fetch;
      window.__pending = [];
      window.fetch = (url, options) => String(url).startsWith('https://data.geopf.fr/geocodage/')
        ? new Promise(resolve => window.__pending.push({url, resolve}))
        : original(url, options);
    })();'''

    def stale(page, field, requests):
        field.fill('12 rue ancienne Orléans')
        page.wait_for_function('window.__pending.length === 1')
        field.fill('13 rue nouvelle Orléans')
        page.evaluate('(f) => window.__pending[0].resolve({ok: true, json: () => Promise.resolve({features: [f]})})', FEATURE)
        expect(page.get_by_role('option')).to_have_count(0)
        page.wait_for_function('window.__pending.length === 2')
        field.press('Escape')
        page.evaluate('(f) => window.__pending[1].resolve({ok: true, json: () => Promise.resolve({features: [f]})})', FEATURE)
        expect(page.get_by_role('option')).to_have_count(0)
        expect(field).to_have_attribute('aria-expanded', 'false')
        if mobile:
            expect(page.locator('[data-diagnostic-sheet]')).to_be_visible()
    run('stale-response-and-escape', stale, init=pending_fetch)

    def timeout(page, field, requests):
        field.fill('12 rue Orléans')
        expect(page.locator('#diagnostic-address-status')).to_contain_text('trop de temps')
        expect(page.locator('#diagnostic-address-retry')).to_be_visible()
        expect(field).to_have_attribute('aria-busy', 'false')
    run('timeout', timeout, init=pending_fetch + '\nconst normalTimer = window.setTimeout; window.setTimeout = (fn, ms, ...args) => normalTimer(fn, ms === 8000 ? 50 : ms, ...args);')

    def escape_tab_resize(page, field, requests):
        field.fill('12 rue République Orléans')
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('Escape')
        expect(page.get_by_role('option')).to_have_count(0)
        if mobile:
            expect(page.locator('[data-diagnostic-sheet]')).to_be_visible()
        field.press('ArrowDown')
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('Tab')
        expect(page.get_by_role('option')).to_have_count(0)
        field.focus()
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('Enter')
        page.set_viewport_size({'width': 1440 if mobile else 390, 'height': 900 if mobile else 844})
        page.wait_for_timeout(300)
        if not mobile:
            page.locator('.hero [data-diagnostic-open]').click()
        expect(field).to_have_value(ADDRESS)
        page.locator('[data-next-step]').click()
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '2')
    run('escape-tab-responsive', escape_tab_resize)

    malicious = deepcopy(FEATURE)
    malicious['properties']['street'] = '<img src=x onerror="window.__xss=true">'
    def xss(page, field, requests):
        field.fill('12 rue Orléans')
        expect(page.get_by_role('option')).to_have_count(1)
        assert page.locator('#diagnostic-address-suggestions img').count() == 0
        assert page.evaluate('window.__xss || false') is False
    run('api-text-not-html', xss, response=[malicious])

    def street_first(page, field, requests):
        field.fill('rue de la République')
        expect(page.get_by_role('option')).to_have_count(1)
        assert requests[-1]['type'] == ['StreetAddress']
        assert requests[-1]['lonlat'] == ['1.904,47.903']
        assert not field.evaluate('(e) => e.validity.valid')
        field.press('Enter')
        expect(field).to_have_value(' rue de la République, 45000 Orléans')
        assert field.evaluate('(e) => e.selectionStart') == 0
        assert not field.evaluate('(e) => e.validity.valid')
        expect(page.locator('#diagnostic-address-status')).to_contain_text('Ajoutez le numéro au début')
        field.press_sequentially('12')
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('Enter')
        expect(field).to_have_value(ADDRESS)
        assert field.evaluate('(e) => e.validity.valid')
    run('street-first-number-second', street_first)

    def street_numbers(page, field, requests):
        for query in ['rue du 8 Mai 1945 Orléans', '45000 Orléans']:
            field.fill(query)
            expect(page.get_by_role('option')).to_have_count(1)
            assert requests[-1]['type'] == ['StreetAddress']
            assert not field.evaluate('(e) => e.validity.valid')
    run('street-date-and-postcode-not-house-number', street_numbers)

    foreign = deepcopy(FEATURE)
    foreign['properties'].update(city='Lille', postcode='59000')
    def geography(page, field, requests):
        for query, expected in [('12 rue République', ADDRESS), ('12 rue République 59000', '12 rue de la République, 59000 Lille'), ('12 rue République Lille', '12 rue de la République, 59000 Lille')]:
            field.fill(query)
            expect(page.get_by_role('option')).to_have_count(2)
            assert requests[-1]['q'] == [query]
            assert requests[-1]['lon'] == ['1.904'] and requests[-1]['lat'] == ['47.903']
            assert 'depcode' not in requests[-1] and 'citycode' not in requests[-1]
            field.press('Enter')
            expect(field).to_have_value(expected)
    run('loiret-priority-with-explicit-city-override', geography, response=[foreign, FEATURE])

    def wrong_number(page, field, requests):
        field.fill('999 rue République Orléans')
        expect(page.locator('#diagnostic-address-status')).to_contain_text('Aucune adresse complète')
        expect(page.get_by_role('option')).to_have_count(0)
        field.press('Enter')
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
        assert not field.evaluate('(e) => e.validity.valid')
    run('fuzzy-wrong-house-number-rejected', wrong_number)

    def suffix(page, field, requests):
        field.fill('12bis rue République Orléans')
        expect(page.get_by_role('option')).to_have_count(1)
        field.press('Enter')
        expect(field).to_have_value('12 bis rue de la République, 45000 Orléans')
    run('bis-suffix-preserved', suffix)

    def autofill(page, field, requests):
        assert field.get_attribute('autocomplete') == 'street-address'
        field.evaluate("(e) => {e.value='12 rue République Orléans'; e.dispatchEvent(new Event('change', {bubbles: true}));}")
        expect(page.get_by_role('option')).to_have_count(2)
        assert not field.evaluate('(e) => e.validity.valid')
        page.get_by_role('option').first.click()
        expect(field).to_have_value(ADDRESS)
    run('native-autofill-still-requires-selection', autofill)

    def no_blur_selection(page, field, requests):
        field.fill('12 rue République')
        expect(page.get_by_role('option')).to_have_count(2)
        expect(page.get_by_role('option').first).to_have_attribute('aria-selected', 'true')
        field.press('Tab')
        expect(page.get_by_role('option')).to_have_count(0)
        assert not field.evaluate('(e) => e.validity.valid')
        expect(field).not_to_have_value(ADDRESS)
    run('highlight-is-not-validation-on-blur', no_blur_selection)

    def cache_reset(page, field, requests):
        field.fill('12 rue République')
        expect(page.get_by_role('option')).to_have_count(2)
        first_count=len(requests)
        field.press('Escape')
        field.press('ArrowDown')
        expect(page.get_by_role('option')).to_have_count(2)
        assert len(requests)==first_count
        field.press('Enter')
        expect(field).to_have_value(ADDRESS)
        page.wait_for_timeout(350)
        expect(page.get_by_role('option')).to_have_count(0)
        assert len(requests)==first_count
        page.locator('[data-diagnostic-form]').evaluate('(e) => e.reset()')
        expect(field).to_have_value('')
        field.fill('12 rue République')
        expect(page.get_by_role('option')).to_have_count(2)
        assert len(requests)==first_count+1
    run('in-memory-cache-and-reset', cache_reset)

    def composing(page, field, requests):
        field.focus()
        field.dispatch_event('compositionstart')
        field.fill('12 rue République')
        page.wait_for_timeout(350)
        assert requests==[]
        field.dispatch_event('compositionend')
        expect(page.get_by_role('option')).to_have_count(2)
    run('composition-no-premature-requests', composing)

    def edit_feedback(page, field, requests):
        field.fill('Orléans')
        page.locator('[data-next-step]').click()
        expect(field).to_have_attribute('aria-invalid', 'true')
        field.fill('12 rue République')
        expect(field).to_have_attribute('aria-invalid', 'false')
        assert not field.evaluate('(e) => e.validity.valid')
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('Enter')
        expect(field).to_have_value(ADDRESS)
    run('correction-without-premature-red-error', edit_feedback)

    many=[]
    for i in range(10):
        item=deepcopy(FEATURE)
        item['properties']['street']='rue Exemple '+str(i)
        many.append(item)
    def seven(page, field, requests):
        field.fill('12 rue Exemple')
        expect(page.get_by_role('option')).to_have_count(7)
        field.scroll_into_view_if_needed()
        before=field.bounding_box()['y']
        for _ in range(6):
            field.press('ArrowDown')
        assert page.locator('#diagnostic-address-suggestions').evaluate('(e) => e.scrollTop')>0
        assert abs(field.bounding_box()['y']-before)<2
        field.press('Enter')
        expect(field).to_have_value('12 rue Exemple 6, 45000 Orléans')
    run('seven-results-keyboard-without-page-jump', seven, response=many)

    def no_touch_select(page, field, requests):
        field.fill('12 rue Exemple')
        expect(page.get_by_role('option')).to_have_count(7)
        first=page.get_by_role('option').first
        first.dispatch_event('pointerdown', {'pointerType':'touch'})
        field.evaluate('(e) => e.blur()')
        page.locator('#diagnostic-address-suggestions').evaluate('(e) => e.scrollTop = e.scrollHeight')
        first.dispatch_event('pointercancel', {'pointerType':'touch'})
        page.wait_for_timeout(250)
        expect(page.get_by_role('option')).to_have_count(7)
        assert not field.evaluate('(e) => e.validity.valid')
        last=page.get_by_role('option').last
        last.tap() if mobile else last.click()
        expect(field).to_have_value('12 rue Exemple 6, 45000 Orléans')
    run('touch-scroll-not-a-selection', no_touch_select, response=many)

    def malformed(page, field, requests):
        page.unroute(API)
        page.route(API, lambda r: r.fulfill(content_type='application/json', body='{"features": null}'))
        field.fill('12 rue Orléans')
        expect(page.locator('#diagnostic-address-retry')).to_be_visible()
        assert not field.evaluate('(e) => e.validity.valid')
    run('malformed-response-safe', malformed)

    def no_city(page, field, requests):
        field.fill('Orléans')
        expect(page.locator('#diagnostic-address-status')).to_contain_text('Ajoutez le nom de la rue')
        expect(page.get_by_role('option')).to_have_count(0)
        assert not field.evaluate('(e) => e.validity.valid')
    run('completion-city-only-never-validates', no_city, completion=[{'country':'StreetAddress','kind':'municipality','city':'Orléans','zipcode':'45000'}])



try:
    with sync_playwright() as p:
        for name in ['chromium', 'webkit']:
            browser = getattr(p, name).launch()
            for width, height in [(1440, 900), (390, 844), (320, 640)]:
                mobile = width < 720
                context = browser.new_context(viewport={'width': width, 'height': height}, has_touch=mobile, is_mobile=mobile, reduced_motion='reduce')
                scenarios(context, mobile, f'{name}-{width}x{height}')
                context.close()
            browser.close()
finally:
    server.shutdown()
    (ROOT / 'tests/address-results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))

failed = [r for r in results if not r['passed']]
print(f'{len(results) - len(failed)}/{len(results)} tests passed')
assert not failed, f'{len(failed)} browser tests failed'

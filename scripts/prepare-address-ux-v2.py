"""One-shot integration on the isolated work branch, not part of the deployed site."""
from pathlib import Path
p = Path('index.html')
s = p.read_text()
changes = [
    ('name="address" type="text" autocomplete="off"', 'name="address" type="text" autocomplete="street-address" enterkeyhint="done"'),
    ('aria-label="Adresses complètes proposées"', 'aria-label="Rues et adresses proposées"'),
    ('Saisissez le numéro et la rue, puis sélectionnez l’adresse avec son code postal et sa commune.', 'Commencez par le numéro ou le nom de la rue, puis sélectionnez l’adresse complète. Orléans et le Loiret sont privilégiés.'),
    ('<script src="assets/js/address-autocomplete.js"></script>', '<script src="assets/js/address-autocomplete.js?v=2"></script>'),
    ('} else if (event.target.matches("input, textarea")) {\n            validateInput(event.target, true);', '} else if (event.target !== addressInput && event.target.matches("input, textarea")) {\n            validateInput(event.target, true);'),
    ('diagnosticMobile.addEventListener("change", function () {\n          closeDiagnosticSheet();', 'diagnosticMobile.addEventListener("change", function () {\n          closeAddressSuggestions();\n          closeDiagnosticSheet();'),
]
for old, new in changes:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
p.write_text(s)
p = Path('tests/address_autocomplete.py')
s = p.read_text()
s = s.replace("API = 'https://data.geopf.fr/geocodage/search?*'", "API = 'https://data.geopf.fr/geocodage/**'\nCOMPLETION = {'country': 'StreetAddress', 'kind': 'street', 'street': 'rue de la République', 'zipcode': '45000', 'city': 'Orléans'}")
s = s.replace('def run(name, action, init=None, response=FEATURES, error_status=None):', 'def run(name, action, init=None, response=FEATURES, error_status=None, completion=None):')
s = s.replace("body=json.dumps({'features': response}))", "body=json.dumps({'results': completion if completion is not None else [COMPLETION]} if '/completion/' in route.request.url else {'features': response}))")
s = s.replace("to_contain_text('Sélectionnez une adresse complète')", "to_contain_text('Ajoutez le numéro et la rue')")
s = s.replace('        assert requests == [], requests\n', '')
s = s.replace('''        field.press('Enter')
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
        field.press('ArrowDown')
        expect(field).to_have_attribute('aria-activedescendant', 'diagnostic-address-option-0')
        field.press('ArrowDown')''', '''        expect(field).to_have_attribute('aria-activedescendant', 'diagnostic-address-option-0')
        field.press('Enter')
        expect(field).to_have_value(ADDRESS)
        expect(page.locator('[data-diagnostic-form]')).to_have_attribute('data-step', '1')
        field.fill('12 rue de la République Orléans')
        expect(page.get_by_role('option')).to_have_count(2)
        field.press('ArrowDown')''')
s = s.replace('        retry.click()\n', '        retry.tap() if mobile else retry.click()\n')
s = s.replace("        field.press('ArrowDown')\n        field.press('Enter')\n        page.set_viewport_size", "        field.press('Enter')\n        page.set_viewport_size")
s = s.replace('''        except Exception:
            page.screenshot(path=str(OUT / f'{prefix}-{name}-failure.png'), full_page=False)
            results.append({'browser_viewport': prefix, 'test': name, 'passed': False, 'error': traceback.format_exc()})''', '''        except Exception:
            failure = traceback.format_exc()
            try:
                page.screenshot(path=str(OUT / f'{prefix}-{name}-failure.png'), full_page=False)
            except Exception:
                pass
            results.append({'browser_viewport': prefix, 'test': name, 'passed': False, 'error': failure})''')
marker = "    run('api-text-not-html', xss, response=[malicious])"
assert s.count(marker) == 1
extra = '''

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
        page.locator('#diagnostic-address-suggestions').evaluate('(e) => e.scrollTop = e.scrollHeight')
        first.dispatch_event('pointercancel', {'pointerType':'touch'})
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
'''
s = s.replace(marker, marker + extra)
p.write_text(s)

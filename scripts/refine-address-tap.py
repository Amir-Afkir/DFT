from pathlib import Path

def replace(path, old, new):
    p = Path(path)
    content = p.read_text()
    if old in content:
        assert content.count(old) == 1, old
        p.write_text(content.replace(old, new))
    else:
        assert new in content, old

replace('assets/js/address-autocomplete.js', 'let pointerInField = false, suppressFocus = false, blurTimer = null;', 'let pointerInField = false, listInteraction = false, suppressFocus = false, blurTimer = null;')
replace('assets/js/address-autocomplete.js', '    function close() {\n      if (!list.hidden', '    function close() {\n      listInteraction = false;\n      if (!list.hidden')
replace('assets/js/address-autocomplete.js', 'if (!pointerInField && !(field && field.contains(document.activeElement)))', 'if (!listInteraction && !pointerInField && !(field && field.contains(document.activeElement)))')
replace('assets/js/address-autocomplete.js', '      pointerInField = Boolean(field && field.contains(event.target));', '      listInteraction = list.contains(event.target);\n      pointerInField = Boolean(field && field.contains(event.target));')
replace('tests/address_autocomplete.py', "        first.dispatch_event('pointerdown', {'pointerType':'touch'})\n        page.locator", "        first.dispatch_event('pointerdown', {'pointerType':'touch'})\n        field.evaluate('(e) => e.blur()')\n        page.locator")
replace('tests/address_autocomplete.py', "        first.dispatch_event('pointercancel', {'pointerType':'touch'})\n        assert not", "        first.dispatch_event('pointercancel', {'pointerType':'touch'})\n        page.wait_for_timeout(250)\n        expect(page.get_by_role('option')).to_have_count(7)\n        assert not")
replace('index.html', 'Commencez par le numéro ou le nom de la rue, puis sélectionnez l’adresse complète. Orléans et le Loiret sont privilégiés.', 'Commencez par le numéro ou la rue. Orléans et le Loiret sont privilégiés.')

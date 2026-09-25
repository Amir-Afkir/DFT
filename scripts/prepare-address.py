"""One-shot, checksum-guarded migration; never run against an unreviewed page."""
from pathlib import Path
import hashlib

path = Path('index.html')
raw = path.read_bytes()
assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == '898b7484ce264ce1f604628306bd43b6c9aff6f9', 'Unexpected source page; review current main first'
text = raw.decode('utf-8')

def replace(old, new):
    global text
    assert text.count(old) == 1, f'Ambiguous or missing anchor: {old[:90]}'
    text = text.replace(old, new, 1)

def section(start, end, new):
    global text
    assert text.count(start) == 1 and text.count(end) == 1
    i = text.index(start)
    j = text.index(end, i)
    text = text[:i] + new + text[j:]

replace('<label for="diagnostic-address">Adresse complète</label>', '<label for="diagnostic-address">Adresse complète <span class="field-help">(obligatoire)</span></label>')
replace('autocomplete="address-line1" placeholder="Ex. Orléans, Olivet, Saran..."', 'autocomplete="off" spellcheck="false" maxlength="240" placeholder="Ex. 12 rue de la République, 45000 Orléans"')
replace('aria-describedby="diagnostic-address-help diagnostic-address-error"', 'aria-describedby="diagnostic-address-help diagnostic-address-error" aria-busy="false"')
replace('role="listbox" data-address-suggestions hidden', 'role="listbox" aria-label="Adresses complètes proposées" data-address-suggestions hidden')
replace('DFT intervient autour d’Orléans et dans le Loiret.</span>', 'Saisissez le numéro et la rue, puis sélectionnez l’adresse avec son code postal et sa commune.</span>')
replace('                    <span class="diagnostic-error" id="diagnostic-address-error" data-error-for="address" aria-live="polite"></span>', '''                    <span class="field-help address-status" id="diagnostic-address-status" role="status" aria-live="polite" aria-atomic="true"></span>
                    <span class="diagnostic-error" id="diagnostic-address-error" data-error-for="address" aria-live="polite"></span>
                    <button class="address-retry" id="diagnostic-address-retry" type="button" hidden>Réessayer la recherche</button>
                    <span class="field-help address-assistance" id="diagnostic-address-assistance" hidden>Adresse introuvable ou sans numéro ? <a href="tel:+33688046639">Appelez DFT au 06 88 04 66 39</a> pour préciser le lieu d’intervention.</span>''')
replace('    .address-combobox {\n      position: relative;\n    }', '    .address-combobox {\n      position: relative;\n      min-width: 0;\n    }')
replace('''    .address-suggestions {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      left: 0;''', '''    .address-suggestions {
      /* Stay in the scrollable form, above the mobile action footer. */
      position: relative;
      margin-top: 8px;
      min-width: 0;''')
replace('      max-height: min(260px, 42vh);', '      max-height: min(260px, 36vh);\n      max-height: min(260px, 36dvh);')
replace('''    .address-suggestion {
      display: grid;
      gap: 2px;''', '''    .address-suggestion {
      display: grid;
      gap: 2px;
      min-height: 48px;
      min-width: 0;
      overflow-wrap: anywhere;
      touch-action: pan-y;''')
replace('    .field.is-valid input,', '''    .address-status:empty {
      display: none;
    }

    .address-retry {
      justify-self: start;
      min-height: 44px;
      padding: 8px 12px;
      border: 1px solid var(--blue-roof);
      border-radius: 6px;
      background: var(--white);
      color: var(--blue-night);
      font: inherit;
      cursor: pointer;
    }

    .address-assistance a {
      display: inline-flex;
      min-height: 44px;
      align-items: center;
      text-decoration: underline;
      text-underline-offset: 3px;
    }

    .address-retry[hidden],
    .address-assistance[hidden] {
      display: none;
    }

    .field.is-valid input,''')
replace('  <script>\n    (function () {', '  <script src="assets/js/address-autocomplete.js"></script>\n  <script>\n    (function () {')
section('      const localAddressSuggestions = [', '      function setMenu(open) {', '''      const addressController = window.DFTAddressAutocomplete && window.DFTAddressAutocomplete.create({
        input: addressInput,
        box: addressCombobox,
        list: addressSuggestions,
        status: document.querySelector("#diagnostic-address-status"),
        error: document.querySelector("#diagnostic-address-error"),
        assistance: document.querySelector("#diagnostic-address-assistance"),
        retry: document.querySelector("#diagnostic-address-retry")
      });
      let diagnosticLastFocus = null;

''')
section('      function escapeHtml(value) {', '      function setError(name, message) {', '''      function closeAddressSuggestions() {
        if (addressController) addressController.close();
      }

''')
replace('''      function validateInput(input, showMessage) {
''', '''      function validateInput(input, showMessage) {
        if (input && input === addressInput) {
          if (addressController) return addressController.validate(showMessage);
          setError("address", "La recherche d’adresses n’a pas pu se charger. Rechargez la page ou appelez DFT au 06 88 04 66 39.");
          return false;
        }
''')
section('      if (addressInput) {\n        addressInput.addEventListener("input", queueAddressSearch);', '      if (diagnosticForm) {\n        diagnosticForm.querySelector("[data-next-step]")', '')
replace('''          if (!validateStepTwo()) event.preventDefault();''', '''          // Recheck step 1 at final submission, not only on "Continuer".
          if (!validateStepOne()) {
            event.preventDefault();
            setDiagnosticStep(1, false);
            validateStepOne();
            return;
          }
          if (!validateStepTwo()) event.preventDefault();''')
assert 'api-adresse.data.gouv.fr' not in text
assert 'getLocalAddressMatches' not in text
path.write_text(text, encoding='utf-8')
print('Updated index.html with targeted complete-address integration')

/* DFT: only an explicitly selected, complete BAN address can validate the form.
 * IGN completion discovers streets; geocoding autocomplete verifies numbered addresses.
 * Orléans is a fixed search preference, NOT the visitor's GPS position or a territory ban.
 * Positive results are cached only in memory (2 minutes / 30 queries), never in storage.
 */
(function (global) {
  "use strict";
  const ORLEANS = { lon: "1.904", lat: "47.903" };
  const MAX_RESULTS = 7;
  const NUMBER = /^(\d{1,4}(?:\s*[-/]\s*\d{1,4})?(?:\s*(?:bis|ter|quater|[a-z]\b))?)(?=\s|,|$)/i;
  function text(value) { return typeof value === "string" ? value.trim() : ""; }
  function normalize(value) { return String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, " ").trim(); }
  function numberOf(value) { const match = text(value).match(NUMBER); return match ? normalize(match[1]).replace(/\s+/g, "") : ""; }
  function matchesNumber(number, wanted) {
    return number === wanted || (/^\d+$/.test(wanted) && number.replace(/(?:bis|ter|quater|[a-z])$/, "") === wanted);
  }
  function completeAddress(feature, wanted) {
    const p = feature && feature.properties;
    if (!p || p.type !== "housenumber") return null;
    const number = text(p.housenumber), street = text(p.street), postcode = text(p.postcode), city = text(p.city);
    if (!numberOf(number) || !matchesNumber(numberOf(number), wanted) || !street || !/^\d{5}$/.test(postcode) || !city) return null;
    return { kind: "address", number: numberOf(number), street: number + " " + street, city: city, postcode: postcode,
      locality: postcode + " " + city, label: number + " " + street + ", " + postcode + " " + city };
  }
  function streetSuggestion(item) {
    if (!item || item.kind !== "street" || item.country !== "StreetAddress") return null;
    const street = text(item.street), postcode = text(item.zipcode), city = text(item.city);
    if (!street || !/^\d{5}$/.test(postcode) || !city) return null;
    return { kind: "street", street: street, city: city, postcode: postcode,
      locality: postcode + " " + city, label: street + ", " + postcode + " " + city };
  }
  function prioritize(items, query, wanted) {
    const postal = query.match(/\b\d{5}\b/);
    const words = " " + normalize(query).replace(/[,;]+/g, " ") + " ";
    const namedCities = items.filter(function (item) { return words.includes(" " + normalize(item.city) + " "); });
    const seen = new Set();
    return items.filter(function (item) {
      const key = normalize(item.label);
      if (seen.has(key)) return false;
      seen.add(key); return true;
    }).map(function (item, index) {
      // Explicit postcode/city always takes precedence over the local preference.
      const location = postal ? (item.postcode === postal[0] ? 0 : 1)
        : namedCities.length ? (namedCities.includes(item) ? 0 : 1)
        : (item.postcode.startsWith("45") ? 0 : 1);
      return { item: item, index: index, rank: location * 2 + (wanted && item.number !== wanted ? 1 : 0) };
    }).sort(function (a, b) { return a.rank - b.rank || a.index - b.index; })
      .slice(0, MAX_RESULTS).map(function (entry) { return entry.item; });
  }

  function create(options) {
    const input = options.input, list = options.list, box = options.box;
    const status = options.status, error = options.error, assistance = options.assistance, retry = options.retry;
    if (!input || !list || !box) return null;
    const field = input.closest("[data-field]");
    const cache = new Map();
    let selected = null, results = [], active = -1, touched = false;
    let debounce = null, request = null, sequence = 0, composing = false;
    let pointerInField = false, listInteraction = false, suppressFocus = false, blurTimer = null;
    let lastValue = input.value;
    function announce(message) { if (status) status.textContent = message; }
    function cancelPending() {
      sequence += 1;
      window.clearTimeout(debounce); debounce = null;
      if (request) {
        window.clearTimeout(request.timeout); request.controller.abort(); request = null;
      }
      input.setAttribute("aria-busy", "false");
    }
    function hideList() {
      results = []; active = -1;
      list.replaceChildren(); list.hidden = true;
      input.setAttribute("aria-expanded", "false"); input.removeAttribute("aria-activedescendant");
      box.classList.remove("is-open");
    }
    function close() {
      listInteraction = false;
      if (!list.hidden || request || debounce) announce("");
      cancelPending(); hideList();
    }
    function isValid() {
      if (selected && input.value !== selected.label) selected = null;
      return Boolean(selected);
    }
    function validate(showMessage) {
      if (showMessage) touched = true;
      const valid = isValid();
      const message = valid ? "" : !input.value.trim()
        ? "Renseignez puis sélectionnez l’adresse complète du lieu d’intervention."
        : !numberOf(input.value)
          ? "Ajoutez le numéro et la rue, puis sélectionnez l’adresse complète proposée."
          : "Sélectionnez votre adresse complète dans les suggestions pour confirmer le lieu d’intervention.";
      input.setCustomValidity(message);
      input.setAttribute("aria-invalid", String(touched && !valid));
      if (field) {
        field.classList.toggle("is-valid", valid);
        field.classList.toggle("is-invalid", touched && !valid);
      }
      if (error) error.textContent = touched ? message : "";
      return valid;
    }
    function focusInput() {
      suppressFocus = true; input.focus({ preventScroll: true }); suppressFocus = false;
    }
    function select(index) {
      const item = results[index];
      if (!item) return;
      close(); window.clearTimeout(blurTimer);
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      if (item.kind === "street") {
        // Leave a space and the caret at the beginning for typing the house number.
        selected = null; touched = false; input.value = " " + item.label;
        lastValue = input.value; validate(false); focusInput(); input.setSelectionRange(0, 0);
        announce("Rue choisie. Ajoutez le numéro au début, puis sélectionnez l’adresse complète.");
      } else {
        selected = item; input.value = item.label; lastValue = input.value;
        validate(true); focusInput(); announce("Adresse sélectionnée : " + item.label);
      }
    }
    function setActive(index, scroll) {
      active = index;
      Array.from(list.children).forEach(function (option, i) {
        option.setAttribute("aria-selected", String(i === active));
        option.classList.toggle("is-active", i === active);
        if (i === active) {
          input.setAttribute("aria-activedescendant", option.id);
          if (scroll) {
            // Scroll the results, not the page or the mobile sheet containing the input.
            const item = option.getBoundingClientRect(), bounds = list.getBoundingClientRect();
            if (item.bottom > bounds.bottom - 7) list.scrollTop += item.bottom - bounds.bottom + 7;
            else if (item.top < bounds.top + 7) list.scrollTop -= bounds.top + 7 - item.top;
          }
        }
      });
    }
    function showAssistance(message, canRetry) {
      hideList(); announce(message);
      if (assistance) assistance.hidden = false;
      if (retry) retry.hidden = !canRetry;
    }
    function render(items, numbered) {
      hideList(); results = items;
      if (!results.length) {
        showAssistance(numbered
          ? "Aucune adresse complète trouvée pour ce numéro. Vérifiez le numéro, la rue et la commune ou le code postal."
          : "Ajoutez le nom de la rue et votre commune. Le numéro sera nécessaire pour confirmer l’adresse.", false);
        return;
      }
      results.forEach(function (item, index) {
        const option = document.createElement("div");
        option.className = "address-suggestion"; option.id = input.id + "-option-" + index;
        option.setAttribute("role", "option"); option.setAttribute("aria-selected", "false");
        const main = document.createElement("strong"), detail = document.createElement("small");
        main.textContent = item.street;
        detail.textContent = item.locality + (item.kind === "street" ? " · Ajouter le numéro" : "");
        option.append(main, detail);
        option.addEventListener("mousedown", function (event) { event.preventDefault(); });
        option.addEventListener("click", function () { select(index); });
        list.appendChild(option);
      });
      list.hidden = false; list.scrollTop = 0;
      input.setAttribute("aria-expanded", "true"); box.classList.add("is-open");
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      setActive(0, false); // Enter confirms; merely opening or leaving the list never does.
      announce(numbered ? "Sélectionnez votre adresse. Entrée confirme la suggestion surlignée."
        : "Sélectionnez votre rue, puis ajoutez le numéro. Une rue seule ne suffit pas.");
    }
    function cacheResult(key, items) {
      if (!items.length) return;
      cache.delete(key); cache.set(key, { items: items, until: Date.now() + 120000 });
      if (cache.size > 30) cache.delete(cache.keys().next().value);
    }
    function search(query, version) {
      debounce = null;
      if (version !== sequence || query !== input.value.trim()) return;
      const wanted = numberOf(query), numbered = Boolean(wanted);
      const key = (numbered ? "address:" : "street:") + normalize(query);
      const saved = cache.get(key);
      if (saved && saved.until > Date.now()) { render(saved.items, numbered); return; }
      cache.delete(key);
      const controller = new AbortController(), task = { controller: controller, timeout: null };
      request = task; input.setAttribute("aria-busy", "true"); announce("Recherche d’adresses…");
      function current() { return sequence === version && request === task && input.value.trim() === query; }
      task.timeout = window.setTimeout(function () {
        if (!current()) return;
        cancelPending(); showAssistance("La recherche prend trop de temps. Réessayez ou contactez DFT par téléphone.", true);
      }, 8000);
      // Completion includes unnumbered streets; the numbered endpoint has explicit housenumber fields.
      const params = new URLSearchParams(numbered
        ? { q: query, index: "address", type: "housenumber", limit: "10", autocomplete: "true", lon: ORLEANS.lon, lat: ORLEANS.lat }
        : { text: query, type: "StreetAddress", maximumResponses: "10", lonlat: ORLEANS.lon + "," + ORLEANS.lat });
      fetch("https://data.geopf.fr/geocodage/" + (numbered ? "search?" : "completion/?") + params, {
        signal: controller.signal, credentials: "omit", referrerPolicy: "no-referrer"
      }).then(function (response) {
        if (!response.ok) throw new Error("Address service unavailable");
        return response.json();
      }).then(function (data) {
        if (!current()) return;
        const raw = data && (numbered ? data.features : data.results);
        if (!Array.isArray(raw)) throw new Error("Invalid address response");
        const items = prioritize(raw.slice(0, 30).map(function (item) {
          return numbered ? completeAddress(item, wanted) : streetSuggestion(item);
        }).filter(Boolean), query, wanted);
        cacheResult(key, items); render(items, numbered);
      }).catch(function (failure) {
        if (current() && failure.name !== "AbortError") showAssistance("La recherche d’adresses est momentanément indisponible. Réessayez ou contactez DFT par téléphone.", true);
      }).finally(function () {
        window.clearTimeout(task.timeout);
        if (request === task) { request = null; input.setAttribute("aria-busy", "false"); }
      });
    }
    function queue(force) {
      close();
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      if (isValid() || composing) return;
      const query = input.value.trim();
      if (query.length < 3 || !/[a-zÀ-ÿ]{2}/i.test(query)) {
        announce(query ? "Saisissez le nom de la rue, avec le numéro si vous le connaissez." : ""); return;
      }
      if (force) cache.clear();
      announce("Recherche d’adresses…");
      const version = sequence;
      debounce = window.setTimeout(function () { search(query, version); }, 250);
    }
    function edit(event) {
      if (event.type === "change" && input.value === lastValue) return;
      lastValue = input.value; selected = null; touched = false; validate(false);
      if (event.isComposing || composing) { close(); return; }
      queue(false);
    }
    input.addEventListener("input", edit);
    input.addEventListener("change", edit); // Native saved addresses still need a BAN selection.
    input.addEventListener("compositionstart", function () { composing = true; close(); });
    input.addEventListener("compositionend", function () { composing = false; edit({ type: "input" }); });
    input.addEventListener("focus", function () {
      window.clearTimeout(blurTimer);
      if (!suppressFocus && !isValid()) queue(false);
    });
    input.addEventListener("blur", function () {
      window.clearTimeout(blurTimer);
      blurTimer = window.setTimeout(function () {
        // Do not move a suggestion, retry button or phone link while a tap is landing.
        if (!listInteraction && !pointerInField && !(field && field.contains(document.activeElement))) { close(); validate(true); }
      }, 160);
    });
    input.addEventListener("keydown", function (event) {
      if (event.isComposing || composing) return;
      if (event.key === "Escape" && (!list.hidden || request || debounce)) {
        event.preventDefault(); event.stopPropagation(); close(); announce(""); return;
      }
      if (event.key === "Tab") { close(); return; }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!results.length) { queue(false); return; }
        setActive(event.key === "ArrowDown" ? (active + 1) % results.length : (active <= 0 ? results.length - 1 : active - 1), true);
      } else if (event.key === "Enter" && !list.hidden) {
        event.preventDefault(); select(active);
      }
    });
    document.addEventListener("pointerdown", function (event) {
      listInteraction = list.contains(event.target);
      pointerInField = Boolean(field && field.contains(event.target));
      if (!box.contains(event.target)) close();
    });
    function releasePointer() { window.setTimeout(function () { pointerInField = false; }, 0); }
    document.addEventListener("pointerup", releasePointer);
    document.addEventListener("pointercancel", releasePointer);
    document.addEventListener("focusin", function (event) { if (!box.contains(event.target)) close(); });
    if (retry) {
      retry.addEventListener("mousedown", function (event) { event.preventDefault(); });
      retry.addEventListener("click", function () { focusInput(); queue(true); });
    }
    if (input.form) input.form.addEventListener("reset", function () {
      close(); cache.clear(); selected = null; touched = false; announce("");
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      window.setTimeout(function () { lastValue = input.value; validate(false); }, 0);
    });
    validate(false);
    return Object.freeze({ validate: validate, isValid: isValid, close: close });
  }
  global.DFTAddressAutocomplete = Object.freeze({ create: create });
}(window));

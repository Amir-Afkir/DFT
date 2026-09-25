/* DFT: a complete, explicitly selected BAN address is required.
 * API: https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/
 * No address is stored in localStorage or sent to any analytics service.
 */
(function (global) {
  "use strict";

  function completeAddress(feature) {
    const p = feature && feature.properties;
    if (!p || p.type !== "housenumber") return null;
    const number = String(p.housenumber || "").trim();
    const street = String(p.street || "").trim();
    const postcode = String(p.postcode || "").trim();
    const city = String(p.city || "").trim();
    if (!/\d/.test(number) || !street || !/^\d{5}$/.test(postcode) || !city) return null;
    return { street: number + " " + street, locality: postcode + " " + city,
      label: number + " " + street + ", " + postcode + " " + city };
  }

  function create(options) {
    const input = options.input;
    const list = options.list;
    const box = options.box;
    const status = options.status;
    const error = options.error;
    const assistance = options.assistance;
    const retry = options.retry;
    if (!input || !list || !box) return null;
    const field = input.closest("[data-field]");
    let selected = null;
    let results = [];
    let active = -1;
    let touched = false;
    let debounce = null;
    let request = null;
    let sequence = 0;
    let composing = false;
    let touchingList = false;

    function announce(message) {
      if (status) status.textContent = message;
    }

    function cancelPending() {
      sequence += 1;
      window.clearTimeout(debounce);
      debounce = null;
      if (request) {
        window.clearTimeout(request.timeout);
        request.controller.abort();
        request = null;
      }
      input.setAttribute("aria-busy", "false");
    }

    function hideList() {
      results = [];
      active = -1;
      list.replaceChildren();
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      box.classList.remove("is-open");
    }

    function close() {
      const loading = input.getAttribute("aria-busy") === "true" || debounce !== null;
      cancelPending();
      hideList();
      touchingList = false;
      if (loading) announce("");
    }

    function isValid() {
      if (selected && input.value !== selected.label) selected = null;
      return Boolean(selected);
    }

    function validate(showMessage) {
      if (showMessage) touched = true;
      const valid = isValid();
      const message = valid ? "" : input.value.trim()
        ? "Sélectionnez une adresse complète avec numéro, rue, code postal et commune dans les suggestions."
        : "Renseignez puis sélectionnez l’adresse complète du lieu d’intervention.";
      input.setCustomValidity(message);
      input.setAttribute("aria-invalid", String(touched && !valid));
      if (field) {
        field.classList.toggle("is-valid", valid);
        field.classList.toggle("is-invalid", touched && !valid);
      }
      if (error) error.textContent = touched ? message : "";
      return valid;
    }

    function select(index) {
      const item = results[index];
      if (!item) return;
      close();
      selected = item;
      input.value = item.label;
      validate(true);
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      announce("Adresse sélectionnée : " + item.label);
      input.focus({ preventScroll: true });
    }

    function setActive(index) {
      active = index;
      Array.from(list.children).forEach(function (option, i) {
        option.setAttribute("aria-selected", String(i === active));
        option.classList.toggle("is-active", i === active);
        if (i === active) {
          input.setAttribute("aria-activedescendant", option.id);
          option.scrollIntoView({ block: "nearest" });
        }
      });
    }

    function showAssistance(message, canRetry) {
      hideList();
      announce(message);
      if (assistance) assistance.hidden = false;
      if (retry) retry.hidden = !canRetry;
    }

    function render(features) {
      hideList();
      const seen = new Set();
      results = features.map(completeAddress).filter(function (item) {
        if (!item || seen.has(item.label)) return false;
        seen.add(item.label);
        return true;
      }).slice(0, 5);
      if (!results.length) {
        showAssistance("Aucune adresse complète trouvée. Ajoutez le numéro, le nom de la rue et la commune ou le code postal.", false);
        return;
      }
      results.forEach(function (item, index) {
        const option = document.createElement("div");
        option.className = "address-suggestion";
        option.id = input.id + "-option-" + index;
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");
        const main = document.createElement("strong");
        const detail = document.createElement("small");
        // API text must never be parsed as HTML.
        main.textContent = item.street;
        detail.textContent = item.locality;
        option.append(main, detail);
        // Keep focus on the combobox with a mouse; let touch scrolling work.
        option.addEventListener("mousedown", function (event) { event.preventDefault(); });
        option.addEventListener("click", function () { select(index); });
        list.appendChild(option);
      });
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      box.classList.add("is-open");
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      announce(results.length + " adresse" + (results.length > 1 ? "s" : "") + " trouvée" + (results.length > 1 ? "s" : "") + " (Base Adresse Nationale). Sélectionnez votre adresse.");
    }

    function search(query, version) {
      debounce = null;
      if (version !== sequence || query !== input.value.trim()) return;
      const controller = new AbortController();
      const task = { controller: controller, timeout: null };
      request = task;
      input.setAttribute("aria-busy", "true");
      announce("Recherche d’adresses…");
      function current() {
        return sequence === version && request === task && input.value.trim() === query;
      }
      task.timeout = window.setTimeout(function () {
        if (!current()) return;
        cancelPending();
        showAssistance("La recherche prend trop de temps. Réessayez ou contactez DFT par téléphone.", true);
      }, 8000);
      const params = new URLSearchParams({ q: query, index: "address", type: "housenumber", limit: "5", autocomplete: "true" });
      fetch("https://data.geopf.fr/geocodage/search?" + params.toString(), {
        signal: controller.signal, credentials: "omit", referrerPolicy: "no-referrer"
      }).then(function (response) {
        if (!response.ok) throw new Error("Address service unavailable");
        return response.json();
      }).then(function (data) {
        if (!current()) return;
        if (!data || !Array.isArray(data.features)) throw new Error("Invalid address response");
        render(data.features);
      }).catch(function (failure) {
        if (current() && failure.name !== "AbortError") {
          showAssistance("La recherche d’adresses est momentanément indisponible. Réessayez ou contactez DFT par téléphone.", true);
        }
      }).finally(function () {
        window.clearTimeout(task.timeout);
        if (request === task) {
          request = null;
          input.setAttribute("aria-busy", "false");
        }
      });
    }

    function queue() {
      close();
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      if (isValid() || composing) return;
      const query = input.value.trim();
      if (query.length < 3 || !/\d/.test(query)) {
        announce(query ? "Commencez par le numéro et le nom de la rue, puis ajoutez votre commune." : "");
        if (assistance) assistance.hidden = query.length < 3;
        return;
      }
      announce("Recherche d’adresses…");
      const version = sequence;
      debounce = window.setTimeout(function () { search(query, version); }, 300);
    }

    input.addEventListener("input", function (event) {
      selected = null;
      validate(false);
      if (event.isComposing || composing) { close(); return; }
      queue();
    });
    input.addEventListener("compositionstart", function () { composing = true; close(); });
    input.addEventListener("compositionend", function () { composing = false; selected = null; validate(false); queue(); });
    input.addEventListener("focus", function () { touchingList = false; if (!isValid()) queue(); });
    input.addEventListener("change", function () { validate(true); });
    input.addEventListener("blur", function () {
      validate(true);
      window.setTimeout(function () {
        if (!touchingList && !box.contains(document.activeElement)) close();
      }, 120);
    });
    input.addEventListener("keydown", function (event) {
      if (event.isComposing || composing) return;
      if (event.key === "Escape" && (!list.hidden || request || debounce)) {
        event.preventDefault(); event.stopPropagation(); close(); announce(""); return;
      }
      if (event.key === "Tab") { close(); return; }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!results.length) { queue(); return; }
        setActive(event.key === "ArrowDown" ? (active + 1) % results.length : (active <= 0 ? results.length - 1 : active - 1));
      } else if (event.key === "Enter" && !list.hidden) {
        event.preventDefault();
        if (active >= 0) select(active); else validate(true);
      }
    });
    list.addEventListener("pointerdown", function () { touchingList = true; });
    document.addEventListener("pointerdown", function (event) { if (!box.contains(event.target)) close(); });
    document.addEventListener("focusin", function (event) { if (!box.contains(event.target)) close(); });
    if (retry) {
      // Do not let blur-time error text move the button before the click lands.
      retry.addEventListener("mousedown", function (event) { event.preventDefault(); });
      retry.addEventListener("click", function () { input.focus({ preventScroll: true }); queue(); });
    }
    if (input.form) input.form.addEventListener("reset", function () {
      close(); selected = null; touched = false; announce("");
      if (assistance) assistance.hidden = true;
      if (retry) retry.hidden = true;
      window.setTimeout(function () { validate(false); }, 0);
    });
    validate(false);
    return Object.freeze({ validate: validate, isValid: isValid, close: close });
  }

  global.DFTAddressAutocomplete = Object.freeze({ create: create });
}(window));

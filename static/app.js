(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const state = {
    lat: null,
    lon: null,
    yelpConfigured: false,
    restaurants: [],
    selected: null,
    menuItems: [],
  };

  const els = {
    pills: $$(".step-pill"),
    address: $("#addressInput"),
    radius: $("#radiusSelect"),
    dataSource: $("#dataSourceSelect"),
    yelpTerm: $("#yelpTermRow"),
    yelpTermInput: $("#yelpTermInput"),
    preference: $("#preferenceSelect"),
    btnGps: $("#btnGps"),
    btnIp: $("#btnIp"),
    btnGeocode: $("#btnGeocode"),
    btnDiscover: $("#btnDiscover"),
    coordLine: $("#coordLine"),
    restSection: $("#restSection"),
    restGrid: $("#restGrid"),
    pickSection: $("#pickSection"),
    pickDetail: $("#pickDetail"),
    menuChips: $("#menuChips"),
    btnSpin: $("#btnSpin"),
    wheel: $("#wheel"),
    resultCard: $("#resultCard"),
    resultLuck: $("#resultLuck"),
    resultRest: $("#resultRest"),
    resultFood: $("#resultFood"),
    resultDrink: $("#resultDrink"),
    resultMsg: $("#resultMsg"),
    err: $("#errorBanner"),
    loadDiscover: $("#loadDiscover"),
    loadPick: $("#loadPick"),
    yelpFoot: $("#yelpFooter"),
    btnReset: $("#btnReset"),
  };

  function showErr(msg) {
    els.err.textContent = msg;
    els.err.classList.add("visible");
  }
  function clearErr() {
    els.err.textContent = "";
    els.err.classList.remove("visible");
  }

  async function apiJson(url, options = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
    let data = {};
    try {
      data = await res.json();
    } catch {
      /* empty */
    }
    if (!res.ok) {
      const msg =
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map((d) => d.msg || d).join("; ")
            : data.error || res.statusText;
      throw new Error(msg || "Request failed");
    }
    return data;
  }

  function setPills(step) {
    const names = ["loc", "browse", "roulette"];
    els.pills.forEach((p, i) => {
      p.classList.remove("active", "done");
      if (i + 1 < step) p.classList.add("done");
      if (i + 1 === step) p.classList.add("active");
    });
  }

  function updateCoordLine() {
    if (state.lat != null && state.lon != null) {
      els.coordLine.textContent = `Using ${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`;
    } else {
      els.coordLine.textContent = "";
    }
  }

  function toggleYelpTermRow() {
    const v = els.dataSource.value;
    els.yelpTerm.classList.toggle("hidden", v !== "yelp");
  }

  function effectiveSource() {
    let s = els.dataSource.value;
    if (s === "auto") s = state.yelpConfigured ? "yelp" : "osm";
    if (s === "yelp" && !state.yelpConfigured) s = "osm";
    return s;
  }

  async function loadConfig() {
    const cfg = await apiJson("/api/config");
    state.yelpConfigured = !!cfg.yelp_configured;
    const optAuto = $("#optAuto");
    const optYelp = $("#optYelp");
    if (optAuto) {
      optAuto.textContent = state.yelpConfigured
        ? "Auto (Yelp — key found)"
        : "Auto (OpenStreetMap — no Yelp key)";
    }
    if (optYelp) {
      optYelp.disabled = !state.yelpConfigured;
      optYelp.textContent = state.yelpConfigured ? "Yelp only" : "Yelp only (add YELP_API_KEY)";
    }
    toggleYelpTermRow();
  }

  function resetFlow() {
    state.restaurants = [];
    state.selected = null;
    state.menuItems = [];
    els.restGrid.innerHTML = "";
    els.pickDetail.innerHTML = "";
    els.menuChips.innerHTML = "";
    els.pickSection.classList.add("hidden");
    els.resultCard.classList.remove("visible");
    els.wheel.classList.remove("spinning");
    clearErr();
    setPills(1);
  }

  function cardLetter(name) {
    const t = (name || "?").trim();
    return t.charAt(0).toUpperCase();
  }

  function renderRestaurants() {
    els.restGrid.innerHTML = "";
    const src = effectiveSource();
    els.yelpFoot.classList.toggle("hidden", src !== "yelp");

    state.restaurants.forEach((r) => {
      const card = document.createElement("article");
      card.className = "rest-card";
      card.dataset.id = r.id || r.name;
      const photo = r.photo_url;
      const thumb = document.createElement("div");
      thumb.className = "thumb" + (photo ? "" : " placeholder");
      if (photo) thumb.style.backgroundImage = `url("${photo.replace(/"/g, "")}")`;
      else thumb.textContent = cardLetter(r.name);

      const badge = document.createElement("span");
      badge.className = "badge-src" + (r.source === "yelp" ? " yelp" : "");
      badge.textContent = r.source === "yelp" ? "Yelp" : "OSM";

      thumb.appendChild(badge);

      const body = document.createElement("div");
      body.className = "body";
      const h = document.createElement("h3");
      h.textContent = r.name;
      const meta = document.createElement("div");
      meta.className = "meta";
      const dist =
        r.distance_km != null ? `${r.distance_km} km` : "";
      meta.textContent = [dist, r.address].filter(Boolean).join(" · ");

      body.appendChild(h);
      body.appendChild(meta);

      if (r.rating != null) {
        const rl = document.createElement("div");
        rl.className = "rating-line";
        rl.textContent = `★ ${r.rating} (${r.review_count ?? 0} reviews)`;
        body.appendChild(rl);
      }

      card.appendChild(thumb);
      card.appendChild(body);

      card.addEventListener("click", () => selectRestaurant(r, card));
      els.restGrid.appendChild(card);
    });

    els.restSection.classList.remove("hidden");
    setPills(2);
  }

  async function selectRestaurant(r, cardEl) {
    $$(".rest-card").forEach((c) => c.classList.remove("selected"));
    cardEl.classList.add("selected");
    state.selected = r;
    clearErr();
    els.loadPick.classList.add("visible");
    els.pickSection.classList.remove("hidden");

    const coords = r.coordinates || {};
    const mapsUrl =
      r.url ||
      r.maps_url ||
      `https://www.google.com/maps/search/?api=1&query=${coords.lat},${coords.lon}`;

    const img = r.photo_url
      ? `<img class="detail-thumb" src="${r.photo_url.replace(/"/g, "")}" alt="">`
      : `<div class="detail-thumb" style="display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-size:2rem;color:#444;">${cardLetter(r.name)}</div>`;

    const yelpLink =
      r.source === "yelp" && r.url
        ? `<p style="margin:0.35rem 0 0;font-size:0.85rem;"><a href="${r.url}" target="_blank" rel="noopener">Open on Yelp →</a></p>`
        : "";

    els.pickDetail.innerHTML = `
      <div class="detail-head">
        ${img}
        <div>
          <h2 style="margin:0 0 0.35rem;font-size:1.35rem;">${escapeHtml(r.name)}</h2>
          <p style="margin:0;color:var(--muted);font-size:0.9rem;line-height:1.45;">${escapeHtml(r.address || "")}</p>
          <p style="margin:0.5rem 0 0;"><a href="${mapsUrl}" target="_blank" rel="noopener">Maps / directions →</a></p>
          ${yelpLink}
        </div>
      </div>
      <p class="hint" style="margin:0 0 0.75rem;">These are <strong>suggested orders</strong> based on cuisine tags — not live menus from the kitchen. The roulette only picks from the list below.</p>
    `;

    try {
      const sug = await apiJson("/api/decision/menu-suggestions", {
        method: "POST",
        body: JSON.stringify({ restaurant: r }),
      });
      state.menuItems = sug.items || [];
      els.menuChips.innerHTML = "";
      state.menuItems.forEach((item, idx) => {
        const span = document.createElement("span");
        span.className = "chip";
        span.textContent = item;
        span.dataset.idx = String(idx);
        els.menuChips.appendChild(span);
      });
    } catch (e) {
      showErr(e.message);
      state.menuItems = [];
    } finally {
      els.loadPick.classList.remove("visible");
    }

    setPills(3);
    els.resultCard.classList.remove("visible");
    els.pickSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function runDiscover() {
    clearErr();
    if (state.lat == null || state.lon == null) {
      showErr("Set a location first (GPS, IP, or geocode an address).");
      return;
    }
    const radius = parseInt(els.radius.value, 10) || 15000;
    const src = els.dataSource.value;
    if (src === "yelp" && !state.yelpConfigured) {
      showErr("Yelp is not configured. Add YELP_API_KEY to your .env file.");
      return;
    }

    els.loadDiscover.classList.add("visible");
    els.btnDiscover.disabled = true;
    try {
      const body = {
        lat: state.lat,
        lon: state.lon,
        radius,
        source: src === "auto" ? "auto" : src,
      };
      if (src === "yelp" && els.yelpTermInput.value.trim()) {
        body.yelp_term = els.yelpTermInput.value.trim();
      }
      const data = await apiJson("/api/restaurants/discover", {
        method: "POST",
        body: JSON.stringify(body),
      });
      state.restaurants = data.restaurants || [];
      if (!state.restaurants.length) {
        showErr("No places found. Try a larger radius or another data source.");
        els.restSection.classList.add("hidden");
        return;
      }
      renderRestaurants();
    } catch (e) {
      showErr(e.message);
    } finally {
      els.loadDiscover.classList.remove("visible");
      els.btnDiscover.disabled = false;
    }
  }

  function flashChipsWinner(winner) {
    const chips = $$(".chip", els.menuChips);
    let i = 0;
    const id = setInterval(() => {
      chips.forEach((c) => c.classList.remove("highlight"));
      const c = chips[i % chips.length];
      if (c) c.classList.add("highlight");
      i++;
    }, 80);
    return new Promise((resolve) => {
      setTimeout(() => {
        clearInterval(id);
        chips.forEach((c) => c.classList.remove("highlight"));
        chips.forEach((c) => {
          if (c.textContent === winner) c.classList.add("highlight");
        });
        resolve();
      }, 1600);
    });
  }

  async function runSpin() {
    clearErr();
    if (!state.selected) {
      showErr("Pick a restaurant first.");
      return;
    }
    if (!state.menuItems.length) {
      showErr("No menu suggestions loaded.");
      return;
    }

    els.btnSpin.disabled = true;
    els.wheel.classList.add("spinning");

    try {
      const data = await apiJson("/api/decision/spin-order", {
        method: "POST",
        body: JSON.stringify({
          restaurant: state.selected,
          menu_items: state.menuItems,
          preference: els.preference.value,
        }),
      });
      const winner = data.decision.menu_item;
      await flashChipsWinner(winner);

      els.resultLuck.textContent = `Luck roll: ${(data.decision.luck_factor ?? 0).toFixed(2)}`;
      els.resultRest.textContent = state.selected.name;
      els.resultFood.textContent = winner;
      els.resultDrink.textContent = data.decision.drink
        ? `Drink: ${data.decision.drink}`
        : "";
      els.resultMsg.textContent =
        data.explanation?.luck_description ||
        "Enjoy — you earned this spin.";
      els.resultCard.classList.add("visible");
    } catch (e) {
      showErr(e.message);
    } finally {
      els.wheel.classList.remove("spinning");
      els.btnSpin.disabled = false;
    }
  }

  /* --- Handlers --- */
  els.btnGps.addEventListener("click", () => {
    clearErr();
    if (!navigator.geolocation) {
      showErr("Geolocation not supported.");
      return;
    }
    els.btnGps.disabled = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.lat = pos.coords.latitude;
        state.lon = pos.coords.longitude;
        updateCoordLine();
        els.btnGps.disabled = false;
      },
      () => {
        showErr("GPS denied or failed. Try IP location or type an address.");
        els.btnGps.disabled = false;
      }
    );
  });

  els.btnIp.addEventListener("click", async () => {
    clearErr();
    els.btnIp.disabled = true;
    try {
      const d = await apiJson("/api/location/detect");
      if (!d.success || !d.location) throw new Error(d.error || "IP location failed");
      state.lat = d.location.lat;
      state.lon = d.location.lon;
      updateCoordLine();
    } catch (e) {
      showErr(e.message);
    } finally {
      els.btnIp.disabled = false;
    }
  });

  els.btnGeocode.addEventListener("click", async () => {
    clearErr();
    const q = els.address.value.trim();
    if (!q) {
      showErr("Enter a city or address to geocode.");
      return;
    }
    els.btnGeocode.disabled = true;
    try {
      const d = await apiJson("/api/location/geocode", {
        method: "POST",
        body: JSON.stringify({ address: q }),
      });
      if (!d.success || !d.location) throw new Error(d.error || "Geocode failed");
      state.lat = d.location.lat;
      state.lon = d.location.lon;
      updateCoordLine();
    } catch (e) {
      showErr(e.message);
    } finally {
      els.btnGeocode.disabled = false;
    }
  });

  els.dataSource.addEventListener("change", toggleYelpTermRow);

  els.btnDiscover.addEventListener("click", runDiscover);
  els.btnSpin.addEventListener("click", runSpin);

  els.btnReset.addEventListener("click", () => {
    resetFlow();
    els.restSection.classList.add("hidden");
  });

  loadConfig().catch(() => {
    state.yelpConfigured = false;
  });
  toggleYelpTermRow();
})();

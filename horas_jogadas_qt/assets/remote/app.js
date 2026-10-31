"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const copy = {
    pt: {
      remote: "CONTROLE PELO CELULAR", waiting: "Aguardando conexão", connected: "Conectado ao PC", disconnected: "Sem conexão", connecting: "Conectando…",
      your_space: "SEU TEMPO DE JOGO", pair_title: "Seu contador,\nsempre por perto.", pair_intro: "Escolha o jogo, inicie a sessão e aproveite a partida. Seu histórico continua no computador.",
      connect_title: "Conectar ao seu PC", pair_help: "No app, abra Configurações → Controle pelo celular e digite o código exibido.", pair_code: "Código de conexão", connect: "Conectar",
      same_wifi: "Celular e PC na mesma rede Wi-Fi. Mantenha o app aberto no computador.", local_connection: "Conexão local · Seus registros continuam com você",
      library: "Biblioteca", library_intro: "Seu próximo jogo. Uma sessão de cada vez.", add_game: "Adicionar jogo", in_session: "Suas sessões", all_games: "Todos os jogos", other_games: "Outros jogos", search: "Buscar na biblioteca…",
      saved_on_pc: "As sessões são salvas no seu computador.", disconnect: "Desconectar este celular", retry: "Tentar novamente", add_hint: "O jogo também aparecerá na biblioteca do seu PC.",
      game_name: "Nome do jogo", game_name_placeholder: "O que vamos jogar?", cancel: "Cancelar", session: "SESSÃO ATUAL", finish_title: "Encerrar esta sessão?", finish_help: "O tempo será salvo no histórico do seu PC.", finish_save: "Encerrar e salvar",
      start: "Iniciar", resume: "Retomar", pause: "Pausar", finish: "Encerrar", playing: "Em andamento", paused: "Pausado", ready: "Pronto para jogar", total: "Tempo total", sending: "Enviando…",
      no_games: "Sua próxima partida começa aqui.", no_games_hint: "Adicione um jogo para começar a contar.", nothing: "Nenhum jogo encontrado.", nothing_hint: "Tente outro nome na busca.",
      offline: "A conexão com o PC foi interrompida. Seus comandos ficam indisponíveis até reconectar. Confira se o app continua aberto e na mesma rede.",
      stale: "O contador foi alterado no PC ou em outro celular. Atualizamos os dados; confira a sessão antes de tentar novamente.",
      recovery: "Há uma sessão para recuperar no PC. Resolva a recuperação no app antes de controlar pelo celular.",
      busy: "Conclua a janela aberta no PC antes de enviar outro comando.", invalid: "Confira os dados e tente novamente.", storage: "Não foi possível salvar no PC. Confira o espaço e as permissões da pasta de dados antes de tentar novamente.",
      unauthorized: "A conexão foi encerrada. Use o código ou escaneie o QR Code atual nas Configurações do PC.", pairing_expired: "Esse código expirou. Gere um novo código nas Configurações do PC.",
      invalid_code: "Código não reconhecido. Confira o código nas Configurações do PC.",
      rate_limited: "Muitas tentativas. Aguarde um pouco antes de tentar novamente.", unavailable: "Não foi possível acessar o PC. Confira a rede e mantenha o app aberto.", not_found: "Esse jogo foi removido no PC. Atualizamos a biblioteca.",
      saved: "Sessão salva no histórico.", added: "Jogo adicionado à biblioteca.", started: "Contador iniciado.", pause_done: "Contador pausado.", disconnected_done: "Este celular foi desconectado.", confirm_name: "Sessão de {name}",
    },
    en: {
      remote: "PHONE CONTROL", waiting: "Waiting to connect", connected: "Connected to PC", disconnected: "Connection lost", connecting: "Connecting…",
      your_space: "YOUR GAMING TIME", pair_title: "Your timer,\nalways close by.", pair_intro: "Pick a game, start a session and enjoy playing. Your history stays on your computer.",
      connect_title: "Connect to your PC", pair_help: "In the app, open Settings → Phone control and enter the code shown there.", pair_code: "Pairing code", connect: "Connect",
      same_wifi: "Keep your phone and PC on the same Wi-Fi network, with the app open on your computer.", local_connection: "Local connection · Your records stay with you",
      library: "Library", library_intro: "Your next game. One session at a time.", add_game: "Add game", in_session: "Your sessions", all_games: "All games", other_games: "Other games", search: "Search your library…",
      saved_on_pc: "Sessions are saved on your computer.", disconnect: "Disconnect this phone", retry: "Try again", add_hint: "The game will also appear in your PC library.",
      game_name: "Game name", game_name_placeholder: "What are we playing?", cancel: "Cancel", session: "CURRENT SESSION", finish_title: "Finish this session?", finish_help: "Your time will be saved to your PC history.", finish_save: "Finish and save",
      start: "Start", resume: "Resume", pause: "Pause", finish: "Finish", playing: "Playing", paused: "Paused", ready: "Ready to play", total: "Total time", sending: "Sending…",
      no_games: "Your next session starts here.", no_games_hint: "Add a game to start tracking your time.", nothing: "No games found.", nothing_hint: "Try a different name in the search.",
      offline: "The connection to your PC was interrupted. Controls will be available after reconnecting. Check that the app is still open and on the same network.",
      stale: "The timer changed on your PC or another phone. We refreshed the data; check the session before trying again.",
      recovery: "A session needs to be recovered on your PC. Resolve it in the app before using phone controls.",
      busy: "Finish the dialog open on your PC before sending another command.", invalid: "Check the details and try again.", storage: "Could not save on your PC. Check available space and data folder permissions before trying again.",
      unauthorized: "Your connection ended. Use the current code or scan the QR code in your PC settings.", pairing_expired: "This code expired. Generate a new code in your PC settings.",
      invalid_code: "Code not recognized. Check the current code in your PC settings.",
      rate_limited: "Too many attempts. Please wait a little before trying again.", unavailable: "Could not reach your PC. Check your network and keep the app open.", not_found: "This game was removed on your PC. We refreshed the library.",
      saved: "Session saved to history.", added: "Game added to your library.", started: "Timer started.", pause_done: "Timer paused.", disconnected_done: "This phone was disconnected.", confirm_name: "Session for {name}",
    },
  };
  const model = {language: "pt", token: "", state: null, received: 0, connected: false, pairing: false, mutating: false, disconnecting: false, polling: false, epoch: 0, finishGame: null, notice: ""};
  const cards = new Map();
  const t = key => (copy[model.language] || copy.pt)[key] || copy.pt[key] || key;
  const storage = {
    read() { try { return sessionStorage.getItem("horasjogadas-remote") || ""; } catch (_) { return ""; } },
    write(value) { try { if (value) sessionStorage.setItem("horasjogadas-remote", value); else sessionStorage.removeItem("horasjogadas-remote"); } catch (_) {} },
  };
  const secret = new URLSearchParams(location.hash.slice(1)).get("pair");
  if (location.hash || location.search) history.replaceState(null, "", location.pathname);
  model.token = secret ? "" : storage.read();
  if (secret) storage.write("");

  function icon(name) {
    const paths = {play: "m7 4 11 8-11 8Z", pause: "M8 5v14M16 5v14", stop: "M6 6h12v12H6Z", search: "m21 21-5.2-5.2M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z"};
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS(svg.namespaceURI, "path"); path.setAttribute("d", paths[name]);
    path.setAttribute("fill", name === "play" || name === "stop" ? "currentColor" : "none");
    path.setAttribute("stroke", "currentColor"); path.setAttribute("stroke-width", "1.7"); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round"); svg.append(path);
    return svg;
  }
  $("search-icon").append(icon("search"));

  function applyInfo(info) {
    const language = info.language === "en" ? "en" : "pt";
    const changed = language !== model.language;
    model.language = language;
    document.documentElement.lang = language === "en" ? "en" : "pt-BR";
    document.documentElement.dataset.theme = info.theme || "dark";
    document.documentElement.style.colorScheme = info.theme === "light" ? "light" : "dark";
    const palette = info.palette || {};
    for (const key of ["bg", "side", "card", "border", "text", "muted", "accent", "on_accent"]) {
      if (/^#[0-9a-f]{6}$/i.test(palette[key] || "")) document.documentElement.style.setProperty("--" + key.replace("_", "-"), palette[key]);
    }
    if (/^#[0-9a-f]{6}$/i.test(palette.bg || "")) document.querySelector("meta[name=theme-color]").content = palette.bg;
    document.title = "HorasJogadas · " + (language === "en" ? "Phone control" : "Controle pelo celular");
    if (changed || !document.documentElement.dataset.translated) {
      document.querySelectorAll("[data-text]").forEach(el => { el.textContent = t(el.dataset.text); });
      document.querySelectorAll("[data-placeholder]").forEach(el => { el.placeholder = t(el.dataset.placeholder); });
      document.documentElement.dataset.translated = "true";
    }
    connection(model.connected ? "connected" : model.token && model.state ? "disconnected" : "waiting");
    if (model.notice) setNotice(model.notice);
  }

  function connection(kind) {
    const status = $("connection");
    status.className = "connection" + (kind === "connected" ? " online" : kind === "disconnected" ? " offline" : "");
    status.lastElementChild.textContent = t(kind);
  }
  function setNotice(key) {
    model.notice = key;
    $("notice").hidden = !key;
    $("notice-text").textContent = key ? t(key) : "";
    $("retry-button").hidden = key !== "offline";
  }
  function apiError(code) { const error = new Error(code); error.code = code; return error; }
  async function api(path, body, authenticated = true) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const headers = {Accept: "application/json"};
    if (authenticated && model.token) headers.Authorization = "Bearer " + model.token;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    try {
      const response = await fetch(path, {method: body === undefined ? "GET" : "POST", headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal, cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer"});
      let data;
      try { data = await response.json(); } catch (_) { throw apiError("unavailable"); }
      if (!response.ok) throw apiError(typeof data.error === "string" ? data.error : "unavailable");
      return data;
    } catch (error) {
      if (error.code) throw error;
      throw apiError("unavailable");
    } finally { clearTimeout(timer); }
  }

  function disconnect(message = "") {
    model.token = ""; storage.write(""); model.connected = false; model.state = null; model.finishGame = null; model.epoch++;
    cards.forEach(card => card.element.remove()); cards.clear();
    for (const dialog of [$("add-dialog"), $("finish-dialog")]) if (dialog.open) dialog.close();
    $("control-view").hidden = true; $("pair-view").hidden = false; $("pair-footer").hidden = false;
    $("pair-message").textContent = message ? t(message) : ""; $("pair-code").value = "";
    connection("waiting");
  }

  async function pair(body) {
    if (model.pairing) return;
    model.pairing = true; $("pair-button").disabled = true; $("pair-button").textContent = t("connecting"); $("pair-message").textContent = ""; connection("connecting");
    try {
      const result = await api("/api/pair", body, false);
      if (typeof result.token !== "string" || !result.token) throw apiError("unavailable");
      model.token = result.token; storage.write(model.token);
      await syncState();
    } catch (error) { $("pair-message").textContent = errorText(error.code === "unauthorized" ? "invalid_code" : error.code); connection("waiting"); }
    finally { model.pairing = false; $("pair-button").disabled = false; $("pair-button").textContent = t("connect"); }
  }

  function errorText(code) {
    const key = {conflict: "stale", rate_limit: "rate_limited", expired: "pairing_expired"}[code] || code;
    return t(copy.pt[key] ? key : "unavailable");
  }
  function markOffline() {
    model.connected = false; connection("disconnected");
    if (model.state) setNotice("offline");
    updateControls();
  }
  function acceptState(state) {
    if (!Array.isArray(state.games)) throw apiError("unavailable");
    model.state = state; model.received = performance.now(); model.connected = true;
    applyInfo(state);
    $("pair-view").hidden = true; $("pair-footer").hidden = true; $("control-view").hidden = false;
    connection("connected");
    if (state.pending_recovery) setNotice("recovery");
    else if (model.notice === "offline" || model.notice === "recovery") setNotice("");
    renderGames();
  }
  async function syncState() {
    if (!model.token || model.polling || model.mutating || model.disconnecting) return;
    model.polling = true;
    const epoch = model.epoch;
    try {
      const result = await api("/api/state");
      if (epoch === model.epoch) acceptState(result);
    } catch (error) {
      if (epoch !== model.epoch) return;
      if (error.code === "unauthorized") disconnect("unauthorized");
      else markOffline();
    } finally { model.polling = false; }
  }

  function initials(name) { return String(name).trim().split(/\s+/).filter(Boolean).slice(0, 2).map(s => Array.from(s)[0]).join("").toUpperCase(); }
  function normalize(value) { return String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase(); }
  function elapsed(game) { return Math.max(0, Number(game.seconds) || 0) + (game.running && model.connected ? Math.max(0, performance.now() - model.received) / 1000 : 0); }
  function clock(seconds) {
    const total = Math.floor(Math.max(0, seconds));
    return String(Math.floor(total / 3600)).padStart(2, "0") + ":" + String(Math.floor(total / 60) % 60).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0");
  }
  function duration(seconds) {
    const value = Math.floor(Math.max(0, Number(seconds) || 0));
    return Math.floor(value / 3600) + "h " + String(Math.floor(value / 60) % 60).padStart(2, "0") + "m";
  }
  function node(tag, name, text) { const el = document.createElement(tag); if (name) el.className = name; if (text !== undefined) el.textContent = text; return el; }
  function gameCard(game) {
    const card = {element: node("article", "game-card"), game};
    const head = node("div", "game-head"), identity = node("div", "game-identity");
    card.avatar = node("div", "avatar"); card.avatar.setAttribute("aria-hidden", "true");
    card.name = node("h3", "game-name"); card.status = node("span", "game-status"); identity.append(card.name, card.status); head.append(card.avatar, identity);
    card.session = node("div", "session-label"); card.elapsed = node("div", "elapsed"); card.elapsed.setAttribute("aria-live", "off");
    card.activity = node("div", "activity"); card.activity.append(node("i")); card.activityText = node("span"); card.activity.append(card.activityText);
    card.total = node("p", "total");
    const actions = node("div", "card-actions");
    card.start = node("button", "start-button primary"); card.start.type = "button"; card.start.append(icon("play")); card.startText = node("span"); card.start.append(card.startText);
    card.pause = node("button", "icon-button"); card.pause.type = "button"; card.pause.append(icon("pause"));
    card.finish = node("button", "icon-button stop-button"); card.finish.type = "button"; card.finish.append(icon("stop"));
    card.start.addEventListener("click", () => command("start", card.game)); card.pause.addEventListener("click", () => command("pause", card.game)); card.finish.addEventListener("click", () => showFinish(card.game));
    actions.append(card.start, card.pause, card.finish); card.element.append(head, card.session, card.elapsed, card.activity, card.total, actions);
    return card;
  }
  function updateCard(card, game) {
    card.game = game;
    card.element.className = "game-card" + (game.running ? " running" : game.pending ? " paused" : "");
    card.name.textContent = game.name; card.name.title = game.name; card.avatar.textContent = initials(game.name);
    card.status.textContent = String(game.status_label || game.status || "").toUpperCase(); card.status.dataset.status = game.status;
    card.session.textContent = t("session"); card.activityText.textContent = t(game.running ? "playing" : game.pending ? "paused" : "ready");
    card.startText.textContent = t(game.running ? "playing" : game.pending ? "resume" : "start");
    card.start.setAttribute("aria-label", t(game.pending ? "resume" : "start") + " · " + game.name);
    card.pause.setAttribute("aria-label", t("pause") + " · " + game.name); card.pause.title = t("pause");
    card.finish.setAttribute("aria-label", t("finish") + " · " + game.name); card.finish.title = t("finish");
    updateClock(card); updateCardControls(card);
  }
  function updateClock(card) {
    const seconds = elapsed(card.game);
    const time = clock(seconds);
    if (card.elapsed.textContent !== time) card.elapsed.textContent = time;
    const total = t("total") + " · " + duration((Number(card.game.total_seconds) || 0) + seconds - (Number(card.game.seconds) || 0));
    if (card.total.textContent !== total) card.total.textContent = total;
  }
  function updateCardControls(card) {
    const blocked = !model.connected || model.mutating || model.disconnecting || Boolean(model.state && model.state.pending_recovery);
    card.start.disabled = blocked || card.game.running;
    card.pause.disabled = blocked || !card.game.running;
    card.finish.disabled = blocked || !card.game.pending;
  }
  function updateControls() {
    cards.forEach(updateCardControls);
    const blocked = !model.connected || model.mutating || model.disconnecting || Boolean(model.state && model.state.pending_recovery);
    $("add-button").disabled = blocked; $("add-confirm").disabled = blocked; $("finish-confirm").disabled = blocked;
    $("disconnect").disabled = model.mutating || model.disconnecting;
    document.querySelectorAll(".dialog-cancel").forEach(button => { button.disabled = model.mutating; });
  }
  function renderGames() {
    if (!model.state) return;
    const games = model.state.games;
    const ids = new Set(games.map(game => game.id));
    for (const [id, card] of cards) if (!ids.has(id)) { card.element.remove(); cards.delete(id); }
    const query = normalize($("search").value.trim());
    const active = [], other = [];
    for (const game of games) {
      let card = cards.get(game.id);
      if (!card) { card = gameCard(game); cards.set(game.id, card); }
      updateCard(card, game);
      if (game.pending) active.push(card); else other.push(card);
      card.element.hidden = Boolean(query && !normalize(game.name).includes(query));
    }
    // Keep keyed nodes in place so polling preserves keyboard focus and scrolling.
    function place(parent, values) {
      values.forEach((card, index) => { if (parent.children[index] !== card.element) parent.insertBefore(card.element, parent.children[index] || null); });
    }
    place($("active-games"), active); place($("library-games"), other);
    const visibleActive = active.filter(card => !card.element.hidden).length;
    const visibleOther = other.filter(card => !card.element.hidden).length;
    $("active-section").hidden = !visibleActive;
    $("active-count").textContent = String(visibleActive);
    $("games-heading").textContent = t(active.length ? "other_games" : "all_games");
    $("game-count").textContent = String(other.length);
    $("empty").hidden = Boolean(visibleActive || visibleOther);
    $("empty-title").textContent = t(games.length ? "nothing" : "no_games");
    $("empty-description").textContent = t(games.length ? "nothing_hint" : "no_games_hint");
    updateControls();
  }

  function requestId() {
    const values = new Uint32Array(4); crypto.getRandomValues(values);
    return Array.from(values, n => n.toString(16).padStart(8, "0")).join("");
  }
  async function command(action, game, name) {
    if (!model.connected || model.mutating || model.disconnecting) return;
    model.mutating = true; model.epoch++; updateControls();
    const commandEpoch = model.epoch;
    $("add-message").textContent = ""; $("finish-message").textContent = "";
    const body = {request_id: requestId(), action};
    if (game) { body.game_id = game.id; body.revision = game.revision; }
    if (name !== undefined) body.name = name;
    let success = false;
    try {
      const result = await api("/api/command", body);
      if (result.state && commandEpoch === model.epoch) acceptState(result.state);
      success = true;
      $("announcement").textContent = t({start: "started", pause: "pause_done", finish: "saved", add: "added"}[action]);
      if (action === "finish") $("finish-dialog").close();
      if (action === "add") { $("add-dialog").close(); $("game-name").value = ""; $("search").value = ""; renderGames(); }
    } catch (error) {
      if (error.code === "unauthorized") disconnect("unauthorized");
      else if (error.code === "unavailable") markOffline();
      else {
        const key = {conflict: "stale", not_found: "not_found", busy: "busy", recovery: "recovery", storage: "storage"}[error.code] || "invalid";
        setNotice(key);
        if (error.code === "conflict" || error.code === "not_found") { model.connected = false; connection("connecting"); }
      }
      if (action === "add") $("add-message").textContent = errorText(error.code);
      if (action === "finish") $("finish-message").textContent = errorText(error.code);
      if (action === "finish" && error.code === "conflict") $("finish-dialog").close();
    } finally {
      model.mutating = false; model.epoch++; updateControls();
      if (model.token) await syncState();
    }
    return success;
  }
  function showFinish(game) {
    if (!model.connected || model.mutating) return;
    model.finishGame = {...game};
    $("finish-description").textContent = t("confirm_name").replace("{name}", game.name);
    $("finish-time").textContent = clock(elapsed(game)); $("finish-message").textContent = "";
    $("finish-dialog").showModal();
  }

  $("pair-form").addEventListener("submit", event => { event.preventDefault(); pair({code: $("pair-code").value.trim()}); });
  $("pair-code").addEventListener("input", event => { event.target.value = event.target.value.replace(/\D/g, "").slice(0, 6); });
  $("search").addEventListener("input", renderGames);
  $("disconnect").addEventListener("click", async () => {
    if (model.disconnecting || model.mutating) return;
    model.disconnecting = true; updateControls();
    try { if (model.token) await api("/api/disconnect", {}); } catch (_) {}
    finally { disconnect("disconnected_done"); model.disconnecting = false; updateControls(); }
  });
  $("retry-button").addEventListener("click", syncState);
  $("add-button").addEventListener("click", () => { $("add-message").textContent = ""; $("add-dialog").showModal(); $("game-name").focus(); });
  $("add-form").addEventListener("submit", event => { event.preventDefault(); const name = $("game-name").value.trim(); if (name) command("add", null, name); });
  $("finish-confirm").addEventListener("click", () => { if (model.finishGame) command("finish", model.finishGame); });
  document.querySelectorAll(".dialog-cancel").forEach(button => button.addEventListener("click", () => button.closest("dialog").close()));
  for (const dialog of [$("add-dialog"), $("finish-dialog")]) dialog.addEventListener("cancel", event => { if (model.mutating) event.preventDefault(); });
  document.addEventListener("visibilitychange", () => {
    model.connected = false; model.epoch++; updateControls();
    if (!document.hidden && model.token) { connection("connecting"); syncState(); }
  });
  window.addEventListener("online", () => { if (model.token) syncState(); });
  window.addEventListener("offline", markOffline);
  setInterval(() => { if (!document.hidden && model.token && !model.pairing) syncState(); }, 2000);
  setInterval(() => { if (!document.hidden && model.connected) cards.forEach(updateClock); }, 250);

  (async () => {
    applyInfo({language: "pt", theme: "dark"});
    try { applyInfo(await api("/api/info", undefined, false)); } catch (_) {}
    if (secret) await pair({secret});
    else if (model.token) await syncState();
  })();
})();

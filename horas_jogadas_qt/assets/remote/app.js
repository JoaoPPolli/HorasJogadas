"use strict";

(() => {
  // A roda navega pelo conteúdo sem alterar valores dos campos sob o cursor.
  document.addEventListener("wheel",event=>{
    if(event.ctrlKey||event.metaKey||!(event.target instanceof Element))return;
    const control=event.target.closest('select,input[type="number"],input[type="date"],input[type="time"],input[type="datetime-local"],input[type="range"]');
    if(!control)return;
    try{if(control.matches('select:open'))return;}catch(_){}
    event.preventDefault();
    let parent=control.parentElement;
    while(parent&&!(parent.scrollHeight>parent.clientHeight+1&&/(auto|scroll)/.test(getComputedStyle(parent).overflowY)))parent=parent.parentElement;
    const scale=event.deltaMode===1?16:event.deltaMode===2?(parent?.clientHeight||innerHeight):1;
    if(parent)parent.scrollBy({top:event.deltaY*scale,left:event.deltaX*scale,behavior:'instant'});
    else window.scrollBy({top:event.deltaY*scale,left:event.deltaX*scale,behavior:'instant'});
  },{capture:true,passive:false});
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
  Object.assign(copy.pt, {
    remember_device: "Lembrar este celular", device_name: "Nome do aparelho", device_placeholder: "Meu celular", remember_help: "Opcional, por 30 dias neste navegador. Revogue o acesso nas Configurações do PC.", remember_save: "Lembrar aparelho", remembered: "Aparelho lembrado", remember_failed: "O navegador não permitiu salvar o acesso. Você pode continuar usando o código temporário.", easy_return: "VOLTAR FICOU MAIS FÁCIL", remembering: "Reconectando ao seu PC…",
    reconnect_review: "A conexão precisou ser renovada. Confira o contador e toque novamente para enviar a ação; ela não foi repetida automaticamente.",
    playing_now: "Jogando agora", focus_intro: "Aproveite a partida. Seu tempo está sendo contado.", sofa_mode: "Seu jogo, sem distrações.", show_library: "Ver biblioteca", focus_mode: "Jogando agora", choose_session: "Escolher sessão", favorites: "Seus favoritos", favorite: "Favoritar", unfavorite: "Remover dos favoritos", favorited: "Favoritos atualizados.",
    session_ended: "SESSÃO ENCERRADA", summary_empty: "Nenhum tempo acumulado. Nada foi adicionado ao histórico.", summary_zero: "Pronto para a próxima partida.", session_saved: "SESSÃO SALVA", summary_duration: "de uma boa partida.", total_game: "Seu tempo neste jogo", summary_help: "Tudo guardado no histórico do seu PC.", done: "Pronto", more_freedom: "MAIS LIBERDADE", companion_title: "Vai jogar com o PC desligado?", companion_help: "Use o contador offline no celular e transfira suas sessões para o PC quando quiser.", open_companion: "Abrir contador offline ↗", export_library: "Levar minha biblioteca", export_done: "Biblioteca baixada. No contador offline, escolha Importar biblioteca e selecione esse arquivo.",
    shortcut: "Atalho no celular", always_close: "SEMPRE POR PERTO", shortcut_help: "Para este controle local, salve esta página nos favoritos do navegador. Mantenha a mesma rede e ative a conexão no PC para voltar.", install_companion: "Quer um app na tela inicial?", install_help: "Abra o contador offline. No Android, use Instalar app no menu do navegador. No iPhone, use Compartilhar → Adicionar à Tela de Início."
  });
  Object.assign(copy.en, {
    remember_device: "Remember this phone", device_name: "Device name", device_placeholder: "My phone", remember_help: "Optional, for 30 days in this browser. Revoke access in your PC settings.", remember_save: "Remember device", remembered: "Device remembered", remember_failed: "Your browser could not save access. You can continue using the temporary code.", easy_return: "AN EASIER WAY BACK", remembering: "Reconnecting to your PC…",
    reconnect_review: "The connection needed renewal. Check the timer and tap again to send the action; it was not retried automatically.",
    playing_now: "Playing now", focus_intro: "Enjoy your game. Your time is being tracked.", sofa_mode: "Your game, without distractions.", show_library: "Show library", focus_mode: "Playing now", choose_session: "Choose session", favorites: "Your favorites", favorite: "Favorite", unfavorite: "Remove favorite", favorited: "Favorites updated.",
    session_ended: "SESSION ENDED", summary_empty: "No time accumulated. Nothing was added to history.", summary_zero: "Ready for your next game.", session_saved: "SESSION SAVED", summary_duration: "of a good game.", total_game: "Your time in this game", summary_help: "All saved in your PC history.", done: "Done", more_freedom: "MORE FREEDOM", companion_title: "Playing with your PC off?", companion_help: "Use the offline timer on your phone and transfer sessions to your PC when you want.", open_companion: "Open offline timer ↗", export_library: "Take my library", export_done: "Library downloaded. In the offline timer, choose Import library and select this file.",
    shortcut: "Phone shortcut", always_close: "ALWAYS CLOSE BY", shortcut_help: "For this local control, bookmark this page in your browser. Stay on the same network and enable the PC connection to return.", install_companion: "Want an app on your home screen?", install_help: "Open the offline timer. On Android, use Install app in the browser menu. On iPhone, use Share → Add to Home Screen."
  });
  const model = {language: "pt", token: "", state: null, received: 0, connected: false, pairing: false, mutating: false, disconnecting: false, polling: false, epoch: 0, finishGame: null, notice: "", focus: true, focusGame: "", resuming: false, remembered: "", authEpoch: 0, initializing: true};
  const cards = new Map();
  const subscribers = new Set();
  function publishState() { for (const callback of subscribers) callback(model.state, model.connected); document.dispatchEvent(new CustomEvent("horas:state", {bubbles: true})); }
  const t = key => (copy[model.language] || copy.pt)[key] || copy.pt[key] || key;
  const storage = {
    read() { try { return sessionStorage.getItem("horasjogadas-remote") || ""; } catch (_) { return ""; } },
    write(value) { try { if (value) sessionStorage.setItem("horasjogadas-remote", value); else sessionStorage.removeItem("horasjogadas-remote"); } catch (_) {} },
  };
  const rememberedStorage = {
    read() { try { return localStorage.getItem("horasjogadas-remembered") || ""; } catch (_) { return ""; } },
    write(value) { try { if (value) localStorage.setItem("horasjogadas-remembered", value); else localStorage.removeItem("horasjogadas-remembered"); return true; } catch (_) { return false; } },
  };
  model.remembered = rememberedStorage.read();
  try { model.focus = localStorage.getItem("horasjogadas-focus") !== "false"; } catch (_) {}
  const artCache = new Map();
  let artEpoch = 0;
  const artObserver = typeof IntersectionObserver === "function" ? new IntersectionObserver(entries => {
    for (const entry of entries) {
      const card = entry.target.phoneCard;
      if (card) { card.inView = entry.isIntersecting; if (card.inView && model.state) updateArt(card, card.game); }
    }
  }, {rootMargin: "250px 0px"}) : null;
  const secret = new URLSearchParams(location.hash.slice(1)).get("pair");
  if (location.hash || location.search) history.replaceState(null, "", location.pathname);
  // Um favorito ou histórico do leitor de QR pode guardar o fragmento original.
  // O código de cinco minutos não deve apagar a autorização de trinta dias.
  model.token = storage.read();

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
    $("focus-picker").setAttribute("aria-label", t("choose_session"));
    const companion = typeof info.companion_url === "string" && info.companion_url === "https://joaoppolli.github.io/HorasJogadas/celular/" ? info.companion_url : "https://joaoppolli.github.io/HorasJogadas/celular/";
    $("companion-link").href = companion;
    document.querySelectorAll("a.companion-link").forEach(link => { link.href = companion; });
    $("remember-button").textContent = t(model.remembered ? "remembered" : "remember_device");
    $("remember-button").disabled = Boolean(model.remembered);
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
    const fileOperation = body && (typeof body.data === "string" && body.data.length > 65536
      || ["backup_create", "backup_restore", "backup_restore_local", "legacy_restore", "phone_import", "pc_create_review"].includes(body.action)
      || ["backup_restore_preview", "phone_import_preview", "completion_import"].includes(body.query));
    const timer = setTimeout(() => controller.abort(), fileOperation ? 120000 : 8000);
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
    model.authEpoch++; model.token = ""; storage.write(""); rememberedStorage.write(""); model.remembered = ""; clearArt(); document.body.classList.remove("is-focused"); model.connected = false; model.state = null; model.finishGame = null; model.epoch++;
    cards.forEach(card => { if (artObserver) artObserver.unobserve(card.element); card.element.remove(); }); cards.clear();
    for (const dialog of document.querySelectorAll("dialog")) if (dialog.open) dialog.close();
    $("control-view").hidden = true; $("pair-view").hidden = false; $("pair-footer").hidden = false;
    $("pair-message").textContent = message ? t(message) : ""; $("pair-code").value = "";
    connection("waiting"); publishState();
  }

  async function pair(body) {
    if (model.pairing) return;
    const authEpoch = ++model.authEpoch;
    model.pairing = true; $("pair-button").disabled = true; $("pair-button").textContent = t("connecting"); $("pair-message").textContent = ""; connection("connecting");
    try {
      const result = await api("/api/pair", body, false);
      if (typeof result.token !== "string" || !result.token) throw apiError("unavailable");
      if (authEpoch !== model.authEpoch || model.disconnecting) return;
      if (model.token !== result.token) clearArt();
      model.token = result.token; storage.write(model.token);
      if (result.remember_token) rememberCredential(result.remember_token);
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
    updateControls(); publishState();
  }
  function acceptState(state) {
    if (!Array.isArray(state.games)) throw apiError("unavailable");
    model.state = state; model.received = performance.now(); model.connected = true;
    applyInfo(state);
    $("pair-view").hidden = true; $("pair-footer").hidden = true; $("control-view").hidden = false;
    connection("connected");
    if (state.pending_recovery) setNotice("recovery");
    else if (model.notice === "offline" || model.notice === "recovery") setNotice("");
    renderGames(); publishState();
  }
  async function syncState() {
    if (!model.token || model.polling || model.resuming || model.mutating || model.disconnecting) return;
    model.polling = true;
    const epoch = model.epoch;
    try {
      const result = await api("/api/state");
      if (epoch === model.epoch) acceptState(result);
    } catch (error) {
      if (epoch !== model.epoch) return;
      if (error.code === "unauthorized") {
        model.token = ""; storage.write("");
        if (model.remembered) return await resumeRemembered();
        disconnect("unauthorized");
        return {rejected: true, authEpoch: model.authEpoch};
      }
      else markOffline();
    } finally { model.polling = false; }
  }

  function rememberCredential(value) {
    if (typeof value !== "string" || !value) return false;
    if (!rememberedStorage.write(value)) { setNotice("remember_failed"); return false; }
    model.remembered = value;
    $("remember-button").textContent = t("remembered"); $("remember-button").disabled = true;
    return true;
  }
  async function resumeRemembered() {
    if (!model.remembered || model.resuming || model.disconnecting) return;
    const authEpoch = model.authEpoch, credential = model.remembered;
    let authorized = false;
    model.resuming = true; model.connected = false; model.epoch++; updateControls(); connection("connecting");
    try {
      const result = await api("/api/resume", {remember_token: credential}, false);
      if (!result.token || typeof result.token !== "string") throw apiError("unavailable");
      if (authEpoch !== model.authEpoch || credential !== model.remembered || model.disconnecting) return;
      authorized = true;
      if (model.token !== result.token) clearArt();
      model.token = result.token; storage.write(result.token);
      const stateEpoch = model.epoch;
      const state = await api("/api/state");
      if (authEpoch === model.authEpoch && stateEpoch === model.epoch && !model.disconnecting && !document.hidden) acceptState(state);
    } catch (error) {
      if (authEpoch !== model.authEpoch || credential !== model.remembered || model.disconnecting) return;
      if (error.code === "unauthorized" && !authorized) {
        disconnect("unauthorized");
        return {rejected: true, authEpoch: model.authEpoch};
      }
      // Uma falha no estado após o resume não revoga o aparelho lembrado.
      if (error.code === "unauthorized") { model.token = ""; storage.write(""); }
      markOffline(); $("pair-message").textContent = t("unavailable");
    } finally { model.resuming = false; }
  }
  function clearArt() {
    artEpoch++;
    for (const entry of artCache.values()) if (entry.blob) URL.revokeObjectURL(entry.blob);
    artCache.clear();
    cards.forEach(card => { for (const image of [card.avatarImage, card.cover]) { image.hidden = true; image.removeAttribute("src"); } });
  }
  function allowedArt(path, kind, id) {
    if (typeof path !== "string" || typeof id !== "string" || !/^[A-Za-z0-9_-]{1,100}$/.test(id)) return false;
    const expected = "/api/art/" + kind + "/" + id;
    return path === expected || path.startsWith(expected + "?v=") && /^\?v=[a-f0-9]{64}$/.test(path.slice(expected.length));
  }
  function imageFor(image, path, kind, id) {
    if (!allowedArt(path, kind, id)) { image.removeAttribute("src"); image.hidden = true; return; }
    const entry = artCache.get(path);
    if (entry && entry.failedAt && model.connected && performance.now() - entry.failedAt > 5000) { artCache.delete(path); imageFor(image, path, kind, id); return; }
    if (entry) {
      entry.used = performance.now();
      if (entry.blob && image.dataset.path === path) { image.src = entry.blob; image.hidden = false; }
      else if (!entry.blob) image.hidden = true;
      return;
    }
    image.hidden = true;
    if (!model.connected) return;
    const generation = artEpoch;
    const token = model.token;
    const created = {blob: "", used: performance.now()};
    artCache.set(path, created);
    const abort = new AbortController(); const timeout = setTimeout(() => abort.abort(), 8000);
    fetch(path, {headers: {Authorization: "Bearer " + token}, cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer", signal: abort.signal})
      .then(async response => {
        if (!response.ok || !["image/jpeg", "image/png"].includes((response.headers.get("Content-Type") || "").split(";")[0])) throw new Error("image");
        const content = await response.blob();
        if (content.size > 10 * 1024 * 1024 || generation !== artEpoch || token !== model.token || artCache.get(path) !== created) return;
        created.blob = URL.createObjectURL(content);
        if (image.dataset.path === path) { image.src = created.blob; image.hidden = false; }
      }).catch(() => { created.failedAt = performance.now(); }).finally(() => clearTimeout(timeout));
  }
  function updateArt(card, game) {
    const iconPath = model.state.icons_enabled !== false ? game.art && game.art.icon : null;
    const coverPath = model.state.covers_enabled === true ? game.art && game.art.cover : null;
    card.avatarImage.dataset.path = iconPath || "";
    if (!iconPath || card.inView || artCache.has(iconPath)) imageFor(card.avatarImage, iconPath, "icon", game.id);
    card.cover.dataset.path = coverPath || "";
    if (!coverPath || card.inView || artCache.has(coverPath)) imageFor(card.cover, coverPath, "cover", game.id);
    card.coverFrame.hidden = !allowedArt(coverPath, "cover", game.id);
  }
  function trimArt(games) {
    const wanted = new Set();
    for (const game of games) {
      if (model.state.icons_enabled !== false && game.art && game.art.icon) wanted.add(game.art.icon);
      if (model.state.covers_enabled === true && game.art && game.art.cover) wanted.add(game.art.cover);
    }
    for (const [key, entry] of artCache) if (!wanted.has(key)) { if (entry.blob) URL.revokeObjectURL(entry.blob); artCache.delete(key); }
    const oldest = [...artCache.entries()].sort((a, b) => a[1].used - b[1].used);
    while (artCache.size > 160 && oldest.length) { const [key, entry] = oldest.shift(); if (entry.blob) URL.revokeObjectURL(entry.blob); artCache.delete(key); }
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
    const card = {element: node("article", "game-card"), game, inView: !artObserver};
    card.element.phoneCard = card;
    if (artObserver) artObserver.observe(card.element);
    card.coverFrame = node("div", "cover-frame"); card.coverFrame.hidden = true;
    card.cover = node("img", "card-cover"); card.cover.alt = ""; card.cover.hidden = true;
    card.coverFrame.append(card.cover);
    const head = node("div", "game-head"), identity = node("div", "game-identity");
    card.avatar = node("div", "avatar"); card.avatar.setAttribute("aria-hidden", "true");
    card.avatarLetters = node("span"); card.avatarImage = node("img"); card.avatarImage.alt = ""; card.avatarImage.hidden = true; card.avatar.append(card.avatarLetters, card.avatarImage);
    card.name = node("h3", "game-name"); card.status = node("span", "game-status"); identity.append(card.name, card.status);
    card.favorite = node("button", "favorite-button"); card.favorite.type = "button"; card.favorite.textContent = "☆";
    card.favorite.addEventListener("click", () => command("favorite", card.game, undefined, {enabled: !card.game.favorite}));
    card.more = node("button", "game-menu-button"); card.more.type = "button"; card.more.textContent = "⋯";
    card.more.addEventListener("click", () => { if (window.HorasDesktop) window.HorasDesktop.gameMenu(card.game); });
    head.append(card.avatar, identity, card.favorite, card.more);
    card.session = node("div", "session-label"); card.elapsed = node("div", "elapsed"); card.elapsed.setAttribute("aria-live", "off");
    card.activity = node("div", "activity"); card.activity.append(node("i")); card.activityText = node("span"); card.activity.append(card.activityText);
    card.total = node("p", "total");
    const actions = node("div", "card-actions");
    card.start = node("button", "start-button primary"); card.start.type = "button"; card.start.append(icon("play")); card.startText = node("span"); card.start.append(card.startText);
    card.pause = node("button", "icon-button"); card.pause.type = "button"; card.pause.append(icon("pause"));
    card.finish = node("button", "icon-button stop-button"); card.finish.type = "button"; card.finish.append(icon("stop"));
    card.start.addEventListener("click", () => command("start", card.game)); card.pause.addEventListener("click", () => command("pause", card.game)); card.finish.addEventListener("click", () => showFinish(card.game));
    actions.append(card.start, card.pause, card.finish); card.element.append(card.coverFrame, head, card.session, card.elapsed, card.activity, card.total, actions);
    return card;
  }
  function updateCard(card, game) {
    card.game = game;
    card.element.className = "game-card" + (game.running ? " running" : game.pending ? " paused" : "");
    card.name.textContent = game.name; card.name.title = game.name; card.avatarLetters.textContent = initials(game.name);
    card.favorite.textContent = game.favorite ? "★" : "☆";
    card.favorite.classList.toggle("is-favorite", Boolean(game.favorite));
    card.favorite.setAttribute("aria-label", t(game.favorite ? "unfavorite" : "favorite") + " · " + game.name);
    card.favorite.setAttribute("aria-pressed", String(Boolean(game.favorite)));
    card.more.setAttribute("aria-label", (model.language === "en" ? "Game actions" : "Ações do jogo") + " · " + game.name);
    updateArt(card, game);
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
    card.finish.disabled = blocked || !card.game.pending; card.favorite.disabled = blocked; card.more.disabled = blocked;
  }
  function updateControls() {
    cards.forEach(updateCardControls);
    const blocked = !model.connected || model.mutating || model.disconnecting || Boolean(model.state && model.state.pending_recovery);
    $("add-button").disabled = blocked; $("add-confirm").disabled = blocked; $("finish-confirm").disabled = blocked;
    $("disconnect").disabled = model.mutating || model.disconnecting;
    $("export-library").disabled = blocked; $("remember-confirm").disabled = blocked;
    $("remember-button").disabled = Boolean(model.remembered) || blocked;
    document.querySelectorAll(".dialog-cancel").forEach(button => { button.disabled = model.mutating; });
    document.dispatchEvent(new CustomEvent("horas:connection", {bubbles: true}));
  }
  function renderGames() {
    if (!model.state) return;
    const games = window.HorasDesktop ? window.HorasDesktop.filterGames(model.state.games) : model.state.games;
    trimArt(model.state.games);
    const ids = new Set(games.map(game => game.id));
    for (const [id, card] of cards) if (!ids.has(id)) { if (artObserver) artObserver.unobserve(card.element); card.element.remove(); cards.delete(id); }
    const query = normalize($("search").value.trim());
    const active = [], favorites = [], other = [];
    for (const game of games) {
      let card = cards.get(game.id);
      if (!card) { card = gameCard(game); cards.set(game.id, card); }
      updateCard(card, game);
      if (game.pending) active.push(card); else if (game.favorite) favorites.push(card); else other.push(card);
      card.element.hidden = Boolean(query && !normalize(game.name).includes(query));
    }
    if (!active.some(card => card.game.id === model.focusGame)) model.focusGame = active.length ? active[0].game.id : "";
    const focused = model.focus && active.length > 0 && !query;
    $("control-view").classList.toggle("focus-mode", focused); document.body.classList.toggle("is-focused", focused && (!window.HorasDesktop || window.HorasDesktop.getPage() === "library"));
    $("mode-toolbar").hidden = !active.length;
    $("focus-toggle").textContent = t(focused ? "show_library" : "focus_mode");
    $("focus-toggle").setAttribute("aria-pressed", String(focused));
    $("library-title").textContent = t(focused ? "playing_now" : "library");
    document.querySelector(".page-heading p").textContent = t(focused ? "focus_intro" : "library_intro");
    $("add-button").hidden = focused;
    $("active-heading").textContent = t(focused ? "session" : "in_session");
    const picker = $("focus-picker");
    const options = JSON.stringify(active.map(card => [card.game.id, card.game.name]));
    if (picker.dataset.options !== options) {
      picker.replaceChildren(...active.map(card => { const option = document.createElement("option"); option.value = card.game.id; option.textContent = card.game.name; return option; }));
      picker.dataset.options = options;
    }
    picker.value = model.focusGame; picker.hidden = !focused || active.length < 2;
    for (const card of active) {
      const selected = focused && card.game.id === model.focusGame;
      card.element.classList.toggle("focus-game", selected);
      if (focused) card.element.hidden = !selected;
    }
    function place(parent, values) { values.forEach((card, index) => { if (parent.children[index] !== card.element) parent.insertBefore(card.element, parent.children[index] || null); }); }
    place($("active-games"), active); place($("favorite-games"), favorites); place($("library-games"), other);
    const visibleActive = active.filter(card => !card.element.hidden).length;
    const visibleFavorite = favorites.filter(card => !card.element.hidden).length;
    const visibleOther = other.filter(card => !card.element.hidden).length;
    $("active-section").hidden = !visibleActive;
    $("active-count").textContent = String(active.length);
    $("favorite-section").hidden = focused || !visibleFavorite;
    $("favorite-count").textContent = String(favorites.length);
    $("library-section").hidden = focused;
    $("games-heading").textContent = t(active.length || favorites.length ? "other_games" : "all_games");
    $("game-count").textContent = String(other.length);
    $("empty").hidden = focused || Boolean(visibleActive || visibleFavorite || visibleOther);
    $("empty-title").textContent = t(games.length ? "nothing" : "no_games");
    $("empty-description").textContent = t(games.length ? "nothing_hint" : "no_games_hint");
    updateControls();
  }

  function requestId() {
    const values = new Uint32Array(4); crypto.getRandomValues(values);
    return Array.from(values, n => n.toString(16).padStart(8, "0")).join("");
  }
  async function command(action, game, name, extra = {}) {
    if (!model.connected || model.mutating || model.disconnecting) return;
    model.mutating = true; model.epoch++; updateControls();
    const commandEpoch = model.epoch;
    $("add-message").textContent = ""; $("finish-message").textContent = "";
    const body = {request_id: requestId(), action, ...extra};
    if (game) { body.game_id = game.id; body.revision = game.revision; }
    if (name !== undefined) body.name = name;
    let success = false, recoverAuth = false;
    try {
      const result = await api("/api/command", body);
      if (["stale", "not_found", "invalid", "storage", "busy", "rate_limited", "reconnect_review"].includes(model.notice)) setNotice("");
      if (result.state && commandEpoch === model.epoch) acceptState(result.state);
      success = true;
      $("announcement").textContent = t({start: "started", pause: "pause_done", finish: "saved", add: "added", favorite: "favorited"}[action]);
      if (action === "start") { model.focusGame = game.id; if (model.focus) $("search").value = ""; renderGames(); }
      if (action === "finish") {
        $("finish-dialog").close();
        const summary = result.summary;
        if (summary && typeof summary.game === "string") {
          const saved = Number(summary.seconds) > 0;
          for (const [id, key] of [["summary-eyebrow", saved ? "session_saved" : "session_ended"], ["summary-help", saved ? "summary_help" : "summary_empty"], ["summary-duration-label", saved ? "summary_duration" : "summary_zero"]]) { $(id).dataset.text = key; $(id).textContent = t(key); }
          $("summary-title").textContent = summary.game; $("summary-time").textContent = clock(summary.seconds);
          $("summary-total").textContent = duration(summary.total_seconds); $("summary-dialog").showModal();
        }
      }
      if (action === "add") { $("add-dialog").close(); $("game-name").value = ""; $("search").value = ""; renderGames(); }
    } catch (error) {
      if (error.code === "unauthorized") { recoverAuth = true; markOffline(); }
      else if (error.code === "unavailable") markOffline();
      else {
        const key = {conflict: "stale", not_found: "not_found", busy: "busy", recovery: "recovery", storage: "storage"}[error.code] || "invalid";
        setNotice(key);
        if (error.code === "conflict" || error.code === "not_found") { model.connected = false; connection("connecting"); }
      }
      if (action === "add") $("add-message").textContent = recoverAuth ? t("reconnect_review") : errorText(error.code);
      if (action === "finish") $("finish-message").textContent = recoverAuth ? t("reconnect_review") : errorText(error.code);
      if (action === "finish" && error.code === "conflict") $("finish-dialog").close();
    } finally {
      model.mutating = false; model.epoch++; updateControls();
      if (recoverAuth) {
        model.token = ""; storage.write("");
        if (model.remembered) await resumeRemembered();
        else disconnect("unauthorized");
        if (model.connected) setNotice("reconnect_review");
      } else if (model.token) await syncState();
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

  $("pair-form").addEventListener("submit", event => { event.preventDefault(); pair({code: $("pair-code").value.trim(), remember: $("remember-device").checked, device_name: $("device-name").value.trim() || t("device_placeholder")}); });
  $("remember-device").addEventListener("change", () => { $("device-name-field").hidden = !$("remember-device").checked; });
  $("focus-toggle").addEventListener("click", () => { model.focus = !$("control-view").classList.contains("focus-mode"); $("search").value = ""; try { localStorage.setItem("horasjogadas-focus", String(model.focus)); } catch (_) {} renderGames(); });
  $("focus-picker").addEventListener("change", event => { model.focusGame = event.target.value; renderGames(); });
  $("summary-close").addEventListener("click", () => $("summary-dialog").close());
  $("shortcut-button").addEventListener("click", () => $("shortcut-dialog").showModal());
  $("remember-button").addEventListener("click", () => { $("remember-message").textContent = ""; $("remember-dialog").showModal(); $("remember-name").focus(); });
  $("remember-form").addEventListener("submit", async event => {
    event.preventDefault(); if (!model.connected || model.mutating) return;
    $("remember-confirm").disabled = true;
    try {
      const result = await api("/api/remember", {device_name: $("remember-name").value.trim() || t("device_placeholder")});
      if (rememberCredential(result.remember_token)) $("remember-dialog").close();
      else $("remember-message").textContent = t("remember_failed");
    } catch (error) { $("remember-message").textContent = errorText(error.code); }
    finally { updateControls(); }
  });
  $("export-library").addEventListener("click", async () => {
    $("export-library").disabled = true; $("export-message").textContent = "";
    try {
      const library = await api("/api/library");
      const url = URL.createObjectURL(new Blob([JSON.stringify(library, null, 2)], {type: "application/json"}));
      const link = document.createElement("a"); link.href = url; link.download = "HorasJogadas-biblioteca.json"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000); $("export-message").textContent = t("export_done");
    } catch (error) { $("export-message").textContent = errorText(error.code); }
    finally { updateControls(); }
  });
  $("pair-code").addEventListener("input", event => { event.target.value = event.target.value.replace(/\D/g, "").slice(0, 6); });
  $("search").addEventListener("input", renderGames);
  $("disconnect").addEventListener("click", async () => {
    if (model.disconnecting || model.mutating) return;
    model.authEpoch++; model.disconnecting = true; updateControls();
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
    if (!document.hidden && !model.initializing) {
      connection("connecting");
      if (model.token) syncState(); else if (model.remembered) resumeRemembered();
    }
  });
  window.addEventListener("online", () => { if (!model.initializing) { if (model.token) syncState(); else if (model.remembered) resumeRemembered(); } });
  window.addEventListener("offline", markOffline);
  setInterval(() => { if (!document.hidden && !model.initializing && !model.pairing && !model.resuming) { if (model.token) syncState(); else if (model.remembered && !$("pair-code").value) resumeRemembered(); } }, 2000);
  setInterval(() => { if (!document.hidden && model.connected) cards.forEach(updateClock); }, 250);

  async function commandRaw(body) {
    if (!model.connected || model.mutating || model.disconnecting) throw apiError("unavailable");
    model.mutating = true; model.epoch++; updateControls();
    const epoch = model.epoch;
    let recoverAuth = false;
    try {
      const result = await api("/api/command", {request_id: requestId(), workspace_revision: model.state && model.state.workspace_revision, ...body});
      if (result.state && epoch === model.epoch) acceptState(result.state);
      return result;
    } catch (error) {
      if (error.code === "unauthorized") { recoverAuth = true; markOffline(); }
      else if (error.code === "unavailable") markOffline();
      throw error;
    } finally {
      model.mutating = false; model.epoch++; updateControls();
      if (recoverAuth) {
        model.token = ""; storage.write("");
        if (model.remembered) await resumeRemembered(); else disconnect("unauthorized");
        if (model.connected) setNotice("reconnect_review");
      } else if (model.token) await syncState();
    }
  }
  async function download(path, filename) {
    if (!model.token) throw apiError("unauthorized");
    const response = await fetch(path, {headers: {Authorization: "Bearer " + model.token}, cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer"});
    if (!response.ok) throw apiError("unavailable");
    const url = URL.createObjectURL(await response.blob());
    const link = node("a"); link.href = url; link.download = filename; link.hidden = true;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  window.HorasPhone = {api, commandRaw, getState: () => model.state, connected: () => model.connected, ready: () => model.connected && !model.mutating && !model.disconnecting,
    language: () => model.language, errorText, clock, duration, refresh: syncState, renderGames, download,
    subscribe(callback) { subscribers.add(callback); if (model.state) callback(model.state, model.connected); return () => subscribers.delete(callback); }};

  (async () => {
    applyInfo({language: "pt", theme: "dark"});
    try { applyInfo(await api("/api/info", undefined, false)); } catch (_) {}
    try {
      const authEpoch = model.authEpoch;
      let result;
      if (model.token) result = await syncState();
      else if (model.remembered) result = await resumeRemembered();
      if (secret && !model.token && !model.remembered && !model.disconnecting
          && (result && result.rejected ? result.authEpoch === model.authEpoch : authEpoch === model.authEpoch)) await pair({secret});
    } finally { model.initializing = false; }
  })();
})();

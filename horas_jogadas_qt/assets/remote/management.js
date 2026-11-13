"use strict";

(() => {
  const words = {
    pt: {
      appearance:"Seu app, do seu jeito", appearance_help:"Estas preferências também são aplicadas no aplicativo do PC.", theme:"Aparência",language:"Idioma",dark:"Escuro minimalista",original:"Original · cinza e roxo",violet:"Violeta",light:"Claro",auto_updates:"Verificar atualizações ao abrir o app",covers:"Exibir capas na biblioteca",icons:"Exibir ícones dos jogos",save:"Salvar preferências",saved:"Preferências salvas.",backups:"Seus dados, protegidos",backup_help:"Crie uma cópia completa com registros e imagens. Restaurar substitui os dados atuais e cria uma cópia preventiva.",create_backup:"Criar backup no PC",download_backup:"Baixar backup completo",restore_file:"Restaurar arquivo de backup",saved_backups:"Backups guardados no PC",legacy_backups:"Backups antigos de registros",restore:"Restaurar",download:"Baixar",empty_backups:"Ainda não há backups nesta lista.",backup_created:"Backup criado no computador.",refresh:"Atualizar",created:"Criado",files:"arquivos",games:"jogos",sessions:"sessões",completions:"zerados",artwork:"Capas e ícones",art_help:"Busque em lote, confira a imagem e importe. Só os títulos escolhidos são enviados às fontes de busca.",manage_covers:"Gerenciar capas",manage_icons:"Gerenciar ícones",cover:"Capa",icon:"Ícone",source:"Fonte de busca",all_sources:"Todas as fontes",search:"Buscar selecionados",select_all:"Marcar / desmarcar todos",searching:"Buscando sugestões…",search_title:"Título para a busca",choose:"Escolha um resultado…",local:"Imagem local",remove:"Remover imagem",preview:"Ver prévia",import_selected:"Importar selecionadas",imported:"Imagens importadas.",image_removed:"Imagem removida.",local_saved:"Imagem salva no PC.",no_results:"Nenhuma sugestão disponível. Ajuste o título ou escolha uma imagem local.",select_images:"Selecione pelo menos um resultado.",view_source:"Abrir fonte ↗",cancel:"Cancelar",close:"Fechar",confirm:"Confirmar",continue:"Continuar",working:"Trabalhando…",done:"Concluído.",failed:"Não foi possível concluir. Confira a conexão e tente novamente.",invalid:"Confira os dados e tente novamente.",file_too_large:"Esse arquivo é muito grande. Escolha um arquivo de até 8 MB.",file_limit:"Limite do envio pelo celular: 8 MB.",restore_title:"Restaurar estes dados?",restore_help:"Os dados atuais serão substituídos. Uma cópia preventiva será criada antes da alteração.",pending:"Cronômetros em andamento",pending_choice:"O que fazer com as sessões abertas no PC?",pending_save:"Salvar no histórico antes de restaurar",pending_discard:"Descartar as sessões abertas",recovery:"Sessões abertas presentes no backup",recovery_save:"Recuperar no histórico",recovery_discard:"Descartar as sessões pendentes do backup",restore_done:"Backup restaurado. Os dados foram atualizados.",phone_import:"Sessões feitas no celular",phone_help:"Leve suas partidas do contador independente para o histórico do PC, conferindo tudo antes de salvar.",import_phone:"Importar arquivo de sessões",phone_review:"Confira suas sessões",phone_review_help:"Escolha quais partidas importar e os jogos de destino. Os registros já importados não serão duplicados.",new_game:"Criar novo jogo",already_imported:"Já importada",import_sessions:"Importar selecionadas",phone_done:"Sessões importadas.",devices:"Aparelhos conectados",devices_help:"Aparelhos lembrados podem reconectar enquanto a conexão do PC estiver ativa.",revoke:"Remover acesso",revoke_all:"Desconectar todos",revoke_help:"Este aparelho precisará parear novamente se você remover o acesso dele.",expires:"Válido até",empty_devices:"Nenhum aparelho lembrado.",updates:"Sempre em dia",updates_help:"A atualização é feita no computador. Seus registros continuam separados da instalação.",current_version:"Versão atual",check_updates:"Verificar atualizações",download_update:"Baixar atualização",install_update:"Instalar e reiniciar o PC app",up_to_date:"Você está na versão mais recente.",available:"Nova versão disponível",update_ready:"Download concluído e pronto para instalar.",update_install_title:"Atualizar o aplicativo do PC?",update_install_help:"O app vai fechar e reiniciar. O controle perderá a conexão; ative-o novamente no PC depois da atualização.",install:"Instalar e reiniciar",installing:"Atualização iniciada no PC. Ative o controle novamente quando o app reabrir.",cancel_job:"Cancelar tarefa",cancelled:"Tarefa cancelada.",desktop:"No computador",desktop_help:"Estas ações abrem uma pasta ou preparam uma cópia no próprio PC.",open_data:"Abrir pasta de dados no PC",review_copy:"Criar cópia para testar no PC",desktop_done:"Ação enviada ao computador.",device_removed:"Acesso removido.",confirmed:"Conferi os dados e quero restaurar",notes:"Observações",no_time:"Sem tempo",selected:"selecionadas",search_again:"Buscar este título",file_loading:"Preparando arquivo…",image_failed:"Não foi possível carregar a prévia.",remembered:"Aparelho lembrado",read_only:"Conecte ao PC para usar estas opções.",import_backup:"Escolher arquivo ZIP",update_progress:"Baixando atualização…",restore_backup:"Backup completo",source_games:"Jogos no PC",name:"Nome",finish_pending:"Confira as sessões antes de continuar."
    },
    en: {
      appearance:"Your app, your way",appearance_help:"These preferences also apply to the PC application.",theme:"Appearance",language:"Language",dark:"Minimal dark",original:"Original · gray and purple",violet:"Violet",light:"Light",auto_updates:"Check for updates when the app opens",covers:"Show library covers",icons:"Show game icons",save:"Save preferences",saved:"Preferences saved.",backups:"Your data, protected",backup_help:"Create a full copy of records and images. Restoring replaces current data and creates a safety copy first.",create_backup:"Create backup on PC",download_backup:"Download full backup",restore_file:"Restore backup file",saved_backups:"Backups saved on PC",legacy_backups:"Older record backups",restore:"Restore",download:"Download",empty_backups:"There are no backups in this list yet.",backup_created:"Backup created on your computer.",refresh:"Refresh",created:"Created",files:"files",games:"games",sessions:"sessions",completions:"completions",artwork:"Covers and icons",art_help:"Search in bulk, check the artwork and import. Only selected game titles are sent to search providers.",manage_covers:"Manage covers",manage_icons:"Manage icons",cover:"Cover",icon:"Icon",source:"Search source",all_sources:"All sources",search:"Search selected",select_all:"Check / uncheck all",searching:"Finding suggestions…",search_title:"Search title",choose:"Choose a result…",local:"Local image",remove:"Remove image",preview:"Preview",import_selected:"Import selected",imported:"Artwork imported.",image_removed:"Image removed.",local_saved:"Image saved on PC.",no_results:"No suggestions available. Edit the title or choose a local image.",select_images:"Select at least one result.",view_source:"Open source ↗",cancel:"Cancel",close:"Close",confirm:"Confirm",continue:"Continue",working:"Working…",done:"Done.",failed:"Could not complete. Check the connection and try again.",invalid:"Check the details and try again.",file_too_large:"This file is too large. Choose a file up to 8 MB.",file_limit:"Phone upload limit: 8 MB.",restore_title:"Restore these records?",restore_help:"Current records will be replaced. A safety copy will be created first.",pending:"Timers in progress",pending_choice:"What should happen to sessions open on your PC?",pending_save:"Save to history before restoring",pending_discard:"Discard open sessions",recovery:"Open sessions in the backup",recovery_save:"Recover to history",recovery_discard:"Discard pending sessions from backup",restore_done:"Backup restored. Records have been refreshed.",phone_import:"Sessions played on your phone",phone_help:"Bring sessions from the independent timer to your PC history, reviewing everything before saving.",import_phone:"Import session file",phone_review:"Review your sessions",phone_review_help:"Choose sessions and destination games. Previously imported records will not be duplicated.",new_game:"Create new game",already_imported:"Already imported",import_sessions:"Import selected",phone_done:"Sessions imported.",devices:"Connected devices",devices_help:"Remembered devices can reconnect while your PC connection is active.",revoke:"Remove access",revoke_all:"Disconnect all",revoke_help:"This device will need to pair again if you remove its access.",expires:"Valid until",empty_devices:"No remembered devices.",updates:"Keep up to date",updates_help:"Updates are installed on the computer. Records remain separate from the application.",current_version:"Current version",check_updates:"Check for updates",download_update:"Download update",install_update:"Update and restart PC app",up_to_date:"You have the latest version.",available:"New version available",update_ready:"Download complete and ready to install.",update_install_title:"Update your PC application?",update_install_help:"The app will close and restart. The control will disconnect; enable it again on your PC after updating.",install:"Install and restart",installing:"Update started on PC. Enable phone control again when the app reopens.",cancel_job:"Cancel task",cancelled:"Task cancelled.",desktop:"On your computer",desktop_help:"These actions open a folder or prepare a copy on the PC itself.",open_data:"Open PC data folder",review_copy:"Create test copy on PC",desktop_done:"Action sent to your computer.",device_removed:"Access removed.",confirmed:"I reviewed the data and want to restore it",notes:"Notes",no_time:"No time",selected:"selected",search_again:"Search this title",file_loading:"Preparing file…",image_failed:"Could not load artwork preview.",remembered:"Remembered device",read_only:"Connect to your PC to use these options.",import_backup:"Choose ZIP file",update_progress:"Downloading update…",restore_backup:"Full backup",source_games:"PC games",name:"Name",finish_pending:"Review your sessions before continuing."
    }
  };
  Object.assign(words.pt, {settings:"Configurações",settings_intro:"Tudo no seu lugar, no celular e no computador.",reload:"Recarregar",stale_form:"Os dados mudaram no PC ou em outro aparelho. Recarregue as preferências, ou feche e abra esta janela para conferir antes de salvar.",official_package:"A instalação de atualizações está disponível no pacote oficial. Esta cópia está sendo executada pelo código-fonte.",recover_title:"Sessão pendente no PC",recover_help:"Resolva a sessão recuperável antes de alterar os registros. Escolha salvar o tempo recuperado ou descartá-lo.",recover_save:"Salvar sessão recuperada",recover_discard:"Descartar sessão pendente",zip_limit:"Envie um backup ZIP de até 32 MB.",image_limit:"Escolha uma imagem de até 10 MB.",session_limit:"Escolha um arquivo de sessões de até 1 MB."});
  Object.assign(words.en, {settings:"Settings",settings_intro:"Everything in place, on your phone and computer.",reload:"Reload",stale_form:"Records changed on your PC or another device. Reload preferences, or close and reopen this dialog to review before saving.",official_package:"Installing updates is available in the official package. This copy is running from source.",recover_title:"Pending PC session",recover_help:"Resolve the recoverable session before changing records. Choose to save recovered time or discard it.",recover_save:"Save recovered session",recover_discard:"Discard pending session",zip_limit:"Upload a backup ZIP up to 32 MB.",image_limit:"Choose an image up to 10 MB.",session_limit:"Choose a session file up to 1 MB."});
  Object.assign(words.pt,{disable_control:"Desativar controle no PC",disable_control_help:"A conexão de todos os celulares será fechada. Os cronômetros continuam funcionando e os aparelhos lembrados ficam preservados. Para conectar novamente, será preciso ativar o controle nas Configurações do PC.",control_disabled:"Conexão encerrada. Ative o controle no PC quando quiser voltar."});
  Object.assign(words.en,{disable_control:"Disable PC phone control",disable_control_help:"All phone connections will close. Timers keep running and remembered devices are preserved. To reconnect, enable phone control again in the PC settings.",control_disabled:"Connection closed. Enable phone control on your PC when you want to return."});
  Object.assign(words.pt,{startup_login:"Abrir HorasJogadas ao entrar no computador",startup_phone:"Ativar controle pelo celular ao abrir o app"});
  Object.assign(words.en,{startup_login:"Open HorasJogadas when signing in",startup_phone:"Enable phone control when opening the app"});
  Object.assign(words.pt,{detect_global:"Ativar detecção dos jogos vinculados no PC"});Object.assign(words.en,{detect_global:"Enable detection for PC-linked games"});
  const $ = id => document.getElementById(id);
  const H = () => window.HorasPhone;
  const t = key => words[H() && H().language() === "en" ? "en" : "pt"][key] || key;
  const state = {host: null, revision: "", language: "", dirty: false, editSerial:0, loading: false, epoch: 0, dialogs: new Set(), jobs: new Map(), notices: new Map()};
  const e = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = String(text); return n; };
  function button(text, fn, cls = "") { const b = e("button", cls, text); b.type = "button"; b.addEventListener("click", fn); return b; }
  function message(node, text = "", error = false) { node.textContent = text; node.classList.toggle("error", error); }
  function errorText(error) { return error && error.code === "conflict" ? t("stale_form") : error && words.pt[error.code] ? t(error.code) : H().errorText(error && error.code) || t("failed"); }
  function controls() { if (!state.host) return; const ready = H().ready ? H().ready() : H().connected(); for (const host of [state.host, ...state.dialogs]) host.querySelectorAll("button,input,select,textarea").forEach(n => { if (!n.dataset.keepEnabled && n.dataset.permanentDisabled !== "true") n.disabled = n.dataset.localCancel ? host.dataset.busy === "true" : !ready || n.dataset.busy === "true" || host.dataset.busy === "true" && !n.dataset.jobCancel; }); }
  async function busy(b, notice, fn) { if (b.dataset.busy === "true") return; const d = b.closest("dialog"); b.dataset.busy = "true"; if (d) d.dataset.busy = "true"; controls(); message(notice, t("working")); try { return await fn(); } catch (error) { message(notice, errorText(error), true); } finally { b.dataset.busy = "false"; if (d) d.dataset.busy = "false"; controls(); } }
  async function action(name, payload = {}) { const result = await H().commandRaw({action: name, ...payload}); return result; }
  async function query(body) { return H().api("/api/query", body); }
  async function view(page, params = {}) { const queryString = new URLSearchParams(params).toString(); return H().api("/api/view/" + page + (queryString ? "?" + queryString : "")); }
  function card(title, description, full = false) { const node = e("section", "management-card" + (full ? " full" : "")), heading = e("div", "management-heading"), name = e("h2", "", title); heading.append(name); node.append(heading); if (description) node.append(e("p", "management-description", description)); const notice = e("p", "management-message"); node.append(notice); return {node, heading, notice, before(child) { node.insertBefore(child, notice); }}; }
  function field(title, type = "text", value = "", options = []) { const host = e("label", "management-field"), name = e("span", "", title), input = e(type === "select" ? "select" : type === "textarea" ? "textarea" : "input"); if (type !== "select" && type !== "textarea") input.type = type; if (type === "select") for (const [key, text] of options) { const option = e("option", "", text); option.value = key; input.append(option); } input.value = value; host.append(name, input); return {host, input}; }
  function check(title, checked = false) { const host = e("label", "management-check"), input = e("input"); input.type = "checkbox"; input.checked = checked; host.append(input, e("span", "", title)); return {host, input}; }
  function date(value) { const parsed = typeof value === "number" ? new Date(value * 1000) : new Date(value); return Number.isFinite(parsed.getTime()) ? parsed.toLocaleString(H().language() === "en" ? "en-US" : "pt-BR") : String(value || "—"); }
  function revision() { return H().getState() && H().getState().workspace_revision || state.revision; }
  function dialog(title, description = "", wide = false) { const node = e("dialog", "management-dialog" + (wide ? " wide" : "")), body = e("div", "dialog-content"); node.dataset.workspaceRevision = revision(); body.append(e("h2", "", title)); if (description) body.append(e("p", "management-description", description)); const form = e("div", "management-form"), notice = e("p", "management-message"), actions = e("div", "management-actions"); const cancel = button(t("cancel"), () => { if (node.dataset.busy !== "true") node.close(); }); cancel.dataset.localCancel = "true"; actions.append(cancel); body.append(form, notice, actions); node.append(body); document.body.append(node); state.dialogs.add(node); const cleanup = []; node.addEventListener("close", () => { cleanup.forEach(fn => fn()); state.dialogs.delete(node); node.remove(); }); node.addEventListener("cancel", event => { if (node.dataset.busy === "true") event.preventDefault(); }); node.showModal(); return {node, body, form, notice, actions, cancel, cleanup}; }
  function confirm(title, description, fn, label = t("confirm")) { const d = dialog(title, description); const yes = button(label, () => busy(yes, d.notice, async () => { d.node.dataset.busy = "true"; try { await fn(d); } finally { d.node.dataset.busy = "false"; } }), "primary"); d.actions.append(yes); return d; }
  async function fileBase64(file, max = 10 * 1024 * 1024, limitKey = "image_limit") { if (!file || file.size > max) throw {code: limitKey}; const bytes = new Uint8Array(await file.arrayBuffer()); let text = ""; for (let i = 0; i < bytes.length; i += 32768) text += String.fromCharCode(...bytes.subarray(i, i + 32768)); return btoa(text); }
  function chooseFile(accept, handler, max) { const input = e("input"); input.type = "file"; input.accept = accept; input.hidden = true; document.body.append(input); input.addEventListener("change", async () => { const file = input.files[0]; input.remove(); if (!file) return; await handler(file, max); }, {once: true}); input.click(); }
  function directDownload(kind, params = {}, filename) { const qs = new URLSearchParams(params).toString(); return H().download("/api/export/" + kind + (qs ? "?" + qs : ""), filename); }

  async function mount(host) {
    if (state.host && state.host !== host) return;
    state.host = host || $("desktop-settings");
    if (!state.host || state.host.dataset.managementMounted) return;
    state.host.dataset.managementMounted = "true";
    await refresh(true);
  }
  async function refresh(force = false, expectedEdit = state.editSerial) {
    if (expectedEdit !== state.editSerial) return;
    if (!state.host || !H() || !H().connected()) return;
    if (state.loading) { if (force) { await state.finished; return refresh(true, expectedEdit); } return; }
    if (state.host.hidden || !state.host.getClientRects().length) return;
    const lang = H().language(), rev = revision();
    if (!force && (state.dirty || state.dialogs.size || rev && rev === state.revision && lang === state.language)) return;
    state.loading = true; let finished; state.finished = new Promise(resolve => { finished = resolve; }); const epoch = ++state.epoch, editSerial = state.editSerial;
    try {
      const [settings, backups, devices, updates] = await Promise.all([view("settings"), view("backups"), view("devices"), view("updates")]);
      if (epoch !== state.epoch || editSerial !== state.editSerial || !H().connected()) return;
      state.revision = settings.revision || rev; state.language = lang; state.dirty = false;
      render(settings, backups, devices, updates);
    } catch (error) {
      if (!state.host.children.length) state.host.append(e("p", "management-message error", errorText(error)));
    } finally { state.loading = false; finished(); controls(); }
  }
  function render(settings, backups, devices, updates) {
    const grid = e("div", "management-grid");
    if (H().getState().pending_recovery) grid.append(recoveryCard());
    grid.append(appearance(settings), artwork(), backupCard(backups), phoneImportCard(), devicesCard(devices), updatesCard(updates), desktopCard());
    const heading = e("header", "desk-heading"); heading.append(e("h1", "", t("settings")), e("p", "", t("settings_intro")));
    state.host.replaceChildren(heading, grid);
  }
  function appearance(data) {
    const c = card(t("appearance"), t("appearance_help")), form = e("form", "management-form"), columns = e("div", "management-two-cols"); c.node.id = "management-appearance"; c.heading.append(button(t("reload"), async () => { const editSerial=state.editSerial;state.dirty=false;await H().refresh();if(editSerial!==state.editSerial)return;await refresh(true,editSerial); }, "quiet"));
    const theme = field(t("theme"), "select", data.theme || "dark", ["dark", "original", "violet", "light"].map(key => [key, t(key)]));
    const language = field(t("language"), "select", data.language || "pt", [["pt", "Português (Brasil)"], ["en", "English"]]);
    const auto = check(t("auto_updates"), data.check_updates !== false), covers = check(t("covers"), Boolean(data.covers_enabled)), icons = check(t("icons"), data.icons_enabled !== false);
    theme.input.id = "phone-settings-theme"; language.input.id = "phone-settings-language"; covers.input.id = "phone-settings-covers"; icons.input.id = "phone-settings-icons";
    columns.append(theme.host, language.host); form.append(columns, auto.host, covers.host, icons.host);
    const login = check(t("startup_login"), Boolean(data.launch_at_login)), phoneAuto = check(t("startup_phone"), Boolean(data.phone_auto_start));
    if (data.startup_available) form.append(login.host, phoneAuto.host);
    const detection=check(t("detect_global"),Boolean(data.detection_enabled));form.append(detection.host);
    const save = button(t("save"), () => {} , "primary"); save.id = "phone-settings-save"; save.type = "submit"; form.append(save); c.before(form);
    form.addEventListener("change", () => { state.dirty = true; state.editSerial++; });
    form.addEventListener("submit", event => { event.preventDefault(); const editSerial = state.editSerial; busy(save, c.notice, async () => { await action("settings_save", {workspace_revision: data.revision || state.revision, theme: theme.input.value, language: language.input.value, ...(data.startup_available ? {launch_at_login:login.input.checked,phone_auto_start:phoneAuto.input.checked}:{}), detection_enabled:detection.input.checked, check_updates: auto.input.checked, covers_enabled: covers.input.checked, icons_enabled: icons.input.checked}); await H().refresh(); if (editSerial !== state.editSerial) return; state.dirty = false; await refresh(true, editSerial); }); });
    return c.node;
  }
  function backupCard(data) {
    const c = card(t("backups"), t("backup_help")), actions = e("div", "management-actions"); c.node.id = "management-backups";
    const create = button(t("create_backup"), () => busy(create, c.notice, async () => { await action("backup_create"); message(c.notice, t("backup_created")); await refresh(true); }));
    const download = button(t("download_backup"), () => busy(download, c.notice, () => directDownload("full_backup", {}, "HorasJogadas-backup.zip")));
    const restore = button(t("restore_file"), () => chooseFile(".zip,application/zip", file => busy(restore, c.notice, async () => { const preview = await query({query: "backup_restore_preview", data: await fileBase64(file, 32 * 1024 * 1024, "zip_limit")}); restoreDialog(preview, "backup_restore", {ticket: preview.ticket}); })));
    create.id = "phone-backup-create"; download.id = "phone-backup-download"; restore.id = "phone-backup-upload";
    actions.append(create, download, restore); c.before(actions); c.before(e("p", "management-file-note", t("zip_limit")));
    for (const [key, title, restoreAction] of [["full", "saved_backups", "backup_restore_local"], ["legacy", "legacy_backups", "legacy_restore"]]) {
      const details = e("details"), summary = e("summary", "", t(title) + " · " + ((data[key] || []).length)); details.append(summary);
      const list = e("div", "management-sublist");
      if (!(data[key] || []).length) list.append(e("p", "management-empty", t("empty_backups")));
      for (const item of data[key] || []) {
        const row = e("article", "management-list-item"), tools = e("div", "management-actions");
        row.append(e("h3", "management-item-title", date(item.created || item.momento || item.id)));
        row.append(e("p", "management-meta", key === "legacy" ? `${item.games || 0} ${t("games")} · ${item.sessions || 0} ${t("sessions")}` : `${item.files || 0} ${t("files")}`));
        if (key === "full") tools.append(button(t("download"), () => directDownload("full_backup", {id: item.id}, "HorasJogadas-backup.zip").catch(error => message(c.notice, errorText(error), true))));
        tools.append(button(t("restore"), () => restoreDialog(item, restoreAction, {id: item.id}), "management-danger")); row.append(tools); list.append(row);
      }
      details.append(list); c.before(details);
    }
    return c.node;
  }
  function restoreDialog(preview, actionName, payload) {
    const d = dialog(t("restore_title"), t("restore_help"));
    const count = [preview.games !== undefined ? `${preview.games} ${t("games")}` : "", preview.sessions !== undefined ? `${preview.sessions} ${t("sessions")}` : "", preview.completions !== undefined ? `${preview.completions} ${t("completions")}` : ""].filter(Boolean).join(" · ");
    if (count) d.form.append(e("p", "management-meta", count));
    const pending = field(t("pending_choice"), "select", "save", [["save", t("pending_save")], ["discard", t("pending_discard")]]);
    const recovery = field(t("recovery"), "select", "save", [["save", t("recovery_save")], ["discard", t("recovery_discard")]]);
    d.form.append(pending.host); if (preview.has_pending !== false) d.form.append(recovery.host);
    const acknowledged = check(t("confirmed")); d.form.append(acknowledged.host);
    const yes = button(t("restore"), () => busy(yes, d.notice, async () => { if (!acknowledged.input.checked) { message(d.notice, t("finish_pending"), true); return; } await action(actionName, {...payload, workspace_revision: d.node.dataset.workspaceRevision, confirmed: true, pending: pending.input.value, recovery: recovery.input.value}); d.node.close(); state.dirty = false; await H().refresh(); await refresh(true); }), "primary"); yes.id = "phone-backup-restore-confirm";
    d.actions.append(yes);
  }
  function phoneImportCard() {
    const c = card(t("phone_import"), t("phone_help")); c.node.id = "management-phone-import";
    const b = button(t("import_phone"), () => chooseFile(".json,application/json", file => busy(b, c.notice, async () => { const result = await query({query: "phone_import_preview", data: await fileBase64(file, 1024 * 1024, "session_limit")}); phoneImportDialog(result); }))); c.before(b); return c.node;
  }
  function phoneImportDialog(preview) {
    const d = dialog(t("phone_review"), t("phone_review_help"), true), list = e("div", "management-selection"), choices = [];
    const games = H().getState().games || [];
    for (const [index, record] of (preview.records || preview.items || []).entries()) {
      const host = e("div", "management-selection-row"), top = e("label", "management-row-top"), checked = e("input"); checked.type = "checkbox";
      const duplicate = Boolean(record.duplicate || record.already_imported); checked.checked = !duplicate; checked.disabled = duplicate; if (duplicate) checked.dataset.permanentDisabled = "true";
      const name = record.game || record.name || "—"; top.append(checked, e("span", "", name)); host.append(top);
      host.append(e("p", "management-meta", duplicate ? t("already_imported") : `${date(record.started_at || record.start)} · ${H().clock(record.seconds || 0)}`));
      const destination = field(t("source_games"), "select", record.destination_id || record.game_id || "", [["", t("new_game")], ...games.map(game => [game.id, game.name])]); host.append(destination.host);
      choices.push({index: record.index === undefined ? index : record.index, checked, destination: destination.input}); list.append(host);
    }
    d.form.append(list);
    d.actions.append(button(t("import_sessions"), event => busy(event.currentTarget, d.notice, async () => { const selected = choices.filter(item => item.checked.checked && item.checked.dataset.permanentDisabled !== "true"); if (!selected.length) { message(d.notice, t("select_images"), true); return; } await action("phone_import", {workspace_revision: d.node.dataset.workspaceRevision, ticket: preview.ticket, selected: selected.map(item => item.index), destinations: Object.fromEntries(selected.map(item => [item.index, item.destination.value || null]))}); d.node.close(); await H().refresh(); await refresh(true); }), "primary"));
  }
  function devicesCard(data) {
    const c = card(t("devices"), t("devices_help")), list = e("div", "management-sublist"); c.node.id = "management-devices";
    const devices = Array.isArray(data) ? data : data.devices || data.remembered_devices || [];
    if (!devices.length) list.append(e("p", "management-empty", t("empty_devices")));
    for (const device of devices) {
      const host = e("article", "management-list-item"), tools = e("div", "management-actions");
      host.append(e("h3", "management-item-title", device.label || device.name || t("remembered")), e("p", "management-meta", t("expires") + " " + date(device.expires_at)));
      tools.append(button(t("revoke"), () => confirm(t("revoke"), t("revoke_help"), async d => { await action("device_revoke", {workspace_revision: d.node.dataset.workspaceRevision, device_id: device.id, confirmed: true}); d.node.close(); await H().refresh(); await refresh(true); }), "management-danger")); host.append(tools); list.append(host);
    }
    c.before(list); if (devices.length) c.before(button(t("revoke_all"), () => confirm(t("revoke_all"), t("revoke_help"), async d => { await action("device_revoke_all", {workspace_revision: d.node.dataset.workspaceRevision, confirmed: true}); d.node.close(); await H().refresh(); }), "management-danger")); const disable = button(t("disable_control"), () => confirm(t("disable_control"), t("disable_control_help"), async d => { await action("control_disable", {workspace_revision: d.node.dataset.workspaceRevision, confirmed:true}); message(d.notice,t("control_disabled")); d.cancel.textContent=t("close"); }), "management-danger"); disable.id="phone-control-disable"; c.before(disable); return c.node;
  }
  function updatesCard(data) {
    const c = card(t("updates"), t("updates_help")), current = data.current_version || data.version || H().getState().version; c.node.id = "management-updates";
    c.before(e("p", "management-meta", t("current_version"))); c.before(e("p", "management-update-version", current));
    const available = data.available || data.release;
    if (data.packaged === false) c.before(e("p", "management-description", t("official_package")));
    if (available) c.before(e("p", "management-description", t("available") + " · " + (available.version || available)));
    const tools = e("div", "management-actions");
    const checkUpdates = button(t("check_updates"), () => busy(checkUpdates, c.notice, async () => { const task = await query({query: "update_check"}); const result = await job(task, c.node, c.notice); if (!result) return; await refresh(true); message(c.notice, result.available || result.release ? t("available") : t("up_to_date")); })); tools.append(checkUpdates);
    const packaged = data.packaged !== false && data.can_install !== false;
    if (available && packaged && !data.busy && data.status !== "ready" && data.status !== "installing") tools.append(button(t("download_update"), event => busy(event.currentTarget, c.notice, async () => { const task = await action("update_download"); await job(task, c.node, c.notice); await refresh(true); })));
    if (data.status === "ready" && packaged) tools.append(button(t("install_update"), () => { const d = confirm(t("update_install_title"), t("update_install_help"), async current => { await action("update_install", {workspace_revision: current.node.dataset.workspaceRevision, confirmed: true, pending: pending.input.value}); message(current.notice, t("installing")); current.cancel.textContent = t("close"); }, t("install")); const pending = field(t("pending_choice"), "select", "save", [["save", t("pending_save")], ["discard", t("pending_discard")]]); d.form.append(pending.host); }, "primary"));
    if (data.busy) setTimeout(() => { if (c.node.isConnected) job({job_id:"update"}, c.node, c.notice).then(() => refresh(true)).catch(error => message(c.notice,errorText(error),true)); }, 0);
    c.before(tools); if (data.error) message(c.notice, H().errorText(data.error), true); return c.node;
  }
  function desktopCard() {
    const c = card(t("desktop"), t("desktop_help")), tools = e("div", "management-actions"); c.node.id = "management-desktop";
    tools.append(button(t("open_data"), event => busy(event.currentTarget, c.notice, async () => { await action("pc_open_data"); message(c.notice, t("desktop_done")); })), button(t("review_copy"), () => confirm(t("review_copy"), t("desktop_help"), async d => { await action("pc_create_review", {workspace_revision: d.node.dataset.workspaceRevision, confirmed: true}); message(d.notice, t("desktop_done")); d.cancel.textContent = t("close"); })));
    c.before(tools); return c.node;
  }
  function recoveryCard() {
    const c = card(t("recover_title"), t("recover_help"), true), tools = e("div", "management-actions");
    for (const choice of ["save", "discard"]) tools.append(button(t(choice === "save" ? "recover_save" : "recover_discard"), () => confirm(t("recover_title"), t("recover_help"), async d => { await action("pending_recover", {workspace_revision:d.node.dataset.workspaceRevision, choice, confirmed:true}); d.node.close(); await H().refresh(); await refresh(true); }), choice === "save" ? "primary" : "management-danger"));
    c.before(tools); return c.node;
  }

  async function job(initial, host, notice, onProgress) {
    if (!initial || !initial.job_id) return initial;
    const id = initial.job_id, token = {cancelled: false}; state.jobs.set(id, token);
    const progress = e("progress", "management-progress"), cancel = button(t("cancel_job"), async () => { try { await action(id === "update" ? "update_cancel" : "job_cancel", id === "update" ? {} : {job_id: id}); token.cancelled = true; message(notice, t("cancelled")); } catch (error) { message(notice, errorText(error), true); } }); cancel.dataset.jobCancel = "true";
    host.append(progress, cancel);
    try {
      for (;;) {
        if (!host.isConnected || !H().connected() || token.cancelled) return null;
        const current = await view("job", {id});
        if (typeof current.progress === "number" && current.total) { progress.max = current.total; progress.value = current.progress; message(notice, `${Math.round(current.progress / current.total * 100)}%`); }
        else if (current.progress && Number(current.progress.total) > 0) { progress.max = current.progress.total; progress.value = current.progress.done || 0; message(notice, `${Math.round((current.progress.done || 0) / current.progress.total * 100)}%`); }
        else progress.removeAttribute("value");
        if (onProgress) onProgress(current);
        if (current.status === "complete" || current.status === "completed" || current.status === "done") { message(notice, t("done")); return current.result || {}; }
        if (current.status === "failed") throw {code: current.error || "storage"};
        if (current.status === "cancelled") { message(notice, t("cancelled")); return null; }
        await new Promise(resolve => setTimeout(resolve, 650));
      }
    } finally { progress.remove(); cancel.remove(); state.jobs.delete(id); }
  }

  async function showArtwork(kind = "cover", gameId = null) {
    const d = dialog(t(kind === "icon" ? "manage_icons" : "manage_covers"), t("art_help"), true);
    try {
      const data = await view("artwork"), games = (data.games || []).filter(game => !gameId || game.id === gameId), tools = e("div", "management-art-tools");
      const sources = data.sources && data.sources[kind] || (kind === "icon" ? ["Steam", "GOG"] : ["Steam", "GOG", "Wikipedia"]);
      const source = field(t("source"), "select", "all", [["all", t("all_sources")], ...sources.map(name => [name, name])]); tools.append(source.host);
      const toggle = button(t("select_all"), () => { const checked = rows.some(item => item.check.checked); rows.forEach(item => { item.check.checked = !checked; }); }); tools.append(toggle); d.form.append(tools);
      const list = e("div", "management-art-games"), rows = [], preview = e("img", "management-art-preview" + (kind === "icon" ? " icon" : "")); preview.hidden = true; preview.alt = t("preview"); d.form.append(list, preview);
      let searchJob = null, previewURL = null;
      d.cleanup.push(() => { if (previewURL) URL.revokeObjectURL(previewURL); });
      async function searchRows(selectedRows) {
        if (!selectedRows.length) { message(d.notice, t("select_images"), true); return; }
        const task = await query({query: "art_search", kind, source: source.input.value, titles: selectedRows.map(item => ({game_id: item.game.id, title: item.title.value.trim() || item.game.name}))});
        const result = await job(task, d.body, d.notice); if (!result) return;
        searchJob = task.job_id;
        for (const item of result.games || []) {
          const target = rows.find(row => row.game.id === item.game_id); if (!target) continue;
          target.candidates = item.candidates || []; target.searchJob = task.job_id; target.select.replaceChildren(e("option", "", t("choose"))); target.select.firstChild.value = "";
          for (const candidate of target.candidates) { const option = e("option", "", candidate.name + " · " + candidate.source); option.value = candidate.id; target.select.append(option); }
          target.select.hidden = false; target.preview.hidden = !target.candidates.length; target.info.textContent = target.candidates.length ? "" : t("no_results");
        }
      }
      for (const game of games) {
        const host = e("article", "management-art-game"), top = e("label", "management-art-name"), checked = e("input"); checked.type = "checkbox"; checked.checked = kind === "icon" ? !game.has_icon : !game.has_cover; top.append(checked, e("span", "", game.name));
        const title = field(t("search_title"), "text", game.name); title.input.maxLength = 200;
        const select = e("select"); select.setAttribute("aria-label", t("choose") + " · " + game.name); select.hidden = true;
        const info = e("p", "management-meta"), actions = e("div", "management-actions"), item = {game, check: checked, title: title.input, select, candidates: [], preview: null, info};
        const search = button(t("search_again"), () => busy(search, d.notice, () => searchRows([item])));
        const viewPreview = button(t("preview"), () => busy(viewPreview, d.notice, async () => {
          if (!item.select.value || !item.searchJob) return;
          const task = await query({query: "art_preview", job_id: item.searchJob, candidate_id: item.select.value}); const result = await job(task, d.body, d.notice); if (!result || !result.data) return;
          const bytes = Uint8Array.from(atob(result.data), char => char.charCodeAt(0)); if (previewURL) URL.revokeObjectURL(previewURL); previewURL = URL.createObjectURL(new Blob([bytes], {type: result.mime || "image/jpeg"})); preview.src = previewURL; preview.hidden = false;
        })); viewPreview.hidden = true; item.preview = viewPreview;
        const local = button(t("local"), () => chooseFile("image/png,image/jpeg,image/webp,image/bmp", file => busy(local, d.notice, async () => { await action("art_local", {workspace_revision: d.node.dataset.workspaceRevision, game_id: game.id, kind, data: await fileBase64(file)}); message(d.notice, t("local_saved")); await H().refresh(); d.node.dataset.workspaceRevision = revision(); })));
        const remove = button(t("remove"), () => confirm(t("remove"), game.name, async confirmation => { await action("art_remove", {workspace_revision: confirmation.node.dataset.workspaceRevision, game_id: game.id, kind}); confirmation.node.close(); message(d.notice, t("image_removed")); await H().refresh(); d.node.dataset.workspaceRevision = revision(); }), "management-danger");
        const link = e("a", "management-source-link", t("view_source")); link.hidden = true; link.target = "_blank"; link.rel = "noopener noreferrer";
        select.addEventListener("change", () => { const candidate = item.candidates.find(value => value.id === select.value); try { const url = new URL(candidate && candidate.page_url); if (url.protocol !== "https:") throw Error(); link.href = url.href; link.hidden = false; } catch (_) { link.hidden = true; link.removeAttribute("href"); } });
        host.dataset.gameId = game.id; local.dataset.artAction = "local"; remove.dataset.artAction = "remove"; search.dataset.artAction = "search";
        actions.append(search, viewPreview, local, remove); host.append(top, title.host, select, info, actions, link); rows.push(item); list.append(host);
      }
      const search = button(t("search"), () => busy(search, d.notice, () => searchRows(rows.filter(item => item.check.checked)))); d.actions.append(search);
      const importImages = button(t("import_selected"), () => busy(importImages, d.notice, async () => {
        const selected = rows.filter(item => item.check.checked && item.select.value && item.searchJob); if (!selected.length) { message(d.notice, t("select_images"), true); return; }
        for (const id of new Set(selected.map(item => item.searchJob))) { const task = await action("art_import", {workspace_revision: d.node.dataset.workspaceRevision, kind, job_id: id, selected: selected.filter(item => item.searchJob === id).map(item => ({game_id: item.game.id, candidate_id: item.select.value}))}); if (!await job(task, d.body, d.notice)) return; await H().refresh(); d.node.dataset.workspaceRevision = revision(); }
        message(d.notice, t("imported")); await H().refresh();
      }), "primary"); d.actions.append(importImages);
      if (gameId) rows[0].check.checked = true;
    } catch (error) { message(d.notice, errorText(error), true); }
  }
  function artwork() { const c = card(t("artwork"), t("art_help")), tools = e("div", "management-actions"); c.node.id = "management-artwork"; const covers = button(t("manage_covers"), () => showArtwork("cover")), icons = button(t("manage_icons"), () => showArtwork("icon")); covers.id = "phone-manage-covers"; icons.id = "phone-manage-icons"; tools.append(covers, icons); c.before(tools); return c.node; }

  document.addEventListener("horas:state", () => { refresh(); controls(); });
  document.addEventListener("horas:connection", controls);
  document.addEventListener("DOMContentLoaded", () => { if (H() && H().subscribe) H().subscribe(() => { refresh(); controls(); }); });
  window.HorasManagement = {mount, refresh, showArtwork};
})();

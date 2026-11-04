/* Connected phone parity: real Qt, HTTP, browser UI and legacy-domain readback. */
"use strict";
const fs = require("fs"), os = require("os"), path = require("path");
const {spawn} = require("child_process");
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const args = process.argv.slice(2);
const option = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const root = path.resolve(__dirname, ".."), temporary = fs.mkdtempSync(path.join(os.tmpdir(), "horas-phone-desktop-"));
const connectionFile = path.join(temporary, "connection.json"), controlFile = path.join(temporary, "control.json");
const resultFile = option("--result", path.join(root, "build-diagnostics", "phone-desktop-browser.json"));
const screenshots = option("--screenshots", "");
const result = {ok: false};
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const check = (value, message) => { if (!value) throw new Error(message); };
const connection = () => JSON.parse(fs.readFileSync(connectionFile));
async function control(value) {
  const nonce = Math.random().toString(36), name = controlFile + ".tmp";
  fs.writeFileSync(name, JSON.stringify({...value, nonce})); fs.renameSync(name, controlFile);
  const end = Date.now() + 5000;
  while (Date.now() < end) { if (connection().control_nonce === nonce) return; await wait(50); }
  throw new Error("Qt fixture did not acknowledge control");
}

(async () => {
  let browser, fixture, page, fixtureErrors = "", stage = "startup";
  const errors = [], violations = [], httpErrors = [];
  try {
    fixture = spawn(option("--python", process.env.PYTHON || "python"), [path.join(__dirname, "phone_browser_fixture.py"), "--output", connectionFile, "--control", controlFile], {cwd: root, env: {...process.env, QT_QPA_PLATFORM: "offscreen"}, stdio: ["ignore", "ignore", "pipe"]});
    fixture.on("error", error => { fixtureErrors = error.message; });
    fixture.stderr.on("data", chunk => { fixtureErrors = (fixtureErrors + chunk.toString()).slice(-4000); });
    const deadline = Date.now() + 20000;
    while (!fs.existsSync(connectionFile) && fixture.exitCode === null && Date.now() < deadline) await wait(100);
    check(fs.existsSync(connectionFile), "Qt fixture failed to start: " + fixtureErrors);
    const launch = {headless: true};
    if (option("--chromium", process.env.CHROMIUM)) launch.executablePath = option("--chromium", process.env.CHROMIUM);
    if (process.env.CI || process.getuid && process.getuid() === 0) launch.args = ["--no-sandbox"];
    browser = await chromium.launch(launch);
    const context = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, acceptDownloads: true});
    page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    page.on("response", response => { if (response.status() >= 400) httpErrors.push({path: new URL(response.url()).pathname, status: response.status()}); });
    page.on("dialog", async dialog => { errors.push("Unexpected native JavaScript dialog"); await dialog.dismiss(); });
    await page.exposeFunction("reportCSP", value => violations.push(value));
    await page.addInitScript(() => document.addEventListener("securitypolicyviolation", event => window.reportCSP(event.violatedDirective)));
    await page.goto(connection().pairing_url);
    await page.locator("#control-view").waitFor({state: "visible"});
    await page.locator("#desktop-nav").waitFor({state: "visible"});
    async function navigate(name) {
      await page.locator(`#desktop-nav [data-page='${name}']`).click();
      if (name === "library") await page.locator("#desktop-library").waitFor({state: "visible"});
      else await page.locator("#desktop-" + name).waitFor({state: "visible"});
    }
    async function library() {
      await navigate("library");
      if (!await page.locator("#library-section").isVisible()) await page.locator("#focus-toggle").click();
    }
    async function request(url, body) {
      return page.evaluate(async ({url, body}) => window.HorasPhone.api(url, body), {url, body});
    }
    async function state() { return request("/api/state"); }
    async function command(body) {
      const current = await state();
      const game = current.games.find(game => game.id === body.game_id);
      return page.evaluate(async body => window.HorasPhone.commandRaw(body), {...body, workspace_revision: current.workspace_revision, ...(game ? {revision: game.revision} : {})});
    }
    async function refresh() { await page.evaluate(() => window.HorasPhone.refresh()); }
    const form = () => page.locator("#desktop-form");
    async function fill(names, value) {
      for (const name of names) {
        const input = form().locator(`[name='${name}']`);
        if (await input.count()) { await input.fill(String(value)); return; }
      }
      throw new Error("Missing form field: " + names.join(" / "));
    }
    async function choose(names, value) {
      for (const name of names) {
        const input = form().locator(`select[name='${name}']`);
        if (await input.count()) { await input.selectOption(String(value)); return; }
      }
      throw new Error("Missing selector field: " + names.join(" / "));
    }
    async function submit() {
      await page.locator("#desktop-submit").click();
      await page.locator("#desktop-dialog").waitFor({state: "hidden"});
    }
    async function snapshot(name) {
      if (!screenshots) return;
      fs.mkdirSync(screenshots, {recursive: true});
      await page.screenshot({path: path.join(screenshots, "HorasJogadas-connected-" + name + ".png")});
    }
    const initial = await state();
    const hollow = initial.games.find(game => game.name === "Hollow Knight");
    check(hollow, "Fake profile is missing expected game");

    stage = "five_pages_and_responsive";
    for (const section of ["library", "history", "stats", "completed", "settings"]) {
      await navigate(section);
      for (const width of [320, 390, 1040]) {
        await page.setViewportSize({width, height: 844});
        check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), section + " horizontal overflow at " + width);
      }
      await page.setViewportSize({width: 390, height: 844});
      await snapshot(section);
    }
    result.five_pages_responsive = true;

    stage = "library_game_edit_and_timer_adjust";
    await library();
    const game = page.locator(".game-card").filter({has: page.getByRole("heading", {name: "Hollow Knight", exact: true})});
    await game.locator(".game-menu-button").click();
    await page.locator("[data-action='game_rename']").click();
    await fill(["name"], "Hollow Knight — conectado");
    await submit();
    check((await state()).games.some(game => game.id === hollow.id && game.name === "Hollow Knight — conectado"), "Rename did not reach PC state");
    result.game_rename = true;

    const editedGame = () => page.locator(".game-card").filter({has: page.getByRole("heading", {name: "Hollow Knight — conectado", exact: true})});
    await editedGame().locator(".game-menu-button").click();
    await page.locator("[data-action='game_rename']").click();
    await fill(["name"], "Rascunho que precisa ser preservado");
    await control({invalidate: true});
    await page.locator("#desktop-submit").click();
    await wait(300);
    check(await page.locator("#desktop-dialog").isVisible(), "A stale edit unexpectedly replaced newer PC state");
    check(await form().locator("[name='name']").inputValue() === "Rascunho que precisa ser preservado", "Stale edit lost the phone draft");
    check((await state()).games.find(game => game.id === hollow.id).name === "Hollow Knight — conectado", "Stale rename changed PC data");
    await page.locator("#desktop-cancel").click();
    result.stale_edit_preserves_draft_and_pc = true;
    await editedGame().locator(".game-menu-button").click();
    await page.locator("[data-action='game_status']").click();
    await choose(["status"], "Backlog");
    await submit();
    check((await state()).games.find(game => game.id === hollow.id).status === "Backlog", "Status did not reach PC state");
    result.game_status = true;
    await page.locator("#library-status").selectOption("Backlog");
    const filteredStatuses = await page.locator(".game-card:visible .game-status").allTextContents();
    check(filteredStatuses.length > 0 && filteredStatuses.every(value => value === "BACKLOG"), "Library status filter displayed another status or hid all games");
    await page.locator("#library-status").selectOption("");
    result.library_status_filter = true;
    await editedGame().locator(".game-menu-button").click();
    await page.locator("[data-action='timer_adjust']").click();
    for (const minutes of [5, 10, 15, 30]) await form().getByRole("button", {name: "+" + minutes + " min", exact: true}).click();
    check(await form().evaluate(form => Number(form.elements.hours.value) * 3600 + Number(form.elements.minutes.value) * 60 + Number(form.elements.seconds.value)) === 3600, "Quick minute buttons did not add and normalize their values");
    check((await state()).games.find(game => game.id === hollow.id).seconds === 0, "Quick minute buttons modified the timer before saving");
    if (await form().locator("[name='hours']").count()) {
      await fill(["hours"], 0); await fill(["minutes"], 2); await fill(["seconds"], 5);
    } else await fill(["seconds", "delta"], 125);
    await submit();
    check(Math.round((await state()).games.find(game => game.id === hollow.id).seconds) === 125, "Time adjustment did not reach PC timer");
    result.timer_adjust = true;
    result.timer_quick_minutes_preview_only = true;
    await command({action: "timer_adjust", game_id: hollow.id, seconds: -5});
    check(Math.round((await state()).games.find(game => game.id === hollow.id).seconds) === 120, "Negative adjustment failed");
    await command({action: "timer_discard", game_id: hollow.id, confirmed: true});
    check(!(await state()).games.find(game => game.id === hollow.id).pending, "Discard left pending timer");
    result.timer_negative_and_discard = true;

    stage = "library_order_and_pause_tools";
    for (const order of ["nome", "horas", "recente"]) {
      await page.locator("#library-sort").selectOption(order);
      await page.waitForFunction(() => !document.querySelector("#library-sort").disabled);
      const sortedState = await state();
      check(sortedState.library_order === order, "Library order was not saved on the PC");
      const expected = sortedState.games.slice().sort(order === "nome" ? (a,b) => a.name.localeCompare(b.name) : order === "horas" ? (a,b) => b.total_seconds-a.total_seconds : (a,b) => String(b.last_played||"").localeCompare(String(a.last_played||"")));
      check(await page.locator(".game-card:visible .game-name").first().textContent() === expected[0].name, "Visible library order differs from selected sort");
    }
    await page.locator("#library-sort").selectOption("manual");
    await page.waitForFunction(() => !document.querySelector("#library-sort").disabled);
    for (const [action, index] of [["game_move_bottom", -1], ["game_move_top", 0]]) {
      await editedGame().locator(".game-menu-button").click();
      await page.locator(`[data-action='${action}']`).click();
      await page.waitForFunction(() => window.HorasPhone.ready());
      const ordered = (await state()).games;
      check(ordered.at(index).id === hollow.id, "Manual move did not update the PC library");
    }
    result.library_sort_and_manual_moves = true;
    await command({action: "start", game_id: hollow.id});
    await wait(1150);
    await command({action: "pause", game_id: hollow.id});
    await wait(1200);
    await refresh();
    const beforePauseAdjustment = (await state()).games.find(game => game.id === hollow.id).seconds;
    await editedGame().locator(".game-menu-button").click();
    await page.locator("[data-action='timer_adjust']").click();
    await page.locator("#timer-use-pause").click();
    await page.waitForFunction(() => { const form = document.querySelector("#desktop-form"); return form && Number(form.elements.hours.value) * 3600 + Number(form.elements.minutes.value) * 60 + Number(form.elements.seconds.value) >= 1; });
    const pauseFields = await form().evaluate(form => Number(form.elements.hours.value) * 3600 + Number(form.elements.minutes.value) * 60 + Number(form.elements.seconds.value));
    check(pauseFields >= 1, "Use pause did not fill the adjustment fields");
    check(!(await state()).games.find(game => game.id === hollow.id).running, "Use pause resumed before adjustment confirmation");
    await page.locator("#desktop-cancel").click();
    check((await state()).games.find(game => game.id === hollow.id).seconds === beforePauseAdjustment, "Cancelling the pause adjustment changed the timer");
    await editedGame().locator(".game-menu-button").click();
    await page.locator("[data-action='timer_count_pause']").click();
    await fill(["minutes"], ""); await submit();
    const resumed = (await state()).games.find(game => game.id === hollow.id);
    check(resumed.running && resumed.seconds >= beforePauseAdjustment + 1, "Counting the pause did not add elapsed pause and resume");
    await command({action: "finish", game_id: hollow.id});
    result.pause_fill_cancel_and_count = true;

    stage = "history_crud_undo_and_csv";
    await navigate("history");
    await page.locator("#history-add").click();
    await choose(["game_id"], hollow.id);
    await fill(["duration", "seconds"], await form().locator("[name='duration']").count() ? "00:03:00" : "180");
    const end = new Date(Date.now() - 3600000).toISOString().slice(0, 19);
    const endInput = form().locator("[name='end']");
    await endInput.fill((await endInput.getAttribute("type")) === "datetime-local" ? end : end.replace("T", " "));
    await submit();
    let history = await request("/api/view/history?search=" + encodeURIComponent("Hollow Knight — conectado"));
    const added = history.sessions.find(session => session.seconds === 180 && session.game_id === hollow.id);
    check(added, "Manual history addition missing from PC");
    result.history_add = true;
    const row = () => page.locator(`[data-session-id='${added.id}']`);
    await row().locator("[data-action='history_edit']").click();
    await fill(["duration", "seconds"], await form().locator("[name='duration']").count() ? "00:04:00" : "240");
    await submit();
    history = await request("/api/view/history");
    check(history.sessions.some(session => session.id === added.id && session.seconds === 240), "History edit missing from PC");
    result.history_edit = true;
    await row().locator("[data-action='history_delete']").click(); await submit();
    history = await request("/api/view/history");
    check(!history.sessions.some(session => session.id === added.id), "History deletion failed");
    await page.locator("#history-undo").click();
    await page.waitForFunction(id => Boolean(document.querySelector(`[data-session-id='${id}']`)), added.id);
    result.history_delete_undo = true;
    const [csv] = await Promise.all([page.waitForEvent("download"), page.locator("#history-export").click()]);
    check(fs.readFileSync(await csv.path(), "utf8").includes("Hollow Knight"), "Downloaded history CSV has no game data");
    result.history_csv_download = true;

    stage = "long_session_confirmation";
    await page.locator("#history-add").click();
    await choose(["game_id"], hollow.id); await fill(["duration"], "25:00:00");
    await form().locator("[name='end']").fill(end);
    await page.locator("#desktop-submit").click();
    await wait(200);
    check(await page.locator("#desktop-dialog").isVisible(), "A long session was saved without explicit confirmation");
    await form().locator("[name='confirmed_long']").check(); await submit();
    history = await request("/api/view/history");
    check(history.sessions.some(session => session.seconds === 90000 && session.game_id === hollow.id), "Confirmed long session was not saved");
    result.long_session_requires_confirmation = true;

    stage = "statistics_real_domain";
    await navigate("stats");
    await page.locator("#stats-period").selectOption("8s");
    await page.locator("#stats-period").selectOption("6m");
    await page.locator("#stats-status").selectOption("Backlog");
    const stats = await request("/api/view/stats?period=6m&status=Backlog");
    check(stats.summary.sessions >= initial.games.length - 2 && stats.chart.length === 6, "Statistics do not match domain data");
    check(stats.groups.every(group => group.status === "Backlog"), "Stats status filter failed");
    result.statistics_period_and_status = true;

    stage = "completed_crud_replay_undo_and_txt";
    await navigate("completed");
    await page.locator("#completed-add").click();
    await fill(["name"], "Conclusão <teste> do controle");
    await fill(["year"], new Date().getFullYear());
    await choose(["month"], "1");
    await fill(["day"], "1");
    await fill(["duration", "seconds"], await form().locator("[name='duration']").count() ? "02:00:00" : "7200");
    await fill(["platinum", "platinum_seconds"], await form().locator("[name='platinum']").count() ? "00:30:00" : "1800");
    await choose(["type"], "zerado");
    await form().locator("[name='dlc']").check();
    await fill(["notes"], "Observação <img src=x onerror=alert(1)>");
    await submit();
    let completed = await request("/api/view/completed?year=" + new Date().getFullYear());
    const completion = completed.records.find(record => record.name === "Conclusão <teste> do controle");
    check(completion && completion.dlc && completion.seconds === 7200 && completion.platinum_seconds === 1800, "Completed details differ from submitted fields");
    result.completion_add_fields = true;
    const completionRow = () => page.locator(`[data-completion-id='${completion.id}']`);
    await completionRow().locator("[data-action='completion_edit']").click();
    await fill(["notes"], "Notas atualizadas no celular"); await submit();
    completed = await request("/api/view/completed?year=" + new Date().getFullYear());
    check(completed.records.find(record => record.id === completion.id).notes === "Notas atualizadas no celular", "Completion editing failed");
    result.completion_edit = true;
    await completionRow().locator("[data-action='completion_replay']").click();
    await fill(["name"], "Nova jogada do controle"); await submit();
    completed = await request("/api/view/completed?year=" + new Date().getFullYear());
    check(completed.records.some(record => record.id !== completion.id && record.name === "Nova jogada do controle"), "Replay overwrote or omitted original completion");
    result.completion_replay = true;
    await completionRow().locator("[data-action='completion_delete']").click(); await submit();
    await page.locator("#completed-undo").click();
    await page.waitForFunction(id => Boolean(document.querySelector(`[data-completion-id='${id}']`)), completion.id);
    result.completion_delete_undo = true;
    const [txt] = await Promise.all([page.waitForEvent("download"), page.locator("#completed-export").click()]);
    const txtContent = fs.readFileSync(await txt.path(), "utf8");
    check(txtContent.includes("Conclusão <teste>"), "Downloaded completions TXT has no actual records");
    result.completion_txt_download = true;

    stage = "completion_txt_import_review";
    await page.locator("#completed-import").click();
    const importedName = "TXT importado pelo celular";
    await page.locator("#completion-import-file").setInputFiles({name: "zerados-" + new Date().getFullYear() + ".txt", mimeType: "text/plain", buffer: Buffer.from(txtContent.replaceAll("Conclusão <teste> do controle", importedName))});
    await page.locator("#completion-import-preview").click();
    await page.locator("#completion-import-rows input[type='checkbox']:checked").first().waitFor();
    const previousCompleted = await request("/api/view/completed?year=" + new Date().getFullYear());
    check(!previousCompleted.records.some(record => record.name === importedName), "TXT preview mutated records before confirmation");
    await submit();
    completed = await request("/api/view/completed?year=" + new Date().getFullYear());
    check(completed.records.some(record => record.name === importedName), "Reviewed TXT selection was not imported");
    result.completion_txt_review_and_import = true;

    stage = "pending_game_deletion_preserves_selected_session";
    const extra = await command({action: "add", name: "Jogo temporário para exclusão"});
    const temporaryGame = extra.state.games.find(game => game.name === "Jogo temporário para exclusão");
    await command({action: "timer_adjust", game_id: temporaryGame.id, seconds: 60});
    await library();
    const temporaryCard = page.locator(".game-card").filter({has: page.getByRole("heading", {name: "Jogo temporário para exclusão", exact: true})});
    await temporaryCard.locator(".game-menu-button").click(); await page.locator("[data-action='game_delete']").click();
    await choose(["pending"], "save"); await submit();
    check(!(await state()).games.some(game => game.id === temporaryGame.id), "Game deletion left the game in the library");
    history = await request("/api/view/history?search=" + encodeURIComponent("Jogo temporário para exclusão"));
    check(history.sessions.some(session => session.seconds === 60), "Saving a pending session before deleting its game lost the record");
    result.game_delete_saves_pending_session = true;

    stage = "statistics_group_delete_and_history_clear";
    await navigate("stats");
    await page.locator(`[data-group-key='${hollow.id}'] [data-action='stats_delete_group']`).click();
    await submit();
    history = await request("/api/view/history");
    check(!history.sessions.some(session => session.game_id === hollow.id), "Deleting a stats group left its sessions");
    result.statistics_delete_group = true;
    await navigate("history");
    const countBeforeCancel = (await request("/api/view/history")).total;
    await page.locator("#history-clear").click(); await page.locator("#desktop-cancel").click();
    check((await request("/api/view/history")).total === countBeforeCancel, "Cancelling clear history changed records");
    await page.locator("#history-clear").click(); await submit();
    check((await request("/api/view/history")).total === 0, "Confirmed clear history did not clear sessions");
    check((await request("/api/view/completed?year=" + new Date().getFullYear())).records.length === completed.records.length, "Clearing history changed the independent completions list");
    check((await request("/api/view/backups")).full.length > 0, "Destructive actions did not preserve a full backup");
    result.history_clear_confirm_cancel_and_backup = true;

    stage = "security_and_preserved_controls";
    check(errors.length === 0, "Browser errors: " + errors.join(", "));
    check(violations.length === 0, "CSP violations: " + violations.join(", "));
    await snapshot("completed-final");
    result.safe_dom_and_csp = true;
    result.ok = true;
  } catch (error) {
    result.failed_case = stage;
    result.error = String(error.message).replace(/#pair=[A-Za-z0-9_-]+/g, "#pair=[redacted]");
    result.browser_errors = errors.map(message => String(message).replace(/#pair=[A-Za-z0-9_-]+/g, "#pair=[redacted]"));
    result.http_errors = httpErrors;
    if (page && !page.isClosed()) {
      try { result.pair_message = await page.locator("#pair-message").textContent(); } catch (_) {}
      try { result.notices = await page.locator(".notice:visible,.desk-error:visible,.management-message:visible").allTextContents(); } catch (_) {}
      try { if (screenshots) await page.screenshot({path: path.join(screenshots, "HorasJogadas-connected-failure.png")}); } catch (_) {}
    }
  } finally {
    if (browser) await browser.close();
    if (fixture && fixture.exitCode === null) {
      try { await control({quit: true}); } catch (_) {}
      await Promise.race([new Promise(resolve => fixture.once("exit", resolve)), wait(3000)]);
      if (fixture.exitCode === null) fixture.kill();
    }
    fs.mkdirSync(path.dirname(resultFile), {recursive: true});
    fs.writeFileSync(resultFile, JSON.stringify(result, null, 2));
    fs.rmSync(temporary, {recursive: true, force: true});
    console.log(JSON.stringify(result));
    process.exitCode = result.ok ? 0 : 1;
  }
})();

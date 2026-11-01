/* Persistent browser + real Qt regression for remembered-phone reconnection. */
"use strict";
const fs = require("fs"), os = require("os"), path = require("path");
const {spawn} = require("child_process");
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const args = process.argv.slice(2);
const option = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const root = path.resolve(__dirname, ".."), temporary = fs.mkdtempSync(path.join(os.tmpdir(), "horas-phone-reconnect-"));
const connectionFile = path.join(temporary, "connection.json"), controlFile = path.join(temporary, "control.json"), profile = path.join(temporary, "browser");
const resultFile = option("--result", path.join(root, "build-diagnostics", "phone-reconnect.json"));
const result = {ok: false};
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const check = (value, message) => { if (!value) throw new Error(message); };
const connection = () => JSON.parse(fs.readFileSync(connectionFile));
async function control(value) {
  const nonce = Math.random().toString(36); const name = controlFile + ".tmp";
  fs.writeFileSync(name, JSON.stringify({...value, nonce})); fs.renameSync(name, controlFile);
  const end = Date.now() + 5000;
  while (Date.now() < end) { if (connection().control_nonce === nonce) return; await wait(50); }
  throw new Error("Qt fixture did not acknowledge control");
}
(async () => {
  let fixture, context, fixtureErrors = "", stage = "startup";
  const errors = [];
  try {
    fixture = spawn(option("--python", process.env.PYTHON || "python"), [path.join(__dirname, "phone_browser_fixture.py"), "--output", connectionFile, "--control", controlFile], {cwd: root, env: {...process.env, QT_QPA_PLATFORM: "offscreen"}, stdio: ["ignore", "ignore", "pipe"]});
    fixture.on("error", error => { fixtureErrors = error.message; });
    fixture.stderr.on("data", chunk => { fixtureErrors = (fixtureErrors + chunk.toString()).slice(-3000); });
    const deadline = Date.now() + 20000;
    while (!fs.existsSync(connectionFile) && fixture.exitCode === null && Date.now() < deadline) await wait(100);
    check(fs.existsSync(connectionFile), "Qt fixture failed to start: " + fixtureErrors);
    const initial = connection();
    const launch = {headless: true, viewport: {width: 390, height: 844}, isMobile: true};
    if (option("--chromium", process.env.CHROMIUM)) launch.executablePath = option("--chromium", process.env.CHROMIUM);
    if (process.env.CI || process.getuid && process.getuid() === 0) launch.args = ["--no-sandbox"];
    async function openBrowser() {
      context = await chromium.launchPersistentContext(profile, launch);
      if (option("--app-script", "")) await context.route("**/app.js", route => route.fulfill({status: 200, contentType: "text/javascript", body: fs.readFileSync(option("--app-script"), "utf8")}));
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(error.message));
      return page;
    }
    const remember = page => page.evaluate(() => localStorage.getItem("horasjogadas-remembered"));
    const token = page => page.evaluate(() => sessionStorage.getItem("horasjogadas-remote"));
    let page = await openBrowser();
    await page.goto(initial.pairing_url);
    await page.locator("#control-view").waitFor({state: "visible"});
    await page.locator("#remember-button").click();
    await page.locator("#remember-name").fill("Reconexão — navegador de teste");
    await page.locator("#remember-confirm").click();
    await page.locator("#remember-dialog").waitFor({state: "hidden"});
    const credential = await remember(page);
    check(Boolean(credential), "Remember opt-in did not save a credential");
    result.remember_opt_in = true;

    stage = "reopen_original_expired_qr";
    await control({expire_pairing: true});
    await context.close(); context = null;
    page = await openBrowser();
    let pairRequests = 0;
    page.on("request", request => { if (new URL(request.url()).pathname === "/api/pair") pairRequests++; });
    await page.goto(initial.pairing_url);
    await page.locator("#control-view").waitFor({state: "visible", timeout: 7000});
    check(await remember(page) === credential, "Reopening original QR erased remembered authorization");
    check(pairRequests === 0, "Reopening original expired QR attempted fresh pairing");
    check(!new URL(page.url()).hash, "QR credential remained in address bar");
    result.browser_restart_expired_qr = true;

    stage = "expired_temporary_session";
    await control({expire_sessions: true});
    await page.reload();
    await page.locator("#control-view").waitFor({state: "visible"});
    check(await remember(page) === credential, "Expired session erased the remembered credential");
    result.expired_session_recovered = true;

    stage = "command_unauthorized";
    const current = await context.request.get(initial.url + "/api/state", {headers: {Authorization: "Bearer " + await token(page)}});
    const baseline = await current.json();
    const target = baseline.games.find(game => game.name === "Hollow Knight");
    check(target && !target.running, "Unexpected fixture timer state");
    let commandRequests = 0;
    await page.route("**/api/command", route => { commandRequests++; return route.fulfill({status: 401, contentType: "application/json", body: JSON.stringify({error: "unauthorized"})}); });
    const game = page.locator(".game-card").filter({has: page.getByRole("heading", {name: "Hollow Knight", exact: true})});
    await game.locator(".start-button").click();
    await page.waitForFunction(() => !document.querySelector("#add-button").disabled);
    check(commandRequests === 1, "Unauthorized mutation was automatically retried");
    check(await remember(page) === credential, "Unauthorized command erased remembered authorization");
    const after = await (await context.request.get(initial.url + "/api/state", {headers: {Authorization: "Bearer " + await token(page)}})).json();
    check(!after.games.find(game => game.id === target.id).running, "Unauthorized command changed timer state");
    await page.unroute("**/api/command");
    result.command_unauthorized_recovers_without_retry = true;

    stage = "temporary_resume_failure";
    await page.evaluate(() => sessionStorage.removeItem("horasjogadas-remote"));
    let resumeRequests = 0;
    await page.route("**/api/resume", route => { resumeRequests++; return resumeRequests === 1 ? route.fulfill({status: 503, contentType: "application/json", body: JSON.stringify({error: "unavailable"})}) : route.continue(); });
    await page.reload();
    await page.waitForFunction(() => Boolean(localStorage.getItem("horasjogadas-remembered")));
    await page.locator("#control-view").waitFor({state: "visible", timeout: 12000});
    check(resumeRequests >= 2 && await remember(page) === credential, "Transient failure erased authorization or did not retry");
    await page.unroute("**/api/resume");
    result.temporary_resume_failure_retains_authorization = true;

    stage = "transient_state_unauthorized_after_resume";
    await page.evaluate(() => sessionStorage.removeItem("horasjogadas-remote"));
    let resumed = false, stateFailures = 0;
    await page.route("**/api/resume", async route => {
      const response = await route.fetch();
      check(response.status() === 200, "Resume fixture was not authorized");
      resumed = true;
      await route.fulfill({response});
    });
    await page.route("**/api/state", route => {
      if (resumed && stateFailures === 0) {
        stateFailures++;
        return route.fulfill({status: 401, contentType: "application/json", body: JSON.stringify({error: "unauthorized"})});
      }
      return route.continue();
    });
    await page.reload();
    await page.locator("#control-view").waitFor({state: "visible", timeout: 12000});
    check(resumed && stateFailures === 1 && await remember(page) === credential, "A state request rejected after valid resume discarded remembered access");
    await page.unroute("**/api/resume"); await page.unroute("**/api/state");
    result.transient_state_unauthorized_retains_authorization = true;

    stage = "plain_browser_restart";
    await context.close(); context = null;
    page = await openBrowser();
    await page.goto(initial.url);
    await page.locator("#control-view").waitFor({state: "visible"});
    check(await remember(page) === credential, "Closing and reopening browser lost saved access");
    result.browser_restart_plain_address = true;

    stage = "explicit_disconnect";
    await page.locator("#disconnect").click();
    await page.locator("#pair-view").waitFor({state: "visible"});
    check(!await remember(page), "Explicit disconnect kept remembered access");
    const revoked = await context.request.post(initial.url + "/api/resume", {headers: {Origin: initial.url, "Content-Type": "application/json"}, data: {remember_token: credential}});
    check(revoked.status() === 401, "Explicit disconnect failed to revoke PC authorization");
    result.explicit_disconnect_revokes = true;

    stage = "fresh_qr_after_rejected_remembered_credential";
    await control({renew: true});
    await page.evaluate(value => { localStorage.setItem("horasjogadas-remembered", value); sessionStorage.removeItem("horasjogadas-remote"); }, credential);
    let rejectedResumes = 0, freshPairs = 0;
    await page.route("**/api/resume", async route => {
      const response = await route.fetch();
      if (response.status() === 401) rejectedResumes++;
      await route.fulfill({response});
    });
    page.on("request", request => { if (new URL(request.url()).pathname === "/api/pair") freshPairs++; });
    // Force a new document: changing only #pair on the same URL does not rerun startup.
    await page.goto("about:blank");
    await page.goto(connection().pairing_url);
    await page.locator("#control-view").waitFor({state: "visible", timeout: 12000});
    check(rejectedResumes >= 1 && freshPairs === 1, "A rejected remembered credential prevented valid QR pairing");
    check(!await remember(page), "Rejected remembered credential was retained after QR fallback");
    check(!new URL(page.url()).hash, "Fresh QR secret remained in address bar");
    await page.unroute("**/api/resume");
    result.fresh_qr_fallback_after_rejected_credential = true;
    await page.locator("#disconnect").click();
    await page.locator("#pair-view").waitFor({state: "visible"});
    check(errors.length === 0, "Unexpected browser errors: " + errors.join(", "));
    result.ok = true;
  } catch (error) {
    result.failed_case = stage;
    result.error = String(error.message).replace(/#pair=[A-Za-z0-9_-]+/g, "#pair=[redacted]");
  } finally {
    if (context) await context.close();
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

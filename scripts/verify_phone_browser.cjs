/* Real browser + Qt + HTTP integration, using a disposable fictitious profile.
 * PLAYWRIGHT_MODULE can point at an existing Playwright installation.
 * node scripts/verify_phone_browser.cjs --python /path/to/python --result /tmp/phone.json
 */
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const {spawn} = require("child_process");
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const args = process.argv.slice(2);
function option(name, fallback) { const index = args.indexOf(name); return index < 0 ? fallback : args[index + 1]; }
const root = path.resolve(__dirname, "..");
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "horas-phone-web-test-"));
const connectionFile = path.join(temporary, "connection.json");
const controlFile = path.join(temporary, "control.json");
const resultFile = option("--result", path.join(root, "build-diagnostics", "phone-browser.json"));
const screenshots = option("--screenshots", "");
const result = {ok: false};
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const check = (condition, message) => { if (!condition) throw new Error(message); };
async function showLibrary(page) {
  if (!await page.locator("#library-section").isVisible()) await page.locator("#focus-toggle").click();
  await page.locator("#library-section").waitFor({state: "visible"});
}
function control(value) { const name = controlFile + ".tmp"; fs.writeFileSync(name, JSON.stringify({...value, nonce: Math.random()})); fs.renameSync(name, controlFile); }
function connection() { return JSON.parse(fs.readFileSync(connectionFile)); }

(async () => {
  let browser, fixture;
  const errors = [], violations = [], artworkRequests = [];
  let fixtureErrors = "";
  try {
    fixture = spawn(option("--python", process.env.PYTHON || "python"), [path.join(__dirname, "phone_browser_fixture.py"), "--output", connectionFile, "--control", controlFile], {cwd: root, env: {...process.env, QT_QPA_PLATFORM: "offscreen"}, stdio: ["ignore", "ignore", "pipe"]});
    fixture.on("error", error => { fixtureErrors = error.message; });
    fixture.stderr.on("data", chunk => { fixtureErrors = (fixtureErrors + chunk.toString()).slice(-4000); });
    const deadline = Date.now() + 20000;
    while (!fs.existsSync(connectionFile) && Date.now() < deadline && fixture.exitCode === null) await wait(100);
    check(fs.existsSync(connectionFile), "Qt fixture failed to start: " + fixtureErrors);
    const initial = connection();
    if (screenshots) {
      fs.mkdirSync(screenshots, {recursive: true});
      for (const [width, height] of [[1240, 820], [840, 620]]) {
        const name = path.join(screenshots, `HorasJogadas-phone-settings-${width}.png`);
        control({size: [width, height], screenshot: name});
        const timeout = Date.now() + 5000;
        while (!fs.existsSync(name) && Date.now() < timeout) await wait(100);
        check(fs.existsSync(name), "Qt settings screenshot failed");
      }
    }
    const launch = {headless: true};
    if (option("--chromium", process.env.CHROMIUM)) launch.executablePath = option("--chromium", process.env.CHROMIUM);
    if (process.env.CI || process.getuid && process.getuid() === 0) launch.args = ["--no-sandbox"];
    browser = await chromium.launch(launch);
    const context = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true});
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => { if (request.url().includes("/api/art/")) artworkRequests.push({url: request.url(), authorization: request.headers().authorization}); });
    page.on("dialog", async dialog => { errors.push("Unexpected JavaScript dialog"); await dialog.dismiss(); });
    await page.exposeFunction("reportCSP", value => violations.push(value));
    await page.addInitScript(() => document.addEventListener("securitypolicyviolation", event => window.reportCSP(event.violatedDirective)));
    const response = await page.goto(initial.url);
    const policy = await response.headerValue("content-security-policy") || "";
    check(policy.includes("default-src 'none'") && policy.includes("script-src 'self'") && !policy.includes("script-src 'self' 'unsafe-inline'"), "Missing restrictive CSP");
    await page.locator("#pair-code").fill(initial.code === "000000" ? "111111" : "000000");
    await page.locator("#pair-button").click();
    await page.waitForFunction(() => document.querySelector("#pair-message").textContent.includes("Código não reconhecido"));
    result.wrong_code_message = true;
    await page.locator("#remember-device").check();
    await page.locator("#device-name").fill("Sala — celular de teste");
    await page.locator("#pair-code").fill(initial.code);
    await page.locator("#pair-button").click();
    await page.locator("#control-view").waitFor({state: "visible"});
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "390px horizontal overflow");
    result.manual_pair = true;
    await page.reload();
    await page.locator("#control-view").waitFor({state: "visible"});
    result.reload_session = true;
    check(Boolean(await page.evaluate(() => localStorage.getItem("horasjogadas-remembered"))), "Remembered-device choice was not persisted");
    await page.evaluate(() => sessionStorage.removeItem("horasjogadas-remote"));
    await page.reload();
    await page.locator("#control-view").waitFor({state: "visible"});
    result.remembered_resume = true;
    control({restart: true});
    await wait(350);
    await page.evaluate(() => sessionStorage.removeItem("horasjogadas-remote"));
    await page.reload();
    await page.locator("#control-view").waitFor({state: "visible"});
    result.remembered_server_restart = true;

    await page.locator("#shortcut-button").click();
    await page.locator("#shortcut-dialog").waitFor({state: "visible"});
    const offlineLink = await page.locator("#shortcut-dialog a[href*='/celular/']").getAttribute("href");
    check(offlineLink.startsWith("https://"), "Offline companion link must use HTTPS");
    await page.locator("#shortcut-dialog .dialog-cancel").click();
    result.shortcut_guidance = true;

    const game = page.locator(".game-card").filter({has: page.getByRole("heading", {name: "Hollow Knight", exact: true})});
    await game.locator(".favorite-button").click();
    await page.waitForFunction(() => document.querySelector("#favorite-games .favorite-button[aria-pressed='true']"));
    check(await page.locator("#favorite-section").isVisible(), "Favorite section did not appear");
    await page.reload();
    await page.locator("#favorite-section").waitFor({state: "visible"});
    result.favorites_persisted = true;
    await game.locator(".start-button").click();
    await page.waitForFunction(() => document.querySelector("#active-games .game-card.running"));
    await page.waitForFunction(() => document.querySelector("#active-games .game-card.focus-game"));
    check(!await page.locator("#library-section").isVisible(), "Playing-now mode should focus on active sessions");
    result.playing_now_focus = true;
    control({covers_enabled: true, icons_enabled: true});
    await page.waitForFunction(() => {
      const card = document.querySelector("#active-games .game-card");
      const cover = card && card.querySelector("img.card-cover"), avatar = card && card.querySelector(".avatar img");
      return cover && avatar && cover.complete && cover.naturalWidth > 0 && avatar.complete && avatar.naturalWidth > 0;
    });
    check(artworkRequests.length >= 2, "Artwork was not loaded from the authenticated server");
    check(artworkRequests.every(request => /^Bearer /.test(request.authorization || "") && !/[?&](?:token|authorization)=/i.test(request.url)), "Artwork credentials were leaked into URLs or omitted");
    const loadedCount = artworkRequests.length;
    await wait(2200);
    check(artworkRequests.length === loadedCount, "Polling unnecessarily downloaded artwork again");
    result.authenticated_artwork = true;
    for (const width of [320, 390, 1040]) {
      for (const height of width <= 390 ? [740, 844] : [844]) {
        await page.setViewportSize({width, height});
        await page.evaluate(() => scrollTo(0, 0));
        check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "Playing-now horizontal overflow at " + width);
        const bounds = await game.getByRole("button", {name: "Pausar · Hollow Knight", exact: true}).boundingBox();
        check(bounds && bounds.y + bounds.height <= height, "Playing-now pause control is below the first screen at " + width + "x" + height);
      }
    }
    await page.setViewportSize({width: 390, height: 844});
    result.focus_controls_in_first_screen = true;
    if (screenshots) await page.screenshot({path: path.join(screenshots, "HorasJogadas-phone-focus.png")});
    control({covers_enabled: false, icons_enabled: false});
    await page.waitForFunction(() => {
      const card = document.querySelector("#active-games .game-card");
      return card && !Array.from(card.querySelectorAll(".cover-frame, .avatar img")).some(el => !el.hidden && el.getClientRects().length);
    });
    result.artwork_preferences = true;
    await wait(1150);
    await game.getByRole("button", {name: "Pausar · Hollow Knight", exact: true}).click();
    await page.waitForFunction(() => document.querySelector("#active-games .game-card.paused"));
    await game.locator(".start-button").click();
    await page.waitForFunction(() => document.querySelector("#active-games .game-card.running"));
    result.start_pause_resume = true;
    if (screenshots) {
      await page.screenshot({path: path.join(screenshots, "HorasJogadas-phone-original.png"), fullPage: true});
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({path: path.join(screenshots, "HorasJogadas-phone-viewport.png")});
    }
    await game.locator(".stop-button").click();
    control({invalidate: true});
    await wait(250);
    await page.locator("#finish-confirm").click();
    await page.locator("#finish-dialog").waitFor({state: "hidden"});
    check(await page.locator("#active-games .game-card").count() === 1, "Conflicting finish unexpectedly ended the session");
    await game.locator(".stop-button").click();
    await page.locator("#finish-dialog").waitFor({state: "visible"});
    result.finish_conflict_requires_reconfirm = true;
    await page.locator("#finish-confirm").click();
    await page.locator("#finish-dialog").waitFor({state: "hidden"});
    await page.waitForFunction(() => !document.querySelector("#active-games .game-card.running"));
    result.finish = true;
    await page.locator("#summary-dialog").waitFor({state: "visible"});
    check((await page.locator("#summary-dialog").textContent()).includes("Hollow Knight"), "Saved-session summary is missing game name");
    if (screenshots) await page.screenshot({path: path.join(screenshots, "HorasJogadas-phone-summary.png")});
    await page.locator("#summary-close").click();
    result.saved_summary = true;
    await showLibrary(page);
    if (screenshots) await page.screenshot({path: path.join(screenshots, "HorasJogadas-phone-favorites.png")});

    await page.locator("#add-button").click();
    const hostileName = "PS5 <img src=x onerror=alert(1)>";
    await page.locator("#game-name").fill(hostileName);
    await page.locator("#add-confirm").click();
    await page.locator("#add-dialog").waitFor({state: "hidden"});
    check(await page.getByText(hostileName, {exact: true}).count() === 1, "Game name was not rendered literally");
    check(await page.locator(".game-name img").count() === 0, "Unsafe game name rendering");
    result.add_and_escaped_names = true;
    await page.locator("#search").fill("hollow");
    await wait(2200);
    check(await page.locator("#search").inputValue() === "hollow", "Polling reset search input");
    check(await page.locator(".game-card:visible").count() === 1, "Search did not filter the library");
    await page.locator("#search").fill("");
    result.search_preserved = true;

    await page.route("**/api/state", async route => { await wait(400); await route.continue(); });
    await page.evaluate(() => {
      Object.defineProperty(document, "hidden", {configurable: true, get: () => true});
      document.dispatchEvent(new Event("visibilitychange"));
    });
    check(await page.locator("#add-button").isDisabled(), "Background controls remained enabled");
    await page.evaluate(() => {
      Object.defineProperty(document, "hidden", {configurable: true, get: () => false});
      document.dispatchEvent(new Event("visibilitychange"));
    });
    check(await page.locator("#add-button").isDisabled(), "Controls enabled before fresh state on resume");
    await page.waitForFunction(() => !document.querySelector("#add-button").disabled);
    await page.unroute("**/api/state");
    result.resume_requires_fresh_state = true;

    await context.setOffline(true);
    await page.waitForFunction(() => document.querySelector("#add-button").disabled);
    await context.setOffline(false);
    await page.waitForFunction(() => !document.querySelector("#add-button").disabled);
    result.offline_controls = true;
    for (const theme of ["dark", "original", "violet", "light"]) {
      control({theme, language: theme === "light" ? "en" : "pt"});
      await page.waitForFunction(name => document.documentElement.dataset.theme === name, theme);
      for (const width of [320, 390, 1040]) {
        await page.setViewportSize({width, height: 820});
        check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), theme + ": horizontal overflow at " + width);
        if (screenshots && theme === "light" && width === 320) await page.screenshot({path: path.join(screenshots, "HorasJogadas-phone-light-320.png"), fullPage: true});
      }
    }
    result.themes_and_responsive = true;
    check(await page.locator("#library-title").textContent() === "Library", "English translation missing");
    result.english = true;
    const [libraryDownload] = await Promise.all([page.waitForEvent("download"), page.locator("#export-library").click()]);
    const libraryFile = await libraryDownload.path();
    const library = JSON.parse(fs.readFileSync(libraryFile, "utf8"));
    check(library.format === "HorasJogadas-Library" && library.version === 1 && Array.isArray(library.games), "Library export format is invalid");
    check(library.games.some(item => item.name === "Hollow Knight" && typeof item.id === "string"), "Library export omitted games or IDs");
    check(!Object.keys(library).some(key => /token|secret|credential/i.test(key)), "Library export contains credentials");
    result.library_transfer = true;

    const oldRemember = await page.evaluate(() => localStorage.getItem("horasjogadas-remembered"));
    check(/^[A-Za-z0-9_-]{40,}$/.test(oldRemember || ""), "Remembered credential has unexpected storage shape");
    const oldToken = await page.evaluate(() => sessionStorage.getItem("horasjogadas-remote"));
    await page.locator("#disconnect").click();
    await page.locator("#pair-view").waitFor({state: "visible"});
    check(!await page.evaluate(() => sessionStorage.getItem("horasjogadas-remote")), "Local session remained after disconnect");
    const revoked = await context.request.get(initial.url + "/api/state", {headers: {Authorization: "Bearer " + oldToken}});
    check(revoked.status() === 401, "Disconnected session was not revoked on PC");
    check(!await page.evaluate(() => localStorage.getItem("horasjogadas-remembered")), "Remembered credential remained after disconnect");
    const rememberedRevoked = await context.request.post(initial.url + "/api/resume", {headers: {Origin: initial.url, "Content-Type": "application/json"}, data: {remember_token: oldRemember}});
    check(rememberedRevoked.status() === 401, "Disconnect did not revoke remembered device credential");
    result.disconnect_revoked = true;

    // A delayed auto-resume must not undo a deliberate disconnect.
    const raceContext = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true});
    const racePage = await raceContext.newPage();
    racePage.on("pageerror", error => errors.push(error.message));
    await racePage.goto(initial.url);
    await racePage.locator("#remember-device").check();
    await racePage.locator("#device-name").fill("Teste de desconexão");
    await racePage.locator("#pair-code").fill(connection().code);
    await racePage.locator("#pair-button").click();
    await racePage.locator("#control-view").waitFor({state: "visible"});
    let releaseResume, resumeSeen;
    const resumeStarted = new Promise(resolve => { resumeSeen = resolve; });
    const holdResume = new Promise(resolve => { releaseResume = resolve; });
    await racePage.route("**/api/resume", async route => {
      const pending = await route.fetch();
      resumeSeen(pending.status());
      await holdResume;
      await route.fulfill({response: pending});
    });
    try {
      control({restart: true});
      const resumeStatus = await Promise.race([resumeStarted, wait(7000).then(() => { throw new Error("Remembered auto-resume did not begin after server restart"); })]);
      check(resumeStatus === 200, "Delayed resume fixture did not produce an authorized response");
      await racePage.locator("#disconnect").click();
      await racePage.locator("#pair-view").waitFor({state: "visible"});
      releaseResume();
      await wait(2300);
      check(await racePage.locator("#pair-view").isVisible() && !await racePage.locator("#control-view").isVisible(), "A late auto-resume response reauthenticated after explicit disconnect");
      check(!await racePage.evaluate(() => sessionStorage.getItem("horasjogadas-remote") || localStorage.getItem("horasjogadas-remembered")), "A late auto-resume restored credentials after disconnect");
      result.disconnect_cancels_pending_resume = true;
    } finally {
      releaseResume();
      await raceContext.close();
    }
    const qrContext = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true});
    const qrPage = await qrContext.newPage();
    qrPage.on("pageerror", error => errors.push(error.message));
    await qrPage.goto(connection().pairing_url);
    await qrPage.locator("#control-view").waitFor({state: "visible"});
    check(!new URL(qrPage.url()).hash, "Pairing fragment remained in address bar");
    result.qr_pair_and_fragment_scrub = true;
    check(!await qrPage.evaluate(() => localStorage.getItem("horasjogadas-remembered")), "QR pairing unexpectedly remembered the phone without opt-in");
    result.remember_opt_in = true;
    check(errors.length === 0, "Browser errors: " + errors.join(", "));
    check(violations.length === 0, "CSP violations: " + violations.join(", "));
    result.csp = true;
    control({stop: true});
    await qrPage.waitForFunction(() => document.querySelector("#add-button").disabled);
    result.stop_revoked = true;
    result.ok = true;
  } catch (error) {
    result.error = String(error.message).replace(/#pair=[A-Za-z0-9_-]+/g, "#pair=[redacted]");
  } finally {
    if (browser) await browser.close();
    if (fixture && fixture.exitCode === null) {
      control({quit: true});
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

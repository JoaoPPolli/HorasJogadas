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
function control(value) { const name = controlFile + ".tmp"; fs.writeFileSync(name, JSON.stringify({...value, nonce: Math.random()})); fs.renameSync(name, controlFile); }
function connection() { return JSON.parse(fs.readFileSync(connectionFile)); }

(async () => {
  let browser, fixture;
  const errors = [], violations = [];
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
    await page.locator("#pair-code").fill(initial.code);
    await page.locator("#pair-button").click();
    await page.locator("#control-view").waitFor({state: "visible"});
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "390px horizontal overflow");
    result.manual_pair = true;
    await page.reload();
    await page.locator("#control-view").waitFor({state: "visible"});
    result.reload_session = true;

    const game = page.locator(".game-card").filter({has: page.getByRole("heading", {name: "Hollow Knight", exact: true})});
    await game.locator(".start-button").click();
    await page.waitForFunction(() => document.querySelector("#active-games .game-card.running"));
    await wait(1150);
    await game.locator(".icon-button").first().click();
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

    const oldToken = await page.evaluate(() => sessionStorage.getItem("horasjogadas-remote"));
    await page.locator("#disconnect").click();
    await page.locator("#pair-view").waitFor({state: "visible"});
    check(!await page.evaluate(() => sessionStorage.getItem("horasjogadas-remote")), "Local session remained after disconnect");
    const revoked = await context.request.get(initial.url + "/api/state", {headers: {Authorization: "Bearer " + oldToken}});
    check(revoked.status() === 401, "Disconnected session was not revoked on PC");
    result.disconnect_revoked = true;
    const qrContext = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true});
    const qrPage = await qrContext.newPage();
    qrPage.on("pageerror", error => errors.push(error.message));
    await qrPage.goto(connection().pairing_url);
    await qrPage.locator("#control-view").waitFor({state: "visible"});
    check(!new URL(qrPage.url()).hash, "Pairing fragment remained in address bar");
    result.qr_pair_and_fragment_scrub = true;
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

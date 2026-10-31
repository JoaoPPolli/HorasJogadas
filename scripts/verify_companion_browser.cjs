/* Real offline PWA test with a loopback HTTP origin and disposable browser data. */
"use strict";
const fs = require("fs");
const path = require("path");
const http = require("http");
const {spawnSync} = require("child_process");
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const args = process.argv.slice(2);
function option(name, fallback) { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; }
const root = path.resolve(__dirname, "..", "site");
const resultFile = option("--result", path.resolve(__dirname, "..", "build-diagnostics", "companion-browser.json"));
const screenshots = option("--screenshots", "");
const KEY = "horasjogadas-companion-v1";
const result = {ok: false};
const unexpectedRequests = [];
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const check = (ok, message) => { if (!ok) throw new Error(message); };
const server = http.createServer((req, res) => {
  try {
    if (req.method !== "GET" && req.method !== "HEAD") { unexpectedRequests.push(req.method); res.writeHead(405); res.end(); return; }
    const pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    if (!pathname.startsWith("/HorasJogadas/")) { res.writeHead(404); res.end(); return; }
    const relative = pathname.slice("/HorasJogadas/".length);
    let target = path.resolve(root, relative);
    if (target !== root && !target.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
    if (fs.statSync(target).isDirectory()) target = path.join(target, "index.html");
    const types = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".webmanifest": "application/manifest+json", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/vnd.microsoft.icon"};
    res.writeHead(200, {"Content-Type": types[path.extname(target)] || "application/octet-stream", "Cache-Control": "no-store"});
    res.end(fs.readFileSync(target));
  } catch (_) { res.writeHead(404); res.end(); }
});

(async () => {
  let browser;
  const errors = [];
  try {
    await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
    const url = `http://127.0.0.1:${server.address().port}/HorasJogadas/celular/`;
    const launch = {headless: true};
    if (option("--chromium", process.env.CHROMIUM)) launch.executablePath = option("--chromium", process.env.CHROMIUM);
    if (process.env.CI || process.getuid && process.getuid() === 0) launch.args = ["--no-sandbox"];
    browser = await chromium.launch(launch);
    const context = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, acceptDownloads: true});
    context.on("request", request => {
      if (/^https?:/.test(request.url()) && new URL(request.url()).hostname !== "127.0.0.1") unexpectedRequests.push(request.method() + " external");
    });
    let page = await context.newPage();
    page.on("pageerror", e => errors.push(e.message));
    await page.goto(url);
    await page.locator("#game-name").waitFor({state: "visible"});
    await page.evaluate(async () => { await Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => setTimeout(() => reject(new Error("Service worker did not become ready")), 12000))]); });
    await page.reload();
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
    const manifest = await page.locator('link[rel="manifest"]').getAttribute("href");
    check(Boolean(manifest), "Install manifest missing");
    const manifestResponse = await context.request.get(new URL(manifest, url).href);
    const installManifest = await manifestResponse.json();
    for (const size of [192, 512]) {
      const icon = installManifest.icons.find(item => item.sizes === `${size}x${size}` && item.type === "image/png");
      check(Boolean(icon), "Missing install icon " + size);
      const response = await context.request.get(new URL(icon.src, url).href);
      const png = await response.body();
      check(png.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && png.readUInt32BE(16) === size && png.readUInt32BE(20) === size, "Install icon dimensions invalid");
    }
    result.service_worker_and_install = true;
    await context.setOffline(true);
    await page.reload();
    await page.locator("#game-name").waitFor({state: "visible"});
    result.offline_reload = true;
    await page.locator("#game-name").fill("Jogo do PS5");
    await page.locator("#start-button").click();
    await page.waitForFunction(key => Boolean(JSON.parse(localStorage.getItem(key)).active), KEY);
    await wait(1300);
    await page.waitForFunction(() => document.querySelector("#current-time").textContent !== "00:00:00", null, {timeout: 5000});
    if (screenshots) {
      fs.mkdirSync(screenshots, {recursive: true});
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({path: path.join(screenshots, "HorasJogadas-companion-playing.png")});
    }
    await page.locator("#pause-button").click();
    let state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
    check(state.active && state.active.segment_at === null, "Pause was not saved");
    const pausedMs = state.active.accumulated_ms;
    await wait(600);
    await page.reload();
    await page.locator("#resume-button").waitFor({state: "visible"});
    state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
    check(state.active.accumulated_ms === pausedMs, "Reload counted paused time");
    await page.locator("#resume-button").click();
    await wait(1200);
    await page.locator("#finish-button").click();
    await page.locator("#finish-save").click();
    await page.waitForFunction(key => JSON.parse(localStorage.getItem(key)).sessions.length === 1, KEY);
    state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
    check(!state.active, "Finished timer is still active");
    const completed = state.sessions[0];
    check(completed.seconds >= 2 && completed.seconds < 10, "Timer did not preserve correct play time");
    check(Date.parse(completed.ended_at) >= Date.parse(completed.started_at), "Session times invalid");
    result.offline_start_pause_resume_finish = true;
    if (await page.locator("#summary-dialog").isVisible()) await page.locator('[data-close="summary-dialog"]').click();

    const downloadPromise = page.waitForEvent("download");
    await page.locator("#export-button").click();
    const downloaded = await downloadPromise;
    const downloadPath = await downloaded.path();
    const transfer = JSON.parse(fs.readFileSync(downloadPath, "utf8"));
    check(transfer.format === "HorasJogadas-Mobile" && transfer.version === 1 && transfer.sessions.length === 1, "Transfer format invalid");
    check(transfer.sessions[0].id === completed.id, "Export changed immutable session ID");
    check(transfer.sessions[0].seconds === completed.seconds, "Export changed duration");
    if (option("--export-fixture", "")) {
      const target = option("--export-fixture", ""); fs.mkdirSync(path.dirname(target), {recursive: true}); fs.writeFileSync(target, JSON.stringify(transfer, null, 2));
    }
    check((await page.evaluate(key => JSON.parse(localStorage.getItem(key)).sessions.length, KEY)) === 1, "Export removed the only copy");
    result.export_keeps_original = true;
    if (option("--python", "")) {
      const verify = spawnSync(option("--python", ""), [path.resolve(__dirname, "verify_phone_import.py"), downloadPath], {cwd: path.resolve(__dirname, ".."), env: {...process.env, QT_QPA_PLATFORM: "offscreen"}, encoding: "utf8", timeout: 30000});
      check(verify.status === 0, "Desktop import of browser export failed: " + (verify.error ? verify.error.message : (verify.stdout + verify.stderr).slice(-2000)));
      let evidence;
      try { evidence = JSON.parse(verify.stdout.trim()); } catch (_) { throw new Error("Desktop import verifier did not return JSON evidence"); }
      check(evidence.ok === true, "Desktop import verifier failed");
      result.desktop_import_roundtrip = true;
    }
    await context.setOffline(false);
    await page.locator("#options").evaluate(el => { el.open = true; });
    const library = {format: "HorasJogadas-Library", version: 1, games: [{id: "game-1", name: "Hollow Knight"}, {id: "game-2", name: "PS5 <img src=x onerror=alert(1)>"}], theme: "original", language: "pt"};
    await page.locator("#library-file").setInputFiles({name: "biblioteca.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(library))});
    await page.waitForFunction(key => JSON.parse(localStorage.getItem(key)).games.some(g => g.pc_id === "game-1" || g.id === "game-1"), KEY);
    check(await page.locator(".game-favorite").count() >= 2, "Imported library has no favorite controls");
    await page.locator(".game-favorite").first().click();
    state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
    check(state.games.some(g => g.favorite), "Favorite was not saved");
    check(await page.locator('img[src="x"]').count() === 0, "Imported game executed HTML");
    result.library_and_favorites = true;

    for (const theme of ["dark", "original", "violet", "light"]) {
      await page.locator("#theme").selectOption(theme);
      for (const width of [320, 390, 1040]) {
        await page.setViewportSize({width, height: 844});
        check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), theme + " horizontal overflow at " + width);
      }
    }
    await page.locator("#language").selectOption("en");
    check(await page.evaluate(() => document.documentElement.lang.startsWith("en")), "English is missing");
    await page.locator("#language").selectOption("pt");
    await page.locator("#theme").selectOption("original");
    await page.setViewportSize({width: 390, height: 844});
    await page.locator("#options").evaluate(el => { el.open = false; });
    if (screenshots) {
      fs.mkdirSync(screenshots, {recursive: true});
      await page.screenshot({path: path.join(screenshots, "HorasJogadas-companion.png"), fullPage: true});
    }
    result.themes_and_responsive = true;

    const second = await context.newPage();
    await second.goto(url);
    await second.locator("#readonly").waitFor({state: "visible"});
    check(await second.locator("#start-button").isDisabled(), "Second tab can overwrite the timer");
    await page.close();
    await second.locator("#take-control").click();
    await second.waitForFunction(() => !document.querySelector("#start-button").disabled);
    page = second;
    result.single_writer_tabs = true;

    const beforeFailure = await page.evaluate(key => localStorage.getItem(key), KEY);
    await page.locator("#game-name").fill("Armazenamento cheio");
    await page.evaluate(key => {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = function (name, value) { if (name === key) throw new DOMException("Fake full storage", "QuotaExceededError"); return original.call(this, name, value); };
    }, KEY);
    await page.locator("#start-button").click();
    await page.locator("#storage-error").waitFor({state: "visible"});
    check(await page.evaluate(key => localStorage.getItem(key), KEY) === beforeFailure, "Failed storage overwrote prior data");
    check(!await page.evaluate(key => JSON.parse(localStorage.getItem(key)).active, KEY), "Failed start was shown as saved");
    result.storage_failure_preserves_data = true;
    await page.reload();
    await page.locator("#game-name").fill("Clock review");
    await page.locator("#start-button").click();
    await page.waitForFunction(key => Boolean(JSON.parse(localStorage.getItem(key)).active), KEY);
    await page.evaluate(() => { const real = Date.now; Date.now = () => real() - 60000; document.dispatchEvent(new Event("visibilitychange")); });
    await page.locator("#clock-review").waitFor({state: "visible"});
    state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
    check(state.active.needs_review, "Clock rollback did not require review");
    await page.locator("#review-seconds").fill("3");
    await page.locator("#review-apply").click();
    await page.waitForFunction(key => !JSON.parse(localStorage.getItem(key)).active.needs_review, KEY);
    await page.reload();
    await page.locator("#resume-button").click();
    await page.evaluate(() => { const real = Date.now; Date.now = () => real() + 48 * 3600000; document.dispatchEvent(new Event("visibilitychange")); });
    await page.locator("#clock-review").waitFor({state: "visible"});
    state = await page.evaluate(key => JSON.parse(localStorage.getItem(key)), KEY);
    check(state.active.needs_review, "Large clock jump did not require review");
    result.clock_changes_require_review = true;
    await page.close();

    const corruptContext = await browser.newContext();
    const corrupt = await corruptContext.newPage();
    await corrupt.addInitScript(key => localStorage.setItem(key, "{invalid stored data"), KEY);
    await corrupt.goto(url);
    await corrupt.locator("#storage-error").waitFor({state: "visible"});
    check(await corrupt.evaluate(key => localStorage.getItem(key), KEY) === "{invalid stored data", "Corrupt data was overwritten");
    check(await corrupt.locator("#start-button").isDisabled(), "Corrupt profile can be silently replaced");
    result.corrupt_storage_preserved = true;
    const retryContext = await browser.newContext();
    const retry = await retryContext.newPage();
    await retry.addInitScript(({key, originalData}) => {
      localStorage.setItem(key, originalData);
      const original = Storage.prototype.getItem;
      Storage.prototype.getItem = function (name) { if (name === key) throw new DOMException("Fake temporarily unavailable", "SecurityError"); return original.call(this, name); };
      window.restoreCompanionReads = () => { Storage.prototype.getItem = original; };
    }, {key: KEY, originalData: beforeFailure});
    await retry.goto(url);
    await retry.locator("#storage-error").waitFor({state: "visible"});
    check(await retry.locator("#start-button").isDisabled(), "Unreadable storage allows overwrite");
    await retry.evaluate(() => window.restoreCompanionReads());
    await retry.locator("#storage-error button").last().click();
    await retry.waitForFunction(() => !document.querySelector("#start-button").disabled);
    check(await retry.evaluate(key => localStorage.getItem(key), KEY) === beforeFailure, "Storage recovery overwrote preserved sessions");
    await retry.locator("#game-name").fill("Leitura recuperada");
    await retry.locator("#start-button").click();
    await retry.waitForFunction(key => Boolean(JSON.parse(localStorage.getItem(key)).active), KEY);
    check(await retry.evaluate(key => JSON.parse(localStorage.getItem(key)).sessions.length, KEY) === 1, "Storage recovery lost previous sessions");
    result.storage_access_retry_recovers = true;
    await wait(1150);
    const beforeFinishFailure = await retry.evaluate(key => localStorage.getItem(key), KEY);
    await retry.locator("#finish-button").click();
    await retry.evaluate(key => {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = function (name, value) { if (name === key) throw new DOMException("Fake full storage", "QuotaExceededError"); return original.call(this, name, value); };
    }, KEY);
    await retry.locator("#finish-save").click();
    await retry.locator("#storage-error").waitFor({state: "visible"});
    check(!await retry.locator("#finish-dialog").isVisible(), "Storage failure trapped user behind a modal");
    check(await retry.evaluate(key => localStorage.getItem(key), KEY) === beforeFinishFailure, "Failed finish overwrote the active session");
    result.failed_finish_preserves_active = true;
    check(errors.length === 0, "Browser errors: " + errors.join(", "));
    check(unexpectedRequests.length === 0, "Offline data must not be sent to a service: " + unexpectedRequests.join(", "));
    result.no_external_data_requests = true;
    result.ok = true;
  } catch (e) { result.error = e.message; }
  finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    fs.mkdirSync(path.dirname(resultFile), {recursive: true});
    fs.writeFileSync(resultFile, JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
    process.exitCode = result.ok ? 0 : 1;
  }
})();

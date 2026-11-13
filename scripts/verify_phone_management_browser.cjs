/* Management actions through the real authenticated phone UI, with fake PC data. */
"use strict";
const fs = require("fs"), os = require("os"), path = require("path");
const {spawn} = require("child_process");
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const args = process.argv.slice(2), option = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const root = path.resolve(__dirname, ".."), temporary = fs.mkdtempSync(path.join(os.tmpdir(), "horas-phone-management-"));
const connectionFile = path.join(temporary, "connection.json"), controlFile = path.join(temporary, "control.json");
const resultFile = option("--result", path.join(root, "build-diagnostics", "phone-management-browser.json"));
const screenshots = option("--screenshots", ""), result = {ok: false};
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const check = (condition, message) => { if (!condition) throw Error(message); };
const connection = () => JSON.parse(fs.readFileSync(connectionFile));
async function control(value) { const nonce = Math.random().toString(36), target = controlFile + ".tmp"; fs.writeFileSync(target, JSON.stringify({...value, nonce})); fs.renameSync(target, controlFile); const deadline = Date.now() + 5000; while (Date.now() < deadline) { if (connection().control_nonce === nonce) return; await wait(50); } throw Error("Qt fixture did not acknowledge command"); }
(async () => {
 let browser, fixture, page, fixtureErrors = "", stage = "startup";
 const errors = [], csp = [];
 try {
  fixture = spawn(option("--python", process.env.PYTHON || "python"), [path.join(__dirname, "phone_browser_fixture.py"), "--output", connectionFile, "--control", controlFile], {cwd: root, env: {...process.env, QT_QPA_PLATFORM: "offscreen"}, stdio: ["ignore", "ignore", "pipe"]});
  fixture.on("error", error => { fixtureErrors = error.message; }); fixture.stderr.on("data", chunk => { fixtureErrors = (fixtureErrors + chunk.toString()).slice(-4000); });
  const deadline = Date.now() + 20000; while (!fs.existsSync(connectionFile) && Date.now() < deadline && fixture.exitCode === null) await wait(100);
  check(fs.existsSync(connectionFile), "Fixture failed: " + fixtureErrors);
  const launch = {headless: true}; if (option("--chromium", process.env.CHROMIUM)) launch.executablePath = option("--chromium", process.env.CHROMIUM); if (process.env.CI || process.getuid && process.getuid() === 0) launch.args = ["--no-sandbox"];
  browser = await chromium.launch(launch);
  const context = await browser.newContext({viewport:{width:390,height:844}, isMobile:true, acceptDownloads:true});
  page = await context.newPage(); page.on("pageerror", error => errors.push(error.message)); page.on("dialog", async dialog => {errors.push("Unexpected native dialog"); await dialog.dismiss();});
  await page.exposeFunction("managementCSP", directive => csp.push(directive)); await page.addInitScript(() => document.addEventListener("securitypolicyviolation", event => window.managementCSP(event.violatedDirective)));
  await page.goto(connection().pairing_url); await page.locator("#control-view").waitFor({state:"visible"});
  const api = (url, body) => page.evaluate(({url,body}) => window.HorasPhone.api(url,body), {url,body});
  async function settings() { await page.locator("#desktop-nav [data-page='settings']").click(); await page.locator("#phone-settings-save").waitFor({state:"visible"}); }
  async function refresh() { await page.evaluate(async()=>{await window.HorasPhone.refresh(); await window.HorasManagement.refresh(true);}); }
  async function choose(button, filename) { const chooser = page.waitForEvent("filechooser"); await button.click(); await (await chooser).setFiles(filename); }
  async function closeManagement() { const dialogs = page.locator("dialog.management-dialog:visible"); while(await dialogs.count()) { await dialogs.last().getByRole("button",{name:/^(Cancelar|Fechar|Cancel|Close)$/}).click(); } }
  async function snapshot(name) { if(!screenshots) return; fs.mkdirSync(screenshots,{recursive:true}); await page.evaluate(()=>scrollTo(0,0)); await page.screenshot({path:path.join(screenshots,"HorasJogadas-connected-management-"+name+".png")}); }
  const initial = await api("/api/state"), game = initial.games.find(item=>item.name==="Hollow Knight"); check(game,"Expected synthetic game missing");

  stage = "settings_preferences"; await settings();
  await page.locator("#phone-settings-theme").selectOption("violet"); await page.locator("#phone-settings-covers").check(); await page.locator("#phone-settings-save").click();
  await page.waitForFunction(()=>document.documentElement.dataset.theme==="violet");
  let preferences = await api("/api/view/settings"); check(preferences.theme==="violet" && preferences.covers_enabled,"Preferences not saved on PC"); result.settings_saved_on_pc=true;
  await snapshot("settings");

  stage = "stale_settings_draft"; await page.locator("#phone-settings-theme").selectOption("light"); await control({theme:"original",language:"pt"});
  await page.locator("#phone-settings-save").click();
  await page.waitForFunction(()=>document.querySelector("#management-appearance .management-message").textContent.includes("mudaram"));
  preferences = await api("/api/view/settings"); check(preferences.theme==="original","Stale phone draft replaced PC settings");
  check(await page.locator("#phone-settings-theme").inputValue()==="light","Polling erased unsaved settings draft");
  await page.locator("#management-appearance").getByRole("button",{name:"Recarregar",exact:true}).click();
  await page.waitForFunction(()=>document.querySelector("#phone-settings-theme").value==="original"); result.stale_settings_preserved=true;

  stage = "backups_create_download";
  const backupAcknowledged=page.waitForResponse(response=>response.url().endsWith('/api/command')&&response.request().postDataJSON()?.action==='backup_create');
  await page.locator("#phone-backup-create").click();
  const backupResponse=await backupAcknowledged;check(backupResponse.status()===200,"Backup creation was rejected: "+backupResponse.status());
  await page.waitForFunction(()=>!document.querySelector("#phone-backup-create").disabled);
  const backupList = await api("/api/view/backups"); check(backupList.full.length>0,"Backup not created on PC");
  const [backupDownload] = await Promise.all([page.waitForEvent("download"),page.locator("#phone-backup-download").click()]);
  const backupPath = path.join(temporary,"records.zip"); await backupDownload.saveAs(backupPath); check(fs.statSync(backupPath).size>0,"Backup download empty"); result.backup_create_and_download=true;

  stage = "backup_upload_review_cancel";
  await choose(page.locator("#phone-backup-upload"),backupPath);
  let restore = page.locator("dialog.management-dialog:visible"); await restore.getByRole("heading",{name:"Restaurar estes dados?"}).waitFor();
  const beforeCancel = await api("/api/view/history"); await restore.getByRole("button",{name:"Cancelar",exact:true}).click();
  check((await api("/api/view/history")).total===beforeCancel.total,"Cancel backup preview changed history"); result.backup_preview_cancel_safe=true;

  stage = "backup_upload_restore";
  await choose(page.locator("#phone-backup-upload"),backupPath); restore = page.locator("dialog.management-dialog:visible");
  await restore.getByRole("checkbox",{name:"Conferi os dados e quero restaurar"}).check(); await page.locator("#phone-backup-restore-confirm").click();
  await restore.waitFor({state:"hidden"}); check((await api("/api/view/history")).total===beforeCancel.total,"Restore lost history"); result.backup_upload_restore=true;
  await refresh();

  stage = "backup_saved_on_pc_restore";
  const savedBackups = page.locator("#management-backups details").filter({has:page.locator("summary",{hasText:"Backups guardados no PC"})});
  await savedBackups.locator("summary").click(); await savedBackups.getByRole("button",{name:"Restaurar",exact:true}).first().click();
  restore = page.locator("dialog.management-dialog:visible"); await restore.getByRole("checkbox",{name:"Conferi os dados e quero restaurar"}).check();
  await restore.locator("#phone-backup-restore-confirm").click(); await restore.waitFor({state:"hidden"});
  check((await api("/api/view/history")).total===beforeCancel.total,"Saved PC backup restore lost history"); result.backup_saved_on_pc_restore=true;
  await refresh();

  stage = "legacy_backup_restore";
  const legacyList = await api("/api/view/backups"); check(legacyList.legacy.length>0,"Synthetic daily legacy backup missing");
  const beforeLegacy = await api("/api/view/completed"), legacyHistory = await api("/api/view/history");
  const legacyBackups = page.locator("#management-backups details").filter({has:page.locator("summary",{hasText:"Backups antigos de registros"})});
  await legacyBackups.locator("summary").click(); await legacyBackups.getByRole("button",{name:"Restaurar",exact:true}).first().click();
  restore = page.locator("dialog.management-dialog:visible"); await restore.getByRole("button",{name:"Cancelar",exact:true}).click();
  check((await api("/api/view/history")).total===legacyHistory.total,"Cancelling legacy restore changed records");
  await legacyBackups.getByRole("button",{name:"Restaurar",exact:true}).first().click(); restore = page.locator("dialog.management-dialog:visible");
  await restore.getByRole("checkbox",{name:"Conferi os dados e quero restaurar"}).check(); await restore.locator("#phone-backup-restore-confirm").click();
  await restore.waitFor({state:"hidden"});
  check((await api("/api/view/history")).total===legacyList.legacy[0].sessions,"Legacy restore did not restore advertised records");
  check(JSON.stringify((await api("/api/view/completed")).records)===JSON.stringify(beforeLegacy.records),"Legacy restore changed unrelated completions"); result.legacy_backup_restore=true;
  await refresh();

  stage = "phone_json_import_review";
  const phoneFile = path.join(temporary,"synthetic-phone-sessions.json");
  fs.writeFileSync(phoneFile,JSON.stringify({format:"HorasJogadas-Mobile",version:1,sessions:[{id:"0b69c878-5de4-4bd5-9876-929c306e77dd",game:game.name,game_id:game.id,seconds:120,started_at:"2024-01-01T12:00:00Z",ended_at:"2024-01-01T12:02:00Z"}]}));
  const phoneImportButton = () => page.locator("#management-phone-import").getByRole("button",{name:"Importar arquivo de sessões",exact:true});
  const historyBeforePhone = await api("/api/view/history");
  await choose(phoneImportButton(),phoneFile); let phoneReview = page.locator("dialog.management-dialog:visible");
  await phoneReview.getByRole("heading",{name:"Confira suas sessões",exact:true}).waitFor();
  check(await phoneReview.locator(".management-selection-row").count()===1,"JSON preview missing selected session");
  check(await phoneReview.locator("select").inputValue()===game.id,"Existing destination not suggested");
  await phoneReview.getByRole("button",{name:"Cancelar",exact:true}).click();
  check((await api("/api/view/history")).total===historyBeforePhone.total,"Cancelling phone import changed history");
  await choose(phoneImportButton(),phoneFile); phoneReview = page.locator("dialog.management-dialog:visible");
  await phoneReview.getByRole("button",{name:"Importar selecionadas",exact:true}).click(); await phoneReview.waitFor({state:"hidden"});
  const importedHistory = await api("/api/view/history"); check(importedHistory.total===historyBeforePhone.total+1,"Phone JSON import did not create one session");
  check(importedHistory.sessions.some(item=>item.game_id===game.id&&item.seconds===120),"Imported session destination or duration changed"); result.phone_json_import_review=true;
  await refresh();

  stage = "phone_json_reimport_duplicate";
  await choose(phoneImportButton(),phoneFile); phoneReview = page.locator("dialog.management-dialog:visible");
  await phoneReview.getByRole("heading",{name:"Confira suas sessões",exact:true}).waitFor();
  check(await phoneReview.locator("input[type='checkbox']").isDisabled(),"Previously imported session selectable for duplicate import");
  await phoneReview.getByText("Já importada",{exact:true}).waitFor();
  await phoneReview.getByRole("button",{name:"Importar selecionadas",exact:true}).click();
  check((await api("/api/view/history")).total===importedHistory.total,"Reimport duplicated a phone session");
  await phoneReview.getByRole("button",{name:"Cancelar",exact:true}).click(); result.phone_json_reimport_duplicate=true;
  await refresh();

  stage = "individual_remembered_device_revocation";
  const otherContext = await browser.newContext({viewport:{width:390,height:844},isMobile:true}); const otherPhone = await otherContext.newPage();
  await otherPhone.goto(connection().pairing_url); await otherPhone.locator("#control-view").waitFor({state:"visible"});
  await otherPhone.locator("#remember-button").click(); await otherPhone.locator("#remember-name").fill("Secondary QA phone"); await otherPhone.locator("#remember-confirm").click();
  await otherPhone.locator("#remember-dialog").waitFor({state:"hidden"});
  const secondaryCredential = await otherPhone.evaluate(()=>localStorage.getItem("horasjogadas-remembered")); check(secondaryCredential,"Secondary remembered device missing credential");
  await refresh(); const otherRow = page.locator("#management-devices article").filter({hasText:"Secondary QA phone"});
  await otherRow.getByRole("button",{name:"Remover acesso",exact:true}).click();
  await page.locator("dialog.management-dialog:visible").getByRole("button",{name:"Confirmar",exact:true}).click();
  await otherRow.waitFor({state:"detached"});
  const revoked = await context.request.post(connection().url+"/api/resume",{headers:{Origin:connection().url,"Content-Type":"application/json"},data:{remember_token:secondaryCredential}});
  check(revoked.status()===401,"Individually revoked device could reconnect");
  check(await page.evaluate(()=>window.HorasPhone.connected()),"Revoking another device disconnected current phone");
  check(!(await api("/api/view/devices")).devices.some(item=>item.name==="Secondary QA phone"||item.label==="Secondary QA phone"),"Revoked device remained listed");
  await otherContext.close(); result.individual_remembered_device_revocation=true;
  await refresh();

  stage = "art_local_and_remove";
  const authorization = await page.evaluate(()=>sessionStorage.getItem("horasjogadas-remote"));
  const iconResponse = await context.request.get(connection().url+"/api/art/icon/"+game.id,{headers:{Authorization:"Bearer "+authorization}}); check(iconResponse.status()===200,"Synthetic fixture icon unavailable");
  const iconFile = path.join(temporary,"synthetic-icon.png"); fs.writeFileSync(iconFile,await iconResponse.body());
  await page.locator("#phone-manage-icons").click(); const art = page.locator("dialog.management-dialog:visible"); await art.locator(".management-art-game").first().waitFor();
  const row = art.locator(".management-art-game[data-game-id='"+game.id+"']");
  await choose(row.locator("[data-art-action='local']"),iconFile);
  await art.locator(".management-message").filter({hasText:"Imagem salva no PC."}).waitFor();
  check((await api("/api/view/artwork")).games.find(item=>item.id===game.id).has_icon,"Local icon not imported");
  await row.locator("[data-art-action='remove']").click();
  await page.locator("dialog.management-dialog:visible").last().getByRole("button",{name:"Confirmar",exact:true}).click();
  await page.waitForFunction(()=>Array.from(document.querySelectorAll(".management-message")).some(n=>n.textContent==="Imagem removida."));
  check(!(await api("/api/view/artwork")).games.find(item=>item.id===game.id).has_icon,"Icon not removed"); result.art_local_and_remove=true;

  stage = "art_search_preview_import"; await control({stub_artwork:true});
  await row.locator("input[type='checkbox']").check(); await row.locator("[data-art-action='search']").click();
  await row.locator("select option").nth(1).waitFor({state:"attached"}); await row.locator("select").selectOption({index:1});
  await row.getByRole("button",{name:"Ver prévia",exact:true}).click(); await art.locator("img.management-art-preview").waitFor({state:"visible"});
  await art.getByRole("button",{name:"Importar selecionadas",exact:true}).click();
  await page.waitForFunction(()=>Array.from(document.querySelectorAll(".management-message")).some(n=>n.textContent==="Imagens importadas."));
  check((await api("/api/view/artwork")).games.find(item=>item.id===game.id).has_icon,"Selected search image not imported"); result.art_search_preview_import=true;
  await closeManagement(); await refresh();

  // This scripted tour performs many more actions per second than a person.
  // Respect the server's bounded per-device request window between sections.
  await wait(10500);
  stage = "updates_check_readonly"; await control({stub_update:true});
  await page.locator("#management-updates").getByRole("button",{name:"Verificar atualizações",exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector("#management-updates progress"));
  const updates = await api("/api/view/updates"); check(["available","latest"].includes(updates.status),"Update check did not complete"); check(updates.can_install===false,"Source fixture unexpectedly permits installing an update"); result.updates_check_source_safe=true;

  stage = "packaged_update_button_lifecycle";
  let simulatedUpdate = {...updates, packaged:true, can_install:true, busy:false, status:"available",available:{version:"99.0.0",notes:"Synthetic UI check"}};
  await page.route("**/api/view/updates", route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(simulatedUpdate)}));
  await refresh();
  await page.locator("#management-updates").getByRole("button",{name:"Baixar atualização",exact:true}).waitFor();
  check(await page.locator("#management-updates").getByRole("button",{name:"Instalar e reiniciar o PC app",exact:true}).count()===0,"Install appeared before download was ready");
  simulatedUpdate.status="ready"; await refresh();
  await page.locator("#management-updates").getByRole("button",{name:"Instalar e reiniciar o PC app",exact:true}).click();
  await page.locator("dialog.management-dialog:visible").getByRole("button",{name:"Cancelar",exact:true}).click();
  await page.unroute("**/api/view/updates"); await refresh(); result.packaged_update_button_lifecycle=true;

  stage = "responsive_translations";
  for(const theme of ["dark","original","violet","light"]) {
   await control({theme,language:theme==="light"?"en":"pt"}); await refresh();
   for(const width of [320,390,1040]) {await page.setViewportSize({width,height:844}); check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),"Management overflow "+theme+" "+width);}
  }
  await page.locator("#management-appearance").getByRole("heading",{name:"Your app, your way"}).waitFor({state:"visible",timeout:10000}); result.responsive_and_translated=true;
  await snapshot("light");

  stage = "disable_control_preserves_remembered_device";
  await page.locator("#remember-button").click(); await page.locator("#remember-name").fill("Management QA"); await page.locator("#remember-confirm").click(); await page.locator("#remember-dialog").waitFor({state:"hidden"});
  const remembered = await page.evaluate(()=>localStorage.getItem("horasjogadas-remembered")); check(Boolean(remembered),"Remembered credential missing before disable");
  await page.locator("#phone-control-disable").click();
  await page.locator("dialog.management-dialog:visible").getByRole("button",{name:"Confirm",exact:true}).click();
  await page.waitForFunction(()=>!window.HorasPhone.connected(),null,{timeout:15000});
  check(await page.evaluate(()=>localStorage.getItem("horasjogadas-remembered"))===remembered,"Disabling control erased remembered access");
  const close = page.locator("dialog.management-dialog:visible").getByRole("button",{name:"Close",exact:true});
  await close.waitFor({state:"visible"}); await page.waitForFunction(()=>Array.from(document.querySelectorAll("dialog.management-dialog[open] button")).some(button=>button.textContent==="Close"&&!button.disabled)); await close.click(); result.disable_control_preserves_remembered=true;
  check(errors.length===0,"Browser errors: "+errors.join(", ")); check(csp.length===0,"CSP violations: "+csp.join(", ")); result.no_browser_or_csp_errors=true;
  result.ok=true;
 } catch(error) {result.failed_case=stage; result.error=String(error.message).replace(/#pair=[A-Za-z0-9_-]+/g,"#pair=[redacted]"); if(page) {try {result.messages=await page.locator(".management-message.error").allTextContents();}catch(_){}}}
 finally {
  if(browser) await browser.close(); if(fixture && fixture.exitCode===null) {try {await control({quit:true});}catch(_){} await Promise.race([new Promise(resolve=>fixture.once("exit",resolve)),wait(3000)]); if(fixture.exitCode===null) fixture.kill();}
  fs.mkdirSync(path.dirname(resultFile),{recursive:true}); fs.writeFileSync(resultFile,JSON.stringify(result,null,2)); fs.rmSync(temporary,{recursive:true,force:true}); console.log(JSON.stringify(result)); process.exitCode=result.ok?0:1;
 }
})();

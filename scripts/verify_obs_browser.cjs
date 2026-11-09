"use strict";
const fs=require('fs'),os=require('os'),path=require('path'),{spawn}=require('child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const args=process.argv.slice(2),option=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const root=path.resolve(__dirname,'..'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'horas-obs-')),output=path.join(tmp,'connection.json'),controlFile=path.join(tmp,'control.json');
const wait=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,m)=>{if(!v)throw Error(m)},connection=()=>JSON.parse(fs.readFileSync(output));
const result={ok:false};let fixture,browser,page,stderr='';
async function control(data){const nonce=Math.random().toString(36);fs.writeFileSync(controlFile+'.tmp',JSON.stringify({...data,nonce}));fs.renameSync(controlFile+'.tmp',controlFile);for(let i=0;i<100;i++){if(connection().control_nonce===nonce)return;await wait(50)}throw Error('Control timeout')}
(async()=>{try{
 fixture=spawn(option('--python','python'),[path.join(root,'scripts/phone_browser_fixture.py'),'--output',output,'--control',controlFile],{cwd:root,env:{...process.env,QT_QPA_PLATFORM:'offscreen'},stdio:['ignore','ignore','pipe']});fixture.stderr.on('data',b=>stderr=(stderr+b).slice(-3000));
 for(let i=0;i<200&&!fs.existsSync(output)&&fixture.exitCode===null;i++)await wait(100);check(fs.existsSync(output),'Fixture: '+stderr);
 await control({obs:{enabled:true},obs_seconds:355966});const url=connection().obs_url;
 const launch={headless:true};if(process.env.CHROMIUM)launch.executablePath=process.env.CHROMIUM;if(process.env.CI||process.getuid&&process.getuid()===0)launch.args=['--no-sandbox'];browser=await chromium.launch(launch);
 const context=await browser.newContext({viewport:{width:600,height:180}});page=await context.newPage();const errors=[],external=[],csp=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).origin!==new URL(url).origin)external.push(r.url())});
 await page.exposeFunction('obsCSP',x=>csp.push(x));await page.addInitScript(()=>document.addEventListener('securitypolicyviolation',e=>window.obsCSP(e.violatedDirective)));
 await page.goto(url);await page.locator('#widget').waitFor({state:'visible'});
 check(await page.locator('#hours').textContent()==='98'&&await page.locator('#minutes').textContent()==='52'&&await page.locator('#seconds').textContent()==='46','Initial time mismatch');
 check(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor)==='rgba(0, 0, 0, 0)','Background not transparent');check(!new URL(page.url()).hash,'Secret remained in address bar');result.transparent_arcade=true;
 const screenshot=option('--screenshot','');if(screenshot){fs.mkdirSync(path.dirname(screenshot),{recursive:true});await page.screenshot({path:screenshot,omitBackground:true})}
 await control({obs_action:'start'});await page.waitForFunction(()=>document.querySelector('#seconds').textContent!=='46');await control({obs_action:'pause'});await wait(1200);const paused=await page.locator('#seconds').textContent();await wait(1500);check(await page.locator('#seconds').textContent()===paused,'Paused timer advanced');result.start_and_pause=true;
 await control({obs:{enabled:true,style:'digital',color:'#77ddff',show_name:true}});await page.waitForFunction(()=>document.querySelector('#widget').className==='digital');check(await page.locator('#name').textContent()==='Hollow Knight','Game name missing');check(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--ink'))==='#77ddff','Color not applied');result.live_style_color_name=true;
 await control({obs:{enabled:true,style:'minimal',scope:'total'}});await page.waitForFunction(()=>document.querySelector('#widget').className==='minimal');check(Number(await page.locator('#hours').textContent())>98,'Total time missing history');result.total_time=true;
 await page.reload();await page.locator('#widget').waitFor({state:'visible'});result.refresh_keeps_authorization=true;
 await control({obs_action:'stop_phone'});await wait(1500);check(await page.locator('#widget').isVisible(),'OBS depends on phone control');result.independent_of_phone=true;
 await control({obs:{enabled:false}});await page.locator('#widget').waitFor({state:'hidden',timeout:5000});result.disconnect_hides_stale_time=true;
 await control({obs:{enabled:true}});check(connection().obs_url===url,'Saved URL changed');await page.locator('#widget').waitFor({state:'visible',timeout:5000});result.stable_link_reconnect=true;
 check(!errors.length&&!csp.length&&!external.length,'Browser/CSP/external requests');result.safe_local_render=true;result.ok=true;
 }catch(e){result.error=String(e.message).replace(/#key=[a-f0-9]+/g,'#key=[redacted]')}
 finally{if(browser)await browser.close();if(fixture&&fixture.exitCode===null){try{await control({quit:true})}catch(_){}fixture.kill()}const file=option('--result',path.join(root,'build-diagnostics/obs-browser.json'));fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(result,null,2));fs.rmSync(tmp,{recursive:true,force:true});console.log(JSON.stringify(result));process.exitCode=result.ok?0:1}
})();

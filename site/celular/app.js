'use strict';
(() => {
  const KEY = 'horasjogadas-companion-v1';
  const LOCK = 'horasjogadas-companion-writer';
  const LIMIT = 604800000;
  const $ = id => document.getElementById(id);
  const palettes = {
    original:['#1f1f23','#19191d','#2b2b2f','#2f2f35','#e6e6e6','#bfbfbf','#5c5cff','#ffffff'],
    dark:['#16191d','#101215','#1e2227','#2c323a','#f0f2f5','#a1a9b5','#e2e8f0','#171a20'],
    violet:['#15141c','#101017','#211f2d','#363147','#f2f0fa','#aba6bc','#a89bfa','#151121'],
    light:['#f4f5f7','#ebedf0','#ffffff','#d6dbe2','#20252d','#596575','#365ac8','#ffffff'],
  };
  const words = {
    pt:{edition:'NO SEU CELULAR',local:'Salvo neste celular',eyebrow:'UMA PARTIDA DE CADA VEZ',heading:'Seu tempo. Seu jogo.',intro:'O PC pode descansar. Sua próxima sessão começa aqui.',install:'Instalar no celular',readonly:'O contador está aberto em outra aba. Use apenas uma para controlar a sessão.',take_control:'Tentar nesta aba',now:'JOGANDO AGORA',pause:'Pausar',resume:'Retomar',finish:'Encerrar e salvar',discard:'Descartar esta sessão',next:'PRÓXIMA PARTIDA',choose:'O que vamos jogar?',game_name:'Nome do jogo',name_placeholder:'Digite ou escolha abaixo…',start:'Iniciar sessão',your_games:'Seus jogos',on_phone:'GUARDADO NO CELULAR',sessions:'Suas sessões',history_empty:'As partidas concluídas vão aparecer aqui.',export:'Exportar selecionadas',select_all:'Marcar todas',export_help:'Envie o arquivo para seu PC. No app, abra Configurações → Controle pelo celular → Importar sessões do celular. Você confere tudo antes de salvar.',export_keep:'Exportar não apaga suas sessões deste celular.',options:'Personalizar e preparar',theme:'Aparência',language:'Idioma',original:'Original · cinza e roxo',dark:'Escuro minimalista',violet:'Violeta',light:'Claro',library:'Biblioteca do PC',library_help:'No app do PC, exporte a biblioteca nas Configurações. Importe o arquivo aqui para escolher seus jogos com mais facilidade.',import_library:'Importar biblioteca do PC',persist:'Proteger armazenamento local',storage_help:'O navegador guarda os dados neste aparelho. Exporte suas sessões regularmente; limpar os dados do navegador também apaga essa cópia.',difference:'Este é um contador independente. Para controlar o cronômetro do PC ligado, use o QR Code do controle local nas Configurações do app.',desktop_app:'Conhecer o app para PC ↗',footer:'Sem conta. Sem nuvem. Cada partida é sua.',preparing:'Preparando o uso offline…',session_done:'BOA PARTIDA',finish_title:'Guardar esta sessão?',finish_help:'Fica salva no celular, pronta para levar ao histórico do PC.',cancel:'Cancelar',save:'Salvar sessão',saved:'SESSÃO SALVA',summary_help:'Quando estiver no PC, exporte suas sessões para importar no app.',great:'Tudo certo',review:'CONFERIR TEMPO',clock_title:'O relógio mudou.',clock_help:'Confira a data e hora do celular e o tempo realmente jogado. Para não salvar horas incorretas, a sessão fica pausada até você confirmar.',played_seconds:'Tempo jogado, em segundos',review_apply:'Confirmar e manter pausado',confirm:'Confirmar',install_title:'Sempre à mão.',install_android:'No Android, abra o menu do navegador e escolha “Instalar aplicativo” ou “Adicionar à tela inicial”.',install_ios:'No iPhone, abra no Safari, toque em Compartilhar e escolha “Adicionar à Tela de Início”.',install_once:'Abra uma vez com internet para preparar os arquivos. Depois, o contador funciona com o PC desligado e sem conexão. Se já tem sessões no navegador, exporte uma cópia antes de mudar para outro navegador ou app instalado.',got_it:'Entendi',running:'Em andamento',paused:'Pausado',running_hint:'Pode bloquear a tela. O tempo continua contando.',paused_hint:'Respire um pouco. Retome quando quiser.',storage_error:'Não foi possível salvar no celular. A última versão guardada foi mantida. Libere espaço ou exporte suas sessões antes de tentar novamente.',corrupt:'Os dados guardados não puderam ser lidos. Nada foi substituído. Guarde uma cópia para recuperar seus registros.',backup_raw:'Baixar cópia dos dados guardados',unsupported:'Este navegador não oferece a proteção necessária para controlar o contador em várias abas. Abra em um navegador atualizado. Seus registros existentes continuam disponíveis para exportar.',ready:'Pronto para usar offline',offline_failed:'Abra com internet uma vez para preparar o uso offline.',updated:'Uma nova versão está pronta. Feche todas as abas e reabra quando terminar a partida; suas sessões ficam guardadas.',persisted:'Armazenamento protegido quando permitido pelo navegador. Continue exportando suas sessões como cópia de segurança.',persist_denied:'O navegador não concedeu armazenamento persistente. Os dados continuam locais; exporte suas sessões regularmente.',library_ok:'Biblioteca importada. Seus registros anteriores foram preservados.',invalid_file:'Esse arquivo não é uma biblioteca válida do HorasJogadas.',invalid_name:'Digite um nome de jogo de até 200 caracteres.',nothing_selected:'Marque pelo menos uma sessão para exportar.',exported:'Arquivo exportado. A cópia no celular foi mantida.',too_many:'Há 500 sessões guardadas. Exporte uma cópia e remova sessões antigas antes de salvar uma nova.',min_time:'A sessão precisa ter ao menos um segundo. Continue jogando ou descarte esta sessão.',discard_title:'Descartar esta sessão?',discard_help:'O tempo desta sessão será removido do celular. As partidas já salvas continuam guardadas.',delete_title:'Excluir esta sessão do celular?',delete_help:'Exporte uma cópia primeiro, se quiser preservá-la. Isso não remove registros já importados no PC.',favorite:'Marcar favorito',unfavorite:'Remover dos favoritos',delete_session:'Excluir sessão',selected:'Selecionar sessão',phone_total:'Total neste celular',clock_invalid:'Informe de 0 a 604800 segundos (sete dias).',clock_before:'Confira o valor antes de confirmar. O tempo só será retomado quando você escolher Retomar.',saved_announcement:'Sessão salva no celular.',export_tip:'Apenas sessões concluídas são exportadas. A sessão atual continua guardada.',retry_save:'Tentar salvar novamente'},
    en:{edition:'ON YOUR PHONE',local:'Saved on this phone',eyebrow:'ONE SESSION AT A TIME',heading:'Your time. Your game.',intro:'Your PC can rest. Your next session starts here.',install:'Install on phone',readonly:'The timer is open in another tab. Use only one tab to control the session.',take_control:'Try this tab',now:'PLAYING NOW',pause:'Pause',resume:'Resume',finish:'Finish and save',discard:'Discard this session',next:'NEXT SESSION',choose:'What are we playing?',game_name:'Game name',name_placeholder:'Type or choose a game below…',start:'Start session',your_games:'Your games',on_phone:'KEPT ON YOUR PHONE',sessions:'Your sessions',history_empty:'Completed sessions will appear here.',export:'Export selected',select_all:'Select all',export_help:'Send the file to your PC. In the app, open Settings → Phone control → Import phone sessions. Review everything before saving.',export_keep:'Exporting does not delete sessions from your phone.',options:'Personalize and prepare',theme:'Appearance',language:'Language',original:'Original · gray and purple',dark:'Minimal dark',violet:'Violet',light:'Light',library:'PC library',library_help:'Export your library from the PC app settings. Import the file here to choose games more easily.',import_library:'Import PC library',persist:'Protect local storage',storage_help:'Your browser keeps the data on this device. Export sessions regularly; clearing browser data also removes this copy.',difference:'This is an independent timer. To control a running PC timer, use the local control QR code in the PC app settings.',desktop_app:'Explore the PC app ↗',footer:'No account. No cloud. Every session is yours.',preparing:'Preparing offline use…',session_done:'GOOD GAME',finish_title:'Keep this session?',finish_help:'Saved on your phone, ready to take to your PC history.',cancel:'Cancel',save:'Save session',saved:'SESSION SAVED',summary_help:'When back at your PC, export your sessions to import them in the app.',great:'All set',review:'REVIEW TIME',clock_title:'The clock changed.',clock_help:'Check your phone’s date and time and the time actually played. To avoid saving incorrect hours, the session stays paused until you confirm.',played_seconds:'Time played, in seconds',review_apply:'Confirm and keep paused',confirm:'Confirm',install_title:'Always close by.',install_android:'On Android, open the browser menu and choose “Install app” or “Add to home screen”.',install_ios:'On iPhone, open in Safari, tap Share and choose “Add to Home Screen”.',install_once:'Open once with internet to prepare the files. Then the timer works with your PC off and without a connection. If you already have browser sessions, export a copy before switching browsers or installed apps.',got_it:'Got it',running:'Playing',paused:'Paused',running_hint:'You can lock your screen. Your time keeps counting.',paused_hint:'Take a breath. Resume whenever you are ready.',storage_error:'Could not save on your phone. The last stored version was kept. Free some space or export your sessions before trying again.',corrupt:'Stored data could not be read. Nothing was replaced. Keep a copy to recover your records.',backup_raw:'Download a copy of stored data',unsupported:'This browser cannot protect the timer across multiple tabs. Open it in an updated browser. Existing sessions can still be exported.',ready:'Ready to use offline',offline_failed:'Open once with internet to prepare offline use.',updated:'An update is ready. Close all tabs and reopen after finishing your session; your records stay saved.',persisted:'Storage protected when allowed by the browser. Keep exporting sessions as backups.',persist_denied:'Your browser did not grant persistent storage. Data stays local; export your sessions regularly.',library_ok:'Library imported. Existing records were preserved.',invalid_file:'This is not a valid HorasJogadas library file.',invalid_name:'Enter a game name with up to 200 characters.',nothing_selected:'Select at least one session to export.',exported:'File exported. The copy on your phone was kept.',too_many:'There are 500 saved sessions. Export a copy and remove older sessions before saving a new one.',min_time:'A session needs at least one second. Keep playing or discard this session.',discard_title:'Discard this session?',discard_help:'Time from this session will be removed from your phone. Previously saved sessions are kept.',delete_title:'Delete this session from your phone?',delete_help:'Export a copy first if you want to preserve it. This does not delete records already imported on your PC.',favorite:'Mark favorite',unfavorite:'Remove favorite',delete_session:'Delete session',selected:'Select session',phone_total:'Total on this phone',clock_invalid:'Enter between 0 and 604800 seconds (seven days).',clock_before:'Check the value before confirming. Time only starts again when you choose Resume.',saved_announcement:'Session saved on your phone.',export_tip:'Only completed sessions are exported. Your current session remains saved.',retry_save:'Try saving again'}
  };
  const fresh = () => ({version:1,revision:0,theme:'original',language:'pt',games:[],active:null,sessions:[]});
  let state=fresh(), owner=false, broken=false, corruptRaw=null, releaseLock=null, acquiring=false, pendingConfirm=null, lastCheckpoint=0, deferredInstall=null;
  const selection=new Set();
  const t=key => (words[state.language]||words.pt)[key] || words.pt[key] || key;
  const uuid=()=>crypto.randomUUID ? crypto.randomUUID() : ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g,c=>(c^crypto.getRandomValues(new Uint8Array(1))[0]&15>>c/4).toString(16));
  const validId = value => typeof value==='string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
  const finite=value=>typeof value==='number' && Number.isFinite(value);
  const stamp=value=>finite(value) && value>=946684800000 && value<=4102444800000;
  const text=value=>typeof value==='string' && value.trim().length>0 && value.length<=200 && !/[\x00-\x1f\x7f]/.test(value);
  const iso=value=>typeof value==='string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
  function validate(value) {
    if(!value || value.version!==1 || !Number.isSafeInteger(value.revision) || value.revision<0 || !Object.hasOwn(palettes,value.theme) || !['pt','en'].includes(value.language) || !Array.isArray(value.games) || value.games.length>2000 || !Array.isArray(value.sessions) || value.sessions.length>500) throw Error('invalid');
    const gameIds=new Set();
    for(const game of value.games) {
      if(!game || !text(game.name) || typeof game.id!=='string' || game.id.length>200 || gameIds.has(game.id) || typeof game.favorite!=='boolean' || (game.pc_id!==undefined && (typeof game.pc_id!=='string'||game.pc_id.length>128))) throw Error('invalid');
      gameIds.add(game.id);
    }
    const ids=new Set();
    for(const session of value.sessions) {
      if(!session || !validId(session.id) || ids.has(session.id) || !text(session.game) || !Number.isSafeInteger(session.seconds) || session.seconds<1 || session.seconds>LIMIT/1000 || !iso(session.started_at) || !iso(session.ended_at) || Date.parse(session.ended_at)<Date.parse(session.started_at) || session.seconds*1000>Date.parse(session.ended_at)-Date.parse(session.started_at)+1000 || (session.game_id!==undefined && (typeof session.game_id!=='string'||session.game_id.length>128))) throw Error('invalid');
      ids.add(session.id);
    }
    if(value.active!==null) {
      const a=value.active;
      if(!a || !validId(a.id) || ids.has(a.id) || !text(a.name) || typeof a.game_id!=='string' || !gameIds.has(a.game_id) || !stamp(a.started_at) || !stamp(a.last_seen) || !finite(a.accumulated_ms) || a.accumulated_ms<0 || a.accumulated_ms>LIMIT || (a.segment_at!==null && !stamp(a.segment_at)) || typeof a.needs_review!=='boolean' || (a.safe_review_ms!==undefined && (!finite(a.safe_review_ms)||a.safe_review_ms<0||a.safe_review_ms>LIMIT))) throw Error('invalid');
    }
    return value;
  }
  function read() {
    try { const raw=localStorage.getItem(KEY);state=raw===null?fresh():validate(JSON.parse(raw));broken=false;corruptRaw=null;return true; }
    catch(_) { try{corruptRaw=localStorage.getItem(KEY);}catch(_ignored){} broken=true;showStorage(corruptRaw!==null?'corrupt':'storage_error');return false; }
  }
  function showStorage(key='storage_error') {
    for(const id of ['finish-dialog','clock-review','confirm-dialog'])if($(id).open)$(id).close();
    $('storage-error').hidden=false;$('storage-error').textContent=t(key);
    if(corruptRaw!==null) {
      const button=document.createElement('button');button.type='button';button.textContent=t('backup_raw');button.className='quiet';button.addEventListener('click',()=>download('HorasJogadas-recuperar-celular.txt',corruptRaw,'text/plain'));$('storage-error').append(document.createElement('br'),button);
    } else {
      const button=document.createElement('button');button.type='button';button.textContent=t('retry_save');button.className='quiet';button.addEventListener('click',()=>{if(read()){$('storage-error').hidden=true;render();acquire();}});$('storage-error').append(document.createElement('br'),button);
    }
  }
  function notice(key) {$('notice').hidden=!key;$('notice').textContent=key?t(key):'';}
  function commit(edit) {
    if(!owner || broken) return false;
    try {
      const raw=localStorage.getItem(KEY);
      const current=raw===null?fresh():validate(JSON.parse(raw));
      if(current.revision!==state.revision) {state=current;render();return false;}
      const next=structuredClone(state);edit(next);next.revision=state.revision+1;validate(next);
      const saved=JSON.stringify(next);localStorage.setItem(KEY,saved);
      state=next;$('storage-error').hidden=true;render();return true;
    } catch(_) {broken=true;showStorage();controls();return false;}
  }
  function translate() {
    document.documentElement.lang=state.language==='en'?'en':'pt-BR';
    document.title='HorasJogadas · '+(state.language==='en'?'On your phone':'No celular');
    document.querySelectorAll('[data-t]').forEach(node=>node.textContent=t(node.dataset.t));
    document.querySelectorAll('[data-placeholder]').forEach(node=>node.placeholder=t(node.dataset.placeholder));
    const keys=['bg','side','card','border','text','muted','accent','on-accent'];
    palettes[state.theme].forEach((color,index)=>document.documentElement.style.setProperty('--'+keys[index],color));
    document.documentElement.dataset.theme=state.theme;document.documentElement.style.colorScheme=state.theme==='light'?'light':'dark';
    document.querySelector('meta[name=theme-color]').content=palettes[state.theme][0];
    $('theme').value=state.theme;$('language').value=state.language;
  }
  function elapsed(a=state.active, now=Date.now()) {
    if(!a)return 0;
    return Math.min(LIMIT,Math.max(0,a.accumulated_ms+(a.segment_at!==null&&!a.needs_review?Math.max(0,now-a.segment_at):0)));
  }
  function clock(ms) {const seconds=Math.floor(ms/1000);return String(Math.floor(seconds/3600)).padStart(2,'0')+':'+String(Math.floor(seconds/60)%60).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');}
  function duration(seconds) {return Math.floor(seconds/3600)+'h '+String(Math.floor(seconds/60)%60).padStart(2,'0')+'m';}
  const initials=name=>name.split(/\s+/).filter(Boolean).slice(0,2).map(part=>Array.from(part)[0]).join('').toUpperCase();
  function element(tag,cls,value) {const node=document.createElement(tag);if(cls)node.className=cls;if(value!==undefined)node.textContent=value;return node;}
  function gameRows() {
    $('games-section').hidden=!state.games.length;$('games-count').textContent=String(state.games.length);$('game-list').replaceChildren();$('suggestions').replaceChildren();
    const games=[...state.games].sort((a,b)=>Number(b.favorite)-Number(a.favorite)||a.name.localeCompare(b.name));
    for(const game of games) {
      const row=element('div','game-item');
      const pick=element('button','game-pick');pick.type='button';pick.append(element('span','game-avatar',initials(game.name)),element('span','',game.name));pick.title=game.name;
      pick.addEventListener('click',()=>{$('game-name').value=game.name;$('game-name').focus();});
      const favorite=element('button','game-favorite',game.favorite?'★':'☆');favorite.type='button';favorite.setAttribute('aria-pressed',String(game.favorite));favorite.setAttribute('aria-label',t(game.favorite?'unfavorite':'favorite')+' · '+game.name);favorite.addEventListener('click',()=>commit(s=>{s.games.find(g=>g.id===game.id).favorite=!game.favorite;}));
      row.append(pick,favorite);$('game-list').append(row);
      if(game.favorite && $('suggestions').children.length<4) {const suggestion=element('button','',game.name);suggestion.type='button';suggestion.addEventListener('click',()=>{$('game-name').value=game.name;});$('suggestions').append(suggestion);}
    }
  }
  function historyRows() {
    $('history').replaceChildren();$('history-count').textContent=String(state.sessions.length);$('history-empty').hidden=state.sessions.length>0;$('export-tools').hidden=!state.sessions.length;
    for(const session of [...state.sessions].reverse()) {
      const row=element('div','history-item');row.dataset.sessionId=session.id;
      const check=document.createElement('input');check.type='checkbox';check.dataset.sessionId=session.id;check.checked=selection.has(session.id);check.setAttribute('aria-label',t('selected')+' · '+session.game);check.addEventListener('change',()=>{if(check.checked)selection.add(session.id);else selection.delete(session.id);});
      const info=element('div','history-info');info.append(element('strong','',session.game),element('small','',new Date(session.ended_at).toLocaleString(state.language==='en'?'en-US':'pt-BR',{dateStyle:'short',timeStyle:'short'})));
      const time=element('span','history-duration',duration(session.seconds));
      const remove=element('button','history-delete','×');remove.type='button';remove.setAttribute('aria-label',t('delete_session')+' · '+session.game);remove.addEventListener('click',()=>confirm('delete_title','delete_help',()=>{if(commit(s=>{s.sessions=s.sessions.filter(item=>item.id!==session.id);})){selection.delete(session.id);$('confirm-dialog').close();}}));
      row.append(check,info,time,remove);$('history').append(row);
    }
  }
  function controls() {
    const blocked=!owner||broken;
    for(const id of ['start-button','theme','language','library-file','persist-button'])$(id).disabled=blocked;
    document.querySelectorAll('.game-favorite,.history-delete').forEach(node=>node.disabled=blocked);
    const active=state.active, review=active&&active.needs_review;
    $('pause-button').disabled=blocked||review;$('resume-button').disabled=blocked||review;$('finish-button').disabled=blocked||review;$('discard-button').disabled=blocked;
    $('finish-save').disabled=blocked||review;$('review-apply').disabled=blocked;
    $('readonly').hidden=owner||broken||!navigator.locks;
  }
  function render() {
    translate();const active=state.active;document.querySelector('.page-heading').hidden=Boolean(active);$('playing').hidden=!active;$('start-card').hidden=Boolean(active);
    if(active) {$('current-title').textContent=active.name;$('current-time').textContent=clock(elapsed());$('current-status').textContent=t(active.segment_at!==null?'running':'paused');$('current-hint').textContent=t(active.segment_at!==null?'running_hint':'paused_hint');$('pause-button').hidden=active.segment_at===null;$('resume-button').hidden=active.segment_at!==null;}
    gameRows();historyRows();controls();
    if(active&&active.needs_review&&owner&&!broken&&!$('clock-review').open) {$('review-seconds').value=String(Math.floor((active.safe_review_ms??active.accumulated_ms)/1000));$('clock-message').textContent=t('clock_before');$('clock-review').showModal();}
  }
  function issue(now=Date.now()) {
    const a=state.active;
    return a&&!a.needs_review&&(now<a.last_seen-2000||(a.segment_at!==null&&(now-a.last_seen>86400000||a.accumulated_ms+Math.max(0,now-a.segment_at)>LIMIT)));
  }
  function checkClock() {
    if(!owner||broken||!state.active)return;
    if(issue()) {const a=state.active;commit(s=>{s.active.needs_review=true;s.active.safe_review_ms=Math.min(LIMIT,a.accumulated_ms+(a.segment_at===null?0:Math.max(0,a.last_seen-a.segment_at)));});}
  }
  async function acquire() {
    if(acquiring||owner||broken)return;
    if(!navigator.locks) {notice('unsupported');controls();return;}
    acquiring=true;
    try {
      await navigator.locks.request(LOCK,{ifAvailable:true},async lock=>{
        acquiring=false;if(!lock){controls();return;}
        owner=true;read();render();checkClock();
        await new Promise(resolve=>{releaseLock=resolve;});
        owner=false;releaseLock=null;controls();
      });
    } catch(_) {owner=false;acquiring=false;notice('unsupported');controls();}
  }
  function confirm(title,description,callback) {pendingConfirm=callback;$('confirm-title').textContent=t(title);$('confirm-description').textContent=t(description);$('confirm-dialog').showModal();}
  function download(name,value,mime='application/json') {const url=URL.createObjectURL(new Blob([value],{type:mime}));const link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
  $('start-form').addEventListener('submit',event=>{
    event.preventDefault();if(state.active||!owner||broken)return;
    const name=$('game-name').value.trim().replace(/\s+/g,' ');if(!text(name)){notice('invalid_name');return;}
    const now=Date.now();const id=uuid();
    if(commit(s=>{let game=s.games.find(g=>g.name.toLocaleLowerCase()===name.toLocaleLowerCase());if(!game){game={id:uuid(),name,favorite:false};s.games.push(game);}s.active={id,game_id:game.id,name:game.name,started_at:now,segment_at:now,accumulated_ms:0,last_seen:now,needs_review:false};})) {notice('');$('game-name').value='';$('playing').scrollIntoView({block:'start',behavior:'smooth'});}
  });
  $('pause-button').addEventListener('click',()=>{checkClock();if(!state.active||state.active.needs_review||state.active.segment_at===null)return;const now=Date.now(),ms=elapsed(state.active,now);commit(s=>{s.active.accumulated_ms=ms;s.active.segment_at=null;s.active.last_seen=now;});});
  $('resume-button').addEventListener('click',()=>{checkClock();if(!state.active||state.active.needs_review||state.active.segment_at!==null)return;commit(s=>{s.active.segment_at=Date.now();s.active.last_seen=Date.now();});});
  $('finish-button').addEventListener('click',()=>{checkClock();if(!state.active||state.active.needs_review)return;$('finish-name').textContent=state.active.name;$('finish-time').textContent=clock(elapsed());$('finish-dialog').showModal();});
  $('finish-save').addEventListener('click',()=>{
    checkClock();if(!state.active||state.active.needs_review)return;
    if(state.sessions.length>=500){notice('too_many');$('finish-dialog').close();return;}
    const now=Date.now(),a=state.active,seconds=Math.floor(elapsed(a,now)/1000);
    if(seconds<1){notice('min_time');$('finish-dialog').close();return;}
    const game=state.games.find(g=>g.id===a.game_id);
    const session={id:a.id,game:a.name,seconds,started_at:new Date(Math.min(a.started_at,now-seconds*1000)).toISOString(),ended_at:new Date(now).toISOString()};
    if(game&&game.pc_id)session.game_id=game.pc_id;
    if(commit(s=>{s.sessions.push(session);s.active=null;})) {
      selection.add(session.id);historyRows();$('finish-dialog').close();$('summary-name').textContent=session.game;$('summary-time').textContent=clock(seconds*1000);$('summary-total').textContent=t('phone_total')+' · '+duration(state.sessions.filter(item=>item.game===session.game).reduce((sum,item)=>sum+item.seconds,0));$('summary-dialog').showModal();$('announcement').textContent=t('saved_announcement');
    }
  });
  $('discard-button').addEventListener('click',()=>confirm('discard_title','discard_help',()=>{if(commit(s=>{s.active=null;})){$('confirm-dialog').close();if($('clock-review').open)$('clock-review').close();}}));
  $('review-apply').addEventListener('click',()=>{const seconds=Number($('review-seconds').value);if(!Number.isInteger(seconds)||seconds<0||seconds>604800){$('clock-message').textContent=t('clock_invalid');return;}const now=Date.now();if(commit(s=>{s.active.accumulated_ms=seconds*1000;s.active.segment_at=null;s.active.started_at=Math.min(s.active.started_at,now-seconds*1000);s.active.last_seen=now;s.active.needs_review=false;delete s.active.safe_review_ms;})){$('clock-review').close();render();}});
  $('clock-review').addEventListener('cancel',event=>event.preventDefault());
  $('confirm-action').addEventListener('click',()=>{if(pendingConfirm)pendingConfirm();});
  document.querySelectorAll('[data-close]').forEach(node=>node.addEventListener('click',()=>$(node.dataset.close).close()));
  $('theme').addEventListener('change',()=>commit(s=>{s.theme=$('theme').value;}));$('language').addEventListener('change',()=>commit(s=>{s.language=$('language').value;}));
  $('select-all').addEventListener('click',()=>{state.sessions.forEach(item=>selection.add(item.id));historyRows();});
  $('export-button').addEventListener('click',()=>{const sessions=state.sessions.filter(item=>selection.has(item.id));if(!sessions.length){notice('nothing_selected');return;}download('HorasJogadas-celular-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify({format:'HorasJogadas-Mobile',version:1,sessions},null,2));notice('exported');});
  $('library-file').addEventListener('change',async()=>{
    const file=$('library-file').files[0];if(!file)return;
    try {
      if(file.size>1024*1024)throw Error();const value=JSON.parse(await file.text());
      if(value.format!=='HorasJogadas-Library'||value.version!==1||!Array.isArray(value.games)||value.games.length>1000||value.games.some(g=>!g||!text(g.name)||typeof g.id!=='string'||!g.id||g.id.length>128)||new Set(value.games.map(g=>g.id)).size!==value.games.length)throw Error();
      const saved=commit(s=>{for(const g of value.games){let game=s.games.find(item=>item.pc_id===g.id||item.name.toLocaleLowerCase()===g.name.toLocaleLowerCase());if(game){game.pc_id=g.id;}else{s.games.push({id:uuid(),pc_id:g.id,name:g.name,favorite:false});}}if(Object.hasOwn(palettes,value.theme))s.theme=value.theme;if(['pt','en'].includes(value.language))s.language=value.language;});if(saved)notice('library_ok');
    } catch(_) {notice('invalid_file');}finally{$('library-file').value='';}
  });
  $('take-control').addEventListener('click',acquire);
  $('persist-button').addEventListener('click',async()=>{let granted=false;try{granted=navigator.storage&&await navigator.storage.persist();}catch(_){}notice(granted?'persisted':'persist_denied');});
  window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredInstall=event;});
  $('install-button').addEventListener('click',async()=>{if(deferredInstall){const prompt=deferredInstall;deferredInstall=null;await prompt.prompt();}else $('install-help').showModal();});
  window.addEventListener('storage',event=>{if(event.key===KEY){read();state.sessions.forEach(item=>selection.add(item.id));render();}});
  window.addEventListener('pagehide',()=>{if(releaseLock)releaseLock();});
  window.addEventListener('pageshow',()=>{if(!owner)acquire();});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){checkClock();if(!owner)acquire();}});
  setInterval(()=>{
    checkClock();if(state.active){$('current-time').textContent=clock(elapsed());if($('finish-dialog').open)$('finish-time').textContent=clock(elapsed());}
    if(owner&&!broken&&state.active&&!state.active.needs_review&&Date.now()-lastCheckpoint>30000) {lastCheckpoint=Date.now();if(Date.now()>=state.active.last_seen)commit(s=>{s.active.last_seen=Date.now();});}
  },500);
  async function prepareOffline() {
    if(!('serviceWorker'in navigator)){ $('ready-status').dataset.t='offline_failed';$('ready-status').textContent=t('offline_failed');return;}
    try {const registration=await navigator.serviceWorker.register('./sw.js',{scope:'./'});await navigator.serviceWorker.ready;$('ready-status').dataset.t='ready';$('ready-status').textContent=t('ready');if(registration.waiting)notice('updated');registration.addEventListener('updatefound',()=>{const worker=registration.installing;if(worker)worker.addEventListener('statechange',()=>{if(worker.state==='installed'&&navigator.serviceWorker.controller)notice('updated');});});}
    catch(_){$('ready-status').dataset.t='offline_failed';$('ready-status').textContent=t('offline_failed');}
  }
  read();state.sessions.forEach(item=>selection.add(item.id));render();acquire();prepareOffline();
})();

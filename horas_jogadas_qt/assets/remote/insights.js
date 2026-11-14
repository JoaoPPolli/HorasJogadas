"use strict";
(()=>{
 const H=window.HorasPhone,D=window.HorasDesktop,n=D.node,b=D.button;
 const words={pt:{details:'Página do jogo',back:'Voltar',sessions:'Sessões',saved:'Tempo salvo',current:'Sessão atual',total:'Total',completions:'Conclusões e platina',empty:'Nenhuma conclusão vinculada.',recent:'Sessões recentes',recap:'Retrospectiva',intro:'Escolha o período e gere sua imagem para compartilhar.',year:'Ano',month:'Mês',all:'Ano inteiro',preview:'Atualizar prévia',download:'Baixar PNG',detect:'Detecção automática',enable:'Ativar neste jogo',disable:'Desativar neste jogo',configure:'Escolha o executável nas Configurações do aplicativo no PC.',global:'A detecção geral está desativada no PC.',history:'Histórico',first:'Primeira sessão',last:'Última sessão',start:'Iniciar',resume:'Retomar',pause:'Pausar',finish:'Encerrar e salvar',confirm:'Salvar esta sessão no histórico do PC?',close:'Fechar',failed:'Não foi possível concluir. Confira a conexão.'},en:{details:'Game page',back:'Back',sessions:'Sessions',saved:'Saved playtime',current:'Current session',total:'Total',completions:'Completions and platinum',empty:'No linked completions.',recent:'Recent sessions',recap:'Gaming recap',intro:'Choose a period and create an image to share.',year:'Year',month:'Month',all:'Entire year',preview:'Update preview',download:'Download PNG',detect:'Automatic detection',enable:'Enable for this game',disable:'Disable for this game',configure:'Choose the executable in the PC app settings.',global:'Global detection is disabled on the PC.',history:'History',first:'First session',last:'Latest session',start:'Start',resume:'Resume',pause:'Pause',finish:'Finish and save',confirm:'Save this session to PC history?',close:'Close',failed:'Could not finish. Check your connection.'}};
 Object.assign(words.pt,{individual:'Retrospectiva do jogo',individualIntro:'Somente as sessões salvas deste jogo: horas, média, maior sessão e evolução no período.'});
 Object.assign(words.en,{individual:'Game recap',individualIntro:'Only this game’s saved sessions: playtime, average, longest session and activity over time.'});
 Object.assign(words.pt,{completedRecap:'Retrospectiva de Zerados',completedIntro:'Pelas datas da lista de Zerados. Campanha e platina adicional entram uma única vez; cada nova jogada conta como um registro.'});
 Object.assign(words.en,{completedRecap:'Completion recap',completedIntro:'Uses dates in your completion list. Campaign and extra platinum time are counted once; each replay counts as a record.'});
 const t=k=>words[H.language()==='en'?'en':'pt'][k]||k;
 const view=(name,values)=>H.api('/api/view/'+name+'?'+new URLSearchParams(values));
 async function showGame(id){
  let data;try{data=await view('game',{id});}catch(e){D.notice(H.errorText(e.code));return;}
  const host=n('div','insight-page');host.id='game-details-content';
  const form=D.formDialog(data.name,[{type:'html',element:host}],()=>true,{wide:true,submitLabel:t('back')});form.form.querySelector('#desktop-submit').hidden=true;form.form.querySelector('#desktop-cancel').textContent=t('close');
  let revision='',baseAt=performance.now(),game=null;
  const badge=n('span','game-status');host.append(badge);const clock=n('strong','insight-clock');clock.id='game-details-clock';const controls=n('div','insight-actions');
  const metrics=n('div','insight-grid'),body=n('div');host.append(clock,controls,metrics,body);
  const button=(kind,title)=>b(title,async()=>{const current=H.getState()?.games.find(g=>g.id===id);if(!current)return;try{if(kind==='finish'){D.confirmAction(t('finish'),t('confirm'),()=>H.commandRaw({action:'finish',game_id:id,revision:current.revision}));return;}await H.commandRaw({action:kind,game_id:id,revision:current.revision});await reload();}catch(e){form.error.textContent=H.errorText(e.code);}});
  const start=button('start',t('start')),pause=button('pause',t('pause')),finish=button('finish',t('finish'));controls.append(start,pause,finish);
  function counter(){if(!game){clock.textContent='—';start.disabled=pause.disabled=finish.disabled=true;return;}badge.textContent=game.status_label||game.status;badge.dataset.status=game.status;start.textContent=t(game.paused?'resume':'start');pause.textContent=t('pause');finish.textContent=t('finish');form.form.querySelector('#desktop-cancel').textContent=t('close');clock.textContent=H.clock(Math.floor(game.seconds+(game.running?(performance.now()-baseAt)/1000:0)));start.disabled=!H.ready()||game.running;pause.disabled=!H.ready()||!game.running;finish.disabled=!H.ready()||!game.pending;}
  function render(){
   form.dialog.dataset.workspaceRevision=data.revision;
   metrics.replaceChildren();for(const [name,value]of [[t('total'),H.duration(data.total_seconds)],[t('sessions'),data.session_count],[t('saved'),H.duration(data.saved_seconds)]]){const card=n('div','insight-metric');card.append(n('small','',name),n('strong','',String(value)));metrics.append(card);}
   body.replaceChildren();body.append(n('p','insight-muted',t('first')+': '+(data.first||'—')),n('p','insight-muted',t('last')+': '+(data.last||'—')),n('h3','',t('detect')));
   if(data.detection.configured)body.append(b(data.detection.enabled?t('disable'):t('enable'),async()=>{try{await D.mutate({action:'detection_toggle',game_id:id,enabled:!data.detection.enabled});await reload();}catch(e){form.error.textContent=H.errorText(e.code);}}));else body.append(n('p','insight-muted',t('configure')));
   if(!data.detection.active)body.append(n('small','insight-muted',t('global')));
   body.append(n('h3','',t('completions')));if(!data.completions.length)body.append(n('p','insight-muted',t('empty')));
   for(const r of data.completions){const card=n('section','insight-entry');card.append(n('strong','',r.name),n('p','insight-muted',`${r.month}/${r.year} · ${r.seconds===null?'—':H.clock(r.seconds)}`));if(r.platinum_seconds!==null)card.append(n('p','insight-muted','✦ '+H.clock(r.platinum_seconds)+(r.platinum_completed?' ✓':'')));if(r.notes)card.append(n('p','',r.notes));body.append(card);}
   body.append(n('h3','',t('recent')));for(const s of data.sessions){const line=n('div','insight-session');line.append(n('span','',s.end),n('strong','',H.clock(s.seconds)));body.append(line);}
   const recapButton=b(t('individual'),()=>{form.dialog.close();showRecap(id);});recapButton.id='game-recap-open';
   const recapActions=n('div','insight-actions');recapActions.append(recapButton,b(t('history'),()=>{form.dialog.close();D.navigate('history');}));body.append(recapActions);
  }
  async function reload(){if(!form.dialog.open)return;data=await view('game',{id});render();}
  render();const unsubscribe=H.subscribe((state,connected)=>{game=state?.games.find(g=>g.id===id);baseAt=performance.now();counter();if(state&&revision&&revision!==state.workspace_revision)reload().catch(error=>{form.error.textContent=H.errorText(error.code);});revision=state?.workspace_revision||'';});
  const timer=setInterval(counter,250);form.dialog.addEventListener('close',()=>{clearInterval(timer);unsubscribe();},{once:true});
 }
 async function showRecap(gameId=null,options={}){
  const source=options.source||'sessions',scope=source==='completed'?{source}:gameId?{game_id:gameId}:{};
  const selectedYear=options.year||new Date().getFullYear();let data;try{data=await view('recap',{year:selectedYear,month:0,...scope});}catch(e){D.notice(H.errorText(e.code));return;}
  const years=data.years.map(y=>[y,String(y)]),months=[[0,t('all')],...Array.from({length:12},(_,i)=>[i+1,new Intl.DateTimeFormat(H.language()==='en'?'en':'pt-BR',{month:'long'}).format(new Date(2024,i,1))])];
  const title=source==='completed'?t('completedRecap'):data.game?t('individual')+' · '+data.game.name:t('recap');
  const image=n('img','insight-recap-image');image.alt=title;image.id='recap-image';let epoch=0,filename=data.filename;
  const preview=b(t('preview'),()=>load());preview.id='recap-preview';
  const form=D.formDialog(title,[{name:'year',label:t('year'),type:'select',value:selectedYear,options:years},{name:'month',label:t('month'),type:'select',value:0,options:months},{type:'html',element:preview},{type:'html',element:image}],async()=>{await H.download('/api/export/recap_png?'+new URLSearchParams({year:form.inputs.year.value,month:form.inputs.month.value,...scope}),filename);return false;},{description:t(source==='completed'?'completedIntro':data.game?'individualIntro':'intro'),wide:true,submitLabel:t('download')});
  form.dialog.dataset.gameId=gameId||'';
  form.dialog.dataset.recapSource=source;
  async function load(){const call=++epoch;preview.disabled=true;form.form.querySelector('#desktop-submit').disabled=true;form.error.textContent='';try{const result=await H.api('/api/query',{query:'recap_preview',year:Number(form.inputs.year.value),month:Number(form.inputs.month.value),...scope});if(call===epoch&&form.dialog.open){image.src=result.image;filename=result.filename;form.form.querySelector('#desktop-submit').disabled=false;}}catch(e){if(call===epoch&&form.dialog.open)form.error.textContent=H.errorText(e.code);}finally{if(call===epoch)preview.disabled=false;}}
  form.inputs.year.addEventListener('change',load);form.inputs.month.addEventListener('change',load);await load();
 }
 window.HorasInsights={showGame,showRecap};
 function addRecap(){for(const page of ['stats','completed']){const tools=document.querySelector('#desktop-'+page+' .desk-tools'),id=page==='stats'?'recap-open':'completed-recap-open';if(tools&&!document.getElementById(id)){const button=b(t('recap'),()=>page==='stats'?showRecap():showRecap(null,{source:'completed',year:Number(document.querySelector('#completed-year').value)}));button.id=id;tools.prepend(button);}}}
 const observer=new MutationObserver(addRecap);for(const page of ['stats','completed'])observer.observe(document.querySelector('#desktop-'+page),{childList:true,subtree:true});
})();

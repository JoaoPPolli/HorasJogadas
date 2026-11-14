"""Consultas somente de leitura para a página do jogo e a retrospectiva."""
from collections import defaultdict
from calendar import monthrange
from datetime import date
import re
from .platinum import matched_game
from horas_jogadas.zerados import resumo_ano


def game_details(c, key):
    game=c.repo.jogo_por_id(key)
    if game is None:raise ValueError('Game not found')
    sessions=[s for s in reversed(c.repo.sessoes) if s.jogo_id==key]
    dates=[s.data_dt for s in sessions if s.data_dt]
    saved=sum(s.segundos for s in sessions);current=int(c.timers[key].seconds())
    return dict(id=key,name=game.nome,status=game.status,saved_seconds=saved,
                current_seconds=current,total_seconds=saved+current,
                session_count=len(sessions),average_seconds=int(saved/len(sessions)) if sessions else 0,
                first=min(dates).strftime('%Y-%m-%d %H:%M:%S') if dates else None,
                last=max(dates).strftime('%Y-%m-%d %H:%M:%S') if dates else None,
                sessions=[dict(id=s.sessao_id,name=s.jogo,seconds=s.segundos,end=s.data,start=s.inicio) for s in sessions[:100]],
                completions=[dict(id=r.id,name=r.nome,year=r.ano,month=r.mes,day=r.dia,seconds=r.segundos,
                                  platinum_seconds=r.platina_segundos,platinum_completed=r.platina_concluida,
                                  dlc=r.dlc,type=r.tipo,notes=r.notas,game_id=r.jogo_id)
                             for r in c.zerados.registros if matched_game(c,r)==key])


def recap(c,year,month=0,game_id=None):
    if type(year) is not int or not 1900<=year<=9999 or type(month) is not int or not 0<=month<=12:raise ValueError('Invalid period')
    game=None
    if game_id is not None:
        if not isinstance(game_id,str) or not (game:=c.repo.jogo_por_id(game_id)):raise ValueError('Game not found')
    totals=defaultdict(int);names={g.id:g.nome for g in c.repo.jogos};days=defaultdict(int);count=0;longest=0
    for s in c.repo.sessoes:
        if game is not None and s.jogo_id!=game_id:continue
        portions={d:seconds for d,seconds in s.segundos_por_dia().items() if d.year==year and (not month or d.month==month)}
        seconds=sum(portions.values())
        if not seconds:continue
        count+=1;longest=max(longest,seconds)
        key=s.jogo_id or 'legacy:'+s.jogo.casefold();names.setdefault(key,s.jogo);totals[key]+=seconds
        for day,value in portions.items():days[day]+=value
    completions=[r for r in c.zerados.registros if r.ano==year and (not month or r.mes==month) and (game is None or matched_game(c,r)==game_id)]
    data=dict(year=year,month=month,total_seconds=sum(totals.values()),sessions=count,games=len(totals),
                days=len(days),longest_seconds=longest,
                average_seconds=sum(totals.values())//count if count else 0,
                completed=sum(r.tipo=='zerado' and not r.dlc for r in completions),
                dlcs=sum(r.tipo=='zerado' and r.dlc for r in completions),
                top=[dict(id=key,name=names[key],seconds=value) for key,value in sorted(totals.items(),key=lambda item:(-item[1],names[item[0]].casefold()))[:5]],
                activity=[dict(date=d.isoformat(),seconds=value) for d,value in sorted(days.items())])
    if game is not None:
        buckets=defaultdict(int)
        for day,seconds in days.items():buckets[day.day if month else day.month]+=seconds
        data['game']=dict(id=game.id,name=game.nome)
        data['timeline']=[dict(index=i,seconds=buckets[i]) for i in range(1,(monthrange(year,month)[1] if month else 12)+1)]
    return data


def available_years(c,game_id=None):
    years={date.today().year}|{r.ano for r in c.zerados.registros if game_id is None or matched_game(c,r)==game_id}
    for s in c.repo.sessoes:
        if game_id is None or s.jogo_id==game_id:years.update(d.year for d in s.segundos_por_dia())
    return sorted(years,reverse=True)


def completed_years(c):
    return sorted({date.today().year}|{r.ano for r in c.zerados.registros},reverse=True)


def completed_recap(c,year,month=0):
    """Cada registro representa uma jogada; datas e tempos desconhecidos são preservados."""
    if type(year) is not int or not 1900<=year<=9999 or type(month) is not int or not 0<=month<=12:raise ValueError('Invalid period')
    records=[r for r in c.zerados.registros if r.ano==year and (not month or r.mes==month)]
    summary=resumo_ano(records,year)
    recent=sorted(enumerate(records),key=lambda pair:(pair[1].mes,pair[1].dia or 0,pair[0]),reverse=True)
    return dict(source='completed',year=year,month=month,records=summary.registros,
                games=summary.jogos_zerados,dlcs=summary.dlcs_zeradas,experiences=summary.experiencias,
                total_seconds=summary.segundos_registrados,
                campaign_seconds=sum(r.segundos for r in records if r.segundos is not None),
                platinum_seconds=summary.platina_segundos,
                platinum_completed=sum(r.platina_concluida for r in records),
                without_time=summary.sem_tempo,
                has_time=any(r.segundos is not None or r.platina_segundos is not None for r in records),
                campaign_known=any(r.segundos is not None for r in records),
                platinum_known=any(r.platina_segundos is not None for r in records),
                timeline=[dict(index=i,count=sum(r.mes==i and r.tipo=='zerado' for r in records)) for i in range(1,13)],
                recent=[dict(id=r.id,name=r.nome,month=r.mes,day=r.dia,type=r.tipo,dlc=r.dlc,
                             seconds=(r.segundos or 0)+(r.platina_segundos or 0) if r.segundos is not None or r.platina_segundos is not None else None,
                             partial=r.segundos is None,
                             platinum_completed=r.platina_concluida) for _,r in recent[:5]])


def recap_filename(data):
    name='-Zerados' if data.get('source')=='completed' else ''
    if data.get('game'):
        title=re.sub(r'[<>:"/\\|?*\x00-\x1f]', '-',data['game']['name']).strip(' .')[:80]
        title=title.encode('utf-8')[:160].decode('utf-8','ignore').rstrip(' .') or 'Jogo'
        name='-'+title
    return f"HorasJogadas{name}-{data['year']}-{data['month']:02d}.png"

"""Consultas somente de leitura para a página do jogo e a retrospectiva."""
from collections import defaultdict
from datetime import date
from horas_jogadas import stats
from .platinum import matched_game


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


def recap(c,year,month=0):
    if type(year) is not int or not 1900<=year<=9999 or type(month) is not int or not 0<=month<=12:raise ValueError('Invalid period')
    totals=defaultdict(int);names={g.id:g.nome for g in c.repo.jogos};days=defaultdict(int);count=0;longest=0
    for s in c.repo.sessoes:
        portions={d:seconds for d,seconds in s.segundos_por_dia().items() if d.year==year and (not month or d.month==month)}
        seconds=sum(portions.values())
        if not seconds:continue
        count+=1;longest=max(longest,seconds)
        key=s.jogo_id or 'legacy:'+s.jogo.casefold();names.setdefault(key,s.jogo);totals[key]+=seconds
        for day,value in portions.items():days[day]+=value
    completions=[r for r in c.zerados.registros if r.ano==year and (not month or r.mes==month)]
    return dict(year=year,month=month,total_seconds=sum(totals.values()),sessions=count,games=len(totals),
                days=len(days),longest_seconds=longest,
                completed=sum(r.tipo=='zerado' and not r.dlc for r in completions),
                dlcs=sum(r.tipo=='zerado' and r.dlc for r in completions),
                top=[dict(id=key,name=names[key],seconds=value) for key,value in sorted(totals.items(),key=lambda item:(-item[1],names[item[0]].casefold()))[:5]],
                activity=[dict(date=d.isoformat(),seconds=value) for d,value in sorted(days.items())])


def available_years(c):
    years={date.today().year}|{r.ano for r in c.zerados.registros}
    for s in c.repo.sessoes:years.update(d.year for d in s.segundos_por_dia())
    return sorted(years,reverse=True)

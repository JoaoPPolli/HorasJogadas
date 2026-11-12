"""Cálculo somente de leitura; o formulário confirma e salva a conclusão."""
from horas_jogadas.utils import normalizar_texto

class ExtraTimeError(ValueError):
    pass


def matched_game(controller, record):
    if record.jogo_id:
        return record.jogo_id if record.jogo_id in controller.timers else None
    matches=[g.id for g in controller.repo.jogos if normalizar_texto(g.nome)==normalizar_texto(record.nome)]
    return matches[0] if len(matches)==1 else None


def calculate_extra(controller, record, game_id, base_seconds, completed=None):
    if completed is None:completed=record.platina_concluida
    if completed:raise ExtraTimeError('platinum_locked')
    if type(base_seconds) is not int or base_seconds<0:raise ExtraTimeError('platinum_need_duration')
    if not isinstance(game_id,str) or game_id not in controller.timers:raise ExtraTimeError('platinum_need_game')
    others=[r for r in controller.zerados.registros if r.id!=record.id and matched_game(controller,r)==game_id]
    if others:raise ExtraTimeError('platinum_multiple')
    total=controller.repo.totais_por_jogo_id().get(game_id,0)+int(controller.timers[game_id].seconds())
    if total<base_seconds:raise ExtraTimeError('platinum_less')
    return dict(seconds=total-base_seconds,total_seconds=total)

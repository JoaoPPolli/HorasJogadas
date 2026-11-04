"""Histórico, estatísticas e Zerados do PC adaptados ao controle conectado.

As escritas são chamadas pelo controlador remoto dentro da transação existente;
esta classe nunca abre diálogos, escolhe caminhos do computador ou cria threads.
"""
import io
import csv
from dataclasses import replace
from datetime import date, datetime, timedelta

from horas_jogadas import i18n, stats, exportacao
from horas_jogadas.constants import STATUS_OPCOES
from horas_jogadas.edicao_sessao import validar, LIMITE_CONFIRMACAO_S
from horas_jogadas.models import novo_id
from horas_jogadas.utils import normalizar_texto
from horas_jogadas.zerados import (Conclusao, MESES, MESES_EN, resumo_ano,
                                  interpretar_txt, exportar_txt)
from .remote_server import RemoteError

ACTIONS = frozenset({'history_save', 'history_delete', 'history_undo', 'history_clear',
                     'stats_delete_group', 'completion_save', 'completion_replay',
                     'completion_delete', 'completion_undo', 'completion_import'})
MAX_SECONDS = 10 ** 12


def needs_backup(action):
    return action in {'history_delete', 'history_clear', 'stats_delete_group',
                      'completion_delete', 'completion_import'}


def _text(value, maximum=200, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) > maximum or '\x00' in value:
        raise RemoteError(400, 'invalid')
    value = value.strip()
    if not optional and not value:
        raise RemoteError(400, 'invalid')
    return value


def _integer(value, low=0, high=MAX_SECONDS, optional=False):
    if value is None and optional:
        return None
    if type(value) is not int or not low <= value <= high:
        raise RemoteError(400, 'invalid')
    return value


def _query_int(query, key, default, low, high):
    value = query.get(key, default)
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    return _integer(value, low, high)


def _date(value):
    return value.strftime('%Y-%m-%d %H:%M:%S') if value is not None else None


def _session(session):
    return dict(id=session.sessao_id, game_id=session.jogo_id, name=session.jogo,
                seconds=session.segundos, start=_date(session.inicio_dt),
                end=_date(session.data_dt) or session.data, warning=session.segundos > 43200)


def _completion(record):
    return dict(id=record.id, name=record.nome, year=record.ano, month=record.mes,
                day=record.dia, seconds=record.segundos, platinum_seconds=record.platina_segundos,
                type=record.tipo, dlc=record.dlc, notes=record.notas, origin=record.origem)


def _group(group):
    return dict(key=group.chave, game_id=group.jogo_id, name=group.nome, status=group.status,
                total_seconds=group.total, sessions=group.sessoes,
                first=_date(group.primeira), last=_date(group.ultima))


class PhoneRecords:
    actions = ACTIONS
    needs_backup = staticmethod(needs_backup)

    def __init__(self, control):
        self.control = control

    @property
    def window(self):
        return self.control.window

    @property
    def c(self):
        return self.window.c

    def _find_session(self, identifier):
        identifier = _text(identifier, 128)
        result = next((s for s in self.c.repo.sessoes if s.sessao_id == identifier), None)
        if result is None:
            raise RemoteError(404, 'not_found')
        return result

    def _find_completion(self, identifier):
        identifier = _text(identifier, 128)
        result = next((r for r in self.c.zerados.registros if r.id == identifier), None)
        if result is None:
            raise RemoteError(404, 'not_found')
        return result

    def view(self, page, query=None):
        query = {} if query is None else query
        if not isinstance(query, dict):
            raise RemoteError(400, 'invalid')
        if page == 'history':
            limit = _query_int(query, 'limit', 100, 1, 100)
            offset = _query_int(query, 'offset', 0, 0, 1000000000)
            search = normalizar_texto(_text(query.get('search', ''), 200, optional=True) or '')
            sessions = list(reversed(self.c.repo.sessoes))
            if search:
                sessions = [s for s in sessions if search in normalizar_texto(s.jogo)]
            result = dict(sessions=[_session(s) for s in sessions[offset:offset + limit]],
                          total=len(sessions), offset=offset, limit=limit, can_undo=bool(self.c.undo))
        elif page == 'stats':
            period = query.get('period', '7d')
            if period not in ('7d', '8s', '6m'):
                raise RemoteError(400, 'invalid')
            status = query.get('status')
            if status in ('', 'all'):
                status = None
            if status is not None and status not in STATUS_OPCOES:
                raise RemoteError(400, 'invalid')
            groups = stats.agrupar_por_jogo(self.c.repo.jogos, self.c.repo.sessoes)
            summary = stats.resumo_geral(groups, self.c.repo.sessoes)
            current, best = stats.sequencias(self.c.repo.sessoes)
            chart = stats.horas_por_periodo(self.c.repo.sessoes, period,
                dias_semana=i18n.lista('dias_semana'), meses_nomes=i18n.lista('meses'), formato_semana=i18n.t('fmt.semana'))
            result = dict(summary=dict(total_seconds=summary.total_segundos, sessions=summary.total_sessoes,
                                       average_seconds=summary.media_sessao,
                                       longest=_session(summary.sessao_mais_longa) if summary.sessao_mais_longa else None,
                                       current_streak=current, best_streak=best),
                          period=period, chart=[dict(label=label, seconds=seconds) for label, seconds in chart],
                          top=[_group(g) for g in stats.top_jogos(groups, 5)],
                          groups=[_group(g) for g in groups if status is None or g.status == status])
        elif page in ('completed', 'completions'):
            year = _query_int(query, 'year', date.today().year, 1900, 9999)
            records = sorted([r for r in self.c.zerados.registros if r.ano == year],
                             key=lambda r: (r.mes, r.dia or 0, r.nome))
            summary = resumo_ano(self.c.zerados.registros, year)
            names = MESES_EN if i18n.idioma_atual() == 'en' else MESES
            result = dict(year=year, years=sorted({date.today().year, year} | {r.ano for r in self.c.zerados.registros}, reverse=True),
                          records=[_completion(r) for r in records],
                          months=[dict(month=month, name=names[month - 1], records=[_completion(r) for r in records if r.mes == month])
                                  for month in range(1, 13) if any(r.mes == month for r in records)],
                          summary=dict(games=summary.jogos_zerados, dlcs=summary.dlcs_zeradas,
                                       experiences=summary.experiencias, total_seconds=summary.segundos_registrados,
                                       platinum_seconds=summary.platina_segundos, without_time=summary.sem_tempo,
                                       records=summary.registros,
                                       has_time=any(r.segundos is not None or r.platina_segundos is not None for r in records)),
                          can_undo=bool(getattr(self.window, 'deleted_completions', [])))
        else:
            raise RemoteError(404, 'not_found')
        result['revision'] = self.control.workspace_revision()
        return result

    def preview_import(self, text, year):
        text = _text(text, 2 * 1024 * 1024)
        year = _integer(year, 1900, 9999)
        items = interpretar_txt(text, year)
        if len(items) > 2000:
            raise RemoteError(400, 'invalid')
        return dict(year=year, revision=self.control.workspace_revision(),
                    items=[dict(index=index, line=item.linha, text=item.texto,
                                record=_completion(item.registro) if item.registro else None,
                                warning=item.aviso, selected=bool(item.selecionado and item.registro and not item.aviso))
                           for index, item in enumerate(items)])

    def _new_completion(self, body, original=None):
        values = body.get('record', body)
        if not isinstance(values, dict):
            raise RemoteError(400, 'invalid')
        identifier = values.get('id')
        if identifier and original is None:
            original = self._find_completion(identifier)
        record = original or Conclusao('', date.today().year, date.today().month)
        name = _text(values.get('name', record.nome), 200)
        year = _integer(values.get('year', record.ano), 1900, 9999)
        month = _integer(values.get('month', record.mes), 1, 12)
        day = _integer(values.get('day', record.dia), 1, 31, optional=True)
        seconds = _integer(values.get('seconds', record.segundos), optional=True)
        platinum = _integer(values.get('platinum_seconds', record.platina_segundos), optional=True)
        kind = values.get('type', record.tipo)
        if kind not in ('zerado', 'experiencia') or type(values.get('dlc', record.dlc)) is not bool:
            raise RemoteError(400, 'invalid')
        notes = _text(values.get('notes', record.notas), 10000, optional=True)
        return replace(record, nome=name, ano=year, mes=month, dia=day, segundos=seconds,
                       platina_segundos=platinum, tipo=kind, dlc=values.get('dlc', record.dlc), notas=notes or '').validar()

    def execute(self, body):
        if not isinstance(body, dict) or body.get('action') not in ACTIONS:
            raise RemoteError(400, 'invalid')
        action = body['action']
        try:
            return self._execute(action, body)
        except (ValueError, TypeError, OverflowError):
            raise RemoteError(400, 'invalid') from None

    def _execute(self, action, body):
        if action == 'history_save':
            original = self._find_session(body['session_id']) if body.get('session_id') else None
            game_id = body.get('game_id')
            game = self.c.repo.jogo_por_id(game_id) if isinstance(game_id, str) else None
            if game is not None:
                name = game.nome
            elif original is not None and game_id == original.jogo_id:
                name = original.jogo
            else:
                raise RemoteError(404, 'not_found')
            seconds = _integer(body.get('seconds'), 1)
            end = _text(body.get('end'), 32)
            hours, rest = divmod(seconds, 3600)
            end_dt, seconds = validar(end, str(hours), str(rest // 60), str(rest % 60), datetime.now())
            if seconds > LIMITE_CONFIRMACAO_S and body.get('confirmed_long') is not True:
                raise RemoteError(409, 'confirm_long')
            if original is not None:
                self.c.repo.atualizar_sessao(original.sessao_id, game_id, name, seconds, end_dt)
                saved_id = original.sessao_id
            else:
                saved = self.c.repo.adicionar_sessao(game_id, name, seconds, end_dt - timedelta(seconds=seconds), end_dt)
                saved_id = saved.sessao_id
            return {'saved_id': saved_id}
        if action == 'history_delete':
            if body.get('confirmed') is not True:
                raise RemoteError(409, 'confirm_required')
            session = self._find_session(body.get('session_id'))
            self.c.delete_session(session)
            return {'deleted': 1}
        if action == 'history_undo':
            if not self.c.undo:
                raise RemoteError(409, 'conflict')
            self.c.undo_session()
            return {'restored': 1}
        if action == 'history_clear':
            if body.get('confirmed') is not True:
                raise RemoteError(409, 'confirm_required')
            count = len(self.c.repo.sessoes)
            self.c.repo.limpar_sessoes(); self.c.undo.clear()
            return {'deleted': count}
        if action == 'stats_delete_group':
            if body.get('confirmed') is not True:
                raise RemoteError(409, 'confirm_required')
            key = _text(body.get('key'), 400)
            if key not in {g.chave for g in stats.agrupar_por_jogo(self.c.repo.jogos, self.c.repo.sessoes)}:
                raise RemoteError(404, 'not_found')
            return {'deleted': self.c.repo.remover_sessoes_do_grupo(key)}
        if action == 'completion_save':
            record = self._new_completion(body)
            self.c.zerados.guardar(record)
            return {'saved_id': record.id, 'selected_year': record.ano}
        if action == 'completion_replay':
            original = self._find_completion(body.get('id'))
            today = date.today()
            template = replace(original, id=novo_id(), ano=today.year, mes=today.month, dia=None,
                               segundos=None, platina_segundos=None, notas='', origem='manual')
            record = self._new_completion(body, template)
            self.c.zerados.guardar(record)
            return {'saved_id': record.id, 'selected_year': record.ano}
        if action == 'completion_delete':
            if body.get('confirmed') is not True:
                raise RemoteError(409, 'confirm_required')
            original = self._find_completion(body.get('id'))
            self.c.zerados.excluir(original.id)
            # Caller commits the returned receipt to the shared UI undo stack
            # only after transaction succeeds, via after_commit().
            return {'deleted': 1, 'deleted_record': _completion(original)}
        if action == 'completion_undo':
            deleted = getattr(self.window, 'deleted_completions', [])
            if not deleted:
                raise RemoteError(409, 'conflict')
            self.c.zerados.guardar(deleted[-1])
            return {'restored': 1, 'pop_completion_undo': True}
        if action == 'completion_import':
            if body.get('confirmed') is not True:
                raise RemoteError(409, 'confirm_required')
            text, year = _text(body.get('text'), 2 * 1024 * 1024), _integer(body.get('year'), 1900, 9999)
            items = interpretar_txt(text, year)
            if len(items) > 2000:
                raise RemoteError(400, 'invalid')
            selected = body.get('selected')
            if not isinstance(selected, list) or not selected or len(selected) > len(items):
                raise RemoteError(400, 'invalid')
            indexes = [_integer(index, 0, len(items) - 1) for index in selected]
            if len(set(indexes)) != len(indexes):
                raise RemoteError(400, 'invalid')
            if any(items[index].registro is None or items[index].aviso for index in indexes):
                raise RemoteError(400, 'invalid')
            return {'imported': self.c.zerados.importar([items[index].registro for index in indexes])}
        raise RemoteError(400, 'invalid')

    def after_commit(self, body, result):
        """Mantém o desfazer da janela após o commit; não altera arquivos."""
        if 'selected_year' in result:
            self.window.year = result.pop('selected_year')
        if body['action'] == 'completion_delete':
            value = result.pop('deleted_record', None)
            if value is not None:
                if not hasattr(self.window, 'deleted_completions'):
                    self.window.deleted_completions = []
                self.window.deleted_completions.append(Conclusao(
                    value['name'], value['year'], value['month'], value['seconds'], value['day'],
                    value['platinum_seconds'], value['notes'], value['type'], value['id'], value['origin'], value['dlc']))
        if result.pop('pop_completion_undo', False):
            self.window.deleted_completions.pop()

    def export(self, kind, query=None):
        query = {} if query is None else query
        if kind in ('history_csv', 'summary_csv'):
            lines = (exportacao.linhas_historico if kind == 'history_csv' else exportacao.linhas_resumo)(self.c.repo.jogos, self.c.repo.sessoes)
            buffer = io.StringIO(newline='')
            csv.writer(buffer, delimiter=i18n.t('csv.sep'), quoting=csv.QUOTE_MINIMAL).writerows(lines)
            return buffer.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8', ('horas-jogadas-historico.csv' if kind == 'history_csv' else 'horas-jogadas-resumo.csv')
        if kind == 'completions_txt':
            year = _query_int(query, 'year', date.today().year, 1900, 9999)
            return exportar_txt(self.c.zerados.registros, year).encode('utf-8'), 'text/plain; charset=utf-8', f'zerados-{year}.txt'
        raise RemoteError(404, 'not_found')

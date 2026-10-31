"""Importação revisada de sessões offline do celular, sem substituir registros."""
import json
import math
import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                              QHeaderView, QMessageBox, QTableWidgetItem, QVBoxLayout, QWidget)

from horas_jogadas.i18n import idioma_atual
from horas_jogadas.models import Sessao
from horas_jogadas.utils import chave_nome, formatar_hhmmss
from .backup import create_full, read_full
from .widgets import button, label, row, table

MAX_BYTES = 1024 * 1024
MAX_RECORDS = 500
MAX_SECONDS = 7 * 24 * 3600
MOBILE_NAMESPACE = uuid.UUID('ac162b8a-6039-5460-a517-6e40da47c587')
DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})')

COPY = {
    'pt': {
        'title': 'Importar sessões do celular', 'intro': 'Confira as partidas feitas com o PC desligado e escolha onde salvá-las. Um backup verificado será criado antes da importação.',
        'game': 'Jogo no celular', 'start': 'Início', 'duration': 'Duração', 'destination': 'Jogo na biblioteca', 'state': 'Situação',
        'new': 'Criar novo jogo', 'choose': 'Escolha um jogo…', 'ready': 'Pronta para importar', 'duplicate': 'Já importada',
        'toggle': 'Marcar / desmarcar todas', 'import': 'Importar selecionadas', 'cancel': 'Cancelar',
        'selected': '{selected} selecionada(s) · {duplicates} já importada(s)',
        'preserved': 'Sessões já importadas não serão duplicadas nem sobrescritas, mesmo se você as editou depois no PC. Cancelar não altera os registros.',
        'invalid': 'Arquivo de sessões do celular inválido. Exporte novamente pelo contador offline.',
        'invalid_row': 'Sessão {number}: dados inválidos. Confira nome, duração e datas no celular.',
        'conflict': 'O mesmo identificador aparece mais de uma vez no arquivo. Exporte novamente sem mesclar sessões manualmente.',
        'mapping': 'Confira o jogo de destino de todas as sessões selecionadas.',
        'missing': 'Um jogo de destino mudou ou foi removido. Feche a revisão e abra o arquivo novamente.',
        'ambiguous': 'Há mais de um jogo com este nome. Escolha o destino na revisão.',
        'error': 'Não foi possível importar',
    },
    'en': {
        'title': 'Import phone sessions', 'intro': 'Review sessions played while your PC was off and choose where to save them. A verified backup will be created before importing.',
        'game': 'Game on phone', 'start': 'Started', 'duration': 'Duration', 'destination': 'Library game', 'state': 'Status',
        'new': 'Create new game', 'choose': 'Choose a game…', 'ready': 'Ready to import', 'duplicate': 'Already imported',
        'toggle': 'Check / uncheck all', 'import': 'Import selected', 'cancel': 'Cancel',
        'selected': '{selected} selected · {duplicates} already imported',
        'preserved': 'Previously imported sessions are never duplicated or overwritten, even if you edited them later on your PC. Cancelling changes no records.',
        'invalid': 'Invalid phone session file. Export it again from the offline timer.',
        'invalid_row': 'Session {number}: invalid details. Check the name, duration and dates on your phone.',
        'conflict': 'The file contains a repeated session identifier. Export again without manually merging sessions.',
        'mapping': 'Check the destination game for every selected session.',
        'missing': 'A destination game changed or was removed. Close the review and open the file again.',
        'ambiguous': 'More than one game has this name. Choose the destination in the review.',
        'error': 'Could not import',
    },
}


def text(key):
    return COPY['en' if idioma_atual() == 'en' else 'pt'][key]


@dataclass(frozen=True)
class MobileSession:
    id: str
    game: str
    game_id: Optional[str]
    seconds: int
    started_at: datetime
    ended_at: datetime
    # '' = resolve by current name/ID; None = explicitly create a new game.
    destination_id: Optional[str] = ''

    @property
    def session_id(self):
        return str(uuid.uuid5(MOBILE_NAMESPACE, self.id))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(text('invalid'))
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(text('invalid'))


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(text('invalid'))
    return number


def _date(value):
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError
    return parsed


def _record(value, number, now):
    required = {'id', 'game', 'seconds', 'started_at', 'ended_at'}
    try:
        if not isinstance(value, dict) or not required <= set(value) <= required | {'game_id'}:
            raise ValueError
        identifier = value['id']
        if not isinstance(identifier, str) or len(identifier) != 36:
            raise ValueError
        canonical = str(uuid.UUID(identifier))
        if identifier.lower() != canonical:
            raise ValueError
        name = value['game']
        if not isinstance(name, str) or not 1 <= len(name) <= 200 or any(ord(c) < 32 for c in name):
            raise ValueError
        name = ' '.join(name.split())
        if not name:
            raise ValueError
        game_id = value.get('game_id')
        if game_id is not None and (not isinstance(game_id, str) or not 1 <= len(game_id) <= 128 or any(ord(c) < 32 for c in game_id)):
            raise ValueError
        seconds = value['seconds']
        if not isinstance(seconds, int) or isinstance(seconds, bool) or not 1 <= seconds <= MAX_SECONDS:
            raise ValueError
        start, end = _date(value['started_at']), _date(value['ended_at'])
        if start < datetime(2000, 1, 1, tzinfo=timezone.utc) or start > end or end > now + timedelta(minutes=5):
            raise ValueError
        if seconds > (end - start).total_seconds() + 2:
            raise ValueError
        return MobileSession(canonical, name, game_id, seconds, start, end)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(text('invalid_row').format(number=number)) from None


def parse_mobile(data):
    """Valida o arquivo inteiro antes de permitir qualquer escrita no domínio."""
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_BYTES:
        raise ValueError(text('invalid'))
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant, parse_float=_finite_float)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError(text('invalid')) from None
    if (not isinstance(value, dict) or set(value) != {'format', 'version', 'sessions'}
            or value['format'] != 'HorasJogadas-Mobile' or type(value['version']) is not int or value['version'] != 1
            or not isinstance(value['sessions'], list) or not 1 <= len(value['sessions']) <= MAX_RECORDS):
        raise ValueError(text('invalid'))
    now = datetime.now(timezone.utc)
    records = [_record(entry, index + 1, now) for index, entry in enumerate(value['sessions'])]
    if len({record.id for record in records}) != len(records):
        raise ValueError(text('conflict'))
    return records


def load_mobile(path):
    with Path(path).open('rb') as stream:
        return parse_mobile(stream.read(MAX_BYTES + 1))


def _validated(records):
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError(text('invalid'))
    result, seen = [], set()
    now = datetime.now(timezone.utc)
    for index, record in enumerate(records):
        if not isinstance(record, MobileSession):
            raise ValueError(text('invalid'))
        try:
            data = dict(id=record.id, game=record.game, game_id=record.game_id, seconds=record.seconds,
                        started_at=record.started_at.isoformat(), ended_at=record.ended_at.isoformat())
        except (AttributeError, TypeError):
            raise ValueError(text('invalid')) from None
        checked = _record(data, index + 1, now)
        if checked.id in seen:
            raise ValueError(text('conflict'))
        seen.add(checked.id)
        destination = record.destination_id
        if destination is not None and (not isinstance(destination, str) or len(destination) > 128):
            raise ValueError(text('mapping'))
        result.append(replace(checked, destination_id=destination))
    return result


def suggested_destination(controller, record):
    """IDs exportados não podem ligar silenciosamente um nome a outro jogo."""
    wanted = chave_nome(record.game)
    identified = controller.repo.jogo_por_id(record.game_id) if record.game_id else None
    if identified is not None and chave_nome(identified.nome) == wanted:
        return identified.id
    matches = [game.id for game in controller.repo.jogos if chave_nome(game.nome) == wanted]
    if len(matches) > 1:
        raise ValueError(text('ambiguous'))
    return matches[0] if matches else None


def import_mobile(controller, records):
    """Importa somente a seleção revisada, com backup e rollback próprios."""
    records = _validated(records)
    existing = {session.sessao_id for session in controller.repo.sessoes}
    selected = [record for record in records if record.session_id not in existing]
    skipped = len(records) - len(selected)
    if not selected:
        return {'imported': 0, 'skipped': skipped, 'backup': None}
    for record in selected:
        if record.destination_id:
            if controller.repo.jogo_por_id(record.destination_id) is None:
                raise ValueError(text('missing'))
        elif record.destination_id == '':
            suggested_destination(controller, record)
        else:
            controller.repo.validar_nome(record.game)
    backup = create_full(controller.folder)
    read_full(backup)  # Só inicia a transação depois de conferir os bytes gravados.
    with controller.transaction():
        for record in selected:
            if any(session.sessao_id == record.session_id for session in controller.repo.sessoes):
                raise ValueError(text('conflict'))
            if record.destination_id:
                game = controller.repo.jogo_por_id(record.destination_id)
                if game is None:
                    raise ValueError(text('missing'))
            else:
                # Reavalia após cada criação: duas partidas de um jogo novo
                # devem criar um único jogo e preservar as duas sessões.
                destination = suggested_destination(controller, record)
                if record.destination_id is None and destination is not None:
                    # Uma criação anterior deste mesmo lote pode ter usado o nome.
                    game = controller.repo.jogo_por_id(destination)
                else:
                    game = controller.repo.jogo_por_id(destination) if destination else controller.add_game(record.game)
            start = record.started_at.astimezone().replace(tzinfo=None)
            end = record.ended_at.astimezone().replace(tzinfo=None)
            session = Sessao.nova(game.id, game.nome, record.seconds, start, end)
            session.sessao_id = record.session_id
            controller.repo.sessoes.append(session)
        controller.repo._salvar_sessoes()
        controller.save_pending()
    return {'imported': len(selected), 'skipped': skipped, 'backup': str(backup)}


def export_library(controller, theme='dark', language='pt'):
    payload = {'format': 'HorasJogadas-Library', 'version': 1,
               'games': [{'id': game.id, 'name': game.nome} for game in controller.repo.jogos],
               'theme': theme if theme in ('dark', 'original', 'violet', 'light') else 'dark',
               'language': 'en' if language == 'en' else 'pt'}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')


class ReviewDialog(QDialog):
    def __init__(self, window, records_or_bytes):
        super().__init__(window)
        self.window = window
        self.records = parse_mobile(records_or_bytes) if isinstance(records_or_bytes, bytes) else _validated(records_or_bytes)
        self.result_counts = None
        self.setWindowTitle(text('title')); self.resize(940, 620); self.setMinimumSize(760, 480)
        box = QVBoxLayout(self); box.setContentsMargins(24, 22, 24, 22); box.setSpacing(16)
        box.addWidget(label(text('title'), 'gameName')); box.addWidget(label(text('intro'), 'muted', True))
        self.toggle_button = button(text('toggle'), self.toggle_all)
        box.addWidget(row(self.toggle_button, None))
        self.grid = table([text(key) for key in ('game', 'start', 'duration', 'destination', 'state')])
        self.grid.setObjectName('phoneImportTable')
        self.grid.setStyleSheet('QTableWidget#phoneImportTable::item { padding: 0px 10px; }')
        self.grid.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.grid.setRowCount(len(self.records))
        self.destinations = []
        self.duplicates = {session.sessao_id for session in window.c.repo.sessoes}
        for index, record in enumerate(self.records):
            duplicate = record.session_id in self.duplicates
            game_item = QTableWidgetItem(record.game)
            game_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | (Qt.NoItemFlags if duplicate else Qt.ItemIsUserCheckable))
            game_item.setCheckState(Qt.Unchecked if duplicate else Qt.Checked)
            self.grid.setItem(index, 0, game_item)
            for column, value in ((1, record.started_at.astimezone().strftime('%d/%m/%Y %H:%M')),
                                  (2, formatar_hhmmss(record.seconds)), (4, text('duplicate') if duplicate else text('ready'))):
                self.grid.setItem(index, column, QTableWidgetItem(value))
            combo = QComboBox(); combo.setAccessibleName(text('destination') + ': ' + record.game)
            combo.addItem(text('choose'), '')
            combo.addItem(text('new'), None)
            for game in sorted(window.c.repo.jogos, key=lambda game: chave_nome(game.nome)):
                combo.addItem(game.nome, game.id)
            try:
                destination = suggested_destination(window.c, record)
                combo.setCurrentIndex(combo.findData(destination))
            except ValueError:
                combo.setCurrentIndex(0)
            combo.setEnabled(not duplicate)
            host = QWidget(); layout = QHBoxLayout(host); layout.setContentsMargins(0, 6, 0, 6); layout.addWidget(combo)
            self.grid.setCellWidget(index, 3, host); self.grid.setRowHeight(index, max(54, combo.sizeHint().height() + 12))
            self.destinations.append(combo)
            combo.currentIndexChanged.connect(self.update_selection)
        box.addWidget(self.grid, 1)
        self.summary = label('', 'muted', True); box.addWidget(self.summary)
        box.addWidget(label(text('preserved'), 'muted', True))
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Save).setText(text('import')); self.buttons.button(QDialogButtonBox.Save).setObjectName('primary')
        self.buttons.button(QDialogButtonBox.Cancel).setText(text('cancel'))
        self.buttons.accepted.connect(self.submit); self.buttons.rejected.connect(self.reject)
        box.addWidget(self.buttons)
        self.grid.itemChanged.connect(self.update_selection)
        self.update_selection()

    def selected(self):
        return [replace(record, destination_id=self.destinations[index].currentData())
                for index, record in enumerate(self.records)
                if record.session_id not in self.duplicates and self.grid.item(index, 0).checkState() == Qt.Checked]

    def update_selection(self):
        if not hasattr(self, 'buttons'):
            return
        selected = self.selected()
        self.summary.setText(text('selected').format(selected=len(selected), duplicates=sum(record.session_id in self.duplicates for record in self.records)))
        self.buttons.button(QDialogButtonBox.Save).setEnabled(bool(selected) and all(record.destination_id != '' for record in selected))

    def toggle_all(self):
        checked = bool(self.selected())
        for index, record in enumerate(self.records):
            if record.session_id not in self.duplicates:
                self.grid.item(index, 0).setCheckState(Qt.Unchecked if checked else Qt.Checked)

    def submit(self):
        try:
            records = self.selected()
            if not records or any(record.destination_id == '' for record in records):
                raise ValueError(text('mapping'))
            self.result_counts = import_mobile(self.window.c, records)
        except Exception as error:
            QMessageBox.critical(self, text('error'), str(error))
            return
        self.accept()

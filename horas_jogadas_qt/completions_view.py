"""Lista de Zerados por mês: pintura nativa Qt, sem reconstrução durante a rolagem."""
from PySide6.QtCore import Qt, QSize, QRect, QAbstractListModel, Signal, QEvent
from PySide6.QtGui import QPainter, QFont, QFontMetrics, QColor
from PySide6.QtWidgets import QListView, QStyledItemDelegate, QStyle, QComboBox, QApplication
from horas_jogadas import i18n
from horas_jogadas.zerados import MESES, MESES_EN, duracao_texto
from .texts import tr

RECORD_ROLE = Qt.UserRole + 1
MONTH_ROLE = Qt.UserRole + 2


class YearPicker(QComboBox):
    """Ano é uma escolha, não uma entrada de texto nem uma alteração acidental por roda."""
    def __init__(self, years, selected, parent=None):
        super().__init__(parent)
        self.setEditable(False)
        self.setMinimumWidth(110)
        self.setAccessibleName(tr('year'))
        for year in sorted(set(years) | {selected}, reverse=True):
            self.addItem(str(year), year)
        self.setCurrentIndex(self.findData(selected))

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class CompletionModel(QAbstractListModel):
    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.entries = []
        self.record_rows = []
        months = MESES_EN if i18n.idioma_atual() == 'en' else MESES
        for month in range(1,13):
            items = [record for record in records if record.mes == month]
            if not items:
                continue
            self.entries.append((None, months[month-1]))
            for record in items:
                self.record_rows.append(len(self.entries))
                self.entries.append((record, None))

    def rowCount(self, parent=None):
        return len(self.entries) if parent is None or not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        record, month = self.entries[index.row()]
        if role == RECORD_ROLE:
            return record
        if role == MONTH_ROLE:
            return month
        if role in (Qt.DisplayRole, Qt.ToolTipRole, Qt.AccessibleTextRole):
            return month if month else '\n'.join([record.nome, duracao_texto(record.segundos) or tr('unknown'), record.notas])
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        if self.entries[index.row()][0] is None:
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class CompletionDelegate(QStyledItemDelegate):
    actionRequested = Signal(str, str)

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.heading_font = QFont('Segoe UI',11,QFont.DemiBold)
        self.body_font = QFont('Segoe UI',10)

    def detail_lines(self, record):
        lines = [tr('duration_col') + ': ' + (duracao_texto(record.segundos) or tr('unknown'))]
        if record.platina_segundos is not None:
            lines.append(tr('platinum') + ': +' + duracao_texto(record.platina_segundos))
            lines.append(tr('total') + ': ' + duracao_texto((record.segundos or 0) + record.platina_segundos))
        if record.dia is not None:
            lines.append(f'{record.dia:02d}/{record.mes:02d}/{record.ano}')
        if record.tipo == 'experiencia':
            lines.append(tr('experience'))
        return lines

    def note_height(self, record, width):
        if not record.notas:
            return 0
        metrics = QFontMetrics(self.body_font)
        return metrics.boundingRect(QRect(0,0,max(40,width-36),100000), Qt.TextWordWrap, record.notas).height() + 8

    def sizeHint(self, option, index):
        if index.data(MONTH_ROLE):
            return QSize(300,42)
        record = index.data(RECORD_ROLE)
        width = option.rect.width() if option.rect.width()>1 else self.view.viewport().width()
        return QSize(300,76 + len(self.detail_lines(record))*21 + self.note_height(record,width))

    def buttons(self, rect):
        metrics = QFontMetrics(self.body_font)
        definitions = [('edit',tr('edit')), ('new_play',tr('new_play')), ('delete',tr('delete'))]
        widths = [max(70, metrics.horizontalAdvance(text)+22) for _,text in definitions]
        x = rect.right() - 18 - sum(widths) - 12
        result = []
        for (action,text),width in zip(definitions,widths):
            result.append((action,text,QRect(x,rect.top()+17,width,32)))
            x += width+6
        return result

    def paint(self, painter, option, index):
        painter.save(); painter.setRenderHint(QPainter.Antialiasing)
        foreground = option.palette.windowText().color()
        muted = QColor(foreground); muted.setAlpha(165)
        month = index.data(MONTH_ROLE)
        if month:
            painter.setFont(self.heading_font); painter.setPen(foreground)
            painter.drawText(option.rect.adjusted(3,8,-3,0), Qt.AlignLeft|Qt.AlignVCenter, month)
            painter.restore(); return
        record = index.data(RECORD_ROLE)
        card = option.rect.adjusted(0,5,-1,-5)
        border = QColor(foreground)
        border.setAlpha(100 if option.state & QStyle.State_Selected else 35)
        painter.setPen(border); painter.setBrush(QApplication.palette().base())
        painter.drawRoundedRect(card,10,10)
        buttons = self.buttons(option.rect)
        name_rect = QRect(card.left()+18,card.top()+12,max(20,buttons[0][2].left()-card.left()-30),32)
        name = record.nome + (' · DLC' if record.dlc else '')
        painter.setFont(self.heading_font); painter.setPen(foreground)
        painter.drawText(name_rect,Qt.AlignVCenter|Qt.AlignLeft,QFontMetrics(self.heading_font).elidedText(name,Qt.ElideRight,name_rect.width()))
        painter.setFont(self.body_font)
        for action,text,rect in buttons:
            painter.setPen(border); painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect,6,6)
            painter.setPen(foreground); painter.drawText(rect,Qt.AlignCenter,text)
        painter.setPen(muted)
        y = card.top()+52
        for line in self.detail_lines(record):
            painter.drawText(QRect(card.left()+18,y,card.width()-36,21),Qt.AlignLeft|Qt.AlignVCenter,line)
            y += 21
        if record.notas:
            painter.drawText(QRect(card.left()+18,y+5,card.width()-36,self.note_height(record,card.width())),Qt.TextWordWrap,record.notas)
        painter.restore()

    def editorEvent(self,event,model,option,index):
        record = index.data(RECORD_ROLE)
        if record is not None and event.type()==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton:
            for action,_,rect in self.buttons(option.rect):
                if rect.contains(event.position().toPoint()):
                    self.actionRequested.emit(action,record.id)
                    return True
        return super().editorEvent(event,model,option,index)


class CompletionList(QListView):
    """Seleção é feita por registro; cabeçalhos de mês nunca viram um registro editável."""
    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.records = records
        self.record_model = CompletionModel(records,self)
        self.setModel(self.record_model)
        self.delegate = CompletionDelegate(self)
        self.setItemDelegate(self.delegate)
        self.setUniformItemSizes(False)
        self.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setSpacing(0)
        self.setObjectName('completionList')
        self.setAccessibleName(tr('completed'))

    def currentRow(self):
        row = self.currentIndex().row()
        try:
            return self.record_model.record_rows.index(row)
        except ValueError:
            return -1

    def selectRow(self, row):
        if 0 <= row < len(self.record_model.record_rows):
            self.setCurrentIndex(self.record_model.index(self.record_model.record_rows[row],0))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.scheduleDelayedItemsLayout()

    def paintEvent(self,event):
        super().paintEvent(event)
        if not self.records:
            painter = QPainter(self.viewport())
            painter.setPen(self.palette().placeholderText().color())
            painter.drawText(self.viewport().rect().adjusted(20,20,-20,-20),Qt.AlignCenter|Qt.TextWordWrap,tr('no_completions'))

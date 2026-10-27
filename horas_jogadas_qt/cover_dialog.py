"""Busca em lote com confirmação dos títulos e prévia antes de importar as capas."""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QComboBox,QProgressBar,QFileDialog,QMessageBox,QAbstractItemView)
from .tasks import Task,Cancelled
from .covers import CoverStore,download,normalize_image,normalized
from .artwork_sources import search_artwork as search,COVER_SOURCES,ICON_SOURCES
from .texts import tr


class CoverDialog(QDialog):
    def __init__(self,window,key=None,kind='cover'):
        super().__init__(window)
        self.window=window;self.kind=kind;self.store=CoverStore(window.c.folder,kind)
        self.games=[g for g in window.c.repo.jogos if key is None or g.id==key]
        self.busy=False;self.pending_close=False;self.cache={};self.preview_failed=set();self.selectors=[];self.filling=False
        self.setWindowTitle(self.text('covers_manage'));self.resize(960,690);self.setMinimumSize(760,540)
        box=QVBoxLayout(self);box.setSpacing(12)
        title=QLabel(self.text('covers_intro'));title.setWordWrap(True);box.addWidget(title)
        tools=QHBoxLayout()
        self.search_all=QPushButton(self.text('covers_search_all'));self.search_all.setObjectName('primary');self.search_all.clicked.connect(self.find_all)
        select_all=QPushButton(self.text('covers_select_all'));select_all.clicked.connect(self.select_all)
        self.sources=QComboBox();self.sources.addItem(tr('artwork_all_sources'),None)
        for name in (ICON_SOURCES if kind=='icon' else COVER_SOURCES):self.sources.addItem(name,name)
        self.sources.setAccessibleName(tr('artwork_source'))
        tools.addWidget(self.search_all);tools.addWidget(select_all);tools.addStretch();tools.addWidget(self.sources);box.addLayout(tools)
        self.table=QTableWidget(len(self.games),2);self.table.setHorizontalHeaderLabels([tr('game'),self.text('covers_suggestion')])
        self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        for row,game in enumerate(self.games):
            item=QTableWidgetItem(game.nome);item.setFlags(item.flags()|Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked if self.store.path(game.id) else Qt.Checked);self.table.setItem(row,0,item)
            combo=QComboBox();combo.addItem(self.text('covers_choose_result'),None)
            combo.currentIndexChanged.connect(lambda index,r=row:self.choice_changed(r));self.table.setCellWidget(row,1,combo)
            self.selectors.append(combo)
        self.table.itemChanged.connect(self.update_count);self.table.currentCellChanged.connect(self.row_changed);box.addWidget(self.table,1)
        search_row=QHBoxLayout();self.query=QLineEdit();self.query.setPlaceholderText(self.text('covers_search_hint'))
        self.search_one=QPushButton(self.text('covers_search_one'));self.search_one.clicked.connect(self.find_one);self.query.returnPressed.connect(self.find_one)
        search_row.addWidget(self.query,1);search_row.addWidget(self.search_one);box.addLayout(search_row)
        preview_row=QHBoxLayout();self.preview=QLabel(self.text('covers_preview'));self.preview.setTextFormat(Qt.PlainText);self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedSize(108,108) if kind=='icon' else self.preview.setFixedSize(230,108);self.preview.setObjectName('coverPreview');preview_row.addWidget(self.preview)
        detail=QVBoxLayout();self.source=QLabel(self.text('covers_source'));self.source.setTextFormat(Qt.PlainText);self.source.setWordWrap(True);detail.addWidget(self.source)
        self.local=QPushButton(self.text('covers_local'));self.local.clicked.connect(self.import_local)
        self.remove=QPushButton(self.text('covers_remove'));self.remove.clicked.connect(self.remove_cover)
        buttons=QHBoxLayout();buttons.addWidget(self.local);buttons.addWidget(self.remove);buttons.addStretch();detail.addLayout(buttons)
        preview_row.addLayout(detail,1);box.addLayout(preview_row)
        self.status=QLabel(self.text('covers_ready'));self.status.setTextFormat(Qt.PlainText);self.status.setWordWrap(True);box.addWidget(self.status)
        self.progress=QProgressBar();self.progress.hide();box.addWidget(self.progress)
        bottom=QHBoxLayout();self.import_button=QPushButton();self.import_button.setObjectName('primary');self.import_button.clicked.connect(self.import_selected)
        self.close_button=QPushButton(tr('close'));self.close_button.clicked.connect(self.reject)
        bottom.addStretch();bottom.addWidget(self.import_button);bottom.addWidget(self.close_button);box.addLayout(bottom)
        self.table.selectRow(0) if self.games else None;self.update_count()

    def text(self,key):return tr(key.replace('covers_','game_icons_') if self.kind=='icon' else key)

    def fetch(self,candidate,cancel):
        return download(candidate,cancel,kind='icon') if self.kind=='icon' else download(candidate,cancel)

    def checked(self,row):return self.table.item(row,0).checkState()==Qt.Checked
    def selected(self,row):return self.selectors[row].currentData()

    def select_all(self):
        state=Qt.Unchecked if all(self.checked(r) for r in range(len(self.games))) else Qt.Checked
        for row in range(len(self.games)):self.table.item(row,0).setCheckState(state)

    def row_changed(self,row,*args):
        if row>=0:
            self.query.setText(self.games[row].nome);self.show_preview()

    def choice_changed(self,row):
        if self.filling:return
        if self.selected(row):self.table.item(row,0).setCheckState(Qt.Checked)
        self.update_count()
        if self.table.currentRow()==row:self.show_preview()

    def update_count(self,*args):
        count=sum(self.checked(row) and self.selected(row) is not None for row in range(len(self.games)))
        self.import_button.setText(self.text('covers_import').format(n=count))
        self.import_button.setEnabled(bool(count) and not self.busy)
        self.remove.setEnabled(not self.busy and self.table.currentRow()>=0 and bool(self.store.path(self.games[self.table.currentRow()].id)))

    def run(self,work,success,kind):
        if self.busy:return
        self.local.setEnabled(False)
        self.table.setEnabled(kind=='preview');self.query.setEnabled(kind=='preview')
        self.busy=True;self.operation=kind;self.sources.setEnabled(False);self.search_all.setEnabled(False);self.search_one.setEnabled(False);self.update_count()
        self.progress.setRange(0,0);self.progress.show();self.close_button.setText(tr('cancel'))
        self.task=Task(self,work);self.task.succeeded.connect(success);self.task.failed.connect(self.failed)
        self.task.progress.connect(self.show_progress);self.task.settled.connect(self.settled);self.task.start()

    def show_progress(self,done,total):self.progress.setRange(0,max(1,total));self.progress.setValue(done)

    def settled(self):
        self.local.setEnabled(True);self.table.setEnabled(True);self.query.setEnabled(True)
        self.busy=False;self.sources.setEnabled(True);self.search_all.setEnabled(True);self.search_one.setEnabled(True);self.close_button.setText(tr('close'));self.progress.hide();self.update_count()
        if self.pending_close:super().reject()
        else:QTimer.singleShot(0,self.show_preview)

    def failed(self,error):
        if self.operation=='preview':
            self.preview_failed.add(self.preview_id)
            self.preview.setText(self.text('covers_preview_failed'))
        elif not isinstance(error,Cancelled):self.status.setText(self.text('covers_error')+' '+str(error))

    def find_all(self):
        self.find([(row,self.games[row].nome) for row in range(len(self.games)) if self.checked(row)])

    def find_one(self):
        row=self.table.currentRow()
        if row>=0 and self.query.text().strip():self.find([(row,self.query.text().strip())])

    def find(self,rows):
        if not rows or self.busy:return
        self.status.setText(self.text('covers_searching'));self.preview_failed.clear()
        source=self.sources.currentData()
        def work(cancel,progress):
            found=[]
            for n,(row,query) in enumerate(rows):
                if cancel.is_set():raise Cancelled()
                try:
                    results=search(query,source=source,kind=self.kind,cancel=cancel)
                    found.append((row,results,'\n'.join(getattr(results,'warnings',())) or None))
                except Cancelled:raise
                except Exception as error:found.append((row,[],str(error)))
                progress(n+1,len(rows))
                if cancel.wait(.2):raise Cancelled()
            return found
        self.run(work,self.found,'search')

    def found(self,results):
        errors=[];self.filling=True
        try:
            for row,candidates,error in results:
                combo=self.selectors[row];combo.clear();combo.addItem(self.text('covers_choose_result'),None)
                for candidate in candidates:
                    duplicated=sum(item.source==candidate.source and item.name==candidate.name for item in candidates)>1
                    combo.addItem(candidate.name+' · '+candidate.source+(' #'+str(candidate.app_id) if duplicated else ''),candidate)
                exact=bool(candidates and candidates[0].score>=.93 and not any(
                    item.score>=candidates[0].score-.03 and (normalized(item.name)!=normalized(candidates[0].name)
                        or item.source==candidates[0].source and item.app_id!=candidates[0].app_id)
                    for item in candidates[1:]))
                combo.setCurrentIndex(1 if exact else 0)
                self.table.item(row,0).setCheckState(Qt.Checked if exact else Qt.Unchecked)
                if error:errors.append(self.games[row].nome+': '+error)
        finally:self.filling=False
        self.status.setText(self.text('covers_review')+ ('\n'+self.text('covers_search_errors').format(n=len(errors)) if errors else ''))
        self.status.setToolTip('\n'.join(errors))

    def show_preview(self):
        row=self.table.currentRow()
        if row<0 or self.busy:return
        candidate=self.selected(row);path=self.store.path(self.games[row].id)
        if candidate:
            self.source.setText(candidate.source+' · '+candidate.name+'\n'+candidate.page)
            if (path and self.store.entries.get(self.games[row].id,{}).get('app_id')==candidate.app_id
                    and self.store.entries.get(self.games[row].id,{}).get('source')==candidate.source):
                self.paint_preview(path.read_bytes());self.update_count();return
            if candidate.cache_key in self.cache:self.paint_preview(self.cache[candidate.cache_key]);return
            if candidate.cache_key in self.preview_failed:
                self.preview.clear();self.preview.setText(self.text('covers_preview_failed'));return
            self.preview.clear();self.preview.setText(self.text('covers_loading'));self.preview_id=candidate.cache_key
            def loaded(data):
                self.cache[candidate.cache_key]=data
                current=self.table.currentRow()
                if current>=0 and self.selected(current)==candidate:self.paint_preview(data)
            self.run(lambda cancel,progress:self.fetch(candidate,cancel),loaded,'preview')
        elif path:
            self.paint_preview(path.read_bytes());self.source.setText(self.text('covers_saved'))
        else:
            self.preview.clear();self.preview.setText(self.text('covers_preview'));self.source.setText(self.text('covers_source'))
        self.update_count()

    def paint_preview(self,data):
        pixmap=QPixmap();pixmap.loadFromData(data)
        self.preview.setPixmap(pixmap.scaled(self.preview.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def import_selected(self):
        rows=[(self.games[r],self.selected(r)) for r in range(len(self.games)) if self.checked(r) and self.selected(r)]
        if not rows or self.busy:return
        self.status.setText(self.text('covers_importing'))
        cached=dict(self.cache)
        def work(cancel,progress):
            records=[];errors=[]
            for n,(game,candidate) in enumerate(rows):
                if cancel.is_set():raise Cancelled()
                try:
                    image=cached.get(candidate.cache_key) or self.fetch(candidate,cancel)
                    records.append((game.id,image,{'source':candidate.source,'app_id':candidate.app_id,'title':candidate.name,'url':candidate.page}))
                except Cancelled:raise
                except Exception as error:errors.append(game.nome+': '+str(error))
                progress(n+1,len(rows))
                if cancel.wait(.15):raise Cancelled()
            return records,errors
        self.run(work,self.imported,'import')

    def imported(self,result):
        records,errors=result
        try:
            self.store.save_many(records);self.window.refresh()
            self.status.setText(self.text('covers_done').format(n=len(records))+ ('\n'+self.text('covers_import_errors').format(n=len(errors)) if errors else ''))
            self.status.setToolTip('\n'.join(errors))
        except Exception as error:self.status.setText(self.text('covers_error')+' '+str(error))

    def import_local(self):
        row=self.table.currentRow()
        if row<0 or self.busy:return
        path,_=QFileDialog.getOpenFileName(self,self.text('covers_local'),'','Images (*.jpg *.jpeg *.png *.webp *.bmp)')
        if not path:return
        try:
            source=Path(path)
            if source.stat().st_size>10*1024*1024:raise ValueError(self.text('covers_image_large'))
            data=normalize_image(source.read_bytes(),self.kind);self.store.save_many([(self.games[row].id,data,{'source':'local'})])
            self.window.refresh();self.paint_preview(data);self.status.setText(self.text('covers_done').format(n=1));self.update_count()
        except Exception as error:QMessageBox.warning(self,tr('error'),str(error))

    def remove_cover(self):
        row=self.table.currentRow()
        if row<0 or self.busy:return
        try:
            self.store.remove(self.games[row].id);self.selectors[row].setCurrentIndex(0)
            self.window.refresh();self.show_preview();self.update_count()
        except Exception as error:QMessageBox.warning(self,tr('error'),str(error))

    def reject(self):
        if self.busy:
            self.pending_close=True;self.task.cancel.set();self.status.setText(self.text('covers_cancelling'))
        else:super().reject()

    def closeEvent(self,event):
        if self.busy:self.reject();event.ignore()
        else:event.accept()

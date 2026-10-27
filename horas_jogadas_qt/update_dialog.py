"""Fluxo de atualização: verificar, baixar, conferir, fazer backup e instalar."""
import shutil
import sys
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QPlainTextEdit,QProgressBar,QMessageBox
from .tasks import Task,Cancelled
from .texts import tr
from .release import VERSION
from . import updates


class UpdateDialog(QDialog):
    def __init__(self,window,release=None):
        super().__init__(window)
        self.window=window; self.release=release; self.package=None; self.staged=None
        self.busy=False; self.pending_close=False; self.work_dir=None
        self.handed_off=False
        self.setWindowTitle(tr('update_title')); self.resize(560,440)
        box=QVBoxLayout(self); box.setSpacing(14)
        self.status=QLabel(tr('update_current').format(version=VERSION)); self.status.setWordWrap(True); box.addWidget(self.status)
        self.notes=QPlainTextEdit(); self.notes.setReadOnly(True); box.addWidget(self.notes)
        self.progress=QProgressBar(); self.progress.hide(); box.addWidget(self.progress)
        help_text=QLabel(tr('update_help'));help_text.setWordWrap(True);box.addWidget(help_text)
        actions=QHBoxLayout(); self.action=QPushButton(); self.action.setObjectName('primary')
        self.cancel_button=QPushButton(tr('close'));self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.action);actions.addWidget(self.cancel_button);box.addLayout(actions)
        self.action.clicked.connect(self.next_step)
        if release: self.show_release(release)
        else:
            self.action.setText(tr('update_check'))
            self.notes.setPlainText(tr('update_help'))

    def run(self,work,success):
        self.busy=True;self.action.setEnabled(False);self.cancel_button.setText(tr('cancel'))
        self.progress.setRange(0,0);self.progress.show()
        self.task=Task(self,work);self.task.succeeded.connect(success);self.task.failed.connect(self.failed)
        self.task.progress.connect(self.show_progress);self.task.settled.connect(self.settled);self.task.start()

    def show_progress(self,done,total):
        self.progress.setRange(0,100);self.progress.setValue(int(done*100/total) if total else 0)

    def settled(self):
        self.busy=False;self.action.setEnabled(True);self.cancel_button.setText(tr('close'))
        self.progress.hide()
        if self.pending_close:
            self.cleanup(); super().reject()

    def failed(self,error):
        if not isinstance(error,Cancelled):
            self.status.setText(tr('update_error')); self.notes.setPlainText(str(error))
        self.action.setText(tr('update_check') if not self.release else tr('update_download'))

    def show_release(self,release):
        self.release=release
        if release is None:
            self.status.setText(tr('update_latest').format(version=VERSION)); self.action.setText(tr('update_check'))
            self.notes.setPlainText(tr('update_help')); return
        self.status.setText(tr('update_available').format(version=release.version))
        self.notes.setPlainText(release.notes)
        self.action.setText(tr('update_download'))

    def next_step(self):
        if self.package:
            if QMessageBox.question(self,tr('update_title'),tr('update_confirm'),QMessageBox.Yes|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Yes: return
            if not self.window.resolve_pending(): return
            try:
                from .backup import create_full
                self.window.c.save_pending(); create_full(self.window.c.folder)
                updates.launch_update(self.package,self.staged)
                self.handed_off=True
                self.window.closing_allowed=True
                self.accept(); self.window.close()
            except Exception as error: QMessageBox.warning(self,tr('error'),str(error))
        elif self.release:
            if not getattr(sys,'frozen',False):
                QMessageBox.information(self,tr('update_title'),tr('update_source'));return
            root=updates.cache_directory();root.mkdir(parents=True,exist_ok=True)
            self.work_dir=Path(tempfile.mkdtemp(prefix='v'+self.release.version+'-',dir=root))
            self.status.setText(tr('update_downloading'))
            def work(cancel,progress):
                package=updates.download(self.release,self.work_dir,cancel,progress)
                staged=updates.stage_linux(package,Path(sys.executable).resolve().parent,self.release.version) if sys.platform.startswith('linux') else None
                return package,staged
            self.run(work,self.downloaded)
        else:
            self.status.setText(tr('update_checking'))
            self.run(lambda cancel,progress:updates.check_release(),self.show_release)

    def downloaded(self,value):
        self.package,self.staged=value
        self.status.setText(tr('update_ready'));self.action.setText(tr('update_install'))

    def reject(self):
        if self.busy:
            self.pending_close=True;self.task.cancel.set();self.cancel_button.setEnabled(False)
        else:
            self.cleanup(); super().reject()

    def cleanup(self):
        if self.handed_off:return
        if self.staged and self.staged.parent.name.startswith('.horasjogadas-update-'):
            shutil.rmtree(self.staged.parent,ignore_errors=True)
        if self.work_dir: shutil.rmtree(self.work_dir,ignore_errors=True)

    def closeEvent(self,event):
        if self.busy:
            self.reject();event.ignore()
        else:
            self.cleanup(); event.accept()

"""Trabalhos de rede fora da thread de widgets, com cancelamento cooperativo."""
from threading import Event
from PySide6.QtCore import QObject,QThread,Signal,Slot,Qt


class Cancelled(Exception):
    pass


class Worker(QObject):
    result=Signal(object,object)
    progress=Signal(int,int)
    def __init__(self,work,cancel):
        super().__init__(); self.work=work; self.cancel=cancel
    @Slot()
    def run(self):
        try: result,error=self.work(self.cancel,self.progress.emit),None
        except Exception as exc: result,error=None,exc
        self.result.emit(result,error)


class Task(QObject):
    succeeded=Signal(object)
    failed=Signal(object)
    progress=Signal(int,int)
    settled=Signal()
    def __init__(self,parent,work):
        super().__init__(parent)
        self.cancel=Event(); self.thread=QThread(self)
        self.worker=Worker(work,self.cancel); self.worker.moveToThread(self.thread)
        self.worker.result.connect(self.thread.quit,Qt.DirectConnection)
        self.worker.result.connect(self.finish)
        self.worker.progress.connect(self.progress)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.started.connect(self.worker.run)
    def start(self): self.thread.start()
    @Slot(object,object)
    def finish(self,value,error):
        self.thread.wait()
        if error is None: self.succeeded.emit(value)
        else: self.failed.emit(error)
        self.settled.emit()

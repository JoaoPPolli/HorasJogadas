"""Detecção opcional e local; só encerra contadores iniciados por este serviço."""
import os
import sys
from functools import lru_cache
from pathlib import Path,PureWindowsPath
from PySide6.QtCore import QObject,QTimer
from PySide6.QtWidgets import QApplication
from . import preferences
from .tasks import Task
from .texts import tr


def basename(value):return PureWindowsPath(str(value).replace('/','\\')).name.casefold()
@lru_cache(maxsize=4096)
def path_key(value):return os.path.normcase(os.path.realpath(value))


def profiles(folder):
    values=preferences.read(folder).get('detection_profiles',{})
    if not isinstance(values,dict):return {}
    return {key:value for key,value in values.items() if isinstance(key,str) and isinstance(value,dict)
            and type(value.get('enabled')) is bool and isinstance(value.get('executable'),str)
            and 0<len(value['executable'])<=4096 and value.get('mode') in ('path','name')}


def save_profile(window,key,enabled,executable,mode):
    if key not in window.c.timers or type(enabled) is not bool or mode not in ('path','name'):raise ValueError(tr('detect_invalid'))
    if not isinstance(executable,str) or any(c in executable for c in ('\x00','\n','\r')) or len(executable)>4096:raise ValueError(tr('detect_invalid'))
    executable=executable.strip()
    if enabled and (not executable or mode=='path' and not Path(executable).is_absolute()):raise ValueError(tr('detect_invalid'))
    if mode=='path' and executable:executable=str(Path(executable).resolve())
    if enabled and (path_key(executable)==path_key(sys.executable) if mode=='path' else basename(executable)==basename(sys.executable)):
        raise ValueError(tr('detect_invalid'))
    values=profiles(window.c.folder)
    for other,value in values.items():
        if enabled and other!=key and value['enabled'] and mode==value['mode'] and (path_key(executable)==path_key(value['executable']) if mode=='path' else basename(executable)==basename(value['executable'])):
            raise ValueError(tr('detect_duplicate'))
    values[key]=dict(enabled=enabled,executable=executable,mode=mode)
    changes={'detection_profiles':values}
    if enabled:changes['detection_enabled']=True
    preferences.save(window.c.folder,**changes)


def scan_processes(values,tracked,cancel,iterator=None):
    import psutil
    if iterator is None:
        iterator=psutil.process_iter
        iterator.cache_clear()  # O mesmo PID pode trocar de executável (exec no Linux).
    found={key:set() for key in values};unknown=set();conflicts=set()
    attributes=['pid','name','exe','create_time']
    try:
        processes=iterator(attrs=attributes,ad_value=None)
        for process in processes:
            if cancel.is_set():return None
            try:info=process.info;pid=info.get('pid');name=info.get('name') or '';exe=info.get('exe') or ''
            except (psutil.AccessDenied,psutil.NoSuchProcess):continue
            matches=[]
            command=None
            for key,profile in values.items():
                target=profile['executable']
                if profile['mode']=='path':
                    match=bool(exe) and path_key(exe)==path_key(target)
                    if not exe and (pid in tracked.get(key,set()) or basename(name)==basename(target)):unknown.add(key)
                else:
                    match=basename(name)==basename(target) or bool(exe) and basename(exe)==basename(target)
                    # Wine/Proton: só compara tokens .exe completos, sem busca parcial.
                    if not match and any(word in basename(exe or name) for word in ('wine','proton')):
                        if command is None:
                            try:command=process.cmdline()
                            except (psutil.AccessDenied,psutil.NoSuchProcess):command=[];unknown.add(key)
                        executables=[token for token in command if isinstance(token,str) and basename(token).endswith('.exe')]
                        match=bool(executables) and basename(executables[0])==basename(target)
                if match:matches.append(key)
            if len(matches)>1:conflicts.update(matches);continue
            for key in matches:found[key].add((pid,info.get('create_time')))
    except (psutil.Error,OSError):return None
    for key in conflicts:found[key].clear();unknown.add(key)
    return dict(found=found,unknown=unknown,conflicts=conflicts)


def fingerprint(timer):return (timer.rodando,timer.inicio,timer.retomado,timer.mono,timer.pausa)


class GameDetection(QObject):
    def __init__(self,window):
        super().__init__(window);self.w=window;self.task=None;self.present=set();self.owned={};self.missing={};self.signature=None;self.failed=False;self.conflicts=set()
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.poll)
        if window.mode=='release':self.timer.start()

    def configuration(self):
        if not preferences.read(self.w.c.folder).get('detection_enabled',False):return {}
        return {k:v for k,v in profiles(self.w.c.folder).items() if v['enabled'] and k in self.w.c.timers
                and (v['mode']=='name' or Path(v['executable']).is_absolute())
                and not (path_key(v['executable'])==path_key(sys.executable) if v['mode']=='path' else basename(v['executable'])==basename(sys.executable))}

    def reconcile(self,values):
        signature=(id(self.w.c),tuple(sorted((k,v['executable'],v['mode']) for k,v in values.items())))
        if signature!=self.signature:
            old=dict((key,(path,mode)) for key,path,mode in self.signature[1]) if self.signature and self.signature[0]==id(self.w.c) else {}
            current={key:(value['executable'],value['mode']) for key,value in values.items()}
            for key in set(self.present)|set(self.owned):
                if old.get(key)!=current.get(key) or key not in current:
                    self.present.discard(key);self.owned.pop(key,None);self.missing.pop(key,None)
            self.signature=signature
        return signature

    def poll(self):
        if self.task or self.failed or self.w.closing_allowed or self.w.pending_recovery or QApplication.activeModalWidget() is not None:return
        values=self.configuration()
        signature=self.reconcile(values)
        if not values:return
        tracked={k:{pid for pid,_ in owner['pids']} for k,owner in self.owned.items()}
        task=Task(self.w,lambda cancel,progress:scan_processes(values,tracked,cancel));self.task=task
        def success(sample):
            if not task.cancel.is_set() and signature==self.signature and values==self.configuration() and id(self.w.c)==signature[0]:self.apply(sample)
        def settled():self.task=None;task.deleteLater()
        task.succeeded.connect(success);task.settled.connect(settled);task.start()

    def apply(self,sample):
        if sample is None or self.w.closing_allowed or self.w.pending_recovery or QApplication.activeModalWidget() is not None:return
        if sample.get('conflicts') and sample['conflicts']!=self.conflicts:self.w.notify(tr('detect_conflict'))
        self.conflicts=set(sample.get('conflicts',set()))
        found=sample['found'];unknown=sample['unknown'];active={k for k,pids in found.items() if pids}
        for key,owner in list(self.owned.items()):
            timer=self.w.c.timers.get(key)
            if timer is not owner['timer'] or fingerprint(timer)!=owner['fingerprint']:
                self.owned.pop(key,None)  # Intervenção manual vale até o processo fechar.
        starts=[k for k in active-self.present if k in self.w.c.timers and not self.w.c.timers[k].pending]
        stops=[]
        for key in self.present-active-unknown:
            self.missing[key]=self.missing.get(key,0)+1
            if self.missing[key]>=2 and key in self.owned:stops.append(key)
        for key in active|unknown:self.missing.pop(key,None)
        if starts or stops:
            def change():
                for key in starts:self.w.c.timers[key].start()
                for key in stops:self.w.c.finish(key)
                self.w.c.save_pending()
            if not self.w.perform(change,refresh=False):
                for key,owner in self.owned.items():
                    timer=self.w.c.timers.get(key)
                    if timer and fingerprint(timer)==owner['fingerprint']:owner['timer']=timer
                self.failed=True;self.w.notify(tr('detect_failed'));return
            for key in starts:
                timer=self.w.c.timers[key];self.owned[key]=dict(timer=timer,fingerprint=fingerprint(timer),pids=found[key])
            for key in stops:self.owned.pop(key,None)
            self.w.phone_control.refresh_desktop()
            self.w.notify(tr('detect_saved') if stops else tr('detect_started'))
        for key in active:
            if key in self.owned:self.owned[key]['pids']=found[key]
        self.present|=active
        for key in list(self.present):
            if key not in active|unknown and self.missing.get(key,0)>=2:self.present.discard(key);self.missing.pop(key,None)

    def reset(self):
        self.failed=False

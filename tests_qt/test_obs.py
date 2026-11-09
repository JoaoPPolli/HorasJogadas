"""Leitura do timer real, isolamento HTTP e persistência do widget OBS."""
import json
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget
from horas_jogadas_qt.controller import Controller
from horas_jogadas_qt.obs import ObsControl, DEFAULTS, read_options
from horas_jogadas_qt.preview import inventory
from horas_jogadas_qt.backup import create_full, read_full
from horas_jogadas_qt import preferences
from .test_data import Clock
APP=QApplication.instance() or QApplication([])

class ObsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.w=QWidget();self.w.c=Controller(self.folder)
        self.w.mode='review';self.w.pending_recovery=False;self.w.notify=lambda message:None
        self.obs=ObsControl(self.w);self.addCleanup(self.w.deleteLater);self.addCleanup(self.obs.server.stop)
        self.game=self.w.c.add_game('My game');self.clock=Clock();self.timer=self.w.c.timers[self.game.id];self.timer.clock=self.clock
    def save(self,**options):self.obs.save(dict(DEFAULTS,**options))
    def request(self,path,token='',method='GET',origin=None):
        server=self.obs.server;port=server.server.serverPort()
        headers=[f'{method} {path} HTTP/1.1',f'Host: 127.0.0.1:{port}','Connection: close']
        if token:headers.append('Authorization: Bearer '+token)
        if origin:headers.append('Origin: '+origin)
        if method=='POST':headers+=['Content-Type: application/json','Content-Length: 2']
        with socket.create_connection(('127.0.0.1',port),timeout=2) as c:
            c.sendall(('\r\n'.join(headers)+'\r\n\r\n').encode()+(b'{}' if method=='POST' else b''));c.setblocking(False)
            result=b'';end=time.monotonic()+3
            while time.monotonic()<end:
                APP.processEvents()
                try:data=c.recv(65536)
                except BlockingIOError:time.sleep(.001);continue
                if not data:break
                result+=data
        head,_,body=result.partition(b'\r\n\r\n');return int(head.split()[1]),body
    def test_timer_pause_resume_finish_total_and_auto_switch(self):
        self.save(scope='total',show_name=True)
        self.timer.start();self.clock.advance(15)
        self.assertEqual(self.obs.snapshot()['seconds'],15)
        self.timer.pause();self.clock.advance(80)
        self.assertEqual(self.obs.snapshot()['seconds'],15)
        self.assertTrue(self.obs.snapshot()['paused'])
        self.timer.start();self.clock.advance(5);self.w.c.finish(self.game.id)
        self.assertEqual(self.obs.snapshot()['seconds'],20)
        self.assertEqual(self.obs.snapshot()['name'],'My game')
        other=self.w.c.add_game('Second');self.w.c.timers[other.id].start()
        self.assertEqual(self.obs.snapshot()['name'],'Second')
        self.save(game=self.game.id,scope='total',show_name=True)
        self.assertEqual(self.obs.snapshot()['seconds'],20)
    def test_read_only_loopback_routes_and_no_history_exposure(self):
        self.save(enabled=True)
        self.assertEqual(self.obs.server.server.serverAddress().toString(),'127.0.0.1')
        for path in ('/','/obs.css','/obs.js'):self.assertEqual(self.request(path)[0],200)
        self.assertEqual(self.request('/state')[0],401)
        code,body=self.request('/state',self.obs.key);self.assertEqual(code,200)
        self.assertNotIn('games',json.loads(body));self.assertNotIn('sessions',json.loads(body))
        self.assertEqual(self.request('/api/state',self.obs.key)[0],404)
        self.assertEqual(self.request('/state',self.obs.key,origin='http://untrusted.test')[0],403)
        self.assertEqual(self.request('/api/command',self.obs.key,'POST',self.obs.server.url)[0],405)
        self.assertFalse(self.timer.pending)
    def test_stable_url_and_private_key_excluded_from_backups(self):
        self.save(enabled=True);url=self.obs.url
        self.obs.server.stop();self.obs.enable();self.assertEqual(self.obs.url,url)
        self.assertNotIn('.obs-key',inventory(self.folder))
        self.assertNotIn('.obs-key',read_full(create_full(self.folder)))
        self.save(enabled=False);self.assertFalse(self.obs.server.running)
    def test_defaults_review_does_not_auto_start_and_invalid_color_keeps_data(self):
        self.assertFalse(read_options(self.folder)['enabled']);self.obs.auto_start();self.assertFalse(self.obs.server.running)
        preferences.save(self.folder,obs=dict(DEFAULTS,enabled=True))
        self.obs.auto_start();self.assertFalse(self.obs.server.running)
        self.w.pending_recovery=True;self.assertFalse(self.obs.snapshot()['visible'])
        with self.assertRaises(ValueError):self.save(color='url(untrusted)')
        self.assertFalse(self.obs.server.running)
    def test_save_failure_stops_new_listener(self):
        with patch('horas_jogadas_qt.obs.preferences.save',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.save(enabled=True)
        self.assertFalse(self.obs.server.running)

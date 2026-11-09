"""Confere os arquivos e a leitura HTTP do widget no executável empacotado."""
import json
import socket
import time
from .obs import DEFAULTS


def run_obs_self_test(window, app):
    if window.mode != 'review':raise RuntimeError('OBS self-test requires an isolated profile')
    obs=window.obs_control
    if obs.server.running:raise RuntimeError('OBS should start disabled')
    obs.save(dict(DEFAULTS,enabled=True))
    try:
        def request(path, authorized=False):
            headers=[f'GET {path} HTTP/1.1',f'Host: 127.0.0.1:{obs.server.server.serverPort()}','Connection: close']
            if authorized:headers.append('Authorization: Bearer '+obs.key)
            data=bytearray()
            with socket.create_connection(('127.0.0.1',obs.server.server.serverPort()),timeout=3) as c:
                c.sendall(('\r\n'.join(headers)+'\r\n\r\n').encode());c.setblocking(False)
                end=time.monotonic()+5
                while time.monotonic()<end:
                    app.processEvents()
                    try:chunk=c.recv(65536)
                    except BlockingIOError:time.sleep(.001);continue
                    if not chunk:break
                    data.extend(chunk)
                else:raise RuntimeError('OBS HTTP timeout')
            head,_,body=bytes(data).partition(b'\r\n\r\n')
            return int(head.split()[1]),body
        for path in ('/','/obs.js','/obs.css'):
            status,body=request(path)
            if status!=200 or not body:raise RuntimeError('OBS asset missing: '+path)
        if request('/state')[0]!=401:raise RuntimeError('OBS exposed private state')
        status,body=request('/state',True)
        if status!=200 or json.loads(body)!=obs.snapshot():raise RuntimeError('OBS state mismatch')
        if request('/api/state',True)[0]!=404:raise RuntimeError('OBS exposed phone routes')
        return dict(obs_assets=True,obs_http=True,obs_read_only=True)
    finally:obs.save(dict(DEFAULTS,enabled=False));app.processEvents()

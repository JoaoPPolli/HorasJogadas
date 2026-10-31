"""Aparelhos lembrados: credenciais opacas, somente hashes e escrita atômica."""
import hashlib
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path

FILE_NAME = '.phone-devices.json'
DEVICE_SECONDS = 30 * 24 * 3600
MAX_DEVICES = 6
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}')
HEX_ID = re.compile(r'[a-f0-9]{32}')
DIGEST = re.compile(r'[a-f0-9]{64}')


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Arquivo de aparelhos inválido')
        value[key] = item
    return value


class TrustStore:
    def __init__(self, folder):
        self.path = Path(folder) / FILE_NAME

    def _read(self, strict=False):
        try:
            if not self.path.exists():
                return []
            if self.path.is_symlink() or self.path.stat().st_size > 65536:
                raise ValueError('Arquivo de aparelhos inválido')
            value = json.loads(self.path.read_text(encoding='utf-8'), object_pairs_hook=_unique)
            if (not isinstance(value, dict) or set(value) != {'version', 'devices'}
                    or type(value['version']) is not int or value['version'] != 1
                    or not isinstance(value['devices'], list) or len(value['devices']) > MAX_DEVICES):
                raise ValueError('Arquivo de aparelhos inválido')
            devices, ids, hashes = [], set(), set()
            for item in value['devices']:
                if not isinstance(item, dict) or set(item) != {'id', 'label', 'hash', 'created_at', 'expires_at'}:
                    raise ValueError('Arquivo de aparelhos inválido')
                if (not isinstance(item['id'], str) or not HEX_ID.fullmatch(item['id'])
                        or not isinstance(item['hash'], str) or not DIGEST.fullmatch(item['hash'])
                        or item['id'] in ids or item['hash'] in hashes
                        or not isinstance(item['label'], str) or not 1 <= len(item['label']) <= 80
                        or any(not char.isprintable() for char in item['label'])
                        or type(item['created_at']) is not int or type(item['expires_at']) is not int
                        or not 0 < item['created_at'] < item['expires_at']
                        or item['expires_at'] - item['created_at'] > DEVICE_SECONDS):
                    raise ValueError('Arquivo de aparelhos inválido')
                ids.add(item['id']); hashes.add(item['hash'])
                if item['expires_at'] > time.time():
                    devices.append(item)
            return devices
        except (OSError, ValueError, UnicodeError):
            if strict:
                raise
            # Dados corrompidos não autorizam nenhum aparelho nem são apagados.
            return []

    def _write(self, devices):
        if self.path.is_symlink():
            raise ValueError('Arquivo de aparelhos inválido')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.phone-devices-', suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'devices': devices}, stream, ensure_ascii=False, indent=2)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    @staticmethod
    def _metadata(item):
        return {key: item[key] for key in ('id', 'label', 'created_at', 'expires_at')}

    def list_devices(self):
        return [self._metadata(item) for item in self._read()]

    def get(self, device_id):
        return next((self._metadata(item) for item in self._read() if item['id'] == device_id), None)

    def remember(self, label):
        devices = self._read(strict=True)
        if len(devices) >= MAX_DEVICES:
            raise ValueError('Limite de aparelhos lembrados atingido')
        label = ' '.join(label.split()) if isinstance(label, str) else ''
        label = ''.join(char for char in label if char.isprintable())[:80] or 'Celular'
        token = secrets.token_urlsafe(32)
        created = int(time.time())
        item = dict(id=secrets.token_hex(16), label=label,
                    hash=hashlib.sha256(token.encode('ascii')).hexdigest(),
                    created_at=created, expires_at=created + DEVICE_SECONDS)
        self._write(devices + [item])
        return {'remember_token': token, 'device_id': item['id']}

    def verify(self, token):
        if not isinstance(token, str) or not TOKEN.fullmatch(token):
            return None
        digest = hashlib.sha256(token.encode('ascii')).hexdigest()
        return next((self._metadata(item) for item in self._read()
                     if secrets.compare_digest(item['hash'], digest)), None)

    def revoke(self, device_id):
        devices = self._read(strict=True)
        selected = [item for item in devices if item['id'] != device_id]
        if len(selected) != len(devices):
            self._write(selected)

    def revoke_all(self):
        # É uma ação explícita; também permite descartar um arquivo corrompido.
        self._write([])

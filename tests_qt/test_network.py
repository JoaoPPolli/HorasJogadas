"""HTTPS portátil: raízes incluídas, CAs locais e rejeição real de certificados inválidos."""
import importlib.util
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch
if importlib.util.find_spec('certifi') is None:raise unittest.SkipTest('Instale requirements-qt.txt')
import certifi
from horas_jogadas_qt.network import ssl_context,urlopen


class TrustStoreTests(unittest.TestCase):
    def test_bundled_roots_work_with_missing_system_ca_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            empty=Path(temporary)/'empty';empty.mkdir()
            with patch.dict(os.environ,SSL_CERT_FILE=str(Path(temporary)/'missing.pem'),SSL_CERT_DIR=str(empty)):
                expected=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                expected.load_verify_locations(cafile=certifi.where())
                actual=ssl_context()
                self.assertTrue(set(expected.get_ca_certs(binary_form=True)).issubset(actual.get_ca_certs(binary_form=True)))
                self.assertGreater(len(expected.get_ca_certs()),50)
                self.assertEqual(actual.verify_mode,ssl.CERT_REQUIRED)
                self.assertTrue(actual.check_hostname)

    def test_updates_and_cover_requests_share_the_portable_transport(self):
        from horas_jogadas_qt import updates,covers
        self.assertIs(updates.urlopen,urlopen);self.assertIs(covers.urlopen,urlopen)


@unittest.skipUnless(shutil.which('openssl'),'OpenSSL CLI necessário para gerar certificados locais efêmeros')
class HttpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        root=cls.root
        (root/'req.cnf').write_text('[req]\ndistinguished_name=dn\n[dn]\n',encoding='ascii')
        def openssl(*arguments):
            subprocess.run(['openssl',*arguments],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout','ca.key','-out','ca.pem','-days','1',
                '-subj','/CN=HorasJogadas Temporary Test CA','-config','req.cnf',
                '-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign',
                '-addext','subjectKeyIdentifier=hash')
        openssl('req','-newkey','rsa:2048','-nodes','-keyout','server.key','-out','server.csr',
                '-subj','/CN=localhost','-config','req.cnf')
        (root/'extensions.cnf').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n',encoding='ascii')
        openssl('x509','-req','-in','server.csr','-CA','ca.pem','-CAkey','ca.key','-CAcreateserial',
                '-out','server.pem','-days','1','-extfile','extensions.cnf')
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'secure')
            def log_message(self,*args):pass
        cls.server=HTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(root/'server.pem',root/'server.key')
        cls.server.socket=context.wrap_socket(cls.server.socket,server_side=True)
        cls.thread=threading.Thread(target=lambda:cls.server.serve_forever(poll_interval=.02),daemon=True);cls.thread.start()
        cls.url='https://localhost:'+str(cls.server.server_port)+'/'
        cls.empty=root/'empty';cls.empty.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5);cls.temporary.cleanup()

    def test_custom_system_ca_remains_trusted(self):
        with patch.dict(os.environ,SSL_CERT_FILE=str(self.root/'ca.pem'),SSL_CERT_DIR=str(self.empty),NO_PROXY='localhost,127.0.0.1'):
            with urlopen(self.url,timeout=3) as response:self.assertEqual(response.read(),b'secure')

    def test_untrusted_issuer_is_still_rejected(self):
        with patch.dict(os.environ,SSL_CERT_FILE=str(self.root/'missing.pem'),SSL_CERT_DIR=str(self.empty),NO_PROXY='localhost,127.0.0.1'):
            with self.assertRaises(URLError) as error:urlopen(self.url,timeout=3)
        self.assertIsInstance(error.exception.reason,ssl.SSLCertVerificationError)

    def test_wrong_hostname_is_still_rejected_even_with_trusted_ca(self):
        with patch.dict(os.environ,SSL_CERT_FILE=str(self.root/'ca.pem'),SSL_CERT_DIR=str(self.empty),NO_PROXY='localhost,127.0.0.1'):
            with self.assertRaises(URLError) as error:urlopen(self.url.replace('localhost','127.0.0.1'),timeout=3)
        self.assertIsInstance(error.exception.reason,ssl.SSLCertVerificationError)

"""HTTPS com confiança do sistema e certificados portáteis incluídos no pacote."""
import ssl
import urllib.request
import certifi


def ssl_context():
    # Mantém as CAs do sistema e SSL_CERT_FILE/SSL_CERT_DIR, inclusive CAs locais.
    context=ssl.create_default_context()
    # O Python empacotado pode apontar para caminhos de CA exclusivos do runner.
    context.load_verify_locations(cafile=certifi.where())
    return context


def urlopen(request,timeout=15):
    return urllib.request.urlopen(request,timeout=timeout,context=ssl_context())

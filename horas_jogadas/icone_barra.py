"""Selo sobre o ícone da barra de tarefas do Windows, como no OBS.

  - bolinha vermelha  = há um cronômetro rodando
  - pause amarelo     = nenhum rodando, mas há cronômetro pausado
  - sem selo          = nada ativo (fica só o ícone original do app)

No Windows usa o recurso nativo "overlay icon" da barra (interface ITaskbarList3), via ctypes: sem
bibliotecas extras. Em outros sistemas, ou se algo falhar, simplesmente não faz nada (o app segue normal).
O desenho dos selos é gerado aqui mesmo (Python puro), sem arquivos de imagem.
"""
import logging
import os
import time
from typing import Callable, Iterable, Optional, Protocol

log = logging.getLogger(__name__)

ultimo_erro: Optional[str] = None   # motivo pelo qual o selo ficou indisponível (mostrado em Configurações)

ESTADO_RODANDO = "rodando"
ESTADO_PAUSADO = "pausado"

COR_VERMELHO = (229, 57, 53)
COR_AMARELO = (255, 193, 7)
TAMANHO_ICONE = 32                 # o Windows reduz para 16 px em 100% de escala (e usa mais pixels em telas HiDPI)
SUPERAMOSTRAGEM = 4                # 4x4 amostras por pixel = bordas suaves


def estado_do_icone(cronometros: Iterable) -> Optional[str]:
    """Estado do selo: rodando vence pausado; nada ativo = None (sem selo)."""
    cronometros = list(cronometros)
    if any(getattr(c, "rodando", False) for c in cronometros):
        return ESTADO_RODANDO
    if any(getattr(c, "pausado", False) for c in cronometros):
        return ESTADO_PAUSADO
    return None


# ---------------------------------------------------------------------------
# Desenho dos selos (sem dependências)
# ---------------------------------------------------------------------------
def _dentro_retangulo_arredondado(x: float, y: float, x0: float, y0: float, x1: float, y1: float, raio: float) -> bool:
    cx = min(max(x, x0 + raio), x1 - raio)
    cy = min(max(y, y0 + raio), y1 - raio)
    return (x - cx) ** 2 + (y - cy) ** 2 <= raio ** 2


def _formas(estado: str):
    """(função 'dentro do preenchimento', função 'dentro do contorno', cor) em coordenadas de 0 a 1."""
    if estado == ESTADO_RODANDO:
        def preenche(x, y): return (x - 0.5) ** 2 + (y - 0.5) ** 2 <= 0.38 ** 2
        def contorno(x, y): return (x - 0.5) ** 2 + (y - 0.5) ** 2 <= 0.45 ** 2
        return preenche, contorno, COR_VERMELHO
    if estado == ESTADO_PAUSADO:
        def preenche(x, y):
            return (_dentro_retangulo_arredondado(x, y, 0.20, 0.14, 0.42, 0.86, 0.05)
                    or _dentro_retangulo_arredondado(x, y, 0.58, 0.14, 0.80, 0.86, 0.05))
        def contorno(x, y):
            return (_dentro_retangulo_arredondado(x, y, 0.165, 0.105, 0.455, 0.895, 0.085)
                    or _dentro_retangulo_arredondado(x, y, 0.545, 0.105, 0.835, 0.895, 0.085))
        return preenche, contorno, COR_AMARELO
    raise ValueError(f"estado desconhecido: {estado}")


def renderizar(estado: str, tamanho: int = TAMANHO_ICONE) -> bytes:
    """Imagem do selo em BGRA (de cima para baixo, alfa 'direto'), com bordas suavizadas."""
    preenche, contorno, cor = _formas(estado)
    n = SUPERAMOSTRAGEM
    saida = bytearray()
    for py in range(tamanho):
        for px in range(tamanho):
            a_total = r_total = g_total = b_total = 0.0
            for sy in range(n):
                for sx in range(n):
                    x, y = (px + (sx + 0.5) / n) / tamanho, (py + (sy + 0.5) / n) / tamanho
                    if preenche(x, y):
                        alfa, rgb = 1.0, cor
                    elif contorno(x, y):
                        alfa, rgb = 0.40, (0, 0, 0)            # contorno escuro: dá contraste em barras claras
                    else:
                        continue
                    a_total += alfa
                    r_total += rgb[0] * alfa
                    g_total += rgb[1] * alfa
                    b_total += rgb[2] * alfa
            if a_total == 0:
                saida += b"\x00\x00\x00\x00"
                continue
            amostras = n * n
            saida += bytes((round(b_total / a_total), round(g_total / a_total), round(r_total / a_total),
                            round(255 * a_total / amostras)))
    return bytes(saida)


def _inteiro(valor: int, bytes_: int, com_sinal: bool = False) -> bytes:
    return valor.to_bytes(bytes_, "little", signed=com_sinal)


def montar_icone_dib(bgra: bytes, tamanho: int = TAMANHO_ICONE) -> bytes:
    """Empacota os pixels no formato de uma imagem de ícone (DIB de 32 bits + máscara), como dentro de um .ico.

    (Montado byte a byte, sem a biblioteca `struct`: o .exe já distribuído não a carrega.)
    """
    cabecalho = (_inteiro(40, 4) + _inteiro(tamanho, 4, True) + _inteiro(tamanho * 2, 4, True)   # tamanho, largura, altura (2x)
                 + _inteiro(1, 2) + _inteiro(32, 2) + _inteiro(0, 4) + _inteiro(tamanho * tamanho * 4, 4)
                 + _inteiro(0, 4) + _inteiro(0, 4) + _inteiro(0, 4) + _inteiro(0, 4))
    linhas = [bgra[i * tamanho * 4:(i + 1) * tamanho * 4] for i in range(tamanho)]
    xor = b"".join(reversed(linhas))                           # DIB é de baixo para cima
    linha_mascara = ((tamanho + 31) // 32) * 4
    return cabecalho + xor + bytes(linha_mascara * tamanho)    # máscara zerada: a transparência vem do alfa


def montar_arquivo_ico(bgra: bytes, tamanho: int = TAMANHO_ICONE) -> bytes:
    """Arquivo .ico completo com uma imagem (plano B para carregar o ícone caso a via direta falhe)."""
    dib = montar_icone_dib(bgra, tamanho)
    cabecalho = _inteiro(0, 2) + _inteiro(1, 2) + _inteiro(1, 2)                   # ICONDIR: reservado, tipo=ícone, 1 imagem
    entrada = (bytes((tamanho % 256, tamanho % 256, 0, 0)) + _inteiro(1, 2) + _inteiro(32, 2)
               + _inteiro(len(dib), 4) + _inteiro(6 + 16, 4))                      # ICONDIRENTRY
    return cabecalho + entrada + dib


# ---------------------------------------------------------------------------
# Aplicar o selo na barra de tarefas
# ---------------------------------------------------------------------------
class Backend(Protocol):
    def aplicar(self, janela_id: int, estado: Optional[str], descricao: str) -> bool:
        """Mostra (ou remove, se estado for None) o selo. Devolve False se não deu certo agora."""


class SobreposicaoBarra:
    """Mantém o selo da barra de tarefas em sincronia com o estado dos cronômetros.

    `definir` é barato e pode ser chamado a cada ciclo: só fala com o Windows quando o estado muda e, a
    cada `reaplicar_a_cada` segundos, para recuperar o selo se o Explorer for reiniciado.
    """

    def __init__(self, janela_id: Callable[[], int], descricao: Callable[[str], str], backend: Optional[Backend],
                 reaplicar_a_cada: float = 10.0, repetir_apos_falha: float = 2.0, relogio: Callable[[], float] = time.monotonic):
        self._janela_id = janela_id
        self._descricao = descricao
        self._backend = backend
        self._reaplicar = reaplicar_a_cada
        self._repetir = repetir_apos_falha
        self._relogio = relogio
        self._aplicado: Optional[str] = None        # None = sem selo (estado inicial já é "sem selo")
        self._ultima = relogio()
        self._proxima_tentativa = 0.0
        self._erros = 0

    @property
    def ativo(self) -> bool:
        return self._backend is not None

    def definir(self, estado: Optional[str]) -> None:
        if self._backend is None:
            return
        agora = self._relogio()
        if estado == self._aplicado and (estado is None or agora - self._ultima < self._reaplicar):
            return                                                  # nada a fazer
        if agora < self._proxima_tentativa:
            return
        try:
            descricao = self._descricao(estado) if estado else ""
            ok = self._backend.aplicar(self._janela_id(), estado, descricao)
        except Exception:                                           # nunca derruba o app por causa de um enfeite
            self._erros += 1
            log.exception("Falha ao atualizar o selo da barra de tarefas (%d)", self._erros)
            if self._erros >= 3:
                log.warning("Selo da barra de tarefas desativado após falhas repetidas")
                self._backend = None
            self._proxima_tentativa = agora + self._repetir
            return
        if ok:
            self._erros = 0
            if estado != self._aplicado:
                log.info("Selo da barra de tarefas: %s", estado or "removido")
            self._aplicado, self._ultima = estado, agora
        else:
            self._proxima_tentativa = agora + self._repetir        # barra ainda não pronta: tenta de novo já já


def chamar_metodo_com(ponteiro, indice: int, fabrica, argtypes, *args) -> int:
    """Chama o método `indice` da tabela de funções (vtable) de um objeto COM. Devolve o HRESULT.

    Um objeto COM é um ponteiro para uma estrutura cujo primeiro campo aponta para a tabela de métodos;
    o método de índice N é a N-ésima entrada dessa tabela (o primeiro argumento é sempre o próprio objeto).
    """
    import ctypes
    tabela = ctypes.cast(ctypes.cast(ponteiro, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    funcao = fabrica(ctypes.c_long, ctypes.c_void_p, *argtypes)(tabela[indice])
    return funcao(ponteiro, *args)


class BackendWindows:
    """ITaskbarList3::SetOverlayIcon via ctypes (só Windows). Usa apenas tipos básicos do ctypes."""

    _CLSID_TASKBAR_LIST = "{56FDF344-FD6D-11D0-958A-006097C9A090}"
    _IID_TASKBAR_LIST3 = "{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}"
    _INDICE_HRINIT = 3                 # ITaskbarList::HrInit
    _INDICE_SET_OVERLAY_ICON = 18      # ITaskbarList3::SetOverlayIcon (IUnknown 0-2, ITaskbarList 3-7, List2 8, List3 9...)

    def __init__(self) -> None:
        import ctypes
        self._ct = ctypes
        self._user32, self._ole32 = ctypes.windll.user32, ctypes.windll.ole32
        self._fabrica = ctypes.WINFUNCTYPE
        self._icones: dict = {}
        self._hr_ja_registrado = None
        self._definir_assinaturas()
        self._ole32.CoInitialize(None)                              # S_OK/S_FALSE; se já inicializado de outro modo, segue
        self._ptr = ctypes.c_void_p()
        hr = self._ole32.CoCreateInstance(ctypes.byref(self._guid(self._CLSID_TASKBAR_LIST)), None, 1,
                                          ctypes.byref(self._guid(self._IID_TASKBAR_LIST3)), ctypes.byref(self._ptr))
        if hr != 0 or not self._ptr.value:
            raise OSError(f"CoCreateInstance(TaskbarList) falhou: 0x{hr & 0xFFFFFFFF:08X}")
        hr = chamar_metodo_com(self._ptr, self._INDICE_HRINIT, self._fabrica, ())
        if hr < 0:
            raise OSError(f"ITaskbarList::HrInit falhou: 0x{hr & 0xFFFFFFFF:08X}")
        log.info("Selo da barra de tarefas pronto (ITaskbarList3 inicializado)")

    def _guid(self, texto: str):
        ct = self._ct

        class GUID(ct.Structure):
            _fields_ = [("a", ct.c_uint32), ("b", ct.c_uint16), ("c", ct.c_uint16), ("d", ct.c_ubyte * 8)]
        import uuid
        u = uuid.UUID(texto)
        return GUID(u.time_low, u.time_mid, u.time_hi_version, (ct.c_ubyte * 8)(*u.bytes[8:]))

    def _definir_assinaturas(self) -> None:
        ct = self._ct
        vp, u32 = ct.c_void_p, ct.c_uint32
        self._user32.CreateIconFromResourceEx.argtypes = [vp, u32, ct.c_int, u32, ct.c_int, ct.c_int, ct.c_uint]
        self._user32.CreateIconFromResourceEx.restype = vp
        self._user32.LoadImageW.argtypes = [vp, ct.c_wchar_p, ct.c_uint, ct.c_int, ct.c_int, ct.c_uint]
        self._user32.LoadImageW.restype = vp
        self._user32.GetAncestor.argtypes = [vp, ct.c_uint]
        self._user32.GetAncestor.restype = vp
        self._user32.GetParent.argtypes = [vp]
        self._user32.GetParent.restype = vp
        self._ole32.CoCreateInstance.argtypes = [vp, vp, u32, vp, vp]
        self._ole32.CoCreateInstance.restype = ct.c_long

    def _icone(self, estado: str):
        if estado in self._icones:
            return self._icones[estado]
        bgra = renderizar(estado)
        dados = montar_icone_dib(bgra)
        buffer = self._ct.create_string_buffer(dados, len(dados))
        hicon = self._user32.CreateIconFromResourceEx(buffer, len(dados), 1, 0x00030000, TAMANHO_ICONE, TAMANHO_ICONE, 0)
        if not hicon:                                               # plano B: grava um .ico temporário e carrega dele
            import tempfile
            caminho = os.path.join(tempfile.gettempdir(), f"horas_jogadas_selo_{estado}.ico")
            with open(caminho, "wb") as f:
                f.write(montar_arquivo_ico(bgra))
            hicon = self._user32.LoadImageW(None, caminho, 1, TAMANHO_ICONE, TAMANHO_ICONE, 0x10)   # IMAGE_ICON, LR_LOADFROMFILE
            log.warning("CreateIconFromResourceEx falhou; ícone carregado do arquivo temporário (%s)", "ok" if hicon else "FALHOU")
        if not hicon:
            raise OSError(f"não foi possível criar o ícone do selo ({estado})")
        self._icones[estado] = hicon
        return hicon

    def _janelas_candidatas(self, janela_id: int):
        """Janela do botão da barra de tarefas: a de nível superior (raiz) da janela interna do Tk."""
        candidatas = []
        for obter in (lambda: self._user32.GetAncestor(janela_id, 2),     # GA_ROOT
                      lambda: self._user32.GetParent(janela_id),
                      lambda: janela_id):
            hwnd = obter()
            if hwnd and hwnd not in candidatas:
                candidatas.append(hwnd)
        return candidatas

    def aplicar(self, janela_id: int, estado: Optional[str], descricao: str) -> bool:
        ct = self._ct
        hicon = self._icone(estado) if estado else None             # None remove o selo
        ultimo_hr = None
        for hwnd in self._janelas_candidatas(janela_id):
            hr = chamar_metodo_com(self._ptr, self._INDICE_SET_OVERLAY_ICON, self._fabrica,
                                   (ct.c_void_p, ct.c_void_p, ct.c_wchar_p), hwnd, hicon, descricao or None)
            if hr >= 0:
                return True
            ultimo_hr = hr
        if ultimo_hr != self._hr_ja_registrado:                     # evita lotar o log com a mesma falha
            self._hr_ja_registrado = ultimo_hr
            log.warning("SetOverlayIcon recusado pelo Windows: HRESULT 0x%08X", (ultimo_hr or 0) & 0xFFFFFFFF)
        return False


def criar_backend() -> Optional[Backend]:
    """Backend do Windows; None em outros sistemas ou se o recurso não estiver disponível."""
    global ultimo_erro
    if os.name != "nt":
        return None
    try:
        return BackendWindows()
    except Exception as e:                                          # noqa: BLE001 - enfeite opcional
        ultimo_erro = f"{type(e).__name__}: {e}"                    # aparece em Configurações, para diagnóstico
        log.exception("Selo da barra de tarefas indisponível; seguindo sem ele")
        return None

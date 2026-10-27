"""Cores da barra de título nativa do Windows, mantendo a moldura e os controles do SO."""
import ctypes
import logging
import sys
import weakref
from PySide6.QtCore import QObject, QEvent, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

log = logging.getLogger(__name__)


def colorref(color):
    value = QColor(color)
    return value.red() | (value.green() << 8) | (value.blue() << 16)


def apply_native_titlebar(hwnd, background, foreground, border, dark, setter=None):
    """Win10 usa modo escuro; Win11 também permite cores explícitas de título/texto/borda.

    Atributos não suportados são ignorados pelo DWM. Não altera estilos de janela,
    eventos de mouse, área de arraste ou o gerenciamento nativo de minimizar/maximizar.
    `setter` permite testar o contrato da API em máquinas sem Windows.
    """
    if setter is None:
        if sys.platform != 'win32':
            return False
        try:
            setter = ctypes.WinDLL('dwmapi').DwmSetWindowAttribute
            setter.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            setter.restype = ctypes.c_int32
        except (AttributeError, OSError):
            return False
    handle = ctypes.c_void_p(int(hwnd))
    def attribute(number, value):
        return setter(handle, number, ctypes.byref(value), ctypes.sizeof(value)) == 0
    try:
        applied = attribute(20, ctypes.c_int32(bool(dark)))
        if not applied:
            applied = attribute(19, ctypes.c_int32(bool(dark)))
        for number, color in ((35, background), (36, foreground), (34, border)):
            # COLORREF é DWORD de 32 bits, inclusive em Windows de 64 bits.
            applied = attribute(number, ctypes.c_uint32(colorref(color))) or applied
        return applied
    except (OSError, AttributeError, TypeError):
        log.debug('Não foi possível aplicar as cores da moldura nativa', exc_info=True)
        return False


def redraw_native_frame(hwnd):
    if sys.platform != 'win32':
        return
    try:
        redraw = ctypes.WinDLL('user32').RedrawWindow
        redraw.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        redraw.restype = ctypes.c_int32
        redraw(ctypes.c_void_p(int(hwnd)), None, None, 0x0001 | 0x0100 | 0x0400)
    except (OSError, AttributeError):
        log.debug('Redesenho da barra de título não disponível', exc_info=True)


class WindowChrome(QObject):
    def __init__(self, app, enabled=None, writer=None):
        super().__init__(app)
        self.app = app
        self.enabled = sys.platform == 'win32' if enabled is None else enabled
        self.writer = writer or apply_native_titlebar
        self.colors = None
        self.busy = False
        self.applied = weakref.WeakKeyDictionary()
        app.installEventFilter(self)

    def update_theme(self, background, foreground, border):
        self.colors = (background, foreground, border, QColor(background).lightness() < 128)
        if self.enabled:
            for widget in self.app.topLevelWidgets():
                self.schedule(widget)

    def schedule(self, widget):
        if (not self.enabled or self.busy or not isinstance(widget, QWidget)
                or not widget.isWindow() or not widget.windowFlags() & Qt.WindowTitleHint):
            return
        # Após o show, o HWND e os controles da barra já pertencem ao Windows.
        QTimer.singleShot(0, widget, lambda: self.apply(widget))

    def apply(self, widget, before_show=False):
        if self.busy or not self.colors or (not before_show and not widget.isVisible()):
            return
        self.busy = True
        try:
            handle = int(widget.winId())
            state = (handle, self.colors)
            if self.applied.get(widget) == state:
                return
            if self.writer(handle, *self.colors):
                self.applied[widget] = state
                redraw_native_frame(handle)
        except RuntimeError:
            # Uma janela pode ter sido fechada antes de processar o callback.
            pass
        finally:
            self.busy = False

    def eventFilter(self, watched, event):
        if self.enabled and not self.busy and event.type() in (QEvent.Show, QEvent.WinIdChange):
            if isinstance(watched, QWidget) and watched.isWindow() and watched.windowFlags() & Qt.WindowTitleHint:
                if event.type() == QEvent.WinIdChange:
                    self.applied.pop(watched, None)
                # Define as cores antes de o Windows expor a moldura branca na abertura.
                self.apply(watched, before_show=True)
                self.schedule(watched)
        return False


def update_window_chrome(app, background, foreground, border):
    controller = getattr(app, '_horas_window_chrome', None)
    if controller is None:
        controller = WindowChrome(app)
        app._horas_window_chrome = controller
    controller.update_theme(background, foreground, border)

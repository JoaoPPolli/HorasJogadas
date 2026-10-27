"""Paleta original e contrato da integração nativa da barra de título."""
import ctypes
import unittest
from unittest.mock import Mock
from . import test_ui as _ui
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from horas_jogadas.constants import COR_BG, COR_CARD, COR_BTN, COR_ACCENT, COR_TEXTO, COR_BORDA
from horas_jogadas_qt.theme import apply_theme, PALETTES
from horas_jogadas_qt.window_chrome import WindowChrome, apply_native_titlebar, colorref
from horas_jogadas_qt.widgets import Form

APP=_ui.APP


class ThemeTests(unittest.TestCase):
    setUp=_ui.UiTests.setUp
    tearDown=_ui.UiTests.tearDown

    def test_original_theme_uses_original_palette_and_is_available_in_settings(self):
        self.w.navigate('settings')
        from PySide6.QtWidgets import QComboBox
        options=[widget for widget in self.w.pages['settings'].findChildren(QComboBox)
                 if widget.findData('original')>=0]
        self.assertEqual(len(options),1)
        self.w.save_settings('original','pt'); APP.processEvents()
        self.assertEqual(self.w.theme_name(),'original')
        for role,expected in [(QPalette.Window,COR_BG),(QPalette.Base,COR_CARD),
                               (QPalette.Button,COR_BTN),(QPalette.Link,COR_ACCENT),
                               (QPalette.WindowText,COR_TEXTO)]:
            self.assertEqual(APP.palette().color(role).name(),expected)
        self.w.navigate('library')
        primary=self.w.cards[self.c.repo.jogos[0].id].start
        self.assertEqual(primary.icon().isNull(),False)
        self.assertEqual(APP.property('horasPrimaryText'),'#ffffff')
        self.assertEqual(self.critical.call_count,0)

    def test_original_theme_can_be_reloaded_without_altering_game_records(self):
        from horas_jogadas_qt.controller import Controller
        before=[s.to_dict() for s in self.c.repo.sessoes]
        self.w.save_settings('original','pt')
        reloaded=Controller(self.folder)
        self.assertEqual([s.to_dict() for s in reloaded.repo.sessoes],before)
        self.assertEqual(self.w.theme_name(),'original')
        self.assertEqual(APP._horas_window_chrome.colors,(COR_BG,COR_TEXTO,COR_BORDA,True))

    def test_chrome_applies_to_existing_window_new_dialog_and_theme_changes(self):
        writer=Mock(return_value=True)
        chrome=WindowChrome(APP,enabled=True,writer=writer)
        try:
            chrome.update_theme(COR_BG,COR_TEXTO,COR_BORDA)
            APP.processEvents()
            self.assertTrue(any(call.args[0]==int(self.w.winId()) for call in writer.call_args_list))
            dialog=Form(self.w,'Diálogo de teste')
            writer.reset_mock()
            dialog.show()
            # O tratamento de Show acontece antes de esperar o próximo frame.
            self.assertTrue(any(call.args[0]==int(dialog.winId()) for call in writer.call_args_list))
            APP.processEvents()
            calls=writer.call_count
            chrome.apply(dialog); chrome.apply(dialog)
            self.assertEqual(writer.call_count,calls)
            chrome.update_theme('#f4f5f7','#20252d','#d6dbe2')
            APP.processEvents()
            self.assertEqual(writer.call_args.args[1:],('#f4f5f7','#20252d','#d6dbe2',False))
            dialog.reject()
        finally:
            APP.removeEventFilter(chrome); chrome.deleteLater()
            APP.sendPostedEvents(None,QEvent.DeferredDelete)


class NativeContractTests(unittest.TestCase):
    def setter(self,result=None):
        self.calls=[]
        def write(hwnd,attribute,pointer,size):
            self.calls.append((hwnd.value,attribute,ctypes.cast(pointer,ctypes.POINTER(ctypes.c_uint32)).contents.value,size))
            return (result or {}).get(attribute,0)
        return write

    def test_native_colors_are_32_bit_colorref_and_handle_is_not_truncated(self):
        hwnd=0x123456789
        self.assertTrue(apply_native_titlebar(hwnd,COR_BG,COR_TEXTO,COR_BORDA,True,self.setter()))
        values={attribute:(handle,value,size) for handle,attribute,value,size in self.calls}
        self.assertEqual(values[20],(hwnd,1,4))
        self.assertEqual(values[35],(hwnd,colorref(COR_BG),4))
        self.assertEqual(values[36],(hwnd,colorref(COR_TEXTO),4))
        self.assertEqual(values[34],(hwnd,colorref(COR_BORDA),4))
        self.assertEqual(colorref('#123456'),0x563412)

    def test_older_windows_can_use_dark_mode_when_explicit_colors_are_unsupported(self):
        self.assertTrue(apply_native_titlebar(1,COR_BG,COR_TEXTO,COR_BORDA,True,
            self.setter({20:-1,35:-1,36:-1,34:-1})))
        self.assertEqual([call[1] for call in self.calls],[20,19,35,36,34])

    def test_light_theme_disables_dark_mode_and_uses_light_caption_colors(self):
        self.assertTrue(apply_native_titlebar(1,'#f4f5f7','#20252d','#d6dbe2',False,self.setter()))
        values={attribute:value for _,attribute,value,_ in self.calls}
        self.assertEqual(values[20],0)
        self.assertEqual(values[35],colorref('#f4f5f7'))

    def test_unsupported_dwm_attributes_do_not_break_the_app(self):
        self.assertFalse(apply_native_titlebar(1,COR_BG,COR_TEXTO,COR_BORDA,True,
            self.setter({20:-1,19:-1,35:-1,36:-1,34:-1})))

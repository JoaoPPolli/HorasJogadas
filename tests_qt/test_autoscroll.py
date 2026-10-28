"""Gestos reais, cancelamento, edição de texto e preservação dos registros."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
if importlib.util.find_spec('PySide6') is None:raise unittest.SkipTest('PySide6 necessário')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt,QPoint,QPointF,QEvent
from PySide6.QtGui import QMouseEvent,QKeyEvent
from PySide6.QtWidgets import QApplication,QWidget,QScrollArea,QVBoxLayout,QPushButton,QLineEdit,QPlainTextEdit,QTableWidget,QTableWidgetItem
from PySide6.QtTest import QTest,QSignalSpy
from horas_jogadas_qt.autoscroll import AutoScroll

APP=QApplication.instance() or QApplication([])


def move(manager,dy):
    point=manager.anchor+QPoint(0,dy)
    event=QMouseEvent(QEvent.MouseMove,QPointF(manager.overlay.mapFromGlobal(point)),QPointF(point),Qt.NoButton,Qt.NoButton,Qt.NoModifier)
    QApplication.sendEvent(manager.overlay,event)


class AutoScrollTests(unittest.TestCase):
    def setUp(self):
        self.window=QWidget();self.window.resize(700,440)
        layout=QVBoxLayout(self.window);self.area=QScrollArea();self.area.setWidgetResizable(True);layout.addWidget(self.area)
        self.content=QWidget();self.content.setMinimumHeight(2200);self.area.setWidget(self.content)
        self.button=QPushButton('Action',self.content);self.button.setGeometry(10,10,160,35)
        self.edit=QLineEdit(self.content);self.edit.setGeometry(10,65,240,35)
        self.notes=QPlainTextEdit(self.content);self.notes.setGeometry(10,120,240,100)
        self.manager=AutoScroll(self.window);self.window.show();self.window.activateWindow();APP.processEvents()

    def tearDown(self):
        self.manager.stop();APP.removeEventFilter(self.manager);self.window.close();self.window.deleteLater()
        APP.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents()

    def start(self):
        QTest.mouseClick(self.area.viewport(),Qt.MiddleButton,pos=QPoint(400,160))
        self.assertTrue(self.manager.active)

    def test_click_and_release_keeps_scrolling_with_direction_and_speed(self):
        self.start();self.assertFalse(self.manager.awaiting_release)
        bar=self.area.verticalScrollBar()
        move(self.manager,8);self.manager.advance(.1);self.assertEqual(bar.value(),0)
        move(self.manager,50);self.manager.advance(.1);slow=bar.value();self.assertGreater(slow,0)
        move(self.manager,150);self.manager.advance(.1);self.assertGreater(bar.value()-slow,slow)
        before=bar.value();move(self.manager,-100);self.manager.advance(.1);self.assertLess(bar.value(),before)
        self.manager.advance(20);self.assertEqual(bar.value(),0)

    def test_escape_cancels_and_restores_normal_pointer(self):
        self.start();overlay=self.manager.overlay
        QApplication.sendEvent(overlay,QKeyEvent(QEvent.KeyPress,Qt.Key_Escape,Qt.NoModifier))
        self.assertFalse(self.manager.active);self.assertFalse(overlay.isVisible());self.assertFalse(self.manager.timer.isActive())
        self.assertIsNone(QApplication.overrideCursor())

    def test_cancel_click_does_not_activate_button_under_pointer(self):
        spy=QSignalSpy(self.button.clicked);self.start()
        QTest.mouseClick(self.button,Qt.LeftButton)
        self.assertFalse(self.manager.active);self.assertEqual(spy.count(),0)
        QTest.mouseClick(self.button,Qt.LeftButton);self.assertEqual(spy.count(),1)

    def test_second_middle_click_cancels(self):
        self.start();QTest.mouseClick(self.manager.overlay,Qt.MiddleButton)
        self.assertFalse(self.manager.active)

    def test_hold_drag_release_stops_but_plain_release_stays_active(self):
        QTest.mousePress(self.area.viewport(),Qt.MiddleButton,pos=QPoint(400,160))
        self.assertTrue(self.manager.active);move(self.manager,90)
        QTest.mouseRelease(self.manager.overlay,Qt.MiddleButton)
        self.assertFalse(self.manager.active)
        self.start()

    def test_middle_click_in_text_fields_keeps_normal_paste_behavior(self):
        for widget in [self.edit,self.notes.viewport()]:
            QTest.mouseClick(widget,Qt.MiddleButton)
            self.assertFalse(self.manager.active)

    def test_empty_page_and_scrollbar_do_not_activate(self):
        QTest.mouseClick(self.area.verticalScrollBar(),Qt.MiddleButton)
        self.assertFalse(self.manager.active)
        self.content.setMinimumHeight(0);self.content.resize(300,50);APP.processEvents()
        self.assertEqual(self.area.verticalScrollBar().maximum(),0)
        QTest.mouseClick(self.area.viewport(),Qt.MiddleButton)
        self.assertFalse(self.manager.active)

    def test_window_hide_deactivation_and_deleted_view_stop_timer(self):
        for event in [QEvent.WindowDeactivate,QEvent.Hide]:
            self.start();QApplication.sendEvent(self.window,QEvent(event))
            self.assertFalse(self.manager.active)
        self.start();self.content.deleteLater();self.area.deleteLater()
        APP.sendPostedEvents(None,QEvent.DeferredDelete);self.manager.advance(.1)
        self.assertFalse(self.manager.active)

    def test_nested_table_scrolls_itself_without_changing_selection(self):
        table=QTableWidget(80,2,self.content);table.setGeometry(300,10,320,240)
        for row in range(80):table.setItem(row,0,QTableWidgetItem(str(row)))
        table.show();table.selectRow(4);APP.processEvents()
        QTest.mouseClick(table.viewport(),Qt.MiddleButton,pos=QPoint(90,90))
        self.assertIs(self.manager.area,table)
        move(self.manager,130);self.manager.advance(.2)
        self.assertGreater(table.verticalScrollBar().value(),0);self.assertEqual(table.currentRow(),4)
        self.assertEqual(self.area.verticalScrollBar().value(),0)

    def test_qt_timer_scrolls_after_mouse_move_without_global_pointer_polling(self):
        self.start();move(self.manager,120);QTest.qWait(90)
        self.assertGreater(self.area.verticalScrollBar().value(),0)


class AppAutoScrollTests(unittest.TestCase):
    def test_library_scroll_keeps_timers_and_raw_records_and_stops_on_navigation(self):
        from app_qt import seed_demo
        from horas_jogadas_qt.controller import Controller
        from horas_jogadas_qt.window import Window
        from horas_jogadas_qt.preview import inventory
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seed_demo(root);controller=Controller(root);window=Window(controller)
            window.resize(840,620);window.show();window.activateWindow();APP.processEvents()
            baseline=inventory(root);key=controller.repo.jogos[0].id;timer=controller.timers[key];timer.start()
            try:
                QTest.mouseClick(window.library_scroll.viewport(),Qt.MiddleButton,pos=QPoint(30,30))
                self.assertTrue(window.autoscroll.active)
                move(window.autoscroll,130);window.autoscroll.advance(.2)
                self.assertGreater(window.library_scroll.verticalScrollBar().value(),0)
                self.assertIs(controller.timers[key],timer);self.assertTrue(timer.rodando)
                for name,digest in baseline.items():self.assertEqual(inventory(root)[name],digest)
                window.navigate('stats');APP.processEvents();self.assertFalse(window.autoscroll.active)
            finally:
                timer.reset();window.timer.stop();window.closing_allowed=True;window.close()
                APP.removeEventFilter(window);window.deleteLater();APP.sendPostedEvents(None,QEvent.DeferredDelete)

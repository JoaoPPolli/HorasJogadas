"""A roda não altera campos e o banner mantém a arte inteira na página do jogo."""
import tempfile
import unittest
from pathlib import Path
from PySide6.QtCore import Qt,QPoint,QPointF
from PySide6.QtGui import QImage,QColor,QPainter,QWheelEvent
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QScrollArea,QComboBox,QSpinBox,QDoubleSpinBox,QDateTimeEdit
from PySide6.QtTest import QTest
from horas_jogadas_qt.theme import apply_theme
from horas_jogadas_qt.cover_widget import GameCover
APP=QApplication.instance() or QApplication([])


def wheel(widget,amount=-120):
    pos=widget.rect().center();global_pos=widget.mapToGlobal(pos)
    event=QWheelEvent(QPointF(pos),QPointF(global_pos),QPoint(),QPoint(0,amount),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
    APP.sendEvent(widget,event);APP.processEvents()


class WheelTests(unittest.TestCase):
    def setUp(self):
        apply_theme(APP,'original');self.area=QScrollArea();self.area.resize(500,350);self.area.setWidgetResizable(True)
        self.host=QWidget();self.layout=QVBoxLayout(self.host);self.host.setMinimumHeight(1800);self.area.setWidget(self.host)
        self.combo=QComboBox();self.combo.addItems(['A','B','C']);self.combo.setCurrentIndex(1);self.layout.addWidget(self.combo)
        self.spin=QSpinBox();self.spin.setRange(0,100);self.spin.setValue(50);self.layout.addWidget(self.spin)
        self.double=QDoubleSpinBox();self.double.setValue(4.5);self.layout.addWidget(self.double)
        self.date=QDateTimeEdit();self.layout.addWidget(self.date)
        self.layout.addStretch();self.area.show();APP.processEvents()
    def tearDown(self):self.area.close();self.area.deleteLater();APP.processEvents()
    def test_closed_selectors_and_values_stay_unchanged_while_page_scrolls(self):
        for widget,value in [(self.combo,self.combo.currentIndex()),(self.spin,self.spin.value()),(self.double,self.double.value()),(self.date,self.date.dateTime())]:
            self.area.verticalScrollBar().setValue(0);widget.setFocus();wheel(widget)
            actual=widget.currentIndex() if isinstance(widget,QComboBox) else widget.dateTime() if isinstance(widget,QDateTimeEdit) else widget.value()
            self.assertEqual(actual,value);self.assertGreater(self.area.verticalScrollBar().value(),0)
    def test_forwarded_wheel_has_same_distance_as_page_wheel(self):
        self.area.verticalScrollBar().setValue(0);wheel(self.area.viewport());distance=self.area.verticalScrollBar().value()
        self.area.verticalScrollBar().setValue(0);wheel(self.combo)
        self.assertEqual(self.area.verticalScrollBar().value(),distance)

    def test_internal_edit_and_page_wheel_work(self):
        self.spin.setFocus();self.area.verticalScrollBar().setValue(0)
        wheel(self.spin.lineEdit());self.assertEqual(self.spin.value(),50);self.assertGreater(self.area.verticalScrollBar().value(),0)
        before=self.area.verticalScrollBar().value();wheel(self.area.viewport());self.assertGreater(self.area.verticalScrollBar().value(),before)
    def test_popup_scroll_does_not_commit_and_click_still_selects(self):
        self.combo.clear();self.combo.addItems([str(i) for i in range(100)]);self.combo.setMaxVisibleItems(6);self.combo.setCurrentIndex(0)
        self.combo.showPopup();APP.processEvents();view=self.combo.view();wheel(view.viewport(),-120)
        self.assertEqual(self.combo.currentIndex(),0)
        view.scrollTo(view.model().index(35,0));APP.processEvents();index=view.model().index(35,0)
        QTest.mouseClick(view.viewport(),Qt.LeftButton,pos=view.visualRect(index).center());APP.processEvents()
        self.assertEqual(self.combo.currentIndex(),35)
    def test_keyboard_still_works_and_reapplying_theme_does_not_duplicate_guard(self):
        guard=APP._horas_wheel_guard;apply_theme(APP,'light');self.assertIs(guard,APP._horas_wheel_guard)
        self.combo.setFocus();QTest.keyClick(self.combo,Qt.Key_Down);self.assertEqual(self.combo.currentIndex(),2)


class BannerTests(unittest.TestCase):
    def test_detail_banner_preserves_entire_image_at_different_widths(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sample.png';image=QImage(460,215,QImage.Format_RGB32);image.fill(QColor('white'))
            painter=QPainter(image);painter.fillRect(0,0,230,108,QColor('red'));painter.fillRect(230,0,230,108,QColor('green'));painter.fillRect(0,108,230,107,QColor('blue'));painter.fillRect(230,108,230,107,QColor('yellow'));painter.end();image.save(str(path))
            cover=GameCover('Synthetic',path,fit='contain',height=260)
            for width in [310,620,1600]:
                cover.resize(width,260);cover.show();APP.processEvents();rect=cover.image_rect()
                self.assertGreaterEqual(rect.left(),0);self.assertGreaterEqual(rect.top(),0)
                self.assertLessEqual(rect.right(),width);self.assertLessEqual(rect.bottom(),260)
                self.assertAlmostEqual(rect.width()/rect.height(),460/215)
                painted=cover.grab().toImage()
                for x,y,color in [(0.1,0.1,'red'),(0.9,0.1,'green'),(0.1,0.9,'blue'),(0.9,0.9,'yellow')]:
                    point=QPoint(int(rect.left()+rect.width()*x),int(rect.top()+rect.height()*y));actual=painted.pixelColor(point);expected=QColor(color)
                    self.assertEqual(tuple(v>0 for v in actual.getRgb()[:3]),tuple(v>0 for v in expected.getRgb()[:3]))
            cover.close();cover.deleteLater()
            thumbnail=GameCover('Synthetic',path);self.assertEqual(thumbnail.height(),132);thumbnail.deleteLater()

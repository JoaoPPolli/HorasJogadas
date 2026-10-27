"""Paletas nativas, sem dependência de imagens ou serviços externos."""
from PySide6.QtGui import QColor, QPalette, QFont

PALETTES = {
    'dark': ('#191c20', '#121416', '#22262b', '#32383f', '#f0f2f5', '#a1a9b5', '#e2e8f0', '#171a20'),
    'violet': ('#15141c', '#101017', '#211f2d', '#363147', '#f2f0fa', '#aba6bc', '#a89bfa', '#151121'),
    'light': ('#f4f5f7', '#ebedf0', '#ffffff', '#d6dbe2', '#20252d', '#596575', '#365ac8', '#ffffff'),
}


def apply_theme(app, name='dark'):
    bg, side, card, border, text, muted, accent, on_accent = PALETTES.get(name, PALETTES['dark'])
    app.setStyle('Fusion')
    palette = QPalette()
    for role, color in [(QPalette.Window, bg), (QPalette.WindowText, text), (QPalette.Base, card),
                        (QPalette.AlternateBase, bg), (QPalette.Text, text), (QPalette.Button, card),
                        (QPalette.ButtonText, text), (QPalette.Highlight, '#506073'),
                        (QPalette.HighlightedText, '#ffffff'), (QPalette.ToolTipBase, card),
                        (QPalette.ToolTipText, text)]:
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(muted))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(muted))
    app.setPalette(palette)
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(f'''
      QWidget {{ color: {text}; }}
      QMainWindow, QDialog {{ background: {bg}; }}
      QFrame#sidebar {{ background: {side}; border-right: 1px solid {border}; }}
      QLabel#brand {{ font-size: 14px; font-weight: 650; }}
      QLabel#logo {{ background: {accent}; color: {on_accent}; border-radius: 10px;
                    font-size: 16px; font-weight: 700; padding: 8px; }}
      QLabel#title {{ font-size: 27px; font-weight: 650; }}
      QLabel#muted, QLabel#subtitle {{ color: {muted}; }}
      QLabel#eyebrow {{ color: {muted}; font-size: 10px; font-weight: 600; }}
      QLabel#metric {{ font-size: 25px; font-weight: 600; }}
      QLabel#gameName {{ font-size: 15px; font-weight: 600; }}
      QLabel#timer {{ font-family: 'Consolas', 'DejaVu Sans Mono'; font-size: 31px; font-weight: 500; }}
      QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 12px; }}
      QFrame#card QLabel {{ background: transparent; border: none; }}
      QLabel#badge {{ background: {side}; color: {muted}; border-radius: 5px; padding: 4px 8px; font-size: 11px; }}
      QLabel#running {{ color: #56bc95; }}
      QLabel#paused {{ color: #d9ae60; }}
      QLabel#review {{ background: {side}; color: {muted}; border: 1px solid {border};
                       border-radius: 8px; padding: 9px 12px; font-size: 11px; }}
      QPushButton {{ background: {card}; border: 1px solid {border}; border-radius: 7px;
                     padding: 8px 12px; min-height: 18px; }}
      QPushButton:hover {{ border-color: {muted}; }}
      QPushButton:focus {{ border: 1px solid {accent}; }}
      QPushButton:pressed {{ background: {border}; }}
      QPushButton:disabled {{ color: {muted}; background: {bg}; border-color: {border}; }}
      QPushButton#primary {{ background: {accent}; color: {on_accent}; border-color: {accent}; font-weight: 600; }}
      QPushButton#primary:disabled {{ background: {border}; color: {muted}; border-color: {border}; }}
      QPushButton#danger {{ color: #df797e; }}
      QPushButton#nav {{ text-align: left; background: transparent; border: none; padding: 12px 14px; color: {muted}; }}
      QPushButton#nav:checked {{ background: {card}; color: {text}; font-weight: 600; }}
      QPushButton#nav:hover {{ background: {card}; color: {text}; }}
      QLineEdit, QComboBox, QSpinBox, QDateTimeEdit, QPlainTextEdit {{ background: {card};
          border: 1px solid {border}; border-radius: 7px; padding: 8px; min-height: 18px; selection-background-color: #506073; }}
      QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border-color: {muted}; }}
      QComboBox::drop-down {{ border: none; width: 22px; }}
      QScrollArea {{ border: none; background: transparent; }}
      QScrollBar:vertical {{ background: transparent; width: 9px; margin: 0; }}
      QScrollBar::handle:vertical {{ background: {border}; min-height: 30px; border-radius: 4px; }}
      QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
      QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
      QTableView {{ background: {card}; alternate-background-color: {bg}; border: 1px solid {border};
                    border-radius: 8px; gridline-color: {border}; selection-background-color: #394959; }}
      QTableView::item {{ padding: 8px; border: none; }}
      QHeaderView::section {{ background: {side}; color: {muted}; padding: 12px 8px; border: none;
                             border-bottom: 1px solid {border}; font-weight: 500; }}
      QMenu {{ background: {card}; border: 1px solid {border}; padding: 6px; }}
      QMenu::item {{ padding: 8px 22px; border-radius: 4px; }}
      QMenu::item:selected {{ background: {border}; }}
      QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; }}
      QStatusBar {{ color: {muted}; background: {side}; }}
    ''')


def translate_standard_controls(app, language):
    from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale
    previous = getattr(app, '_horas_translator', None)
    if previous:
        app.removeTranslator(previous)
    locale = 'pt_BR' if language == 'pt' else 'en_US'
    QLocale.setDefault(QLocale(locale))
    translator = QTranslator(app)
    if translator.load('qtbase_' + locale, QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    app._horas_translator = translator

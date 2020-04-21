#!/usr/bin/env python
"""PyQt + Lean test"""
import sys
from pathlib import Path
from typing import Tuple

from PyQt5.QtWidgets import *
from PyQt5 import QtCore

from lean_client.qt_server import  QtLeanServer

UNSOLVED = 'tactic failed, there are unsolved goals'

def read_lean_template(file_name: str = 'template.lean') -> Tuple[int, str]:
    """Read a template Lean file containing a single sorry.
    Returns the line number of the sorry and the content where
    sorry is replaced by a string placeholder {}"""
    text = Path(file_name).read_text()
    nb = 0
    for line in text.split('\n'):
        nb += 1
        if 'sorry' in line:
            break
    return nb, text.replace('sorry', '{}')



class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        """The main window containing everything."""
        super().__init__(*args, **kwargs)
        self.init_ui()

        self.server = QtLeanServer()
        self.server.incoming_message.connect(self.handle_message)
        self.server.state_update.connect(self.update_state)
        self.server.is_ready.connect(self.handle_ready)
        self.server.error.connect(self.handle_error)

        self.proof_start, self.template = read_lean_template()
        self.lines = []
        self.update_file_content()

    def init_ui(self):
        """Setup user interface. All this could be done graphically in QtDesigner."""
        self.resize(800, 600)

        self.setWindowTitle("Lean Qt test")
        self.code_widget = QPlainTextEdit()
        self.code_widget.setReadOnly(True)
        self.state_widget = QPlainTextEdit()
        self.state_widget.setReadOnly(True)
        self.errors_widget = QPlainTextEdit()
        self.errors_widget.setReadOnly(True)

        self.input_widget = QLineEdit(self)
        self.input_widget.setPlaceholderText("Enter your command here")
        self.input_widget.returnPressed.connect(self.input_widget_validate)


        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        central_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(central_layout)
        main_layout.addLayout(right_layout)

        left_layout.addWidget(QLabel('Code'))
        left_layout.addWidget(self.code_widget)
        central_layout.addWidget(QLabel('Tactic state'))
        central_layout.addWidget(self.state_widget)
        central_layout.addWidget(self.input_widget)
        right_layout.addWidget(QLabel('Errors'))
        right_layout.addWidget(self.errors_widget)

        self.main_widget = QWidget()
        self.main_widget.setLayout(main_layout)
        self.setCentralWidget(self.main_widget)

        self.input_widget.setFocus()
        # Next line allows Ctrl-Z to work, see
        # overloaded method eventFilter
        self.input_widget.installEventFilter(self)

        undo_action = QAction('&Undo', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.setStatusTip('Undo line')
        undo_action.triggered.connect(self.undo)

        quit_action = QAction('&Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.setStatusTip('Exit application')
        quit_action.triggered.connect(self.quit)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Menu')
        fileMenu.addAction(undo_action)
        fileMenu.addAction(quit_action)

    def handle_error(self, err):
        """Called when Lean encounters an error."""

    def handle_ready(self):
        """Called when Lean is done compiling."""
        self.server.info('template.lean',
                line=self.proof_start + len(self.lines), col=0)

    def update_file_content(self):
        """Update the code widget and send content to Lean"""
        self.content = self.template.format('\n'.join(self.lines))
        self.code_widget.setPlainText(self.content)
        self.server.sync('template.lean', content=self.content)

    def input_widget_validate(self):
        """Called when user validates a command."""
        cmd = '  ' + self.input_widget.text().strip(' ,') + ','
        self.lines.append(cmd)
        self.update_file_content()
        cmd = self.input_widget.setText('')

    def handle_message(self):
        """Called each time our LeanServerQt emits the incoming_message signal."""

        #filter out messages saying we are not done yet.
        self.errors_widget.setPlainText('\n'.join(
            [str(msg.text) for msg in self.server.messages
               if not msg.text.startswith(UNSOLVED)]))

    def update_state(self):
        """Called each time our LeanServerQt emits the update_state signal."""
        self.state_widget.setPlainText(self.server.goal_state)

    def undo(self):
        """Called by the Undo action (from menu or Ctrl-Z). """
        self.lines = self.lines[:-1]
        self.update_file_content()

    def quit(self):
        """Called by the Quit action (from menu or Ctrl-Q). """
        self.server.kill()
        qApp.quit()

    def eventFilter(self, source, event):
        """Prevent the input intercepting Ctrl-Z"""
        if (event.type() == QtCore.QEvent.ShortcutOverride and
            event.modifiers() == QtCore.Qt.ControlModifier and
            event.key() == QtCore.Qt.Key_Z):
            return True
        return super().eventFilter(source, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()

from PyQt5.QtCore import QProcess, pyqtSignal, QObject
from PyQt5 import QtCore

from lean_client.commands import (parse_response, SyncRequest, InfoRequest,
        CurrentTasksResponse, InfoResponse, AllMessagesResponse, Severity)

class QtLeanServer(QObject):
    incoming_message = pyqtSignal()
    state_update = pyqtSignal()
    is_ready = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        """Interface to Lean compatible with the Qt event loop and signaling
        framework."""
        super().__init__()
        self.messages = []
        self.goal_state = ''
        self.is_busy = False
        self.current_tasks = []

        self.process = QProcess()
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.lean_reply)
        self.process.finished.connect(self.lean_finished)
        self.process.start('lean --server', QtCore.QIODevice.ReadWrite)
        self.process.waitForStarted()
        self.seq_num = 0

    def sync(self, file_name, content=None):
        """Send synchronisation query to Lean."""
        self.seq_num += 1
        req = SyncRequest(self.seq_num, file_name, content)
        self.process.write((req.to_json()+'\n').encode())
        self.is_busy = True

    def info(self, filename, line, col):
        """Send info query to Lean."""
        self.seq_num += 1
        req = InfoRequest(self.seq_num, filename, line, col)
        self.process.write((req.to_json()+'\n').encode())

    def lean_finished(self):
        pass

    def lean_reply(self):
        """Called when Lean outputs something."""
        data = self.process.readAllStandardOutput().data().decode()
        for line in data.strip().split('\n'):
            resp = parse_response(line)
            if isinstance(resp, InfoResponse):
                self.goal_state = resp.record.state
                self.state_update.emit()
            elif isinstance(resp, CurrentTasksResponse):
                self.current_tasks = resp.tasks
                if self.is_busy and not resp.is_running:
                    self.is_ready.emit()
                self.is_busy = resp.is_running
            elif isinstance(resp, AllMessagesResponse):
                self.messages = resp.msgs
                for msg in resp.msgs:
                    if msg.severity == Severity.error:
                        self.error.emit(msg.text)
                self.incoming_message.emit()

    def kill(self):
        self.process.kill()
        self.process.waitForFinished(2000)

# desktop_app/main_window.py

import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

from services.api_client import ApiClient
from ui.dashboard import DashboardWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("RigSafe AI — Control Room")
        self.setMinimumSize(1000, 700)

        self.api_client = ApiClient()
        self.dashboard = DashboardWidget()
        self._last_events_payload: list | None = None
        self._last_events_hash: str | None = None

        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.dashboard)

        self.setCentralWidget(central_widget)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(4000)
        self.refresh_timer.timeout.connect(self.refresh_events)
        self.refresh_timer.start()

        self.refresh_events()

    def refresh_events(self) -> None:
        events = self.api_client.get_correlated_events(limit=50)
        payload_hash = self._compute_payload_hash(events)
        if payload_hash != self._last_events_hash:
            self._last_events_payload = events
            self._last_events_hash = payload_hash
            self.dashboard.update_events(events)

    def _compute_payload_hash(self, events: list) -> str:
        normalized = json.dumps(events, sort_keys=True, default=str)
        return str(hash(normalized))

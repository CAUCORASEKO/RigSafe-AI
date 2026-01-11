from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
)

from services.api_client import ApiClient


class CorrelatedEventsWidget(QWidget):
    def __init__(self, api_client: ApiClient | None = None) -> None:
        super().__init__()

        self.api_client = api_client or ApiClient()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title = QLabel("Correlated Safety Events")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_events)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_button)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ["Timestamp", "Location", "Risk Level", "Signal Types", "Reason"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        layout.addLayout(header_layout)
        layout.addWidget(self.table)

        self.load_events()

    def load_events(self) -> None:
        events = self.api_client.get_correlated_events(limit=50)
        if self.api_client.last_error:
            QMessageBox.warning(
                self,
                "Backend Connection Error",
                self.api_client.last_error,
            )

        self.table.setRowCount(len(events))
        for row_index, event in enumerate(events):
            timestamp = self._format_timestamp(event.get("timestamp"))
            location = event.get("location", "")
            risk_level = event.get("correlated_risk_level", "")
            signal_types = ", ".join(event.get("involved_signal_types", []))
            reason = event.get("correlation_reason", "")

            self._set_item(row_index, 0, timestamp)
            self._set_item(row_index, 1, location)
            self._set_item(row_index, 2, risk_level)
            self._set_item(row_index, 3, signal_types)
            self._set_item(row_index, 4, reason)

    def _set_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, column, item)

    def _format_timestamp(self, value) -> str:
        if value is None:
            return ""
        return str(value).replace("T", " ")

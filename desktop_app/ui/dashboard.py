"""
Industrial dashboard widget for correlated safety events.

Design rationale:
The layout is dense, stable, and text-first to support rapid scanning,
traceability, and operator trust in a safety-critical control room.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from ui.styles import COLOR_RISK_ELEVATED, COLOR_RISK_HIGH, COLOR_RISK_NORMAL


class DashboardWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        title = QLabel("RigSafe AI Control Room Dashboard")
        title.setObjectName("DashboardTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            [
                "Timestamp",
                "Location",
                "Correlated Risk Level",
                "Involved Signal Types",
                "Correlation Reason",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        layout.addWidget(title)
        layout.addWidget(self.table)

    def update_events(self, events: list) -> None:
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

            self._apply_risk_color(row_index, risk_level)

    def _set_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, column, item)

    def _apply_risk_color(self, row: int, risk_level: str) -> None:
        normalized = (risk_level or "").lower()
        if normalized == "high":
            color = QColor(COLOR_RISK_HIGH)
        elif normalized == "elevated":
            color = QColor(COLOR_RISK_ELEVATED)
        else:
            color = QColor(COLOR_RISK_NORMAL)

        brush = QBrush(color)
        for column in range(self.table.columnCount()):
            item = self.table.item(row, column)
            if item is not None:
                item.setForeground(brush)

    def _format_timestamp(self, value) -> str:
        if value is None:
            return ""
        return str(value).replace("T", " ")

"""
Industrial control-room stylesheet for RigSafe AI.

Rationale:
This theme prioritizes legibility, high contrast, and visual stability to
support safety-critical monitoring without distraction or ambiguity.
"""

# Base palette: dark, neutral, and readable under low-light operations.
COLOR_BG_MAIN = "#0f1115"
COLOR_BG_PANEL = "#151923"
COLOR_BG_HEADER = "#1b202a"
COLOR_BORDER = "#2b303b"
COLOR_TEXT_PRIMARY = "#d6d9df"
COLOR_TEXT_MUTED = "#a9b0bb"
COLOR_BUTTON_BG = "#2a313d"
COLOR_BUTTON_BG_HOVER = "#343c49"
COLOR_BUTTON_BG_PRESSED = "#232a35"

# Semantic risk colors (dark, audit-friendly).
COLOR_RISK_HIGH = "#8B0000"
COLOR_RISK_ELEVATED = "#B8860B"
COLOR_RISK_NORMAL = "#6b6f78"


def get_app_stylesheet() -> str:
    # The stylesheet is intentionally static and deterministic for auditability.
    return f"""
    QMainWindow {{
        background-color: {COLOR_BG_MAIN};
        color: {COLOR_TEXT_PRIMARY};
        font-family: "Segoe UI", "Arial";
        font-size: 13px;
    }}
    QWidget {{
        background-color: {COLOR_BG_MAIN};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLabel {{
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLabel#DashboardTitle {{
        font-size: 22px;
        font-weight: 600;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLabel#SectionTitle {{
        font-size: 16px;
        font-weight: 600;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLabel#MutedText {{
        color: {COLOR_TEXT_MUTED};
    }}
    QLabel#RiskHigh {{
        color: {COLOR_RISK_HIGH};
        font-weight: 600;
    }}
    QLabel#RiskElevated {{
        color: {COLOR_RISK_ELEVATED};
        font-weight: 600;
    }}
    QLabel#RiskNormal {{
        color: {COLOR_RISK_NORMAL};
        font-weight: 600;
    }}
    QPushButton {{
        background-color: {COLOR_BUTTON_BG};
        color: {COLOR_TEXT_PRIMARY};
        padding: 6px 12px;
        border: 1px solid {COLOR_BORDER};
        border-radius: 2px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BUTTON_BG_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_BUTTON_BG_PRESSED};
    }}
    QTableWidget {{
        background-color: {COLOR_BG_PANEL};
        color: {COLOR_TEXT_PRIMARY};
        gridline-color: {COLOR_BORDER};
        border: 1px solid {COLOR_BORDER};
    }}
    QTableWidget::item {{
        padding: 6px;
    }}
    QHeaderView::section {{
        background-color: {COLOR_BG_HEADER};
        color: {COLOR_TEXT_PRIMARY};
        padding: 6px;
        border: 1px solid {COLOR_BORDER};
        font-size: 13px;
        font-weight: 600;
    }}
    QTableWidget::item:selected {{
        background-color: {COLOR_BG_HEADER};
        color: {COLOR_TEXT_PRIMARY};
    }}
    """

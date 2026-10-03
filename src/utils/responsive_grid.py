"""إعادة توزيع بطاقات الواجهة حسب العرض المتاح وحجم العرض."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QWidget


class ResponsiveGrid(QWidget):
    def __init__(self, max_columns=4, card_width=205, parent=None):
        super().__init__(parent)
        self._max_columns = max_columns
        self._card_width = card_width
        self._columns = 0
        self._cards = []
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

    def set_cards(self, cards):
        self._cards = list(cards)
        self._reflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self):
        columns = max(1, min(self._max_columns, (self.width() + 12) // (self._card_width + 12)))
        if columns == self._columns:
            return
        self._columns = columns
        for column in range(self._max_columns):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self._cards):
            self.grid.addWidget(card, index // columns, index % columns)

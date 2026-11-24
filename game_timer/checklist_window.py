from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from game_timer import APP_DISPLAY_NAME
from game_timer.checklist_model import Bucket, ChecklistItem, ChecklistModel
from game_timer.gifts import Gift

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #34495E; }
QLabel#title { font-size: 28px; font-weight: bold; }
QLabel#hint { font-size: 16px; color: #7F8C8D; }
QLabel#activeTitle { font-size: 32px; font-weight: bold; color: #1ABC9C; }
QLabel#section { font-size: 18px; font-weight: bold; color: #5D6D7E; }
QLabel#itemRow { font-size: 16px; }
QLabel#giftEmoji { font-size: 64px; }
QLabel#giftLabel { font-size: 20px; font-weight: bold; color: #1ABC9C; }
QLabel#doneCount { font-size: 16px; color: #7F8C8D; }
QPushButton {
    font-size: 18px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 14px;
    padding: 12px 16px; min-height: 36px;
}
QPushButton:hover { background: #3498DB; }
QPushButton#primary { background: #1ABC9C; font-size: 24px; min-height: 48px; }
QPushButton#primary:hover { background: #17A589; }
QPushButton#complete { background: #27AE60; font-size: 22px; }
QPushButton#complete:hover { background: #229954; }
QPushButton#secondary { background: #BDC3C7; }
QPushButton#secondary:hover { background: #A6ACAF; }
QPushButton#work { background: #5DADE2; }
QPushButton#link {
    background: transparent; color: #7F8C8D; font-size: 14px;
    font-weight: normal; text-decoration: underline; padding: 4px; min-height: 0;
}
QPushButton#tiny {
    font-size: 13px; font-weight: bold; padding: 6px 10px; min-height: 0;
    background: #AED6F1; color: #1B4F72;
}
QPushButton#tiny:hover { background: #85C1E9; }
QLineEdit {
    font-size: 18px; padding: 10px 12px; border: 2px solid #D5DBDB;
    border-radius: 12px; background: white; color: #2C3E50;
}
QWidget#activeCard {
    background: #E8F8F5; border: 2px solid #1ABC9C; border-radius: 18px;
}
"""


def _label(text: str, name: str = "") -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    return label


def _button(text: str, name: str = "") -> QPushButton:
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class ChecklistWindow(QWidget):
    home_requested = Signal()
    start_work_requested = Signal(str, object)  # item_id, minutes|None
    item_completed = Signal(str)  # item_id — controller awards sticker then celebrates
    finish_day_requested = Signal()

    def __init__(self, model: ChecklistModel):
        super().__init__()
        self.model = model
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} · 今日清單")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(680, 640)
        self._pending_summary = False
        self._summary_gift_count = 0

        self.stack = QStackedWidget()
        self.start_page = self._build_start_page()
        self.main_page = self._build_main_page()
        self.celebrate_page = self._build_celebrate_page()
        self.edit_page = self._build_edit_page()
        self.summary_page = self._build_summary_page()
        for page in (self.start_page, self.main_page, self.celebrate_page, self.edit_page, self.summary_page):
            self.stack.addWidget(page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def present(self, celebration: Gift | None = None) -> None:
        self.model.reload()
        if celebration is not None:
            self._show_celebration(celebration)
        elif not self.model.started:
            self.stack.setCurrentWidget(self.start_page)
        else:
            self._refresh_main()
            self.stack.setCurrentWidget(self.main_page)
        self.show()
        self.raise_()
        self.activateWindow()

    def show_celebration(self, gift: Gift, then_summary: bool = False, gift_count: int = 0) -> None:
        self._pending_summary = then_summary
        self._summary_gift_count = gift_count
        self._show_celebration(gift)

    # --- pages ---

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        start = _button("開始今天！", "primary")
        home = _button("回主頁", "link")
        edit = _button("先編輯清單／套用模板", "link")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(_label("今日清單", "title"))
        layout.addWidget(_label("一次只做一件事。準備好了就按下開始。", "hint"))
        layout.addSpacing(20)
        layout.addWidget(start)
        layout.addWidget(edit)
        layout.addStretch()
        layout.addWidget(home, alignment=Qt.AlignmentFlag.AlignLeft)
        start.clicked.connect(self._on_start_today)
        home.clicked.connect(self.home_requested.emit)
        edit.clicked.connect(self._show_edit)
        return page

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        self.active_card = QWidget()
        self.active_card.setObjectName("activeCard")
        self.active_title = _label("", "activeTitle")
        self.active_meta = _label("", "hint")
        complete = _button("完成了！", "complete")
        skip = _button("跳過（移到稍後）", "secondary")
        self.work_button = _button("用蕃茄鐘做", "work")
        active_btns = QVBoxLayout()
        active_btns.setSpacing(10)
        active_btns.addWidget(complete)
        active_btns.addWidget(self.work_button)
        active_btns.addWidget(skip)
        active_layout = QVBoxLayout(self.active_card)
        active_layout.setContentsMargins(20, 18, 20, 18)
        active_layout.setSpacing(10)
        active_layout.addWidget(self.active_title)
        active_layout.addWidget(self.active_meta)
        active_layout.addLayout(active_btns)

        self.empty_active = _label("「現在做」都完成囉！", "hint")

        self.now_list = QVBoxLayout()
        self.later_list = QVBoxLayout()
        self.done_label = _label("", "doneCount")

        scroll_inner = QWidget()
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setSpacing(8)
        scroll_layout.addWidget(_label("其餘「現在做」", "section"))
        scroll_layout.addLayout(self.now_list)
        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(_label("今天稍後", "section"))
        scroll_layout.addLayout(self.later_list)
        scroll_layout.addWidget(self.done_label)
        scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_inner)

        edit = _button("編輯／模板", "link")
        finish = _button("今天先這樣", "link")
        home = _button("回主頁", "link")
        footer = QHBoxLayout()
        footer.addWidget(home)
        footer.addStretch()
        footer.addWidget(edit)
        footer.addWidget(finish)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(12)
        layout.addWidget(_label("今日清單", "title"))
        layout.addWidget(self.active_card)
        layout.addWidget(self.empty_active)
        layout.addWidget(scroll, 1)
        layout.addLayout(footer)

        complete.clicked.connect(self._on_complete_active)
        skip.clicked.connect(self._on_skip_active)
        self.work_button.clicked.connect(self._on_start_work)
        edit.clicked.connect(self._show_edit)
        finish.clicked.connect(self.finish_day_requested.emit)
        home.clicked.connect(self.home_requested.emit)
        return page

    def _build_celebrate_page(self) -> QWidget:
        page = QWidget()
        self.cele_emoji = _label("", "giftEmoji")
        self.cele_label = _label("", "giftLabel")
        cont = _button("繼續", "primary")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.addStretch()
        layout.addWidget(_label("太棒了！", "title"))
        layout.addWidget(self.cele_emoji)
        layout.addWidget(self.cele_label)
        layout.addWidget(_label("又完成一件事，得到一張貼紙", "hint"))
        layout.addSpacing(16)
        layout.addWidget(cont)
        layout.addStretch()
        cont.clicked.connect(self._after_celebration)
        return page

    def _build_edit_page(self) -> QWidget:
        page = QWidget()
        self.edit_text = QLineEdit()
        self.edit_text.setPlaceholderText("要做的具體一步，例如：寫國語習作第 1～5 題")

        self.minutes_group = QButtonGroup(page)
        minutes_row = QHBoxLayout()
        for value, text in ((-1, "不計時"), (5, "5 分"), (10, "10 分"), (15, "15 分")):
            radio = QRadioButton(text)
            radio.setProperty("minutes_value", value)
            self.minutes_group.addButton(radio)
            minutes_row.addWidget(radio)
            if value == -1:
                radio.setChecked(True)

        self.bucket_group = QButtonGroup(page)
        bucket_row = QHBoxLayout()
        for value, text in (("now", "現在做"), ("later", "今天稍後")):
            radio = QRadioButton(text)
            radio.setProperty("bucket_value", value)
            self.bucket_group.addButton(radio)
            bucket_row.addWidget(radio)
            if value == "now":
                radio.setChecked(True)

        add = _button("新增項目", "primary")
        self.edit_items_host = QVBoxLayout()

        self.templates_host = QVBoxLayout()
        save_tpl = _button("把今日清單存成模板", "secondary")
        back = _button("回到清單", "link")

        scroll_inner = QWidget()
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.addWidget(_label("新增項目", "section"))
        scroll_layout.addWidget(self.edit_text)
        scroll_layout.addWidget(_label("建議分鐘", "hint"))
        scroll_layout.addLayout(minutes_row)
        scroll_layout.addWidget(_label("放在哪裡", "hint"))
        scroll_layout.addLayout(bucket_row)
        scroll_layout.addWidget(add)
        scroll_layout.addSpacing(12)
        scroll_layout.addWidget(_label("目前項目", "section"))
        scroll_layout.addLayout(self.edit_items_host)
        scroll_layout.addSpacing(12)
        scroll_layout.addWidget(_label("模板", "section"))
        scroll_layout.addLayout(self.templates_host)
        scroll_layout.addWidget(save_tpl)
        scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_inner)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.addWidget(_label("編輯清單", "title"))
        layout.addWidget(scroll, 1)
        layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignLeft)

        add.clicked.connect(self._on_add_item)
        save_tpl.clicked.connect(self._on_save_template)
        back.clicked.connect(self._back_from_edit)
        return page

    def _build_summary_page(self) -> QWidget:
        page = QWidget()
        self.summary_done = _label("", "title")
        self.summary_gifts = _label("", "hint")
        home = _button("回主頁", "primary")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.addStretch()
        layout.addWidget(_label("今天先到這裡", "title"))
        layout.addWidget(self.summary_done)
        layout.addWidget(self.summary_gifts)
        layout.addSpacing(20)
        layout.addWidget(home)
        layout.addStretch()
        home.clicked.connect(self.home_requested.emit)
        return page

    # --- refresh helpers ---

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_main(self) -> None:
        active = self.model.active_item()
        if active is None:
            self.active_card.hide()
            self.empty_active.show()
            if self.model.all_now_done() and self.model.now_items(include_done=True):
                self.empty_active.setText("「現在做」都完成囉！可以按「今天先這樣」看回顧。")
            elif not self.model.items:
                self.empty_active.setText("還沒有項目。按下方「編輯／模板」加一些吧。")
            else:
                self.empty_active.setText("現在沒有「現在做」的項目。可以把「稍後」移過來。")
        else:
            self.empty_active.hide()
            self.active_card.show()
            self.active_title.setText(active.text)
            if active.minutes:
                self.active_meta.setText(f"建議大約 {active.minutes} 分鐘")
                self.work_button.setText(f"用蕃茄鐘做（{active.minutes} 分）")
            else:
                self.active_meta.setText("想計時的話，可以打開蕃茄鐘")
                self.work_button.setText("用蕃茄鐘做")

        self._clear_layout(self.now_list)
        active_id = active.id if active else None
        for item in self.model.now_items():
            if item.id == active_id:
                continue
            self.now_list.addWidget(self._row_widget(item, show_order=True))

        self._clear_layout(self.later_list)
        for item in self.model.later_items():
            self.later_list.addWidget(self._row_widget(item, show_order=False))

        done_n = self.model.done_count()
        self.done_label.setText(f"已完成 {done_n} 項" if done_n else "")

    def _row_widget(self, item: ChecklistItem, show_order: bool) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        text = QLabel(item.text + (f"（{item.minutes} 分）" if item.minutes else ""))
        text.setObjectName("itemRow")
        text.setWordWrap(True)
        layout.addWidget(text, 1)
        if show_order:
            up = _button("上", "tiny")
            down = _button("下", "tiny")
            up.clicked.connect(lambda: self._move_order(item.id, -1))
            down.clicked.connect(lambda: self._move_order(item.id, 1))
            layout.addWidget(up)
            layout.addWidget(down)
        if item.bucket == "now":
            move = _button("→稍後", "tiny")
            move.clicked.connect(lambda: self._move_bucket(item.id, "later"))
        else:
            move = _button("→現在", "tiny")
            move.clicked.connect(lambda: self._move_bucket(item.id, "now"))
        layout.addWidget(move)
        return row

    def _refresh_edit(self) -> None:
        self._clear_layout(self.edit_items_host)
        for item in self.model.items:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 2, 0, 2)
            status = "✓ " if item.done else ""
            where = "現在" if item.bucket == "now" else "稍後"
            label = QLabel(f"{status}{item.text}（{where}" + (f"·{item.minutes}分" if item.minutes else "") + "）")
            label.setWordWrap(True)
            layout.addWidget(label, 1)
            if not item.done:
                if item.bucket == "now":
                    swap = _button("→稍後", "tiny")
                    swap.clicked.connect(lambda _=False, i=item.id: self._move_bucket(i, "later"))
                else:
                    swap = _button("→現在", "tiny")
                    swap.clicked.connect(lambda _=False, i=item.id: self._move_bucket(i, "now"))
                layout.addWidget(swap)
            delete = _button("刪", "tiny")
            delete.clicked.connect(lambda _=False, i=item.id: self._delete_item(i))
            layout.addWidget(delete)
            self.edit_items_host.addWidget(row)

        self._clear_layout(self.templates_host)
        for tpl in self.model.templates():
            name = str(tpl.get("name", ""))
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 2, 0, 2)
            label = QLabel(name + ("（內建）" if tpl.get("builtin") else ""))
            layout.addWidget(label, 1)
            apply_btn = _button("套用", "tiny")
            apply_btn.clicked.connect(lambda _=False, n=name: self._apply_template(n))
            layout.addWidget(apply_btn)
            if not tpl.get("builtin"):
                del_btn = _button("刪模板", "tiny")
                del_btn.clicked.connect(lambda _=False, n=name: self._delete_template(n))
                layout.addWidget(del_btn)
            self.templates_host.addWidget(row)

    # --- actions ---

    def _on_start_today(self) -> None:
        self.model.start_today()
        self._refresh_main()
        self.stack.setCurrentWidget(self.main_page)

    def _on_complete_active(self) -> None:
        item = self.model.active_item()
        if item is None:
            return
        self.item_completed.emit(item.id)

    def complete_and_celebrate(self, item_id: str, gift: Gift, gift_count: int) -> None:
        self.model.mark_done(item_id)
        then_summary = self.model.all_now_done() and bool(self.model.now_items(include_done=True))
        self.show_celebration(gift, then_summary=then_summary, gift_count=gift_count)

    def _show_celebration(self, gift: Gift) -> None:
        self.cele_emoji.setText(gift.emoji)
        self.cele_label.setText(gift.label)
        self.stack.setCurrentWidget(self.celebrate_page)

    def _after_celebration(self) -> None:
        if self._pending_summary:
            self._pending_summary = False
            self._show_summary(self._summary_gift_count)
            return
        self._refresh_main()
        self.stack.setCurrentWidget(self.main_page)

    def _on_skip_active(self) -> None:
        self.model.skip_active()
        self._refresh_main()

    def _on_start_work(self) -> None:
        item = self.model.active_item()
        if item is None:
            return
        self.start_work_requested.emit(item.id, item.minutes)

    def _move_bucket(self, item_id: str, bucket: Bucket) -> None:
        self.model.move_bucket(item_id, bucket)
        if self.stack.currentWidget() is self.edit_page:
            self._refresh_edit()
        else:
            self._refresh_main()

    def _move_order(self, item_id: str, direction: int) -> None:
        self.model.move_now_order(item_id, direction)
        self._refresh_main()

    def _delete_item(self, item_id: str) -> None:
        self.model.delete_item(item_id)
        self._refresh_edit()

    def _selected_minutes(self) -> int | None:
        button = self.minutes_group.checkedButton()
        if button is None:
            return None
        value = button.property("minutes_value")
        if value is None or int(value) < 0:
            return None
        return int(value)

    def _selected_bucket(self) -> Bucket:
        button = self.bucket_group.checkedButton()
        if button is None:
            return "now"
        value = button.property("bucket_value")
        return "later" if value == "later" else "now"

    def _on_add_item(self) -> None:
        text = self.edit_text.text().strip()
        if not text:
            return
        self.model.add_item(text, self._selected_minutes(), self._selected_bucket())
        self.edit_text.clear()
        self._refresh_edit()

    def _show_edit(self) -> None:
        self._refresh_edit()
        self.stack.setCurrentWidget(self.edit_page)

    def _back_from_edit(self) -> None:
        if not self.model.started:
            self.stack.setCurrentWidget(self.start_page)
        else:
            self._refresh_main()
            self.stack.setCurrentWidget(self.main_page)

    def _apply_template(self, name: str) -> None:
        if self.model.items and any(not i.done for i in self.model.items):
            answer = QMessageBox.question(
                self,
                "套用模板",
                f"要用「{name}」覆蓋今天的清單嗎？未完成的項目會被換成模板內容。",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.model.apply_template(name)
        self._refresh_edit()

    def _on_save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "存成模板", "模板名稱：")
        if not ok or not name.strip():
            return
        self.model.save_as_template(name.strip())
        self._refresh_edit()

    def _delete_template(self, name: str) -> None:
        self.model.delete_template(name)
        self._refresh_edit()

    def _show_summary(self, gift_count: int) -> None:
        self.summary_done.setText(f"今天完成了 {self.model.done_count()} 項")
        self.summary_gifts.setText(f"這次收集了 {gift_count} 張貼紙")
        self.stack.setCurrentWidget(self.summary_page)

    def present_summary(self, gift_count: int) -> None:
        self.model.reload()
        self._show_summary(gift_count)
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        self.home_requested.emit()

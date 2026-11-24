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
QLabel { color: #2C3E50; font-size: 20px; }
QLabel#title { font-size: 32px; font-weight: bold; color: #2C3E50; }
QLabel#hero { font-size: 56px; }
QLabel#hint { font-size: 18px; color: #5D6D7E; }
QLabel#activeTitle { font-size: 34px; font-weight: bold; color: #148F77; }
QLabel#section { font-size: 22px; font-weight: bold; color: #2C3E50; }
QLabel#itemRow { font-size: 20px; color: #2C3E50; }
QLabel#giftEmoji { font-size: 72px; }
QLabel#giftLabel { font-size: 24px; font-weight: bold; color: #148F77; }
QLabel#doneCount { font-size: 18px; color: #5D6D7E; }
QPushButton {
    font-size: 20px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 14px;
    padding: 12px 16px; min-height: 44px;
}
QPushButton:hover { background: #3498DB; }
QPushButton#primary { background: #1ABC9C; font-size: 26px; min-height: 56px; }
QPushButton#primary:hover { background: #17A589; }
QPushButton#complete { background: #27AE60; font-size: 24px; }
QPushButton#complete:hover { background: #229954; }
QPushButton#secondary { background: #95A5A6; }
QPushButton#secondary:hover { background: #7F8C8D; }
QPushButton#work { background: #5DADE2; font-size: 22px; }
QPushButton#nav {
    background: #D6EAF8; color: #1A5276; font-size: 18px;
    min-height: 40px; padding: 10px 14px;
}
QPushButton#nav:hover { background: #AED6F1; }
QPushButton#choice {
    background: #F8F9F9; color: #2C3E50; border: 2px solid #D5DBDB;
    font-size: 20px; min-height: 48px;
}
QPushButton#choice:checked { background: #1ABC9C; color: white; border-color: #148F77; }
QPushButton#choice:hover { border-color: #5DADE2; }
QPushButton#iconBtn {
    font-size: 22px; font-weight: bold; padding: 8px;
    min-width: 48px; max-width: 48px; min-height: 48px;
    background: #D6EAF8; color: #1A5276; border-radius: 12px;
}
QPushButton#iconBtn:hover { background: #AED6F1; }
QPushButton#danger {
    font-size: 22px; padding: 8px;
    min-width: 48px; max-width: 48px; min-height: 48px;
    background: #F5B7B1; color: #922B21; border-radius: 12px;
}
QPushButton#danger:hover { background: #F1948A; }
QLineEdit {
    font-size: 22px; padding: 14px 16px; border: 2px solid #AEB6BF;
    border-radius: 12px; background: white; color: #2C3E50; min-height: 28px;
}
QLineEdit:focus { border-color: #5DADE2; }
QWidget#activeCard {
    background: #E8F8F5; border: 3px solid #1ABC9C; border-radius: 18px;
}
QWidget#listRow {
    background: #FFFFFF; border: 1px solid #D5DBDB; border-radius: 12px;
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
    start_work_requested = Signal(str, object)
    item_completed = Signal(str)
    finish_day_requested = Signal()

    def __init__(self, model: ChecklistModel):
        super().__init__()
        self.model = model
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} · 今日清單")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(720, 680)
        self._pending_summary = False
        self._summary_gift_count = 0
        self._minutes_value = -1
        self._bucket_value: Bucket = "now"

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

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        start = _button("✅ 開始", "primary")
        home = _button("🏠 主頁", "nav")
        edit = _button("✏️ 編輯", "nav")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(_label("✅", "hero"))
        layout.addWidget(_label("今日清單", "title"))
        layout.addWidget(_label("一次一件事", "hint"))
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
        complete = _button("✅ 完成", "complete")
        skip = _button("⏭️ 稍後", "secondary")
        self.work_button = _button("🍅 計時", "work")
        active_btns = QHBoxLayout()
        active_btns.setSpacing(10)
        active_btns.addWidget(complete, 2)
        active_btns.addWidget(self.work_button, 2)
        active_btns.addWidget(skip, 1)
        active_layout = QVBoxLayout(self.active_card)
        active_layout.setContentsMargins(20, 18, 20, 18)
        active_layout.setSpacing(12)
        active_layout.addWidget(self.active_title)
        active_layout.addWidget(self.active_meta)
        active_layout.addLayout(active_btns)

        self.empty_active = _label("🎉 都完成了", "hint")

        self.now_section = _label("⚡ 現在", "section")
        self.later_section = _label("🌙 稍後", "section")
        self.now_list = QVBoxLayout()
        self.later_list = QVBoxLayout()
        self.done_label = _label("", "doneCount")

        scroll_inner = QWidget()
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setSpacing(8)
        scroll_layout.addWidget(self.now_section)
        scroll_layout.addLayout(self.now_list)
        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(self.later_section)
        scroll_layout.addLayout(self.later_list)
        scroll_layout.addWidget(self.done_label)
        scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_inner)

        edit = _button("✏️ 編輯", "nav")
        finish = _button("🏁 結束", "nav")
        home = _button("🏠 主頁", "nav")
        footer = QHBoxLayout()
        footer.addWidget(home)
        footer.addStretch()
        footer.addWidget(edit)
        footer.addWidget(finish)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(12)
        layout.addWidget(_label("✅ 今日清單", "title"))
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
        cont = _button("👉 繼續", "primary")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.addStretch()
        layout.addWidget(_label("🎉 太棒了", "title"))
        layout.addWidget(self.cele_emoji)
        layout.addWidget(self.cele_label)
        layout.addWidget(_label("＋1 貼紙", "hint"))
        layout.addSpacing(16)
        layout.addWidget(cont)
        layout.addStretch()
        cont.clicked.connect(self._after_celebration)
        return page

    def _build_edit_page(self) -> QWidget:
        page = QWidget()
        self.edit_text = QLineEdit()
        self.edit_text.setPlaceholderText("具體一步，例如：寫國語 1～5 題")

        self.minutes_group = QButtonGroup(page)
        self.minutes_group.setExclusive(True)
        minutes_row = QHBoxLayout()
        minutes_row.setSpacing(8)
        for value, text in ((-1, "⏱️ —"), (5, "5"), (10, "10"), (15, "15")):
            button = _button(text, "choice")
            button.setCheckable(True)
            button.setProperty("minutes_value", value)
            self.minutes_group.addButton(button)
            minutes_row.addWidget(button)
            if value == -1:
                button.setChecked(True)
            button.clicked.connect(lambda _=False, v=value: self._set_minutes_choice(v))

        self.bucket_group = QButtonGroup(page)
        self.bucket_group.setExclusive(True)
        bucket_row = QHBoxLayout()
        bucket_row.setSpacing(8)
        for value, text in (("now", "⚡ 現在"), ("later", "🌙 稍後")):
            button = _button(text, "choice")
            button.setCheckable(True)
            button.setProperty("bucket_value", value)
            self.bucket_group.addButton(button)
            bucket_row.addWidget(button)
            if value == "now":
                button.setChecked(True)
            button.clicked.connect(lambda _=False, v=value: self._set_bucket_choice(v))

        add = _button("➕ 新增", "primary")
        self.edit_items_host = QVBoxLayout()
        self.templates_host = QVBoxLayout()
        save_tpl = _button("💾 存成模板", "secondary")
        back = _button("✅ 完成編輯", "nav")

        scroll_inner = QWidget()
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setSpacing(12)
        scroll_layout.addWidget(_label("➕ 新增", "section"))
        scroll_layout.addWidget(self.edit_text)
        scroll_layout.addWidget(_label("⏱️ 分鐘", "section"))
        scroll_layout.addLayout(minutes_row)
        scroll_layout.addWidget(_label("📂 放哪裡", "section"))
        scroll_layout.addLayout(bucket_row)
        scroll_layout.addWidget(add)
        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(_label("📋 項目", "section"))
        scroll_layout.addLayout(self.edit_items_host)
        scroll_layout.addSpacing(8)
        scroll_layout.addWidget(_label("📦 模板", "section"))
        scroll_layout.addLayout(self.templates_host)
        scroll_layout.addWidget(save_tpl)
        scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_inner)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.addWidget(_label("✏️ 編輯", "title"))
        layout.addWidget(scroll, 1)
        layout.addWidget(back)

        add.clicked.connect(self._on_add_item)
        save_tpl.clicked.connect(self._on_save_template)
        back.clicked.connect(self._back_from_edit)
        return page

    def _build_summary_page(self) -> QWidget:
        page = QWidget()
        self.summary_done = _label("", "title")
        self.summary_gifts = _label("", "hint")
        home = _button("🏠 主頁", "primary")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.addStretch()
        layout.addWidget(_label("🏁", "hero"))
        layout.addWidget(_label("今天先到這裡", "title"))
        layout.addWidget(self.summary_done)
        layout.addWidget(self.summary_gifts)
        layout.addSpacing(20)
        layout.addWidget(home)
        layout.addStretch()
        home.clicked.connect(self.home_requested.emit)
        return page

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
                self.empty_active.setText("🎉 現在都完成了")
            elif not self.model.items:
                self.empty_active.setText("📭 還沒有項目\n按 ✏️ 編輯 新增")
            else:
                self.empty_active.setText("⚡ 沒有「現在」\n把 🌙 稍後移過來")
        else:
            self.empty_active.hide()
            self.active_card.show()
            self.active_title.setText(active.text)
            if active.minutes:
                self.active_meta.setText(f"⏱️ 約 {active.minutes} 分")
                self.work_button.setText(f"🍅 {active.minutes}分")
            else:
                self.active_meta.setText("🍅 可開計時")
                self.work_button.setText("🍅 計時")

        self._clear_layout(self.now_list)
        active_id = active.id if active else None
        extras = [item for item in self.model.now_items() if item.id != active_id]
        self.now_section.setVisible(bool(extras))
        for item in extras:
            self.now_list.addWidget(self._row_widget(item, show_order=True))

        self._clear_layout(self.later_list)
        later = self.model.later_items()
        self.later_section.setVisible(bool(later))
        for item in later:
            self.later_list.addWidget(self._row_widget(item, show_order=False))

        done_n = self.model.done_count()
        self.done_label.setText(f"✔️ 已完成 {done_n}" if done_n else "")

    def _row_widget(self, item: ChecklistItem, show_order: bool) -> QWidget:
        row = QWidget()
        row.setObjectName("listRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 8, 8)
        text = QLabel(item.text + (f"  ⏱️{item.minutes}" if item.minutes else ""))
        text.setObjectName("itemRow")
        text.setWordWrap(True)
        layout.addWidget(text, 1)
        if show_order:
            up = _button("⬆️", "iconBtn")
            down = _button("⬇️", "iconBtn")
            up.clicked.connect(lambda: self._move_order(item.id, -1))
            down.clicked.connect(lambda: self._move_order(item.id, 1))
            layout.addWidget(up)
            layout.addWidget(down)
        if item.bucket == "now":
            move = _button("🌙", "iconBtn")
            move.setToolTip("移到稍後")
            move.clicked.connect(lambda: self._move_bucket(item.id, "later"))
        else:
            move = _button("⚡", "iconBtn")
            move.setToolTip("移到現在")
            move.clicked.connect(lambda: self._move_bucket(item.id, "now"))
        layout.addWidget(move)
        return row

    def _refresh_edit(self) -> None:
        self._clear_layout(self.edit_items_host)
        for item in self.model.items:
            row = QWidget()
            row.setObjectName("listRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 8, 8, 8)
            status = "✔️ " if item.done else ""
            where = "⚡" if item.bucket == "now" else "🌙"
            label = QLabel(
                f"{status}{item.text}  {where}" + (f" ⏱️{item.minutes}" if item.minutes else "")
            )
            label.setObjectName("itemRow")
            label.setWordWrap(True)
            layout.addWidget(label, 1)
            if not item.done:
                if item.bucket == "now":
                    swap = _button("🌙", "iconBtn")
                    swap.setToolTip("移到稍後")
                    swap.clicked.connect(lambda _=False, i=item.id: self._move_bucket(i, "later"))
                else:
                    swap = _button("⚡", "iconBtn")
                    swap.setToolTip("移到現在")
                    swap.clicked.connect(lambda _=False, i=item.id: self._move_bucket(i, "now"))
                layout.addWidget(swap)
            delete = _button("🗑️", "danger")
            delete.setToolTip("刪除")
            delete.clicked.connect(lambda _=False, i=item.id: self._delete_item(i))
            layout.addWidget(delete)
            self.edit_items_host.addWidget(row)

        self._clear_layout(self.templates_host)
        for tpl in self.model.templates():
            name = str(tpl.get("name", ""))
            row = QWidget()
            row.setObjectName("listRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 8, 8, 8)
            icon = "📌" if tpl.get("builtin") else "📦"
            label = QLabel(f"{icon} {name}")
            label.setObjectName("itemRow")
            layout.addWidget(label, 1)
            apply_btn = _button("▶️", "iconBtn")
            apply_btn.setToolTip("套用")
            apply_btn.clicked.connect(lambda _=False, n=name: self._apply_template(n))
            layout.addWidget(apply_btn)
            if not tpl.get("builtin"):
                del_btn = _button("🗑️", "danger")
                del_btn.setToolTip("刪模板")
                del_btn.clicked.connect(lambda _=False, n=name: self._delete_template(n))
                layout.addWidget(del_btn)
            self.templates_host.addWidget(row)

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

    def _set_minutes_choice(self, value: int) -> None:
        self._minutes_value = value

    def _set_bucket_choice(self, value: str) -> None:
        self._bucket_value = "later" if value == "later" else "now"

    def _selected_minutes(self) -> int | None:
        if self._minutes_value < 0:
            return None
        return self._minutes_value

    def _selected_bucket(self) -> Bucket:
        return self._bucket_value

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
                f"要用「{name}」覆蓋今天的清單嗎？",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.model.apply_template(name)
        self._refresh_edit()

    def _on_save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "存成模板", "名稱：")
        if not ok or not name.strip():
            return
        self.model.save_as_template(name.strip())
        self._refresh_edit()

    def _delete_template(self, name: str) -> None:
        self.model.delete_template(name)
        self._refresh_edit()

    def _show_summary(self, gift_count: int) -> None:
        self.summary_done.setText(f"✔️ 完成 {self.model.done_count()} 項")
        self.summary_gifts.setText(f"🎁 貼紙 {gift_count} 張")
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

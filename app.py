import json
import time
from pathlib import Path

import streamlit as st

STORAGE_FILE = Path(__file__).parent / "todo-items.json"

CATEGORY_LABELS = {"work": "업무", "personal": "개인", "etc": "기타"}
CATEGORY_COLORS = {
    "work": ("#dbeafe", "#1d4ed8"),
    "personal": ("#dcfce7", "#15803d"),
    "etc": ("#f3f4f6", "#6b7280"),
}
STATUS_FILTERS = [("all", "전체"), ("active", "진행중"), ("completed", "완료")]
CATEGORY_FILTERS = [("all", "전체"), ("work", "업무"), ("personal", "개인"), ("etc", "기타")]


# ---------------------------------------------------------------------------
# 데이터 계층: localStorage 대신 JSON 파일로 영속화
# ---------------------------------------------------------------------------
def load_todos():
    try:
        raw = json.loads(STORAGE_FILE.read_text(encoding="utf-8")) if STORAGE_FILE.exists() else []
    except Exception:
        return []

    # 이전 버전 데이터(category/createdAt 없음) 마이그레이션
    return [
        {
            "id": todo["id"],
            "text": todo["text"],
            "completed": bool(todo.get("completed", False)),
            "category": todo.get("category") or "etc",
            "createdAt": todo.get("createdAt") or todo["id"],
        }
        for todo in raw
    ]


def save_todos():
    STORAGE_FILE.write_text(
        json.dumps(st.session_state.todos, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 상태 변경 콜백
# ---------------------------------------------------------------------------
def add_todo():
    text = st.session_state.new_text.strip()
    if not text:
        return
    now_ms = int(time.time() * 1000)
    st.session_state.todos.append(
        {
            "id": now_ms,
            "text": text,
            "completed": False,
            "category": st.session_state.new_category,
            "createdAt": now_ms,
        }
    )
    save_todos()
    st.session_state.new_text = ""


def toggle_todo(todo_id):
    for todo in st.session_state.todos:
        if todo["id"] == todo_id:
            todo["completed"] = not todo["completed"]
            break
    save_todos()


def delete_todo(todo_id):
    st.session_state.todos = [t for t in st.session_state.todos if t["id"] != todo_id]
    save_todos()


def clear_completed():
    st.session_state.todos = [t for t in st.session_state.todos if not t["completed"]]
    save_todos()


def start_edit(todo_id):
    st.session_state.editing_id = todo_id


def save_edit(todo_id, input_key):
    trimmed = st.session_state[input_key].strip()
    if trimmed:
        for todo in st.session_state.todos:
            if todo["id"] == todo_id:
                todo["text"] = trimmed
                break
        save_todos()
    st.session_state.editing_id = None


def cancel_edit():
    st.session_state.editing_id = None


def set_status_filter(value):
    st.session_state.status_filter = value


def set_category_filter(value):
    st.session_state.category_filter = value


# ---------------------------------------------------------------------------
# 페이지 설정 및 초기 상태
# ---------------------------------------------------------------------------
st.set_page_config(page_title="To Do List", page_icon="✅", layout="centered")

st.session_state.setdefault("todos", load_todos())
st.session_state.setdefault("editing_id", None)
st.session_state.setdefault("status_filter", "all")
st.session_state.setdefault("category_filter", "all")

st.markdown(
    """
    <style>
    .stApp { background: #ffffff; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff; border-radius: 16px; padding: 8px;
        border: 1px solid #000000; box-shadow: none;
    }
    .todo-badge {
        font-size: 11px; padding: 2px 10px; border-radius: 999px;
        display: inline-block; white-space: nowrap; border: 1px solid #000000;
    }
    .todo-text-done { text-decoration: line-through; color: #4b4b4b; }
    .empty-message { text-align: center; color: #000000; padding: 24px 0; }
    .muted-text { color: #333333; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 레이아웃
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("<h1 style='text-align:center;margin-bottom:0;'>To Do List</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p class='muted-text' style='text-align:center;font-size:13px;'>{time.strftime('%Y년 %m월 %d일')}</p>",
        unsafe_allow_html=True,
    )

    with st.form("add-form", clear_on_submit=False, border=False):
        text_col, category_col, submit_col = st.columns([3, 1, 1])
        text_col.text_input(
            "할 일 내용", key="new_text", placeholder="할 일을 입력하세요", label_visibility="collapsed"
        )
        category_col.selectbox(
            "카테고리",
            options=list(CATEGORY_LABELS.keys()),
            format_func=lambda k: CATEGORY_LABELS[k],
            index=2,
            key="new_category",
            label_visibility="collapsed",
        )
        submit_col.form_submit_button("추가", on_click=add_todo, use_container_width=True)

    status_cols = st.columns(len(STATUS_FILTERS))
    for col, (value, label) in zip(status_cols, STATUS_FILTERS):
        col.button(
            label,
            key=f"status-{value}",
            on_click=set_status_filter,
            args=(value,),
            type="primary" if st.session_state.status_filter == value else "secondary",
            use_container_width=True,
        )

    category_cols = st.columns(len(CATEGORY_FILTERS))
    for col, (value, label) in zip(category_cols, CATEGORY_FILTERS):
        col.button(
            label,
            key=f"category-{value}",
            on_click=set_category_filter,
            args=(value,),
            type="primary" if st.session_state.category_filter == value else "secondary",
            use_container_width=True,
        )

    # 진행율은 필터와 무관하게 항상 전체 항목 기준으로 계산 (PRD 5.3)
    total = len(st.session_state.todos)
    completed_count = sum(1 for t in st.session_state.todos if t["completed"])
    percent = round((completed_count / total) * 100) if total else 0

    st.progress(percent / 100)
    progress_label = "할 일 없음" if total == 0 else f"{completed_count}/{total} 완료 ({percent}%)"
    st.markdown(
        f"<p class='muted-text' style='text-align:right;font-size:12px;'>{progress_label}</p>",
        unsafe_allow_html=True,
    )

    filtered = [
        todo
        for todo in st.session_state.todos
        if (
            st.session_state.status_filter == "all"
            or (st.session_state.status_filter == "active" and not todo["completed"])
            or (st.session_state.status_filter == "completed" and todo["completed"])
        )
        and (st.session_state.category_filter == "all" or todo["category"] == st.session_state.category_filter)
    ]

    st.divider()

    if not filtered:
        st.markdown("<p class='empty-message'>할 일이 없습니다</p>", unsafe_allow_html=True)
    else:
        for todo in filtered:
            badge_bg, badge_fg = CATEGORY_COLORS[todo["category"]]
            check_col, text_col, badge_col, edit_col, delete_col = st.columns([0.5, 5, 1.3, 0.6, 0.6])

            check_col.checkbox(
                "완료",
                value=todo["completed"],
                key=f"check-{todo['id']}",
                on_change=toggle_todo,
                args=(todo["id"],),
                label_visibility="collapsed",
            )

            if st.session_state.editing_id == todo["id"]:
                input_key = f"edit-{todo['id']}"
                text_col.text_input(
                    "수정",
                    value=todo["text"],
                    key=input_key,
                    on_change=save_edit,
                    args=(todo["id"], input_key),
                    label_visibility="collapsed",
                )
            else:
                text_class = "todo-text-done" if todo["completed"] else ""
                text_col.markdown(f"<span class='{text_class}'>{todo['text']}</span>", unsafe_allow_html=True)

            badge_col.markdown(
                f"<span class='todo-badge' style='background:{badge_bg};color:{badge_fg};'>"
                f"{CATEGORY_LABELS[todo['category']]}</span>",
                unsafe_allow_html=True,
            )

            if st.session_state.editing_id == todo["id"]:
                edit_col.button("취소", key=f"cancel-{todo['id']}", on_click=cancel_edit)
            else:
                edit_col.button("✏️", key=f"editbtn-{todo['id']}", on_click=start_edit, args=(todo["id"],))

            delete_col.button("✕", key=f"delete-{todo['id']}", on_click=delete_todo, args=(todo["id"],))

    st.divider()

    remaining_col, clear_col = st.columns([1, 1])
    remaining = sum(1 for todo in st.session_state.todos if not todo["completed"])
    remaining_col.markdown(f"<span class='muted-text' style='font-size:13px;'>{remaining}개 남음</span>", unsafe_allow_html=True)
    clear_col.button("완료된 항목 삭제", on_click=clear_completed, use_container_width=True)

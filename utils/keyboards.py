from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PRESET_PLATFORMS = ["LinkedIn", "Telegram", "HH.ru", "Glassdoor", "Djinni"]
PRESET_POSITIONS = [
    "Middle Python Developer",
    "Senior Python Developer",
    "Junior Python Developer",
    "Lead Python Developer",
]


def platform_kb(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for p in PRESET_PLATFORMS:
        tick = "✅ " if p in selected else ""
        rows.append([InlineKeyboardButton(f"{tick}{p}", callback_data=f"plt:{p}")])
    if selected:
        rows.append([InlineKeyboardButton("Continue →", callback_data="plt_done")])
    return InlineKeyboardMarkup(rows)


def position_kb(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for p in PRESET_POSITIONS:
        tick = "✅ " if p in selected else ""
        rows.append([InlineKeyboardButton(f"{tick}{p}", callback_data=f"pos:{p}")])
    rows.append([InlineKeyboardButton("✏️ Custom title…", callback_data="pos_custom")])
    if selected:
        rows.append([InlineKeyboardButton("Continue →", callback_data="pos_done")])
    return InlineKeyboardMarkup(rows)


def cv_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Skip", callback_data="cv_skip")],
    ])


def blacklist_kb(done: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if done:
        rows.append([InlineKeyboardButton("Done ✓", callback_data="bl_done")])
    else:
        rows.append([InlineKeyboardButton("Skip →", callback_data="bl_done")])
    return InlineKeyboardMarkup(rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Launch", callback_data="launch")],
        [
            InlineKeyboardButton("Edit platforms",  callback_data="edit_platforms"),
            InlineKeyboardButton("Edit positions",  callback_data="edit_positions"),
        ],
        [
            InlineKeyboardButton("Edit CV",         callback_data="edit_cv"),
            InlineKeyboardButton("Edit blacklist",  callback_data="edit_blacklist"),
        ],
    ])

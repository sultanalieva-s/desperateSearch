"""
handlers/setup.py — Multi-step configuration wizard.

Flow:
  /start
    → PLATFORM_SELECT  (inline keyboard — multi-select)
    → POSITION_SELECT  (inline keyboard + custom text option)
    → POSITION_CUSTOM  (free text, returns to POSITION_SELECT)
    → CV_UPLOAD        (PDF document or skip)
    → BLACKLIST_INPUT  (free text list or skip)
    → CONFIRM          (summary + launch / edit)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

from telegram import (
    CallbackQuery,
    Document,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from config import settings
from handlers.states import (
    BLACKLIST_INPUT, CONFIRM, CV_UPLOAD,
    PLATFORM_SELECT, POSITION_CUSTOM, POSITION_SELECT,
)
from utils.keyboards import (
    blacklist_kb, confirm_kb, cv_kb,
    platform_kb, position_kb,
)
from utils.storage import UserConfig, db

log = logging.getLogger(__name__)

PRESET_PLATFORMS = ["LinkedIn", "Telegram", "HH.ru", "Glassdoor", "Djinni"]
PRESET_POSITIONS = [
    "Middle Python Developer",
    "Senior Python Developer",
    "Junior Python Developer",
    "Lead Python Developer",
]


# ─── helpers ─────────────────────────────────────────────────────────────────

def _cfg(ctx: ContextTypes.DEFAULT_TYPE) -> dict:
    """Lazy-init wizard scratch-space in user_data."""
    ctx.user_data.setdefault("cfg", {
        "platforms":  [],
        "positions":  [],
        "cv_path":    None,
        "blacklist":  [],
    })
    return ctx.user_data["cfg"]


async def _edit_or_reply(update: Update, text: str, markup: InlineKeyboardMarkup) -> None:
    """Edit existing message if callback, otherwise send new."""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=markup, parse_mode=ParseMode.HTML
        )
    else:
        msg = cast(Message, update.effective_message)
        await msg.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)


# ─── SetupHandler ────────────────────────────────────────────────────────────

class SetupHandler:

    # ── /start ────────────────────────────────────────────────────────────────

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        ctx.user_data.pop("cfg", None)   # fresh run
        cfg = _cfg(ctx)
        await update.message.reply_text(
            "<b>Welcome to desperateSearch bot!</b>\n\n"
            "I'll scan job platforms, write tailored cover letters using your CV, "
            "and apply on your behalf.\n\n"
            "Let's configure your search.\n\n"
            "<b>Step 1/5</b> — Which platforms should I search?",
            parse_mode=ParseMode.HTML,
            reply_markup=platform_kb(cfg["platforms"]),
        )
        return PLATFORM_SELECT

    # ── PLATFORM_SELECT ───────────────────────────────────────────────────────

    async def cb_platform(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        platform = q.data.removeprefix("plt:")
        cfg = _cfg(ctx)

        if platform in cfg["platforms"]:
            cfg["platforms"].remove(platform)
        else:
            cfg["platforms"].append(platform)

        await q.edit_message_reply_markup(platform_kb(cfg["platforms"]))
        return PLATFORM_SELECT

    async def cb_platform_done(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        cfg = _cfg(ctx)

        if not cfg["platforms"]:
            await q.answer("Select at least one platform!", show_alert=True)
            return PLATFORM_SELECT

        await q.edit_message_text(
            f"✅ Platforms: <b>{', '.join(cfg['platforms'])}</b>\n\n"
            "<b>Step 2/5</b> — Select target job positions:",
            parse_mode=ParseMode.HTML,
            reply_markup=position_kb(cfg["positions"]),
        )
        return POSITION_SELECT

    # ── POSITION_SELECT ───────────────────────────────────────────────────────

    async def cb_position(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        pos = q.data.removeprefix("pos:")
        cfg = _cfg(ctx)

        if pos in cfg["positions"]:
            cfg["positions"].remove(pos)
        else:
            cfg["positions"].append(pos)

        await q.edit_message_reply_markup(position_kb(cfg["positions"]))
        return POSITION_SELECT

    async def cb_position_custom(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        await q.edit_message_text(
            "✏️ Type a custom position title and send it:\n"
            "<i>(e.g. «Python Backend Engineer»)</i>",
            parse_mode=ParseMode.HTML,
        )
        return POSITION_CUSTOM

    async def msg_position_custom(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        title = update.message.text.strip()
        cfg = _cfg(ctx)
        if title and title not in cfg["positions"]:
            cfg["positions"].append(title)

        await update.message.reply_text(
            f"✅ Added: <b>{title}</b>\n\n"
            "<b>Step 2/5</b> — Add more positions or continue:",
            parse_mode=ParseMode.HTML,
            reply_markup=position_kb(cfg["positions"]),
        )
        return POSITION_SELECT

    async def cb_position_done(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        cfg = _cfg(ctx)

        if not cfg["positions"]:
            await q.answer("Select at least one position!", show_alert=True)
            return POSITION_SELECT

        await q.edit_message_text(
            f"✅ Positions: <b>{', '.join(cfg['positions'])}</b>\n\n"
            "<b>Step 3/5</b> — Upload your CV (PDF) so I can write cover letters.\n"
            "You can skip this if you'd rather write them manually.",
            parse_mode=ParseMode.HTML,
            reply_markup=cv_kb(),
        )
        return CV_UPLOAD

    # ── CV_UPLOAD ─────────────────────────────────────────────────────────────

    async def msg_cv_upload(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        doc: Document = update.message.document
        cfg = _cfg(ctx)
        user_id = update.effective_user.id

        # Save PDF locally
        cv_path = settings.CV_DIR / f"{user_id}.pdf"
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(str(cv_path))
        cfg["cv_path"] = str(cv_path)

        await update.message.reply_text(
            f"📄 CV saved: <b>{doc.file_name}</b>\n\n"
            "<b>Step 4/5</b> — Any companies to <b>blacklist</b>?\n"
            "Send company names separated by commas or one per line.\n"
            "Example: <code>Sirius, Reviro, BadCorp</code>\n\n"
            "Or press <b>Skip</b> to continue.",
            parse_mode=ParseMode.HTML,
            reply_markup=blacklist_kb(),
        )
        return BLACKLIST_INPUT

    async def cb_cv_skip(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        await q.edit_message_text(
            "⏭ CV skipped — cover letters will be generic.\n\n"
            "<b>Step 4/5</b> — Any companies to <b>blacklist</b>?\n"
            "Send names separated by commas, or press Skip.",
            parse_mode=ParseMode.HTML,
            reply_markup=blacklist_kb(),
        )
        return BLACKLIST_INPUT

    # ── BLACKLIST_INPUT ───────────────────────────────────────────────────────

    async def msg_blacklist(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        raw = update.message.text
        cfg = _cfg(ctx)

        # Parse comma- or newline-separated list
        entries = [
            e.strip()
            for part in raw.replace("\n", ",").split(",")
            for e in [part.strip()]
            if e
        ]
        cfg["blacklist"].extend(e for e in entries if e not in cfg["blacklist"])

        await update.message.reply_text(
            f"🚫 Blacklisted: <b>{', '.join(cfg['blacklist'])}</b>\n\n"
            "Add more, or press <b>Done</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=blacklist_kb(done=True),
        )
        return BLACKLIST_INPUT

    async def cb_blacklist_done(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        cfg = _cfg(ctx)
        await q.edit_message_text(
            self._summary_text(cfg) + "\n\nReady to launch?",
            parse_mode=ParseMode.HTML,
            reply_markup=confirm_kb(),
        )
        return CONFIRM

    # ── CONFIRM ───────────────────────────────────────────────────────────────

    async def cb_confirm_launch(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer("🚀 Launching…")
        cfg = _cfg(ctx)
        user_id = update.effective_user.id

        # Persist config
        user_cfg = UserConfig(
            user_id=user_id,
            platforms=cfg["platforms"],
            positions=cfg["positions"],
            cv_path=cfg.get("cv_path"),
            blacklist=cfg["blacklist"],
            active=True,
        )
        db.save_config(user_cfg)

        #todo: start background agent

        await q.edit_message_text(
            "✅ <b>Agent launched!</b>\n\n"
            f"🔍 Scanning: {', '.join(cfg['platforms'])}\n"
            f"💼 Positions: {', '.join(cfg['positions'])}\n\n"
            "I'll message you whenever I find a new vacancy and when a cover letter is ready.\n\n"
            "<b>Commands:</b>\n"
            "/status — agent status\n"
            "/results — jobs found so far\n"
            "/pause — pause scanning\n"
            "/resume — resume scanning\n"
            "/help — this message",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    async def cb_confirm_edit(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        q: CallbackQuery = update.callback_query
        await q.answer()
        section = q.data.removeprefix("edit_")
        cfg = _cfg(ctx)

        if section == "platforms":
            await q.edit_message_text(
                "<b>Step 1/5</b> — Re-select platforms:",
                parse_mode=ParseMode.HTML,
                reply_markup=platform_kb(cfg["platforms"]),
            )
            return PLATFORM_SELECT

        if section == "positions":
            await q.edit_message_text(
                "<b>Step 2/5</b> — Re-select positions:",
                parse_mode=ParseMode.HTML,
                reply_markup=position_kb(cfg["positions"]),
            )
            return POSITION_SELECT

        if section == "cv":
            await q.edit_message_text(
                "<b>Step 3/5</b> — Re-upload your CV (PDF):",
                parse_mode=ParseMode.HTML,
                reply_markup=cv_kb(),
            )
            return CV_UPLOAD

        if section == "blacklist":
            await q.edit_message_text(
                f"Current blacklist: <b>{', '.join(cfg['blacklist']) or 'none'}</b>\n\n"
                "Send updated list (comma-separated) or press Done:",
                parse_mode=ParseMode.HTML,
                reply_markup=blacklist_kb(done=True),
            )
            return BLACKLIST_INPUT

        return CONFIRM

    # ── /cancel ───────────────────────────────────────────────────────────────

    async def cmd_cancel(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("❌ Setup cancelled. Send /start to begin again.")
        ctx.user_data.pop("cfg", None)
        return ConversationHandler.END

    # ── /help ─────────────────────────────────────────────────────────────────

    async def cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "<b>JobSearch Bot — Help</b>\n\n"
            "/start — (re)configure the agent\n"
            "/status — show agent status\n"
            "/results — list jobs found\n"
            "/pause — pause scanning\n"
            "/resume — resume scanning\n"
            "/cancel — abort current setup\n",
            parse_mode=ParseMode.HTML,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _summary_text(cfg: dict) -> str:
        bl = ", ".join(cfg["blacklist"]) if cfg["blacklist"] else "none"
        cv = Path(cfg["cv_path"]).name if cfg.get("cv_path") else "not uploaded"
        return (
            "📋 <b>Your configuration</b>\n\n"
            f"🌐 <b>Platforms:</b> {', '.join(cfg['platforms'])}\n"
            f"💼 <b>Positions:</b> {', '.join(cfg['positions'])}\n"
            f"📄 <b>CV:</b> {cv}\n"
            f"🚫 <b>Blacklist:</b> {bl}"
        )

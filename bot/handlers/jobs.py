"""handlers/jobs.py — Runtime commands: /status /pause /resume /results."""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db

log = logging.getLogger(__name__)


class JobsHandler:

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        cfg = db.load_config(uid)
        if not cfg:
            await update.message.reply_text("No active config. Run /start to set up.")
            return

        jobs = db.get_jobs(uid)
        applied = sum(1 for j in jobs if j["status"] == "applied")
        pending = sum(1 for j in jobs if j["status"] == "pending")
        state = "▶️ Running" if cfg.active else "⏸ Paused"

        await update.message.reply_text(
            f"<b>Agent Status</b>\n\n"
            f"State: {state}\n"
            f"Platforms: {', '.join(cfg.platforms)}\n"
            f"Positions: {', '.join(cfg.positions)}\n"
            f"Jobs found: {len(jobs)}\n"
            f"Applied: {applied}\n"
            f"Pending: {pending}",
            parse_mode=ParseMode.HTML,
        )

    async def cmd_pause(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        cfg = db.load_config(uid)
        if not cfg:
            await update.message.reply_text("No active config. Run /start first.")
            return
        cfg.active = False
        db.save_config(cfg)
        await update.message.reply_text("⏸ Agent paused. Send /resume to continue.")

    async def cmd_resume(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        cfg = db.load_config(uid)
        if not cfg:
            await update.message.reply_text("No active config. Run /start first.")
            return
        cfg.active = True
        db.save_config(cfg)
        # todo: Re-launch agent

        await update.message.reply_text("▶️ Agent resumed.")

    async def cmd_results(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        jobs = db.get_jobs(uid, limit=10)
        if not jobs:
            await update.message.reply_text("No jobs found yet. The agent is still scanning.")
            return

        lines = ["<b>Latest jobs found:</b>\n"]
        for j in jobs:
            status_icon = {"applied": "✅", "pending": "🕐", "skipped": "⛔"}.get(j["status"], "•")
            lines.append(
                f"{status_icon} <a href='{j['url']}'>{j['title']}</a>\n"
                f"   <i>{j['company']} — {j['platform']}</i>"
            )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

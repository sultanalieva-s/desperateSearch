import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from config import settings
from handlers.setup import SetupHandler
from handlers.jobs import JobsHandler
from handlers.states import (
    PLATFORM_SELECT, POSITION_SELECT, POSITION_CUSTOM,
    CV_UPLOAD, BLACKLIST_INPUT, CONFIRM,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("bot")


def main() -> None:
    app = Application.builder().token(settings.TELEGRAM_TOKEN).build()

    setup = SetupHandler()
    jobs  = JobsHandler()

    # ── Conversation: /start wizard ──────────────────────────────────────────
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", setup.cmd_start)],
        states={
            PLATFORM_SELECT: [
                CallbackQueryHandler(setup.cb_platform, pattern=r"^plt:"),
                CallbackQueryHandler(setup.cb_platform_done, pattern=r"^plt_done$"),
            ],
            POSITION_SELECT: [
                CallbackQueryHandler(setup.cb_position, pattern=r"^pos:"),
                CallbackQueryHandler(setup.cb_position_custom, pattern=r"^pos_custom$"),
                CallbackQueryHandler(setup.cb_position_done, pattern=r"^pos_done$"),
            ],
            POSITION_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, setup.msg_position_custom),
            ],
            CV_UPLOAD: [
                MessageHandler(filters.Document.PDF, setup.msg_cv_upload),
                CallbackQueryHandler(setup.cb_cv_skip, pattern=r"^cv_skip$"),
            ],
            BLACKLIST_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, setup.msg_blacklist),
                CallbackQueryHandler(setup.cb_blacklist_done, pattern=r"^bl_done$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(setup.cb_confirm_launch, pattern=r"^launch$"),
                CallbackQueryHandler(setup.cb_confirm_edit,   pattern=r"^edit_(\w+)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", setup.cmd_cancel)],
        allow_reentry=True,
        name="setup",
        persistent=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("status",  jobs.cmd_status))
    app.add_handler(CommandHandler("pause",   jobs.cmd_pause))
    app.add_handler(CommandHandler("resume",  jobs.cmd_resume))
    app.add_handler(CommandHandler("results", jobs.cmd_results))
    app.add_handler(CommandHandler("help",    setup.cmd_help))

    log.info("Bot is running — press Ctrl-C to stop")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

import logging
import os

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.helpers import create_deep_linked_url
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler("logs.log")],
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == ChatType.PRIVATE:
        bot = await context.bot.get_me()
        await update.message.reply_text(
            "I'm online! I'll place landmines in any group; try adding me in one!",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    "➕ Add me to a group",
                    url=create_deep_linked_url(bot.username, "start", group=True),
                )
            ),
        )
    else:
        await update.message.reply_text(
            "I'm online! I'll place landmines in this group; try not to step on one when sending a message!\n"
            "\n"
            "Use /place to place some landmines\n"
            "Use /settings to tweak how rare the landmines are and the punishment for stepping on one"
        )


def main():
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    application.add_handler(CommandHandler("start", start))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

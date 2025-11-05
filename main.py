import logging
import os
import random
from typing import Literal

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.helpers import create_deep_linked_url
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    ExtBot,
    PicklePersistence,
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


class ChatData:
    def __init__(self):
        self.placed_mines = 0

        self.punishment: Literal["NONE", "BAN", "MUTE"] = "NONE"
        self.punishment_time_minutes = 15
        self.infinite_mines = False
        self.mines_frequence: Literal["RARE", "OCCASIONAL", "COMMON"] = "OCCASIONAL"

    def landed_on_mine(self):
        num_mines = self.placed_mines if not self.infinite_mines else 100
        if num_mines <= 0:
            return False
        if self.mines_frequence == "COMMON":
            base_probability = 900
        elif self.mines_frequence == "OCCASIONAL":
            base_probability = 9900
        elif self.mines_frequence == "RARE":
            base_probability = 99900
        else:
            raise ValueError(
                "Incorrect value for 'mines_frequence': " + self.mines_frequence
            )
        probability = num_mines / (num_mines + base_probability)
        return random.random() < probability


ContextType = CallbackContext[ExtBot, dict, ChatData, dict]


async def start(update: Update, context: ContextType):
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
    application = (
        Application.builder()
        .token(os.environ["BOT_TOKEN"])
        .context_types(ContextTypes(chat_data=ChatData))
        .persistence(PicklePersistence("persistence.pickle"))
        .concurrent_updates(True)
        .build()
    )

    application.add_handler(CommandHandler("start", start))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

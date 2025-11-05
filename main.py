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


async def is_admin(update: Update) -> bool:
    return update.effective_user.id in (
        admin.user.id for admin in await update.effective_chat.get_administrators()
    )


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


def get_settings(user_id: int, context: ContextType):
    def button(text: str, data=""):
        return InlineKeyboardButton(text, callback_data=f"{user_id}_{data}")

    punishment_time = (
        f"{context.chat_data.punishment_time_minutes}m"
        if context.chat_data.punishment_time_minutes < 60
        else f"{context.chat_data.punishment_time_minutes / 60}h"
    )
    return (
        "Settings:\n"
        "\n"
        f"Current punishment: <b>{context.chat_data.punishment}</b>\n"
        f"Punishment time: <b>{punishment_time}</b>\n"
        f"Infinite mines: <b>{context.chat_data.infinite_mines}</b>\n"
        f"Mines frequence: <b>{context.chat_data.mines_frequence}</b>\n"
        f"Placed mines: <b>{context.chat_data.placed_mines}</b>",
        InlineKeyboardMarkup(
            [
                [button("⚒️ Punishment")],
                [
                    button(
                        ("✅" if context.chat_data.punishment == "NONE" else "☑️")
                        + " None",
                        "punishment_NONE",
                    ),
                    button(
                        ("✅" if context.chat_data.punishment == "BAN" else "☑️")
                        + " Ban",
                        "punishment_BAN",
                    ),
                    button(
                        ("✅" if context.chat_data.punishment == "MUTE" else "☑️")
                        + " Mute",
                        "punishment_MUTE",
                    ),
                ],
                [button("⏳ Punishment Time")],
                [
                    button("➖ Less time", "time_less"),
                    button("➕ More time", "time_more"),
                ],
                [
                    button(
                        ("✅" if context.chat_data.infinite_mines else "☑️")
                        + " Infinite mines",
                        "infinitemines",
                    )
                ],
                [button("💣 Mines frequence")],
                [
                    button(
                        ("✅" if context.chat_data.mines_frequence == "RARE" else "☑️")
                        + " Rare",
                        "frequence_RARE",
                    ),
                    button(
                        (
                            "✅"
                            if context.chat_data.mines_frequence == "OCCASIONAL"
                            else "☑️"
                        )
                        + " Occasional",
                        "frequence_OCCASIONAL",
                    ),
                    button(
                        ("✅" if context.chat_data.mines_frequence == "COMMON" else "☑️")
                        + " Common",
                        "frequence_COMMON",
                    ),
                ],
                [button("❌ Remove all mines", "removeall")],
            ]
        ),
    )


async def settings(update: Update, context: ContextType):
    if await is_admin(update):
        text, reply_markup = get_settings(update.effective_user.id, context)
        await update.message.reply_html(
            text,
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            "Sorry, you're not allowed to use this command."
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
    application.add_handler(CommandHandler("settings", settings))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

from datetime import datetime
import logging
import os
import random
from typing import Literal, cast

from telegram import ChatPermissions, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.helpers import create_deep_linked_url
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    ExtBot,
    PicklePersistence,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest
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
        else f"{context.chat_data.punishment_time_minutes // 60}h"
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


async def settings_button(update: Update, context: ContextType):
    query = update.callback_query.data.split("_")
    if update.effective_user.id != int(query[0]):
        await update.callback_query.answer("This is not for you.")
        return
    await update.callback_query.answer()
    match query[1]:
        case "punishment":
            context.chat_data.punishment = cast(
                Literal["NONE", "BAN", "MUTE"], query[2]
            )
        case "time":
            if query[2] == "less" and context.chat_data.punishment_time_minutes > 15:
                context.chat_data.punishment_time_minutes //= 2
            elif query[2] == "more":
                context.chat_data.punishment_time_minutes *= 2
        case "infinitemines":
            context.chat_data.infinite_mines ^= True
        case "frequence":
            context.chat_data.mines_frequence = cast(
                Literal["RARE", "OCCASIONAL", "COMMON"], query[2]
            )
        case "removeall":
            context.chat_data.placed_mines = 0
    try:
        text, reply_markup = get_settings(update.effective_user.id, context)

        await update.effective_message.edit_text(text, "HTML", reply_markup)
    except BadRequest:
        pass


async def mine_check(update: Update, context: ContextType):
    if context.chat_data.landed_on_mine():
        message = f"💥 {update.effective_user.name} stepped on a landmine"

        punishment_time = (
            f"{context.chat_data.punishment_time_minutes}m"
            if context.chat_data.punishment_time_minutes < 60
            else f"{context.chat_data.punishment_time_minutes // 60}h"
        )

        if context.chat_data.punishment == "MUTE":
            try:
                await update.effective_chat.restrict_member(
                    update.effective_user.id,
                    ChatPermissions.no_permissions(),
                    until_date=(
                        datetime.now().timestamp()
                        + context.chat_data.punishment_time_minutes * 60
                    ),
                )
                message += f" and has been muted for {punishment_time}"
            except BadRequest:
                pass
        elif context.chat_data.punishment == "BAN":
            try:
                await update.effective_chat.ban_member(
                    update.effective_user.id,
                    until_date=(
                        datetime.now().timestamp()
                        + context.chat_data.punishment_time_minutes * 60
                    ),
                )
                message += f" and has been banned for {punishment_time}"
            except BadRequest:
                pass

        message += "!"

        if not context.chat_data.infinite_mines:
            context.chat_data.placed_mines -= 1
            message += f" ({context.chat_data.placed_mines} landmine(s) remaining)"
        await update.effective_chat.send_message(message)


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
    application.add_handler(CallbackQueryHandler(settings_button))
    application.add_handler(MessageHandler(filters.USER, mine_check))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

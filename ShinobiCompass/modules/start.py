import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CallbackContext,
    ContextTypes,
    filters,
)

# Command: /start
async def start(update: Update, context: CallbackContext) -> None:
    username = update.message.from_user.username or "User"

    if update.message.chat.type == 'private':
        # For private chats, show the "Add Me to Group" button
        buttons = [
            [
                InlineKeyboardButton("➕ Add Me to Group", url="https://t.me/ShinobiCompassBot?startgroup=true"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        intro_text = (
            f"👋 Hello, <b>{username}</b>!\n\n"
            "🤖 <b>Welcome to Black Market Analysis Bot!</b>\n\n"
            "📌 <b>About the Bot:</b>\n"
            "I specialize in analyzing black market messages to identify <b>profitable deals</b>, saving you time and maximizing your resources.\n\n"
            "🛠 <b>Key Features:</b>\n"
            " - Automatically detects and analyzes black market messages in <b>groups</b> and <b>private chats</b>.\n"
            " - Identifies <b>profitable deals</b> using pre-set pricing logic.\n"
            " - Provides <b>clear and detailed analysis reports</b>.\n\n"
            "🗂 <b>Commands:</b>\n"
            "1️⃣ <b>/start</b> - Introduces the bot and guides you to get started.\n"
            "2️⃣ <b>/bm</b> - Manually analyze a black market message by replying to it.\n\n"
        )
    else:
        # Check if the bot is an admin and has required rights in the group
        chat = update.message.chat
        bot = await chat.get_member(context.bot.id)  # Use context.bot.id instead of update.message.bot.id

        if bot.status != 'administrator':
            # If the bot is not an admin, notify the user in the group
            await update.message.reply_text(
                "⚠️ The bot needs to be an admin in this group to function properly. Please make sure it has the required permissions."
            )
            return

        # Check the bot's privileges
        if not bot.can_manage_chat or not bot.can_delete_messages:
            # If any of the required permissions are missing
            await update.message.reply_text(
                "⚠️ The bot is missing some required admin rights in this group."
                " Please update the permissions."
            )
            return

        # If the bot has all required rights
        reply_markup = None  # No buttons for groups
        intro_text = (
            f"👋 Hello, <b>{username}</b>!\n\n"
            "🤖 <b>Welcome to Black Market Analysis Bot!</b>\n\n"
            "📌 <b>About the Bot:</b>\n"
            "I specialize in analyzing black market messages to identify <b>profitable deals</b> in your groups, saving you time and maximizing your resources.\n\n"
            "🛠 <b>Key Features:</b>\n"
            " - Automatically detects and analyzes black market messages in <b>groups</b>.\n"
            " - Identifies <b>profitable deals</b> using pre-set pricing logic.\n"
            " - Provides <b>clear and detailed analysis reports</b>.\n\n"
            "🗂 <b>Commands:</b>\n"
            "1️⃣ <b>/start</b> - Introduces the bot and guides you to get started.\n"
            "2️⃣ <b>/bm</b> - Manually analyze a black market message by replying to it.\n\n"
        )

    await update.message.reply_text(
        intro_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Callback query handlers for scenarios
async def handle_callback_query(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "group_scenario":
        await query.edit_message_text(
            "📍 <b>Using the Bot in Groups:</b>\n\n"
            "1️⃣ Add me to your group using the <b>Add Me to Group</b> button.\n"
            "2️⃣ Ensure I have message-reading permissions.\n"
            "3️⃣ I will monitor messages and automatically analyze any black market listings.\n"
            "4️⃣ Use <b>/bm</b> on a replied message for manual analysis.\n\n"
            "🌟 <b>Start finding profitable deals with ease in your groups!</b>",
            parse_mode="HTML"
        )
    elif query.data == "pm_scenario":
        await query.edit_message_text(
            "📍 <b>Using the Bot in Private Messages:</b>\n\n"
            "1️⃣ Forward a black market message to me or use <b>/bm</b> on a replied message.\n"
            "2️⃣ I’ll analyze the message and provide a detailed profit analysis report.\n\n"
            "🌟 <b>Enjoy private, personalized black market analysis!</b>",
            parse_mode="HTML"
        )

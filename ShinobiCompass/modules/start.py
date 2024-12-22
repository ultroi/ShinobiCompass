import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAdministratorRights
from telegram.ext import (
    CallbackQueryHandler,
    CallbackContext,
    ContextTypes,
    filters,
)

# Command: /start
async def start(update: Update, _: CallbackContext) -> None:
    username = update.message.from_user.username or "User"

    if update.message.chat.type == 'private':
        # For private chats, show the "Add Me to Group" button
        buttons = [
            [
                InlineKeyboardButton("➕ Add Me to Group", url="https://t.me/HelpClanOT_bot?startgroup=true"),
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
            "🌐 <b>How It Works:</b>\n"
            "Click the button below to add the bot to your group and automate black market analysis.\n\n"
            "👇 <b>Use the button below:</b>"
        )
    else:
        # Check if the bot is an admin and has required rights in the group
        chat = update.message.chat
        bot = await chat.get_member(update.message.bot.id)

        if not bot.is_chat_admin():
            # If bot is not an admin, notify the user in the group
            await update.message.reply_text(
                "⚠️ The bot needs to be an admin in this group to function properly. Please make sure it has the required permissions."
            )
            return

        # Required rights for the bot to function properly in a group
        required_rights = ChatAdministratorRights(
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_manage_video_chats=True,
            can_invite_users=True,
            can_post_messages=True,
        )

        if not bot.privileges.can_manage_chat or not bot.privileges.can_delete_messages:
            # If any of the required permissions are missing
            await update.message.reply_text(
                "⚠️ The bot is missing some required admin rights in this group. It needs the following permissions: "
                "Manage Chat, Delete Messages. Please update the permissions."
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
            "🌐 <b>How It Works:</b>\n"
            "The bot will automatically analyze black market messages in your group. You can also use <b>/bm</b> on a specific message for manual analysis."
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
            "1️⃣ Add me to your group.\n"
            "2️⃣ I will monitor messages and automatically analyze any black market listings.\n"
            "3️⃣ Use <b>/bm</b> on a replied message for manual analysis.\n\n"
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

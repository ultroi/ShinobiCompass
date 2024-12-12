import logging
from modules.start import start
from modules.bm import bm, handle_callback_query, handle_message
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# Main function
def main() -> None:
    bot_token = "7866673972:AAFSczpid7J-1vAANUfFgKkq0pxaz-Rc9oA"
    application = ApplicationBuilder().token(bot_token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bm", bm))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()

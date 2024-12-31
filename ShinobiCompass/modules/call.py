from ShinobiCompass.modules.sudo import is_owner_or_sudo
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext


async def reply(update: Update, context: CallbackContext) -> None:
    # Check if the user has permission to execute the command
    user = update.effective_user
    if not is_owner_or_sudo(user.id):
        await update.message.reply_text('You do not have permission to use this command.')
        return

    # Ensure the command has the correct number of arguments
    if len(context.args) < 2:
        await update.message.reply_text('Usage: /reply <user_id> <message>')
        return

    # Extract user_id and the reply message
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text('Invalid user ID. It must be a numeric value.')
        return

    reply_message = ' '.join(context.args[1:])

    # Attempt to send the message
    try:
        await context.bot.send_message(chat_id=user_id, text=reply_message)
        await update.message.reply_text('Your reply has been sent.')
    except Exception as e:
        await update.message.reply_text(f'Failed to send message: {e}')




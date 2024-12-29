from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import random
from bson import ObjectId
from ShinobiCompass.database import db  # Correct import for MongoDB



# Handle /sell command
async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Sell Beast", callback_data="sell_beast")],
        [InlineKeyboardButton("Sell Level-Up Card", callback_data="sell_level_up_card")],
        [InlineKeyboardButton("Sell Awaken Card", callback_data="sell_awaken_card")],
        [InlineKeyboardButton("Sell Mask", callback_data="sell_mask")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose an item category to sell:", reply_markup=reply_markup)

# Handle category selection
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.split("_")[1]
    context.user_data["selling_category"] = category

    await query.edit_message_text(
        text=f"Please provide the details for your {category.replace('_', ' ').title()}."
    )

# Handle item submissions
async def handle_item_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to the bot's message with the item details.")
        return

    category = context.user_data.get("selling_category")
    if not category:
        await update.message.reply_text("No category selected. Use /sell to begin selling an item.")
        return

    user_id = update.message.from_user.id
    message_text = update.message.text

    # Here, you can implement specific parsing logic for each item type.
    # For example, for 'beast', you could extract level, stats, etc.
    details = {
        "name": message_text.split("\n")[0],  # Sample placeholder for parsing logic
        "quantity": 10,  # Example placeholder, modify as needed
        "price": "50 tokens"  # Modify as needed based on parsing
    }

    db.items_for_sale.insert_one({
        "seller_id": user_id,
        "category": category,
        **details,
        "status": "draft",
        "views": 0
    })

    await update.message.reply_text(
        f"Your {category.replace('_', ' ').title()} '{details['name']}' has been saved. "
        f"Use /myitems to manage your listed items."
    )

# Handle /myitems command
async def myitems_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    items = list(db.items_for_sale.find({"seller_id": user_id}))

    if not items:
        await update.message.reply_text("You have no items listed for sale.")
        return

    for item in items:
        keyboard = [
            [InlineKeyboardButton("Edit", callback_data=f"edit_{item['_id']}")],
            [InlineKeyboardButton("Put On Sale", callback_data=f"onsale_{item['_id']}")],
            [InlineKeyboardButton("Remove", callback_data=f"remove_{item['_id']}")]
        ]
        await update.message.reply_text(
            f"Item Details:\n\n{format_item_details(item)}\nStatus: {item['status'].title()}\nViews: {item.get('views', 0)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Handle item actions (Edit, On Sale, Remove)
async def handle_item_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, item_id = query.data.split("_")
    item = db.items_for_sale.find_one({"_id": ObjectId(item_id)})

    if not item:
        await query.edit_message_text("This item could not be found.")
        return

    if action == "edit":
        await query.edit_message_text("Please reply with the updated details for this item.")
        context.user_data["edit_item_id"] = item_id
    elif action == "onsale":
        db.items_for_sale.update_one({"_id": ObjectId(item_id)}, {"$set": {"status": "on_sale"}})
        await query.edit_message_text("This item is now available for purchase!")
    elif action == "remove":
        db.items_for_sale.delete_one({"_id": ObjectId(item_id)})
        await query.edit_message_text("This item has been removed from your listings.")

# Handle /scroll command
async def scroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    context.user_data.setdefault("seen_items", [])
    seen_items = context.user_data["seen_items"]

    query = {
        "seller_id": {"$ne": user_id},
        "_id": {"$nin": seen_items},
        "status": "on_sale"
    }

    items = list(db.items_for_sale.find(query))
    if not items:
        await update.message.reply_text("No new items are available for viewing right now.")
        return

    item = random.choice(items)
    context.user_data["seen_items"].append(item["_id"])
    db.items_for_sale.update_one({"_id": item["_id"]}, {"$inc": {"views": 1}})

    keyboard = [
        [InlineKeyboardButton("Trade Accept", callback_data=f"trade_accept_{item['_id']}")],
        [InlineKeyboardButton("Trade Request", callback_data=f"trade_request_{item['_id']}")]
    ]

    await update.message.reply_text(
        f"Item Found:\n\n{format_item_details(item)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
        )

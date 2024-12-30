from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
import random
from bson import ObjectId
from ShinobiCompass.database import db  # Correct import for MongoDB


# Handle forwarded messages for beasts
async def handle_forwarded_beast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.forward_from or update.message.forward_from.id != 5416991774:
        await update.message.reply_text("Please forward a beast message from the bot @beastbot (ID: 5416991774).")
        return

    # Extract beast details
    message_text = update.message.text
    lines = message_text.split("\n")
    beast_details = {}

    # Extract specific fields
    for line in lines:
        if line.startswith("Name:"):
            beast_details["name"] = line.split(":")[1].strip()
        elif line.startswith("Stats:"):
            stats = line.split(":")[1].strip()
            beast_details.update({
                "atk": stats.split(",")[0].strip(),
                "def": stats.split(",")[1].strip(),
                "speed": stats.split(",")[2].strip(),
                "intelligence": stats.split(",")[3].strip(),
                "enchantments": stats.split(",")[4].strip()
            })

    if not beast_details:
        await update.message.reply_text("Invalid format. Please forward the correct beast message.")
        return

    # Save details to context
    context.user_data["beast_details"] = beast_details

    await update.message.reply_text(
        f"Beast details extracted:\n"
        f"Name: {beast_details.get('name')}\n"
        f"ATK: {beast_details.get('atk')}, DEF: {beast_details.get('def')}\n"
        f"Speed: {beast_details.get('speed')}, Intelligence: {beast_details.get('intelligence')}\n"
        f"Enchantments: {beast_details.get('enchantments')}\n\n"
        f"Now, please input the price (e.g., `50000 coins`)."
    )

# Handle price input for beasts
async def handle_beast_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "beast_details" not in context.user_data:
        await update.message.reply_text("No beast details found. Please start by forwarding the beast message.")
        return

    beast_details = context.user_data["beast_details"]
    price_text = update.message.text.strip()

    # Validate price input
    if not price_text or len(price_text.split()) < 2:
        await update.message.reply_text("Invalid format. Please provide the price in the format `amount currency` (e.g., `50000 coins`).")
        return

    price, currency = price_text.split(maxsplit=1)
    beast_details["price"] = f"{price} {currency}"

    # Save beast to database
    db.items_for_sale.insert_one({
        "seller_id": update.message.from_user.id,
        "category": "beast",
        **beast_details,
        "status": "draft",
        "views": 0
    })

    await update.message.reply_text(f"Beast '{beast_details['name']}' has been listed")

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


# Validate level-up cards, awaken cards, and masks
async def handle_item_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        await update.message.reply_text("This command requires a text message. Please provide the necessary details.")
        return

    
    category = context.user_data.get("selling_category")
    message_text = update.message.text.strip()
    user_id = update.message.from_user.id

    if not category:
        await update.message.reply_text("No category selected. Use /sell to start.")
        return

    lines = message_text.split("\n")
    details = {}

    if category in ["level_up_card", "awaken_card"]:
        # Check format: name, quantity, price
        if len(lines) < 3:
            await update.message.reply_text("Please provide the details in the format:\n`Name\nQuantity\nPrice`")
            return

        card_name = lines[0].strip()
        if category == "level_up_card" and card_name not in LEVEL_UP_CARD_NAMES:
            await update.message.reply_text("Invalid card name. Please use one from the predefined list.")
            return

        details = {
            "name": card_name,
            "quantity": int(lines[1]) if lines[1].isdigit() else 1,
            "price": lines[2]
        }
    elif category == "mask":
        # Check format: quantity, price
        if len(lines) < 2:
            await update.message.reply_text("Please provide the details in the format:\n`Quantity\nPrice`")
            return

        details = {
            "name": "Mask",
            "quantity": int(lines[0]) if lines[0].isdigit() else 1,
            "price": lines[1]
        }

    # Save to database
    db.items_for_sale.insert_one({
        "seller_id": user_id,
        "category": category,
        **details,
        "status": "draft",
        "views": 0
    })

    await update.message.reply_text(f"Your {category.replace('_', ' ').title()} '{details['name']}' has been listed.")


# Helper function to format item details
def format_item_details(item):
    return (
        f"Category: {item['category'].title()}\n"
        f"Name: {item['name']}\n"
        f"Quantity: {item.get('quantity', 'N/A')}\n"
        f"Price: {item['price']}\n"
        f"Views: {item['views']}"
    )

async def myitems_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    items = list(db.items_for_sale.find({"seller_id": user_id}))

    if not items:
        await update.message.reply_text("You have no items listed for sale. Use /sell to add items.")
        return

    categories = {"beasts": [], "level_up_cards": [], "awaken_cards": [], "masks": []}
    for item in items:
        categories[item["category"]].append(item)

    keyboard = []
    for category, items in categories.items():
        if items:
            keyboard.append([InlineKeyboardButton(f"{category.title()} ({len(items)})", callback_data=f"myitems_{category}")])

    await update.message.reply_text(
        "Select a category to view and manage your items:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, category = query.data.split("_")
    user_id = query.from_user.id

    items = list(db.items_for_sale.find({"seller_id": user_id, "category": category}))

    if not items:
        await query.edit_message_text(f"You have no items in the {category.title()} category.")
        return

    message = f"Items in {category.title()} category:\n\n"
    for item in items:
        item_details = (
            f"Item ID: `{item['_id']}`\n"
            f"Name: {item['name']}\n"
            f"Price: {item['price']} {item['currency']}\n"
            f"Status: {item['status']}\n\n"
            f"Use `/status {item['_id']}` to view and manage this item.\n\n"
        )
        message += item_details

    await query.edit_message_text(message, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Please provide an item ID. Usage: `/status <item_id>`", parse_mode="Markdown")
        return

    item_id = context.args[0]
    try:
        item = db.items_for_sale.find_one({"_id": ObjectId(item_id)})
        if not item:
            await update.message.reply_text("Item not found. Please check the ID and try again.")
            return

        details = (
            f"Item Details:\n\n"
            f"Item ID: `{item['_id']}`\n"
            f"Name: {item['name']}\n"
            f"Category: {item['category'].title()}\n"
            f"Price: {item['price']} {item['currency']}\n"
            f"Status: {item['status']}\n\n"
            "What would you like to do with this item?"
        )

        keyboard = [
            [InlineKeyboardButton("Edit", callback_data=f"edit_{item['_id']}")],
            [InlineKeyboardButton("Put on Sale", callback_data=f"onsale_{item['_id']}")],
            [InlineKeyboardButton("Remove", callback_data=f"remove_{item['_id']}")]
        ]

        await update.message.reply_text(details, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("Invalid item ID format. Please try again.")


async def handle_item_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, item_id = query.data.split("_")
    item = db.items_for_sale.find_one({"_id": ObjectId(item_id)})

    if not item:
        await query.edit_message_text("This item could not be found.")
        return

    if action == "edit":
        if item["status"] == "on_sale":
            await query.edit_message_text("You must remove this item from sale before editing.")
            return
        await query.edit_message_text("Please reply with the updated details for this item.")
        context.user_data["edit_item_id"] = item_id
    elif action == "onsale":
        db.items_for_sale.update_one({"_id": ObjectId(item_id)}, {"$set": {"status": "on_sale"}})
        await query.edit_message_text("This item is now available for purchase!")
    elif action == "remove":
        db.items_for_sale.delete_one({"_id": ObjectId(item_id)})
        await query.edit_message_text("This item has been removed from your listings.")





# Handle accept offer
async def handle_accept_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, item_id = query.data.split("_")
    item = db.items_for_sale.find_one({"_id": ObjectId(item_id)})

    if not item:
        await query.edit_message_text("This item could not be found.")
        return

    seller_id = item["seller_id"]
    buyer_id = query.from_user.id

    # Notify the seller
    try:
        await context.bot.send_message(
            seller_id,
            f"User @{query.from_user.username} wants to buy your item:\n\n{format_item_details(item)}\n\nAccept or Decline?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Accept", callback_data=f"accept_trade_{item_id}_{buyer_id}"),
                 InlineKeyboardButton("Decline", callback_data=f"decline_trade_{item_id}_{buyer_id}")]
            ])
        )
        await query.edit_message_text("The seller has been notified. Awaiting their response.")
    except:
        await query.edit_message_text("Failed to notify the seller. Please try again later.")

# Handle trade request
async def handle_trade_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, item_id = query.data.split("_")
    item = db.items_for_sale.find_one({"_id": ObjectId(item_id)})

    if not item:
        await query.edit_message_text("This item could not be found.")
        return

    context.user_data["trade_item_id"] = item_id
    await query.edit_message_text(
        "What would you like to offer in exchange? Choose a category:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Beast", callback_data="trade_beast"),
             InlineKeyboardButton("Card", callback_data="trade_card")]
        ])
    )

# Handle price negotiation
async def handle_price_negotiation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, item_id = query.data.split("_")
    item = db.items_for_sale.find_one({"_id": ObjectId(item_id)})

    if not item:
        await query.edit_message_text("This item could not be found.")
        return

    context.user_data["negotiate_item_id"] = item_id
    await query.edit_message_text("Please reply with your counter-offer price (same currency as the original price).")


 



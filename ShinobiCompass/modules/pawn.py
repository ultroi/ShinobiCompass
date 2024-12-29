from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
import random
from ShinobiCompass.database import db  # Correct import for the database

# Function to format item details
def format_item_details(item):
    if item['category'] == 'beast':
        return f"Beast: {item['name']}\nLevel: {item['level']}\nStats: {item['stats']}\nPrice: {item['price']}"
    elif item['category'] == 'level_up_card':
        return f"Level-Up Card: {item['name']}\nQuantity: {item['quantity']}\nPrice: {item['price']}"
    elif item['category'] == 'awaken_card':
        return f"Awaken Card: {item['name']}\nQuantity: {item['quantity']}\nPrice: {item['price']}"
    elif item['category'] == 'mask':
        return f"Mask: {item['name']}\nQuantity: {item['quantity']}\nPrice: {item['price']}"

# Handle /sell command
async def sell_command(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("Sell Beast", callback_data="sell_beast")],
        [InlineKeyboardButton("Sell Level-Up Card", callback_data="sell_level_up_card")],
        [InlineKeyboardButton("Sell Awaken Card", callback_data="sell_awaken_card")],
        [InlineKeyboardButton("Sell Mask", callback_data="sell_mask")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose an item to sell:", reply_markup=reply_markup)

# Handle category selection (Beast, Level-Up Cards, Awaken Cards, Mask)
async def handle_category_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    category = query.data.split("_")[1]  # Get the category from the callback data

    # Save the selected category in user_data
    context.user_data["selling_category"] = category

    # Request item details based on the category
    if category == "beast":
        await query.edit_message_text("Send the beast details in the following format:\n\n"
                                      "Beast ID: [ID]\nUSER: [UserName]\nName: [Name]\nLevel: [Level]\n"
                                      "STATS:\natk: [Atk]\ndef: [Def]\nspeed: [Speed]\nintelligence: [Intelligence]\n"
                                      "accuracy: [Accuracy]\nENHANCED STATS:\natk: [Atk]\ndef: [Def]\nspeed: [Speed]\n"
                                      "intelligence: [Intelligence]\naccuracy: [Accuracy]")
    elif category == "level_up_card":
        await query.edit_message_text("Send the details for the Level-Up Card:\n\n"
                                      "Name: [CardName]\nQuantity: [Quantity]\nPrice: [Price in Tokens, Coins, Gems, or Stocks]")
    elif category == "awaken_card":
        await query.edit_message_text("Send the details for the Awaken Card:\n\n"
                                      "Name: [CardName]\nQuantity: [Quantity]\nPrice: [Price in Tokens, Coins, Gems, or Stocks]")
    elif category == "mask":
        await query.edit_message_text("Send the quantity for the Mask:\n\n"
                                      "Quantity: [Quantity]\nPrice: [Price in Tokens, Coins, Gems, or Stocks]")

# Handle user submission of item details for selling
async def handle_item_submission(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    message_text = update.message.text

    # Retrieve the selected category from user_data
    category = context.user_data.get("selling_category")
    if not category:
        await update.message.reply_text("No category selected. Use /sell to start the selling process.")
        return

    # Process the submission based on the category
    if category == "beast":
        # Parse and save beast details
        # Simplified parsing example:
        details = {"name": "Shukaku", "level": 6, "stats": "atk: 50, def: 40", "price": "100 tokens"}  # Replace with actual parsing logic
        db.items_for_sale.insert_one({
            "seller_id": user_id,
            "category": "beast",
            **details,
            "status": "on_sale"
        })
        await update.message.reply_text(f"Your Beast '{details['name']}' has been listed for sale!")
    elif category in ["level_up_card", "awaken_card", "mask"]:
        # Parse and save other item details
        details = {"name": "CardName", "quantity": 10, "price": "50 tokens"}  # Replace with actual parsing logic
        db.items_for_sale.insert_one({
            "seller_id": user_id,
            "category": category,
            **details,
            "status": "on_sale"
        })
        await update.message.reply_text(f"Your {category.replace('_', ' ').title()} '{details['name']}' has been listed for sale!")

# Handle /scroll command to show random items for sale
async def scroll_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data.setdefault("seen_items", [])  # Track seen items
    seen_items = context.user_data["seen_items"]

    # Exclude user's own items and recently viewed items
    query = {
        "seller_id": {"$ne": user_id},  # Exclude user's own listings
        "_id": {"$nin": seen_items},   # Exclude recently seen items
        "status": "on_sale"            # Only show items that are on sale
    }

    items = list(db.items_for_sale.find(query))
    if not items:
        await update.message.reply_text("No new items available to view.")
        return

    # Randomly select an item and ensure it's not seen too frequently
    item = random.choice(items)
    context.user_data["seen_items"].append(item["_id"])  # Mark as seen

    # Limit the size of `seen_items` to avoid excessive memory usage
    if len(seen_items) > 10:  # Allow a buffer of 10 recently viewed items
        context.user_data["seen_items"] = seen_items[-10:]

    # Display the selected item
    keyboard = [
        [InlineKeyboardButton("Trade Accept", callback_data=f"trade_accept_{item['_id']}")],
        [InlineKeyboardButton("Trade Request", callback_data=f"trade_request_{item['_id']}")]
    ]

    await update.message.reply_text(
        f"Item Found:\n\n{format_item_details(item)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CallbackContext,
    filters,
)
from ShinobiCompass.modules.saveinfo import save_info
#from ShinobiCompass.modules.flood import flood_control

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Shinobi classifications
LEGENDARY_SHINOBIS = [
    "Shisui Uchiha", "Tsunade Senju", "Gaara", "Jiraiya", "Hiruzen Sarutobi",
    "Orochimaru", "Might Guy", "Kakashi Hatake", "Itachi Uchiha", "Minato Namikaze",
    "Madara Uchiha", "Hashirama Senju", "Tobirama Senju", "Mu", "Onoki",
    "Gengetsu Hozuki", "A", "Ay", "Mei Terumi", "Rasa",
]
NON_LEGENDARY_SHINOBIS = [
    "Ino Yamanaka", "Choji Akimichi", "Shikamaru Nara", "Rock Lee", "Neji Hyuga",
    "Ten Ten", "Sakura Haruno", "Hinata Hyuga", "Kiba Inuzuka", "Shino Aburame",
    "Kankuro", "Temari", "Asuma", "Konohamaru", "Iruka Umino", "Sai", "Rin Nohara",
    "Hanabi Hyuga", "Kurenai Yuhi", "Kushina Uzumaki",
]

# Conversion rates and fixed prices
GEM_TO_COIN = 2000
TOKEN_TO_GEM = 20
STOCK_TO_TOKEN = 15
STOCK_TO_COIN = 600000
STOCK_TO_GEM = 300
RARE_LEVELUP_CARD_TOKENS = 10
LEGENDARY_AWAKEN_CARD = 120
NON_LEGENDARY_AWAKEN_CARD = 90

# Helper function to calculate expected price in stocks
def calculate_expected_price_in_stocks(price_in_tokens):
    """
    This function calculates the price in stocks based on the given price in tokens.
    It divides the price in tokens by the STOCK_TO_TOKEN constant.
    """
    return price_in_tokens / STOCK_TO_TOKEN

# Analyze the black market message
def analyze_message(message):
    profit_deals = []
    lines = message.split("\n")

    # Remove the last two lines
    lines = lines[:-2] if len(lines) > 2 else lines

    section = None

    for line in lines:
        line = line.strip()

        # Identify section (Epic, Legendary, Rare, Common)
        if line.startswith(("Epic:", "Legendary:", "Rare:", "Common:")):
            section = line.split(":")[0]

        if not section or not line:
            continue

        try:
            # Remove serial number
            parts = line.split(":")[1].strip().split()
            if len(parts) < 2:
                continue

            # Parse quantity and item
            quantity = int(parts[0])
            item = " ".join(parts[1:])

            # Parse price
            price_str = item.split("(")[-1].split(")")[0]
            price = float(price_str)

            # Check for Epic section (Orochimaru)
            if section == "Epic" and "Orochimaru" in item:
                expected_price_tokens_min = 12000 * quantity
                expected_price_tokens_max = 12750 * quantity
                expected_price_stocks_min = calculate_expected_price_in_stocks(expected_price_tokens_min)
                expected_price_stocks_max = calculate_expected_price_in_stocks(expected_price_tokens_max)
                if price < expected_price_stocks_min:
                    profit_deals.append(
                        f"<b>Epic Orochimaru:</b> {item}\n"
                        f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                        f"   📈 <b>Expected Price:</b> {expected_price_stocks_min:.2f} - {expected_price_stocks_max:.2f} stocks "
                        f"({expected_price_tokens_min} - {expected_price_tokens_max} tokens)\n\n"
                    )

            # Check for Legendary section (Awakening Cards)
            elif section == "Legendary" and "awakencard" in item.lower():
                if any(legendary in item for legendary in LEGENDARY_SHINOBIS):
                    # Legendary Awakening Cards
                    expected_price_tokens = quantity * LEGENDARY_AWAKEN_CARD
                    expected_price_stocks = calculate_expected_price_in_stocks(expected_price_tokens)
                    if price < expected_price_stocks:
                        profit_deals.append(
                            f"<b>Legendary Awakening Card:</b> {item}\n"
                            f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                            f"   📈 <b>Expected Price:</b> {expected_price_stocks:.2f} stocks ({expected_price_tokens} tokens)\n\n"
                        )
                else:
                    # Non-Legendary Awakening Cards
                    expected_price_tokens = quantity * NON_LEGENDARY_AWAKEN_CARD
                    expected_price_stocks = calculate_expected_price_in_stocks(expected_price_tokens)
                    if price < expected_price_stocks:
                        profit_deals.append(
                            f"<b>Non-Legendary Awakening Card:</b> {item}\n"
                            f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                            f"   📈 <b>Expected Price:</b> {expected_price_stocks:.2f} stocks ({expected_price_tokens} tokens)\n\n"
                        )

            # Check for Rare section (Levelup card)
            elif section == "Rare" and "card" in item.lower():
                if "legendary" in item.lower():
                    # Legendary Levelup Cards
                    expected_price_tokens = quantity * RARE_LEVELUP_CARD_TOKENS
                    expected_price_stocks = calculate_expected_price_in_stocks(expected_price_tokens)
                    if price < expected_price_stocks:
                        profit_deals.append(
                            f"<b>Legendary Levelup Card:</b> {item}\n"
                            f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                            f"   📈 <b>Expected Price:</b> {expected_price_stocks:.2f} stocks ({expected_price_tokens} tokens)\n\n"
                        )
                else:
                    # Non-Legendary Levelup Cards
                    expected_price_tokens = quantity * RARE_LEVELUP_CARD_TOKENS
                    expected_price_stocks = calculate_expected_price_in_stocks(expected_price_tokens)
                    if price < expected_price_stocks:
                        profit_deals.append(
                            f"<b>Non-Legendary Levelup Card:</b> {item}\n"
                            f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                            f"   📈 <b>Expected Price:</b> {expected_price_stocks:.2f} stocks ({expected_price_tokens} tokens)\n\n"
                        )

            # Check for Common section (Coins and Gems)
            elif section == "Common":
                if "coins" in item.lower():
                    expected_price_stocks = quantity / STOCK_TO_COIN
                    if price < expected_price_stocks:
                        profit_deals.append(
                            f"<b>Common Coins:</b> {item}\n"
                            f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                            f"   📈 <b>Expected Price:</b> {expected_price_stocks:.2f} stocks\n\n"
                        )
                elif "gems" in item.lower():
                    expected_price_stocks = quantity / STOCK_TO_GEM
                    if price < expected_price_stocks:
                        profit_deals.append(
                            f"<b>Common Gems:</b> {item}\n"
                            f"   💸 <b>Offer Price:</b> {price:.2f} stocks\n"
                            f"   📈 <b>Expected Price:</b> {expected_price_stocks:.2f} stocks\n\n"
                        )

        except Exception as e:
            logging.error(f"Error processing line '{line}': {e}")
            continue

    return profit_deals


# Command: /bm (manual analysis)
@save_info
async def bm(update: Update, _: CallbackContext) -> None:
    if update.message.reply_to_message:
        # Get the replied message content
        message = update.message.reply_to_message.text or update.message.reply_to_message.caption
        if not message or "BLACK MARKET" not in message.upper():
            await update.message.reply_text("⚠️ This is not a valid black market message.")
            return

        sent_message = await update.message.reply_text("🔍 Analyzing...")
        profit_deals = analyze_message(message)

        if profit_deals:
            await sent_message.edit_text(
                "💎 <b>Profitable Deals Found</b>:\n\n" + "".join(profit_deals) + "\n<b>Note: Bot only analyzes Shinobi card trade profit.</b>",
                parse_mode="HTML"
            )
        else:
            await sent_message.edit_text("🔍 No profitable deals found.", parse_mode="HTML")
    else:
        await update.message.reply_text("⚠️ Please reply to a valid black market message.")

# Automatic analysis
@save_info
async def handle_message(update: Update, _: CallbackContext) -> None:
    if not update.message:
        return

    message = update.message.text or update.message.caption
    if hasattr(update.message, 'forward_from') or hasattr(update.message, 'forward_from_chat'):
        message = update.message.text or update.message.caption
    logging.info(f"Received message: {message}")  # Log the message received
    if "BLACK MARKET" in (message or "").upper():  # Ensure the condition is met
        sent_message = await update.message.reply_text("🔍 Analyzing...")
        profit_deals = analyze_message(message)

        if profit_deals:
            await sent_message.edit_text(
                "💎 <b>Profitable Deals Found</b>:\n\n" + "".join(profit_deals),
                parse_mode="HTML"
            )
        else:
            await sent_message.edit_text("🔍 No profitable deals found.", parse_mode="HTML")

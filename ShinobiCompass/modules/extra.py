from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import re
from ShinobiCompass.modules.saveinfo import save_info

#   Function to calculate XP details with the updated format and HTML
 Function to calculate XP details with the updated format and HTML
async def calculate_xp_info(inventory_text):
 try:
        # Extract information from the inventory using regex
        name_match = re.search(r"┣ 👤 Name: (.+)", inventory_text)
        level_match = re.search(r"┣ 🎚️ Level: (\d+)", inventory_text)
        exp_data_match = re.search(r"┣ ✨ Exp: (\d+) / (\d+)", inventory_text)
        chakra_match = re.search(r"┣ 🔮 Chakra: (\d+)", inventory_text)
        explores_match = re.search(r"🗺 Explores: (\d+)", inventory_text)

        # Check if all matches were found
        if not name_match or not level_match or not exp_data_match or not chakra_match or not explores_match:
            return "Error: Could not extract all required information. Please check the inventory format."

        name = name_match.group(1)
        level = int(level_match.group(1))
        current_exp = int(exp_data_match.group(1))
        next_level_exp = int(exp_data_match.group(2))
        total_chakra = int(chakra_match.group(1))
        explores_done = int(explores_match.group(1))

        # Calculate remaining EXP and explores left
        remaining_exp = next_level_exp - current_exp
        explores_left = remaining_exp // 325  # Updated from 350 to 325

        # Calculate next level up rewards based on the next level
        next_level = level + 1  # Next level calculation
        if next_level < 100:
            coins = next_level * 1000
            gems = next_level * 5
            tokens = next_level + 10
        elif next_level < 200:
            coins = next_level * 1000
            gems = next_level * 10
            tokens = next_level * 2 + 10
        else:
            coins = next_level * 1000
            gems = next_level * 20
            tokens = next_level * 3 + 10

        # Generate the output message in HTML format
        xp_info = f"""
<b>🌟 Shinobi Profile - {name} 🌟</b>
---------------------------------
<b>👤 Name</b>: {name}
<b>⚔️ Level</b>: {level} 
<b>🌀 Remaining Exp</b>: {remaining_exp}
<b>🎯 Explores Left</b>: {explores_left} more to rank up

---------------------------------
<b>🎉 Next Level (Level {level + 1}) 🎉</b>
---------------------------------
<b>💰 Coins</b>: {coins}
<b>💎 Gems</b>: {gems}
<b>🎫 Tokens</b>: {tokens}

<b>⚡️ Progress ⚡️</b>
--------------------
<b>🌀 Chakra Flow</b>: {total_chakra}
<b>🌱 Explores</b>: {explores_left} left to rank up!

<b>📜 Note</b> 📜
----------------
⚠️ <i>These are approximate values. Keep pushing, Shinobi!</i>
"""
        return xp_info
    except Exception as e:
        return f"Error processing inventory: {str(e)}"

# /xp command handler to process the inventory text from the message
@save_info
async def xp_command(update: Update, context: CallbackContext):
    if update.message.reply_to_message:
        # Get the inventory text from the replied message
        inventory_text = update.message.reply_to_message.text
        xp_info = await calculate_xp_info(inventory_text)  # Awaiting the function call here
        if xp_info:
            await update.message.reply_text(xp_info, parse_mode="HTML")  # Awaiting reply_text here with HTML parse mode
        else:
            await update.message.reply_text("Error: Could not calculate XP details.", parse_mode="HTML")
    else:
        await update.message.reply_text("Please reply to an inventory message to get XP details.", parse_mode="HTML")

# /iseal command handler to display sealing techniques
@save_info
async def iseal_command(update: Update, context: CallbackContext):
    response = """
<b>🍃 Naruto Sealing Techniques 🍃</b>

🔰 <b>Available Seals</b> 🔰

📜 <b>1️⃣ Four Symbol Seal</b>  
🌀 <b>Catch Chance</b>: 25%  
💰 <b>Price</b>: 2,000 Gems  
⚡ <b>Chakra Usage</b>: 1,000 per use  

📜 <b>2️⃣ Five Elements Seal</b>  
🔥 <b>Catch Chance</b>: 50%  
💰 <b>Price</b>: 9,000 Gems  
⚡ <b>Chakra Usage</b>: 10,000 per use  

📜 <b>3️⃣ Adamantine Sealing Chains</b>  
⛓️ <b>Catch Chance</b>: 75%  
💰 <b>Price</b>: 20,000 Gems  
⚡ <b>Chakra Usage</b>: 25,000 per use  

📜 <b>4️⃣ Demonic Status Chain</b>  
👹 <b>Catch Chance</b>: 90%  
🔒 <b>Unlock Requirement</b>: Madara Uchiha must be in your team  
⚡ <b>Chakra Usage</b>: 250,000 per use  

🌟 <b>Team Synergy Bonus</b> 🌟  
⚔️ If Hashirama Senju or Kushina Uzumaki is in your team, the chances of catching the Beast with any seal will be greatly boosted!

🎮 <b>Shinobi Tips</b>:  
🍥 Save your chakra for stronger seals.  
🍥 Build a balanced team for maximum success.  
🍥 Aim for synergy to boost your chances!

<b>💡 Believe in your ninja way and seal the Beast!</b>
"""
    await update.message.reply_text(response, parse_mode="HTML")  # Awaiting reply_text here with HTML parse mode

import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------- CONFIG ----------
I2C_RATE = 95.0
C2I_RATE_LOW = 91.0
C2I_RATE_HIGH = 91.5
C2I_THRESHOLD = 100.0
GUILD_ID = 785743682334752768
IST = timezone(timedelta(hours=5, minutes=30))

CRYPTO_FILE = "crypto_slots.json"
UPI_FILE = "upi_slots.json"

# ---------- Helpers ----------
def load_json(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return default

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# ---------- Load persistent data ----------
user_crypto_slots = load_json(CRYPTO_FILE, {})  # {user_id: {1: {"address":..., "type":...}, ...}}
user_upi_slots = load_json(UPI_FILE, {})        # {user_id: {1: "upi_id", ...}}

# ---------- Flask Keep-Alive ----------
app = Flask("")

@app.route("/")
def home():
    return "✅ Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ---------- Bot ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- On Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("💱 USD ⇄ INR"))
    try:
        await tree.sync()
        print("🟢 Slash commands synced!")
    except Exception as e:
        print(f"⚠️ Failed to sync: {e}")

# ---------- Modals ----------
class AddCryptoModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"Crypto Slot {slot_num}")
        self.slot_num = slot_num
        self.add_item(discord.ui.TextInput(label="Crypto Address", placeholder="Enter your address", required=True))
        self.add_item(discord.ui.TextInput(label="Crypto Type", placeholder="e.g., USDT POLY, USDT BEP20, LTC", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        slots = user_crypto_slots.setdefault(str(interaction.user.id), {str(i): {"address": None, "type": None} for i in range(1,6)})
        slots[str(self.slot_num)]["address"] = self.children[0].value
        slots[str(self.slot_num)]["type"] = self.children[1].value
        save_json(CRYPTO_FILE, user_crypto_slots)
        await interaction.response.send_message(f"✅ Crypto slot {self.slot_num} updated.", ephemeral=True)

class AddUPIModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"UPI Slot {slot_num}")
        self.slot_num = slot_num
        self.add_item(discord.ui.TextInput(label="UPI ID", placeholder="Enter your UPI ID", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        slots = user_upi_slots.setdefault(str(interaction.user.id), {str(i): None for i in range(1,6)})
        slots[str(self.slot_num)] = self.children[0].value
        save_json(UPI_FILE, user_upi_slots)
        await interaction.response.send_message(f"✅ UPI slot {self.slot_num} updated.", ephemeral=True)

# ---------- Add / Update Slots ----------
@tree.command(name="add-addy", description="Add or replace a crypto slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddCryptoModal(slot_num))

@tree.command(name="add-upi", description="Add or replace a UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Manage Slots ----------
@tree.command(name="manage-slot", description="Update or delete your slot")
@app_commands.describe(action="Choose action", slot_type="Slot type", slot_num="Slot number 1-5")
@app_commands.choices(action=[
    app_commands.Choice(name="Update", value="update"),
    app_commands.Choice(name="Delete", value="delete")
])
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
async def manage_slot(interaction: discord.Interaction, action: app_commands.Choice[str], slot_type: app_commands.Choice[str], slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return

    if slot_type.value == "crypto":
        slots = user_crypto_slots.setdefault(str(interaction.user.id), {str(i): {"address": None, "type": None} for i in range(1,6)})
        if action.value == "delete":
            slots[str(slot_num)] = {"address": None, "type": None}
            save_json(CRYPTO_FILE, user_crypto_slots)
            await interaction.response.send_message(f"✅ Crypto slot {slot_num} deleted.", ephemeral=True)
        else:
            await interaction.response.send_modal(AddCryptoModal(slot_num))
    else:
        slots = user_upi_slots.setdefault(str(interaction.user.id), {str(i): None for i in range(1,6)})
        if action.value == "delete":
            slots[str(slot_num)] = None
            save_json(UPI_FILE, user_upi_slots)
            await interaction.response.send_message(f"✅ UPI slot {slot_num} deleted.", ephemeral=True)
        else:
            await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Receiving Method ----------
@tree.command(name="receiving-method", description="Get your saved crypto/UPI address")
@app_commands.describe(slot_type="Type", slot_num="Slot number 1-5")
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
@app_commands.choices(slot_num=[
    app_commands.Choice(name="1", value=1),
    app_commands.Choice(name="2", value=2),
    app_commands.Choice(name="3", value=3),
    app_commands.Choice(name="4", value=4),
    app_commands.Choice(name="5", value=5)
])
async def receiving_method(interaction: discord.Interaction, slot_type: app_commands.Choice[str], slot_num: app_commands.Choice[int]):
    user_id = str(interaction.user.id)
    ist_now = datetime.now(tz=IST)

    # Prepare embed message
    if slot_type.value == "crypto":
        slots = user_crypto_slots.get(user_id, {})
        slot_data = slots.get(str(slot_num.value), {"address": "Empty", "type": "Empty"})
        address = slot_data.get("address", "Empty")
        addr_type = slot_data.get("type", "Empty")
        embed = discord.Embed(
            title="📌 Payment Method",
            color=discord.Color.blue(),
            timestamp=ist_now
        )
        embed.add_field(name="💰 Payment Address", value=f"`{address}`", inline=False)
        embed.add_field(name="🔹 Address Type", value=f"`{addr_type}`", inline=False)
        embed.set_footer(text=f"Time: {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    else:
        slots = user_upi_slots.get(user_id, {})
        address = slots.get(str(slot_num.value), "Empty")
        embed = discord.Embed(
            title="📌 Payment Method",
            color=discord.Color.blue(),
            timestamp=ist_now
        )
        embed.add_field(name="💰 Payment UPI", value=f"`{address}`", inline=False)
        embed.set_footer(text=f"Time: {ist_now.strftime('%I:%M %p, %d %b %Y')}")

    # Send embed first
    await interaction.response.send_message(embed=embed)
    
    # Send plain address/UPI immediately after
    await interaction.followup.send(f"{address}")

# ---------- Run Bot ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ TOKEN not found!")
else:
    bot.run(TOKEN)

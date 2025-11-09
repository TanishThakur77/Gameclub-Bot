import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
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

crypto_slots = {i: None for i in range(1, 6)}
upi_slots = {i: None for i in range(1, 6)}

# ---------- Helpers ----------
def pretty_num(value):
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.2f}"

def pick_color(amount):
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    return discord.Color.gold()

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

# ---------- /ping ----------
@tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot is working ✅",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
    embed.add_field(name="Info", value="All systems are operational!")
    await interaction.response.send_message(embed=embed)

# ---------- /i2c ----------
@tree.command(name="i2c", description="Convert INR → USD")
@app_commands.describe(amount="Amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    usd = amount / I2C_RATE
    color = pick_color(amount)
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(
        title="💱 INR → USD Conversion",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💸 Amount in INR", value=f"**₹ {pretty_num(amount)}**")
    embed.add_field(name="💵 Converted USD", value=f"**$ {pretty_num(usd)}**")
    embed.add_field(name="⚖️ Rate Used", value=f"**{I2C_RATE} INR per $**")
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /c2i ----------
@tree.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(amount="Amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr = amount * rate
    color = pick_color(inr)
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(
        title="💱 USD → INR Conversion",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💵 Amount in USD", value=f"**$ {pretty_num(amount)}**")
    embed.add_field(name="💸 Converted INR", value=f"**₹ {pretty_num(inr)}**")
    embed.add_field(name="⚖️ Rate Used", value=f"**{rate} INR per $**")
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /setrate ----------
@tree.command(name="setrate", description="Set conversion rates (Admin only)")
@app_commands.describe(new_rate="Enter new rate")
@app_commands.choices(rate_type=[
    app_commands.Choice(name="I2C (INR → USD)", value="i2c"),
    app_commands.Choice(name="C2I Low (USD < 100)", value="c2i_low"),
    app_commands.Choice(name="C2I High (USD ≥ 100)", value="c2i_high")
])
async def setrate(interaction: discord.Interaction, rate_type: app_commands.Choice[str], new_rate: float):
    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can change rates.", ephemeral=True)
        return
    if rate_type.value == "i2c":
        I2C_RATE = new_rate
        title = "💱 I2C Rate Updated"
    elif rate_type.value == "c2i_low":
        C2I_RATE_LOW = new_rate
        title = "💸 C2I Low Rate Updated"
    elif rate_type.value == "c2i_high":
        C2I_RATE_HIGH = new_rate
        title = "💰 C2I High Rate Updated"
    embed = discord.Embed(title=title, description=f"New rate: **{new_rate}**", color=discord.Color.gold())
    embed.set_footer(text=f"Updated by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ---------- Modal for Add / Update ----------
class AddSlotModal(Modal):
    def __init__(self, slot_type: str, slot_num: int):
        super().__init__(title=f"{slot_type.capitalize()} Slot {slot_num}")
        self.slot_type = slot_type
        self.slot_num = slot_num
        self.add_item(TextInput(label="Enter Value", placeholder="Address or UPI here", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        slots = crypto_slots if self.slot_type=="crypto" else upi_slots
        slots[self.slot_num] = self.children[0].value
        embed = discord.Embed(
            title=f"✅ {self.slot_type.capitalize()} Slot {self.slot_num} Updated",
            description=f"New Value: `{self.children[0].value}`",
            color=discord.Color.green(),
            timestamp=datetime.now(tz=IST)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- Dropdown View ----------
class SlotSelect(Select):
    def __init__(self):
        options = []
        for i in range(1, 6):
            crypto_val = crypto_slots[i] or "Empty"
            upi_val = upi_slots[i] or "Empty"
            options.append(discord.SelectOption(
                label=f"Crypto Slot {i}: {crypto_val}",
                description="Select to pay using this crypto slot",
                value=f"crypto_{i}"
            ))
            options.append(discord.SelectOption(
                label=f"UPI Slot {i}: {upi_val}",
                description="Select to pay using this UPI slot",
                value=f"upi_{i}"
            ))
        super().__init__(placeholder="Select slot to pay", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0].split("_")
        slot_type = val[0]
        slot_num = int(val[1])
        slots = crypto_slots if slot_type=="crypto" else upi_slots
        slot_val = slots[slot_num] or "Empty"
        msg = f"💰 Pay on this {slot_type.upper()} only: `{slot_val}`\nSend screenshot of payment."
        embed = discord.Embed(
            title=f"📌 {slot_type.capitalize()} Slot {slot_num}",
            description=msg,
            color=discord.Color.blue(),
            timestamp=datetime.now(tz=IST)
        )
        await interaction.response.send_message(embed=embed)

class SlotView(View):
    def __init__(self):
        super().__init__()
        self.add_item(SlotSelect())

# ---------- /receiving-method ----------
@tree.command(name="receiving-method", description="Select crypto or UPI slot to pay")
async def receiving_method(interaction: discord.Interaction):
    await interaction.response.send_message("Select a slot to pay:", view=SlotView(), ephemeral=True)

# ---------- /add-addy ----------
@tree.command(name="add-addy", description="Add/replace crypto slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddSlotModal("crypto", slot_num))

# ---------- /add-upi ----------
@tree.command(name="add-upi", description="Add/replace UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddSlotModal("upi", slot_num))

# ---------- /manage-slot ----------
@tree.command(name="manage-slot", description="Update or delete any slot")
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
    slots = crypto_slots if slot_type.value=="crypto" else upi_slots
    if action.value=="delete":
        slots[slot_num] = None
        await interaction.response.send_message(f"✅ {slot_type.value.capitalize()} Slot {slot_num} deleted.", ephemeral=True)
    else:
        await interaction.response.send_modal(AddSlotModal(slot_type.value, slot_num))

# ---------- Run Bot ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ TOKEN not found!")
else:
    bot.run(TOKEN)


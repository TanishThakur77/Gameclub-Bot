import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread
import sqlite3

# ---------- CONFIG ----------
IST = timezone(timedelta(hours=5, minutes=30))

I2C_RATE = 95.0
C2I_RATE_LOW = 91.0
C2I_RATE_HIGH = 91.5
C2I_THRESHOLD = 100.0

EXCHANGER_ROLE_ID = 1373872952990236692  # Exchanger role
DB_FILE = "bot_data.db"

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
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- DATABASE ----------
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Users slots
c.execute('''CREATE TABLE IF NOT EXISTS user_slots (
    user_id TEXT,
    slot_type TEXT,
    slot_num INTEGER,
    address TEXT,
    crypto_type TEXT,
    qr TEXT,
    upi TEXT,
    PRIMARY KEY (user_id, slot_type, slot_num)
)''')

# Exchanges
c.execute('''CREATE TABLE IF NOT EXISTS exchanges (
    user_id TEXT PRIMARY KEY,
    total_amount REAL DEFAULT 0,
    deals INTEGER DEFAULT 0
)''')

# Dot commands
c.execute('''CREATE TABLE IF NOT EXISTS dot_commands (
    command_name TEXT PRIMARY KEY,
    response TEXT
)''')

conn.commit()

# ---------- HELPERS ----------
def pretty_num(value):
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.2f}"

def pick_color(amount):
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    return discord.Color.gold()

def get_user_slot(user_id, slot_type):
    c.execute("SELECT slot_num, address, crypto_type, qr, upi FROM user_slots WHERE user_id=? AND slot_type=?", (str(user_id), slot_type))
    return {row[0]: {"address": row[1], "type": row[2], "qr": row[3], "upi": row[4]} for row in c.fetchall()}

# ---------- PERMISSIONS ----------
def is_exchanger(user):
    return any(role.id == EXCHANGER_ROLE_ID for role in user.roles)

def can_use_admin_commands(user):
    return user.guild_permissions.administrator or is_exchanger(user)

# ---------- ON READY ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("💱 Exchange Tracker"))
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
        description="Bot is working ✅ All systems operational.",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
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
    if not can_use_admin_commands(interaction.user):
        await interaction.response.send_message("🚫 Only admins/exchangers can change rates.", ephemeral=True)
        return
    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH
    if rate_type.value == "i2c":
        I2C_RATE = new_rate
        title = "💱 I2C Rate Updated"
    elif rate_type.value == "c2i_low":
        C2I_RATE_LOW = new_rate
        title = "💸 C2I Low Rate Updated"
    else:
        C2I_RATE_HIGH = new_rate
        title = "💰 C2I High Rate Updated"
    embed = discord.Embed(title=title, description=f"New rate: **{new_rate}**", color=discord.Color.gold())
    embed.set_footer(text=f"Updated by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ---------- AddSlotModal ----------
class AddSlotModal(Modal):
    def __init__(self, slot_type: str, slot_num: int):
        super().__init__(title=f"{slot_type.capitalize()} Slot {slot_num}")
        self.slot_type = slot_type
        self.slot_num = slot_num
        if slot_type == "crypto":
            self.add_item(TextInput(label="Address", placeholder="Enter your crypto address", required=True))
            self.add_item(TextInput(label="Type", placeholder="e.g., USDT POLY, LTC", required=True))
            self.add_item(TextInput(label="QR URL", placeholder="Paste QR image URL", required=False))
        else:
            self.add_item(TextInput(label="UPI ID", placeholder="Enter your UPI ID", required=True))
            self.add_item(TextInput(label="QR URL (optional)", placeholder="Paste QR image URL", required=False))

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        address = self.children[0].value
        ctype = self.children[1].value if self.slot_type=="crypto" else None
        qr = self.children[2].value if len(self.children) > 2 else None
        upi = self.children[0].value if self.slot_type=="upi" else None

        c.execute('''INSERT OR REPLACE INTO user_slots (user_id, slot_type, slot_num, address, crypto_type, qr, upi)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', (uid, self.slot_type, self.slot_num, address, ctype, qr, upi))
        conn.commit()

        await interaction.response.send_message(f"✅ {self.slot_type.capitalize()} Slot {self.slot_num} Updated.", ephemeral=True)

# ---------- /add-addy ----------
@tree.command(name="add-addy", description="Add or replace crypto slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddSlotModal("crypto", slot_num))

# ---------- /add-upi ----------
@tree.command(name="add-upi", description="Add or replace UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddSlotModal("upi", slot_num))

# ---------- /manage-slot ----------
@app_commands.choices(action=[
    app_commands.Choice(name="Update", value="update"),
    app_commands.Choice(name="Delete", value="delete")
])
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
@tree.command(name="manage-slot", description="Update or delete any slot")
@app_commands.describe(action="Choose action", slot_type="Slot type", slot_num="Slot number 1-5")
async def manage_slot(interaction: discord.Interaction, action: app_commands.Choice[str], slot_type: app_commands.Choice[str], slot_num: int):
    if not can_use_admin_commands(interaction.user):
        await interaction.response.send_message("🚫 You can't do this.", ephemeral=True)
        return
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    if action.value == "delete":
        c.execute("DELETE FROM user_slots WHERE user_id=? AND slot_type=? AND slot_num=?", (str(interaction.user.id), slot_type.value, slot_num))
        conn.commit()
        await interaction.response.send_message(f"✅ {slot_type.value.capitalize()} Slot {slot_num} deleted.", ephemeral=True)
    else:
        await interaction.response.send_modal(AddSlotModal(slot_type.value, slot_num))

# ---------- /receiving-method ----------
@tree.command(name="receiving-method", description="Select crypto or UPI slot to pay")
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
    slots = get_user_slot(interaction.user.id, slot_type.value)
    value = slots.get(slot_num.value)
    if not value:
        await interaction.response.send_message("❌ This slot is empty.", ephemeral=True)
        return

    desc = ""
    if slot_type.value == "crypto":
        desc = f"💰 **{value['address']}**\nType: **{value['type']}**\nQR: {value.get('qr','None')}"
        embed = discord.Embed(title="📌 Payment Info (Crypto)", description=desc, color=discord.Color.blue(), timestamp=datetime.now(tz=IST))
        await interaction.response.send_message(embed=embed)
        await interaction.channel.send(f"{value['address']}")
        if value.get("qr"):
            await interaction.channel.send(value["qr"])
    else:
        desc = f"💰 **{value.get('upi','')}**\nQR: {value.get('qr','None')}"
        embed = discord.Embed(title="📌 Payment Info (UPI)", description=desc, color=discord.Color.green(), timestamp=datetime.now(tz=IST))
        await interaction.response.send_message(embed=embed)
        await interaction.channel.send(f"{value.get('upi','')}")
        if value.get("qr"):
            await interaction.channel.send(value["qr"])

# ---------- /done ----------
class ConfirmDone(discord.ui.View):
    def __init__(self, user: discord.Member, amount: float, ex_type: str, exchanger: discord.Member, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.user = user
        self.amount = amount
        self.ex_type = ex_type
        self.exchanger = exchanger

    def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        self.disable_all()
        if hasattr(self, "message") and self.message:
            await self.message.edit(content="⌛ Confirmation timed out.", view=self)
        self.stop()

    @discord.ui.button(label="OKAY", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.exchanger.id:
            return await interaction.response.send_message("❌ Only the exchanger can confirm this.", ephemeral=True)
        self.disable_all()
        # Record exchange
        uid = str(self.user.id)
        c.execute("INSERT OR IGNORE INTO exchanges (user_id) VALUES (?)", (uid,))
        c.execute("UPDATE exchanges SET total_amount = total_amount + ?, deals = deals + 1 WHERE user_id=?", (self.amount, uid))
        conn.commit()

        embed = discord.Embed(
            title="✅ Exchange Recorded",
            color=pick_color(self.amount),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="Client", value=self.user.mention)
        embed.add_field(name="Amount", value=f"${self.amount:,.2f}")
        embed.add_field(name="Type", value=self.ex_type)
        c.execute("SELECT deals FROM exchanges WHERE user_id=?", (uid,))
        deals = c.fetchone()[0]
        embed.add_field(name="Total Deals (Client)", value=str(deals))
        try:
            if self.user.avatar:
                embed.set_thumbnail(url=self.user.avatar.url)
        except: pass
        embed.set_footer(text=f"Recorded by {self.exchanger.display_name}")
        await interaction.followup.send(embed=embed)
        await interaction.channel.send(f"{self.user.mention} 🙏 Thank you for choosing Gameclub exchanges! Hope you liked our service.")
        await interaction.channel.send(f"📌 Copy Paste this vouch in this server only or get blacklisted!")
        await interaction.channel.send("https://discord.gg/ResmDRqhyD")
        await interaction.channel.send(f"+rep {self.exchanger.id} Legit Exchange • {self.ex_type} [${self.amount:,.2f}]")
        feedback_channel_mention = "<#1371445182658252900>"
        await interaction.channel.send(f"📝 Kindly give feedback for our exchanger {self.exchanger.mention} in {feedback_channel_mention}")

        if hasattr(self, "message") and self.message:
            await self.message.edit(content="✅ Exchange Confirmed!", view=self)
        self.stop()

    @discord.ui.button(label="CANCEL", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.exchanger.id:
            return await interaction.response.send_message("❌ Only the exchanger can cancel this.", ephemeral=True)
        self.disable_all()
        if interaction.response.is_done():
            await interaction.followup.send("❌ Exchange cancelled.", ephemeral=True)
        else:
            await interaction.response.edit_message(content="❌ Exchange cancelled.", view=self)
        self.stop()

@tree.command(name="done", description="Record a completed exchange")
@app_commands.describe(
    user="Mention the client",
    amount="Amount in USD",
    ex_type="Exchange type (e.g., USDT → UPI)"
)
async def done(interaction: discord.Interaction, user: discord.Member, amount: float, ex_type: str):
    if not can_use_admin_commands(interaction.user):
        await interaction.response.send_message("🚫 You can't use this command.", ephemeral=True)
        return
    view = ConfirmDone(user, amount, ex_type, interaction.user, timeout=30)
    await interaction.response.send_message(
        f"Are you sure you want to confirm this exchange?\n**Client:** {user.display_name}\n**Amount:** ${amount:,.2f}\n**Type:** {ex_type}",
        view=view,
        ephemeral=True
    )
    try:
        view.message = await interaction.original_response()
    except:
        view.message = None

# ---------- /adjust-total ----------
@tree.command(name="adjust-total", description="Adjust total exchanged amount and deals for a user")
@app_commands.describe(user="Mention a user", adjust_amount="Amount to add/subtract", adjust_deals="Deals to add/subtract")
async def adjust_total(interaction: discord.Interaction, user: discord.Member, adjust_amount: float = 0, adjust_deals: int = 0):
    if not can_use_admin_commands(interaction.user):
        await interaction.response.send_message("🚫 You can't use this command.", ephemeral=True)
        return
    uid = str(user.id)
    c.execute("INSERT OR IGNORE INTO exchanges (user_id) VALUES (?)", (uid,))
    c.execute("UPDATE exchanges SET total_amount = total_amount + ?, deals = deals + ? WHERE user_id=?", (adjust_amount, adjust_deals, uid))
    conn.commit()
    await interaction.response.send_message(f"✅ Adjusted {user.display_name}'s record. Amount change: {adjust_amount}, Deals change: {adjust_deals}")

# ---------- /add-dot ----------
@tree.command(name="add-dot", description="Add a custom dot command")
@app_commands.describe(command_name="Command name without dot", response="Message to send when used")
async def add_dot(interaction: discord.Interaction, command_name: str, response: str):
    if not can_use_admin_commands(interaction.user):
        await interaction.response.send_message("🚫 Only admins/exchangers can add dot commands.", ephemeral=True)
        return
    c.execute("INSERT OR REPLACE INTO dot_commands (command_name, response) VALUES (?, ?)", (command_name, response))
    conn.commit()
    await interaction.response.send_message(f"✅ Dot command `. {command_name}` added!")

# ---------- Dot command listener ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith("."):
        cmd_name = message.content[1:].split(" ")[0]
        c.execute("SELECT response FROM dot_commands WHERE command_name=?", (cmd_name,))
        row = c.fetchone()
        if row:
            await message.channel.send(row[0])
            return
    await bot.process_commands(message)

# ---------- /profile ----------
@tree.command(name="profile", description="View your exchange profile")
async def profile(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    c.execute("SELECT total_amount, deals FROM exchanges WHERE user_id=?", (uid,))
    row = c.fetchone()
    total = row[0] if row else 0
    deals = row[1] if row else 0
    embed = discord.Embed(title=f"📊 {interaction.user.display_name}'s Profile", color=discord.Color.blurple())
    embed.add_field(name="💰 Total Amount Exchanged", value=f"${total:,.2f}")
    embed.add_field(name="📝 Total Deals", value=str(deals))
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- RUN ----------
bot.run(os.environ["DISCORD_TOKEN"])

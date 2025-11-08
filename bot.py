import discord
from discord import app_commands
from discord.ext import commands
import asyncio

# ✅ Your Guild (Server) ID
GUILD_ID = 785743682334752768  # replace with your actual server ID
TOKEN = "YOUR_BOT_TOKEN_HERE"  # replace this

# ✅ Intents setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --------- EVENTS ---------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

    # Sync commands to your specific guild (instant)
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🔹 Synced {len(synced)} slash command(s) for guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

    # Change bot status
    await bot.change_presence(activity=discord.Game(name="Ready to convert 📏"))


# --------- SLASH COMMANDS ---------
@bot.tree.command(name="i2c", description="Convert inches to centimeters", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(inches="Enter inches to convert")
async def i2c(interaction: discord.Interaction, inches: float):
    cm = inches * 2.54
    await interaction.response.send_message(f"📏 {inches} inches = {cm:.2f} cm")


@bot.tree.command(name="c2i", description="Convert centimeters to inches", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(cm="Enter centimeters to convert")
async def c2i(interaction: discord.Interaction, cm: float):
    inches = cm / 2.54
    await interaction.response.send_message(f"📏 {cm} cm = {inches:.2f} inches")


# --------- RUN ---------
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())


if not token:
    print("ERROR: No token found. Set TOKEN in environment variables.")
else:
    bot.run(token)

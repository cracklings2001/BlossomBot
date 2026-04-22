import discord
from discord.ext import commands, tasks
import random
import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from keep_alive import keep_alive

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="b!", intents=intents)
bot.remove_command('help')

# --- DATA STORAGE ---
economy = {}
last_claimed = {} 

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

# --- BACKGROUND TASKS ---
@tasks.loop(hours=1)
async def hourly_leaderboard():
    CHANNEL_ID = 123456789012345678 # <--- CHANGE THIS TO YOUR CHANNEL ID
    channel = bot.get_channel(CHANNEL_ID)
    if channel and economy:
        sorted_economy = sorted(economy.items(), key=lambda item: item[1], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Hourly Blossom Leaderboard", color=0xffb7c5)
        lb_text = ""
        for i, (user_id, bal) in enumerate(sorted_economy, 1):
            try:
                user = await bot.fetch_user(user_id)
                name = user.display_name
            except: name = "Unknown"
            lb_text += f"**{i}. {name}**: {bal} petals\n"
        embed.description = lb_text or "No one has petals yet!"
        await channel.send(embed=embed)

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'🌸 Blossom Buddies Online: {bot.user}')
    if not hourly_leaderboard.is_running():
        hourly_leaderboard.start()
    await bot.change_presence(activity=discord.Game(name="b!help | Tending the Garden"))

# --- TUTORIAL & HELP ---
@bot.command()
async def help(ctx, command_name: str = None):
    if command_name is None:
        embed = discord.Embed(title="🌸 Blossom Buddies Instructions", color=0xffb7c5)
        embed.add_field(name="🌱 Earning", value="`beg`, `work`, `hunt`, `farm`", inline=True)
        embed.add_field(name="🎁 Gifts", value="`daily`, `weekly`, `monthly`, `yearly`", inline=True)
        embed.add_field(name="🎲 Games", value="`mines`, `guess`, `rps`, `dice`, `blackjack`", inline=True)
        embed.add_field(name="💰 Stats", value="`balance`, `lb`, `give`", inline=True)
        embed.set_footer(text="Type 'b!help [game]' for a tutorial! (e.g. b!help mines)")
        return await ctx.send(embed=embed)

    tutorials = {
        "mines": "💣 **Mines**: Pick numbers 1-9. Don't hit the 3 bombs! Type `cashout` after any safe pick to keep winnings.",
        "guess": "🌸 **Guess**: Guess a flower number (1-20) in 3 tries. Win 2x your bet!",
        "rps": "✂️ **RPS**: `b!rps [rock/paper/scissors] [bet]`. Win doubles your bet.",
        "dice": "🎲 **Dice**: Higher roll than the bot wins the petals!",
        "blackjack": "🃏 **Blackjack**: Get close to 21. Type `hit` for card, `stand` to stop."
    }
    cmd = command_name.lower()
    if cmd in tutorials:
        await ctx.send(embed=discord.Embed(title=f"📖 {cmd.capitalize()} Tutorial", description=tutorials[cmd], color=0xffb7c5))
    else:
        await ctx.send("❌ Tutorial not found.")

# --- ECONOMY & REWARDS ---
@bot.command(aliases=["bal"])
async def balance(ctx):
    await ctx.send(f"👛 **{ctx.author.display_name}**, you have **{get_balance(ctx.author.id)} petals**.")

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def beg(ctx):
    gain = random.randint(5, 25); update_balance(ctx.author.id, gain)
    await ctx.send(f"🌸 You found **{gain} petals**!")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(50, 150); update_balance(ctx.author.id, gain)
    await ctx.send(f"💼 You worked and earned **{gain} petals**.")

@bot.command()
async def daily(ctx):
    now = datetime.now()
    user_id = ctx.author.id
    if user_id in last_claimed and now < last_claimed[user_id].get('d', now - timedelta(1)) + timedelta(days=1):
        return await ctx.send("⏳ Daily reward not ready yet!")
    if user_id not in last_claimed: last_claimed[user_id] = {}
    last_claimed[user_id]['d'] = now
    update_balance(user_id, 500)
    await ctx.send("☀️ +500 petals!")

# --- MINI GAMES ---
@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals.")
    bombs = random.sample(range(1, 10), 3)
    revealed = []
    await ctx.send("💣 Pick 1-9. Don't hit a bomb! Type `cashout` to stop.")
    while len(revealed) < 6:
        try:
            msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=30.0)
            if msg.content.lower() == 'cashout' and revealed:
                win = int(bet * (1.3 ** len(revealed)))
                update_balance(ctx.author.id, win - bet)
                return await ctx.send(f"💰 Cashed out with **{win} petals**!")
            if not msg.content.isdigit(): continue
            pick = int(msg.content)
            if pick in bombs:
                update_balance(ctx.author.id, -bet)
                return await ctx.send(f"💥 BOOM! You lost {bet} petals.")
            if pick not in revealed and 1 <= pick <= 9:
                revealed.append(pick)
                await ctx.send(f"🍃 Safe! ({len(revealed)}/6). Next number or `cashout`?")
        except asyncio.TimeoutError: return await ctx.send("⏰ Timed out.")

@bot.command()
async def guess(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return
    secret = random.randint(1, 20)
    await ctx.send("🌸 Guess (1-20). 3 tries!")
    for i in range(3):
        try:
            m = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=20.0)
            g = int(m.content)
            if g == secret:
                update_balance(ctx.author.id, bet); return await ctx.send(f"✅ Yes! +{bet} petals.")
            await ctx.send("Higher! 📈" if g < secret else "Lower! 📉")
        except: continue
    update_balance(ctx.author.id, -bet)
    await ctx.send(f"🥀 Failed. It was {secret}.")

@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return
    u, b = random.randint(1, 6), random.randint(1, 6)
    if u > b: update_balance(ctx.author.id, bet); res = f"Win! +{bet}"
    elif u < b: update_balance(ctx.author.id, -bet); res = f"Loss! -{bet}"
    else: res = "Tie!"
    await ctx.send(f"🎲 You: {u} | Me: {b}. {res}")

@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    sorted_e = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "\n".join([f"**{i+1}.** <@{u[0]}> - {u[1]} petals" for i, u in enumerate(sorted_e)])
    await ctx.send(embed=discord.Embed(title="🌸 Top Gardeners", description=text or "None", color=0xffb7c5))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown: {error.retry_after:.1f}s")

keep_alive()
bot.run(TOKEN)

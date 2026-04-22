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
    CHANNEL_ID = 123456789012345678 # <--- REPLACE WITH YOUR ACTUAL CHANNEL ID
    channel = bot.get_channel(CHANNEL_ID)
    if channel and economy:
        sorted_economy = sorted(economy.items(), key=lambda item: item[1], reverse=True)[:10]
        embed = discord.Embed(title="🏆 Hourly Blossom Leaderboard", color=0xffb7c5)
        lb_text = ""
        for i, (user_id, bal) in enumerate(sorted_economy, 1):
            try:
                user = await bot.fetch_user(user_id)
                name = user.display_name
            except: name = "Unknown Gardener"
            lb_text += f"**{i}. {name}**: {bal} petals\n"
        embed.description = lb_text or "No data yet!"
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
        embed.add_field(name="🤝 Social", value="`balance`, `lb`, `give`", inline=True)
        embed.set_footer(text="Type 'b!help [game]' for a tutorial! (e.g. b!help mines)")
        return await ctx.send(embed=embed)

    tutorials = {
        "mines": "💣 **Mines**: Pick 1-9. Avoid the 3 bombs! `cashout` to keep winnings.",
        "guess": "🌸 **Guess**: Guess number (1-20) in 3 tries. Win 2x your bet!",
        "rps": "✂️ **RPS**: `b!rps [rock/paper/scissors] [bet]`. Win = 2x bet.",
        "dice": "🎲 **Dice**: Higher roll than bot wins the pot!",
        "blackjack": "🃏 **Blackjack**: Get to 21. `hit` for card, `stand` to stop.",
        "give": "🤝 **Give**: `b!give [@user] [amount]` to send your petals to a friend!"
    }
    cmd = command_name.lower()
    if cmd in tutorials:
        await ctx.send(embed=discord.Embed(title=f"📖 {cmd.capitalize()} Tutorial", description=tutorials[cmd], color=0xffb7c5))
    else:
        await ctx.send("❌ Tutorial not found.")

# --- ADMIN COMMAND ---
@bot.command()
async def admin_give(ctx, member: discord.Member, amount: int):
    if ctx.author.name != "dispute12":
        return await ctx.send("⛔ Admin only.")
    update_balance(member.id, amount)
    await ctx.send(f"🪄 **Admin Magic**: Added **{amount} petals** to **{member.display_name}**.")

# --- ECONOMY COMMANDS ---
@bot.command(aliases=["bal"])
async def balance(ctx):
    await ctx.send(f"👛 **{ctx.author.display_name}**, you have **{get_balance(ctx.author.id)} petals**.")

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        return await ctx.send("🌸 You can't give petals to yourself!")
    if amount <= 0:
        return await ctx.send("🌸 Amount must be positive.")
    if get_balance(ctx.author.id) < amount:
        return await ctx.send("❌ You don't have enough petals!")
    
    update_balance(ctx.author.id, -amount)
    update_balance(member.id, amount)
    await ctx.send(f"🌸 **{ctx.author.display_name}** gave **{amount} petals** to **{member.display_name}**!")

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def beg(ctx):
    gain = random.randint(5, 25); update_balance(ctx.author.id, gain)
    await ctx.send(f"🌸 You found **{gain} petals**!")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(50, 150); update_balance(ctx.author.id, gain)
    await ctx.send(f"💼 You earned **{gain} petals**.")

@bot.command()
@commands.cooldown(1, 120, commands.BucketType.user)
async def farm(ctx):
    gain = random.randint(150, 400); update_balance(ctx.author.id, gain)
    await ctx.send(f"🚜 **Farm**: Harvest complete! +**{gain} petals**.")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def hunt(ctx):
    if random.random() < 0.2:
        return await ctx.send("🏹 **Hunt**: Nothing caught today.")
    gain = random.randint(60, 120); update_balance(ctx.author.id, gain)
    await ctx.send(f"🏹 **Hunt**: You caught a rare bug! +**{gain} petals**.")

# --- REWARDS ---
@bot.command()
async def daily(ctx):
    now = datetime.now(); user_id = ctx.author.id
    if user_id in last_claimed and now < last_claimed[user_id].get('d', now - timedelta(1)) + timedelta(days=1):
        return await ctx.send("⏳ Daily reward not ready!")
    if user_id not in last_claimed: last_claimed[user_id] = {}
    last_claimed[user_id]['d'] = now; update_balance(user_id, 500)
    await ctx.send("☀️ Daily claimed! +500 petals.")

# --- MINI GAMES ---
@bot.command()
async def blackjack(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Poor.")
    p_hand, d_hand = [random.randint(1, 11), random.randint(1, 11)], [random.randint(1, 11), random.randint(1, 11)]
    await ctx.send(f"🃏 Your total: **{sum(p_hand)}**. `hit` or `stand`?")
    def check(m): return m.author == ctx.author and m.content.lower() in ['hit', 'stand']
    while sum(p_hand) < 21:
        try:
            m = await bot.wait_for('message', check=check, timeout=30.0)
            if m.content.lower() == 'hit':
                p_hand.append(random.randint(1, 11))
                if sum(p_hand) > 21: break
                await ctx.send(f"🃏 Total: **{sum(p_hand)}**. `hit` or `stand`?")
            else: break
        except asyncio.TimeoutError: break
    p_total = sum(p_hand)
    while sum(d_hand) < 17: d_hand.append(random.randint(1, 11))
    d_total = sum(d_hand)
    if p_total > 21:
        update_balance(ctx.author.id, -bet); await ctx.send(f"💥 Bust! Total {p_total}. -{bet} petals.")
    elif d_total > 21 or p_total > d_total:
        update_balance(ctx.author.id, bet); await ctx.send(f"🏆 Win! Dealer had {d_total}. +{bet} petals.")
    elif p_total < d_total:
        update_balance(ctx.author.id, -bet); await ctx.send(f"😢 Loss. Dealer had {d_total}. -{bet} petals.")
    else: await ctx.send(f"🤝 Tie! Both had {p_total}.")

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Poor.")
    bombs = random.sample(range(1, 10), 3); revealed = []
    await ctx.send("💣 Pick 1-9 or `cashout`.")
    while len(revealed) < 6:
        try:
            msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=30.0)
            if msg.content.lower() == 'cashout' and revealed:
                win = int(bet * (1.3 ** len(revealed))); update_balance(ctx.author.id, win - bet)
                return await ctx.send(f"💰 Cashed out! +{win} petals.")
            if not msg.content.isdigit(): continue
            pick = int(msg.content)
            if pick in bombs:
                update_balance(ctx.author.id, -bet); return await ctx.send(f"💥 BOOM! -{bet} petals.")
            if pick not in revealed and 1 <= pick <= 9:
                revealed.append(pick); await ctx.send(f"🍃 Safe! ({len(revealed)}/6) Next?")
        except asyncio.TimeoutError: return

@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    if not economy: return await ctx.send("Empty garden!")
    sorted_e = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "\n".join([f"**{i+1}.** <@{u[0]}> - {u[1]} petals" for i, u in enumerate(sorted_e)])
    await ctx.send(embed=discord.Embed(title="🌸 Top Gardeners", description=text, color=0xffb7c5))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Patience! {error.retry_after:.1f}s left.")

keep_alive()
bot.run(TOKEN)

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

# --- DATA STORAGE (In-Memory) ---
# Note: Restarts will clear this. Use a JSON file for permanent storage.
economy = {}
last_claimed = {} # {user_id: {reward_type: timestamp}}

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

# --- BACKGROUND TASKS ---
@tasks.loop(hours=1)
async def hourly_leaderboard():
    CHANNEL_ID = 123456789012345678  # <--- REPLACE WITH YOUR CHANNEL ID
    channel = bot.get_channel(CHANNEL_ID)
    
    if channel and economy:
        sorted_economy = sorted(economy.items(), key=lambda item: item[1], reverse=True)
        top_10 = sorted_economy[:10]

        embed = discord.Embed(title="🏆 Hourly Blossom Leaderboard", color=0xffb7c5)
        lb_text = ""
        for i, (user_id, bal) in enumerate(top_10, 1):
            try:
                user = await bot.fetch_user(user_id)
                name = user.display_name
            except:
                name = "Unknown"
            lb_text += f"**{i}. {name}**: {bal} petals\n"
        
        embed.add_field(name="Top Players", value=lb_text or "No data yet!")
        await channel.send(embed=embed)

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'🌸 Blossom Buddies is online as {bot.user}')
    if not hourly_leaderboard.is_running():
        hourly_leaderboard.start()
    await bot.change_presence(activity=discord.Game(name="b!help | Tending the Garden"))

# --- HELP COMMAND ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🌸 Blossom Buddies Menu", color=0xffb7c5)
    embed.add_field(name="🌱 Earn", value="`b!beg`, `b!work`, `b!hunt`, `b!farm`", inline=True)
    embed.add_field(name="🎁 Rewards", value="`b!daily`, `b!weekly`, `b!monthly`, `b!yearly`", inline=True)
    embed.add_field(name="🎲 Games", value="`b!rps`, `b!dice`, `b!blackjack`", inline=True)
    embed.add_field(name="🤝 Social", value="`b!give [user] [amount]`, `b!lb`", inline=True)
    embed.add_field(name="💰 Stats", value="`b!balance`", inline=True)
    await ctx.send(embed=embed)

# --- ECONOMY COMMANDS ---
@bot.command(aliases=["bal"])
async def balance(ctx):
    await ctx.send(f"👛 **{ctx.author.display_name}**, you have **{get_balance(ctx.author.id)} petals**.")

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def beg(ctx):
    gain = random.randint(5, 25)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"🌸 You found **{gain} petals** under a leaf!")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(50, 150)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"💼 You trimmed the hedges and earned **{gain} petals**.")

@bot.command()
@commands.cooldown(1, 120, commands.BucketType.user)
async def farm(ctx):
    gain = random.randint(150, 400)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"🚜 Harvest complete! +**{gain} petals**.")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def hunt(ctx):
    if random.random() < 0.2:
        return await ctx.send("🏹 No luck hunting today.")
    gain = random.randint(60, 120)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"🏹 You caught a rare bug! Sold for **{gain} petals**.")

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if amount <= 0 or get_balance(ctx.author.id) < amount or member.id == ctx.author.id:
        return await ctx.send("❌ Invalid transaction.")
    update_balance(ctx.author.id, -amount)
    update_balance(member.id, amount)
    await ctx.send(f"🌸 Gave **{amount} petals** to **{member.display_name}**!")

# --- REWARD SYSTEM ---
def check_claim(user_id, reward_type, delta):
    now = datetime.now()
    user_times = last_claimed.get(user_id, {})
    last_time = user_times.get(reward_type)
    if last_time and now < last_time + delta:
        return False, (last_time + delta) - now
    if user_id not in last_claimed: last_claimed[user_id] = {}
    last_claimed[user_id][reward_type] = now
    return True, None

@bot.command()
async def daily(ctx):
    claimed, time_left = check_claim(ctx.author.id, "daily", timedelta(days=1))
    if not claimed: return await ctx.send(f"⏳ Wait {time_left.seconds//3600}h.")
    update_balance(ctx.author.id, 500)
    await ctx.send("☀️ Daily reward of **500 petals** claimed!")

@bot.command()
async def weekly(ctx):
    claimed, time_left = check_claim(ctx.author.id, "weekly", timedelta(weeks=1))
    if not claimed: return await ctx.send(f"⏳ Wait {time_left.days} days.")
    update_balance(ctx.author.id, 3000)
    await ctx.send("🌱 Weekly reward of **3000 petals** claimed!")

@bot.command()
async def monthly(ctx):
    claimed, time_left = check_claim(ctx.author.id, "monthly", timedelta(days=30))
    if not claimed: return await ctx.send(f"⏳ Wait {time_left.days} days.")
    update_balance(ctx.author.id, 15000)
    await ctx.send("🌸 Monthly reward of **15000 petals** claimed!")

@bot.command()
async def yearly(ctx):
    claimed, time_left = check_claim(ctx.author.id, "yearly", timedelta(days=365))
    if not claimed: return await ctx.send(f"⏳ Wait {time_left.days} days.")
    update_balance(ctx.author.id, 100000)
    await ctx.send("👑 Yearly reward of **100000 petals** claimed!")

# --- GAMES ---
@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Poor.")
    u, b = random.randint(1, 6), random.randint(1, 6)
    if u > b:
        update_balance(ctx.author.id, bet)
        await ctx.send(f"🎲 Win! {u} vs {b}. +{bet}")
    elif u < b:
        update_balance(ctx.author.id, -bet)
        await ctx.send(f"🎲 Loss! {u} vs {b}. -{bet}")
    else: await ctx.send("🎲 Tie!")

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return
    options = ["rock", "paper", "scissors"]
    bot_c = random.choice(options)
    user_c = choice.lower()
    if user_c not in options: return
    if user_c == bot_c: await ctx.send(f"Tie! Both chose {bot_c}")
    elif (user_c == "rock" and bot_c == "scissors") or (user_c == "paper" and bot_c == "rock") or (user_c == "scissors" and bot_c == "paper"):
        update_balance(ctx.author.id, bet)
        await ctx.send(f"Win! I chose {bot_c}. +{bet}")
    else:
        update_balance(ctx.author.id, -bet)
        await ctx.send(f"Loss! I chose {bot_c}. -{bet}")

@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    if not economy: return await ctx.send("Empty garden!")
    sorted_e = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "\n".join([f"**{i+1}.** <@{u[0]}> - {u[1]} petals" for i, u in enumerate(sorted_e)])
    await ctx.send(embed=discord.Embed(title="🌸 Top Gardeners", description=text, color=0xffb7c5))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown: {error.retry_after:.1f}s")

keep_alive()
bot.run(TOKEN)

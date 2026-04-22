import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
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
intents.members = True 
bot = commands.Bot(command_prefix="b!", intents=intents)
bot.remove_command('help')

# --- DATA STORAGE ---
economy = {}
server_channels = {} 

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

# --- MINES GRAPHICAL UI ---
class MinesButton(Button):
    def __init__(self, number):
        super().__init__(label=str(number), style=discord.ButtonStyle.secondary, custom_id=f"mine_{number}", row=(number-1)//3)
        self.number = number

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: return
        
        if self.number in view.bombs:
            view.stop()
            update_balance(view.ctx.author.id, -view.bet)
            for item in view.children:
                item.disabled = True
                if hasattr(item, 'label') and item.label.isdigit() and int(item.label) in view.bombs:
                    item.style, item.label = discord.ButtonStyle.danger, "💣"
            await interaction.response.edit_message(content=f"💥 **BOOM!** {view.ctx.author.mention} hit a bomb! Lost **{view.bet} petals**.", view=view)
        else:
            view.revealed += 1
            self.style, self.label, self.disabled = discord.ButtonStyle.success, "🍃", True
            multiplier = round(1.3 ** view.revealed, 2)
            total_payout = int(view.bet * multiplier)
            profit = total_payout - view.bet 

            async def cashout_logic(inter):
                if inter.user != view.ctx.author: return
                view.stop()
                update_balance(view.ctx.author.id, profit)
                for child in view.children: child.disabled = True
                await inter.response.edit_message(content=f"💰 {view.ctx.author.mention} cashed out! \nMultiplier: **{multiplier}x** | Received: **{total_payout} petals**", view=view)

            cashout_btn = discord.utils.get(view.children, label="Cashout")
            if not cashout_btn:
                cashout_btn = Button(label="Cashout", style=discord.ButtonStyle.primary, row=3)
                cashout_btn.callback = cashout_logic
                view.add_item(cashout_btn)
            else:
                cashout_btn.callback = cashout_logic 

            await interaction.response.edit_message(content=f"🍃 **Safe!** {view.ctx.author.mention}\nMultiplier: **{multiplier}x** | Potential Payout: **{total_payout}**", view=view)

class MinesView(View):
    def __init__(self, ctx, bet, bombs):
        super().__init__(timeout=60.0)
        self.ctx, self.bet, self.bombs, self.revealed = ctx, bet, bombs, 0
        for i in range(1, 10): self.add_item(MinesButton(i))

# --- COLOR GAME GRAPHICAL UI ---
class ColorButton(Button):
    def __init__(self, name, emoji, style):
        super().__init__(label=name, emoji=emoji, style=style)
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: return
        view.stop()
        colors = ["Yellow", "Red", "White", "Green", "Pink", "Blue"]
        emojis = {"Yellow": "🟡", "Red": "🔴", "White": "⚪", "Green": "🟢", "Pink": "🌸", "Blue": "🔵"}
        roll = [random.choice(colors) for _ in range(3)]
        matches = roll.count(self.name)
        for child in view.children: child.disabled = True
        if matches > 0:
            win = view.bet * (matches + 1)
            update_balance(view.ctx.author.id, win - view.bet)
            msg = f"🎨 **WIN!** {view.ctx.author.mention} bet on **{self.name}**.\nResult: {' '.join([emojis[c] for c in roll])}\nMatched {matches}x! Won **{win} petals**!"
        else:
            update_balance(view.ctx.author.id, -view.bet)
            msg = f"🥀 **LOSS.** {view.ctx.author.mention} bet on **{self.name}**.\nResult: {' '.join([emojis[c] for c in roll])}\nYou lost **{view.bet} petals**."
        await interaction.response.edit_message(content=msg, view=view)

class ColorView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
        self.add_item(ColorButton("Yellow", "🟡", discord.ButtonStyle.secondary))
        self.add_item(ColorButton("Red", "🔴", discord.ButtonStyle.danger))
        self.add_item(ColorButton("White", "⚪", discord.ButtonStyle.secondary))
        self.add_item(ColorButton("Green", "🟢", discord.ButtonStyle.success))
        self.add_item(ColorButton("Pink", "🌸", discord.ButtonStyle.secondary))
        self.add_item(ColorButton("Blue", "🔵", discord.ButtonStyle.primary))

# --- TASKS ---
@tasks.loop(hours=1)
async def hourly_leaderboard():
    for g_id, c_id in server_channels.items():
        channel = bot.get_channel(c_id)
        if channel and economy:
            sorted_e = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
            text = ""
            for i, (uid, bal) in enumerate(sorted_e):
                text += f"**{i+1}.** <@{uid}> - {bal} petals\n"
            await channel.send(embed=discord.Embed(title="🏆 Hourly Leaderboard", description=text or "No data", color=0xffb7c5))

@bot.event
async def on_ready():
    print(f'🌸 {bot.user} is online!')
    if not hourly_leaderboard.is_running(): hourly_leaderboard.start()

# --- ADMINISTRATIVE ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    server_channels[ctx.guild.id] = ctx.channel.id
    await ctx.send(f"✅ {ctx.author.mention}, update channel set to {ctx.channel.mention}!")

@bot.command()
async def admin_give(ctx, member: discord.Member, amount: int):
    if ctx.author.name != "dispute12": return
    update_balance(member.id, amount)
    await ctx.send(f"🪄 {ctx.author.mention} granted **{amount} petals** to {member.mention}!")

# --- EARNING (FARM & HUNT ADDED BACK) ---
@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def beg(ctx):
    g = random.randint(10, 35); update_balance(ctx.author.id, g)
    await ctx.send(f"🌸 {ctx.author.mention}, you found **{g} petals**!")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def work(ctx):
    g = random.randint(60, 160); update_balance(ctx.author.id, g)
    await ctx.send(f"💼 {ctx.author.mention}, you earned **{g} petals**!")

@bot.command()
@commands.cooldown(1, 120, commands.BucketType.user)
async def farm(ctx):
    g = random.randint(150, 450); update_balance(ctx.author.id, g)
    await ctx.send(f"🚜 {ctx.author.mention}, the harvest was bountiful! You got **{g} petals**.")

@bot.command()
@commands.cooldown(1, 90, commands.BucketType.user)
async def hunt(ctx):
    if random.random() < 0.2:
        return await ctx.send(f"🏹 {ctx.author.mention}, you hunted but found nothing.")
    g = random.randint(80, 200); update_balance(ctx.author.id, g)
    await ctx.send(f"🏹 {ctx.author.mention}, you caught a rare creature! +**{g} petals**.")

# --- GAMES ---
@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send(f"❌ {ctx.author.mention}, no petals!")
    u, b = random.randint(1, 6), random.randint(1, 6)
    if u > b: update_balance(ctx.author.id, bet); res = f"Win! +{bet}"
    elif u < b: update_balance(ctx.author.id, -bet); res = f"Loss! -{bet}"
    else: res = "Tie!"
    await ctx.send(f"🎲 {ctx.author.mention}: {u} | Me: {b}. {res}")

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ No petals!")
    opt = ["rock", "paper", "scissors"]; bc = random.choice(opt); uc = choice.lower()
    if uc not in opt: return await ctx.send("❌ Pick rock, paper, or scissors.")
    if uc == bc: res = "Tie!"
    elif (uc=="rock" and bc=="scissors") or (uc=="paper" and bc=="rock") or (uc=="scissors" and bc=="paper"):
        update_balance(ctx.author.id, bet); res = f"Win! +{bet}"
    else: update_balance(ctx.author.id, -bet); res = f"Loss! -{bet}"
    await ctx.send(f"✂️ {ctx.author.mention} {uc} vs {bc}. {res}")

@bot.command()
async def blackjack(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ No petals!")
    p_hand, d_hand = [random.randint(1, 11), random.randint(1, 11)], [random.randint(1, 11), random.randint(1, 11)]
    await ctx.send(f"🃏 {ctx.author.mention}, total: **{sum(p_hand)}**. `hit` or `stand`?")
    def check(m): return m.author == ctx.author and m.content.lower() in ['hit', 'stand']
    while sum(p_hand) < 21:
        try:
            m = await bot.wait_for('message', check=check, timeout=30.0)
            if m.content.lower() == 'hit':
                p_hand.append(random.randint(1, 11))
                if sum(p_hand) > 21: break
                await ctx.send(f"🃏 {ctx.author.mention}, total: **{sum(p_hand)}**. `hit`/`stand`?")
            else: break
        except asyncio.TimeoutError: break
    p_total, d_total = sum(p_hand), sum(d_hand)
    while d_total < 17: d_hand.append(random.randint(1, 11)); d_total = sum(d_hand)
    if p_total > 21: update_balance(ctx.author.id, -bet); res = f"💥 Bust! -{bet}"
    elif d_total > 21 or p_total > d_total: update_balance(ctx.author.id, bet); res = f"🏆 Win! +{bet}"
    elif p_total < d_total: update_balance(ctx.author.id, -bet); res = f"😢 Loss! -{bet}"
    else: res = "🤝 Tie!"
    await ctx.send(f"{ctx.author.mention} {res}")

@bot.command()
async def color(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ No petals!")
    await ctx.send(f"🎨 {ctx.author.mention}, pick a color!", view=ColorView(ctx, bet))

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ No petals!")
    await ctx.send(f"💣 {ctx.author.mention}, Mines!", view=MinesView(ctx, bet, random.sample(range(1, 10), 3)))

# --- SYSTEM ---
@bot.command()
async def bal(ctx):
    await ctx.send(f"👛 {ctx.author.mention}, balance: **{get_balance(ctx.author.id)}**")

@bot.command()
async def lb(ctx):
    sorted_e = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "\n".join([f"**{i+1}.** <@{u[0]}> - {u[1]}" for i, u in enumerate(sorted_e)])
    await ctx.send(embed=discord.Embed(title="🌸 Top Gardeners", description=text or "None", color=0xffb7c5))

@bot.command()
async def help(ctx):
    e = discord.Embed(title="🌸 Blossom Help", color=0xffb7c5)
    e.add_field(name="🌱 Earn", value="`beg`, `work`, `farm`, `hunt`, `bal`, `lb`", inline=False)
    e.add_field(name="🎲 Games", value="`dice`, `rps`, `color`, `mines`, `blackjack`", inline=False)
    await ctx.send(embed=e)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ {ctx.author.mention}, wait **{error.retry_after:.1f}s**.")

keep_alive(); bot.run(TOKEN)

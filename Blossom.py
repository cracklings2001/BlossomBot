import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import random
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

# --- BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="b!", intents=intents)
bot.remove_command('help')

# --- DATABASE ---
economy = {}
server_channels = {} 
redeem_codes = {} 

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

# --- UI: REDEEM MODAL ---
class RedeemModal(Modal, title="Redeem Petals"):
    code_input = TextInput(label="Voucher Code", placeholder="Enter code...", min_length=1, max_length=20)
    async def on_submit(self, interaction: discord.Interaction):
        code_text = self.code_input.value.strip().upper()
        if code_text in redeem_codes:
            data = redeem_codes[code_text]
            if data["uses"] > 0:
                update_balance(interaction.user.id, data["value"])
                data["uses"] -= 1
                if data["uses"] <= 0: del redeem_codes[code_text]
                await interaction.response.send_message(f"🌸 {interaction.user.mention}, claimed **{data['value']} petals**!", ephemeral=False)
            else: await interaction.response.send_message("🥀 Code expired!", ephemeral=True)
        else: await interaction.response.send_message("❌ Invalid code.", ephemeral=True)

class RedeemStarterView(View):
    @discord.ui.button(label="Enter Code", style=discord.ButtonStyle.primary, emoji="🎟️")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

# --- UI: CRASH ---
class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=120.0)
        self.ctx, self.bet, self.multiplier = ctx, bet, 1.0
        self.cashed_out, self.crashed = False, False
    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.green, emoji="💰")
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author or self.cashed_out or self.crashed: return
        self.cashed_out = True; self.stop()
        win = int(self.bet * self.multiplier)
        update_balance(self.ctx.author.id, win - self.bet)
        await interaction.response.edit_message(content=f"📈 **Win!** {self.ctx.author.mention} cashed at **{self.multiplier:.2f}x**! Got **{win} petals**.", view=None)
    async def start_flight(self, msg):
        crash_at = round(random.uniform(1.1, 10.0), 2) if random.random() > 0.1 else 1.0
        while not self.cashed_out:
            await asyncio.sleep(1.6)
            if self.cashed_out: break
            self.multiplier += random.uniform(0.1, 0.4)
            if self.multiplier >= crash_at:
                self.crashed = True; self.stop(); update_balance(self.ctx.author.id, -self.bet)
                await msg.edit(content=f"💥 **CRASHED!** Plane exploded at **{crash_at:.2f}x**. {self.ctx.author.mention} lost **{self.bet} petals**.", view=None)
                break
            await msg.edit(content=f"✈️ **Flying...**\nMultiplier: **{self.multiplier:.2f}x**", view=self)

# --- UI: MINES ---
class MinesButton(Button):
    def __init__(self, num): super().__init__(label=str(num), style=discord.ButtonStyle.secondary, row=(num-1)//3); self.num = num
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: return
        if self.num in view.bombs:
            view.stop(); update_balance(view.ctx.author.id, -view.bet)
            for c in view.children: 
                if hasattr(c, 'label') and c.label.isdigit() and int(c.label) in view.bombs: c.style, c.label = discord.ButtonStyle.danger, "💣"
                c.disabled = True
            await interaction.response.edit_message(content=f"💥 **BOOM!** Lost **{view.bet} petals**.", view=view)
        else:
            view.revealed += 1; self.style, self.label, self.disabled = discord.ButtonStyle.success, "🍃", True
            mult = round(1.3 ** view.revealed, 2); val = int(view.bet * mult)
            async def co(i):
                view.stop(); update_balance(view.ctx.author.id, val - view.bet)
                for c in view.children: c.disabled = True
                await i.response.edit_message(content=f"💰 **Cashout!** Won **{val} petals**!", view=view)
            btn = discord.utils.get(view.children, label="Cashout")
            if not btn: 
                btn = Button(label="Cashout", style=discord.ButtonStyle.primary, row=3); btn.callback = co; view.add_item(btn)
            else: btn.callback = co
            await interaction.response.edit_message(content=f"🍃 **Safe!** {mult}x", view=view)

class MinesView(View):
    def __init__(self, ctx, bet, bombs):
        super().__init__(timeout=60.0); self.ctx, self.bet, self.bombs, self.revealed = ctx, bet, bombs, 0
        for i in range(1, 10): self.add_item(MinesButton(i))

# --- UI: COLOR GAME ---
class ColorButton(Button):
    def __init__(self, n, e, s): super().__init__(label=n, emoji=e, style=s); self.n = n
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: return
        view.stop(); opts = ["Yellow", "Red", "White", "Green", "Pink", "Blue"]
        roll = [random.choice(opts) for _ in range(3)]; hits = roll.count(self.n)
        for c in view.children: c.disabled = True
        if hits > 0:
            win = view.bet * (hits + 1); update_balance(view.ctx.author.id, win - view.bet)
            m = f"🎉 **WIN!** Result: {' '.join(roll)}. +{win} petals!"
        else:
            update_balance(view.ctx.author.id, -view.bet); m = f"🥀 **LOSS.** Result: {' '.join(roll)}. -{view.bet} petals."
        await interaction.response.edit_message(content=m, view=view)

class ColorView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0); self.ctx, self.bet = ctx, bet
        d = [("Yellow","🟡",2), ("Red","🔴",4), ("White","⚪",2), ("Green","🟢",3), ("Pink","🌸",2), ("Blue","🔵",1)]
        for n, e, s in d: self.add_item(ColorButton(n, e, discord.ButtonStyle(s)))

# --- AUTOMATED TASKS ---
@tasks.loop(hours=1)
async def hourly_leaderboard():
    for g_id, c_id in server_channels.items():
        chan = bot.get_channel(c_id)
        if chan and economy:
            top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
            txt = "\n".join([f"**{i+1}.** <@{u[0]}> — {u[1]} petals" for i, u in enumerate(top)])
            embed = discord.Embed(title="🏆 Hourly Top Gardeners", description=txt or "No petals found yet!", color=0xffb7c5)
            await chan.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🌸 {bot.user} is fully loaded!'); 
    if not hourly_leaderboard.is_running(): hourly_leaderboard.start()

# --- ADMIN COMMANDS ---
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
    if ctx.author.name != "dispute12": return
    redeem_codes[code.upper()] = {"value": value, "uses": uses}
    await ctx.send(f"🎟️ **Voucher Created!** `{code.upper()}` for **{value} petals** ({uses} uses).")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    server_channels[ctx.guild.id] = ctx.channel.id
    await ctx.send(f"✅ **Setup Complete!** Hourly leaderboard updates will be sent to {ctx.channel.mention}.")

# --- USER COMMANDS ---
@bot.command()
async def lb(ctx):
    """Displays the top 10 players globally."""
    if not economy:
        return await ctx.send("🥀 The leaderboard is currently empty.")
    top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:10]
    txt = "\n".join([f"**{i+1}.** <@{u[0]}> — {u[1]} petals" for i, u in enumerate(top)])
    embed = discord.Embed(title="🌸 Global Leaderboard", description=txt, color=0xffb7c5)
    await ctx.send(embed=embed)

@bot.command()
async def beg(ctx):
    g = random.randint(10, 50); update_balance(ctx.author.id, g)
    await ctx.send(f"🌸 {ctx.author.mention}, you found **{g} petals**!")

@bot.command()
async def farm(ctx):
    g = random.randint(200, 450); update_balance(ctx.author.id, g)
    await ctx.send(f"🚜 {ctx.author.mention}, harvest: **{g} petals**!")

@bot.command()
async def hunt(ctx):
    g = random.randint(100, 300); update_balance(ctx.author.id, g)
    await ctx.send(f"🏹 {ctx.author.mention}, hunt: **{g} petals**!")

@bot.command()
async def bal(ctx):
    await ctx.send(f"👛 {ctx.author.mention}: **{get_balance(ctx.author.id)} petals**.")

@bot.command()
async def crash(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals!")
    v = CrashView(ctx, bet); m = await ctx.send(f"✈️ Fueling up...", view=v); await v.start_flight(m)

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals!")
    await ctx.send(f"💣 Choose safe flowers!", view=MinesView(ctx, bet, random.sample(range(1, 10), 3)))

@bot.command()
async def color(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals!")
    await ctx.send(f"🎨 Pick a color!", view=ColorView(ctx, bet))

@bot.command()
async def blackjack(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals!")
    p, d = [random.randint(1,11), random.randint(1,11)], [random.randint(1,11), random.randint(1,11)]
    await ctx.send(f"🃏 {ctx.author.mention}, total **{sum(p)}**. `hit` or `stand`?")
    def check(m): return m.author == ctx.author and m.content.lower() in ['hit', 'stand']
    try:
        while sum(p) < 21:
            m = await bot.wait_for('message', check=check, timeout=20)
            if m.content.lower() == 'hit': 
                p.append(random.randint(1,11))
                if sum(p) > 21: break
                await ctx.send(f"🃏 Total **{sum(p)}**. `hit`/`stand`?")
            else: break
    except: pass
    pt, dt = sum(p), sum(d)
    while dt < 17: d.append(random.randint(1,11)); dt = sum(d)
    if pt > 21: update_balance(ctx.author.id, -bet); r = "Bust!"
    elif dt > 21 or pt > dt: update_balance(ctx.author.id, bet); r = "Win!"
    elif pt < dt: update_balance(ctx.author.id, -bet); r = "Loss!"
    else: r = "Tie!"
    await ctx.send(f"🃏 {ctx.author.mention}, {r} (Dealer: {dt})")

@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet: return
    u, b = random.randint(1,6), random.randint(1,6)
    if u > b: update_balance(ctx.author.id, bet); r = "Win!"
    elif u < b: update_balance(ctx.author.id, -bet); r = "Loss!"
    else: r = "Tie!"
    await ctx.send(f"🎲 {ctx.author.mention}: {u} vs {b}. {r}")

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if get_balance(ctx.author.id) < bet: return
    opts = ["rock", "paper", "scissors"]; bc = random.choice(opts); uc = choice.lower()
    if uc not in opts: return
    if uc == bc: r = "Tie!"
    elif (uc=="rock" and bc=="scissors") or (uc=="paper" and bc=="rock") or (uc=="scissors" and bc=="paper"):
        update_balance(ctx.author.id, bet); r = "Win!"
    else: update_balance(ctx.author.id, -bet); r = "Loss!"
    await ctx.send(f"✂️ {ctx.author.mention} {uc} vs {bc}. {r}")

@bot.command()
async def redeem(ctx):
    await ctx.send("🎟️ Click below to redeem!", view=RedeemStarterView())

@bot.command()
async def help(ctx):
    e = discord.Embed(title="🌸 Blossom Menu", color=0xffb7c5)
    e.add_field(name="🌱 Earn", value="`beg`, `farm`, `hunt`, `bal`, `lb`, `redeem`", inline=False)
    e.add_field(name="🎲 Games", value="`crash`, `mines`, `color`, `blackjack`, `dice`, `rps`", inline=False)
    e.add_field(name="🎟️ Admin", value="`gen [code] [val] [qty]`, `setup`", inline=False)
    await ctx.send(embed=e)

keep_alive(); bot.run(TOKEN)

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

# --- DATA STORAGE ---
economy = {}
server_channels = {} 
redeem_codes = {} # Format: {"CODE": {"value": 100, "uses": 5}}

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

# --- REDEEM SYSTEM (MODAL & VIEW) ---
class RedeemModal(Modal, title="Redeem Petals"):
    code_input = TextInput(
        label="Voucher Code",
        placeholder="Enter your code here...",
        min_length=1,
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        code_text = self.code_input.value.strip()
        
        if code_text in redeem_codes:
            data = redeem_codes[code_text]
            if data["uses"] > 0:
                value = data["value"]
                data["uses"] -= 1
                update_balance(interaction.user.id, value)
                
                # Cleanup if no uses left
                if data["uses"] <= 0:
                    del redeem_codes[code_text]
                
                await interaction.response.send_message(
                    f"🌸 **Success!** {interaction.user.mention}, you claimed **{value} petals**!", 
                    ephemeral=False
                )
            else:
                await interaction.response.send_message("🥀 This code has run out of uses!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid code. Please try again.", ephemeral=True)

class RedeemStarterView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Click to Enter Code", style=discord.ButtonStyle.primary, emoji="🎟️")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

# --- GAME: CRASH ---
class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=120.0)
        self.ctx, self.bet = ctx, bet
        self.multiplier, self.cashed_out, self.crashed = 1.0, False, False

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.green, emoji="💰")
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author or self.cashed_out or self.crashed: return
        self.cashed_out = True
        self.stop()
        
        total_payout = int(self.bet * self.multiplier)
        update_balance(self.ctx.author.id, total_payout - self.bet)
        await interaction.response.edit_message(content=f"📈 **Cashed Out!** {self.ctx.author.mention} jumped at **{self.multiplier:.2f}x**!\nWon: **{total_payout} petals**", view=None)

    async def start_flight(self, msg):
        # Crash point logic
        crash_at = round(random.uniform(1.1, 15.0), 2) if random.random() > 0.1 else 1.0
        
        while not self.cashed_out:
            await asyncio.sleep(1.5)
            if self.cashed_out: break
            
            self.multiplier += random.uniform(0.1, 0.4)
            
            if self.multiplier >= crash_at:
                self.crashed = True
                self.stop()
                update_balance(self.ctx.author.id, -self.bet)
                await msg.edit(content=f"💥 **CRASHED!** The plane exploded at **{crash_at:.2f}x**.\n{self.ctx.author.mention} lost **{self.bet} petals**.", view=None)
                break
            
            await msg.edit(content=f"✈️ **Flying...**\nMultiplier: **{self.multiplier:.2f}x**\nValue: **{int(self.bet * self.multiplier)}**", view=self)

# --- GAME: MINES ---
class MinesButton(Button):
    def __init__(self, num):
        super().__init__(label=str(num), style=discord.ButtonStyle.secondary, row=(num-1)//3)
        self.num = num

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: return
        
        if self.num in view.bombs:
            view.stop()
            update_balance(view.ctx.author.id, -view.bet)
            for child in view.children:
                if hasattr(child, 'label') and child.label.isdigit() and int(child.label) in view.bombs:
                    child.style, child.label = discord.ButtonStyle.danger, "💣"
                child.disabled = True
            await interaction.response.edit_message(content=f"💥 **BOOM!** Lost **{view.bet} petals**.", view=view)
        else:
            view.revealed += 1
            self.style, self.label, self.disabled = discord.ButtonStyle.success, "🍃", True
            mult = round(1.3 ** view.revealed, 2)
            val = int(view.bet * mult)
            
            async def co(i):
                view.stop(); update_balance(view.ctx.author.id, val - view.bet)
                for c in view.children: c.disabled = True
                await i.response.edit_message(content=f"💰 **Cashout!** Gained **{val} petals**!", view=view)
            
            btn = discord.utils.get(view.children, label="Cashout")
            if not btn:
                btn = Button(label="Cashout", style=discord.ButtonStyle.primary, row=3); btn.callback = co; view.add_item(btn)
            else: btn.callback = co
            await interaction.response.edit_message(content=f"🍃 **Safe!** Current Multiplier: **{mult}x**", view=view)

class MinesView(View):
    def __init__(self, ctx, bet, bombs):
        super().__init__(timeout=60.0); self.ctx, self.bet, self.bombs, self.revealed = ctx, bet, bombs, 0
        for i in range(1, 10): self.add_item(MinesButton(i))

# --- ADMINISTRATIVE ---
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
    if ctx.author.name != "dispute12": return
    redeem_codes[code.upper()] = {"value": value, "uses": uses}
    await ctx.send(f"🎟️ **Voucher Created!**\nCode: `{code.upper()}`\nValue: **{value}**\nQuantity: **{uses}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    server_channels[ctx.guild.id] = ctx.channel.id
    await ctx.send(f"✅ Updates will be sent to {ctx.channel.mention}!")

# --- USER COMMANDS ---
@bot.command()
async def redeem(ctx):
    # Sends a button because Modals cannot open from a text command directly
    await ctx.send("🌸 Click the button below to enter your code!", view=RedeemStarterView())

@bot.command()
async def beg(ctx):
    g = random.randint(10, 50); update_balance(ctx.author.id, g)
    await ctx.send(f"🌸 {ctx.author.mention}, you found **{g} petals**!")

@bot.command()
async def farm(ctx):
    g = random.randint(150, 400); update_balance(ctx.author.id, g)
    await ctx.send(f"🚜 {ctx.author.mention}, you harvested **{g} petals**!")

@bot.command()
async def crash(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals!")
    view = CrashView(ctx, bet)
    msg = await ctx.send(f"✈️ **Plane is fueling up...**", view=view)
    await view.start_flight(msg)

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0: return await ctx.send("❌ Not enough petals!")
    await ctx.send(f"💣 {ctx.author.mention}, Mines!", view=MinesView(ctx, bet, random.sample(range(1, 10), 3)))

@bot.command()
async def bal(ctx):
    await ctx.send(f"👛 {ctx.author.mention}, you have **{get_balance(ctx.author.id)} petals**.")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="🌸 Blossom Menu", color=0xffb7c5)
    e.add_field(name="🌱 Basics", value="`beg`, `farm`, `bal`, `redeem`", inline=False)
    e.add_field(name="🎲 Games", value="`crash [bet]`, `mines [bet]`", inline=False)
    e.add_field(name="🎟️ Admin", value="`gen [code] [val] [qty]`", inline=False)
    await ctx.send(embed=e)

keep_alive(); bot.run(TOKEN)

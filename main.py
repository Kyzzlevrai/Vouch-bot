import discord
from discord.ext import commands
from discord.ui import Button, View
import json
from datetime import datetime

with open('config.json') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True

bot_prefix = config.get('prefix', '+')

bot = commands.Bot(command_prefix=bot_prefix, intents=intents)

bot.remove_command('help')

try:
    with open('vouch.json') as f:
        vouches = json.load(f)
except FileNotFoundError:
    vouches = []

def save_vouches():
    with open('vouch.json', 'w') as f:
        json.dump(vouches, f, indent=4)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(config['bot_status']))

class VouchView(View):
    def __init__(self, vouch_id):
        super().__init__()
        self.vouch_id = vouch_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        vouch = next((v for v in vouches if v['id'] == self.vouch_id), None)
        if vouch:
            vouch['status'] = 'approved'
            save_vouches()
            embed = discord.Embed(title="Vouch Approved", description="Vouch approved!", color=discord.Color.green())
            embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=config['footer'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            # Send a message to the user
            user = interaction.guild.get_member(vouch['receiver'])
            if user:
                embed = discord.Embed(title="Vouch Approved", description=f"Your vouch ID {self.vouch_id} has been approved!", color=discord.Color.green())
                embed.set_thumbnail(url=interaction.guild.icon.url)
                embed.set_footer(text=config['footer'])
                await user.send(embed=embed)

    @discord.ui.button(label="Suspend", style=discord.ButtonStyle.red)
    async def suspend(self, interaction: discord.Interaction, button: discord.ui.Button):
        vouch = next((v for v in vouches if v['id'] == self.vouch_id), None)
        if vouch:
            vouch['status'] = 'suspended'
            save_vouches()
            embed = discord.Embed(title="Vouch Suspended", description="Vouch suspended!", color=discord.Color.red())
            embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=config['footer'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            user = interaction.guild.get_member(vouch['receiver'])
            if user:
                embed = discord.Embed(title="Vouch Suspended", description=f"Your vouch ID {self.vouch_id} has been suspended.", color=discord.Color.red())
                embed.set_thumbnail(url=interaction.guild.icon.url)
                embed.set_footer(text=config['footer'])
                await user.send(embed=embed)

@bot.command()
async def vouch(ctx, user: discord.Member = None, *, details: str = None):
    if user is None or details is None or user == bot.user:
        embed = discord.Embed(title="Vouch Denied", description="The vouch could not be sent. Possible reasons:\n- User is blacklisted.\n- Message is improperly formatted.\n- Missing required arguments.\n- Vouch sent to the bot.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
        return

    if user.id in config.get('blacklist', []):
        embed = discord.Embed(title="Vouch Denied", description="User is blacklisted.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
        return

    try:
        product, price = details.split(" | ")
    except ValueError:
        embed = discord.Embed(title="Vouch Denied", description="The vouch could not be sent. Possible reasons:\n- User is blacklisted.\n- Message is improperly formatted.\n- Missing required arguments.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
        return

    vouch_id = len(vouches) + 1
    vouches.append({
        'id': vouch_id,
        'sender': ctx.author.id,
        'receiver': user.id,
        'product': product,
        'price': price,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'pending'
    })
    save_vouches()

    embed = discord.Embed(title="Vouch Sent", description=f"Vouch sent! ID: {vouch_id}", color=discord.Color.green())
    embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text=config['footer'])
    await ctx.send(embed=embed, delete_after=10)

    embed = discord.Embed(title="Vouch Received", description=f"You have received a vouch from {ctx.author}.\nID: {vouch_id}\nProduct: {product}\nPrice: {price}", color=discord.Color.green())
    embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text=config['footer'])
    await user.send(embed=embed)

    moderation_channel = bot.get_channel(config.get('moderation_channel'))
    if moderation_channel:
        embed = discord.Embed(title="New Vouch", description=f"ID: {vouch_id}\nSender: {ctx.author}\nReceiver: {user}\nProduct: {product}\nPrice: {price}", color=discord.Color.blue())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        view = VouchView(vouch_id)
        await moderation_channel.send(embed=embed, view=view)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def blacklist(ctx, user: discord.Member):
    if user.id not in config.get('blacklist', []):
        config['blacklist'].append(user.id)
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        embed = discord.Embed(title="User Blacklisted", description=f"{user.name} has been blacklisted.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="User Already Blacklisted", description=f"{user.name} is already blacklisted.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def unblacklist(ctx, user: discord.Member):
    if user.id in config.get('blacklist', []):
        config['blacklist'].remove(user.id)
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        embed = discord.Embed(title="User Unblacklisted", description=f"{user.name} has been unblacklisted.", color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="User Not Blacklisted", description=f"{user.name} is not blacklisted.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)

@bot.command()
async def profile(ctx, user: discord.Member = None):
    if not user:
        user = ctx.author

    badges = []
    user_vouches = [v for v in vouches if v['receiver'] == user.id and v['status'] == 'approved']
    total_vouches = len([v for v in vouches if v['receiver'] == user.id])

    if len(user_vouches) >= 50:
        badges.append(f"{config['badge_emojis']['50+ Vouches']} 50+ Vouches")
    if len(user_vouches) >= 100:
        badges.append(f"{config['badge_emojis']['100+ Vouches']} 100+ Vouches")
    if user.id == config.get('creator'):
        badges.append(f"{config['badge_emojis']['Creator']} Creator")
    if any(role.id in config.get('moderator_roles', []) for role in user.roles):
        badges.append(f"{config['badge_emojis']['Moderator']} Moderator")
    if user.id in config.get('donators', []):
        badges.append(f"{config['badge_emojis']['Donator']} Donator")

    badges_text = "\n".join(badges)

    embed = discord.Embed(title=f"{user.name}'s Profile", description=f"Badges:\n{badges_text}\n\nTotal Vouches: {total_vouches}", color=discord.Color.blue())
    embed.add_field(name="Recent Vouches", value="\n".join([f"ID: {v['id']}, Product: {v['product']}, Price: {v['price']}" for v in user_vouches[-5:]]))
    embed.set_thumbnail(url=user.avatar.url)
    embed.set_footer(text=config['footer'])
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def add_donator(ctx, user: discord.Member):
    if user.id not in config.get('donators', []):
        config['donators'].append(user.id)
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        embed = discord.Embed(title="Donator Added", description=f"{user.name} has been added as a donator.", color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Already a Donator", description=f"{user.name} is already a donator.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def remove_donator(ctx, user: discord.Member):
    if user.id in config.get('donators', []):
        config['donators'].remove(user.id)
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        embed = discord.Embed(title="Donator Removed", description=f"{user.name} has been removed as a donator.", color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Not a Donator", description=f"{user.name} is not a donator.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)

@bot.command()
async def get(ctx, vouch_id: int):
    vouch = next((v for v in vouches if v['id'] == vouch_id), None)
    if vouch:
        embed = discord.Embed(title="Vouch Details", description=f"ID: {vouch['id']}\nSender: <@{vouch['sender']}>\nReceiver: <@{vouch['receiver']}>\nProduct: {vouch['product']}\nPrice: {vouch['price']}\nStatus: {vouch['status']}", color=discord.Color.blue())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Vouch Not Found", description="Vouch not found.", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=config['footer'])
        await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help", description="List of commands:", color=discord.Color.blue())
    embed.add_field(name="User Commands", value=f"`{config['prefix']}vouch` - Vouch for a user.\n`{config['prefix']}profile` - View user profile.\n`{config['prefix']}get` - Get vouch details.\n`{config['prefix']}help` - Show this help message.", inline=False)
    embed.add_field(name="Moderator Commands", value=f"`{config['prefix']}blacklist` - Blacklist a user.\n`{config['prefix']}unblacklist` - Unblacklist a user.\n`{config['prefix']}add_donator` - Add a donator.\n`{config['prefix']}remove_donator` - Remove a donator.", inline=False)
    embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text=f"Prefix: `{config['prefix']}`\n{config['footer']}\nMade by kyzz")
    await ctx.send(embed=embed)

bot.run(f'{config["token"]}')

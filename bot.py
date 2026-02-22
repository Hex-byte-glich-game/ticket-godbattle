from workers import WorkerEntrypoint, Response

import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import asyncio
import os
import random
from config import Config




class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(id=Config.GUILD_ID))
        print(f'✅ Synced commands for guild {Config.GUILD_ID}')
        
        # Start status rotation task
        self.status_task.start()

    # Status rotation task
    @tasks.loop(seconds=10)  # Change status every 10 seconds
    async def status_task(self):
        await self.change_status()

    async def change_status(self):
        """Change bot status with different messages"""
        
        # Get ticket counts
        total_tickets = len(active_tickets)
        
        # Different status messages
        status_messages = [
            f"🎫 {total_tickets} active tickets",
            "💸 BUY SKIN",
            "💰 DONATIONS",
            "🎥 POV",
            "❓ GENERAL",
            "❗ REPORT",
            "✨ Support Online 24/7"
        ]
        
        # Choose random status
        status = random.choice(status_messages)
        
        # Set activity
        await self.change_presence(
            activity=discord.Game(name=status),
            status=discord.Status.online  # Can be online, idle, dnd, invisible
        )

    @status_task.before_loop
    async def before_status_task(self):
        """Wait until bot is ready before starting status rotation"""
        await self.wait_until_ready()

bot = TicketBot()

# Store active tickets
active_tickets = {}

# ==================== STATUS HELPER FUNCTIONS ====================

def get_ticket_stats():
    """Get ticket statistics"""
    total = len(active_tickets)
    by_category = {}
    
    for ticket_id, ticket_data in active_tickets.items():
        category = ticket_data['category']
        if category in by_category:
            by_category[category] += 1
        else:
            by_category[category] = 1
    
    return total, by_category

# ==================== BEAUTIFUL VIEWS ====================

class BeautifulTicketView(discord.ui.View):
    """Beautiful buttons inside ticket channels"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket", row=0)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_close(interaction)
    
    @discord.ui.button(label="📄 Transcript", style=discord.ButtonStyle.secondary, custom_id="transcript", row=0)
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_transcript(interaction)
        
    async def handle_close(self, interaction: discord.Interaction):
        channel = interaction.channel
        user = interaction.user
        
        support_role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
        is_creator = channel.id in active_tickets and active_tickets[channel.id]['user_id'] == user.id
        
        if not (support_role in user.roles or is_creator or user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You don't have permission to close this ticket!", ephemeral=True)
            return
        
        view = ConfirmCloseView(channel)
        await interaction.response.send_message(
            "⚠️ **Are you sure you want to close this ticket?**",
            view=view,
            ephemeral=True
        )
    
    async def handle_transcript(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        transcript = await generate_transcript(interaction.channel)
        
        embed = discord.Embed(
            title="📄 Ticket Transcript",
            description=f"Channel: {interaction.channel.mention}",
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed, file=transcript, ephemeral=True)
    
    async def handle_add_user(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith('ticket-'):
            return
        
        support_role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
        if not (support_role in interaction.user.roles or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
            return
        
        modal = AddUserModal()
        await interaction.response.send_modal(modal)
    
    async def handle_rename(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith('ticket-'):
            return
        
        support_role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
        if not (support_role in interaction.user.roles or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
            return
        
        modal = RenameModal()
        await interaction.response.send_modal(modal)

class AddUserModal(discord.ui.Modal, title="👥 Add User to Ticket"):
    user_id = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="Paste user ID or @mention",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = self.user_id.value
            user_id = ''.join(filter(str.isdigit, user_input))
            user = await interaction.guild.fetch_member(int(user_id))
            
            if user:
                await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
                await interaction.response.send_message(f"✅ Added {user.mention} to the ticket!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Invalid user ID or mention!", ephemeral=True)

class RenameModal(discord.ui.Modal, title="🔧 Rename Ticket"):
    new_name = discord.ui.TextInput(
        label="New Ticket Name",
        placeholder="Enter new name (without ticket- prefix)",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        clean_name = self.new_name.value.lower().replace(' ', '-')
        await interaction.channel.edit(name=f"ticket-{clean_name}")
        await interaction.response.send_message(f"✅ Ticket renamed to `ticket-{clean_name}`", ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=30)
        self.channel = channel
    
    @discord.ui.button(label="✅ Yes, Close", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✅ Closure cancelled.", view=None)
    
    async def close_ticket(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="📝 Generating transcript and closing ticket...", view=None)
        
        transcript_file = await generate_transcript(self.channel)
        
        log_channel = interaction.guild.get_channel(Config.LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🔒 Ticket Closed",
                color=0xe74c3c,
                timestamp=datetime.datetime.utcnow()
            )
            
            if self.channel.id in active_tickets:
                ticket_data = active_tickets[self.channel.id]
                creator = interaction.guild.get_member(ticket_data['user_id'])
                ticket_type = Config.TICKET_TYPES[ticket_data['type']]
                
                embed.add_field(name="Created By", value=creator.mention if creator else "Unknown", inline=True)
                embed.add_field(name="Ticket Type", value=f"{ticket_type['emoji']} {ticket_type['name']}", inline=True)
                embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
            
            await log_channel.send(embed=embed, file=transcript_file)
        
        await self.channel.send("🔒 **Ticket closing in 3 seconds...**")
        await asyncio.sleep(3)
        await self.channel.delete()
        
        if self.channel.id in active_tickets:
            del active_tickets[self.channel.id]

class BeautifulTicketSelect(discord.ui.Select):
    """Beautiful dropdown menu for ticket categories"""
    def __init__(self):
        options = []
        for key, value in Config.TICKET_TYPES.items():
            options.append(
                discord.SelectOption(
                    label=value["name"],
                    description=value["description"],
                    emoji=value["emoji"],
                    value=key
                )
            )
        
        super().__init__(
            placeholder="✨ Select a category to create ticket...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        await create_beautiful_ticket(interaction, self.values[0])

class BeautifulSetupView(discord.ui.View):
    """Beautiful main ticket panel"""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BeautifulTicketSelect())

# ==================== BOT EVENTS ====================

@bot.event
async def on_ready():
    print(f'✨ {bot.user} is now online!')
    print(f'📊 Serving {len(bot.guilds)} guild(s)')
    print(f'🎫 Ticket categories: {len(Config.TICKET_TYPES)}')
    print(f'🔄 Status rotation started - changes every 10 seconds')
    
    bot.add_view(BeautifulTicketView())
    bot.add_view(BeautifulSetupView())
    
    # Set initial status
    await bot.change_presence(
        activity=discord.Game(name="🎫 Godbattle Support"),
        status=discord.Status.online
    )

# ==================== BEAUTIFUL COMMANDS ====================

@bot.tree.command(name="setup-ticket", description="Setup beautiful ticket system", guild=discord.Object(id=Config.GUILD_ID))
@app_commands.default_permissions(administrator=True)
async def setup_beautiful_ticket(interaction: discord.Interaction):
    """Create beautiful ticket panel"""
    
    embed = discord.Embed(
        title="🎫 **GODBATTLE SUPPORT TICKET**",
        description="*Your gateway to getting help from our team*",
        color=0x9b59b6,
        timestamp=datetime.datetime.utcnow()
    )
    
    categories = (
        "```ansi\n"
        "[2;33m🟡 BUY SKIN     - Purchase skins or cosmetics[0m\n"
        "[2;35m🟣 DONATION     - Support server with donations[0m\n"
        "[2;36m🔵 POV          - Share evidence or POV[0m\n"
        "[2;32m🟢 GENERAL      - General questions[0m\n"
        "[2;31m🔴 REPORT       - Report rule-breakers[0m\n"
        "```"
    )
    
    embed.add_field(name="📋 **AVAILABLE CATEGORIES**", value=categories, inline=False)
    
    steps = (
        "⬇️ **1. SELECT** a category from dropdown below\n"
        "🔒 **2. PRIVATE** channel created automatically\n"
        "💬 **3. EXPLAIN** your issue to support team\n"
        "✅ **4. CLOSE** ticket when resolved"
    )
    
    embed.add_field(name="⚡ **HOW IT WORKS**", value=steps, inline=False)
    
    rules = (
        "• ⏰ **Response time:** 5-30 minutes\n"
        "• 👤 **One ticket** per person at a time\n"
        "• 📸 **Provide evidence** for reports\n"
        "• ❌ **No spam** or fake tickets"
    )
    
    embed.add_field(name="📌 **RULES & INFO**", value=rules, inline=False)
    
    embed.set_footer(
        text="Godbattle Support • Click dropdown to begin",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )
    
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    await interaction.channel.send(embed=embed, view=BeautifulSetupView())
    await interaction.response.send_message("✅ Beautiful ticket system installed!", ephemeral=True)

@bot.tree.command(name="stats", description="Show ticket statistics", guild=discord.Object(id=Config.GUILD_ID))
async def ticket_stats(interaction: discord.Interaction):
    """Show current ticket statistics"""
    
    total, by_category = get_ticket_stats()
    
    embed = discord.Embed(
        title="📊 **Ticket Statistics**",
        color=0x3498db,
        timestamp=datetime.datetime.utcnow()
    )
    
    embed.add_field(name="📌 Total Active Tickets", value=f"```{total}```", inline=False)
    
    if by_category:
        categories_text = ""
        for category, count in by_category.items():
            categories_text += f"• {category}: **{count}** tickets\n"
        embed.add_field(name="📋 By Category", value=categories_text, inline=False)
    else:
        embed.add_field(name="📋 By Category", value="No active tickets", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Change bot status (Admin only)", guild=discord.Object(id=Config.GUILD_ID))
@app_commands.default_permissions(administrator=True)
async def change_status(interaction: discord.Interaction, status_type: str, status_text: str):
    """Change bot status manually"""
    
    status_types = {
        "playing": discord.Game(name=status_text),
        "watching": discord.Activity(type=discord.ActivityType.watching, name=status_text),
        "listening": discord.Activity(type=discord.ActivityType.listening, name=status_text),
        "competing": discord.Activity(type=discord.ActivityType.competing, name=status_text)
    }
    
    if status_type.lower() in status_types:
        await bot.change_presence(activity=status_types[status_type.lower()])
        await interaction.response.send_message(f"✅ Status changed to **{status_type} {status_text}**", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid status type! Use: playing, watching, listening, competing", ephemeral=True)

# ==================== TICKET FUNCTIONS ====================

async def create_beautiful_ticket(interaction: discord.Interaction, ticket_type: str):
    """Create a beautiful new ticket"""
    
    guild = interaction.guild
    user = interaction.user
    
    category_id = Config.get_category_id(ticket_type)
    category = guild.get_channel(category_id)
    
    if not category:
        await interaction.response.send_message(
            "❌ Category not found! Contact admin.",
            ephemeral=True
        )
        return
    
    for channel in category.channels:
        if user.name.lower() in channel.name:
            await interaction.response.send_message(
                f"❌ You already have a ticket! {channel.mention}",
                ephemeral=True
            )
            return
    
    ticket_number = len([c for c in category.channels if c.name.startswith('ticket')]) + 1
    channel_name = f"ticket-{ticket_number:04d}-{user.name.lower()}"
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    support_role = guild.get_role(Config.SUPPORT_ROLE_ID)
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    channel = await category.create_text_channel(
        name=channel_name,
        overwrites=overwrites
    )
    
    ticket_info = Config.TICKET_TYPES[ticket_type]
    
    welcome_embed = discord.Embed(
        title=f"{ticket_info['emoji']} **{ticket_info['name']} TICKET**",
        description=f"✨ **Welcome {user.mention}!**\n\n{ticket_info['description']}",
        color=ticket_info['color'],
        timestamp=datetime.datetime.utcnow()
    )
    
    category_messages = {
        "buy_skin": "💰 **Please provide:**\n• Skin name\n• In-game username\n• Payment method",
        "donation": "💝 **Please provide:**\n• Donation amount\n• Payment method\n• Any special message",
        "pov": "📸 **Please provide:**\n• Screenshots/videos\n• Description\n• Time of incident",
        "general": "💬 **Please describe:**\n• Your question/issue\n• What you need help with",
        "report_players": "🚨 **Please provide:**\n• Player username\n• Rule violated\n• Evidence"
    }
    
    welcome_embed.add_field(
        name="📋 **REQUIRED INFORMATION**",
        value=category_messages[ticket_type],
        inline=False
    )
    
    welcome_embed.add_field(
        name="⏱️ **RESPONSE TIME**",
        value="Support will respond within 5-30 minutes",
        inline=True
    )
    
    welcome_embed.add_field(
        name="🆔 **TICKET ID**",
        value=f"#{ticket_number:04d}",
        inline=True
    )
    
    welcome_embed.set_footer(
        text=f"Godbattle • {ticket_info['name']} Support",
        icon_url=guild.icon.url if guild.icon else None
    )
    
    await channel.send(content=support_role.mention if support_role else "", embed=welcome_embed, view=BeautifulTicketView())
    
    active_tickets[channel.id] = {
        'user_id': user.id,
        'type': ticket_type,
        'category': ticket_info['name'],
        'created_at': datetime.datetime.utcnow().isoformat()
    }
    
    await interaction.response.send_message(
        f"✅ Ticket created! {channel.mention}",
        ephemeral=True
    )

async def generate_transcript(channel: discord.TextChannel) -> discord.File:
    """Generate transcript"""
    messages = []
    messages.append("=" * 60)
    messages.append(f"GODBATTLE TICKET TRANSCRIPT")
    messages.append(f"Channel: {channel.name}")
    messages.append(f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    messages.append("=" * 60)
    messages.append("")
    
    if channel.id in active_tickets:
        ticket_data = active_tickets[channel.id]
        messages.append(f"Ticket Type: {ticket_data['category']}")
        messages.append(f"Created By: {ticket_data['user_id']}")
        messages.append(f"Created At: {ticket_data['created_at']}")
        messages.append("")
    
    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{message.author.name}#{message.author.discriminator}"
        content = message.clean_content
        
        if message.attachments:
            content += f" [Attachments: {', '.join([a.filename for a in message.attachments])}]"
        
        messages.append(f"[{timestamp}] {author}: {content}")
    
    messages.append("")
    messages.append("=" * 60)
    messages.append("END OF TRANSCRIPT")
    messages.append("=" * 60)
    
    filename = f"transcript-{channel.name}-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(messages))
    
    return discord.File(filename)

# ==================== COMMANDS ====================

@bot.tree.command(name="add", description="Add user to ticket", guild=discord.Object(id=Config.GUILD_ID))
async def add_user(interaction: discord.Interaction, user: discord.Member):
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("❌ Ticket channel only!", ephemeral=True)
        return
    
    support_role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
    if not (support_role in interaction.user.roles or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ No permission!", ephemeral=True)
        return
    
    await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ Added {user.mention}!")

@bot.tree.command(name="remove", description="Remove user from ticket", guild=discord.Object(id=Config.GUILD_ID))
async def remove_user(interaction: discord.Interaction, user: discord.Member):
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("❌ Ticket channel only!", ephemeral=True)
        return
    
    support_role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
    if not (support_role in interaction.user.roles or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ No permission!", ephemeral=True)
        return
    
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"✅ Removed {user.mention}!")

@bot.tree.command(name="close", description="Close current ticket", guild=discord.Object(id=Config.GUILD_ID))
async def close_command(interaction: discord.Interaction):
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("❌ Ticket channel only!", ephemeral=True)
        return
    
    support_role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
    is_creator = interaction.channel.id in active_tickets and active_tickets[interaction.channel.id]['user_id'] == interaction.user.id
    
    if not (support_role in interaction.user.roles or is_creator or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ No permission!", ephemeral=True)
        return
    
    view = ConfirmCloseView(interaction.channel)
    await interaction.response.send_message(
        "⚠️ **Close this ticket?**",
        view=view,
        ephemeral=True
    )

# ==================== RUN BOT ====================

if __name__ == "__main__":
    if not Config.TOKEN:
        print("❌ No token found!")
        exit(1)
    
    print("✨ Starting Godbattle Ticket Bot...")
    print("🎨 Beautiful UI Edition")
    print("🔄 Status rotation: Active (changes every 10 seconds)")
    
    try:
        bot.run(Config.TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")

#class running(WorkerEntrypoint)
#async def fetch(self, request):
#        return Response("Hello World!")
#        
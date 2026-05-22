import builtins
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from utils import load, save, ok, err, info
# no main import needed

def get_mc(guild_id):
    cfg = load('mod_config.json')
    return cfg.get(str(guild_id), {})

async def log_action(bot, guild, title, description, color=discord.Color.red()):
    mc = get_mc(guild.id)
    if not mc.get('logging'): return
    ch_id = mc.get('log_channel')
    if not ch_id: return
    ch = bot.get_channel(ch_id)
    if not ch: return
    punch_color = int(mc.get('punch_color','#ed4245').replace('#',''), 16)
    em = discord.Embed(title=title, description=description, color=punch_color, timestamp=datetime.now())
    await ch.send(embed=em)

async def send_ghost(member, guild, message):
    mc = get_mc(guild.id)
    if not mc.get('ghost_msg'): return
    try: await member.send(f"**{guild.name}:** {message}")
    except: pass

async def check_auto_punch(interaction, member, warnings):
    mc = get_mc(interaction.guild.id)
    if not mc.get('auto_punch'): return
    threshold = mc.get('ap_threshold', 3)
    if warnings < threshold: return
    action   = mc.get('ap_action','timeout')
    duration = mc.get('ap_duration', 60)
    reason   = f"Auto-punishment: reached {warnings} warnings"
    try:
        if action == 'timeout':
            await member.timeout(timedelta(minutes=duration), reason=reason)
            await interaction.followup.send(embed=discord.Embed(
                title="🤖 Auto-Punishment",
                description=f"{member.mention} was automatically **muted for {duration} min** after reaching {warnings} warnings!",
                color=discord.Color.orange()
            ))
        elif action == 'kick':
            await member.kick(reason=reason)
            await interaction.followup.send(embed=discord.Embed(
                title="🤖 Auto-Punishment",
                description=f"{member.mention} was automatically **kicked** after reaching {warnings} warnings!",
                color=discord.Color.orange()
            ))
        elif action == 'ban':
            await member.ban(reason=reason)
            await interaction.followup.send(embed=discord.Embed(
                title="🤖 Auto-Punishment",
                description=f"{member.mention} was automatically **banned** after reaching {warnings} warnings!",
                color=discord.Color.red()
            ))
    except: pass

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="Who to ban", reason="Reason for ban")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        mc = get_mc(interaction.guild.id)
        color = int(mc.get('punch_color','ed4245').replace('#',''), 16)
        em = discord.Embed(title="🔨 Banned", description=f"{member.mention} was banned!\n**Reason:** {reason}", color=color)
        em.set_footer(text=f"By {interaction.user}")
        await interaction.response.send_message(embed=em)
        await send_ghost(member, interaction.guild, f"You were banned. Reason: {reason}")
        await log_action(self.bot, interaction.guild, "🔨 Member Banned", f"**User:** {member.mention}\n**By:** {interaction.user.mention}\n**Reason:** {reason}")

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Who to kick", reason="Reason for kick")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        mc = get_mc(interaction.guild.id)
        color = int(mc.get('punch_color','ed4245').replace('#',''), 16)
        em = discord.Embed(title="👢 Kicked", description=f"{member.mention} was kicked!\n**Reason:** {reason}", color=color)
        em.set_footer(text=f"By {interaction.user}")
        await interaction.response.send_message(embed=em)
        await send_ghost(member, interaction.guild, f"You were kicked. Reason: {reason}")
        await log_action(self.bot, interaction.guild, "👢 Member Kicked", f"**User:** {member.mention}\n**By:** {interaction.user.mention}\n**Reason:** {reason}")

    @app_commands.command(name="mute", description="Mute a member")
    @app_commands.describe(member="Who to mute", minutes="Duration in minutes", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        em = discord.Embed(title="🔇 Muted", description=f"{member.mention} muted for **{minutes} min**!\n**Reason:** {reason}", color=discord.Color.greyple())
        await interaction.response.send_message(embed=em)
        await send_ghost(member, interaction.guild, f"You were muted for {minutes} minutes. Reason: {reason}")
        await log_action(self.bot, interaction.guild, "🔇 Member Muted", f"**User:** {member.mention}\n**Duration:** {minutes} min\n**By:** {interaction.user.mention}\n**Reason:** {reason}")

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="Who to unmute")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(embed=ok("Unmuted", f"{member.mention} has been unmuted!"))
        await log_action(self.bot, interaction.guild, "🔊 Member Unmuted", f"**User:** {member.mention}\n**By:** {interaction.user.mention}")

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Who to warn", reason="Reason for warning")
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        w = load('warnings.json')
        gid, uid = str(interaction.guild.id), str(member.id)
        w.setdefault(gid, {}).setdefault(uid, []).append({'reason': reason, 'time': str(datetime.now())[:10], 'by': str(interaction.user)})
        save('warnings.json', w)
        count = len(w[gid][uid])
        em = discord.Embed(title=f"⚠️ Warning #{count}", description=f"{member.mention} was warned!\n**Reason:** {reason}", color=discord.Color.yellow())
        em.set_footer(text=f"By {interaction.user}")
        await interaction.followup.send(embed=em)
        await send_ghost(member, interaction.guild, f"You received warning #{count}. Reason: {reason}")
        await log_action(self.bot, interaction.guild, f"⚠️ Member Warned (#{count})", f"**User:** {member.mention}\n**By:** {interaction.user.mention}\n**Reason:** {reason}")
        builtins.refresh_bot_cache() if hasattr(builtins, "refresh_bot_cache") else None
        await check_auto_punch(interaction, member, count)

    @app_commands.command(name="warnings", description="View warnings for a member")
    @app_commands.describe(member="Who to check")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        w = load('warnings.json').get(str(interaction.guild.id), {}).get(str(member.id), [])
        em = discord.Embed(title=f"⚠️ Warnings — {member.display_name}", color=discord.Color.yellow())
        em.set_thumbnail(url=member.display_avatar.url)
        em.description = "No warnings! 😇" if not w else ""
        for i, x in enumerate(w, 1):
            em.add_field(name=f"#{i} — {x['time']}", value=x['reason'], inline=False)
        await interaction.response.send_message(embed=em)

    @app_commands.command(name="clearwarns", description="Clear all warnings for a member")
    @app_commands.describe(member="Who to clear")
    @app_commands.default_permissions(manage_messages=True)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        w = load('warnings.json')
        gid, uid = str(interaction.guild.id), str(member.id)
        if w.get(gid, {}).pop(uid, None):
            save('warnings.json', w)
            await interaction.response.send_message(embed=ok(f"Cleared warnings for {member.display_name}"))
        else:
            await interaction.response.send_message(embed=err("No warnings found!"))

    @app_commands.command(name="clear", description="Delete messages from this channel")
    @app_commands.describe(amount="How many messages to delete")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 10):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=ok(f"Deleted {len(deleted)} messages!"), ephemeral=True)
        await log_action(self.bot, interaction.guild, "🗑️ Messages Purged", f"**{len(deleted)} messages** deleted in {interaction.channel.mention}\n**By:** {interaction.user.mention}")

    @app_commands.command(name="role", description="Add or remove a role from a member")
    @app_commands.describe(action="add or remove", member="Target member", role="Which role")
    @app_commands.default_permissions(manage_roles=True)
    async def role(self, interaction: discord.Interaction, action: str, member: discord.Member, role: discord.Role):
        if action == 'add':
            await member.add_roles(role)
            await interaction.response.send_message(embed=ok("Role Added", f"Added {role.mention} to {member.mention}"))
        elif action == 'remove':
            await member.remove_roles(role)
            await interaction.response.send_message(embed=ok("Role Removed", f"Removed {role.mention} from {member.mention}"))
        else:
            await interaction.response.send_message(embed=err("Use `add` or `remove`"))

    @app_commands.command(name="setlogchannel", description="Set the mod-log channel")
    @app_commands.describe(channel="Where to send mod logs")
    @app_commands.default_permissions(administrator=True)
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        cfg = load('mod_config.json')
        cfg.setdefault(str(interaction.guild.id), {})['log_channel'] = channel.id
        cfg[str(interaction.guild.id)]['logging'] = True
        save('mod_config.json', cfg)
        await interaction.response.send_message(embed=ok("Log Channel Set!", f"Mod logs → {channel.mention}"))

    @app_commands.command(name="serverinfo", description="Show server information")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        em = discord.Embed(title=f"ℹ️ {g.name}", color=discord.Color.blue())
        if g.icon: em.set_thumbnail(url=g.icon.url)
        em.add_field(name="👑 Owner",    value=g.owner.mention)
        em.add_field(name="👥 Members",  value=g.member_count)
        em.add_field(name="📅 Created",  value=g.created_at.strftime("%d/%m/%Y"))
        em.add_field(name="💬 Channels", value=len(g.channels))
        em.add_field(name="🎭 Roles",    value=len(g.roles))
        em.add_field(name="😀 Emojis",   value=len(g.emojis))
        await interaction.response.send_message(embed=em)

    @app_commands.command(name="userinfo", description="Show user information")
    @app_commands.describe(member="Who to check")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        em = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
        em.set_thumbnail(url=member.display_avatar.url)
        em.add_field(name="🆔 ID",      value=member.id)
        em.add_field(name="📅 Joined",  value=member.joined_at.strftime("%d/%m/%Y"))
        em.add_field(name="📅 Created", value=member.created_at.strftime("%d/%m/%Y"))
        w = load('warnings.json').get(str(interaction.guild.id), {}).get(str(member.id), [])
        em.add_field(name="⚠️ Warnings", value=len(w))
        roles = [r.mention for r in member.roles[1:]]
        em.add_field(name=f"🎭 Roles ({len(roles)})", value=' '.join(roles) if roles else "None", inline=False)
        await interaction.response.send_message(embed=em)

    @app_commands.command(name="setwelcome", description="Set the welcome channel")
    @app_commands.describe(channel="Welcome channel")
    @app_commands.default_permissions(administrator=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        cfg = load('config.json')
        cfg.setdefault(str(interaction.guild.id), {})['welcome_channel'] = channel.id
        save('config.json', cfg)
        await interaction.response.send_message(embed=ok("Welcome Channel Set!", f"Welcome messages → {channel.mention}"))

    @app_commands.command(name="setautorole", description="Set the auto-role for new members")
    @app_commands.describe(role="Role to give")
    @app_commands.default_permissions(administrator=True)
    async def setautorole(self, interaction: discord.Interaction, role: discord.Role):
        cfg = load('config.json')
        cfg.setdefault(str(interaction.guild.id), {})['auto_role'] = role.id
        save('config.json', cfg)
        await interaction.response.send_message(embed=ok("Auto-role Set!", f"New members get {role.mention}"))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = load('config.json').get(str(member.guild.id), {})
        ch = self.bot.get_channel(cfg.get('welcome_channel'))
        if ch:
            em = discord.Embed(title=f"🎉 Welcome to {member.guild.name}!", description=f"Hey {member.mention}! Glad you're here! 🎮", color=discord.Color.green())
            em.set_thumbnail(url=member.display_avatar.url)
            em.set_footer(text=f"Member #{member.guild.member_count}")
            await ch.send(embed=em)
        role_id = cfg.get('auto_role')
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try: await member.add_roles(role)
                except: pass

async def setup(bot):
    await bot.add_cog(Moderation(bot))

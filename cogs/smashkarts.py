import builtins
import discord
from discord.ext import commands
from discord import app_commands
from utils import load, save, ok, err, info, medal

class SmashKarts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    sk = app_commands.Group(name="sk", description="Smash Karts leaderboard commands")

    @sk.command(name="add", description="Submit your Smash Karts score")
    @app_commands.describe(score="Your score")
    async def add(self, interaction: discord.Interaction, score: int):
        if score < 0:
            return await interaction.response.send_message(embed=err("Score can't be negative!"), ephemeral=True)
        lb = load('smashkarts.json')
        gid, uid = str(interaction.guild.id), str(interaction.user.id)
        lb.setdefault(gid, {})
        entry = lb[gid].get(uid, {'best': 0, 'games': 0, 'name': interaction.user.display_name})
        entry['games'] = entry.get('games', 0) + 1
        entry['name'] = interaction.user.display_name
        new_record = score > entry['best']
        if new_record: entry['best'] = score
        lb[gid][uid] = entry
        save('smashkarts.json', lb)
        if new_record:
            await interaction.response.send_message(embed=ok("NEW RECORD! 🏆", f"**{interaction.user.display_name}**: **{score} pts**!", discord.Color.gold()))
        else:
            await interaction.response.send_message(embed=ok("Score Saved", f"Submitted: **{score}** pts | Record: **{entry['best']}** pts"))

    @sk.command(name="lb", description="Show the Smash Karts leaderboard")
    async def lb(self, interaction: discord.Interaction):
        lb = load('smashkarts.json').get(str(interaction.guild.id), {})
        if not lb: return await interaction.response.send_message(embed=err("No scores yet! Use `/sk add`"))
        sorted_lb = sorted(lb.items(), key=lambda x: x[1]['best'], reverse=True)[:10]
        em = discord.Embed(title="🏆 Smash Karts Leaderboard", color=discord.Color.gold())
        desc = ""
        for i, (uid, d) in enumerate(sorted_lb):
            desc += f"{medal(i)} **{d['name']}** — {d['best']} pts\n"
        em.description = desc
        em.set_footer(text="Submit your score with /sk add")
        await interaction.response.send_message(embed=em)

    @sk.command(name="profile", description="View a Smash Karts profile")
    @app_commands.describe(member="Who to check")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        lb = load('smashkarts.json')
        gid, uid = str(interaction.guild.id), str(member.id)
        data = lb.get(gid, {}).get(uid)
        if not data: return await interaction.response.send_message(embed=err(f"{member.mention} has no scores!"))
        sorted_lb = sorted(lb.get(gid, {}).items(), key=lambda x: x[1]['best'], reverse=True)
        rank = next((i+1 for i,(id,_) in enumerate(sorted_lb) if id == uid), '?')
        em = discord.Embed(title=f"🏎️ {member.display_name}", color=discord.Color.purple())
        em.set_thumbnail(url=member.display_avatar.url)
        em.add_field(name="🏆 Best Score",   value=f"{data['best']} pts")
        em.add_field(name="📊 Rank",          value=f"#{rank}")
        em.add_field(name="🎮 Games Played", value=data.get('games', 1))
        await interaction.response.send_message(embed=em)

    @sk.command(name="reset", description="Reset a user's Smash Karts data (Admin)")
    @app_commands.describe(member="Who to reset")
    @app_commands.default_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction, member: discord.Member):
        lb = load('smashkarts.json')
        gid, uid = str(interaction.guild.id), str(member.id)
        if lb.get(gid, {}).pop(uid, None):
            save('smashkarts.json', lb)
            await interaction.response.send_message(embed=ok(f"Reset data for {member.display_name}"))
        else:
            await interaction.response.send_message(embed=err("No data found!"))

async def setup(bot):
    await bot.add_cog(SmashKarts(bot))

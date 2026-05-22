import builtins
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import random
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
from utils import load, save, ok, err, info, medal

# ── XP Изчисления ──────────────────────────────────────────
def xp_for_level(level):
    return 5 * (level ** 2) + 50 * level + 100

def total_xp_for_level(level):
    return sum(xp_for_level(i) for i in range(level))

def get_level(xp):
    level = 0
    while xp >= total_xp_for_level(level + 1):
        level += 1
        if level > 500: break
    return level

def xp_progress(xp):
    level = get_level(xp)
    cur = xp - total_xp_for_level(level)
    needed = xp_for_level(level)
    return level, cur, needed

def bar(cur, total, length=12):
    filled = round((cur / total) * length) if total > 0 else 0
    return "█" * filled + "░" * (length - filled)

XP_CD = {}       
VOICE_LAST_CHECK = {} 

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_xp_ticker.start()

    def cog_unload(self):
        self.voice_xp_ticker.cancel()

    # Помощна функция за сигурно взимане на конфигурацията
    def get_guild_config(self, gid):
        # Първо четем от диска, за да сме сигурни, че имаме най-новото от Flask
        configs = load('config.json')
        return configs.get(str(gid), {})

    def calculate_multipliers(self, member, channel, cfg):
        multiplier = 1.0
        stack_boosters = cfg.get('stack_boosters', True)
        
        # 1. Role Boosters
        highest_role_bonus = 0
        role_boosters = cfg.get('role_boosters', {})
        for role_id_str, percentage in role_boosters.items():
            if any(r.id == int(role_id_str) for r in member.roles):
                if stack_boosters:
                    multiplier += (percentage / 100)
                else:
                    if (percentage / 100) > highest_role_bonus:
                        highest_role_bonus = percentage / 100
                        
        if not stack_boosters and highest_role_bonus > 0:
            multiplier += highest_role_bonus

        # 2. Channel Boosters
        highest_ch_bonus = 0
        channel_boosters = cfg.get('channel_boosters', {})
        ch_id_str = str(channel.id)
        if ch_id_str in channel_boosters:
            percentage = channel_boosters[ch_id_str]
            if stack_boosters:
                multiplier += (percentage / 100)
            else:
                highest_ch_bonus = percentage / 100

        if not stack_boosters and highest_ch_bonus > 0 and (highest_ch_bonus > highest_role_bonus):
            multiplier = 1.0 + highest_ch_bonus
            
        return multiplier

    # Трябва да добавим тези импорти най-отгоре във файла leveling.py, ако ги няма:
    # from PIL import Image, ImageDraw, ImageFont
    # import io
    # import aiohttp

    async def generate_level_card(self, member, new_level):
        """ Генерира красива графична картичка за Level Up """
        # Създаваме празно платно с тъмен цвят (Discord стил)
        W, H = 600, 180
        image = Image.new("RGBA", (W, H), "#1e1f22")
        draw = ImageDraw.Draw(image)

        # Опит за вграждане на шрифтове (ползваме системни или базовия, ако няма налични)
        try:
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_sub = ImageFont.truetype("arial.ttf", 20)
            font_level = ImageFont.truetype("arial.ttf", 45)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_level = ImageFont.load_default()

        # 1. Изтегляне и вграждане на Аватара на потребителя
        avatar_url = member.display_avatar.with_format("png").url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status == 200:
                    avatar_bytes = await response.read()
                    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                    avatar_img = avatar_img.resize((120, 120))
                    
                    # Правим аватара кръгъл
                    mask = Image.new("L", (120, 120), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, 120, 120), fill=255)
                    
                    image.paste(avatar_img, (30, 30), mask)

        # 2. Изписване на текстовете върху картичката
        # Име на потребителя
        draw.text((180, 40), member.display_name, fill="#ffffff", font=font_title)
        # Текст за левъла
        draw.text((180, 80), f"Just leveled up!", fill="#b5bac1", font=font_sub)
        
        # Голям брандиран надпис за НИВОТО вдясно
        draw.text((450, 45), f"LVL", fill="#5865f2", font=font_sub)
        draw.text((450, 65), str(new_level), fill="#57f287", font=font_level)

        # 3. Нарисуване на декоративен златен прогрес бар най-отдолу
        # Фон на бара
        draw.rounded_rectangle([(180, 125), (550, 137)], radius=6, fill="#313338")
        # Пълен бар (тъй като току що е вдигнал ниво, показваме го зареден в зелено/синьо)
        draw.rounded_rectangle([(180, 125), (520, 137)], radius=6, fill="#5865f2")

        # Запазваме изображението в паметта (BytesIO), за да не цапаме диска с файлове
        final_buffer = io.BytesIO()
        image.save(final_buffer, format="PNG")
        final_buffer.seek(0)
        return final_buffer

    async def generate_level_card(self, member, new_level):
        """ Генерира красива графична картичка за Level Up, ползвайки твоя шрифт """
        W, H = 600, 180
        image = Image.new("RGBA", (W, H), "#1e1f22")
        draw = ImageDraw.Draw(image)

        # Използваме точно твоя път до шрифта, който си настроил
        try:
            font_title = ImageFont.truetype("fonts/FontsFree-Net-arial-bold.ttf", 28)
            font_sub   = ImageFont.truetype("fonts/FontsFree-Net-arial-bold.ttf", 20)
            font_level = ImageFont.truetype("fonts/FontsFree-Net-arial-bold.ttf", 45)
        except Exception as e:
            print(f"⚠️ Шрифтовете не заредиха, ползвам default: {e}")
            font_title = font_sub = font_level = ImageFont.load_default()

        # 1. Изтегляне и вграждане на Аватара
        avatar_url = member.display_avatar.with_format("png").url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status == 200:
                    avatar_bytes = await response.read()
                    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                    avatar_img = avatar_img.resize((120, 120))
                    
                    mask = Image.new("L", (120, 120), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, 120, 120), fill=255)
                    
                    image.paste(avatar_img, (30, 30), mask)

        # 2. Изписване на текстовете върху картичката
        draw.text((180, 40), member.display_name, fill="#ffffff", font=font_title)
        draw.text((180, 80), f"Just leveled up!", fill="#b5bac1", font=font_sub)
        
        draw.text((450, 45), f"LVL", fill="#5865f2", font=font_sub)
        draw.text((450, 65), str(new_level), fill="#57f287", font=font_level)

        # 3. Модерен заоблен прогрес бар (зареден)
        draw.rounded_rectangle([(180, 125), (550, 137)], radius=6, fill="#313338")
        draw.rounded_rectangle([(180, 125), (520, 137)], radius=6, fill="#5865f2")

        final_buffer = io.BytesIO()
        image.save(final_buffer, format="PNG")
        final_buffer.seek(0)
        return final_buffer

    async def process_level_up(self, member, guild, entry, old_level, new_level, cfg, current_channel=None):
        if new_level <= old_level:
            return

        # 1. Проверка дали известията са включени глобално
        if not cfg.get('enable_levelup_message', True):
            return

        levelup_type = cfg.get('levelup_type', 'channel') # channel, dm, current, disabled
        if levelup_type == 'disabled':
            return

        # Намиране къде да изпратим известието спрямо настройките в дешборда
        target = None
        if levelup_type == 'dm':
            target = member
        elif levelup_type == 'current' and current_channel:
            target = current_channel
        elif levelup_type == 'channel':
            ch_id = cfg.get('level_channel')
            if ch_id:
                target = self.bot.get_channel(int(ch_id))
            if not target:
                target = guild.system_channel

        # 2. Генериране и изпращане на картичката
        if target:
            try:
                # Генерираме снимката на заден план
                card_buffer = await self.generate_level_card(member, new_level)
                discord_file = discord.File(fp=card_buffer, filename=f"levelup_{member.id}.png")
                
                # Форматираме текста над картинката
                custom_msg = cfg.get('levelup_message', "GG {user.mention}! You just leveled up!")
                formatted_msg = custom_msg.replace("{user.mention}", member.mention)\
                                          .replace("{user.name}", member.display_name)\
                                          .replace("{level}", str(new_level))
                
                # Изпращаме съобщението с прикачения файл
                await target.send(content=formatted_msg, file=discord_file)
                
            except Exception as e:
                print(f"❌ Грешка при изпращане на картичка за ниво: {e}")

        # 3. Автоматично раздаване на Level Roles (остава непроменено)
        lr = load('levelroles.json').get(str(guild.id), {})
        role_id = lr.get(str(new_level))
        if role_id:
            role = guild.get_role(role_id)
            if role:
                try: await member.add_roles(role)
                except: pass

    # ── Текстово XP ────────────────────────────────────────
    async def add_text_xp(self, message):
        uid = str(message.author.id)
        gid = str(message.guild.id)
        now = datetime.now()
        key = f"{gid}:{uid}"

        cfg = self.get_guild_config(gid)
        
        if not cfg.get('enable_message_xp', True):
            return

        if message.channel.id in cfg.get('no_xp_channels', []):
            return
        if any(role.id in cfg.get('no_xp_roles', []) for role in message.author.roles):
            return

        cooldown_sec = cfg.get('message_cooldown', 60)
        if key in XP_CD and (now - XP_CD[key]).total_seconds() < cooldown_sec:
            return
        XP_CD[key] = now

        levels = load('levels.json')
        levels.setdefault(gid, {})
        entry = levels[gid].get(uid, {'xp': 0, 'name': message.author.display_name})
        old_level = get_level(entry['xp'])
        
        min_xp = cfg.get('min_xp', 15)
        max_xp = cfg.get('max_xp', 25)
        xp_to_add = random.randint(min_xp, max_xp)

        multiplier = self.calculate_multipliers(message.author, message.channel, cfg)

        if cfg.get('enable_effort_booster', False):
            req_words = cfg.get('effort_words', 20)
            req_chars = cfg.get('effort_chars', 100)
            effort_mult = cfg.get('effort_multiplier', 1.2)
            if len(message.content.split()) >= req_words and len(message.content) >= req_chars:
                multiplier *= effort_mult

        entry['xp'] += round(xp_to_add * multiplier)
        entry['name'] = message.author.display_name
        new_level = get_level(entry['xp'])
        
        levels[gid][uid] = entry
        save('levels.json', levels)
        if hasattr(builtins, "refresh_bot_cache"): builtins.refresh_bot_cache()

        await self.process_level_up(message.author, message.guild, entry, old_level, new_level, cfg, current_channel=message.channel)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        await self.add_text_xp(message)

    # ── Гласово (Voice) XP ──────────────────────────────────
    @tasks.loop(seconds=15)
    async def voice_xp_ticker(self):
        now = datetime.now()
        levels_data = None
        
        for guild in self.bot.guilds:
            gid = str(guild.id)
            cfg = self.get_guild_config(gid)
            
            if not cfg.get('enable_voice_xp', False):
                continue
                
            voice_cooldown = cfg.get('voice_cooldown', 60)
            min_xp = cfg.get('voice_min_xp', 10)
            max_xp = cfg.get('voice_max_xp', 20)
            min_members = cfg.get('voice_min_members', 2)
            ignore_muted = cfg.get('voice_ignore_muted', True)

            for vc in guild.voice_channels:
                active_members = [m for m in vc.members if not m.bot]
                if len(active_members) < min_members:
                    continue

                for member in active_members:
                    if ignore_muted and (member.voice.self_mute or member.voice.self_deaf or member.voice.mute or member.voice.deaf):
                        continue
                    if any(role.id in cfg.get('no_xp_roles', []) for role in member.roles):
                        continue

                    v_key = f"{gid}:{member.id}"
                    if v_key in VOICE_LAST_CHECK:
                        if (now - VOICE_LAST_CHECK[v_key]).total_seconds() < voice_cooldown:
                            continue
                            
                    VOICE_LAST_CHECK[v_key] = now

                    if levels_data is None:
                        levels_data = load('levels.json')
                    
                    levels_data.setdefault(gid, {})
                    entry = levels_data[gid].get(str(member.id), {'xp': 0, 'name': member.display_name})
                    old_level = get_level(entry['xp'])
                    
                    base_xp = random.randint(min_xp, max_xp)
                    mult = self.calculate_multipliers(member, vc, cfg)
                    
                    entry['xp'] += round(base_xp * mult)
                    entry['name'] = member.display_name
                    new_level = get_level(entry['xp'])
                    
                    levels_data[gid][str(member.id)] = entry
                    await self.process_level_up(member, guild, entry, old_level, new_level, cfg)

        if levels_data is not None:
            save('levels.json', levels_data)
            if hasattr(builtins, "refresh_bot_cache"): builtins.refresh_bot_cache()

    @voice_xp_ticker.before_loop
    async def before_voice_ticker(self):
        await self.bot.wait_until_ready()

    # ── Слаш Команди ───────────────────────────────────────
    @app_commands.command(name="rank", description="View your or someone's rank")
    @app_commands.describe(member="Who to check")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        gid, uid = str(interaction.guild.id), str(member.id)
        levels = load('levels.json')
        entry = levels.get(gid, {}).get(uid, {'xp': 0})
        xp = entry['xp']
        level, cur, needed = xp_progress(xp)
        guild_data = levels.get(gid, {})
        sorted_users = sorted(guild_data.items(), key=lambda x: x[1]['xp'], reverse=True)
        rank_pos = next((i+1 for i,(id,_) in enumerate(sorted_users) if id == uid), '?')
        
        em = discord.Embed(color=member.color or discord.Color.purple())
        em.set_author(name=f"{member.display_name}'s Rank", icon_url=member.display_avatar.url)
        em.add_field(name="🏆 Rank",  value=f"#{rank_pos}")
        em.add_field(name="⭐ Level", value=f"**{level}**")
        em.add_field(name="✨ XP",    value=f"{xp:,}")
        em.add_field(name="📊 Progress", value=f"`{bar(cur, needed)}` {cur}/{needed} XP", inline=False)
        em.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=em)

    @app_commands.command(name="leaderboard", description="Show the level leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)
        levels = load('levels.json')
        guild_data = levels.get(gid, {})
        if not guild_data:
            return await interaction.response.send_message(embed=err("No level data yet!"))
        sorted_users = sorted(guild_data.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
        em = discord.Embed(title="⭐ Level Leaderboard", color=discord.Color.gold())
        desc = ""
        for i, (uid, data) in enumerate(sorted_users):
            level = get_level(data['xp'])
            desc += f"{medal(i)} **{data['name']}** — Level {level} ({data['xp']:,} XP)\n"
        em.description = desc
        await interaction.response.send_message(embed=em)

    @app_commands.command(name="setlevelchannel", description="Set channel for level-up messages")
    @app_commands.describe(channel="The channel")
    @app_commands.default_permissions(administrator=True)
    async def setlevelchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        cfg = load('config.json')
        cfg.setdefault(str(interaction.guild.id), {})['level_channel'] = channel.id
        save('config.json', cfg)
        if hasattr(builtins, "refresh_bot_cache"): builtins.refresh_bot_cache()
        await interaction.response.send_message(embed=ok("Level Channel Set!", f"Level-up messages → {channel.mention}"))

    @app_commands.command(name="levelrole", description="Manage level roles")
    @app_commands.describe(action="add / remove / list", level="Level number", role="Role to give")
    @app_commands.default_permissions(administrator=True)
    async def levelrole(self, interaction: discord.Interaction, action: str, level: int = None, role: discord.Role = None):
        gid = str(interaction.guild.id)
        lr = load('levelroles.json')
        lr.setdefault(gid, {})
        if action == 'add':
            if not level or not role:
                return await interaction.response.send_message(embed=err("Provide level and role!"))
            lr[gid][str(level)] = role.id
            save('levelroles.json', lr)
            await interaction.response.send_message(embed=ok(f"Level Role Set!", f"{role.mention} given at **Level {level}**"))
        elif action == 'remove':
            if not level:
                return await interaction.response.send_message(embed=err("Provide a level!"))
            if lr[gid].pop(str(level), None):
                save('levelroles.json', lr)
                await interaction.response.send_message(embed=ok("Removed!"))
            else:
                await interaction.response.send_message(embed=err("No role for that level!"))
        elif action == 'list':
            if not lr[gid]:
                return await interaction.response.send_message(embed=info("Level Roles", "No level roles set!"))
            em = discord.Embed(title="🎭 Level Roles", color=discord.Color.purple())
            desc = ""
            for lvl, rid in sorted(lr[gid].items(), key=lambda x: int(x[0])):
                role_obj = interaction.guild.get_role(rid)
                desc += f"Level **{lvl}** → {role_obj.mention if role_obj else f'<@&{rid}>'}\n"
            em.description = desc
            await interaction.response.send_message(embed=em)
        else:
            await interaction.response.send_message(embed=err("Use `add`, `remove`, or `list`"))

async def setup(bot):
    await bot.add_cog(Leveling(bot))
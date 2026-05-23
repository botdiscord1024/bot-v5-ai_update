from flask import Flask, render_template_string, current_app, request, jsonify, redirect, url_for
import json
import os

app = Flask(__name__)

def load(f):
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}

def save(f, d):
    json.dump(d, open(f, 'w', encoding='utf-8'), indent=2)

def xp_for_level(level):
    return 5 * (level ** 2) + 50 * level + 100

def total_xp_for_level(level):
    return sum(xp_for_level(i) for i in range(level))

def get_level_from_xp(xp):
    level = 0
    while xp >= total_xp_for_level(level + 1):
        level += 1
        if level > 500: 
            break
    return level

def get_gid():
    bot = current_app.config.get('BOT')
    if bot and hasattr(bot, 'cached_data'):
        # Модерацията вече е с най-висок приоритет при проверка на Guild ID
        for key in ['moderation', 'levels', 'counting', 'smashkarts', 'story']:
            d = bot.cached_data.get(key, {})
            if d:
                return list(d.keys())[0]
    return None

def resolve_name(uid, lvl_data):
    bot = current_app.config.get('BOT')
    if uid in lvl_data and 'name' in lvl_data[uid]:
        return lvl_data[uid]['name']
    if bot:
        user = bot.get_user(int(uid))
        if user: 
            return user.display_name
    return f"User {uid}"

def render(route, title, desc, body):
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>{{ title }}</title>
      <link href="https://fonts.googleapis.com/css2?family=GG+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
      <style>
        :root { --b-dark: #1e1f22; --b-mid: #2b2d31; --b-light: #313338; --b-nav: #111214; --accent: #5865f2; --text: #f2f3f5; --sub: #b5bac1; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'GG Sans', sans-serif; }
        body { display: flex; height: 100vh; background: var(--b-dark); color: var(--text); overflow: hidden; }
        
        .sidebar { width: 260px; background: var(--b-nav); padding: 24px 12px; display: flex; flex-direction: column; gap: 4px; }
        .brand { font-size: 18px; font-weight: 700; padding: 0 12px 20px 12px; border-bottom: 1px solid #2e3035; margin-bottom: 16px; color: #fff; }
        .nav-item { display: flex; align-items: center; padding: 10px 12px; border-radius: 4px; color: var(--sub); text-decoration: none; font-size: 14px; font-weight: 500; transition: .15s; }
        .nav-item:hover { background: #35373c; color: #fff; }
        .nav-item.active { background: var(--accent); color: #fff; }
        
        .main { flex: 1; display: flex; flex-direction: column; height: 100vh; background: var(--b-dark); }
        .header { background: var(--b-mid); padding: 20px 32px; border-bottom: 1px solid #1f2023; }
        .header h1 { font-size: 24px; font-weight: 700; color: #fff; }
        .header p { font-size: 14px; color: var(--sub); margin-top: 4px; }
        
        .content { flex: 1; padding: 32px; overflow-y: auto; }
        .card { background: var(--b-mid); border-radius: 8px; border: 1px solid #232428; padding: 24px; margin-bottom: 24px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #3f4248; padding-bottom: 16px; margin-bottom: 20px; }
        .card-header h3 { font-size: 18px; color: #fff; }
        .card-header p { font-size: 13px; color: var(--sub); margin-top: 2px; }
        
        /* Form Controls */
        .field { margin-bottom: 20px; }
        .field label { display: block; font-size: 12px; font-weight: 700; color: var(--sub); text-transform: uppercase; margin-bottom: 8px; }
        .field input, .field select, .field textarea { width: 100%; background: var(--b-dark); border: 1px solid #111214; padding: 10px; border-radius: 4px; color: #fff; font-size: 14px; }
        .field input:focus, .field select:focus, .field textarea:focus { border-color: var(--accent); outline: none; }
        
        /* Toggles */
        .toggle-row { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid #2e3035; }
        .toggle-row:last-child { border-bottom: none; }
        .toggle-info h4 { margin: 0; font-size: 15px; color: #fff; }
        .toggle-info p { margin: 4px 0 0 0; font-size: 13px; color: var(--sub); }
        .toggle { position: relative; display: inline-block; width: 48px; height: 26px; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #4e5058; transition: .2s; border-radius: 34px; }
        .toggle-slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 4px; bottom: 4px; background-color: white; transition: .2s; border-radius: 50%; }
        input:checked + .toggle-slider { background-color: #23a55a; }
        input:checked + .toggle-slider:before { transform: translateX(22px); }
        
        /* Leaderboards & Lists */
        .lb-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--b-light); border-radius: 4px; margin-bottom: 8px; }
        .lb-name { display: flex; align-items: center; font-size: 14px; }
        .lb-val { font-size: 14px; color: var(--sub); font-weight: 600; }
        .lb-empty { text-align: center; color: var(--sub); padding: 20px; font-size: 14px; }
        
        .btn { display: inline-block; background: var(--accent); color: #fff; border: none; padding: 10px 20px; border-radius: 4px; font-size: 14px; font-weight: 500; cursor: pointer; transition: .15s; text-decoration: none; }
        .btn:hover { background: #4752c4; }
        .btn-primary { background: var(--accent); }
        .btn-save-row { display: flex; justify-content: flex-end; margin-top: 12px; }
      </style>
    </head>
    <body>
      <div class="sidebar">
        <div class="brand">👑 Admin Panel</div>
        <a href="/moderation" class="nav-item {% if route=='moderation' %}active{% endif %}">🛡️ Moderation</a>
        <a href="/levels" class="nav-item {% if route=='levels' %}active{% endif %}">⭐ Leveling System</a>
        <a href="/counting" class="nav-item {% if route=='counting' %}active{% endif %}">🔢 Counting Game</a>
        <a href="/ai-settings" class="nav-item {% if route=='ai-settings' %}active{% endif %}">🤖 AI Assistant</a>
        <a href="/smashkarts" class="nav-item {% if route=='smashkarts' %}active{% endif %}">🏎️ Smash Karts</a>
        <a href="/story" class="nav-item {% if route=='story' %}active{% endif %}">📖 Story Mode</a>
      </div>
      <div class="main">
        <div class="header">
          <h1>{{ title }}</h1>
          <p>{{ desc }}</p>
        </div>
        <div class="content">
          {{ body|safe }}
        </div>
      </div>
    </body>
    </html>
    """, route=route, title=title, desc=desc, body=body)

# ══════════════════════════════════════════════════════════
#  MODERATION PAGE (НАЧАЛНА СТРАНИЦА)
# ══════════════════════════════════════════════════════════
@app.route('/')
@app.route('/moderation')
def moderation():
    gid = get_gid() or 'default'
    cfg = load('config.json').get(gid, {})
    
    automod_on = 'checked' if cfg.get('automod_enabled', False) else ''
    invite_block_on = 'checked' if cfg.get('block_invites', False) else ''
    banned_words = cfg.get('banned_words', "")
    log_channel = cfg.get('log_channel', "")
    
    body = f"""
    <form id="modForm" onsubmit="saveMod(event)">
    <div class="card">
      <div class="card-header"><div><h3>Auto-Moderation</h3><p>Configure automated filter rules</p></div></div>
      <div class="card-body">
        <div class="toggle-row">
          <div class="toggle-info"><h4>Enable Word Filter (AutoMod)</h4><p>Scan and delete messages containing blacklisted phrases</p></div>
          <label class="toggle"><input type="checkbox" id="automod_enabled" {automod_on}> <span class="toggle-slider"></span></label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Block Server Invites</h4><p>Automatically remove raw Discord server invitation links</p></div>
          <label class="toggle"><input type="checkbox" id="block_invites" {invite_block_on}> <span class="toggle-slider"></span></label>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><div><h3>Logging & Blacklists</h3><p>Manage system logging channels and terms</p></div></div>
      <div class="card-body">
        <div class="field"><label>Mod Log Channel ID</label><input type="text" id="log_channel" value="{log_channel}" placeholder="123456789012345678"></div>
        <div class="field"><label>Banned Words List (comma separated)</label><textarea id="banned_words" rows="3" placeholder="badword1, badword2, toxic">{banned_words}</textarea></div>
      </div>
    </div>
    <div class="btn-save-row"><button type="submit" class="btn btn-primary">Save Moderation Config</button></div>
    </form>

    <div id="toast_mod" style="display:none;position:fixed;bottom:24px;right:24px;background:#23a55a;color:#fff;padding:12px 20px;border-radius:6px;font-weight:600;font-size:14px;z-index:9999;">✅ Moderation configs saved successfully!</div>

    <script>
    function saveMod(e){{
      e.preventDefault();
      fetch('/api/moderation/save', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          automod_enabled: document.getElementById('automod_enabled').checked,
          block_invites: document.getElementById('block_invites').checked,
          log_channel: document.getElementById('log_channel').value,
          banned_words: document.getElementById('banned_words').value
        }})
      }}).then(() => {{
         var t = document.getElementById('toast_mod'); t.style.display='block'; setTimeout(()=>t.style.display='none',2500);
      }});
    }}
    </script>
    """
    return render('moderation', '🛡️ Moderation Settings', 'Control automod configurations, blacklisted word definitions, and execution protocols', body)

@app.route('/api/moderation/save', methods=['POST'])
def api_moderation_save():
    gid = get_gid() or 'default'
    cfg = load('config.json')
    cfg.setdefault(gid, {}).update(request.json)
    save('config.json', cfg)
    import builtins
    if hasattr(builtins, 'refresh_bot_cache'): 
        builtins.refresh_bot_cache()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════
#  LEVELING PAGE
# ══════════════════════════════════════════════════════════
@app.route('/levels')
def levels():
    gid = get_gid() or 'default'
    cfg = load('config.json').get(gid, {})
    
    lvl_msg_on = 'checked' if cfg.get('enable_levelup_message', True) else ''
    vc_xp_on = 'checked' if cfg.get('enable_voice_xp', True) else ''
    
    type_opt = cfg.get('levelup_type', 'channel')
    opts = f"""
    <option value="channel" {'selected' if type_opt=='channel' else ''}>Specific Channel</option>
    <option value="current" {'selected' if type_opt=='current' else ''}>Current Channel</option>
    <option value="dm" {'selected' if type_opt=='dm' else ''}>Direct Message (DM)</option>
    <option value="disabled" {'selected' if type_opt=='disabled' else ''}>Disabled</option>
    """
    
    msg_val = cfg.get('levelup_message', "GG {{user.mention}}! You just leveled up to **Level {{level}}**!")
    ch_val = cfg.get('level_channel', "")

    lvl_data = load('levels.json').get(gid, {})
    sorted_users = sorted(lvl_data.items(), key=lambda x: x[1].get('xp', 0) if isinstance(x[1], dict) else x[1], reverse=True)[:10]
    
    lb_rows = ""
    for rank, (uid, data) in enumerate(sorted_users, 1):
        xp = data.get('xp', 0) if isinstance(data, dict) else data
        lvl = get_level_from_xp(xp)
        name = resolve_name(uid, lvl_data)
        lb_rows += f"""
        <div class="lb-row">
            <div class="lb-name"><b>#{rank}</b> &nbsp; {name}</div>
            <div class="lb-val">Lvl {lvl} &nbsp;<span style="color:#4e5058;font-weight:normal;">({xp} XP)</span></div>
        </div>"""
    if not lb_rows:
        lb_rows = '<div class="lb-empty">No level data available yet.</div>'

    body = f"""
    <form id="lvlForm" onsubmit="saveLvl(event)">
    <div class="card">
      <div class="card-header"><div><h3>General Settings</h3><p>Configure automated level alerts and behaviors</p></div></div>
      <div class="card-body">
        <div class="toggle-row">
          <div class="toggle-info"><h4>Level Up Messages</h4><p>Enable announcements when server members level up</p></div>
          <label class="toggle"><input type="checkbox" id="enable_levelup_message" {lvl_msg_on}> <span class="toggle-slider"></span></label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Voice Channel XP</h4><p>Award XP passively to members active in voice chats</p></div>
          <label class="toggle"><input type="checkbox" id="enable_voice_xp" {vc_xp_on}> <span class="toggle-slider"></span></label>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><div><h3>Alert Behavior & Templates</h3><p>Customize where and how leveling up is displayed</p></div></div>
      <div class="card-body">
        <div class="field"><label>Alert Destination</label><select id="levelup_type">{opts}</select></div>
        <div class="field"><label>Target Channel ID (Only if Specific Channel is active)</label><input type="text" id="level_channel" value="{ch_val}" placeholder="123456789012345678"></div>
        <div class="field"><label>Custom Announcement Message</label><textarea id="levelup_message" rows="3">{msg_val}</textarea></div>
      </div>
    </div>
    <div class="btn-save-row"><button type="submit" class="btn btn-primary">Save Configuration</button></div>
    </form>

    <div class="card" style="margin-top:24px">
      <div class="card-header"><h3>🏆 Server Top 10 Leaderboard</h3></div>
      <div class="card-body">{lb_rows}</div>
    </div>

    <div id="toast" style="display:none;position:fixed;bottom:24px;right:24px;background:#23a55a;color:#fff;padding:12px 20px;border-radius:6px;font-weight:600;font-size:14px;z-index:9999;">✅ Leveling configs saved successfully!</div>

    <script>
    function saveLvl(e){{
      e.preventDefault();
      fetch('/api/levels/save', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          enable_levelup_message: document.getElementById('enable_levelup_message').checked,
          enable_voice_xp: document.getElementById('enable_voice_xp').checked,
          levelup_type: document.getElementById('levelup_type').value,
          level_channel: document.getElementById('level_channel').value,
          levelup_message: document.getElementById('levelup_message').value
        }})
      }}).then(() => {{
         var t = document.getElementById('toast'); t.style.display='block'; setTimeout(()=>t.style.display='none',2500);
      }});
    }}
    </script>
    """
    return render('levels', '⭐ Leveling System', 'Manage configurations and track active user XP records', body)

@app.route('/api/levels/save', methods=['POST'])
def api_levels_save():
    gid = get_gid() or 'default'
    cfg = load('config.json')
    cfg.setdefault(gid, {}).update(request.json)
    save('config.json', cfg)
    import builtins
    if hasattr(builtins, 'refresh_bot_cache'): 
        builtins.refresh_bot_cache()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════
#  COUNTING GAME PAGE
# ══════════════════════════════════════════════════════════
@app.route('/counting')
def counting():
    gid = get_gid() or 'default'
    c_data = load('counting.json').get(gid, {})
    
    current_count = c_data.get('current', 0)
    high_score = c_data.get('highest', 0)
    last_user_id = c_data.get('last_user', 'None')
    
    body = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px;">
      <div class="card" style="margin:0; text-align:center;">
        <h4 style="color:#b5bac1;text-transform:uppercase;font-size:12px;letter-spacing:1px;">Current Counter</h4>
        <h1 style="font-size:48px;color:#5865f2;margin-top:10px;">{current_count}</h1>
      </div>
      <div class="card" style="margin:0; text-align:center;">
        <h4 style="color:#b5bac1;text-transform:uppercase;font-size:12px;letter-spacing:1px;">Server High Score</h4>
        <h1 style="font-size:48px;color:#23a55a;margin-top:10px;">{high_score}</h1>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><h3>Active Session Data</h3></div>
      <div class="card-body">
        <p style="font-size:14px;color:#b5bac1;">Last Submitting User ID: <b style="color:#fff;">{last_user_id}</b></p>
        <p style="font-size:13px;color:#4e5058;margin-top:8px;">Note: To reset numbers or shift channels, execute the native slash tools on Discord.</p>
      </div>
    </div>
    """
    return render('counting', '🔢 Counting System', 'Real-time synchronization data tracking counting parameters', body)

# ══════════════════════════════════════════════════════════
#  AI SETTINGS & CUSTOM EMOJIS
# ══════════════════════════════════════════════════════════
@app.route('/ai-settings')
def ai_settings():
    gid = get_gid() or 'default'
    cfg = load('config.json').get(gid, {})
    
    ai_on = 'checked' if cfg.get('ai_enabled', True) else ''
    reply_on = 'checked' if cfg.get('ai_reply_on_mention', True) else ''
    emojis_on = 'checked' if cfg.get('ai_auto_emojis', True) else ''
    
    custom_emojis = cfg.get('custom_external_emojis', {})
    emoji_rows = ''
    for name, url in custom_emojis.items():
        emoji_rows += f"""
        <div class="lb-row">
            <div class="lb-name"><img src="{url}" style="width:24px;height:24px;border-radius:4px;margin-right:8px;vertical-align:middle"><b>:{name}:</b></div>
            <div class="lb-val"><button onclick="deleteEmoji('{name}')" style="background:#ed4245;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer">Remove</button></div>
        </div>"""
    if not emoji_rows:
        emoji_rows = '<div class="lb-empty">No custom external emojis added yet</div>'

    body = f"""
    <form id="aiForm" onsubmit="saveAiSettings(event)">
    <div class="card">
      <div class="card-header">
        <div><h3>AI Control Panel</h3><p>Manage the behavior of your bot's smart AI assistant</p></div>
        <label class="toggle"><input type="checkbox" id="ai_enabled" {ai_on}><span class="toggle-slider"></span></label>
      </div>
      <div class="card-body">
        <div class="toggle-row">
          <div class="toggle-info"><h4>Reply on Mention / Reply</h4><p>Should the AI answer when someone pings or replies to its messages (like Level Up alerts)?</p></div>
          <label class="toggle"><input type="checkbox" id="ai_reply_on_mention" {reply_on}><span class="toggle-slider"></span></label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Auto Emoji Reactions</h4><p>Allow the AI to automatically place smart emojis on messages</p></div>
          <label class="toggle"><input type="checkbox" id="ai_auto_emojis" {emojis_on}><span class="toggle-slider"></span></label>
        </div>
      </div>
    </div>
    <div class="btn-save-row">
      <button type="submit" class="btn btn-primary">Save Settings</button>
    </div>
    </form>

    <div class="card" style="margin-top:24px">
      <div class="card-header"><h3>✨ Add External Emojis (Not in Discord Guild)</h3></div>
      <div class="card-body">
        <div style="display:grid;grid-template-columns:1fr 2fr;gap:12px;margin-bottom:12px">
          <div class="field"><label>Emoji Name</label><input type="text" id="em_name" placeholder="pepe_smile"></div>
          <div class="field"><label>Image URL (PNG/JPG Link)</label><input type="text" id="em_url" placeholder="https://example.com/image.png"></div>
        </div>
        <button onclick="addEmoji()" class="btn btn-primary" style="background:#57f287;color:black;font-weight:bold;">Add External Emoji</button>
        
        <div style="margin-top:20px">
            <h4>Current Custom External Emojis:</h4>
            {emoji_rows}
        </div>
      </div>
    </div>

    <div id="toast" style="display:none;position:fixed;bottom:24px;right:24px;background:#57f287;color:#000;padding:12px 20px;border-radius:6px;font-weight:600;font-size:14px;z-index:9999;">✅ Updated!</div>

    <script>
    function showToast(){{
      var t=document.getElementById('toast'); t.style.display='block'; setTimeout(()=>t.style.display='none',2500);
    }}
    function saveAiSettings(e){{
      e.preventDefault();
      fetch('/api/ai/save',{{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{
          ai_enabled: document.getElementById('ai_enabled').checked,
          ai_reply_on_mention: document.getElementById('ai_reply_on_mention').checked,
          ai_auto_emojis: document.getElementById('ai_auto_emojis').checked
        }})
      }}).then(()=>showToast());
    }}
    function addEmoji(){{
      var name = document.getElementById('em_name').value;
      var url = document.getElementById('em_url').value;
      if(!name || !url) return alert('Please fill both fields!');
      fetch('/api/ai/emoji/add',{{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{name:name, url:url}})
      }}).then(()=>location.reload());
    }}
    function deleteEmoji(name){{
      fetch('/api/ai/emoji/delete',{{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{name:name}})
      }}).then(()=>location.reload());
    }}
    </script>
    """
    return render('ai-settings', 'AI Assistant', 'Configure AI actions and external emojis', body)

@app.route('/api/ai/save', methods=['POST'])
def api_ai_save():
    gid = get_gid() or 'default'
    cfg = load('config.json')
    cfg.setdefault(gid, {}).update(request.json)
    save('config.json', cfg)
    import builtins
    if hasattr(builtins, 'refresh_bot_cache'): 
        builtins.refresh_bot_cache()
    return jsonify({'ok':True})

@app.route('/api/ai/emoji/add', methods=['POST'])
def api_ai_emoji_add():
    gid = get_gid() or 'default'
    cfg = load('config.json')
    cfg.setdefault(gid, {}).setdefault('custom_external_emojis', {})[request.json['name']] = request.json['url']
    save('config.json', cfg)
    import builtins
    if hasattr(builtins, 'refresh_bot_cache'): 
        builtins.refresh_bot_cache()
    return jsonify({'ok':True})

@app.route('/api/ai/emoji/delete', methods=['POST'])
def api_ai_emoji_delete():
    gid = get_gid() or 'default'
    cfg = load('config.json')
    if gid in cfg and 'custom_external_emojis' in cfg[gid]:
        cfg[gid]['custom_external_emojis'].pop(request.json['name'], None)
        save('config.json', cfg)
    import builtins
    if hasattr(builtins, 'refresh_bot_cache'): 
        builtins.refresh_bot_cache()
    return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════
#  SMASH KARTS PAGE
# ══════════════════════════════════════════════════════════
@app.route('/smashkarts')
def smashkarts():
    gid = get_gid() or 'default'
    sk_data = load('smashkarts.json').get(gid, {})
    sorted_sk = sorted(sk_data.items(), key=lambda x: x[1].get('wins', 0) if isinstance(x[1], dict) else 0, reverse=True)[:10]
    
    lb_rows = ""
    for rank, (uid, data) in enumerate(sorted_sk, 1):
        wins = data.get('wins', 0)
        lb_rows += f"""
        <div class="lb-row">
            <div class="lb-name"><b>#{rank}</b> &nbsp; User {uid}</div>
            <div class="lb-val" style="color:#57f287;">{wins} Wins 🏎️</div>
        </div>"""
    if not lb_rows:
        lb_rows = '<div class="lb-empty">No active matches recorded yet.</div>'

    body = f"""<div class="card"><div class="card-header"><h3>🏎️ Competitive Leaderboard</h3></div><div class="card-body">{lb_rows}</div></div>"""
    return render('smashkarts', '🏎️ Smash Karts Statistics', 'Global race metrics and win record compilations', body)

# ══════════════════════════════════════════════════════════
#  STORY MODE PAGE
# ══════════════════════════════════════════════════════════
@app.route('/story')
def story():
    gid = get_gid() or 'default'
    st_data = load('story.json').get(gid, {})
    
    body = f"""
    <div class="card">
      <div class="card-header"><h3>📖 Ongoing Story Session</h3></div>
      <div class="card-body">
        <p style="font-size:14px;color:#b5bac1;">Active Authors/Contributors recorded: <b style="color:#fff;">{len(st_data)} members</b></p>
        <p style="font-size:13px;color:#4e5058;margin-top:12px;">Full adventure configurations are generated directly via storytelling interactions inside discord channels.</p>
      </div>
    </div>
    """
    return render('story', '📖 Story Adventure Mode', 'Track server generated text simulations and interactive histories', body)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

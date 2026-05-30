import os
import discord
from discord.ext import commands
import json

# ================= TOKEN =================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN이 설정되지 않았습니다.")

# ================= BOT =================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

DEFAULT_ADMIN_ID = 1503121370945683626

# ================= DATA =================
def load():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"eco": {}, "admins": []}
    return {"eco": {}, "admins": []}

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load()

# ================= ADMIN SYSTEM =================
def get_admins():
    return set(data.get("admins", [])) | {DEFAULT_ADMIN_ID}

def save_admins(admins):
    data["admins"] = list(admins)
    save(data)

def is_admin(user_id: int):
    return user_id in get_admins()

# ================= USER SYSTEM =================
def get_user(guild_id, user_id):
    guild = data["eco"].setdefault(str(guild_id), {})
    user = guild.setdefault(str(user_id), {
        "wallet": 0,
        "bank": 0,
        "exp": 0,
        "level": 1
    })
    return user

def set_user(guild_id, user_id, user):
    data["eco"].setdefault(str(guild_id), {})[str(user_id)] = user
    save(data)

# ================= LEVEL SYSTEM =================
def add_exp(user, guild_id, user_id, amount):
    user["exp"] += amount
    leveled = False

    while user["exp"] >= user["level"] * 100:
        user["exp"] -= user["level"] * 100
        user["level"] += 1
        leveled = True

    set_user(guild_id, user_id, user)
    return leveled

# ================= READY (핵심 1개만 존재) =================
@bot.event
async def on_ready():

    admins = set(data.get("admins", []))
    admins.add(DEFAULT_ADMIN_ID)
    data["admins"] = list(admins)
    save(data)

    await bot.tree.sync()

    print(f"✅ {bot.user} 로그인 완료")

# ================= USER COMMANDS =================
@bot.tree.command(name="돈")
async def money(interaction: discord.Interaction):

    u = get_user(interaction.guild.id, interaction.user.id)

    await interaction.response.send_message(
        f"💰 월렛: {u['wallet']:,}\n"
        f"🏦 은행: {u['bank']:,}\n"
        f"⭐ Lv: {u['level']}\n"
        f"📈 EXP: {u['exp']}/{u['level']*100}"
    )

@bot.tree.command(name="송금")
async def send_money(interaction: discord.Interaction, user: discord.Member, amount: int):

    sender = get_user(interaction.guild.id, interaction.user.id)
    receiver = get_user(interaction.guild.id, user.id)

    if amount <= 0 or sender["wallet"] < amount:
        await interaction.response.send_message("❌ 잔액 부족", ephemeral=True)
        return

    sender["wallet"] -= amount
    receiver["wallet"] += amount

    add_exp(sender, interaction.guild.id, interaction.user.id, 10)

    set_user(interaction.guild.id, interaction.user.id, sender)
    set_user(interaction.guild.id, user.id, receiver)

    await interaction.response.send_message(f"📤 {user.name}에게 {amount:,}원 송금")

@bot.tree.command(name="입금")
async def deposit(interaction: discord.Interaction, amount: int):

    u = get_user(interaction.guild.id, interaction.user.id)

    if amount <= 0 or u["wallet"] < amount:
        await interaction.response.send_message("❌ 실패", ephemeral=True)
        return

    u["wallet"] -= amount
    u["bank"] += amount

    add_exp(u, interaction.guild.id, interaction.user.id, 5)

    set_user(interaction.guild.id, interaction.user.id, u)

    await interaction.response.send_message(f"🏦 {amount:,}원 입금")

@bot.tree.command(name="출금")
async def withdraw(interaction: discord.Interaction, amount: int):

    u = get_user(interaction.guild.id, interaction.user.id)

    if amount <= 0 or u["bank"] < amount:
        await interaction.response.send_message("❌ 실패", ephemeral=True)
        return

    u["bank"] -= amount
    u["wallet"] += amount

    add_exp(u, interaction.guild.id, interaction.user.id, 5)

    set_user(interaction.guild.id, interaction.user.id, u)

    await interaction.response.send_message(f"💸 {amount:,}원 출금")

@bot.tree.command(name="랭킹")
async def ranking(interaction: discord.Interaction):

    guild = data["eco"].get(str(interaction.guild.id), {})

    sorted_users = sorted(
        guild.items(),
        key=lambda x: x[1]["wallet"] + x[1]["bank"] + x[1]["level"] * 1000,
        reverse=True
    )[:10]

    msg = "🏆 TOP 10\n\n"

    for i, (uid, v) in enumerate(sorted_users, 1):
        total = v["wallet"] + v["bank"]
        msg += f"{i}. <@{uid}> | 💰 {total:,} | ⭐ Lv.{v['level']}\n"

    await interaction.response.send_message(msg)

# ================= ADMIN SYSTEM =================
@bot.tree.command(name="관리자임명")
async def add_admin(interaction: discord.Interaction, user: discord.Member):

    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ 권한 없음", ephemeral=True)
        return

    admins = get_admins()
    admins.add(user.id)
    save_admins(admins)

    await interaction.response.send_message(f"👑 {user.name} 관리자 추가됨")

@bot.tree.command(name="관리자해제")
async def remove_admin(interaction: discord.Interaction, user: discord.Member):

    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ 권한 없음", ephemeral=True)
        return

    admins = get_admins()

    if user.id not in admins:
        await interaction.response.send_message("❌ 해당 유저는 관리자가 아님", ephemeral=True)
        return

    admins.discard(user.id)
    save_admins(admins)

    await interaction.response.send_message(f"🚫 {user.name} 관리자 해제됨")

@bot.tree.command(name="지급")
async def give_money(interaction: discord.Interaction, user: discord.Member, amount: int):

    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ 관리자만 사용 가능", ephemeral=True)
        return

    u = get_user(interaction.guild.id, user.id)
    u["wallet"] += amount
    set_user(interaction.guild.id, user.id, u)

    await interaction.response.send_message(f"💰 {user.name} +{amount:,}")

@bot.tree.command(name="경험치지급")
async def give_exp(interaction: discord.Interaction, user: discord.Member, amount: int):

    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ 관리자만 사용 가능", ephemeral=True)
        return

    u = get_user(interaction.guild.id, user.id)

    leveled = add_exp(u, interaction.guild.id, user.id, amount)

    msg = f"⭐ {user.name} +{amount} EXP"
    if leveled:
        msg += "\n🎉 레벨 업!"

    await interaction.response.send_message(msg)

@bot.tree.command(name="레벨설정")
async def set_level(interaction: discord.Interaction, user: discord.Member, level: int):

    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ 관리자만 사용 가능", ephemeral=True)
        return

    u = get_user(interaction.guild.id, user.id)
    u["level"] = max(1, level)
    u["exp"] = 0

    set_user(interaction.guild.id, user.id, u)

    await interaction.response.send_message(f"⭐ {user.name} → Lv.{level}")

# ================= RUN =================
bot.run(TOKEN)
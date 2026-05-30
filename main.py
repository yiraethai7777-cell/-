import os
import discord
from discord import app_commands
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

# ================= DATA =================
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"eco": {}}

def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load()

# ================= USER =================
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
    save()

# ================= LEVEL SYSTEM =================
def add_exp(user, guild_id, user_id, amount):
    user["exp"] += amount

    leveled_up = False

    while user["exp"] >= user["level"] * 100:
        user["exp"] -= user["level"] * 100
        user["level"] += 1
        leveled_up = True

    set_user(guild_id, user_id, user)
    return leveled_up

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} 로그인 완료")

# ================= 돈 확인 =================
@bot.tree.command(name="돈", description="잔액 확인")
async def money(interaction: discord.Interaction):
    u = get_user(interaction.guild.id, interaction.user.id)

    await interaction.response.send_message(
        f"💰 월렛: {u['wallet']:,}\n"
        f"🏦 은행: {u['bank']:,}\n"
        f"⭐ 레벨: {u['level']}\n"
        f"📈 EXP: {u['exp']}/{u['level']*100}"
    )

# ================= 송금 =================
@bot.tree.command(name="송금", description="유저에게 돈 보내기")
@app_commands.describe(user="대상", amount="금액")
async def transfer(interaction: discord.Interaction, user: discord.Member, amount: int):

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

# ================= 은행 =================
@bot.tree.command(name="입금", description="은행에 돈 넣기")
@app_commands.describe(amount="금액")
async def deposit(interaction: discord.Interaction, amount: int):

    u = get_user(interaction.guild.id, interaction.user.id)

    if amount <= 0 or u["wallet"] < amount:
        await interaction.response.send_message("❌ 금액 부족", ephemeral=True)
        return

    u["wallet"] -= amount
    u["bank"] += amount

    add_exp(u, interaction.guild.id, interaction.user.id, 5)

    set_user(interaction.guild.id, interaction.user.id, u)

    await interaction.response.send_message(f"🏦 {amount:,}원 입금 완료")

@bot.tree.command(name="출금", description="은행 돈 출금")
@app_commands.describe(amount="금액")
async def withdraw(interaction: discord.Interaction, amount: int):

    u = get_user(interaction.guild.id, interaction.user.id)

    if amount <= 0 or u["bank"] < amount:
        await interaction.response.send_message("❌ 금액 부족", ephemeral=True)
        return

    u["bank"] -= amount
    u["wallet"] += amount

    add_exp(u, interaction.guild.id, interaction.user.id, 5)

    set_user(interaction.guild.id, interaction.user.id, u)

    await interaction.response.send_message(f"💸 {amount:,}원 출금 완료")

@bot.tree.command(name="이자", description="은행 이자 받기 (5%)")
async def interest(interaction: discord.Interaction):

    u = get_user(interaction.guild.id, interaction.user.id)

    earn = int(u["bank"] * 0.05)

    if earn <= 0:
        await interaction.response.send_message("❌ 받을 이자 없음")
        return

    u["bank"] += earn
    set_user(interaction.guild.id, interaction.user.id, u)

    await interaction.response.send_message(f"💰 이자 +{earn:,}원")

# ================= 랭킹 =================
@bot.tree.command(name="랭킹", description="돈 + 은행 + 레벨 순위")
async def ranking(interaction: discord.Interaction):

    guild = data["eco"].get(str(interaction.guild.id), {})

    if not guild:
        await interaction.response.send_message("데이터 없음")
        return

    sorted_users = sorted(
        guild.items(),
        key=lambda x: x[1]["wallet"] + x[1]["bank"] + x[1]["level"] * 1000,
        reverse=True
    )[:10]

    msg = "🏆 랭킹 TOP 10\n\n"

    for i, (uid, v) in enumerate(sorted_users, 1):
        total = v["wallet"] + v["bank"]
        msg += f"{i}. <@{uid}> | 💰 {total:,}원 | ⭐ Lv.{v['level']}\n"

    await interaction.response.send_message(msg)

# ================= 실행 =================
bot.run(TOKEN)
import discord
from discord.ext import commands
import aiosqlite
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    # 데이터베이스 초기화
    async with aiosqlite.connect('stats.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0
            )
        ''')
        await db.commit()

@bot.command()
async def 승리(ctx):
    user_id = ctx.author.id
    async with aiosqlite.connect('stats.db') as db:
        await db.execute('''
            INSERT INTO stats (user_id, wins, losses)
            VALUES (?, 1, 0)
            ON CONFLICT(user_id) DO UPDATE SET wins = wins + 1
        ''', (user_id,))
        await db.commit()
    await ctx.send(f"{ctx.author.display_name}님의 승리가 기록되었습니다.")

@bot.command()
async def 패배(ctx):
    user_id = ctx.author.id
    async with aiosqlite.connect('stats.db') as db:
        await db.execute('''
            INSERT INTO stats (user_id, wins, losses)
            VALUES (?, 0, 1)
            ON CONFLICT(user_id) DO UPDATE SET losses = losses + 1
        ''', (user_id,))
        await db.commit()
    await ctx.send(f"{ctx.author.display_name}님의 패배가 기록되었습니다.")

@bot.command()
async def 전적(ctx):
    user_id = ctx.author.id
    async with aiosqlite.connect('stats.db') as db:
        async with db.execute('SELECT wins, losses FROM stats WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                wins, losses = row
                total = wins + losses
                if total > 0:
                    rate = round(wins / total * 100, 2)
                    await ctx.send(f"{ctx.author.display_name}님의 전적 - 승리: {wins}회, 패배: {losses}회, 승률: {rate}%")
                else:
                    await ctx.send(f"{ctx.author.display_name}님의 전적 - 승리: {wins}회, 패배: {losses}회 (아직 승률 없음)")
            else:
                await ctx.send(f"{ctx.author.display_name}님의 전적이 없습니다.")

@bot.command()
async def 초기화(ctx):
    user_id = ctx.author.id
    async with aiosqlite.connect('stats.db') as db:
        await db.execute('''
            INSERT INTO stats (user_id, wins, losses)
            VALUES (?, 0, 0)
            ON CONFLICT(user_id) DO UPDATE SET wins = 0, losses = 0
        ''', (user_id,))
        await db.commit()
    await ctx.send(f"{ctx.author.display_name}님의 전적이 초기화되었습니다.")

@bot.command()
async def 순위(ctx):
    async with aiosqlite.connect('stats.db') as db:
        async with db.execute('SELECT user_id, wins FROM stats ORDER BY wins DESC LIMIT 10') as cursor:
            rows = await cursor.fetchall()
            if not rows:
                await ctx.send("아직 기록된 전적이 없습니다.")
                return

            leaderboard = []
            for i, (user_id, wins) in enumerate(rows, start=1):
                member = ctx.guild.get_member(user_id)
                if member:
                    name = member.display_name
                else:
                    try:
                        user = await bot.fetch_user(user_id)
                        name = user.name
                    except:
                        name = "Unknown User"
                leaderboard.append(f"{i}. {name} - {wins}승")

            embed = discord.Embed(title="🏆 승리 순위 TOP 10", description="\n".join(leaderboard), color=0x00ffcc)
            await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def 전체초기화(ctx):
    async with aiosqlite.connect('stats.db') as db:
        await db.execute('UPDATE stats SET wins = 0, losses = 0')
        await db.commit()
    await ctx.send("✅ 모든 유저의 전적이 초기화되었습니다. (관리자 명령)")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 이 명령어는 관리자만 사용할 수 있습니다.")
    else:
        raise error

bot.run(TOKEN)

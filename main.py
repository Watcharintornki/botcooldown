import os
import discord
from discord.ext import commands, tasks
import datetime
import asyncio
from flask import Flask
import threading

# ====== Flask Keep-Alive ======
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Discord bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ====== Discord Bot Setup ======
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DEFAULT_MINUTES = 15
cooldowns = {}      # channel-based
active_tasks = {}   # user-based

# ====== บอทพร้อมใช้งาน ======
@bot.event
async def on_ready():
    print(f'✅ บอทออนไลน์แล้ว: {bot.user}')
    countdown_updater.start()

# ====== Channel-based Cooldown ======
@bot.command(name="c", aliases=["คูลดาวน์"])
async def cooldown_command(ctx, *, arg: str):
    try:
        parts = arg.strip().split()
        if not parts:
            await ctx.send("❗ ใช้: `!คูลดาวน์ <ชื่อ> [นาที]`")
            return

        minutes = DEFAULT_MINUTES
        name_parts = parts[:-1] if parts[-1].isdigit() else parts
        if parts[-1].isdigit():
            minutes = int(parts[-1])

        name = " ".join(name_parts)
        if not name:
            await ctx.send("❗ กรุณาระบุชื่อ")
            return

        now = datetime.datetime.now()
        end_time = now + datetime.timedelta(minutes=minutes)
        channel_id = ctx.channel.id

        if channel_id not in cooldowns:
            cooldowns[channel_id] = []

        msg = await ctx.send(f'🕒 `{name}` คูลดาวน์ {minutes} นาที (สิ้นสุด {end_time.strftime("%H:%M:%S")})')

        cooldowns[channel_id].append({
            'name': name.lower(),
            'end_time': end_time,
            'message': msg
        })

    except Exception as e:
        await ctx.send(f'⚠️ ข้อผิดพลาด: {str(e)}')

@bot.command(name="x", aliases=["ยกเลิก"])
async def cancel_command(ctx, *, name: str):
    channel_id = ctx.channel.id
    name = name.strip().lower()

    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("⚠️ ไม่มีคิวคูลดาวน์")
        return

    for item in list(cooldowns[channel_id]):
        if item['name'] == name:
            try:
                await item['message'].edit(content=f'❌ `{name}` ยกเลิกแล้ว')
            except discord.NotFound:
                pass
            cooldowns[channel_id].remove(item)
            await ctx.send(f'🛑 ยกเลิก `{name}` เรียบร้อย')
            return

    await ctx.send(f"⚠️ ไม่พบ `{name}` ในคิว")

@bot.command(name="list", aliases=["รายการ"])
async def list_command(ctx):
    channel_id = ctx.channel.id
    now = datetime.datetime.now()

    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("ℹ️ ไม่มีคิวคูลดาวน์ในห้องนี้")
        return

    lines = []
    for item in cooldowns[channel_id]:
        remaining = item['end_time'] - now
        if remaining.total_seconds() > 0:
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            lines.append(f"`{item['name']}` เหลือ {mins} นาที {secs} วิ (จบ {item['end_time'].strftime('%H:%M:%S')})")

    await ctx.send("⏳ คิวคูลดาวน์:\n" + "\n".join(lines))

@tasks.loop(seconds=60)
async def countdown_updater():
    now = datetime.datetime.now()
    for channel_id, items in list(cooldowns.items()):
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        for item in items[:]:
            name = item['name']
            end_time = item['end_time']
            msg = item['message']
            remaining = end_time - now

            if remaining.total_seconds() <= 0:
                try:
                    await channel.send(f'✅ `{name}` คูลดาวน์เสร็จแล้ว!')
                except Exception:
                    pass
                items.remove(item)
            else:
                mins_left = int(remaining.total_seconds() // 60)
                try:
                    await msg.edit(content=f'⏳ `{name}` เหลือ {mins_left} นาที (จบ {end_time.strftime("%H:%M:%S")})')
                except discord.NotFound:
                    items.remove(item)

        if not items:
            del cooldowns[channel_id]

# ====== User-based Cooldown ======
async def countdown(ctx, name, minutes):
    message = await ctx.send(f"🕒 `{name}` คูลดาวน์ {minutes} นาที...")
    for i in range(minutes, 0, -1):
        await asyncio.sleep(60)
        try:
            await message.edit(content=f"🕒 `{name}` เหลือ {i - 1} นาที...")
        except discord.NotFound:
            break

    await ctx.send(f"✅ `{name}` คูลดาวน์เสร็จแล้ว!")

    user_id = ctx.author.id
    if user_id in active_tasks and name in active_tasks[user_id]:
        del active_tasks[user_id][name]
        if not active_tasks[user_id]:
            del active_tasks[user_id]

@bot.command(name="usercd")
async def user_cd(ctx, *, arg):
    parts = arg.strip().split()
    if not parts:
        await ctx.send("❗ ใช้: `!usercd <ชื่อ> [นาที]`")
        return

    minutes = DEFAULT_MINUTES
    if parts[-1].isdigit():
        minutes = int(parts[-1])
        name = " ".join(parts[:-1])
    else:
        name = " ".join(parts)

    user_id = ctx.author.id
    if user_id in active_tasks and name in active_tasks[user_id]:
        await ctx.send(f"⚠️ `{name}` คูลดาวน์อยู่แล้ว")
        return

    if user_id not in active_tasks:
        active_tasks[user_id] = {}

    task = asyncio.create_task(countdown(ctx, name, minutes))
    active_tasks[user_id][name] = task

@bot.command()
async def ยกเลิกส่วนตัว(ctx, *, name):
    user_id = ctx.author.id
    if user_id in active_tasks and name in active_tasks[user_id]:
        task = active_tasks[user_id][name]
        task.cancel()
        del active_tasks[user_id][name]
        if not active_tasks[user_id]:
            del active_tasks[user_id]
        await ctx.send(f"❌ ยกเลิก `{name}` แล้ว")
    else:
        await ctx.send(f"ℹ️ ไม่มี `{name}` กำลังทำงาน")

@bot.command()
async def รายการส่วนตัว(ctx):
    user_id = ctx.author.id
    if user_id in active_tasks and active_tasks[user_id]:
        names = list(active_tasks[user_id].keys())
        await ctx.send(f"📋 คูลดาวน์ของคุณ: {', '.join(names)}")
    else:
        await ctx.send("📭 ไม่มีคูลดาวน์ของคุณ")

# ====== Main Entry Point ======
async def main():
    threading.Thread(target=run_flask).start()
    await bot.start(os.getenv("TOKEN") or "ใส่โทเค็นของคุณที่นี่")

if __name__ == "__main__":
    print("🚀 บอทกำลังเริ่มต้น...")
    asyncio.run(main())

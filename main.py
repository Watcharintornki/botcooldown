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
    return "✅ Discord bot with cooldown is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ====== Discord Bot Setup ======
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DEFAULT_MINUTES = 15
active_tasks = {}  # เก็บข้อมูล cooldown ของแต่ละผู้ใช้

@bot.event
async def on_ready():
    print(f'✅ บอททำงานแล้ว: {bot.user}')

async def countdown(ctx, name, minutes):
    message = await ctx.send(f"🕒 `{name}` จะคูลดาวน์เป็นเวลา {minutes} นาที...")

    for i in range(minutes, 0, -1):
        await asyncio.sleep(60)
        try:
            await message.edit(content=f"🕒 `{name}` เหลือเวลา {i - 1} นาที...")
        except discord.NotFound:
            break  # ถ้าข้อความถูกลบแล้ว

    await ctx.send(f"✅ `{name}` คูลดาวน์เสร็จแล้ว!")

    # ลบจากรายการ
    user_id = ctx.author.id
    if user_id in active_tasks and name in active_tasks[user_id]:
        del active_tasks[user_id][name]
        if not active_tasks[user_id]:
            del active_tasks[user_id]

@bot.command()
async def c(ctx, *, arg):
    try:
        parts = arg.strip().split()

        if not parts:
            await ctx.send("❗ กรุณาระบุชื่อ เช่น `!คูลดาวน์ โรงน้ำมัน` หรือ `!คูลดาวน์ โรงน้ำมัน 10`")
            return

        if parts[-1].isdigit():
            minutes = int(parts[-1])
            name = " ".join(parts[:-1])
        else:
            minutes = DEFAULT_MINUTES
            name = " ".join(parts)

        if not name:
            await ctx.send("❗ กรุณาระบุชื่อสิ่งที่ต้องการคูลดาวน์")
            return

        user_id = ctx.author.id
        if user_id in active_tasks and name in active_tasks[user_id]:
            await ctx.send(f"⚠️ `{name}` กำลังอยู่ในคูลดาวน์แล้ว")
            return

        if user_id not in active_tasks:
            active_tasks[user_id] = {}

        task = asyncio.create_task(countdown(ctx, name, minutes))
        active_tasks[user_id][name] = task

    except Exception as e:
        await ctx.send(f'⚠️ เกิดข้อผิดพลาด: {str(e)}')

@bot.command()
async def x(ctx, *, name):
    user_id = ctx.author.id
    if user_id in active_tasks and name in active_tasks[user_id]:
        task = active_tasks[user_id][name]
        task.cancel()
        del active_tasks[user_id][name]
        if not active_tasks[user_id]:
            del active_tasks[user_id]
        await ctx.send(f"❌ ยกเลิกคูลดาวน์ `{name}` แล้ว")
    else:
        await ctx.send(f"ℹ️ ไม่พบคูลดาวน์ชื่อ `{name}` ที่กำลังทำงาน")

@bot.command()
async def list(ctx):
    user_id = ctx.author.id
    if user_id in active_tasks and active_tasks[user_id]:
        names = list(active_tasks[user_id].keys())
        await ctx.send(f"📋 รายการคูลดาวน์ของคุณ: {', '.join(names)}")
    else:
        await ctx.send("📭 คุณไม่มีคูลดาวน์ที่กำลังทำงานอยู่")

# ====== Entry Point ======
async def main():
    threading.Thread(target=run_flask).start()
    await bot.start(os.getenv("TOKEN") or "ใส่โทเค็นของคุณที่นี่")

if __name__ == "__main__":
    print("🚀 Starting bot with keep-alive web server...")
    asyncio.run(main())

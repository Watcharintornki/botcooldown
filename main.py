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
cooldowns = {}  # {channel_id: [ {'name': str, 'end_time': datetime, 'message': discord.Message, 'last_minute': int} ] }

@bot.event
async def on_ready():
    print(f'✅ บอทออนไลน์แล้ว: {bot.user}')
    countdown_updater.start()

@bot.command(name="c", aliases=["cd", "cooldown"])
async def cooldown_command(ctx, *, arg: str):
    parts = arg.strip().split()
    if not parts:
        await ctx.send("❗ ใช้: `!c <ชื่อ> [นาที]`")
        return

    minutes = DEFAULT_MINUTES
    if parts[-1].isdigit():
        minutes = int(parts[-1])
        name = " ".join(parts[:-1])
    else:
        name = " ".join(parts)

    if not name:
        await ctx.send("❗ กรุณาระบุชื่อ")
        return

    now = datetime.datetime.now()
    end_time = now + datetime.timedelta(minutes=minutes)
    channel_id = ctx.channel.id

    if channel_id not in cooldowns:
        cooldowns[channel_id] = []

    msg = await ctx.send(f'🕒 `{name}` คูลดาวน์ {minutes} นาที...')

    cooldowns[channel_id].append({
        'name': name.lower(),
        'end_time': end_time,
        'message': msg,
        'last_minute': minutes
    })

@bot.command(name="x", aliases=["cancel", "ยกเลิก"])
async def cancel_command(ctx, *, name: str):
    name = name.strip().lower()
    channel_id = ctx.channel.id

    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("⚠️ ไม่มีคิวคูลดาวน์ในห้องนี้")
        return

    found = False
    for item in list(cooldowns[channel_id]):
        if item['name'] == name:
            try:
                await item['message'].edit(content=f'❌ `{name}` คูลดาวน์ถูกยกเลิกแล้ว')
            except discord.NotFound:
                pass
            cooldowns[channel_id].remove(item)
            await ctx.send(f'🛑 ยกเลิกคูลดาวน์ `{name}` เรียบร้อยแล้ว')
            found = True
            break

    if not found:
        await ctx.send(f"⚠️ ไม่พบชื่อ `{name}` ในคิวคูลดาวน์")

@bot.command(name="list", aliases=["l", "รายการ"])
async def list_command(ctx):
    channel_id = ctx.channel.id
    now = datetime.datetime.now()

    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("ℹ️ ไม่มีรายการคูลดาวน์ในห้องนี้ตอนนี้")
        return

    lines = []
    for item in cooldowns[channel_id]:
        remaining = item['end_time'] - now
        if remaining.total_seconds() > 0:
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            lines.append(f"`{item['name']}` เหลือ {mins} นาที {secs} วินาที (สิ้นสุด {item['end_time'].strftime('%H:%M:%S')})")

    if lines:
        await ctx.send("⏳ รายการคูลดาวน์:\n" + "\n".join(lines))
    else:
        await ctx.send("ℹ️ ไม่มีรายการคูลดาวน์ในห้องนี้ตอนนี้")

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
                    # แจ้งเตือนว่าคูลดาวน์เสร็จแล้ว
                    await channel.send(f'✅ `{name}` คูลดาวน์เสร็จแล้ว!')
                    # ลบข้อความเก่าที่แสดงเวลาคูลดาวน์
                    await msg.delete()
                except Exception as e:
                    print(f"เกิดข้อผิดพลาด: {e}")
                items.remove(item)
            else:
                mins_left = int(remaining.total_seconds() // 60)
                try:
                    await msg.edit(content=f'⏳ `{name}` เหลือเวลาอีก {mins_left} นาที (สิ้นสุด {end_time.strftime("%H:%M:%S")})')
                except discord.NotFound:
                    # ถ้าข้อความถูกลบ ให้ลบคูลดาวน์นี้ออกด้วย
                    items.remove(item)
                except Exception as e:
                    print(f"เกิดข้อผิดพลาดในการแก้ไขข้อความสำหรับ `{name}`: {e}")

        if not items:
            del cooldowns[channel_id]

# ====== Entry Point ======
async def main():
    threading.Thread(target=run_flask).start()
    await bot.start(os.getenv("TOKEN") or "ใส่โทเค็นของคุณที่นี่")

if __name__ == "__main__":
    print("🚀 Starting bot with keep-alive web server...")
    asyncio.run(main())

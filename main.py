# main.py
import os
import discord
from discord.ext import commands, tasks
import datetime
import asyncio
from myserver import app  # เผื่อ Flask ถูก import ที่อื่น

# Intents สำหรับ Discord Bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

DEFAULT_MINUTES = 15
cooldowns = {}

@bot.event
async def on_ready():
    print(f'✅ บอทออนไลน์แล้ว: {bot.user}')
    countdown_updater.start()

@bot.command()
async def c(ctx, *, arg: str):
    try:
        parts = arg.strip().split()
        if not parts:
            await ctx.send("❗ ใช้คำสั่ง: `!คูลดาวน์ <ชื่อ> [นาที]`")
            return

        minutes = DEFAULT_MINUTES
        name_parts = []

        if parts[-1].isdigit():
            minutes = int(parts[-1])
            name_parts = parts[:-1]
        else:
            name_parts = parts

        name = " ".join(name_parts)
        if not name:
            await ctx.send("❗ กรุณาระบุชื่อสิ่งที่ต้องการคูลดาวน์")
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
        await ctx.send(f'⚠️ เกิดข้อผิดพลาด: {str(e)}')

@bot.command()
async def x(ctx, *, name: str):
    channel_id = ctx.channel.id
    name = name.strip().lower()

    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("⚠️ ไม่มีคิวคูลดาวน์ในห้องนี้")
        return

    found = False
    for item in list(cooldowns[channel_id]):
        if item['name'] == name:
            try:
                await item['message'].edit(content=f'❌ `{name}` คูลดาวน์ถูกยกเลิกแล้ว')
            except discord.NotFound:
                print(f"ข้อความ `{name}` ไม่พบแล้ว")
            cooldowns[channel_id].remove(item)
            await ctx.send(f'🛑 ยกเลิกคูลดาวน์ `{name}` เรียบร้อยแล้ว')
            found = True
            break

    if not found:
        await ctx.send(f"⚠️ ไม่พบชื่อ `{name}` ในคิวคูลดาวน์")

@bot.command()
async def list(ctx):
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
            lines.append(f"`{item['name']}` เหลือเวลา {mins} นาที {secs} วินาที (สิ้นสุด {item['end_time'].strftime('%H:%M:%S')})")

    if lines:
        await ctx.send("⏳ รายการคูลดาวน์ที่กำลังทำงาน:\n" + "\n".join(lines))
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
                    await channel.send(f'✅ `{name}` คูลดาวน์เสร็จแล้ว!')
                except Exception as e:
                    print(f"ส่งข้อความแจ้งเตือนไม่ได้: {e}")
                items.remove(item)
            else:
                mins_left = int(remaining.total_seconds() // 60)
                try:
                    await msg.edit(content=f'⏳ `{name}` เหลือเวลาอีก {mins_left} นาที (สิ้นสุด {end_time.strftime("%H:%M:%S")})')
                except discord.NotFound:
                    items.remove(item)
                except Exception as e:
                    print(f"เกิดข้อผิดพลาดในการแก้ไขข้อความสำหรับ `{name}`: {e}")

        if not items:
            del cooldowns[channel_id]

# Entry point
if __name__ == "__main__":
    print("🚀 Starting Discord bot with Flask keep-alive...")
    asyncio.run(bot.start(os.getenv('TOKEN')))

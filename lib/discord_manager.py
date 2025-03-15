from discord.ext import commands
import httpx

# Discord 配置
DISCORD_TOKEN = 'Rmy498C1UgiCHDkMvAjVmtfQFyuC0SBsRMFNqKBVRgQKhQShknHKmGFO2BMsq2OhHob5'
CHANNEL_ID = 771696772233428992  # 替换为你的 Discord 频道 ID


# 发送 Discord 通知
# async def send_discord_notification(message):
#     bot = commands.Bot(command_prefix='!')
#     @bot.event
#     async def on_ready():
#         channel = bot.get_channel(CHANNEL_ID)
#         await channel.send(message)
#         await bot.close()
#     await bot.start(DISCORD_TOKEN)


async def send_discord_notification(message, proxy):
    webhook_url = "https://discord.com/api/webhooks/771696793808797696/Rmy498C1UgiCHDkMvAjVmtfQFyuC0SBsRMFNqKBVRgQKhQShknHKmGFO2BMsq2OhHob5"
    data = {
        "content": message,
        "username": "AsyncBot"
    }

    async with httpx.AsyncClient(proxy=proxy) as client:
        response = await client.post(webhook_url, json=data)
        if response.status_code == 204:
            print("消息发送成功！")
        else:
            print(f"消息发送失败，状态码: {response.status_code}, 响应内容: {response.text}")
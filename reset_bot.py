from telegram import Bot
import os

TOKEN = "7694058257:AAGdp9Bsrq3fJWnpyjMOQkZyVPeCCj-j6Pw"

bot = Bot(token=TOKEN)

bot.delete_webhook(drop_pending_updates=True)
print("Webhook deleted, pending updates dropped")

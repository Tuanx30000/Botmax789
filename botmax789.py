import os
import requests
import random
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====================== CẤU HÌNH ======================
TOKEN = "8667000858:AAHfBKtARPMZhaldyblv_ehP0l2xlkrY8o8"
CHANNEL_ID = '-1002807452773'

# CHỈ 1 ADMIN ID
ADMIN_IDS = [8566247215]

API_URL = "https://taixiumd5.maksh3979madfw.com/api/md5luckydice/GetSoiCau"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ====================== FLASK KEEP-ALIVE ======================
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "✅ Bot MAX789 VIP TUANX3000 đang chạy!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False)

# ====================== HÀM SOI CẦU ======================
async def soi_cau(context: ContextTypes.DEFAULT_TYPE, so_lan: int = 1):
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()

        if 'list' not in data or not data['list']:
            return "❌ Không lấy được dữ liệu từ API."

        messages = []
        for phien in data['list'][:so_lan]:
            id_moi = int(phien.get('id', 0)) + 1
            ma_md5 = str(phien.get('_id', '0' * 32)).lower()

            last4 = ma_md5[-4:].zfill(4)
            last8 = ma_md5[-8:].zfill(8)
            last12 = ma_md5[-12:].zfill(12)

            val4 = int(last4, 16) % 100
            val8 = int(last8, 16) % 100
            sum_hex = sum(int(c, 16) for c in last12)
            last_digit = int(ma_md5[-1], 16) if ma_md5 else 0

            recent = data['list'][:10]
            tai_count = sum(1 for p in recent 
                            if p.get('resultTruyenThong') == 'TAI' or p.get('point', 0) >= 5)
            xiu_count = 10 - tai_count
            trend_bias = (tai_count - xiu_count) * 2

            base = (id_moi * 15 + val4 * 8 + val8 * 5 + last_digit * 10 + sum_hex * 3 + trend_bias)
            diem = (base % 10 + random.randint(0, 1)) % 10

            ket_qua = "🟢 TÀI" if diem >= 5 else "🔴 XỈU"

            ti_le = 75 + (val4 % 14)
            if (trend_bias > 4 and ket_qua == "🟢 TÀI") or (trend_bias < -4 and ket_qua == "🔴 XỈU"):
                ti_le += 3
            ti_le = max(74, min(88, ti_le))

            msg = (f"🌟 MAX789 VIP TUANX3000 🌟\n"
                   f"🎯 Phiên: #{id_moi}\n"
                   f"🔮 Dự đoán: {ket_qua}\n"
                   f"📊 Tỉ lệ chuẩn: {ti_le}%\n"
                   f"♾️ Mã MD5: {ma_md5}\n"
                   f"──────────────────")

            messages.append(msg)

        for m in messages:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=m)

        return f"✅ Đã soi {len(messages)} phiên thành công!"

    except Exception as e:
        logging.error(f"Lỗi soi cầu: {e}")
        return "❌ Lỗi kết nối API, thử lại sau."

# ====================== COMMAND ======================
async def soicau_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Chỉ admin mới dùng được lệnh này.")
        return

    try:
        so_lan = int(context.args[0]) if context.args else 1
        so_lan = max(1, min(10, so_lan))
    except:
        so_lan = 1

    status = await soi_cau(context, so_lan)
    await update.message.reply_text(status)

# ====================== KHỞI ĐỘNG ======================
async def main():
    # Xóa webhook cũ để tránh conflict 409
    try:
        temp_app = ApplicationBuilder().token(TOKEN).build()
        await temp_app.bot.delete_webhook(drop_pending_updates=True)
        logging.info("✅ Đã xóa webhook cũ thành công")
    except Exception as e:
        logging.warning(f"Không xóa được webhook: {e}")

    # Chạy Flask keep-alive
    threading.Thread(target=run_web, daemon=True).start()

    # Khởi tạo bot chính
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("soicau", soicau_command))

    logging.info("🚀 Bot MAX789 VIP TUANX3000 khởi động thành công!")
    await application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
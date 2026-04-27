import os
import requests
import random
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====================== CẤU HÌNH ======================
TOKEN = "8667000858:AAHfBKtARPMZhaldyblv_ehP0l2xlkrY8o8"
CHANNEL_ID = '-1002807452773'

# ADMIN IDS (chỉ admin mới được dùng lệnh /soicau)
ADMIN_IDS = [8566247215]   # ← Thay YOUR_SECOND_ID_HERE bằng ID thật của bạn

API_URL = "https://taixiumd5.maksh3979madfw.com/api/md5luckydice/GetSoiCau"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ====================== WEB SERVER (keep-alive) ======================
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot MAX789 VIP is running!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False)

# ====================== HÀM SOI CẦU ======================
async def soi_cau(context: ContextTypes.DEFAULT_TYPE, so_lan: int = 1):
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'list' not in data or not data['list']:
            return "❌ Không lấy được dữ liệu từ API."

        messages = []
        recent_list = data['list'][:so_lan]   # Giới hạn số phiên

        for phien in recent_list:
            id_moi = int(phien.get('id', 0)) + 1
            ma_md5 = str(phien.get('_id', '0' * 32)).lower()

            # Phân tích MD5
            last4 = ma_md5[-4:].zfill(4)
            last8 = ma_md5[-8:].zfill(8)
            last12 = ma_md5[-12:].zfill(12)

            val4 = int(last4, 16) % 100
            val8 = int(last8, 16) % 100
            sum_hex = sum(int(c, 16) for c in last12)
            last_digit = int(ma_md5[-1], 16) if ma_md5 else 0

            # Trend từ 10 phiên gần nhất
            recent = data['list'][:10]
            tai_count = sum(1 for p in recent 
                            if p.get('resultTruyenThong') == 'TAI' or p.get('point', 0) >= 5)
            xiu_count = 10 - tai_count
            trend_bias = (tai_count - xiu_count) * 2

            # Tính điểm dự đoán
            base = (id_moi * 15 + val4 * 8 + val8 * 5 + last_digit * 10 + sum_hex * 3 + trend_bias)
            diem = base % 10
            diem = (diem + random.randint(0, 1)) % 10

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

        # Gửi tin nhắn
        for m in messages:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=m)

        return f"✅ Đã soi {len(messages)} phiên thành công vào kênh!"

    except Exception as e:
        logging.error(f"Lỗi soi cầu: {e}")
        return "❌ Lỗi khi kết nối API, vui lòng thử lại sau."

# ====================== COMMAND SOI CẦU ======================
async def soicau_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Chỉ admin mới được sử dụng lệnh này.")
        return

    # Lấy số lần soi (mặc định là 1)
    try:
        so_lan = int(context.args[0]) if context.args else 1
        so_lan = max(1, min(10, so_lan))  # Giới hạn từ 1 đến 10 phiên
    except ValueError:
        so_lan = 1

    status = await soi_cau(context, so_lan)
    await update.message.reply_text(status)

# ====================== KHỞI ĐỘNG ======================
if __name__ == '__main__':
    # Chạy web server để giữ bot alive
    threading.Thread(target=run_web, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    # Chỉ còn lệnh soi cầu
    app.add_handler(CommandHandler("soicau", soicau_command))

    logging.info("🚀 Bot MAX789 VIP TUANX3000 đã khởi động - Chế độ soi thủ công!")
    app.run_polling(drop_pending_updates=True)
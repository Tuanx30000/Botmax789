import os
import requests
import random
import logging
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, CommandHandler

# ====================== CẤU HÌNH ======================
TOKEN = "8639357771:AAE5i6uDVgnAMd3vX5Y8-wYp8SaA-P2H59Y" 
CHANNEL_ID = '-1003991810381'

ADMIN_IDS = [8566247215]

API_URL = "https://taixiumd5.maksh3979madfw.com/api/md5luckydice/GetSoiCau"

logging.basicConfig(level=logging.INFO)

# ====================== WEB SERVER ======================
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False)

# ====================== BIẾN TOÀN CỤC ======================
bot_enabled = True
last_session_id = None

# ====================== PARSE DỮ LIỆU ======================
def parse_session_line(line: str):
    try:
        line = line.strip().strip('[]')
        items = line.split(',')
        data = {}
        for item in items:
            if ':' in item:
                key, value = item.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"')
                data[key] = value
        return data
    except:
        return None

# ====================== JOB MONITOR - TÍNH TOÁN NÂNG CAO ======================
async def job_monitor(context):
    global last_session_id, bot_enabled

    if not bot_enabled:
        return

    try:
        response = requests.get(API_URL, timeout=12)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return

        latest_line = data[0]
        phien = parse_session_line(latest_line)

        if not phien or 'SessionId' not in phien:
            return

        current_session = int(phien['SessionId'])

        if last_session_id == current_session:
            return

        next_session = current_session + 1

        # ====================== PHÂN TÍCH CẦU NÂNG CAO ======================
        recent_10 = data[:10]
        recent_5 = data[:5]

        tai_10 = 0
        tai_5 = 0
        results = []  # lưu kết quả T/X của 10 phiên

        for line in recent_10:
            p = parse_session_line(line)
            if p:
                dice_sum = int(p.get('DiceSum', 0))
                is_tai = dice_sum >= 11 or p.get('resultTruyenThong') == 'TAI'
                results.append('T' if is_tai else 'X')
                tai_10 += 1 if is_tai else 0
                if line in recent_5[:5]:  # 5 phiên gần nhất
                    tai_5 += 1 if is_tai else 0

        xiu_10 = 10 - tai_10
        xiu_5 = 5 - tai_5

        trend_bias = (tai_10 - xiu_10) * 2
        short_trend = tai_5 - xiu_5

        # Phát hiện cầu bệt (3+ liên tiếp)
        streak_tai = max((i for i in range(1, len(results)+1) if all(r == 'T' for r in results[:i])), default=0)
        streak_xiu = max((i for i in range(1, len(results)+1) if all(r == 'X' for r in results[:i])), default=0)

        # ====================== TÍNH TOÁN DỰ ĐOÁN NÂNG CAO ======================
        base = (next_session * 12) + (trend_bias * 4) + (short_trend * 6)

        # Ưu tiên theo cầu bệt mạnh
        if streak_tai >= 3:
            base += 25
        elif streak_xiu >= 3:
            base -= 25

        diem = (base % 10 + random.randint(-1, 2)) % 10   # random kiểm soát

        ket_qua = "🟢 TÀI" if diem >= 5 else "🔴 XỈU"

        # Tính tỉ lệ động
        ti_le = 76 + abs(trend_bias) * 1.2 + abs(short_trend) * 2

        # Bonus khi cầu rất mạnh
        if (trend_bias > 6 and ket_qua == "🟢 TÀI") or (trend_bias < -6 and ket_qua == "🔴 XỈU"):
            ti_le += 5
        if (streak_tai >= 3 and ket_qua == "🟢 TÀI") or (streak_xiu >= 3 and ket_qua == "🔴 XỈU"):
            ti_le += 4

        ti_le = max(72, min(89, int(ti_le)))

        # ====================== SOẠN TIN NHẮN ======================
        trend_text = "TÀI MẠNH" if tai_10 >= 7 else "XỈU MẠNH" if xiu_10 >= 7 else "Cân bằng"

        msg = (f"🌟 **Max789 VIP TUANX3000** 🌟\n"
               f"🎯 Phiên: #{next_session}\n"
               f"🔮 Dự đoán: {ket_qua}\n"
               f"📊 Tỉ lệ: **{ti_le}%**\n"
               f"📈 Trend 10: {tai_10}T - {xiu_10}X ({trend_text})\n"
               f"🔥 Trend 5:  {tai_5}T - {xiu_5}X\n"
               f"⚡ Cầu: {'Bệt ' + str(streak_tai) + 'T' if streak_tai >= 3 else 'Bệt ' + str(streak_xiu) + 'X' if streak_xiu >= 3 else 'Đang chuyển'}")

        await context.bot.send_message(
            chat_id=CHANNEL_ID, 
            text=msg, 
            parse_mode='Markdown'
        )
        
        last_session_id = current_session
        logging.info(f"Phiên #{next_session} → {ket_qua} | {ti_le}% | Trend: {tai_10}-{xiu_10}")

    except Exception as e:
        logging.error(f"Lỗi job_monitor: {e}", exc_info=True)

# ====================== COMMAND ======================
async def bat_tool(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    global bot_enabled
    bot_enabled = True
    await update.message.reply_text("✅ Bot đã được **BẬT**.")

async def tat_tool(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    global bot_enabled
    bot_enabled = False
    await update.message.reply_text("❌ Bot đã được **TẮT**.")

# ====================== KHỞI ĐỘNG ======================
if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()

    if app.job_queue:
        app.job_queue.run_repeating(job_monitor, interval=25, first=5)   # chạy nhanh hơn một chút

    app.add_handler(CommandHandler("batmax", bat_tool))
    app.add_handler(CommandHandler("tatmax", tat_tool))

    logging.info("🚀 Bot Tài Xỉu MD5 - Phiên bản Tính Toán NÂNG CAO đã khởi động!")
    app.run_polling()
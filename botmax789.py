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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
    except Exception:
        return None

# ====================== JOB MONITOR - ĐÃ SỬA ======================
def job_monitor(context):
    global last_session_id, bot_enabled

    if not bot_enabled:
        return

    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return

        # Lấy phiên mới nhất
        latest_line = data[0]
        phien = parse_session_line(latest_line)

        if not phien or 'SessionId' not in phien:
            logging.warning("Không parse được dữ liệu phiên")
            return

        current_session = int(phien['SessionId'])

        # Tránh lặp lại phiên cũ
        if last_session_id is not None and last_session_id == current_session:
            return

        next_session = current_session + 1

        # ====================== TÍNH TOÁN NỘI BỘ ======================
        recent_10 = data[:10]

        tai_10 = 0
        results = []   # Dùng để tính streak

        for i, line in enumerate(recent_10):
            p = parse_session_line(line)
            if not p:
                continue
                
            dice_sum = int(p.get('DiceSum', 0))
            is_tai = (p.get('resultTruyenThong') == 'TAI') or (dice_sum >= 11)
            
            results.append('T' if is_tai else 'X')
            tai_10 += 1 if is_tai else 0

        xiu_10 = 10 - tai_10
        trend_bias = (tai_10 - xiu_10) * 2

        # Tính cầu bệt (streak)
        streak_tai = streak_xiu = 0
        for r in results:
            if r == 'T':
                streak_tai += 1
                streak_xiu = 0
            else:
                streak_xiu += 1
                streak_tai = 0

        # ====================== DỰ ĐOÁN NÂNG CAO ======================
        base = (next_session * 12) + (trend_bias * 4)

        if streak_tai >= 3:
            base += 25
        elif streak_xiu >= 3:
            base -= 25

        diem = (base % 10 + random.randint(-1, 2)) % 10
        ket_qua = "🟢 TÀI" if diem >= 5 else "🔴 XỈU"

        # Tính tỉ lệ
        ti_le = 76 + abs(trend_bias) * 1.2
        if (trend_bias > 6 and ket_qua == "🟢 TÀI") or (trend_bias < -6 and ket_qua == "🔴 XỈU"):
            ti_le += 5
        if (streak_tai >= 3 and ket_qua == "🟢 TÀI") or (streak_xiu >= 3 and ket_qua == "🔴 XỈU"):
            ti_le += 4

        ti_le = max(72, min(89, int(ti_le)))

        # ====================== SOẠN TIN NHẮN (ĐÃ ẨN TOÀN BỘ TREND) ======================
        msg = (
            f"🌟 **Max789 VIP TUANX3000** 🌟\n"
            f"🎯 Phiên: #{next_session}\n"
            f"🔮 Dự đoán: {ket_qua}\n"
            f"📊 Tỉ lệ: **{ti_le}%**"
        )

        # Gửi tin nhắn
        context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=msg,
            parse_mode='Markdown'
        )

        last_session_id = current_session
        logging.info(f"Đã gửi dự đoán phiên #{next_session} → {ket_qua} | {ti_le}%")

    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi kết nối API: {e}")
    except Exception as e:
        logging.error(f"Lỗi job_monitor: {e}", exc_info=True)


# ====================== COMMANDS ======================
async def bat_tool(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return
    global bot_enabled
    bot_enabled = True
    await update.message.reply_text("✅ Bot đã được **BẬT**.")


async def tat_tool(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return
    global bot_enabled
    bot_enabled = False
    await update.message.reply_text("❌ Bot đã được **TẮT**.")


# ====================== KHỞI ĐỘNG ======================
if __name__ == '__main__':
    # Chạy Flask web server trong thread riêng
    threading.Thread(target=run_web, daemon=True).start()

    # Khởi tạo Telegram Bot
    app = ApplicationBuilder().token(TOKEN).build()

    # Thêm Job chạy định kỳ
    app.job_queue.run_repeating(job_monitor, interval=25, first=5)

    # Thêm lệnh điều khiển
    app.add_handler(CommandHandler("batmax", bat_tool))
    app.add_handler(CommandHandler("tatmax", tat_tool))

    logging.info("🚀 Bot Tài Xỉu MD5 - Phiên bản ẨN TREND đã khởi động thành công!")
    
    # Chạy bot
    app.run_polling(drop_pending_updates=True)
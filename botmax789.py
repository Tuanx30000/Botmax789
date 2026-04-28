import os
import requests
import random
import logging
import threading
from flask import Flask

from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

# ====================== CẤU HÌNH ======================
TOKEN = "8639357771:AAE5i6uDVgnAMd3vX5Y8-wYp8SaA-P2H59Y" 
CHANNEL_ID = -1003991810381   # Dùng số âm, không dấu ngoặc kép

ADMIN_IDS = [8566247215]

API_URL = "https://taixiumd5.maksh3979madfw.com/api/md5luckydice/GetSoiCau?access_token=05%2F7JlwSPGzFBT3sGaKY2ZcLjROdAOOPB3UwDAmuWFKyfHGWuuM%2BC2zy%2FjjnuznAdeJ1hnJUb8IJnvmUDf44qzL49F2ysXpxi9Qj3ZQZ6ahSqlIQmeUS94Mz3ywCtmnj6ssOz4%2BcY90Z%2FFIaUyLA7aw%2FSOcfQ5jEh4AWpcuvdekhs8XvL9mZS4qPwgCPexrDRWK4gHWx7n2akAHlUFDedm6o6uPDpIEA7z1BXADeLKqizH6WVpDMuD3pEFwdC0zHP2jJtVEQgvGeDGXWLSeSr%2F00etslH1TXwCrs%2BrD4Dj%2B3OmJ3VlTStd%2BirPOtXfmDIBLEr2fUlNRwt%2BRKzRuxt3piAyOlfP1UjrYRX7ekIiTrO%2BYBr3m%2FKDgomuTf2vrP6KqCW%2F2hEdU%3D.14abebf71302f5cce8f3d94ed438ba5c1d31a484d0319b3172db76015a64b4d7"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    except Exception as e:
        logging.error(f"Lỗi parse line: {e}")
        return None

# ====================== JOB MONITOR ======================
async def job_monitor(context: ContextTypes.DEFAULT_TYPE):
    global last_session_id, bot_enabled

    if not bot_enabled:
        return

    chat_id = context.job.chat_id or CHANNEL_ID

    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            logging.warning("API trả về dữ liệu rỗng")
            return

        latest_line = data[0]
        phien = parse_session_line(latest_line)

        if not phien or 'SessionId' not in phien:
            logging.warning("Không parse được SessionId")
            return

        current_session = int(phien.get('SessionId'))

        # Tránh lặp lại cùng phiên
        if last_session_id is not None and last_session_id == current_session:
            return

        next_session = current_session + 1

        # ====================== TÍNH TOÁN ======================
        recent_10 = data[:10]
        tai_10 = 0
        results = []

        for line in recent_10:
            p = parse_session_line(line)
            if not p:
                continue
            dice_sum = int(p.get('DiceSum', 0))
            is_tai = (p.get('resultTruyenThong') == 'TAI') or (dice_sum >= 11)
            results.append('T' if is_tai else 'X')
            if is_tai:
                tai_10 += 1

        xiu_10 = 10 - tai_10
        trend_bias = (tai_10 - xiu_10) * 2

        # Tính streak
        streak_tai = streak_xiu = 0
        for r in results:
            if r == 'T':
                streak_tai += 1
                streak_xiu = 0
            else:
                streak_xiu += 1
                streak_tai = 0

        # ====================== DỰ ĐOÁN ======================
        base = (next_session * 12) + (trend_bias * 4)
        if streak_tai >= 3:
            base += 25
        elif streak_xiu >= 3:
            base -= 25

        diem = (base % 10 + random.randint(-1, 2)) % 10
        ket_qua = "🟢 TÀI" if diem >= 5 else "🔴 XỈU"

        ti_le = 76 + abs(trend_bias) * 1.2
        if (trend_bias > 6 and ket_qua == "🟢 TÀI") or (trend_bias < -6 and ket_qua == "🔴 XỈU"):
            ti_le += 5
        if (streak_tai >= 3 and ket_qua == "🟢 TÀI") or (streak_xiu >= 3 and ket_qua == "🔴 XỈU"):
            ti_le += 4

        ti_le = max(72, min(89, int(ti_le)))

        # ====================== GỬI TIN NHẮN ======================
        msg = (
            f"🌟 **Max789 VIP TUANX3000** 🌟\n"
            f"🎯 Phiên: #{next_session}\n"
            f"🔮 Dự đoán: {ket_qua}\n"
            f"📊 Tỉ lệ: **{ti_le}%**"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode='Markdown'
        )

        last_session_id = current_session
        logging.info(f"Đã gửi dự đoán phiên #{next_session} → {ket_qua} | {ti_le}%")

    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi kết nối API: {e}")
    except Exception as e:
        logging.error(f"Lỗi trong job_monitor: {e}", exc_info=True)


# ====================== COMMAND ======================
async def bat_tool(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    global bot_enabled
    bot_enabled = True
    await update.message.reply_text("✅ Bot đã được **BẬT**.")


async def tat_tool(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    global bot_enabled
    bot_enabled = False
    await update.message.reply_text("❌ Bot đã được **TẮT**.")


async def test_send(update, context: ContextTypes.DEFAULT_TYPE):
    """Test xem bot có gửi tin được vào channel không"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="✅ **Test thành công!** Bot đang hoạt động bình thường.",
            parse_mode='Markdown'
        )
        await update.message.reply_text("Đã gửi tin test vào channel.")
    except Exception as e:
        await update.message.reply_text(f"Lỗi khi gửi test: {e}")


# ====================== KHỞI ĐỘNG ======================
if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    # Job chạy đúng cách (quan trọng nhất)
    app.job_queue.run_repeating(
        job_monitor,
        interval=25,
        first=5,
        chat_id=CHANNEL_ID,
        name="md5_soicau_job"
    )

    app.add_handler(CommandHandler("batmax", bat_tool))
    app.add_handler(CommandHandler("tatmax", tat_tool))
    app.add_handler(CommandHandler("test", test_send))   # Dùng /test để kiểm tra

    logging.info("🚀 Bot Tài Xỉu MD5 - Phiên bản max789 đã khởi động!")
    
    app.run_polling(drop_pending_updates=True)
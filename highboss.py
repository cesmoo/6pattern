import asyncio
import time
import os
import hashlib
import random
import string
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
import motor.motor_asyncio 

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

load_dotenv()

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
USERNAME = os.getenv("BIGWIN_USERNAME")
PASSWORD = os.getenv("BIGWIN_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("CHANNEL_ID")
MONGO_URI = os.getenv("MONGO_URI") 

if not all([USERNAME, PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, MONGO_URI]):
    print("❌ Error: .env ဖိုင်ထဲတွင် အချက်အလက်များ ပြည့်စုံစွာ မပါဝင်ပါ။")
    exit()
  
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# MongoDB Setup
db_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = db_client['bigwin_database'] 
history_collection = db['game_history'] 
predictions_collection = db['predictions'] 
betting_collection = db['betting_history']

# ==========================================
# 🔧 2. SYSTEM & TRACKING VARIABLES 
# ==========================================
CURRENT_TOKEN = ""
LAST_PROCESSED_ISSUE = ""
LAST_PREDICTED_ISSUE = ""
LAST_PREDICTED_RESULT = ""

# --- Streak & Stats Tracking ---
CURRENT_WIN_STREAK = 0
CURRENT_LOSE_STREAK = 0
LONGEST_WIN_STREAK = 0
LONGEST_LOSE_STREAK = 0
TOTAL_PREDICTIONS = 0 

# --- Auto Bet Settings ---
AUTO_BET_ENABLED = False

# --- Martingale Settings ---
BASE_BET_AMOUNT = 10  # အခြေခံထိုးငွေ (10 ကျပ်)
CURRENT_BET_AMOUNT = 10  # လက်ရှိထိုးမည့်ငွေပမာဏ
MAX_BET_AMOUNT = 5120  # အများဆုံးထိုးနိုင်သောငွေ
MIN_BALANCE_REQUIRED = 5000  # အနည်းဆုံးလိုအပ်သောလက်ကျန်
CONSECUTIVE_LOSSES = 0  # ဆက်တိုက်အရှုံးအကြိမ်ရေ
MAX_CONSECUTIVE_LOSSES = 10  # အများဆုံးခံနိုင်သောအရှုံးအကြိမ်ရေ
TOTAL_PROFIT = 0  # စုစုပေါင်းအမြတ်
TOTAL_BETS = 0  # စုစုပေါင်းထိုးထားသောအကြိမ်ရေ
WINS = 0  # အနိုင်ရအကြိမ်ရေ
LOSSES = 0  # အရှုံးအကြိမ်ရေ

# --- Bet Tracking ---
PENDING_BETS = {}  # {issue_number: {"amount": amount, "prediction": "BIG/SMALL", "timestamp": time}}
BET_HISTORY = []  # ထိုးမှတ်တမ်းများ

BASE_HEADERS = {
    'authority': 'api.bigwinqaz.com',
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/json;charset=UTF-8',
    'origin': 'https://www.777bigwingame.app',
    'referer': 'https://www.777bigwingame.app/',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
}

# ==========================================
# 🔐 3. BIGWIN API CLASS (Signature Generator)
# ==========================================
class BigwinAPI:
    def __init__(self, secret_key: str = "bigwin"):
        self.secret_key = secret_key
    
    def generate_random(self, length: int = 32) -> str:
        """Random string 32 characters generate လုပ်ရန်"""
        return ''.join(random.choices(string.hexdigits.lower(), k=length))
    
    def generate_signature(self, timestamp: int, random_str: str, additional_params: str = "") -> str:
        """
        Signature Algorithm:
        MD5(timestamp + random_str + secret_key + additional_params)
        """
        base_string = f"{timestamp}{random_str}{self.secret_key}{additional_params}"
        signature = hashlib.md5(base_string.encode()).hexdigest().upper()
        return signature
    
    def prepare_request_data(self, endpoint: str, params: dict) -> dict:
        """Request data ပြင်ဆင်ရန် (signature ထည့်ပေး)"""
        timestamp = int(time.time())
        random_str = self.generate_random()
        
        additional = ""
        if endpoint == "GameBetting":
            additional = f"{params.get('typeId', '')}{params.get('issuenumber', '')}{params.get('amount', '')}"
        elif endpoint == "GetBalance":
            additional = "balance"
        elif endpoint == "GetNoaverageEmerdList":
            additional = f"{params.get('pageSize', '')}{params.get('pageNo', '')}{params.get('typeId', '')}"
        elif endpoint == "GetWinTheLotteryResult":
            additional = "winresult"
        
        signature = self.generate_signature(timestamp, random_str, additional)
        
        data = {
            **params,
            'language': 7,
            'random': random_str,
            'signature': signature,
            'timestamp': timestamp
        }
        
        return data

# Initialize BigwinAPI
bigwin_api = BigwinAPI(secret_key="bigwin")

# ==========================================
# 🗄️ 4. DATABASE INIT
# ==========================================
async def init_db():
    try:
        await history_collection.create_index("issue_number", unique=True)
        await predictions_collection.create_index("issue_number", unique=True)
        await betting_collection.create_index("issue_number", unique=True)
        print("🗄 MongoDB ချိတ်ဆက်မှု အောင်မြင်ပါသည်။")
    except Exception as e:
        print(f"❌ MongoDB Indexing Error: {e}")

# ==========================================
# 🔑 5. ASYNC API FUNCTIONS
# ==========================================
async def login_and_get_token(session: aiohttp.ClientSession):
    global CURRENT_TOKEN
    print("🔐 အကောင့်ထဲသို့ Login ဝင်နေပါသည်...")
    
    json_data = {
        'username': '959770069402',
        'pwd': 'Mitheint11',
        'phonetype': 1,
        'logintype': 'mobile',
        'packId': '',
        'deviceId': '51ed4ee0f338a1bb24063ffdfcd31ce6',
        'language': 7,
        'random': '917a4606cf0140449f628bbf80a114b4',
        'signature': '221A1FE8611A88CFE0A05A3B7594652F',
        'timestamp': int(time.time()),
    }
    try:
        async with session.post('https://api.bigwinqaz.com/api/webapi/Login', headers=BASE_HEADERS, json=json_data) as response:
            data = await response.json()
            if data.get('code') == 0:
                token_str = data.get('data', {}).get('token', '')
                CURRENT_TOKEN = f"Bearer {token_str}"
                print("✅ Login အောင်မြင်ပါသည်။ Token အသစ် ရရှိပါပြီ။\n")
                return True
            return False
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return False

async def get_user_balance(session: aiohttp.ClientSession):
    """လက်ကျန်ငွေစစ်ဆေးရန် (Signature ပါ)"""
    global CURRENT_TOKEN
    if not CURRENT_TOKEN:
        return 0
    
    headers = BASE_HEADERS.copy()
    headers['authorization'] = CURRENT_TOKEN
    
    request_data = bigwin_api.prepare_request_data("GetBalance", {})
    
    try:
        async with session.post('https://api.bigwinqaz.com/api/webapi/GetBalance', headers=headers, json=request_data) as response:
            data = await response.json()
            if data.get('code') == 0:
                return float(data.get('data', {}).get('amount', 0))
            elif data.get('code') == 401:
                CURRENT_TOKEN = ""
            return 0
    except Exception as e:
        print(f"❌ Balance Check Error: {e}")
        return 0

async def place_martingale_bet(session: aiohttp.ClientSession, issue_number: str, prediction: str):
    """Martingale Strategy နဲ့ထိုးရန်"""
    global CURRENT_TOKEN, PENDING_BETS, CURRENT_BET_AMOUNT, CONSECUTIVE_LOSSES, TOTAL_PROFIT, TOTAL_BETS
    
    if not CURRENT_TOKEN:
        if not await login_and_get_token(session):
            return False, "Login failed"
    
    # လက်ကျန်စစ်ဆေး
    balance = await get_user_balance(session)
    
    if balance < CURRENT_BET_AMOUNT:
        error_msg = (f"❌ လက်ကျန်မလုံလောက်ပါ။\n"
                     f"လက်ကျန်: {balance:,.0f} ကျပ်\n"
                     f"လိုအပ်သောငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
                     f"ဆက်တိုက်အရှုံး: {CONSECUTIVE_LOSSES} ကြိမ်")
        
        global AUTO_BET_ENABLED
        AUTO_BET_ENABLED = False
        
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=f"⚠️ လက်ကျန်မလုံလောက်၍ Auto Bet ရပ်နားပါသည်။\n{error_msg}"
        )
        
        return False, error_msg
    
    # သတ်မှတ်ထားတဲ့အများဆုံးငွေထက်မကျော်အောင်စစ်ဆေး
    if CURRENT_BET_AMOUNT > MAX_BET_AMOUNT:
        error_msg = (f"❌ သတ်မှတ်ထားသောအများဆုံးငွေပမာဏထက်ကျော်လွန်နေပါသည်။\n"
                     f"လက်ရှိထိုးငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
                     f"အများဆုံးခွင့်ပြုငွေ: {MAX_BET_AMOUNT} ကျပ်")
        
        AUTO_BET_ENABLED = False
        return False, error_msg
    
    # selectType: 13 = BIG, 14 = SMALL
    select_type = 13 if prediction == "BIG" else 14
    
    params = {
        'typeId': 30,
        'issuenumber': str(issue_number),
        'amount': CURRENT_BET_AMOUNT,
        'betCount': 1,
        'gameType': 2,
        'selectType': select_type
    }
    
    request_data = bigwin_api.prepare_request_data("GameBetting", params)
    
    headers = BASE_HEADERS.copy()
    headers['authorization'] = CURRENT_TOKEN
    
    try:
        print(f"🎯 Martingale Bet: {issue_number} - {prediction} - {CURRENT_BET_AMOUNT} ကျပ်")
        print(f"📊 Consecutive Losses: {CONSECUTIVE_LOSSES}")
        
        async with session.post('https://api.bigwinqaz.com/api/webapi/GameBetting', 
                               headers=headers, json=request_data) as response:
            data = await response.json()
            
            if data.get('code') == 0:
                # Pending Bets ထဲသိမ်း
                PENDING_BETS[issue_number] = {
                    "amount": CURRENT_BET_AMOUNT,
                    "prediction": prediction,
                    "select_type": select_type,
                    "timestamp": time.time(),
                    "consecutive_losses": CONSECUTIVE_LOSSES
                }
                
                # Bet History ထဲသိမ်း
                BET_HISTORY.append({
                    "issue": issue_number,
                    "amount": CURRENT_BET_AMOUNT,
                    "prediction": prediction,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                TOTAL_BETS += 1
                
                # MongoDB မှာသိမ်း
                await betting_collection.insert_one({
                    "issue_number": issue_number,
                    "amount": CURRENT_BET_AMOUNT,
                    "prediction": prediction,
                    "timestamp": time.time(),
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "pending"
                })
                
                # Channel ကိုအကြောင်းကြား
                bet_msg = (
                    f"💰 <b>Martingale Bet Placed</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"ပွဲစဉ်: <code>{issue_number}</code>\n"
                    f"ထိုးသည့်အမျိုးအစား: {'အကြီး 🔴' if prediction == 'BIG' else 'အသေး 🟢'}\n"
                    f"ငွေပမာဏ: {CURRENT_BET_AMOUNT} ကျပ်\n"
                    f"လက်ကျန်: {balance - CURRENT_BET_AMOUNT:,.0f} ကျပ်\n"
                    f"ဆက်တိုက်အရှုံး: {CONSECUTIVE_LOSSES} ကြိမ်"
                )
                
                await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=bet_msg)
                
                return True, f"✅ ထိုးနိုင်ခဲ့ပါပြီ။ ပွဲစဉ်: {issue_number}"
            else:
                error_msg = data.get('msg', 'Unknown error')
                return False, error_msg
                
    except Exception as e:
        print(f"❌ Bet Error: {e}")
        return False, str(e)

async def check_bet_result(session: aiohttp.ClientSession, issue_number: str, bet_info: dict):
    """ထိုးထားတဲ့ပွဲ နိုင်/ရှုံး စစ်ဆေးရန်"""
    global CURRENT_BET_AMOUNT, CONSECUTIVE_LOSSES, TOTAL_PROFIT, WINS, LOSSES
    
    headers = BASE_HEADERS.copy()
    headers['authorization'] = CURRENT_TOKEN
    
    params = {
        'issueNumber': [issue_number]
    }
    
    request_data = bigwin_api.prepare_request_data("GetWinTheLotteryResult", params)
    
    try:
        async with session.post('https://api.bigwinqaz.com/api/webapi/GetWinTheLotteryResult', 
                               headers=headers, json=request_data) as response:
            data = await response.json()
            
            if data.get('code') == 0:
                result_data = data.get('data', [])
                if result_data:
                    result = result_data[0]
                    lottery_number = result.get('lotteryNumber', 0)
                    win_lose = result.get('winLose', 2)  # 1=win, 2=lose
                    win_amount = result.get('winAmount', 0)
                    
                    # ဂဏန်းအရ အနိုင်/အရှုံးစစ်ဆေး
                    number_size = "BIG" if lottery_number >= 5 else "SMALL"
                    
                    if win_lose == 1 or number_size == bet_info['prediction']:  # နိုင်
                        profit = win_amount - bet_info['amount']
                        TOTAL_PROFIT += profit
                        WINS += 1
                        
                        # နိုင်ရင် ငွေပမာဏကို အခြေခံသို့ပြန်ထား
                        CURRENT_BET_AMOUNT = BASE_BET_AMOUNT
                        CONSECUTIVE_LOSSES = 0
                        
                        result_text = (
                            f"✅ <b>အနိုင်ရရှိပါပြီ။</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"ပွဲစဉ်: <code>{issue_number}</code>\n"
                            f"ထွက်ဂဏန်း: {lottery_number} ({number_size})\n"
                            f"ထိုးငွေ: {bet_info['amount']} ကျပ်\n"
                            f"ရရှိငွေ: {win_amount} ကျပ်\n"
                            f"အမြတ်: +{profit} ကျပ်\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"စုစုပေါင်းအမြတ်: {TOTAL_PROFIT} ကျပ်\n"
                            f"အနိုင်/အရှုံး: {WINS}/{LOSSES}\n"
                            f"နောက်ထိုးမည့်ငွေ: {CURRENT_BET_AMOUNT} ကျပ်"
                        )
                        
                        # MongoDB မှာ update
                        await betting_collection.update_one(
                            {"issue_number": issue_number},
                            {"$set": {
                                "status": "win",
                                "result_number": lottery_number,
                                "result_size": number_size,
                                "win_amount": win_amount,
                                "profit": profit
                            }}
                        )
                        
                    else:  # ရှုံး
                        loss = bet_info['amount']
                        TOTAL_PROFIT -= loss
                        LOSSES += 1
                        
                        # ရှုံးရင် ငွေပမာဏကို ၂ ဆတိုး
                        CURRENT_BET_AMOUNT = bet_info['amount'] * 2
                        CONSECUTIVE_LOSSES += 1
                        
                        result_text = (
                            f"❌ <b>အရှုံးပါ။</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"ပွဲစဉ်: <code>{issue_number}</code>\n"
                            f"ထွက်ဂဏန်း: {lottery_number} ({number_size})\n"
                            f"ထိုးငွေ: {bet_info['amount']} ကျပ်\n"
                            f"ဆုံးရှုံးမှု: -{loss} ကျပ်\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"စုစုပေါင်းအမြတ်: {TOTAL_PROFIT} ကျပ်\n"
                            f"အနိုင်/အရှုံး: {WINS}/{LOSSES}\n"
                            f"ဆက်တိုက်အရှုံး: {CONSECUTIVE_LOSSES} ကြိမ်\n"
                            f"နောက်ထိုးမည့်ငွေ: {CURRENT_BET_AMOUNT} ကျပ်"
                        )
                        
                        # MongoDB မှာ update
                        await betting_collection.update_one(
                            {"issue_number": issue_number},
                            {"$set": {
                                "status": "lose",
                                "result_number": lottery_number,
                                "result_size": number_size,
                                "loss": loss
                            }}
                        )
                        
                        # ဆက်တိုက်အရှုံး ၁၀ ကြိမ်ရှိရင် သတိပေး
                        if CONSECUTIVE_LOSSES >= MAX_CONSECUTIVE_LOSSES:
                            result_text += (
                                f"\n⚠️ <b>သတိပေးချက်!</b>\n"
                                f"ဆက်တိုက်အရှုံး {CONSECUTIVE_LOSSES} ကြိမ်ရှိပါပြီ။\n"
                                f"ထိုးနည်းစနစ်ပြောင်းရန်စဉ်းစားပါ။"
                            )
                    
                    # Channel ကိုပို့
                    await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=result_text)
                    
                    return True
                    
    except Exception as e:
        print(f"❌ Check Result Error: {e}")
        return False

async def check_game_and_predict(session: aiohttp.ClientSession):
    """ဂိမ်းဒေတာယူပြီး ခန့်မှန်းချက်ထုတ်ရန်"""
    global CURRENT_TOKEN, LAST_PROCESSED_ISSUE, LAST_PREDICTED_ISSUE, LAST_PREDICTED_RESULT
    global CURRENT_WIN_STREAK, CURRENT_LOSE_STREAK, LONGEST_WIN_STREAK, LONGEST_LOSE_STREAK, TOTAL_PREDICTIONS
    
    if not CURRENT_TOKEN:
        if not await login_and_get_token(session):
            return

    params = {
        'pageSize': 10,
        'pageNo': 1,
        'typeId': 30
    }
    
    request_data = bigwin_api.prepare_request_data("GetNoaverageEmerdList", params)
    
    headers = BASE_HEADERS.copy()
    headers['authorization'] = CURRENT_TOKEN

    try:
        async with session.post('https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList', headers=headers, json=request_data) as response:
            data = await response.json()
            if data.get('code') == 0:
                records = data.get("data", {}).get("list", [])
                if not records:
                    return
                
                latest_record = records[0]
                latest_issue = str(latest_record["issueNumber"])
                latest_number = int(latest_record["number"])
                latest_size = "BIG" if latest_number >= 5 else "SMALL"
                
                if latest_issue == LAST_PROCESSED_ISSUE:
                    return
                
                LAST_PROCESSED_ISSUE = latest_issue
                next_issue = str(int(latest_issue) + 1)
                win_lose_text = ""
                
                await history_collection.update_one(
                    {"issue_number": latest_issue}, 
                    {"$setOnInsert": {"number": latest_number, "size": latest_size}}, 
                    upsert=True
                )
                
                # နိုင်/ရှုံး စစ်ဆေးခြင်း
                if LAST_PREDICTED_ISSUE == latest_issue:
                    is_win = (LAST_PREDICTED_RESULT == latest_size)
                    TOTAL_PREDICTIONS += 1
                    
                    if is_win:
                        win_lose_status = "WIN ✅"
                        CURRENT_WIN_STREAK += 1
                        CURRENT_LOSE_STREAK = 0
                        if CURRENT_WIN_STREAK > LONGEST_WIN_STREAK:
                            LONGEST_WIN_STREAK = CURRENT_WIN_STREAK
                    else:
                        win_lose_status = "LOSE ❌"
                        CURRENT_LOSE_STREAK += 1
                        CURRENT_WIN_STREAK = 0
                        if CURRENT_LOSE_STREAK > LONGEST_LOSE_STREAK:
                            LONGEST_LOSE_STREAK = CURRENT_LOSE_STREAK
                    
                    await predictions_collection.update_one(
                        {"issue_number": latest_issue}, 
                        {"$set": {"actual_size": latest_size, "win_lose": win_lose_status}}
                    )
                    
                    win_lose_text = (
                        f"🏆 <b>ပြီးခဲ့သောပွဲစဉ် ({latest_issue})</b> ရလဒ်: {latest_size}\n"
                        f"📊 <b>ခန့်မှန်းချက်: {win_lose_status}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                    )

                # AI Pattern Prediction
                cursor = history_collection.find().sort("issue_number", -1).limit(5000)
                history_docs = await cursor.to_list(length=5000)
                history_docs.reverse()
                all_history = [doc["size"] for doc in history_docs]
                
                predicted = "BIG (အကြီး) 🔴"
                base_prob = 55.0
                reason = "Pattern အသစ်ဖြစ်နေသဖြင့် သမိုင်းကြောင်းအရ တွက်ချက်ထားသည်"
                
                MAX_PATTERN_LENGTH = 10
                MIN_PATTERN_LENGTH = 10
                pattern_found = False
                
                for current_len in range(MAX_PATTERN_LENGTH, MIN_PATTERN_LENGTH - 1, -1):
                    if len(all_history) > current_len:
                        recent_pattern = all_history[-current_len:]
                        big_next_count = 0
                        small_next_count = 0
                        
                        for i in range(len(all_history) - current_len):
                            if all_history[i:i+current_len] == recent_pattern:
                                next_result = all_history[i+current_len]
                                if next_result == 'BIG':
                                    big_next_count += 1
                                elif next_result == 'SMALL':
                                    small_next_count += 1
                        
                        total_pattern_matches = big_next_count + small_next_count
                        if total_pattern_matches > 0:
                            big_prob = (big_next_count / total_pattern_matches) * 100
                            small_prob = (small_next_count / total_pattern_matches) * 100
                            pattern_str = "-".join(recent_pattern).replace('BIG', 'B').replace('SMALL', 'S')
                            
                            if big_prob > small_prob:
                                predicted = "BIG (အကြီး) 🔴"
                                base_prob = big_prob
                                reason = f"[{pattern_str}] လာလျှင် အကြီးဆက်ထွက်လေ့ရှိ၍"
                            elif small_prob > big_prob:
                                predicted = "SMALL (အသေး) 🟢"
                                base_prob = small_prob
                                reason = f"[{pattern_str}] လာလျှင် အသေးဆက်ထွက်လေ့ရှိ၍"
                            else:
                                predicted = "BIG (အကြီး) 🔴"
                                base_prob = 50.0
                                reason = f"[{pattern_str}] အရင်က မျှခြေထွက်ဖူး၍ အကြီးရွေးထားသည်"
                            
                            pattern_found = True
                            break
                
                if not pattern_found:
                    big_count = all_history.count("BIG")
                    small_count = all_history.count("SMALL")
                    predicted = "BIG (အကြီး) 🔴" if big_count > small_count else "SMALL (အသေး) 🟢"
                    base_prob = 55.0
                    reason = "Pattern အသစ်ဖြစ်နေသဖြင့် သမိုင်းကြောင်းအရ တွက်ချက်ထားသည်"

                final_prob = min(round(base_prob, 1), 85.0)

                LAST_PREDICTED_ISSUE = next_issue
                LAST_PREDICTED_RESULT = "BIG" if "BIG" in predicted else "SMALL"
                
                await predictions_collection.update_one(
                    {"issue_number": next_issue}, 
                    {"$set": {
                        "predicted_size": LAST_PREDICTED_RESULT, 
                        "probability": final_prob, 
                        "actual_size": None, 
                        "win_lose": None
                    }}, 
                    upsert=True
                )

                print(f"✅ [NEW] ပွဲစဉ်: {next_issue} | Predict: {predicted}")

                # Telegram Message
                tg_message = (
                    f"🎰 <b>Bigwin 30-Seconds (AI Predictor)</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{win_lose_text}"
                    f"🎯 <b>နောက်ပွဲစဉ်အမှတ် :</b>\n"
                    f"<code>{next_issue}</code>\n"
                    f"🤖 <b>AI ခန့်မှန်းချက် : {predicted}</b>\n"
                    f"📈 <b>ဖြစ်နိုင်ခြေ :</b> {final_prob}%\n"
                    f"💡 <b>အကြောင်းပြချက် :</b>\n"
                    f"{reason}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Cᴜʀʀᴇɴᴛ Wɪɴ Sᴛʀᴇᴀᴋ : {CURRENT_WIN_STREAK}\n"
                    f"Cᴜʀʀᴇɴᴛ Lᴏsᴇ Sᴛʀᴇᴀᴋ : {CURRENT_LOSE_STREAK}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Lᴏɴɢᴇsᴛ Wɪɴ Sᴛʀᴇᴀᴋ : {LONGEST_WIN_STREAK}\n"
                    f"Lᴏɴɢᴇsᴛ Lᴏsᴇ Sᴛʀᴇᴀᴋ : {LONGEST_LOSE_STREAK}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Tᴏᴛᴀʟ Pʀᴇᴅɪᴄᴛɪᴏɴs : {TOTAL_PREDICTIONS}"
                )
                
                try:
                    await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=tg_message)
                except Exception as e:
                    print(f"❌ Telegram Send Error: {e}")
                
                # Auto Bet ဖွင့်ထားရင် ထိုးမည်
                if AUTO_BET_ENABLED and LAST_PREDICTED_RESULT:
                    await asyncio.sleep(2)  # ခဏစောင့်ပြီးမှထိုး
                    success, msg = await place_martingale_bet(session, next_issue, LAST_PREDICTED_RESULT)
                    if not success:
                        print(f"❌ Auto Bet Failed: {msg}")
                
            elif data.get('code') == 401:
                CURRENT_TOKEN = ""
                
    except Exception as e:
        print(f"❌ Game Data Request Error: {e}")

# ==========================================
# 🔄 6. BACKGROUND TASK
# ==========================================
async def check_pending_bets_background():
    """နောက်ကွယ်ကနေ Bet Result တွေစစ်ဆေးရန်"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                if CURRENT_TOKEN and PENDING_BETS:
                    completed_issues = []
                    
                    for issue_number, bet_info in PENDING_BETS.items():
                        # 2 မိနစ်ကြာမှသာစစ်ဆေး (ပွဲပြီးဖို့စောင့်)
                        if time.time() - bet_info["timestamp"] > 120:
                            await check_bet_result(session, issue_number, bet_info)
                            completed_issues.append(issue_number)
                    
                    for issue in completed_issues:
                        del PENDING_BETS[issue]
                
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"❌ Check Results Error: {e}")
                await asyncio.sleep(60)

async def auto_broadcaster():
    """ပင်မ Broadcaster Task"""
    await init_db()
    async with aiohttp.ClientSession() as session:
        await login_and_get_token(session)
        while True:
            await check_game_and_predict(session)
            await asyncio.sleep(5)

# ==========================================
# 🤖 7. COMMAND HANDLERS
# ==========================================
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "👋 မင်္ဂလာပါ။ Bigwin AI Predictor Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "📋 ရနိုင်သော Commands များ:\n"
        "/autobet on - အလိုအလျောက်ထိုးခြင်းဖွင့်ရန်\n"
        "/autobet off - အလိုအလျောက်ထိုးခြင်းပိတ်ရန်\n"
        "/setbasebet [ငွေပမာဏ] - အခြေခံထိုးငွေသတ်မှတ်ရန်\n"
        "/martingale - Martingale အခြေအနေကြည့်ရန်\n"
        "/reset_martingale - Martingale ပြန်စရန်\n"
        "/balance - လက်ကျန်ငွေကြည့်ရန်\n"
        "/status - လက်ရှိအခြေအနေကြည့်ရန်\n"
        "/stats - စာရင်းဇယားကြည့်ရန်"
    )

@dp.message(Command("autobet"))
async def toggle_autobet(message: types.Message):
    global AUTO_BET_ENABLED, CURRENT_BET_AMOUNT, BASE_BET_AMOUNT
    
    args = message.text.split()
    if len(args) < 2:
        status_text = "✅ ဖွင့်ထားသည်" if AUTO_BET_ENABLED else "❌ ပိတ်ထားသည်"
        await message.reply(
            f"🤖 Auto Bet Status: {status_text}\n"
            f"💰 အခြေခံထိုးငွေ: {BASE_BET_AMOUNT} ကျပ်\n"
            f"💵 လက်ရှိထိုးငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"သုံးရန်:\n"
            f"/autobet on - ဖွင့်ရန်\n"
            f"/autobet off - ပိတ်ရန်\n"
            f"/setbasebet [ငွေပမာဏ] - အခြေခံထိုးငွေပြောင်းရန်"
        )
        return
    
    command = args[1].lower()
    if command == "on":
        if not AUTO_BET_ENABLED:
            async with aiohttp.ClientSession() as session:
                balance = await get_user_balance(session)
                if balance < MIN_BALANCE_REQUIRED:
                    await message.reply(f"❌ လက်ကျန်မလုံလောက်ပါ။ အနည်းဆုံး {MIN_BALANCE_REQUIRED} ကျပ်လိုအပ်ပါသည်။\nလက်ကျန်: {balance:,.0f} ကျပ်")
                    return
            
            AUTO_BET_ENABLED = True
            CURRENT_BET_AMOUNT = BASE_BET_AMOUNT  # ပြန်စသည်
            
            await message.reply(
                f"✅ Auto Bet ကိုဖွင့်လိုက်ပါပြီ။\n"
                f"💰 အခြေခံထိုးငွေ: {BASE_BET_AMOUNT} ကျပ်\n"
                f"📊 Strategy: Martingale (ရှုံးတိုင်း ၂ ဆတိုး)\n"
                f"⚠️ သတိပေးချက်: ငွေအရှုံးပေါ်ပါက တာဝန်မယူပါ။"
            )
    elif command == "off":
        if AUTO_BET_ENABLED:
            AUTO_BET_ENABLED = False
            await message.reply("🛑 Auto Bet ကိုပိတ်လိုက်ပါပြီ။")
    else:
        await message.reply("❌ /autobet on သို့မဟုတ် /autobet off သာသုံးပါ။")

@dp.message(Command("setbasebet"))
async def set_base_bet(message: types.Message):
    global BASE_BET_AMOUNT, CURRENT_BET_AMOUNT
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply(f"💰 လက်ရှိအခြေခံထိုးငွေ: {BASE_BET_AMOUNT} ကျပ်\n\nသုံးရန်: /setbasebet 20")
        return
    
    try:
        new_amount = int(args[1])
        if new_amount < 10:
            await message.reply("❌ အနည်းဆုံး 10 ကျပ်ထက်မနည်းရပါ။")
            return
        if new_amount > 1000:
            await message.reply("❌ အခြေခံထိုးငွေသည် 1000 ကျပ်ထက်မများရပါ။")
            return
        
        BASE_BET_AMOUNT = new_amount
        CURRENT_BET_AMOUNT = new_amount  # ပြန်စသည်
        
        await message.reply(f"✅ အခြေခံထိုးငွေပမာဏကို {BASE_BET_AMOUNT} ကျပ်သို့ပြောင်းလိုက်ပါပြီ။")
    except ValueError:
        await message.reply("❌ ကျေးဇူးပြု၍ ကိန်းဂဏန်းသာထည့်ပါ။")

@dp.message(Command("martingale"))
async def martingale_status(message: types.Message):
    global CURRENT_BET_AMOUNT, CONSECUTIVE_LOSSES, TOTAL_PROFIT, BASE_BET_AMOUNT, MAX_BET_AMOUNT, WINS, LOSSES, TOTAL_BETS
    
    win_rate = (WINS / TOTAL_BETS * 100) if TOTAL_BETS > 0 else 0
    
    status_text = (
        f"📊 <b>Martingale Strategy Status</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 အခြေခံထိုးငွေ: {BASE_BET_AMOUNT} ကျပ်\n"
        f"💵 လက်ရှိထိုးငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
        f"📈 ဆက်တိုက်အရှုံး: {CONSECUTIVE_LOSSES} ကြိမ်\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 စာရင်းဇယား\n"
        f"စုစုပေါင်းအမြတ်: {TOTAL_PROFIT} ကျပ်\n"
        f"အနိုင်/အရှုံး: {WINS}/{LOSSES}\n"
        f"အနိုင်ရနှုန်း: {win_rate:.1f}%\n"
        f"စုစုပေါင်းထိုးကြိမ်: {TOTAL_BETS}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 နောက်ထိုးမည့်ငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
        f"⚠️ အများဆုံးထိုးငွေ: {MAX_BET_AMOUNT} ကျပ်"
    )
    
    await message.reply(status_text)

@dp.message(Command("reset_martingale"))
async def reset_martingale(message: types.Message):
    global CURRENT_BET_AMOUNT, CONSECUTIVE_LOSSES, TOTAL_PROFIT, WINS, LOSSES, TOTAL_BETS, BET_HISTORY
    
    CURRENT_BET_AMOUNT = BASE_BET_AMOUNT
    CONSECUTIVE_LOSSES = 0
    TOTAL_PROFIT = 0
    WINS = 0
    LOSSES = 0
    TOTAL_BETS = 0
    BET_HISTORY = []
    
    await message.reply("✅ Martingale Strategy ကိုပြန်စလိုက်ပါပြီ။")

@dp.message(Command("balance"))
async def check_balance(message: types.Message):
    async with aiohttp.ClientSession() as session:
        if not CURRENT_TOKEN:
            await login_and_get_token(session)
        
        balance = await get_user_balance(session)
        await message.reply(f"💰 လက်ကျန်ငွေ: {balance:,.0f} ကျပ်")

@dp.message(Command("status"))
async def show_status(message: types.Message):
    status_text = "✅ ဖွင့်ထားသည်" if AUTO_BET_ENABLED else "❌ ပိတ်ထားသည်"
    
    async with aiohttp.ClientSession() as session:
        balance = await get_user_balance(session)
        
        status_message = (
            f"📊 <b>Bot အခြေအနေ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Auto Bet: {status_text}\n"
            f"💰 အခြေခံထိုးငွေ: {BASE_BET_AMOUNT} ကျပ်\n"
            f"💵 လက်ရှိထိုးငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
            f"💳 လက်ကျန်ငွေ: {balance:,.0f} ကျပ်\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 စာရင်းဇယားများ\n"
            f"Current Win: {CURRENT_WIN_STREAK}\n"
            f"Current Lose: {CURRENT_LOSE_STREAK}\n"
            f"Longest Win: {LONGEST_WIN_STREAK}\n"
            f"Longest Lose: {LONGEST_LOSE_STREAK}\n"
            f"Total Predictions: {TOTAL_PREDICTIONS}\n"
            f"Pending Bets: {len(PENDING_BETS)}"
        )
        
        await message.reply(status_message)

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    """အသေးစိတ်စာရင်းဇယားပြရန်"""
    global WINS, LOSSES, TOTAL_PROFIT, TOTAL_BETS, CONSECUTIVE_LOSSES
    
    win_rate = (WINS / TOTAL_BETS * 100) if TOTAL_BETS > 0 else 0
    
    stats_text = (
        f"📈 <b>အသေးစိတ်စာရင်းဇယား</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 စုစုပေါင်းထိုးကြိမ်: {TOTAL_BETS}\n"
        f"✅ အနိုင်ရကြိမ်: {WINS}\n"
        f"❌ အရှုံးကြိမ်: {LOSSES}\n"
        f"📊 အနိုင်ရနှုန်း: {win_rate:.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 စုစုပေါင်းအမြတ်: {TOTAL_PROFIT} ကျပ်\n"
        f"📈 ဆက်တိုက်အရှုံး: {CONSECUTIVE_LOSSES} ကြိမ်\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 နောက်ထိုးမည့်ငွေ: {CURRENT_BET_AMOUNT} ကျပ်\n"
        f"📋 မှတ်တမ်းအရေအတွက်: {len(BET_HISTORY)}"
    )
    
    await message.reply(stats_text)

# ==========================================
# 🚀 8. MAIN FUNCTION
# ==========================================
async def main():
    print("🚀 Bigwin AI Bot (Martingale Strategy) စတင်နေပါပြီ...\n")
    print(f"📊 Martingale Settings:")
    print(f"   - အခြေခံထိုးငွေ: {BASE_BET_AMOUNT} ကျပ်")
    print(f"   - အများဆုံးထိုးငွေ: {MAX_BET_AMOUNT} ကျပ်")
    print(f"   - ဆက်တိုက်အရှုံးကန့်သတ်ချက်: {MAX_CONSECUTIVE_LOSSES} ကြိမ်\n")
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start background tasks
    asyncio.create_task(auto_broadcaster())
    asyncio.create_task(check_pending_bets_background())
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot ကိုရပ်တန့်လိုက်ပါသည်။")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")

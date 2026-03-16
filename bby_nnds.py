"""
====================================================================================
🏆 ULTRA-AI PREDICTION SYSTEM (10-CORE ARCHITECTURE) 🏆
====================================================================================
Developer: Master AI System
Target: 6win566 Win Go (Regular)
Architecture: Modular Object-Oriented Programming (OOP)
Engines: RandomForest, GradientBoost, Markov, NGram, MonteCarlo, 
         Trend, Bayesian, LSTM, Entropy, Meta-Optimizer.
====================================================================================
"""

import asyncio
import time
import os
import logging
import math
from collections import Counter
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from dotenv import load_dotenv

# Async Web & Database
import aiohttp
import motor.motor_asyncio 

# Telegram UI
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# --- 🧠 ULTRA AI & DATA SCIENCE LIBRARIES ---
import numpy as np
import scipy.stats as stats
import random
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim

import warnings
warnings.filterwarnings("ignore")

# =========================================================================
# ⚙️ MODULE 1: SYSTEM CONFIGURATION & ADVANCED LOGGING
# =========================================================================
load_dotenv()

# Logger ကို စနစ်တကျ တည်ဆောက်ခြင်း
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ULTRA-AI")

class Config:
    """ စနစ်တစ်ခုလုံးအတွက် လိုအပ်သော ကနဦး အချက်အလက်များ """
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "YOUR_CHANNEL_ID")
    MONGO_URI: str = os.getenv("MONGO_URI", "YOUR_MONGO_URI")
    
    # UI Elements
    WIN_STICKER: str = "CAACAgUAAxkBAAEQwtVpt1_oWxyaQFmiy3O_1knZjN9yCwAC2hIAAikFkVX0qhu40v6REDoE"  
    LOSE_STICKER: str = "" 
    
    # Auto Multiplier Strategy (Martingale Hybrid)
    MULTIPLIERS: List[int] = [1, 2, 3, 5, 8, 15, 30, 50, 100]
    
    # API Configuration (Regular Win Go)
    API_URL: str = 'https://6lotteryapi.com/api/webapi/GetNoaverageEmerdList'
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """ API Request အတွက် Headers များကို ထုတ်ပေးသည် """
        return {
            'authority': '6lotteryapi.com', 
            'accept': 'application/json, text/plain, */*',
            # 💡 သတိပြုရန်: ဤနေရာတွင် Token အသစ်ကို အစားထိုးပါ
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzczNjMxOTU4IiwibmJmIjoiMTc3MzYzMTk1OCIsImV4cCI6IjE3NzM2MzM3NTgiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiIzLzE2LzIwMjYgMTA6MzI6MzggQU0iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBY2Nlc3NfVG9rZW4iLCJVc2VySWQiOiIxMDc2NTk0IiwiVXNlck5hbWUiOiI5NTk2NzUzMjM4NzgiLCJVc2VyUGhvdG8iOiI3IiwiTmlja05hbWUiOiLhgJXhgLzhgIrhgLfhgLrhgIXhgK_hgLYiLCJBbW91bnQiOiI5NS41NSIsIkludGVncmFsIjoiMCIsIkxvZ2luTWFyayI6Ikg1IiwiTG9naW5UaW1lIjoiMy8xNi8yMDI2IDEwOjAyOjM4IEFNIiwiTG9naW5JUEFkZHJlc3MiOiIxMDMuMTM0LjIwNy4xNTIiLCJEYk51bWJlciI6IjAiLCJJc3ZhbGlkYXRvciI6IjAiLCJLZXlDb2RlIjoiMTA2IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6IiIsImlzcyI6Imp3dElzc3VlciIsImF1ZCI6ImxvdHRlcnlUaWNrZXQifQ.ODo3Y-5b0iaBUF8O05E1eOsxWj8WpKgIqETu0LeEWR8',
            'content-type': 'application/json;charset=UTF-8', 
            'origin': 'https://www.6win566.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# =========================================================================
# 🗄️ MODULE 2: ASYNC DATABASE MANAGER
# =========================================================================
class DatabaseManager:
    """ MongoDB သို့ ချိတ်ဆက်၍ Data အဝင်အထွက်များကို စီမံသော Class """
    
    def __init__(self, uri: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client['sixlottery_ultra']
        self.history = self.db['game_history']
        self.predictions = self.db['predictions']

    async def initialize(self) -> None:
        """ Database Index များကို စတင်တည်ဆောက်သည် """
        try:
            await self.history.create_index("issue_number", unique=True)
            await self.predictions.create_index("issue_number", unique=True)
            logger.info("✅ Async Database Initialized Successfully.")
        except Exception as e:
            logger.error(f"❌ Database Initialization Error: {e}")

    async def save_history(self, issue: str, number: int, size: str, parity: str) -> None:
        """ ပွဲစဉ်ရလဒ် အသစ်များကို သမိုင်းကြောင်းအဖြစ် သိမ်းဆည်းသည် """
        try:
            doc = {
                "number": int(number),
                "size": str(size),
                "parity": str(parity),
                "timestamp": datetime.now()
            }
            await self.history.update_one(
                {"issue_number": issue}, 
                {"$setOnInsert": doc}, 
                upsert=True
            )
        except Exception as e:
            logger.error(f"Save History Error: {e}")

    async def save_prediction(self, issue: str, pred_size: str, confidence: float, details: Dict[str, float]) -> None:
        """ AI ၏ ခန့်မှန်းချက်များကို နောက်ပိုင်း ပြန်လည်စစ်ဆေးရန် သိမ်းဆည်းသည် """
        try:
            doc = {
                "predicted_size": str(pred_size), 
                "confidence": float(confidence), 
                "model_votes": details, 
                "timestamp": datetime.now()
            }
            await self.predictions.update_one(
                {"issue_number": issue},
                {"$set": doc},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Save Prediction Error: {e}")

    async def update_result(self, issue: str, actual_size: str, actual_number: int, win_lose: str) -> None:
        """ ပွဲပြီးဆုံးသွားသောအခါ ခန့်မှန်းချက် မှန်/မမှန် Update ပြုလုပ်သည် """
        try:
            doc = {
                "actual_size": str(actual_size), 
                "actual_number": int(actual_number), 
                "win_lose": str(win_lose)
            }
            await self.predictions.update_one(
                {"issue_number": issue},
                {"$set": doc}
            )
        except Exception as e:
            logger.error(f"Update Result Error: {e}")

    async def get_history(self, limit: int = 500) -> List[Dict[str, Any]]:
        """ AI သင်ယူရန်အတွက် သမိုင်းကြောင်းများကို ဆွဲထုတ်သည် """
        try:
            return await self.history.find().sort("issue_number", -1).limit(limit).to_list(length=limit)
        except Exception as e:
            logger.error(f"Get History Error: {e}")
            return []

    async def get_recent_predictions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """ Streak တွက်ချက်ရန် နောက်ဆုံး ခန့်မှန်းချက်များကို ဆွဲထုတ်သည် """
        try:
            return await self.predictions.find({"win_lose": {"$ne": None}}).sort("issue_number", -1).limit(limit).to_list(length=limit)
        except Exception as e:
            logger.error(f"Get Predictions Error: {e}")
            return []

# =========================================================================
# 🔬 MODULE 3: ADVANCED FEATURE ENGINEERING
# =========================================================================
class FeatureEngineer:
    """ Raw Data များကို Deep Learning နှင့် ML နားလည်သော သင်္ချာကိန်းဂဏန်းများအဖြစ် ပြောင်းလဲသည် """
    
    def __init__(self, window_size: int = 6):
        self.window = window_size
        self.scaler = StandardScaler()

    def extract_features(self, sizes: List[str], numbers: List[int], parities: List[str]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """ 
        Time-Series Sequence မှ Window Size အလိုက် Features များကို ဖြတ်ထုတ်သည် 
        Returns: (X_train_scaled, y_train, X_current_scaled)
        """
        if len(sizes) < self.window * 4:
            return None, None, None
            
        X, y = [], []
        try:
            for i in range(len(sizes) - self.window):
                row = []
                for j in range(self.window):
                    size_val = 1.0 if sizes[i+j] == 'BIG' else 0.0
                    par_val = 1.0 if parities[i+j] == 'EVEN' else 0.0
                    num_val = float(numbers[i+j])
                    row.extend([size_val, par_val, num_val])
                X.append(row)
                y.append(1.0 if sizes[i+self.window] == 'BIG' else 0.0)
            
            curr_feats = []
            for j in range(1, self.window + 1):
                size_val = 1.0 if sizes[-j] == 'BIG' else 0.0
                par_val = 1.0 if parities[-j] == 'EVEN' else 0.0
                num_val = float(numbers[-j])
                curr_feats.extend([size_val, par_val, num_val])
                
            # Standardization လုပ်ခြင်းဖြင့် AI ပိုမိုမြန်ဆန်စွာ သင်ယူနိုင်သည်
            X_scaled = self.scaler.fit_transform(X)
            curr_scaled = self.scaler.transform([curr_feats])
            
            return X_scaled, np.array(y), curr_scaled
        except Exception as e:
            logger.error(f"Feature Engineering Error: {e}")
            return None, None, None

# =========================================================================
# 🧠 MODULE 4: THE 10 AI CORES (SUB-ENGINES)
# =========================================================================

class TreeEngines:
    """ Core 1 & 2: Random Forest နှင့် Gradient Boosting """
    def __init__(self):
        self.rf = RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42, n_jobs=-1)
        self.gb = GradientBoostingClassifier(n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42)
        
    def predict(self, X: np.ndarray, y: np.ndarray, curr_X: np.ndarray) -> Tuple[float, float]:
        try:
            self.rf.fit(X, y)
            self.gb.fit(X, y)
            rf_prob = float(self.rf.predict_proba(curr_X)[0][1]) if 1.0 in self.rf.classes_ else 0.5
            gb_prob = float(self.gb.predict_proba(curr_X)[0][1]) if 1.0 in self.gb.classes_ else 0.5
            return rf_prob, gb_prob
        except Exception:
            return 0.5, 0.5

class MarkovEngine:
    """ Core 3: Markov Chain State Transition Probabilities """
    @staticmethod
    def predict(sizes: List[str]) -> float:
        if len(sizes) < 10: return 0.5
        trans = {'BIG': {'BIG': 0, 'SMALL': 0}, 'SMALL': {'BIG': 0, 'SMALL': 0}}
        try:
            for i in range(len(sizes)-1): 
                trans[sizes[i]][sizes[i+1]] += 1
            curr = sizes[-1]
            tot = sum(trans[curr].values())
            return float(trans[curr]['BIG'] / tot) if tot > 0 else 0.5
        except: return 0.5

class NGramEngine:
    """ Core 4: Sequential Pattern Matching (N-Grams) """
    @staticmethod
    def predict(sizes: List[str], n: int = 4) -> float:
        if len(sizes) < n+1: return 0.5
        try:
            pat = tuple(sizes[-n:])
            matches = [sizes[i+n] for i in range(len(sizes)-n) if tuple(sizes[i:i+n]) == pat]
            if not matches: return 0.5
            return float(matches.count('BIG') / len(matches))
        except: return 0.5

class MonteCarloEngine:
    """ Core 5: Monte Carlo Random Walk Simulations """
    @staticmethod
    def predict(sizes: List[str], sims: int = 1000) -> float:
        if not sizes: return 0.5
        try:
            prob_b = sizes.count('BIG') / len(sizes)
            results = np.random.choice([1.0, 0.0], size=sims, p=[prob_b, 1.0-prob_b])
            return float(np.mean(results))
        except: return 0.5

class TrendEngine:
    """ Core 6: Market Trend & Momentum Analyzer """
    @staticmethod
    def predict(sizes: List[str], window: int = 15) -> float:
        if len(sizes) < window: return 0.5
        try:
            recent = sizes[-window:]
            momentum = recent.count('BIG') / float(window)
            # Mean Reversion Logic (Overbought/Oversold)
            if momentum >= 0.8: return 0.25 
            if momentum <= 0.2: return 0.75 
            return float(momentum)
        except: return 0.5

class BayesianEngine:
    """ Core 7: Naive Bayes Probability Network """
    def __init__(self): 
        self.nb = GaussianNB()
        
    def predict(self, X: np.ndarray, y: np.ndarray, curr_X: np.ndarray) -> float:
        try:
            self.nb.fit(X, y)
            return float(self.nb.predict_proba(curr_X)[0][1]) if 1.0 in self.nb.classes_ else 0.5
        except: return 0.5

class SimpleLSTM(nn.Module):
    """ PyTorch Neural Network Structure """
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=16, num_layers=1, batch_first=True)
        self.fc = nn.Linear(16, 1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        out = self.fc(hn[-1])
        return self.sigmoid(out)

class LSTMEngine:
    """ Core 8: Long Short-Term Memory Deep Learning """
    def predict(self, sizes: List[str]) -> float:
        if len(sizes) < 50: return 0.5
        try:
            # Prepare Sequence
            data = [1.0 if s == 'BIG' else 0.0 for s in sizes[-50:]]
            X_t = torch.tensor(data[:-1], dtype=torch.float32).view(1, -1, 1)
            y_t = torch.tensor([data[-1]], dtype=torch.float32).view(1, 1)
            
            # Fast Online Training
            model = SimpleLSTM()
            optimizer = optim.Adam(model.parameters(), lr=0.01)
            criterion = nn.BCELoss()
            
            model.train()
            for _ in range(5): # 5 Epochs for real-time speed
                optimizer.zero_grad()
                loss = criterion(model(X_t), y_t)
                loss.backward()
                optimizer.step()
            
            # Predict Next
            model.eval()
            curr_X = torch.tensor(data[1:], dtype=torch.float32).view(1, -1, 1)
            with torch.no_grad(): 
                prediction = model(curr_X).item()
            return float(prediction)
        except Exception as e: 
            logger.warning(f"LSTM Error: {e}")
            return 0.5

class EntropyEngine:
    """ Core 9: Shannon Entropy (Chaos & Volatility) Measurement """
    @staticmethod
    def predict(sizes: List[str]) -> float:
        if len(sizes) < 20: return 0.5
        try:
            recent = sizes[-20:]
            p_b = recent.count('BIG') / 20.0
            p_s = 1.0 - p_b
            if p_b == 0 or p_s == 0: return float(p_b)
            
            entropy = stats.entropy([p_b, p_s], base=2)
            # If entropy is extremely high (>0.98), market is chaotic. Default to 0.5
            if entropy > 0.98: return 0.5 
            return float(p_b)
        except: return 0.5

class MetaOptimizer:
    """ Core 10: Dynamic Weight Adjustment (Self-Learning Hub) """
    def __init__(self):
        self.weights: Dict[str, float] = {
            'rf': 0.15, 'gb': 0.15, 'markov': 0.10, 'ngram': 0.10,
            'monte': 0.05, 'trend': 0.10, 'bayes': 0.10, 'lstm': 0.15, 'entropy': 0.10
        }

    def update(self, actual: str, past_preds: Dict[str, float]) -> None:
        if not past_preds: return
        try:
            actual_val = 1.0 if actual == 'BIG' else 0.0
            total_w = 0.0
            
            for model, prob in past_preds.items():
                error = abs(actual_val - prob)
                # Reward accuracy, penalize error
                if error < 0.4: 
                    self.weights[model] += 0.05
                else: 
                    self.weights[model] = max(0.01, self.weights[model] - 0.02)
                total_w += self.weights[model]
                
            # Normalize
            if total_w > 0:
                for k in self.weights: 
                    self.weights[k] = float(self.weights[k] / total_w)
        except Exception as e:
            logger.error(f"Meta Optimizer Error: {e}")

# =========================================================================
# ⚙️ MODULE 5: MASTER ORCHESTRATOR
# =========================================================================
class UltraMasterEngine:
    """ 10-Core System အားလုံးကို တစ်နေရာတည်းမှ ပေါင်းစပ်ထိန်းချုပ်သော အင်ဂျင်ကြီး """
    
    def __init__(self):
        self.fe = FeatureEngineer()
        self.opt = MetaOptimizer()
        self.trees = TreeEngines()
        self.bayes = BayesianEngine()
        self.lstm = LSTMEngine()
        self.last_probs: Dict[str, float] = {}

    def analyze(self, docs: List[Dict[str, Any]]) -> Tuple[str, float, Dict[str, float]]:
        """ ဒေတာများကို သရုပ်ခွဲ၍ နောက်ဆုံးခန့်မှန်းချက်ကို ထုတ်ပေးသည် """
        if len(docs) < 50: 
            return random.choice(["BIG", "SMALL"]), random.uniform(50.1, 54.9), {}
        
        try:
            sizes = [d.get('size', 'BIG') for d in reversed(docs)]
            nums = [int(d.get('number', 0)) for d in reversed(docs)]
            pars = [d.get('parity', 'EVEN') for d in reversed(docs)]
            
            # Market Baseline ရှာခြင်း
            baseline_b = sizes.count('BIG') / len(sizes)
            if baseline_b == 0 or baseline_b == 1:
                baseline_b = 0.5 

            # 💡 [FIXED] 'prepare_data' အစား 'extract_features' ဟု အမည်မှန်ပြင်ထားသည်
            X, y, curr_X = self.fe.extract_features(sizes, nums, pars)
            
            probs = {}
            probs['markov'] = MarkovEngine.predict(sizes)
            probs['ngram'] = NGramEngine.predict(sizes)
            probs['monte'] = MonteCarloEngine.predict(sizes)
            probs['trend'] = TrendEngine.predict(sizes)
            probs['entropy'] = EntropyEngine.predict(sizes)
            probs['lstm'] = self.lstm.predict(sizes)
            
            if X is not None and len(X) > 10:
                probs['rf'], probs['gb'] = self.trees.predict(X, y, curr_X)
                probs['bayes'] = self.bayes.predict(X, y, curr_X)
            else:
                probs['rf'] = probs['gb'] = probs['bayes'] = baseline_b
                
            self.last_probs = {k: float(v) for k, v in probs.items()}
            
            w = self.opt.weights
            final_b = sum(probs[k] * w.get(k, 0.1) for k in probs)
            
            # Baseline ဖြင့် နှိုင်းယှဉ်ခြင်း (BIG ငြိခြင်းကို ကာကွယ်ရန်)
            if final_b > baseline_b:
                final_pred = "BIG"
            elif final_b < baseline_b:
                final_pred = "SMALL"
            else:
                final_pred = random.choice(["BIG", "SMALL"])
            
            # Confidence Calculation
            deviation = abs(final_b - baseline_b)
            raw_conf = 0.5 + (deviation * 2.5)
            conf = min(max(float(raw_conf) * 100, 51.0), 99.0)
            
            return final_pred, round(conf, 1), self.last_probs
            
        except Exception as e:
            logger.error(f"Master Engine Error: {e}")
            return random.choice(["BIG", "SMALL"]), 50.0, {}

# =========================================================================
# 💰 MODULE 6: TELEGRAM UI & PRESENTATION
# =========================================================================
class UIManager:
    """ Telegram သို့ လှပသော စာသားများ၊ စတစ်ကာများ ပို့ဆောင်ခြင်းကို စီမံသည် """
    def __init__(self, bot_client: Bot):
        self.bot = bot_client

    async def broadcast_prediction(self, issue: str, pred: str, step: int, conf: float, top_engine: str) -> None:
        msg = (
            f"<b>[ULTRA-AI 10-CORE PRO]</b>\n"
            f"⏰ Period: <code>{issue}</code>\n"
            f"🎯 Prediction: <b>{pred}</b> {step}x\n"
            f"📊 Confidence: {conf}%\n"
            f"🧠 Top Engine: <code>{top_engine.upper()}</code>"
        )
        try: 
            await self.bot.send_message(chat_id=Config.CHANNEL_ID, text=msg)
        except Exception as e: 
            logger.error(f"UI Predict Send Error: {e}")

    async def broadcast_result(self, issue: str, pred: str, step: int, is_win: bool, actual_size: str, actual_num: int) -> None:
        win_str = "WIN ✅" if is_win else "LOSE ❌"
        icon = "🟢" if is_win else "🔴"
        res_letter = "B" if actual_size == "BIG" else "S"
        
        msg = (
            f"<b>🏆 SIX-LOTTERY RESULTS</b>\n\n"
            f"⏰ Period: <code>{issue}</code>\n"
            f"🎯 Choice: {pred} {step}x\n"
            f"📊 Result: {icon} <b>{win_str}</b> | {res_letter} ({actual_num})"
        )
        try: 
            await self.bot.send_message(chat_id=Config.CHANNEL_ID, text=msg)
            
            if is_win and Config.WIN_STICKER:
                await self.bot.send_sticker(chat_id=Config.CHANNEL_ID, sticker=Config.WIN_STICKER)
            elif not is_win and Config.LOSE_STICKER:
                await self.bot.send_sticker(chat_id=Config.CHANNEL_ID, sticker=Config.LOSE_STICKER)
        except Exception as e: 
            logger.error(f"UI Result Send Error: {e}")

# =========================================================================
# 🚀 MODULE 7: THE MAIN CONTROLLER LOOP
# =========================================================================
class ApplicationController:
    """ API မှ Data ဆွဲခြင်း၊ Database သိမ်းခြင်း၊ AI တွက်ခြင်းတို့ကို အချိန်ကိုက် လုပ်ဆောင်သည် """
    def __init__(self):
        self.db = DatabaseManager(Config.MONGO_URI)
        self.ai = UltraMasterEngine()
        self.ui = UIManager(bot)
        self.last_issue: Optional[str] = None
        self.lose_streak: int = 0

    async def fetch_api_data(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """ ဆာဗာမှ ပွဲစဉ်ရလဒ်များကို လှမ်းတောင်းသည် (Retry စနစ်ပါဝင်သည်) """
        json_data = {
            'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7, 
            'random': '029ef9cb888540c4b19e0c4b5eb49cbf', 
            'signature': 'C526273C4CCB81BBD1A1227C3DC5D025', 
            'timestamp': int(time.time())
        }
        for attempt in range(3):
            try:
                async with session.post(Config.API_URL, headers=Config.get_headers(), json=json_data, timeout=5.0) as r:
                    if r.status == 200: 
                        res = await r.json()
                        if res.get('code') != 0:
                            logger.error(f"API Rejected (Code: {res.get('code')}): Update Token/Signature!")
                        return res
                    else:
                        logger.error(f"HTTP Status Error: {r.status}")
            except Exception as e:
                logger.warning(f"API Fetch Retry {attempt+1}/3 failed: {e}")
                await asyncio.sleep(0.5)
        return None

    async def run_forever(self) -> None:
        """ စက်ခေါင်းကြီးကို အဆုံးမရှိ (Infinite Loop) မောင်းနှင်သည် """
        await self.db.initialize()
        
        async with aiohttp.ClientSession() as session:
            logger.info("🔥 ULTRA-AI 10-CORE GAME LOOP STARTED SUCCESSFULLY 🔥")
            while True:
                try:
                    data = await self.fetch_api_data(session)
                    if not data or data.get('code') != 0:
                        await asyncio.sleep(1.5); continue
                        
                    records = data.get("data", {}).get("list", [])
                    if not records: continue
                    
                    latest = records[0]
                    issue = str(latest["issueNumber"])
                    number = int(latest["number"])
                    size = "BIG" if number >= 5 else "SMALL"
                    parity = "EVEN" if number % 2 == 0 else "ODD"
                    
                    # 1️⃣ စတင်ဖွင့်ချိန် (Initialization State)
                    if not self.last_issue:
                        logger.info(f"🔄 Initializing State at Issue: {issue}")
                        self.last_issue = issue
                        
                        recent_preds = await self.db.get_recent_predictions(15)
                        self.lose_streak = 0
                        for p in recent_preds:
                            if p.get("win_lose") == "LOSE": self.lose_streak += 1
                            else: break
                        if self.lose_streak >= len(Config.MULTIPLIERS): self.lose_streak = 0

                        next_issue = str(int(issue) + 1)
                        docs = await self.db.get_history(500)
                        
                        pred, conf, details = self.ai.analyze(docs)
                        top_model = max(self.ai.opt.weights, key=self.ai.opt.weights.get) if self.ai.opt.weights else "rf"
                        
                        await self.ui.broadcast_prediction(next_issue, pred, self.lose_streak + 1, conf, top_model)
                        await asyncio.sleep(1.0); continue

                    # 2️⃣ ပွဲစဉ်အသစ် ထွက်လာသောအခါ (New Issue State)
                    if int(issue) > int(self.last_issue):
                        logger.info(f"🟢 New Result Arrived: {issue} -> {size} ({number})")
                        
                        # History သိမ်းမည်
                        await self.db.save_history(issue, number, size, parity)
                        
                        # AI Optimizer ကို သင်ယူခိုင်းမည် (Self-Learning)
                        self.ai.opt.update(size, self.ai.last_probs)
                        
                        # ယခင် Prediction ကို ရှာ၍ ရလဒ်တိုက်စစ်မည်
                        pred_doc = await self.db.predictions.find_one({"issue_number": issue})
                        
                        if pred_doc and pred_doc.get('predicted_size'):
                            predicted_size = str(pred_doc['predicted_size'])
                            is_win = (predicted_size == size)
                            win_lose_db = "WIN" if is_win else "LOSE"
                            
                            # DB တွင် ရလဒ် Update လုပ်မည်
                            await self.db.update_result(issue, size, number, win_lose_db)
                            
                            # Telegram သို့ Result ပို့မည်
                            current_step = self.lose_streak + 1
                            await self.ui.broadcast_result(issue, predicted_size, current_step, is_win, size, number)
                            
                            # Streak ကို Update လုပ်မည်
                            if is_win: 
                                self.lose_streak = 0
                            else: 
                                self.lose_streak += 1
                                if self.lose_streak >= len(Config.MULTIPLIERS): 
                                    self.lose_streak = 0

                        self.last_issue = issue
                        
                        # 3️⃣ နောက်ပွဲစဉ်အတွက် ချက်ချင်း ခန့်မှန်းမည် (Prediction State)
                        next_issue = str(int(issue) + 1)
                        docs = await self.db.get_history(500)
                        
                        logger.info(f"⏳ Analyzing probabilities for {next_issue}...")
                        pred, conf, details = self.ai.analyze(docs)
                        
                        # DB သို့ Prediction အသစ် သိမ်းမည်
                        await self.db.save_prediction(next_issue, pred, conf, details)
                        
                        top_model = max(self.ai.opt.weights, key=self.ai.opt.weights.get)
                        current_step = self.lose_streak + 1
                        
                        # Telegram သို့ Prediction ပို့မည်
                        await self.ui.broadcast_prediction(next_issue, pred, current_step, conf, top_model)

                except Exception as e:
                    logger.error(f"Critical Loop Exception: {e}")
                
                # Server ဝန်မပိစေရန် 1.5s နားမည်
                await asyncio.sleep(1.5)

# =========================================================================
# 🚀 MODULE 8: ENTRY POINT
# =========================================================================
async def main() -> None:
    """ Python Program စတင်အလုပ်လုပ်သော နေရာ """
    logger.info("Initializing ULTRA-AI Core Components...")
    
    # Webhook အဟောင်းများရှိပါက ရှင်းလင်းသည်
    await bot.delete_webhook(drop_pending_updates=True)
    
    app_controller = ApplicationController()
    
    # Game Loop ကို Background တွင် အလုပ်လုပ်စေသည်
    asyncio.create_task(app_controller.run_forever())
    
    logger.info("Bot is now Polling Telegram Updates...")
    # Telegram Bot ကို စတင်အလုပ်လုပ်စေသည်
    await dp.start_polling(bot)

if __name__ == '__main__':
    try: 
        # Async Event Loop ဖြင့် Main Function ကို မောင်းနှင်သည်
        asyncio.run(main())
    except KeyboardInterrupt: 
        logger.info("System Shut Down by User (Ctrl+C).")

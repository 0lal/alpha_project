# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - HISTORICAL MARKET REPLAY ENGINE
=================================================================
Component: sim_lab/backtest/replay_engine.py
Core Responsibility: إعادة بث بيانات السوق التاريخية بدقة زمنية صارمة (Realism Pillar).
Design Pattern: Iterator / Event Emitter
Forensic Impact: يسمح بـ "إعادة تمثيل الجريمة" (Crime Re-enactment). إذا فشل المحرك في تاريخ معين، نعيد تشغيل هذا التاريخ بالضبط لتصحيح الخطأ.
=================================================================
"""

import pandas as pd
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Generator, Optional, List, Any

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.replay")

class ReplayMode(Enum):
    BACKTEST_FAST = "FAST"      # أقصى سرعة ممكنة (للتدريب والتحسين)
    REALTIME_SIM = "REALTIME"   # سرعة 1:1 (للمراقبة الحية واختبار الواجهة)
    VARIABLE_SPEED = "VARIABLE" # سرعة مخصصة (مثلاً 10x)

@dataclass
class MarketTick:
    timestamp: float    # Unix Timestamp
    symbol: str
    price: float
    volume: float
    side: str           # buy/sell
    is_maker: bool      # للتحليل المتقدم

class ReplayEngine:
    def __init__(self, data_path: Optional[str] = None):
        self.data_buffer: pd.DataFrame = pd.DataFrame()
        self.current_cursor = 0
        self.mode = ReplayMode.BACKTEST_FAST
        self.speed_factor = 1.0 # يستخدم فقط في VARIABLE_SPEED
        self.is_running = False
        
        # تحميل البيانات
        if data_path:
            self.load_data(data_path)

    def load_data(self, path: str):
        """تحميل ملف CSV أو Parquet"""
        try:
            # افتراض تنسيق قياسي: timestamp, symbol, price, volume, side
            logger.info(f"REPLAY: Loading data from {path}...")
            if path.endswith('.parquet'):
                self.data_buffer = pd.read_parquet(path)
            else:
                self.data_buffer = pd.read_csv(path)
            
            # التأكد من الترتيب الزمني (حيوي جداً!)
            self.data_buffer.sort_values(by='timestamp', inplace=True)
            self.data_buffer.reset_index(drop=True, inplace=True)
            
            logger.info(f"REPLAY: Loaded {len(self.data_buffer)} ticks. Time range: {self.data_buffer['timestamp'].min()} -> {self.data_buffer['timestamp'].max()}")
        except Exception as e:
            logger.error(f"REPLAY_ERR: Failed to load data: {e}")

    def load_dataframe(self, df: pd.DataFrame):
        """تحميل مباشر من الذاكرة (للاختبارات)"""
        self.data_buffer = df.sort_values(by='timestamp').reset_index(drop=True)

    def set_mode(self, mode: ReplayMode, speed_factor: float = 1.0):
        self.mode = mode
        self.speed_factor = speed_factor

    def stream(self) -> Generator[MarketTick, None, None]:
        """
        المولد الرئيسي للأحداث.
        يستخدم 'yield' لإنتاج البيانات تتابعياً.
        """
        self.is_running = True
        total_ticks = len(self.data_buffer)
        
        if total_ticks == 0:
            logger.warning("REPLAY: No data to stream.")
            return

        logger.info(f"REPLAY: Starting stream in {self.mode.name} mode...")
        
        start_wall_time = time.time()
        prev_tick_time = self.data_buffer.iloc[0]['timestamp']

        # استخدام itertuples لأداء أسرع بـ 100 مرة من iterrows
        for row in self.data_buffer.itertuples(index=False):
            if not self.is_running: break

            current_tick_time = row.timestamp
            
            # منطق التحكم في الزمن
            if self.mode != ReplayMode.BACKTEST_FAST:
                time_delta = current_tick_time - prev_tick_time
                
                if time_delta > 0:
                    sleep_time = time_delta
                    if self.mode == ReplayMode.VARIABLE_SPEED:
                        sleep_time = time_delta / self.speed_factor
                    
                    # ننام فقط إذا كانت الفترة تستحق (فوق 1 مللي ثانية)
                    if sleep_time > 0.001:
                        time.sleep(sleep_time)

            prev_tick_time = current_tick_time

            # تحويل الصف إلى كائن MarketTick
            # نفترض أسماء الأعمدة (timestamp, symbol, price, volume, side)
            # بما أننا نستخدم itertuples، الوصول يتم عبر النقطة row.column_name
            tick = MarketTick(
                timestamp=row.timestamp,
                symbol=row.symbol,
                price=row.price,
                volume=row.volume,
                side=getattr(row, 'side', 'buy'), # Default to buy if missing
                is_maker=getattr(row, 'is_maker', False)
            )

            yield tick

        duration = time.time() - start_wall_time
        logger.info(f"REPLAY: Stream finished. Processed {total_ticks} ticks in {duration:.2f}s ({total_ticks/duration:.0f} ticks/s)")

    def stop(self):
        self.is_running = False

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 1. إنشاء بيانات وهمية (Synthetic Data)
    print("--- Generating Synthetic Data ---")
    data = []
    base_time = time.time()
    price = 50000.0
    
    for i in range(100):
        # كل تيك يأتي بعد 0.1 ثانية من سابقه
        base_time += 0.1
        price += (i % 2 - 0.5) * 10 # تذبذب عشوائي
        data.append({
            'timestamp': base_time,
            'symbol': 'BTCUSDT',
            'price': price,
            'volume': 0.5,
            'side': 'buy' if i % 2 == 0 else 'sell'
        })
    
    df = pd.DataFrame(data)

    # 2. إعداد المحرك
    engine = ReplayEngine()
    engine.load_dataframe(df)

    # 3. اختبار الوضع السريع (Backtest)
    print("\n--- Test 1: Fast Backtest Mode ---")
    engine.set_mode(ReplayMode.BACKTEST_FAST)
    count = 0
    for tick in engine.stream():
        count += 1
    print(f"Processed {count} ticks instantly.")

    # 4. اختبار وضع المحاكاة الزمنية (Realtime Speed 10x)
    # البيانات تغطي 10 ثواني (100 * 0.1). بسرعة 10x يجب أن تنتهي في 1 ثانية.
    print("\n--- Test 2: Variable Speed (10x) ---")
    engine.set_mode(ReplayMode.VARIABLE_SPEED, speed_factor=10.0)
    
    start = time.time()
    for tick in engine.stream():
        # هنا سيقوم "الدماغ" باتخاذ القرارات
        pass
    end = time.time()
    
    print(f"Replay took {end - start:.2f} seconds (Expected ~1.0s)")
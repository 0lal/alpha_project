# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - EXPERIENCE REPLAY BUFFER (RL CORE)
# =================================================================
# Component Name: brain/memory/experience_replay.py
# Core Responsibility: إعادة بث المواقف السابقة للتعلم من الأخطاء (Adaptability Pillar).
# Design Pattern: Prioritized Experience Replay (PER)
# Forensic Impact: يحتفظ بـ "سجل الأخطاء" (Error Logs) ويعيد تدريب النظام عليها لضمان عدم تكرار الكوارث.
# =================================================================

import logging
import random
import numpy as np
from collections import deque
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class Experience:
    """وحدة الخبرة الواحدة."""
    state_vector: np.ndarray    # حالة السوق قبل القرار
    action_taken: int           # القرار (0: Hold, 1: Buy, 2: Sell)
    reward_received: float      # النتيجة (الربح/الخسارة)
    next_state_vector: np.ndarray # حالة السوق بعد القرار
    done: bool                  # هل انتهت الصفقة؟
    priority: float             # أهمية هذا الدرس (الخسائر لها أولوية أعلى)

class ExperienceReplay:
    """
    ذاكرة إعادة الخبرة (Experience Replay Buffer).
    تستخدم لكسر الارتباط الزمني (Temporal Correlation) في البيانات،
    مما يسمح للنظام بالتعلم من الماضي بشكل مستقر.
    """

    def __init__(self, capacity: int = 10000, alpha_priority: float = 0.6):
        """
        Args:
            capacity: السعة القصوى للذاكرة (عدد المواقف).
            alpha_priority: مدى التركيز على الأحداث الهامة (0 = عشوائي، 1 = أولوية كاملة).
        """
        self.logger = logging.getLogger("Alpha.Brain.Memory.Replay")
        self.capacity = capacity
        self.alpha = alpha_priority
        
        # المخزن الفعلي للبيانات
        self.buffer: deque = deque(maxlen=capacity)
        # مخزن الأولويات (للاحتمالات)
        self.priorities: deque = deque(maxlen=capacity)

    def remember(self, 
                 state: List[float], 
                 action: int, 
                 reward: float, 
                 next_state: List[float], 
                 done: bool):
        """
        تخزين تجربة جديدة.
        """
        # حساب الأولوية المبدئية
        # الأحداث ذات المكافأة السلبية جداً (خسارة) أو الإيجابية جداً (ربح ضخم) تأخذ أولوية قصوى
        # نضيف ثابتاً صغيراً (epsilon) لضمان أن كل حدث لديه فرصة للظهور
        priority = abs(reward) + 1e-5
        
        experience = Experience(
            state_vector=np.array(state, dtype=np.float32),
            action_taken=action,
            reward_received=reward,
            next_state_vector=np.array(next_state, dtype=np.float32),
            done=done,
            priority=priority
        )

        self.buffer.append(experience)
        self.priorities.append(priority)

    def sample_batch(self, batch_size: int = 64) -> Dict[str, np.ndarray]:
        """
        سحب دفعة عشوائية للتدريب (Training Batch).
        نستخدم الاحتمالات المرجحة بالأولوية (Prioritized Sampling).
        """
        if len(self.buffer) < batch_size:
            return None

        # 1. حساب احتمالات السحب
        probs = np.array(self.priorities) ** self.alpha
        probs /= probs.sum()

        # 2. اختيار العينات (Indices)
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        
        # 3. تجميع البيانات
        states, actions, rewards, next_states, dones = [], [], [], [], []
        
        for idx in indices:
            exp = self.buffer[idx]
            states.append(exp.state_vector)
            actions.append(exp.action_taken)
            rewards.append(exp.reward_received)
            next_states.append(exp.next_state_vector)
            dones.append(exp.done)

        return {
            "states": np.array(states),
            "actions": np.array(actions),
            "rewards": np.array(rewards, dtype=np.float32),
            "next_states": np.array(next_states),
            "dones": np.array(dones, dtype=bool),
            "indices": indices # نحتاج المؤشرات لتحديث الأولويات لاحقاً
        }

    def update_priorities(self, indices: np.ndarray, errors: np.ndarray):
        """
        تحديث أهمية الدروس بعد التدريب.
        إذا أخطأ النموذج في التنبؤ بدرس معين (Error عالي)، نزيد أولويته ليتعلمه مرة أخرى.
        """
        for idx, error in zip(indices, errors):
            if idx < len(self.priorities):
                self.priorities[idx] = abs(error) + 1e-5

    def get_painful_lessons(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        استخراج أسوأ الخسائر للتحليل الجنائي البشري.
        """
        # تحويل الذاكرة لقائمة للفرز
        all_experiences = list(self.buffer)
        # الفرز حسب "سلبية" المكافأة (الأقل ربحاً = الأكثر خسارة)
        painful = sorted(all_experiences, key=lambda x: x.reward_received)[:top_k]
        
        return [
            {
                "reward": exp.reward_received,
                "action": "BUY" if exp.action_taken == 1 else "SELL",
                "market_vector_snapshot": exp.state_vector.tolist()[:5] # عرض مقتضب
            }
            for exp in painful
        ]
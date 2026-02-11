# Twitter/Reddit Sentiment

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - SOCIAL SENTIMENT & HYPE ANALYZER
# =================================================================
# Component Name: brain/agents/sentiment/social_agent.py
# Core Responsibility: تحليل زخم مشاعر Twitter/Reddit وفهم نبرة السخرية (Intelligence Pillar).
# Design Pattern: Agent / Heuristic Analyzer
# Forensic Impact: يفرق بين "النمو العضوي" (Organic Growth) وبين "حملات الترويج الوهمية" (Astroturfing).
# =================================================================

import re
import logging
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

class SocialAgent:
    """
    وكيل التحليل الاجتماعي.
    مصمم لفهم لغة "الشارع الرقمي" (Crypto Slang) وكشف البوتات.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Sentiment.Social")

        # 1. قاموس عامية الكريبتو (Crypto Slang Lexicon)
        # الكلمات التي لا تفهمها نماذج NLP التقليدية
        self.slang_lexicon = {
            # إيجابي جداً
            "wagmi": 0.9,       # We Are Gonna Make It
            "lfg": 0.8,         # Let's F***ing Go
            "moon": 0.8,
            "gem": 0.7,
            "diamond hands": 0.9,
            "bullish": 0.8,
            "aped in": 0.6,     # الشراء بتهور (إيجابي للزخم)
            
            # سلبي جداً
            "rekt": -0.9,       # Wrecked (خسارة فادحة)
            "ngmi": -0.9,       # Not Gonna Make It
            "rug": -1.0,        # Rug Pull (احتيال)
            "scam": -1.0,
            "ponzi": -1.0,
            "paper hands": -0.6,
            "bearish": -0.7,
            "dump": -0.8
        }

        # 2. مؤشرات السخرية (Sarcasm Markers)
        # كلمات تشير غالباً للسخرية عند دمجها مع سياق معين
        self.sarcasm_triggers = [
            "sure buddy",
            "good luck with that",
            "have fun staying poor", # قد تكون سخرية أو جدية حسب السياق
            "totally not a scam",    # سخرية واضحة
            "another killer app"     # غالباً سخرية
        ]

    def analyze_social_batch(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تحليل حزمة من المنشورات الاجتماعية (Tweets/Posts).
        
        Args:
            posts: قائمة قواميس {text, user_followers, is_verified, source}
        """
        if not posts:
            return {"status": "NO_DATA"}

        total_sentiment = 0.0
        total_weight = 0.0
        organic_post_count = 0
        bot_count = 0
        
        hype_keywords_hits = 0

        for post in posts:
            text = post.get('text', '').lower()
            
            # 1. كشف البوتات (Forensic Bot Detection)
            # إذا كان المستخدم مشبوهاً، نتجاهل مشاعره
            if self._is_likely_bot(post):
                bot_count += 1
                continue

            organic_post_count += 1

            # 2. كشف السخرية (Sarcasm Detection)
            is_sarcastic = self._detect_sarcasm(text)
            
            # 3. حساب المشاعر (Slang-Aware Scoring)
            score = self._calculate_slang_score(text)
            
            # إذا كانت سخرية، نقلب النتيجة (Positive Sarcasm -> Negative)
            if is_sarcastic:
                score = -score

            # 4. ترجيح النتيجة بناءً على تأثير المستخدم (User Influence)
            followers = post.get('user_followers', 0)
            weight = np.log1p(followers) + 1.0 # Logarithmic scaling
            
            total_sentiment += score * weight
            total_weight += weight
            
            if score > 0.5 or score < -0.5:
                hype_keywords_hits += 1

        # تجميع النتائج النهائية
        final_sentiment = (total_sentiment / total_weight) if total_weight > 0 else 0.0
        
        # مؤشر الزخم (Hype Score): نسبة المنشورات المؤثرة إلى الكل
        hype_score = (hype_keywords_hits / max(1, len(posts))) * 10.0

        return {
            "agent": "SocialAgent",
            "timestamp": datetime.utcnow().isoformat(),
            "volume_metrics": {
                "total_posts": len(posts),
                "organic_posts": organic_post_count,
                "bot_posts": bot_count,
                "bot_ratio": round(bot_count / max(1, len(posts)), 2)
            },
            "sentiment_metrics": {
                "score": round(final_sentiment, 4), # من -1 إلى 1
                "label": self._get_label(final_sentiment),
                "hype_index": round(hype_score, 2) # من 0 إلى 10
            }
        }

    def _calculate_slang_score(self, text: str) -> float:
        """حساب المشاعر باستخدام قاموس الكريبتو."""
        score = 0.0
        hits = 0
        
        # البحث عن كلمات العامية
        for word, val in self.slang_lexicon.items():
            if word in text:
                score += val
                hits += 1
        
        # إذا لم نجد عامية، نعيد 0 (محايد) أو نستخدم محلل NLP قياسي (TextBlob)
        # هنا للتبسيط نعتمد على القاموس فقط لضمان السرعة
        if hits == 0:
            return 0.0
            
        return score / hits

    def _detect_sarcasm(self, text: str) -> bool:
        """
        محاولة كشف السخرية (Heuristic).
        """
        # 1. البحث عن عبارات "تهكمية" معروفة
        for trigger in self.sarcasm_triggers:
            if trigger in text:
                return True
        
        # 2. الكتابة المختلطة (Meme Case)
        # e.g., "ToTaLlY SaFe"
        if sum(1 for c in text if c.isupper()) > 0.3 * len(text) and not text.isupper():
            # إذا كان النص مختلط الحروف بشكل عشوائي
            return True # (هذا تبسيط، يحتاج منطق أدق)

        # 3. التناقض: كلمات إيجابية جداً مع سياق سلبي (صعب بدون Deep Learning)
        # لكن يمكننا كشف تكرار الرموز التعبيرية المبالغ فيه مع كلمات سلبية
        if "scam" in text and "🚀" in text:
            return True # "Scam 🚀" تعني غالباً أنه يسخر من مشروع يطير رغم أنه احتيال
            
        return False

    def _is_likely_bot(self, post: Dict[str, Any]) -> bool:
        """
        الفلتر الجنائي للبوتات.
        """
        # 1. حساب جديد جداً أو بدون متابعين
        followers = post.get('user_followers', 0)
        account_age_days = post.get('account_age_days', 365)
        
        if followers < 5 and account_age_days < 30:
            return True
            
        # 2. تكرار النص (Spam) - يتم التعامل معه خارجياً عادةً
        
        # 3. اسم المستخدم النمطي (e.g., User12345678)
        username = post.get('username', '')
        if re.search(r'\d{5,}$', username): # ينتهي بـ 5 أرقام أو أكثر
            return True

        return False

    def _get_label(self, score: float) -> str:
        if score >= 0.5: return "EUPHORIA" # نشوة
        if score >= 0.2: return "OPTIMISTIC"
        if score <= -0.5: return "PANIC"   # ذعر
        if score <= -0.2: return "PESSIMISTIC"
        return "NEUTRAL"
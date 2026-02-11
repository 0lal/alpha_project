# NLP Event Classification

# -*- coding: utf-8 -*-
# ALPHA SOVEREIGN - FINANCIAL NEWS NLP PROCESSOR
# =================================================================
# Component Name: brain/agents/sentiment/news_processor.py
# Core Responsibility: تحليل الأخبار وتصنيفها وقياس تأثيرها الماكرو (Intelligence Pillar).
# Design Pattern: NLP Pipe / Rule-Based Classifier
# Forensic Impact: يمنع "التداول على الضجيج" (Noise Trading). يفرق بين "الاختراق الأمني" (كارثة) وبين "الصيانة" (روتيني).
# =================================================================

import re
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

class NewsProcessor:
    """
    معالج اللغة الطبيعية المخصص للأسواق المالية (Financial NLP).
    لا يعتمد على نماذج ضخمة بطيئة، بل على قاموس دلالي سريع جداً (Lexicon-based)
    تم ضبطه يدوياً ليتناسب مع مصطلحات الكريبتو والاقتصاد الكلي.
    """

    def __init__(self):
        self.logger = logging.getLogger("Alpha.Brain.Sentiment.News")
        
        # 1. القاموس المالي (The Financial Lexicon)
        # تصنيف الكلمات: الوزن (-1.0 إلى 1.0)، الأهمية (1-5)
        self.lexicon = {
            # إيجابي (Bullish / Dovish)
            "adoption":     {"score": 0.8, "weight": 3},
            "partnership":  {"score": 0.6, "weight": 2},
            "launch":       {"score": 0.5, "weight": 2},
            "approval":     {"score": 0.9, "weight": 5}, # ETF Approval
            "bullish":      {"score": 0.7, "weight": 1},
            "upgrade":      {"score": 0.4, "weight": 2},
            "support":      {"score": 0.3, "weight": 1},
            "rate cut":     {"score": 0.9, "weight": 5}, # Fed Policy
            "soft landing": {"score": 0.6, "weight": 4},
            
            # سلبي (Bearish / Hawkish)
            "hack":         {"score": -1.0, "weight": 5},
            "stolen":       {"score": -0.9, "weight": 5},
            "ban":          {"score": -0.8, "weight": 4},
            "lawsuit":      {"score": -0.7, "weight": 4},
            "sec":          {"score": -0.5, "weight": 3}, # غالباً أخبارهم سلبية
            "inflation":    {"score": -0.6, "weight": 4},
            "rate hike":    {"score": -0.9, "weight": 5},
            "recession":    {"score": -0.8, "weight": 5},
            "crackdown":    {"score": -0.7, "weight": 3},
            "delist":       {"score": -0.9, "weight": 4},
        }

        # 2. الكلمات المفتاحية للتصنيف (Event Classification)
        self.categories = {
            "SECURITY": ["hack", "exploit", "attack", "vulnerability", "stolen", "compromised"],
            "REGULATORY": ["sec", "cftc", "ban", "law", "regulation", "compliance", "judge", "court"],
            "MACRO": ["fed", "powell", "inflation", "cpi", "gdp", "interest rate", "economy"],
            "MARKET": ["listing", "delisting", "volume", "liquidity", "ath", "support level"]
        }

    def process_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل مقال إخباري واستخراج البيانات الوصفية.
        
        Args:
            article: {title, content, source, published_at}
        """
        try:
            # دمج العنوان والمحتوى (العنوان أهم بـ 2x)
            text = f"{article.get('title', '')} . {article.get('title', '')} . {article.get('content', '')}"
            text_clean = self._clean_text(text)

            # 1. حساب المشاعر (Sentiment Scoring)
            sentiment_score, confidence = self._calculate_sentiment(text_clean)

            # 2. تصنيف الحدث (Event Classification)
            event_type = self._classify_event(text_clean)

            # 3. حساب التأثير المتوقع (Impact Factor)
            # الأخبار الأمنية والتنظيمية لها تأثير فوري وعنيف
            impact_factor = 1.0
            if event_type in ["SECURITY", "REGULATORY"] and abs(sentiment_score) > 0.5:
                impact_factor = 2.0 # مضاعفة التأثير
            
            result = {
                "processed_at": datetime.utcnow().isoformat(),
                "original_id": article.get("id"),
                "sentiment_score": round(sentiment_score, 4), # من -1 إلى 1
                "sentiment_label": self._get_label(sentiment_score),
                "confidence": round(confidence, 2),
                "event_type": event_type,
                "impact_factor": impact_factor,
                "keywords_detected": self._extract_keywords(text_clean)
            }
            
            # تسجيل جنائي للأخبار عالية التأثير
            if impact_factor >= 1.5:
                self.logger.warning(f"HIGH_IMPACT_NEWS: [{event_type}] Score: {sentiment_score:.2f} | Title: {article.get('title')}")

            return result

        except Exception as e:
            self.logger.error(f"NLP_ERROR: فشل معالجة الخبر: {e}")
            return {"error": str(e)}

    def _clean_text(self, text: str) -> str:
        """تنظيف النص وتوحيده."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text) # إزالة الرموز
        return text

    def _calculate_sentiment(self, text: str) -> Tuple[float, float]:
        """
        حساب المجموع المرجح للمشاعر.
        Returns: (Score, Confidence)
        """
        total_score = 0.0
        total_weight = 0.0
        hits = 0

        # البحث عن الكلمات في القاموس
        for word, metrics in self.lexicon.items():
            # استخدام Regex للتأكد من تطابق الكلمة كاملة (وليس جزء منها)
            # مثال: "hack" لا يجب أن تطابق "shack"
            if re.search(rf"\b{word}\b", text):
                total_score += metrics["score"] * metrics["weight"]
                total_weight += metrics["weight"]
                hits += 1

        if total_weight == 0:
            return 0.0, 0.0

        final_score = total_score / total_weight
        
        # الثقة تزيد كلما وجدنا كلمات مفتاحية أكثر
        confidence = min(hits / 5.0, 1.0) 
        
        return final_score, confidence

    def _classify_event(self, text: str) -> str:
        """تحديد نوع الحدث بناءً على الكلمات المفتاحية."""
        counts = {cat: 0 for cat in self.categories}
        
        for cat, keywords in self.categories.items():
            for kw in keywords:
                if kw in text:
                    counts[cat] += 1
        
        # إرجاع الفئة الأكثر تكراراً
        best_cat = max(counts, key=counts.get)
        
        # إذا لم نجد أي كلمة مفتاحية
        if counts[best_cat] == 0:
            return "GENERAL"
            
        return best_cat

    def _extract_keywords(self, text: str) -> List[str]:
        """استخراج الكلمات المؤثرة التي وجدت في النص."""
        found = []
        for word in self.lexicon:
            if word in text:
                found.append(word)
        return found

    def _get_label(self, score: float) -> str:
        if score > 0.3: return "BULLISH"
        if score < -0.3: return "BEARISH"
        return "NEUTRAL"
# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - POPULATION & GENERATION MANAGER
=================================================================
Component: sim_lab/evolution/population_mgr.py
Core Responsibility: إدارة دورة حياة الاستراتيجيات واختيار المرشحين للنشر (Adaptability Pillar).
Design Pattern: Manager / Repository
Forensic Impact: يحتفظ بملف "السيرة الذاتية" لكل استراتيجية (Lineage Tracking). إذا فشلت استراتيجية في الإنتاج، يمكننا تتبع سلالتها لمعرفة الخلل الجيني.
=================================================================
"""

import os
import json
import logging
import pickle
import time
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from sim_lab.evolution.genetic_optimizer import GeneticOptimizer, Individual, GeneParam

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.evolution.mgr")

class PopulationManager:
    def __init__(self, 
                 storage_dir: str = "data/evolution", 
                 optimizer: GeneticOptimizer = None):
        
        self.storage_dir = storage_dir
        self.optimizer = optimizer if optimizer else GeneticOptimizer()
        self.current_generation_id = 0
        self.hall_of_fame: List[Individual] = [] # أفضل الاستراتيجيات على الإطلاق
        
        # التأكد من وجود المجلدات
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
            
        # محاولة استعادة الحالة السابقة
        self.load_state()

    def run_evolution_cycle(self, 
                          genes_config: List[GeneParam], 
                          fitness_func, 
                          generations: int = 10):
        """
        تشغيل دورة تطوير كاملة وتحديث السجلات.
        """
        logger.info(f"POP_MGR: Starting evolution cycle from Gen {self.current_generation_id}...")
        
        # إذا لم يكن هناك مجتمع حالي، ابدأ من الصفر
        if not self.optimizer.population:
            logger.info("POP_MGR: Initializing new Genesis population.")
            self.optimizer.population = self.optimizer._create_initial_population(genes_config)

        # تشغيل التطور
        best_of_cycle = self.optimizer.evolve(genes_config, fitness_func, generations)
        
        # تحديث عداد الأجيال
        self.current_generation_id += generations
        
        # تحديث قاعة المشاهير
        self._update_hall_of_fame(self.optimizer.population)
        
        # الحفظ الآمن
        self.save_state()
        
        return best_of_cycle

    def promote_to_core(self, min_fitness: float, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        اختيار الاستراتيجيات الجاهزة للإنتاج.
        لا نختار فقط الأفضل في اللياقة، بل نطبق معايير صارمة.
        """
        candidates = []
        
        # دمج الجيل الحالي مع قاعة المشاهير للاختيار
        pool = self.optimizer.population + self.hall_of_fame
        
        # إزالة التكرار (Deduplication based on DNA hash)
        unique_pool = {}
        for ind in pool:
            dna_hash = str(sorted(ind.dna.items()))
            if dna_hash not in unique_pool:
                unique_pool[dna_hash] = ind
            else:
                # الاحتفاظ بالنسخة ذات اللياقة الأعلى (إذا وجدت)
                if ind.fitness > unique_pool[dna_hash].fitness:
                    unique_pool[dna_hash] = ind
        
        sorted_candidates = sorted(unique_pool.values(), key=lambda x: x.fitness, reverse=True)

        for ind in sorted_candidates:
            if len(candidates) >= top_n:
                break
                
            if ind.fitness >= min_fitness:
                # تحضير ملف النشر
                deploy_package = {
                    "strategy_id": ind.id,
                    "generation": ind.generation,
                    "fitness_score": ind.fitness,
                    "parameters": ind.dna,
                    "deployed_at": time.time(),
                    "status": "CANDIDATE"
                }
                candidates.append(deploy_package)
                logger.info(f"POP_MGR: Promoted {ind.id} to CORE CANDIDATES (Fitness: {ind.fitness:.4f})")
            else:
                # بما أن القائمة مرتبة، إذا وصلنا لأقل من الحد الأدنى نتوقف
                break
                
        return candidates

    def _update_hall_of_fame(self, population: List[Individual]):
        """تحديث قائمة الأفضل على الإطلاق"""
        self.hall_of_fame.extend(population)
        self.hall_of_fame.sort(key=lambda x: x.fitness, reverse=True)
        
        # الاحتفاظ فقط بأفضل 10 تاريخياً لمنع تضخم الذاكرة
        self.hall_of_fame = self.hall_of_fame[:10]
        
        if self.hall_of_fame:
            top = self.hall_of_fame[0]
            logger.info(f"POP_MGR: Hall of Fame Leader: {top.id} (Fitness: {top.fitness:.4f})")

    def save_state(self):
        """حفظ حالة التطور لاستكمالها لاحقاً"""
        state_path = os.path.join(self.storage_dir, "evolution_state.pkl")
        try:
            state = {
                "gen_id": self.current_generation_id,
                "population": self.optimizer.population,
                "hall_of_fame": self.hall_of_fame,
                "history": self.optimizer.history
            }
            with open(state_path, "wb") as f:
                pickle.dump(state, f)
            logger.debug("POP_MGR: State saved successfully.")
        except Exception as e:
            logger.error(f"POP_MGR_ERR: Failed to save state: {e}")

    def load_state(self):
        """استعادة الحالة"""
        state_path = os.path.join(self.storage_dir, "evolution_state.pkl")
        if os.path.exists(state_path):
            try:
                with open(state_path, "rb") as f:
                    state = pickle.load(f)
                
                self.current_generation_id = state.get("gen_id", 0)
                self.optimizer.population = state.get("population", [])
                self.hall_of_fame = state.get("hall_of_fame", [])
                self.optimizer.history = state.get("history", [])
                
                logger.info(f"POP_MGR: State loaded. Resuming from Gen {self.current_generation_id}.")
            except Exception as e:
                logger.warning(f"POP_MGR: Failed to load state (starting fresh): {e}")

    def export_lineage(self, strategy_id: str) -> str:
        """تتبع السلالة (لأغراض التحليل الجنائي)"""
        # في النسخة الكاملة، يجب تخزين الآباء (Parent IDs) في كل فرد
        # هنا سنبحث في المجتمع الحالي
        for ind in self.optimizer.population + self.hall_of_fame:
            if ind.id == strategy_id:
                return json.dumps(asdict(ind), indent=4)
        return "Strategy Not Found"

# =================================================================
# اختبار المحاكاة
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 1. الإعداد
    mgr = PopulationManager(storage_dir="temp_evo_test")
    
    genes = [
        GeneParam("rsi_period", 10, 30, is_integer=True),
        GeneParam("stop_loss", 0.01, 0.05, step=0.01)
    ]
    
    # دالة لياقة وهمية
    import random
    def mock_fitness(dna):
        # الهدف: rsi=14, sl=0.02
        score = 100 - abs(dna["rsi_period"] - 14) - (abs(dna["stop_loss"] - 0.02) * 1000)
        return max(0, score + random.uniform(-5, 5))

    # 2. تشغيل دورة التطور
    print("--- Running Evolution Cycle ---")
    best = mgr.run_evolution_cycle(genes, mock_fitness, generations=5)
    
    # 3. محاولة الترقية
    print("\n--- Promoting Candidates ---")
    candidates = mgr.promote_to_core(min_fitness=80.0)
    for c in candidates:
        print(f"Candidate: {c['strategy_id']} | Fitness: {c['fitness_score']:.2f} | Params: {c['parameters']}")
        
    # 4. حفظ واستعادة
    print("\n--- Testing Persistence ---")
    mgr.save_state()
    mgr2 = PopulationManager(storage_dir="temp_evo_test") # إعادة التحميل
    print(f"Loaded Gen ID: {mgr2.current_generation_id} (Should be 5)")
    
    # تنظيف
    import shutil
    shutil.rmtree("temp_evo_test")
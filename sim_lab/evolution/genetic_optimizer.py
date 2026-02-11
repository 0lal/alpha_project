# -*- coding: utf-8 -*-
"""
ALPHA SOVEREIGN - GENETIC ALGORITHM OPTIMIZER
=================================================================
Component: sim_lab/evolution/genetic_optimizer.py
Core Responsibility: تحسين معاملات الاستراتيجيات تلقائياً عبر المحاكاة التطورية (Adaptability Pillar).
Design Pattern: Genetic Algorithm (GA) / Evolutionary Strategy
Forensic Impact: يسجل "سلالة" الاستراتيجية (Lineage). نعرف بالضبط كيف تطورت الاستراتيجية ومن هم "آباؤها".
=================================================================
"""

import random
import numpy as np
import logging
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any

# إعداد التسجيل
logger = logging.getLogger("alpha.sim.evolution")

@dataclass
class GeneParam:
    """تعريف الجين (المتغير الذي نريد تحسينه)"""
    name: str
    min_val: float
    max_val: float
    is_integer: bool = False
    step: float = 1.0

@dataclass
class Individual:
    """فرد في المجتمع (استراتيجية واحدة)"""
    dna: Dict[str, Any]       # المعاملات (Genotype)
    fitness: float = 0.0      # نتيجة الأداء (Phenotype)
    generation: int = 0
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"G{self.generation}_{random.randint(1000, 9999)}"

class GeneticOptimizer:
    def __init__(self, 
                 population_size: int = 50, 
                 mutation_rate: float = 0.1, 
                 crossover_rate: float = 0.8,
                 elitism_count: int = 2):
        
        self.pop_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count # عدد الأفضل الذين ينتقلون للجيل التالي دون تغيير
        self.population: List[Individual] = []
        self.best_solution: Individual = None
        self.history = []

    def evolve(self, 
               genes_config: List[GeneParam], 
               fitness_function: Callable[[Dict[str, Any]], float], 
               generations: int = 20) -> Individual:
        """
        تشغيل المحرك التطوري.
        genes_config: تعريف المتغيرات وحدودها.
        fitness_function: دالة خارجية تقبل الـ DNA وتعيد رقم (Sharpe Ratio مثلاً).
        """
        logger.info(f"EVOLUTION: Starting evolution for {generations} generations with pop_size={self.pop_size}...")

        # 1. التكوين المبدئي (Genesis)
        self.population = self._create_initial_population(genes_config)

        for gen in range(generations):
            # 2. تقييم اللياقة (Fitness Evaluation)
            self._evaluate_population(fitness_function)
            
            # ترتيب المجتمع حسب اللياقة (من الأفضل للأسوأ)
            self.population.sort(key=lambda x: x.fitness, reverse=True)
            
            # حفظ الأفضل
            current_best = self.population[0]
            if self.best_solution is None or current_best.fitness > self.best_solution.fitness:
                self.best_solution = copy.deepcopy(current_best)
                logger.info(f"EVOLUTION: New Alpha discovered in Gen {gen}: Fitness={current_best.fitness:.4f} | DNA={current_best.dna}")

            self.history.append(current_best.fitness)

            # 3. النخبة (Elitism)
            new_population = [copy.deepcopy(ind) for ind in self.population[:self.elitism_count]]
            
            # 4. التكاثر (Breeding)
            while len(new_population) < self.pop_size:
                parent1 = self._tournament_selection()
                parent2 = self._tournament_selection()
                
                # التزاوج (Crossover)
                child1_dna, child2_dna = self._crossover(parent1, parent2)
                
                # الطفرات (Mutation)
                child1_dna = self._mutate(child1_dna, genes_config)
                child2_dna = self._mutate(child2_dna, genes_config)
                
                new_population.append(Individual(dna=child1_dna, generation=gen+1))
                if len(new_population) < self.pop_size:
                    new_population.append(Individual(dna=child2_dna, generation=gen+1))

            self.population = new_population
            logger.debug(f"EVOLUTION: Generation {gen} complete. Best Fitness: {current_best.fitness:.4f}")

        logger.info("EVOLUTION: Optimization complete.")
        return self.best_solution

    def _create_initial_population(self, genes_config: List[GeneParam]) -> List[Individual]:
        population = []
        for _ in range(self.pop_size):
            dna = {}
            for gene in genes_config:
                val = random.uniform(gene.min_val, gene.max_val)
                if gene.is_integer:
                    val = int(round(val))
                else:
                    # تقريب لأقرب خطوة (Step)
                    val = round(val / gene.step) * gene.step
                dna[gene.name] = val
            population.append(Individual(dna=dna, generation=0))
        return population

    def _evaluate_population(self, fitness_function: Callable):
        """تقييم كل فرد (تشغيل Backtest له)"""
        for ind in self.population:
            # هنا يتم استدعاء المحرك الحقيقي في الإنتاج
            # في المحاكاة، قد نستخدم Multiprocessing لتسريع العملية
            score = fitness_function(ind.dna)
            ind.fitness = score

    def _tournament_selection(self, k: int = 3) -> Individual:
        """اختيار الوالدين عبر بطولة مصغرة (يحافظ على التنوع الجيني)"""
        tournament = random.sample(self.population, k)
        return max(tournament, key=lambda x: x.fitness)

    def _crossover(self, p1: Individual, p2: Individual) -> tuple:
        """تزاوج موحد (Uniform Crossover)"""
        if random.random() > self.crossover_rate:
            return p1.dna.copy(), p2.dna.copy()

        c1_dna = {}
        c2_dna = {}
        
        for key in p1.dna.keys():
            # 50% فرصة لأخذ الجين من الأب أو الأم
            if random.random() < 0.5:
                c1_dna[key] = p1.dna[key]
                c2_dna[key] = p2.dna[key]
            else:
                c1_dna[key] = p2.dna[key]
                c2_dna[key] = p1.dna[key]
        
        return c1_dna, c2_dna

    def _mutate(self, dna: Dict[str, Any], genes_config: List[GeneParam]) -> Dict[str, Any]:
        """إحداث طفرات عشوائية"""
        mutated_dna = dna.copy()
        for gene in genes_config:
            if random.random() < self.mutation_rate:
                # طفرة غاوسية (Gaussian Mutation): تغيير طفيف بدلاً من عشوائي كامل
                current_val = mutated_dna[gene.name]
                change = np.random.normal(0, (gene.max_val - gene.min_val) * 0.1) # 10% standard deviation
                
                new_val = current_val + change
                
                # الالتزام بالحدود
                new_val = max(gene.min_val, min(gene.max_val, new_val))
                
                if gene.is_integer:
                    new_val = int(round(new_val))
                else:
                    new_val = round(new_val / gene.step) * gene.step
                
                mutated_dna[gene.name] = new_val
        return mutated_dna

# =================================================================
# اختبار المحاكاة (Demo)
# =================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 1. تعريف الجينات (Parameters Space)
    # نريد تحسين استراتيجية تعتمد على متوسطين متحركين ووقف خسارة
    genes = [
        GeneParam("fast_ma", 5, 50, is_integer=True),   # 5 to 50
        GeneParam("slow_ma", 50, 200, is_integer=True), # 50 to 200
        GeneParam("stop_loss_pct", 0.01, 0.10, step=0.005) # 1% to 10%
    ]

    # 2. دالة اللياقة (Mock Fitness Function)
    # في الواقع، هذه الدالة ستقوم بتشغيل BacktestEngine
    # هنا سنحاكي دالة رياضية نعرف حلها الأمثل
    def mock_fitness(dna):
        # لنفترض أن الحل الأمثل هو: fast=20, slow=100, sl=0.05
        # كلما اقتربنا، زادت النتيجة
        score = 100
        score -= abs(dna["fast_ma"] - 20)
        score -= abs(dna["slow_ma"] - 100) * 0.5
        score -= abs(dna["stop_loss_pct"] - 0.05) * 1000
        
        # إضافة ضجيج عشوائي لمحاكاة تقلب السوق
        noise = random.uniform(-1, 1)
        return max(0, score + noise)

    # 3. تشغيل المُحسِّن
    optimizer = GeneticOptimizer(population_size=20, mutation_rate=0.2)
    
    print("--- Starting Genetic Optimization ---")
    best_ind = optimizer.evolve(genes, mock_fitness, generations=15)
    
    print("\n--- Optimization Results ---")
    print(f"Best Fitness: {best_ind.fitness:.4f}")
    print(f"Optimal DNA: {best_ind.dna}")
    print("Target was roughly: {fast_ma: 20, slow_ma: 100, stop_loss_pct: 0.05}")
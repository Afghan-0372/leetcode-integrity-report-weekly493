import re
import time
import tracemalloc
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from functools import partial
from report_modules import gen_report, save_report
from utils import parse_dump, get_logic_signature, normalize, get_ast_fingerprint, detect_ai_noise
from compare_worker import compare_worker_serial, mp_init_worker, compare_worker_shared, compare_worker_original

# MY EMAIL !!!
# CONTACT ME:
MY_EMAIL = "pooacc2@gmail.com"

# If data wil be more larger or i find more efficient ways i just tune this params
SERIAL_THRESHOLD     = 1200   # use serial below this count (usually fastest)
SHARED_MP_THRESHOLD  = 3500   # use shared-memory mp in this range

# CLAASS 2 (before)
class AntiCheatHacker:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = parse_dump(self.file_path)
        self.reports = []
        self.clusters = defaultdict(list)
        
        # Pre-compile regex
        self.ai_patterns_full = {
            re.compile(r"// Step \d+:", re.I): "Steps",
            re.compile(r"// Time Complexity:", re.I): "Complexity",
            re.compile(r"Explanation:", re.I): "Text",
            re.compile(r"auto solve = \[&\]", re.I): "Lambda Recursion",
            re.compile(r"idCounter\+\+", re.I): "ID Counter Pattern"
        }
        self.ai_patterns_short = {
            re.compile(r"// Step \d+:", re.I): "Steps",
            re.compile(r"// Time Complexity:", re.I): "Complexity"
        }

    def analyze(self):
        by_question = defaultdict(list)
        for sol in self.data:
            by_question[sol['q']].append(sol)

        for q_name, solutions in by_question.items():
            if q_name not in ["Q3", "Q4"]: continue
            N = len(solutions)
            print(f"Analyzing {q_name} (Total: {N})")

            # 1. Pre-processing
            t = time.time()
            for s in solutions:
                code = s['code']
                s['logic_masked'] = normalize(code)
                s['signature']    = get_logic_signature(code)
                s['ast_fp']       = get_ast_fingerprint(code)
                s['has_ai_noise'] = detect_ai_noise(code)
                lm = s['logic_masked']
                s['ng_set'] = set(lm[k:k+4] for k in range(len(lm)-3)) if len(lm) >= 10 else set()
            print(f"- Pre-processing: {time.time() - t:.4f} s")

            # 2. Execution Strategy
            t = time.time()
            if N <= SERIAL_THRESHOLD:
                results = [compare_worker_serial(i, solutions) for i in range(N)]
            elif N <= SHARED_MP_THRESHOLD:
                with Pool(processes=max(2, cpu_count()-2), initializer=mp_init_worker, initargs=(solutions,)) as pool:
                    results = pool.map(compare_worker_shared, range(N))
            else:
                with Pool(processes=max(2, cpu_count()-2)) as pool:
                    func = partial(compare_worker_original, solutions=solutions, q_name=q_name)
                    results = pool.map(func, enumerate(solutions))
            print(f"- Comparison time: {time.time() - t:.4f} s")

            # 3. SPEED OPTIMIZED Post-processing
            t = time.time()
            processed_indices = set()
            # Map rank to index for O(1) lookup instead of nested O(N) scan
            rank_to_idx = {s['rank']: idx for idx, s in enumerate(solutions)}

            for i, cluster, sims, _ in results:
                if i in processed_indices:
                    continue

                code = solutions[i]['code']
                if len(cluster) <= 1:
                    found_ai = [desc for pat, desc in self.ai_patterns_full.items() if pat.search(code)]
                    if found_ai:
                        gen_report(self, solutions[i], [solutions[i]['rank']], found_ai)
                    processed_indices.add(i)
                    continue

                # Cluster logic
                avg_sim = int((sum(sims) / len(sims)) * 100) if sims else 100
                self.clusters[q_name].append({"ranks": sorted(cluster), "avg_sim": avg_sim})
                
                found_ai = [desc for pat, desc in self.ai_patterns_short.items() if pat.search(code)]
                gen_report(self, solutions[i], cluster, found_ai)

                # OPTIMIZATION O(1) membership marking
                for member_rank in cluster:
                    if member_rank in rank_to_idx:
                        processed_indices.add(rank_to_idx[member_rank])

            print(f"- Post-processing: {time.time() - t:.4f} s")

    def save_final_report(self, pdf_filename="LEETCODE_AUDIT_REPORT.pdf"):
        save_report(self, pdf_filename)


if __name__ == "__main__":
    start = time.time()
    tracemalloc.start()

    hacker = AntiCheatHacker("contest_dump.txt")
    hacker.analyze()

    cur, peak = tracemalloc.get_traced_memory()
    print(f"Full time:   {time.time() - start:.4f} seconds")
    print(f"Memory peak: {peak / 1024 / 1024:.2f} MB")  # 21MB to 500 members, linear growth you can calc if 50_000 = 2_100MB of RAM, i think its low cost, and sure i can make lower memory computing.

    #hacker.save_final_report()   # RREEEEEPOPOOROORORORTRTTTY ALL THIS SHIT IN ONE BIGI BIGI BOOM XPLOSION FILE!!!!!!

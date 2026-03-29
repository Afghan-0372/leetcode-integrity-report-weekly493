import re, time, tracemalloc
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from functools import partial
from report_modules import gen_report, save_report
from utils import parse_dump, get_logic_signature, normalize, get_ast_fingerprint, detect_ai_noise
from compare_worker import compare_worker_serial, compare_worker_original

class AntiCheatHacker:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = parse_dump(file_path)
        self.reports, self.clusters = [], defaultdict(list)
        
        # Паттерны для AI
        p = lambda r: re.compile(r, re.I)
        self.ai_patterns = {
            "full": {p(r"// Step \d+:"): "Steps", p(r"// Time Complexity:"): "Complexity", 
                     p(r"Explanation:"): "Text", p(r"auto solve = \[&\]"): "Lambda Rec"},
            "short": {p(r"// Step \d+:"): "Steps", p(r"// Time Complexity:"): "Complexity"}
        }

    def _prepare_solutions(self, solutions):
        for s in solutions:
            lm = s['logic_masked'] = normalize(s['code'])
            s.update({
                'signature': get_logic_signature(s['code']),
                'ast_fp': get_ast_fingerprint(s['code']),
                'has_ai_noise': detect_ai_noise(s['code']),
                'ng_set': set(lm[k:k+4] for k in range(len(lm)-3)) if len(lm) >= 10 else set()
            })

    def analyze(self):
        by_q = defaultdict(list)
        for sol in self.data: by_q[sol['q']].append(sol)

        for q_name, solutions in by_q.items():
            if q_name not in ["Q3", "Q4"]: continue
            N = len(solutions)
            print(f"Analyzing {q_name} (N={N})")

            self._prepare_solutions(solutions)
            
            t = time.time()
            if N <= 1200: # SERIAL_THRESHOLD
                results = [compare_worker_serial(i, solutions) for i in range(N)]
            else:
                # Fixed #### only transfer solutions to partial
                with Pool(processes=max(2, cpu_count()-2)) as pool:
                    func = partial(compare_worker_original, solutions=solutions)
                    results = pool.map(func, enumerate(solutions))
            
            print(f"- Processed in {time.time() - t:.4f}s")
            self._process_clusters(q_name, solutions, results)

    def _process_clusters(self, q_name, solutions, results):
        processed_indices = set()
        r2i = {s['rank']: idx for idx, s in enumerate(solutions)}

        for i, cluster, sims, _ in results:
            if i in processed_indices: continue
            
            sol = solutions[i]
            is_group = len(cluster) > 1
            pats = self.ai_patterns["short"] if is_group else self.ai_patterns["full"]
            found_ai = [desc for pat, desc in pats.items() if pat.search(sol['code'])]

            if is_group:
                avg = int((sum(sims)/len(sims))*100) if sims else 100
                self.clusters[q_name].append({"ranks": sorted(cluster), "avg_sim": avg})
                gen_report(self, sol, cluster, found_ai)
                for r in cluster: 
                    if r in r2i: processed_indices.add(r2i[r])
            elif found_ai:
                gen_report(self, sol, [sol['rank']], found_ai)
                processed_indices.add(i)

    def save_final_report(self, filename="LEETCODE_AUDIT_REPORT.pdf"):
        save_report(self, filename)

if __name__ == "__main__":
    tracemalloc.start()
    start = time.time()
    
    hacker = AntiCheatHacker("contest_dump.txt")
    hacker.analyze()
    

    _, peak = tracemalloc.get_traced_memory()
    print(f"Done in {time.time()-start:.2f}s | Peak RAM: {peak/10**6:.2f}MB")
    #hacker.save_final_report()

import re, time, tracemalloc
from collections import defaultdict
import multiprocessing as mp
from functools import partial
# imports
import report_modules as rm
import utils as ut
import compare_worker as cw

class Engine:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = ut.parse_dump(file_path)
        self.reports, self.clusters = [], defaultdict(list)
        
        # AI Patterns
        p = lambda r: re.compile(r, re.I)
        self.ai_patterns = {
            "full": {p(r"// Step \d+:"): "Steps", p(r"// Time Complexity:"): "Complexity", 
                     p(r"Explanation:"): "Text", p(r"auto solve = \[&\]"): "Lambda Rec"},
            "short": {p(r"// Step \d+:"): "Steps", p(r"// Time Complexity:"): "Complexity"}
        }
        

    def _prepare_solutions(self, solutions):
        for s in solutions:
            lm = s['logic_masked'] = ut.normalize(s['code'])
            s.update({
                'signature': ut.get_logic_signature(s['code']),
                'ast_fp': ut.get_ast_c(s['code']),
                'has_ai_noise': ut.detect_ai_noise_c(s['code']),
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
            if N <= 1200:
                results = [cw.compare_worker_serial(i, solutions) for i in range(N)]
            else:
                # Fixed #### only transfer solutions to partial
                with mp.Pool(processes=max(2, mp.cpu_count()-2)) as pool:
                    func = partial(cw.compare_worker_original, solutions=solutions)
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
                rm.gen_report(self, sol, cluster, found_ai)
                for r in cluster: 
                    if r in r2i: processed_indices.add(r2i[r])
            elif found_ai:
                rm.gen_report(self, sol, [sol['rank']], found_ai)
                processed_indices.add(i)
    # Final PDF report just visualise the scale of issue
    def save_final_report(self, filename="LEETCODE_AUDIT_REPORT.pdf"):
        rm.save_report(self, filename)

if __name__ == "__main__":
    tracemalloc.start()
    start = time.time()
    
    hacker = Engine("contest_dump.txt")
    hacker.analyze()
    
    _, peak = tracemalloc.get_traced_memory()
    print(f"Done in {time.time()-start:.2f}s | Peak RAM: {peak/10**6:.2f}MB")
    #hacker.save_final_report()

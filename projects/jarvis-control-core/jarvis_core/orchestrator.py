from __future__ import annotations
import threading, time

class Orchestrator:
    """Runs heterogeneous workers against one shared transactional queue."""
    def __init__(self, runner_factory, workers, idle_sleep=.05):
        self.runner_factory=runner_factory; self.workers=list(workers); self.idle_sleep=idle_sleep
    def run_until_idle(self, max_idle_rounds=3):
        results=[]; lock=threading.Lock()
        def loop(worker):
            runner=self.runner_factory(); idle=0
            while idle < max_idle_rounds:
                out=runner.run_once(worker)
                with lock: results.append((worker.name,out))
                if out["status"]=="IDLE":
                    idle+=1; time.sleep(self.idle_sleep)
                else: idle=0
        threads=[threading.Thread(target=loop,args=(w,)) for w in self.workers]
        for t in threads:t.start()
        for t in threads:t.join()
        return results

from optimizer import *
import random,json,time
def seq(pieces,stock,kerf):
 bars=[]
 for p in pieces:
  if not bars or used_length([x.length_mm for x in bars[-1]],kerf)+p.length_mm+(kerf if bars[-1] else 0)>stock: bars.append([p])
  else: bars[-1].append(p)
 return bars
random.seed(20260810);cases=[]
for n in [20,50,100,250]:
 ps=[Piece(str(i),random.randint(300,3200)) for i in range(n)];row={'n':n}
 for name,fn in [('sequential',seq),('ffd',first_fit_decreasing),('bfd',best_fit_decreasing)]:
  t=time.perf_counter();bars=fn(ps,6000,3);dt=(time.perf_counter()-t)*1000;row[name]={**summarize(bars,6000,3),'runtime_ms':round(dt,3)}
 cases.append(row)
with open('results/benchmark.json','w') as f: json.dump({'seed':20260810,'stock_mm':6000,'kerf_mm':3,'cases':cases},f,indent=2)
print(json.dumps(cases,indent=2))

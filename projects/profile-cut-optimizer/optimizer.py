from dataclasses import dataclass
import csv,json,math
@dataclass(frozen=True)
class Piece:
    id:str; length_mm:int; profile:str='default'
def used_length(lengths,kerf_mm): return sum(lengths)+max(0,len(lengths)-1)*kerf_mm
def waste_for_bar(stock_mm,lengths,kerf_mm): return stock_mm-used_length(lengths,kerf_mm)
def validate(pieces,stock_mm,kerf_mm):
    if stock_mm<=0 or kerf_mm<0: raise ValueError('stock_mm must be >0 and kerf_mm >=0')
    for p in pieces:
        if p.length_mm<=0: raise ValueError(f'non-positive piece {p.id}')
        if p.length_mm>stock_mm: raise ValueError(f'piece {p.id} exceeds stock length')
def _fits(bar,length,stock_mm,kerf_mm): return used_length(bar,kerf_mm)+length+(kerf_mm if bar else 0)<=stock_mm
def first_fit_decreasing(pieces,stock_mm,kerf_mm=3):
    validate(pieces,stock_mm,kerf_mm); bars=[]
    for p in sorted(pieces,key=lambda x:x.length_mm,reverse=True):
        for b in bars:
            if _fits([x.length_mm for x in b],p.length_mm,stock_mm,kerf_mm): b.append(p); break
        else: bars.append([p])
    return bars
def best_fit_decreasing(pieces,stock_mm,kerf_mm=3):
    validate(pieces,stock_mm,kerf_mm); bars=[]
    for p in sorted(pieces,key=lambda x:x.length_mm,reverse=True):
        c=[]
        for i,b in enumerate(bars):
            lens=[x.length_mm for x in b]
            if _fits(lens,p.length_mm,stock_mm,kerf_mm): c.append((waste_for_bar(stock_mm,lens+[p.length_mm],kerf_mm),i))
        if c: bars[min(c)[1]].append(p)
        else: bars.append([p])
    return bars
def exact_branch_and_bound(pieces,stock_mm,kerf_mm=3,max_pieces=28):
    validate(pieces,stock_mm,kerf_mm)
    if len(pieces)>max_pieces: raise ValueError(f'exact solver limited to {max_pieces} pieces')
    ordered=sorted(pieces,key=lambda x:x.length_mm,reverse=True); best=[list(b) for b in best_fit_decreasing(ordered,stock_mm,kerf_mm)]; bars=[]
    def rec(i):
        nonlocal best
        if len(bars)>=len(best): return
        if i==len(ordered): best=[list(b) for b in bars]; return
        remaining=sum(p.length_mm for p in ordered[i:]); free=sum(stock_mm-used_length([x.length_mm for x in b],kerf_mm) for b in bars)
        if len(bars)+math.ceil(max(0,remaining-free)/stock_mm)>=len(best): return
        p=ordered[i]; seen=set()
        for b in bars:
            state=used_length([x.length_mm for x in b],kerf_mm)
            if state in seen: continue
            seen.add(state)
            if _fits([x.length_mm for x in b],p.length_mm,stock_mm,kerf_mm): b.append(p); rec(i+1); b.pop()
        bars.append([p]); rec(i+1); bars.pop()
    rec(0); return best
def summarize(bars,stock_mm,kerf_mm):
    used=sum(used_length([p.length_mm for p in b],kerf_mm) for b in bars); purchased=len(bars)*stock_mm; waste=purchased-used
    return {'bars':len(bars),'purchased_mm':purchased,'used_mm':used,'waste_mm':waste,'waste_pct':round(100*waste/purchased,2) if purchased else 0}
def optimize_by_profile(pieces,stock_mm=6000,kerf_mm=3,exact_threshold=22):
    out={}
    for profile in sorted(set(p.profile for p in pieces)):
        ps=[p for p in pieces if p.profile==profile]; method='exact' if len(ps)<=exact_threshold else 'best_fit_decreasing'; bars=exact_branch_and_bound(ps,stock_mm,kerf_mm,max_pieces=exact_threshold) if method=='exact' else best_fit_decreasing(ps,stock_mm,kerf_mm)
        out[profile]={'method':method,'bars':bars,'summary':summarize(bars,stock_mm,kerf_mm)}
    return out
def load_csv(path):
    pieces=[]
    with open(path,newline='',encoding='utf-8') as f:
        for i,row in enumerate(csv.DictReader(f),1):
            for q in range(int(row.get('qty',1))): pieces.append(Piece(f"{row.get('id',i)}-{q+1}",int(row['length_mm']),row.get('profile','default')))
    return pieces
def export_plan(result,path,stock_mm,kerf_mm):
    serial={'stock_mm':stock_mm,'kerf_mm':kerf_mm,'profiles':{}}
    for prof,r in result.items():
        serial['profiles'][prof]={'method':r['method'],'summary':r['summary'],'bars':[{'bar':i+1,'cuts':[{'id':p.id,'length_mm':p.length_mm} for p in b],'used_mm':used_length([p.length_mm for p in b],kerf_mm),'waste_mm':waste_for_bar(stock_mm,[p.length_mm for p in b],kerf_mm)} for i,b in enumerate(r['bars'])]}
    with open(path,'w') as f: json.dump(serial,f,indent=2)
    return serial

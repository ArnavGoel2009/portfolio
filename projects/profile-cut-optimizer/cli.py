import argparse
from optimizer import load_csv,optimize_by_profile,export_plan
p=argparse.ArgumentParser();p.add_argument('csv');p.add_argument('--stock',type=int,default=6000);p.add_argument('--kerf',type=int,default=3);p.add_argument('--out',default='cut_plan.json');a=p.parse_args()
r=optimize_by_profile(load_csv(a.csv),a.stock,a.kerf);s=export_plan(r,a.out,a.stock,a.kerf)
for prof,x in s['profiles'].items(): print(prof,x['method'],x['summary'])

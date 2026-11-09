from multiprocessing import Pool
from audio import births_events
def f(s):
    e = births_events(s); return s, sum(x[0] for x in e)
if __name__ == "__main__":
    import sys
    names = sys.argv[1:] or ['rpent','gun','end','eater','glider','osc','law','open','still','credits','sting']
    with Pool(2) as p:
        for r in p.imap_unordered(f, names): print(r, flush=True)

#!/usr/bin/env python3
"""Parse STRAT_EVIDENCE lines from journal to extract per-account signal metrics"""
import sys
import re
from collections import defaultdict

accounts = defaultdict(lambda: {
    "signals": 0,
    "decisions": {"BUY": 0, "SELL": 0, "NONE": 0},
    "instruments": set(),
    "strategies": set()
})

for line in sys.stdin:
    m = re.search(r"account=(\d+)", line)
    if not m:
        continue
    acc = m.group(1)
    
    m_strat = re.search(r"strategy=(\w+)", line)
    m_sig = re.search(r"signals_generated=(\d+)", line)
    m_dec = re.search(r"decision=(\w+)", line)
    m_inst = re.search(r"signal_instrument=(\w+)", line)
    
    if m_strat:
        accounts[acc]["strategies"].add(m_strat.group(1))
    if m_sig:
        accounts[acc]["signals"] += int(m_sig.group(1))
    if m_dec:
        dec = m_dec.group(1)
        if dec in accounts[acc]["decisions"]:
            accounts[acc]["decisions"][dec] += 1
    if m_inst:
        accounts[acc]["instruments"].add(m_inst.group(1))

for acc in sorted(accounts.keys()):
    d = accounts[acc]
    strat = list(d["strategies"])[0] if d["strategies"] else "unknown"
    inst_list = sorted(d["instruments"])
    print(f"{acc}|{strat}|{d['signals']}|{d['decisions']['BUY']}|{d['decisions']['SELL']}|{d['decisions']['NONE']}|{len(d['instruments'])}|{','.join(inst_list)}")

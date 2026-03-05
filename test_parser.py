"""Quick diagnostic: run parser on all problem files and show counts + structure."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rgf.planning_api import docx_parser as dp

DATA = '/home/adilannister/ml_engineering/polozhenia/parse_functioons/data'

FILES = {
    'УЗиСП':    'Положение УЗСП.docx',
    'УМП':      'Положение УМП.docx',
    'УО':       'Положение УО.docx',
    'УОЗ':      'Положение УОЗ.docx',
    'УОДДиПТ':  'Положение УОДДиПТ.docx',
    'УЗО':      'Положение УЗО.docx',
    'УКИиЖИ':   'Положение УКИЖИ.docx',
    'УК':       'Положение УК.docx',
}

dp.DEBUG = True

for short, fname in FILES.items():
    path = os.path.join(DATA, fname)
    print(f'\n{"="*60}')
    print(f'  {short}  ({fname})')
    print('='*60)
    r = dp.parse_docx_universal(path)
    print(f'  tasks           : {len(r["tasks"])}')
    print(f'  rights          : {len(r["authorities_rights"])}')
    print(f'  responsibilities: {len(r["authorities_responsibilities"])}')
    print(f'  functions       : {len(r["functions"])}')
    print(f'  confidence      : {r["confidence"]:.2f}')
    gp = r['general_provisions']
    gp_lines = gp.splitlines()
    print(f'  general_prov    : {len(gp_lines)} lines  (last: {gp_lines[-1][:80] if gp_lines else "–"})')
    add = r['additions']
    add_lines = add.splitlines()
    print(f'  additions       : {len(add_lines)} lines  (first: {add_lines[0][:80] if add_lines else "–"})')
    if r['functions']:
        print(f'  func[0]         : {r["functions"][0][:80]}')
        print(f'  func[-1]        : {r["functions"][-1][:80]}')

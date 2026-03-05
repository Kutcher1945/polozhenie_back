"""Detailed diagnostic: show section boundaries for problem files."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from rgf.planning_api.docx_parser import _iter_texts
from docx import Document

DATA = '/home/adilannister/ml_engineering/polozhenia/parse_functioons/data'

FILES = {
    'УЗО':     'Положение УЗО.docx',
    'УКИиЖИ':  'Положение УКИЖИ.docx',
    'УК':      'Положение УК.docx',
}

for short, fname in FILES.items():
    path = os.path.join(DATA, fname)
    doc = Document(path)
    texts = [t.replace('\xa0', ' ') for t in _iter_texts(doc) if len(t) >= 3]
    print(f'\n{"="*70}')
    print(f'  {short}  —  {len(texts)} lines total')
    print('='*70)
    for i, t in enumerate(texts):
        print(f'  [{i:3d}] {t[:110]}')

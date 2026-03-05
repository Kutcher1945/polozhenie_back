"""
Universal DOCX parser — single-pass keyword-driven state machine.

Handles all known Almaty government document structures:
 - "Глава 1 / Глава 2" chapter-based
 - "1. Общие положения / 2. Задачи" numbered-sections
 - Keyword-only headers (no chapter/section numbers)
 - Combined "Права и обязанности" section (no separate sub-markers)
 - Items numbered as "N)" or "N. " or plain text (with regular or non-breaking space)
"""

import re
from docx import Document

DEBUG = False

def _debug(msg):
    if DEBUG:
        print(msg)


# ─── Text extraction ──────────────────────────────────────────────────────────

def _iter_texts(doc):
    """Yield paragraph texts in document order, including from tables."""
    for elem in doc.element.body:
        local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if local == 'p':
            from docx.text.paragraph import Paragraph
            text = Paragraph(elem, doc).text.strip()
            if text:
                yield text
        elif local == 'tbl':
            from docx.table import Table
            for row in Table(elem, doc).rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        text = p.text.strip()
                        if text:
                            yield text


# ─── Classification helpers ───────────────────────────────────────────────────

# Numbered list item: "1) text" — also matches non-breaking space (\xa0)
_ITEM_PAREN_RE = re.compile(r'^\d+\)[\s\xa0]')
# Chapter header: "Глава 1.", "Глава 2.", etc.
_CHAPTER_RE    = re.compile(r'^глава\s+\d+', re.I)


def _is_multi_keyword_title(tl):
    """
    True for combined section titles that list multiple topics, e.g.:
    "2. Миссия, цель, основные задачи, функции, права и обязанности..."
    These are chapter titles, not zone-specific headers.
    """
    return bool(
        re.search(r'задачи.{2,}функции', tl) or
        re.search(r'задачи.{2,}полномочия', tl) or
        re.search(r'задачи.{2,}права', tl) or
        re.search(r'миссия.{2,}задачи', tl)
    )


def _sub_from_text(tl):
    """
    Detect a rights/responsibilities sub-header within the authorities zone.
    Accepts: "права:", "1) права:", "2) обязанности:", "права :", etc.
    Returns 'rights', 'responsibilities', or None.
    """
    if re.match(r'^(\d+[\)\.]\s*)?права\s*:?\s*$', tl):
        return 'rights'
    if re.match(r'^(\d+[\)\.]\s*)?обязанности\s*:?\s*$', tl):
        return 'responsibilities'
    return None


# Subsection words that appear inside tasks/functions zones but are NOT items
_NON_ITEM_HEADERS = re.compile(
    r'^\d+[\.\)]\s*(миссия|цель\b|наименование|место нахождения|финансирование)',
    re.I
)

# ─── Main parser ──────────────────────────────────────────────────────────────

def parse_docx_universal(docx_path):
    """
    Parse a .docx regulation document and return structured data dict.
    Keys: general_provisions, tasks, authorities_rights,
          authorities_responsibilities, functions, additions.
    """
    doc = Document(docx_path)

    general_provisions    = []
    tasks                 = []
    authorities_rights    = []
    authorities_responsibilities = []
    functions             = []
    additions             = []

    zone = None   # 'general' | 'tasks' | 'authorities' | 'functions' | 'additions'
    sub  = None   # 'rights' | 'responsibilities' | 'combined'  (within authorities)
    # Structural progress flags — order-independent zone detection
    seen_general   = False
    seen_tasks     = False
    seen_functions = False

    def _reset_chapter():
        """Full state reset between document chapters."""
        nonlocal zone, sub, seen_general, seen_tasks, seen_functions
        zone           = None
        sub            = None
        seen_general   = False
        seen_tasks     = False
        seen_functions = False
        _debug("  [reset chapter]")

    for text in _iter_texts(doc):
        if len(text) < 3:
            continue

        tl = text.lower()

        # ── Attempt to detect zone transitions ────────────────────────────────
        # N) items are never zone headers — skip zone detection for them.
        if not _ITEM_PAREN_RE.match(text):

            # ── Skip multi-keyword chapter titles ────────────────────────────
            # e.g. "2. Миссия, цель, задачи, функции, права и обязанности"
            if _is_multi_keyword_title(tl) and len(text) < 300:
                _debug(f"  SKIP multi-kw: {text[:60]}")
                if zone == 'general':
                    zone = None  # stop capturing миссия/цель as general provisions
                continue

            # ── General provisions ───────────────────────────────────────────
            if 'общие положения' in tl and len(text) < 120:
                zone = 'general'
                sub  = None
                seen_general = True
                _debug(f"  ZONE→general: {text[:60]}")
                continue

            # ── Additions (property, reorganization, …) ──────────────────────
            # Keyword must be near the start of the text (main topic), not buried
            # mid-sentence ("управлять переданным ему имуществом;").
            _kw_pos = min(
                (tl.index(kw) for kw in ('имущество', 'реорганизация', 'ликвидация') if kw in tl),
                default=999,
            )
            if _kw_pos < 20 and len(text) < 120:
                zone = 'additions'
                additions.append(text)
                _debug(f"  ZONE→additions: {text[:60]}")
                continue

            # ── Tasks ────────────────────────────────────────────────────────
            if re.match(r'^(\d+[\.\)]\s*)?задачи\b', tl, re.I) and len(text) < 120:
                if not _is_multi_keyword_title(tl) and not re.search(r'задачи.{2,}права|задачи.{2,}функции', tl):
                    zone = 'tasks'
                    sub  = None
                    seen_tasks = True
                    _debug(f"  ZONE→tasks: {text[:60]}")
                    continue

            # ── Functions ────────────────────────────────────────────────────
            if re.match(r'^(\d+[\.\)]\s*)?функции\b', tl, re.I) and len(text) < 200:
                if not _is_multi_keyword_title(tl) and not re.search(r'функции.{2,}права', tl):
                    zone = 'functions'
                    sub  = None
                    seen_functions = True
                    _debug(f"  ZONE→functions: {text[:60]}")
                    continue

            # ── Organizational / leadership sections → additions ──────────────
            if (re.match(r'^(\d+[\.\)]\s*)?(организация\s+деятельности|статус)', tl, re.I)
                    and re.search(r'деятельности|руководител', tl, re.I)
                    and len(text) < 200):
                zone = 'additions'
                additions.append(text)
                _debug(f"  ZONE→additions(org/status): {text[:60]}")
                continue

            # ── Authorities / Полномочия ──────────────────────────────────────
            # "Полномочия руководителя" belongs to additions, not authorities
            if re.match(r'^(\d+[\.\)]\s*)?полномочия\b', tl, re.I) and len(text) < 150:
                if re.search(r'руководител', tl, re.I):
                    zone = 'additions'
                    additions.append(text)
                    _debug(f"  ZONE→additions(полномочия руководителя): {text[:60]}")
                    continue
                zone = 'authorities'
                sub  = None
                if re.search(r'права\s*:', tl):
                    sub = 'rights'
                _debug(f"  ZONE→authorities(полномочия): {text[:60]}")
                continue

            # ── Combined "Права и обязанности" ───────────────────────────────
            # Real zone header when structural progress confirms we're past the
            # intro section, OR the legislative "определяется" formula is used,
            # OR it is a short standalone header without an org name.
            if re.search(r'права\s+и\s+обязанности', tl) and len(text) < 700:
                is_real_header = (
                    # Strongest signal: document has already gone through general + tasks/functions
                    (seen_general and (seen_tasks or seen_functions) and zone not in ('additions',))
                    or re.search(r'определяет|определяются|определен', tl)
                    or (len(text) < 50 and not re.search(r'управления|учреждения|аппарата', tl))
                )
                if is_real_header:
                    zone = 'authorities'
                    sub  = 'combined'
                    _debug(f"  ZONE→authorities(combined): {text[:60]}")
                continue

            # ── Chapter header with no recognized zone keyword → reset state ──
            # Prevents zone/state leakage into Глава 3 (Организация деятельности)
            # and beyond. Глава 1/2 are handled above before reaching this point.
            if _CHAPTER_RE.match(tl):
                _reset_chapter()
                continue

        # ── Sub-zone detection inside authorities (rights / responsibilities) ──
        if zone == 'authorities':
            sub_detected = _sub_from_text(tl)
            if sub_detected:
                sub = sub_detected
                _debug(f"  sub→{sub_detected}: {text[:60]}")
                continue

        # ── Content collection ────────────────────────────────────────────────
        if zone == 'general':
            general_provisions.append(text)

        elif zone == 'tasks':
            if _NON_ITEM_HEADERS.match(text):
                continue
            if len(text) > 8:
                tasks.append(text)

        elif zone == 'authorities':
            if len(text) > 10:
                if sub in ('rights', 'combined'):
                    authorities_rights.append(text)
                if sub in ('responsibilities', 'combined'):
                    # combined: intentionally duplicated into both lists — the API
                    # requires both fields populated when the document merges them
                    authorities_responsibilities.append(text)

        elif zone == 'functions':
            # ── Explicit rights section: "вправе:" / "имеет право:" header ──
            if (not _ITEM_PAREN_RE.match(text)
                    and re.search(r'\bвправе\b|\bимеет\s+право\b', tl)
                    and text.rstrip().endswith(':')
                    and len(text) < 300):
                zone = 'authorities'
                sub  = 'combined'
                _debug(f"  ZONE→authorities(вправе): {text[:60]}")
                continue

            if _NON_ITEM_HEADERS.match(text):
                continue
            if len(text) > 8:
                functions.append(text)

        elif zone == 'additions':
            additions.append(text)

    has_gp    = bool(general_provisions)
    has_tasks = len(tasks) >= 1
    has_funcs = len(functions) >= 3
    has_auth  = bool(authorities_rights or authorities_responsibilities)
    confidence = sum([has_gp, has_tasks, has_funcs, has_auth]) / 4

    _debug(f"  confidence={confidence:.2f}  gp={has_gp} tasks={has_tasks} funcs={has_funcs} auth={has_auth}")

    return {
        'general_provisions':           '\n'.join(general_provisions),
        'tasks':                        tasks,
        'authorities_rights':           authorities_rights,
        'authorities_responsibilities': authorities_responsibilities,
        'functions':                    functions,
        'additions':                    '\n'.join(additions),
        'confidence':                   confidence,   # 0.0–1.0; <0.75 warrants manual review
    }

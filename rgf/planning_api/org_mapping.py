"""
Маппинг организаций для автоматического определения GU ID

Основано на data/guid_names.txt
"""

import re
from pathlib import Path
from typing import Optional
from docx import Document


# Маппинг аббревиатура → ключевые слова для поиска организации
ABBREVIATION_TO_SEARCH = {
    'УДР': 'развития дорожной инфраструктуры',
    'УОДДиПТ': 'организации дорожного движения',
    'УЭиФ': 'экономики и финансов',
    'УМПиТиГО': 'мобилизационной подготовке',
    'УМПТиГР': 'мобилизационной подготовке',
    'УКиЖИ': 'коммунальной инфраструктуры',
    'УКИЖИ': 'коммунальной инфраструктуры',
    'УРОП': 'развития общественных пространств',
    'УЗСП': 'занятости и социальных программ',
    'УМП': 'молодежной политики',
    'УЭиОС': 'экологии и окружающей среды',
    'УОЗ': 'общественного здравоохранения',
    'УЭВ': 'энергетики и водоснабжения',
    'УЭиВ': 'энергетики и водоснабжения',
    'УСтроительства': 'строительства города',
    'УДРел': 'делам религий',
    'УЦ': 'цифровизации',
    'УПиИ': 'предпринимательства',
    'УГК': 'градостроительного контроля',
    'УК': 'культуры города',
    'УС': 'спорта города',
    'УТур': 'туризма',
    'УТ': 'туризма',
    'УГА': 'государственных активов',
    'УЗО': 'земельных отношений',
    'УО': 'образования города',
    'УВП': 'внутренней политики',
    'УАиГ': 'архитектуры и градостроительства',
    'Аппарат': 'Аппарат акима города',
}


def extract_abbreviation_from_filename(filename):
    """Извлечь аббревиатуру из имени файла."""
    name = filename.replace('.docx', '').replace('.DOCX', '')

    patterns = [
        r'Положение\s+([А-ЯЁа-яё]+(?:и[А-ЯЁ][А-ЯЁ])?)',
        r'Положение\s+о\s+«(Аппарат)',
    ]

    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            abbr = match.group(1)
            if abbr in ABBREVIATION_TO_SEARCH:
                return abbr

    return None


def extract_org_name_from_docx(file_path):
    """Извлечь название организации из заголовка документа."""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs[:5]:
            text = para.text.strip()
            match = re.search(r'«([^»]+)»', text)
            if match:
                org_name = match.group(1).strip()
                if 'управление' in org_name.lower() or 'аппарат' in org_name.lower():
                    return org_name
        return None
    except Exception:
        return None


def find_gu_by_abbreviation(abbreviation, gu_list):
    """Найти организацию в списке по аббревиатуре."""
    if abbreviation not in ABBREVIATION_TO_SEARCH:
        return None, None

    search_keywords = ABBREVIATION_TO_SEARCH[abbreviation]
    for gu in gu_list:
        gu_name = gu.get('nameRu', '')
        if search_keywords.lower() in gu_name.lower():
            return gu.get('id'), gu.get('nameRu')

    return None, None


def find_gu_by_org_name(org_name, gu_list):
    """Найти организацию в списке по полному названию."""
    org_name_lower = org_name.lower()

    for gu in gu_list:
        gu_name = gu.get('nameRu', '')
        gu_core = gu_name.lower()
        for prefix in ['кгу "', 'кгу «', 'кгу', '"', '«', '»']:
            gu_core = gu_core.replace(prefix, '')
        gu_core = gu_core.strip().strip('"»')

        if org_name_lower in gu_core or gu_core in org_name_lower:
            return gu.get('id'), gu.get('nameRu')

    # Fuzzy keyword match
    keywords = [w for w in org_name_lower.split()
                if len(w) > 4 and w not in ['города', 'алматы', 'управление']]

    best_match = None
    max_matches = 0
    for gu in gu_list:
        gu_name_lower = gu.get('nameRu', '').lower()
        matches = sum(1 for kw in keywords if kw in gu_name_lower)
        if matches > max_matches and matches >= len(keywords) // 2:
            max_matches = matches
            best_match = gu

    if best_match:
        return best_match.get('id'), best_match.get('nameRu')

    return None, None


_guid_mapping_cache: Optional[dict] = None


def load_guid_mapping(guid_file_path=None):
    """Загрузить прямой маппинг GUID → Name из файла (кэшируется в памяти)."""
    global _guid_mapping_cache
    if _guid_mapping_cache is not None:
        return _guid_mapping_cache

    if guid_file_path is None:
        guid_file_path = Path(__file__).parent / 'data' / 'guid_names.txt'

    guid_mapping = {}
    try:
        with open(guid_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('GUID') or line.startswith('='):
                    continue
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    guid = parts[0].strip()
                    name = parts[1].strip()
                    if guid and name:
                        guid_mapping[guid] = name
    except FileNotFoundError:
        pass

    _guid_mapping_cache = guid_mapping
    return guid_mapping


def suggest_gu_for_file(filename, gu_list, file_path=None, use_guid_mapping=True):
    """Автоматически предложить организацию для файла.

    Returns:
        tuple: (gu_id, gu_name, detected_source)
    """
    if file_path is None:
        file_path = Path(__file__).parent / 'data' / filename

    detected_source = None

    # Strategy 0: Direct GUID mapping
    if use_guid_mapping:
        guid_mapping = load_guid_mapping()
        if guid_mapping:
            abbr = extract_abbreviation_from_filename(filename)
            if abbr and abbr in ABBREVIATION_TO_SEARCH:
                keywords = ABBREVIATION_TO_SEARCH[abbr]
                for guid, name in guid_mapping.items():
                    if keywords.lower() in name.lower():
                        for gu in gu_list:
                            if str(gu.get('id')) == str(guid):
                                detected_source = f"[GUID mapping: {abbr} → {guid}]"
                                return gu.get('id'), gu.get('nameRu'), detected_source

    # Strategy 1: Abbreviation from filename
    abbr = extract_abbreviation_from_filename(filename)
    if abbr:
        gu_id, gu_name = find_gu_by_abbreviation(abbr, gu_list)
        if gu_id:
            detected_source = f"[Аббревиатура из имени файла: {abbr}]"
            return gu_id, gu_name, detected_source

    # Strategy 2: Extract from document content
    org_name = extract_org_name_from_docx(file_path)
    if org_name:
        detected_source = org_name
        gu_id, gu_name = find_gu_by_org_name(org_name, gu_list)
        if gu_id:
            return gu_id, gu_name, detected_source

    return None, None, detected_source

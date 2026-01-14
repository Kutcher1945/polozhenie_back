"""
Test script for Clinical Protocol RAG API
Demonstrates how to use the RAG service to answer questions
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mchs_back.settings')
django.setup()

from clinical_protocols.services import rag_service
from colorama import Fore, Style, init

init(autoreset=True)

def print_section(title):
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{title}")
    print(f"{'='*70}{Style.RESET_ALL}\n")

def print_result(result):
    """Pretty print the RAG result"""
    print(f"{Fore.GREEN}✓ Успех: {result['success']}{Style.RESET_ALL}")

    if result.get('error'):
        print(f"{Fore.RED}✗ Ошибка: {result['error']}{Style.RESET_ALL}")
        return

    print(f"\n{Fore.YELLOW}ВОПРОС:{Style.RESET_ALL}")
    print(result['question'])

    print(f"\n{Fore.GREEN}ОТВЕТ:{Style.RESET_ALL}")
    print(result['answer'])

    metadata = result.get('metadata', {})
    print(f"\n{Fore.CYAN}МЕТАДАННЫЕ:{Style.RESET_ALL}")
    print(f"  Модель: {metadata.get('model')}")
    print(f"  Язык: {metadata.get('language')}")
    print(f"  Источников найдено: {metadata.get('num_sources')}")

    if result.get('sources'):
        print(f"\n{Fore.MAGENTA}ИСТОЧНИКИ ({len(result['sources'])}):{Style.RESET_ALL}")
        for i, source in enumerate(result['sources'][:3], 1):  # Show first 3
            print(f"\n  [{i}] {source['protocol_name']}")
            print(f"      Тип: {source['content_type_display']}")
            print(f"      Заголовок: {source['title']}")
            print(f"      Страницы: {source['page_from']}-{source['page_to']}")
            print(f"      Содержание (первые 200 символов):")
            print(f"      {source['content'][:200]}...")

        if len(result['sources']) > 3:
            print(f"\n  ... и еще {len(result['sources']) - 3} источник(ов)")


def main():
    print_section("🏥 ТЕСТ RAG API ДЛЯ КЛИНИЧЕСКИХ ПРОТОКОЛОВ")

    # Test 1: Simple question about definition
    print_section("ТЕСТ 1: Что такое HELLP-синдром?")
    result1 = rag_service.answer_question(
        question="Что такое HELLP-синдром?",
        protocol_id=1,
        include_sources=True
    )
    print_result(result1)

    # Test 2: Diagnostic criteria
    print_section("ТЕСТ 2: Диагностические критерии")
    result2 = rag_service.answer_question(
        question="Какие диагностические критерии HELLP-синдрома?",
        protocol_id=1,
        content_types=['diagnosis'],
        include_sources=True
    )
    print_result(result2)

    # Test 3: Treatment question
    print_section("ТЕСТ 3: Лечение")
    result3 = rag_service.answer_question(
        question="Как лечить HELLP-синдром? Какие препараты используются?",
        protocol_id=1,
        content_types=['treatment', 'drugs'],
        include_sources=True
    )
    print_result(result3)

    # Test 4: Complications
    print_section("ТЕСТ 4: Осложнения")
    result4 = rag_service.answer_question(
        question="Какие осложнения могут возникнуть при HELLP-синдроме?",
        protocol_id=1,
        content_types=['complications'],
        include_sources=True
    )
    print_result(result4)

    # Test 5: Search without AI
    print_section("ТЕСТ 5: Простой поиск (без AI)")
    search_results = rag_service.search_relevant_content(
        query="тромбоциты гемолиз",
        protocol_id=1,
        limit=5
    )
    print(f"Найдено разделов: {len(search_results)}")
    for i, section in enumerate(search_results, 1):
        print(f"\n[{i}] {section['content_type_display']}: {section['title'][:60]}...")
        print(f"    Содержание: {section['content'][:150]}...")

    print_section("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Прервано пользователем{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()

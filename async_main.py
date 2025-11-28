#!/usr/bin/env python3
"""
Асинхронная точка входа для DSEI Company Scraper
"""

import sys
import argparse
import asyncio
import signal
from pathlib import Path

# Добавление src в Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dsei_scraper import AsyncDSEICompanyScraper, Config


async def main():
    """Асинхронная главная точка входа"""
    parser = argparse.ArgumentParser(description='Асинхронный DSEI Company Scraper')
    parser.add_argument('--start-page', type=int, default=1, 
                       help='Начальный номер страницы (по умолчанию: 1)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Максимальное количество страниц для обработки (по умолчанию: все)')
    parser.add_argument('--config', type=str, default=None,
                       help='Путь к файлу конфигурации')
    parser.add_argument('--output', type=str, default=None,
                       help='Путь к выходному CSV файлу')
    parser.add_argument('--max-tasks', type=int, default=15,
                       help='Максимальное количество одновременных задач (по умолчанию: 15)')
    
    args = parser.parse_args()
    
    # Инициализация конфигурации
    if args.config:
        config = Config(args.config)
    else:
        config = Config()
    
    # Инициализация асинхронного скрапера
    scraper = AsyncDSEICompanyScraper(config, max_concurrent_tasks=args.max_tasks)
    
    # Настройка обработчиков сигналов для корректного завершения
    def signal_handler(signum, frame):
        print(f"\n🛑 Получен сигнал {signum}. Корректное завершение...")
        scraper.should_stop = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запуск скрапера
    try:
        await scraper.scrape_all_companies(
            start_page=args.start_page,
            max_pages=args.max_pages
        )
        
        # Сохранение с пользовательским выходным файлом если указан
        if args.output:
            await scraper.save_to_csv(args.output)
        
        print(f"🎉 Скрапинг завершен успешно! Собрано {len(scraper.companies_data)} компаний.")
        return 0
        
    except KeyboardInterrupt:
        print("⏹️ Скрапинг прерван пользователем")
        return 1
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return 1


def run():
    """Синхронная обертка для запуска асинхронного main"""
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(run())

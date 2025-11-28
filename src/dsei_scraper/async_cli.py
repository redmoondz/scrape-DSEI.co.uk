#!/usr/bin/env python3
"""
Интерфейс командной строки для асинхронного DSEI Company Scraper
"""

import asyncio
import click
from pathlib import Path
import sys

# Добавление src в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dsei_scraper import AsyncDSEICompanyScraper, Config


@click.command()
@click.option('--start-page', default=1, help='Начальный номер страницы')
@click.option('--max-pages', default=None, type=int, help='Максимальное количество страниц для обработки')
@click.option('--config', default=None, help='Путь к файлу конфигурации')
@click.option('--output', default=None, help='Путь к выходному CSV файлу')
@click.option('--max-tasks', default=15, help='Максимальное количество одновременных задач')
@click.option('--verbose', '-v', is_flag=True, help='Подробный вывод')
def async_scrape(start_page, max_pages, config, output, max_tasks, verbose):
    """Асинхронный скрапер компаний DSEI с ограничением до 15 одновременных задач."""
    
    async def run_scraper():
        # Инициализация конфигурации
        if config:
            cfg = Config(config)
        else:
            cfg = Config()
        
        # Инициализация асинхронного скрапера
        scraper = AsyncDSEICompanyScraper(cfg, max_concurrent_tasks=max_tasks)
        
        # Запуск скрапера
        try:
            await scraper.scrape_all_companies(
                start_page=start_page,
                max_pages=max_pages
            )
            
            # Сохранение с пользовательским выходным файлом если указан
            if output:
                await scraper.save_to_csv(output)
            
            click.echo(f"🎉 Скрапинг завершен успешно! Собрано {len(scraper.companies_data)} компаний.")
            
        except KeyboardInterrupt:
            click.echo("⏹️ Скрапинг прерван пользователем")
        except Exception as e:
            click.echo(f"💥 Ошибка: {e}")
            raise
    
    # Запуск асинхронной функции
    asyncio.run(run_scraper())


if __name__ == '__main__':
    async_scrape()

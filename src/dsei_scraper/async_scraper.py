#!/usr/bin/env python3
"""
Асинхронный DSEI.co.uk Company Data Scraper

Этот скрапер использует асинхронную архитектуру с ограничением до 15 одновременных задач:
1. Получает первую страницу ресурса
2. Собирает все блоки компаний (li теги с определенным классом)
3. Извлекает slugs компаний из каждого блока
4. Выполняет HTTP запросы к API для дополнительной информации о компаниях асинхронно
5. Сохраняет данные и переходит к следующей странице

Формат вывода CSV: company_name, slug_name, url, stand, tags, overview, website
"""

import asyncio
import aiohttp
import aiofiles
import csv
import re
import logging
import signal
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, quote
from typing import List, Dict, Optional, Set
import json
from pathlib import Path

from .config import Config


class AsyncDSEICompanyScraper:
    def __init__(self, config: Optional[Config] = None, max_concurrent_tasks: Optional[int] = None):
        """
        Инициализация асинхронного DSEI Company Scraper
        
        Args:
            config: Объект конфигурации. Если None, использует конфигурацию по умолчанию.
            max_concurrent_tasks: Максимальное количество одновременных задач. Если None, берет из конфигурации.
        """
        self.config = config or Config()
        
        # Определение количества одновременных задач
        if max_concurrent_tasks is None:
            async_config = self.config.get_async_config()
            max_concurrent_tasks = async_config.get('max_concurrent_tasks', 15)
        
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # URLs из конфигурации
        self.base_url = self.config.get_base_url()
        self.list_url_template = self.config.get_list_url_template()
        self.company_detail_url_template = self.config.get_company_detail_url_template()
        
        # Получение корня проекта для путей
        self.project_root = Path(__file__).parent.parent.parent
        
        # Настройка логирования
        self._setup_logging()
        
        # Хранение данных
        self.companies_data = []
        
        # Настройки из конфигурации
        self.delays = self.config.get_delays()
        self.timeouts = self.config.get_timeouts()
        self.selectors = self.config.get_selectors()
        self.max_retries = 3
        
        # Отслеживание существующих компаний для избежания дубликатов
        self.existing_companies: Set[str] = set()
        self.output_file_path = None
        self.processed_slugs: Set[str] = set()  # Отслеживание обработанных slugs во время текущей сессии
        
        # Семафор для ограничения количества одновременных задач
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        # Сессия будет создана в async методе
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Флаг для обработки остановки пользователем
        self.should_stop = False
        
        # Настройка обработчиков сигналов
        self._setup_signal_handlers()
    
    def _setup_logging(self):
        """Настройка конфигурации логирования"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / self.config.get_output_config().get('log_filename', 'scraper.log')
        
        # Очистка существующих обработчиков для избежания дублирования
        logging.getLogger().handlers.clear()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для корректного завершения"""
        def signal_handler(signum, frame):
            self.logger.info(f"🛑 Получен сигнал {signum}. Подготовка к корректному завершению...")
            self.should_stop = True
        
        # Настройка обработчиков для SIGINT (Ctrl+C) и SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _create_session(self):
        """Создание асинхронной HTTP сессии"""
        async_config = self.config.get_async_config()
        
        timeout = aiohttp.ClientTimeout(
            total=self.timeouts.get('request_timeout', 30),
            connect=async_config.get('connection_timeout', 10),
            sock_read=async_config.get('read_timeout', 30)
        )
        
        headers = {
            'User-Agent': self.config.get_user_agent(),
            'Accept': '*/*',
            'Accept-Language': 'ru,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'X-Requested-With': 'XMLHttpRequest',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': self.base_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-GPC': '1',
            'Priority': 'u=0'
        }
        
        # Ограничение соединений из конфигурации
        connector = aiohttp.TCPConnector(
            limit=async_config.get('connection_pool_size', 20),
            limit_per_host=async_config.get('per_host_limit', 10),
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector
        )
    
    async def _close_session(self):
        """Закрытие асинхронной HTTP сессии"""
        if self.session:
            await self.session.close()
    
    async def make_request_with_retry(self, url: str) -> Optional[str]:
        """
        Выполнение HTTP запроса с логикой повторных попыток и обработкой защиты сайта
        
        Args:
            url: URL для запроса
            
        Returns:
            Содержимое ответа как строка или None если все попытки не удались
        """
        if not self.session:
            await self._create_session()
            
        # Таймауты для защиты сайта (405, 429 ошибки)
        protection_timeouts = [30, 60, 90]  # секунды
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url) as response:
                    # Обработка защиты сайта
                    if response.status in [405, 429]:
                        timeout_index = min(attempt, len(protection_timeouts) - 1)
                        timeout_duration = protection_timeouts[timeout_index]
                        
                        self.logger.warning(
                            f"Сайт защищается (код {response.status}) для {url}. "
                            f"Ожидание {timeout_duration} секунд... (попытка {attempt + 1}/{self.max_retries})"
                        )
                        
                        await asyncio.sleep(timeout_duration)
                        continue
                    
                    response.raise_for_status()
                    # Возвращаем содержимое как строку
                    content = await response.text()
                    return content
                
            except aiohttp.ClientResponseError as e:
                # Обработка HTTP ошибок
                if e.status in [405, 429]:
                    timeout_index = min(attempt, len(protection_timeouts) - 1)
                    timeout_duration = protection_timeouts[timeout_index]
                    
                    self.logger.warning(
                        f"HTTP ошибка {e.status} для {url}. "
                        f"Ожидание {timeout_duration} секунд... (попытка {attempt + 1}/{self.max_retries})"
                    )
                    
                    await asyncio.sleep(timeout_duration)
                    continue
                else:
                    self.logger.warning(f"HTTP ошибка {e.status} для {url}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.logger.warning(f"Попытка {attempt + 1} не удалась для {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                else:
                    self.logger.error(f"Все {self.max_retries} попытки не удались для {url}")
        
        return None
    
    async def load_existing_companies(self, file_path: Optional[Path] = None) -> int:
        """
        Загрузка существующих компаний из CSV файла для избежания дубликатов
        
        Args:
            file_path: Путь к существующему CSV файлу. Если None, использует путь по умолчанию.
            
        Returns:
            Количество загруженных существующих компаний
        """
        if file_path is None:
            # Использование пути вывода по умолчанию
            data_dir = self.project_root / "data" / "processed"
            file_path = data_dir / self.config.get_output_config().get('csv_filename', 'dsei_companies.csv')
        
        # Сохранение пути выходного файла для последующего использования
        self.output_file_path = file_path
        
        if not file_path.exists():
            self.logger.info(f"Существующий файл не найден по пути {file_path}. Начинаем заново.")
            return 0
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as csvfile:
                content = await csvfile.read()
                reader = csv.DictReader(content.splitlines())
                for row in reader:
                    company_name = row.get('company_name', '').strip()
                    if company_name:
                        # Использование имени компании как уникального идентификатора
                        self.existing_companies.add(company_name.lower())
            
            count = len(self.existing_companies)
            self.logger.info(f"Загружено {count} существующих компаний из {file_path}")
            return count
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки существующих компаний из {file_path}: {e}")
            return 0
    
    def is_company_already_scraped(self, company_name: str) -> bool:
        """
        Проверка, была ли компания уже обработана
        
        Args:
            company_name: Имя компании для проверки
            
        Returns:
            True если компания уже существует, False в противном случае
        """
        return company_name.lower().strip() in self.existing_companies
    
    def add_company_to_existing(self, company_name: str):
        """
        Добавление компании в набор существующих компаний
        
        Args:
            company_name: Имя компании для добавления
        """
        if company_name and company_name.strip():
            self.existing_companies.add(company_name.lower().strip())
    
    async def get_company_slugs_from_page(self, page_number: int) -> List[Dict[str, str]]:
        """
        ШАГ 1: Получение всей информации о компаниях со страницы списка
        
        Args:
            page_number: Номер страницы для обработки
            
        Returns:
            Список словарей, содержащих slug компании и информацию о стенде
        """
        url = self.list_url_template.format(page=page_number)
        self.logger.info(f"Получение страницы {page_number}: {url}")
        
        try:
            response = await self.make_request_with_retry(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response, 'html.parser')
            
            # Поиск всех блоков компаний с использованием основного контейнера
            companies_info = []
            # Сначала найдем все основные контейнеры компаний
            company_containers = soup.find_all('li', class_='m-exhibitors-list__items__item')

            for container in company_containers:
                if isinstance(container, Tag):
                    # Поиск ссылки внутри этого контейнера
                    link = container.find('a', class_='js-librarylink-entry')
                    if link and isinstance(link, Tag):
                        href = link.get('href', '') or ''
                        # Извлечение slug из href типа "javascript:openRemoteModal('exhibitors-list/wind-river','ajax'..."
                        if isinstance(href, str):
                            match = re.search(r"'exhibitors-list/([^']+)'", href)
                            if match:
                                slug = match.group(1)
                                
                                # Поиск информации о стенде в том же контейнере
                                stand = ""
                                stand_element = container.find('div', class_='m-exhibitors-list__items__item__header__meta__stand')
                                if stand_element:
                                    stand_text = stand_element.get_text(strip=True)
                                    # Извлечение только номера стенда (удаление префикса "Stand: ")
                                    if stand_text.startswith('Stand:'):
                                        stand = stand_text.replace('Stand:', '').strip()
                                    else:
                                        stand = stand_text
                                
                                companies_info.append({
                                    'slug': slug,
                                    'stand': stand
                                })
                                self.logger.debug(f"Найден slug компании: {slug}, стенд: {stand}")

            # Удаление дубликатов с сохранением порядка
            unique_companies = []
            seen_slugs = set()
            for company in companies_info:
                if company['slug'] not in seen_slugs:
                    unique_companies.append(company)
                    seen_slugs.add(company['slug'])

            if len(companies_info) != len(unique_companies):
                self.logger.info(f"Удалено {len(companies_info) - len(unique_companies)} дублирующихся slugs на странице {page_number}")

            self.logger.info(f"Найдено {len(unique_companies)} уникальных компаний на странице {page_number}")
            return unique_companies
            
        except Exception as e:
            self.logger.error(f"Ошибка получения страницы {page_number}: {e}")
            return []
    
    async def get_company_details(self, company_slug: str, page_number: int, stand: str = "") -> Optional[Dict[str, str]]:
        """
        ШАГ 2: Получение подробной информации о компании с использованием slug компании
        
        Args:
            company_slug: URL slug компании
            page_number: Текущий номер страницы для API вызова
            stand: Информация о стенде со страницы списка
            
        Returns:
            Словарь с деталями компании или None если не удалось
        """
        # Проверка флага остановки
        if self.should_stop:
            self.logger.debug(f"🛑 Пропуск обработки {company_slug} - получен сигнал остановки")
            return None
            
        async with self.semaphore:  # Ограничение одновременных запросов
            url = self.company_detail_url_template.format(
                company_slug=quote(company_slug), 
                page=page_number
            )
            
            self.logger.debug(f"Получение деталей компании: {url}")
            
            try:
                response = await self.make_request_with_retry(url)
                if not response:
                    return None
                
                soup = BeautifulSoup(response, 'html.parser')
                
                # Извлечение имени компании с использованием селектора из конфигурации
                company_name = ""
                title_selector = self.selectors.get('company_title', 'h1.m-exhibitor-entry__item__header__title')
                title_element = soup.select_one(title_selector)
                if title_element:
                    company_name = title_element.get_text(strip=True)
                
                # Проверка, существует ли компания уже - пропускаем если да
                if company_name and self.is_company_already_scraped(company_name):
                    self.logger.info(f"⏭️  Пропуск {company_name} - уже существует в выходном файле")
                    return None
                
                # Извлечение тегов/категорий с использованием селектора из конфигурации
                tags = []
                category_selector = self.selectors.get('categories', 'li.m-exhibitor-entry__item__header__categories__item')
                category_elements = soup.select(category_selector)
                for cat_elem in category_elements:
                    tag = cat_elem.get_text(strip=True)
                    if tag:
                        tags.append(tag)
                
                # Извлечение обзора/описания с использованием селектора из конфигурации
                overview = ""
                desc_selector = self.selectors.get('description', 'div.m-exhibitor-entry__item__body__description')
                description_element = soup.select_one(desc_selector)
                if description_element:
                    overview = description_element.get_text(strip=True)
                
                # Извлечение URL сайта
                website = ""
                website_elements = soup.find_all('a', href=True)
                for link in website_elements:
                    if isinstance(link, Tag):
                        href = link.get('href', '') or ''
                        # Поиск внешних URL (не внутренних ссылок сайта)
                        if isinstance(href, str) and href.startswith('http') and 'dsei.co.uk' not in href:
                            website = href
                            break
                
                # Генерация полного URL компании
                company_url = self.company_detail_url_template.format(
                    company_slug=quote(company_slug), 
                    page=page_number
                )
                
                company_data = {
                    'company_name': company_name,
                    'slug_name': company_slug,
                    'url': company_url,
                    'stand': stand,
                    'tags': '; '.join(tags),  # Объединение тегов точкой с запятой
                    'overview': overview.replace('\n', ' ').replace('\r', ' '),  # Очистка переносов строк
                    'website': website
                }
                
                self.logger.debug(f"Извлечены данные для {company_name}")
                return company_data
                
            except Exception as e:
                self.logger.error(f"Ошибка получения деталей для {company_slug}: {e}")
                return None
    
    async def has_next_page(self, page_number: int) -> bool:
        """
        Проверка наличия дополнительных страниц для обработки
        
        Args:
            page_number: Текущий номер страницы
            
        Returns:
            True если есть еще страницы, False в противном случае
        """
        url = self.list_url_template.format(page=page_number + 1)
        
        try:
            response = await self.make_request_with_retry(url)
            if not response:
                return False
            
            soup = BeautifulSoup(response, 'html.parser')
            
            # Проверка наличия ссылок на компании на следующей странице
            company_links = soup.find_all('a', class_='js-librarylink-entry')
            
            return len(company_links) > 0
            
        except Exception:
            return False
    
    async def save_to_csv(self, filename: Optional[str] = None):
        """
        Сохранение собранных данных в CSV файл
        
        Args:
            filename: Имя выходного CSV файла. Если None, использует значение по умолчанию из конфигурации.
        """
        if not self.companies_data:
            self.logger.warning("Нет данных для сохранения")
            return
        
        if filename is None:
            # Сохранение в каталог data/processed
            data_dir = self.project_root / "data" / "processed"
            data_dir.mkdir(parents=True, exist_ok=True)
            file_path = data_dir / self.config.get_output_config().get('csv_filename', 'dsei_companies.csv')
        else:
            file_path = Path(filename)
        
        try:
            # Проверка существования файла для определения необходимости записи заголовка
            file_exists = file_path.exists() and file_path.stat().st_size > 0
            
            # Открытие в режиме добавления если файл существует, режиме записи если новый
            mode = 'a' if file_exists else 'w'
            
            async with aiofiles.open(file_path, mode, encoding='utf-8', newline='') as csvfile:
                fieldnames = ['company_name', 'slug_name', 'url', 'stand', 'tags', 'overview', 'website']
                
                # Создание CSV контента в памяти
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                # Запись заголовка только если файл новый/пустой
                if not file_exists:
                    writer.writeheader()
                
                for company in self.companies_data:
                    writer.writerow(company)
                
                # Запись в файл
                await csvfile.write(output.getvalue())
            
            action = "Добавлено" if file_exists else "Сохранено"
            self.logger.info(f"{action} {len(self.companies_data)} компаний в {file_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения в CSV: {e}")
    
    async def auto_save_progress(self):
        """
        Автоматическое сохранение прогресса для защиты от потери данных
        """
        if self.companies_data:
            # Создание резервного файла с временной меткой
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = self.project_root / "data" / "processed"
            data_dir.mkdir(parents=True, exist_ok=True)
            backup_filename = f"dsei_companies_backup_{timestamp}.csv"
            backup_path = data_dir / backup_filename
            
            try:
                await self.save_to_csv(str(backup_path))
                self.logger.info(f"💾 Автосохранение выполнено: {backup_path}")
            except Exception as e:
                self.logger.error(f"❌ Ошибка автосохранения: {e}")
    
    async def process_companies_batch(self, companies_info: List[Dict[str, str]], page_number: int) -> List[Dict[str, str]]:
        """
        Асинхронная обработка пакета компаний
        
        Args:
            companies_info: Список информации о компаниях (slug и stand)
            page_number: Номер текущей страницы
            
        Returns:
            Список успешно обработанных компаний
        """
        # Фильтрация уже обработанных slugs
        companies_to_process = [
            company for company in companies_info 
            if company['slug'] not in self.processed_slugs
        ]
        
        if len(companies_to_process) < len(companies_info):
            skipped = len(companies_info) - len(companies_to_process)
            self.logger.info(f"⏭️  Пропуск {skipped} slugs - уже обработаны в текущей сессии")
        
        # Создание задач для асинхронной обработки
        tasks = []
        for company_info in companies_to_process:
            # Проверка флага остановки
            if self.should_stop:
                self.logger.info("🛑 Получен сигнал остановки во время создания задач...")
                break
                
            slug = company_info['slug']
            stand = company_info['stand']
            
            # Отметка slug как обработанного
            self.processed_slugs.add(slug)
            
            # Создание задачи с небольшой задержкой между запросами
            task = self.get_company_details(slug, page_number, stand)
            tasks.append(task)
        
        # Выполнение всех задач одновременно с ограничением семафора
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтрация успешных результатов
        successful_companies = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                successful_companies.append(result)
                # Добавление в набор существующих компаний для предотвращения повторной обработки
                self.add_company_to_existing(result['company_name'])
                self.logger.info(f"✅ Обработано: {result['company_name']}")
            elif isinstance(result, Exception):
                slug = companies_to_process[i]['slug']
                self.logger.error(f"❌ Ошибка обработки {slug}: {result}")
            else:
                # result is None - может быть дубликат
                slug = companies_to_process[i]['slug']
                self.logger.debug(f"⏭️  Нет данных для {slug} (возможно, дубликат)")
        
        return successful_companies
    
    async def scrape_all_companies(self, start_page: int = 1, max_pages: Optional[int] = None):
        """
        Основной метод скрапинга, который следует логике блок-схемы
        
        Args:
            start_page: Номер страницы для начала
            max_pages: Максимальное количество страниц для обработки (None для всех)
        """
        self.logger.info(f"🚀 Запуск асинхронного DSEI скрапера компаний (макс. {self.max_concurrent_tasks} одновременных задач)")
        
        # Создание HTTP сессии
        await self._create_session()
        
        try:
            # Загрузка существующих компаний для избежания дубликатов
            await self.load_existing_companies()
            
            current_page = start_page
            pages_scraped = 0
            
            while True:
                # Проверка флага остановки
                if self.should_stop:
                    self.logger.info("🛑 Получен сигнал остановки. Завершение текущей обработки...")
                    break
                
                # Проверка ограничения максимального количества страниц
                if max_pages and pages_scraped >= max_pages:
                    self.logger.info(f"🏁 Достигнуто ограничение максимального количества страниц: {max_pages}")
                    break
                
                # ШАГ 1: Получение slugs компаний с текущей страницы
                companies_info = await self.get_company_slugs_from_page(current_page)
                
                # Проверка наличия компаний на странице (точка принятия решения в блок-схеме)
                if not companies_info:
                    self.logger.info(f"🏁 Компании не найдены на странице {current_page}. Парсинг завершен.")
                    break
                
                # Проверка флага остановки перед обработкой
                if self.should_stop:
                    self.logger.info("🛑 Получен сигнал остановки перед обработкой компаний...")
                    break
                
                # ШАГ 2: Асинхронная обработка каждой компании
                self.logger.info(f"⚡ Начинается асинхронная обработка {len(companies_info)} компаний со страницы {current_page}")
                
                batch_results = await self.process_companies_batch(companies_info, current_page)
                
                # Добавление результатов к общим данным
                self.companies_data.extend(batch_results)
                
                self.logger.info(f"✅ Завершена обработка страницы {current_page}: {len(batch_results)} новых компаний")
                
                # Автосохранение после каждой страницы (каждые 5 страниц)
                if pages_scraped % 5 == 0 and self.companies_data:
                    await self.auto_save_progress()
                
                # Проверка наличия следующей страницы (точка принятия решения в блок-схеме)
                if not await self.has_next_page(current_page):
                    self.logger.info("🏁 Больше страниц не найдено. Парсинг завершен.")
                    break
                
                # Переход к следующей странице
                current_page += 1
                pages_scraped += 1
                
                # Добавление задержки между страницами
                if self.delays.get('between_pages', 0) > 0:
                    await asyncio.sleep(self.delays.get('between_pages', 2))
            
            # Финальный отчет
            self.logger.info(f"🎉 Скрапинг завершен. Всего собрано компаний: {len(self.companies_data)}")
            self.logger.info(f"📄 Обработано страниц: {pages_scraped + 1}")
            
            # Сохранение данных в CSV
            await self.save_to_csv()
            
        except KeyboardInterrupt:
            self.logger.info("⏹️ Скрапинг прерван пользователем (Ctrl+C)")
            if self.companies_data:
                self.logger.info(f"💾 Сохранение {len(self.companies_data)} компаний, собранных до сих пор...")
                await self.save_to_csv()
                await self.auto_save_progress()  # Дополнительное резервное сохранение
        
        except Exception as e:
            self.logger.error(f"💥 Неожиданная ошибка: {e}")
            if self.companies_data:
                self.logger.info(f"💾 Сохранение {len(self.companies_data)} компаний, собранных до ошибки...")
                await self.save_to_csv()
                await self.auto_save_progress()  # Дополнительное резервное сохранение
        
        finally:
            # Закрытие HTTP сессии
            await self._close_session()


# Функция-обертка для удобного запуска асинхронного скрапера
async def run_async_scraper(config: Optional[Config] = None, 
                           start_page: int = 1, 
                           max_pages: Optional[int] = None,
                           max_concurrent_tasks: int = 15):
    """
    Функция-обертка для запуска асинхронного скрапера
    
    Args:
        config: Объект конфигурации
        start_page: Начальная страница
        max_pages: Максимальное количество страниц
        max_concurrent_tasks: Максимальное количество одновременных задач
    """
    scraper = AsyncDSEICompanyScraper(config, max_concurrent_tasks)
    await scraper.scrape_all_companies(start_page, max_pages)

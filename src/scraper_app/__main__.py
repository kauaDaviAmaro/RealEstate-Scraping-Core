"""
Main entry point for the Elite Web Scraping application
"""
import argparse
import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import List

from src.scraper_app.config import Config
from src.scraper_app.core.proxy_manager import ProxyManager, ProxyType
from src.scraper_app.pipelines.data_pipeline import DataPipeline

# Configure logging - prevent duplicates
root_logger = logging.getLogger()

# Remove all existing handlers to prevent duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
    try:
        handler.close()
    except Exception:
        pass

# Create a single handler
if Config.LOG_FILE:
    handler = logging.FileHandler(Config.LOG_FILE)
else:
    handler = logging.StreamHandler(sys.stdout)

# Configure formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Configure logging with force=True to replace any existing configuration
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[handler],
    force=True  # Python 3.8+: force reconfiguration
)

logger = logging.getLogger(__name__)

# Default search URL
DEFAULT_SEARCH_URL = "https://www.zapimoveis.com.br/venda/"


def discover_search_urls() -> List[str]:
    """
    Returns default Zap Imóveis search URLs
    The system automatically extracts ALL listings from all pages
    """
    logger.info("Using default Zap Imóveis search URLs...")
    
    base_search_urls = [
        DEFAULT_SEARCH_URL,
    ]
    
    return base_search_urls


def get_missing_deep_search_urls(csv_path: Path) -> List[str]:
    """
    Reads the CSV file and returns URLs that are missing deep search data
    
    Args:
        csv_path: Path to the scraped_data.csv file
        
    Returns:
        List of URLs that need deep search
    """
    if not csv_path.exists():
        logger.warning(f"CSV file not found: {csv_path}")
        return []
    
    missing_urls = []
    
    # Fields that indicate deep search was completed
    deep_search_indicators = [
        'full_address',
        'full_description',
        'advertiser_name',
        'advertiser_code',
        'zap_code',
        'phone_partial',
        'has_whatsapp',
        'iptu',
        'condo_fee',
        'suites',
        'floor_level'
    ]
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                url = row.get('url', '').strip()
                if not url:
                    continue
                
                # Check if deep search data is missing
                # A row is considered to need deep search if:
                # Most deep search fields are empty (less than 2 indicators filled)
                filled_indicators = 0
                
                for indicator in deep_search_indicators:
                    value = row.get(indicator, '').strip()
                    if value and value.lower() not in ['', 'none', 'null', 'false']:
                        filled_indicators += 1
                
                # If less than 2 indicators are filled, consider it missing deep search
                if filled_indicators < 2:
                    missing_urls.append(url)
                    logger.debug(f"URL needs deep search: {url} (filled indicators: {filled_indicators})")
        
        logger.info(f"Found {len(missing_urls)} URLs that need deep search from {csv_path}")
        return missing_urls
        
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_path}: {e}")
        return []


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Elite Web Scraping Application",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--deep-search-only",
        "--deep-only",
        action="store_true",
        dest="deep_search_only",
        help="Execute only deep search on listing URLs (skip search page scraping)"
    )
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_arguments()
    
    logger.info("Starting Elite Web Scraping Application")
    logger.info(f"Configuration: {Config.to_dict()}")
    
    if args.deep_search_only:
        logger.info("Mode: Deep Search Only - Reading URLs from scraped_data.csv")
        
        # Read URLs from CSV that need deep search
        csv_path = Path(Config.OUTPUT_DIR) / "scraped_data.csv"
        urls = get_missing_deep_search_urls(csv_path)
        
        if not urls:
            logger.warning("No URLs found in CSV that need deep search.")
            logger.info("Falling back to discover_search_urls()...")
            urls = discover_search_urls()
            if not urls:
                logger.warning("No URLs provided for deep search. Using default URLs.")
                urls = [
                    DEFAULT_SEARCH_URL,
                ]
        else:
            logger.info(f"Found {len(urls)} URLs from CSV that need deep search")
    else:
        urls = discover_search_urls()
        if not urls:
            logger.warning("No search URLs discovered. Using default URLs.")
            urls = [
                DEFAULT_SEARCH_URL,
            ]
        logger.info(f"Automatically searching in {len(urls)} search URL(s)")
        logger.info("The system will automatically extract ALL listings from all pages")
    
    # Initialize proxy manager if enabled
    proxy_manager = None
    if Config.PROXY_ENABLED:
        proxy_manager = ProxyManager(
            rotation_strategy=Config.PROXY_ROTATION_STRATEGY,
            max_failures=Config.PROXY_MAX_FAILURES,
            cooldown_seconds=Config.PROXY_COOLDOWN_SECONDS
        )
        
        # Load proxies from config
        proxies = Config.get_all_proxies()
        if proxies:
            proxy_manager.load_proxies_from_config(proxies)
            logger.info(f"Loaded {len(proxies)} proxies")
        else:
            logger.warning("PROXY_ENABLED is True but no proxies configured")
            logger.info("Continuing without proxy rotation")
    else:
        logger.info("Running without proxies (direct connection)")
    
    # Create pipeline
    pipeline = DataPipeline(
        urls=urls,
        proxy_manager=proxy_manager,
        deep_search_only=args.deep_search_only
    )
    
    # Run pipeline
    try:
        await pipeline.run()
        logger.info("Pipeline completed successfully")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


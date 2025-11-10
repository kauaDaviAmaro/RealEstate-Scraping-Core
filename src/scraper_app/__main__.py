"""
Main entry point for the Elite Web Scraping application
"""
import asyncio
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


def discover_search_urls() -> List[str]:
    """
    Returns default Zap Imóveis search URLs
    The system automatically extracts ALL listings from all pages
    """
    logger.info("Using default Zap Imóveis search URLs...")
    
    base_search_urls = [
        "https://www.zapimoveis.com.br/venda/",
    ]
    
    return base_search_urls


async def main():
    """Main entry point"""
    logger.info("Starting Elite Web Scraping Application")
    logger.info(f"Configuration: {Config.to_dict()}")
    
    urls = discover_search_urls()
    
    if not urls:
        logger.warning("No search URLs discovered. Using default URLs.")
        urls = [
            "https://www.zapimoveis.com.br/venda/",
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
        proxy_manager=proxy_manager
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


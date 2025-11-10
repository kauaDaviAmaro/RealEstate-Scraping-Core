"""
End-to-end system tests - Full pipeline execution with mocked browser, integration scenarios
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from src.scraper_app.pipelines.data_pipeline import DataPipeline
from src.scraper_app.core.browser_manager import BrowserManager
from src.scraper_app.core.proxy_manager import ProxyManager
from src.scraper_app.core.compliance_manager import ComplianceManager
from src.scraper_app.services.zap_imoveis_service import ZapImoveisService
from src.scraper_app.config import Config


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
class TestSystemE2E:
    """End-to-end system tests"""
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_full_pipeline_search_url(self, mock_config, mock_service_class, mock_browser_manager_class, temp_output_dir):
        """Test full pipeline execution with search URL"""
        mock_config.HEADLESS = True
        mock_config.MAX_PAGES = 1
        mock_config.SAVE_IMAGES = False
        mock_config.MAX_RETRIES = 1
        mock_config.MAX_CONCURRENT = 2
        mock_config.RESPECT_ROBOTS_TXT = False
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_listings = [
            {"url": "https://example.com/listing1", "price": 100000},
            {"url": "https://example.com/listing2", "price": 200000}
        ]
        mock_service.scrape_search_results = AsyncMock(return_value=mock_listings)
        mock_service.deep_scrape_listings = AsyncMock(return_value=mock_listings)
        mock_service_class.return_value = mock_service
        
        # Create pipeline
        pipeline = DataPipeline(
            urls=["https://example.com/venda/"],
            output_dir=str(temp_output_dir)
        )
        
        # Mock compliance checks
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                    results = await pipeline.process_urls()
        
        assert len(results) == 1
        assert results[0]["type"] == "search_results"
        assert len(results[0]["listings"]) == 2
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_full_pipeline_listing_url(self, mock_config, mock_service_class, mock_browser_manager_class, temp_output_dir):
        """Test full pipeline execution with listing URL"""
        mock_config.HEADLESS = True
        mock_config.MAX_RETRIES = 1
        mock_config.MAX_CONCURRENT = 2
        mock_config.RESPECT_ROBOTS_TXT = False
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_listing = AsyncMock(return_value={
            "url": "https://example.com/listing",
            "price": 100000,
            "title": "Test Listing"
        })
        mock_service_class.return_value = mock_service
        
        # Create pipeline
        pipeline = DataPipeline(
            urls=["https://example.com/listing"],
            output_dir=str(temp_output_dir)
        )
        
        # Mock compliance checks
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                    results = await pipeline.process_urls()
        
        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/listing"
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_pipeline_with_proxy_rotation(self, mock_config, mock_service_class, mock_browser_manager_class, temp_output_dir):
        """Test pipeline with proxy rotation"""
        mock_config.HEADLESS = True
        mock_config.PROXY_ENABLED = True
        mock_config.MAX_RETRIES = 1
        mock_config.MAX_CONCURRENT = 2
        mock_config.RESPECT_ROBOTS_TXT = False
        
        # Create proxy manager
        proxy_manager = ProxyManager()
        proxy_manager.add_proxy("127.0.0.1", 8080)
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager.mark_proxy_failure = AsyncMock()
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_listing = AsyncMock(return_value={"url": "https://example.com/listing"})
        mock_service_class.return_value = mock_service
        
        # Create pipeline with proxy manager
        pipeline = DataPipeline(
            urls=["https://example.com/listing"],
            output_dir=str(temp_output_dir),
            proxy_manager=proxy_manager
        )
        
        # Mock compliance checks
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                    results = await pipeline.process_urls()
        
        assert len(results) == 1
        mock_browser_manager.mark_proxy_success.assert_called()
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_pipeline_error_handling(self, mock_config, mock_service_class, mock_browser_manager_class, temp_output_dir):
        """Test pipeline error handling and retries"""
        mock_config.HEADLESS = True
        mock_config.MAX_RETRIES = 2
        mock_config.MAX_CONCURRENT = 2
        mock_config.RESPECT_ROBOTS_TXT = False
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_listing = AsyncMock(side_effect=[
            Exception("Network error"),
            {"url": "https://example.com/listing", "price": 100000}
        ])
        mock_service_class.return_value = mock_service
        
        # Create pipeline
        pipeline = DataPipeline(
            urls=["https://example.com/listing"],
            output_dir=str(temp_output_dir)
        )
        
        # Mock _process_scrape_attempt to control retry behavior
        # max_retries=2 means 3 attempts (0, 1, 2)
        attempt_count = [0]
        async def mock_process_scrape_attempt(url, browser_manager, attempt, max_retries):
            attempt_count[0] += 1
            if attempt_count[0] <= 2:  # First two attempts fail
                # Return None to trigger retry (not raise exception, as that's handled differently)
                return None
            else:
                # Third attempt succeeds
                return {"url": "https://example.com/listing", "price": 100000}
        
        # Mock compliance checks and retry delay
        with patch.object(pipeline, '_process_scrape_attempt', side_effect=mock_process_scrape_attempt):
            with patch.object(pipeline, '_calculate_retry_delay', return_value=0.0):  # No delay for faster test
                with patch('asyncio.sleep', return_value=None):  # Mock asyncio.sleep
                    with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
                        with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                            with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                                results = await pipeline.process_urls()
        
        # Should eventually succeed after retry
        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/listing"
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_pipeline_concurrency(self, mock_config, mock_service_class, mock_browser_manager_class, temp_output_dir):
        """Test pipeline concurrency control"""
        mock_config.HEADLESS = True
        mock_config.MAX_RETRIES = 1
        mock_config.MAX_CONCURRENT = 2
        mock_config.RESPECT_ROBOTS_TXT = False
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_listing = AsyncMock(return_value={"url": "test"})
        mock_service_class.return_value = mock_service
        
        # Create pipeline with limited concurrency
        pipeline = DataPipeline(
            urls=[
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3"
            ],
            output_dir=str(temp_output_dir),
            max_concurrent=2
        )
        
        # Mock compliance checks
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                    results = await pipeline.process_urls()
        
        # Should process all URLs
        assert len(results) == 3
        assert pipeline.stats["total"] == 3
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_pipeline_csv_output(self, mock_config, mock_service_class, mock_browser_manager_class, temp_output_dir):
        """Test pipeline CSV output generation"""
        mock_config.HEADLESS = True
        mock_config.MAX_RETRIES = 1
        mock_config.MAX_CONCURRENT = 2
        mock_config.RESPECT_ROBOTS_TXT = False
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_listing = AsyncMock(return_value={
            "url": "https://example.com/listing",
            "price": 100000,
            "title": "Test Listing",
            "area": 100
        })
        mock_service_class.return_value = mock_service
        
        # Create pipeline
        pipeline = DataPipeline(
            urls=["https://example.com/listing"],
            output_dir=str(temp_output_dir)
        )
        
        # Mock compliance checks
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                    await pipeline.process_urls()
                    pipeline.save_to_csv()
        
        # Check CSV file
        csv_file = temp_output_dir / "scraped_data.csv"
        assert csv_file.exists()
        
        # Read and verify
        import csv
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["url"] == "https://example.com/listing"
            assert rows[0]["price"] == "100000"


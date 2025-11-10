"""
Tests for DataPipeline - URL processing, concurrency control, CSV saving, image downloads
"""
import pytest
import asyncio
import csv
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from src.scraper_app.pipelines.data_pipeline import DataPipeline
from src.scraper_app.core.proxy_manager import ProxyManager
from src.scraper_app.core.compliance_manager import ComplianceManager
from src.scraper_app.core.human_behavior import HumanBehavior
from src.scraper_app.core.browser_manager import BrowserManager
from src.scraper_app.services.zap_imoveis_service import ZapImoveisService
from src.scraper_app.config import Config


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
class TestDataPipelineInitialization:
    """Tests for DataPipeline initialization"""
    
    def test_init_with_defaults(self):
        """Test initialization with defaults"""
        pipeline = DataPipeline(urls=["https://example.com"])
        
        assert pipeline.urls == ["https://example.com"]
        assert pipeline.max_concurrent == Config.MAX_CONCURRENT
        assert pipeline.results == []
        assert isinstance(pipeline.compliance_manager, ComplianceManager)
        assert isinstance(pipeline.human_behavior, HumanBehavior)
    
    def test_init_with_custom_params(self, temp_output_dir):
        """Test initialization with custom parameters"""
        proxy_manager = ProxyManager()
        compliance_manager = ComplianceManager()
        human_behavior = HumanBehavior()
        
        pipeline = DataPipeline(
            urls=["https://example.com"],
            output_dir=str(temp_output_dir),
            max_concurrent=5,
            proxy_manager=proxy_manager,
            compliance_manager=compliance_manager,
            human_behavior=human_behavior
        )
        
        assert pipeline.output_dir == temp_output_dir
        assert pipeline.max_concurrent == 5
        assert pipeline.proxy_manager == proxy_manager
        assert pipeline.compliance_manager == compliance_manager
        assert pipeline.human_behavior == human_behavior


@pytest.mark.asyncio
class TestDataPipelineCompliance:
    """Tests for compliance checking"""
    
    async def test_check_compliance_public_data(self):
        """Test compliance check for public data"""
        pipeline = DataPipeline(urls=[])
        
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=True):
                with patch.object(pipeline.compliance_manager, 'wait_for_rate_limit', return_value=None):
                    result = await pipeline._check_compliance("https://example.com/listings")
                    assert result is True
    
    async def test_check_compliance_private_data(self):
        """Test compliance check for private data"""
        pipeline = DataPipeline(urls=[])
        
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=False):
            result = await pipeline._check_compliance("https://example.com/login")
            assert result is False
            assert pipeline.stats["skipped"] == 1
    
    async def test_check_compliance_robots_disallows(self):
        """Test compliance check when robots.txt disallows"""
        pipeline = DataPipeline(urls=[])
        
        with patch.object(pipeline.compliance_manager, 'is_public_data', return_value=True):
            with patch.object(pipeline.compliance_manager, 'can_fetch', return_value=False):
                result = await pipeline._check_compliance("https://example.com/page")
                assert result is False
                assert pipeline.stats["skipped"] == 1


@pytest.mark.asyncio
class TestDataPipelineURLProcessing:
    """Tests for URL processing"""
    
    def test_is_search_url(self):
        """Test search URL detection"""
        pipeline = DataPipeline(urls=[])
        
        assert pipeline._is_search_url("https://example.com/venda/") is True
        assert pipeline._is_search_url("https://example.com/imovel/123") is False
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_attempt_scrape_search_url(self, mock_config, mock_service_class, mock_browser_manager_class):
        """Test scraping a search URL"""
        mock_config.MAX_PAGES = None
        mock_config.SAVE_IMAGES = False
        
        pipeline = DataPipeline(urls=[])
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_search_results = AsyncMock(return_value=[{"url": "test"}])
        mock_service.deep_scrape_listings = AsyncMock(return_value=[{"url": "test"}])
        mock_service_class.return_value = mock_service
        
        result = await pipeline._attempt_scrape("https://example.com/venda/", mock_browser_manager)
        
        assert result is not None
        assert result["type"] == "search_results"
        mock_service.scrape_search_results.assert_called_once()
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.ZapImoveisService')
    async def test_attempt_scrape_listing_url(self, mock_service_class, mock_browser_manager_class):
        """Test scraping a listing URL"""
        pipeline = DataPipeline(urls=[])
        
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.initialize = AsyncMock()
        mock_browser_manager.create_page = AsyncMock(return_value=AsyncMock())
        mock_browser_manager.mark_proxy_success = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.scrape_listing = AsyncMock(return_value={"url": "https://example.com/listing"})
        mock_service_class.return_value = mock_service
        
        result = await pipeline._attempt_scrape("https://example.com/listing", mock_browser_manager)
        
        assert result is not None
        assert "url" in result
        mock_service.scrape_listing.assert_called_once()


@pytest.mark.asyncio
class TestDataPipelineErrorHandling:
    """Tests for error handling"""
    
    def test_is_blocked_error(self):
        """Test blocked error detection"""
        pipeline = DataPipeline(urls=[])
        
        assert pipeline._is_blocked_error({"error": "403 Forbidden"}) is True
        assert pipeline._is_blocked_error({"error": "429 Too Many Requests"}) is True
        assert pipeline._is_blocked_error({"error": "500 Internal Server Error"}) is False
    
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    async def test_handle_blocked_error(self, mock_browser_manager_class):
        """Test handling blocked error"""
        pipeline = DataPipeline(urls=[])
        
        mock_browser_manager = AsyncMock()
        mock_browser_manager.mark_proxy_failure = AsyncMock()
        mock_browser_manager.rotate_fingerprint = Mock(return_value=Mock())  # Synchronous method
        mock_browser_manager_class.return_value = mock_browser_manager
        
        await pipeline._handle_blocked_error(
            "https://example.com/page",
            {"error": "403 Forbidden"},
            mock_browser_manager
        )
        
        assert pipeline.stats["blocked"] == 1
        mock_browser_manager.mark_proxy_failure.assert_called_once()
        mock_browser_manager.rotate_fingerprint.assert_called_once()
    
    def test_handle_successful_result(self):
        """Test handling successful result"""
        pipeline = DataPipeline(urls=[])
        
        result = pipeline._handle_successful_result(
            {"url": "https://example.com/listing"},
            "https://example.com/listing"
        )
        
        assert pipeline.stats["success"] == 1
        assert result["url"] == "https://example.com/listing"
    
    def test_handle_successful_result_search(self):
        """Test handling successful search result"""
        pipeline = DataPipeline(urls=[])
        
        result = {
            "type": "search_results",
            "listings": [{"url": "1"}, {"url": "2"}]
        }
        
        pipeline._handle_successful_result(result, "https://example.com/search")
        
        assert pipeline.stats["success"] == 2  # Count of listings


@pytest.mark.asyncio
class TestDataPipelineCSVSaving:
    """Tests for CSV saving"""
    
    def test_convert_result_to_row(self):
        """Test converting result to CSV row"""
        pipeline = DataPipeline(urls=[])
        
        result = {
            "url": "https://example.com",
            "price": 100000,
            "images": ["img1.jpg", "img2.jpg"],
            "metadata": {"key": "value"}
        }
        
        row = pipeline._convert_result_to_row(result)
        
        assert row["url"] == "https://example.com"
        assert row["price"] == 100000
        assert isinstance(row["images"], str)  # List converted to string
        assert isinstance(row["metadata"], str)  # Dict converted to string
    
    def test_is_valid_fieldname(self):
        """Test fieldname validation"""
        pipeline = DataPipeline(urls=[])
        
        assert pipeline._is_valid_fieldname("url") is True
        assert pipeline._is_valid_fieldname("price") is True
        assert pipeline._is_valid_fieldname("column_42") is False
        assert pipeline._is_valid_fieldname("") is False
        assert pipeline._is_valid_fieldname(None) is False
    
    async def test_save_single_listing_to_csv(self, temp_output_dir):
        """Test saving single listing to CSV"""
        pipeline = DataPipeline(urls=[], output_dir=str(temp_output_dir))
        
        listing = {
            "url": "https://example.com/listing",
            "price": 100000,
            "title": "Test Listing"
        }
        
        await pipeline.save_single_listing_to_csv(listing, "https://example.com")
        
        csv_file = temp_output_dir / "scraped_data.csv"
        assert csv_file.exists()
        
        # Read and verify
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["url"] == "https://example.com/listing"
            assert rows[0]["price"] == "100000"
    
    async def test_save_page_to_csv(self, temp_output_dir):
        """Test saving page of listings to CSV"""
        pipeline = DataPipeline(urls=[], output_dir=str(temp_output_dir))
        
        listings = [
            {"url": "https://example.com/1", "price": 100000},
            {"url": "https://example.com/2", "price": 200000}
        ]
        
        await pipeline.save_page_to_csv(1, listings, "https://example.com")
        
        csv_file = temp_output_dir / "scraped_data.csv"
        assert csv_file.exists()
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2


@pytest.mark.asyncio
class TestDataPipelineImageDownload:
    """Tests for image downloading"""
    
    def test_get_image_extension(self):
        """Test image extension extraction"""
        pipeline = DataPipeline(urls=[])
        
        assert pipeline._get_image_extension("image.jpg") == "jpg"
        assert pipeline._get_image_extension("image.png?param=value") == "png"
        assert pipeline._get_image_extension("image.webp") == "webp"
        assert pipeline._get_image_extension("image.unknown") == "jpg"  # Default
    
    def test_get_listing_id_from_url(self):
        """Test listing ID extraction from URL"""
        pipeline = DataPipeline(urls=[])
        
        assert pipeline._get_listing_id_from_url("https://example.com/imovel/id-123456/") == "listing_123456"
        assert pipeline._get_listing_id_from_url("https://example.com/test/") != "unknown"
        assert pipeline._get_listing_id_from_url("") == "unknown"
    
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    @patch('src.scraper_app.pipelines.data_pipeline.aiohttp.ClientSession')
    async def test_download_listing_images_disabled(self, mock_session_class, mock_config):
        """Test image download when disabled"""
        mock_config.SAVE_IMAGES = False
        
        pipeline = DataPipeline(urls=[])
        listing = {"url": "https://example.com/listing", "images": ["img1.jpg"]}
        
        await pipeline._download_listing_images(listing)
        
        # Should not create session
        mock_session_class.assert_not_called()
    
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    @patch('src.scraper_app.pipelines.data_pipeline.aiohttp.ClientSession')
    @patch('src.scraper_app.pipelines.data_pipeline.aiofiles.open')
    async def test_download_listing_images(self, mock_aiofiles, mock_session_class, mock_config, temp_output_dir):
        """Test downloading listing images"""
        mock_config.SAVE_IMAGES = True
        
        pipeline = DataPipeline(urls=[], output_dir=str(temp_output_dir))
        
        listing = {
            "url": "https://example.com/imovel/id-123456/",
            "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        }
        
        # Mock HTTP response
        async def mock_iter_chunked(chunk_size):
            yield b"image_data"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.iter_chunked = mock_iter_chunked
        
        # Create async context manager for response
        class MockResponseContext:
            def __init__(self, response):
                self.response = response
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, *args):
                return None
        
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = Mock(return_value=MockResponseContext(mock_response))
        mock_session_class.return_value = mock_session
        
        # Mock file writing
        mock_file = AsyncMock()
        mock_file.write = AsyncMock()
        mock_file_context = AsyncMock()
        mock_file_context.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file_context.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles.return_value = mock_file_context
        
        await pipeline._download_listing_images(listing)
        
        # Should have attempted to download
        assert mock_session.get.call_count > 0
        assert "images_local" in listing


@pytest.mark.asyncio
class TestDataPipelineConcurrency:
    """Tests for concurrency control"""
    
    @patch('src.scraper_app.pipelines.data_pipeline.DataPipeline.process_single_url')
    async def test_process_urls_with_concurrency(self, mock_process_single_url):
        """Test URL processing with concurrency control"""
        mock_process_single_url.return_value = {"url": "test"}
        
        pipeline = DataPipeline(urls=["https://example.com/1", "https://example.com/2"], max_concurrent=2)
        
        results = await pipeline.process_urls()
        
        assert len(results) == 2
        assert mock_process_single_url.call_count == 2
    
    @patch('src.scraper_app.pipelines.data_pipeline.DataPipeline._check_compliance')
    @patch('src.scraper_app.pipelines.data_pipeline.DataPipeline._process_scrape_attempt')
    @patch('src.scraper_app.pipelines.data_pipeline.BrowserManager')
    @patch('src.scraper_app.pipelines.data_pipeline.Config')
    async def test_process_single_url_with_retries(self, mock_config, mock_browser_manager_class, mock_process_attempt, mock_check_compliance):
        """Test URL processing with retry logic"""
        mock_config.MAX_RETRIES = 2
        mock_config.HEADLESS = True
        
        mock_check_compliance.return_value = True
        mock_process_attempt.side_effect = [None, None, {"url": "test"}]  # Success on 3rd attempt
        
        mock_browser_manager = AsyncMock()
        mock_browser_manager.close = AsyncMock()
        mock_browser_manager_class.return_value = mock_browser_manager
        
        pipeline = DataPipeline(urls=[])
        result = await pipeline.process_single_url("https://example.com/page")
        
        assert result is not None
        assert mock_process_attempt.call_count == 3  # 3 attempts (0, 1, 2)


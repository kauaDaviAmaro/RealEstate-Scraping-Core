"""
Unit tests for ZapImoveisService using mocked Playwright
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.scraper_app.services.zap_imoveis_service import ZapImoveisService
from src.scraper_app.core.human_behavior import HumanBehavior


@pytest.mark.asyncio
class TestInitialization:
    """Tests for service initialization"""
    
    async def test_init_with_page(self, mock_page):
        """Test service initialization with page"""
        service = ZapImoveisService(mock_page)
        assert service.page == mock_page
        assert service.human_behavior is not None
        assert isinstance(service.human_behavior, HumanBehavior)
    
    async def test_init_with_custom_human_behavior(self, mock_page, mock_human_behavior):
        """Test service initialization with custom human_behavior"""
        service = ZapImoveisService(mock_page, mock_human_behavior)
        assert service.page == mock_page
        assert service.human_behavior == mock_human_behavior
    
    async def test_init_creates_default_human_behavior(self, mock_page):
        """Test that default human_behavior is created when None is provided"""
        service = ZapImoveisService(mock_page, None)
        assert service.human_behavior is not None
        assert isinstance(service.human_behavior, HumanBehavior)


@pytest.mark.asyncio
class TestPriceExtraction:
    """Tests for price extraction methods"""
    
    async def test_parse_price_text_valid_formats(self, mock_page):
        """Test parsing various price text formats"""
        service = ZapImoveisService(mock_page)
        
        # Test standard format
        assert service.extractor._parse_price_text("R$ 440.000") == 440000.0
        assert service.extractor._parse_price_text("R$ 1.500.000") == 1500000.0
        assert service.extractor._parse_price_text("R$ 20.998.000") == 20998000.0
        
        # Test with spaces
        assert service.extractor._parse_price_text("R$ 440.000") == 440000.0
        assert service.extractor._parse_price_text("R$440.000") == 440000.0
        
        # Test with comma as decimal
        assert service.extractor._parse_price_text("R$ 440.000,50") == 440000.5
    
    async def test_parse_price_text_invalid(self, mock_page):
        """Test parsing invalid price text"""
        service = ZapImoveisService(mock_page)
        
        assert service.extractor._parse_price_text("") is None
        assert service.extractor._parse_price_text("440.000") is None  # Missing R$
        assert service.extractor._parse_price_text("R$ abc") is None
        assert service.extractor._parse_price_text("R$ 5") is None  # Too low
        assert service.extractor._parse_price_text("R$ 2000000000") is None  # Too high
    
    async def test_extract_price_from_selectors_success(self, mock_page, mock_element):
        """Test price extraction from selectors"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="R$ 440.000")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        price = await service.extractor._extract_price_from_selectors()
        assert price == 440000.0
    
    async def test_extract_price_from_selectors_not_found(self, mock_page):
        """Test price extraction when selectors don't match"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        price = await service.extractor._extract_price_from_selectors()
        assert price is None
    
    async def test_extract_price_from_content_success(self, mock_page):
        """Test price extraction from page content"""
        service = ZapImoveisService(mock_page)
        mock_page.content = AsyncMock(return_value='<html><body>Price: R$ 440.000</body></html>')
        
        price = await service.extractor._extract_price_from_content()
        assert price == 440000.0
    
    async def test_extract_price_from_content_not_found(self, mock_page):
        """Test price extraction when not in content"""
        service = ZapImoveisService(mock_page)
        mock_page.content = AsyncMock(return_value='<html><body>No price here</body></html>')
        
        price = await service.extractor._extract_price_from_content()
        assert price is None
    
    async def test_extract_price_success_from_selectors(self, mock_page, mock_element):
        """Test extract_price using selectors"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="R$ 440.000")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        price = await service.extractor.extract_price()
        assert price == 440000.0
    
    async def test_extract_price_fallback_to_content(self, mock_page):
        """Test extract_price fallback to content"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value='<html><body>R$ 440.000</body></html>')
        
        price = await service.extractor.extract_price()
        assert price == 440000.0
    
    async def test_extract_price_not_found(self, mock_page):
        """Test extract_price when price is not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value='<html><body>No price</body></html>')
        
        price = await service.extractor.extract_price()
        assert price is None


@pytest.mark.asyncio
class TestTitleExtraction:
    """Tests for title extraction methods"""
    
    async def test_extract_title_from_meta_success(self, mock_page, mock_element):
        """Test title extraction from meta tag"""
        service = ZapImoveisService(mock_page)
        mock_element.get_attribute = AsyncMock(return_value="Apartamento 3 quartos, 140m²")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        title = await service.extractor._extract_title_from_meta()
        assert title == "Apartamento 3 quartos, 140m²"
    
    async def test_extract_title_from_meta_not_found(self, mock_page):
        """Test title extraction when meta tag not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        title = await service.extractor._extract_title_from_meta()
        assert title is None
    
    async def test_extract_title_from_selectors_success(self, mock_page, mock_element):
        """Test title extraction from HTML selectors"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="Apartamento 3 quartos")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        title = await service.extractor._extract_title_from_selectors()
        assert title == "Apartamento 3 quartos"
    
    async def test_extract_title_from_selectors_not_found(self, mock_page):
        """Test title extraction when selectors don't match"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        title = await service.extractor._extract_title_from_selectors()
        assert title is None
    
    async def test_extract_title_success_from_meta(self, mock_page, mock_element):
        """Test extract_title using meta tag"""
        service = ZapImoveisService(mock_page)
        mock_element.get_attribute = AsyncMock(return_value="Apartamento 3 quartos")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        title = await service.extractor.extract_title()
        assert title == "Apartamento 3 quartos"
    
    async def test_extract_title_fallback_to_selectors(self, mock_page, mock_element):
        """Test extract_title fallback to selectors"""
        service = ZapImoveisService(mock_page)
        # Meta returns None
        mock_page.query_selector = AsyncMock(side_effect=[None, mock_element])
        mock_element.text_content = AsyncMock(return_value="Apartamento 3 quartos")
        
        title = await service.extractor.extract_title()
        assert title == "Apartamento 3 quartos"
    
    async def test_extract_title_fallback_to_page_title(self, mock_page):
        """Test extract_title fallback to page title"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.title = AsyncMock(return_value="Apartamento - Imóvel")
        
        title = await service.extractor.extract_title()
        assert title == "Apartamento - Imóvel"
    
    async def test_extract_title_not_found(self, mock_page):
        """Test extract_title when title is not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.title = AsyncMock(return_value="Zap Imóveis")
        
        title = await service.extractor.extract_title()
        assert title is None


@pytest.mark.asyncio
class TestLocationExtraction:
    """Tests for location extraction"""
    
    async def test_extract_location_with_both_parts(self, mock_page, mock_element):
        """Test location extraction with both location and street"""
        service = ZapImoveisService(mock_page)
        
        # Mock location element
        location_elem = AsyncMock()
        location_elem.text_content = AsyncMock(return_value="Vila Nossa Senhora das Graças, Franca")
        
        # Mock street element
        street_elem = AsyncMock()
        street_elem.text_content = AsyncMock(return_value="Rua Osório Arantes")
        
        mock_page.query_selector = AsyncMock(side_effect=[location_elem, street_elem])
        
        location = await service.extractor.extract_location()
        assert location == "Vila Nossa Senhora das Graças, Franca, Rua Osório Arantes"
    
    async def test_extract_location_only_location(self, mock_page, mock_element):
        """Test location extraction with only location"""
        service = ZapImoveisService(mock_page)
        
        location_elem = AsyncMock()
        location_elem.text_content = AsyncMock(return_value="Vila Nossa Senhora das Graças, Franca")
        
        mock_page.query_selector = AsyncMock(side_effect=[location_elem, None])
        
        location = await service.extractor.extract_location()
        assert location == "Vila Nossa Senhora das Graças, Franca"
    
    async def test_extract_location_not_found(self, mock_page):
        """Test location extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        location = await service.extractor.extract_location()
        assert location is None


@pytest.mark.asyncio
class TestPropertyDetailsExtraction:
    """Tests for property details extraction (area, bedrooms, bathrooms, parking)"""
    
    async def test_extract_area_success(self, mock_page, mock_element):
        """Test area extraction"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="140 m²")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        area = await service.extractor.extract_area()
        assert area == 140.0
    
    async def test_extract_area_with_decimal(self, mock_page, mock_element):
        """Test area extraction with decimal"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="140.5 m²")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        area = await service.extractor.extract_area()
        assert area == 140.5
    
    async def test_extract_area_not_found(self, mock_page):
        """Test area extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        area = await service.extractor.extract_area()
        assert area is None
    
    async def test_extract_bedrooms_success(self, mock_page, mock_element):
        """Test bedrooms extraction"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="3")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        bedrooms = await service.extractor.extract_bedrooms()
        assert bedrooms == 3
    
    async def test_extract_bedrooms_not_found(self, mock_page):
        """Test bedrooms extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        bedrooms = await service.extractor.extract_bedrooms()
        assert bedrooms is None
    
    async def test_extract_bathrooms_success(self, mock_page, mock_element):
        """Test bathrooms extraction"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="2")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        bathrooms = await service.extractor.extract_bathrooms()
        assert bathrooms == 2
    
    async def test_extract_bathrooms_with_range(self, mock_page, mock_element):
        """Test bathrooms extraction with range (takes first number)"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="2-5")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        bathrooms = await service.extractor.extract_bathrooms()
        assert bathrooms == 2
    
    async def test_extract_bathrooms_not_found(self, mock_page):
        """Test bathrooms extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        bathrooms = await service.extractor.extract_bathrooms()
        assert bathrooms is None
    
    async def test_extract_parking_spaces_success(self, mock_page, mock_element):
        """Test parking spaces extraction"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="1")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        parking = await service.extractor.extract_parking_spaces()
        assert parking == 1
    
    async def test_extract_parking_spaces_with_range(self, mock_page, mock_element):
        """Test parking spaces extraction with range"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="4-5")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        parking = await service.extractor.extract_parking_spaces()
        assert parking == 4
    
    async def test_extract_parking_spaces_not_found(self, mock_page):
        """Test parking spaces extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        parking = await service.extractor.extract_parking_spaces()
        assert parking is None
    
    async def test_extract_property_type_success(self, mock_page, mock_element):
        """Test property type extraction"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="Apartamento")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        prop_type = await service.extractor.extract_property_type()
        assert prop_type == "Apartamento"
    
    async def test_extract_property_type_not_found(self, mock_page):
        """Test property type extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        prop_type = await service.extractor.extract_property_type()
        assert prop_type is None


@pytest.mark.asyncio
class TestImageExtraction:
    """Tests for image extraction methods"""
    
    async def test_normalize_image_url_absolute(self, mock_page):
        """Test URL normalization for absolute URLs"""
        service = ZapImoveisService(mock_page)
        url = "https://example.com/image.jpg"
        assert service.extractor._normalize_image_url(url) == url
    
    async def test_normalize_image_url_protocol_relative(self, mock_page):
        """Test URL normalization for protocol-relative URLs"""
        service = ZapImoveisService(mock_page)
        url = "//example.com/image.jpg"
        assert service.extractor._normalize_image_url(url) == "https://example.com/image.jpg"
    
    async def test_normalize_image_url_relative(self, mock_page):
        """Test URL normalization for relative URLs"""
        service = ZapImoveisService(mock_page)
        service.page.url = "https://www.zapimoveis.com.br/imovel/test"
        url = "/image.jpg"
        normalized = service.extractor._normalize_image_url(url)
        assert normalized == "https://www.zapimoveis.com.br/image.jpg"
    
    async def test_clean_image_url_with_dimension(self, mock_page):
        """Test URL cleaning removes dimension parameters"""
        service = ZapImoveisService(mock_page)
        url = "https://example.com/image.jpg?action=fit-in&dimension=614x297"
        cleaned = service.extractor._clean_image_url(url)
        assert cleaned == "https://example.com/image.jpg"
    
    async def test_clean_image_url_without_dimension(self, mock_page):
        """Test URL cleaning when no dimension parameter"""
        service = ZapImoveisService(mock_page)
        url = "https://example.com/image.jpg?other=param"
        cleaned = service.extractor._clean_image_url(url)
        assert cleaned == url
    
    async def test_extract_images_from_selectors_success(self, mock_page, mock_element):
        """Test image extraction from selectors"""
        service = ZapImoveisService(mock_page)
        service.page.url = "https://www.zapimoveis.com.br/imovel/test"
        
        img1 = AsyncMock()
        img1.get_attribute = AsyncMock(return_value="https://resizedimgs.zapimoveis.com.br/img1.jpg?dimension=614x297")
        img2 = AsyncMock()
        img2.get_attribute = AsyncMock(return_value="https://resizedimgs.zapimoveis.com.br/img2.jpg?dimension=614x297")
        
        mock_page.query_selector_all = AsyncMock(return_value=[img1, img2])
        
        images = await service.extractor._extract_images_from_selectors()
        assert len(images) == 2
        assert "img1.jpg" in images[0]
        assert "img2.jpg" in images[1]
        assert "dimension" not in images[0]  # Should be cleaned
    
    async def test_extract_images_from_meta_success(self, mock_page, mock_element):
        """Test image extraction from meta tags"""
        service = ZapImoveisService(mock_page)
        mock_element.get_attribute = AsyncMock(return_value="https://example.com/og-image.jpg")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        images = await service.extractor._extract_images_from_meta()
        assert len(images) == 1
        assert images[0] == "https://example.com/og-image.jpg"
    
    async def test_extract_images_from_meta_not_found(self, mock_page):
        """Test image extraction when meta tag not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        images = await service.extractor._extract_images_from_meta()
        assert images == []
    
    async def test_extract_images_success(self, mock_page, mock_element):
        """Test extract_images combining selectors and meta"""
        service = ZapImoveisService(mock_page)
        service.page.url = "https://www.zapimoveis.com.br/imovel/test"
        
        # Mock selector images
        img1 = AsyncMock()
        img1.get_attribute = AsyncMock(return_value="https://resizedimgs.zapimoveis.com.br/img1.jpg")
        mock_page.query_selector_all = AsyncMock(return_value=[img1])
        
        # Mock meta image
        meta_elem = AsyncMock()
        meta_elem.get_attribute = AsyncMock(return_value="https://example.com/og-image.jpg")
        mock_page.query_selector = AsyncMock(side_effect=[None, meta_elem])  # First call for selectors, second for meta
        
        images = await service.extractor.extract_images()
        assert len(images) >= 1
    
    async def test_extract_images_limit(self, mock_page, mock_element):
        """Test that extract_images limits to 20 images"""
        service = ZapImoveisService(mock_page)
        service.page.url = "https://www.zapimoveis.com.br/imovel/test"
        
        # Create 25 mock images
        images_list = []
        for i in range(25):
            img = AsyncMock()
            img.get_attribute = AsyncMock(return_value=f"https://example.com/img{i}.jpg")
            images_list.append(img)
        
        mock_page.query_selector_all = AsyncMock(return_value=images_list)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        images = await service.extractor.extract_images()
        assert len(images) == 20


@pytest.mark.asyncio
class TestDescriptionAndAmenitiesExtraction:
    """Tests for description and amenities extraction"""
    
    async def test_extract_description_from_meta_success(self, mock_page, mock_element):
        """Test description extraction from meta tag"""
        service = ZapImoveisService(mock_page)
        mock_element.get_attribute = AsyncMock(return_value="Apartamento espaçoso com 3 quartos")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        description = await service.extractor._extract_description_from_meta()
        assert description == "Apartamento espaçoso com 3 quartos"
    
    async def test_extract_description_from_selectors_success(self, mock_page, mock_element):
        """Test description extraction from selectors"""
        service = ZapImoveisService(mock_page)
        mock_element.text_content = AsyncMock(return_value="Apartamento espaçoso")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        description = await service.extractor._extract_description_from_selectors()
        assert description == "Apartamento espaçoso"
    
    async def test_extract_description_success(self, mock_page, mock_element):
        """Test extract_description using meta tag"""
        service = ZapImoveisService(mock_page)
        mock_element.get_attribute = AsyncMock(return_value="Apartamento espaçoso")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        description = await service.extractor.extract_description()
        assert description == "Apartamento espaçoso"
    
    async def test_extract_description_not_found(self, mock_page):
        """Test extract_description when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        description = await service.extractor.extract_description()
        assert description is None
    
    async def test_extract_amenities_success(self, mock_page, mock_element):
        """Test amenities extraction"""
        service = ZapImoveisService(mock_page)
        
        amenity1 = AsyncMock()
        amenity1.text_content = AsyncMock(return_value="Piscina")
        amenity2 = AsyncMock()
        amenity2.text_content = AsyncMock(return_value="Academia")
        
        mock_page.query_selector_all = AsyncMock(return_value=[amenity1, amenity2])
        
        amenities = await service.extractor.extract_amenities()
        assert len(amenities) == 2
        assert "Piscina" in amenities
        assert "Academia" in amenities
    
    async def test_extract_amenities_limit(self, mock_page, mock_element):
        """Test that amenities are limited to 30"""
        service = ZapImoveisService(mock_page)
        
        # Create 35 mock amenities
        amenities_list = []
        for i in range(35):
            amenity = AsyncMock()
            amenity.text_content = AsyncMock(return_value=f"Amenity {i}")
            amenities_list.append(amenity)
        
        mock_page.query_selector_all = AsyncMock(return_value=amenities_list)
        
        amenities = await service.extractor.extract_amenities()
        assert len(amenities) == 30
    
    async def test_extract_amenities_not_found(self, mock_page):
        """Test amenities extraction when not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        amenities = await service.extractor.extract_amenities()
        assert amenities == []


@pytest.mark.asyncio
class TestSearchResultsExtraction:
    """Tests for search results extraction methods"""
    
    async def test_normalize_listing_url_absolute(self, mock_page):
        """Test URL normalization for absolute URLs"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/venda-apartamento/"
        assert service.search_extractor._normalize_listing_url(url) == url
    
    async def test_normalize_listing_url_relative(self, mock_page):
        """Test URL normalization for relative URLs"""
        service = ZapImoveisService(mock_page)
        url = "/imovel/venda-apartamento/"
        normalized = service.search_extractor._normalize_listing_url(url)
        assert normalized == "https://www.zapimoveis.com.br/imovel/venda-apartamento/"
    
    async def test_normalize_listing_url_no_slash(self, mock_page):
        """Test URL normalization for URLs without leading slash"""
        service = ZapImoveisService(mock_page)
        url = "imovel/venda-apartamento/"
        normalized = service.search_extractor._normalize_listing_url(url)
        assert normalized == "https://www.zapimoveis.com.br/imovel/venda-apartamento/"
    
    async def test_clean_listing_url_with_id(self, mock_page):
        """Test URL cleaning keeping id parameter"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/test/?id=123456&source=ranking"
        cleaned = service.search_extractor._clean_listing_url(url)
        assert cleaned == "https://www.zapimoveis.com.br/imovel/test/?id=123456"
    
    async def test_clean_listing_url_without_id(self, mock_page):
        """Test URL cleaning without id parameter"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/test/?source=ranking"
        cleaned = service.search_extractor._clean_listing_url(url)
        assert cleaned == "https://www.zapimoveis.com.br/imovel/test/"
    
    async def test_clean_listing_url_no_params(self, mock_page):
        """Test URL cleaning when no query params"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/test/"
        cleaned = service.search_extractor._clean_listing_url(url)
        assert cleaned == url
    
    async def test_extract_urls_from_selector_success(self, mock_page, mock_element):
        """Test URL extraction from selector"""
        service = ZapImoveisService(mock_page)
        
        link1 = AsyncMock()
        link1.get_attribute = AsyncMock(return_value="/imovel/venda-apartamento-id-123/?id=123")
        link2 = AsyncMock()
        link2.get_attribute = AsyncMock(return_value="/imovel/venda-casa-id-456/?id=456")
        
        mock_page.query_selector_all = AsyncMock(return_value=[link1, link2])
        
        urls = await service.search_extractor._extract_urls_from_selector('a[href*="/imovel/"]')
        assert len(urls) == 2
        assert "id=123" in urls[0]
        assert "id=456" in urls[1]
    
    async def test_extract_listing_urls_from_search_success(self, mock_page, mock_element):
        """Test listing URLs extraction from search page"""
        service = ZapImoveisService(mock_page)
        
        link = AsyncMock()
        link.get_attribute = AsyncMock(return_value="/imovel/venda-apartamento-id-123/?id=123")
        mock_page.query_selector_all = AsyncMock(return_value=[link])
        
        urls = await service.search_extractor.extract_listing_urls_from_search()
        assert len(urls) >= 1
    
    async def test_extract_listing_id_from_url_with_id_param(self, mock_page):
        """Test listing ID extraction from URL with id parameter"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/test/?id=123456&source=ranking"
        listing_id = service.search_extractor._extract_listing_id_from_url(url)
        assert listing_id == "123456"
    
    async def test_extract_listing_id_from_url_with_id_in_path(self, mock_page):
        """Test listing ID extraction from URL path"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/venda-apartamento-3-quartos-id-123456/"
        listing_id = service.search_extractor._extract_listing_id_from_url(url)
        assert listing_id == "123456"
    
    async def test_extract_listing_id_from_url_not_found(self, mock_page):
        """Test listing ID extraction when not found"""
        service = ZapImoveisService(mock_page)
        url = "https://www.zapimoveis.com.br/imovel/venda-apartamento/"
        listing_id = service.search_extractor._extract_listing_id_from_url(url)
        assert listing_id is None
    
    async def test_find_card_by_id_success(self, mock_page, mock_element):
        """Test finding card by ID"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        card = await service.search_extractor._find_card_by_id("123456")
        assert card == mock_element
    
    async def test_find_card_by_url_pattern_success(self, mock_page, mock_element):
        """Test finding card by URL pattern"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        url = "https://www.zapimoveis.com.br/imovel/venda-apartamento-3-quartos/"
        card = await service.search_extractor._find_card_by_url_pattern(url)
        assert card == mock_element
    
    async def test_find_card_by_url_pattern_no_prefix(self, mock_page):
        """Test finding card by URL pattern when no prefix"""
        service = ZapImoveisService(mock_page)
        url = "https://example.com/test"
        card = await service.search_extractor._find_card_by_url_pattern(url)
        assert card is None
    
    async def test_find_card_by_scanning_success(self, mock_page, mock_element):
        """Test finding card by scanning"""
        service = ZapImoveisService(mock_page)
        
        card = AsyncMock()
        link = AsyncMock()
        link.get_attribute = AsyncMock(return_value="https://www.zapimoveis.com.br/imovel/test/?id=123")
        card.query_selector = AsyncMock(return_value=link)
        
        mock_page.query_selector_all = AsyncMock(return_value=[card])
        
        found_card = await service.search_extractor._find_card_by_scanning("https://www.zapimoveis.com.br/imovel/test/?id=123", "123")
        assert found_card == card
    
    async def test_find_listing_card_by_id(self, mock_page, mock_element):
        """Test finding listing card using ID strategy"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        url = "https://www.zapimoveis.com.br/imovel/test/?id=123456"
        card = await service.search_extractor._find_listing_card(url)
        assert card == mock_element
    
    async def test_extract_title_from_card_success(self, mock_page, mock_element):
        """Test title extraction from card"""
        service = ZapImoveisService(mock_page)
        
        title_elem = AsyncMock()
        title_elem.text_content = AsyncMock(return_value="Apartamento para comprar com 140 m² em Vila Nossa Senhora")
        
        mock_element.query_selector = AsyncMock(return_value=title_elem)
        
        title = await service.search_extractor._extract_title_from_card(mock_element)
        assert "Apartamento para comprar" in title
    
    async def test_extract_price_from_card_success(self, mock_page, mock_element):
        """Test price extraction from card"""
        service = ZapImoveisService(mock_page)
        
        price_elem = AsyncMock()
        price_elem.text_content = AsyncMock(return_value="R$ 440.000")
        
        mock_element.query_selector = AsyncMock(return_value=price_elem)
        
        price = await service.search_extractor._extract_price_from_card(mock_element)
        assert price == 440000.0
    
    async def test_extract_location_from_card_success(self, mock_page, mock_element):
        """Test location extraction from card"""
        service = ZapImoveisService(mock_page)
        
        loc_elem = AsyncMock()
        loc_elem.text_content = AsyncMock(return_value="Apartamento em Vila Nossa Senhora das Graças, Franca")
        street_elem = AsyncMock()
        street_elem.text_content = AsyncMock(return_value="Rua Osório Arantes")
        
        mock_element.query_selector = AsyncMock(side_effect=[loc_elem, street_elem])
        
        location = await service.search_extractor._extract_location_from_card(mock_element)
        assert "Vila Nossa Senhora" in location
        assert "Rua Osório Arantes" in location
    
    async def test_extract_numeric_field_from_card_success(self, mock_page, mock_element):
        """Test numeric field extraction from card"""
        service = ZapImoveisService(mock_page)
        
        area_elem = AsyncMock()
        area_elem.text_content = AsyncMock(return_value="140 m²")
        
        mock_element.query_selector = AsyncMock(return_value=area_elem)
        
        area = await service.search_extractor._extract_numeric_field_from_card(mock_element, '[data-cy="rp-cardProperty-propertyArea-txt"]')
        assert area == 140.0
    
    async def test_extract_integer_field_from_card_success(self, mock_page, mock_element):
        """Test integer field extraction from card"""
        service = ZapImoveisService(mock_page)
        
        bedroom_elem = AsyncMock()
        bedroom_elem.text_content = AsyncMock(return_value="3")
        
        mock_element.query_selector = AsyncMock(return_value=bedroom_elem)
        
        bedrooms = await service.search_extractor._extract_integer_field_from_card(mock_element, '[data-cy="rp-cardProperty-bedroomQuantity-txt"]')
        assert bedrooms == 3
    
    async def test_extract_image_from_card_success(self, mock_page, mock_element):
        """Test image extraction from card"""
        service = ZapImoveisService(mock_page)
        service.page.url = "https://www.zapimoveis.com.br/imovel/test"
        
        img_elem = AsyncMock()
        img_elem.get_attribute = AsyncMock(return_value="https://resizedimgs.zapimoveis.com.br/img.jpg?dimension=614x297")
        
        mock_element.query_selector = AsyncMock(return_value=img_elem)
        
        images = await service.search_extractor._extract_image_from_card(mock_element)
        assert len(images) == 1
        assert "img.jpg" in images[0]
        assert "dimension" not in images[0]
    
    async def test_extract_listing_from_search_card_success(self, mock_page, mock_element):
        """Test full listing extraction from search card"""
        service = ZapImoveisService(mock_page)
        service.page.url = "https://www.zapimoveis.com.br/imovel/test"
        
        # Mock all card elements
        title_elem = AsyncMock()
        title_elem.text_content = AsyncMock(return_value="Apartamento para comprar com 140 m² em Vila Nossa Senhora")
        price_elem = AsyncMock()
        price_elem.text_content = AsyncMock(return_value="R$ 440.000")
        loc_elem = AsyncMock()
        loc_elem.text_content = AsyncMock(return_value="Apartamento em Vila Nossa Senhora das Graças, Franca")
        street_elem = AsyncMock()
        street_elem.text_content = AsyncMock(return_value="Rua Osório Arantes")
        area_elem = AsyncMock()
        area_elem.text_content = AsyncMock(return_value="140 m²")
        bedroom_elem = AsyncMock()
        bedroom_elem.text_content = AsyncMock(return_value="3")
        bathroom_elem = AsyncMock()
        bathroom_elem.text_content = AsyncMock(return_value="2")
        parking_elem = AsyncMock()
        parking_elem.text_content = AsyncMock(return_value="1")
        img_elem = AsyncMock()
        img_elem.get_attribute = AsyncMock(return_value="https://resizedimgs.zapimoveis.com.br/img.jpg")
        
        # Mock card finding
        mock_page.query_selector = AsyncMock(side_effect=[
            mock_element,  # find_card_by_id
            title_elem,    # title
            price_elem,    # price (first selector)
            price_elem,    # price (fallback)
            loc_elem,      # location
            street_elem,   # street
            area_elem,     # area
            bedroom_elem,  # bedrooms
            bathroom_elem, # bathrooms
            parking_elem,  # parking
            img_elem       # image
        ])
        
        url = "https://www.zapimoveis.com.br/imovel/test/?id=123456"
        data = await service.search_extractor.extract_listing_from_search_card(url)
        
        assert data is not None
        assert data["url"] == url
        assert data["price"] == 440000.0
        assert data["area"] == 140.0
        assert data["bedrooms"] == 3
    
    async def test_extract_listing_from_search_card_not_found(self, mock_page):
        """Test listing extraction when card not found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        url = "https://www.zapimoveis.com.br/imovel/test/?id=999999"
        data = await service.search_extractor.extract_listing_from_search_card(url)
        assert data is None
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scroll_to_load_listings_disabled(self, mock_config, mock_page, mock_human_behavior):
        """Test scroll when SCROLL_ENABLED is False"""
        mock_config.SCROLL_ENABLED = False
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        await service._scroll_to_load_listings()
        # Should return early, no scrolling
        mock_human_behavior.scroll_page.assert_not_called()
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    @patch('src.scraper_app.services.zap_imoveis_service.asyncio')
    async def test_scroll_to_load_listings_enabled(self, mock_asyncio, mock_config, mock_page, mock_human_behavior):
        """Test scroll when SCROLL_ENABLED is True"""
        mock_config.SCROLL_ENABLED = True
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        # Mock evaluate to return listing count
        mock_page.evaluate = AsyncMock(return_value=5)
        
        await service._scroll_to_load_listings(max_listings=10)
        # Should scroll
        mock_human_behavior.scroll_page.assert_called()
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_search_results_success(self, mock_config, mock_page, mock_human_behavior):
        """Test scraping search results"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.SCROLL_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        # Mock URL extraction
        link = AsyncMock()
        link.get_attribute = AsyncMock(return_value="/imovel/venda-apartamento-id-123/?id=123")
        mock_page.query_selector_all = AsyncMock(return_value=[link])
        
        # Mock card extraction
        card = AsyncMock()
        title_elem = AsyncMock()
        title_elem.text_content = AsyncMock(return_value="Apartamento em Vila")
        price_elem = AsyncMock()
        price_elem.text_content = AsyncMock(return_value="R$ 440.000")
        mock_page.query_selector = AsyncMock(side_effect=[card, title_elem, price_elem, price_elem])
        
        results = await service.scrape_search_results("https://www.zapimoveis.com.br/busca/")
        assert isinstance(results, list)
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_search_results_error(self, mock_config, mock_page, mock_human_behavior):
        """Test scraping search results with error"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
        
        results = await service.scrape_search_results("https://www.zapimoveis.com.br/busca/")
        assert results == []


@pytest.mark.asyncio
class TestMainScraping:
    """Tests for main scraping methods"""
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    @patch('src.scraper_app.services.zap_imoveis_service.random')
    async def test_scrape_listing_success(self, mock_random, mock_config, mock_page, mock_human_behavior):
        """Test successful listing scraping"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = True
        mock_config.SCROLL_ENABLED = True
        mock_config.NAVIGATION_TIMEOUT = 30000
        mock_random.randint = MagicMock(return_value=300)
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        # Mock all extraction methods
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Apartamento - Zap Imóveis")
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        result = await service.scrape_listing("https://www.zapimoveis.com.br/imovel/test/")
        
        assert "url" in result
        assert result["url"] == "https://www.zapimoveis.com.br/imovel/test/"
        mock_page.goto.assert_called_once()
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_listing_error(self, mock_config, mock_page, mock_human_behavior):
        """Test listing scraping with error"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation error"))
        
        result = await service.scrape_listing("https://www.zapimoveis.com.br/imovel/test/")
        
        assert "error" in result
        assert result["url"] == "https://www.zapimoveis.com.br/imovel/test/"
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_wait_for_page_load_with_human_behavior(self, mock_config, mock_page, mock_human_behavior):
        """Test wait_for_page_load with human behavior enabled"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = True
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        await service.wait_for_page_load()
        mock_human_behavior.wait_for_page_with_behavior.assert_called_once_with(mock_page)
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_wait_for_page_load_without_human_behavior(self, mock_config, mock_page, mock_human_behavior):
        """Test wait_for_page_load without human behavior"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        await service.wait_for_page_load()
        mock_page.wait_for_load_state.assert_called_once_with("networkidle")


@pytest.mark.asyncio
class TestPaginationMethods:
    """Tests for pagination-related methods"""
    
    async def test_build_page_url_no_params(self, mock_page):
        """Test building page URL from base URL without params"""
        service = ZapImoveisService(mock_page)
        base_url = "https://www.zapimoveis.com.br/busca/"
        page_url = service.pagination.build_page_url(base_url, 2)
        assert page_url == "https://www.zapimoveis.com.br/busca/?page=2"
    
    async def test_build_page_url_with_params(self, mock_page):
        """Test building page URL from base URL with existing params"""
        service = ZapImoveisService(mock_page)
        base_url = "https://www.zapimoveis.com.br/busca/?city=São Paulo"
        page_url = service.pagination.build_page_url(base_url, 2)
        assert "page=2" in page_url
        assert "city=São Paulo" in page_url
    
    async def test_build_page_url_replace_existing_page(self, mock_page):
        """Test building page URL replacing existing page param"""
        service = ZapImoveisService(mock_page)
        base_url = "https://www.zapimoveis.com.br/busca/?page=1&city=São Paulo"
        page_url = service.pagination.build_page_url(base_url, 3)
        assert "page=3" in page_url
        assert "page=1" not in page_url
    
    async def test_get_total_pages_from_pagination(self, mock_page, mock_element):
        """Test getting total pages from pagination element"""
        service = ZapImoveisService(mock_page)
        
        # Mock pagination element with page links
        page_link1 = AsyncMock()
        page_link1.text_content = AsyncMock(return_value="1")
        page_link2 = AsyncMock()
        page_link2.text_content = AsyncMock(return_value="2")
        page_link3 = AsyncMock()
        page_link3.text_content = AsyncMock(return_value="3")
        
        pagination = AsyncMock()
        pagination.query_selector_all = AsyncMock(return_value=[page_link1, page_link2, page_link3])
        
        mock_page.query_selector = AsyncMock(return_value=pagination)
        
        total_pages = await service.pagination.get_total_pages()
        assert total_pages == 3
    
    async def test_get_total_pages_from_href(self, mock_page, mock_element):
        """Test getting total pages from href attributes"""
        from src.scraper_app.services.zap_imoveis.selectors import PAGE_PARAM
        service = ZapImoveisService(mock_page)
        
        page_link = AsyncMock()
        page_link.text_content = AsyncMock(return_value="Next")
        page_link.get_attribute = AsyncMock(return_value=f"/busca/?{PAGE_PARAM}5")
        
        pagination = AsyncMock()
        pagination.query_selector_all = AsyncMock(return_value=[page_link])
        
        mock_page.query_selector = AsyncMock(return_value=pagination)
        
        total_pages = await service.pagination.get_total_pages()
        assert total_pages == 5
    
    async def test_get_total_pages_no_pagination(self, mock_page):
        """Test getting total pages when no pagination found"""
        service = ZapImoveisService(mock_page)
        mock_page.query_selector = AsyncMock(return_value=None)
        
        total_pages = await service.pagination.get_total_pages()
        assert total_pages == 1
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_single_page_success(self, mock_config, mock_page, mock_human_behavior):
        """Test scraping a single page"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.SCROLL_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        # Mock URL extraction
        link = AsyncMock()
        link.get_attribute = AsyncMock(return_value="/imovel/venda-apartamento-id-123/?id=123")
        mock_page.query_selector_all = AsyncMock(return_value=[link])
        
        # Mock card extraction
        card = AsyncMock()
        title_elem = AsyncMock()
        title_elem.text_content = AsyncMock(return_value="Apartamento em Vila")
        price_elem = AsyncMock()
        price_elem.text_content = AsyncMock(return_value="R$ 440.000")
        mock_page.query_selector = AsyncMock(side_effect=[card, title_elem, price_elem, price_elem])
        
        results = await service._scrape_single_page("https://www.zapimoveis.com.br/busca/?page=1")
        assert isinstance(results, list)
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_single_page_error(self, mock_config, mock_page, mock_human_behavior):
        """Test scraping single page with error"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation error"))
        
        results = await service._scrape_single_page("https://www.zapimoveis.com.br/busca/?page=1")
        assert results == []
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_search_results_with_max_pages(self, mock_config, mock_page, mock_human_behavior):
        """Test scraping search results with max_pages parameter"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.SCROLL_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        # Mock pagination detection
        pagination = AsyncMock()
        page_link = AsyncMock()
        page_link.text_content = AsyncMock(return_value="5")
        pagination.query_selector_all = AsyncMock(return_value=[page_link])
        mock_page.query_selector = AsyncMock(return_value=pagination)
        
        # Mock URL extraction
        link = AsyncMock()
        link.get_attribute = AsyncMock(return_value="/imovel/venda-apartamento-id-123/?id=123")
        mock_page.query_selector_all = AsyncMock(return_value=[link])
        
        # Mock card extraction
        card = AsyncMock()
        title_elem = AsyncMock()
        title_elem.text_content = AsyncMock(return_value="Apartamento")
        price_elem = AsyncMock()
        price_elem.text_content = AsyncMock(return_value="R$ 440.000")
        
        # Setup side_effect for multiple calls
        def query_selector_side_effect(selector):
            if 'pagination' in selector or '[data-cy="pagination"]' in selector:
                return pagination
            return card
        
        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)
        
        results = await service.scrape_search_results(
            "https://www.zapimoveis.com.br/busca/",
            max_pages=2
        )
        assert isinstance(results, list)
    
    @patch('src.scraper_app.services.zap_imoveis_service.Config')
    async def test_scrape_search_results_with_specific_page(self, mock_config, mock_page, mock_human_behavior):
        """Test scraping search results with specific page in URL"""
        mock_config.HUMAN_BEHAVIOR_ENABLED = False
        mock_config.SCROLL_ENABLED = False
        mock_config.NAVIGATION_TIMEOUT = 30000
        
        service = ZapImoveisService(mock_page, mock_human_behavior)
        
        # Mock URL extraction
        link = AsyncMock()
        link.get_attribute = AsyncMock(return_value="/imovel/venda-apartamento-id-123/?id=123")
        mock_page.query_selector_all = AsyncMock(return_value=[link])
        
        # Mock card extraction
        card = AsyncMock()
        title_elem = AsyncMock()
        title_elem.text_content = AsyncMock(return_value="Apartamento")
        price_elem = AsyncMock()
        price_elem.text_content = AsyncMock(return_value="R$ 440.000")
        mock_page.query_selector = AsyncMock(side_effect=[card, title_elem, price_elem, price_elem])
        
        results = await service.scrape_search_results(
            "https://www.zapimoveis.com.br/busca/?page=2"
        )
        assert isinstance(results, list)


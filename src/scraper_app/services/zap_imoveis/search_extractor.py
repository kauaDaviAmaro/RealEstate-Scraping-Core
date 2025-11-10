"""
Extraction of listing data from search result cards
"""
from playwright.async_api import Page
from typing import Dict, List, Optional
import re
import logging

from src.scraper_app.services.zap_imoveis.selectors import (
    SELECTOR_LOCATION, SELECTOR_STREET, SELECTOR_PRICE, SELECTOR_AREA,
    SELECTOR_BEDROOMS, SELECTOR_BATHROOMS, SELECTOR_PARKING, SELECTOR_IMAGE,
    SELECTOR_PROPERTY_CARD, URL_IMOVEL_PREFIX, PATTERN_NUMBER
)

logger = logging.getLogger(__name__)


class SearchExtractor:
    """Extracts listing data from search result cards without visiting individual pages"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def _normalize_listing_url(self, href: str) -> str:
        """Normalize listing URL to absolute format"""
        if href.startswith('/'):
            return 'https://www.zapimoveis.com.br' + href
        elif not href.startswith('http'):
            return 'https://www.zapimoveis.com.br/' + href
        return href
    
    def _clean_listing_url(self, href: str) -> str:
        """Clean URL, keeping only id parameter if present"""
        if '?' not in href:
            return href
        
        base_url = href.split('?')[0]
        url_params = href.split('?')[1]
        
        if 'id=' in url_params:
            id_param = [p for p in url_params.split('&') if p.startswith('id=')][0]
            return f"{base_url}?{id_param}"
        
        return base_url
    
    async def _extract_urls_from_selector(self, selector: str) -> List[str]:
        """Extract URLs using a specific selector"""
        urls = []
        try:
            elements = await self.page.query_selector_all(selector)
            for element in elements:
                href = await element.get_attribute('href')
                if href and URL_IMOVEL_PREFIX in href:
                    href = self._normalize_listing_url(href)
                    href = self._clean_listing_url(href)
                    urls.append(href)
        except Exception:
            pass
        return urls
    
    async def extract_listing_urls_from_search(self) -> List[str]:
        """Extract listing URLs from search results page"""
        try:
            listing_selectors = [
                f'{SELECTOR_PROPERTY_CARD} a[href*="{URL_IMOVEL_PREFIX}"]',
                f'a[href*="{URL_IMOVEL_PREFIX}venda-"]',
            ]
            
            urls = set()
            for selector in listing_selectors:
                extracted_urls = await self._extract_urls_from_selector(selector)
                urls.update(extracted_urls)
            
            return list(urls)
            
        except Exception as e:
            logger.debug(f"Error extracting listing URLs: {e}")
            return []
    
    def _extract_listing_id_from_url(self, listing_url: str) -> Optional[str]:
        """Extract listing ID from URL"""
        if 'id=' in listing_url:
            return listing_url.split('id=')[-1].split('&')[0].split('/')[0]
        
        if URL_IMOVEL_PREFIX in listing_url:
            parts = listing_url.split(URL_IMOVEL_PREFIX)[-1].split('/')
            if parts:
                return parts[0].split('-')[-1] if '-' in parts[0] else parts[0]
        
        return None
    
    async def _find_card_by_id(self, listing_id: str):
        """Find card element by listing ID"""
        card_selector = f'a[href*="id-{listing_id}"], a[href*="id={listing_id}"]'
        return await self.page.query_selector(card_selector)
    
    async def _find_card_by_url_pattern(self, listing_url: str):
        """Find card element by URL pattern"""
        if URL_IMOVEL_PREFIX not in listing_url:
            return None
        
        url_pattern = listing_url.split(URL_IMOVEL_PREFIX)[-1].split('?')[0]
        if url_pattern:
            card_selector = f'a[href*="{url_pattern[:30]}"]'
            return await self.page.query_selector(card_selector)
        return None
    
    async def _find_card_by_scanning(self, listing_url: str, listing_id: Optional[str]):
        """Find card by scanning all property cards"""
        cards = await self.page.query_selector_all(SELECTOR_PROPERTY_CARD)
        base_url = listing_url.split('?')[0]
        
        for card in cards:
            link = await card.query_selector(f'a[href*="{URL_IMOVEL_PREFIX}"]')
            if link:
                href = await link.get_attribute('href')
                if href and (base_url in href or (listing_id and listing_id in href)):
                    return card
        return None
    
    async def _find_listing_card(self, listing_url: str) -> Optional[object]:
        """Find the card element for a listing URL"""
        listing_id = self._extract_listing_id_from_url(listing_url)
        
        # Try by ID first
        if listing_id:
            card = await self._find_card_by_id(listing_id)
            if card:
                return card
        
        # Try by URL pattern
        card = await self._find_card_by_url_pattern(listing_url)
        if card:
            return card
        
        # Last resort: scan all cards
        return await self._find_card_by_scanning(listing_url, listing_id)
    
    def _parse_price_text(self, text: str) -> Optional[float]:
        """Parse price from text string"""
        if not text or 'R$' not in text:
            return None
        
        price_text = text.replace('R$', '').strip().replace('.', '').replace(',', '.')
        price_match = re.search(r'[\d.]+', price_text)
        if price_match:
            try:
                price = float(price_match.group())
                if 10000 <= price <= 1000000000:  # Reasonable price range
                    return price
            except ValueError:
                pass
        return None
    
    async def _extract_title_from_card(self, card) -> Optional[str]:
        """Extract title from card element"""
        title_elem = await card.query_selector(SELECTOR_LOCATION)
        if not title_elem:
            return None
        
        title_text = await title_elem.text_content()
        if not title_text:
            return None
        
        parts = title_text.split('em')
        return parts[0].strip() if len(parts) > 1 else title_text.strip()
    
    async def _extract_price_from_card(self, card) -> Optional[float]:
        """Extract price from card element"""
        price_elem = await card.query_selector(f'{SELECTOR_PRICE} p.text-2-25')
        if not price_elem:
            price_elem = await card.query_selector(f'{SELECTOR_PRICE} p')
        
        if price_elem:
            price_text = await price_elem.text_content()
            return self._parse_price_text(price_text or '')
        return None
    
    async def _extract_location_from_card(self, card) -> Optional[str]:
        """Extract location from card element"""
        location_parts = []
        
        loc_elem = await card.query_selector(SELECTOR_LOCATION)
        if loc_elem:
            loc_text = await loc_elem.text_content()
            if loc_text and 'em' in loc_text:
                location_parts.append(loc_text.split('em')[-1].strip())
        
        street_elem = await card.query_selector(SELECTOR_STREET)
        if street_elem:
            street_text = await street_elem.text_content()
            if street_text:
                location_parts.append(street_text.strip())
        
        return ', '.join(location_parts) if location_parts else None
    
    def _normalize_image_url(self, src: str) -> str:
        """Normalize image URL to absolute format"""
        if src.startswith('//'):
            return 'https:' + src
        elif src.startswith('/'):
            base_url = '/'.join(self.page.url.split('/')[:3])
            return base_url + src
        return src
    
    def _clean_image_url(self, src: str) -> str:
        """Remove dimension query parameters from image URL"""
        if '?' in src and 'dimension=' in src:
            return src.split('?')[0]
        return src
    
    async def _extract_numeric_field_from_card(self, card, selector: str) -> Optional[float]:
        """Extract numeric field (area) from card"""
        elem = await card.query_selector(selector)
        if not elem:
            return None
        
        text = await elem.text_content()
        if text and 'm²' in text:
            area_match = re.search(r'(\d+\.?\d*)\s*m²', text, re.IGNORECASE)
            if area_match:
                try:
                    return float(area_match.group(1))
                except ValueError:
                    pass
        return None
    
    async def _extract_integer_field_from_card(self, card, selector: str) -> Optional[int]:
        """Extract integer field (bedrooms, bathrooms, parking) from card"""
        elem = await card.query_selector(selector)
        if not elem:
            return None
        
        text = await elem.text_content()
        if text:
            match = re.search(PATTERN_NUMBER, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return None
    
    async def _extract_image_from_card(self, card) -> List[str]:
        """Extract first image from card"""
        img_elem = await card.query_selector(f'{SELECTOR_IMAGE} img')
        if not img_elem:
            img_elem = await card.query_selector('img[src*="resizedimgs.zapimoveis.com.br"]')
        
        if img_elem:
            img_src = await img_elem.get_attribute('src')
            if img_src:
                img_src = self._normalize_image_url(img_src)
                img_src = self._clean_image_url(img_src)
                return [img_src]
        return []
    
    async def extract_listing_from_search_card(self, listing_url: str) -> Optional[Dict]:
        """
        Extract basic data from a listing card on search results page
        (without visiting the individual listing page)
        """
        try:
            card = await self._find_listing_card(listing_url)
            if not card:
                return None
            
            data = {
                "url": listing_url,
                "title": await self._extract_title_from_card(card),
                "price": await self._extract_price_from_card(card),
                "location": await self._extract_location_from_card(card),
                "property_type": None,
                "area": await self._extract_numeric_field_from_card(card, SELECTOR_AREA),
                "bedrooms": await self._extract_integer_field_from_card(card, SELECTOR_BEDROOMS),
                "bathrooms": await self._extract_integer_field_from_card(card, SELECTOR_BATHROOMS),
                "parking_spaces": await self._extract_integer_field_from_card(card, SELECTOR_PARKING),
                "images": await self._extract_image_from_card(card)
            }
            
            return data
            
        except Exception as e:
            logger.debug(f"Error extracting from card: {e}")
            return None


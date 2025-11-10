"""
Browser Manager - Playwright Initialization and Shutdown Logic
Manages browser configuration and anti-bot measures
"""
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional
import logging
import os

from src.scraper_app.core.proxy_manager import ProxyManager, Proxy
from src.scraper_app.core.fingerprint_manager import FingerprintManager, BrowserFingerprint
from src.scraper_app.config import Config

logger = logging.getLogger(__name__)


def is_docker_environment() -> bool:
    """Check if running in Docker container"""
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"


class BrowserManager:
    """Manages Playwright browser initialization and shutdown with elite anti-detection"""
    
    def __init__(
        self,
        headless: Optional[bool] = None,
        proxy_manager: Optional[ProxyManager] = None,
        fingerprint_manager: Optional[FingerprintManager] = None,
        fingerprint: Optional[BrowserFingerprint] = None
    ):
        """
        Initializes the BrowserManager
        
        Args:
            headless: If True, runs the browser in headless mode (uses Config if None)
            proxy_manager: ProxyManager instance (creates new if None)
            fingerprint_manager: FingerprintManager instance (creates new if None)
            fingerprint: Specific fingerprint to use (generates new if None)
        """
        # Force headless in Docker environments
        if is_docker_environment():
            self.headless = True
            logger.info("Docker environment detected - forcing headless mode")
        else:
            self.headless = headless if headless is not None else Config.HEADLESS
        
        logger.info(f"Browser will run in {'headless' if self.headless else 'headed'} mode")
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        self.proxy_manager = proxy_manager
        self.fingerprint_manager = fingerprint_manager or FingerprintManager()
        self.current_fingerprint: Optional[BrowserFingerprint] = fingerprint
        self.current_proxy: Optional[Proxy] = None
    
    async def initialize(self, preferred_proxy_type: Optional[str] = None) -> BrowserContext:
        """
        Initializes Playwright and creates the browser context with elite anti-detection
        
        Args:
            preferred_proxy_type: Preferred proxy type (residential, mobile, datacenter)
            
        Returns:
            BrowserContext: Configured browser context
        """
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        
        # Get or generate fingerprint
        if not self.current_fingerprint:
            # Use BR region for Brazilian sites, or use config
            region = Config.FINGERPRINT_REGION
            # Auto-detect region from URL if available (for future use)
            self.current_fingerprint = self.fingerprint_manager.generate_fingerprint(
                region=region
            )
            logger.debug(f"Generated fingerprint with region: {region}, UA: {self.current_fingerprint.user_agent[:60]}...")
        
        # Get proxy if enabled
        proxy_config = None
        if Config.PROXY_ENABLED and self.proxy_manager:
            from src.scraper_app.core.proxy_manager import ProxyType
            proxy_type = None
            if preferred_proxy_type:
                try:
                    proxy_type = ProxyType(preferred_proxy_type)
                except ValueError:
                    pass
            
            self.current_proxy = await self.proxy_manager.get_proxy(proxy_type)
            if self.current_proxy:
                proxy_config = self.current_proxy.to_playwright_config()
                logger.info(f"Using proxy: {self.current_proxy.host}:{self.current_proxy.port}")
        
        # Get browser type
        browser_type_map = {
            "chromium": self.playwright.chromium,
            "firefox": self.playwright.firefox,
            "webkit": self.playwright.webkit
        }
        browser_launcher = browser_type_map.get(Config.BROWSER_TYPE, self.playwright.chromium)
        
        # Launch browser
        browser_args = []
        if Config.BROWSER_TYPE == "chromium":
            # Add stealth arguments to avoid bot detection
            browser_args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-popup-blocking",
                "--window-size=1920,1080",
                "--start-maximized",
                "--lang=pt-BR,pt",
                "--accept-lang=pt-BR,pt;q=0.9"
            ])
            
            # Force headless mode arguments when in headless mode
            if self.headless:
                browser_args.extend([
                    "--headless=new",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions"
                ])
        
        logger.debug(f"Launching browser with headless={self.headless}, args={browser_args[:5]}...")
        
        # Always force headless=True when in Docker, regardless of config
        launch_headless = self.headless
        if is_docker_environment():
            launch_headless = True
            logger.info("Forcing headless=True for Docker environment")
        
        self.browser = await browser_launcher.launch(
            headless=launch_headless,
            args=browser_args,
            proxy=proxy_config
        )
        
        # Create context with fingerprint
        context_options = {
            "viewport": self.current_fingerprint.to_playwright_viewport(),
            "locale": self.current_fingerprint.to_playwright_locale(),
            "timezone_id": self.current_fingerprint.timezone,
            "user_agent": self.current_fingerprint.user_agent,
            "extra_http_headers": self.fingerprint_manager.get_http_headers(self.current_fingerprint),
            "ignore_https_errors": True,
            "java_script_enabled": True
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Configure anti-bot measures
        await self.configure_anti_bot(self.context)
        
        logger.info(f"Browser initialized with fingerprint: {self.current_fingerprint.user_agent[:50]}...")
        
        return self.context
    
    async def create_page(self) -> Page:
        """
        Creates a new page in the browser context
        
        Returns:
            Page: New browser page
        """
        if not self.context:
            await self.initialize()
        
        return await self.context.new_page()
    
    async def configure_anti_bot(self, context: BrowserContext) -> None:
        """
        Configures anti-bot measures in the browser context
        
        Args:
            context: Browser context to be configured
        """
        if not self.current_fingerprint:
            return
        
        # Inject anti-detect script
        anti_detect_script = self.fingerprint_manager.get_anti_detect_script(self.current_fingerprint)
        await context.add_init_script(anti_detect_script)
        
        # Override webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        logger.debug("Anti-bot measures configured")
    
    def rotate_fingerprint(self) -> BrowserFingerprint:
        """
        Rotate to a new fingerprint
        
        Returns:
            New BrowserFingerprint
        """
        self.current_fingerprint = self.fingerprint_manager.generate_fingerprint(
            region=Config.FINGERPRINT_REGION
        )
        logger.info(f"Rotated to new fingerprint: {self.current_fingerprint.user_agent[:50]}...")
        return self.current_fingerprint
    
    async def mark_proxy_success(self) -> None:
        """Mark current proxy as successful"""
        if self.current_proxy and self.proxy_manager:
            await self.proxy_manager.mark_success(self.current_proxy)
    
    async def mark_proxy_failure(self) -> None:
        """Mark current proxy as failed"""
        if self.current_proxy and self.proxy_manager:
            await self.proxy_manager.mark_failure(self.current_proxy)
            self.current_proxy = None  # Will get new proxy on next initialize
    
    async def close(self) -> None:
        """Closes the browser and shuts down Playwright"""
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        logger.debug("Browser closed")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()


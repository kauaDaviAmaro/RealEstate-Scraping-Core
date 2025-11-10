"""
Tests for Config - environment variable loading, proxy config parsing, defaults
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.scraper_app.config import Config


@pytest.mark.asyncio
class TestConfigDefaults:
    """Tests for default configuration values"""
    
    def test_browser_defaults(self):
        """Test browser configuration defaults"""
        # These should match Config defaults
        assert isinstance(Config.HEADLESS, bool)
        assert Config.BROWSER_TYPE in ["chromium", "firefox", "webkit"]
    
    def test_proxy_defaults(self):
        """Test proxy configuration defaults"""
        assert isinstance(Config.PROXY_ENABLED, bool)
        assert Config.PROXY_ROTATION_STRATEGY in ["round_robin", "random", "least_used", "best_performance"]
        assert isinstance(Config.PROXY_MAX_FAILURES, int)
        assert Config.PROXY_MAX_FAILURES > 0
    
    def test_fingerprint_defaults(self):
        """Test fingerprint configuration defaults"""
        assert isinstance(Config.FINGERPRINT_REGION, str)
        assert isinstance(Config.FINGERPRINT_ROTATION, bool)
    
    def test_human_behavior_defaults(self):
        """Test human behavior configuration defaults"""
        assert isinstance(Config.HUMAN_BEHAVIOR_ENABLED, bool)
        assert isinstance(Config.MIN_DELAY, float)
        assert isinstance(Config.MAX_DELAY, float)
        assert Config.MIN_DELAY < Config.MAX_DELAY
    
    def test_compliance_defaults(self):
        """Test compliance configuration defaults"""
        assert isinstance(Config.RESPECT_ROBOTS_TXT, bool)
        assert isinstance(Config.ROBOTS_CACHE_DIR, str)
        assert isinstance(Config.ROBOTS_CACHE_TTL, int)
        assert Config.ROBOTS_CACHE_TTL > 0


@pytest.mark.asyncio
class TestConfigEnvironmentVariables:
    """Tests for environment variable loading"""
    
    @patch.dict(os.environ, {'HEADLESS': 'False'})
    def test_headless_from_env(self):
        """Test loading HEADLESS from environment"""
        # Reload config to pick up env var
        from importlib import reload
        import src.scraper_app.config
        reload(src.scraper_app.config)
        from src.scraper_app.config import Config
        
        assert Config.HEADLESS is False
    
    @patch.dict(os.environ, {'BROWSER_TYPE': 'firefox'})
    def test_browser_type_from_env(self):
        """Test loading BROWSER_TYPE from environment"""
        from importlib import reload
        import src.scraper_app.config
        reload(src.scraper_app.config)
        from src.scraper_app.config import Config
        
        assert Config.BROWSER_TYPE == "firefox"
    
    @patch.dict(os.environ, {'PROXY_ENABLED': 'True'})
    def test_proxy_enabled_from_env(self):
        """Test loading PROXY_ENABLED from environment"""
        from importlib import reload
        import src.scraper_app.config
        reload(src.scraper_app.config)
        from src.scraper_app.config import Config
        
        assert Config.PROXY_ENABLED is True
    
    @patch.dict(os.environ, {'MAX_CONCURRENT': '10'})
    def test_max_concurrent_from_env(self):
        """Test loading MAX_CONCURRENT from environment"""
        from importlib import reload
        import src.scraper_app.config
        reload(src.scraper_app.config)
        from src.scraper_app.config import Config
        
        assert Config.MAX_CONCURRENT == 10


@pytest.mark.asyncio
class TestConfigProxyLoading:
    """Tests for proxy configuration loading"""
    
    def test_load_proxies_from_env_single(self):
        """Test loading single proxy from environment"""
        with patch.dict(os.environ, {'PROXY_1': '127.0.0.1:8080:user:pass:residential:http'}):
            proxies = Config.load_proxies_from_env()
            
            assert len(proxies) == 1
            assert proxies[0]["host"] == "127.0.0.1"
            assert proxies[0]["port"] == 8080
            assert proxies[0]["username"] == "user"
            assert proxies[0]["password"] == "pass"
            assert proxies[0]["type"] == "residential"
            assert proxies[0]["protocol"] == "http"
    
    def test_load_proxies_from_env_multiple(self):
        """Test loading multiple proxies from environment"""
        with patch.dict(os.environ, {
            'PROXY_1': '127.0.0.1:8080',
            'PROXY_2': '127.0.0.1:8081:user:pass:datacenter:socks5'
        }):
            proxies = Config.load_proxies_from_env()
            
            assert len(proxies) == 2
            assert proxies[0]["port"] == 8080
            assert proxies[1]["port"] == 8081
    
    def test_load_proxies_from_env_no_auth(self):
        """Test loading proxy without authentication"""
        with patch.dict(os.environ, {'PROXY_1': '127.0.0.1:8080'}):
            proxies = Config.load_proxies_from_env()
            
            assert len(proxies) == 1
            assert proxies[0]["username"] is None
            assert proxies[0]["password"] is None
    
    def test_load_proxies_from_file(self):
        """Test loading proxies from JSON file"""
        proxy_data = [
            {
                "host": "127.0.0.1",
                "port": 8080,
                "username": "user",
                "password": "pass",
                "type": "residential",
                "protocol": "http"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(proxy_data, f)
            temp_path = f.name
        
        try:
            with patch.object(Config, 'PROXY_CONFIG_FILE', temp_path):
                proxies = Config.load_proxies_from_file()
                
                assert len(proxies) == 1
                assert proxies[0]["host"] == "127.0.0.1"
        finally:
            os.unlink(temp_path)
    
    def test_load_proxies_from_file_not_found(self):
        """Test loading proxies from non-existent file"""
        proxies = Config.load_proxies_from_file("nonexistent.json")
        assert proxies == []
    
    def test_get_all_proxies(self):
        """Test getting all proxies from env and file"""
        with patch.dict(os.environ, {'PROXY_1': '127.0.0.1:8080'}):
            with patch.object(Config, 'PROXY_CONFIG_FILE', None):
                proxies = Config.get_all_proxies()
                
                assert len(proxies) >= 1


@pytest.mark.asyncio
class TestConfigToDict:
    """Tests for configuration dictionary conversion"""
    
    def test_to_dict(self):
        """Test converting config to dictionary"""
        config_dict = Config.to_dict()
        
        assert "browser" in config_dict
        assert "proxy" in config_dict
        assert "fingerprint" in config_dict
        assert "human_behavior" in config_dict
        assert "compliance" in config_dict
        assert "retry" in config_dict
        assert "timeout" in config_dict
        assert "concurrency" in config_dict
        assert "output" in config_dict
        assert "logging" in config_dict
    
    def test_to_dict_structure(self):
        """Test structure of config dictionary"""
        config_dict = Config.to_dict()
        
        assert config_dict["browser"]["headless"] == Config.HEADLESS
        assert config_dict["browser"]["browser_type"] == Config.BROWSER_TYPE
        assert config_dict["proxy"]["enabled"] == Config.PROXY_ENABLED
        assert config_dict["fingerprint"]["region"] == Config.FINGERPRINT_REGION


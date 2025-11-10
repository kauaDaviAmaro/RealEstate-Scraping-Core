# Advanced Web Scraping System

Professional web scraping system developed for extracting real estate data from Zap Imóveis, implementing advanced anti-detection techniques, proxy rotation, browser fingerprinting, and human behavior simulation.

## Key Features

### Pillar 1: IP Rotation
- Support for multiple proxy types: residential, mobile, and datacenter
- Configurable rotation strategies (round-robin, random, by type)
- Automatic failure management and cooldown
- Support for authentication and multiple protocols (HTTP, SOCKS5)

### Pillar 2: Advanced Fingerprinting
- Automatic User-Agent rotation
- Browser characteristic modification (Canvas, WebGL, Fonts)
- Configurable regional fingerprinting
- Automation anti-detection

### Pillar 3: Human Behavior Simulation
- Random delays between requests
- Simulated mouse movements
- Progressive and natural scrolling
- Humanized navigation patterns

### Pillar 4: Legal and Technical Compliance
- robots.txt verification and respect
- robots.txt policy caching
- Configurable rate limiting
- Terms of Service verification

## Architecture

The system is composed of specialized modules:

- **BrowserManager**: Manages Playwright initialization and configuration with anti-detection
- **ProxyManager**: Controls proxy rotation and management
- **FingerprintManager**: Generates and rotates browser fingerprints
- **HumanBehavior**: Simulates human behavior during scraping
- **ComplianceManager**: Verifies and respects robots.txt and policies
- **ZapImoveisService**: Specialized service for Zap Imóveis data extraction
- **DataPipeline**: Orchestrates data flow and concurrency control

## Prerequisites

- Docker and Docker Compose (for containerized execution)
- Python 3.11+ (for local development)
- Playwright Chromium (installed automatically)

## Installation and Configuration

### Option 1: Docker Execution (Recommended)

1. Clone the repository and navigate to the project directory

2. Configure environment variables by creating a `.env` file:

```bash
# Browser Configuration
HEADLESS=True
BROWSER_TYPE=chromium

# Proxy Configuration
PROXY_ENABLED=False
PROXY_ROTATION_STRATEGY=round_robin
PROXY_MAX_FAILURES=3
PROXY_COOLDOWN_SECONDS=300

# Fingerprint Configuration
FINGERPRINT_REGION=BR
FINGERPRINT_ROTATION=True

# Human Behavior Configuration
HUMAN_BEHAVIOR_ENABLED=True
MIN_DELAY=1.0
MAX_DELAY=4.0
SCROLL_DELAY_MIN=0.5
SCROLL_DELAY_MAX=2.0
MOUSE_MOVEMENT_ENABLED=True
SCROLL_ENABLED=True

# Compliance Configuration
RESPECT_ROBOTS_TXT=True
ROBOTS_CACHE_DIR=.cache/robots
ROBOTS_CACHE_TTL=3600

# Retry Configuration
MAX_RETRIES=3
RETRY_DELAY=2.0
RETRY_BACKOFF=2.0

# Timeout Configuration
PAGE_LOAD_TIMEOUT=30000
NAVIGATION_TIMEOUT=30000
WAIT_UNTIL=domcontentloaded

# Concurrency Configuration
MAX_CONCURRENT=3

# Pagination Configuration
MAX_PAGES=

# Output Configuration
OUTPUT_DIR=data
SAVE_IMAGES=True

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=
```

3. Configure search URLs by editing `src/scraper_app/__main__.py`:

```python
def discover_search_urls() -> List[str]:
    base_search_urls = [
        "https://www.zapimoveis.com.br/venda/",
        # Add more URLs as needed
    ]
    return base_search_urls
```

4. Build and run the container:

```bash
# Build the image
docker-compose build

# Run the scraper
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 2: Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

2. Configure the environment by creating a `.env` file (see example above)

3. Run the scraper:

```bash
python -m src.scraper_app
```

## Proxy Configuration

### Option 1: Environment Variables

In the `.env` file, configure proxies using the format:

```env
PROXY_ENABLED=True
PROXY_1=host:port:username:password:type:protocol
PROXY_2=host2:port2:user2:pass2:mobile:socks5
```

Format: `host:port:username:password:type:protocol`

- **type**: `residential`, `mobile`, or `datacenter`
- **protocol**: `http` or `socks5`
- For proxies without authentication: `host:port`

### Option 2: JSON File

Configure in `.env`:

```env
PROXY_ENABLED=True
PROXY_CONFIG_FILE=config/proxies.json
```

Create the `config/proxies.json` file:

```json
[
  {
    "host": "proxy.example.com",
    "port": 8080,
    "username": "user",
    "password": "pass",
    "type": "residential",
    "protocol": "http"
  },
  {
    "host": "proxy2.example.com",
    "port": 1080,
    "username": "user2",
    "password": "pass2",
    "type": "mobile",
    "protocol": "socks5"
  }
]
```

## Project Structure

```
.
├── src/
│   └── scraper_app/
│       ├── __main__.py              # Main entry point
│       ├── config.py                 # Centralized configuration
│       ├── core/                     # Core components
│       │   ├── browser_manager.py    # Playwright management
│       │   ├── proxy_manager.py      # Proxy rotation
│       │   ├── fingerprint_manager.py # Advanced fingerprinting
│       │   ├── human_behavior.py     # Behavior simulation
│       │   └── compliance_manager.py # Legal compliance
│       ├── services/                 # Scraping services
│       │   ├── zap_imoveis_service.py
│       │   └── zap_imoveis/
│       │       ├── extractors.py     # Data extractors
│       │       ├── pagination.py     # Pagination management
│       │       ├── search_extractor.py # Search extraction
│       │       └── selectors.py      # CSS/XPath selectors
│       └── pipelines/               # Data pipeline
│           └── data_pipeline.py     # Flow orchestration
├── data/                            # Extracted data
│   └── scraped_data.csv
├── notebooks/                       # Exploratory analysis
│   └── EDA.ipynb
├── tests/                           # Automated tests
│   ├── conftest.py
│   ├── fixtures/
│   └── test_*.py
├── docker-compose.yml               # Docker configuration
├── Dockerfile                       # Docker image
├── requirements.txt                 # Python dependencies
└── pytest.ini                      # Test configuration
```

## Detailed Configuration

### Browser

- `HEADLESS`: Run browser in headless mode (True/False)
- `BROWSER_TYPE`: Browser type (chromium, firefox, webkit)

### Proxy

- `PROXY_ENABLED`: Enable proxy rotation (True/False)
- `PROXY_ROTATION_STRATEGY`: Rotation strategy (round_robin, random, by_type)
- `PROXY_MAX_FAILURES`: Maximum failures before disabling proxy
- `PROXY_COOLDOWN_SECONDS`: Cooldown time after failures

### Fingerprint

- `FINGERPRINT_REGION`: Region for fingerprint generation (BR, US, etc.)
- `FINGERPRINT_ROTATION`: Rotate fingerprints automatically (True/False)

### Human Behavior

- `HUMAN_BEHAVIOR_ENABLED`: Enable behavior simulation (True/False)
- `MIN_DELAY` / `MAX_DELAY`: Delay interval between actions (seconds)
- `SCROLL_DELAY_MIN` / `SCROLL_DELAY_MAX`: Scroll delay interval
- `MOUSE_MOVEMENT_ENABLED`: Simulate mouse movements (True/False)
- `SCROLL_ENABLED`: Enable progressive scrolling (True/False)

### Compliance

- `RESPECT_ROBOTS_TXT`: Respect robots.txt (True/False)
- `ROBOTS_CACHE_DIR`: Cache directory for robots.txt
- `ROBOTS_CACHE_TTL`: Cache time to live (seconds)

### Retry and Timeout

- `MAX_RETRIES`: Maximum number of retry attempts
- `RETRY_DELAY`: Initial delay between retries (seconds)
- `RETRY_BACKOFF`: Exponential backoff multiplier
- `PAGE_LOAD_TIMEOUT`: Page load timeout (ms)
- `NAVIGATION_TIMEOUT`: Navigation timeout (ms)
- `WAIT_UNTIL`: Wait condition (domcontentloaded, load, networkidle)

### Concurrency and Pagination

- `MAX_CONCURRENT`: Maximum number of concurrent requests
- `MAX_PAGES`: Page limit for scraping (empty = no limit)

### Output

- `OUTPUT_DIR`: Output directory for data
- `SAVE_IMAGES`: Save property images (True/False)

### Logging

- `LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE`: Log file (empty = stdout)

## Data Output

Extracted data is saved in:

- `data/scraped_data.csv`: Data in CSV format with all property information
- `data/images/{listing_id}/`: Downloaded images (if `SAVE_IMAGES=True`)

The CSV contains information such as:
- Property ID
- URL
- Title
- Price
- Location
- Features (bedrooms, bathrooms, area, etc.)
- Description
- Images
- And other relevant information

## Pipeline Features

The system automatically:

1. Discovers configured search URLs
2. Extracts all listings from all result pages
3. Processes each listing individually with deep scraping
4. Manages concurrency and rate control
5. Applies anti-detection techniques
6. Saves data to CSV and images (if enabled)
7. Generates execution statistics

## Testing

Run tests with:

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific tests
pytest tests/test_zap_imoveis_service.py
```

## Troubleshooting

### Playwright in Docker

If you encounter issues with Playwright in Docker:

- Verify that `shm_size: '2gb'` is configured in `docker-compose.yml`
- Confirm browsers were installed: `playwright install chromium`
- Check logs: `docker-compose logs scraper`

### Proxies not working

- Verify `PROXY_ENABLED=True` in `.env`
- Confirm format: `host:port:username:password:type:protocol`
- Test proxy manually before using
- Check logs for authentication or connection errors

### Frequent blocks

- Increase `MIN_DELAY` and `MAX_DELAY` to reduce speed
- Use residential proxies (`type=residential`) instead of datacenter
- Reduce `MAX_CONCURRENT` for fewer simultaneous requests
- Verify `HUMAN_BEHAVIOR_ENABLED=True`
- Increase scroll delays: `SCROLL_DELAY_MIN` and `SCROLL_DELAY_MAX`

### Timeout errors

- Increase `PAGE_LOAD_TIMEOUT` and `NAVIGATION_TIMEOUT`
- Change `WAIT_UNTIL` to `load` or `networkidle` if necessary
- Check internet connection and speed

### Memory issues

- Reduce `MAX_CONCURRENT`
- Run in headless mode (`HEADLESS=True`)
- Increase Docker resources if necessary

## Development

### Code Structure

The code follows principles of:

- Separation of concerns
- Dependency injection
- Centralized configuration
- Robust error handling
- Detailed logging

### Adding New Sites

To add support for new sites:

1. Create a new service in `src/scraper_app/services/`
2. Implement site-specific extractors
3. Add CSS/XPath selectors
4. Integrate with `DataPipeline`

### Contributing

1. Keep code clean and documented
2. Add tests for new features
3. Follow existing code patterns
4. Test locally before submitting

## License

This project is for educational and research purposes. Respect the terms of service of the sites you are scraping.

## Legal Notice

This system was developed for educational and research purposes. Always:

- Respect the target sites' `robots.txt`
- Verify and respect Terms of Service
- Use only publicly available data
- Do not overload target servers with excessive requests
- Consider using official APIs when available
- Obtain explicit permission when necessary
- Be aware of local laws regarding web scraping
- Do not use for illegal or unauthorized activities

The use of this software is your responsibility. The developers are not responsible for misuse of this system.

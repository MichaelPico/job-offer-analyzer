from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import psutil
import time
import shutil

class ChromeScrapper:
    """
    A class to handle Chrome browser automation for web scraping.
    
    This class provides methods to manage Chrome instances, create temporary profiles,
    and fetch web pages using Selenium WebDriver.
    
    Attributes:
        chrome_path (str): Path to the Chrome executable
        temp_user_data_dir (str): Path to temporary user data directory
    """
    
    def __init__(self, chrome_path=None):
        """
        Initialize ChromeScrapper with optional Chrome executable path.
        
        Args:
            chrome_path (str, optional): Path to Chrome executable. If None, will attempt to locate automatically.
        """
        if chrome_path:
            self.chrome_path = chrome_path
        else:
            self.chrome_path = self._find_chrome_executable()
        self.temp_user_data_dir = None

    def _find_chrome_executable(self):
        """
        Locate Chrome executable in standard Windows installation paths.
        
        Returns:
            str: Path to Chrome executable
        
        Raises:
            Exception: If Chrome executable is not found
        """
        chrome_paths = [
            os.path.expandvars("%LocalAppData%/Google/Chrome/Application/chrome.exe"),
            os.path.expandvars("%ProgramFiles%/Google/Chrome/Application/chrome.exe"),
            os.path.expandvars("%ProgramFiles(x86)%/Google/Chrome/Application/chrome.exe"),
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                return path
        
        raise Exception("Chrome executable not found. Please verify Chrome is installed.")

    def kill_chrome_processes(self):
        """
        Kill all running Chrome and ChromeDriver processes.
        """
        for proc in psutil.process_iter(['name']):
            try:
                if proc.name() in ['chrome.exe', 'chromedriver.exe']:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(2)

    def create_temp_user_data_dir(self):
        """
        Create a temporary user data directory for Chrome.
        
        Returns:
            str: Path to the created temporary directory
        """
        self.temp_user_data_dir = os.path.join(os.environ['TEMP'], f'chrome_temp_profile_{int(time.time())}')
        if not os.path.exists(self.temp_user_data_dir):
            os.makedirs(self.temp_user_data_dir)
        return self.temp_user_data_dir

    def fetch_page(self, url, headless=False, force_kill=False):
        """
        Fetch a web page using Chrome in incognito mode.
        
        Args:
            url (str): The URL to open
            headless (bool): Whether to run Chrome in headless mode
            force_kill (bool): Whether to force kill existing Chrome processes
        
        Returns:
            str: The page source HTML
            
        Raises:
            Exception: If browser initialization fails
        """
        if force_kill:
            self.kill_chrome_processes()

        self.create_temp_user_data_dir()
        
        options = Options()
        options.add_argument('--incognito')
        options.add_argument(f'--user-data-dir={self.temp_user_data_dir}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        if headless:
            options.add_argument('--headless=new')

        options.binary_location = self.chrome_path
        
        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            source = driver.page_source
            driver.quit()
            return source
            
        except Exception as e:
            try:
                shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
            except:
                pass
            raise Exception(f"Failed to initialize Chrome: {str(e)}")
        finally:
            if self.temp_user_data_dir and os.path.exists(self.temp_user_data_dir):
                try:
                    shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
                except:
                    pass
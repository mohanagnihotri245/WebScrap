from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
from collections import Counter
from urllib.parse import urljoin
import os
import time

class ElPaisHeaderAnalyzer:
    def __init__(self, api_key, driver=None):
        self.base_url = "https://elpais.com"
        self.opinion_url = f"{self.base_url}/opinion/"
        self.api_key = api_key
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.session = requests.Session()
        self.driver = driver
        
    def get_page_source(self):
        """Get page source using Selenium if driver is available, else use requests"""
        if self.driver:
            self.driver.get(self.opinion_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            return self.driver.page_source
        else:
            response = self.session.get(self.opinion_url, headers=self.headers)
            response.raise_for_status()
            return response.text

    # [Previous methods remain unchanged: download_image, translate_text, get_article_content]
    def download_image(self, image_url, idx):
        """Download and save article image"""
        if not image_url:
            return None
            
        try:
            if not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(self.base_url, image_url)
                
            response = self.session.get(image_url, stream=True)
            response.raise_for_status()
            
            # Create directory if it doesn't exist
            os.makedirs('article_images', exist_ok=True)
            
            image_path = f"article_images/article_{idx}_photo.jpg"
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            return image_path
            
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None

    def translate_text(self, text, source_lang="es", target_lang="en"):
        """Translate text using RapidAPI translation service"""
        if not text:
            return None
            
        translate_url = "https://rapid-translate-multi-traduction.p.rapidapi.com/t"
        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Host": "rapid-translate-multi-traduction.p.rapidapi.com",
            "X-RapidAPI-Key": self.api_key
        }
        
        payload = {
            "from": source_lang,
            "to": target_lang,
            "e": "",
            "q": [text]
        }
        
        try:
            response = requests.post(translate_url, json=payload, headers=headers)
            response.raise_for_status()
            translation = response.json()
            return translation[0] if translation else None
        except Exception as e:
            print(f"Translation error: {e}")
            return None
        
        
    def get_article_content(self, article_url):
        """Extract article content"""
        try:
            response = self.session.get(article_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_selectors = [
                {'class': 'a_c clearfix', 'data-dtm-region': 'articulo_cuerpo'},
                {'class': 'articulo-cuerpo'},
                {'class': 'article_body'},
                {'itemprop': 'articleBody'},
                {'class': 'article__body'},
            ]
            
            content = None
            for selector in content_selectors:
                content = soup.find('div', selector)
                if content:
                    break
            
            if not content:
                content = soup.find('article')
                if content:
                    paragraphs = content.find_all('p')
                    return '\n'.join(p.get_text(strip=True) for p in paragraphs)
            
            return content.get_text(strip=True) if content else None
            
        except Exception as e:
            print(f"Error fetching article content: {e}")
            return None

    def get_and_analyze_content(self, num_articles=5):
        """Get content using Selenium or requests, translate headers, and analyze word frequency"""
        try:
            page_source = self.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            articles = []
            all_words = []
            
            for idx, article_elem in enumerate(soup.find_all('article')[:num_articles]):
                title = article_elem.find('h2')
                link = article_elem.find('a', href=True)
                image = article_elem.find('img', src=True)
                
                if not (title and link):
                    continue
                    
                title_text = title.get_text(strip=True)
                article_url = urljoin(self.base_url, link['href'])
                content = self.get_article_content(article_url)
                translated_title = self.translate_text(title_text)
                
                # Download image if available
                image_path = None
                if image and 'src' in image.attrs:
                    print(f"\nDownloading image for article {idx + 1}...")
                    image_path = self.download_image(image['src'], idx + 1)
                    if image_path:
                        print(f"Image saved to: {image_path}")
                    else:
                        print("Failed to download image")
                
                if translated_title:
                    articles.append({
                        'original_title': title_text,
                        'translated_title': translated_title,
                        'content': content,
                        'url': article_url,
                        'image_path': image_path
                    })
                    
                    # Add words to analysis list
                    words = translated_title.lower().split()
                    # Remove common English words and short words
                    words = [w for w in words if len(w) > 3 and w not in {'the', 'and', 'for', 'that', 'with', 'this'}]
                    all_words.extend(words)
                
                # Add a small delay between requests
                time.sleep(1)
            
            # Analyze word frequency
            word_counts = Counter(all_words)
            repeated_words = {word: count for word, count in word_counts.items() if count > 1}
            
            return articles, repeated_words
            
        except Exception as e:
            print(f"Error analyzing content: {e}")
            return [], {}    
           
            
def get_browserstack_driver():
    username = "mohanagnihotri_CvlIQB"
    access_key = "eMJHZt4yM61rybpx885x"
    
    options = Options()
    options.set_capability('browserName', 'chrome')
    options.set_capability('browserVersion', 'latest')
    options.set_capability('bstack:options', {
        'os': 'Windows',
        'osVersion': '10',
        'local': 'false',
        'seleniumVersion': '4.1.2',
        
    })
    
    driver = webdriver.Remote(
        command_executor=f'https://{username}:{access_key}@hub-cloud.browserstack.com/wd/hub',
        options=options
    )
    
    return driver

def main():
    API_KEY = "2c409c4353mshd7b30a5c9f13b61p1eddbfjsn685d3da9af61"
    driver = get_browserstack_driver()
    
    try:
        analyzer = ElPaisHeaderAnalyzer(API_KEY, driver=driver)
        print("Starting analysis with BrowserStack...")
        articles, repeated_words = analyzer.get_and_analyze_content()
        
        # [Rest of the printing logic remains unchanged]
        # Print original Spanish content
        print("\nOriginal Spanish Articles:")
        print("=" * 80)
        for idx, article in enumerate(articles, 1):
            print(f"\nArticle {idx}:")
            print("-" * 40)
            print(f"Title: {article['original_title']}")
            if article['content']:
                print(f"\nContent (first 200 characters):")
                print(article['content'][:200] + "...")
            else:
                print("\nContent: Not available")
            if article['image_path']:
                print(f"\nImage saved: {article['image_path']}")
            else:
                print("\nNo image available")
            print("-" * 40)
    
    # Print translated headers
        print("\nTranslated Headers:")
        print("=" * 80)
        for idx, article in enumerate(articles, 1):
            print(f"{idx}. {article['translated_title']}")
    
    # Print word frequency analysis
        print("\nRepeated Words Analysis:")
        print("=" * 80)
        if repeated_words:
            for word, count in sorted(repeated_words.items(), key=lambda x: x[1], reverse=True):
                print(f"'{word}' appears {count} times")
            else:
                print("No words were repeated more than once in the headers")

        session_url = driver.execute_script('browserstack_executor: {"action": "getSessionDetails"}')
        print("\nBrowserStack Session URL:", session_url)
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
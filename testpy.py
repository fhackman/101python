import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse

def crawl_and_download_images(url, max_pages=10, output_dir='downloaded_images'):
    visited_urls = set()
    queue = [url]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    while queue and len(visited_urls) < max_pages:
        current_url = queue.pop(0)
        
        if current_url in visited_urls:
            continue
        
        visited_urls.add(current_url)
        
        try:
            response = requests.get(current_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Download images
            for img in soup.find_all('img'):
                img_url = img.get('src')
                if img_url:
                    img_url = urljoin(current_url, img_url)
                    download_image(img_url, output_dir)
            
            # Add links to queue
            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    full_url = urljoin(current_url, href)
                    if urlparse(full_url).netloc == urlparse(url).netloc:
                        queue.append(full_url)
        
        except Exception as e:
            print(f"Error crawling {current_url}: {e}")

def download_image(img_url, output_dir):
    try:
        response = requests.get(img_url, stream=True)
        if response.status_code == 200:
            file_name = os.path.join(output_dir, os.path.basename(urlparse(img_url).path))
            with open(file_name, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Downloaded: {img_url}")
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")

# Usage
start_url = 'https://www.microsoft.com'
crawl_and_download_images(start_url, max_pages=15)
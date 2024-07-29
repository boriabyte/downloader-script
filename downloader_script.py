import os
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import zipfile
from io import BytesIO
import urllib.parse

file_path = "" # source where links are being read from
save_path = "" # destination to where files should be saved

class FileReader:
    def __init__(self, file_path):
        self.file_path = file_path
      
    def readLines(self):
        links = []
        try:
            with open(self.file_path, 'r') as file:
                links = file.readlines()
        except FileNotFoundError:
            print(f"\nFile at {file_path} not found! Check spelling, path or if you are in the working directory.")
        except Exception as e:
            print(f"\nError occurred: {e}")
        return links

class Download:
    def __init__(self, links, save_path):
        self.links = links
        self.save_path = save_path
        self.archive_path = os.path.join(self.save_path, "downloaded_files.zip") # placeholder
        
        print(f"\nReading from {file_path}")
        print(f"Download process started; files will be archived to {self.archive_path}\n")

    def get_file_extension(self, content_type):
        # map content types to file extensions.
        extension_map = {
            # archives
            'application/zip': '.rar',               # zip files
            'application/x-7z-compressed': '.rar',   # 7zip files
            'application/x-rar-compressed': '.rar',  # rar files
            'application/x-msdownload': '.exe',      # exe files
            #'application/pdf': '.pdf',
            #'image/jpeg': '.jpg',
            #'image/png': '.png',
            #'text/html': '.html',

            # Add more mappings as needed
        }
        
        # default to bin if can't identify
        return extension_map.get(content_type, '.bin') 

    # method for determining name of file from url
    def extract_file_name_from_url(self, url):
        path = urllib.parse.urlparse(url).path
        segments = path.split('/')
        if len(segments) >= 3:
            return '-'.join(segments[3:]).replace('/', '-')
        return "unknown_file"
    
    def scrape(self):
        # firefox selenium webdriver
        firefox_options = Options()
        firefox_options.add_argument("--headless")  # Run in headless mode
        driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=firefox_options)

        # request session
        session = requests.Session()

        # in-memory zip file
        zip_buffer = BytesIO()

        # copy cookies for session
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # parse links in .txt file + logic
            index = 1
            for link in self.links:
                link = link.strip() 
                try:
                    print(f"Processing page [{index}]: {link}")
                    driver.get(link)

                    # wait for the download button - identified by the text 'Download this file'
                    try:
                        download_btn = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//a[text()='Download this file']"))
                        )
                        download_link = download_btn.get_attribute('href')  # extract the href of the btn

                        if download_link:
                            print(f"Downloading file from: {download_link}")

                            # cookies from Selenium
                            cookies = driver.get_cookies()
                            for cookie in cookies:
                                session.cookies.set(cookie['name'], cookie['value'])

                            # headers to mimic a real browser
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            }

                            # request file
                            file_response = session.get(download_link, headers=headers)
                            file_response.raise_for_status()
                            
                            # determine file extension from content type
                            content_type = file_response.headers.get('Content-Type', '')
                            file_extension = self.get_file_extension(content_type)
                            
                            # construct file name
                            name =  self.extract_file_name_from_url(link)
                            file_name = f"[{index}]. {name}{file_extension}"
                            
                            # write the file content to the zip archive
                            zip_file.writestr(file_name, file_response.content)
                            
                            print(f"File added to archive as: {file_name}\n")
                        else:
                            print(f"No href attribute found for button at URL number [{index}]: {link}\nExpected format: <a href='...'>...</a>\n")

                    except Exception as e:
                        print(f"Error occurred while waiting for the download button: {e}")

                except Exception as e:
                    print(f"Error occurred trying to download from URL [{index}] {link}: {e}. Download halted.")
                index += 1

        # close conn
        driver.quit()

        # Save the zip archive to disk
        with open(self.archive_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        print(f"\nDownload process finished successfully.")
        print(f"All files have been archived to: {self.archive_path}\n")


def main():
    file_reader = FileReader(file_path)
    links = file_reader.readLines()

    if links:
        downloader = Download(links, save_path)
        downloader.scrape()
    else:
        print("No links to process.")
        
if __name__ == "__main__":
    main()

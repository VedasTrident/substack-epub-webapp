from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import tempfile
import uuid
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from ebooklib import epub
import time
from urllib.parse import urlparse, urljoin
import base64
import mimetypes

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

class SubstackFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.images = []  # Store downloaded images
    
    def fetch_article(self, url):
        """Fetch and parse a single Substack article."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('h1', class_='post-title')
            if not title:
                title = soup.find('h1')
            title_text = title.get_text().strip() if title else "Untitled"
            
            # Extract author
            author = soup.find('span', class_='byline-name')
            if not author:
                author = soup.find('a', class_='author-name')
            author_text = author.get_text().strip() if author else "Unknown Author"
            
            # Extract publication date
            date_elem = soup.find('time')
            date_text = date_elem.get('datetime') if date_elem else ""
            
            # Extract content
            content_div = soup.find('div', class_='available-content')
            if not content_div:
                content_div = soup.find('div', class_='post-content')
            if not content_div:
                content_div = soup.find('article')
            
            if not content_div:
                raise ValueError("Could not find article content")
            
            # Clean up content
            content = self._clean_content(content_div, url)
            
            return {
                'title': title_text,
                'author': author_text,
                'date': date_text,
                'content': content,
                'url': url
            }
            
        except Exception as e:
            return {'error': str(e), 'url': url}
    
    def _clean_content(self, content_div, base_url):
        """Clean and format the article content while preserving images."""
        # Remove script and style elements
        for script in content_div(["script", "style", "noscript"]):
            script.decompose()
        
        # Remove social media buttons, ads, etc.
        for elem in content_div.find_all(class_=re.compile(r'(share|social|ad-|subscribe|footer)')):
            elem.decompose()
        
        # Process images
        for img in content_div.find_all('img'):
            src = img.get('src')
            if src:
                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(base_url, src)
                elif not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                # Download and process image
                try:
                    img_response = self.session.get(src, timeout=10)
                    if img_response.status_code == 200:
                        # Generate unique filename
                        img_id = f"img_{len(self.images)}"
                        
                        # Determine file extension from content type or URL
                        content_type = img_response.headers.get('content-type', '')
                        if 'jpeg' in content_type or 'jpg' in content_type:
                            ext = '.jpg'
                        elif 'png' in content_type:
                            ext = '.png'
                        elif 'gif' in content_type:
                            ext = '.gif'
                        elif 'webp' in content_type:
                            ext = '.webp'
                        else:
                            # Try to get extension from URL
                            ext = os.path.splitext(urlparse(src).path)[1] or '.jpg'
                        
                        filename = f"images/{img_id}{ext}"
                        
                        # Store image data
                        self.images.append({
                            'id': img_id,
                            'filename': filename,
                            'data': img_response.content,
                            'content_type': content_type or mimetypes.guess_type(filename)[0] or 'image/jpeg'
                        })
                        
                        # Update img tag to reference local file
                        img['src'] = filename
                        
                except Exception as e:
                    # If image download fails, remove the img tag or keep original src
                    print(f"Failed to download image {src}: {e}")
                    pass
        
        # Convert to string and clean up
        content = str(content_div)
        
        # Basic cleanup
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        return content

class EPUBCompiler:
    def __init__(self, title="Substack Collection", author="Various"):
        self.book = epub.EpubBook()
        self.book.set_identifier(f'substack-collection-{uuid.uuid4()}')
        self.book.set_title(title)
        self.book.set_language('en')
        self.book.add_author(author)
        
        self.chapters = []
        self.toc = []
        self.spine = ['nav']
        self.added_images = set()  # Track added images to avoid duplicates
    
    def add_article(self, article):
        """Add an article as a chapter to the EPUB."""
        if not article or 'error' in article:
            return False
        
        # Create chapter
        chapter_id = f"chapter_{len(self.chapters) + 1}"
        chapter = epub.EpubHtml(
            title=article['title'],
            file_name=f"{chapter_id}.xhtml",
            lang='en'
        )
        
        # Format chapter content
        chapter_content = f"""
        <html>
        <head>
            <title>{article['title']}</title>
        </head>
        <body>
            <h1>{article['title']}</h1>
            <p><em>By {article['author']}</em></p>
            {f"<p><small>{article['date']}</small></p>" if article['date'] else ""}
            <hr/>
            {article['content']}
            <hr/>
            <p><small>Source: <a href="{article['url']}">{article['url']}</a></small></p>
        </body>
        </html>
        """
        
        chapter.content = chapter_content
        
        # Add to book
        self.book.add_item(chapter)
        self.chapters.append(chapter)
        self.toc.append(epub.Link(f"{chapter_id}.xhtml", article['title'], chapter_id))
        self.spine.append(chapter)
        return True
    
    def add_images(self, images):
        """Add images from fetcher to the EPUB."""
        for img_data in images:
            if img_data['filename'] not in self.added_images:
                img_item = epub.EpubItem(
                    uid=img_data['id'],
                    file_name=img_data['filename'],
                    media_type=img_data['content_type'],
                    content=img_data['data']
                )
                self.book.add_item(img_item)
                self.added_images.add(img_data['filename'])
    
    def compile_epub(self, output_path):
        """Compile and save the EPUB file."""
        # Add navigation
        self.book.toc = self.toc
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        
        # Add CSS
        style = '''
        body { font-family: Georgia, serif; margin: 2em; line-height: 1.6; }
        h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 0.5em; }
        h2, h3 { color: #555; }
        p { margin-bottom: 1em; }
        blockquote { font-style: italic; margin: 1em 2em; padding: 1em; background-color: #f5f5f5; }
        hr { margin: 2em 0; border: none; border-top: 1px solid #ccc; }
        '''
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        self.book.add_item(nav_css)
        
        # Set spine
        self.book.spine = self.spine
        
        # Write EPUB
        epub.write_epub(output_path, self.book, {})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_epub():
    urls = request.form.get('urls', '').strip()
    title = request.form.get('title', 'Substack Collection').strip()
    author = request.form.get('author', 'Various').strip()
    
    if not urls:
        flash('Please provide at least one Substack URL', 'error')
        return redirect(url_for('index'))
    
    # Parse URLs
    url_list = [url.strip() for url in urls.split('\n') if url.strip()]
    
    if not url_list:
        flash('Please provide valid URLs', 'error')
        return redirect(url_for('index'))
    
    # Initialize components
    fetcher = SubstackFetcher()
    compiler = EPUBCompiler(title=title, author=author)
    
    # Track progress
    successful_articles = []
    failed_articles = []
    
    # Fetch articles
    for url in url_list:
        try:
            article = fetcher.fetch_article(url)
            if article and 'error' not in article:
                if compiler.add_article(article):
                    successful_articles.append(article['title'])
                else:
                    failed_articles.append(url)
            else:
                failed_articles.append(url)
        except Exception as e:
            failed_articles.append(url)
        
        # Be nice to servers
        time.sleep(1)
    
    if not successful_articles:
        flash('Failed to fetch any articles. Please check your URLs.', 'error')
        return redirect(url_for('index'))
    
    # Generate EPUB
    try:
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        filename = f"substack_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.epub"
        output_path = os.path.join(temp_dir, filename)
        
        compiler.compile_epub(output_path)
        
        # Show success message
        success_msg = f"Successfully compiled {len(successful_articles)} articles"
        if failed_articles:
            success_msg += f" ({len(failed_articles)} failed)"
        flash(success_msg, 'success')
        
        # Return file for download
        return send_file(output_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        flash(f'Error creating EPUB: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
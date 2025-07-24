# Substack to EPUB Web App

A Flask web application that allows users to compile Substack articles into EPUB files for offline reading.

## Features

- 🌐 **Web Interface**: User-friendly web form for inputting URLs and options
- 📚 **EPUB Generation**: Compiles multiple Substack articles into a single EPUB file
- 🎨 **Clean Design**: Modern, responsive interface with gradient styling
- 📱 **Mobile Friendly**: Works on desktop and mobile devices
- ⚡ **Real-time Feedback**: Progress indicators and error handling
- 📖 **Custom Metadata**: Set custom book title and author

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access the Web App**
   Open your browser and go to `http://localhost:5000`

## Usage

1. **Enter URLs**: Paste Substack article URLs (one per line) in the text area
2. **Customize**: Set your preferred book title and author
3. **Compile**: Click "Compile EPUB" to generate your book
4. **Download**: The EPUB file will automatically download when ready

## File Structure

```
substack-epub-webapp/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html     # Main web interface
├── static/
│   └── style.css      # CSS styling
└── README.md          # This file
```

## Features

- **Multi-article Support**: Compile multiple articles into one book
- **Error Handling**: Graceful handling of failed article fetches
- **Progress Tracking**: Shows which articles were successfully added
- **Responsive Design**: Works on all device sizes
- **Clean Content**: Automatically removes ads and social media buttons

## Deployment

For production deployment:

1. **Use a production WSGI server** (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn app:app
   ```

2. **Set environment variables**:
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-secret-key-here
   ```

3. **Configure reverse proxy** (e.g., Nginx) if needed

## Notes

- The application includes a 1-second delay between article fetches to be respectful to Substack's servers
- Generated EPUB files are temporarily stored and automatically cleaned up
- The app works with any Substack publication
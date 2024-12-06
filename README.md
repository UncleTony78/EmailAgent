# Jared - AI Email Assistant

Jared is a sophisticated AI-powered email assistant that helps manage and analyze your emails using CrewAI and the Gmail API.

## Features

- 📧 Read and analyze emails with filtering capabilities
- ✍️ Draft and send emails
- 🔍 Analyze email conversations
- 🤖 Multi-agent architecture for specialized tasks

## Tech Stack

- Python 3.8+
- CrewAI
- FastAPI
- Google Gmail API
- LangChain

## Setup

1. Clone the repository:
```bash
git clone https://github.com/UncleTony78/EmailAgent.git
cd EmailAgent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google OAuth:
   - Go to Google Cloud Console
   - Create a new project or select existing one
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download client configuration and save as `client_secrets.json`
   - Add authorized redirect URIs:
     * http://localhost:8000/auth/callback
     * http://127.0.0.1:8000/auth/callback

4. Create a `.env` file with your credentials:
```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_API_KEY=your_api_key
```

5. Run the application:
```bash
python main.py
```

6. Visit http://localhost:8000/auth/login to authenticate with Google

## API Endpoints

- `GET /auth/login` - Initiate Google OAuth flow
- `GET /auth/callback` - Handle OAuth callback
- `POST /read-emails` - Read and analyze emails
- `POST /send-email` - Send a new email
- `POST /analyze-conversation` - Analyze email conversations

## License

MIT License

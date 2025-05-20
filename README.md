# AI Pitchdeck Content Generator

A powerful FastAPI application that leverages Google's Generative AI to automatically generate content for presentation slides based on user prompts.

## 🚀 Features

- **AI-Powered Content Generation**: Automatically creates professional content for presentation slides
- **Google Slides Integration**: Seamlessly works with Google Slides templates
- **Placeholder Replacement**: Intelligently fills in placeholders in your templates
- **Secure Authentication**: JWT-based authentication for API endpoints
- **Docker Support**: Easy deployment with Docker
- **Scalable Architecture**: Built with FastAPI for high performance

## 📋 Prerequisites

- Python 3.11+
- Google Cloud Platform account with the following APIs enabled:
  - Google Slides API
  - Google Drive API
  - Google Generative AI API
- Google API credentials

## 🛠️ Installation

### Local Development

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/ai-pitchdeck-generator.git
cd ai-pitchdeck-generator
```

2. **Create a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory with the following variables (see `example.env` for a template):

```
GOOGLE_API_KEY=your-api-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
# Additional Google credentials
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
```

5. **Run the application**

```bash
uvicorn main:app --reload
```

### Docker Deployment

1. **Build the Docker image**

```bash
docker build -t ai-pitchdeck-generator .
```

2. **Run the container**

```bash
docker run -p 8000:8000 --env-file .env ai-pitchdeck-generator
```

## 🔧 Configuration

### Google API Setup

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Slides API, Google Drive API, and Google Generative AI API
3. Create OAuth 2.0 credentials and download the credentials file
4. Set up the necessary environment variables as described in the Installation section

## 📚 API Documentation

Once the application is running, you can access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

- `GET /`: Welcome message
- `POST /generate-content`: Generate content for a presentation
- `GET /templates`: List available templates
- `POST /auth/token`: Get authentication token

## 🧩 Project Structure

```
ai-pitchdeck-generator/
├── main.py                 # FastAPI application entry point
├── ai_generator.py         # AI content generation logic
├── slides_manager.py       # Google Slides integration
├── auth.py                 # Authentication utilities
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in repo)
└── example.env             # Example environment variables
```

## 🔒 Security

- All API endpoints are protected with JWT authentication
- Google API credentials are stored securely as environment variables
- Generated presentations have appropriate sharing permissions

## 🚀 Usage Example

```python
import requests
import json

# Get authentication token
auth_response = requests.post(
    "http://localhost:8000/auth/token",
    data={"username": "your-username", "password": "your-password"}
)
token = auth_response.json()["access_token"]

# Generate content
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/generate-content",
    headers=headers,
    json={
        "template_id": "your-google-slides-template-id",
        "prompt": "Create a pitch deck for a sustainable energy startup"
    }
)

# Get the generated presentation URL
result = response.json()
presentation_url = result["presentation_url"]
print(f"Generated presentation: {presentation_url}")
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Google Generative AI](https://ai.google.dev/) for the AI capabilities
- [LangChain](https://www.langchain.com/) for AI orchestration
- [Google Slides API](https://developers.google.com/slides) for presentation integration



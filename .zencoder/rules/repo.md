---
description: Repository Information Overview
alwaysApply: true
---

# AI Pitchdeck Content Generator Information

## Summary
A FastAPI application that leverages Google's Generative AI to automatically generate content for presentation slides based on user prompts. The system integrates with Google Slides to fill in placeholders in templates with AI-generated content.

## Structure
- **main.py**: FastAPI application entry point
- **ai_content_generator.py**: AI content generation logic using Google Gemini
- **slides_manager.py**: Google Slides integration for template management
- **auth_new.py**: Authentication utilities for JWT and Google OAuth
- **placeholder_selector.py**: Logic for processing and grouping placeholders
- **Dockerfile**: Multi-stage Docker configuration
- **requirements.txt**: Python dependencies

## Language & Runtime
**Language**: Python
**Version**: 3.11+
**Framework**: FastAPI
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- fastapi: Web framework for building APIs
- uvicorn: ASGI server for running FastAPI applications
- google-auth, google-auth-oauthlib, google-auth-httplib2: Google authentication libraries
- google-api-python-client: Google APIs client library
- langchain, langchain-core, langgraph: Framework for LLM applications
- google-generativeai, langchain-google-genai: Google AI integration
- pydantic: Data validation and settings management
- python-jose: JWT token handling
- python-dotenv: Environment variable management

## Build & Installation
```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload
```

## Docker
**Dockerfile**: Multi-stage build process
**Base Image**: python:3.11-slim
**Exposed Port**: 8000
**Run Command**:
```bash
# Build the Docker image
docker build -t ai-pitchdeck-generator .

# Run the container
docker run -p 8000:8000 --env-file .env ai-pitchdeck-generator
```

## AI Models
**Primary Model**: Google Gemini 1.5 Pro
**Configuration**:
```python
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
```
**Features**:
- Advanced text generation with context awareness
- Instruction following with precise word count requirements
- Style and format consistency
- Multi-turn conversations with memory

## API Endpoints
**Main Endpoints**:
- `GET /`: Welcome message
- `POST /generate-content`: Generate content for a presentation
- `GET /templates`: List available templates
- `POST /auth/token`: Get authentication token

## Authentication
**Methods**:
- JWT-based authentication
- Google OAuth2 for Google API access
- API Key authentication as an alternative

## Environment Configuration
**Required Variables**:
```
GOOGLE_API_KEY=your-api-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
```
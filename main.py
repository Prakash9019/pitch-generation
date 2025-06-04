import os
import datetime
import asyncio
from fastapi import Depends, FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from googleapiclient.discovery import build

from auth_new import router as auth_router, get_current_user, get_credentials, verify_api_key
from slides_manager import SlidesManager
from ai_content_generator import AIContentGenerator

import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="AI Pitchdeck Content Generator")

# Add CORS middleware for specific origins (frontend domains)
origins = [
    "http://localhost:3000",    # Local development server
    "http://localhost:5173",    # Vite development server
    "https://app.govertx.com",
    "https://vertx-flow-fe.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use the specific origins list instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize slides manager
slides_manager = SlidesManager()

# Initialize AI content generator
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("WARNING: GOOGLE_API_KEY environment variable not set")
    
ai_generator = AIContentGenerator(api_key=api_key) if api_key else None

# Include routers
app.include_router(auth_router)

# Define response models
class TemplateResponse(BaseModel):
    id: str
    name: str
    thumbnailLink: Optional[str] = None

class PlaceholderResponse(BaseModel):
    name: str
    instruction: Optional[str] = None
    slide_index: Optional[int] = None
    element_type: Optional[str] = None

class ContentGenerationRequest(BaseModel):
    template_id: str
    prompt: str
    thread_id: Optional[str] = None
    color_updates: Optional[Dict[str, str]] = None  # Add thread_id as optional parameter

class ContentGenerationResponse(BaseModel):
    results: Dict[str, str]
    errors: Optional[List[str]] = None
    presentation_id: Optional[str] = None
    presentation_url: Optional[str] = None
    presentation_view_url: Optional[str] = None

class ColorUsageResponse(BaseModel):
    colors: Dict[str, List[str]]

class ReplaceColorsRequest(BaseModel):
    color_replacements: Dict[str, str]  # Old color to new color mapping

@app.get("/")
async def root():
    return {"message": "Welcome to AI Pitchdeck Content Generator API"}

@app.get("/protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    """Example protected route that requires authentication"""
    return {"message": f"Authenticated as {user_id}"}

# Public endpoints that use application credentials
@app.get("/templates", response_model=List[TemplateResponse])
def get_templates(folder_name: str = "Templates"):
    """Get available presentation templates from Google Drive (public endpoint)"""
    try:
        # Use application credentials for listing templates
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get templates
        templates = slides_manager.list_templates(folder_name=folder_name)
        
        return [TemplateResponse(
            id=template.get("id"),
            name=template.get("name"),
            thumbnailLink=template.get("thumbnailLink")
        ) for template in templates]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch templates: {str(e)}")

@app.get("/templates/{template_id}/placeholders", response_model=List[PlaceholderResponse])
def get_template_placeholders(template_id: str):
    """Get all placeholders from a template presentation with their instructions"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get placeholders
        placeholders = slides_manager.get_template_placeholders(template_id)
        return placeholders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch placeholders: {str(e)}")

# Public endpoint for content generation
@app.post("/generate-content", response_model=ContentGenerationResponse)
def generate_content(request: ContentGenerationRequest, background_tasks: BackgroundTasks):
    """Generate content for placeholders based on a prompt and template ID, and optionally update colors"""
    if not ai_generator:
        raise HTTPException(status_code=500, detail="AI generator not initialized. Check GOOGLE_API_KEY environment variable.")
    
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get placeholders from the template
        placeholders = slides_manager.get_template_placeholders(request.template_id)
        
        if not placeholders:
            return ContentGenerationResponse(
                results={},
                errors=["No placeholders found in the template"]
            )
        
        # Generate content for the placeholders with thread_id for memory
        result = ai_generator.generate(request.prompt, placeholders, thread_id=request.thread_id)
        
        # Ensure result has the expected structure
        if not isinstance(result, dict):
            result = {"results": {}, "errors": [f"Unexpected result type: {type(result)}"]}
        
        if "results" not in result:
            result["results"] = {}
        
        if "errors" not in result:
            result["errors"] = []
        
        # Replace placeholders in the presentation
        # colors = slides_manager.get_theme_colors(request.template_id)
        # print(colors)
        generated_presentation_id = slides_manager.replace_placeholders(
            request.template_id, 
            result["results"]
        )

        # Update colors if color_updates is provided
        if request.color_updates:
            # theme_color_success = slides_manager.change_theme_colors(
            #     generated_presentation_id,
            #     request.color_updates
            # )
            hex_color_success = slides_manager.change_colors(
                generated_presentation_id,
                request.color_updates
            )
            if not hex_color_success:
                result["errors"].append("Failed to update colors in the presentation")

        
        # Get the URLs for the generated presentation
        presentation_edit_url = f"https://docs.google.com/presentation/d/{generated_presentation_id}/edit"
        presentation_view_url = f"https://docs.google.com/presentation/d/{generated_presentation_id}/view"
        
        # Add the presentation ID and URLs to the response
        result["presentation_id"] = generated_presentation_id
        result["presentation_url"] = presentation_edit_url
        result["presentation_view_url"] = presentation_view_url
            
        return ContentGenerationResponse(**result)
    except Exception as e:
        import traceback
        error_detail = f"Failed to generate content: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/templates/{template_id}/comments", response_model=List[Dict[str, Any]])
async def get_template_comments(template_id: str, user_id: str = Depends(get_current_user)):
    """Get all comments from a template presentation for debugging"""
    try:
        # Get user credentials from the auth system
        credentials = get_credentials(user_id)
        
        # Initialize drive service
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Get comments for the presentation
        comments_response = drive_service.comments().list(
            fileId=template_id,
            fields="comments(content,quotedFileContent)",
            includeDeleted=False
        ).execute()
        
        # Return all comments
        return comments_response.get('comments', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch comments: {str(e)}")

@app.get("/outputs", response_model=List[TemplateResponse])
async def get_outputs(user_id: str = Depends(get_current_user)):
    """Get generated presentations from the Output folder"""
    try:
        # Get user credentials from the auth system
        credentials = get_credentials(user_id)
        
        # Initialize slides manager with user credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # List presentations in the Output folder
        outputs = slides_manager.list_templates(folder_name="Output")
        
        return [TemplateResponse(
            id=output.get("id"),
            name=output.get("name"),
            thumbnailLink=output.get("thumbnailLink")
        ) for output in outputs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch outputs: {str(e)}")

@app.delete("/outputs/{presentation_id}")
async def delete_output(presentation_id: str, user_id: str = Depends(get_current_user)):
    """Delete a generated presentation"""
    try:
        # Get user credentials from the auth system
        credentials = get_credentials(user_id)
        
        # Initialize slides manager with user credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Delete the presentation
        success = slides_manager.delete_presentation(presentation_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete presentation")
        
        return {"message": "Presentation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete presentation: {str(e)}")
        
@app.get("/presentations/{presentation_id}/colors", response_model=ColorUsageResponse)
async def get_presentation_colors(presentation_id: str):
    """Get all colors used in a presentation"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get colors
        colors = slides_manager.get_presentation_colors(presentation_id)
        
        return ColorUsageResponse(colors=colors)
    except Exception as e:
        import traceback
        error_detail = f"Failed to get colors: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

class ColorUpdateRequest(BaseModel):
    color_updates: Dict[str, str]

@app.post("/presentations/{presentation_id}/colors")
async def update_presentation_colors(presentation_id: str, color_update: ColorUpdateRequest):
    """Update colors in a presentation"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Update colors
        success = slides_manager.change_colors(presentation_id, color_update.color_updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update colors")
        
        return {"message": "Colors updated successfully"}
    except Exception as e:
        import traceback
        error_detail = f"Failed to update colors: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/presentations/{presentation_id}/structure")
async def get_presentation_structure(presentation_id: str, slide_index: Optional[int] = None):
    """Get the structure of slides in a presentation"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get slide structure
        structure = slides_manager.get_slide_structure(presentation_id, slide_index)
        
        return structure
    except Exception as e:
        import traceback
        error_detail = f"Failed to get presentation structure: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/presentations/{presentation_id}/slides/{slide_index}/elements")
async def get_slide_elements(presentation_id: str, slide_index: int):
    """Get detailed information about elements in a specific slide"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get slide elements
        elements = slides_manager.get_slide_elements(presentation_id, slide_index)
        
        return elements
    except Exception as e:
        import traceback
        error_detail = f"Failed to get slide elements: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/presentations/{presentation_id}/colors/debug")
async def debug_color_changes(presentation_id: str, color_update: ColorUpdateRequest):
    """Debug color changes to see what would be updated without actually applying changes"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Debug color changes
        debug_info = slides_manager.debug_color_changes(presentation_id, color_update.color_updates)
        
        return debug_info
    except Exception as e:
        import traceback
        error_detail = f"Failed to debug color changes: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

# Credential and connection testing endpoints
@app.get("/admin/test-connection")
async def test_connection():
    """Test if credentials and connection are working"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Test connection
        result = slides_manager.test_connection()
        
        return result
    except Exception as e:
        import traceback
        error_detail = f"Failed to test connection: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/admin/credential-info")
async def get_credential_info():
    """Get information about current credentials"""
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get credential info
        result = slides_manager.get_credential_info()
        
        return result
    except Exception as e:
        import traceback
        error_detail = f"Failed to get credential info: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


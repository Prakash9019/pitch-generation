import os
from datetime import datetime
import asyncio
import time
from fastapi import Depends, FastAPI, HTTPException, Body, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from googleapiclient.discovery import build

from auth_new import router as auth_router, get_current_user, get_credentials, verify_api_key
from slides_manager import SlidesManager
from ai_content_generator import AIContentGenerator
from demo_data import get_demo_templates, get_demo_placeholders
from chat_slide_editor import ChatSlideEditor, ChatEditRequest, ChatEditResponse

import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="AI Pitchdeck Content Generator")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Add CORS middleware for specific origins (frontend domains)
origins = [
    "http://localhost:3000",    # Local development server
    "http://localhost:5173",    # Vite development server
    "http://localhost:8000",    # FastAPI development server
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
# Initialize slides manager
slides_manager = None
try:
    credentials = get_credentials(None)
    slides_manager = SlidesManager(credentials=credentials)
except Exception as e:
    print(f"WARNING: Failed to initialize SlidesManager with credentials: {e}")


# Initialize AI content generator
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("WARNING: GOOGLE_API_KEY environment variable not set")
    
ai_generator = AIContentGenerator(api_key=api_key) if api_key else None

# Initialize chat slide editor
chat_editor = None
try:
    chat_editor = ChatSlideEditor(api_key=api_key, slides_manager=slides_manager) if api_key else None
except Exception as e:
    print(f"WARNING: Failed to initialize chat slide editor: {e}")
    chat_editor = None

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

class SlideData(BaseModel):
    slide_id: str
    slide_index: int
    title: Optional[str] = None
    elements: List[Dict[str, Any]]

class PresentationData(BaseModel):
    presentation_id: str
    title: str
    slides: List[SlideData]

class UpdateSlideRequest(BaseModel):
    slide_id: str
    elements: Dict[str, Any]  # element_id -> enhanced element data
    background_color: Optional[str] = None
    theme: Optional[str] = None

class ElementData(BaseModel):
    element_id: str
    type: str  # text, image, shape, chart
    content: str
    position: Optional[Dict[str, float]] = None  # x, y coordinates
    size: Optional[Dict[str, float]] = None  # width, height
    font_size: Optional[int] = None
    font_family: Optional[str] = None
    color: Optional[str] = None
    background_color: Optional[str] = None
    font_weight: Optional[str] = None
    font_style: Optional[str] = None
    text_align: Optional[str] = None
    rotation: Optional[float] = None
    opacity: Optional[float] = None
    border_color: Optional[str] = None
    border_width: Optional[int] = None
    animation: Optional[str] = None
    animation_delay: Optional[int] = None

@app.get("/")
async def root():
    """Serve the frontend HTML file"""
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.get("/chat-editor")
async def chat_editor_page():
    """Serve the chat editor HTML file"""
    return FileResponse(os.path.join(static_dir, 'chat-editor.html'))

@app.get("/api")
async def api_root():
    return {"message": "Welcome to AI Pitchdeck Content Generator API"}

@app.get("/debug/static")
async def debug_static():
    """Debug endpoint to check static files"""
    static_files = []
    try:
        for file in os.listdir(static_dir):
            file_path = os.path.join(static_dir, file)
            if os.path.isfile(file_path):
                static_files.append({
                    "name": file,
                    "path": file_path,
                    "exists": os.path.exists(file_path),
                    "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                })
    except Exception as e:
        return {"error": str(e), "static_dir": static_dir}
    
    return {
        "static_dir": static_dir,
        "static_dir_exists": os.path.exists(static_dir),
        "files": static_files
    }

@app.get("/protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    """Example protected route that requires authentication"""
    return {"message": f"Authenticated as {user_id}"}

# Public endpoints that use application credentials
@app.get("/templates", response_model=List[TemplateResponse])
def get_templates(folder_name: str = "Templates", demo: bool = False):
    """Get available presentation templates from Google Drive (public endpoint)"""
    if demo:
        # Return demo templates for testing
        demo_templates = get_demo_templates()
        return [TemplateResponse(
            id=template.get("id"),
            name=template.get("name"),
            thumbnailLink=template.get("thumbnailLink")
        ) for template in demo_templates]
    
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
        # Fallback to demo templates if Google Drive fails
        print(f"Google Drive failed, using demo templates: {str(e)}")
        demo_templates = get_demo_templates()
        return [TemplateResponse(
            id=template.get("id"),
            name=template.get("name"),
            thumbnailLink=template.get("thumbnailLink")
        ) for template in demo_templates]

@app.get("/templates/{template_id}/placeholders", response_model=List[PlaceholderResponse])
def get_template_placeholders(template_id: str):
    """Get all placeholders from a template presentation with their instructions"""
    # Check if this is a demo template
    if template_id.startswith("demo-"):
        demo_placeholders = get_demo_placeholders(template_id)
        return demo_placeholders
    
    try:
        # Use application credentials
        credentials = get_credentials(None)
        
        # Initialize slides manager with application credentials
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get placeholders
        placeholders = slides_manager.get_template_placeholders(template_id)
        return placeholders
    except Exception as e:
        # Fallback to demo placeholders if available
        demo_placeholders = get_demo_placeholders(template_id)
        if demo_placeholders:
            print(f"Google Drive failed, using demo placeholders: {str(e)}")
            return demo_placeholders
        raise HTTPException(status_code=500, detail=f"Failed to fetch placeholders: {str(e)}")

# Public endpoint for content generation
@app.post("/generate-content", response_model=ContentGenerationResponse)
def generate_content(request: ContentGenerationRequest, background_tasks: BackgroundTasks):
    """Generate content for placeholders based on a prompt and template ID, and optionally update colors"""
    if not ai_generator:
        raise HTTPException(status_code=500, detail="AI generator not initialized. Check GOOGLE_API_KEY environment variable.")
    
    try:
        # Check if this is a demo template
        if request.template_id.startswith("demo-"):
            # Get demo placeholders
            placeholders = get_demo_placeholders(request.template_id)
            
            if not placeholders:
                return ContentGenerationResponse(
                    results={},
                    errors=["No placeholders found in the demo template"]
                )
            
            # Generate content for the placeholders with thread_id for memory
            result = ai_generator.generate(request.prompt, placeholders, thread_id=request.thread_id)
            # After generation
            print("\n===== AI MODEL RAW OUTPUT =====")
            print(result)
            print("================================\n")

            # Ensure result has the expected structure
            if not isinstance(result, dict):
                result = {"results": {}, "errors": [f"Unexpected result type: {type(result)}"]}
            
            if "results" not in result:
                result["results"] = {}
            
            if "errors" not in result:
                result["errors"] = []
            
            # For demo templates, we don't create actual presentations
            result["presentation_id"] = f"demo-presentation-{request.template_id}"
            result["presentation_url"] = "#demo-presentation"
            result["presentation_view_url"] = "#demo-presentation"
            result["errors"].append("Demo mode: No actual presentation was created. This is a demonstration of the content generation feature.")
            
            return ContentGenerationResponse(**result)
        
        # Use application credentials for real templates
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
        print("\n===== AI MODEL RAW OUTPUT =====")
        print(result)
        print("================================\n")
        return ContentGenerationResponse(**result)
    except Exception as e:
        import traceback
        error_detail = f"Failed to generate content: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/download/{presentation_id}")
def download_presentation(presentation_id: str):
    """Download the generated PowerPoint presentation"""
    file_path = os.path.join("static", f"{presentation_id}.pptx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Presentation not found")
    return FileResponse(
        file_path, 
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{presentation_id}.pptx"
    )


@app.get("/presentations/{presentation_id}/slides", response_model=PresentationData)
async def get_presentation_slides(presentation_id: str):
    """Get all slides data from a presentation for the frontend viewer"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            # Return demo slides data
            demo_slides = generate_demo_slides_data(presentation_id)
            return demo_slides
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Get presentation data
        presentation_data = slides_manager.get_presentation_slides(presentation_id)
        return presentation_data
        
    except Exception as e:
        # Fallback to demo data if available
        if presentation_id.startswith("demo-"):
            demo_slides = generate_demo_slides_data(presentation_id)
            return demo_slides
        raise HTTPException(status_code=500, detail=f"Failed to fetch presentation slides: {str(e)}")

@app.put("/presentations/{presentation_id}/slides/{slide_id}")
async def update_slide_content(presentation_id: str, slide_id: str, request: UpdateSlideRequest):
    """Update content of a specific slide"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            # For demo mode, just return success without actually updating
            return {"success": True, "message": "Demo mode: Slide updated successfully (simulation)"}
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Update slide content
        success = slides_manager.update_slide_elements(presentation_id, slide_id, request.elements)
        
        if success:
            return {"success": True, "message": "Slide updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update slide")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update slide: {str(e)}")

@app.post("/presentations/{presentation_id}/slides/{slide_id}/upload-image")
async def upload_image_to_slide(presentation_id: str, slide_id: str, file: UploadFile = File(...)):
    """Upload an image to be used in a slide"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            # For demo mode, return a placeholder image URL
            return {
                "success": True, 
                "image_url": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='150'%3E%3Crect width='200' height='150' fill='%23e9ecef'/%3E%3Ctext x='100' y='75' font-family='Arial' font-size='14' fill='%23666' text-anchor='middle'%3EDemo Image%3C/text%3E%3C/svg%3E",
                "message": "Demo mode: Image uploaded successfully (simulation)"
            }
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Read file content
        file_content = await file.read()
        
        # Upload image to Google Drive and get public URL
        image_url = slides_manager.upload_image_to_drive(file_content, file.filename, file.content_type)
        
        if image_url:
            return {
                "success": True,
                "image_url": image_url,
                "message": "Image uploaded successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload image")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

@app.put("/presentations/{presentation_id}/slides/{slide_id}/canvas")
async def update_slide_canvas(presentation_id: str, slide_id: str, canvas_data: Dict[str, Any]):
    """Update slide with canvas data including all visual elements"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            # For demo mode, just return success
            return {"success": True, "message": "Demo mode: Canvas updated successfully (simulation)"}
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Process canvas data and update slide
        success = slides_manager.update_slide_canvas(presentation_id, slide_id, canvas_data)
        
        if success:
            return {"success": True, "message": "Canvas updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update canvas")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update canvas: {str(e)}")

@app.post("/presentations/{presentation_id}/slides/{slide_id}/elements")
async def add_slide_element(presentation_id: str, slide_id: str, element: ElementData):
    """Add a new element to a slide"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            # For demo mode, return success with a generated element ID
            return {
                "success": True, 
                "element_id": f"demo_element_{int(time.time())}",
                "message": "Demo mode: Element added successfully (simulation)"
            }
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Add element to slide
        element_id = slides_manager.add_slide_element(presentation_id, slide_id, element.dict())
        
        if element_id:
            return {
                "success": True,
                "element_id": element_id,
                "message": "Element added successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add element")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add element: {str(e)}")

@app.delete("/presentations/{presentation_id}/slides/{slide_id}/elements/{element_id}")
async def delete_slide_element(presentation_id: str, slide_id: str, element_id: str):
    """Delete an element from a slide"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            return {"success": True, "message": "Demo mode: Element deleted successfully (simulation)"}
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Delete element from slide
        success = slides_manager.delete_slide_element(presentation_id, slide_id, element_id)
        
        if success:
            return {"success": True, "message": "Element deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete element")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete element: {str(e)}")

@app.post("/presentations/{presentation_id}/duplicate")
async def duplicate_presentation(presentation_id: str, new_title: Optional[str] = None):
    """Create a duplicate of an existing presentation"""
    try:
        # Check if this is a demo presentation
        if presentation_id.startswith("demo-"):
            new_id = f"demo-duplicate-{int(time.time())}"
            return {
                "success": True, 
                "new_presentation_id": new_id,
                "title": new_title or "Copy of Demo Presentation",
                "message": "Demo mode: Presentation duplicated successfully (simulation)"
            }
        
        # Use application credentials for real presentations
        credentials = get_credentials(None)
        slides_manager = SlidesManager(credentials=credentials)
        
        # Duplicate presentation
        new_presentation_id = slides_manager.duplicate_presentation(presentation_id, new_title)
        
        if new_presentation_id:
            return {
                "success": True,
                "new_presentation_id": new_presentation_id,
                "message": "Presentation duplicated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to duplicate presentation")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate presentation: {str(e)}")

def generate_demo_slides_data(presentation_id: str) -> PresentationData:
    """Generate demo slides data for the presentation viewer"""
    template_id = presentation_id.replace("demo-presentation-", "")
    
    # Get demo placeholders to create realistic slides
    placeholders = get_demo_placeholders(template_id)
    
    slides = []
    
    # Group placeholders by slide
    slides_data = {}
    for placeholder in placeholders:
        slide_idx = placeholder.get('slide_index', 1)
        if slide_idx not in slides_data:
            slides_data[slide_idx] = []
        slides_data[slide_idx].append(placeholder)
    
    # Define slide titles based on common pitch deck structure
    slide_titles = {
        1: "Company Overview",
        2: "Problem Statement", 
        3: "Our Solution",
        4: "Market Opportunity",
        5: "Business Model",
        6: "Competition & Advantage",
        7: "Team",
        8: "Funding Request"
    }
    
    # Create slide data
    for slide_idx, slide_placeholders in slides_data.items():
        slide_elements = []
        slide_title = slide_titles.get(slide_idx, f"Slide {slide_idx}")
        
        for placeholder in slide_placeholders:
            # Create more realistic placeholder content
            placeholder_content = get_placeholder_preview_content(placeholder['name'])
            
            element = {
                "element_id": f"element_{placeholder['name']}",
                "type": placeholder.get('element_type', 'text'),
                "content": placeholder_content,
                "placeholder_name": placeholder['name'],
                "editable": True
            }
            slide_elements.append(element)
        
        slides.append(SlideData(
            slide_id=f"slide_{slide_idx}",
            slide_index=slide_idx,
            title=slide_title,
            elements=slide_elements
        ))
    
    return PresentationData(
        presentation_id=presentation_id,
        title=f"AI-Generated Pitch Deck",
        slides=sorted(slides, key=lambda x: x.slide_index)
    )

def get_placeholder_preview_content(placeholder_name: str) -> str:
    """Get preview content for placeholders before AI generation"""
    preview_content = {
        "company_name": "Your Company Name",
        "tagline": "Revolutionary solution for modern problems",
        "problem_statement": "Many businesses struggle with inefficient processes that cost time and money. Current solutions are outdated and don't meet modern needs.",
        "solution_overview": "Our innovative platform streamlines operations and increases efficiency by 40% through AI-powered automation.",
        "target_market": "Small to medium businesses in the technology sector, particularly those with 50-500 employees looking to scale operations.",
        "business_model": "SaaS subscription model with tiered pricing: Basic ($99/month), Professional ($299/month), Enterprise (custom pricing).",
        "key_features": "• AI-powered automation\n• Real-time analytics dashboard\n• Seamless integrations\n• 24/7 customer support",
        "market_analysis": "The global market for business automation is valued at $12.6B and growing at 12% annually.",
        "competitive_advantage": "Our unique AI algorithm and user-friendly interface set us apart from traditional solutions.",
        "team_description": "Experienced team with backgrounds from top tech companies, combining 50+ years of industry expertise.",
        "funding_ask": "Seeking $2M Series A funding to accelerate product development and expand our sales team."
    }
    
    return preview_content.get(placeholder_name, f"[{placeholder_name.replace('_', ' ').title()}] - Content will be generated here")

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

# ========================================
# CHAT-BASED LIVE EDITING ENDPOINTS
# ========================================

@app.post("/presentations/{presentation_id}/chat-edit", response_model=ChatEditResponse)
async def chat_edit_slide(presentation_id: str, request: Dict[str, Any]):
    """
    Chat-based slide editing endpoint
    
    Allows users to edit slides using natural language commands like:
    - "Reduce the growth numbers in Slide 5"
    - "Change customer persona image on Slide 4"
    - "Make the title bigger on slide 2"
    - "Add a bullet point about market trends"
    """
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="Chat editor not initialized. Check GOOGLE_API_KEY environment variable."
        )
    
    try:
        # Get proper credentials for slides access
        credentials = get_credentials(None)
        
        # Initialize slides manager with proper credentials
        slides_manager_with_creds = SlidesManager(credentials=credentials)
        
        # Initialize chat editor with proper slides manager
        chat_editor_instance = ChatSlideEditor(api_key=api_key, slides_manager=slides_manager_with_creds)
        
        # Create chat edit request
        chat_request = ChatEditRequest(
            presentation_id=presentation_id,
            message=request.get("message", ""),
            thread_id=request.get("thread_id")
        )
        
        # Process the chat edit request
        response = await chat_editor_instance.edit_slide(chat_request)
        return response
        
    except Exception as e:
        import traceback
        error_detail = f"Failed to process chat edit: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/presentations/{presentation_id}/chat", response_model=Dict[str, Any])
async def start_chat_session(presentation_id: str):
    """
    Start a new chat editing session for a presentation
    Returns a thread_id for conversation continuity
    """
    try:
        thread_id = f"chat_{presentation_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return {
            "thread_id": thread_id,
            "presentation_id": presentation_id,
            "message": "Chat session started! You can now edit your slides using natural language. Try commands like 'reduce the numbers in slide 3' or 'change the title on slide 1'.",
            "examples": [
                "Reduce the growth numbers in Slide 5",
                "Change customer persona image on Slide 4",
                "Make the title bigger on the current slide",
                "Add a bullet point about market size to slide 3",
                "Replace the chart on slide 2 with updated data",
                "Change the color scheme to blue and white"
            ]
        }
        
    except Exception as e:
        import traceback
        error_detail = f"Failed to start chat session: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/presentations/{presentation_id}/chat/help")
async def get_chat_help():
    """
    Get help information for chat-based editing
    """
    return {
        "title": "Chat-Based Slide Editing Help",
        "description": "Edit your presentation slides using natural language commands",
        "supported_commands": {
            "content_editing": [
                "Reduce/increase numbers in slide X",
                "Change text in slide X",
                "Update the title on slide X",
                "Add/remove bullet points"
            ],
            "visual_editing": [
                "Change image on slide X",
                "Make title/text bigger/smaller",
                "Change colors to [color name]",
                "Update chart/graph data"
            ],
            "slide_management": [
                "Add a new slide after slide X",
                "Delete slide X",
                "Move slide X to position Y",
                "Duplicate slide X"
            ]
        },
        "examples": [
            {
                "command": "Reduce the growth numbers in Slide 5",
                "description": "Automatically finds numerical values in slide 5 and reduces them by a percentage"
            },
            {
                "command": "Change customer persona image on Slide 4",
                "description": "Replaces the image on slide 4 with a new customer persona image"
            },
            {
                "command": "Make the title bigger on slide 2",
                "description": "Increases the font size of the title on slide 2"
            },
            {
                "command": "Add a bullet point about market trends",
                "description": "Adds a new bullet point with market trends information to the current slide"
            }
        ],
        "tips": [
            "Be specific about which slide you want to edit",
            "Use natural language - the system understands context",
            "You can reference 'current slide' if you're viewing a specific slide",
            "Multiple changes can be made in a single command",
            "Use thread_id to maintain conversation context across multiple edits"
        ]
    }

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

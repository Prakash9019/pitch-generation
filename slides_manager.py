import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, List, Optional, Set, Any
import re
import datetime
import json
from google.auth.transport.requests import Request
class SlidesManager:
    def __init__(self, credentials=None):
        """Initialize the SlidesManager with user credentials
        
        Args:
            credentials: Google OAuth2 credentials from auth.py get_credentials()
        """
        self.credentials = credentials
        self._slides_service = None
        self._drive_service = None
        if credentials:
            self._build_services()
    
    def _build_services(self):
        """Build Google API services"""
        try:
            self._slides_service = build('slides', 'v1', credentials=self.credentials)
            self._drive_service = build('drive', 'v3', credentials=self.credentials)
        except Exception as e:
            print(f"Failed to build services: {e}")
            raise
    
    def _refresh_credentials_if_needed(self):
        """Refresh credentials if they are expired"""
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                print("Refreshing expired credentials...")
                request = Request()
                self.credentials.refresh(request)
                print("Credentials refreshed successfully")
                # Rebuild services with new credentials
                self._build_services()
                return True
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                return False
        return True
    
    def _execute_with_retry(self, api_call, *args, **kwargs):
        """Execute API call with automatic credential refresh on auth errors"""
        try:
            return api_call(*args, **kwargs).execute()
        except HttpError as e:
            if e.resp.status == 401:  # Unauthorized - credentials might be expired
                print("Got 401 error, attempting to refresh credentials...")
                if self._refresh_credentials_if_needed():
                    print("Retrying API call after credential refresh...")
                    return api_call(*args, **kwargs).execute()
                else:
                    print("Failed to refresh credentials, re-raising error")
                    raise
            else:
                raise
        except Exception as e:
            print(f"API call failed with error: {e}")
            raise
    
    @property
    def slides_service(self):
        """Get slides service, refreshing credentials if needed"""
        if self._slides_service is None and self.credentials:
            self._build_services()
        return self._slides_service
    
    @property
    def drive_service(self):
        """Get drive service, refreshing credentials if needed"""
        if self._drive_service is None and self.credentials:
            self._build_services()
        return self._drive_service
    
    async def list_templates_async(self, folder_name: str = "Templates") -> List[Dict]:
        """Async version: List available templates in the specified folder"""
        # Create a new event loop for this function
        loop = asyncio.get_event_loop()
        
        # Run the synchronous API calls in a thread pool
        return await loop.run_in_executor(
            None, lambda: self.list_templates(folder_name)
        )
    
    async def get_template_placeholders_async(self, template_id: str) -> List[Dict[str, str]]:
        """Async version: Get all placeholders from a template presentation with associated comments"""
        # Create a new event loop for this function
        loop = asyncio.get_event_loop()
        
        # Run the synchronous API calls in a thread pool
        return await loop.run_in_executor(
            None, lambda: self.get_template_placeholders(template_id)
        )
    
    async def replace_placeholders_async(self, presentation_id: str, replacements: Dict[str, str]) -> str:
        """Async version: Replace placeholders in a presentation with generated content"""
        # Create a new event_loop for this function
        loop = asyncio.get_event_loop()
        
        # Run the synchronous API calls in a thread pool
        return await loop.run_in_executor(
            None, lambda: self.replace_placeholders(presentation_id, replacements)
        )
    
    def list_templates(self, folder_name: str = "Templates") -> List[Dict]:
        """List available templates in the specified folder"""
        # Search for the folder
        folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        folder_results = self.drive_service.files().list(
            q=folder_query, spaces='drive', fields='files(id, name)').execute()
        folders = folder_results.get('files', [])
        
        if not folders:
            return []
        
        # Search for presentations in the folder
        folder_id = folders[0]['id']
        template_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.presentation'"
        template_results = self.drive_service.files().list(
            q=template_query, spaces='drive', fields='files(id, name, thumbnailLink)').execute()
        
        return template_results.get('files', [])
    
    def get_template_placeholders(self, template_id: str) -> List[Dict[str, str]]:
        """
        Get all placeholders from a template presentation with associated comments
        Placeholders are text in the format {{placeholder_name}}
        
        Returns:
            List of dictionaries with placeholder name and comment instructions
        """
        # Get the presentation
        presentation = self.slides_service.presentations().get(
            presentationId=template_id).execute()
        
        # Get comments for the presentation with more fields and maximum results
        comments_response = self.drive_service.comments().list(
            fileId=template_id,
            fields="comments(content,quotedFileContent,anchor,modifiedTime,replies)",
            includeDeleted=False,
            pageSize=100  # Request maximum number of comments
        ).execute()
        
        print(f"Found {len(comments_response.get('comments', []))} comments in the presentation")
        
        # Create a dictionary to map placeholder names to comments
        placeholder_to_comment = {}
        
        # First pass: Process all comments and extract placeholder names
        for comment in comments_response.get('comments', []):
            # Get the most recent version of the comment (either the comment itself or its latest reply)
            comment_content = comment['content']
            comment_time = comment.get('modifiedTime', '')
            
            # Check if there are replies and get the most recent one
            if 'replies' in comment and comment['replies']:
                replies = sorted(comment['replies'], key=lambda x: x.get('modifiedTime', ''), reverse=True)
                if replies and replies[0].get('content'):
                    comment_content = replies[0]['content']
                    comment_time = replies[0].get('modifiedTime', comment_time)
            
            if 'quotedFileContent' in comment and 'value' in comment['quotedFileContent']:
                quoted_text = comment['quotedFileContent']['value']
                
                print(f"Comment quoted text: {quoted_text}")
                print(f"Comment content: {comment_content}")
                print(f"Comment modified time: {comment_time}")
                
                # Extract placeholder name from the quoted text using a more flexible pattern
                # This will match {{placeholder_name}} as well as text containing it
                placeholder_pattern = re.compile(r'{{([^{}]+)}}')
                matches = placeholder_pattern.findall(quoted_text)
                
                if matches:
                    # If we found a placeholder in the quoted text, map it to the comment
                    for match in matches:
                        # Only update if this is a newer comment or we don't have one yet
                        if match not in placeholder_to_comment or comment_time > placeholder_to_comment[match]['time']:
                            placeholder_to_comment[match] = {
                                'content': comment_content,
                                'time': comment_time
                            }
        
        print(f"Found comments for {len(placeholder_to_comment)} unique placeholders")
        
        # Collect all placeholders from the presentation
        all_placeholders = set()
        placeholder_details = {}
        
        # Iterate through all slides
        for slide_index, slide in enumerate(presentation.get('slides', [])):
            # Check all page elements
            for element in slide.get('pageElements', []):
                # If the element has a shape with text
                if 'shape' in element and 'text' in element['shape']:
                    # Check all text elements in the shape
                    for text_element in element['shape']['text'].get('textElements', []):
                        if 'textRun' in text_element and 'content' in text_element['textRun']:
                            content = text_element['textRun']['content']
                            # Find all placeholders in the text
                            placeholder_pattern = re.compile(r'{{([^{}]+)}}')
                            matches = placeholder_pattern.findall(content)
                            
                            # Add each placeholder to our set and store details
                            for match in matches:
                                all_placeholders.add(match)
                                if match not in placeholder_details:
                                    placeholder_details[match] = {
                                        'name': match,
                                        'slide_index': slide_index + 1,  # 1-based for human readability
                                        'element_type': 'text'
                                    }
        
        # Build the final list of placeholders with instructions
        placeholders = []
        
        for placeholder_name in all_placeholders:
            # Get the details we stored earlier
            details = placeholder_details[placeholder_name]
            
            # Get the instruction from our comment map, or use a default
            instruction = None
            if placeholder_name in placeholder_to_comment:
                instruction = placeholder_to_comment[placeholder_name]['content']
            
            # If no instruction was found, provide a generic instruction
            if instruction is None:
                instruction = f"Provide appropriate content for {placeholder_name}"
            
            # Parse word count constraints from instruction if present
            min_words = None
            max_words = None
            if instruction:
                word_count_pattern = r"{{(\d+),(\d+)}}"
                word_count_match = re.search(word_count_pattern, instruction)
                if word_count_match:
                    min_words = int(word_count_match.group(1))
                    max_words = int(word_count_match.group(2))
            
            # Create the placeholder entry with all details
            placeholder_entry = {
                'name': placeholder_name,
                'instruction': instruction,
                'slide_index': details['slide_index'],
                'element_type': details['element_type'],
                'min_words': min_words,
                'max_words': max_words
            }
            
            placeholders.append(placeholder_entry)
        
        return placeholders

    def replace_placeholders(self, presentation_id: str, replacements: Dict[str, str]) -> str:
        """
        Replace placeholders in a presentation with generated content
        
        Args:
            presentation_id: ID of the presentation to update
            replacements: Dictionary mapping placeholders to their replacements
        
        Returns:
            ID of the updated presentation
        """
        # First, create a copy of the template
        copy_title = f"Generated Presentation - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Create or find the Output folder
        output_folder_id = self._get_or_create_output_folder()
        
        # Copy the template to the Output folder
        copied_file = self.drive_service.files().copy(
            fileId=presentation_id,
            body={
                "name": copy_title,
                "parents": [output_folder_id]  # Place in Output folder
            }
        ).execute()
        
        copied_presentation_id = copied_file['id']
        
        # Make the presentation accessible to anyone with the link with editor permissions
        self.drive_service.permissions().create(
            fileId=copied_presentation_id,
            body={
                'type': 'anyone',
                'role': 'writer',  # Changed from 'reader' to 'writer'
                'allowFileDiscovery': False
            }
        ).execute()
        
        # Prepare the requests for batch update
        requests = []
        
        # For each placeholder-replacement pair
        for placeholder, replacement in replacements.items():
            # Create a request to replace all instances of the placeholder
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': f'{{{{{placeholder}}}}}',
                        'matchCase': True
                    },
                    'replaceText': replacement
                }
            })
        
        # Execute the batch update
        if requests:
            self.slides_service.presentations().batchUpdate(
                presentationId=copied_presentation_id,  # Fixed: changed copied_id to copied_presentation_id
                body={'requests': requests}
            ).execute()
        
        return copied_presentation_id  # Return the ID of the copied presentation

    def _get_or_create_output_folder(self) -> str:
        """
        Get or create an Output folder in Google Drive
        
        Returns:
            ID of the Output folder
        """
        # Search for existing Output folder
        folder_query = "name='Output' and mimeType='application/vnd.google-apps.folder'"
        folder_results = self.drive_service.files().list(
            q=folder_query, spaces='drive', fields='files(id, name)'
        ).execute()
        
        folders = folder_results.get('files', [])
        
        # If Output folder exists, return its ID
        if folders:
            return folders[0]['id']
        
        # Otherwise, create a new Output folder
        folder_metadata = {
            'name': 'Output',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        return folder.get('id')

    def delete_presentation(self, presentation_id: str) -> bool:
        """
        Delete a presentation from Google Drive
        
        Args:
            presentation_id: ID of the presentation to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.drive_service.files().delete(fileId=presentation_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting presentation: {str(e)}")
            return False
            
    def find_colors(self, presentation_id: str) -> Dict[str, Dict[str, List[str]]]:
        """
        Find all colors used in a presentation and track where each color is used
        
        Args:
            presentation_id: ID of the presentation to analyze
            
        Returns:
            Dictionary with hex colors as keys and dictionaries of usage information as values
            Format: {
                "#RRGGBB": {
                    "usage_types": ["text", "background", "shape", etc.],
                    "slide_indices": [0, 1, 3],
                    "element_types": ["shape", "line", "table", etc.]
                }
            }
        """
        try:
            print(f"Finding colors in presentation: {presentation_id}")
            
            # Get the presentation with retry logic
            presentation = self._execute_with_retry(
                self.slides_service.presentations().get,
                presentationId=presentation_id
            )
            
            # Dictionary to store color information
            colors_info = {}
            
            # Process each slide
            slides = presentation.get('slides', [])
            print(f"Found {len(slides)} slides")
            
            for slide_index, slide in enumerate(slides):
                try:
                    print(f"Processing slide {slide_index + 1}")
                    self._find_colors_in_object(slide, colors_info, slide_index, "slide")
                except Exception as e:
                    print(f"Error processing slide {slide_index + 1}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Convert sets to lists for JSON serialization
            for color, info in colors_info.items():
                for key, value in info.items():
                    if isinstance(value, set):
                        info[key] = list(value)
            
            return colors_info
        except Exception as e:
            print(f"Error in find_colors: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty dict instead of failing
            return {}
    
    def _find_colors_in_object(self, obj: Dict, colors_info: Dict, slide_index: int, element_type: str, path: str = ""):
        """
        Recursively find all color attributes in an object
        
        Args:
            obj: Object to search for colors
            colors_info: Dictionary to update with color information
            slide_index: Index of the current slide
            element_type: Type of element being processed
            path: Current path in the object structure (for debugging)
        """
        try:
            # Base case: not a dictionary
            if not isinstance(obj, dict):
                return
            
            # Check if this is a color object
            if self._is_color_object(obj):
                hex_color = self._rgb_to_hex(obj)
                self._add_color_info(colors_info, hex_color, slide_index, element_type, path)
                return
            
            # Special handling for specific color attributes
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                
                try:
                    # Check if this is a color attribute
                    if key in ["color", "foregroundColor", "backgroundColor"] and isinstance(value, dict):
                        hex_color = self._rgb_to_hex(value)
                        usage_type = self._determine_usage_type(key, path, element_type)
                        self._add_color_info(colors_info, hex_color, slide_index, element_type, path, usage_type)
                    
                    # Handle specific structures we know contain colors
                    elif key == "solidFill" and isinstance(value, dict) and "color" in value:
                        hex_color = self._rgb_to_hex(value["color"])
                        usage_type = self._determine_usage_type("solidFill", path, element_type)
                        self._add_color_info(colors_info, hex_color, slide_index, element_type, path, usage_type)
                    
                    # Handle gradient stops
                    elif key == "stops" and isinstance(value, list):
                        for stop in value:
                            if isinstance(stop, dict) and "color" in stop:
                                hex_color = self._rgb_to_hex(stop["color"])
                                usage_type = self._determine_usage_type("gradient", path, element_type)
                                self._add_color_info(colors_info, hex_color, slide_index, element_type, path, usage_type)
                    
                    # Recursively process nested objects and arrays
                    elif isinstance(value, dict):
                        self._find_colors_in_object(value, colors_info, slide_index, element_type, new_path)
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                item_path = f"{new_path}[{i}]"
                                self._find_colors_in_object(item, colors_info, slide_index, element_type, item_path)
                except Exception as e:
                    print(f"Error processing key {key} at path {new_path}: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error in _find_colors_in_object at path {path}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _is_color_object(self, obj: Dict) -> bool:
        """
        Check if an object is a color object
        
        Args:
            obj: Object to check
            
        Returns:
            True if the object is a color object, False otherwise
        """
        # Check for rgbColor
        if "rgbColor" in obj:
            return True
        
        # Check for opaqueColor
        if "opaqueColor" in obj:
            return True
        
        # Check for direct RGB values
        if all(key in obj for key in ["red", "green", "blue"]):
            return True
        
        # Check for theme color
        if "themeColor" in obj:
            return True
        
        return False
        
    def _rgb_to_hex(self, rgb_dict: Dict[str, Any]) -> str:
        """
        Convert RGB dict from Google Slides API to hex color
        
        Args:
            rgb_dict: Dictionary containing color information from Google Slides API
        
        Returns:
            Hex color string in format #RRGGBB
        """
        # Handle empty or None input
        if not rgb_dict:
            print("Warning: Empty RGB dictionary, defaulting to black")
            return "#000000"
        
        # Debug: Print the RGB dict structure
        print(f"RGB dict: {rgb_dict}")
        
        try:
            # Handle nested color structure with opaqueColor
            if 'opaqueColor' in rgb_dict:
                return self._rgb_to_hex(rgb_dict['opaqueColor'])
            
            # Handle nested rgbColor structure
            if 'rgbColor' in rgb_dict:
                rgb_values = rgb_dict['rgbColor']
                
                # If rgbColor is empty, return black
                if not rgb_values:
                    return "#000000"
                
                # Extract RGB values and convert from 0-1 to 0-255
                r = int(float(rgb_values.get('red', 0)) * 255)
                g = int(float(rgb_values.get('green', 0)) * 255)
                b = int(float(rgb_values.get('blue', 0)) * 255)
                
                # Ensure values are in valid range
                r = max(0, min(r, 255))
                g = max(0, min(g, 255))
                b = max(0, min(b, 255))
                
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                print(f"Converted RGB to hex: {hex_color}")
                return hex_color
            
            # Check for direct RGB color space (most common)
            elif all(key in rgb_dict for key in ['red', 'green', 'blue']):
                # Extract RGB values and convert from 0-1 to 0-255
                r = int(float(rgb_dict.get('red', 0)) * 255)
                g = int(float(rgb_dict.get('green', 0)) * 255)
                b = int(float(rgb_dict.get('blue', 0)) * 255)
                
                # Ensure values are in valid range
                r = max(0, min(r, 255))
                g = max(0, min(g, 255))
                b = max(0, min(b, 255))
                
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                print(f"Converted RGB to hex: {hex_color}")
                return hex_color
            
            # Handle theme colors
            elif 'themeColor' in rgb_dict:
                # Map theme colors to hex values (these are just examples)
                theme_colors = {
                    'DARK1': '#000000',
                    'LIGHT1': '#FFFFFF',
                    'DARK2': '#333333',
                    'LIGHT2': '#EEEEEE',
                    'ACCENT1': '#4285F4',
                    'ACCENT2': '#EA4335',
                    'ACCENT3': '#FBBC05',
                    'ACCENT4': '#34A853',
                    'ACCENT5': '#8AB4F8',
                    'ACCENT6': '#F6AEA9',
                    'HYPERLINK': '#1A73E8',
                    'FOLLOWED_HYPERLINK': '#6E2EBF',
                    'TEXT1': '#000000',
                    'TEXT2': '#666666',
                    'BACKGROUND1': '#FFFFFF',
                    'BACKGROUND2': '#F8F9FA'
                }
                theme_color = rgb_dict['themeColor']
                return theme_colors.get(theme_color, "#000000")
            
            # If no recognized color format, return black
            else:
                print("Warning: Unrecognized color format, defaulting to black")
                return "#000000"
                
        except Exception as e:
            print(f"Error converting RGB to hex: {str(e)}")
            return "#000000"
    
    def _determine_usage_type(self, key: str, path: str, element_type: str) -> str:
        """
        Determine the usage type of a color based on its path and key
        
        Args:
            key: Key of the color attribute
            path: Path to the color attribute
            element_type: Type of element containing the color
            
        Returns:
            Usage type of the color
        """
        # Background colors
        if "pageBackgroundFill" in path:
            return "background"
        
        # Text colors
        if "textRun" in path and key == "foregroundColor":
            return "text"
        
        if "textRun" in path and key == "backgroundColor":
            return "text_highlight"
        
        # Shape colors
        if "shapeFill" in path:
            return "shape_fill"
        
        # Outline colors
        if "outline" in path:
            return "outline"
        
        # Line colors
        if "line" in path and "lineFill" in path:
            return "line"
        
        # Table cell colors
        if "tableCellBackgroundFill" in path:
            return "table_cell"
        
        # Bullet colors
        if "bulletStyle" in path:
            return "bullet"
        
        # Default to the key name
        return key
    
    def _add_color_info(self, colors_info: Dict, hex_color: str, slide_index: int, 
                        element_type: str, path: str, usage_type: str = None):
        """
        Add color information to the colors_info dictionary
        
        Args:
            colors_info: Dictionary to update
            hex_color: Hex color code
            slide_index: Index of the slide
            element_type: Type of element
            path: Path to the color attribute
            usage_type: Type of usage for the color
        """
        # Skip default black when it's likely not an intentional color choice
        if hex_color == "#000000" and not path.endswith("color"):
            return
            
        # Initialize if this is a new color
        if hex_color not in colors_info:
            colors_info[hex_color] = {
                "usage_types": set(),
                "slide_indices": set(),
                "element_types": set(),
                "paths": set()  # For debugging
            }
        
        # Add information
        if usage_type:
            colors_info[hex_color]["usage_types"].add(usage_type)
        
        colors_info[hex_color]["slide_indices"].add(slide_index)
        colors_info[hex_color]["element_types"].add(element_type)
        colors_info[hex_color]["paths"].add(path)
        
        # Log the found color
        if usage_type:
            print(f"Found color {hex_color} used as {usage_type} in slide {slide_index + 1}, element type: {element_type}")
        else:
            print(f"Found color {hex_color} in slide {slide_index + 1}, element type: {element_type}")
            
    def get_presentation_colors(self, presentation_id: str) -> Dict[str, List[str]]:
        """
        Get all colors used in a presentation with simplified usage information
        
        Args:
            presentation_id: ID of the presentation to analyze
            
        Returns:
            Dictionary with hex colors as keys and lists of usage types as values
        """
        try:
            # Find all colors and their detailed usage
            colors_info = self.find_colors(presentation_id)
            
            # Simplify the output
            simplified_colors = {}
            for color, info in colors_info.items():
                if "usage_types" in info:
                    simplified_colors[color] = info["usage_types"]
                else:
                    # If usage_types is missing, provide a default
                    simplified_colors[color] = ["unknown"]
            
            return simplified_colors
        except Exception as e:
            print(f"Error in get_presentation_colors: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty dict instead of failing
            return {}
    
    def change_colors(self, presentation_id: str, color_updates: Dict[str, str]) -> bool:
        """
        Update colors in text, shapes (fill and background), lines, and tables by replacing matching hex values.
        """
        try:
            # Get the presentation with retry logic
            presentation = self._execute_with_retry(
                self.slides_service.presentations().get,
                presentationId=presentation_id
            )

            requests = []

            for slide in presentation.get("slides", []):
                for element in slide.get("pageElements", []):
                    object_id = element.get("objectId")

                    # --- TEXT COLOR ---
                    text_elements = element.get('shape', {}).get('text', {}).get('textElements', [])
                    for text_el in text_elements:
                        style = text_el.get('textRun', {}).get('style', {})
                        fg_color = style.get('foregroundColor', {}).get('opaqueColor', {}).get('rgbColor')
                        if fg_color:
                            old_hex = self._rgb_to_hex({'rgbColor': fg_color})
                            if old_hex in color_updates:
                                r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                                requests.append({
                                    'updateTextStyle': {
                                        'objectId': object_id,
                                        'textRange': {'type': 'ALL'},
                                        'style': {
                                            'foregroundColor': {
                                                'opaqueColor': {
                                                    'rgbColor': {'red': r, 'green': g, 'blue': b}
                                                }
                                            }
                                        },
                                        'fields': 'foregroundColor'
                                    }
                                })

                    # --- SHAPE BACKGROUND COLOR ---
                    shape_props = element.get('shape', {}).get('shapeProperties', {})
                    bg_color_data = shape_props.get('shapeBackgroundFill', {}).get('solidFill', {}).get('color', {})
                    bg_rgb = bg_color_data.get('rgbColor') or bg_color_data.get('opaqueColor', {}).get('rgbColor')
                    if bg_rgb:
                        old_hex = self._rgb_to_hex({'rgbColor': bg_rgb})
                        if old_hex in color_updates:
                            r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                            requests.append({
                                'updateShapeProperties': {
                                    'objectId': object_id,
                                    'shapeProperties': {
                                        'shapeBackgroundFill': {
                                            'solidFill': {
                                                'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                            }
                                        }
                                    },
                                    'fields': 'shapeBackgroundFill.solidFill.color'
                                }
                            })

                    # --- SHAPE FILL COLOR ---
                    fill_color_data = shape_props.get('solidFill', {}).get('color', {})
                    fill_rgb = fill_color_data.get('rgbColor') or fill_color_data.get('opaqueColor', {}).get('rgbColor')
                    if fill_rgb:
                        old_hex = self._rgb_to_hex({'rgbColor': fill_rgb})
                        if old_hex in color_updates:
                            r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                            requests.append({
                                'updateShapeProperties': {
                                    'objectId': object_id,
                                    'shapeProperties': {
                                        'solidFill': {
                                            'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                        }
                                    },
                                    'fields': 'solidFill.color'
                                }
                            })

                    # --- LINE COLOR ---
                    line_color_data = element.get('line', {}).get('lineProperties', {}).get('lineFill', {}).get('solidFill', {}).get('color', {})
                    line_rgb = line_color_data.get('rgbColor') or line_color_data.get('opaqueColor', {}).get('rgbColor')
                    if line_rgb:
                        old_hex = self._rgb_to_hex({'rgbColor': line_rgb})
                        if old_hex in color_updates:
                            r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                            requests.append({
                                'updateLineProperties': {
                                    'objectId': object_id,
                                    'lineProperties': {
                                        'lineFill': {
                                            'solidFill': {
                                                'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                            }
                                        }
                                    },
                                    'fields': 'lineFill.solidFill.color'
                                }
                            })

                    # --- TABLE CELL BACKGROUND COLOR ---
                    if 'table' in element:
                        rows = element['table'].get('tableRows', [])
                        for row_idx, row in enumerate(rows):
                            for col_idx, cell in enumerate(row.get('tableCells', [])):
                                cell_color_data = cell.get('tableCellProperties', {}).get('tableCellBackgroundFill', {}).get('solidFill', {}).get('color', {})
                                cell_rgb = cell_color_data.get('rgbColor') or cell_color_data.get('opaqueColor', {}).get('rgbColor')
                                if cell_rgb:
                                    old_hex = self._rgb_to_hex({'rgbColor': cell_rgb})
                                    if old_hex in color_updates:
                                        r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                                        requests.append({
                                            'updateTableCellProperties': {
                                                'objectId': object_id,
                                                'tableRange': {
                                                    'location': {'rowIndex': row_idx, 'columnIndex': col_idx},
                                                    'rowSpan': 1,
                                                    'columnSpan': 1
                                                },
                                                'tableCellProperties': {
                                                    'tableCellBackgroundFill': {
                                                        'solidFill': {
                                                            'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                                        }
                                                    }
                                                },
                                                'fields': 'tableCellBackgroundFill.solidFill.color'
                                            }
                                        })

            if requests:
                # Execute batch update with retry logic
                self._execute_with_retry(
                    self.slides_service.presentations().batchUpdate,
                    presentationId=presentation_id,
                    body={'requests': requests}
                )

            return True

        except Exception as e:
            print(f"Error in change_colors: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    # def get_theme_colors(self, presentation_id: str) -> Dict[str, str]:
    #     """
    #     Fetch the theme color scheme from the given presentation.

    #     Returns:
    #         A dictionary mapping theme color slots (e.g., 'ACCENT1') to their hex color value.
    #     """
    #     try:
    #         presentation = self.slides_service.presentations().get(
    #             presentationId=presentation_id
    #         ).execute()

    #         masters = presentation.get("masters", [])
    #         if not masters:
    #             print("❌ No master slides found in presentation.")
    #             return {}

    #         master = masters[0]

    #         # 🔍 Write full master dump for debugging
    #         with open("theme_debug_dump.json", "w", encoding="utf-8") as f:
    #             json.dump(master, f, indent=2)
    #             print("📝 Theme debug structure written to theme_debug_dump.json")

    #         # ✅ Try all known paths to colorScheme
    #         color_scheme = (
    #             master.get("theme", {}).get("colorScheme", {}).get("colors") or
    #             master.get("colorScheme", {}).get("colors") or
    #             master.get("pageProperties", {}).get("colorScheme", {}).get("colors")
    #         )

    #         if not color_scheme:
    #             print("❌ No color scheme found in any known location.")
    #             return {}

    #         result = {}

    #         print("--- Raw theme color scheme ---")
    #         print(json.dumps(color_scheme, indent=2))

    #         for color_entry in color_scheme:
    #             key = color_entry.get("type")
    #             color_data = color_entry.get("color", {})
    #             rgb = color_data.get("rgbColor") or color_data  # support both formats

    #             if not key or not isinstance(rgb, dict):
    #                 print(f"⚠️ Skipping invalid theme color: {key} → {color_data}")
    #                 continue

    #             r = int(rgb.get("red", 0) * 255)
    #             g = int(rgb.get("green", 0) * 255)
    #             b = int(rgb.get("blue", 0) * 255)
    #             hex_color = f"#{r:02x}{g:02x}{b:02x}"
    #             result[key] = hex_color

    #         print("--- Final theme color hex map ---")
    #         print(json.dumps(result, indent=2))

    #         return result

    #     except Exception as e:
    #         print(f"Error fetching theme colors: {str(e)}")
    #         import traceback
    #         traceback.print_exc()
    #         return {}

    # def change_theme_colors(self, presentation_id: str, theme_color_updates: Dict[str, str]) -> bool:
    #     """
    #     Update elements styled with themeColor (e.g., ACCENT1) by replacing them with custom RGB values.
    #     """
    #     try:
    #         presentation = self.slides_service.presentations().get(
    #             presentationId=presentation_id
    #         ).execute()
            

    #         requests = []

    #         def hex_to_rgb(hex_color):
    #             hex_color = hex_color.lstrip("#")
    #             return {
    #                 "red": int(hex_color[0:2], 16) / 255.0,
    #                 "green": int(hex_color[2:4], 16) / 255.0,
    #                 "blue": int(hex_color[4:6], 16) / 255.0
    #             }

    #         for slide in presentation.get("slides", []):
    #             for element in slide.get("pageElements", []):
    #                 object_id = element.get("objectId")

    #                 # --- TEXT COLOR ---
    #                 text_elements = element.get('shape', {}).get('text', {}).get('textElements', [])
    #                 for text_el in text_elements:
    #                     style = text_el.get('textRun', {}).get('style', {})
    #                     fg = style.get('foregroundColor', {}).get('opaqueColor', {})
    #                     theme_color = fg.get("themeColor")
    #                     if theme_color and theme_color in theme_color_updates:
    #                         rgb = hex_to_rgb(theme_color_updates[theme_color])
    #                         requests.append({
    #                             'updateTextStyle': {
    #                                 'objectId': object_id,
    #                                 'textRange': {'type': 'ALL'},
    #                                 'style': {
    #                                     'foregroundColor': {
    #                                         'opaqueColor': {
    #                                             'rgbColor': rgb
    #                                         }
    #                                     }
    #                                 },
    #                                 'fields': 'foregroundColor'
    #                             }
    #                         })

    #                 # --- SHAPE FILL COLOR ---
    #                 shape_props = element.get('shape', {}).get('shapeProperties', {})
    #                 fill = shape_props.get('solidFill', {})
    #                 theme_color = fill.get('color', {}).get('themeColor')
    #                 if theme_color and theme_color in theme_color_updates:
    #                     rgb = hex_to_rgb(theme_color_updates[theme_color])
    #                     requests.append({
    #                         'updateShapeProperties': {
    #                             'objectId': object_id,
    #                             'shapeProperties': {
    #                                 'solidFill': {
    #                                     'color': {'rgbColor': rgb}
    #                                 }
    #                             },
    #                             'fields': 'solidFill.color'
    #                         }
    #                     })

    #                 # --- SHAPE BACKGROUND FILL ---
    #                 bg_fill = shape_props.get('shapeBackgroundFill', {}).get('solidFill', {}).get('color', {})
    #                 theme_color = bg_fill.get('themeColor')
    #                 if theme_color and theme_color in theme_color_updates:
    #                     rgb = hex_to_rgb(theme_color_updates[theme_color])
    #                     requests.append({
    #                         'updateShapeProperties': {
    #                             'objectId': object_id,
    #                             'shapeProperties': {
    #                                 'shapeBackgroundFill': {
    #                                     'solidFill': {
    #                                         'color': {'rgbColor': rgb}
    #                                     }
    #                                 }
    #                             },
    #                             'fields': 'shapeBackgroundFill.solidFill.color'
    #                         }
    #                     })

    #                 # --- LINE COLOR ---
    #                 line_props = element.get('line', {}).get('lineProperties', {})
    #                 theme_color = line_props.get('lineFill', {}).get('solidFill', {}).get('color', {}).get('themeColor')
    #                 if theme_color and theme_color in theme_color_updates:
    #                     rgb = hex_to_rgb(theme_color_updates[theme_color])
    #                     requests.append({
    #                         'updateLineProperties': {
    #                             'objectId': object_id,
    #                             'lineProperties': {
    #                                 'lineFill': {
    #                                     'solidFill': {
    #                                         'color': {'rgbColor': rgb}
    #                                     }
    #                                 }
    #                             },
    #                             'fields': 'lineFill.solidFill.color'
    #                         }
    #                     })

    #                 # --- TABLE CELL BACKGROUND ---
    #                 if 'table' in element:
    #                     rows = element['table'].get('tableRows', [])
    #                     for row_idx, row in enumerate(rows):
    #                         for col_idx, cell in enumerate(row.get('tableCells', [])):
    #                             theme_color = cell.get('tableCellProperties', {}).get(
    #                                 'tableCellBackgroundFill', {}).get('solidFill', {}).get('color', {}).get('themeColor')
    #                             if theme_color and theme_color in theme_color_updates:
    #                                 rgb = hex_to_rgb(theme_color_updates[theme_color])
    #                                 requests.append({
    #                                     'updateTableCellProperties': {
    #                                         'objectId': object_id,
    #                                         'tableRange': {
    #                                             'location': {
    #                                                 'rowIndex': row_idx,
    #                                                 'columnIndex': col_idx
    #                                             },
    #                                             'rowSpan': 1,
    #                                             'columnSpan': 1
    #                                         },
    #                                         'tableCellProperties': {
    #                                             'tableCellBackgroundFill': {
    #                                                 'solidFill': {
    #                                                     'color': {'rgbColor': rgb}
    #                                                 }
    #                                             }
    #                                         },
    #                                         'fields': 'tableCellBackgroundFill.solidFill.color'
    #                                     }
    #                                 })

    #         # --- SLIDE BACKGROUND COLOR ---
    #         for slide in presentation.get("slides", []):
    #             page_bg = slide.get("pageProperties", {}).get("pageBackgroundFill", {}).get("solidFill", {}).get("color", {})
    #             theme_color = page_bg.get("themeColor")
    #             if theme_color and theme_color in theme_color_updates:
    #                 rgb = hex_to_rgb(theme_color_updates[theme_color])
    #                 requests.append({
    #                     'updatePageProperties': {
    #                         'objectId': slide.get("objectId"),
    #                         'pageProperties': {
    #                             'pageBackgroundFill': {
    #                                 'solidFill': {
    #                                     'color': {'rgbColor': rgb}
    #                                 }
    #                             }
    #                         },
    #                         'fields': 'pageBackgroundFill.solidFill.color'
    #                     }
    #                 })

    #         if requests:
    #             self.slides_service.presentations().batchUpdate(
    #                 presentationId=presentation_id,
    #                 body={'requests': requests}
    #             ).execute()

    #         return True

    #     except Exception as e:
    #         print(f"Error updating theme colors: {str(e)}")
    #         import traceback
    #         traceback.print_exc()
    #         return False

    def get_slide_structure(self, presentation_id: str, slide_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the structure of slides in a presentation
        
        Args:
            presentation_id: ID of the presentation to analyze
            slide_index: Optional specific slide index (0-based). If None, returns all slides
            
        Returns:
            Dictionary containing slide structure information
        """
        try:
            print(f"Getting slide structure for presentation: {presentation_id}")
            
            # Get the presentation
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id).execute()
            
            slides = presentation.get('slides', [])
            print(f"Found {len(slides)} slides")
            
            if slide_index is not None:
                # Return specific slide
                if 0 <= slide_index < len(slides):
                    slide = slides[slide_index]
                    return {
                        "presentation_id": presentation_id,
                        "slide_index": slide_index,
                        "total_slides": len(slides),
                        "slide_data": slide
                    }
                else:
                    return {
                        "error": f"Slide index {slide_index} out of range. Presentation has {len(slides)} slides."
                    }
            else:
                # Return all slides with basic info
                slides_info = []
                for idx, slide in enumerate(slides):
                    slide_info = {
                        "slide_index": idx,
                        "slide_id": slide.get('objectId', 'unknown'),
                        "elements_count": len(slide.get('pageElements', [])),
                        "layout_id": slide.get('slideProperties', {}).get('layoutObjectId', 'unknown')
                    }
                    slides_info.append(slide_info)
                
                return {
                    "presentation_id": presentation_id,
                    "total_slides": len(slides),
                    "slides_overview": slides_info
                }
                
        except Exception as e:
            print(f"Error getting slide structure: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to get slide structure: {str(e)}"}

    def get_slide_elements(self, presentation_id: str, slide_index: int) -> Dict[str, Any]:
        """
        Get detailed information about elements in a specific slide
        
        Args:
            presentation_id: ID of the presentation to analyze
            slide_index: Slide index (0-based)
            
        Returns:
            Dictionary containing detailed element information
        """
        try:
            print(f"Getting elements for slide {slide_index} in presentation: {presentation_id}")
            
            # Get the presentation
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id).execute()
            
            slides = presentation.get('slides', [])
            
            if not (0 <= slide_index < len(slides)):
                return {
                    "error": f"Slide index {slide_index} out of range. Presentation has {len(slides)} slides."
                }
            
            slide = slides[slide_index]
            elements = slide.get('pageElements', [])
            
            elements_info = []
            for element in elements:
                element_info = {
                    "object_id": element.get('objectId', 'unknown'),
                    "element_type": self._get_element_type(element),
                    "transform": element.get('transform', {}),
                    "size": element.get('size', {}),
                }
                
                # Add type-specific information
                if 'shape' in element:
                    shape = element['shape']
                    element_info['shape_type'] = shape.get('shapeType', 'unknown')
                    element_info['text'] = shape.get('text', {}).get('textElements', [])
                    element_info['shape_properties'] = shape.get('shapeProperties', {})
                elif 'line' in element:
                    element_info['line_properties'] = element['line'].get('lineProperties', {})
                elif 'table' in element:
                    table = element['table']
                    element_info['table_rows'] = table.get('rows', 0)
                    element_info['table_columns'] = table.get('columns', 0)
                elif 'image' in element:
                    element_info['image_properties'] = element['image'].get('imageProperties', {})
                
                elements_info.append(element_info)
            
            return {
                "presentation_id": presentation_id,
                "slide_index": slide_index,
                "total_elements": len(elements),
                "elements": elements_info
            }
                
        except Exception as e:
            print(f"Error getting slide elements: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to get slide elements: {str(e)}"}

    def _get_element_type(self, element: Dict[str, Any]) -> str:
        """Helper method to determine element type"""
        if 'shape' in element:
            return 'shape'
        elif 'line' in element:
            return 'line'
        elif 'table' in element:
            return 'table'
        elif 'image' in element:
            return 'image'
        elif 'video' in element:
            return 'video'
        elif 'sheetsChart' in element:
            return 'sheets_chart'
        elif 'wordArt' in element:
            return 'word_art'
        else:
            return 'unknown'

    def debug_color_changes(self, presentation_id: str, color_updates: Dict[str, str]) -> Dict[str, Any]:
        """
        Debug method to see what color change requests would be generated without actually applying them
        
        Args:
            presentation_id: ID of the presentation to analyze
            color_updates: Dictionary mapping old hex colors to new hex colors
            
        Returns:
            Dictionary containing debug information about color changes
        """
        try:
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id).execute()

            requests = []
            found_colors = {}
            processed_elements = []

            for slide_idx, slide in enumerate(presentation.get("slides", [])):
                for element_idx, element in enumerate(slide.get("pageElements", [])):
                    object_id = element.get("objectId")
                    element_info = {
                        "slide_index": slide_idx,
                        "element_index": element_idx,
                        "object_id": object_id,
                        "element_type": self._get_element_type(element),
                        "colors_found": [],
                        "requests_generated": []
                    }

                    # --- TEXT COLOR ---
                    text_elements = element.get('shape', {}).get('text', {}).get('textElements', [])
                    for text_el in text_elements:
                        style = text_el.get('textRun', {}).get('style', {})
                        fg_color = style.get('foregroundColor', {}).get('opaqueColor', {}).get('rgbColor')
                        if fg_color:
                            old_hex = self._rgb_to_hex({'rgbColor': fg_color})
                            element_info["colors_found"].append({
                                "type": "text_color",
                                "hex": old_hex,
                                "rgb": fg_color
                            })
                            if old_hex not in found_colors:
                                found_colors[old_hex] = []
                            found_colors[old_hex].append(f"slide_{slide_idx}_element_{element_idx}_text")
                            
                            if old_hex in color_updates:
                                r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                                request = {
                                    'updateTextStyle': {
                                        'objectId': object_id,
                                        'textRange': {'type': 'ALL'},
                                        'style': {
                                            'foregroundColor': {
                                                'opaqueColor': {
                                                    'rgbColor': {'red': r, 'green': g, 'blue': b}
                                                }
                                            }
                                        },
                                        'fields': 'foregroundColor'
                                    }
                                }
                                requests.append(request)
                                element_info["requests_generated"].append({
                                    "type": "text_color_update",
                                    "old_color": old_hex,
                                    "new_color": color_updates[old_hex],
                                    "request": request
                                })

                    # --- SHAPE BACKGROUND COLOR ---
                    shape_props = element.get('shape', {}).get('shapeProperties', {})
                    bg_color_data = shape_props.get('shapeBackgroundFill', {}).get('solidFill', {}).get('color', {})
                    bg_rgb = bg_color_data.get('rgbColor') or bg_color_data.get('opaqueColor', {}).get('rgbColor')
                    if bg_rgb:
                        old_hex = self._rgb_to_hex({'rgbColor': bg_rgb})
                        element_info["colors_found"].append({
                            "type": "shape_background",
                            "hex": old_hex,
                            "rgb": bg_rgb
                        })
                        if old_hex not in found_colors:
                            found_colors[old_hex] = []
                        found_colors[old_hex].append(f"slide_{slide_idx}_element_{element_idx}_shape_bg")
                        
                        if old_hex in color_updates:
                            r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                            request = {
                                'updateShapeProperties': {
                                    'objectId': object_id,
                                    'shapeProperties': {
                                        'shapeBackgroundFill': {
                                            'solidFill': {
                                                'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                            }
                                        }
                                    },
                                    'fields': 'shapeBackgroundFill.solidFill.color'
                                }
                            }
                            requests.append(request)
                            element_info["requests_generated"].append({
                                "type": "shape_background_update",
                                "old_color": old_hex,
                                "new_color": color_updates[old_hex],
                                "request": request
                            })

                    # --- SHAPE FILL COLOR ---
                    fill_color_data = shape_props.get('solidFill', {}).get('color', {})
                    fill_rgb = fill_color_data.get('rgbColor') or fill_color_data.get('opaqueColor', {}).get('rgbColor')
                    if fill_rgb:
                        old_hex = self._rgb_to_hex({'rgbColor': fill_rgb})
                        element_info["colors_found"].append({
                            "type": "shape_fill",
                            "hex": old_hex,
                            "rgb": fill_rgb
                        })
                        if old_hex not in found_colors:
                            found_colors[old_hex] = []
                        found_colors[old_hex].append(f"slide_{slide_idx}_element_{element_idx}_shape_fill")
                        
                        if old_hex in color_updates:
                            r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                            request = {
                                'updateShapeProperties': {
                                    'objectId': object_id,
                                    'shapeProperties': {
                                        'solidFill': {
                                            'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                        }
                                    },
                                    'fields': 'solidFill.color'
                                }
                            }
                            requests.append(request)
                            element_info["requests_generated"].append({
                                "type": "shape_fill_update",
                                "old_color": old_hex,
                                "new_color": color_updates[old_hex],
                                "request": request
                            })

                    # --- LINE COLOR ---
                    line_color_data = element.get('line', {}).get('lineProperties', {}).get('lineFill', {}).get('solidFill', {}).get('color', {})
                    line_rgb = line_color_data.get('rgbColor') or line_color_data.get('opaqueColor', {}).get('rgbColor')
                    if line_rgb:
                        old_hex = self._rgb_to_hex({'rgbColor': line_rgb})
                        element_info["colors_found"].append({
                            "type": "line_color",
                            "hex": old_hex,
                            "rgb": line_rgb
                        })
                        if old_hex not in found_colors:
                            found_colors[old_hex] = []
                        found_colors[old_hex].append(f"slide_{slide_idx}_element_{element_idx}_line")
                        
                        if old_hex in color_updates:
                            r, g, b = [int(color_updates[old_hex][i:i+2], 16) / 255.0 for i in (1, 3, 5)]
                            request = {
                                'updateLineProperties': {
                                    'objectId': object_id,
                                    'lineProperties': {
                                        'lineFill': {
                                            'solidFill': {
                                                'color': {'rgbColor': {'red': r, 'green': g, 'blue': b}}
                                            }
                                        }
                                    },
                                    'fields': 'lineFill.solidFill.color'
                                }
                            }
                            requests.append(request)
                            element_info["requests_generated"].append({
                                "type": "line_color_update",
                                "old_color": old_hex,
                                "new_color": color_updates[old_hex],
                                "request": request
                            })

                    # Only add element info if it has colors or requests
                    if element_info["colors_found"] or element_info["requests_generated"]:
                        processed_elements.append(element_info)

            return {
                "presentation_id": presentation_id,
                "color_updates_requested": color_updates,
                "total_requests_generated": len(requests),
                "all_colors_found": found_colors,
                "processed_elements": processed_elements,
                "requests": requests
            }

        except Exception as e:
            print(f"Error in debug_color_changes: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to debug color changes: {str(e)}"}

    def test_connection(self) -> Dict[str, any]:
        """
        Test if the connection and credentials are working
        
        Returns:
            Dictionary with test results
        """
        try:
            # Test with a simple Drive API call
            about = self._execute_with_retry(
                self.drive_service.about().get,
                fields="user"
            )
            
            return {
                "status": "success",
                "user_email": about.get("user", {}).get("emailAddress", "unknown"),
                "message": "Connection and credentials are working correctly",
                "credentials_expired": self.credentials.expired if self.credentials else False,
                "credentials_valid": self.credentials.valid if self.credentials else False
            }
            
        except HttpError as e:
            return {
                "status": "error",
                "error_code": e.resp.status,
                "message": f"HTTP Error: {e.resp.reason}",
                "details": str(e),
                "credentials_expired": self.credentials.expired if self.credentials else None,
                "credentials_valid": self.credentials.valid if self.credentials else None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "details": str(e),
                "credentials_expired": self.credentials.expired if self.credentials else None,
                "credentials_valid": self.credentials.valid if self.credentials else None
            }

    def get_credential_info(self) -> Dict[str, any]:
        """
        Get information about current credentials
        
        Returns:
            Dictionary with credential information
        """
        if not self.credentials:
            return {"status": "no_credentials", "message": "No credentials available"}
        
        try:
            return {
                "status": "credentials_available",
                "expired": self.credentials.expired,
                "valid": self.credentials.valid,
                "has_refresh_token": bool(self.credentials.refresh_token),
                "expiry": self.credentials.expiry.isoformat() if self.credentials.expiry else None,
                "scopes": self.credentials.scopes if hasattr(self.credentials, 'scopes') else None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting credential info: {str(e)}"
            }

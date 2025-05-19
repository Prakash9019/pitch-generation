from googleapiclient.discovery import build
from typing import Dict, List, Optional, Set
import re
import datetime

class SlidesManager:
    def __init__(self, credentials=None):
        """Initialize the SlidesManager with user credentials
        
        Args:
            credentials: Google OAuth2 credentials from auth.py get_credentials()
        """
        self.credentials = credentials
        if credentials:
            self.slides_service = build('slides', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
    
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
        
        # Get comments for the presentation
        comments_response = self.drive_service.comments().list(
            fileId=template_id,
            fields="comments(content,quotedFileContent)",
            includeDeleted=False
        ).execute()
        
        # Debug: Print all comments to understand what's being returned
        print(f"Found {len(comments_response.get('comments', []))} comments in the presentation")
        
        # Create a dictionary to map quoted text to comments
        comment_map = {}
        for comment in comments_response.get('comments', []):
            if 'quotedFileContent' in comment and 'value' in comment['quotedFileContent']:
                quoted_text = comment['quotedFileContent']['value']
                print(f"Comment quoted text: {quoted_text}")
                print(f"Comment content: {comment['content']}")
                
                # Check if the quoted text contains a placeholder pattern
                if '{{' in quoted_text and '}}' in quoted_text:
                    comment_map[quoted_text] = comment['content']
        
        print(f"Mapped {len(comment_map)} comments to placeholders")
        
        placeholders = []
        placeholder_pattern = re.compile(r'{{([^{}]+)}}')
        
        # Iterate through all slides
        for slide_index, slide in enumerate(presentation.get('slides', [])):
            # Check all page elements
            for element_index, element in enumerate(slide.get('pageElements', [])):
                # If the element has a shape with text
                if 'shape' in element and 'text' in element['shape']:
                    # Check all text elements in the shape
                    for text_element in element['shape']['text'].get('textElements', []):
                        if 'textRun' in text_element and 'content' in text_element['textRun']:
                            content = text_element['textRun']['content']
                            # Find all placeholders in the text
                            matches = placeholder_pattern.findall(content)
                            # Add new placeholders while preserving order
                            for match in matches:
                                # Check if this placeholder is already in our list
                                if not any(p['name'] == match for p in placeholders):
                                    # Look for a comment associated with this placeholder
                                    instruction = None
                                    placeholder_with_braces = f"{{{{{match}}}}}"
                                    
                                    # Try different ways to match comments to placeholders
                                    for quoted_text, comment_content in comment_map.items():
                                        # Exact match
                                        if placeholder_with_braces == quoted_text.strip():
                                            instruction = comment_content
                                            print(f"Exact match found for {placeholder_with_braces}")
                                            break
                                        # Placeholder is contained in the quoted text
                                        elif placeholder_with_braces in quoted_text:
                                            instruction = comment_content
                                            print(f"Partial match found for {placeholder_with_braces} in {quoted_text}")
                                            break
                                    
                                    # Add placeholder with instruction (which may be None)
                                    placeholders.append({
                                        'name': match,
                                        'instruction': instruction,
                                        'slide_index': slide_index + 1,  # 1-based for human readability
                                        'element_type': 'text'
                                    })
        
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
        copied_file = self.drive_service.files().copy(
            fileId=presentation_id,
            body={"name": copy_title}
        ).execute()
        
        copied_id = copied_file.get('id')
        
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
                presentationId=copied_id,
                body={'requests': requests}
            ).execute()
        
        return copied_id

import asyncio
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






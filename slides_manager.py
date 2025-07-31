"""
Manages interactions with the Google Slides and Google Drive APIs.
Handles fetching presentation data, creating copies, and applying updates.
"""
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

class SlidesManager:
    """A wrapper for the Google Slides and Drive APIs."""

    def __init__(self, credentials: Optional[Credentials] = None):
        """
        Initializes the SlidesManager.

        Args:
            credentials: Google OAuth2 credentials. Must be provided for the manager to function.
        """
        if not credentials:
            raise ValueError("Credentials are required to initialize SlidesManager.")
        self.credentials = credentials
        self._slides_service = None
        self._drive_service = None
        self._build_services()

    def _build_services(self):
        """Builds the Google API service clients."""
        try:
            self._slides_service = build('slides', 'v1', credentials=self.credentials)
            self._drive_service = build('drive', 'v3', credentials=self.credentials)
        except Exception as e:
            print(f"Error: Failed to build Google API services: {e}")
            raise

    def _refresh_credentials_if_needed(self):
        """Refreshes credentials if they are expired and a refresh token is available."""
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                print("Credentials expired. Attempting to refresh...")
                self.credentials.refresh(Request())
                self._build_services() # Rebuild services with the new token
                print("Credentials refreshed successfully.")
                return True
            except Exception as e:
                print(f"Error: Failed to refresh credentials: {e}")
                return False
        return True

    def _execute_with_retry(self, api_call, *args, **kwargs):
        """
        Executes an API call with a single retry attempt after refreshing credentials
        if an authorization (401) error occurs.
        """
        try:
            return api_call(*args, **kwargs).execute()
        except HttpError as e:
            if e.resp.status == 401:
                print("Authorization error (401). Refreshing credentials and retrying...")
                if self._refresh_credentials_if_needed():
                    return api_call(*args, **kwargs).execute()
            # Re-raise the error if it's not a 401 or if refresh fails
            raise

    def get_presentation_slides(self, presentation_id: str) -> Dict[str, Any]:
        """
        Fetches a structured representation of a presentation, optimized for the editing agent.

        Args:
            presentation_id: The ID of the Google Slides presentation.

        Returns:
            A dictionary containing the presentation title and a list of slides,
            where each slide contains a list of its text-containing elements.
        """
        print(f"  -> Fetching presentation data for ID: {presentation_id}")
        if not self._slides_service:
            raise Exception("Slides service is not initialized.")

        try:
            presentation = self._execute_with_retry(
                self._slides_service.presentations().get,
                presentationId=presentation_id
            )

            slides_data = []
            for slide_index, slide in enumerate(presentation.get('slides', [])):
                slide_elements = []
                title_element = None

                for element in slide.get('pageElements', []):
                    # We are interested in shapes that contain text
                    if 'shape' in element and 'text' in element['shape']:
                        text_content = ""
                        for text_run in element['shape']['text'].get('textElements', []):
                            if 'textRun' in text_run:
                                text_content += text_run['textRun'].get('content', '')
                        
                        # Heuristic to identify the title: often the first non-empty text box
                        if not title_element and text_content.strip():
                            title_element = text_content.strip()

                        slide_elements.append({
                            "element_id": element['objectId'],
                            "type": "text",
                            "content": text_content.strip(),
                        })
                
                slides_data.append({
                    "slide_id": slide['objectId'],
                    "slide_index": slide_index,
                    "title": title_element or f"Slide {slide_index + 1}",
                    "elements": slide_elements
                })

            return {
                "presentation_id": presentation_id,
                "title": presentation.get('title', 'Untitled Presentation'),
                "slides": slides_data
            }
        except Exception as e:
            print(f"Error getting presentation slides: {e}")
            raise

    def update_slide_elements(self, presentation_id: str, slide_id: str, elements: Dict[str, str]) -> bool:
        """
        Updates the content of one or more text elements on a specific slide.

        Args:
            presentation_id: The ID of the presentation.
            slide_id: The ID of the slide containing the elements.
            elements: A dictionary mapping element_id to its new text content.

        Returns:
            True if the update was successful, False otherwise.
        """
        if not self._slides_service:
            raise Exception("Slides service is not initialized.")

        try:
            requests = []
            for element_id, new_content in elements.items():
                # First, delete the existing text in the shape.
                requests.append({
                    'deleteText': {
                        'objectId': element_id,
                        'textRange': {'type': 'ALL'}
                    }
                })
                # Then, insert the new text.
                requests.append({
                    'insertText': {
                        'objectId': element_id,
                        'text': new_content,
                        'insertionIndex': 0
                    }
                })

            if requests:
                body = {'requests': requests}
                self._execute_with_retry(
                    self._slides_service.presentations().batchUpdate,
                    presentationId=presentation_id,
                    body=body
                )
            
            print(f"  -> Successfully executed {len(requests)} requests for slide {slide_id}.")
            return True
        except Exception as e:
            print(f"Error updating slide elements: {e}")
            return False

    # Keep other methods like list_templates, duplicate_presentation etc. as they are.

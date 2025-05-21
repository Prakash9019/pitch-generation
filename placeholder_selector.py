import asyncio
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
import re

class Placeholder(BaseModel):
    """Model representing a placeholder in a slide template."""
    name: str
    instruction: Optional[str] = None
    slide_index: Optional[int] = None
    element_type: Optional[str] = None
    min_words: Optional[int] = None
    max_words: Optional[int] = None

class PlaceholderGroup(BaseModel):
    """Group of placeholders for a specific slide."""
    slide_index: int
    placeholders: List[Placeholder]
    slide_title: Optional[str] = None

class PlaceholderSelector:
    """Selects and groups placeholders by slide index."""
    
    def __init__(self):
        pass
    
    def _parse_word_constraints(self, instruction: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse word count constraints from instruction if present."""
        if not instruction:
            return None, None
            
        # Look for pattern like {{27,30}} in the instruction
        pattern = r"{{(\d+),(\d+)}}"
        match = re.search(pattern, instruction)
        
        if match:
            min_words = int(match.group(1))
            max_words = int(match.group(2))
            return min_words, max_words
        
        return None, None
    
    def process_placeholders(self, placeholders: List[Dict]) -> List[Placeholder]:
        """Process raw placeholders and extract constraints."""
        result = []
        
        for p in placeholders:
            min_words, max_words = self._parse_word_constraints(p.get("instruction", ""))
            
            # Create Placeholder object with word constraints
            placeholder = Placeholder(
                name=p["name"],
                instruction=p.get("instruction", ""),
                slide_index=p.get("slide_index", 0),
                element_type=p.get("element_type", ""),
                min_words=min_words,
                max_words=max_words
            )
            
            result.append(placeholder)
            
        return result
        
    def group_by_slide(self, placeholders: List[Placeholder]) -> List[PlaceholderGroup]:
        """Group placeholders by slide index."""
        # Create a dictionary to store placeholders by slide index
        slides_dict: Dict[int, List[Placeholder]] = {}
        
        # Group placeholders by slide index
        for placeholder in placeholders:
            slide_index = placeholder.slide_index or 0
            if slide_index not in slides_dict:
                slides_dict[slide_index] = []
            slides_dict[slide_index].append(placeholder)
        
        # Convert dictionary to list of PlaceholderGroup objects
        result = []
        for slide_index, slide_placeholders in slides_dict.items():
            result.append(
                PlaceholderGroup(
                    slide_index=slide_index,
                    placeholders=slide_placeholders
                )
            )
        
        # Sort by slide index
        result.sort(key=lambda x: x.slide_index)
        return result
    
    def __call__(self, placeholders: List) -> List[PlaceholderGroup]:
        """Make the selector callable directly."""
        # Process raw placeholders if they're dictionaries
        if placeholders and isinstance(placeholders[0], dict):
            placeholders = self.process_placeholders(placeholders)
            
        return self.group_by_slide(placeholders)


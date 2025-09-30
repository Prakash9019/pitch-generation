import os
import re
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from pydantic import BaseModel, Field
from placeholder_selector import Placeholder, PlaceholderGroup, PlaceholderSelector

# Configure Google Generative AI
api_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

class WorkflowState(BaseModel):
    """State for the pitch deck generation workflow."""
    prompt: str = Field(description="The user's prompt for generating the pitch deck")
    placeholders: List[Any] = Field(default_factory=list, description="List of placeholders from the template")
    placeholder_groups: List[PlaceholderGroup] = Field(default_factory=list, description="Placeholders grouped by slide")
    generated_content: Dict[str, str] = Field(default_factory=dict, description="Generated content for each placeholder")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during generation")

def select_placeholders(state: WorkflowState) -> WorkflowState:
    """Group placeholders by slide index."""
    selector = PlaceholderSelector()
    
    # Process the placeholders using the appropriate method
    # First process raw placeholders if they're dictionaries
    if state.placeholders and isinstance(state.placeholders[0], dict):
        processed_placeholders = selector.process_placeholders(state.placeholders)
        placeholder_groups = selector.group_by_slide(processed_placeholders)
    else:
        # If they're already Placeholder objects, just group them
        placeholder_groups = selector.group_by_slide(state.placeholders)
    
    return {"placeholder_groups": placeholder_groups}

def generate_slide_content(state: WorkflowState) -> WorkflowState:
    """Generate content for each slide's placeholders using Google Generative AI directly."""
    
    try:
        # Initialize the Gemini model directly (not through LangChain)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        generated_content = {}
        errors = []
        
        # Gather all placeholders from all groups
        all_placeholders = []
        for group in state.placeholder_groups:
            all_placeholders.extend(group.placeholders)
        
        # Process placeholders sequentially
        for placeholder in all_placeholders:
            try:
                # Determine exact word count requirements
                word_count_text = ""
                target_count = None
                
                if placeholder.min_words and placeholder.max_words:
                    if placeholder.min_words == placeholder.max_words:
                        word_count_text = f"EXACTLY {placeholder.min_words} words"
                        target_count = placeholder.min_words
                    else:
                        # For ranges, aim for the middle or slightly above minimum
                        target_count = max(placeholder.min_words, (placeholder.min_words + placeholder.max_words) // 2)
                        word_count_text = f"between {placeholder.min_words} and {placeholder.max_words} words (aim for {target_count})"
                elif placeholder.max_words:
                    word_count_text = f"EXACTLY {placeholder.max_words} words"
                    target_count = placeholder.max_words
                elif placeholder.min_words:
                    word_count_text = f"EXACTLY {placeholder.min_words} words"
                    target_count = placeholder.min_words
                else:
                    word_count_text = "an appropriate number of words"
                
                # Get the instruction for this placeholder
                instruction = placeholder.instruction or "Provide content for this placeholder"
                
                # Create the prompt
                system_prompt = f"""You are an expert pitch deck creator specializing in professional business presentations.
Your task is to generate content for a placeholder using {word_count_text}.

CRITICAL REQUIREMENTS:
1. MEET THE EXACT WORD COUNT REQUIREMENT
2. FOLLOW THE SPECIFIC INSTRUCTION FOR THIS PLACEHOLDER
3. Create professional, engaging content suitable for investors

Count words carefully - each word separated by spaces counts as one word.
Examples: 'We are' is 2 words. 'State-of-the-art' is 4 words.

Context: {state.prompt}
Placeholder: {placeholder.name}
Instruction: {instruction}
Word Count Required: {word_count_text}

Generate ONLY the content, without any explanations or formatting."""

                # Generate content using Gemini directly
                response = model.generate_content(system_prompt)
                content = response.text.strip()
                
                # Verify word count and retry if needed
                word_count = len(content.split())
                max_retries = 2
                retry_count = 0
                
                while target_count and abs(word_count - target_count) > 2 and retry_count < max_retries:
                    word_difference = target_count - word_count
                    action = "add more words" if word_difference > 0 else "remove words"
                    
                    retry_prompt = f"""The previous content had {word_count} words, but I need EXACTLY {target_count} words.
Previous content: "{content}"

Please rewrite this to have EXACTLY {target_count} words by {action}.
Keep the same meaning and professional tone.
Context: {state.prompt}

Generate ONLY the revised content, without explanations."""

                    retry_response = model.generate_content(retry_prompt)
                    content = retry_response.text.strip()
                    word_count = len(content.split())
                    retry_count += 1
                
                # Store the content
                generated_content[placeholder.name] = content
                
                # Log successful generation
                print(f"Generated content for {placeholder.name}: {word_count} words")
                
            except Exception as e:
                error_msg = f"Error generating content for placeholder {placeholder.name}: {str(e)}"
                errors.append(error_msg)
                generated_content[placeholder.name] = f"[Content for {placeholder.name}]"
                print(f"Error: {error_msg}")
        
    except Exception as e:
        error_msg = f"Error in generate_slide_content: {str(e)}"
        errors.append(error_msg)
        print(f"Critical error: {error_msg}")
        # Return empty content if there's a critical error
        generated_content = {p.name: f"[Content for {p.name}]" for group in state.placeholder_groups for p in group.placeholders}
    
    return {"generated_content": generated_content, "errors": errors}

class AIContentGenerator:
    """Generates content for pitch deck placeholders using Google Generative AI."""
    
    def __init__(self, template_id: str, prompt: str, placeholders: List[Any]):
        """Initialize the content generator."""
        self.template_id = template_id
        self.prompt = prompt
        self.placeholders = placeholders
    
    async def generate(self) -> tuple[Dict[str, str], List[str], str]:
        """Generate content for placeholders based on the prompt."""
        
        # Create presentation ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        presentation_id = f"demo-presentation-{self.template_id}-{timestamp}" if self.template_id.startswith('demo-') else f"presentation-{self.template_id}-{timestamp}"
        
        try:
            # Initialize the workflow state
            initial_state = WorkflowState(
                prompt=self.prompt,
                placeholders=self.placeholders
            )
            
            # Process placeholders
            state_after_selection = select_placeholders(initial_state)
            initial_state.placeholder_groups = state_after_selection["placeholder_groups"]
            
            # Generate content
            result = generate_slide_content(initial_state)
            
            # Return results
            return result["generated_content"], result["errors"], presentation_id
            
        except Exception as e:
            error_msg = f"Critical error in content generation: {str(e)}"
            print(f"Error: {error_msg}")
            
            # Return fallback content
            fallback_content = {}
            for placeholder in self.placeholders:
                if isinstance(placeholder, dict):
                    fallback_content[placeholder["name"]] = f"[Content for {placeholder['name']}]"
                else:
                    fallback_content[placeholder.name] = f"[Content for {placeholder.name}]"
            
            return fallback_content, [error_msg], presentation_id
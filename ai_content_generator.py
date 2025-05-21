import os
import re
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
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
    """Generate content for each slide's placeholders."""
    # Try a different model that might be better at following instructions
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")  # Use pro instead of flash
    generated_content = {}
    errors = []
    
    try:
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
                
                # Create a prompt specifically for this placeholder
                instruction = placeholder.instruction or "Provide content for this placeholder"
                
                # Enhanced system message with more explicit instructions about visual consequences
                system_message = (
                    "You are an expert pitch deck creator specializing in professional business presentations.\n"
                    f"Your task is to generate content for a placeholder using {word_count_text}.\n"
                    "CRITICAL: The EXACT word count is the most important requirement - more important than any other aspect.\n\n"
                    f"VISUAL CONSEQUENCES: If you provide fewer words than required, the slide will look empty with awkward white space.\n"
                    f"If you exceed the maximum word count, text will overflow and be cut off, making the presentation look unprofessional.\n\n"
                    "Count words carefully - each word separated by spaces counts as one word.\n"
                    "Examples: 'We are' is 2 words. 'State-of-the-art' is 4 words.\n"
                    "Your performance will be evaluated primarily on meeting the word count requirement."
                )
                
                # Enhanced human message with examples of properly expanded content
                human_message = (
                    f"Generate content for the placeholder: {placeholder.name}\n"
                    f"This placeholder appears on slide {placeholder.slide_index}.\n"
                    f"Instruction: {instruction}\n"
                    f"Context: {state.prompt}\n\n"
                    f"CRITICAL: Your response must contain {word_count_text}. This text will appear on a professional pitch deck viewed by potential investors.\n\n"
                    "EXAMPLES OF PROPERLY EXPANDED CONTENT:\n"
                    "Basic (15 words): Our company offers innovative solutions for businesses seeking to improve their digital transformation processes.\n\n"
                    "Expanded (25 words): Our award-winning company delivers cutting-edge, customizable solutions for forward-thinking businesses actively seeking to accelerate and improve their comprehensive digital transformation processes.\n\n"
                    "Further Expanded (35 words): Our award-winning company consistently delivers cutting-edge, highly customizable solutions for forward-thinking businesses actively seeking to accelerate, streamline, and fundamentally improve their comprehensive digital transformation processes across multiple departments and operational functions.\n\n"
                    "SPECIFIC EXPANSION TECHNIQUES:\n"
                    "1. Add descriptive adjectives before nouns: 'solutions' → 'innovative, scalable solutions'\n"
                    "2. Include benefits: 'We offer services' → 'We offer comprehensive services that increase efficiency'\n"
                    "3. Add context: 'market trends' → 'market trends in today's rapidly evolving business landscape'\n"
                    "4. Specify details: 'technology' → 'cloud-based AI technology with machine learning capabilities'\n\n"
                    "WORD COUNT VERIFICATION INSTRUCTIONS:\n"
                    "- After writing your response, count the words manually by counting each space-separated term\n"
                    "- If below the requirement, add more descriptive details until you reach the exact count\n"
                    "- If above the requirement, remove less essential details until you reach the exact count\n\n"
                    "Provide ONLY the content, without any explanations or formatting."
                )
                
                if target_count and target_count > 20:
                    # For longer content, give more specific guidance
                    human_message += f"\n\nThis requires {target_count} words, which is substantial content. The slide template has been precisely designed for {target_count} words - no more, no less. Make sure to develop your ideas fully with supporting details."
                
                placeholder_prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=system_message),
                    HumanMessage(content=human_message)
                ])
                
                # Generate content for this specific placeholder
                start_time = time.time()
                response = placeholder_prompt | llm | StrOutputParser()
                content = response.invoke({})
                content = content.strip()
                
                # Save original content before any modifications
                original_content = content
                original_word_count = len(content.split())
                
                # Verify word count
                word_count = original_word_count
                
                # Try up to 3 times if the word count is significantly off
                max_retries = 3
                retry_count = 0
                previous_content = content  # Store the previous content for each retry

                while target_count and abs(word_count - target_count) > 5 and retry_count < max_retries:
                    # Calculate exactly how many words to add or remove
                    word_difference = target_count - word_count
                    action_text = f"add {word_difference} more words" if word_difference > 0 else f"remove {abs(word_difference)} words"
                    
                    # Create a more specific prompt for the retry with clear instructions
                    retry_message = (
                        f"Your previous response had {word_count} words, but I need EXACTLY {target_count} words.\n"
                        f"Previous content: \"{previous_content}\"\n\n"
                        f"Please rewrite this to have EXACTLY {target_count} words by {action_text}.\n"
                        f"Word count difference: {word_difference} words {'too few' if word_difference > 0 else 'too many'}\n\n"
                        "Specific instructions:\n"
                        f"1. {action_text} while preserving the core meaning\n"
                        f"2. If adding words: Add descriptive adjectives, context details, or supporting points\n"
                        f"3. If removing words: Remove less important modifiers or redundant phrases\n"
                        f"4. Ensure the final text is coherent and professionally written\n"
                        f"5. Count carefully - each space-separated term counts as one word\n\n"
                        "The word count must be EXACT - this is critical for the slide layout."
                    )
                    
                    retry_prompt = ChatPromptTemplate.from_messages([
                        SystemMessage(content=system_message),
                        HumanMessage(content=retry_message)
                    ])
                    
                    # Try again
                    retry_response = retry_prompt | llm | StrOutputParser()
                    content = retry_response.invoke({}).strip()
                    word_count = len(content.split())
                    
                    # Update previous content for the next retry
                    previous_content = content
                    retry_count += 1
                
                # Store the content
                generated_content[placeholder.name] = content
                
                # Add error if word count still doesn't match
                if placeholder.max_words and word_count > placeholder.max_words:
                    error_msg = f"Content for {placeholder.name} has {word_count} words, but maximum is {placeholder.max_words}"
                    errors.append(error_msg)
                
                if placeholder.min_words and word_count < placeholder.min_words:
                    error_msg = f"Content for {placeholder.name} has {word_count} words, but minimum is {placeholder.min_words}"
                    errors.append(error_msg)
                
            except Exception as e:
                error_msg = f"Error generating content for placeholder {placeholder.name}: {str(e)}"
                errors.append(error_msg)
                generated_content[placeholder.name] = f"[Content for {placeholder.name}]"
    
    except Exception as e:
        error_msg = f"Error in generate_slide_content: {str(e)}"
        errors.append(error_msg)
    
    return {"generated_content": generated_content, "errors": errors}

def create_pitch_deck_workflow() -> StateGraph:
    """Create the workflow for generating pitch deck content."""
    # Define the workflow
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("select_placeholders", select_placeholders)
    workflow.add_node("generate_slide_content", generate_slide_content)
    
    # Define edges
    workflow.add_edge("select_placeholders", "generate_slide_content")
    workflow.add_edge("generate_slide_content", END)
    
    # Set the entry point
    workflow.set_entry_point("select_placeholders")
    
    return workflow.compile()

class AIContentGenerator:
    """Generates content for pitch deck placeholders."""
    
    def __init__(self, api_key: str = None):
        """Initialize the content generator."""
        if api_key:
            genai.configure(api_key=api_key)
        self.workflow = create_pitch_deck_workflow()
    
    def generate(self, prompt: str, placeholders: List[Any]) -> Dict[str, Any]:
        """Generate content for placeholders based on the prompt."""
        # Initialize the workflow state
        initial_state = WorkflowState(
            prompt=prompt,
            placeholders=placeholders
        )
        
        # Execute the workflow
        result = self.workflow.invoke(initial_state)
        
        # Return the results - LangGraph returns an AddableValuesDict, not the state object
        return {
            "results": result["generated_content"],
            "errors": result["errors"]
        }
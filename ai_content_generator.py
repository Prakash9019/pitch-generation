import os
import re
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
    placeholder_groups = selector(state.placeholders)
    return {"placeholder_groups": placeholder_groups}

def generate_slide_content(state: WorkflowState) -> WorkflowState:
    """Generate content for each slide's placeholders."""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    generated_content = {}
    errors = []
    
    # First, create a list of all placeholder names for validation
    all_placeholder_names = []
    for group in state.placeholder_groups:
        for placeholder in group.placeholders:
            all_placeholder_names.append(placeholder.name.upper())
    
    for group in state.placeholder_groups:
        # Create a prompt for this slide's content
        placeholder_instructions = []
        
        for p in group.placeholders:
            instruction = p.instruction or "Provide content for this placeholder"
            
            # Add word count constraints if present
            constraint_text = ""
            if p.min_words and p.max_words:
                constraint_text = f" (Use between {p.min_words} and {p.max_words} words)"
            
            placeholder_instructions.append(f"- {p.name}: {instruction}{constraint_text}")
        
        instructions_text = "\n".join(placeholder_instructions)
        
        slide_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an expert pitch deck creator specializing in professional business presentations. "
                "Generate concise, compelling content for each placeholder based on the user's requirements. "
                "Use professional business language that is clear, impactful, and persuasive. "
                "Ensure you provide content for EVERY placeholder listed. "
                "If word count constraints are specified, strictly adhere to them.\n\n"
                "IMPORTANT: Format your response with ONE placeholder per line, with each placeholder "
                "on its own line starting with the placeholder name followed by a colon. "
                "DO NOT combine multiple placeholders in a single response."
            )),
            HumanMessage(content=(
                f"Slide {group.slide_index} placeholders:\n{instructions_text}\n\n"
                f"User requirements: {state.prompt}\n\n"
                "For each placeholder, generate appropriate content. Format your response as:\n"
                "PLACEHOLDER_NAME: content\n\n"
                "IMPORTANT: Each placeholder must be on its own line. Do not combine multiple placeholders in one response."
            ))
        ])
        
        try:
            # Generate content for this slide
            response = slide_prompt | llm | StrOutputParser()
            result = response.invoke({})
            
            # Improved parsing logic to handle combined placeholders
            # Split the response by lines and look for placeholder patterns
            lines = result.strip().split("\n")
            
            # Process each line
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line contains a placeholder
                for placeholder_name in all_placeholder_names:
                    pattern = rf"{placeholder_name}\s*:"
                    match = re.search(pattern, line, re.IGNORECASE)
                    
                    if match:
                        # Extract the content after the placeholder name
                        content_start = match.end()
                        content = line[content_start:].strip()
                        
                        # Find the actual placeholder object to get the correct case
                        actual_name = None
                        for group in state.placeholder_groups:
                            for p in group.placeholders:
                                if p.name.upper() == placeholder_name:
                                    actual_name = p.name
                                    break
                            if actual_name:
                                break
                        
                        if actual_name:
                            generated_content[actual_name] = content
                        
                        # Remove this part from the line to avoid double-counting
                        line = line[:match.start()] + line[content_start + len(content):]
            
            # Verify all placeholders have content
            for placeholder in group.placeholders:
                if placeholder.name not in generated_content:
                    errors.append(f"Missing content for placeholder: {placeholder.name} in slide {group.slide_index}")
                else:
                    # Verify word count constraints
                    content = generated_content[placeholder.name]
                    word_count = len(content.split())
                    
                    if placeholder.min_words and word_count < placeholder.min_words:
                        errors.append(f"Content for {placeholder.name} has {word_count} words, but minimum is {placeholder.min_words}")
                    
                    if placeholder.max_words and word_count > placeholder.max_words:
                        # Truncate to max words if too long
                        words = content.split()
                        generated_content[placeholder.name] = " ".join(words[:placeholder.max_words])
                        errors.append(f"Content for {placeholder.name} was truncated to {placeholder.max_words} words")
                        
        except Exception as e:
            errors.append(f"Error generating content for slide {group.slide_index}: {str(e)}")
    
    # Second pass: Generate content for any missing placeholders one by one
    missing_placeholders = []
    for group in state.placeholder_groups:
        for placeholder in group.placeholders:
            if placeholder.name not in generated_content:
                missing_placeholders.append(placeholder)
    
    for placeholder in missing_placeholders:
        try:
            # Generate content for each missing placeholder individually
            instruction = placeholder.instruction or "Provide content for this placeholder"
            constraint_text = ""
            if placeholder.min_words and placeholder.max_words:
                constraint_text = f" (Use between {placeholder.min_words} and {placeholder.max_words} words)"
            
            single_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=(
                    "You are an expert pitch deck creator. Generate content for a single placeholder."
                )),
                HumanMessage(content=(
                    f"Generate content for the placeholder: {placeholder.name}\n"
                    f"Instruction: {instruction}{constraint_text}\n"
                    f"Context: {state.prompt}\n"
                    f"This is for slide {placeholder.slide_index} of a business presentation.\n\n"
                    f"Provide ONLY the content, without the placeholder name or any formatting."
                ))
            ])
            
            single_response = single_prompt | llm | StrOutputParser()
            content = single_response.invoke({}).strip()
            
            # Add the content
            generated_content[placeholder.name] = content
            
            # Verify word count constraints
            word_count = len(content.split())
            if placeholder.min_words and word_count < placeholder.min_words:
                errors.append(f"Content for {placeholder.name} has {word_count} words, but minimum is {placeholder.min_words}")
            
            if placeholder.max_words and word_count > placeholder.max_words:
                # Truncate to max words if too long
                words = content.split()
                generated_content[placeholder.name] = " ".join(words[:placeholder.max_words])
                errors.append(f"Content for {placeholder.name} was truncated to {placeholder.max_words} words")
                
        except Exception as e:
            # Use a generic placeholder as last resort
            generated_content[placeholder.name] = f"[Content for {placeholder.name}]"
            errors.append(f"Used generic content for placeholder: {placeholder.name} - Error: {str(e)}")
    
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





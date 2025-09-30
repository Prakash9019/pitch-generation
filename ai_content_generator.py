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
from langgraph.checkpoint.memory import MemorySaver  # Using the specific import path
from pydantic import BaseModel, Field

from placeholder_selector import Placeholder, PlaceholderGroup, PlaceholderSelector



# Configure Google Generative AI
api_key = os.environ.get("GOOGLE_API_KEY")
print("API Key:", api_key)  # Debugging line to check if the API key is being read
if api_key:
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
    # --- FIX START ---
    # Use the LangChain compatible model wrapper, which is a "Runnable"
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
    # --- FIX END ---
    
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
                
                # Get the instruction for this placeholder
                instruction = placeholder.instruction or "Provide content for this placeholder"
                
                # Extract example from instruction if available
                example = None
                if instruction and '"' in instruction:
                    # Extract text between quotes as example
                    import re
                    quoted_text = re.findall(r'"([^"]*)"', instruction)
                    if quoted_text:
                        example = quoted_text[0]
                
                # Enhanced system message with more explicit instructions
                system_message = (
                    "You are an expert pitch deck creator specializing in professional business presentations.\n"
                    f"Your task is to generate content for a placeholder using {word_count_text}.\n"
                    "CRITICAL REQUIREMENTS (in order of importance):\n"
                    "1. FOLLOW THE EXACT FORMAT OF THE EXAMPLE if one is provided\n"
                    "2. MEET THE EXACT WORD COUNT REQUIREMENT\n"
                    "3. FOLLOW THE SPECIFIC INSTRUCTION FOR THIS PLACEHOLDER\n\n"
                    f"VISUAL CONSEQUENCES: If you provide fewer words than required, the slide will look empty with awkward white space.\n"
                    f"If you exceed the maximum word count, text will overflow and be cut off, making the presentation look unprofessional.\n\n"
                    "Count words carefully - each word separated by spaces counts as one word.\n"
                    "Examples: 'We are' is 2 words. 'State-of-the-art' is 4 words.\n"
                    "Your performance will be evaluated primarily on following the example format and meeting the word count requirement."
                )
                
                # Enhanced human message with emphasis on following the example
                human_message = (
                    f"Generate content for the placeholder: {placeholder.name}\n"
                    f"This placeholder appears on slide {placeholder.slide_index}.\n\n"
                )
                
                # Add instruction with clear formatting
                human_message += f"INSTRUCTION: {instruction}\n\n"
                
                # Add example with clear formatting if available
                if example:
                    human_message += f"EXAMPLE FORMAT TO FOLLOW: \"{example}\"\n\n"
                    human_message += (
                        f"Your content MUST follow the EXACT SAME STYLE, TONE, AND FORMAT as this example.\n"
                        f"Study the example carefully - notice its structure, language style, and formatting.\n"
                        f"Your response should look like it belongs in the same document as the example.\n\n"
                    )
                
                # Add context and requirements
                human_message += (
                    f"Context: {state.prompt}\n\n"
                    f"CRITICAL: Your response must contain {word_count_text}.\n"
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
                
                # --- FIX START ---
                # Generate content for this specific placeholder using the correct 'llm' object
                start_time = time.time()
                response = placeholder_prompt | llm | StrOutputParser()
                # --- FIX END ---
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

                while target_count and abs(word_count - target_count) > 2 and retry_count < max_retries:
                    # Calculate exactly how many words to add or remove
                    word_difference = target_count - word_count
                    is_adding = word_difference > 0
                    action_text = f"add {word_difference} more words" if is_adding else f"remove {abs(word_difference)} words"
                    
                    # Create a more specific prompt for the retry with clear instructions
                    retry_message = (
                        f"Your previous response had {word_count} words, but I need EXACTLY {target_count} words.\n"
                        f"Previous content: \"{previous_content}\"\n\n"
                    )
                    
                    # Add example with clear formatting if available
                    if example:
                        retry_message += f"EXAMPLE FORMAT TO FOLLOW: \"{example}\"\n\n"
                        retry_message += f"Your content MUST follow the EXACT SAME STYLE, TONE, AND FORMAT as this example.\n\n"
                    
                    # Customize instructions based on whether we're adding or removing words
                    if is_adding:
                        strategy_text = (
                            f"To add {word_difference} words while preserving meaning:\n"
                            "1. Expand descriptions with relevant adjectives and adverbs\n"
                            "2. Add supporting details or examples that reinforce the main points\n"
                            "3. Break complex sentences into multiple simpler sentences\n"
                            "4. Add context or background information that enhances understanding\n"
                        )
                    else:
                        strategy_text = (
                            f"To remove {abs(word_difference)} words while preserving meaning:\n"
                            "1. Remove redundant phrases and unnecessary modifiers\n"
                            "2. Replace verbose phrases with concise alternatives\n"
                            "3. Combine sentences that express related ideas\n"
                            "4. Focus on the most important points and remove less critical details\n"
                            "5. Prioritize keeping key terminology and main arguments intact\n"
                        )
                    
                    retry_message += (
                        f"Please rewrite this to have EXACTLY {target_count} words by {action_text}.\n"
                        f"Word count difference: {word_difference} words {'too few' if is_adding else 'too many'}\n\n"
                        f"STRATEGY: {strategy_text}\n\n"
                        "CRITICAL REQUIREMENTS:\n"
                        "1. MAINTAIN THE CORE MEANING of the original content\n"
                        f"2. FOLLOW THE EXACT SAME FORMAT as the example if provided\n"
                        "3. Count carefully - each space-separated term counts as one word\n"
                        "4. The word count must be EXACTLY {target_count} - this is critical for the slide layout\n\n"
                        "Provide ONLY the revised content, without any explanations."
                    )
                    
                    retry_prompt = ChatPromptTemplate.from_messages([
                        SystemMessage(content=system_message),
                        HumanMessage(content=retry_message)
                    ])
                    
                    # --- FIX START ---
                    # Try again using the correct 'llm' object
                    retry_response = retry_prompt | llm | StrOutputParser()
                    # --- FIX END ---
                    content = retry_response.invoke({}).strip()
                    word_count = len(content.split())
                    
                    # If we're still far off, try a more aggressive approach on the last retry
                    if retry_count == max_retries - 1 and abs(word_count - target_count) > 5:
                        # For removing words, try truncating and fixing
                        if word_count > target_count:
                            # Split into words, take exactly the target count, and join
                            words = content.split()[:target_count]
                            truncated = " ".join(words)
                            
                            # Fix the truncated content to make it coherent
                            fix_message = (
                                f"I've truncated the content to exactly {target_count} words, but it may not be coherent:\n"
                                f"\"{truncated}\"\n\n"
                                f"Please fix this to make it coherent while keeping EXACTLY {target_count} words and preserving the core meaning."
                            )
                            
                            fix_prompt = ChatPromptTemplate.from_messages([
                                SystemMessage(content=system_message),
                                HumanMessage(content=fix_message)
                            ])
                            
                            # --- FIX START ---
                            fix_response = fix_prompt | llm | StrOutputParser()
                            # --- FIX END ---
                            content = fix_response.invoke({}).strip()
                            word_count = len(content.split())
                    
                    # Update previous content for the next retry
                    previous_content = content
                    retry_count += 1
                
                # Store the content
                generated_content[placeholder.name] = content
                
                # Add error if word count still doesn't match (with small tolerance)
                tolerance = 2  # Allow 2 words tolerance for better user experience
                
                if placeholder.max_words and word_count > (placeholder.max_words + tolerance):
                    error_msg = f"Content for {placeholder.name} has {word_count} words, but maximum is {placeholder.max_words}"
                    errors.append(error_msg)
                
                if placeholder.min_words and word_count < (placeholder.min_words - tolerance):
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
    """Create the workflow for generating pitch deck content with memory."""
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
    
    # Add memory checkpointer using the specific import
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

class AIContentGenerator:
    """Generates content for pitch deck placeholders with LangGraph memory."""
    
    def __init__(self, api_key: str = None):
        """Initialize the content generator."""
        if api_key:
            genai.configure(api_key=api_key)
        self.workflow = create_pitch_deck_workflow()
    
    def generate(self, prompt: str, placeholders: List[Any], thread_id: str = None) -> Dict[str, Any]:
        """Generate content for placeholders based on the prompt with memory."""
        # Initialize the workflow state
        initial_state = WorkflowState(
            prompt=prompt,
            placeholders=placeholders
        )
        
        # Create a thread_id if not provided (for conversation persistence)
        if not thread_id:
            thread_id = f"thread_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Execute the workflow with thread_id for memory persistence
        config = {"configurable": {"thread_id": thread_id}}
        result = self.workflow.invoke(initial_state, config)
        
        # Return the results
        return {
            "results": result["generated_content"],
            "errors": result["errors"],
            "thread_id": thread_id  # Return thread_id for future calls
        }
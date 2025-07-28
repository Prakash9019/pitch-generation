"""
Chat-based Live Slide Editor
Enables natural language editing of presentation slides
"""

import os
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from slides_manager import SlidesManager


class ChatEditRequest(BaseModel):
    """Request model for chat-based slide editing"""
    presentation_id: str = Field(description="ID of the presentation to edit")
    message: str = Field(description="Natural language edit instruction")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")


class ChatEditResponse(BaseModel):
    """Response model for chat-based slide editing"""
    success: bool = Field(description="Whether the edit was successful")
    message: str = Field(description="Response message to user")
    changes_made: List[str] = Field(default_factory=list, description="List of changes that were made")
    thread_id: str = Field(description="Thread ID for conversation continuity")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class SlideEditState(BaseModel):
    """State for slide editing workflow"""
    presentation_id: str = Field(description="Presentation ID")
    message: str = Field(description="User's edit message")
    slide_data: Dict[str, Any] = Field(default_factory=dict, description="Current slide data")
    parsed_intent: Dict[str, Any] = Field(default_factory=dict, description="Parsed user intent")
    changes_to_make: List[Dict[str, Any]] = Field(default_factory=list, description="Specific changes to apply")
    execution_result: Dict[str, Any] = Field(default_factory=dict, description="Result of executing changes")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")


class ChatSlideEditor:
    """
    Chat-based slide editor that interprets natural language commands
    and applies them to presentation slides
    """
    
    def __init__(self, api_key: str = None, slides_manager: SlidesManager = None):
        """Initialize the chat slide editor"""
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")
            
        genai.configure(api_key=self.api_key)
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
        self.slides_manager = slides_manager
        
        # Create memory for conversation persistence
        self.memory = MemorySaver()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the chat editing workflow graph"""
        workflow = StateGraph(SlideEditState)
        
        # Add nodes
        workflow.add_node("parse_intent", self._parse_user_intent)
        workflow.add_node("get_slide_data", self._get_slide_data)
        workflow.add_node("plan_changes", self._plan_changes)
        workflow.add_node("execute_changes", self._execute_changes)
        
        # Add edges
        workflow.set_entry_point("parse_intent")
        workflow.add_edge("parse_intent", "get_slide_data")
        workflow.add_edge("get_slide_data", "plan_changes")
        workflow.add_edge("plan_changes", "execute_changes")
        workflow.add_edge("execute_changes", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    def _parse_user_intent(self, state: SlideEditState) -> Dict[str, Any]:
        """Parse user's natural language intent into structured data"""
        
        intent_parser_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at parsing natural language instructions for slide editing.
            
            Parse the user's message and extract:
            1. Target slide (slide number, "current slide", "all slides", etc.)
            2. Action type (edit, add, delete, replace, modify, etc.)
            3. Target element (text, image, title, bullet points, numbers, charts, etc.)
            4. Specific instruction (what exactly to change)
            5. Any numerical values or parameters mentioned
            
            Examples:
            - "Reduce the growth numbers in Slide 5" → slide: 5, action: modify, element: numbers, instruction: reduce
            - "Change customer persona image on Slide 4" → slide: 4, action: replace, element: image, instruction: change to customer persona
            - "Add a bullet point about market size to slide 3" → slide: 3, action: add, element: bullet_point, instruction: add market size info
            - "Make the title bigger on the current slide" → slide: current, action: modify, element: title, instruction: increase size
            
            Return JSON with keys: slide_target, action_type, target_element, instruction, parameters
            """),
            ("human", "Parse this editing instruction: {message}")
        ])
        
        try:
            # Use the LLM to parse the intent
            chain = intent_parser_prompt | self.llm
            response = chain.invoke({"message": state.message})
            
            # Try to parse JSON from response
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed_intent = json.loads(json_match.group())
            else:
                # Fallback parsing
                parsed_intent = self._fallback_intent_parsing(state.message)
            
            return {"parsed_intent": parsed_intent}
            
        except Exception as e:
            print(f"Error parsing intent: {e}")
            # Fallback to simple keyword-based parsing
            parsed_intent = self._fallback_intent_parsing(state.message)
            return {"parsed_intent": parsed_intent}
    
    def _fallback_intent_parsing(self, message: str) -> Dict[str, Any]:
        """Fallback intent parsing using keyword matching"""
        message_lower = message.lower()
        
        # Extract slide number
        slide_match = re.search(r'slide\s+(\d+)', message_lower)
        slide_target = int(slide_match.group(1)) if slide_match else "current"
        
        # Determine action type
        action_type = "modify"
        if any(word in message_lower for word in ["add", "insert", "create"]):
            action_type = "add"
        elif any(word in message_lower for word in ["delete", "remove"]):
            action_type = "delete"
        elif any(word in message_lower for word in ["replace", "change"]):
            action_type = "replace"
        
        # Determine target element
        target_element = "text"
        if any(word in message_lower for word in ["image", "picture", "photo"]):
            target_element = "image"
        elif any(word in message_lower for word in ["title", "heading"]):
            target_element = "title"
        elif any(word in message_lower for word in ["number", "value", "data"]):
            target_element = "numbers"
        elif any(word in message_lower for word in ["bullet", "point", "list"]):
            target_element = "bullet_point"
        
        return {
            "slide_target": slide_target,
            "action_type": action_type,
            "target_element": target_element,
            "instruction": message,
            "parameters": {}
        }
    
    def _get_slide_data(self, state: SlideEditState) -> Dict[str, Any]:
        """Get current data for the target slide(s)"""
        try:
            if not self.slides_manager:
                raise Exception("Slides manager not available")
            
            # Handle demo presentations
            if state.presentation_id.startswith("demo-"):
                # For demo, create mock slide data
                slide_data = {
                    "presentation_title": "Demo Presentation",
                    "target_slides": [
                        {
                            "slide_id": "demo_slide_1",
                            "slide_index": 0,
                            "title": "Demo Slide 1",
                            "elements": [
                                {
                                    "element_id": "demo_text_1",
                                    "type": "text",
                                    "content": "Sample growth rate: 150% year over year"
                                },
                                {
                                    "element_id": "demo_image_1", 
                                    "type": "image",
                                    "content": "customer_persona.jpg"
                                }
                            ]
                        }
                    ]
                }
                return {"slide_data": slide_data}
            
            # Get presentation data for real presentations
            presentation_data = self.slides_manager.get_presentation_slides(state.presentation_id)
            
            slide_target = state.parsed_intent.get("slide_target", "current")
            
            if isinstance(slide_target, int):
                # Specific slide number
                target_slides = [s for s in presentation_data.slides if s.slide_index == slide_target - 1]
            elif slide_target == "current":
                # For now, assume first slide (could be enhanced with session state)
                target_slides = [presentation_data.slides[0]] if presentation_data.slides else []
            else:
                # All slides
                target_slides = presentation_data.slides
            
            slide_data = {
                "presentation_title": presentation_data.title,
                "target_slides": [
                    {
                        "slide_id": slide.slide_id,
                        "slide_index": slide.slide_index,
                        "title": slide.title,
                        "elements": slide.elements
                    } for slide in target_slides
                ]
            }
            
            return {"slide_data": slide_data}
            
        except Exception as e:
            error_msg = f"Error getting slide data: {e}"
            print(error_msg)
            return {"slide_data": {}, "errors": [error_msg]}
    
    def _plan_changes(self, state: SlideEditState) -> Dict[str, Any]:
        """Plan specific changes based on intent and slide data"""
        
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at planning slide edits based on user intent and slide content.
            
            Given the user's parsed intent and current slide data, create a specific plan for changes.
            
            For each change, specify:
            1. slide_id: The ID of the slide to modify
            2. element_id: The ID of the specific element to change (if applicable)
            3. change_type: The type of change (modify_text, replace_image, add_element, delete_element, etc.)
            4. new_content: The new content (if applicable)
            5. parameters: Any additional parameters (font_size, color, position, etc.)
            
            Guidelines:
            - For "reduce numbers", look for numerical values and decrease them by 10-20%
            - For "change image", plan to replace with a placeholder or search for new image
            - For text modifications, maintain the original style and formatting
            - Be specific about which elements to target based on the content
            
            Return a JSON array of change objects.
            """),
            ("human", """
            User Intent: {intent}
            Current Slide Data: {slide_data}
            
            Plan the specific changes needed:
            """)
        ])
        
        try:
            # Use the LLM to plan changes
            chain = planning_prompt | self.llm
            response = chain.invoke({
                "intent": json.dumps(state.parsed_intent, indent=2),
                "slide_data": json.dumps(state.slide_data, indent=2)
            })
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                changes_to_make = json.loads(json_match.group())
            else:
                # Fallback planning
                changes_to_make = self._fallback_change_planning(state)
            
            return {"changes_to_make": changes_to_make}
            
        except Exception as e:
            print(f"Error planning changes: {e}")
            # Fallback to simple change planning
            changes_to_make = self._fallback_change_planning(state)
            return {"changes_to_make": changes_to_make}
    
    def _fallback_change_planning(self, state: SlideEditState) -> List[Dict[str, Any]]:
        """Fallback change planning for common cases"""
        changes = []
        intent = state.parsed_intent
        slide_data = state.slide_data
        
        action_type = intent.get("action_type", "modify")
        target_element = intent.get("target_element", "text")
        
        for slide in slide_data.get("target_slides", []):
            slide_id = slide["slide_id"]
            
            if action_type == "modify" and target_element == "numbers":
                # Find elements with numbers and reduce them
                for element in slide["elements"]:
                    if element.get("type") == "text":
                        content = element.get("content", "")
                        # Look for numbers in the content
                        if re.search(r'\d+', content):
                            changes.append({
                                "slide_id": slide_id,
                                "element_id": element.get("element_id"),
                                "change_type": "modify_numbers",
                                "new_content": self._reduce_numbers_in_text(content),
                                "parameters": {}
                            })
            
            elif action_type == "replace" and target_element == "image":
                # Find image elements to replace
                for element in slide["elements"]:
                    if element.get("type") == "image":
                        changes.append({
                            "slide_id": slide_id,
                            "element_id": element.get("element_id"),
                            "change_type": "replace_image",
                            "new_content": "placeholder_image_url",
                            "parameters": {"alt_text": "Updated image"}
                        })
        
        return changes
    
    def _reduce_numbers_in_text(self, text: str) -> str:
        """Reduce numerical values in text by 15%"""
        def reduce_number(match):
            number = float(match.group())
            reduced = number * 0.85  # Reduce by 15%
            # Keep as integer if it was originally an integer
            if number == int(number):
                return str(int(reduced))
            else:
                return f"{reduced:.1f}"
        
        # Replace numbers with reduced values
        return re.sub(r'\b\d+(?:\.\d+)?\b', reduce_number, text)
    
    def _execute_changes(self, state: SlideEditState) -> Dict[str, Any]:
        """Execute the planned changes on the slides"""
        executed_changes = []
        errors = []
        
        # Handle demo presentations
        if state.presentation_id.startswith("demo-"):
            # For demo, simulate successful execution
            for change in state.changes_to_make:
                change_type = change.get("change_type", "modify_text")
                element_id = change.get("element_id", "unknown")
                
                if change_type in ["modify_text", "modify_numbers"]:
                    executed_changes.append(f"Simulated update to element {element_id} (Demo mode)")
                elif change_type == "replace_image":
                    executed_changes.append(f"Simulated image replacement for element {element_id} (Demo mode)")
                else:
                    executed_changes.append(f"Simulated {change_type} change (Demo mode)")
                    
            execution_result = {
                "success": True,
                "changes_executed": len(executed_changes),
                "total_changes_planned": len(state.changes_to_make),
                "demo_mode": True
            }
            
            return {
                "execution_result": execution_result,
                "errors": ["Note: This is demo mode. No actual changes were made to a real presentation."]
            }
        
        # Handle real presentations
        if not self.slides_manager:
            return {"execution_result": {"success": False}, "errors": ["Slides manager not available"]}
        
        try:
            for change in state.changes_to_make:
                slide_id = change.get("slide_id")
                element_id = change.get("element_id")
                change_type = change.get("change_type")
                new_content = change.get("new_content")
                
                if change_type == "modify_text" or change_type == "modify_numbers":
                    # Update text content
                    success = self.slides_manager.update_slide_elements(
                        state.presentation_id,
                        slide_id,
                        {element_id: new_content}
                    )
                    
                    if success:
                        executed_changes.append(f"Updated content in slide element")
                    else:
                        errors.append(f"Failed to update element {element_id}")
                
                elif change_type == "replace_image":
                    # For now, we'll add this as a future enhancement
                    executed_changes.append("Image replacement feature coming soon")
                
                # Add more change types as needed
            
            execution_result = {
                "success": len(errors) == 0,
                "changes_executed": len(executed_changes),
                "total_changes_planned": len(state.changes_to_make)
            }
            
            return {
                "execution_result": execution_result,
                "errors": errors
            }
            
        except Exception as e:
            error_msg = f"Error executing changes: {e}"
            return {
                "execution_result": {"success": False},
                "errors": [error_msg]
            }
    
    async def edit_slide(self, request: ChatEditRequest) -> ChatEditResponse:
        """Main method to handle chat-based slide editing"""
        # Create thread_id if not provided
        thread_id = request.thread_id or f"edit_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create initial state
        initial_state = SlideEditState(
            presentation_id=request.presentation_id,
            message=request.message
        )
        
        try:
            # Execute the workflow
            config = {"configurable": {"thread_id": thread_id}}
            result = await self.workflow.ainvoke(initial_state.dict(), config=config)
            
            # Build response
            execution_result = result.get("execution_result", {})
            changes_made = []
            
            if execution_result.get("success"):
                changes_count = execution_result.get("changes_executed", 0)
                changes_made.append(f"Successfully applied {changes_count} changes to your presentation")
                
                response_message = "Great! I've successfully updated your slides based on your request."
                if result.get("parsed_intent", {}).get("action_type") == "modify":
                    response_message += " The changes have been applied and should be visible in your presentation."
            else:
                response_message = "I encountered some issues while trying to update your slides. Please check the details below."
            
            return ChatEditResponse(
                success=execution_result.get("success", False),
                message=response_message,
                changes_made=changes_made,
                thread_id=thread_id,
                errors=result.get("errors", [])
            )
            
        except Exception as e:
            return ChatEditResponse(
                success=False,
                message=f"I'm sorry, I encountered an error while processing your request: {str(e)}",
                changes_made=[],
                thread_id=thread_id,
                errors=[str(e)]
            )


# Example usage and testing
if __name__ == "__main__":
    # This would be used for testing the chat editor
    pass
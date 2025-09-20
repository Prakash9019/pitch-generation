"""
Chat-based Live Slide Editor
Enables natural language editing of presentation slides using a LangGraph agent.
"""

import os
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from slides_manager import SlidesManager


class ChatEditRequest(BaseModel):
    """Request model for chat-based slide editing"""
    presentation_id: str = Field(description="ID of the Google Slides presentation to edit")
    message: str = Field(description="Natural language edit instruction")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")


class ChatEditResponse(BaseModel):
    """Response model for chat-based slide editing"""
    success: bool = Field(description="Whether the edit was successful")
    message: str = Field(description="Response message to the user")
    changes_made: List[str] = Field(default_factory=list, description="A summary of changes that were made")
    thread_id: str = Field(description="Thread ID for conversation continuity")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class SlideEditState(BaseModel):
    """Represents the state of the slide editing workflow."""
    presentation_id: str = Field(description="Presentation ID")
    message: str = Field(description="User's original edit message")
    slide_data: Dict[str, Any] = Field(default_factory=dict, description="Data of the target slide(s)")
    parsed_intent: Dict[str, Any] = Field(default_factory=dict, description="Structured user intent from the LLM")
    changes_to_make: List[Dict[str, Any]] = Field(default_factory=list, description="A list of specific API calls to make")
    execution_result: Dict[str, Any] = Field(default_factory=dict, description="Result from executing the changes")
    errors: List[str] = Field(default_factory=list, description="A list of errors encountered during the workflow")


class ChatSlideEditor:
    """
    Orchestrates the process of editing Google Slides using natural language commands.
    It uses a state machine (LangGraph) to manage the flow:
    1. Parse Intent: Understand the user's command.
    2. Get Slide Data: Fetch the current state of the relevant slide.
    3. Plan Changes: Convert the intent into specific, executable API commands.
    4. Execute Changes: Apply the commands to the presentation via the SlidesManager.
    """

    def __init__(self, api_key: str = None, slides_manager: SlidesManager = None):
        """Initializes the chat slide editor and its workflow."""
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("A Google API key is required to initialize the ChatSlideEditor.")

        genai.configure(api_key=self.api_key)
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.1)
        
        # The SlidesManager must be provided to interact with the Google Slides API.
        if slides_manager is None:
            raise ValueError("A SlidesManager instance is required.")
        self.slides_manager = slides_manager

        self.memory = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Builds the state graph for the slide editing workflow."""
        workflow = StateGraph(SlideEditState)

        workflow.add_node("parse_intent", self._parse_user_intent)
        workflow.add_node("get_slide_data", self._get_slide_data)
        workflow.add_node("plan_changes", self._plan_changes)
        workflow.add_node("execute_changes", self._execute_changes)

        workflow.set_entry_point("parse_intent")
        workflow.add_edge("parse_intent", "get_slide_data")
        workflow.add_edge("get_slide_data", "plan_changes")
        workflow.add_edge("plan_changes", "execute_changes")
        workflow.add_edge("execute_changes", END)

        return workflow.compile(checkpointer=self.memory)

    def _parse_user_intent(self, state: SlideEditState) -> Dict[str, Any]:
        """Parses the user's natural language intent into a structured format."""
        print("--- 1. Parsing User Intent ---")
        intent_parser_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at parsing natural language instructions for editing Google Slides.
            Your task is to extract key information from the user's message.

            Extract the following details:
            - slide_target: The target slide. Can be a number (e.g., 5), "current", "all", "last", or "first".
            - action_type: The core action (e.g., 'edit_text', 'add_element', 'delete_element', 'replace_image', 'change_style').
            - target_element: The type of element to act on (e.g., 'title', 'body', 'text', 'image', 'shape', 'chart').
            - instruction: A clear, concise summary of what to do (e.g., "Change text to 'New Market Growth'", "Increase font size").
            - parameters: Any specific values mentioned (e.g., font_size: 24, color: '#FF0000', new_text: 'New Market Growth').

            Examples:
            - "change the title on slide 3 to 'Market Opportunity'" ->
              { "slide_target": 3, "action_type": "edit_text", "target_element": "title", "instruction": "Change title text", "parameters": { "new_text": "Market Opportunity" } }
            - "delete the image on the current slide" ->
              { "slide_target": "current", "action_type": "delete_element", "target_element": "image", "instruction": "Delete the image", "parameters": {} }
            - "make the text in the body red" ->
              { "slide_target": "current", "action_type": "change_style", "target_element": "body", "instruction": "Change text color to red", "parameters": { "color": "#FF0000" } }

            Return ONLY a valid JSON object with the extracted information."""),
            ("human", "Parse this editing instruction: {message}")
        ])

        try:
            chain = intent_parser_prompt | self.llm
            response = chain.invoke({"message": state.message})
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed_intent = json.loads(json_match.group())
                print(f"  -> Parsed Intent: {parsed_intent}")
                return {"parsed_intent": parsed_intent}
            else:
                raise ValueError("LLM did not return a valid JSON object.")
        except Exception as e:
            print(f"  -> Error parsing intent with LLM: {e}. Using fallback.")
            # Fallback to a simpler parsing if the LLM fails
            return {"parsed_intent": self._fallback_intent_parsing(state.message)}

    def _fallback_intent_parsing(self, message: str) -> Dict[str, Any]:
        """A simple keyword-based fallback for intent parsing."""
        # This is a simplified version. A real-world fallback might be more complex.
        return {
            "slide_target": "current",
            "action_type": "edit_text",
            "target_element": "text",
            "instruction": message,
            "parameters": {}
        }

    def _get_slide_data(self, state: SlideEditState) -> Dict[str, Any]:
        """Fetches the current data for the target slide(s) from the SlidesManager."""
        print("--- 2. Fetching Slide Data ---")
        try:
            if not self.slides_manager:
                raise ValueError("Slides manager is not available.")

            # Use the manager to get a structured representation of the presentation
            presentation_data = self.slides_manager.get_presentation_slides(state.presentation_id)
            all_slides = presentation_data.get("slides", [])
            
            if not all_slides:
                raise ValueError("Presentation contains no slides or could not be read.")

            slide_target = state.parsed_intent.get("slide_target", "current")
            target_slides_data = []

            if isinstance(slide_target, int):
                # 1-based index from user to 0-based for list access
                if 1 <= slide_target <= len(all_slides):
                    target_slides_data = [all_slides[slide_target - 1]]
            elif slide_target == "current":
                # Defaulting to the first slide for "current"
                target_slides_data = [all_slides[0]]
            elif slide_target == "all":
                target_slides_data = all_slides
            
            if not target_slides_data:
                 raise ValueError(f"Could not find the target slide: '{slide_target}'")

            slide_data = {
                "presentation_title": presentation_data.get("title"),
                "target_slides": target_slides_data
            }
            print(f"  -> Fetched data for {len(target_slides_data)} slide(s).")
            return {"slide_data": slide_data}

        except Exception as e:
            error_msg = f"Error getting slide data: {e}"
            print(f"  -> {error_msg}")
            return {"slide_data": {}, "errors": state.errors + [error_msg]}

    def _plan_changes(self, state: SlideEditState) -> Dict[str, Any]:
        """Converts the user's intent and slide data into specific, executable API calls."""
        print("--- 3. Planning Changes ---")
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert slide editor AI. Your task is to convert a user's intent and the current slide data into a precise list of API calls.

            You will be given the user's parsed intent and the JSON data of the target slide(s).
            The slide data includes an 'elements' list, where each element has a unique 'element_id'.

            Your goal is to find the correct `element_id` for the user's target and create a JSON object for the change.

            Available `change_type` commands:
            - `update_text`: To change the text of an element.
            - `update_shape_fill`: To change the background color of a shape.
            - `update_text_style`: To change font size, color, bold, etc.
            - `replace_image`: To replace an image.
            - `delete_element`: To delete an element.

            **Crucial Instructions:**
            1.  Analyze the `target_element` from the user's intent (e.g., 'title', 'body').
            2.  Look through the `elements` in the `slide_data` to find the one that best matches the description. The title is often the first large text box. The body is usually the main content area.
            3.  **You MUST extract the `element_id`** of the matching element.
            4.  Construct a JSON object for each change.

            Example:
            - Intent: { "target_element": "title", "parameters": { "new_text": "New Title" } }
            - Slide Data: { "elements": [ { "element_id": "g123_0_1", "content": "Old Title", ... }, ... ] }
            - Your Output should be:
              [{ "change_type": "update_text", "slide_id": "p1", "element_id": "g123_0_1", "new_content": "New Title" }]

            Return ONLY a valid JSON array of change objects."""),
            ("human", """
            User Intent: {intent}
            Current Slide Data: {slide_data}

            Plan the specific changes:
            """)
        ])

        try:
            chain = planning_prompt | self.llm
            response = chain.invoke({
                "intent": json.dumps(state.parsed_intent, indent=2),
                "slide_data": json.dumps(state.slide_data, indent=2)
            })
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                changes_to_make = json.loads(json_match.group())
                print(f"  -> Planned Changes: {changes_to_make}")
                return {"changes_to_make": changes_to_make}
            else:
                raise ValueError("LLM did not return a valid JSON array for the plan.")
        except Exception as e:
            error_msg = f"Error planning changes: {e}"
            print(f"  -> {error_msg}")
            return {"changes_to_make": [], "errors": state.errors + [error_msg]}

    def _execute_changes(self, state: SlideEditState) -> Dict[str, Any]:
        """Executes the planned changes using the SlidesManager."""
        print("--- 4. Executing Changes ---")
        if not self.slides_manager:
            return {"execution_result": {"success": False}, "errors": state.errors + ["Slides manager not available."]}
        
        if not state.changes_to_make:
            print("  -> No changes planned, skipping execution.")
            return {"execution_result": {"success": True, "changes_executed": 0, "message": "No changes were needed."}}

        executed_count = 0
        errors = []

        try:
            # Group changes by slide to make fewer API calls if necessary in the future
            # For now, we process them one by one as planned.
            for change in state.changes_to_make:
                change_type = change.get("change_type")
                slide_id = change.get("slide_id")
                element_id = change.get("element_id")
                
                success = False
                if change_type == "update_text":
                    new_content = change.get("new_content")
                    success = self.slides_manager.update_slide_elements(
                        state.presentation_id, slide_id, {element_id: new_content}
                    )
                # Add other change_type handlers here (e.g., for styling, images)
                
                if success:
                    executed_count += 1
                else:
                    errors.append(f"Failed to execute change: {change}")

            execution_result = {
                "success": len(errors) == 0,
                "changes_executed": executed_count,
                "total_changes_planned": len(state.changes_to_make)
            }
            print(f"  -> Execution Result: {execution_result}")
            return {"execution_result": execution_result, "errors": state.errors + errors}

        except Exception as e:
            error_msg = f"Error executing changes: {e}"
            print(f"  -> {error_msg}")
            return {"execution_result": {"success": False}, "errors": state.errors + [error_msg]}

    async def edit_slide(self, request: ChatEditRequest) -> ChatEditResponse:
        """Main entry point to handle a chat-based slide editing request."""
        thread_id = request.thread_id or f"edit_thread_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        initial_state = {
            "presentation_id": request.presentation_id,
            "message": request.message,
            "errors": [] # Initialize errors list
        }
        
        config = {"configurable": {"thread_id": thread_id}}

        try:
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            execution_result = final_state.get("execution_result", {})
            success = execution_result.get("success", False)
            changes_count = execution_result.get("changes_executed", 0)
            
            message = ""
            if success:
                if changes_count > 0:
                    message = f"I've successfully applied {changes_count} change(s) to your presentation."
                else:
                    message = "No changes were applied. This might be because the request was unclear or no action was needed."
            else:
                message = "I'm sorry, I encountered an issue and couldn't complete your request."

            return ChatEditResponse(
                success=success,
                message=message,
                changes_made=[f"Applied {changes_count} change(s)."] if changes_count > 0 else [],
                thread_id=thread_id,
                errors=final_state.get("errors", [])
            )
        except Exception as e:
            return ChatEditResponse(
                success=False,
                message=f"A critical error occurred in the workflow: {str(e)}",
                thread_id=thread_id,
                errors=[str(e)]
            )

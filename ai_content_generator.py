from typing import Dict, List, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import LLMChain
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

class PitchDeckContentState(BaseModel):
    """State for the pitch deck content generation workflow"""
    prompt: str = Field(..., description="User's request, e.g., 'create a pitchdeck on Facebook'")
    placeholders: List[Dict[str, Any]] = Field(..., description="List of placeholder objects with name, instruction, etc.")
    current_placeholder: Optional[Dict[str, Any]] = Field(None, description="Current placeholder being processed")
    results: Dict[str, str] = Field(default_factory=dict, description="Generated content for each placeholder")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during generation")

class AIContentGenerator:
    """AI Content Generator for Pitch Decks using LangChain and LangGraph"""
    
    def __init__(self, api_key: str):
        """Initialize the AI Content Generator
        
        Args:
            api_key: Google API key for Gemini
        """
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=api_key,
            temperature=0.3,
            max_output_tokens=2048
        )
        
        # Create the workflow graph
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for content generation"""
        # Define the graph
        workflow = StateGraph(PitchDeckContentState)
        
        # Define the nodes
        workflow.add_node("select_next_placeholder", self._select_next_placeholder)
        workflow.add_node("generate_content", self._generate_content)
        
        # Define the edges
        workflow.add_edge("select_next_placeholder", "generate_content")
        workflow.add_conditional_edges(
            "generate_content",
            self._should_continue,
            {
                True: "select_next_placeholder",
                False: END
            }
        )
        
        # Set the entry point
        workflow.set_entry_point("select_next_placeholder")
        
        return workflow.compile()
    
    def _select_next_placeholder(self, state: PitchDeckContentState) -> PitchDeckContentState:
        """Select the next placeholder to process"""
        # Find placeholders that haven't been processed yet
        remaining = [p for p in state.placeholders if p['name'] not in state.results]
        
        if not remaining:
            # All placeholders have been processed
            return state
        
        # Select the next placeholder
        state.current_placeholder = remaining[0]
        return state
    
    def _generate_content(self, state: PitchDeckContentState) -> PitchDeckContentState:
        """Generate content for the current placeholder"""
        if not state.current_placeholder:
            return state
        
        try:
            # Extract placeholder name and instruction
            placeholder_name = state.current_placeholder['name']
            placeholder_instruction = state.current_placeholder.get('instruction', '')
            slide_index = state.current_placeholder.get('slide_index', '')
            
            # Create a system prompt
            system_prompt = """You are an expert pitch deck creator with deep knowledge of companies, business models, and professional presentations. 
Your task is to generate appropriate content to replace placeholders in a pitch deck template.

For each placeholder, you should:
1. Analyze what kind of content is needed based on the placeholder name
2. Generate concise, professional content that fits the context of the presentation
3. Ensure the content is factually accurate and appropriate for the company/topic
4. Format the content appropriately for a presentation slide (brief, impactful)
5. Provide ONLY the replacement text, no explanations or formatting

The user has requested a pitch deck about: {prompt}
The current placeholder to fill is: {placeholder}
This placeholder appears on slide {slide_index}
"""
            
            # Add special instructions if available
            if placeholder_instruction:
                system_prompt += f"\nSpecial instructions for this placeholder: {placeholder_instruction}\n"
            else:
                # Add a generic instruction based on the placeholder name
                system_prompt += f"\nNo specific instructions provided. Generate appropriate content for a placeholder named '{placeholder_name}'.\n"
                
            system_prompt += "\nBased on this information, provide the appropriate replacement text for this placeholder."
            
            # Create a prompt for the current placeholder
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", f"Generate the appropriate content to replace the placeholder '{placeholder_name}' in a pitch deck about {state.prompt}.")
            ])
            
            # Generate content
            chain = prompt | self.llm | StrOutputParser()
            content = chain.invoke({
                "prompt": state.prompt,
                "placeholder": placeholder_name,
                "instruction": placeholder_instruction,
                "slide_index": slide_index
            })
            
            # Store the result
            state.results[placeholder_name] = content
            
        except Exception as e:
            # Handle errors
            state.errors.append(f"Error generating content for {placeholder_name}: {str(e)}")
        
        return state
    
    def _should_continue(self, state: PitchDeckContentState) -> bool:
        """Determine if we should continue processing placeholders"""
        # Continue if there are still placeholders to process
        processed = set(state.results.keys())
        all_placeholders = set(p['name'] for p in state.placeholders)
        return len(processed) < len(all_placeholders)
    
    def generate(self, prompt: str, placeholders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate content for all placeholders based on the prompt
        
        Args:
            prompt: User's request (e.g., "create a pitchdeck on Facebook")
            placeholders: List of placeholder objects with name, instruction, etc.
        
        Returns:
            Dictionary with results and errors
        """
        # Initialize the state
        initial_state = PitchDeckContentState(
            prompt=prompt,
            placeholders=placeholders,
            results={},
            errors=[]
        )
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        # The final_state is a dict-like object, but we need to extract the actual state
        # Convert to a dictionary and extract the relevant fields
        if hasattr(final_state, "dict"):
            # If it's a Pydantic model
            state_dict = final_state.dict()
        else:
            # If it's a dict-like object
            state_dict = dict(final_state)
        
        # Return the results and errors
        return {
            "results": state_dict.get("results", {}),
            "errors": state_dict.get("errors", [])
        }

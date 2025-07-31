#!/usr/bin/env python
"""
CLI interface for the LangChain-based calendar assistant agent.
"""
import os
import sys
import re
from typing import Optional, List

from rich.prompt import Prompt
from dotenv import load_dotenv

# Import shared CLI utilities
from backend.cli.cli_utils import (
    console, display_error, display_info, display_warning, 
    display_success, check_credentials_file, initialize_app
)
from backend.utils.logging_config import get_logger
from agent import AgentCalendarAssistant, DEFAULT_MODEL

# Load environment variables
load_dotenv()

# Setup logging
logger = get_logger("agent_cli")


def main() -> Optional[int]:
    """Main entry point for the application."""
    try:
        # Check if credentials file exists
        if not check_credentials_file('credentials.json'):
            return 1

        # Initialize the agent
        display_info(
            "Initializing your AI Calendar Assistant...\n"
            "This may take a moment as we connect to the necessary services.",
            "Starting Up"
        )
        
        # Get model name from environment or use default from agent.py
        from agent import DEFAULT_MODEL
        model_name = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        
        # Create the agent with appropriate error handling
        try:
            # First check if model exists in Ollama
            import ollama
            try:
                # Override model directly if specified in environment variable
                env_override = os.getenv("FORCE_MODEL")
                if env_override:
                    logger.info(f"Using model override from environment: {env_override}")
                    model_name = env_override
                    # No need to check availability - we trust the override
                else:
                    # Get available models from Ollama
                    model_names = get_available_ollama_models()
                    
                    # Check if the specified model exists
                    model_exists = model_name in model_names
                    
                    if not model_exists:
                        display_warning(
                            f"Model '{model_name}' not found in Ollama.\n\n"
                            f"Available models: {', '.join(model_names)}\n\n"
                            f"Please make sure you've pulled this model using: ollama pull {model_name}\n\n"
                            f"Falling back to llama3 model. Function calling features may not work properly.",
                            title="Model Not Found",
                            border_style="yellow"
                        )
                        model_name = "llama3"  # Fallback model
                        logger.warning(f"Model {DEFAULT_MODEL} not found, falling back to llama3")
                    else:
                        logger.info(f"Found model {model_name} in available models: {model_names}")
            except Exception as e:
                logger.warning(f"Could not check model availability: {e}")
            
            # Initialize the agent
            agent = AgentCalendarAssistant(model_name=model_name)
            logger.info(f"Agent initialized successfully with model: {model_name}")
            
            # Warn about function calling if not using the recommended model
            if model_name != DEFAULT_MODEL:
                display_warning(
                    f"Using '{model_name}' instead of recommended '{DEFAULT_MODEL}'.\n\n"
                    f"Function calling capabilities may be limited with this model.",
                    "Model Information"
                )
        except Exception as e:
            display_error(
                f"Failed to initialize the agent.\n\n{str(e)}\n\n"
                "Please make sure Ollama is running and that you have installed all requirements.\n"
                "If using llama3.1, ensure you've pulled the model: ollama pull llama3.1",
                "Initialization Error"
            )
            logger.error(f"Failed to initialize agent: {e}")
            return 1
        
        # Start the interactive session
        initialize_app(
            "AI Calendar Assistant", 
            "Your LangChain-powered AI Calendar Assistant is ready!\n"
            "You can ask about your events, create new events, manage tasks, and more."
        )
        
        # Interactive loop
        while True:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ["quit", "exit", "bye"]:
                console.print("[bold green]Assistant:[/bold green] Goodbye!")
                break
            
            logger.info(f"User input: {user_input}")
            
            try:
                response = agent.process_input(user_input)
                logger.info(f"Agent response: {response}")
                console.print(f"[bold green]Assistant:[/bold green] {response}")
            except Exception as e:
                logger.error(f"Error processing input: {e}")
                display_error(str(e))
                console.print("[bold green]Assistant:[/bold green] I encountered an error processing your request. Please try again.")
                
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[bold green]Assistant:[/bold green] Goodbye!")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        display_error(f"An unexpected error occurred: {str(e)}")
        return 1


def get_available_ollama_models() -> List[str]:
    """
    Get a list of available Ollama models.
    
    Returns:
        List of model names
    """
    try:
        import ollama
        models_output = ollama.list()
        logger.info(f"Raw Ollama models output: {models_output}")
        
        # Parse model names from the response - handling different formats
        model_names = []
        
        # Handle both possible response formats (newer and older Ollama versions)
        if hasattr(models_output, 'models'):
            # This appears to be the newer object-oriented response format
            for model_obj in models_output.models:
                if hasattr(model_obj, 'model'):
                    model_names.append(model_obj.model)
        elif isinstance(models_output, dict) and 'models' in models_output:
            # This is the dictionary-based response format
            for model in models_output['models']:
                if isinstance(model, dict) and 'name' in model:
                    model_names.append(model['name'])
        
        # Special case handling: if the response format is completely different,
        # try to extract model names from the string representation
        if not model_names and 'llama3.1' in str(models_output):
            logger.info("Using fallback string parsing for model detection")
            # Extract model names from the string representation using regex
            model_matches = re.findall(r"model=['\"]([^'\"]+)['\"]|model='([^']+)'|model=\"([^\"]+)\"", str(models_output))
            # Flatten the matches and remove empty strings
            for match in model_matches:
                name = next((m for m in match if m), None)
                if name:
                    model_names.append(name)
        
        return model_names
    except Exception as e:
        logger.error(f"Error getting Ollama models: {e}")
        return []


if __name__ == "__main__":
    sys.exit(main())

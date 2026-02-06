import json
from typing import Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from app.config.settings import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger("character_generation_service")

# Initialize LLM for generation
LLM = ChatGoogleGenerativeAI(
    model=getattr(settings, "GOOGLE_MODEL", None),
    temperature=0.8, # Slightly higher creativity for generation
    google_api_key=getattr(settings, "GOOGLE_API_KEY", None),
)

GENERATION_SYSTEM_PROMPT = """
You are an expert character creator for roleplay scenarios.
Your task is to generate a detailed character profile based on a user's topic or description.

CRITICAL RULES:
1. Return ONLY valid JSON - no explanation, no markdown, no extra text before or after
2. Do NOT include ```json or ``` backticks
3. Keep all text on single lines - do not include actual line breaks in string values
4. All strings must be on one line - if you need line breaks in examples, use the literal text "User:" and "Character:" on the same line
5. Ensure all quotes inside strings are properly escaped with backslash

Return EXACTLY this JSON structure (single line per field):
{
    "name": "Character Name",
    "visual_description": "A detailed visual description here",
    "personality": "A detailed personality description here",
    "roleplay_examples": [
        "User: Hello | Character: Hi there! *smiles*",
        "User: How are you? | Character: Doing great thanks!"
    ]
}

Ensure the character is interesting and consistent with the requested theme.
"""

async def generate_character_profile(topic: str) -> Dict:
    """
    Generates a character profile based on the given topic using LLM.
    """
    logger.info(f"Generating character for topic: {topic}")
    
    messages = [
        SystemMessage(content=GENERATION_SYSTEM_PROMPT),
        HumanMessage(content=f"Create a character based on this idea: {topic}")
    ]

    try:
        response = await LLM.ainvoke(messages)
        raw_content = response.content.strip()
        logger.debug(f"Raw LLM response: {raw_content}")
        
        # Clean up potential markdown code blocks and extra text
        content = raw_content
        
        # Remove markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1]
        if "```" in content:
            content = content.split("```")[0]
        
        content = content.strip()
        
        # Handle case where LLM adds explanation text before/after JSON
        # Try to find JSON object boundaries
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        
        if start_idx == -1 or end_idx == -1:
            logger.error(f"No JSON object found in response. Raw: {raw_content}")
            raise ValueError("LLM response does not contain a valid JSON object")
        
        content = content[start_idx:end_idx+1]
        logger.debug(f"Extracted JSON: {content}")
        
        # Fix common JSON formatting issues
        # Replace actual newlines with escaped newlines within strings
        try:
            character_data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("First parse failed, attempting to fix newlines...")
            # Try to fix unescaped newlines in the JSON
            # This is a workaround for LLMs that include actual newlines in string values
            lines = content.split('\n')
            fixed_lines = []
            in_string = False
            escape_next = False
            
            for line in lines:
                if not in_string:
                    fixed_lines.append(line)
                else:
                    # We're continuing a string from previous line
                    fixed_lines[-1] += " " + line.lstrip()
                
                # Count unescaped quotes to track if we're in a string
                for char in line:
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"':
                        in_string = not in_string
            
            content = '\n'.join(fixed_lines)
            character_data = json.loads(content)
        
        # Map to our internal schema
        mapped_data = {
            "name": character_data.get("name", "Unknown"),
            "Visual_Description": character_data.get("visual_description", ""),
            "Personality": character_data.get("personality", ""),
            "Roleplay_Examples": character_data.get("roleplay_examples", []),
            "description": f"Generated from topic: {topic}"
        }
        
        logger.info(f"Successfully generated character: {mapped_data['name']}")
        return mapped_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Attempted to parse: {content}")
        logger.error(f"Original raw response: {raw_content}")
        raise ValueError(f"Invalid JSON from LLM: {e}")
    except Exception as e:
        logger.exception(f"Error generating character: {e}")
        raise e

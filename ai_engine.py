import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables (API Key)
load_dotenv()

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_quiz_data(topic, num_questions):
    # Strict JSON configuration
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    Create a JSON list of exactly {num_questions} quiz questions about {topic}.
    Each object MUST have: "question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer".
    The "correct_answer" must be 'A', 'B', 'C', or 'D'.
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Safety check if AI blocks the prompt (e.g. sensitive topics)
        if not response.text:
            print("AI Blocked the prompt or returned empty.")
            return None
            
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_text)
        
        # Ensure it's always a list
        return data if isinstance(data, list) else [data]
        
    except Exception as e:
        print(f"AI Engine Error: {str(e)}")
        return None
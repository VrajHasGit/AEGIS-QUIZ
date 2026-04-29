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
        model_name="gemini-2.5-flash-lite",
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""Generate {num_questions} multiple-choice questions on {topic}. 
JSON format: [{{"question_text":"", "option_a":"", "option_b":"", "option_c":"", "option_d":"", "correct_answer":"A|B|C|D"}}]"""
    
    try:
        response = model.generate_content(prompt)
        
        if not response.text:
            print("AI Blocked the prompt or returned empty.")
            return None
            
        # Clean the response text to ensure it's valid JSON
        clean_text = response.text.strip()
        if clean_text.startswith('```'):
            clean_text = clean_text.split('\n', 1)[1] if '\n' in clean_text else clean_text
            clean_text = clean_text.rsplit('\n', 1)[0] if '\n' in clean_text else clean_text
            clean_text = clean_text.replace('```', '')
        
        data = json.loads(clean_text)
        
        return data if isinstance(data, list) else [data]
        
    except Exception as e:
        print(f"AI Engine Error: {str(e)}")
        return None
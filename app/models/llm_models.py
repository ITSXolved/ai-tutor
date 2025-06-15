from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from utils.config import Config
import openai

class ModelManager:
    def __init__(self):
        self.config = Config()
        self._learnlm_model = None
        self._openrouter_model = None
    
    def get_learnlm_model(self):
        """Get LearnLM model instance"""
        if self._learnlm_model is None:
            self._learnlm_model = ChatGoogleGenerativeAI(
                model=self.config.LEARNLM_MODEL,
                google_api_key=self.config.GOOGLE_API_KEY,
                temperature=0.7,
                max_tokens=1000
            )
        return self._learnlm_model
    
    def get_openrouter_model(self):
        """Get OpenRouter model instance as fallback"""
        if self._openrouter_model is None:
            self._openrouter_model = ChatOpenAI(
                model=self.config.OPENROUTER_MODEL,
                openai_api_key=self.config.OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=1000
            )
        return self._openrouter_model
    
    def get_active_model(self, prefer_learnlm=None):
        """Get the active model based on preference and availability"""
        if prefer_learnlm is None:
            prefer_learnlm = self.config.PREFER_LEARNLM
        try:
            if prefer_learnlm and self.config.GOOGLE_API_KEY:
                return self.get_learnlm_model()
            elif self.config.OPENROUTER_API_KEY:
                return self.get_openrouter_model()
            else:
                raise ValueError("No valid API keys configured")
        except Exception as e:
            print(f"Error getting model: {e}")
            return self.get_openrouter_model()  # Fallback
import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


try:
    import google.generativeai as google_genai

    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
try:
    from anthropic import AI_PROMPT, HUMAN_PROMPT, Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMInterface(ABC):
    @abstractmethod
    def run(self, prompt, temperature=0):
        pass


class LLMFactory(LLMInterface):
    def __init__(self, model):
        super().__init__()
        self.model = model
        if model in ["gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k", "gpt-4-1106-preview", "gpt-4-0125-preview"]:
            assert os.getenv("OPENAI_API_KEY") is not None, (
                "Please set the environment variable OPENAI_API_KEY. "
                "You can get one at https://beta.openai.com/account/api-keys."
            )
            self.client = OpenAI()
        elif model in ["claude-2.1", "claude-2.0", "claude-instant-1.2"]:
            assert ANTHROPIC_AVAILABLE, "Anthropic is not available. Please install it."
            assert os.getenv("ANTHROPIC_API_KEY") is not None, (
                "Please set the environment variable ANTHROPIC_API_KEY. "
                "You can get one at https://www.anthropic.com/signup."
            )
            self.client = Anthropic()
        elif model in ["gemini-pro"]:
            assert GOOGLE_GENAI_AVAILABLE, "Google GenAI is not available. Please install it."
            assert os.getenv("GEMINI_API_KEY") is not None, (
                "Please set the environment variable GEMINI_API_KEY. "
                "You can get one at https://ai.google.dev/tutorials/setup."
            )
            google_genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.client = google_genai.GenerativeModel(model_name=model)
        else:
            raise ValueError(
                f"Model {model} is not supported. "
                "Please choose one of the following models: "
                "gpt-3.5-turbo-1106, gpt-4-1106-preview, gpt-4-0125-preview, gemini-pro, claude-2.1, claude-2.0, claude-instant-1.2."
            )

    def _llm_response(self, prompt, temperature):
        """
        Send a prompt to the LLM and return the response.
        """
        if isinstance(self.client, OpenAI):
            # Leverage JSON mode in OpenAI API. Make sure the system prompt contains "Output JSON".
            if "Output JSON" in prompt["system_prompt"]:
                response = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": prompt["system_prompt"]},
                        {"role": "user", "content": prompt["user_prompt"]},
                    ],
                    seed=0,
                    temperature=temperature,
                    max_tokens=1024,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt["system_prompt"]},
                        {"role": "user", "content": prompt["user_prompt"]},
                    ],
                    seed=0,
                    temperature=temperature,
                    max_tokens=1024,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
            content = response.choices[0].message.content
        elif ANTHROPIC_AVAILABLE and isinstance(self.client, Anthropic):
            response = self.client.completions.create(
                model="claude-2.1",
                max_tokens_to_sample=1024,
                temperature=temperature,
                prompt=f"{prompt['system_prompt']}{HUMAN_PROMPT}{prompt['user_prompt']}{AI_PROMPT}",
            )
            content = response.completion
        elif GOOGLE_GENAI_AVAILABLE and isinstance(self.client, google_genai.GenerativeModel):
            generation_config = {
                "temperature": temperature,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 1024,
            }
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
            ]
            response = self.client.generate_content(
                f"{prompt['system_prompt']}\n{prompt['user_prompt']}",
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            content = response.text
        else:
            raise ValueError(f"Unknown model client")

        return content

    def run(self, prompt, temperature=0):
        """
        Run the LLM and return the response.
        Default temperature: 0
        """
        content = self._llm_response(prompt=prompt, temperature=temperature)
        return content


DefaultLLM = lambda: LLMFactory(model=os.getenv("EVAL_LLM", "gpt-3.5-turbo-1106"))

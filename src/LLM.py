from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover - runtime fallback
    ChatOllama = None

class LLMService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the model and the session memory storage."""
        print("Initializing Multi-turn LLM Service...")
        self.llm = None
        if ChatOllama is not None:
            try:
                self.llm = ChatOllama(model="qwen3:4b", temperature=0)
            except Exception as exc:
                print(f"LLM initialization failed: {exc}")
        else:
            print("langchain_ollama is not installed; using fallback responses.")

        # Dictionary to store chat histories. Key = session_id, Value = List of messages
        self.sessions = {}

    def chat(self, prompt: str, session_id: str = "default", system_prompt: str = None) -> str:
        """
        Sends a prompt to the LLM while maintaining conversation history for the given session_id.
        """
        try:
            # 1. Initialize the session if it doesn't exist
            if session_id not in self.sessions:
                self.sessions[session_id] = []
                # Optionally inject a system prompt at the very beginning of the chat
                if system_prompt:
                    self.sessions[session_id].append(SystemMessage(content=system_prompt))

            # 2. Append the new user prompt to the history
            self.sessions[session_id].append(HumanMessage(content=prompt))

            if self.llm is None:
                fallback = "Please describe your experience in one concise sentence."
                self.sessions[session_id].append(AIMessage(content=fallback))
                return fallback

            # 3. Send the entire history to the LLM
            response = self.llm.invoke(self.sessions[session_id])

            # 4. Append the LLM's response to the history so it remembers it next time
            self.sessions[session_id].append(response)

            return response.content

        except Exception as e:
            return f"An error occurred: {str(e)}"

    def clear_session(self, session_id: str = "default"):
        """Clears the history for a specific session to start fresh."""
        if session_id in self.sessions:
            self.sessions[session_id] = []
            print(f"Session '{session_id}' cleared.")

# Instantiate once
llm_client = LLMService()
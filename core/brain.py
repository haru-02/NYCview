from llama_cpp import Llama
from core.schema import AgentState
llm = Llama(model_path="/app/models/tinyllama.gguf", n_ctx=512, verbose=False)

class AgentBrain:
    @staticmethod
    def decide_next_action(state):
        # Prevent trying the same thing forever
        available = [t for t in ["search_unsplash", "search_pexels", "search_wikimedia"] if t.replace("search_", "") not in state.tried_sources]
        
        if not available or state.best_score > 0.85:
            return "finalize"

        prompt = f"<|system|>\nYou are a helpful assistant that chooses tools. Respond with ONLY the tool name from this list: {available} or finalize.<|user|>\nGoal: {state.poi_name}. Best score: {state.best_score}. Tried: {state.tried_sources}. Next tool?<|assistant|>\n"
        
        output = llm(prompt, max_tokens=10, stop=["\n"])
        action = output["choices"][0]["text"].strip().lower()
        
        # Validation fallback
        for tool in available + ["finalize"]:
            if tool in action:
                return tool
        return available[0] if available else "finalize"
import random
from llama_cpp import Llama
from core.schema import AgentState

# Load the LLM once
llm = Llama(model_path="/app/models/tinyllama.gguf", n_ctx=512, verbose=False)

class AgentBrain:
    TOOLS = ["search_unsplash", "search_pexels", "search_wikimedia"]
    EPSILON = 0.30  # chance for random exploration

    @staticmethod
    def decide_next_action(state: AgentState, action_count: int) -> str:
        """
        Decide which tool to use next.
        Strategy:
        1. Try each tool at least once (initial exploration)
        2. Stop if good enough or max actions reached
        3. Random epsilon exploration
        4. Prefer least-used source
        5. LLM tie-breaker as last option
        """

        # ---------------------------
        # Stop conditions
        # ---------------------------
        if action_count >= 10 or state.best_score > 0.70:
            return "finalize"

        # ---------------------------
        # 1. INITIAL EXPLORATION PHASE
        # Try each tool at least once
        # ---------------------------
        for tool in AgentBrain.TOOLS:
            source = tool.split("_")[1]
            if state.tried_sources.count(source) == 0:
                return tool

        # ---------------------------
        # 2. EPSILON RANDOM EXPLORATION
        # ---------------------------
        if random.random() < AgentBrain.EPSILON:
            return random.choice(AgentBrain.TOOLS)

        # ---------------------------
        # 3. Prefer least-used source
        # ---------------------------
        least_used = min(["unsplash", "pexels", "wikimedia"], key=lambda s: state.tried_sources.count(s))
        preferred_tool = f"search_{least_used}"
        if random.random() < 0.5:
            return preferred_tool

        # ---------------------------
        # 4. LLM tie-breaker (last option)
        # ---------------------------
        prompt = f"""
You are a NYC Photo Agent.

Goal: {state.poi_name}
Current best score: {state.best_score:.2f}
Unsplash used: {state.tried_sources.count('unsplash')}
Pexels used: {state.tried_sources.count('pexels')}
Wikimedia used: {state.tried_sources.count('wikimedia')}

Choose ONE tool that may improve results.
Reply ONLY with:
search_unsplash
search_pexels
search_wikimedia
finalize
"""
        try:
            output = llm(prompt, max_tokens=10, stop=["\n"], echo=False)
            action = output["choices"][0]["text"].strip().lower()
            if action in AgentBrain.TOOLS + ["finalize"]:
                return action
        except Exception as e:
            print(f"[LLM Warning] failed to decide: {e}")

        # fallback safety
        return preferred_tool
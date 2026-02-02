# NYCview: Autonomous Discovery Agent

# A Jaunt assessment

An autonomous agent that discovers, validates, and archives iconic imagery for NYC Landmarks. This project implements a local **OODA (Observe-Orient-Decide-Act) loop** to intelligently search for the highest-quality images across multiple providers.

## 🤖 The "Brain"

Unlike static scripts, NYCview uses a **Small Language Model (SLM)** to handle decision-making:

- **Reasoning**: Powered by `TinyLlama-1.1B` (GGUF Q4_K_M).
- **Vision**: Uses `OpenAI's CLIP (ViT-B-32)` to perform semantic image-text matching.
- **Decision Engine**: The agent observes its current best match and decides whether to keep searching or finalize the task.

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- API Keys for Unsplash and Pexels

### Installation

1. Clone the repository:
   ```Bash
   $ git clone [https://github.com/haru-02/NYCview.git](https://github.com/haru-02/NYCview.git)
   $ cd NYCview
   ```
2. Configure your keys in docker-compose.yml:
   ```YAML
   environment:
       - UNSPLASH_ACCESS_KEY=your_key_here
       - PEXELS_API_KEY=your_key_here
       - EMAIL=your_email@example.com
   ```
3. Run the Agent:

   ```Bash
    docker compose up --build
   ```

## 📁 Output

Results are stored in `/output/{landmark_name}/`: - image.jpg: The highest-scoring discovered image. - metadata.json: Full attribution, source link, and AI confidence scores.

## 🛠 Tech Stack

- AI Orchestration: Python 3.11, llama-cpp-python
- Computer Vision: Sentence-Transformers (CLIP)
- Data Validation: Pydantic
- Geospatial: Geopy

# Engineering Design: Agent

## 1. Objective

To move beyond deterministic scraping. The goal was to build an agent capable of **autonomous tool selection** to find the most geographically and visually accurate representation of NYC points of interest.

## 2. Architecture & Decision Logic

The agent operates on a feedback loop centered around an **Agent State**.

### The Reasoning Loop

1. **Observe**: The agent checks its state (current best score, sources already searched).
2. **Decide**: A greedy randomizer algorithm (a varant of the epsilon-greedy algorithm) decides the next course of action in a non-deterministic fashion. Tiebreakers are handled by querying Tiny Llama (SLM), and often acts as the final judge.
3. **Act**: The chosen tool fetches candidates.
4. **Evaluate**:
   - **Visual Score**: CLIP calculates cosine similarity between the image pixels and the text "a photo of {POI} NYC".
   - **Geo Score**: Geopy calculates the Haversine distance from the target coordinates.
5. **Update**: The state is updated with new scores, and the loop repeats.

## 3. Scoring Matrix

The final score is a weighted sum designed to prioritize visual accuracy while rewarding proximity:

- **Visual Weight**: 70% ($V_{score}$)
- **Geo Weight**: 30% ($G_{score}$)
- **Bonus**: A `+0.08` aesthetic bonus is applied to high-resolution providers (Unsplash/Pexels).

$$
FinalScore = (V \times 0.7) + (G \times 0.3) + Bonus(0.08)
$$

## 4. Hardware Optimization (8GB RAM)

Running an LLM and a CLIP model simultaneously in a container requires strict memory management:

- **Quantization**: Used `Q4_K_M` GGUF format for the SLM to reduce memory footprint by 60%.
- **CPU Offloading**: Optimized for `torch-cpu` to ensure stability on standard laptop hardware.
- **Memory Safety**: Explicitly managed PIL image buffers to prevent heap overflow during the scoring of large batch results.

## 5. Conclusion

This agent demonstrates that even with limited local compute, small specialized models can replace large, expensive APIs for complex decision-making tasks. It balances performance, cost (API credits), and accuracy.

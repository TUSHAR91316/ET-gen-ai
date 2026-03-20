# Slide 1: ResQAI - The Concept

**Title:** ResQAI: Hyper-Local Generative Disaster Response Coordinator

**The Problem:**
*   Disaster response is chaotic; data is fragmented across social media, calls, and sensors.
*   "Golden Hour" is often lost due to information overload.
*   Existing tools show *where* events are, but don't tell responders *what to do*.

**Our Solution:**
*   **ResQAI** is an AI Agent that acts as a "Digital Dispatcher".
*   It ingests multi-modal data (Text, Audio, Vision).
*   It builds a live **Knowledge Graph** of the disaster zone.
*   **Novelty:** It doesn't just display data; it **generates actionable rescue plans** using Graph-RAG.

---

# Slide 2: How It Works (The Tech Stack)

**1. Multi-Modal Ingestion Engine:**
*   Listens to SOS tweets, emergency calls (Whisper STT), and drone feeds.
*   Classifies urgency (High/Medium/Low).

**2. Dynamic Knowledge Graph (The Brain):**
*   Maps relationships: [Victim] is trapped in [Building A] which is blocked by [Flood].
*   This context is far richer than simple vector databases.

**3. Generative Planning Agent (The Output):**
*   LLM (Gemini/GPT) queries the Graph.
*   Generates structured JSON plans:
    *   *Team Alpha -> Go to Sector 4 (Medical Emergency)*
    *   *Team Bravo -> Clear debris at Main St.*

---

# Slide 3: Impact & Scalability

**Validation Metrics:**
*   **Response Time:** Reducing decision latency from minutes to seconds.
*   **Accuracy:** High recall for "Critical" life-threatening events.

**Scalability:**
*   **Smart Cities:** Integration with traffic and emergency grids.
*   **Offline Mode:** Capable of running on portable edge servers when internet fails.

**Vision:**
*   Moving from "Reactive Response" to "Proactive Coordination".
*   Saving lives by making sense of the noise.

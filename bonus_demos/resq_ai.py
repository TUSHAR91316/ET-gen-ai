import json
import time
import random
from dataclasses import dataclass
from typing import List, Dict

# Simulating a basic GenAI / RAG flow for Disaster Response
# In production, this would connect to LangChain/LlamaIndex and actual LLM APIs

@dataclass
class EmergencyEvent:
    id: str
    type: str # 'fire', 'flood', 'medical'
    location: tuple # (lat, long)
    description: str
    priority: int # 1 (Critical) to 5 (Low)

class DisasterKnowledgeGraph:
    """
    A simple graph representation to hold context about the disaster zone.
    This helps the AI 'understand' relationships between events and resources.
    """
    def __init__(self):
        self.events = {}
        self.resources = {}

    def add_event(self, event: EmergencyEvent):
        print(f"[Graph Builder] Node added: {event.type.upper()} at {event.location}")
        self.events[event.id] = event

    def get_context(self) -> str:
        # Serializes the current state into a context string for the LLM
        context = "Current Active Emergencies:\n"
        for evt in self.events.values():
            context += f"- ID: {evt.id} | Type: {evt.type} | Priority: {evt.priority} | Desc: {evt.description}\n"
        return context

class ResQAI_Agent:
    def __init__(self, model_name="gemini-pro-vision-sim"):
        self.model_name = model_name
        self.graph = DisasterKnowledgeGraph()
    
    def ingest_data(self, raw_data: Dict):
        """
        Simulates ingesting multi-modal data (Text/Sensors)
        and normalizing it into our Knowledge Graph.
        """
        # Parsing logic (Mock NLP extraction)
        loc = raw_data.get('gps', (0,0))
        urgency = self._calculate_urgency(raw_data['text'])
        
        event = EmergencyEvent(
            id=f"evt_{int(time.time())}",
            type=raw_data.get('category', 'general'),
            location=loc,
            description=raw_data['text'],
            priority=urgency
        )
        self.graph.add_event(event)

    def _calculate_urgency(self, text: str) -> int:
        # Simple heuristic, in reality this would be an NLP classifier
        critical_keywords = ['trapped', 'dying', 'fire', 'collapse']
        if any(w in text.lower() for w in critical_keywords):
            return 1
        return 3

    def generate_response_plan(self):
        """
        The core GenAI loop:
        1. Retrieve Context from Graph
        2. Prompt the LLM
        3. Parse valid JSON plan
        """
        context = self.graph.get_context()
        
        system_prompt = f"""
        ACT AS: Disaster Response Coordinator AI.
        TASK: Analyze the following emergency context and assign resources.
        
        CONTEXT:
        {context}
        
        OUTPUT FORMAT: JSON List of actions.
        """
        
        print("\n--- Sending Prompt to LLM ---")
        print(system_prompt.strip())
        print("-----------------------------\n")
        
        # Simulate LLM Latency and Token Generation
        time.sleep(1.5) 
        return self._mock_llm_output()

    def _mock_llm_output(self):
        # This mocks what the GenAI would return based on the priority logic
        return {
            "strategy_id": "plan_alpha_1",
            "actions": [
                {"team": "Drone_Squad_A", "target": "evt_123", "action": "deploy_thermal_camera", "reason": "High confidence of survivors trapped in rubble"},
                {"team": "Medical_Unit_4", "target": "evt_456", "action": "dispatch_ambulance", "reason": "Reported cardiac arrest details in text"}
            ]
        }

if __name__ == "__main__":
    # --- DRIVER CODE ---
    
    # Initialize System
    system = ResQAI_Agent()
    
    # 1. Simulate Incoming Distress Signals (Twitter/SMS)
    incoming_stream = [
        {"text": "Building collapsed near Main St! People trapped under debris!", "category": "collapse", "gps": (34.05, -118.25)},
        {"text": "Water levels rising basement flooded, need evacuation.", "category": "flood", "gps": (34.06, -118.27)}
    ]
    
    print(">>> ResQAI System Online. Monitoring channels...\n")
    
    for signal in incoming_stream:
        print(f"Processing signal: {signal['text'][:30]}...")
        system.ingest_data(signal)
        time.sleep(0.5)
        
    # 2. Trigger Planning Phase
    print("\n>>> Analyzing Situation & Generating Plan...")
    plan = system.generate_response_plan()
    
    # 3. Output
    print(">>> GENERATED ACTION PLAN:")
    print(json.dumps(plan, indent=2))

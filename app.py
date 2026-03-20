import streamlit as st
import pandas as pd
import time
import json
from resq_ai import ResQAI_Agent

# Page Config
st.set_page_config(page_title="ResQAI Dashboard", page_icon="🚨", layout="wide")

# Custom CSS for "Dark/Emergency" Theme
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ff4b4b;
    }
    .priority-high { color: #ff4b4b; font-weight: bold; }
    .priority-med { color: #ffa421; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State for the Agent
if 'agent' not in st.session_state:
    st.session_state.agent = ResQAI_Agent()
    # Pre-seed with some data for the demo
    st.session_state.agent.ingest_data({
        "text": "Flood waters rising in Sector 4, people stranded on rooftops.", 
        "category": "flood", 
        "gps": (34.0522, -118.2437)
    })
    st.session_state.agent.ingest_data({
        "text": "Medical emergency at Central Station, cardiac arrest reported.", 
        "category": "medical", 
        "gps": (34.0407, -118.2468)
    })

def main():
    st.title("🚨 ResQAI Command Center")
    st.caption("Hyper-Local Generative Disaster Response Coordinator")

    # Layout: Sidebar for Controls/Feed, Main for Map/Plan
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Incoming Data Feed")
        
        # Simulation Controls
        with st.expander("Simulate New Incident", expanded=True):
            new_text = st.text_area("Emergency Report Text", "Building fire reported near the Downtown Plaza!")
            new_type = st.selectbox("Type", ["fire", "collapse", "flood", "medical"])
            lat = st.number_input("Latitude", value=34.0500)
            lon = st.number_input("Longitude", value=-118.2500)
            
            if st.button("Broadcast Signal"):
                with st.spinner("Ingesting Multi-Modal Data..."):
                    st.session_state.agent.ingest_data({
                        "text": new_text,
                        "category": new_type,
                        "gps": (lat, lon)
                    })
                st.success("Signal Received & Added to Knowledge Graph")

        st.divider()
        
        # Display Active Events List
        st.subheader("Active Incidents")
        events = st.session_state.agent.graph.events
        for eid, evt in events.items():
            p_color = "🔴" if evt.priority == 1 else "🟠"
            st.markdown(f"""
            <div class="metric-card">
                {p_color} <strong>{evt.type.upper()}</strong><br>
                <small>{evt.description}</small><br>
                <small>📍 {evt.location}</small>
            </div>
            <br>
            """, unsafe_allow_html=True)

    with col2:
        # Live Map View
        st.subheader("Geospatial Situational Awareness")
        
        # Convert events to DataFrame for Map
        map_data = []
        for evt in events.values():
            map_data.append({
                "lat": evt.location[0],
                "lon": evt.location[1],
                "type": evt.type,
                "priority": 100 if evt.priority == 1 else 50 # Size based on priority
            })
        
        if map_data:
            df = pd.DataFrame(map_data)
            st.map(df, latitude="lat", longitude="lon", size="priority", color="#ff4b4b")
        else:
            st.info("No active incidents on the map.")

        st.divider()

        # GenAI Planner Section
        st.subheader("🤖 Generative Response Planner")
        
        if st.button("Generate Action Plan (RAG)", type="primary"):
            with st.spinner("Querying Knowledge Graph & Optimizing Resources..."):
                response_plan = st.session_state.agent.generate_response_plan()
            
            st.success("Plan Generated Successfully!")
            
            # Display Plan cleanly
            st.markdown(f"**Strategy ID:** `{response_plan['strategy_id']}`")
            
            for action in response_plan['actions']:
                st.info(f"""
                **Team:** {action['team']} ➡️ **Target:** {action['target']}
                \n**Action:** {action['action']}
                \n*Reasoning: {action['reason']}*
                """)
            
            with st.expander("View Raw JSON Output"):
                st.json(response_plan)

if __name__ == "__main__":
    main()

import json
import os
from typing import List, Optional
from app.core.models import AgentProfile
from app.core.config import settings

class AgentRegistry:
    def __init__(self, agents_file: str = "data/agents.json"):
        # Resolve path relative to workspace root if needed, though usually we run from root
        self.agents_file = agents_file
        self.profiles: List[AgentProfile] = []
        self._load_agents()

    def _load_agents(self):
        if not os.path.exists(self.agents_file):
            print(f"Warning: Agents file not found at {self.agents_file}")
            return
        
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.profiles = [AgentProfile(**item) for item in data]
        except Exception as e:
            print(f"Error loading agent registry: {e}")

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        for p in self.profiles:
            if p.id == agent_id:
                return p
        return None

    def list_agents(self) -> List[AgentProfile]:
        return self.profiles

    def register_agent(self, profile: AgentProfile):
        # Check if exists
        for i, p in enumerate(self.profiles):
            if p.id == profile.id:
                self.profiles[i] = profile
                self._save_agents()
                print(f"Agent {profile.id} updated.")
                return

        self.profiles.append(profile)
        self._save_agents()
        print(f"Agent {profile.id} registered.")

    def _save_agents(self):
        try:
            # Check if directory exists
            os.makedirs(os.path.dirname(self.agents_file), exist_ok=True)
            
            with open(self.agents_file, 'w', encoding='utf-8') as f:
                # Convert pydantic models to dict
                data = [p.dict() for p in self.profiles]
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving agent registry: {e}")

# Global instance
registry = AgentRegistry()

def get_agent_registry() -> AgentRegistry:
    return registry

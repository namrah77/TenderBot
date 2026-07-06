import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

@dataclass
class AgentConfig:
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    mcp_server_port: int = 8090
    max_iterations: int = 3
    pii_redaction_enabled: bool = True
    injection_detection_enabled: bool = True
    pipeline_debug: bool = os.getenv("PIPELINE_DEBUG", "").lower() in ("1", "true", "yes")

config = AgentConfig()
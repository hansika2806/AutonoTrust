"""
config.py — Environment variables, constants, model names.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === LLM ===
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
GROQ_MODEL: str = "llama-3.3-70b-versatile"
OPENROUTER_MODEL: str = "google/gemma-3-4b-it:free"
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# === Blockchain ===
POLYGON_AMOY_RPC_URL: str = os.getenv("POLYGON_AMOY_RPC_URL", "")
CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")

CLIENT_PRIVATE_KEY: str = os.getenv("CLIENT_PRIVATE_KEY", "")
CLIENT_ADDRESS: str = os.getenv("CLIENT_ADDRESS", "")

AUDITOR_PRIVATE_KEY: str = os.getenv("AUDITOR_PRIVATE_KEY", "")
AUDITOR_ADDRESS: str = os.getenv("AUDITOR_ADDRESS", "")

EXECUTOR_1_PRIVATE_KEY: str = os.getenv("EXECUTOR_1_PRIVATE_KEY", "")
EXECUTOR_1_ADDRESS: str = os.getenv("EXECUTOR_1_ADDRESS", "")

EXECUTOR_2_PRIVATE_KEY: str = os.getenv("EXECUTOR_2_PRIVATE_KEY", "")
EXECUTOR_2_ADDRESS: str = os.getenv("EXECUTOR_2_ADDRESS", "")

DEPLOYER_PRIVATE_KEY: str = os.getenv("DEPLOYER_PRIVATE_KEY", "")

# === Chroma ===
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

# === Graph defaults ===
MAX_RETRIES: int = 2
CODE_SANDBOX_TIMEOUT: int = 5
CODE_SANDBOX_MEMORY_MB: int = 256

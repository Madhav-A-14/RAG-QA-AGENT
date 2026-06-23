import os                   
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"

from config import agent

from deepteam import red_team
from deepteam.vulnerabilities import misinformation
from deepteam.attacks.single_turn import PromptInjection


class RAGSecurity_Tester:
    
    # ── Calling the RAG Model ─────────────────────────────────────────────────────
    
    def _model_callback(self,input:str) -> str:
        
        result = agent.ask(input)
        if isinstance(result,dict):
            return result.get("answer",str(result))
        return str(result)
    
    # ── Building the necessary Vulnerabilities ─────────────────────────────────────────────────────

        # This is where we define what vulnerabilities to test for.
    
    def _build_vulnerabilities(self) -> list:
        
        return [
            misinformation(types = ["factual errors","unsupported_claims"]),
            
            
            
            # Factual_errors -> agent stating something that is not factually correct.
            # Unsupported_claims -> agent claims not backed up by retrieved corpus
        ]
    
    # ── Setting up Attack ─────────────────────────────────────────────────────
    
        # This is where  we define "how are we trying to break it" rule.
        # PromptInjection contains sneaky instructions to make the agent ignore its grounding rules.
        
    def _build_attacks(self) -> list:
        return[
            PromptInjection(weight=2),
        ]
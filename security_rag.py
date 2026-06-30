import os                   
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"

from config import agent
from unittest.mock import patch

from deepteam import red_team
from deepteam.vulnerabilities import Misinformation, PIILeakage,Bias
from deepteam.attacks.single_turn import PromptInjection


# ── Calling the RAG Model ─────────────────────────────────────────────────────

async def model_callback(input: str) -> str:
    result = agent.ask(input)
    if isinstance(result, dict):
        return result.get("answer", str(result))
    return str(result)



def _noop_post(*args, **kwargs):
    print("\n[INFO] Skipping Confident AI cloud upload (not on Enterprise plan).")


class RAGSecurityTester:
    
    
    
    # ── Building the necessary Vulnerabilities ─────────────────────────────────────────────────────

        # This is where we define what vulnerabilities to test for.
    
    def _build_vulnerabilities(self) -> list:
        
        return [
            Misinformation(types = ["factual_errors","unsupported_claims"]),
            PIILeakage(types=["api_and_database_access","session_leak"]),
            Bias(types = ["gender","politics"]),
            
            
            
            # Factual_errors -> agent stating something that is not factually correct.
            # Unsupported_claims -> agent claims not backed up by retrieved corpus
            # api_and_database_access -> checks whether the agent can be tricked into exposing details that should be hidden from end users like database schema, ChromaDB details etc.
            # session_leak -> checks whether the agent can be tricked into revealing info about different user's session or previous conversation.
            # gender -> checks whether the agent makes assumptions or favor towards a particular gender.
            # politics -> tests whether the agent leans towards a political party, ideology etc while answering.
        ]
    
    # ── Setting up Attack ─────────────────────────────────────────────────────
    
        # This is where  we define "how are we trying to break it" rule.
        # PromptInjection contains sneaky instructions to make the agent ignore its grounding rules.
        
    def _build_attacks(self) -> list:
        return[
            PromptInjection(weight=2),
        ]
        
    
    # ── Running the Attack ─────────────────────────────────────────────────────
        
        # This function ties every other function together 
        
    def run(self):
        
        print("\n" + "=" * 60)
        print("PHASE 1 SECURITY TEST -- MISINFORMATION")
        print("=" * 60)
        
        with patch(
            "deepteam.red_teamer.red_teamer.RedTeamer._post_risk_assessment",
            new =_noop_post,
        ):
            risk_assessment = red_team(
                model_callback=model_callback,
                vulnerabilities=self._build_vulnerabilities(),
                attacks=self._build_attacks(),
                max_concurrent=1,
                attacks_per_vulnerability_type = 2,
            )
        # Prints an overview of Risk Assessment done.
        print("\n" + "=" * 60)
        print("RISK ASSESSMENT OVERVIEW")
        print("=" * 60)
        print(risk_assessment.overview)

        # Gives a detailed report of Risk Assessment done.
        print("\n" + "=" * 60)
        print("RISK ASSESSMENT TEST CASES")
        print("=" * 60)
        print(risk_assessment.test_cases)

        
        # Saving everything to a Local Folder.
        risk_assessment.save(to="./security-results/")
        print("\nResults saved to ./security-results/")
        
        return risk_assessment
    

# Entry Point of the Code....

if __name__ == "__main__":
    tester = RAGSecurityTester()
    tester.run()
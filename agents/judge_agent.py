import logging
import os
import re
import json

from pydantic import BaseModel, Field
from agents.llm_client import llm
from agents.prompts.judge_prompt import build_judge_prompt
from agents.json_utils import invoke_json

logger = logging.getLogger(__name__)


class JudgeScore(BaseModel):
    grounding: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    overall: int = Field(ge=0, le=10)
    flagged_issues: list[str] = Field(default_factory=list)


JUDGE_MODE = os.getenv("JUDGE_MODE", "api")  # "api" or "finetuned"

_finetuned_model = None
_finetuned_tokenizer = None


def _load_finetuned_model():
    global _finetuned_model, _finetuned_tokenizer
    if _finetuned_model is None:
        from unsloth import FastLanguageModel

        _finetuned_model, _finetuned_tokenizer = FastLanguageModel.from_pretrained(
            model_name=os.getenv("FINETUNED_ADAPTER_PATH", "finetune/full_adapter_v1"),
            max_seq_length=6144,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(_finetuned_model)
    return _finetuned_model, _finetuned_tokenizer


def _judge_with_api(prompt: str) -> dict:
    json_instructions = """
Please output ONLY a valid JSON object matching the following structure exactly. Do not wrap it in markdown block quotes or add any extra text before or after:
{
  "grounding": 0,
  "completeness": 0,
  "clarity": 0,
  "overall": 0,
  "flagged_issues": ["string", "string", ...]
}
"""
    full_prompt = prompt + json_instructions

    try:
        validated_score = invoke_json(llm, full_prompt, JudgeScore)
        return {"judge_score": validated_score.model_dump()}
    except Exception as e:
        logger.warning("Judge evaluation failed: %s", e)
        return {"judge_score": None}



def _judge_with_finetuned(prompt: str) -> dict:
    try:
        model, tokenizer = _load_finetuned_model()
        formatted = f"### Instruction:\n{prompt}\n\n### Response:\n"
        inputs = tokenizer(formatted, return_tensors="pt").to("cuda")
        outputs = model.generate(**inputs, max_new_tokens=300, use_cache=True)
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        raw_response = generated_text.split("### Response:\n")[-1]

        # Try clean JSON first
        match = re.search(r"\{.*?\}", raw_response, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                validated = JudgeScore(**parsed)
                return {"judge_score": validated.model_dump()}
            except Exception:
                pass  # fall through to prose extraction

        # Prose extraction — model outputs "Grounding: 7" style lines
        def extract_score(pattern):
            m = re.search(pattern, raw_response, re.IGNORECASE)
            return max(1, min(10, int(m.group(1)))) if m else 5

        grounding = extract_score(r"Grounding[:\s]+([0-9]+)")
        completeness = extract_score(r"Completeness[:\s]+([0-9]+)")
        clarity = extract_score(r"Clarity[:\s]+([0-9]+)")
        overall = extract_score(r"Overall[:\s]+([0-9]+)")
        if overall == 5:
            overall = max(1, min(10, round((grounding + completeness + clarity) / 3)))
            if min(grounding, completeness, clarity) <= 3:
                overall = min(overall, 5)

        issues = []
        list_match = re.search(r"flagged_issues\s*=\s*\[(.+?)\]", raw_response, re.DOTALL)
        if list_match:
            raw_list = list_match.group(1)
            issues = [
                s.strip().strip("'\"")
                for s in re.split(r",\s*'|,\s*\"", raw_list)
                if s.strip().strip("'\"")
            ]
        else:
            bullet_matches = re.findall(
                r"[-•]\s*(.+?)(?=\n[-•]|\nGrounding|\nCompleteness|\nClarity|\nOverall|$)",
                raw_response,
                re.DOTALL,
            )
            issues = [m.strip() for m in bullet_matches if len(m.strip()) > 10][:5]

        validated = JudgeScore(
            grounding=grounding,
            completeness=completeness,
            clarity=clarity,
            overall=overall,
            flagged_issues=issues,
        )
        return {"judge_score": validated.model_dump()}
    except Exception as e:
        logger.warning("Fine-tuned judge inference failed: %s", e)
        return {"judge_score": None}



def judge_agent_node(state: dict) -> dict:
    if os.environ.get("SKIP_JUDGE", "false") == "true":
        return {
            "judge_score": {
                "grounding": 0,
                "completeness": 0,
                "clarity": 0,
                "overall": 0,
                "flagged_issues": ["[skipped during experiment]"],
            }
        }
    report_draft = state.get("report_draft", {})
    retrieved_chunks = state.get("retrieved_chunks", [])
    prompt = build_judge_prompt(report_draft, retrieved_chunks)

    if JUDGE_MODE == "finetuned":
        return _judge_with_finetuned(prompt)
    else:
        return _judge_with_api(prompt)
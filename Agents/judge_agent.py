import os
import re
import json

from pydantic import BaseModel
from agents.llm_client import llm
from agents.prompts.judge_prompt import build_judge_prompt


class JudgeScore(BaseModel):
    grounding: int
    completeness: int
    clarity: int
    overall: int
    flagged_issues: list[str]


FALLBACK_JUDGE_SCORE = {
    "grounding": -1,
    "completeness": -1,
    "clarity": -1,
    "overall": -1,
    "flagged_issues": ["Judge evaluation failed — LLM call error, this score is not real"],
}

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


def _judge_with_api(prompt) -> dict:
    structured_llm = llm.with_structured_output(JudgeScore)
    try:
        result = structured_llm.invoke(prompt)
        return {"judge_score": result.model_dump()}
    except Exception as e:
        print(f"[judge_agent_node/api] LLM call failed: {e}")
        return {"judge_score": FALLBACK_JUDGE_SCORE}


def _judge_with_finetuned(prompt) -> dict:
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

        grounding    = extract_score(r"Grounding[:\s]+([0-9]+)")
        completeness = extract_score(r"Completeness[:\s]+([0-9]+)")
        clarity      = extract_score(r"Clarity[:\s]+([0-9]+)")
        overall      = extract_score(r"Overall[:\s]+([0-9]+)")
        if overall == 5:  # wasn't found, compute it
            overall = max(1, min(10, round((grounding + completeness + clarity) / 3)))
            if min(grounding, completeness, clarity) <= 3:
                overall = min(overall, 5)

        # Extract flagged_issues list if present
        issues = []
        list_match = re.search(r"flagged_issues\s*=\s*\[(.+?)\]", raw_response, re.DOTALL)
        if list_match:
            raw_list = list_match.group(1)
            issues = [s.strip().strip("'\"") for s in re.split(r",\s*'|,\s*\"", raw_list) if s.strip().strip("'\"")]
        else:
            # Fall back to bullet-point style flagged issues
            bullet_matches = re.findall(r"[-•]\s*(.+?)(?=\n[-•]|\nGrounding|\nCompleteness|\nClarity|\nOverall|$)", raw_response, re.DOTALL)
            issues = [m.strip() for m in bullet_matches if len(m.strip()) > 10][:5]

        validated = JudgeScore(
            grounding=grounding,
            completeness=completeness,
            clarity=clarity,
            overall=overall,
            flagged_issues=issues
        )
        return {"judge_score": validated.model_dump()}
    except Exception as e:
        print(f"[judge_agent_node/finetuned] Fine-tuned judge failed: {e}")
        return {"judge_score": FALLBACK_JUDGE_SCORE}


def judge_agent_node(state: dict) -> dict:
    report_draft = state.get("report_draft", {})
    retrieved_chunks = state.get("retrieved_chunks", [])
    prompt = build_judge_prompt(report_draft, retrieved_chunks)

    if JUDGE_MODE == "finetuned":
        return _judge_with_finetuned(prompt)
    else:
        return _judge_with_api(prompt)
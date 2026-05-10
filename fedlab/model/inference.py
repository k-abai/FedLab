"""Helpers for loading Phi-3 + optional LoRA adapter and extracting probabilities."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

BASE_MODEL = "microsoft/Phi-3-mini-4k-instruct"
_PROB_RE = re.compile(r"probability[^0-9]*([0-9]*\.?[0-9]+)", re.IGNORECASE)


def extract_probability(text: str, default: float = 0.5) -> float:
    """Pull a probability in [0,1] from arbitrary generation. Robust to '0.85', '85%', etc."""
    if not text:
        return default
    m = _PROB_RE.search(text)
    if m:
        try:
            v = float(m.group(1))
        except ValueError:
            return default
        if v > 1.0:
            v /= 100.0
        return max(0.0, min(1.0, v))
    pct = re.search(r"([0-9]*\.?[0-9]+)\s*%", text)
    if pct:
        try:
            return max(0.0, min(1.0, float(pct.group(1)) / 100.0))
        except ValueError:
            return default
    lower = text.lower()
    if "yes" in lower and "no" not in lower:
        return 0.75
    if "no" in lower and "yes" not in lower:
        return 0.25
    return default


def load_model_and_tokenizer(adapter_path: Optional[str | Path] = None, four_bit: bool = True):
    """Load base Phi-3 with optional LoRA adapter. Imports are local so this module imports cleanly."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant_config = None
    if four_bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
    )

    if adapter_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(adapter_path))

    return model, tokenizer


class PhiPredictor:
    """Wraps a model+tokenizer and exposes predict_probability for the benchmark interface."""

    def __init__(self, model, tokenizer, max_new_tokens: int = 64):
        self.model = model
        self.tokenizer = tokenizer
        self.max_new_tokens = max_new_tokens

    def predict_probability(self, question: str, context: str = "") -> float:
        prompt = f"Question: {question}\nContext: {context}\nAnswer with 'Probability: <0-1>.':\n"
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        out = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        text = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return extract_probability(text)

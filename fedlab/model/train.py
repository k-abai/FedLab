"""Fine-tune Phi-3-mini with QLoRA on Polymarket-derived instruction data.

Targets a 6 GB consumer GPU (e.g. RTX 3050): 4-bit NF4 + LoRA r=8, batch 1, grad accum 8.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

BASE_MODEL = "microsoft/Phi-3-mini-4k-instruct"
TRAIN_FILE = Path(__file__).resolve().parents[1] / "data" / "train.jsonl"
ADAPTER_DIR = Path(__file__).parent / "adapters" / "v0"


@dataclass
class TrainConfig:
    base_model: str = BASE_MODEL
    train_file: Path = TRAIN_FILE
    output_dir: Path = ADAPTER_DIR
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    target_modules: tuple[str, ...] = ("q_proj", "v_proj")
    epochs: int = 3
    learning_rate: float = 2e-4
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    max_seq_length: int = 1024


def load_jsonl(path: Path) -> Dataset:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return Dataset.from_list(rows)


def format_example(ex: dict) -> str:
    instruction = ex.get("instruction", "")
    context = ex.get("input", "")
    output = ex.get("output", "")
    ctx_block = f"\nContext: {context}" if context else ""
    return f"<|user|>\n{instruction}{ctx_block}\n<|assistant|>\n{output}"


def build_quant_config() -> BitsAndBytesConfig:
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )


def train(cfg: TrainConfig = TrainConfig()) -> None:
    tokenizer = AutoTokenizer.from_pretrained(cfg.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model,
        quantization_config=build_quant_config(),
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    lora_cfg = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules=list(cfg.target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.4f}%)")

    raw = load_jsonl(cfg.train_file)

    def tokenize(batch):
        texts = [format_example(b) for b in (
            {k: batch[k][i] for k in batch} for i in range(len(batch[next(iter(batch))]))
        )]
        return tokenizer(
            texts,
            max_length=cfg.max_seq_length,
            truncation=True,
            padding=False,
        )

    tokenized = raw.map(tokenize, batched=True, remove_columns=raw.column_names)

    training_args = TrainingArguments(
        output_dir=str(cfg.output_dir),
        num_train_epochs=cfg.epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        learning_rate=cfg.learning_rate,
        fp16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
        optim="paged_adamw_8bit",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(cfg.output_dir))
    tokenizer.save_pretrained(str(cfg.output_dir))
    print(f"Saved LoRA adapter to {cfg.output_dir}")


if __name__ == "__main__":
    train()

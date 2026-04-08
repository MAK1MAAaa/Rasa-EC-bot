#!/usr/bin/env python
"""Train Qwen3.5-2B with QLoRA using config file."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)
from env_utils import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoRA from YAML config.")
    parser.add_argument("--config", required=True, type=Path)
    return parser.parse_args()


def resolve_path(value: str, root_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (root_dir / path).resolve()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a dict-like YAML.")
    return cfg


def format_chat(example: dict[str, Any], tokenizer: AutoTokenizer) -> dict[str, Any]:
    text = tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )
    return {"text": text}


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    lora_root = config_path.parent.parent
    load_env_file(lora_root / ".env")
    cfg = load_config(config_path)

    seed = int(cfg.get("seed", 42))
    set_seed(seed)

    base_model = os.getenv("BASE_MODEL_PATH", "").strip() or cfg.get("base_model", "")
    if not base_model:
        raise ValueError(
            "Missing base model. Set BASE_MODEL_PATH in LoRA/.env or base_model in config."
        )
    train_file = resolve_path(cfg["train_file"], lora_root)
    eval_file = resolve_path(cfg["eval_file"], lora_root)
    output_dir = resolve_path(cfg["output_dir"], lora_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    cuda_available = torch.cuda.is_available()
    allow_cpu_training = os.getenv("ALLOW_CPU_TRAINING", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not cuda_available and not allow_cpu_training:
        raise RuntimeError(
            "CUDA is not available in this environment (torch is CPU build). "
            "Install CUDA-enabled PyTorch, then rerun. "
            "If you intentionally want very slow CPU training, set ALLOW_CPU_TRAINING=1."
        )

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=bool(cfg.get("load_in_4bit", True)),
        bnb_4bit_quant_type=cfg.get("bnb_4bit_quant_type", "nf4"),
        bnb_4bit_use_double_quant=bool(cfg.get("bnb_4bit_use_double_quant", True)),
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        trust_remote_code=True,
        device_map="auto",
        dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    target_modules = cfg.get(
        "target_modules",
        [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    peft_cfg = LoraConfig(
        r=int(cfg.get("lora_r", 16)),
        lora_alpha=int(cfg.get("lora_alpha", 32)),
        lora_dropout=float(cfg.get("lora_dropout", 0.05)),
        target_modules=target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, peft_cfg)
    model.print_trainable_parameters()

    data_files = {"train": str(train_file), "validation": str(eval_file)}
    raw_dataset = load_dataset("json", data_files=data_files)
    processed = raw_dataset.map(
        lambda x: format_chat(x, tokenizer),
        remove_columns=raw_dataset["train"].column_names,
        desc="Formatting chat examples",
    )

    max_seq_len = int(cfg.get("max_seq_len", 1024))

    def tokenize_batch(batch: dict[str, Any]) -> dict[str, Any]:
        return tokenizer(batch["text"], truncation=True, max_length=max_seq_len)

    tokenized = processed.map(
        tokenize_batch,
        batched=True,
        remove_columns=processed["train"].column_names,
        desc="Tokenizing",
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    requested_bf16 = bool(cfg.get("bf16", True))
    requested_fp16 = bool(cfg.get("fp16", False))
    bf16_supported = bool(cuda_available and torch.cuda.is_bf16_supported())
    effective_bf16 = requested_bf16 and bf16_supported
    effective_fp16 = requested_fp16
    if requested_bf16 and not bf16_supported:
        if not effective_fp16:
            effective_fp16 = True
        print(
            "bf16 requested but not supported on this setup; "
            "falling back to fp16 for TrainingArguments."
        )
    if effective_bf16 and effective_fp16:
        effective_fp16 = False

    training_kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "num_train_epochs": float(cfg.get("num_train_epochs", 1)),
        "per_device_train_batch_size": int(cfg.get("per_device_train_batch_size", 1)),
        "per_device_eval_batch_size": int(cfg.get("per_device_eval_batch_size", 1)),
        "gradient_accumulation_steps": int(cfg.get("gradient_accumulation_steps", 8)),
        "learning_rate": float(cfg.get("learning_rate", 2e-4)),
        "lr_scheduler_type": str(cfg.get("lr_scheduler_type", "cosine")),
        "warmup_ratio": float(cfg.get("warmup_ratio", 0.03)),
        "logging_steps": int(cfg.get("logging_steps", 10)),
        "save_steps": int(cfg.get("save_steps", 100)),
        "eval_steps": int(cfg.get("eval_steps", 100)),
        "save_total_limit": int(cfg.get("save_total_limit", 2)),
        "save_strategy": "steps",
        "bf16": effective_bf16,
        "fp16": effective_fp16,
        "gradient_checkpointing": bool(cfg.get("gradient_checkpointing", True)),
        "optim": str(cfg.get("optim", "paged_adamw_8bit")),
        "report_to": [],
        "remove_unused_columns": False,
        "dataloader_pin_memory": False,
        "seed": seed,
    }
    ta_params = inspect.signature(TrainingArguments.__init__).parameters
    if "evaluation_strategy" in ta_params:
        training_kwargs["evaluation_strategy"] = "steps"
    elif "eval_strategy" in ta_params:
        training_kwargs["eval_strategy"] = "steps"
    else:
        raise RuntimeError(
            "Your transformers version does not expose evaluation strategy arg."
        )
    training_args = TrainingArguments(**training_kwargs)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=data_collator,
    )

    trainer.train()

    adapter_dir = output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    trainer.save_state()

    run_summary = {
        "base_model": base_model,
        "train_file": str(train_file),
        "eval_file": str(eval_file),
        "output_dir": str(output_dir),
        "adapter_dir": str(adapter_dir),
        "max_seq_len": max_seq_len,
        "seed": seed,
    }
    with (output_dir / "run_summary.json").open("w", encoding="utf-8") as f:
        json.dump(run_summary, f, indent=2)

    print("Training complete.")
    print(json.dumps(run_summary, indent=2))


if __name__ == "__main__":
    main()

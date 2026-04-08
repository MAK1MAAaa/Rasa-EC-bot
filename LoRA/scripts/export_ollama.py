#!/usr/bin/env python
"""Merge LoRA adapter, export GGUF, and create Ollama model."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import torch
from env_utils import load_env_file
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export LoRA adapter to merged HF model and Ollama artifact."
    )
    parser.add_argument("--base-model", required=False, default=None)
    parser.add_argument("--adapter-dir", required=True, type=Path)
    parser.add_argument("--merged-dir", required=True, type=Path)
    parser.add_argument("--gguf-dir", required=True, type=Path)
    parser.add_argument("--ollama-model-name", required=True)
    parser.add_argument("--llama-cpp-dir", type=Path, default=None)
    parser.add_argument("--quant-type", default="Q4_K_M")
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def find_llama_cpp_dir(explicit_dir: Path | None) -> Path:
    if explicit_dir:
        if explicit_dir.exists():
            return explicit_dir.resolve()
        raise FileNotFoundError(f"llama.cpp dir not found: {explicit_dir}")
    env_path = Path.cwd() / "tools" / "llama.cpp"
    if env_path.exists():
        return env_path.resolve()
    raise FileNotFoundError(
        "Cannot find llama.cpp. Pass --llama-cpp-dir or place it under LoRA/tools/llama.cpp"
    )


def to_posix(path: Path) -> str:
    return path.resolve().as_posix()


def main() -> None:
    args = parse_args()
    lora_root = Path(__file__).resolve().parent.parent
    load_env_file(lora_root / ".env")
    base_model = args.base_model or os.getenv("BASE_MODEL_PATH", "").strip() or "Qwen/Qwen3.5-2B"
    adapter_dir = args.adapter_dir.resolve()
    merged_dir = args.merged_dir.resolve()
    gguf_dir = args.gguf_dir.resolve()
    merged_dir.mkdir(parents=True, exist_ok=True)
    gguf_dir.mkdir(parents=True, exist_ok=True)

    print("Merging adapter into base model weights...")
    model = AutoPeftModelForCausalLM.from_pretrained(
        str(adapter_dir),
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    merged_model = model.merge_and_unload()
    tokenizer = AutoTokenizer.from_pretrained(str(adapter_dir), trust_remote_code=True)
    merged_model.save_pretrained(str(merged_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(merged_dir))
    print(f"Merged model saved to {merged_dir}")

    llama_cpp_dir = find_llama_cpp_dir(args.llama_cpp_dir)
    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        raise FileNotFoundError(f"Missing converter script: {convert_script}")

    quantize_bin = llama_cpp_dir / "llama-quantize.exe"
    if not quantize_bin.exists():
        quantize_bin = llama_cpp_dir / "llama-quantize"
    if not quantize_bin.exists():
        raise FileNotFoundError(
            "Missing llama-quantize executable. Build llama.cpp first."
        )

    f16_file = gguf_dir / "qwen3.5-2b-lora-ec-f16.gguf"
    q4_file = gguf_dir / "qwen3.5-2b-lora-ec-q4_k_m.gguf"

    run_cmd(
        [
            "python",
            str(convert_script),
            str(merged_dir),
            "--outfile",
            str(f16_file),
            "--outtype",
            "f16",
        ]
    )
    run_cmd([str(quantize_bin), str(f16_file), str(q4_file), args.quant_type])

    modelfile = gguf_dir / "Modelfile"
    modelfile.write_text(
        (
            f"FROM {to_posix(q4_file)}\n"
            "SYSTEM \"You are an ecommerce customer-support assistant. "
            "Never fabricate order IDs. Ask for explicit confirmation before sensitive actions.\"\n"
            "PARAMETER temperature 0.2\n"
            "PARAMETER top_p 0.9\n"
        ),
        encoding="utf-8",
    )
    print(f"Modelfile written to {modelfile}")

    if shutil.which("ollama") is None:
        raise RuntimeError("`ollama` command not found in PATH.")
    run_cmd(["ollama", "create", args.ollama_model_name, "-f", str(modelfile)])
    print(f"Ollama model ready: {args.ollama_model_name}")
    print(f"Base model reference: {base_model}")


if __name__ == "__main__":
    main()

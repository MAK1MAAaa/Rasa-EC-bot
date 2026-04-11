#!/usr/bin/env python
"""Generate an Ollama Modelfile for a LoRA adapter and optionally register it."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为 LoRA 适配器生成 Ollama Modelfile。")
    parser.add_argument("--adapter-dir", required=True, type=Path, help="LoRA adapter 目录。")
    parser.add_argument("--base-model", required=True, help="Ollama 中已经存在的基础模型名，例如 qwen3.5:2b。")
    parser.add_argument("--model-name", required=True, help="导出的 Ollama 模型名，例如 qwen3.5:2b-lora。")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ollama_export"),
        help="Modelfile 输出目录。",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="写入 Modelfile 的默认温度参数。",
    )
    parser.add_argument(
        "--run-create",
        action="store_true",
        help="生成 Modelfile 后直接执行 ollama create。",
    )
    return parser.parse_args()


def ensure_adapter_dir(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Adapter directory not found: {resolved}")
    config_path = resolved / "adapter_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing adapter_config.json in: {resolved}")
    return resolved


def build_modelfile(base_model: str, adapter_dir: Path, temperature: float) -> str:
    return "\n".join(
        [
            f"FROM {base_model}",
            f"ADAPTER {adapter_dir}",
            f"PARAMETER temperature {temperature}",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    adapter_dir = ensure_adapter_dir(args.adapter_dir)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    modelfile_path = output_dir / "Modelfile"
    modelfile_path.write_text(
        build_modelfile(args.base_model, adapter_dir, args.temperature),
        encoding="utf-8",
    )

    print(f"Modelfile saved to: {modelfile_path}")
    print(f"Suggested command: ollama create {args.model_name} -f {modelfile_path}")

    if args.run_create:
        command = ["ollama", "create", args.model_name, "-f", str(modelfile_path)]
        subprocess.run(command, check=True)
        print(f"Ollama model created: {args.model_name}")


if __name__ == "__main__":
    main()

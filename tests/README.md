# Tests

`tests/` 现在只保留普通代码测试，不再作为 benchmark 的入口、数据目录或结果目录。

## 当前测试文件

| 文件 | 说明 |
| --- | --- |
| `test_chat_router_logic.py` | 聊天路由逻辑测试 |
| `test_chat_memory_logic.py` | 记忆系统逻辑测试 |
| `test_product_recommendation_logic.py` | 商品推荐逻辑测试 |

## 运行

```powershell
cd backend
uv sync
uv run python -m unittest discover -s ..\tests -p "test_*.py"
```

## 说明

- benchmark 相关工程、数据集、运行脚本、结果归档和分析脚本已经迁到 [../benchmark/README.md](../benchmark/README.md)。
- 历史 `tests/benchmark_results/` 仅作为旧实验归档，不属于当前默认流程。

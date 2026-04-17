# Tests

`tests/` 现在只保留普通代码测试，不再作为 benchmark 的入口、数据目录或结果目录。

## 当前测试文件

| 文件                                   | 说明             |
| -------------------------------------- | ---------------- |
| `test_chat_router_logic.py`            | 聊天路由逻辑测试 |
| `test_chat_memory_logic.py`            | 记忆系统逻辑测试 |
| `test_product_recommendation_logic.py` | 商品推荐逻辑测试 |

## 运行

Windows：

```powershell
cd backend
uv sync
uv run python -m unittest discover -s ..\tests -p "test_*.py"
```

macOS / Linux：

```bash
cd backend
uv sync
uv run python -m unittest discover -s ../tests -p "test_*.py"
```

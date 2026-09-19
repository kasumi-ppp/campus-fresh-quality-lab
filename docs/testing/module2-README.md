# 模块二 AI 生成测试：运行方式说明

本说明对应成员 C 的模块二「AI 测」交付物：AI 生成的测试用例清单与自动化测试脚本。

## 1. 交付物

| 交付物 | 位置 |
| --- | --- |
| AI 生成用例清单（21 条） | `docs/testing/module2-ai-test-case-matrix.xlsx` |
| AI 生成自动化脚本（购物车 6 条） | `apps/df_cart/tests_ai_generated.py` |
| AI 生成自动化脚本（订单与库存 14 条，含支付回归） | `apps/df_order/tests_ai_generated.py` |
| AI 生成自动化脚本（登录回跳安全 3 条） | `apps/df_user/tests_ai_generated.py` |
| 完整运行输出记录 | `docs/testing/module2-automation-run-output.txt` |
| AI 实践过程与对照实验记录 | `docs/ai-records/2026-09-19-member-c-ai-testing.md` |

## 2. 环境准备

与项目主 README 相同：

```powershell
cd "C:\Users\32915\Desktop\软件测试\campus-fresh-quality-lab"
.\.venv\Scripts\Activate.ps1   # 如无虚拟环境则 python -m venv .venv 后激活
python -m pip install -r requirements.txt
```

自动化测试使用 Django 自带测试数据库，不需要提前准备业务数据，也不会修改本地的 `db.sqlite3`。

## 3. 一键运行

```powershell
python manage.py test apps.df_user.tests_ai_generated apps.df_order.tests_ai_generated apps.df_cart.tests_ai_generated -v 2
```

预期输出末尾：`Ran 23 tests ... OK`。

如需连同全部既有回归一起运行：

```powershell
python manage.py test
```

## 4. 用例与脚本的对应关系

用例编号写在每个测试方法的 docstring 第一行（如 `C-AI-CART-001`），
与用例清单表格 A 列一一对应；表格「证据路径」列记录了运行输出文件与对应测试函数名。

## 5. 生成过程声明

21 条用例与三个测试文件由 AI 工具（ZCode 智能体，GLM 模型）依据
`docs/requirements/member-c-cart-order-requirements.md` 生成，成员 C 逐条审核、
修正并真实执行。生成与审核过程记录见 `docs/ai-records/2026-09-19-member-c-ai-testing.md`。

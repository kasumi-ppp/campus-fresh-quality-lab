# 校园鲜达质量改进项目

本仓库用于软件测试与质量保证课程实践。被测系统以 DailyFresh Django 生鲜商城的代码快照为起点，三名成员将在清晰标注来源的基础上重新完成需求分析、测试设计、测试实现、缺陷验证和质量改进。

## 当前状态

- 基线：`baseline-v0.1`
- 当前环境：Python 3.13 + Django 5.2 LTS
- 已验证版本：Python 3.13.9、Django 5.2.17、django-tinymce 5.0.0、Pillow 12.3.0
- 数据库：本地 SQLite，数据库文件不提交到 Git

环境迁移只处理新版框架兼容问题，没有修改商城业务规则。模块一的测试用例和自动化测试不会从往届材料复制，也不会由 AI 生成。

## 本地启动

在 Windows PowerShell 中执行：

```powershell
cd "E:\project\softtest project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

浏览器打开 `http://127.0.0.1:8000/`。以后进入项目时只需激活已有虚拟环境，不要重复创建：

```powershell
cd "E:\project\softtest project"
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

也可以不激活环境，直接使用：

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

## 当前数据说明

仓库不会复制往届 SQLite 数据库，因为其中可能混有往届账号、订单和测试数据。全新数据库迁移后默认没有商品分类和商品数据，首页会显示校园鲜达欢迎页和商品待上架提示，不再因固定读取六个分类而报错。

由成员 B 维护的脱敏演示数据可通过管理命令加载。命令只写入 6 个分类和 24 个商品，不创建用户、地址、购物车或订单：

```powershell
.\.venv\Scripts\python.exe manage.py load_demo_data
```

命令可以重复执行而不会重复创建同名商品。需要重新生成这组演示商品时可使用 `--reset`；该参数只处理本命令生成的商品，并保留其他业务数据。加载完成后刷新首页即可看到商品分类和商品卡片。

人工测试需要的脱敏账号和收货地址可单独加载：

```powershell
.\.venv\Scripts\python.exe manage.py load_demo_users
```

该命令幂等创建或更新 `test01`～`test12` 共 12 个脱敏账号，密码均为 `123456`，不会导入往届账号或订单数据。

## 模块一测试资料

- [人工测试用例记录表](docs/testing/module1-manual-test-case-matrix.xlsx)：36 条覆盖编号，执行字段由三位成员亲自补写和执行。
- [缺陷证据记录](docs/testing/module1-defect-evidence.md)：D-01、D-03、D-04 的复现、修复和回归链路。
- [修复前代码片段](docs/testing/baseline-defect-snippets.txt)：从 `84aa763` 直接提取的基线证据。
- [中期检查 PPT](docs/presentation/campus-fresh-module1-midterm.pptx)：11 页、5–8 分钟汇报稿。

提交前可运行完整度检查。脚本只检查字段是否齐全，不生成测试用例，也不执行测试：

```powershell
.\.venv\Scripts\python.exe scripts/check_manual_cases.py
.\.venv\Scripts\python.exe scripts/check_manual_cases.py --strict
```

`--strict` 只有在至少 30 条用例完成成员填写并执行后才会通过。

截图或录屏路径回填到 Excel 后，可进一步检查已执行用例引用的媒体文件：

```powershell
.\.venv\Scripts\python.exe scripts/check_manual_evidence.py
.\.venv\Scripts\python.exe scripts/check_manual_evidence.py --strict
```

证据检查会确认路径位于 `docs/testing/evidence/` 内、文件确实存在且扩展名属于支持的图片或视频格式；它不能替代成员本人对截图内容和操作真实性的核对。

## 模块二测试资料（AI 辅助测试）

- [AI 生成测试用例清单](docs/testing/module2-ai-test-case-matrix.xlsx)：21 条，由 AI 依据成员 C 需求文档生成、成员 C 审核并自动化执行。
- [AI 实践过程与对照实验记录](docs/ai-records/2026-09-19-member-c-ai-testing.md)：AI 独立审查基线代码与人工测试的对照结论，AI 发现缺陷 D-AI-01（登录回跳开放重定向）、D-AI-02（支付视图空壳）的修复与回归。
- [运行方式说明](docs/testing/module2-README.md)：环境准备与一键运行命令。
- 自动化运行记录：`docs/testing/module2-automation-run-output.txt`（23 条 AI 测试 + 全量回归 101 条，均通过）。

## 业务范围

- 用户、登录和收货信息
- 商品、搜索和浏览历史
- 购物车、订单和库存

## 目录

- `apps/`：商城业务模块
- `daily_fresh_demo/`：Django 项目配置
- `templates/`：页面模板
- `static/`：静态资源
- `sql/`：原参考项目附带的数据库结构说明
- `docs/`：项目设计、需求、缺陷、报告和 AI 过程记录

## 三人协作

- 成员 A（组长）：用户、登录和地址；环境与集成
- 成员 B：商品、搜索和浏览历史；演示数据与度量
- 成员 C：购物车、订单和库存；集成执行与演示

三名成员使用各自的 GitHub 账号提交实际完成的工作。每名成员在自己的业务域中完成需求、人工测试设计、自动化实现、缺陷闭环和文档，提交信息描述真实变更。

## 后续里程碑

1. `baseline-v0.1`：清理后的待测系统基线。
2. `environment-v0.2`：Python 3.13 与 Django 5.2 环境迁移。
3. `module1-final`：完成基础测试、缺陷修复与回归。
4. 模块二：在模块一版本上开展 AI 辅助测试对照实验。

来源及导入范围见 [NOTICE.md](NOTICE.md)。

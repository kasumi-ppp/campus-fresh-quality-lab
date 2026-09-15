# 校园鲜达模块一缺陷证据记录

## 证据范围

本记录把“发现版本、复现路径、影响、修复提交、回归结果”串成一条可核对链路。缺陷基线为 `demo-v0.3`（提交 `84aa763`），修复提交为成员 C 的 `816eec0`。当前工作区在 Django 5.2 兼容修复后，使用 `manage.py test` 回归。

回归命令：

```text
\.venv\Scripts\python.exe manage.py test apps.df_cart.tests_member_c.CartAccessControlTests apps.df_order.tests_member_c.OrderAccessControlTests apps.df_order.tests_member_c.OrderAmountTests -v 2
```

执行记录见 `docs/testing/defect-regression-output.txt`：专项回归共 10 个测试，结果为 `OK`。

修复前代码片段和提取命令见 `docs/testing/baseline-defect-snippets.txt`，可直接用 Git 历史复核基线行为。

## D-01：购物车条目越权修改

| 项目 | 证据 |
| --- | --- |
| 需求编号 | C-CART-002 |
| 严重程度 | 高 |
| 发现版本 | `84aa763`（修复前） |
| 前置条件 | 用户 A、用户 B 已登录过；用户 B 有一条购物车记录 |
| 复现步骤 | 用户 A 构造用户 B 的 `cart_id`，访问购物车数量修改接口并提交新数量 |
| 修复前现象 | 服务器仅按条目编号查询，用户 B 的数量被改写 |
| 影响 | 越权写入，篡改他人购物车数据 |
| 根因 | 查询条件缺少当前会话的 `user_id` 过滤 |
| 修复 | `apps/df_cart/views.py` 的修改接口使用 `pk=cart_id, user_id=uid`，未命中返回失败 JSON |
| 修复提交 | `816eec0` |
| 回归测试 | `apps/df_cart/tests_member_c.py::CartAccessControlTests::test_edit_other_user_cart_is_rejected` |
| 当前结果 | 通过：返回失败，用户 B 的数量保持不变 |

## D-03：订单越权结算

| 项目 | 证据 |
| --- | --- |
| 需求编号 | C-ORD-001 |
| 严重程度 | 高 |
| 发现版本 | `84aa763`（修复前） |
| 前置条件 | 用户 B 的购物车存在商品；用户 A 已登录并知道该条目编号 |
| 复现步骤 | 用户 A 在订单确认或下单请求中提交用户 B 的 `cart_id` |
| 修复前现象 | 服务端按条目编号直接取购物车记录，可将他人商品带入订单 |
| 影响 | 跨用户结算，订单数据和库存归属错误 |
| 根因 | 订单确认页和下单接口没有校验购物车条目所有者 |
| 修复 | 订单确认和创建订单均按 `pk=cart_id, user_id=uid` 过滤；混入他人条目时整单失败 |
| 修复提交 | `816eec0` |
| 回归测试 | `apps/df_order/tests_member_c.py::OrderAccessControlTests::test_cannot_submit_order_with_other_user_cart`；`test_mixed_cart_ids_are_rejected_entirely` |
| 当前结果 | 通过：不生成订单、不扣库存、不删除他人购物车条目 |

## D-04：订单总额信任浏览器输入

| 项目 | 证据 |
| --- | --- |
| 需求编号 | C-ORD-005 |
| 严重程度 | 高 |
| 发现版本 | `84aa763`（修复前） |
| 前置条件 | 用户已登录并有可结算购物车商品 |
| 复现步骤 | 浏览器提交订单时，将表单 `total` 改为 `0.00`，其余字段保持有效 |
| 修复前现象 | 订单总额直接采用客户端提交值，可以低价下单 |
| 影响 | 金额完整性被破坏，存在低价支付风险 |
| 根因 | 服务端没有按商品单价、数量和配送费重新计算订单总额 |
| 修复 | `apps/df_order/views.py` 使用 `Decimal` 重新计算商品小计并加 `10.00` 元配送费，忽略浏览器 `total` |
| 修复提交 | `816eec0` |
| 回归测试 | `apps/df_order/tests_member_c.py::OrderAmountTests::test_tampered_total_from_browser_is_ignored` |
| 当前结果 | 通过：苹果 12.50 元、数量 1 的订单保存为 22.50 元，篡改值不生效 |

## 证据核对清单

- 三项缺陷均有需求编号、复现条件、影响、根因、修复提交和回归测试。
- 代码证据可核对 `apps/df_cart/views.py` 第 78–83 行、`apps/df_order/views.py` 第 109–131 行。
- 回归日志保留在 `docs/testing/defect-regression-output.txt`，可与当前提交一起检查。
- 提交前应由成员 C 在自己的账号下补充实际浏览器截图或录屏，并把路径回填到人工用例 Excel 的“证据路径”列。

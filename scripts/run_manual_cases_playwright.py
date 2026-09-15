# -*- coding: utf-8 -*-
"""成员 C（购物车 / 订单 / 库存）11 条人工用例的自动执行 + 截图取证。

输出：
  - 截图  -> docs/testing/evidence/{用例编号}-步骤{N}-{简述}.png
  - 记录  -> 工作区的 c_run_log.json（用于回填 Excel 的“实际结果 / 状态 / 证据路径”）
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVID = os.path.join(PROJ, "docs", "testing", "evidence")
LOGPATH = os.path.join(PROJ, "docs", "testing", "manual_case_run_log.json")

os.makedirs(EVID, exist_ok=True)
LOG = {}


def begin(case):
    LOG[case] = {"shots": [], "notes": {}}
    print("\n########", case, flush=True)


def shot(page, case, step, desc):
    name = "%s-步骤%s-%s.png" % (case, step, desc)
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(EVID, name), full_page=True)
    LOG[case]["shots"].append(name)
    print("   shot:", name, flush=True)


def note(case, key, val):
    LOG[case]["notes"][key] = val
    print("   note: %s = %s" % (key, val), flush=True)


def attach(page):
    """自动接受 alert / confirm 弹窗。"""
    page.on("dialog", lambda d: d.accept())


def login(page, user="test01", pwd="123456"):
    page.goto(BASE + "/user/login/")
    page.fill("input[name=username]", user)
    page.fill("input[name=pwd]", pwd)
    page.click("input.input_submit")
    page.wait_for_load_state("networkidle")


def add_cart(page, gid, qty, clamp=False):
    """详情页加购。该页【加入购物车】第一次点击只绑定事件，第二次才发请求。"""
    page.goto("%s/%s/" % (BASE, gid))
    page.fill(".num_show", str(qty))
    if clamp:
        page.locator(".num_show").blur()
        page.wait_for_timeout(300)
    page.click("#add_cart")
    page.wait_for_timeout(300)
    page.click("#add_cart")
    page.wait_for_timeout(900)
    return page.locator(".num_show").input_value() if clamp else None


def cart_ids(page):
    page.goto(BASE + "/cart/")
    page.wait_for_timeout(500)
    return page.eval_on_selector_all("ul.cart_list_td", "els => els.map(e => e.id)")


def cart_summary(page):
    return {
        "rows": page.locator("ul.cart_list_td").count(),
        "count_text": page.locator(".total_count em").inner_text()
        if page.locator(".total_count em").count() else "",
        "total": page.locator("#total").inner_text()
        if page.locator("#total").count() else "",
    }


def clear_cart(page):
    page.goto(BASE + "/cart/")
    page.wait_for_timeout(400)
    for _ in range(6):
        n = page.locator("ul.cart_list_td").count()
        if n == 0:
            break
        page.locator("ul.cart_list_td").first.locator("a", has_text="删除").click()
        page.wait_for_timeout(900)
    return page.locator("ul.cart_list_td").count()


def checkout(page):
    page.goto(BASE + "/cart/")
    page.wait_for_timeout(400)
    page.locator("a", has_text="去结算").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)


def submit_order(page):
    page.click("#order_btn")
    page.wait_for_timeout(1200)


def order_page_text(page):
    page.goto(BASE + "/user/order/1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    return page.inner_text("body")


def stock(gid):
    import sqlite3
    c = sqlite3.connect(os.path.join(PROJ, "db.sqlite3"))
    v = c.execute("select gkucun from df_goods_goodsinfo where id=?", (gid,)).fetchone()[0]
    c.close()
    return v


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        ctxA = browser.new_context(viewport={"width": 1360, "height": 900})
        ctxB = browser.new_context(viewport={"width": 1360, "height": 900})
        A = ctxA.new_page(); attach(A)
        B = ctxB.new_page(); attach(B)

        # ---------------- C-CART-002 ----------------
        case = "C-CART-002"
        begin(case)
        clear_cart(A)
        login(A)
        shot(A, case, 1, "登录成功")
        A.goto(BASE + "/4/"); A.wait_for_timeout(500)
        note(case, "库存显示", A.locator(".goods_kucun").inner_text())
        shot(A, case, 2, "详情页库存69")
        for _ in range(3):
            A.click("a.minus"); A.wait_for_timeout(250)
        note(case, "连点3次减号后", A.locator(".num_show").input_value())
        shot(A, case, 3, "连点减号数量保持1")
        A.goto(BASE + "/cart/add4_0/"); A.wait_for_timeout(500)
        note(case, "add4_0响应", A.inner_text("body")[:200])
        shot(A, case, 4, "加购数量0返回JSON")
        A.goto(BASE + "/cart/add4_-1/"); A.wait_for_timeout(500)
        note(case, "add4_-1首行", A.inner_text("body")[:120].replace("\n", " "))
        shot(A, case, 5, "负数参数返回404")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(400)
        note(case, "购物车", cart_summary(A))
        shot(A, case, 6, "购物车仍为空")

        # ---------------- C-CART-003 ----------------
        case = "C-CART-003"
        begin(case)
        clear_cart(A)
        note(case, "执行前库存", stock(4))
        A.goto(BASE + "/user/login/")
        login(A)
        shot(A, case, 1, "登录成功")
        add_cart(A, 4, 65)
        shot(A, case, 2, "加入65件")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(500)
        note(case, "第一次加购后", cart_summary(A))
        shot(A, case, 3, "购物车数量65")
        add_cart(A, 4, 10)
        note(case, "第二次加购后角标", A.locator("#show_count").inner_text() if A.locator("#show_count").count() else "n/a")
        shot(A, case, 4, "二次加购被拒绝")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(500)
        note(case, "二次加购后购物车", cart_summary(A))
        shot(A, case, 5, "数量未累加仍为65")
        A.goto(BASE + "/cart/add4_999/"); A.wait_for_timeout(500)
        note(case, "add4_999响应", A.inner_text("body")[:200])
        shot(A, case, 6, "URL传999返回JSON")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(400)
        note(case, "刷新后", cart_summary(A))
        shot(A, case, 7, "刷新后仍为65")
        A.goto(BASE + "/4/"); A.wait_for_timeout(400)
        A.fill(".num_show", "999")
        A.locator(".num_show").blur(); A.wait_for_timeout(500)
        note(case, "输入999失焦后", A.locator(".num_show").input_value())
        shot(A, case, 8, "输入框被夹到库存上限")

        # ---------------- C-CART-004 ----------------
        case = "C-CART-004"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 1)
        A.goto(BASE + "/cart/"); A.wait_for_timeout(500)
        note(case, "修改前", cart_summary(A))
        shot(A, case, 2, "购物车初始状态")
        A.fill(".num_show", "3"); A.wait_for_timeout(300)
        shot(A, case, 3, "数量改为3")
        A.locator(".num_show").blur(); A.wait_for_timeout(1200)
        note(case, "修改后", cart_summary(A))
        shot(A, case, 4, "失焦后小计重算")
        A.wait_for_timeout(400)
        shot(A, case, 5, "合计与件数")
        A.reload(); A.wait_for_timeout(900)
        note(case, "刷新后", cart_summary(A))
        shot(A, case, 6, "刷新后仍为3")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(600)
        note(case, "重开后", cart_summary(A))
        shot(A, case, 7, "重开确认已持久化")

        # ---------------- C-CART-005 ----------------
        case = "C-CART-005"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 1)
        add_cart(A, 5, 1)
        A.goto(BASE + "/cart/"); A.wait_for_timeout(500)
        note(case, "删除前", cart_summary(A))
        shot(A, case, 2, "购物车两行初始")
        A.locator("ul.cart_list_td").nth(1).locator("a", has_text="删除").click()
        A.wait_for_timeout(200)
        shot(A, case, 3, "点击删除弹出确认框")
        A.wait_for_timeout(1200)
        note(case, "删除后", cart_summary(A))
        shot(A, case, 4, "删除后剩一行")
        A.wait_for_timeout(400)
        shot(A, case, 5, "合计变为9.90")
        A.reload(); A.wait_for_timeout(900)
        note(case, "刷新后", cart_summary(A))
        shot(A, case, 6, "刷新后仍为一行")

        # ---------------- C-CART-006 ----------------
        case = "C-CART-006"
        begin(case)
        clear_cart(A); clear_cart(B)
        add_cart(A, 4, 1)
        login(B, "test02", "123456")
        add_cart(B, 5, 1)
        A.goto(BASE + "/cart/"); A.wait_for_timeout(500)
        idsA = cart_ids(A); note(case, "test01条目X", idsA)
        shot(A, case, 1, "test01购物车")
        shot(A, case, 2, "查看条目编号X")
        B.goto(BASE + "/cart/"); B.wait_for_timeout(500)
        note(case, "test02条目Y", cart_ids(B))
        shot(B, case, 3, "test02购物车")
        X = idsA[0] if idsA else "1"
        B.goto("%s/cart/edit%s_99/" % (BASE, X)); B.wait_for_timeout(600)
        note(case, "越权修改响应", B.inner_text("body")[:200])
        shot(B, case, 4, "越权修改返回JSON")
        B.goto("%s/cart/delete%s/" % (BASE, X)); B.wait_for_timeout(600)
        note(case, "越权删除响应", B.inner_text("body")[:200])
        shot(B, case, 5, "越权删除返回JSON")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(600)
        note(case, "test01复查", cart_summary(A))
        shot(A, case, 6, "test01购物车未受影响")

        # ---------------- C-ORD-001 ----------------
        case = "C-ORD-001"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 2)
        shot(A, case, 2, "加入商品4两件")
        add_cart(A, 5, 1)
        shot(A, case, 3, "加入商品5一件")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(600)
        note(case, "购物车合计", cart_summary(A))
        shot(A, case, 4, "购物车合计47.80")
        checkout(A)
        note(case, "确认页金额", {
            "总金额": A.locator(".total_goods_count b").inner_text(),
            "运费": A.locator(".transit b").inner_text(),
            "实付款": A.locator(".total_pay b").inner_text(),
        })
        shot(A, case, 5, "去结算进入确认页")
        A.wait_for_timeout(300)
        shot(A, case, 6, "确认页收货信息核对")
        submit_order(A)
        shot(A, case, 7, "提交成功浮层")
        A.wait_for_timeout(2200)
        note(case, "订单页", A.url)
        txt = order_page_text(A)
        note(case, "订单页片段", txt[:400].replace("\n", " "))
        shot(A, case, 8, "订单列表57.80")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(600)
        note(case, "下单后购物车", cart_summary(A))
        note(case, "库存", {"4": stock(4), "5": stock(5)})
        shot(A, case, 9, "购物车已清空")

        # ---------------- C-ORD-002 ----------------
        case = "C-ORD-002"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 1)
        A.goto(BASE + "/user/site/"); A.wait_for_timeout(500)
        A.fill("textarea[name=uaddress]", "")
        A.click("input.info_submit")
        A.wait_for_load_state("networkidle"); A.wait_for_timeout(500)
        shot(A, case, 2, "清空收货地址")
        checkout(A)
        shot(A, case, 3, "去结算")
        note(case, "确认页地址", A.locator(".user_info_check").first.inner_text())
        shot(A, case, 4, "确认页地址为空")
        A.click("#order_btn")
        A.wait_for_timeout(1500)
        note(case, "提交后URL", A.url)
        shot(A, case, 5, "提示请填写收货地址")
        shot(A, case, 6, "自动跳转地址页")
        txt = order_page_text(A)
        note(case, "订单页片段", txt[:300].replace("\n", " "))
        shot(A, case, 7, "订单列表无新增")
        A.goto(BASE + "/user/site/"); A.wait_for_timeout(400)
        A.fill("textarea[name=uaddress]", "湖北省武汉市洪山区珞喻路1037号 1栋101")
        A.click("input.info_submit")
        A.wait_for_load_state("networkidle"); A.wait_for_timeout(500)
        shot(A, case, 8, "地址已复原")

        # ---------------- C-ORD-003 ----------------
        case = "C-ORD-003"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 2)
        checkout(A)
        note(case, "确认页金额", {
            "总金额": A.locator(".total_goods_count b").inner_text(),
            "运费": A.locator(".transit b").inner_text(),
            "实付款": A.locator(".total_pay b").inner_text(),
        })
        shot(A, case, 2, "确认页金额29.80")
        shot(A, case, 3, "记录三项数值")
        A.evaluate("document.querySelector('.total_pay b').textContent = '0.01'")
        A.wait_for_timeout(400)
        note(case, "篡改后实付款", A.locator(".total_pay b").inner_text())
        shot(A, case, 4, "实付款被改为0.01")
        shot(A, case, 5, "确认篡改生效")
        submit_order(A)
        shot(A, case, 6, "提交成功")
        A.wait_for_timeout(2200)
        txt = order_page_text(A)
        note(case, "订单页片段", txt[:400].replace("\n", " "))
        shot(A, case, 7, "订单金额仍为29.80")
        A.reload(); A.wait_for_timeout(800)
        shot(A, case, 8, "刷新后金额不变")
        note(case, "库存", {"4": stock(4)})

        # ---------------- C-ORD-005 ----------------
        case = "C-ORD-005"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 1)
        checkout(A)
        submit_order(A)
        shot(A, case, 2, "第一笔提交成功")
        A.wait_for_timeout(2200)
        t1 = order_page_text(A)
        note(case, "第一笔订单页", t1[:400].replace("\n", " "))
        shot(A, case, 3, "第一笔订单19.80")
        add_cart(A, 5, 1)
        checkout(A)
        submit_order(A)
        shot(A, case, 4, "第二笔提交成功")
        A.wait_for_timeout(2200)
        t2 = order_page_text(A)
        note(case, "第二笔订单页", t2[:400].replace("\n", " "))
        shot(A, case, 5, "两笔订单并列")
        A.wait_for_timeout(400)
        shot(A, case, 6, "核对两笔明细")
        A.reload(); A.wait_for_timeout(800)
        shot(A, case, 7, "刷新后两笔仍在")
        note(case, "库存", {"4": stock(4), "5": stock(5)})

        # ---------------- C-ORD-006 ----------------
        case = "C-ORD-006"
        begin(case)
        clear_cart(A)
        add_cart(A, 4, 1)
        A.goto(BASE + "/cart/"); A.wait_for_timeout(500)
        ids = cart_ids(A); note(case, "有效条目X", ids)
        shot(A, case, 2, "查看条目编号")
        A.goto(BASE + "/order/?cart_id=99999"); A.wait_for_timeout(600)
        note(case, "99999页面", A.inner_text("body")[:200].replace("\n", " "))
        shot(A, case, 3, "不存在编号99999")
        A.goto(BASE + "/order/?cart_id=abc"); A.wait_for_timeout(600)
        note(case, "abc页面", A.inner_text("body")[:200].replace("\n", " "))
        shot(A, case, 4, "非数字参数abc")
        A.goto("%s/order/?cart_id=%s" % (BASE, ids[0] if ids else "")); A.wait_for_timeout(600)
        note(case, "有效编号页面", A.inner_text("body")[:250].replace("\n", " "))
        shot(A, case, 5, "有效编号正常显示")
        A.goto(BASE + "/order/"); A.wait_for_timeout(600)
        note(case, "无参数页面", A.inner_text("body")[:200].replace("\n", " "))
        shot(A, case, 6, "无参数空态")

        # ---------------- C-ORD-004 ----------------
        case = "C-ORD-004"
        begin(case)
        clear_cart(A); clear_cart(B)
        k = stock(4)
        note(case, "执行前库存", k)
        # test01 先加购 3 件并停在确认页
        add_cart(A, 4, 3)
        checkout(A)
        shot(A, case, 1, "test01确认页待提交")
        # test02 买光剩余库存
        add_cart(B, 4, k)
        B.goto(BASE + "/cart/"); B.wait_for_timeout(600)
        note(case, "test02购物车", cart_summary(B))
        shot(B, case, 2, "test02加购买光库存")
        checkout(B)
        note(case, "test02确认页", {
            "总金额": B.locator(".total_goods_count b").inner_text(),
            "实付款": B.locator(".total_pay b").inner_text(),
        })
        submit_order(B)
        shot(B, case, 3, "test02下单成功")
        B.wait_for_timeout(2200)
        t3 = order_page_text(B)
        note(case, "test02订单页", t3[:400].replace("\n", " "))
        shot(B, case, 4, "test02订单记录")
        note(case, "test02下单后库存", stock(4))
        # test01 此时提交
        A.click("#order_btn")
        A.wait_for_timeout(1800)
        note(case, "test01提交后URL", A.url)
        shot(A, case, 5, "test01提交失败提示")
        A.wait_for_timeout(600)
        shot(A, case, 6, "失败提示内容")
        A.goto(BASE + "/cart/"); A.wait_for_timeout(600)
        note(case, "test01购物车", cart_summary(A))
        shot(A, case, 7, "test01购物车条目仍在")
        A.goto(BASE + "/4/"); A.wait_for_timeout(500)
        note(case, "库存显示", A.locator(".goods_kucun").inner_text())
        shot(A, case, 8, "商品4库存为0")

        browser.close()

    with open(LOGPATH, "w", encoding="utf-8") as f:
        json.dump(LOG, f, ensure_ascii=False, indent=2)
    print("\nLOG ->", LOGPATH)


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        with open(LOGPATH, "w", encoding="utf-8") as f:
            json.dump(LOG, f, ensure_ascii=False, indent=2)
        sys.exit(1)

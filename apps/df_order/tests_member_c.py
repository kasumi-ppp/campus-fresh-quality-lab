# 成员 C：订单、库存与集成执行模块独立测试
#
# 覆盖需求编号：C-CART-009 / C-ORD-001 / C-ORD-003 / C-ORD-004 / C-ORD-005 /
# C-ORD-006 / C-ORD-007 / C-ORD-008 / C-ORD-009 / C-ORD-010 /
# C-INV-002 / C-INV-003 / C-INV-004 / C-INV-006
#
# 本文件由成员 C 独立编写，针对订单金额可信性、跨用户数据隔离和库存事务一致性。
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from df_cart.models import CartInfo
from df_goods.models import GoodsInfo, TypeInfo
from df_order.models import OrderDetailInfo, OrderInfo
from df_user.models import UserInfo


class OrderTestBase(TestCase):
    """公共测试数据：两个已填写收货地址的用户，共享两个商品。"""

    def setUp(self):
        self.user = UserInfo.objects.create(
            uname="buyer", upwd="pwd", uemail="buyer@example.com",
            ushou="张三", uaddress="北京市海淀区中关村大街1号", uphone="13800000000")
        self.other = UserInfo.objects.create(
            uname="other", upwd="pwd", uemail="other@example.com",
            ushou="李四", uaddress="北京市朝阳区建国路2号", uphone="13900000000")

        self.category = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        self.apple = GoodsInfo.objects.create(
            gtitle="苹果", gprice=Decimal('12.50'), gunit="500g", gclick=0,
            gjianjie="新鲜苹果", gkucun=100, gcontent="优质苹果", gtype=self.category)
        self.banana = GoodsInfo.objects.create(
            gtitle="香蕉", gprice=Decimal('8.00'), gunit="500g", gclick=0,
            gjianjie="新鲜香蕉", gkucun=50, gcontent="优质香蕉", gtype=self.category)

    def login(self, user=None):
        session = self.client.session
        session["user_id"] = (user or self.user).id
        session.save()

    def submit(self, carts, total="0.01"):
        """提交订单。total 故意传一个远小于应收金额的值，用于验证后端不信任浏览器金额。"""
        ids = ",".join(str(cart.id) for cart in carts)
        return self.client.post(reverse("df_order:push"),
                                {"cart_ids": ids, "total": total})


class OrderAmountTests(OrderTestBase):
    """C-ORD-004 / C-ORD-005 / C-ORD-007：金额由服务器重新计算并保存快照。"""

    def test_total_is_recalculated_and_includes_delivery_fee(self):
        self.login()
        cart1 = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)
        cart2 = CartInfo.objects.create(user=self.user, goods=self.banana, count=1)

        resp = self.submit([cart1, cart2])

        self.assertEqual(resp.json()["ok"], 1)
        order = OrderInfo.objects.get(user=self.user)
        # 商品小计 25.00 + 8.00 = 33.00，加配送费 10.00
        self.assertEqual(order.ototal, Decimal('43.00'))

    def test_tampered_total_from_browser_is_ignored(self):
        """浏览器提交的总额不影响订单金额。"""
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)

        resp = self.submit([cart], total="0.00")

        self.assertEqual(resp.json()["ok"], 1)
        order = OrderInfo.objects.get(user=self.user)
        self.assertEqual(order.ototal, Decimal('22.50'))

    def test_order_detail_keeps_price_snapshot_after_price_change(self):
        """商品调价后历史订单明细和总额保持不变（C-ORD-007）。"""
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)
        self.submit([cart])

        order = OrderInfo.objects.get(user=self.user)
        detail = OrderDetailInfo.objects.get(order=order)
        self.assertEqual(detail.price, Decimal('12.50'))

        self.apple.gprice = Decimal('99.00')
        self.apple.save()

        detail.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(detail.price, Decimal('12.50'))
        self.assertEqual(order.ototal, Decimal('35.00'))


class OrderAccessControlTests(OrderTestBase):
    """C-ORD-001：只能选择并结算属于当前登录用户的购物车条目。"""

    def test_cannot_submit_order_with_other_user_cart(self):
        theirs = CartInfo.objects.create(user=self.other, goods=self.apple, count=1)
        self.login()

        resp = self.submit([theirs])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.filter(user=self.user).count(), 0)
        theirs.refresh_from_db()
        self.assertEqual(theirs.count, 1)

    def test_order_page_hides_other_user_cart(self):
        theirs = CartInfo.objects.create(user=self.other, goods=self.apple, count=1)
        self.login()

        resp = self.client.get(reverse("df_order:order"), {"cart_id": [theirs.id]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["carts"]), 0)
        self.assertTrue(resp.context["empty_cart"])

    def test_mixed_cart_ids_are_rejected_entirely(self):
        """提交中混入他人条目时整单失败，自己的条目和库存都不发生变化（C-INV-003）。"""
        mine = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        theirs = CartInfo.objects.create(user=self.other, goods=self.banana, count=2)
        self.login()

        resp = self.submit([mine, theirs])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.assertTrue(CartInfo.objects.filter(id=mine.id).exists())
        theirs.refresh_from_db()
        self.assertEqual(theirs.count, 2)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 100)


class OrderAddressTests(OrderTestBase):
    """C-ORD-003：创建订单前必须存在有效收货地址，订单保存地址快照。"""

    def test_order_rejected_without_address(self):
        self.user.uaddress = ""
        self.user.save()
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)

        resp = self.submit([cart])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertIn("地址", resp.json()["msg"])
        self.assertEqual(OrderInfo.objects.filter(user=self.user).count(), 0)
        # 失败后购物车保留，便于补全地址后重新结算（C-INV-006）
        self.assertTrue(CartInfo.objects.filter(id=cart.id).exists())

    def test_order_saves_address_snapshot(self):
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)

        self.submit([cart])

        order = OrderInfo.objects.get(user=self.user)
        self.assertEqual(order.oaddress, "北京市海淀区中关村大街1号")


class OrderStockTests(OrderTestBase):
    """C-INV-002 / C-INV-003 / C-INV-004 / C-INV-006：库存与事务一致性。"""

    def test_stock_is_reduced_after_successful_order(self):
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=3)

        self.submit([cart])

        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 97)

    def test_insufficient_stock_rolls_back_the_whole_order(self):
        """任一商品库存不足时不得留下半张订单、部分明细或部分库存扣减（C-INV-003）。"""
        self.login()
        ok_cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        too_many = CartInfo.objects.create(user=self.user, goods=self.banana, count=999)

        resp = self.submit([ok_cart, too_many])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertIn("库存不足", resp.json()["msg"])
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.assertEqual(OrderDetailInfo.objects.count(), 0)
        self.apple.refresh_from_db()
        self.banana.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 100)
        self.assertEqual(self.banana.gkucun, 50)
        # 失败后原有购物车条目继续保留（C-INV-006）
        self.assertTrue(CartInfo.objects.filter(id=ok_cart.id).exists())
        self.assertTrue(CartInfo.objects.filter(id=too_many.id).exists())

    def test_oversell_is_prevented_between_two_buyers(self):
        """C-INV-004：售出数量不超过可售库存，库存不会变成负数。

        这里以顺序提交验证“不超卖”这一可观察结果；真实并发场景在集成执行阶段验证。
        """
        self.apple.gkucun = 5
        self.apple.save()
        cart_a = CartInfo.objects.create(user=self.user, goods=self.apple, count=3)
        cart_b = CartInfo.objects.create(user=self.other, goods=self.apple, count=3)

        self.login(self.user)
        first = self.submit([cart_a])
        self.login(self.other)
        second = self.submit([cart_b])

        self.assertEqual(first.json()["ok"], 1)
        self.assertEqual(second.json()["ok"], 0)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 2)
        self.assertEqual(OrderInfo.objects.count(), 1)

    def test_out_of_stock_goods_cannot_be_ordered(self):
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        self.apple.gkucun = 0
        self.apple.save()

        resp = self.submit([cart])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 0)


class OrderLifecycleTests(OrderTestBase):
    """C-CART-009 / C-ORD-006 / C-ORD-008 / C-ORD-009 / C-ORD-010。"""

    def test_order_ids_are_unique_across_consecutive_orders(self):
        """同一用户连续下单得到不同订单编号（C-ORD-006）。"""
        self.login()
        first_cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        self.submit([first_cart])
        second_cart = CartInfo.objects.create(user=self.user, goods=self.banana, count=1)
        self.submit([second_cart])

        orders = list(OrderInfo.objects.filter(user=self.user))
        self.assertEqual(len(orders), 2)
        self.assertEqual(len({order.oid for order in orders}), 2)
        for order in orders:
            self.assertTrue(order.oid)

    def test_only_selected_carts_are_removed(self):
        """只删除本次已结算的购物车条目，未选条目继续保留（C-ORD-008）。"""
        self.login()
        selected = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)
        kept = CartInfo.objects.create(user=self.user, goods=self.banana, count=1)

        self.submit([selected])

        self.assertFalse(CartInfo.objects.filter(id=selected.id).exists())
        self.assertTrue(CartInfo.objects.filter(id=kept.id).exists())

    def test_resubmitting_same_carts_creates_no_second_order(self):
        """同一批条目重复提交不会生成第二张订单或重复扣减库存（C-ORD-009）。"""
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)

        first = self.submit([cart])
        second = self.submit([cart])

        self.assertEqual(first.json()["ok"], 1)
        self.assertEqual(second.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 1)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 98)

    def test_empty_cart_cannot_be_submitted(self):
        self.login()

        resp = self.client.post(reverse("df_order:push"), {"cart_ids": ""})

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 0)

    def test_invalid_cart_id_returns_readable_error(self):
        """非法条目编号返回可理解的失败信息，不向普通用户暴露调试堆栈（C-ORD-010）。"""
        self.login()

        resp = self.client.post(reverse("df_order:push"), {"cart_ids": "abc"})

        self.assertEqual(resp.json()["ok"], 0)
        self.assertTrue(resp.json()["msg"])
        self.assertNotIn("Traceback", resp.content.decode())

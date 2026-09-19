# 模块二 AI 生成测试：订单与库存模块
#
# 本文件由 AI 工具（ZCode/GLM）依据需求文档生成，成员 C 审核修改后执行。
# 属于课程模块二「AI 测」方案交付物，与模块一人工测试（tests_member_c.py）相互独立。
#
# 覆盖用例：C-AI-ORD-001 ~ C-AI-ORD-007、C-AI-INV-001 ~ C-AI-INV-005
# 运行方式：python manage.py test apps.df_order.tests_ai_generated
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from df_cart.models import CartInfo
from df_goods.models import GoodsInfo, TypeInfo
from df_order.models import OrderDetailInfo, OrderInfo
from df_user.models import UserInfo


class AiOrderTestBase(TestCase):
    """AI 生成用例的公共数据：两个已填地址的用户与两个商品。"""

    def setUp(self):
        self.user = UserInfo.objects.create(
            uname="ai_buyer", upwd="pwd", uemail="ai_buyer@example.com",
            ushou="王五", uaddress="北京市海淀区学院路37号", uphone="13700000000")
        self.other = UserInfo.objects.create(
            uname="ai_other", upwd="pwd", uemail="ai_other@example.com",
            ushou="赵六", uaddress="上海市杨浦区五角场", uphone="13600000000")
        self.category = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        self.apple = GoodsInfo.objects.create(
            gtitle="AI测试苹果", gprice=Decimal('8.80'), gunit="500g", gclick=0,
            gjianjie="AI 用例测试苹果", gkucun=100, gcontent="测试", gtype=self.category)
        self.banana = GoodsInfo.objects.create(
            gtitle="AI测试香蕉", gprice=Decimal('8.00'), gunit="500g", gclick=0,
            gjianjie="AI 用例测试香蕉", gkucun=50, gcontent="测试", gtype=self.category)

    def login(self, user=None):
        session = self.client.session
        session["user_id"] = (user or self.user).id
        session.save()

    def submit(self, carts, total="0.01"):
        """提交订单。total 默认传远小于应收的值，用于持续验证后端不信任浏览器金额。"""
        ids = ",".join(str(cart.id) for cart in carts)
        return self.client.post(reverse("df_order:push"),
                                {"cart_ids": ids, "total": total})


class AiOrderAmountTests(AiOrderTestBase):
    """C-AI-ORD-001：金额精度。"""

    def test_decimal_amount_no_float_drift(self):
        """C-AI-ORD-001：小数单价乘数量后总额必须精确。

        单价 8.80 × 3 = 26.40，加运费 10.00 = 36.40。
        二进制浮点下 8.80×3 会产生精度漂移，预期服务器用十进制计算得到精确值。
        """
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=3)

        resp = self.submit([cart])

        self.assertEqual(resp.json()["ok"], 1)
        order = OrderInfo.objects.get(user=self.user)
        self.assertEqual(order.ototal, Decimal('36.40'))


class AiOrderLifecycleTests(AiOrderTestBase):
    """C-AI-ORD-002 ~ C-AI-ORD-007：订单生命周期场景。"""

    def test_consecutive_orders_have_unique_nonempty_ids(self):
        """C-AI-ORD-002：同一用户连续下两单。

        预期：两张订单编号都非空且互不相同（C-ORD-006）。
        """
        self.login()
        cart1 = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        self.submit([cart1])
        cart2 = CartInfo.objects.create(user=self.user, goods=self.banana, count=1)
        self.submit([cart2])

        orders = list(OrderInfo.objects.filter(user=self.user))
        self.assertEqual(len(orders), 2)
        ids = {order.oid for order in orders}
        self.assertEqual(len(ids), 2)
        for oid in ids:
            self.assertTrue(oid)

    def test_resubmit_of_settled_cart_creates_no_second_order(self):
        """C-AI-ORD-003：同一条目重复提交。

        预期：第二次提交失败；订单只有 1 张；库存只扣减一次（C-ORD-009）。
        """
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)

        first = self.submit([cart])
        second = self.submit([cart])

        self.assertEqual(first.json()["ok"], 1)
        self.assertEqual(second.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 1)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 98)

    def test_malformed_cart_ids_return_readable_error(self):
        """C-AI-ORD-004：cart_ids 为字母、纯逗号、空白等无效输入。

        预期：返回 ok=0 与中文提示，响应不含 Traceback（C-ORD-010）。
        """
        self.login()
        for bad_value in ("abc", ",", " , ,", "   "):
            resp = self.client.post(reverse("df_order:push"), {"cart_ids": bad_value})
            data = resp.json()
            self.assertEqual(data["ok"], 0, msg="输入 %r 应被拒绝" % bad_value)
            self.assertTrue(data["msg"], msg="输入 %r 应给出提示" % bad_value)
            self.assertNotIn("Traceback", resp.content.decode())
        self.assertEqual(OrderInfo.objects.count(), 0)

    def test_price_change_does_not_touch_historical_order(self):
        """C-AI-ORD-005：下单后商品调价。

        预期：历史订单明细单价与订单总额保持下单时的快照（C-ORD-007）。
        """
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)
        self.submit([cart])

        self.apple.gprice = Decimal('99.99')
        self.apple.save()

        order = OrderInfo.objects.get(user=self.user)
        detail = OrderDetailInfo.objects.get(order=order)
        self.assertEqual(detail.price, Decimal('8.80'))
        self.assertEqual(order.ototal, Decimal('27.60'))

    def test_order_without_address_is_rejected_and_cart_kept(self):
        """C-AI-ORD-006：地址为空时下单。

        预期：失败并提示与地址相关；购物车条目保留；不产生订单（C-ORD-003）。
        """
        self.user.uaddress = ""
        self.user.save()
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)

        resp = self.submit([cart])

        data = resp.json()
        self.assertEqual(data["ok"], 0)
        self.assertIn("地址", data["msg"])
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.assertTrue(CartInfo.objects.filter(id=cart.id).exists())

    def test_mixed_owner_cart_ids_rejected_as_a_whole(self):
        """C-AI-ORD-007：提交列表混入他人条目。

        预期：整单拒绝；自己的条目与库存保持不变（C-ORD-001 / C-INV-003）。
        """
        mine = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)
        theirs = CartInfo.objects.create(user=self.other, goods=self.banana, count=1)
        self.login()

        resp = self.submit([mine, theirs])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 0)
        mine.refresh_from_db()
        self.assertEqual(mine.count, 2)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 100)


class AiPayTests(AiOrderTestBase):
    """C-AI-ORD-008 / C-AI-ORD-009：演示支付状态流转（AI 发现缺陷 AI-16 的回归）。

    缺陷背景：支付视图原为空壳且无路由，访问返回 500，
    订单支付状态（oIsPay）永远无法流转。AI 定位后补齐实现。
    """

    def make_paid_order(self):
        """造一张已成功创建的未支付订单，返回订单对象。"""
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        resp = self.submit([cart])
        assert resp.json()["ok"] == 1
        return OrderInfo.objects.get(user=self.user)

    def test_pay_own_order_flips_status_exactly_once(self):
        """C-AI-ORD-008：本人订单演示支付成功且状态只流转一次。

        预期：支付返回 ok=1；数据库 oIsPay 变为 True；
        重复支付被拒绝并提示（C-ORD-012：不得声称已完成真实支付）。
        """
        order = self.make_paid_order()
        self.assertFalse(order.oIsPay)

        first = self.client.get(reverse("df_order:pay", args=[order.oid]))
        self.assertEqual(first.json()["ok"], 1)
        self.assertIn("演示", first.json()["msg"])

        order.refresh_from_db()
        self.assertTrue(order.oIsPay)

        second = self.client.get(reverse("df_order:pay", args=[order.oid]))
        self.assertEqual(second.json()["ok"], 0)
        self.assertIn("已支付", second.json()["msg"])

    def test_pay_other_users_order_is_rejected(self):
        """C-AI-ORD-009：支付他人订单必须被拒绝（所有者校验）。

        预期：返回 ok=0；他人订单的支付状态保持未支付。
        """
        # 以 ai_other 身份下单，得到一张属于他人的订单
        self.login(self.other)
        cart = CartInfo.objects.create(user=self.other, goods=self.apple, count=1)
        self.client.post(reverse("df_order:push"),
                         {"cart_ids": str(cart.id), "total": "0.01"})
        theirs = OrderInfo.objects.get(user=self.other)

        # 换回 ai_buyer 身份尝试支付他人订单
        self.login(self.user)
        resp = self.client.get(reverse("df_order:pay", args=[theirs.oid]))

        self.assertEqual(resp.json()["ok"], 0)
        theirs.refresh_from_db()
        self.assertFalse(theirs.oIsPay)


class AiInventoryTests(AiOrderTestBase):
    """C-AI-INV-001 ~ C-AI-INV-005：库存一致性与边界。"""

    def test_stock_exactly_reaches_zero_not_negative(self):
        """C-AI-INV-001：库存恰好等于购买数量（边界内侧）。

        预期：下单成功，库存归 0，不为负（C-INV-002）。
        """
        self.apple.gkucun = 3
        self.apple.save()
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=3)

        resp = self.submit([cart])

        self.assertEqual(resp.json()["ok"], 1)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 0)

    def test_partial_failure_rolls_back_entire_order(self):
        """C-AI-INV-002：两件商品一件够买一件不够买。

        预期：整单回滚——无订单无明细，够买的那件库存不变，
        全部购物车条目保留（C-INV-003 / C-INV-006）。
        """
        self.banana.gkucun = 1
        self.banana.save()
        self.login()
        ok_cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)
        bad_cart = CartInfo.objects.create(user=self.user, goods=self.banana, count=2)

        resp = self.submit([ok_cart, bad_cart])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.assertEqual(OrderDetailInfo.objects.count(), 0)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 100)
        self.assertTrue(CartInfo.objects.filter(id=ok_cart.id).exists())
        self.assertTrue(CartInfo.objects.filter(id=bad_cart.id).exists())

    def test_two_buyers_cannot_exceed_stock(self):
        """C-AI-INV-003：两位买家争购低库存商品。

        库存 5，买家 A 买 3、买家 B 买 3。预期：A 成功 B 失败，
        最终售出 3、库存 2，售出总数不超库存（C-INV-004）。
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

    def test_second_order_validates_against_deducted_stock(self):
        """C-AI-INV-004：下单成功后再次购买同一商品。

        预期：库存校验基于扣减后的新库存，超量部分被拒绝（C-INV-001）。
        """
        self.apple.gkucun = 4
        self.apple.save()
        self.login()
        first_cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=3)
        self.submit([first_cart])

        second_cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=2)
        resp = self.submit([second_cart])

        self.assertEqual(resp.json()["ok"], 0)
        self.apple.refresh_from_db()
        self.assertEqual(self.apple.gkucun, 1)
        self.assertTrue(CartInfo.objects.filter(id=second_cart.id).exists())

    def test_order_rejected_when_category_deleted(self):
        """C-AI-INV-005：商品所属分类被逻辑删除后下单。

        预期：下单被拒绝，不产生订单（C-INV-001，商品有效性包含分类有效）。
        """
        self.category.isDelete = True
        self.category.save()
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.apple, count=1)

        resp = self.submit([cart])

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.assertTrue(CartInfo.objects.filter(id=cart.id).exists())

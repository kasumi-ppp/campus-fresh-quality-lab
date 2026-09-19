# 模块二 AI 生成测试：购物车模块
#
# 本文件由 AI 工具（ZCode/GLM）依据需求文档生成，成员 C 审核修改后执行。
# 属于课程模块二「AI 测」方案交付物，与模块一人工测试（tests_member_c.py）相互独立。
#
# 覆盖用例：C-AI-CART-001 ~ C-AI-CART-006
# 运行方式：python manage.py test apps.df_cart.tests_ai_generated
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from df_cart.models import CartInfo
from df_goods.models import GoodsInfo, TypeInfo
from df_user.models import UserInfo


class AiCartTestBase(TestCase):
    """AI 生成用例的公共数据：一个用户、一个库存为 10 的商品。"""

    def setUp(self):
        self.user = UserInfo.objects.create(
            uname="ai_user", upwd="pwd", uemail="ai_user@example.com")
        self.category = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        self.goods = GoodsInfo.objects.create(
            gtitle="测试苹果", gprice=Decimal('12.50'), gunit="500g", gclick=0,
            gjianjie="AI 用例测试商品", gkucun=10, gcontent="测试", gtype=self.category)

    def login(self, user=None):
        session = self.client.session
        session["user_id"] = (user or self.user).id
        session.save()

    def get_ajax(self, url):
        """带 AJAX 头请求，命中接口的 JSON 分支。"""
        return self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")


class AiCartInvalidInputTests(AiCartTestBase):
    """C-AI-CART-001 / C-AI-CART-003：URL 层与编号层的无效等价类。"""

    def test_url_invalid_count_format_returns_404_without_dirty_data(self):
        """C-AI-CART-001：URL 中数量为字母或小数属于无效等价类。

        预期：路由不匹配返回 404，服务器不产生任何购物车记录，
        也不返回 500 错误页（C-CART-010 要求不向用户展示调试堆栈）。
        """
        self.login()
        for bad_count in ("abc", "2.5", "-1"):
            resp = self.client.get("/cart/add%d_%s/" % (self.goods.id, bad_count))
            self.assertEqual(resp.status_code, 404, msg="数量 %r 应被路由拒绝" % bad_count)
        self.assertEqual(CartInfo.objects.filter(user=self.user).count(), 0)

    def test_add_extreme_nonexistent_goods_id(self):
        """C-AI-CART-003：极大商品编号（远超正常主键范围）加购。

        预期：返回 JSON 失败信息且包含“商品不存在”，响应不含 Traceback。
        """
        self.login()
        resp = self.get_ajax(reverse("df_cart:add", args=[99999999, 1]))
        data = resp.json()
        self.assertEqual(data["ok"], 0)
        self.assertIn("商品不存在", data["msg"])
        self.assertNotIn("Traceback", resp.content.decode())


class AiCartBoundaryTests(AiCartTestBase):
    """C-AI-CART-002 / C-AI-CART-005：库存边界两侧。"""

    def test_add_count_exactly_equal_to_stock_succeeds(self):
        """C-AI-CART-002：数量恰好等于库存（边界内侧）。

        预期：加购成功，条目数量 = 库存 = 10。
        """
        self.login()
        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 10]))
        self.assertEqual(resp.status_code, 302)
        cart = CartInfo.objects.get(user=self.user, goods=self.goods)
        self.assertEqual(cart.count, 10)

    def test_edit_above_stock_rejected_and_keeps_saved_value(self):
        """C-AI-CART-005：修改数量为库存 + 1（边界外侧）。

        预期：拒绝修改，响应返回服务器保存的数量，数据库数值不变。
        """
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.goods, count=3)
        resp = self.get_ajax(reverse("df_cart:edit", args=[cart.id, 11]))
        data = resp.json()
        self.assertEqual(data["ok"], 0)
        self.assertEqual(data["count"], 3)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 3)


class AiCartScenarioTests(AiCartTestBase):
    """C-AI-CART-004 / C-AI-CART-006：业务场景与未登录访问。"""

    def test_readd_after_delete_starts_fresh_count(self):
        """C-AI-CART-004：删除条目后重新加购同一商品。

        预期：新条目数量等于本次加购数量，而不是复活删除前的旧数量。
        """
        self.login()
        cart = CartInfo.objects.create(user=self.user, goods=self.goods, count=5)
        self.get_ajax(reverse("df_cart:delete", args=[cart.id]))
        self.assertFalse(CartInfo.objects.filter(id=cart.id).exists())

        self.client.get(reverse("df_cart:add", args=[self.goods.id, 2]))
        cart = CartInfo.objects.get(user=self.user, goods=self.goods)
        self.assertEqual(cart.count, 2)

    def test_anonymous_edit_and_delete_redirect_to_login(self):
        """C-AI-CART-006：未登录直接调用修改/删除接口。

        预期：重定向到登录页（302），购物车数据不受影响。
        """
        cart = CartInfo.objects.create(user=self.user, goods=self.goods, count=4)
        edit_resp = self.client.get(reverse("df_cart:edit", args=[cart.id, 8]))
        delete_resp = self.client.get(reverse("df_cart:delete", args=[cart.id]))

        self.assertEqual(edit_resp.status_code, 302)
        self.assertIn(reverse("df_user:login"), edit_resp.url)
        self.assertEqual(delete_resp.status_code, 302)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 4)
        self.assertTrue(CartInfo.objects.filter(id=cart.id).exists())

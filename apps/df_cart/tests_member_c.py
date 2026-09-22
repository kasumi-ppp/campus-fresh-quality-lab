# 成员 C：购物车模块独立测试
#
# 覆盖需求编号：C-CART-002 / C-CART-003 / C-CART-004 / C-CART-005 /
# C-CART-007 / C-CART-008 / C-CART-009 / C-CART-010
#
# 本文件由成员 C 独立编写，针对购物车模块的权限隔离、数量校验和商品有效性。
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from df_cart.models import CartInfo
from df_goods.models import GoodsInfo, TypeInfo
from df_user.models import UserInfo


class CartTestBase(TestCase):
    """公共测试数据：两个用户共享一个商品，用于验证购物车数据隔离。"""

    def setUp(self):
        self.owner = UserInfo.objects.create(
            uname="owner", upwd="pwd", uemail="owner@example.com")
        self.other = UserInfo.objects.create(
            uname="other", upwd="pwd", uemail="other@example.com")

        self.category = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        self.goods = GoodsInfo.objects.create(
            gtitle="苹果", gprice=Decimal('12.50'), gunit="500g", gclick=0,
            gjianjie="新鲜苹果", gkucun=10, gcontent="优质苹果", gtype=self.category)

    def login(self, user=None):
        session = self.client.session
        session["user_id"] = (user or self.owner).id
        session.save()


class CartAccessControlTests(CartTestBase):
    """C-CART-002 / C-CART-008：购物车条目的读取、修改和删除必须校验所有者。"""

    def test_edit_other_user_cart_is_rejected(self):
        cart = CartInfo.objects.create(user=self.other, goods=self.goods, count=2)
        self.login(self.owner)

        resp = self.client.get(reverse("df_cart:edit", args=[cart.id, 9]))

        self.assertEqual(resp.json()["ok"], 0)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 2)

    def test_delete_other_user_cart_is_rejected(self):
        cart = CartInfo.objects.create(user=self.other, goods=self.goods, count=2)
        self.login(self.owner)

        resp = self.client.get(reverse("df_cart:delete", args=[cart.id]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertTrue(CartInfo.objects.filter(id=cart.id).exists())

    def test_delete_own_entry_does_not_touch_other_user(self):
        mine = CartInfo.objects.create(user=self.owner, goods=self.goods, count=1)
        theirs = CartInfo.objects.create(user=self.other, goods=self.goods, count=3)
        self.login(self.owner)

        resp = self.client.get(reverse("df_cart:delete", args=[mine.id]))

        self.assertEqual(resp.json()["ok"], 1)
        self.assertFalse(CartInfo.objects.filter(id=mine.id).exists())
        theirs.refresh_from_db()
        self.assertEqual(theirs.count, 3)

    def test_cart_page_only_lists_current_user_entries(self):
        CartInfo.objects.create(user=self.owner, goods=self.goods, count=1)
        CartInfo.objects.create(user=self.other, goods=self.goods, count=5)
        self.login(self.owner)

        resp = self.client.get(reverse("df_cart:cart"))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["carts"]), 1)


class CartQuantityValidationTests(CartTestBase):
    """C-CART-004：加入和修改的数量必须是正整数且不得超过当前可售库存。"""

    def test_add_rejects_zero_count(self):
        self.login()

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 0]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(CartInfo.objects.filter(user=self.owner).count(), 0)

    def test_add_rejects_count_over_stock(self):
        self.login()

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 11]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertIn("库存", resp.json()["msg"])
        self.assertEqual(CartInfo.objects.filter(user=self.owner).count(), 0)

    def test_add_rejects_accumulated_count_over_stock(self):
        """重复加入按累加后的数量判断上限，不能绕过库存限制（C-CART-003）。"""
        self.login()
        CartInfo.objects.create(user=self.owner, goods=self.goods, count=8)

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 5]))

        self.assertEqual(resp.json()["ok"], 0)
        cart = CartInfo.objects.get(user=self.owner, goods=self.goods)
        self.assertEqual(cart.count, 8)

    def test_add_accumulates_when_within_stock(self):
        self.login()
        CartInfo.objects.create(user=self.owner, goods=self.goods, count=4)

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 5]))

        self.assertEqual(resp.status_code, 302)
        cart = CartInfo.objects.get(user=self.owner, goods=self.goods)
        self.assertEqual(cart.count, 9)

    def test_edit_rejects_zero_count_and_returns_saved_value(self):
        """失败时返回服务器保存的数量，页面回填后与数据库保持一致（C-CART-007）。"""
        self.login()
        cart = CartInfo.objects.create(user=self.owner, goods=self.goods, count=3)

        resp = self.client.get(reverse("df_cart:edit", args=[cart.id, 0]))

        data = resp.json()
        self.assertEqual(data["ok"], 0)
        self.assertEqual(data["count"], 3)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 3)

    def test_edit_rejects_count_over_stock(self):
        self.login()
        cart = CartInfo.objects.create(user=self.owner, goods=self.goods, count=3)

        resp = self.client.get(reverse("df_cart:edit", args=[cart.id, 99]))

        self.assertEqual(resp.json()["ok"], 0)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 3)

    def test_edit_accepts_count_within_stock(self):
        self.login()
        cart = CartInfo.objects.create(user=self.owner, goods=self.goods, count=3)

        resp = self.client.get(reverse("df_cart:edit", args=[cart.id, 7]))

        self.assertEqual(resp.json()["count"], 0)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 7)


class CartGoodsStateTests(CartTestBase):
    """C-CART-005：已逻辑删除、分类失效或库存为 0 的商品不得进入购物流程。"""

    def test_add_rejects_deleted_goods(self):
        self.goods.isDelete = True
        self.goods.save()
        self.login()

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 1]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(CartInfo.objects.filter(user=self.owner).count(), 0)

    def test_add_rejects_goods_in_deleted_category(self):
        self.category.isDelete = True
        self.category.save()
        self.login()

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 1]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(CartInfo.objects.filter(user=self.owner).count(), 0)

    def test_add_rejects_out_of_stock_goods(self):
        self.goods.gkucun = 0
        self.goods.save()
        self.login()

        resp = self.client.get(reverse("df_cart:add", args=[self.goods.id, 1]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertEqual(CartInfo.objects.filter(user=self.owner).count(), 0)

    def test_edit_rejects_when_goods_taken_off_shelf(self):
        """商品在结算前失效时，不允许通过修改数量继续购买。"""
        self.login()
        cart = CartInfo.objects.create(user=self.owner, goods=self.goods, count=2)
        self.goods.isDelete = True
        self.goods.save()

        resp = self.client.get(reverse("df_cart:edit", args=[cart.id, 3]))

        self.assertEqual(resp.json()["ok"], 0)
        cart.refresh_from_db()
        self.assertEqual(cart.count, 2)


class CartErrorResponseTests(CartTestBase):
    """C-CART-010：无效条目编号或商品编号返回可理解的失败信息。"""

    def test_add_nonexistent_goods_returns_message(self):
        self.login()

        resp = self.client.get(reverse("df_cart:add", args=[999999, 1]))

        self.assertEqual(resp.json()["ok"], 0)
        self.assertIn("商品不存在", resp.json()["msg"])

    def test_edit_nonexistent_entry_returns_message(self):
        self.login()

        resp = self.client.get(reverse("df_cart:edit", args=[999999, 1]))

        data = resp.json()
        self.assertEqual(data["ok"], 0)
        self.assertTrue(data["msg"])
        self.assertNotIn("Traceback", resp.content.decode())

    def test_delete_nonexistent_entry_returns_message(self):
        self.login()

        resp = self.client.get(reverse("df_cart:delete", args=[999999]))

        data = resp.json()
        self.assertEqual(data["ok"], 0)
        self.assertTrue(data["msg"])
        self.assertNotIn("Traceback", resp.content.decode())



class CartUniqueConstraintTests(CartTestBase):
    """AI-17 并发加固：同一用户与同一商品的条目必须唯一。

    修复前：并发加购实测 5 轮全部异常（丢失数量更新或产生重复条目）。
    并发场景由独立压测脚本验证，此处守护模型层唯一约束这一兜底防线。
    """

    def test_unique_constraint_blocks_duplicate_entries(self):
        CartInfo.objects.create(user=self.owner, goods=self.goods, count=1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartInfo.objects.create(user=self.owner, goods=self.goods, count=2)

        self.assertEqual(
            CartInfo.objects.filter(user=self.owner, goods=self.goods).count(), 1)

    def test_different_users_may_hold_same_goods(self):
        """约束只针对同一用户，不同用户购买同一商品不受影响。"""
        CartInfo.objects.create(user=self.owner, goods=self.goods, count=1)
        CartInfo.objects.create(user=self.other, goods=self.goods, count=1)

        self.assertEqual(CartInfo.objects.filter(goods=self.goods).count(), 2)

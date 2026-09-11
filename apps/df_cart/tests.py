from django.test import TestCase
from django.urls import reverse
from django.http import JsonResponse
from decimal import Decimal

from df_cart.models import CartInfo
from df_user.models import UserInfo
from df_goods.models import TypeInfo, GoodsInfo


class CartModelsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_cart tests] ===== 购物车模型测试套件开始 =====")
        # 规避 SQLite 迁移重建表后的 __old 外键引用问题
        try:
            from django.db import connection
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA foreign_keys=OFF;')
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        print("[df_cart tests] ===== 购物车模型测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_cart tests] setUp: 创建测试数据 ...")
        # 创建用户
        self.user = UserInfo.objects.create(
            uname="testuser",
            upwd="hashedpassword",
            uemail="test@example.com"
        )
        
        # 创建商品分类
        self.type1 = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        
        # 创建商品
        self.goods1 = GoodsInfo.objects.create(
            gtitle="苹果",
            gprice=Decimal('12.50'),
            gunit="500g",
            gclick=10,
            gjianjie="新鲜苹果",
            gkucun=100,
            gcontent="优质苹果",
            gtype=self.type1
        )

    def test_cartinfo_creation(self):
        print("[df_cart tests] 开始: test_cartinfo_creation")
        cart = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        self.assertEqual(cart.user, self.user)
        self.assertEqual(cart.goods, self.goods1)
        self.assertEqual(cart.count, 2)
        print("[df_cart tests] 结果: 购物车记录创建成功")

    def test_cartinfo_str_representation(self):
        print("[df_cart tests] 开始: test_cartinfo_str_representation")
        cart = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        expected_str = f"{self.user.uname}的购物车"
        self.assertEqual(str(cart), expected_str)
        print("[df_cart tests] 结果: 购物车字符串表示正确")


class CartViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_cart tests] ===== 购物车视图测试套件开始 =====")
        # 规避 SQLite 迁移重建表后的 __old 外键引用问题
        try:
            from django.db import connection
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA foreign_keys=OFF;')
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        print("[df_cart tests] ===== 购物车视图测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_cart tests] setUp: 创建测试数据 ...")
        # 创建用户
        self.user = UserInfo.objects.create(
            uname="testuser",
            upwd="hashedpassword",
            uemail="test@example.com"
        )
        
        # 创建商品分类
        self.type1 = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        
        # 创建商品
        self.goods1 = GoodsInfo.objects.create(
            gtitle="苹果",
            gprice=Decimal('12.50'),
            gunit="500g",
            gclick=10,
            gjianjie="新鲜苹果",
            gkucun=100,
            gcontent="优质苹果",
            gtype=self.type1
        )

    def test_user_cart_page_redirects_when_not_logged_in(self):
        print("[df_cart tests] 开始: test_user_cart_page_redirects_when_not_logged_in")
        url = reverse("df_cart:cart")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("df_user:login"), resp.url)
        print("[df_cart tests] 结果: 未登录访问购物车被重定向到登录页")

    def test_user_cart_page_ok_when_logged_in(self):
        print("[df_cart tests] 开始: test_user_cart_page_ok_when_logged_in")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 添加购物车商品
        CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        
        url = reverse("df_cart:cart")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_cart/cart.html")
        self.assertIn("carts", resp.context)
        self.assertEqual(len(resp.context["carts"]), 1)
        print("[df_cart tests] 结果: 登录用户购物车页可访问, 显示商品列表")

    def test_add_to_cart_new_item(self):
        print("[df_cart tests] 开始: test_add_to_cart_new_item")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        url = reverse("df_cart:add", args=[self.goods1.id, 2])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("df_cart:cart"))
        
        # 验证购物车记录创建
        cart = CartInfo.objects.filter(user=self.user, goods=self.goods1).first()
        self.assertIsNotNone(cart)
        self.assertEqual(cart.count, 2)
        print("[df_cart tests] 结果: 新商品添加到购物车成功")

    def test_add_to_cart_existing_item(self):
        print("[df_cart tests] 开始: test_add_to_cart_existing_item")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 先添加一个商品
        CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        
        # 再次添加相同商品
        url = reverse("df_cart:add", args=[self.goods1.id, 3])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        
        # 验证数量累加
        cart = CartInfo.objects.get(user=self.user, goods=self.goods1)
        self.assertEqual(cart.count, 5)  # 2 + 3
        print("[df_cart tests] 结果: 已存在商品数量正确累加")

    def test_edit_cart_success(self):
        print("[df_cart tests] 开始: test_edit_cart_success")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 创建购物车记录
        cart = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        
        url = reverse("df_cart:edit", args=[cart.id, 5])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        data = resp.json()
        self.assertEqual(data["count"], 0)  # 成功时返回 0
        
        # 验证数量更新
        cart.refresh_from_db()
        self.assertEqual(cart.count, 5)
        print("[df_cart tests] 结果: 购物车商品数量编辑成功")

    def test_delete_cart_success(self):
        print("[df_cart tests] 开始: test_delete_cart_success")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 创建购物车记录
        cart = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        cart_id = cart.id
        
        url = reverse("df_cart:delete", args=[cart_id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        data = resp.json()
        self.assertEqual(data["ok"], 1)
        
        # 验证记录被删除
        self.assertFalse(CartInfo.objects.filter(id=cart_id).exists())
        print("[df_cart tests] 结果: 购物车商品删除成功")
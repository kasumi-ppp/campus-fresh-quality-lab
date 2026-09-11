from django.test import TestCase
from django.urls import reverse
from django.http import JsonResponse
from decimal import Decimal

from df_order.models import OrderInfo, OrderDetailInfo
from df_user.models import UserInfo
from df_goods.models import TypeInfo, GoodsInfo
from df_cart.models import CartInfo


class OrderModelsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_order tests] ===== 订单模型测试套件开始 =====")

    @classmethod
    def tearDownClass(cls):
        print("[df_order tests] ===== 订单模型测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_order tests] setUp: 创建测试数据 ...")
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

    def test_orderinfo_creation(self):
        print("[df_order tests] 开始: test_orderinfo_creation")
        order = OrderInfo.objects.create(
            oid="202401011200001",
            user=self.user,
            ototal=Decimal('25.00'),
            oaddress="北京市海淀区",
            oIsPay=False
        )
        self.assertEqual(order.oid, "202401011200001")
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.ototal, Decimal('25.00'))
        self.assertEqual(order.oaddress, "北京市海淀区")
        self.assertFalse(order.oIsPay)
        print("[df_order tests] 结果: 订单信息创建成功")

    def test_orderdetailinfo_creation(self):
        print("[df_order tests] 开始: test_orderdetailinfo_creation")
        # 先创建订单
        order = OrderInfo.objects.create(
            oid="202401011200001",
            user=self.user,
            ototal=Decimal('25.00'),
            oaddress="北京市海淀区"
        )
        
        # 创建订单详情
        order_detail = OrderDetailInfo.objects.create(
            goods=self.goods1,
            order=order,
            price=self.goods1.gprice,
            count=2
        )
        
        self.assertEqual(order_detail.goods, self.goods1)
        self.assertEqual(order_detail.order, order)
        self.assertEqual(order_detail.price, self.goods1.gprice)
        self.assertEqual(order_detail.count, 2)
        print("[df_order tests] 结果: 订单详情创建成功")


class OrderViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_order tests] ===== 订单视图测试套件开始 =====")

    @classmethod
    def tearDownClass(cls):
        print("[df_order tests] ===== 订单视图测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_order tests] setUp: 创建测试数据 ...")
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
        self.goods2 = GoodsInfo.objects.create(
            gtitle="香蕉",
            gprice=Decimal('8.00'),
            gunit="500g",
            gclick=5,
            gjianjie="新鲜香蕉",
            gkucun=50,
            gcontent="优质香蕉",
            gtype=self.type1
        )

    def test_order_page_redirects_when_not_logged_in(self):
        print("[df_order tests] 开始: test_order_page_redirects_when_not_logged_in")
        url = reverse("df_order:order")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("df_user:login"), resp.url)
        print("[df_order tests] 结果: 未登录访问订单页被重定向到登录页")

    def test_order_page_ok_when_logged_in(self):
        print("[df_order tests] 开始: test_order_page_ok_when_logged_in")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 添加购物车商品
        cart1 = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        cart2 = CartInfo.objects.create(
            user=self.user,
            goods=self.goods2,
            count=1
        )
        
        url = reverse("df_order:order")
        resp = self.client.get(url, {"cart_id": [cart1.id, cart2.id]})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_order/place_order.html")
        self.assertIn("user", resp.context)
        self.assertIn("carts", resp.context)
        self.assertIn("total_price", resp.context)
        print("[df_order tests] 结果: 登录用户订单页可访问, 显示购物车商品和价格")

    def test_order_handle_success(self):
        print("[df_order tests] 开始: test_order_handle_success")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 添加购物车商品
        cart1 = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=2
        )
        cart2 = CartInfo.objects.create(
            user=self.user,
            goods=self.goods2,
            count=1
        )
        
        url = reverse("df_order:push")
        resp = self.client.post(url, {
            "cart_ids": f"{cart1.id},{cart2.id}",
            "total": "33.00"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp, JsonResponse)
        data = resp.json()
        self.assertEqual(data["ok"], 1)
        
        # 验证订单创建
        order = OrderInfo.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.ototal, Decimal('33.00'))
        
        # 验证订单详情创建
        order_details = OrderDetailInfo.objects.filter(order=order)
        self.assertEqual(order_details.count(), 2)
        
        # 验证购物车被删除
        self.assertFalse(CartInfo.objects.filter(id=cart1.id).exists())
        self.assertFalse(CartInfo.objects.filter(id=cart2.id).exists())
        
        # 验证库存减少
        self.goods1.refresh_from_db()
        self.goods2.refresh_from_db()
        self.assertEqual(self.goods1.gkucun, 98)  # 100 - 2
        self.assertEqual(self.goods2.gkucun, 49)  # 50 - 1
        print("[df_order tests] 结果: 订单提交成功, 库存正确减少, 购物车被清空")

    def test_order_handle_insufficient_stock(self):
        print("[df_order tests] 开始: test_order_handle_insufficient_stock")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        # 添加购物车商品，数量超过库存
        cart1 = CartInfo.objects.create(
            user=self.user,
            goods=self.goods1,
            count=150  # 超过库存100
        )
        
        url = reverse("df_order:push")
        resp = self.client.post(url, {
            "cart_ids": f"{cart1.id}",
            "total": "1875.00"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "库存不足")
        
        # 验证订单未创建
        order_count = OrderInfo.objects.filter(user=self.user).count()
        self.assertEqual(order_count, 0)
        
        # 验证购物车未被删除
        self.assertTrue(CartInfo.objects.filter(id=cart1.id).exists())
        
        # 验证库存未减少
        self.goods1.refresh_from_db()
        self.assertEqual(self.goods1.gkucun, 100)
        print("[df_order tests] 结果: 库存不足时订单提交失败, 数据回滚正确")
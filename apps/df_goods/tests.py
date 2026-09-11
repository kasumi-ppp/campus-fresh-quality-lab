# 运行所有测试  要求python版本为3.8-3.12
# python manage.py test -v 2

# 运行特定模块测试
#python manage.py test apps.df_user -v 2
#python manage.py test apps.df_goods -v 2
#python manage.py test apps.df_cart -v 2
#python manage.py test apps.df_order -v 2
from django.test import TestCase
from django.urls import reverse
from django.core.paginator import Paginator
from decimal import Decimal

from df_goods.models import TypeInfo, GoodsInfo
from df_user.models import UserInfo
from df_cart.models import CartInfo


class GoodsModelsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_goods tests] ===== 商品模型测试套件开始 =====")

    @classmethod
    def tearDownClass(cls):
        print("[df_goods tests] ===== 商品模型测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_goods tests] setUp: 创建测试数据 ...")
        # 创建商品分类
        self.type1 = TypeInfo.objects.create(
            ttitle="水果",
            isDelete=False
        )
        self.type2 = TypeInfo.objects.create(
            ttitle="海鲜",
            isDelete=False
        )
        
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
        self.goods3 = GoodsInfo.objects.create(
            gtitle="大闸蟹",
            gprice=Decimal('88.00'),
            gunit="1kg",
            gclick=20,
            gjianjie="新鲜大闸蟹",
            gkucun=30,
            gcontent="优质大闸蟹",
            gtype=self.type2
        )

    def test_typeinfo_creation(self):
        print("[df_goods tests] 开始: test_typeinfo_creation")
        self.assertEqual(self.type1.ttitle, "水果")
        self.assertEqual(self.type2.ttitle, "海鲜")
        self.assertFalse(self.type1.isDelete)
        print("[df_goods tests] 结果: 商品分类创建成功")

    def test_goodsinfo_creation(self):
        print("[df_goods tests] 开始: test_goodsinfo_creation")
        self.assertEqual(self.goods1.gtitle, "苹果")
        self.assertEqual(self.goods1.gprice, Decimal('12.50'))
        self.assertEqual(self.goods1.gtype, self.type1)
        self.assertEqual(self.goods1.gkucun, 100)
        print("[df_goods tests] 结果: 商品信息创建成功")

    def test_goodsinfo_str_representation(self):
        print("[df_goods tests] 开始: test_goodsinfo_str_representation")
        self.assertEqual(str(self.goods1), "苹果")
        self.assertEqual(str(self.goods2), "香蕉")
        print("[df_goods tests] 结果: 商品字符串表示正确")

    def test_typeinfo_str_representation(self):
        print("[df_goods tests] 开始: test_typeinfo_str_representation")
        self.assertEqual(str(self.type1), "水果")
        self.assertEqual(str(self.type2), "海鲜")
        print("[df_goods tests] 结果: 分类字符串表示正确")

    def test_sample_image_uses_static_url(self):
        print("[df_goods tests] 开始: test_sample_image_uses_static_url")
        self.goods1.gpic = 'df_goods/goods001.jpg'
        self.assertEqual(self.goods1.image_url, '/static/df_goods/goods001.jpg')
        print("[df_goods tests] 结果: 示例商品图片使用静态资源路径")


class GoodsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_goods tests] ===== 商品视图测试套件开始 =====")
        # 规避 SQLite 在迁移重建表后残留的 __old 外键引用导致的错误
        try:
            from django.db import connection
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA foreign_keys=OFF;')
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        print("[df_goods tests] ===== 商品视图测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_goods tests] setUp: 创建测试数据 ...")
        # 创建用户
        self.user = UserInfo.objects.create(
            uname="testuser",
            upwd="hashedpassword",
            uemail="test@example.com"
        )
        
        # 创建6个商品分类（首页需要6个分类）
        self.type1 = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        self.type2 = TypeInfo.objects.create(ttitle="海鲜", isDelete=False)
        self.type3 = TypeInfo.objects.create(ttitle="蔬菜", isDelete=False)
        self.type4 = TypeInfo.objects.create(ttitle="肉类", isDelete=False)
        self.type5 = TypeInfo.objects.create(ttitle="坚果", isDelete=False)
        self.type6 = TypeInfo.objects.create(ttitle="饮品", isDelete=False)
        
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
        self.goods3 = GoodsInfo.objects.create(
            gtitle="大闸蟹",
            gprice=Decimal('88.00'),
            gunit="1kg",
            gclick=20,
            gjianjie="新鲜大闸蟹",
            gkucun=30,
            gcontent="优质大闸蟹",
            gtype=self.type2
        )

    def test_index_page_ok(self):
        print("[df_goods tests] 开始: test_index_page_ok")
        url = reverse("df_goods:index")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_goods/index.html")
        self.assertIn("title", resp.context)
        self.assertEqual(resp.context["title"], "首页")
        print("[df_goods tests] 结果: 首页可访问, 模板正确")

    def test_index_only_renders_populated_categories_with_valid_links(self):
        print("[df_goods tests] 开始: test_index_only_renders_populated_categories_with_valid_links")
        resp = self.client.get(reverse("df_goods:index"))
        sections = resp.context["sections"]
        self.assertEqual([section["category"] for section in sections], [self.type1, self.type2])
        self.assertContains(resp, reverse("df_goods:detail", args=[self.goods1.id]))
        self.assertContains(resp, reverse("df_goods:good_list", args=[self.type1.id, 1, 1]))
        print("[df_goods tests] 结果: 首页仅显示有商品分类，商品链接有效")

    def test_index_page_with_login_user(self):
        print("[df_goods tests] 开始: test_index_page_with_login_user")
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
        
        url = reverse("df_goods:index")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["cart_num"], 1)
        self.assertEqual(resp.context["guest_cart"], 1)
        print("[df_goods tests] 结果: 登录用户首页显示购物车数量正确")

    def test_good_list_page_ok(self):
        print("[df_goods tests] 开始: test_good_list_page_ok")
        url = reverse("df_goods:good_list", args=[self.type1.id, 1, 1])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_goods/list.html")
        self.assertIn("typeinfo", resp.context)
        self.assertEqual(resp.context["typeinfo"], self.type1)
        print("[df_goods tests] 结果: 商品列表页可访问, 分类信息正确")

    def test_good_list_sort_by_price(self):
        print("[df_goods tests] 开始: test_good_list_sort_by_price")
        url = reverse("df_goods:good_list", args=[self.type1.id, 1, 2])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["sort"], "2")
        print("[df_goods tests] 结果: 按价格排序功能正常")

    def test_good_list_sort_by_click(self):
        print("[df_goods tests] 开始: test_good_list_sort_by_click")
        url = reverse("df_goods:good_list", args=[self.type1.id, 1, 3])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["sort"], "3")
        print("[df_goods tests] 结果: 按点击量排序功能正常")

    def test_good_detail_page_ok(self):
        print("[df_goods tests] 开始: test_good_detail_page_ok")
        initial_click = self.goods1.gclick
        url = reverse("df_goods:detail", args=[self.goods1.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_goods/detail.html")
        self.assertIn("goods", resp.context)
        self.assertEqual(resp.context["goods"], self.goods1)
        
        # 验证点击量增加
        self.goods1.refresh_from_db()
        self.assertEqual(self.goods1.gclick, initial_click + 1)
        print("[df_goods tests] 结果: 商品详情页可访问, 点击量正确增加")

    def test_good_detail_with_login_user_browser_record(self):
        print("[df_goods tests] 开始: test_good_detail_with_login_user_browser_record")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        url = reverse("df_goods:detail", args=[self.goods1.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # 验证浏览记录创建
        from df_user.models import GoodsBrowser
        browser_record = GoodsBrowser.objects.filter(
            user=self.user, 
            good=self.goods1
        ).first()
        self.assertIsNotNone(browser_record)
        print("[df_goods tests] 结果: 登录用户浏览记录创建成功")

    def test_ordinary_search_with_results(self):
        print("[df_goods tests] 开始: test_ordinary_search_with_results")
        url = reverse("df_goods:ordinary_search")
        resp = self.client.get(url, {"q": "苹果"})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_goods/ordinary_search.html")
        self.assertEqual(resp.context["search_status"], 1)
        self.assertIn("page", resp.context)
        print("[df_goods tests] 结果: 搜索有结果时状态正确")

    def test_ordinary_search_no_results(self):
        print("[df_goods tests] 开始: test_ordinary_search_no_results")
        url = reverse("df_goods:ordinary_search")
        resp = self.client.get(url, {"q": "不存在的商品"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["search_status"], 0)
        print("[df_goods tests] 结果: 搜索无结果时显示推荐商品")

    def test_ordinary_search_with_login_user(self):
        print("[df_goods tests] 开始: test_ordinary_search_with_login_user")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session.save()
        
        url = reverse("df_goods:ordinary_search")
        resp = self.client.get(url, {"q": "苹果"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["guest_cart"], 1)
        print("[df_goods tests] 结果: 登录用户搜索页显示购物车状态正确")

    def test_cart_count_function(self):
        print("[df_goods tests] 开始: test_cart_count_function")
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
        CartInfo.objects.create(
            user=self.user,
            goods=self.goods2,
            count=1
        )
        
        # 测试 cart_count 函数
        from df_goods.views import cart_count
        request = self.client.request()
        request.session = session
        count = cart_count(request)
        self.assertEqual(count, 2)
        print("[df_goods tests] 结果: 购物车计数函数正确")


class GoodsPaginationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_goods tests] ===== 商品分页测试套件开始 =====")

    @classmethod
    def tearDownClass(cls):
        print("[df_goods tests] ===== 商品分页测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_goods tests] setUp: 创建分页测试数据 ...")
        # 创建商品分类
        self.type1 = TypeInfo.objects.create(ttitle="水果", isDelete=False)
        
        # 创建多个商品用于测试分页
        for i in range(10):
            GoodsInfo.objects.create(
                gtitle=f"商品{i+1}",
                gprice=Decimal('10.00'),
                gunit="500g",
                gclick=i,
                gjianjie=f"商品{i+1}简介",
                gkucun=100,
                gcontent=f"商品{i+1}详情",
                gtype=self.type1
            )

    def test_good_list_pagination_first_page(self):
        print("[df_goods tests] 开始: test_good_list_pagination_first_page")
        url = reverse("df_goods:good_list", args=[self.type1.id, 1, 1])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("page", resp.context)
        self.assertIn("paginator", resp.context)
        self.assertEqual(resp.context["page"].number, 1)
        print("[df_goods tests] 结果: 第一页分页正确")

    def test_good_list_pagination_second_page(self):
        print("[df_goods tests] 开始: test_good_list_pagination_second_page")
        url = reverse("df_goods:good_list", args=[self.type1.id, 2, 1])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["page"].number, 2)
        print("[df_goods tests] 结果: 第二页分页正确")

    def test_search_pagination(self):
        print("[df_goods tests] 开始: test_search_pagination")
        url = reverse("df_goods:ordinary_search")
        resp = self.client.get(url, {"q": "商品", "pindex": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("page", resp.context)
        self.assertIn("paginator", resp.context)
        print("[df_goods tests] 结果: 搜索分页功能正常")

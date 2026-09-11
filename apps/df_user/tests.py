from django.test import TestCase
from django.urls import reverse
from django.http import HttpResponse
from hashlib import sha1

from df_user.models import UserInfo

#尝试Travis CI 上运行 Django 项目的单元测试
class UserViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("[df_user tests] ===== 测试套件开始 =====")

    @classmethod
    def tearDownClass(cls):
        print("[df_user tests] ===== 测试套件结束 =====")
        super().tearDownClass()

    def setUp(self):
        print("[df_user tests] setUp: 创建初始用户数据 ...")
        # 预置一个已注册用户（密码使用与视图相同的 sha1 方式加密）
        raw_pwd = "secret123"
        s1 = sha1()
        s1.update(raw_pwd.encode("utf8"))
        self.user_password_plain = raw_pwd
        self.user = UserInfo.objects.create(
            uname="alice",
            upwd=s1.hexdigest(),
            uemail="alice@example.com",
            ushou="",
            uaddress="",
            uyoubian="",
            uphone="",
        )

    def test_register_page_ok(self):
        print("[df_user tests] 开始: test_register_page_ok")
        url = reverse("df_user:register")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_user/register.html")
        print("[df_user tests] 结果: 注册页可访问, 使用模板 df_user/register.html")

    def test_register_handle_password_mismatch_redirect(self):
        print("[df_user tests] 开始: test_register_handle_password_mismatch_redirect")
        url = reverse("df_user:register_handle")
        resp = self.client.post(url, {
            "user_name": "bob",
            "pwd": "123456",
            "confirm_pwd": "654321",
            "email": "bob@example.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith("/user/register/"))
        print(f"[df_user tests] 结果: 密码不一致 -> 302 跳转到 {resp.url}")

    def test_register_handle_success_render_login(self):
        print("[df_user tests] 开始: test_register_handle_success_render_login")
        url = reverse("df_user:register_handle")
        resp = self.client.post(url, {
            "user_name": "charlie",
            "pwd": "pass123456",
            "confirm_pwd": "pass123456",
            "email": "charlie@example.com",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_user/login.html")
        self.assertIn("username", resp.context)
        self.assertEqual(resp.context["username"], "charlie")
        print("[df_user tests] 结果: 注册成功 -> 渲染登录页, context.username=charlie")

    def test_register_exist_json(self):
        print("[df_user tests] 开始: test_register_exist_json")
        url = reverse("df_user:register_exist")
        # 已存在用户名 alice，count 应为 1
        resp1 = self.client.get(url, {"uname": "alice"})
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json().get("count"), 1)
        print("[df_user tests] 检查已存在用户名 -> count=1")
        # 不存在用户名，count 应为 0
        resp2 = self.client.get(url, {"uname": "nobody"})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json().get("count"), 0)
        print("[df_user tests] 检查不存在用户名 -> count=0")

    def test_login_page_ok(self):
        print("[df_user tests] 开始: test_login_page_ok")
        url = reverse("df_user:login")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_user/login.html")
        print("[df_user tests] 结果: 登录页可访问, 使用模板 df_user/login.html")

    def test_login_handle_success_redirect_and_cookie(self):
        print("[df_user tests] 开始: test_login_handle_success_redirect_and_cookie")
        url = reverse("df_user:login_handle")
        # 传 jizhu=1 以便设置 uname cookie
        resp = self.client.post(url, {
            "username": self.user.uname,
            "pwd": self.user_password_plain,
            "jizhu": 1,
        })
        self.assertEqual(resp.status_code, 302)
        # 未设置 url cookie 时，默认重定向到 /
        self.assertEqual(resp.url, "/")
        # 记住用户名 cookie 已设置
        self.assertIn("uname", resp.cookies)
        self.assertEqual(resp.cookies["uname"].value, self.user.uname)
        print(f"[df_user tests] 结果: 登录成功 -> 302 跳转 {resp.url}, 设置 cookie uname={self.user.uname}")

    def test_login_required_decorator_redirects_when_not_logged_in(self):
        print("[df_user tests] 开始: test_login_required_decorator_redirects_when_not_logged_in")
        # 访问需要登录的 info 页，应被重定向到登录页
        url = reverse("df_user:info")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("df_user:login"), resp.url)
        print(f"[df_user tests] 结果: 未登录访问 info -> 302 跳转到 {resp.url}")

    def test_info_page_ok_when_logged_in(self):
        print("[df_user tests] 开始: test_info_page_ok_when_logged_in")
        # 模拟登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session["user_name"] = self.user.uname
        session.save()

        url = reverse("df_user:info")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_user/user_center_info.html")
        self.assertIn("user_name", resp.context)
        self.assertEqual(resp.context["user_name"], self.user.uname)
        print("[df_user tests] 结果: 已登录访问 info -> 200 且模板正确, user_name 匹配")

    def test_site_update_profile_post(self):
        print("[df_user tests] 开始: test_site_update_profile_post")
        # 登录态
        session = self.client.session
        session["user_id"] = self.user.id
        session["user_name"] = self.user.uname
        session.save()

        url = reverse("df_user:site")
        payload = {
            "ushou": "张三",
            "uaddress": "北京市海淀区",
            "uyoubian": "100000",
            "uphone": "13800000000",
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "df_user/user_center_site.html")

        # 刷新对象验证已保存
        self.user.refresh_from_db()
        self.assertEqual(self.user.ushou, payload["ushou"])
        self.assertEqual(self.user.uaddress, payload["uaddress"])
        self.assertEqual(self.user.uyoubian, payload["uyoubian"])
        self.assertEqual(self.user.uphone, payload["uphone"])
        print("[df_user tests] 结果: POST 更新地址成功, 字段已正确持久化")


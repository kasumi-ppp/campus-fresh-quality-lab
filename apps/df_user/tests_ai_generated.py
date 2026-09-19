# 模块二 AI 生成测试：登录回跳安全（AI 发现缺陷 AI-21 的回归）
#
# 本文件由 AI 工具（ZCode/GLM）生成，成员 C 审核修改后执行。
# 属于课程模块二「AI 测」方案交付物。
#
# 覆盖用例：C-AI-SEC-001
# 缺陷背景：登录视图直接重定向到用户可篡改的 url Cookie，
# 构成开放重定向漏洞（钓鱼跳转）。AI 定位后增加站内路径校验。
# 运行方式：python manage.py test apps.df_user.tests_ai_generated
import hashlib

from django.test import TestCase
from django.urls import reverse

from df_user.models import UserInfo


class AiLoginRedirectTests(TestCase):
    """C-AI-SEC-001：url Cookie 只能用于站内回跳。"""

    def setUp(self):
        self.pwd_sha1 = hashlib.sha1("123456".encode("utf8")).hexdigest()
        self.user = UserInfo.objects.create(
            uname="sec_user", upwd=self.pwd_sha1,
            uemail="sec_user@example.com")

    def login_with_redirect_cookie(self, cookie_value):
        self.client.cookies["url"] = cookie_value
        return self.client.post(reverse("df_user:login_handle"), {
            "username": "sec_user",
            "pwd": "123456",
            "jizhu": 0,
        })

    def test_external_cookie_url_is_not_followed(self):
        """C-AI-SEC-001：外站回跳地址必须被拒绝。

        预期：登录成功但重定向到站内首页“/”，绝不跳向外站（防钓鱼）。
        """
        resp = self.login_with_redirect_cookie("https://evil.example.com/phish")

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")
        # 登录本身应正常完成
        self.assertIn("user_id", self.client.session)

    def test_protocol_relative_cookie_url_is_not_followed(self):
        """C-AI-SEC-001：协议相对地址（//evil.com）同样拒绝。"""
        resp = self.login_with_redirect_cookie("//evil.example.com/phish")

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_site_relative_cookie_url_still_works(self):
        """C-AI-SEC-001：合法站内路径（如 /cart/）回跳不受影响。"""
        resp = self.login_with_redirect_cookie("/cart/")

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/cart/")
        self.assertIn("user_id", self.client.session)

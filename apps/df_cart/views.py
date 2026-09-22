from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, redirect, reverse

from .models import CartInfo
from df_goods.models import GoodsInfo
from df_user import user_decorator


class CartLimitExceeded(Exception):
    """累加后的数量超过库存（C-CART-004），用于回滚本次加购。"""

    def __init__(self, gkucun):
        self.gkucun = gkucun


def _cart_entry_count(uid):
    """当前用户购物车中的商品件数，用于页面角标。"""
    return CartInfo.objects.filter(user_id=uid).count()


def _fail(message, **extra):
    """购物车写操作的失败响应：给出可理解的提示，不泄露调试信息（C-CART-010）。"""
    data = {'ok': 0, 'msg': message}
    data.update(extra)
    return JsonResponse(data)


@user_decorator.login
def user_cart(request):
    uid = request.session['user_id']
    carts = CartInfo.objects.filter(user_id=uid)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        # 求当前用户购买了几件商品
        return JsonResponse({'count': carts.count()})
    context = {
        'title': '购物车',
        'page_name': 1,
        'carts': carts
    }
    return render(request, 'df_cart/cart.html', context)


@user_decorator.login
def add(request, gid, count):
    uid = request.session['user_id']
    gid, count = int(gid), int(count)

    # C-CART-004：购买数量必须是正整数
    if count < 1:
        return _fail('购买数量必须是大于 0 的整数', count=_cart_entry_count(uid))

    goods = GoodsInfo.objects.filter(pk=gid).select_related('gtype').first()
    if goods is None:
        return _fail('商品不存在', count=_cart_entry_count(uid))
    # C-CART-005：已逻辑删除、所属分类失效或库存为 0 的商品不得新加入购物车
    if not goods.is_on_sale:
        return _fail('商品“%s”已下架或暂时缺货，无法加入购物车' % goods.gtitle,
                     count=_cart_entry_count(uid))

    # C-CART-003：同一用户的同一商品只保留一个条目，重复加入时累加数量。
    # 并发加固（AI-17）：原实现「先查条目、再算数量、后写回」不是原子操作，
    # 并发加购会产生重复条目或丢失数量更新（实测 10 并发 5 轮全部异常）。
    # 改为由数据库端累加，并以 (user, goods) 唯一约束兜底。
    try:
        with transaction.atomic():
            updated = CartInfo.objects.filter(
                user_id=uid, goods_id=gid
            ).update(count=F('count') + count)
            if updated == 0:
                try:
                    with transaction.atomic():
                        CartInfo.objects.create(user_id=uid, goods_id=gid, count=count)
                except IntegrityError:
                    # 并发插入被唯一约束拦下，改为在已存在的条目上累加
                    CartInfo.objects.filter(
                        user_id=uid, goods_id=gid
                    ).update(count=F('count') + count)
            cart = CartInfo.objects.filter(user_id=uid, goods_id=gid).first()
            # C-CART-004：累加后的数量不得超过商品当前可售库存
            if cart is not None and cart.count > goods.gkucun:
                raise CartLimitExceeded(goods.gkucun)
    except CartLimitExceeded as exc:
        return _fail('购买数量超过库存，当前库存 %d' % exc.gkucun,
                     count=_cart_entry_count(uid))

    # 如果是ajax提交则直接返回json，否则转向购物车
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({'count': _cart_entry_count(uid)})
    return redirect(reverse("df_cart:cart"))


@user_decorator.login
def edit(request, cart_id, count):
    uid = request.session['user_id']
    cart_id, count = int(cart_id), int(count)

    # C-CART-002：只能修改属于自己的购物车条目，浏览器传入的编号不能作为权限依据
    cart = CartInfo.objects.filter(
        pk=cart_id, user_id=uid
    ).select_related('goods', 'goods__gtype').first()
    if cart is None:
        return _fail('购物车条目不存在', count=0)

    # C-CART-004：数量必须是正整数，且不得超过商品当前可售库存
    if count < 1:
        return _fail('购买数量必须是大于 0 的整数', count=cart.count)
    if not cart.goods.is_on_sale:
        return _fail('商品“%s”已下架或暂时缺货' % cart.goods.gtitle, count=cart.count)
    if count > cart.goods.gkucun:
        return _fail('购买数量超过库存，当前库存 %d' % cart.goods.gkucun, count=cart.count)

    cart.count = count
    cart.save()
    # count 为 0 表示修改成功，沿用页面原有的判定约定（C-CART-007）
    return JsonResponse({'ok': 1, 'count': 0})


@user_decorator.login
def delete(request, cart_id):
    uid = request.session['user_id']

    # C-CART-008：只能删除属于自己的条目，其他用户的数据不受影响
    deleted, _ = CartInfo.objects.filter(pk=cart_id, user_id=uid).delete()
    if deleted == 0:
        return _fail('购物车条目不存在或已被删除')
    return JsonResponse({'ok': 1})

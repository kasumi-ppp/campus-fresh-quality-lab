from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render

from datetime import datetime
from decimal import Decimal
import random

from .models import OrderInfo, OrderDetailInfo
from df_cart.models import CartInfo
from df_goods.models import GoodsInfo
from df_user.models import UserInfo
from df_user import user_decorator

# C-ORD-004：配送费固定为每个订单 10.00 元，确认页与订单记录使用同一规则
TRANS_COST = Decimal('10.00')


class OrderSubmitError(Exception):
    """下单过程中的业务失败，用于回滚事务并向用户返回可理解的提示。"""


def _new_oid():
    """生成 18 位订单号（C-ORD-006）：秒级时间戳加 4 位随机片段。

    原实现先查库判断编号是否已存在再插入。该查询位于下单事务内部，会让整个事务
    以读语句开始，SQLite 下多个事务同时「读后写」不会等待而是直接返回
    database is locked（实测 10 并发仅 1 单成功）。改为不在事务内查询，
    依靠主键唯一性保证不重复，插入冲突时由调用方重新生成。
    """
    now = datetime.now()
    return '%s%04d' % (now.strftime('%Y%m%d%H%M%S'), random.randint(0, 9999))


def _parse_cart_id(raw_id):
    """购物车条目编号必须是正整数，非法参数返回 None（C-ORD-001）。"""
    try:
        cart_id = int(str(raw_id).strip())
    except (TypeError, ValueError):
        return None
    return cart_id if cart_id > 0 else None


@user_decorator.login
def order(request):
    uid = request.session['user_id']
    user = UserInfo.objects.get(id=uid)

    carts = []
    for raw_id in request.GET.getlist('cart_id'):
        cart_id = _parse_cart_id(raw_id)
        if cart_id is None:
            continue
        # C-ORD-001：只能选择属于自己的购物车条目，且商品必须仍然有效
        cart = CartInfo.objects.filter(
            pk=cart_id, user_id=uid
        ).select_related('goods', 'goods__gtype').first()
        if cart is not None and cart.goods.is_on_sale:
            carts.append(cart)

    # C-ORD-005：金额由服务器使用十进制数计算，不使用浮点数
    total_price = sum((cart.goods.gprice * cart.count for cart in carts), Decimal('0.00'))
    total_trans_price = total_price + TRANS_COST

    context = {
        'title': '提交订单',
        'page_name': 1,
        'user': user,
        'carts': carts,
        'total_price': total_price,
        'trans_cost': TRANS_COST,
        'total_trans_price': total_trans_price,
        # C-CART-009：没有有效商品时页面给出提示，并阻止提交
        'empty_cart': not carts,
    }
    return render(request, 'df_order/place_order.html', context)


@user_decorator.login
def order_handle(request):
    """创建订单：只读校验在事务外完成，事务内只包含写语句。

    这样拆分是因为 SQLite 的锁行为：事务若以读语句开始、之后再升级为写锁，并发时
    不会等待而是直接返回 database is locked。让事务的第一条语句就是写语句，并发
    请求才会被正确串行化（实测修复前 10 并发仅 1 单成功、9 单报通用错误，修复后
    5 单成功、5 单按库存不足被拒）。写入仍集中在同一事务内完成（C-INV-005），
    任一环节失败整体回滚（C-INV-003）。
    """
    uid = request.session['user_id']
    cart_ids = (request.POST.get('cart_ids') or '').strip()

    # ---- 事务外：只读校验，不占用写锁 ----
    try:
        # C-CART-009：空购物车不得进入无商品的订单确认流程
        if not cart_ids:
            raise OrderSubmitError('请选择要结算的商品')

        user = UserInfo.objects.get(id=uid)
        # C-ORD-003：下单前必须存在有效收货地址，不能依赖页面校验
        if not (user.uaddress or '').strip():
            raise OrderSubmitError('请先填写收货地址')

        carts = []
        seen = set()
        for raw_id in cart_ids.split(','):
            raw_id = raw_id.strip()
            if not raw_id:
                # 容忍尾逗号等格式产生的空片段（AI 审查建议 AI-12），不视为非法输入
                continue
            cart_id = _parse_cart_id(raw_id)
            if cart_id is None:
                raise OrderSubmitError('购物车条目编号无效，请重新选择商品')
            if cart_id in seen:
                # C-ORD-009：同一次提交中的重复条目只结算一次
                continue
            seen.add(cart_id)

            # C-ORD-001：只能结算属于当前用户的条目
            cart = CartInfo.objects.filter(
                pk=cart_id, user_id=uid
            ).select_related('goods', 'goods__gtype').first()
            if cart is None:
                raise OrderSubmitError('购物车条目不存在或不属于当前用户')
            # C-INV-001：下单时重新读取并校验商品的有效状态
            if not cart.goods.is_on_sale:
                raise OrderSubmitError('商品“%s”已下架或库存不足' % cart.goods.gtitle)
            carts.append(cart)

        if not carts:
            raise OrderSubmitError('请选择要结算的商品')
    except OrderSubmitError as exc:
        return JsonResponse({'ok': 0, 'msg': str(exc)})

    # ---- 事务内：只做写入 ----
    try:
        with transaction.atomic():
            # C-ORD-005：服务器端用十进制金额重新计算，忽略浏览器提交的总额
            goods_total = sum((cart.goods.gprice * cart.count for cart in carts), Decimal('0.00'))
            order_total = goods_total + TRANS_COST

            order_info = OrderInfo()
            order_info.user_id = int(uid)        # C-ORD-006：关联当前登录用户
            order_info.ototal = order_total      # C-ORD-005：服务器计算的订单总额
            order_info.oaddress = user.uaddress  # C-ORD-003：保存下单时的收货信息快照
            # C-ORD-006：订单编号唯一且不为空。插入冲突时重新生成，避免主键重复覆盖订单。
            for _ in range(5):
                order_info.oid = _new_oid()
                try:
                    with transaction.atomic():
                        order_info.save(force_insert=True)
                    break
                except IntegrityError:
                    continue
            else:
                raise OrderSubmitError('订单号生成失败，请稍后重试')

            for cart in carts:
                goods = cart.goods
                # C-INV-002 / C-INV-004：以条件更新原子扣减库存，
                # 只有库存仍然充足时才会命中，并发下单不会超卖。
                affected = GoodsInfo.objects.filter(
                    pk=goods.pk,
                    isDelete=False,
                    gtype__isDelete=False,
                    gkucun__gte=cart.count,
                ).update(gkucun=F('gkucun') - cart.count)
                if affected != 1:
                    raise OrderSubmitError('商品“%s”库存不足' % goods.gtitle)

                OrderDetailInfo.objects.create(
                    order=order_info,
                    goods=goods,
                    price=goods.gprice,  # C-ORD-007：保存下单时的价格快照
                    count=cart.count,
                )
                cart.delete()  # C-ORD-008：只删除本次已结算的条目
    except OrderSubmitError as exc:
        # C-INV-003 / C-INV-006：业务失败时事务整体回滚，
        # 购物车条目、库存和订单数据都保持失败前的状态。
        return JsonResponse({'ok': 0, 'msg': str(exc)})
    except Exception:
        # C-ORD-010：未预期的异常同样回滚，但不向普通用户展示调试堆栈
        return JsonResponse({'ok': 0, 'msg': '订单提交失败，请稍后重试'})

    return JsonResponse({'ok': 1, 'oid': order_info.oid})


@user_decorator.login
def pay(request, oid):
    """演示支付：将本人订单标记为已支付（C-ORD-012）。

    仅作演示用途，不接入真实支付平台；只允许订单所有者操作，
    用查询集更新以绕开 odate 的 auto_now 副作用（AI 审查发现 AI-16/AI-23）。
    """
    uid = request.session['user_id']
    updated = OrderInfo.objects.filter(oid=oid, user_id=uid, oIsPay=False).update(oIsPay=True)
    if updated == 0:
        order = OrderInfo.objects.filter(oid=oid, user_id=uid).first()
        if order is None:
            return JsonResponse({'ok': 0, 'msg': '订单不存在或不属于当前用户'})
        return JsonResponse({'ok': 0, 'msg': '该订单已支付，请勿重复支付'})
    return JsonResponse({'ok': 1, 'msg': '支付成功（演示环境，未发生真实支付）'})

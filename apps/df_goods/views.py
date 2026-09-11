from django.core.paginator import Paginator
from django.shortcuts import render

from df_user.models import UserInfo
from .models import GoodsInfo, TypeInfo
from df_cart.models import CartInfo
from df_user.models import GoodsBrowser


def index(request):
    # Only render categories that contain actual, non-deleted products.
    nav_styles = ['fruit', 'seafood', 'meet', 'egg', 'vegetables', 'ice']
    sections = []
    for position, category in enumerate(TypeInfo.objects.filter(isDelete=False).order_by('id')):
        products = category.goodsinfo_set.filter(isDelete=False)
        latest = products.order_by('-id')[:4]
        if not latest:
            continue
        sections.append({
            'category': category,
            'latest': latest,
            'hot': products.order_by('-gclick')[:4],
            'style': nav_styles[position % len(nav_styles)],
            'banner': 'images/banner{:02d}.jpg'.format(position + 1),
        })

    cart_num = 0
    # 判断是否存在登录状态
    # if request.session.has_key('user_id'):
    if 'user_id' in request.session:
        user_id = request.session['user_id']
        cart_num = CartInfo.objects.filter(user_id=int(user_id)).count()

    context = {
        'title': '首页',
        'cart_num': cart_num,
        'guest_cart': 1,
        'sections': sections,
    }

    return render(request, 'df_goods/index.html', context)


def good_list(request, tid, pindex, sort):
    # tid：商品种类信息  pindex：商品页码 sort：商品显示分类方式
    typeinfo = TypeInfo.objects.get(pk=int(tid))

    # 根据主键查找当前的商品分类  海鲜或者水果
    news = typeinfo.goodsinfo_set.order_by('-id')[0:2]
    # list.html左侧最新商品推荐
    goods_list = []
    # list中间栏商品显示方式
    cart_num, guest_cart = 0, 0

    try:
        user_id = request.session['user_id']
    except:
        user_id = None
    if user_id:
        guest_cart = 1
        cart_num = CartInfo.objects.filter(user_id=int(user_id)).count()

    if sort == '1':  # 默认最新
        goods_list = GoodsInfo.objects.filter(gtype_id=int(tid)).order_by('-id')
    elif sort == '2':  # 按照价格
        goods_list = GoodsInfo.objects.filter(gtype_id=int(tid)).order_by('-gprice')
    elif sort == '3':  # 按照人气点击量
        goods_list = GoodsInfo.objects.filter(gtype_id=int(tid)).order_by('-gclick')

    # 创建Paginator一个分页对象
    paginator = Paginator(goods_list, 4)
    # 返回Page对象，包含商品信息
    page = paginator.page(int(pindex))
    context = {
        'title': '商品列表',
        'guest_cart': guest_cart,
        'cart_num': cart_num,
        'page': page,
        'paginator': paginator,
        'typeinfo': typeinfo,
        'sort': sort,  # 排序方式
        'news': news,
    }
    return render(request, 'df_goods/list.html', context)


def detail(request, gid):
    good_id = gid
    goods = GoodsInfo.objects.get(pk=int(good_id))
    goods.gclick = goods.gclick + 1  # 商品点击量
    goods.save()

    news = goods.gtype.goodsinfo_set.order_by('-id')[0:2]
    context = {
        'title': goods.gtype.ttitle,
        'guest_cart': 1,
        'cart_num': cart_count(request),
        'goods': goods,
        'news': news,
        'id': good_id,
    }
    response = render(request, 'df_goods/detail.html', context)

    if 'user_id' in request.session:
        user_id = request.session["user_id"]
        try:
            browsed_good = GoodsBrowser.objects.get(user_id=int(user_id), good_id=int(good_id))
        except Exception:
            browsed_good = None
        if browsed_good:
            from datetime import datetime
            browsed_good.browser_time = datetime.now()
            browsed_good.save()
        else:
            GoodsBrowser.objects.create(user_id=int(user_id), good_id=int(good_id))
            browsed_goods = GoodsBrowser.objects.filter(user_id=int(user_id))
            browsed_good_count = browsed_goods.count()
            if browsed_good_count > 5:
                ordered_goods = browsed_goods.order_by("-browser_time")
                for _ in ordered_goods[5:]:
                    _.delete()
    return response


def cart_count(request):
    if 'user_id' in request.session:
        return CartInfo.objects.filter(user_id=request.session['user_id']).count()
    else:
        return 0


def ordinary_search(request):

    from django.db.models import Q

    search_keywords = request.GET.get('q', '')
    pindex = request.GET.get('pindex', 1)
    search_status = 1
    cart_num, guest_cart = 0, 0

    try:
        user_id = request.session['user_id']
    except:
        user_id = None

    if user_id:
        guest_cart = 1
        cart_num = CartInfo.objects.filter(user_id=int(user_id)).count()

    goods_list = GoodsInfo.objects.filter(
        Q(gtitle__icontains=search_keywords) |
        Q(gcontent__icontains=search_keywords) |
        Q(gjianjie__icontains=search_keywords)).order_by("gclick")

    if goods_list.count() == 0:
        # 商品搜索结果为空，返回推荐商品
        search_status = 0
        goods_list = GoodsInfo.objects.all().order_by("gclick")[:4]

    paginator = Paginator(goods_list, 4)
    page = paginator.page(int(pindex))

    context = {
        'title': '搜索列表',
        'search_status': search_status,
        'guest_cart': guest_cart,
        'cart_num': cart_num,
        'page': page,
        'paginator': paginator,
    }
    return render(request, 'df_goods/ordinary_search.html', context)

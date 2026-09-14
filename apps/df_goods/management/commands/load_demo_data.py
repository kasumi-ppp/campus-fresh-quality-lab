from django.core.management.base import BaseCommand
from django.db import transaction

from df_goods.models import GoodsInfo, TypeInfo


DEMO_CATEGORIES = (
    "水果鲜选",
    "海鲜水产",
    "肉禽蛋品",
    "新鲜蔬菜",
    "速冻食品",
    "校园轻食",
)


DEMO_GOODS = (
    ("水果鲜选", "阳光红苹果", "df_goods/goods010.jpg", "3.90", "500g", 86, "清甜脆爽，校园早餐好搭档。", 120),
    ("水果鲜选", "云南蓝莓", "df_goods/goods002.jpg", "12.80", "125g", 72, "颗粒饱满，酸甜平衡。", 80),
    ("水果鲜选", "当季水蜜桃", "df_goods/goods003.jpg", "8.50", "500g", 64, "果肉细嫩，现货供应。", 95),
    ("水果鲜选", "海南小台芒", "df_goods/goods005.jpg", "9.90", "500g", 58, "香气浓郁，适合宿舍分享。", 70),
    ("海鲜水产", "鲜活基围虾", "df_goods/goods012.jpg", "28.00", "500g", 124, "当天分拣，冷链配送到校。", 45),
    ("海鲜水产", "精选白虾仁", "df_goods/goods013.jpg", "22.50", "250g", 98, "去壳虾仁，烹饪方便。", 55),
    ("海鲜水产", "深海鳕鱼排", "df_goods/goods018.jpg", "19.80", "300g", 81, "肉质细嫩，适合蒸煎。", 60),
    ("海鲜水产", "鲜香扇贝肉", "df_goods/goods019.jpg", "16.90", "250g", 66, "鲜香紧实，简单调味即可。", 50),
    ("肉禽蛋品", "黑椒鸡胸肉", "df_goods/goods020.jpg", "13.90", "200g", 142, "低脂高蛋白，运动餐首选。", 100),
    ("肉禽蛋品", "农场鲜鸡蛋", "df_goods/goods021.jpg", "11.80", "10枚", 119, "每日分装，蛋香浓郁。", 150),
    ("肉禽蛋品", "鲜切牛肉片", "df_goods/goods001.jpg", "35.00", "300g", 105, "纹理清晰，火锅和煎炒皆宜。", 42),
    ("肉禽蛋品", "香煎猪里脊", "df_goods/goods003.jpg", "24.90", "400g", 74, "肉质鲜嫩，适合宿舍简餐。", 65),
    ("新鲜蔬菜", "奶油生菜", "df_goods/goods006.jpg", "5.60", "300g", 53, "叶片清脆，沙拉配菜方便。", 90),
    ("新鲜蔬菜", "水果玉米", "df_goods/goods007.jpg", "7.90", "2根", 61, "清甜多汁，蒸煮皆可。", 75),
    ("新鲜蔬菜", "清炒小油菜", "df_goods/goods009.jpg", "4.80", "500g", 49, "鲜嫩爽口，适合快手烹饪。", 110),
    ("新鲜蔬菜", "西红柿组合", "df_goods/goods017.jpg", "6.90", "500g", 67, "自然成熟，酸甜多汁。", 85),
    ("速冻食品", "手工水饺", "df_goods/goods018.jpg", "15.90", "500g", 96, "皮薄馅足，宿舍煮食方便。", 100),
    ("速冻食品", "玉米蔬菜包", "df_goods/goods019.jpg", "12.50", "6只", 62, "清爽馅料，早餐加热即食。", 80),
    ("速冻食品", "香脆鸡米花", "df_goods/goods020.jpg", "18.90", "300g", 88, "外酥里嫩，聚会分享装。", 65),
    ("速冻食品", "芝士披萨饼", "df_goods/goods021.jpg", "21.90", "1张", 77, "芝士丰富，烤箱加热即可。", 50),
    ("校园轻食", "燕麦酸奶杯", "df_goods/goods002.jpg", "10.90", "180g", 132, "低糖轻负担，课间方便食用。", 70),
    ("校园轻食", "坚果能量包", "df_goods/goods005.jpg", "14.90", "120g", 102, "多种坚果组合，学习加餐之选。", 90),
    ("校园轻食", "全麦三明治", "df_goods/goods010.jpg", "9.90", "1份", 115, "全麦面包搭配新鲜蔬菜。", 60),
    ("校园轻食", "鲜榨橙汁", "df_goods/goods013.jpg", "8.90", "300ml", 91, "现榨风味，冰镇后口感更佳。", 75),
)


class Command(BaseCommand):
    help = "加载校园鲜达的脱敏演示分类和商品数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="先移除本命令生成的商品，再重新生成；不会删除用户、地址、购物车或订单",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo_data()

        categories = {}
        for title in DEMO_CATEGORIES:
            category, _ = TypeInfo.objects.update_or_create(
                ttitle=title,
                defaults={"isDelete": False},
            )
            categories[title] = category

        for category_title, title, image, price, unit, clicks, intro, stock in DEMO_GOODS:
            GoodsInfo.objects.update_or_create(
                gtitle=title,
                defaults={
                    "isDelete": False,
                    "gpic": image,
                    "gprice": price,
                    "gunit": unit,
                    "gclick": clicks,
                    "gjianjie": intro,
                    "gkucun": stock,
                    "gcontent": "<p>%s</p>" % intro,
                    "gtype": categories[category_title],
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "已加载校园鲜达演示数据：%d 个分类，%d 个商品。"
                % (len(DEMO_CATEGORIES), len(DEMO_GOODS))
            )
        )

    def _reset_demo_data(self):
        titles = [item[1] for item in DEMO_GOODS]
        GoodsInfo.objects.filter(gtitle__in=titles).delete()
        for category in TypeInfo.objects.filter(ttitle__in=DEMO_CATEGORIES):
            if not category.goodsinfo_set.exists():
                category.delete()

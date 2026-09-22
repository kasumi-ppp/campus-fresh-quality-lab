from django.db import migrations, models


def merge_duplicate_entries(apps, schema_editor):
    """加约束前先合并历史重复条目：数量累加，只保留最早的一条。

    并发加购可能已产生 (用户, 商品) 重复行（AI-17）。直接加唯一约束会失败，
    因此先合并再建约束，保证迁移在任何已有数据上都能执行。
    """
    CartInfo = apps.get_model("df_cart", "CartInfo")
    duplicates = (
        CartInfo.objects.values("user_id", "goods_id")
        .annotate(rows=models.Count("id"))
        .filter(rows__gt=1)
    )
    for group in duplicates:
        entries = list(
            CartInfo.objects.filter(
                user_id=group["user_id"], goods_id=group["goods_id"]
            ).order_by("id")
        )
        keeper, extras = entries[0], entries[1:]
        keeper.count = sum(entry.count for entry in entries)
        keeper.save(update_fields=["count"])
        CartInfo.objects.filter(id__in=[entry.id for entry in extras]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("df_cart", "0003_auto_20190427_2158"),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_entries, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="cartinfo",
            constraint=models.UniqueConstraint(
                fields=("user", "goods"), name="uniq_cart_user_goods"
            ),
        ),
    ]

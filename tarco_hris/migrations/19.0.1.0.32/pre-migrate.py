# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("SELECT to_regclass('public.tarco_hr_asset_type')")
    if not cr.fetchone()[0]:
        return
    cr.execute("""
        SELECT code FROM tarco_hr_asset_type
        WHERE COALESCE(code, '') <> ''
        GROUP BY code
        HAVING COUNT(*) > 1
    """)
    for (code,) in cr.fetchall():
        cr.execute(
            """
            SELECT t.id
              FROM tarco_hr_asset_type t
         LEFT JOIN ir_model_data d
                ON d.model = 'tarco.hr.asset.type' AND d.res_id = t.id
             WHERE t.code = %s
          ORDER BY (d.module = 'tarco_hris') DESC NULLS LAST, t.id
            """,
            [code],
        )
        ids = [row[0] for row in cr.fetchall()]
        keep, drop = ids[0], tuple(ids[1:])
        if not drop:
            continue
        cr.execute("SELECT to_regclass('public.tarco_hr_asset')")
        if cr.fetchone()[0]:
            cr.execute(
                "UPDATE tarco_hr_asset SET type_id = %s WHERE type_id IN %s",
                [keep, drop],
            )
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'tarco.hr.asset.type' AND res_id IN %s",
            [drop],
        )
        cr.execute("DELETE FROM tarco_hr_asset_type WHERE id IN %s", [drop])

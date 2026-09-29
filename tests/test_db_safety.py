# guard ฐานเทสต้องไม่ชนฐานแอป — เทสไฟล์นี้ไม่ต่อ DB เลย รันได้แม้ MariaDB ดับ
import pytest

from repository.db import is_test_db_allowed


@pytest.mark.parametrize(("test_db", "app_db", "allowed"), [
    ("lawfirm_test", "lawfirm-db", True),
    ("lawfirm_test", "lawfirm_test", False),  # ชน DB_NAME ของแอป
    ("lawfirm-db", "other-db", False),  # ชื่อต้องห้ามเด็ดขาด
    ("lawfirm-db", "lawfirm-db", False),
])
def test_test_db_name_must_not_collide_with_app_db(test_db, app_db, allowed):
    assert is_test_db_allowed(test_db, app_db) is allowed

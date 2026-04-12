import unittest
from src.utils import excel_helpers as helpers
from src.parsers import fixed_assets as fa_parser
from datetime import datetime

class TestSrcV2Logic(unittest.TestCase):
    
    def test_depreciation_expansion_logic(self):
        """Xác nhận logic Khấu hao: Dừng đúng lúc và lấy đúng giá trị tháng cuối."""
        fy_months = ['202604', '202605', '202606', '202607']
        monthly_depr = 100.0
        last_month = '202605'
        last_month_depr = 50.0
        
        schedule = fa_parser.expand_depreciation_schedule(monthly_depr, last_month, last_month_depr, fy_months)
        
        self.assertEqual(schedule['202604'], 100.0)  # Trước tháng cuối
        self.assertEqual(schedule['202605'], 50.0)   # Đúng tháng cuối
        self.assertNotIn('202606', schedule)         # Sau tháng cuối (Phải bằng 0/Không tồn tại)

    def test_interest_expansion_logic(self):
        """Xác nhận logic Lãi: Tách tháng 4 và các tháng sau."""
        fy_months = ['202604', '202605', '202606']
        apr_interest = 10.0
        may_interest = 8.0
        last_month = '202605'
        
        schedule = fa_parser.expand_interest_schedule(apr_interest, may_interest, last_month, fy_months)
        
        self.assertEqual(schedule['202604'], 10.0)  # Lãi tháng 4
        self.assertEqual(schedule['202605'], 8.0)   # Lãi tháng 5+
        self.assertNotIn('202606', schedule)         # Sau khi hết hạn

    def test_normalize_period(self):
        """Xác nhận logic chuẩn hóa ngày tháng."""
        self.assertEqual(helpers.normalize_period(datetime(2027, 11, 30)), '202711')
        self.assertEqual(helpers.normalize_period("2027-11-30"), '202711')

if __name__ == '__main__':
    unittest.main()

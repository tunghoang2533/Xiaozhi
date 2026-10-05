import os
import subprocess
import sys
import unittest

from docx import Document
from docx.shared import Cm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_SCRIPT = os.path.join(os.path.dirname(__file__), "gen_bao_cao.py")
DOCX_PATH = os.path.join(ROOT, "BAO_CAO_TTTN_Smart_Desk_Assistant.docx")


class TestBaoCaoGenerator(unittest.TestCase):
    """Kiem chung file bao cao .docx dung chuan trinh bay khoa luan."""

    @classmethod
    def setUpClass(cls):
        res = subprocess.run([sys.executable, GEN_SCRIPT],
                             capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError("gen_bao_cao.py failed:\n" + res.stdout + res.stderr)
        cls.assertTrue = lambda *a, **k: None
        if not os.path.exists(DOCX_PATH):
            raise RuntimeError("Khong tim thay file docx: " + DOCX_PATH)
        cls.doc = Document(DOCX_PATH)

    def _all_text(self):
        parts = [p.text for p in self.doc.paragraphs]
        for tbl in self.doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    parts.append(cell.text)
        return "\n".join(parts)

    def test_page_setup_a4_and_margins(self):
        sec = self.doc.sections[0]
        self.assertAlmostEqual(sec.page_width.cm, 21.0, places=1)
        self.assertAlmostEqual(sec.page_height.cm, 29.7, places=1)
        self.assertAlmostEqual(sec.top_margin.cm, 3.0, places=1)
        self.assertAlmostEqual(sec.bottom_margin.cm, 3.0, places=1)
        self.assertAlmostEqual(sec.left_margin.cm, 3.5, places=1)
        self.assertAlmostEqual(sec.right_margin.cm, 2.0, places=1)

    def test_normal_style_times_new_roman_13_1p5(self):
        normal = self.doc.styles["Normal"]
        self.assertEqual(normal.font.name, "Times New Roman")
        self.assertEqual(round(normal.font.size.pt), 13)
        self.assertAlmostEqual(normal.paragraph_format.line_spacing, 1.5, places=2)

    def test_page_number_field_in_footer(self):
        from docx.oxml.ns import qn
        sec = self.doc.sections[0]
        xml = sec.footer._element.xml
        self.assertIn("PAGE", xml)

    def test_toc_field_present(self):
        xml = self.doc.element.xml
        self.assertIn("TOC", xml)

    def test_required_structure_sections(self):
        text = self._all_text()
        required = [
            "MỤC LỤC",
            "DANH MỤC CÁC KÝ HIỆU, CÁC CHỮ VIẾT TẮT",
            "DANH MỤC CÁC BẢNG",
            "DANH MỤC CÁC HÌNH VẼ, ĐỒ THỊ",
            "MỞ ĐẦU",
            "CHƯƠNG 1. CƠ SỞ LÝ THUYẾT VÀ TỔNG QUAN CÔNG NGHỆ",
            "CHƯƠNG 2. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG",
            "CHƯƠNG 3. XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG",
            "CHƯƠNG 4. KIỂM THỬ VÀ ĐÁNH GIÁ KẾT QUẢ",
            "KẾT LUẬN VÀ KIẾN NGHỊ",
            "TÀI LIỆU THAM KHẢO",
            "PHỤ LỤC",
        ]
        for item in required:
            self.assertIn(item, text, "Thieu muc: " + item)

    def test_figure_placeholders_and_captions(self):
        text = self._all_text()
        self.assertIn("[ CHỖ TRỐNG CHÈN HÌNH / SƠ ĐỒ ]", text)
        # it nhat 19 hinh co caption theo chuong
        import re
        figures = set(re.findall(r"Hình \d+\.\d+", text))
        tables = set(re.findall(r"Bảng \d+\.\d+", text))
        self.assertGreaterEqual(len(figures), 18)
        self.assertGreaterEqual(len(tables), 15)
        # caption hinh phai theo tung chuong 1..4
        for ch in ("1", "2", "3", "4"):
            self.assertTrue(any(f.startswith("Hình %s." % ch) for f in figures))
            self.assertTrue(any(t.startswith("Bảng %s." % ch) for t in tables))

    def test_no_known_typos(self):
        text = self._all_text()
        for bad in ["ngườ i", "thờ i", "rờ i", "lờ i", "củ a", "Bảmg",
                    "phưong án", "băng giọng", "thờOK1"]:
            self.assertNotIn(bad, text, "Con loi chinh ta: " + bad)

    def test_headings_numbering_present(self):
        text = self._all_text()
        for item in ["1.1.", "1.7.", "2.1.", "2.6.", "3.1.", "3.6.", "4.1.", "4.6."]:
            self.assertIn(item, text, "Thieu tieu muc: " + item)


if __name__ == "__main__":
    unittest.main(verbosity=2)

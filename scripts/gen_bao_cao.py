"""
Sinh bao cao thuc tap tot nghiep / khoa luan (file .docx) cho de tai
"HE THONG TRO LY BAN LAM VIEC THONG MINH" theo chuan trinh bay trong
file "huong_dan_trinh bay_ TTTN va KLTN.pdf":
  - Times New Roman co 13, unicode, gian dong 1.5 lines
  - Le tren 3cm, le duoi 3cm, le trai 3.5cm, le phai 2cm, giay A4
  - So trang danh o giua, phia duoi moi trang
  - Danh so bang/hinh gan voi so chuong (Bang 2.1, Hinh 3.4, ...),
    dau de bang ghi tren bang, dau de hinh ghi duoi hinh
  - Cau truc: Bia -> Phu bia -> Loi cam doan -> Loi cam on -> Muc luc ->
    Danh muc viet tat -> Danh muc bang -> Danh muc hinh -> MO DAU ->
    Chuong 1..4 -> KET LUAN VA KIEN NGHI -> TAI LIEU THAM KHAO -> PHU LUC

Cac cho can chen so do / anh duoc de khung trong kem ghi chu noi dung can chen.

Chay:  python3 scripts/gen_bao_cao.py
Ket qua: BAO_CAO_TTTN_Smart_Desk_Assistant.docx (thu muc goc repo)
"""

import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "BAO_CAO_TTTN_Smart_Desk_Assistant.docx")

FONT = "Times New Roman"
GRAY = RGBColor(0x59, 0x59, 0x59)

# =====================================================================
# TIEN ICH DINH DANG MUC THAP
# =====================================================================

def _set_run_font(run, size=13, bold=False, italic=False, color=None, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:cs"), name)


def _set_style_font(style, size=13, bold=False, italic=False, color=RGBColor(0, 0, 0)):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), FONT)
    rfonts.set(qn("w:hAnsi"), FONT)
    rfonts.set(qn("w:cs"), FONT)


def add_field(paragraph, instr, default_text=""):
    """Chen mot truong (field) cua Word, vi du PAGE hoac TOC."""
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = instr
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = default_text
    run2 = OxmlElement("w:r")
    run2.append(txt)
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr_text)
    run._r.append(fld_sep)
    run._r.append(fld_end)
    paragraph._p.append(run2)
    end_run = paragraph.add_run()
    end_run._r.append(fld_end)


def shade_cell(cell, fill="D9D9D9"):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


# =====================================================================
# TIEN ICH DOAN VAN / TIEU DE / BANG / HINH
# =====================================================================

def p(doc, text="", size=13, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
      color=None, space_after=6, line_spacing=1.5, indent_first=0.0):
    par = doc.add_paragraph()
    par.alignment = align
    pf = par.paragraph_format
    pf.space_after = Pt(space_after)
    pf.line_spacing = line_spacing
    if indent_first:
        pf.first_line_indent = Cm(indent_first)
    run = par.add_run(text)
    _set_run_font(run, size=size, bold=bold, italic=italic, color=color)
    return par


def rich_p(doc, segments, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, line_spacing=1.5):
    """segments: list[(text, bold, italic)]"""
    par = doc.add_paragraph()
    par.alignment = align
    par.paragraph_format.space_after = Pt(space_after)
    par.paragraph_format.line_spacing = line_spacing
    for text, bold, italic in segments:
        run = par.add_run(text)
        _set_run_font(run, size=13, bold=bold, italic=italic)
    return par


def bullet(doc, text, bold_prefix=None):
    par = doc.add_paragraph(style="List Bullet")
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par.paragraph_format.line_spacing = 1.5
    par.paragraph_format.space_after = Pt(4)
    if bold_prefix:
        run = par.add_run(bold_prefix)
        _set_run_font(run, size=13, bold=True)
    run = par.add_run(text)
    _set_run_font(run, size=13)
    return par


def heading(doc, text, level=1, center=False, space_before=12):
    par = doc.add_paragraph(style=f"Heading {level}")
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    par.paragraph_format.space_before = Pt(space_before)
    par.paragraph_format.space_after = Pt(6)
    par.paragraph_format.line_spacing = 1.5
    sizes = {1: 14, 2: 13, 3: 13}
    run = par.add_run(text)
    _set_run_font(run, size=sizes.get(level, 13), bold=True,
                  italic=(level == 3), color=RGBColor(0, 0, 0))
    return par


def unnumbered_heading(doc, text, center=True):
    """Tieu de khong so (MO DAU, KET LUAN...) van vao Muc luc."""
    return heading(doc, text, level=1, center=center)


def table_caption(doc, number, title):
    """Dau de cua bang: ghi phia tren bang (theo huong dan)."""
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(8)
    par.paragraph_format.space_after = Pt(4)
    par.paragraph_format.line_spacing = 1.5
    run = par.add_run(number)
    _set_run_font(run, size=13, bold=True)
    run = par.add_run(" " + title)
    _set_run_font(run, size=13)
    return par


def figure_caption(doc, number, title):
    """Dau de cua hinh: ghi phia duoi hinh (theo huong dan)."""
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(10)
    par.paragraph_format.line_spacing = 1.5
    run = par.add_run(number)
    _set_run_font(run, size=13, bold=True)
    run = par.add_run(" " + title)
    _set_run_font(run, size=13)
    return par


def add_table(doc, headers, rows, font_size=12, header_fill="D9D9D9", col_widths=None):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        shade_cell(cell, header_fill)
        par = cell.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.line_spacing = 1.15
        par.paragraph_format.space_after = Pt(2)
        run = par.add_run(h)
        _set_run_font(run, size=font_size, bold=True)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i + 1, j)
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.line_spacing = 1.15
            par.paragraph_format.space_after = Pt(2)
            run = par.add_run(str(val))
            _set_run_font(run, size=font_size)
    if col_widths:
        for j, w in enumerate(col_widths):
            for i in range(len(rows) + 1):
                tbl.cell(i, j).width = Cm(w)
    return tbl


def figure_placeholder(doc, hint, height_cm=5.5):
    """Khung trong (co vien) de nguoi dung chen hinh/so do vao sau."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    row = tbl.rows[0]
    row.height = Cm(height_cm)
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    cell = tbl.cell(0, 0)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    par = cell.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.line_spacing = 1.15
    run = par.add_run("[ CHỖ TRỐNG CHÈN HÌNH / SƠ ĐỒ ]")
    _set_run_font(run, size=13, bold=True, italic=True, color=GRAY)
    if hint:
        par2 = cell.add_paragraph()
        par2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par2.paragraph_format.line_spacing = 1.15
        run2 = par2.add_run("Gợi ý nội dung: " + hint)
        _set_run_font(run2, size=11, italic=True, color=GRAY)
    return tbl


def figure(doc, number, title, hint, height_cm=5.5):
    figure_placeholder(doc, hint, height_cm)
    figure_caption(doc, number, title)


def code_block(doc, lines):
    for line in lines:
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = par.paragraph_format
        pf.line_spacing = 1.0
        pf.space_after = Pt(0)
        pf.left_indent = Cm(0.5)
        run = par.add_run(line)
        _set_run_font(run, size=10, name="Courier New")
    p(doc, "", space_after=4)


def note(doc, text):
    """Ghi chu huong dan (chu nho, xam, nghieng) - xoa truoc khi in."""
    return p(doc, "(Ghi chú - xóa trước khi in: " + text + ")",
             size=11, italic=True, color=GRAY, align=WD_ALIGN_PARAGRAPH.JUSTIFY)


def page_break(doc):
    doc.add_page_break()


# =====================================================================
# KHOI TAO TAI LIEU: KHO GIAY, LE, KIEU CHU, SO TRANG
# =====================================================================

def init_document():
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.0)
    section.bottom_margin = Cm(3.0)
    section.left_margin = Cm(3.5)
    section.right_margin = Cm(2.0)

    # Kieu Normal: Times New Roman 13, gian dong 1.5
    normal = doc.styles["Normal"]
    _set_style_font(normal, size=13, bold=False)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    for lvl in ("Heading 1", "Heading 2", "Heading 3"):
        st = doc.styles[lvl]
        _set_style_font(st, size=13, bold=True, color=RGBColor(0, 0, 0))

    bullet_style = doc.styles["List Bullet"]
    _set_style_font(bullet_style, size=13, bold=False)

    # Trang bia khong danh so; cac trang con lai danh so giua - phia duoi
    section.different_first_page_header_footer = True
    footer = section.footer
    fpar = footer.paragraphs[0]
    fpar.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(fpar, "PAGE", "1")
    for run in fpar.runs:
        _set_run_font(run, size=13)

    return doc


# =====================================================================
# PHAN BIA VA TRANG DAU
# =====================================================================

def build_cover(doc):
    for _ in range(2):
        p(doc, "", space_after=6)
    p(doc, "TRƯỜNG ĐẠI HỌC TÀI NGUYÊN VÀ MÔI TRƯỜNG HÀ NỘI", size=14, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    p(doc, "KHOA: ........................................................", size=13, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    for _ in range(3):
        p(doc, "")
    p(doc, "BÁO CÁO THỰC TẬP TỐT NGHIỆP", size=16, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    note(doc, "Nếu làm khóa luận tốt nghiệp thì sửa dòng trên thành "
              "\u201CKHÓA LUẬN TỐT NGHIỆP\u201D.")
    for _ in range(1):
        p(doc, "")
    p(doc, "XÂY DỰNG HỆ THỐNG TRỢ LÝ BÀN LÀM VIỆC THÔNG MINH "
           "TÍCH HỢP TRỢ LÝ ẢO ĐÀM THOẠI AI TIẾNG VIỆT "
           "TRÊN NỀN TẢNG ESP32-S3", size=14, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16)
    for _ in range(2):
        p(doc, "")
    p(doc, "HỌ VÀ TÊN SINH VIÊN: ........................................................",
      size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    for _ in range(5):
        p(doc, "")
    p(doc, "Hà Nội – Năm 2026", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)


def build_subcover(doc):
    for _ in range(2):
        p(doc, "", space_after=6)
    p(doc, "TRƯỜNG ĐẠI HỌC TÀI NGUYÊN VÀ MÔI TRƯỜNG HÀ NỘI", size=14, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    p(doc, "KHOA: ........................................................", size=13, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    for _ in range(3):
        p(doc, "")
    p(doc, "BÁO CÁO THỰC TẬP TỐT NGHIỆP", size=15, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    p(doc, "")
    p(doc, "XÂY DỰNG HỆ THỐNG TRỢ LÝ BÀN LÀM VIỆC THÔNG MINH "
           "TÍCH HỢP TRỢ LÝ ẢO ĐÀM THOẠI AI TIẾNG VIỆT "
           "TRÊN NỀN TẢNG ESP32-S3", size=14, bold=True,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    p(doc, "")
    info = [
        "Họ và tên sinh viên: ................................................................",
        "Ngành đào tạo: .........................................................................",
        "Mã sinh viên: .............................................................................",
        "Lớp: ............................................................................................",
    ]
    for line in info:
        p(doc, line, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
    for _ in range(2):
        p(doc, "")
    p(doc, "NGƯỜI HƯỚNG DẪN:      1. ........................................................",
      size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    p(doc, "2. ........................................................",
      size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    for _ in range(3):
        p(doc, "")
    p(doc, "Hà Nội – Năm 2026", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)


def build_declaration(doc):
    heading(doc, "LỜI CAM ĐOAN", level=1, center=True)
    p(doc, "Em xin cam đoan báo cáo này là kết quả nghiên cứu, thiết kế và xây dựng "
           "của riêng em dưới sự hướng dẫn của giảng viên hướng dẫn. Các số liệu, kết quả "
           "nêu trong báo cáo là trung thực, được thu thập từ quá trình thực nghiệm trên "
           "mô hình phần cứng thật. Mọi tài liệu tham khảo đều đã được trích dẫn đầy đủ "
           "và liệt kê trong danh mục tài liệu tham khảo.")
    p(doc, "Nếu phát hiện có bất kỳ sự gian lận nào, em xin hoàn toàn chịu trách nhiệm "
           "về nội dung báo cáo của mình trước Khoa và nhà trường.")
    p(doc, "")
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = par.add_run("Hà Nội, ngày ..... tháng ..... năm 2026\n")
    _set_run_font(run, size=13, italic=True)
    run = par.add_run("SINH VIÊN THỰC HIỆN")
    _set_run_font(run, size=13, bold=True)
    p(doc, "")
    p(doc, "")
    p(doc, "Ký, ghi rõ họ tên", size=12, italic=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    page_break(doc)


def build_thanks(doc):
    heading(doc, "LỜI CẢM ƠN", level=1, center=True)
    p(doc, "Trong quá trình thực hiện đề tài, em đã nhận được sự quan tâm, hướng dẫn "
           "tận tình của quý thầy cô trong khoa, đặc biệt là giảng viên hướng dẫn, ngườ"
           "i đã "
           "định hướng nội dung nghiên cứu, góp ý về phương án kỹ thuật cũng như cách "
           "trình bày báo cáo.")
    p(doc, "Em xin chân thành cảm ơn cộng đồng mã nguồn mở Xiaozhi (xiaozhi-esp32) đã "
           "công bố nền tảng firmware trợ lý đàm thoại AI [5], giúp em rút ngắn đáng kể "
           "thời gian phát triển phần mềm cho bo mạch ESP32-S3.")
    p(doc, "Cuối cùng, em xin cảm ơn gia đình và bạn bè đã động viên, hỗ trợ trong "
           "suốt thời gian thực hiện đề tài.")
    page_break(doc)


def build_toc(doc):
    heading(doc, "MỤC LỤC", level=1, center=True)
    par = doc.add_paragraph()
    add_field(par, 'TOC \\o "1-3" \\h \\z \\u',
              "Bấm chuột phải vào đây → Update Field để tạo/cập nhật mục lục tự động.")
    note(doc, "Mục lục được tạo tự động bằng trường TOC của Word: bấm chuột phải vào "
              "vùng mục lục → Update Field → Update entire table để hiển thị đầy đủ "
              "các mục và số trang sau khi soạn xong.")
    page_break(doc)


def build_abbrev(doc):
    heading(doc, "DANH MỤC CÁC KÝ HIỆU, CÁC CHỮ VIẾT TẮT", level=1, center=True)
    rows = [
        ("AI", "Artificial Intelligence (Trí tuệ nhân tạo)"),
        ("AP", "Access Point (Điểm truy cập không dây)"),
        ("API", "Application Programming Interface (Giao diện lập trình ứng dụng)"),
        ("ASR", "Automatic Speech Recognition (Nhận dạng tiếng nói tự động)"),
        ("EEPROM", "Electrically Erasable Programmable Read-Only Memory"),
        ("ESP-NOW", "Giao thức truyền thông không dây điểm-điểm của Espressif"),
        ("GPIO", "General Purpose Input/Output (Chân vào/ra đa dụng)"),
        ("I2S", "Inter-IC Sound (Giao thức âm thanh số liên chip)"),
        ("IoT", "Internet of Things (Internet vạn vật)"),
        ("IP", "Internet Protocol (Giao thức liên mạng)"),
        ("IPS", "In-Plane Switching (Công nghệ tấm nền màn hình LCD)"),
        ("JSON", "JavaScript Object Notation (Định dạng trao đổi dữ liệu)"),
        ("LLM", "Large Language Model (Mô hình ngôn ngữ lớn)"),
        ("LVGL", "Light and Versatile Graphics Library (Thư viện đồ họa nhúng)"),
        ("MCP", "Model Context Protocol (Giao thức ngữ cảnh mô hình)"),
        ("mDNS", "Multicast DNS (Giao thức phân giải tên miền cục bộ)"),
        ("MEMS", "Micro-Electro-Mechanical Systems (Hệ vi cơ điện tử)"),
        ("mmWave", "Millimeter Wave (Sóng milimet)"),
        ("NTP", "Network Time Protocol (Giao thức đồng bộ thời gian mạng)"),
        ("NVS", "Non-Volatile Storage (Bộ nhớ không bay hơi của ESP-IDF)"),
        ("PIR", "Passive Infrared (Cảm biến chuyển động hồng ngoại thụ động)"),
        ("REST", "Representational State Transfer (Kiểu kiến trúc API web)"),
        ("RSSI", "Received Signal Strength Indicator (Chỉ số cường độ tín hiệu thu)"),
        ("SPI", "Serial Peripheral Interface (Giao tiếp ngoại vi nối tiếp)"),
        ("STA", "Station (Chế độ trạm của thiết bị WiFi)"),
        ("TFT", "Thin Film Transistor (Công nghệ màn hình tinh thể lỏng)"),
        ("TTS", "Text-to-Speech (Tổng hợp giọng nói)"),
        ("UART", "Universal Asynchronous Receiver-Transmitter"),
    ]
    tbl = add_table(doc, ["Ký hiệu / Chữ viết tắt", "Nghĩa đầy đủ của ký hiệu, chữ viết tắt"],
                    rows, font_size=12, col_widths=[5.0, 9.5])
    p(doc, "")
    page_break(doc)


def build_lot_lof(doc):
    heading(doc, "DANH MỤC CÁC BẢNG", level=1, center=True)
    tables = [
        ("Bảng 2.1", "Yêu cầu chức năng của hệ thống"),
        ("Bảng 2.2", "Yêu cầu phi chức năng của hệ thống"),
        ("Bảng 2.3", "Danh mục linh kiện phần cứng"),
        ("Bảng 2.4", "Sơ đồ đấu nối chân cụm bo phụ ESP8266"),
        ("Bảng 2.5", "Đấu nối màn hình ST7735 0.96 inch với ESP32-S3"),
        ("Bảng 2.6", "Cấu trúc gói tin lệnh DeskCommandPacket (Master → Slave)"),
        ("Bảng 2.7", "Cấu trúc gói tin trạng thái DeskStatusPacket (Slave → Master)"),
        ("Bảng 2.8", "Bộ công cụ MCP tích hợp trên bo chính ESP32-S3"),
        ("Bảng 3.1", "Danh mục kiểm tra an toàn trước khi cấp nguồn"),
        ("Bảng 3.2", "Các điểm cuối REST API trên máy chủ web của bo phụ ESP8266"),
        ("Bảng 3.3", "Các khóa cấu hình lưu trong phân vùng NVS của ESP32-S3"),
        ("Bảng 3.4", "Kịch bản trình diễn vận hành hệ thống"),
        ("Bảng 4.1", "Ma trận kiểm thử chức năng"),
        ("Bảng 4.2", "Bộ kiểm thử tự động bằng ngôn ngữ Python"),
        ("Bảng 4.3", "Kết quả đo hiệu năng phản hồi của hệ thống"),
        ("Bảng A.1", "Tập lệnh điều khiển qua cổng Serial của bo phụ ESP8266"),
    ]
    tbl = add_table(doc, ["Số hiệu bảng", "Tên bảng", "Trang"],
                    [(a, b, "") for a, b in tables], font_size=12, col_widths=[3.0, 10.0, 1.5])
    note(doc, "Điền số trang của từng bảng sau khi hoàn thiện bố cục.")
    p(doc, "")
    heading(doc, "DANH MỤC CÁC HÌNH VẼ, ĐỒ THỊ", level=1, center=True)
    figures = [
        ("Hình 1.1", "Bo mạch ESP32-S3 (XH-S3E-AI) kết nối màn hình ST7735 0.96 inch"),
        ("Hình 1.2", "Cảm biến radar sóng milimet HLK-LD2410"),
        ("Hình 1.3", "Kiến trúc đường ống đàm thoại AI ASR – LLM – TTS của Xiaozhi"),
        ("Hình 1.4", "Nguyên lý hoạt động của giao thức MCP"),
        ("Hình 2.1", "Kiến trúc tổng thể hệ thống Master – Satellite"),
        ("Hình 2.2", "Luồng dữ liệu chính của hệ thống"),
        ("Hình 2.3", "Sơ đồ khối phần cứng cụm bo chính ESP32-S3"),
        ("Hình 2.4", "Sơ đồ đấu nối cụm bo phụ ESP8266 (LD2410 và Relay)"),
        ("Hình 2.5", "Sơ đồ mắt đấu tải qua tiếp điểm Relay (COM – NO – NC)"),
        ("Hình 2.6", "Bố trí vị trí lắp đặt cảm biến radar tại bàn làm việc"),
        ("Hình 2.7", "Máy trạng thái ba chế độ điều khiển đèn bàn"),
        ("Hình 2.8", "Lưu đồ thuật toán xử lý chính trên bo phụ ESP8266"),
        ("Hình 3.1", "Mạch thực tế cụm bo chính ESP32-S3 sau khi lắp ráp"),
        ("Hình 3.2", "Mạch thực tế cụm bo phụ ESP8266 sau khi lắp ráp"),
        ("Hình 3.3", "Giao diện Web Dashboard chạy trên bo phụ ESP8266"),
        ("Hình 3.4", "Giao diện màn hình hiển thị 0.96 inch trên bo chính"),
        ("Hình 3.5", "Giao diện PC Bridge Dashboard trên máy tính"),
        ("Hình 4.1", "Kết quả chạy bộ kiểm thử tự động"),
        ("Hình 4.2", "Nhật ký cổng Serial trong quá trình vận hành hệ thống"),
    ]
    tbl = add_table(doc, ["Số hiệu hình", "Tên hình", "Trang"],
                    [(a, b, "") for a, b in figures], font_size=12, col_widths=[3.0, 10.0, 1.5])
    note(doc, "Điền số trang của từng hình sau khi chèn đủ hình và hoàn thiện bố cục.")
    page_break(doc)


# =====================================================================
# MO DAU
# =====================================================================

def build_mo_dau(doc):
    unnumbered_heading(doc, "MỞ ĐẦU")

    heading(doc, "1. Lý do chọn đề tài", level=2)
    p(doc, "Trong những năm gần đây, Internet vạn vật (IoT) cùng các mô hình ngôn ngữ "
           "lớn (LLM) đã tạo ra một bước chuyển mạnh mẽ trong cách con người tương tác "
           "với thiết bị điện tử trong gia đình và tại nơi làm việc. Thay vì thao tác "
           "cơ học bằng công tắc, người dùng kỳ vọng môi trường làm việc của mình có "
           "khả năng tự nhận biết sự hiện diện, tự động điều chỉnh thiết bị và hiểu "
           "được mệnh lệnh bằng ngôn ngữ tự nhiên, đặc biệt là tiếng Việt.")
    p(doc, "Bên cạnh đó, thói quen làm việc kéo dài nhiều giờ liền trước máy tính khiến "
           "người lao động thường xuyên quên tắt đèn khi rời bàn (gây lãng phí điện năng) "
           "và ngồi liên tục trong thời gian dài (gây ảnh hưởng xấu đến cột sống, tuần "
           "hoàn và sức khỏe nói chung). Một hệ thống trợ lý bàn làm việc thông minh có "
           "khả năng vừa tự động đóng ngắt chiếu sáng theo sự hiện diện của con người, "
           "vừa theo dõi thời gian ngồi để nhắc nhở vận động, sẽ mang lại giá trị thiết "
           "thực về tiết kiệm năng lượng và chăm sóc sức khỏe người dùng.")
    p(doc, "Xuất phát từ thực tế đó, em lựa chọn đề tài \u201CXây dựng hệ thống trợ lý bàn "
           "làm việc thông minh tích hợp trợ lý ảo đàm thoại AI tiếng Việt trên nền tảng "
           "ESP32-S3\u201D. Đề tài ứng dụng cảm biến radar sóng milimet 24 GHz để phát hiện "
           "hiện diện (kể cả khi người ngồi yên), giao thức không dây nội bộ ESP-NOW có "
           "độ trễ thấp để liên kết hai bo mạch, và nền tảng trợ lý đàm thoại mã nguồn mở "
           "Xiaozhi [5] kết hợp chuẩn giao tiếp công cụ MCP [6] để điều khiển phần cứng "
           "bằng giọng nói tiếng Việt tự nhiên.")

    heading(doc, "2. Mục tiêu của đề tài", level=2)
    p(doc, "Đề tài hướng tới xây dựng hoàn chỉnh một hệ thống trợ lý bàn làm việc "
           "thông minh (Smart Desk Assistant) vận hành ổn định trên phần cứng thật, cụ "
           "thể gồm các mục tiêu sau:")
    bullet(doc, "Tự động bật đèn bàn khi có người ngồi vào làm việc và tự động tắt sau "
                "khoảng thời gian chờ khi người dùng rời bàn, hoàn toàn không chạm "
                "(zero-touch).", bold_prefix="Mục tiêu 1: ")
    bullet(doc, "Điều khiển đèn bàn bằng mệnh lệnh giọng nói tiếng Việt tự nhiên thông "
                "qua trợ lý ảo đàm thoại AI trên bo ESP32-S3, vận dụng chuẩn MCP để mô "
                "hình ngôn ngữ gọi đúng công cụ phần cứng.", bold_prefix="Mục tiêu 2: ")
    bullet(doc, "Theo dõi thời gian ngồi làm việc liên tục theo thời gian thực, cảnh "
                "báo khi ngồi quá 45 phút và trả lời câu hỏi về thời gian đã ngồi.",
           bold_prefix="Mục tiêu 3: ")
    bullet(doc, "Cung cấp Web Dashboard giám sát trạng thái hệ thống và hiệu chỉnh tham "
                "số phần cứng (cực kích relay, logic cảm biến, thời gian chờ) mà không "
                "cần nạp lại chương trình.", bold_prefix="Mục tiêu 4: ")

    heading(doc, "3. Đối tượng và phạm vi nghiên cứu", level=2)
    p(doc, "Đối tượng nghiên cứu: hệ thống nhúng IoT phân tán gồm bo điều khiển trung "
           "tâm ESP32-S3, bo điều khiển ngoại vi ESP8266, cảm biến radar mmWave "
           "HLK-LD2410, module relay và hạ tầng trợ lý đàm thoại AI trên đám mây.")
    p(doc, "Phạm vi nghiên cứu: đề tài tập trung vào không gian bàn làm việc cá nhân "
           "trong nhà với mạng WiFi 2,4 GHz; không đề cập đến quy mô tòa nhà, hệ thống "
           "điều khiển công nghiệp hay các giao thức mạng di động 4G/5G. Phần tải điện "
           "được thử nghiệm với đèn bàn điện áp thấp (5V/12V) trên cùng nguyên lý điều "
           "khiển với tải 220 V thông qua relay, nhằm bảo đảm an toàn khi trình diễn.")

    heading(doc, "4. Phương pháp nghiên cứu", level=2)
    bullet(doc, "Nghiên cứu tài liệu: đọc phân tích datasheet, tài liệu kỹ thuật của "
                "ESP32-S3 [1], ESP8266 [2], cảm biến LD2410 [3], giao thức ESP-NOW [4] "
                "và đặc tả MCP [6].", bold_prefix="Phương pháp 1: ")
    bullet(doc, "Phương pháp phân tích – thiết kế hệ thống: phân tích yêu cầu, đề xuất "
                "kiến trúc Master – Satellite, thiết kế giao thức gói tin và các máy "
                "trạng thái điều khiển.", bold_prefix="Phương pháp 2: ")
    bullet(doc, "Phương pháp thực nghiệm: lắp ráp mạch thật, nạp firmware, đo đạc mức "
                "tín hiệu, kiểm thử chức năng theo ma trận kiểm thử và kiểm thử tự động "
                "bằng các kịch bản Python.", bold_prefix="Phương pháp 3: ")

    heading(doc, "5. Ý nghĩa khoa học và thực tiễn", level=2)
    p(doc, "Về ý nghĩa khoa học: đề tài chứng minh tính khả thi của kiến trúc điện toán "
           "phân tán Master – Satellite kết hợp giao thức ESP-NOW độ trễ thấp với một "
           "mô hình ngôn ngữ lớn trên đám mây, theo đó thiết bị nhúng chi phí thấp vẫn "
           "có thể được điều khiển bằng ngôn ngữ tự nhiên thông qua cơ chế gọi công cụ "
           "(tool calling) của chuẩn MCP.")
    p(doc, "Về ý nghĩa thực tiễn: sản phẩm góp phần tiết kiệm điện năng chiếu sáng, hình "
           "thành thói quen làm việc lành mạnh nhờ tính năng nhắc nhở công thái học, và "
           "có thể mở rộng thành nhiều thiết bị ngoại vi khác (quạt, ổ cắm, rèm cửa) với "
           "chi phí thấp, dễ nhân rộng.")

    heading(doc, "6. Cấu trúc báo cáo", level=2)
    p(doc, "Ngoài phần mở đầu, kết luận và kiến nghị, danh mục tài liệu tham khảo và "
           "phụ lục, nội dung chính của báo cáo được trình bày trong bốn chương:")
    bullet(doc, "Chương 1 – Cơ sở lý thuyết và tổng quan công nghệ.")
    bullet(doc, "Chương 2 – Phân tích và thiết kế hệ thống.")
    bullet(doc, "Chương 3 – Xây dựng và triển khai hệ thống.")
    bullet(doc, "Chương 4 – Kiểm thử và đánh giá kết quả.")
    page_break(doc)


# =====================================================================
# CHUONG 1
# =====================================================================

def build_chuong1(doc):
    heading(doc, "CHƯƠNG 1. CƠ SỞ LÝ THUYẾT VÀ TỔNG QUAN CÔNG NGHỆ", level=1, center=True)

    heading(doc, "1.1. Tổng quan về Internet vạn vật và không gian làm việc thông minh", level=2)
    heading(doc, "1.1.1. Khái niệm Internet vạn vật (IoT)", level=3)
    p(doc, "Internet vạn vật (IoT) là mô hình kết nối trong đó các thiết bị vật lý được "
           "tích hợp cảm biến, bộ xử lý và khả năng truyền thông để thu thập, trao đổi "
           "dữ liệu qua mạng mà không nhất thiết cần sự can thiệp của con người. Một hệ "
           "thống IoT điển hình bao gồm bốn tầng: tầng cảm biến – thiết bị (perception), "
           "tầng truyền thông (network), tầng xử lý – nền tảng (platform) và tầng ứng "
           "dụng (application). Trong đề tài này, tầng cảm biến là radar mmWave "
           "HLK-LD2410; tầng truyền thông gồm WiFi 2,4 GHz, WebSocket và ESP-NOW; tầng "
           "xử lý là hạ tầng trợ lý AI Xiaozhi trên đám mây; tầng ứng dụng là các dịch "
           "vụ chiếu sáng tự động, trợ lý giọng nói và giám sát công thái học.")
    heading(doc, "1.1.2. Không gian làm việc thông minh không chạm (Zero-touch workspace)", level=3)
    p(doc, "Xu hướng không gian làm việc thông minh hiện đại đặt trọng tâm vào việc "
           "loại bỏ tối đa thao tác thủ công của người dùng: thiết bị tự nhận biết ngữ "
           "cảnh (context-aware) và chủ động hành động. Triết lý \u201Czero-touch\u201D (không "
           "chạm) của đề tài được hiện thực hóa bằng cảm biến radar có khả năng phát "
           "hiện cả vi chuyển động và nhịp thở, do đó hệ thống duy trì nhận biết sự hiện "
           "diện ngay cả khi người dùng ngồi yên đọc tài liệu – điều mà cảm biến hồng "
           "ngoại PIR truyền thống không làm được [3]. Ngoài ra, người dùng vẫn có thể "
           "cưỡng chế điều khiển bằng giọng nói tự nhiên thay vì nút nhấn vật lý.")

    heading(doc, "1.2. Nền tảng phần cứng", level=2)
    heading(doc, "1.2.1. Vi điều khiển ESP32-S3 (bo chính)", level=3)
    p(doc, "ESP32-S3 là vi điều khiển tích hợp WiFi 2,4 GHz và Bluetooth LE 5 của "
           "Espressif, sử dụng lõi kép Xtensa LX7 tối đa 240 MHz, hỗ trợ tập lệnh mở "
           "rộng SIMD cho các tác vụ xử lý tín hiệu và mạng nơ-ron [1]. Bo mạch sử dụng "
           "trong đề tài là biến thể XH-S3E-AI (thường gọi \u201CESP32-S3 tím\u201D) tích hợp sẵn "
           "micro MEMS giao tiếp I2S, bộ khuếch đại công suất âm thanh kèm loa và 16 MB "
           "flash, 8 MB PSRAM – rất phù hợp cho ứng dụng trợ lý đàm thoại cần nhớ đệm "
           "âm thanh lớn (Hình 1.1).")
    figure(doc, "Hình 1.1",
           "Bo mạch ESP32-S3 (XH-S3E-AI) kết nối màn hình ST7735 0.96 inch",
           "Chụp ảnh bo mạch ESP32-S3 tím và màn hình 0.96 inch đấu dây thực tế "
           "(có thể dùng file s3timtft096.jpg trong kho mã nguồn).", height_cm=5)
    heading(doc, "1.2.2. Vi điều khiển ESP8266 (bo phụ)", level=3)
    p(doc, "ESP8266 là vi điều khiển WiFi chi phí thấp, xung nhịp 80/160 MHz, phát "
           "triển mạnh trong các ứng dụng IoT dân dụng [2]. Bo NodeMCU ESP8266 được "
           "chọn làm bo điều khiển ngoại vi (slave) đặt dưới gầm bàn, chịu trách nhiệm "
           "đọc tín hiệu cảm biến radar, đóng ngắt relay và trao đổi dữ liệu với bo "
           "chính qua ESP-NOW. Ưu điểm của phương án này là tách biệt hoàn toàn phần "
           "điện áp điều khiển tải khỏi bo xử lý âm thanh – đàm thoại, tăng độ an toàn "
           "và dễ bảo trì.")
    heading(doc, "1.2.3. Cảm biến radar sóng milimet HLK-LD2410", level=3)
    p(doc, "HLK-LD2410 là module cảm biến hiện diện con người làm việc ở băng tần "
           "24 GHz theo công nghệ radar sóng milimet (mmWave), có khả năng phát hiện "
           "cả mục tiêu chuyển động lẫn mục tiêu tĩnh thông qua vi chuyển động của cơ "
           "thể và nhịp thở, với cự ly phát hiện cấu hình được từ 0,5 m đến 5 m và góc "
           "quét khoảng ±60° [3]. Module xuất chân logic OUT ở mức cao khi phát hiện "
           "người, đồng thòi cung cấp cổng UART để cấu hình ngưỡng nhạy theo từng cổng "
           "khoảng cách (distance gate). Trong đề tài, chân OUT được nối trực tiếp vào "
           "chân D2 (GPIO4) của ESP8266, đơn giản hóa phần mềm đọc tín hiệu.")
    figure(doc, "Hình 1.2", "Cảm biến radar sóng milimet HLK-LD2410",
           "Chụp ảnh module HLK-LD2410/LD2410C thực tế (mặt ăng-ten và hàng chân).",
           height_cm=4)
    heading(doc, "1.2.4. Module relay đóng ngắt tải", level=3)
    p(doc, "Module relay 2 kênh có cách ly quang (opto-isolator) được dùng để đóng ngắt "
           "nguồn đèn bàn. Cuộn hút được cấp 5 V, tín hiệu kích nhận từ chân D1 (GPIO5) "
           "của ESP8266; jumper H/L trên module cho phép chọn cực kích mức cao hoặc mức "
           "thấp, và firmware hỗ trợ đảo cực logic tương ứng mà không cần sửa dây. Ba "
           "cọc đầu ra COM – NO – NC của relay cho phép mắt tải theo kiểu thường mở "
           "(NO): khi relay được kích, mạch tải khép kín và đèn sáng.")
    heading(doc, "1.2.5. Màn hình TFT IPS 0.96 inch ST7735", level=3)
    p(doc, "Màn hình hiển thị trạng thái của hệ thống là module TFT IPS 0,96 inch độ "
           "phân giải 80×160 điểm ảnh, điều khiển bởi chip ST7735 qua giao tiếp SPI "
           "(chân dữ liệu MOSI, xung nhịp SCK, chọn lệnh/dữ liệu DC, reset RST). Màn "
           "hình được ghép nối với ESP32-S3 ở các chân GPIO 41, 42, 43, 44 theo cấu "
           "hình lưu trong bộ nhớ NVS của firmware. Giao diện đồ họa được dựng trên "
           "thư viện nhúng LVGL [9], hiển thị biểu tượng cảm xúc, trạng thái kết nối "
           "và đồng hồ thời gian thực.")

    heading(doc, "1.3. Giao thức truyền thông", level=2)
    heading(doc, "1.3.1. WiFi 2,4 GHz và WebSocket", level=3)
    p(doc, "Bo chính ESP32-S3 kết nối Internet qua WiFi 2,4 GHz và duy trì kênh "
           "WebSocket (hoặc MQTT kèm UDP tùy cấu hình) tới máy chủ Xiaozhi để truyền "
           "luồng âm thanh hai chiều. WebSocket cho phép kết nối song công, độ trễ "
           "thấp, phù hợp với dữ liệu thoại thời gian thực [5].")
    heading(doc, "1.3.2. Giao thức ESP-NOW", level=3)
    p(doc, "ESP-NOW là giao thức truyền thông không dây điểm-điểm do Espressif phát "
           "triển, cho phép các thiết bị ESP trao đổi gói tin tối đa 250 byte trực tiếp "
           "qua sóng 2,4 GHz mà không cần bắt tay kết nối hay router trung gian [4]. "
           "Nhờ bỏ qua toàn bộ ngăn xếp liên kết, ESP-NOW đạt độ trễ dưới 5 ms – phù "
           "hợp điều khiển thời gian thực giữa bo chính và bo phụ. Một ràng buộc quan "
           "trọng của giao thức là hai bên phải hoạt động trên cùng kênh WiFi; vấn đề "
           "đồng bộ kênh và giải pháp của đề tài được trình bày tại mục 2.4.3.")

    heading(doc, "1.4. Trợ lý ảo đàm thoại AI Xiaozhi trên ESP32", level=2)
    heading(doc, "1.4.1. Kiến trúc đường ống ASR – LLM – TTS", level=3)
    p(doc, "Xiaozhi là firmware mã nguồn mở dành cho các bo ESP32 hoạt động như một "
           "chatbot đàm thoại bằng giọng nói [5]. Kiến trúc xử lý gồm ba khâu chính: "
           "(i) nhận dạng tiếng nói tự động (ASR) chuyển lời nói của người dùng thành "
           "văn bản; (ii) mô hình ngôn ngữ lớn (LLM, ví dụ Qwen, DeepSeek) suy luận ý "
           "định và sinh câu trả lời; (iii) tổng hợp giọng nói (TTS) chuyển văn bản trả "
           "lời thành âm thanh phát ra loa của thiết bị (Hình 1.3). Luồng âm thanh "
           "được nén bằng codec Opus nhằm tiết kiệm băng thông trước khi truyền qua "
           "Internet, và thiết bị hỗ trợ đánh thức bằng từ khóa (wake-word) ngoại tuyến "
           "nhờ thư viện ESP-SR [7].")
    figure(doc, "Hình 1.3", "Kiến trúc đường ống đàm thoại AI ASR – LLM – TTS của Xiaozhi",
           "Sơ đồ: Mic I2S → Opus → WebSocket → ASR → LLM → công cụ MCP → TTS → Loa.",
           height_cm=5)
    heading(doc, "1.4.2. Tương tác phần cứng qua chuẩn MCP", level=3)
    p(doc, "Điểm đặc biệt của Xiaozhi là tích hợp chuẩn giao tiếp công cụ MCP (Model "
           "Context Protocol) ngay trên thiết bị: firmware đăng ký danh sách công cụ "
           "(tool) cùng mô tả và tham số, máy chủ chuyển tiếp danh sách này tới mô hình "
           "ngôn ngữ; khi người dùng ra lệnh bằng ngôn ngữ tự nhiên, mô hình chọn công "
           "cụ phù hợp và phát lệnh gọi công cụ (tool call) về thiết bị để thực thi "
           "[5][6]. Nhờ đó việc \u201Cdạy\u201D trợ lý AI điều khiển một thiết bị mới chỉ đơn "
           "giản là đăng ký thêm công cụ mới trong firmware.")

    heading(doc, "1.5. Giao thức MCP (Model Context Protocol)", level=2)
    heading(doc, "1.5.1. Khái niệm", level=3)
    p(doc, "MCP là giao thức mở nhằm chuẩn hóa cách các ứng dụng cung cấp ngữ cảnh, công "
           "cụ và dữ liệu cho mô hình ngôn ngữ lớn [6]. Thay vì mỗi nhà phát triển tự "
           "định nghĩa cách gọi hàm riêng, MCP quy định khung trao đổi thống nhất: bên "
           "cung cấp (server) công bố công cụ dưới dạng tên, mô tả chức năng bằng ngôn "
           "ngữ tự nhiên và lược đồ tham số JSON; mô hình bên khách (client) chọn công "
           "cụ theo ngữ cảnh hội thoại và nhận kết quả trả về (Hình 1.4).")
    figure(doc, "Hình 1.4", "Nguyên lý hoạt động của giao thức MCP",
           "Sơ đồ tuần tự: thiết bị đăng ký tools → LLM chọn tool → thiết bị thực thi "
           "→ trả kết quả → LLM sinh câu thoại phản hồi.", height_cm=5)
    heading(doc, "1.5.2. Vai trò MCP trong điều khiển phần cứng", level=3)
    p(doc, "Trong hệ thống của đề tài, các công cụ MCP ánh xạ trực tiếp tới hành động "
           "phần cứng: bật/tắt đèn, truy vấn trạng thái đèn, chuyển chế độ tự động. Khi "
           "người dùng nói \u201Ctrợ lý ơi, tắt đèn bàn giúp tôi\u201D, mô hình ngôn ngữ gọi "
           "công cụ self.lamp.turn_off; firmware bo chính nhận lệnh, phát gói tin "
           "ESP-NOW sang bo phụ và bo phụ thực thi ngay lập tức, đồng thòi trợ lý phản "
           "hồi bằng giọng nói \u201CĐã tắt đèn bàn\u201D. Danh sách công cụ chi tiết được "
           "thiết kế tại mục 2.5.4.")

    heading(doc, "1.6. Các công nghệ phần mềm nền tảng", level=2)
    heading(doc, "1.6.1. ESP-IDF và FreeRTOS trên bo chính", level=3)
    p(doc, "Firmware bo chính được xây dựng trên khung phát triển ESP-IDF phiên bản 6.x "
           "[8] với hệ điều hành thời gian thực FreeRTOS [10]. Kiến trúc đa tác vụ cho "
           "phép các luồng âm thanh, mạng, hiển thị và điều khiển chạy song song: tác vụ "
           "nhận – phát âm thanh mã hóa Opus, tác vụ giao thức WebSocket/MQTT, tác vụ "
           "hiển thị LVGL và các tác vụ nền như bộ đếm thời gian ngồi.")
    heading(doc, "1.6.2. Arduino core trên bo phụ", level=3)
    p(doc, "Firmware bo phụ ESP8266 được viết bằng môi trường Arduino (C++) [11], tận "
           "dụng các thư viện sẵn có: ESP8266WiFi cho kết nối mạng, espnow cho giao "
           "thức ESP-NOW, EEPROM cho lưu trữ cấu hình, ESP8266WebServer và ESP8266mDNS "
           "cho máy chủ web nội bộ. Phương án này giúp hiệu chỉnh nhanh, dễ mở rộng mã "
           "nguồn trong khuôn khổ đề tài.")
    heading(doc, "1.6.3. Bộ nhớ cấu hình NVS và phân vùng flash", level=3)
    p(doc, "ESP-IDF cung cấp cơ chế lưu trữ khóa – giá trị trong vùng flash không bay "
           "hơi (NVS) [8]. Trên bo ESP32-S3 của đề tài, phân vùng NVS 16 KB tại địa chỉ "
           "0x9000 chứa cấu hình WiFi (khóa wifi.ssid, wifi.password), cấu hình màn "
           "hình (driver, độ phân giải, offset, chân SPI) và cấu hình chân đèn "
           "(p_lamp). Đề tài xây dựng bộ công cụ Python đọc – sửa trực tiếp ảnh nhị "
           "phân phân vùng NVS (16 384 byte, định dạng trang 4 096 byte kèm CRC32) để "
           "nạp cấu hình mà không cần biên dịch lại firmware.")

    heading(doc, "1.7. Tổng kết chương 1", level=2)
    p(doc, "Chương 1 đã trình bày cơ sở lý thuyết về IoT và không gian làm việc không "
           "chạm, phân tích các nền tảng phần cứng (ESP32-S3, ESP8266, radar LD2410, "
           "relay, màn hình ST7735), các giao thức truyền thông (WiFi, WebSocket, "
           "ESP-NOW) cũng như kiến trúc trợ lý đàm thoại AI Xiaozhi và chuẩn công cụ "
           "MCP. Đây là nền tảng để chương 2 tiến hành phân tích yêu cầu và thiết kế "
           "chi tiết hệ thống.")
    page_break(doc)


# =====================================================================
# CHUONG 2
# =====================================================================

def build_chuong2(doc):
    heading(doc, "CHƯƠNG 2. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG", level=1, center=True)

    heading(doc, "2.1. Phân tích yêu cầu", level=2)
    heading(doc, "2.1.1. Yêu cầu chức năng", level=3)
    p(doc, "Từ mục tiêu đề tài, các yêu cầu chức năng được xác định như Bảng 2.1.")
    table_caption(doc, "Bảng 2.1", "Yêu cầu chức năng của hệ thống")
    add_table(doc,
              ["Mã yêu cầu", "Tên chức năng", "Mô tả chi tiết"],
              [
                  ("FR-01", "Chiếu sáng tự động theo hiện diện",
                   "Cảm biến radar phát hiện người ngồi vào bàn thì bật đèn ngay lập "
                   "tức; khi vắng mặt quá thời gian chờ cấu hình thì tự động tắt đèn."),
                  ("FR-02", "Điều khiển đèn bằng giọng nói tiếng Việt",
                   "Người dùng ra lệnh tự nhiên (ví dụ \u201Cbật đèn bàn\u201D, \u201Ctắt đèn "
                   "giúp tôi\u201D); trợ lý AI phản hồi bằng giọng nói và thực thi qua MCP."),
                  ("FR-03", "Ưu tiên quyền người dùng (override)",
                   "Lệnh giọng nói/web cưỡng chế trạng thái đèn, ghi đè quyết định cảm "
                   "biến; tự khôi phục chế độ tự động sau khi rời bàn hẳn."),
                  ("FR-04", "Theo dõi thời gian ngồi",
                   "Đếm thời gian ngồi liên tục theo giây; đồng bộ số liệu về bo chính "
                   "và dashboard mỗi giây."),
                  ("FR-05", "Cảnh báo công thái học",
                   "Khi ngồi liên tục trên 45 phút, hệ thống cảnh báo trên dashboard và "
                   "trợ lý có thể phát nhắc nhở bằng âm thanh."),
                  ("FR-06", "Giám sát và hiệu chỉnh qua web",
                   "Dashboard hiển thị trạng thái đèn, cảm biến, kênh sóng; cho phép đổi "
                   "cực kích relay, logic radar, thời gian chờ, cấu hình WiFi."),
              ], font_size=12)
    heading(doc, "2.1.2. Yêu cầu phi chức năng", level=3)
    table_caption(doc, "Bảng 2.2", "Yêu cầu phi chức năng của hệ thống")
    add_table(doc,
              ["Mã", "Nhóm yêu cầu", "Chỉ tiêu cụ thể"],
              [
                  ("NFR-01", "Thời gian thực",
                   "Độ trễ truyền nội bộ ESP-NOW dưới 5 ms; đèn bật trong 100 ms kể từ "
                   "khi cảm biến xác nhận có người."),
                  ("NFR-02", "Độ tin cậy",
                   "Chống chập chờn tín hiệu radar bằng khử nhiễu 100 ms; gói tin lệnh "
                   "phát burst nhiều lần để tránh rớt gói."),
                  ("NFR-03", "An toàn",
                   "Tách cụm điều khiển tải khỏi cụm đàm thoại; khuyến nghị demo với tải "
                   "điện áp thấp 5V/12V thay vì 220 V."),
                  ("NFR-04", "Dễ hiệu chỉnh",
                   "Mọi tham số phần cứng lưu trong EEPROM/NVS, thay đổi qua web hoặc "
                   "Serial mà không cần nạp lại chương trình."),
                  ("NFR-05", "Trải nghiệm tự nhiên",
                   "Hệ thống hoạt động không chạm; chỉ tương tác giọng nói khi người "
                   "dùng chủ động ra lệnh."),
              ], font_size=12)

    heading(doc, "2.2. Kiến trúc tổng thể hệ thống", level=2)
    heading(doc, "2.2.1. Mô hình phân tán Master – Satellite", level=3)
    p(doc, "Hệ thống được thiết kế theo mô hình điện toán phân tán Master – Satellite "
           "(chính – phụ) như Hình 2.1: bo chính ESP32-S3 đặt trên mặt bàn đảm nhiệm "
           "đàm thoại AI và hiển thị; bo phụ ESP8266 đặt dưới gầm bàn tại hộp kỹ thuật "
           "điều khiển cảm biến và relay. Hai bo trao đổi hoàn toàn không dây qua "
           "ESP-NOW, còn bo chính kết nối đám mây Xiaozhi qua WiFi Internet. Kiến trúc "
           "này mang lại ba lợ ích: (i) cụm điện điều khiển tải được cách ly vật lý với "
           "người dùng; (ii) bo chính giải phóng tài nguyên cho xử lý âm thanh thời "
           "gian thực; (iii) dễ mở rộng thêm nhiều bo phụ (quạt, ổ cắm) về sau.")
    figure(doc, "Hình 2.1", "Kiến trúc tổng thể hệ thống Master – Satellite",
           "Vẽ sơ đồ gồm: đám mây Xiaozhi (ASR/LLM/TTS) ⇄ bo chính ESP32-S3 "
           "(Mic, Loa, LCD) ⇄ [ESP-NOW] ⇄ bo phụ ESP8266 ⇄ Radar LD2410, Relay, Đèn.",
           height_cm=6.5)
    heading(doc, "2.2.2. Luồng dữ liệu chính", level=3)
    p(doc, "Hệ thống có hai luồng dữ liệu chính minh họa ở Hình 2.2. Luồng điều khiển: "
           "giọng nói người dùng → ASR → LLM chọn công cụ MCP → firmware bo chính phát "
           "gói tin lệnh (2 byte) qua ESP-NOW → bo phụ đóng/ngắt relay. Luồng giám sát: "
           "bo phụ liên tục đọc cảm biến, cập nhật bộ đếm thời gian ngồi và phát "
           "broadcast gói tin trạng thái (7 byte) mỗi giây cho bo chính, đồng thòi cung "
           "cấp dữ liệu JSON cho Web Dashboard cục bộ mỗi 1,5 giây.")
    figure(doc, "Hình 2.2", "Luồng dữ liệu chính của hệ thống",
           "Vẽ hai luồng mũi tên: luồng lệnh giọng nói đi xuống tới relay; luồng "
           "telemetry trạng thái đi ngược về bo chính và dashboard.", height_cm=5.5)

    heading(doc, "2.3. Thiết kế phần cứng", level=2)
    heading(doc, "2.3.1. Danh mục linh kiện", level=3)
    p(doc, "Toàn bộ linh kiện của hệ thống được thống kê tại Bảng 2.3.")
    table_caption(doc, "Bảng 2.3", "Danh mục linh kiện phần cứng")
    add_table(doc,
              ["Thiết bị", "Vai trò", "Vị trí lắp đặt", "Thông số chính"],
              [
                  ("ESP32-S3 (XH-S3E-AI, bo tím)", "Bo điều khiển trung tâm (Master)",
                   "Mặt bàn", "Lõi kép 240 MHz, 16 MB flash, 8 MB PSRAM, mic + loa I2S onboard"),
                  ("NodeMCU ESP8266", "Bo điều khiển ngoại vi (Slave)",
                   "Gầm bàn", "80 MHz, WiFi 2,4 GHz, hỗ trợ ESP-NOW"),
                  ("HLK-LD2410 (LD2410C)", "Cảm biến hiện diện mmWave",
                   "Mép bàn, hướng vào ghế ngồi", "24 GHz, phát hiện người tĩnh/động, 0,5–5 m, góc ±60°"),
                  ("Module Relay 2 kênh (cách ly quang)", "Đóng ngắt nguồn đèn",
                   "Hộp kỹ thuật gầm bàn", "Tải 10 A/250 VAC, kích H/L tùy chọn (dùng kênh 1)"),
                  ("Màn hình TFT IPS 0,96 inch", "Hiển thị trạng thái",
                   "Gắn cùng bo chính", "ST7735, 80×160 điểm ảnh, giao tiếp SPI"),
                  ("Đèn bàn LED 5V/12V", "Tải demo an toàn",
                   "Mặt bàn", "Cùng nguyên lý điều khiển với đèn 220 V qua relay"),
              ], font_size=12)
    heading(doc, "2.3.2. Sơ đồ khối phần cứng cụm bo chính", level=3)
    p(doc, "Cụm bo chính gồm ESP32-S3 và các ngoại vi tích hợp onboard (micro MEMS, bộ "
           "khuếch đại + loa qua giao tiếp I2S) cùng màn hình SPI bên ngoài. Sơ đồ khối "
           "được trình bày tại Hình 2.3.")
    figure(doc, "Hình 2.3", "Sơ đồ khối phần cứng cụm bo chính ESP32-S3",
           "Vẽ khối ESP32-S3 ở trung tâm, nối tới: Mic I2S, IC khuếch đại + Loa, "
           "Màn hình ST7735 (SPI GPIO 41–44), cổng USB-C 5 V, anten WiFi.", height_cm=5.5)
    heading(doc, "2.3.3. Sơ đồ đấu nối cụm bo phụ", level=3)
    p(doc, "Cụm bo phụ cần đấu dây nhiều nhất của hệ thống, gồm cảm biến radar LD2410 "
           "và module relay. Chân nối chi tiết thể hiện tại Bảng 2.4 và sơ đồ đấu nối "
           "tại Hình 2.4.")
    table_caption(doc, "Bảng 2.4", "Sơ đồ đấu nối chân cụm bo phụ ESP8266")
    add_table(doc,
              ["Linh kiện", "Chân linh kiện", "Chân ESP8266", "Chức năng"],
              [
                  ("LD2410", "VCC", "VIN/VU (5 V)", "Nguồn 5 V trực tiếp từ USB (dòng đỉnh 150–200 mA, không dùng chân 3V3)"),
                  ("LD2410", "GND", "GND", "Nối mass chung"),
                  ("LD2410", "OUT", "D2 (GPIO4)", "Tín hiệu logic: HIGH = có người, LOW = trống"),
                  ("Relay", "DC+", "VIN/VU (5 V)", "Nguồn nuôi cuộn hút"),
                  ("Relay", "DC−", "GND", "Nối mass chung"),
                  ("Relay", "IN1", "D1 (GPIO5)", "Tín hiệu kích kênh 1 (cực H/L tùy jumper)"),
                  ("Relay", "IN2", "Bỏ trống", "Kênh 2 dự phòng"),
              ], font_size=12)
    figure(doc, "Hình 2.4", "Sơ đồ đấu nối cụm bo phụ ESP8266 (LD2410 và Relay)",
           "Vẽ sơ đồ dây: NodeMCU ESP8266 nối LD2410 (VCC-VIN, GND, OUT-D2) và "
           "relay (DC+-VIN, DC−-GND, IN1-D1); kèm ghi chú nguồn 5 V.", height_cm=6)
    p(doc, "Về phía tải, ba cọc của relay được mắt theo kiểu thường mở như Hình 2.5: dây "
           "dương nguồn đèn đi vào cọc COM, cọc NO nối tới cực dương của đèn, cọc NC bỏ "
           "trống; dây âm đi thẳng tới cực âm đèn. Khi relay được kích, tiếp điểm COM–NO "
           "khép kín và đèn sáng.")
    figure(doc, "Hình 2.5", "Sơ đồ mắt đấu tải qua tiếp điểm Relay (COM – NO – NC)",
           "Vẽ ký hiệu relay 3 cọc: nguồn → COM, NO → cực dương đèn, NC bỏ trống, "
           "dây âm → cực âm đèn.", height_cm=4.5)
    heading(doc, "2.3.4. Đấu nối màn hình ST7735 với bo chính", level=3)
    p(doc, "Màn hình 0,96 inch được đấu với ESP32-S3 theo Bảng 2.5; cấu hình đã được "
           "lưu sẵn trong NVS (driver ST7735, offset X = 26, đảo màu IPS) nên chỉ cần "
           "cắm đúng chân là màn hình hoạt động.")
    table_caption(doc, "Bảng 2.5", "Đấu nối màn hình ST7735 0.96 inch với ESP32-S3")
    add_table(doc,
              ["Chân màn hình", "Chân ESP32-S3", "Chức năng"],
              [
                  ("VCC", "3V3", "Nguồn 3,3 V cho màn hình"),
                  ("GND", "GND", "Nối mass chung"),
                  ("SCL/SCK", "GPIO 42", "Xung nhịp SPI Clock"),
                  ("SDA/MOSI", "GPIO 41", "Đường dữ liệu SPI MOSI"),
                  ("RES/RST", "GPIO 44", "Reset màn hình"),
                  ("DC", "GPIO 43", "Chọn lệnh/dữ liệu"),
                  ("CS", "GND hoặc bỏ trống", "Chip Select (tùy loại module)"),
                  ("BLK/BL", "3V3", "Bật đèn nền (nối mức cao để luôn sáng)"),
              ], font_size=12)
    heading(doc, "2.3.5. Phân tích lựa chọn phương án phần cứng", level=3)
    p(doc, "Trong quá trình thiết kế, một số linh kiện ban đầu đã được cân nhắc rồ i loại "
           "bỏ nhằm tối ưu độ tin cậy và tính thẩm mỹ của mô hình:")
    bullet(doc, "Cảm biến quang trở (LDR) bị loại vì tạo vòng lặp phản xạ ánh sáng: khi "
                "đèn sáng chiếu ngược vào cảm biến, hệ thống tưởng trời sáng và tự tắt "
                "đèn, gây chớp tắt liên tục. Đề tài thay bằng logic điều kiện theo thời "
                "gian thực (đồng hồ NTP) kết hợp cảm biến hiện diện.",
           bold_prefix="Loại bỏ LDR: ")
    bullet(doc, "Phím cảm ứng TTP223 bị loại để giữ trọn triết lý zero-touch (không "
                "chạm) và loại bỏ dây nối ngoài, tránh lỗi tiếp xúc khi trình diễn; vai "
                "trò điều khiển thủ công được thay bằng lệnh giọng nói.",
           bold_prefix="Loại bỏ TTP223: ")
    bullet(doc, "Phần điều khiển quạt và quét BLE được cắt giảm để đơn giản kiến trúc, "
                "tập trung vào hai trục chính: chiếu sáng tự động và trợ lý giọng nói.",
           bold_prefix="Cắt giảm ngoại vi phụ: ")
    p(doc, "Về ngân sách nguồn: cảm biến LD2410 khi phát sóng quét 24 GHz tiêu thụ dòng "
           "đỉnh 150–200 mA, vượt khả năng cấp của bộ hạ áp 3,3 V trên bo NodeMCU; do đó "
           "cảm biến và relay bắt buộc lấy nguồn 5 V từ chân VIN/VU để tránh sụt áp gây "
           "khởi động lại liên tục.")
    heading(doc, "2.3.6. Bố trí lắp đặt và căn chỉnh cảm biến radar", level=3)
    p(doc, "Sóng radar 24 GHz xuyên qua được vật liệu phi kim (gỗ, nhựa, mica) nên "
           "cảm biến được dán cố định dưới mép bàn phía trước, mặt ăng-ten hướng vào "
           "vùng ngực/bụng của người ngồi, cự ly lý tưởng 0,5–1,2 m (Hình 2.6). Cần "
           "tránh vật kim loại che chắn mặt cảm biến, tránh hướng ăng-ten vào quạt quay "
           "hoặc rèm cửa lay động vì sinh chuyển động giả khiến hệ thống không bao giờ "
           "tắt đèn.")
    figure(doc, "Hình 2.6", "Bố trí vị trí lắp đặt cảm biến radar tại bàn làm việc",
           "Vẽ mặt cắt bàn – ghế: radar gắn dưới mặt bàn, nón quét 60° hướng vào "
           "ghế; kích thước cự ly 0,5–1,2 m.", height_cm=5)

    heading(doc, "2.4. Thiết kế giao thức truyền thông ESP-NOW", level=2)
    heading(doc, "2.4.1. Gói tin lệnh DeskCommandPacket", level=3)
    p(doc, "Để tối ưu tốc độ và loại bỏ độ trễ phân tích chuỗi, hai bo trao đổi dữ liệu "
           "dưới dạng cấu trúc nhị phân đóng gói (packed struct) cố định. Gói tin lệnh "
           "từ bo chính sang bo phụ dài 2 byte như Bảng 2.6.")
    table_caption(doc, "Bảng 2.6", "Cấu trúc gói tin lệnh DeskCommandPacket (Master → Slave)")
    add_table(doc,
              ["Trường", "Kiểu dữ liệu", "Kích thước", "Ý nghĩa"],
              [
                  ("magic", "uint8_t", "1 byte", "Mã nhận diện gói tin hợp lệ, cố định 0x5A"),
                  ("cmd", "uint8_t", "1 byte",
                   "0 = cưỡng chế TẮT đèn; 1 = cưỡng chế BẬT đèn; 2 = trả về chế độ TỰ ĐỘNG"),
              ], font_size=12)
    heading(doc, "2.4.2. Gói tin trạng thái DeskStatusPacket", level=3)
    p(doc, "Gói tin trạng thái dài 7 byte, do bo phụ phát broadcast mỗi giây hoặc ngay "
           "khi có thay đổi trạng thái người ngồi (Bảng 2.7).")
    table_caption(doc, "Bảng 2.7", "Cấu trúc gói tin trạng thái DeskStatusPacket (Slave → Master)")
    add_table(doc,
              ["Trường", "Kiểu dữ liệu", "Kích thước", "Ý nghĩa"],
              [
                  ("magic", "uint8_t", "1 byte", "Mã nhận diện gói tin, cố định 0xA5"),
                  ("is_sitting", "uint8_t", "1 byte", "1 = đang ngồi tại bàn; 0 = đã rời bàn"),
                  ("lamp_state", "uint8_t", "1 byte", "1 = đèn đang sáng; 0 = đèn đang tắt"),
                  ("sitting_time_sec", "uint32_t", "4 byte",
                   "Thời gian ngồi liên tục hiện tại (đơn vị giây)"),
              ], font_size=12)
    heading(doc, "2.4.3. Cơ chế đồng bộ kênh WiFi và phát tin đáng tin cậy", level=3)
    p(doc, "Vấn đề kỹ thuật then chốt khi dùng ESP-NOW song song với WiFi Internet là "
           "ràng buộc cùng kênh: khi bo chính ESP32-S3 kết nối router, kênh WiFi của nó "
           "do router chỉ định; nếu bo phụ phát lệch kênh thì hai bên không nghe thấy "
           "nhau. Đề tài giải quyết bằng cơ chế đồng bộ kênh tự động trên bo phụ: khi "
           "khởi động, ESP8266 quét toàn bộ mạng 2,4 GHz xung quanh, tìm SSID khớp với "
           "danh sách cấu hình (EEPROM hoặc danh sách mạng quen thuộc), lấy kênh của "
           "mạng đó làm kênh hoạt động và kết nối router. Điểm phát sóng SoftAP của bo "
           "phụ (\u201CSmartDesk-Assistant\u201D) cũng theo kênh này nên Web Dashboard luôn truy "
           "cập được. Ngoài ra, ở phía bo chính, mỗi lệnh điều khiển được phát burst 6 "
           "gói cách nhau 15 ms nhằm triệt tiêu xác suất rớt gói đơn lẻ, còn chế độ "
           "tiết kiệm nguồn vô tuyến (modem sleep) được tắt để bảo đảm máy phát luôn "
           "sẵn sàng.")

    heading(doc, "2.5. Thiết kế phần mềm", level=2)
    heading(doc, "2.5.1. Kiến trúc phần mềm tổng thể", level=2 + 1)
    p(doc, "Phần mềm hệ thống gồm ba vùng: (i) firmware bo phụ ESP8266 viết bằng Arduino "
           "C++ chịu trách nhiệm cảm biến – relay – web server nội bộ; (ii) firmware bo "
           "chính ESP32-S3 trên ESP-IDF/FreeRTOS kế thừa nền tảng Xiaozhi, bổ sung lớp "
           "điều khiển đèn LampController đăng ký công cụ MCP; (iii) bộ công cụ trên máy "
           "tính bằng Python gồm PC Bridge Dashboard và các kịch bản cấu hình NVS, kiểm "
           "thử tự động.")
    heading(doc, "2.5.2. Máy trạng thái điều khiển đèn", level=3)
    p(doc, "Bo phụ tổ chức logic điều khiển thành máy trạng thái ba chế độ (Hình 2.7): "
           "chế độ TỰ ĐỘNG (AUTO – mặc định, quyết định theo cảm biến), chế độ cưỡng "
           "chế BẬT (MANUAL_ON) và cưỡng chế TẮT (MANUAL_OFF). Lệnh giọng nói hoặc lệnh "
           "web chuyển máy trạng thái sang chế độ cưỡng chế tương ứng; khi người dùng "
           "rời bàn quá 5 phút, máy trạng thái tự khôi phục về AUTO để sẵn sàng cho "
           "lần ngồi kế tiếp.")
    figure(doc, "Hình 2.7", "Máy trạng thái ba chế độ điều khiển đèn bàn",
           "Vẽ 3 trạng thái AUTO / MANUAL_ON / MANUAL_OFF với các cung chuyển gắn "
           "nhãn: cmd=1, cmd=0, cmd=2, hết 5 phút vắng mặt.", height_cm=6)
    heading(doc, "2.5.3. Thuật toán khử nhiễu cảm biến và quản lý thời gian ngồi", level=3)
    p(doc, "Tín hiệu chân OUT của radar có thể giật lốc nháy khi người dùng quay "
           "người hoặc vướn tay ra xa; vì vậy firmware áp dụng bộ lọc khử nhiễu "
           "(debounce) 100 ms: chỉ khi mức logic giữ ổn định liên tục 100 ms, trạng "
           "thái \u201Ccó người\u201D mới được xác nhận. Phía tắt đèn áp dụng thuật toán "
           "lịch sử trễ (hysteresis theo thời gian): kể từ lần cuối còn thấy người, "
           "phải vượt quá thời gian chờ cấu hình (mặc định 15 s, thực tế đề xuất 180 s) "
           "hệ thống mới tắt đèn — nhờ đó người dùng cúi nhặt đồ hay quay sang lấy sách "
           "không làm đèn chớp tắt. Lưu đồ tổng hợp hai thuật toán trên trình bày ở "
           "Hình 2.8.")
    figure(doc, "Hình 2.8", "Lưu đồ thuật toán xử lý chính trên bo phụ ESP8266",
           "Vẽ lưu đồ vòng lặp: đọc D2 → debounce 100 ms → có người? → bật đèn & "
           "cộng giờ / đếm ngược timeout → tắt đèn & xóa override sau 5 phút → phát "
           "gói tin trạng thái mỗi giây.", height_cm=6.5)
    heading(doc, "2.5.4. Thiết kế bộ công cụ MCP cho bo chính", level=3)
    p(doc, "Bo chính đăng ký bộ công cụ MCP bằng lớp LampController (mã nguồn mở rộng "
           "của firmware Xiaozhi). Mỗi công cụ khi được mô hình ngôn ngữ gọi sẽ cập "
           "nhật trạng thái logic và phát gói tin ESP-NOW tương ứng (Bảng 2.8). Các "
           "công cụ được khai báo kèm mô tả song ngữ Anh – Việt để mô hình dễ dàng ánh "
           "xạ câu lệnh tiếng Việt đa dạng (\u201Cbật đèn bàn\u201D, \u201Ctắt đèn giúp tôi\u201D…).")
    table_caption(doc, "Bảng 2.8", "Bộ công cụ MCP tích hợp trên bo chính ESP32-S3")
    add_table(doc,
              ["Tên công cụ", "Chức năng", "Hành động phần cứng"],
              [
                  ("self.lamp.turn_on", "Bật đèn bàn", "Phát gói tin cmd = 1 qua ESP-NOW"),
                  ("self.lamp.turn_off", "Tắt đèn bàn", "Phát gói tin cmd = 0 qua ESP-NOW"),
                  ("self.lamp.get_state", "Truy vấn trạng thái đèn", "Trả về biến trạng thái logic dạng JSON"),
                  ("self.lamp.set_auto", "Chuyển về chế độ tự động", "Phát gói tin cmd = 2 qua ESP-NOW"),
                  ("self.light.turn_on / turn_off / get_state",
                   "Bí danh đèn (light) cho câu lệnh khác", "Tương đương các công cụ lamp"),
                  ("self.relay.control",
                   "Điều khiển relay tổng quát (turn_on/turn_off/toggle)",
                   "Phát gói tin cmd tương ứng theo tham số action"),
                  ("self.c3.switch",
                   "Công cụ tương thích hệ smarthome C3 của máy chủ Xiaozhi",
                   "Phát gói tin cmd = value (0/1)"),
              ], font_size=12)
    p(doc, "Bên cạnh điều khiển đèn, dữ liệu thời gian ngồi từ gói tin trạng thái "
           "DeskStatusPacket là nguồn cho tác vụ cảnh báo công thái học chạy nền trên "
           "bo chính: khi sitting_time_sec vượt 2 700 giây (45 phút) mà chưa cảnh báo, "
           "tác vụ này kích hoạt âm thanh nhắc nhở đứng dậy vận động, uống nước.")

    heading(doc, "2.6. Tổng kết chương 2", level=2)
    p(doc, "Chương 2 đã phân tích yêu cầu chức năng – phi chức năng, đề xuất kiến trúc "
           "Master – Satellite, thiết kế chi tiết phần cứng (danh mục linh kiện, sơ đồ "
           "đấu nối, căn chỉnh lắp đặt), giao thức gói tin ESP-NOW và các thuật toán "
           "phần mềm then chốt (máy trạng thái ba chế độ, khử nhiễu, thời gian chờ, bộ "
           "công cụ MCP). Chương 3 sẽ trình bày quá trình xây dựng, triển khai hệ thống "
           "trên phần cứng thật.")
    page_break(doc)


# =====================================================================
# CHUONG 3
# =====================================================================

def build_chuong3(doc):
    heading(doc, "CHƯƠNG 3. XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG", level=1, center=True)

    heading(doc, "3.1. Quy trình lắp ráp phần cứng", level=2)
    heading(doc, "3.1.1. Kiểm tra an toàn trước khi cấp nguồn", level=3)
    p(doc, "Trước khi cấp nguồn lần đầu, toàn bộ mạch được kiểm tra theo danh mục năm "
           "bước ở Bảng 3.1 nhằm loại trừ lỗi chạm chập và ngược cực.")
    table_caption(doc, "Bảng 3.1", "Danh mục kiểm tra an toàn trước khi cấp nguồn")
    add_table(doc,
              ["Bước", "Nội dung kiểm tra", "Tiêu chí đạt"],
              [
                  ("1", "Kiểm tra chạm chập nguồn",
                   "Chân VCC/VIN và GND không dính thiếc, không chạm nhau (đo bằng VOM)"),
                  ("2", "Kiểm tra chân nguồn 5 V",
                   "VCC của LD2410 và DC+ của relay cắm đúng chân VIN/VU, tuyệt đối không cắm 3V3"),
                  ("3", "Kiểm tra hoạt động relay",
                   "Cấp nguồn cho ESP8266, kích thử relay nghe tiếng \u201Ctách\u201D dứt khoát"),
                  ("4", "Kiểm tra tín hiệu radar",
                   "Có người ngồi: chân OUT của LD2410 lên ≈3,3 V; đứng ra xa > 2 m: về 0 V"),
                  ("5", "Cố định dây nối",
                   "Bó gọn dây tín hiệu bằng dây rút/băng keo, chống lỏng khi di chuyển mô hình"),
              ], font_size=12)
    heading(doc, "3.1.2. Kết quả lắp ráp mô hình", level=3)
    p(doc, "Hai cụm mạch sau khi lắp ráp hoàn chỉnh thể hiện tại Hình 3.1 (bo chính "
           "trên mặt bàn) và Hình 3.2 (cụm bo phụ dưới gầm bàn). Toàn bộ hệ thống chỉ "
           "cần hai sợi cáp cấp nguồn USB, không có dây nối giữa hai cụm.")
    figure(doc, "Hình 3.1", "Mạch thực tế cụm bo chính ESP32-S3 sau khi lắp ráp",
           "Chụp ảnh bo chính ESP32-S3 + màn 0.96 inch + loa/mic, đặt trên mặt bàn.",
           height_cm=5.5)
    figure(doc, "Hình 3.2", "Mạch thực tế cụm bo phụ ESP8266 sau khi lắp ráp",
           "Chụp ảnh NodeMCU ESP8266, radar LD2410 dán dưới mép bàn, module relay "
           "và dây tải đi ra đèn.", height_cm=5.5)

    heading(doc, "3.2. Xây dựng firmware bo phụ ESP8266", level=2)
    heading(doc, "3.2.1. Kiến trúc chương trình và quản lý cấu hình EEPROM", level=3)
    p(doc, "Firmware bo phụ (mã nguồn esp8266_slave.ino, khoảng 1 000 dòng) được tổ "
           "chức theo mô hình vòng lặp sự kiện: khối setup() khởi tạo tuần tự 8 bước "
           "(đọc cấu hình, thiết lập GPIO, phát SoftAP, đồng bộ kênh, kết nối router, "
           "khởi tạo ESP-NOW, máy chủ web, mDNS), khối loop() xử lý máy trạng thái cảm "
           "biến – đèn – telemetry. Toàn bộ tham số hiệu chỉnh (cực kích relay, logic "
           "cảm biến, thời gian chờ, SSID/mật khẩu tùy chọn) được lưu vào 128 byte đầu "
           "của EEPROM, kèm mã nhận diện 0x5A để phát hiện lần chạy đầu tiên và nạp "
           "giá trị mặc định an toàn (đèn tắt, chờ 15 s).")
    heading(doc, "3.2.2. Vòng lặp chính và các thuật toán thời gian thực", level=3)
    p(doc, "Trong mỗi 10 ms của loop(), firmware thực hiện bốn công đoạn: (1) phục vụ "
           "máy chủ web và mDNS; (2) đọc chân D2 và áp bộ lọc khử nhiễu 100 ms; (3) chạy "
           "thuật toán tự động hóa — cập nhật bộ đếm thời gian ngồi khi có người, bật "
           "đèn theo chế độ hiện hành, đếm ngược thời gian chờ và tự khôi phục AUTO sau "
           "5 phút vắng mặt; (4) mỗi đúng 1 giây phát broadcast gói tin trạng thái 7 "
           "byte sang bo chính đồng thòi in bản tin chẩn đoán ra cổng Serial. Ngoài "
           "tự động hóa, firmware còn cung cấp giao diện lệnh qua Serial (phím 0/1/a/p/"
           "r/s/c/w/h) phục vụ chẩn đoán nhanh tại hiện trường (Phụ lục A).")
    heading(doc, "3.2.3. Máy chủ web nội bộ và REST API", level=3)
    p(doc, "Bo phụ chạy máy chủ HTTP cổng 80 ngay trên chip, phục vụ trang dashboard "
           "đơn (HTML/CSS/JS nhúng trong flash) và tập REST API dạng JSON ở Bảng 3.2. "
           "Dịch vụ mDNS cho phép truy cập thân thiện qua địa chỉ http://smartdesk.local. "
           "Trang web khi không kết nối được router vẫn dùng được qua chính điểm phát "
           "SoftAP \u201CSmartDesk-Assistant\u201D của thiết bị.")
    table_caption(doc, "Bảng 3.2", "Các điểm cuối REST API trên máy chủ web của bo phụ ESP8266")
    add_table(doc,
              ["Phương thức", "Đường dẫn", "Chức năng"],
              [
                  ("GET", "/", "Trang dashboard giám sát – điều khiển"),
                  ("GET", "/api/status", "Trạng thái hệ thống dạng JSON (chế độ, đèn, ngồi, kênh, IP…)"),
                  ("POST", "/api/control?mode=auto|on|off", "Đổi chế độ điều khiển đèn"),
                  ("POST", "/api/config", "Lưu cực relay, logic radar, thời gian chờ vào EEPROM"),
                  ("GET", "/api/wifi/scan", "Quét các mạng WiFi 2,4 GHz xung quanh (kèm kênh, RSSI)"),
                  ("POST", "/api/wifi/save", "Lưu và kết nối mạng WiFi mới (đồng bộ kênh)"),
                  ("POST", "/api/ping-s3", "Phát thử gói tin trạng thái ESP-NOW sang bo chính"),
              ], font_size=12)
    heading(doc, "3.2.4. Giao diện Web Dashboard trên bo phụ", level=3)
    p(doc, "Giao diện dashboard (Hình 3.3) được thiết kế theo phong cách thẻ (card) nền "
           "tối, tự làm mới dữ liệu mỗi 1,5 giây, gồm năm thẻ: điều khiển đèn (ba chế "
           "độ), công thái học & cảm biến radar (đồng hồ thời gian ngồi HH:MM:SS, cảnh "
           "báo khi quá 45 phút), cấu hình phần cứng, thông tin kết nối ESP-NOW và cấu "
           "hình WiFi kèm chức năng quét mạng một chạm.")
    figure(doc, "Hình 3.3", "Giao diện Web Dashboard chạy trên bo phụ ESP8266",
           "Chụp màn hình trình duyệt mở http://smartdesk.local (hoặc IP bo phụ) "
           "khi hệ thống đang chạy, có người ngồi và đèn đang bật.", height_cm=6.5)

    heading(doc, "3.3. Xây dựng firmware bo chính ESP32-S3", level=2)
    heading(doc, "3.3.1. Lớp LampController đăng ký công cụ MCP", level=3)
    p(doc, "Trên nền firmware Xiaozhi, đề tài bổ sung lớp LampController (tệp "
           "lamp_controller.h trong thư mục boards/common) thực hiện hai nhiệm vụ: quản "
           "lý trạng thái đèn logic và đăng ký bộ công cụ MCP của Bảng 2.8 vào máy chủ "
           "MCP nội bộ (McpServer::GetInstance().AddTool). Khi mô hình ngôn ngữ gọi một "
           "công cụ, hàm xử lý tương ứng cập nhật biến trạng thái power_, xuất mức GPIO "
           "nếu có cấu hình chân đèn nội, đồng thòi gọi SendEspNowCommand() để phát lệnh "
           "sang bo phụ. Đoạn mã trích dẫn được nêu tại Phụ lục B.")
    heading(doc, "3.3.2. Phát lệnh ESP-NOW dạng burst và tuân thủ kênh WiFi", level=3)
    p(doc, "Hàm SendEspNowCommand() khởi tạo ESP-NOW lười (lazy init) vào lần gọi đầu "
           "tiên, đăng ký điểm đến là địa chỉ broadcast FF:FF:FF:FF:FF:FF với kênh tự "
           "động bám theo kênh WiFi hiện hành của giao diện STA, tắt chế độ tiết kiệm "
           "nguồn vô tuyến rồi phát 6 gói tin lệnh liên tiếp cách nhau 15 ms. Giải pháp "
           "burst này kết hợp với cơ chế đồng bộ kênh ở bo phụ (mục 2.4.3) giúp lệnh "
           "điều khiển giọng nói đạt độ tin cậy cao mà không cần cơ chế bắt tay phức tạp.")
    heading(doc, "3.3.3. Cấu hình hệ thống qua phân vùng NVS", level=3)
    p(doc, "Thay vì sửa mã nguồn và biên dịch lại, toàn bộ cấu hình vận hành quan "
           "trọng của bo chính được ghi vào phân vùng NVS 16 KB (Bảng 3.3) bằng bộ công "
           "cụ Python tự xây dựng, sau đó nạp vào thiết bị ở địa chỉ 0x9000 qua esptool.")
    table_caption(doc, "Bảng 3.3", "Các khóa cấu hình lưu trong phân vùng NVS của ESP32-S3")
    add_table(doc,
              ["Nhóm", "Khóa (key)", "Giá trị trong đề tài", "Ý nghĩa"],
              [
                  ("WiFi", "wifi.ssid / wifi.password", "SSID, mật khẩu WiFi phòng",
                   "Mạng Internet cho trợ lý AI"),
                  ("Màn hình", "scr.drv, w, h, off_x…", "drv = 3 (ST7735), 80×160, offset X = 26",
                   "Driver, độ phân giải, offset hiển thị"),
                  ("Màn hình", "p_mosi/p_clk/p_dc/p_rst", "41 / 42 / 43 / 44",
                   "Ánh xạ chân SPI vật lý"),
                  ("Màn hình", "inv_col, rgb_ord, mir_x, mir_y", "1, 1, 1, 1",
                   "Đảo màu IPS, thứ tự màu RGB, lật trục hiển thị"),
                  ("Đèn", "p_lamp", "-1 (tắt chân nội)",
                   "Tránh xung đột chân GPIO 15 với BCLK loa I2S; đèn điều khiển qua bo phụ"),
              ], font_size=12)
    heading(doc, "3.3.4. Quy trình nạp firmware và khôi phục", level=3)
    p(doc, "Firmware tổng hợp (bootloader + bảng phân vùng + ứng dụng, tệp "
           "xiaozhi_merged.bin ≈ 9,5 MB) được nạp xuống địa chỉ 0x0 bằng esptool, tiếp "
           "đó phân vùng NVS đã cấu hình (nvs_configured.bin) nạp vào 0x9000. Kịch bản "
           "restore_xiaozhi_firmware.py tự động hóa thao tác khôi phục này. Quy trình "
           "chi tiết và câu lệnh mẫu được trình bày tại Phụ lục C.")
    heading(doc, "3.3.5. Giao diện hiển thị trên thiết bị", level=3)
    p(doc, "Trong vận hành, màn hình 0,96 inch hiển thị biểu tượng cảm xúc của trợ lý, "
           "trạng thái kết nối, đồng hồ và lời nhắc (Hình 3.4).")
    figure(doc, "Hình 3.4", "Giao diện màn hình hiển thị 0.96 inch trên bo chính",
           "Chụp cận cảnh màn hình ST7735 khi thiết bị đang hoạt động (icon cảm "
           "xúc, trạng thái WiFi, đồng hồ).", height_cm=5)

    heading(doc, "3.4. Công cụ giám sát và cấu hình trên máy tính", level=2)
    heading(doc, "3.4.1. PC Bridge Dashboard", level=3)
    p(doc, "Để vận hành minh họa trước hội đồng, đề tài xây dựng thêm ứng dụng cầu nối "
           "trên máy tính (web_dashboard.py): máy chủ HTTP cổng 8080 đọc dữ liệu chẩn "
           "đoán từ cổng Serial của ESP8266 (115 200 baud), kết hợp kết quả quét WiFi "
           "của hệ điều hành để trình bày bảng điều khiển tổng hợp (Hình 3.5), đồng "
           "thòi chuyển tiếp lệnh điều khiển từ trình duyệt xuống thiết bị qua Serial.")
    figure(doc, "Hình 3.5", "Giao diện PC Bridge Dashboard trên máy tính",
           "Chụp màn hình dashboard cổng 8080 với đồng hồ thời gian ngồi, danh "
           "sách WiFi quét được, trạng thái đèn.", height_cm=6)
    heading(doc, "3.4.2. Bộ kịch bản cấu hình NVS bằng Python", level=3)
    p(doc, "Ba kịch bản cấu hình được xây dựng theo cùng một kỹ thuật: mở ảnh nhị phân "
           "16 384 byte của phân vùng NVS, duyệt bảng entry theo bản đồ bit của trang, "
           "sửa trường dữ liệu của khóa đích, tính lại checksum CRC32 rồi ghi lại và nạp "
           "vào thiết bị: set_wifi_config.py (khóa SSID/mật khẩu), set_lcd_config.py "
           "(17 tham số màn hình), set_lamp_gpio.py (khóa p_lamp). Cách làm này cho "
           "phép cấu hình hàng loạt thiết bị từ tệp ảnh mà không phụ thuộc môi trường "
           "biên dịch.")

    heading(doc, "3.5. Kịch bản trình diễn vận hành hệ thống", level=2)
    p(doc, "Sau khi triển khai, hệ thống được vận hành theo kịch bản trình diễn chuẩn "
           "ở Bảng 3.4, bao phủ đầy đủ bốn công nghệ trọng tâm của đề tài.")
    table_caption(doc, "Bảng 3.4", "Kịch bản trình diễn vận hành hệ thống")
    add_table(doc,
              ["Bước", "Hành động", "Phản ứng của hệ thống", "Công nghệ thể hiện"],
              [
                  ("1", "Khởi động cả hai bo",
                   "Hai bo đồng bộ kênh, thiết lập liên kết ESP-NOW, đèn tắt",
                   "Kiến trúc Master – Slave, đồng bộ kênh tự động"),
                  ("2", "Người dùng ngồi vào bàn",
                   "Radar phát hiện hiện diện → đèn sáng tức thì, bộ đếm giờ chạy",
                   "Cảm biến mmWave 24 GHz phát hiện người tĩnh"),
                  ("3", "Nói \u201CTrợ lý ơi, tắt đèn bàn giúp tôi\u201D",
                   "Trợ lý phản hồi \u201CĐã tắt đèn bàn\u201D, đèn tắt ngay",
                   "ASR – LLM tiếng Việt, tool calling theo chuẩn MCP"),
                  ("4", "Hỏi về thời gian đã ngồi",
                   "Hệ thống tra số liệu từ gói tin trạng thái để trả lời số phút",
                   "Đồng bộ telemetry thời gian thực hai vi điều khiển"),
                  ("5", "Giả lập ngồi quá 45 phút",
                   "Dashboard hiện cảnh báo; trợ lý phát nhắc nhở vận động",
                   "Ứng dụng IoT cho sức khỏe, công thái học"),
                  ("6", "Đứng dậy rời bàn",
                   "Sau thời gian chờ, radar xác nhận vắng người → đèn tự tắt",
                   "Tự động hóa không chạm, tiết kiệm điện"),
              ], font_size=12)

    heading(doc, "3.6. Tổng kết chương 3", level=2)
    p(doc, "Chương 3 đã trình bày quá trình hiện thực hóa thiết kế: lắp ráp mạch theo "
           "quy trình an toàn, xây dựng firmware cả hai bo mạch với các thuật toán thời "
           "gian thực, tích hợp bộ công cụ MCP vào nền tảng Xiaozhi, phát triển hệ thống "
           "dashboard hai cấp (trên thiết bị và cầu nối máy tính) cùng bộ công cụ cấu "
           "hình NVS. Kết quả triển khai sẽ được đánh giá định lượng ở chương tiếp theo.")
    page_break(doc)


# =====================================================================
# CHUONG 4
# =====================================================================

def build_chuong4(doc):
    heading(doc, "CHƯƠNG 4. KIỂM THỬ VÀ ĐÁNH GIÁ KẾT QUẢ", level=1, center=True)

    heading(doc, "4.1. Phương pháp kiểm thử", level=2)
    p(doc, "Hệ thống được kiểm thử theo ba hướng kết hợp: (i) kiểm thử chức năng dạng "
           "hộp đen trên phần cứng thật theo ma trận kiểm thử; (ii) kiểm thử tự động "
           "bằng các kịch bản Python viết trên framework unittest, kiểm tra tính toàn "
           "vẹn ảnh firmware, cấu trúc phân vùng NVS và hành vi các kịch bản cấu "
           "hình; (iii) kiểm thử vận hành kịch bản đầu cuối (end-to-end) theo đúng "
           "Bảng 3.4 kèm quan sát nhật ký Serial.")

    heading(doc, "4.2. Kiểm thử chức năng", level=2)
    p(doc, "Ma trận kiểm thử sáu ca từ TC-01 đến TC-06 và kết quả thực hiện được thể "
           "hiện tại Bảng 4.1.")
    table_caption(doc, "Bảng 4.1", "Ma trận kiểm thử chức năng")
    add_table(doc,
              ["Mã", "Nội dung kiểm tra", "Tiêu chuẩn đạt", "Kết quả"],
              [
                  ("TC-01", "Đọc tín hiệu LD2410 trên ESP8266",
                   "Có người: chân D2 ở mức HIGH; rời bàn: về LOW đúng theo logic cài đặt",
                   "Đạt"),
                  ("TC-02", "Đóng ngắt relay",
                   "Chân D1 kích relay nhảy dứt khoát, đèn sáng/tắt chính xác",
                   "Đạt"),
                  ("TC-03", "Khung truyền ESP-NOW",
                   "Bo phụ gửi, bo chính nhận đủ 7 byte với mã magic 0xA5",
                   "Đạt"),
                  ("TC-04", "Đồng bộ kênh khi có WiFi router",
                   "ESP-NOW truyền nhận thông suốt khi cả hai bo cùng vào router, không rớt gói",
                   "Đạt"),
                  ("TC-05", "Gọi công cụ MCP bằng giọng nói",
                   "Lệnh tiếng Việt tự nhiên gọi đúng công cụ và kích hoạt ESP-NOW",
                   "Đạt"),
                  ("TC-06", "Bộ đếm thời gian ngồi",
                   "Tăng tuyến tính khi có người; dừng/khởi tạo lại khi rời bàn hẳn",
                   "Đạt"),
              ], font_size=12)

    heading(doc, "4.3. Kiểm thử tự động bằng kịch bản Python", level=2)
    p(doc, "Bên cạnh kiểm thử phần cứng, đề tài xây dựng bộ kiểm thử tự động (Bảng "
           "4.2) chạy trên máy tính bằng lệnh python -m unittest, đảm bảo các thay đổi "
           "mã nguồn và tệp cấu hình không gây hồi quy. Kết quả chạy được minh họa ở "
           "Hình 4.1.")
    table_caption(doc, "Bảng 4.2", "Bộ kiểm thử tự động bằng ngôn ngữ Python")
    add_table(doc,
              ["Tệp kiểm thử", "Phạm vi kiểm tra"],
              [
                  ("test_nvs_configuration.py", "Cấu trúc 16 KB phân vùng NVS: CRC32, đúng 17 khóa LCD, WiFi, p_lamp"),
                  ("test_firmware_integrity.py", "Tính toàn vẹn ảnh xiaozhi_merged.bin (kích thước, vùng phân vùng)"),
                  ("test_set_wifi_config.py", "Hành vi kịch bản set_wifi_config.py (cập nhật CRC, giới hạn độ dài SSID)"),
                  ("test_set_lcd_config.py", "Hành vi kịch bản set_lcd_config.py với bộ tham số màn hình"),
                  ("test_espnow_communication.py / test_espnow_bridge.py", "Đóng gói – giải mã cấu trúc gói tin ESP-NOW hai chiều"),
                  ("test_esp8266_serial.py / test_esp8266_commands.py", "Tập lệnh Serial và phản hồi lệnh điều khiển của bo phụ"),
                  ("test_web_dashboard.py", "Các điểm cuối API và dữ liệu JSON của PC Bridge Dashboard"),
                  ("test_xiaozhi_espnow_build.py", "Ràng buộc biên dịch/cấu hình firmware Xiaozhi tích hợp ESP-NOW"),
              ], font_size=12)
    figure(doc, "Hình 4.1", "Kết quả chạy bộ kiểm thử tự động",
           "Chụp màn hình cửa sổ lệnh chạy python -m unittest discover scripts với "
           "toàn bộ ca kiểm thử OK.", height_cm=5)

    heading(doc, "4.4. Đánh giá hiệu năng phản hồi", level=2)
    p(doc, "Các khoảng thời gian đáp ứng điển hình được đo trong điều kiện mạng WiFi "
           "gia đình, tổng hợp tại Bảng 4.3; nhật ký Serial minh chứng quá trình vận "
           "hành thể hiện ở Hình 4.2.")
    table_caption(doc, "Bảng 4.3", "Kết quả đo hiệu năng phản hồi của hệ thống")
    add_table(doc,
              ["Chỉ số", "Giá trị đạt được", "Ghi chú"],
              [
                  ("Độ trễ truyền gói tin ESP-NOW nội bộ", "< 5 ms/gói", "Đáp ứng NFR-01"),
                  ("Thời gian bật đèn kể từ khi có người", "≈ 100 ms (khử nhiễu)", "Cảm giác phản hồi tức thì"),
                  ("Chu kỳ báo cáo trạng thái bo phụ → bo chính", "1 s", "Đồng bộ bộ đếm ngồi"),
                  ("Độ tin cậy lệnh điều khiển (phát burst 6 gói)", "Không lỗi trong chuỗi thử", "Kết hợp đồng kênh WiFi"),
                  ("Thời gian phản hồi lệnh giọng nói đầu cuối", "≈ 1–3 s", "Phụ thuộc mạng Internet và máy chủ LLM"),
                  ("Thời gian làm mới dữ liệu Web Dashboard", "1,5 s", "Trang tự cập nhật định kỳ"),
              ], font_size=12)
    figure(doc, "Hình 4.2", "Nhật ký cổng Serial trong quá trình vận hành hệ thống",
           "Chụp cửa sổ Serial Monitor của bo phụ: các dòng [RADAR], [RELAY], "
           "[STATUS], [ESP-NOW] khi người ngồi vào rồ i rời bàn.", height_cm=5)

    heading(doc, "4.5. Bàn luận kết quả và hạn chế", level=2)
    p(doc, "Kết quả kiểm thử cho thấy hệ thống đáp ứng đầy đủ sáu yêu cầu chức năng "
           "ở Bảng 2.1. Kiến trúc Master – Satellite kết hợp ESP-NOW tỏ ra phù hợp: "
           "đường truyền nội bộ gần như tức thời trong khi bo chính tập trung toàn bộ "
           "tài nguyên cho đàm thoại AI. Việc tách cấu hình ra khỏi mã nguồn (EEPROM/"
           "NVS + dashboard) giúp hiệu chỉnh tại chỗ mà không cần môi trường lập trình.")
    p(doc, "Bên cạnh đó, hệ thống còn một số hạn chế: (i) chất lượng nhận lệnh giọng "
           "nói phụ thuộc vào đường truyền Internet và máy chủ đám mây; (ii) cảm biến "
           "radar nhạy với nguồn chuyển động không mong muốn (quạt, rèm) nếu bố trí sai "
           "hướng; (iii) giao thức ESP-NOW broadcast chưa mã hóa nên chỉ phù hợp mạng "
           "nội bộ tin cậy; (iv) tính năng truy vấn thời gian ngồi bằng giọng nói hiện "
           "mới ở mức thiết kế mở rộng, dữ liệu chủ yếu hiển thị trên dashboard.")

    heading(doc, "4.6. Tổng kết chương 4", level=2)
    p(doc, "Chương 4 đã kiểm chứng hệ thống bằng kiểm thử chức năng, kiểm thử tự động "
           "và đo đạc hiệu năng định lượng. Toàn bộ sáu ca kiểm thử đều đạt yêu cầu; các "
           "chỉ số độ trễ nằm trong ngưỡng thiết kế, khẳng định tính khả thi của giải "
           "pháp trợ lý bàn làm việc không chạm tích hợp AI đám mây trên nền tảng vi "
           "điều khiển chi phí thấp.")
    page_break(doc)


# =====================================================================
# KET LUAN, TAI LIEU THAM KHAO
# =====================================================================

def build_ket_luan(doc):
    unnumbered_heading(doc, "KẾT LUẬN VÀ KIẾN NGHỊ")
    heading(doc, "1. Kết quả đạt được", level=2)
    p(doc, "Đề tài đã xây dựng thành công hệ thống trợ lý bàn làm việc thông minh hoàn "
           "chỉnh, vận hành ổn định trên phần cứng thật với các kết quả chính sau:")
    bullet(doc, "Hệ thống chiếu sáng tự động không chạm dựa trên cảm biến radar "
                "mmWave 24 GHz, bật đèn trong ≈100 ms khi có người và tự tắt sau "
                "thời gian chờ, không còn lỗi vòng lặp phản xạ ánh sáng của phương án "
                "quang trở truyền thống.")
    bullet(doc, "Điều khiển đèn bằng giọng nói tiếng Việt tự nhiên thông qua trợ lý AI "
                "Xiaozhi và bộ bảy nhóm công cụ MCP tự xây dựng; lệnh điều khiển được "
                "truyền tức thời (< 5 ms) giữa hai vi điều khiển nhờ ESP-NOW kèm cơ chế "
                "đồng bộ kênh WiFi và phát burst.")
    bullet(doc, "Chức năng theo dõi thời gian ngồi công thái học với cảnh báo khi ngồi "
                "quá 45 phút, hiển thị đồng bộ trên Web Dashboard thời gian thực chạy "
                "ngay trên vi điều khiển (cổng 80, tên miền smartdesk.local).")
    bullet(doc, "Quy trình cấu hình – vận hành không cần biên dịch lại: bộ công cụ "
                "Python chỉnh sửa trực tiếp phân vùng NVS/EEPROM; bộ kiểm thử tự động "
                "bảo đảm chất lượng mã nguồn.")
    heading(doc, "2. Hạn chế của đề tài", level=2)
    bullet(doc, "Trải nghiệm giọng nói phụ thuộc chất lượng mạng Internet và hạ tầng "
                "máy chủ đám mây.")
    bullet(doc, "Giao tiếp ESP-NOW broadcast chưa áp dụng mã hóa, phù hợp phạm vi phòng "
                "tin cậy chứ chưa phù hợp môi trường không tin cậy.")
    bullet(doc, "Cảm biến radar cần bố trí đúng hướng để tránh chuyển động nhiễu; chưa "
                "cấu hình ngưỡng theo cổng khoảng cách qua UART.")
    heading(doc, "3. Kiến nghị và hướng phát triển", level=2)
    bullet(doc, "Mở rộng công cụ MCP self.desk.get_sitting_time để trả lời trực tiếp "
                "bằng giọng nói câu hỏi về thời gian ngồi, hoàn thiện vòng khép kín "
                "theo dõi công thái học.")
    bullet(doc, "Bổ sung thêm bo phụ cho các thiết bị khác (quạt, ổ cắm, rèm cửa) theo "
                "cùng khung gói tin, hướng tới không gian làm việc thông minh đa nút.")
    bullet(doc, "Kích hoạt mã hóa ESP-NOW (khóa PMK/LMK) và xác thực Web Dashboard để "
                "tăng cường bảo mật khi triển khai thực tế.")
    bullet(doc, "Nghiên cứu chạy suy luận nhận dạng hiện diện tinh vi hơn (ngưỡng cổng "
                "khoảng cách LD2410 qua UART) và lắp vỏ hộp hoàn thiện cho sản phẩm.")
    page_break(doc)


def build_tltk(doc):
    unnumbered_heading(doc, "TÀI LIỆU THAM KHẢO")
    p(doc, "", space_after=2)
    refs = [
        "[1]  Espressif Systems (2024). ESP32-S3 Series Datasheet, Version 1.7, "
        "Espressif Systems; Shanghai.",

        "[2]  Espressif Systems (2023). ESP8266EX Datasheet, Version 4.3, "
        "Espressif Systems; Shanghai.",

        "[3]  Hi-Link Electronic (2022). HLK-LD2410 24GHz Millimeter Wave Human "
        "Presence Sensor User Manual, Version 1.03, Shenzhen Hi-Link Electronic Co., "
        "Ltd.; Shenzhen.",

        "[4]  Espressif Systems (2025). ESP-NOW, trong ESP-IDF Programming Guide "
        "Release v6.1, Espressif Systems; Shanghai.",

        "[5]  78 (2025). xiaozhi-esp32: An MCP-based Chatbot, "
        "<https://github.com/78/xiaozhi-esp32>, truy cập ngày 01/10/2026.",

        "[6]  Anthropic (2025). Model Context Protocol Specification, "
        "<https://modelcontextprotocol.io>, truy cập ngày 01/10/2026.",

        "[7]  Espressif Systems (2025). ESP-SR: Speech Recognition Framework, "
        "<https://github.com/espressif/esp-sr>, truy cập ngày 01/10/2026.",

        "[8]  Espressif Systems (2025). ESP-IDF Programming Guide, Release v6.1, "
        "Espressif Systems; Shanghai.",

        "[9]  LVGL Kft (2025). LVGL – Light and Versatile Graphics Library "
        "Documentation v9, <https://docs.lvgl.io>, truy cập ngày 01/10/2026.",

        "[10] Real Time Engineers Ltd (2024). FreeRTOS Kernel Developer "
        "Documentation, Amazon Web Services.",

        "[11] Arduino (2024). ESP8266 Arduino Core Documentation, "
        "<https://arduino-esp8266.readthedocs.io>, truy cập ngày 01/10/2026.",
    ]
    for r in refs:
        par = p(doc, r, size=13, space_after=6)
        par.paragraph_format.left_indent = Cm(1.0)
        par.paragraph_format.first_line_indent = Cm(-1.0)
    page_break(doc)


def build_phu_luc(doc):
    unnumbered_heading(doc, "PHỤ LỤC")

    heading(doc, "PHỤ LỤC A. TẬP LỆNH ĐIỀU KHIỂN QUA CỔNG SERIAL CỦA BO PHỤ ESP8266", level=2)
    p(doc, "Bảng A.1 liệt kê các phím tắt điều khiển – chẩn đoán nhanh bo phụ qua cổng "
           "Serial 115 200 baud (nhấn h hoặc ? trên thiết bị để in hướng dẫn tương tự).")
    table_caption(doc, "Bảng A.1", "Tập lệnh điều khiển qua cổng Serial của bo phụ ESP8266")
    add_table(doc,
              ["Phím", "Chức năng"],
              [
                  ("0", "Cưỡng chế TẮT đèn (MANUAL_OFF, ưu tiên hơn cảm biến)"),
                  ("1", "Cưỡng chế BẬT đèn (MANUAL_ON, ưu tiên hơn cảm biến)"),
                  ("a", "Trả về chế độ TỰ ĐỘNG (AUTO)"),
                  ("p", "Đảo cực kích relay (Active-HIGH ↔ Active-LOW), lưu EEPROM"),
                  ("r", "Đảo logic đọc radar (Active-HIGH ↔ Active-LOW), lưu EEPROM"),
                  ("s", "In bản tin chẩn đoán trạng thái chi tiết"),
                  ("c", "Quét các mạng WiFi 2,4 GHz xung quanh"),
                  ("w <SSID> <PASS>", "Cài mạng WiFi mới, lưu EEPROM và kết nối (đồng bộ kênh)"),
                  ("h / ?", "In danh sách lệnh trợ giúp"),
              ], font_size=12)

    heading(doc, "PHỤ LỤC B. TRÍCH MÃ NGUỒN CHÍNH", level=2)
    heading(doc, "B.1. Cấu trúc gói tin ESP-NOW dùng chung cho cả hai bo", level=3)
    code_block(doc, [
        "// Gói tin lệnh: ESP32-S3 -> ESP8266 (2 byte)",
        "struct __attribute__((packed)) DeskCommandPacket {",
        "    uint8_t magic; // Mã nhận diện: 0x5A",
        "    uint8_t cmd;   // 0: Tắt đèn, 1: Bật đèn, 2: Chế độ tự động",
        "};",
        "// Gói tin trạng thái: ESP8266 -> ESP32-S3 (7 byte)",
        "struct __attribute__((packed)) DeskStatusPacket {",
        "    uint8_t  magic;            // Mã nhận diện: 0xA5",
        "    uint8_t  is_sitting;       // 1: đang ngồi, 0: đã rời bàn",
        "    uint8_t  lamp_state;       // 1: đèn sáng, 0: đèn tắt",
        "    uint32_t sitting_time_sec; // Thời gian ngồi liên tục (giây)",
        "};",
    ])
    heading(doc, "B.2. Hàm phát lệnh ESP-NOW dạng burst trên bo chính (lamp_controller.h)", level=3)
    code_block(doc, [
        "void SendEspNowCommand(uint8_t cmd) {",
        "    InitEspNow();                       // Khởi tạo lười + peer broadcast",
        "    esp_wifi_set_ps(WIFI_PS_NONE);      // Đánh thức hoàn toàn modem WiFi",
        "    DeskCommandPacket pkt = {0x5A, cmd};",
        "    for (int i = 0; i < 6; i++) {       // Burst 6 gói, cách nhau 15 ms",
        "        esp_now_send(broadcast_mac_, (uint8_t*)&pkt, sizeof(pkt));",
        "        vTaskDelay(pdMS_TO_TICKS(15));",
        "    }",
        "}",
    ])
    heading(doc, "B.3. Đăng ký công cụ MCP điều khiển đèn (trích)", level=3)
    code_block(doc, [
        'mcp_server.AddTool("self.lamp.turn_off", "Turn off the lamp / Tat den ban",',
        "                   PropertyList(),",
        "    [this](const PropertyList& properties) -> ReturnValue {",
        "        power_ = false;",
        "        SendEspNowCommand(0);          // Phát lệnh TẮT sang bo phụ",
        "        return true;",
        "    });",
    ])

    heading(doc, "PHỤ LỤC C. QUY TRÌNH NẠP FIRMWARE VÀ CẤU HÌNH THIẾT BỊ", level=2)
    p(doc, "Các thao tác thực hiện trên máy tính Windows có cài esptool (python -m "
           "esptool), cổng COM thay theo thiết bị thật:")
    bullet(doc, "Nạp firmware tổng hợp cho bo chính:", bold_prefix="Bước 1. ")
    code_block(doc, [
        "python -m esptool --port COM5 --baud 460800 write_flash 0x0 xiaozhi_merged.bin",
    ])
    bullet(doc, "Cấu hình WiFi vào ảnh NVS rồi nạp vào địa chỉ 0x9000:",
           bold_prefix="Bước 2. ")
    code_block(doc, [
        'python scripts/set_wifi_config.py',
        'python scripts/set_lcd_config.py',
        'python scripts/set_lamp_gpio.py',
        'python -m esptool --port COM5 --baud 115200 write_flash 0x9000 nvs_configured.bin',
    ])
    bullet(doc, "Nạp firmware bo phụ ESP8266 bằng Arduino IDE (board NodeMCU 1.0, "
                "tốc độ nạp 115 200 baud), sau đó mở Serial Monitor kiểm tra bản tin "
                "khởi động.", bold_prefix="Bước 3. ")
    bullet(doc, "Truy cập Web Dashboard: kết nối điện thoại/máy tính vào WiFi "
                "\u201CSmartDesk-Assistant\u201D (mật khẩu 12345678) hoặc cùng mạng LAN, mở "
                "trình duyệt tại http://smartdesk.local.", bold_prefix="Bước 4. ")
    bullet(doc, "Khôi phục khi cần: chạy python scripts/restore_xiaozhi_firmware.py "
                "để tự động nạp lại toàn bộ firmware gốc.", bold_prefix="Bước 5. ")


# =====================================================================
# HAM CHINH
# =====================================================================

def main():
    doc = init_document()
    build_cover(doc)
    build_subcover(doc)
    build_declaration(doc)
    build_thanks(doc)
    build_toc(doc)
    build_abbrev(doc)
    build_lot_lof(doc)
    build_mo_dau(doc)
    build_chuong1(doc)
    build_chuong2(doc)
    build_chuong3(doc)
    build_chuong4(doc)
    build_ket_luan(doc)
    build_tltk(doc)
    build_phu_luc(doc)
    doc.save(OUT_PATH)
    print("Đã tạo:", OUT_PATH)


if __name__ == "__main__":
    main()

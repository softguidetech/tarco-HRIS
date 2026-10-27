# -*- coding: utf-8 -*-
"""Build the Arabic Tarco HRIS user guide PDF (Soft Guide Technology)."""
import os
import re
import sys
from datetime import date

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

COMPANY = 'SOFT GUIDE TECHNOLOGY'
SITE = 'www.softguidetech.com'
TITLE = 'نظام موارد بشرية تاركو لأودو 19'
SUBTITLE = 'دليل المستخدم - وحدة الموارد البشرية'
VERSION = 'إصدار الوحدة 19.0.1.0.29'

NAVY = colors.HexColor('#0F2C4C')
NAVY_2 = colors.HexColor('#1A4370')
TEAL = colors.HexColor('#13A89E')
TEAL_SOFT = colors.HexColor('#9FDCD5')
ORANGE = colors.HexColor('#E8902A')
INK = colors.HexColor('#1F2933')
MUTED = colors.HexColor('#66788A')
LINE = colors.HexColor('#D9E2EC')
PALE = colors.HexColor('#F3F7FA')
TIP_BG = colors.HexColor('#E7F6F4')
WARN_BG = colors.HexColor('#FFF3E3')

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm
CONTENT_W = PAGE_W - 2 * MARGIN


def _font_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, '..', 'static', 'src', 'fonts'))


def _register_fonts():
    fonts = {
        'Plex': 'IBMPlexSansArabic-Regular.ttf',
        'Plex-Med': 'IBMPlexSansArabic-Medium.ttf',
        'Plex-Semi': 'IBMPlexSansArabic-SemiBold.ttf',
        'Plex-Bold': 'IBMPlexSansArabic-Bold.ttf',
    }
    folder = _font_dir()
    for name, filename in fonts.items():
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            raise FileNotFoundError('Missing Arabic font: %s' % path)
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily(
        'Plex', normal='Plex', bold='Plex-Bold', italic='Plex', boldItalic='Plex-Bold',
    )
    return 'Plex', 'Plex-Bold', 'Plex-Semi', 'Plex-Med'


F, FB, FSB, FM = _register_fonts()


def ar(text):
    if not text:
        return ''
    return get_display(arabic_reshaper.reshape(str(text)))


def arp(html):
    parts = re.split(r'(<[^>]+>)', str(html))
    out = []
    for part in parts:
        if not part:
            continue
        if part.startswith('<'):
            out.append(part)
        else:
            out.append(ar(part))
    return ''.join(out)


BODY = ParagraphStyle(
    'BodyAr', fontName=F, fontSize=10.5, leading=17, textColor=INK, spaceAfter=7,
    alignment=TA_RIGHT,
)
CELL = ParagraphStyle('CellAr', parent=BODY, fontSize=9, leading=13.5, spaceAfter=0)
CELL_KEY = ParagraphStyle('CellKeyAr', parent=CELL, fontName=FSB, textColor=NAVY)
CELL_HEAD = ParagraphStyle('CellHeadAr', parent=CELL, fontName=FSB, textColor=colors.white, alignment=TA_CENTER)
H2 = ParagraphStyle(
    'H2Ar', fontName=FB, fontSize=13, leading=18, textColor=NAVY, spaceBefore=12,
    spaceAfter=6, keepWithNext=1, alignment=TA_RIGHT,
)
PAGE_TITLE = ParagraphStyle(
    'PageTitleAr', fontName=FB, fontSize=22, leading=28, textColor=NAVY, spaceAfter=4,
    alignment=TA_RIGHT,
)
TOC1 = ParagraphStyle(
    'TOC1Ar', fontName=FSB, fontSize=10.5, leading=16, textColor=NAVY, spaceBefore=6,
    alignment=TA_RIGHT,
)
TOC2 = ParagraphStyle(
    'TOC2Ar', fontName=F, fontSize=9.5, leading=14, rightIndent=20, textColor=MUTED,
    alignment=TA_RIGHT,
)
TILE_TITLE = ParagraphStyle(
    'TileTitleAr', fontName=FSB, fontSize=10, leading=14, textColor=NAVY,
    alignment=TA_RIGHT,
)
TILE_TEXT = ParagraphStyle(
    'TileTextAr', fontName=F, fontSize=8.5, leading=12.5, textColor=MUTED,
    alignment=TA_RIGHT,
)

CHAPTER_BLURBS = {
    1: 'ماذا يفعل النظام، ولوحة المعلومات، وأين تجده، ومن يستخدمه، وما الجديد في 19.0.1.0.29.',
    2: 'إعداد لمرة واحدة قبل بدء العمل اليومي.',
    3: 'الأرقام والهيكل ومتطلبات العمل والعهد والراتب والمستندات في شاشة واحدة.',
    4: 'التجربة والتجديد، ونموذج نهاية الخدمة (حساب أو مبلغ ثابت للمالية)، والاستقالة وإعادة التعيين.',
    5: 'أجهزة ZKTeco عبر BioTime، والورديات، والتأخير، والحضور اليومي.',
    6: 'أنواع الإجازات والرصيد السنوي والاعتمادات والعطلات والتصفية.',
    7: 'المأموريات بعملة المهمة مع أمر مأمورية قابل للطباعة.',
    8: 'دفعات العمل الإضافي من بصمات الحضور.',
    9: 'جزاءات قانون العمل، التوليد من الحضور، سبب قابل للمراجعة، وتأكيد جماعي.',
    10: 'السلف القصيرة والقروض طويلة الأجل والأقساط.',
    11: 'الدرجات الوظيفية ورابط التقديم والترتيب والمقابلات.',
    12: 'قوالب الأسئلة والدرجات والمخرجات والإنجاز الكلي.',
    13: 'تقارير الفترة PDF وExcel المنسّق وملف الموظف مع العهد وخط IBM Plex Sans Arabic.',
    14: 'كيف تصل سجلات الموارد البشرية إلى قسيمة الراتب.',
    15: 'قائمة مهام يومية وشهرية وسنوية.',
    16: 'المشكلات الشائعة وحلولها.',
    17: 'كيف تتواصل مع سوفت جايد تكنولوجي.',
}


def draw_logo(c, x, y, size, bg=TEAL, fg=colors.white):
    c.saveState()
    c.setFillColor(bg)
    c.roundRect(x, y, size, size, size * 0.22, stroke=0, fill=1)
    c.setFillColor(fg)
    c.setFont(FB, size * 0.42)
    c.drawCentredString(x + size / 2, y + size * 0.33, 'SG')
    c.restoreState()


def draw_ar(c, text, x, y, font, size, align='right'):
    c.setFont(font, size)
    shaped = ar(text)
    if align == 'right':
        c.drawRightString(x, y, shaped)
    elif align == 'center':
        c.drawCentredString(x, y, shaped)
    else:
        c.drawString(x, y, shaped)


class ChapterBanner(Flowable):
    def __init__(self, number, title, blurb=''):
        super().__init__()
        self.number, self.title, self.blurb = number, title, blurb
        self.toc_text = '%s. %s' % (number, title)
        self.keepWithNext = 1

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        self.box_h = 3.1 * cm if self.blurb else 2.4 * cm
        return avail_width, self.box_h + 0.5 * cm

    def draw(self):
        c, w, h, y0 = self.canv, self.width, self.box_h, 0.5 * cm
        c.saveState()
        path = c.beginPath()
        path.roundRect(0, y0, w, h, 9)
        c.clipPath(path, stroke=0, fill=0)
        c.setFillColor(NAVY)
        c.rect(0, y0, w, h, stroke=0, fill=1)
        c.setFillColor(NAVY_2)
        c.circle(1.0 * cm, y0 + h, 2.6 * cm, stroke=0, fill=1)
        c.setFillColor(TEAL)
        c.rect(w - 0.25 * cm, y0, 0.25 * cm, h, stroke=0, fill=1)
        c.restoreState()

        c.saveState()
        cx, cy = w - 1.55 * cm, y0 + h / 2
        c.setFillColor(TEAL)
        c.circle(cx, cy, 0.72 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(FB, 18)
        c.drawCentredString(cx, cy - 6.3, str(self.number))
        tx = w - 2.75 * cm
        top = y0 + h - 0.75 * cm
        c.setFillColor(TEAL_SOFT)
        draw_ar(c, 'الفصل %02d' % self.number, tx, top, FSB, 8)
        c.setFillColor(colors.white)
        draw_ar(c, self.title, tx, top - 0.68 * cm, FB, 16)
        if self.blurb:
            c.setFillColor(colors.HexColor('#C9D6E3'))
            from reportlab.lib.utils import simpleSplit
            shaped = ar(self.blurb)
            for i, line in enumerate(simpleSplit(shaped, F, 9.5, w - 3.6 * cm)[:2]):
                c.setFont(F, 9.5)
                c.drawRightString(tx, top - 1.25 * cm - i * 12, line)
        c.restoreState()


class Badge(Flowable):
    def __init__(self, text, color=TEAL, size=0.55 * cm, font_size=9):
        super().__init__()
        self.text, self.color, self.size, self.font_size = str(text), color, size, font_size

    def wrap(self, avail_width, avail_height):
        return self.size, self.size

    def draw(self):
        c, r = self.canv, self.size / 2
        c.setFillColor(self.color)
        c.circle(r, r, r, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(FB, self.font_size)
        c.drawCentredString(r, r - self.font_size * 0.35, self.text)


def menu(path):
    path = path.replace(' > ', ' &#8250; ').replace('>', '&gt;')
    return '<font name="%s" color="#0F2C4C" backColor="#E3EEF7">&nbsp;%s&nbsp;</font>' % (FSB, path)


def p(text):
    return Paragraph(arp(text), BODY)


def chapter(text):
    number, title = text.split('. ', 1)
    return ChapterBanner(int(number), title, CHAPTER_BLURBS.get(int(number), ''))


def section(text):
    match = re.match(r'^([\d.]+)\s+(.*)$', text)
    if match:
        para = Paragraph(
            '<font color="#13A89E">%s</font>&nbsp;&nbsp;%s' % (match.group(1), arp(match.group(2))),
            H2,
        )
    else:
        para = Paragraph(arp(text), H2)
    para._toc_text = text
    return para


def bullets(items):
    rows = [[Paragraph(arp(item), BODY), Badge('\u25aa')] for item in items]
    t = Table(rows, colWidths=[CONTENT_W - 0.7 * cm, 0.7 * cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t


def steps(items):
    rows = [[Paragraph(arp(item), BODY), Badge(i)] for i, item in enumerate(items, 1)]
    t = Table(rows, colWidths=[CONTENT_W - 0.95 * cm, 0.95 * cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (1, -1), 1.5),
        ('TOPPADDING', (0, 0), (0, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    return KeepTogether([t, Spacer(1, 4)]) if len(items) <= 5 else t


def table(headers, rows, widths):
    headers = list(reversed(headers))
    rows = [list(reversed(row)) for row in rows]
    widths = list(reversed(widths))
    scale = CONTENT_W / (sum(widths) * cm)
    data = [[Paragraph(arp(h), CELL_HEAD) for h in headers]]
    last = len(headers) - 1
    data += [[Paragraph(arp(c), CELL_KEY if i == last else CELL) for i, c in enumerate(row)] for row in rows]
    t = Table(data, colWidths=[w * cm * scale for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, LINE),
        ('BOX', (0, 0), (-1, -1), 0.6, LINE),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5.5),
    ]))
    return KeepTogether([t, Spacer(1, 10)]) if len(rows) < 12 else t


def callout(label, symbol, text, accent, bg):
    body = Paragraph(
        '<font name="%s" color="%s">%s</font><br/>%s' % (
            FSB, accent.hexval().replace('0x', '#'), arp(label), arp(text),
        ),
        CELL,
    )
    t = Table([[body, Badge(symbol, accent, 0.6 * cm, 10)]], colWidths=[CONTENT_W - 1.1 * cm, 1.1 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('RIGHTPADDING', (1, 0), (1, 0), 10),
        ('RIGHTPADDING', (0, 0), (0, 0), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 10)])


def tip(text):
    return callout('تنبيه', 'i', text, TEAL, TIP_BG)


def note(text):
    return callout('مهم', '!', text, ORANGE, WARN_BG)


def _ar_box_label(lines):
    return [ar(lines[0]), ar(lines[1])]


def flow_diagram():
    w, h = CONTENT_W, 150
    d = Drawing(w, h)
    main = [
        ('البصمة', 'الحضور'),
        ('الملخص', 'اليومي'),
        ('إضافي و', 'جزاءات'),
        ('تسويات', 'الراتب'),
        ('القسيمة', 'التالية'),
    ]
    feeders = {1: ('إجازة ومأموريات', 'وعطلات'), 3: ('مكافآت وسلف', 'وضرائب')}
    bw, bh, y = 80, 46, 92
    gap = (w - len(main) * bw) / (len(main) - 1)

    def box(x, y, lines, fill, text_color, stroke=None):
        shaped = _ar_box_label(lines)
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fill, strokeColor=stroke,
                   strokeWidth=0.8 if stroke else 0))
        d.add(String(x + bw / 2, y + bh / 2 + 2, shaped[0], fontName=FSB, fontSize=8,
                     fillColor=text_color, textAnchor='middle'))
        d.add(String(x + bw / 2, y + bh / 2 - 9, shaped[1], fontName=F, fontSize=8,
                     fillColor=text_color, textAnchor='middle'))

    def arrow(x1, y1, x2, y2, rtl=True):
        d.add(Line(x1, y1, x2, y2, strokeColor=TEAL, strokeWidth=1.6))
        if y1 == y2:
            d.add(Polygon([x1, y2, x1 + 6, y2 + 3.5, x1 + 6, y2 - 3.5], fillColor=TEAL, strokeWidth=0))
        else:
            d.add(Polygon([x2, y2, x2 - 3.5, y2 - 6, x2 + 3.5, y2 - 6], fillColor=TEAL, strokeWidth=0))

    items = list(reversed(main))
    feeder_map = {len(main) - 1 - k: v for k, v in feeders.items()}
    for i, lines in enumerate(items):
        x = i * (bw + gap)
        fill = TEAL if i == 0 else NAVY
        box(x, y, lines, fill, colors.white)
        if i < len(items) - 1:
            arrow(x + bw + 3, y + bh / 2, x + bw + gap - 3, y + bh / 2)
        if i in feeder_map:
            box(x, 14, feeder_map[i], PALE, NAVY, LINE)
            arrow(x + bw / 2, 14 + bh + 3, x + bw / 2, y - 3, rtl=False)
    return KeepTogether([Spacer(1, 4), d, Spacer(1, 8)])


def cover_tiles():
    items = [
        ('ملف الموظف', 'الرقم والهيكل وأنواع عهد قابلة للضبط والراتب والمستندات.'),
        ('العقود', 'تجربة 89 يوماً والتجديد وإعادة التعيين بنفس الرقم.'),
        ('الحضور', 'بصمة ZKTeco عبر BioTime والتأخير بعد 08:15.'),
        ('الإجازات', 'نظام 21 أو 30 يوماً والمرضية والعطلات والتصفية.'),
        ('المأموريات والإضافي', 'مأموريات جماعية وعمل إضافي 1.5 و 2.'),
        ('الجزاءات والمكافآت', 'توليد من الحضور وسبب واضح وتأكيد جماعي.'),
        ('السلف والقروض', 'أقساط لا تتجاوز إجمالي الراتب.'),
        ('التوظيف', 'الدرجات ورابط التقديم والمرشحون المرتبون.'),
        ('اللوحة والتقارير', 'سجلات الشركة أو الموظف، مع 20 تقريراً PDF وExcel.'),
    ]
    tile_w = (CONTENT_W - 2 * 0.3 * cm) / 3
    cells = []
    for title, text in items:
        inner = Table([[Paragraph(arp(title), TILE_TITLE)], [Paragraph(arp(text), TILE_TEXT)]], colWidths=[tile_w],
                      rowHeights=[None, 1.15 * cm])
        inner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PALE),
            ('LINEABOVE', (0, 0), (-1, 0), 2.5, TEAL),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        cells.append(inner)
    grid = Table([cells[i:i + 3] for i in range(0, 9, 3)], colWidths=[tile_w + 0.3 * cm] * 2 + [tile_w])
    grid.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (1, -1), 0.3 * cm),
        ('RIGHTPADDING', (2, 0), (2, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.3 * cm),
    ]))
    return grid


class ContactCard(Flowable):
    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return avail_width, 3.0 * cm

    def draw(self):
        c, w, h = self.canv, self.width, 2.6 * cm
        y0 = 0.2 * cm
        c.saveState()
        c.setFillColor(PALE)
        c.setStrokeColor(LINE)
        c.roundRect(0, y0, w, h, 8, stroke=1, fill=1)
        draw_logo(c, w - 2.0 * cm, y0 + (h - 1.4 * cm) / 2, 1.4 * cm)
        x = w - 2.4 * cm
        c.setFillColor(NAVY)
        draw_ar(c, COMPANY, x, y0 + h - 0.95 * cm, FB, 13)
        c.setFillColor(TEAL)
        c.setFont(FSB, 11)
        c.drawRightString(x, y0 + h - 1.6 * cm, SITE)
        c.setFillColor(MUTED)
        draw_ar(c, 'تنفيذ أودو، التخصيص، التدريب والدعم', x, y0 + h - 2.15 * cm, F, 9)
        c.restoreState()


class GuideDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=2.7 * cm, bottomMargin=2.2 * cm,
            title='%s - %s' % (TITLE, SUBTITLE), author=COMPANY, subject='دليل مستخدم وحدة الموارد البشرية',
            creator='%s - %s' % (COMPANY, SITE),
        )
        cover_frame = Frame(MARGIN, 3.0 * cm, CONTENT_W, PAGE_H - 16.2 * cm - 3.0 * cm, id='cover')
        body_frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='body')
        self.addPageTemplates([
            PageTemplate(id='cover', frames=[cover_frame], onPage=self._cover),
            PageTemplate(id='content', frames=[body_frame], onPage=self._page),
        ])

    def afterFlowable(self, flowable):
        if isinstance(flowable, ChapterBanner):
            level, logical = 0, flowable.toc_text
        elif isinstance(flowable, Paragraph) and flowable.style.name == 'H2Ar':
            level, logical = 1, getattr(flowable, '_toc_text', flowable.getPlainText().replace('\xa0', ' '))
        else:
            return
        key = 'h%s' % id(flowable)
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(logical, key, level=level, closed=level > 0)
        self.notify('TOCEntry', (level, ar(logical), self.page, key))

    def _cover(self, c, doc):
        band_h = 15.6 * cm
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, PAGE_H - band_h, PAGE_W, band_h, stroke=0, fill=1)
        path = c.beginPath()
        path.rect(0, PAGE_H - band_h, PAGE_W, band_h)
        c.clipPath(path, stroke=0, fill=0)
        c.setFillColor(NAVY_2)
        c.circle(2.5 * cm, PAGE_H - 2.0 * cm, 6.5 * cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor('#163B63'))
        c.circle(1.0 * cm, PAGE_H - band_h + 1.0 * cm, 3.6 * cm, stroke=0, fill=1)
        c.restoreState()

        c.saveState()
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - band_h - 0.35 * cm, PAGE_W, 0.35 * cm, stroke=0, fill=1)
        x = PAGE_W - MARGIN
        draw_logo(c, x - 1.35 * cm, PAGE_H - 3.3 * cm, 1.35 * cm)
        c.setFillColor(colors.white)
        draw_ar(c, COMPANY, x - 1.75 * cm, PAGE_H - 2.55 * cm, FB, 14)
        c.setFillColor(TEAL_SOFT)
        c.setFont(F, 10)
        c.drawRightString(x - 1.75 * cm, PAGE_H - 3.15 * cm, SITE)

        c.setFillColor(TEAL_SOFT)
        draw_ar(c, 'دليل المستخدم', x, PAGE_H - 7.0 * cm, FSB, 12)
        c.setFillColor(colors.white)
        draw_ar(c, TITLE, x, PAGE_H - 8.45 * cm, FB, 26)
        c.setFillColor(colors.HexColor('#D6E2EE'))
        draw_ar(c, 'إدارة الموارد البشرية - شرح كامل للاستخدام', x, PAGE_H - 9.5 * cm, FM, 14)
        c.setFillColor(TEAL)
        c.rect(x - 3.2 * cm, PAGE_H - 10.25 * cm, 3.2 * cm, 0.13 * cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor('#C9D6E3'))
        draw_ar(c, 'أُعد لخدمات تاركو للطيران - إدارة الموارد البشرية', x, PAGE_H - 11.1 * cm, F, 11)

        months = 'يناير فبراير مارس أبريل مايو يونيو يوليو أغسطس سبتمبر أكتوبر نوفمبر ديسمبر'.split()
        issued = 'صدر في %s %s %s' % (date.today().day, months[date.today().month - 1], date.today().year)
        label = 'أودو 19 إنتربرايز  |  %s  |  %s' % (VERSION, issued)
        shaped = ar(label)
        lw = pdfmetrics.stringWidth(shaped, F, 9) + 0.9 * cm
        c.setStrokeColor(TEAL_SOFT)
        c.setLineWidth(0.8)
        c.roundRect(x - lw, PAGE_H - 12.75 * cm, lw, 0.75 * cm, 0.375 * cm, stroke=1, fill=0)
        c.setFillColor(colors.white)
        draw_ar(c, label, x - 0.45 * cm, PAGE_H - 12.47 * cm, F, 9)

        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, 2.2 * cm, PAGE_W - MARGIN, 2.2 * cm)
        c.setFillColor(MUTED)
        draw_ar(c, 'حقوق النشر %s %s. جميع الحقوق محفوظة.' % (date.today().year, COMPANY), PAGE_W - MARGIN, 1.5 * cm, F, 8.5)
        c.setFillColor(NAVY)
        c.setFont(FB, 10)
        c.drawString(MARGIN, 1.5 * cm, SITE)
        c.restoreState()

    def _page(self, c, doc):
        c.saveState()
        top = PAGE_H - 1.75 * cm
        draw_logo(c, PAGE_W - MARGIN - 0.75 * cm, top, 0.75 * cm)
        c.setFillColor(NAVY)
        draw_ar(c, COMPANY, PAGE_W - MARGIN - 1.0 * cm, top + 0.4 * cm, FB, 9.5)
        c.setFillColor(MUTED)
        c.setFont(F, 8)
        c.drawRightString(PAGE_W - MARGIN - 1.0 * cm, top + 0.05 * cm, SITE)
        draw_ar(c, '%s  |  دليل المستخدم' % TITLE, MARGIN, top + 0.25 * cm, F, 8, align='left')
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, top - 0.3 * cm, PAGE_W - MARGIN, top - 0.3 * cm)

        c.line(MARGIN, 1.55 * cm, PAGE_W - MARGIN, 1.55 * cm)
        c.setFillColor(MUTED)
        c.setFont(F, 8)
        c.drawRightString(PAGE_W - MARGIN, 0.95 * cm, SITE)
        draw_ar(c, 'وحدة الموارد البشرية - أودو 19', PAGE_W / 2, 0.95 * cm, F, 8, align='center')
        label = '%d' % doc.page
        pw = max(0.9 * cm, pdfmetrics.stringWidth(label, FB, 8.5) + 0.5 * cm)
        c.setFillColor(NAVY)
        c.roundRect(MARGIN, 0.78 * cm, pw, 0.52 * cm, 0.26 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(FB, 8.5)
        c.drawCentredString(MARGIN + pw / 2, 0.95 * cm, label)
        c.restoreState()


def build_story():
    s = []
    s.append(Paragraph(arp('ماذا داخل الدليل'), ParagraphStyle(
        'CoverHeadAr', parent=TILE_TITLE, fontSize=12, spaceAfter=8,
    )))
    s.append(cover_tiles())
    s.append(NextPageTemplate('content'))
    s.append(PageBreak())

    s.append(Paragraph(arp('المحتويات'), PAGE_TITLE))
    s.append(Paragraph(
        arp('اضغط العنوان للانتقال إليه. القائمة نفسها متاحة كإشارات مرجعية في ملف PDF.'),
        ParagraphStyle('ContentsSubAr', parent=BODY, textColor=MUTED, spaceAfter=10),
    ))
    toc = TableOfContents()
    toc.levelStyles = [TOC1, TOC2]
    toc.dotsMinLevel = 1
    s.append(toc)
    s.append(PageBreak())

    s.append(chapter('1. مقدمة'))
    s.append(p('نظام موارد بشرية تاركو وحدة مخصصة لأودو 19 بُنيت وفق متطلبات خدمات تاركو للطيران '
               '(TAS/HRM الإصدار 01 بتاريخ 1 يناير 2024). توسّع تطبيقات الموظفين والحضور والإجازات والتوظيف والرواتب، '
               'فيبقى ما تعرفه في أودو كما هو، وتُضاف قواعد تاركو: رقم الموظف، تجربة 89 يوماً، التأخير بعد 08:15، '
               'العمل الإضافي 1.5 و 2، إجازات 21 أو 30 يوماً، جزاءات قانون العمل 1997، السلف والتقارير.'))
    s.append(section('1.1 أين تجده'))
    s.append(p('افتح تطبيق %s ثم قائمة %s. كل شاشات هذا الدليل تحت تلك القائمة.'
               % (menu('Employees'), menu('Tarco HRIS'))))
    s.append(table(['القائمة', 'ماذا تحتوي'], [
        ['لوحة المعلومات', 'بلاطات الأرقام مع عرض الرسوم (دونات، مدرج، أعمدة وخط). الموارد البشرية ترى الشركة. الموظف يرى سجلاته فقط.'],
        ['ملف الموظف', 'الموظفون (قائمة وهرم)، الهيكل الوظيفي، الإدارات، التعريف، متطلبات العمل، عهد الموظف وصرف العهدة.'],
        ['العقود', 'كل العقود. نهاية التجربة والتجديد ونهاية الخدمة (حساب أو مبلغ ثابت للمالية).'],
        ['الحضور', 'الورديات والملخص اليومي من بصمات الحضور.'],
        ['الإجازات', 'طلبات الإجازة والعطلات الرسمية وتصفية الإجازة.'],
        ['المأموريات', 'مأموريات بعملة المهمة وأمر مأمورية PDF.'],
        ['العمل الإضافي', 'دفعات تُحسب من البصمة.'],
        ['الجزاءات والمكافآت', 'القواعد، التوليد من الحضور، سبب واضح، تأكيد جماعي، المكافآت.'],
        ['السلف والقروض', 'سلفة قصيرة وقرض طويل وشراء بضاعة وخصومات أخرى.'],
        ['التوظيف', 'الوظائف بأسئلة الفرز والمتقدمون.'],
        ['المؤشرات', 'قوالب الأسئلة ومراجعات الأداء.'],
        ['التقارير', 'تقارير الفترة PDF وExcel وملف الموظف وإعداد قواعد الراتب.'],
        ['الإعداد', 'بيانات تجريبية، وأنواع العهد (أضف أو أعد تسمية أي بند تسلّمه الشركة).'],
    ], [4.2, 12.2]))
    s.append(section('1.2 من يفعل ماذا'))
    s.append(table(['الدور', 'الصلاحية'], [
        ['موظف موارد بشرية', 'وصول كامل لكل شاشات وتقارير تاركو.'],
        ['مدير موارد بشرية', 'كل ما للموظف، إضافة إلى إنشاء قواعد الراتب.'],
        ['مدير الإدارة', 'يطلب المأموريات ويوافق الإجازات ويملأ مؤشرات مرؤوسيه.'],
        ['الموظف', 'يفتح لوحة المعلومات لحضورِه وإجازته ومأمورياته وإضافيه وجزاءاته ومكافآته وسلفه وتصفيته وعُهدته ومتطلبات عمله ومؤشراته فقط. يطلب الإجازة من تطبيق الإجازات.'],
    ], [5.4, 11.0]))
    s.append(tip('تُمنح الصلاحية من %s. افتح المستخدم واضبط دور الموظفين.'
                 % menu('Settings > Users & Companies > Users')))
    s.append(section('1.3 كيف تتصل الأجزاء'))
    s.append(flow_diagram())
    s.append(bullets([
        '<b>رقم الموظف</b> هو المفتاح. يُولَّد من سنة وشهر الالتحاق (مثل 202610001)، ويظهر أمام الاسم، '
        'ويُكتب في أي حقل موظف للبحث، ويُنسخ إلى رقم البطاقة لجهاز البصمة إن كان فارغاً.',
        'تجمع ZKBioTime بصمات أجهزة ZKTeco، ويجلب أودو الموظفين والحضور منها (الفصل 5.2). يحوّلها النظام إلى '
        '<b>سطر حضور يومي</b> لكل موظف لكل يوم.',
        'تُكتب الإجازة المعتمدة والمأمورية المعتمدة والعطلة الرسمية على نفس السطر اليومي.',
        'الجزاءات والمكافآت والإضافي والسلف وخصم الإجازة وتصفية الإجازة والضريبة والتأمين تُرحَّل '
        '<b>تسويات راتب</b> وتظهر في القسيمة التالية تلقائياً.',
    ]))
    s.append(section('1.4 لوحة معلومات الموارد البشرية'))
    s.append(p('افتح %s. الشاشة الأولى هي اللوحة. التصميم واحد للجميع، والأرقام تتغير حسب الدور. اضغط <b>تحديث</b> بعد تأكيد أو ترحيل السجلات.'
               % menu('Employees > Tarco HRIS > Dashboard')))
    s.append(table(['من يفتحها', 'ماذا يرى'], [
        ['موظف أو مدير موارد بشرية', 'نظرة على الشركة: كل الموظفين، نهاية التجربة، تجديد العقود، المتقدمون، '
                                     'العطلات غير المنشورة، وحضور وإجازة ومأموريات وإضافي وجزاءات ومكافآت وسلف وتصفية ومؤشرات هذا الشهر.'],
        ['الموظف (بدون دور موارد بشرية)', 'سجلاته فقط. البلاطات والقوائم تقتصر على الموظف المرتبط بالمستخدم. '
                                          'لا تظهر ملفات الآخرين. إن لم يُربط موظف تظهر رسالة بذلك.'],
    ], [5.4, 11.0]))
    s.append(p('كل بلاطة تفتح القائمة المناسبة مفلترة. الصفحات تحت البلاطات تعرض آخر أيام التأخير أو الغياب، والإجازات، والمأموريات، والجزاءات، والمكافآت، والسلف، ومراجعات المؤشرات.'))
    s.append(p('عرض ثانٍ، %s، يرسم نفس البيانات حسب الدور. من لوحة البلاطات اضغط <b>رسوم</b> أو افتح القائمة مباشرة. الرسوم هي:'
               % menu('Tarco HRIS > Dashboard charts')))
    s.append(table(['الرسم', 'ماذا يعرض'], [
        ['مزيج الحضور (دونات)', 'أسطر هذا الشهر حسب الحالة: حاضر، متأخر، غائب، إجازة، مأمورية، عطلة، راحة.'],
        ['أنواع الإجازة (دونات)', 'أيام الإجازة المعتمدة هذا الشهر حسب النوع.'],
        ['الحضور اليومي (مدرج تكراري)', 'عدد الحاضرين والمتأخرين والغائبين لكل يوم.'],
        ['اتجاه التأخير (خط)', 'مجموع دقائق التأخير لكل يوم.'],
        ['إضافات الراتب (أعمدة)', 'مبالغ الإضافي والجزاءات والمكافآت والتصفية هذا الشهر.'],
        ['القوة حسب الإدارة (أعمدة)', 'الموظفون النشطون لكل إدارة. للموارد البشرية فقط.'],
    ], [5.4, 11.0]))
    s.append(p('مرّر صفحة الرسوم لترى كل المخططات. للحضور اليومي أيضاً عرضا الرسم والمحور: افتح %s وبدّل أيقونات العرض.'
               % menu('Tarco HRIS > Attendance > Daily attendance')))
    s.append(p('بلاطات للشاشات الجديدة: <b>متطلبات العمل</b> (البنود المفتوحة) و<b>العهد القائمة</b> '
               '(البنود المسلَّمة من أي نوع مضبوط) و<b>نهاية الخدمة للصرف</b> (مُرسلة للمالية). '
               'الموارد البشرية ترى الشركة، والموظف يرى سجلاته فقط.'))
    s.append(tip('يجب ربط الموظف في بطاقة المستخدم (%s). اللوحة تستخدم هذا الربط لإخفاء سجلات الآخرين.'
                 % menu('Settings > Users & Companies > Users')))
    s.append(section('1.5 ما الجديد في هذا الإصدار'))
    s.append(p('هذا الدليل يطابق <b>نظام تاركو 19.0.1.0.29</b>. حدّث الوحدة على Odoo.sh ثم استخدم القوائم أدناه.'))
    s.append(table(['الإصدار', 'ماذا أُضيف'], [
        ['19.0.1.0.29',
         'نهاية الخدمة نموذج: احسب مكافأة قانون العمل 1997 أو اكتب مبلغاً ثابتاً للمالية. '
         'إرسال للمالية يرحّل ربح تاركو على القسيمة التالية. اطبع التسوية. تُسترجع العهد المسلَّمة.'],
        ['19.0.1.0.28',
         'زر مفقود في قائمة العهد بجانب استرجاع. السطر الأحمر لا يُطلب عند الخروج.'],
        ['19.0.1.0.27',
         'أنواع العهد قابلة للضبط. أضف أو أعد تسمية أو أرشف أنواعاً في الإعداد > أنواع العهد '
         '(سماعة، مفاتيح، أدوات أو أي بند). صرف العهدة يعرض تلك الأنواع بدل أربعة خانات ثابتة.'],
        ['19.0.1.0.26',
         'صرف العهدة خطوة واحدة. حفظ السطر يسلّم فوراً. الاستقالة أو الفصل تسترجع كل العهد تلقائياً دون إرجاع بند بند.'],
        ['19.0.1.0.25',
         'الهيكل الوظيفي وهيكل الإدارات يُفتحان هرماً كاملاً. يظهر كل المديرين والإدارات دون الضغط على «عدد أشخاص» للدخول لكل فرع.'],
        ['19.0.1.0.24',
         'الهيكل الوظيفي هرم للموظفين والمدراء، وهيكل الإدارات؛ متطلبات العمل بعد القبول؛ عهد الموظف (حاسوب، جوال، زي، بطاقة)؛ '
         'استرجاع العهد عند نهاية الخدمة قبل تثبيت الاستقالة؛ بلاطات اللوحة؛ العهد في تقرير ملف الموظف.'],
        ['19.0.1.0.23',
         'تصدير Excel بألوان سوفت جايد: عنوان وأعمدة كحلي (#0F2C4C)، عناوين أقسام تركواز، صفوف متناوبة، تجميد الصف، تصفية، وأفقي A4.'],
        ['19.0.1.0.21',
         'المأمورية تنشئ اجتماع تقويم لكل موظف وتظهر في الحضور اليومي بحالة مأمورية (مسودة أو معتمدة أو منجزة).'],
        ['19.0.1.0.20',
         'تأكيد القسيمة يغلق تسويات المرة الواحدة لذلك الشهر. القرض يبقى جارياً حتى آخر قسط.'],
    ], [3.4, 13.0]))
    s.append(PageBreak())

    s.append(chapter('2. الإعداد لأول مرة'))
    s.append(p('نفّذ هذه الخطوات مرة واحدة وبهذا الترتيب قبل بدء العمل اليومي.'))
    s.append(steps([
        'أنشئ الإدارات والأقسام في %s. القسم إدارة تابعة لإدارتها الأم.'
        % menu('Employees > Configuration > Departments'),
        'راجع الورديات في %s. ورديتان جاهزتان: نهارية 08:00-16:00 ووردية 08:00-20:00 والجمعة راحة.'
        % menu('Tarco HRIS > Attendance > Shifts'),
        'أدخل عطلات السنة في %s واضغط <b>نشر في التقويم</b> لكل عطلة.'
        % menu('Tarco HRIS > Leave > Official holidays'),
        'راجع قواعد الجزاء في %s. حدّد مبلغ المخالفة وعدّل النص القانوني وفق قانون العمل 1997.'
        % menu('Tarco HRIS > Penalties and rewards > Penalty rules'),
        'أنشئ قوالب أسئلة المؤشرات في %s.' % menu('Tarco HRIS > KPIs > Question templates'),
        'تأكد أن كل هيكل راتب فيه قواعد تاركو. تُضاف عند التثبيت وكل يوم. لإضافتها فوراً يشغّل المدير %s.'
        % menu('Tarco HRIS > Reports > Create payroll rules'),
        'عيّن <b>الإدارة الأم</b> و<b>المدير</b> لكل إدارة، ثم <b>المدير</b> لكل موظف، حتى يظهر %s و %s هرماً لا قائمة مسطحة.'
        % (menu('Employee file > Organization chart'), menu('Employee file > Departments')),
        'راجع أنواع العهد في %s. الأنواع الأربعة الأولى (حاسوب، جوال، زي، بطاقة) يمكن إعادة تسميتها. '
        'اضغط جديد لإضافة أي بند آخر (سماعة، مفاتيح، شريحة، أدوات). علّم <b>يُعلَّم افتراضياً</b> للأنواع التي '
        'يجب أن تكون معلَّمة عند فتح صرف العهدة.'
        % menu('Tarco HRIS > Configuration > Custody types'),
        'أكمل ملف كل موظف ثم حدد الموظفين واضغط <b>تطبيق نظام الإجازة</b> من القائمة (أو الإجراءات) لإعطاء رصيد السنة.',
    ]))
    s.append(note('يجب أن يطابق رقم البطاقة رقم الموظف في BioTime. إذا وُلد الرقم والبطاقة فارغة تُنسخ إليه. '
                  'بطاقة مملوءة لا تُغيَّر.'))
    s.append(section('2.1 البيانات التجريبية'))
    s.append(p('لتجربة كل الشاشات افتح %s. علّم <b>تفعيل البيانات التجريبية</b> ثم <b>تطبيق</b>. يُنشئ أودو موظفين '
               'ومستندات وتعريفاً وعقوداً وحضوراً وإجازات وعطلات ومأمورية وإضافياً وجزاءات ومكافأة وسلفاً '
               'ووظيفة بمتقدمين ومراجعة مؤشرات وتسويات الراتب، وهرم إداري (عمر في القمة)، وهيكل إدارات، '
               'ومتطلبات عمل لسارة، وعهد مسلَّمة (حاسوب وجوال وزي وبطاقة)، وحاسوب خالد مُسترجع عند نهاية الخدمة.'
               % menu('Tarco HRIS > Configuration > Demo data')))
    s.append(p('ألغِ العلامة واضغط تطبيق لحذف <b>سجلات التجربة فقط</b>. سجلاتك تبقى. إعادة التفعيل تستبدل مجموعة التجربة.'))
    s.append(note('استخدم التجربة على قاعدة تدريب أو اختبار. لا تحمّلها على ملف الشركة الحي إن بدأ العمل الحقيقي.'))
    s.append(PageBreak())

    s.append(chapter('3. ملف الموظف'))
    s.append(p('كل بيانات الموظف من شاشة واحدة. افتح %s وأنشئ أو افتح موظفاً ثم صفحة <b>الملف</b>.'
               % menu('Tarco HRIS > Employee file > Employees')))
    s.append(section('3.1 حقول صفحة الملف'))
    s.append(table(['المجموعة', 'الحقول'], [
        ['الهوية', 'رقم الموظف، الإدارة، القسم، الوظيفة، المدير (أب الهرم الوظيفي)، تاريخ التعيين، الميلاد، الجنسية، الجنس، الحالة الاجتماعية، '
                   'الدين، المؤهل، التخصص، المدرسة، سنوات الخبرة.'],
        ['التواصل والعنوان', 'هاتف خاص، جوال العمل، هاتف الطوارئ، بريد خاص، بريد العمل، الولاية والمدينة والحي والمربع.'],
        ['العقد', 'نهاية التجربة، نهاية التجربة في الرواتب، نهاية العقد في الرواتب، تاريخ التجديد السنوي، تنبيه العقد، '
                  'مدة الخدمة، الاستقالة، إعادة التعيين، الوردية، الإعفاء من التأخير، حساب الإضافي.'],
        ['الراتب', 'الأساسي، غلاء المعيشة، بدل الترحيل، بدل السكن، بدلات أخرى، الإجمالي، الخضوع للضريبة والنسبة، '
                   'التأمين الاجتماعي والنسبة، تسوية الضرائب تلقائياً، شهر الترحيل.'],
        ['رصيد الإجازة', 'نظام 21 أو 30 يوماً، أيام عارضة، أيام اعتيادية.'],
        ['تصفية الإجازة', 'أيام ومبلغ هذا الشهر (زيادة على قسيمة هذا الشهر) وقائمة السجلات وتسوية الراتب المرتبطة.'],
        ['متطلبات العمل', 'قائمة بعد قبول الموظف: تدريب، سلامة، حاسوب، جوال، زي، بطاقة، مخزن، حسابات.'],
        ['عهد الموظف', 'ما تسلّمه من الشركة من أي نوع في الإعداد &gt; أنواع العهد. يُسترجع تلقائياً عند نهاية الخدمة.'],
        ['مستندات التعيين والمراجعة', 'سطر لكل مستند مع ملف مرفق.'],
    ], [3.8, 12.6]))
    s.append(section('3.2 إنشاء موظف جديد'))
    s.append(steps([
        'اضغط <b>جديد</b> واكتب الاسم.',
        'في الملف أدخل <b>تاريخ التعيين</b>. تُملأ نهاية التجربة (+89 يوماً) وتاريخ التجديد السنوي (+سنة).',
        'اترك <b>رقم الموظف</b> فارغاً. يُولَّد عند الحفظ (3.3).',
        'أكمل الهوية والتواصل والعنوان.',
        'أدخل مكونات الراتب. الإجمالي يُنسخ إلى أجر العقد.',
        'اختر نظام الإجازة والوردية.',
        'أضف المستندات وعلّم <b>تم الاستلام</b> عند وصول كل ملف.',
        'احفظ.',
    ]))
    s.append(section('3.3 أرقام الموظفين التلقائية'))
    s.append(p('الرقم = <b>سنة وشهر الالتحاق</b> ثم <b>تسلسل من 3 أرقام</b> لذلك الشهر. أرقام فقط لتصلح لجهاز البصمة.'))
    s.append(table(['الالتحاق', 'الترتيب في الشهر', 'الرقم'], [
        ['3 أكتوبر 2026', 'أول موظف', '202610001'],
        ['20 أكتوبر 2026', 'ثاني موظف', '202610002'],
        ['1 مارس 2024', 'أول موظف', '202403001'],
    ], [5.0, 5.0, 6.4]))
    s.append(bullets([
        '<b>موظف جديد:</b> يُنشأ الرقم عند الحفظ من تاريخ التعيين، أو الشهر الحالي إن خلا التاريخ. يمكنك كتابة رقم يدوياً.',
        '<b>موظفون قائمون:</b> حدّدهم في القائمة ثم %s. شهر الالتحاق من التعيين أو بداية العقد أو تاريخ الإنشاء. '
        'من ررقمه يطابق شهره يُتخطى.'
        % menu('Actions > Generate employee code'),
        '<b>فريد:</b> التسلسل يكمل أعلى رقم في ذلك الشهر بما فيه المؤرشفون، وقاعدة البيانات ترفض التكرار.',
    ]))
    s.append(note('توليد الأرقام لا يغيّر بطاقة مملوءة حتى تبقى البصمة مطابقة. غيّر الجهاز أو البطاقة بنفسك إن أردت الرقم الجديد.'))
    s.append(section('3.4 مستندات التعيين والمراجعة'))
    s.append(table(['المجموعة', 'الأنواع'], [
        ['مستند تعيين', 'شهادة ميلاد، مؤهل، خبرة، صورة، هوية، أخرى.'],
        ['مستند مراجعة', 'طلب توظيف، عقد، وصف وظيفي، إقرار لائحة العمل، أخرى.'],
    ], [3.8, 12.6]))
    s.append(section('3.5 أزرار الموظف'))
    s.append(table(['الزر', 'ماذا يفعل'], [
        ['تطبيق نظام الإجازة', 'ينشئ مخصصات العارضة والاعتيادي لهذه السنة. حدد عدة موظفين من القائمة ثم الزر أو الإجراءات. ما وُجد لهذه السنة يبقى. يُتخطى المستقيلون.'],
        ['ترحيل الضريبة والتأمين', 'خصم لمرة لهذا الشهر: إجمالي × النسبة. يظهر إن كانت التسوية التلقائية مغلقة.'],
        ['إشعار التعريف', 'يفتح إشعاراً للإدارات التي تجهّز الموظف الجديد.'],
        ['طباعة الملف', 'تقرير ملف الموظف مع اختيار الأقسام.'],
        ['صرف عهدة', 'نموذج يعرض كل نوع عهد نشط. علّم ما تسلّمه، املأ الصنف / الرقم / الكمية، ثم تسليم للموظف. أضف الأنواع في الإعداد &gt; أنواع العهد.'],
        ['نهاية الخدمة', 'يفتح نموذج نهاية الخدمة: احسب المكافأة أو اكتب مبلغاً ثابتاً ثم أرسل للمالية.'],
        ['تسجيل استقالة / تسجيل فصل / إعادة تعيين / تجديد عقد', 'انظر الفصل 4. الخروج يسترجع كل العهد المسلَّمة تلقائياً.'],
        ['الأزرار الذكية', 'المستندات، المأموريات، الجزاءات، المكافآت، السلف، تصفية الإجازة، المؤشرات، متطلبات العمل، العهد القائمة، نهاية الخدمة.'],
        ['إجراءات > توليد رقم موظف', 'ينشئ الرقم من شهر الالتحاق، ويمكن لعدة موظفين معاً.'],
    ], [4.6, 11.8]))
    s.append(section('3.6 إشعار التعريف'))
    s.append(p('لإبلاغ الإدارات عند التعيين: تدريب تعريفي، سلامة، حاسوب، مكتبة، زي، صرف مخزن.'))
    s.append(steps([
        'من الموظف اضغط <b>إشعار التعريف</b> أو افتح %s ثم جديد.'
        % menu('Tarco HRIS > Employee file > Onboarding notices'),
        'علّم البنود وأضف ملاحظة.',
        'اضغط <b>إشعار الإدارات</b>. تُنشر رسالة ويُنشأ نشاط للمدير ويُرسل بريد. ويُنشأ سطر <b>متطلب عمل</b> لكل بند معلَّم.',
    ]))
    s.append(p('الرسالة خطاب عادي: ترحيب، قائمة التجهيز، الوظيفة والإدارة وتاريخ البداية والمدير، ملاحظتك، وتوقيع الموارد البشرية. '
               'عنوان البريد: <b>أهلاً [الاسم] - ترتيبات التعريف</b>.'))
    s.append(section('3.7 البحث عن موظف'))
    s.append(p('اكتب الرقم أو الاسم في البحث أو في أي حقل موظف. يظهر الرقم بين قوسين مثل <b>[202610001] أحمد علي</b>. '
               'كتابة جزء مثل <b>202610</b> تعرض من التحقوا في ذلك الشهر.'))
    s.append(section('3.8 الهيكل الوظيفي والإداري'))
    s.append(p('الهيكل الوظيفي للموظفين والمدراء، والهيكل الإداري للإدارات، يُعرضان كهرم كامل من أول فتح — لا حاجة '
               'للضغط على كل مدير أو إدارة لرؤية من تحتهم. عيّن <b>المدير</b> على الموظف '
               '(الأب في الهرم) و<b>الإدارة الأم</b> و<b>المدير</b> على الإدارة.'))
    s.append(table(['القائمة', 'ماذا ترى'], [
        [menu('Employee file > Organization chart'),
         'الموظفون هرماً تحت مديرهم. اسحب بطاقة فوق مدير آخر لتغيير التبعية. نفس العرض على قائمة الموظفين.'],
        [menu('Employee file > Departments'),
         'الإدارات هرماً (العمليات تحت تاركو للطيران) مع مدير الإدارة وعدد الموظفين.'],
        ['نموذج الموظف، الهيكل التنظيمي',
         'المدير أعلاه والمرؤوسون أسفل الموظف المفتوح. المخطط الكامل يفتح الهرم.'],
    ], [5.6, 10.8]))
    s.append(tip('البيانات التجريبية تجعل عمر في القمة، وفاطمة وأحمد تحته، وسارة تحت فاطمة، والعمليات والمالية والموارد البشرية تحت تاركو للطيران.'))
    s.append(section('3.9 متطلبات العمل بعد القبول'))
    s.append(p('بعد قبول الموظف تتابع الموارد البشرية ما يلزم تجهيزه: تدريب، سلامة، حاسوب، جوال، زي، بطاقة، مخزن أو حسابات. افتح %s أو الزر الذكي متطلبات العمل.'
               % menu('Tarco HRIS > Employee file > Work requirements')))
    s.append(steps([
        'أرسل إشعار التعريف بالبنود المطلوبة، أو أنشئ متطلباً جديداً للموظف.',
        'عند إتمام المهمة اضغط <b>تم</b>.',
        'إن كان البند عُهدة مادية (حاسوب، جوال، زي، بطاقة) اضغط <b>صرف عهدة</b>. يُغلق المتطلب ويُنشأ سجل عهدة مسلَّمة.',
    ]))
    s.append(section('3.10 عهد الموظف'))
    s.append(p('العهدة ملك الشركة تُعطى للموظف بعد التعيين. الأنواع ليست ثابتة: تضيفها الموارد البشرية في %s. '
               'الحاسوب والجوال والزي والبطاقة جاهزة؛ أضف سماعة أو مفاتيح أو أدوات أو أي بند. الصرف خطوة واحدة. '
               'الاسترجاع يتم تلقائياً عند الاستقالة أو الفصل.'
               % menu('Tarco HRIS > Configuration > Custody types')))
    s.append(steps([
        'من الموظف اضغط <b>صرف عهدة</b> أو افتح %s.'
        % menu('Tarco HRIS > Employee file > Give custody'),
        'يعرض المعالج كل أنواع العهد النشطة. علّم ما تسلّمه. اكتب الموديل أو الرقم التسلسلي أو الكمية.',
        'لإصدار نوع غير موجود أضفه أولاً في %s (أو أنشئه من عمود النوع) ثم أعد فتح صرف العهدة.'
        % menu('Configuration > Custody types'),
        'اضغط <b>تسليم للموظف</b>. البنود المعلَّمة تُسجَّل مسلَّمة بتاريخ اليوم.',
        'أو أضف سطراً في قائمة العهد بصفحة الملف: النوع والوصف والرقم — الحفظ يسلّم فوراً.',
        'إن أُعيد بند مبكراً اضغط <b>استرجاع</b> على السطر. لا يلزم ذلك عند الخروج.',
        'إن لن يعود البند اضغط <b>مفقود</b> بجانب استرجاع. أكّد؛ يصبح السطر أحمر ولا يُطلب عند نهاية الخدمة.',
    ]))
    s.append(table(['الحالة', 'المعنى'], [
        ['مسلَّمة', 'مع الموظف. تظهر في العهد القائمة. سطر أزرق.'],
        ['مُسترجعة', 'أُعيدت. بالزر أو تلقائياً عند الاستقالة أو الفصل أو نهاية الخدمة. سطر أخضر.'],
        ['مفقودة', 'لن تعود. اضغط مفقود في القائمة. سطر أحمر. لا تُطلب عند الخروج.'],
    ], [3.4, 13.0]))
    s.append(note('الاسم والرمز و<b>يُعلَّم افتراضياً</b> لكل نوع في %s. أرشف نوعاً لإخفائه من صرف العهدة دون حذف السجل.'
                  % menu('Configuration > Custody types')))
    s.append(table(['حقل نوع العهد', 'الاستخدام'], [
        ['الاسم', 'يظهر في صرف العهدة وعلى السطور المسلَّمة. ترجمه إن عملت بالعربية.'],
        ['الرمز', 'مفتاح قصير فريد (laptop أو headset). المسافات تصبح شرطات سفلية ويُحفظ بأحرف صغيرة.'],
        ['يُعلَّم افتراضياً', 'يُعلَّم الصف عند فتح صرف العهدة.'],
        ['التسلسل', 'ترتيب الصفوف في صرف العهدة.'],
        ['نشط', 'ألغِ العلامة للأرشفة. السجلات القديمة تبقى؛ صرف العهدة لا يعرض النوع.'],
    ], [4.2, 12.2]))
    s.append(table(['عمود صرف العهدة', 'الاستخدام'], [
        ['تسليم', 'علّم الأنواع التي تسلّمها الآن.'],
        ['النوع', 'أي نوع عهد نشط. أضف سطراً أو أنشئ نوعاً من هذا العمود.'],
        ['الصنف / الموديل', 'نص حر مثل Dell Latitude.'],
        ['الرقم التسلسلي', 'رقم الأصل أو IMEI أو رقم البطاقة.'],
        ['الكمية', 'القطع (زي، مفاتيح). واحد على الأقل.'],
    ], [4.2, 12.2]))
    s.append(PageBreak())

    s.append(chapter('4. عقود العمل'))
    s.append(p('تواريخ العقد على الموظف. استخدم %s لرؤية التعيين والتجربة ونهاية العقد والاستقالة وإعادة التعيين ومدة الخدمة.'
               % menu('Tarco HRIS > Contracts > Contracts')))
    s.append(section('4.1 تواريخ التجربة والتجديد'))
    s.append(bullets([
        '<b>نهاية التجربة</b> = التعيين + 89 يوماً وتُنسخ إلى نهاية التجربة في صفحة <b>الرواتب</b>. إن غيّرتها يدوياً تُعلَّم '
        '<b>التجربة محددة يدوياً</b>. %s يعرض فقط من تقع نهاية تجربتهم في الرواتب خلال 10 أيام.'
        % menu('Contracts > Probation ending'),
        '<b>نهاية العقد</b> من صفحة <b>الرواتب</b>. %s يعرض فقط من تنتهي عقودهم خلال 10 أيام. العقود بلا نهاية لا تظهر.'
        % menu('Contracts > Renewals due'),
        '<b>تاريخ التجديد السنوي</b> = التعيين + سنة للمراجعة فقط، ولا يُدخل الموظف في قائمة التجديدات.',
        'نهاية التجربة والإجمالي يُنسخان إلى عقد أودو.',
    ]))
    s.append(section('4.2 تنبيهات قبل 7 إلى 10 أيام'))
    s.append(p('كل يوم يبحث الإجراء المجدول عن نهايات التجربة و<b>نهاية العقد في الرواتب</b> خلال 10 أيام، وينشئ مهمة '
               'لمسؤول العقد أو المدير ويرسل بريداً. كل تاريخ يُنبَّه مرة واحدة.'))
    s.append(p('القائمتان %s و %s تستخدمان مرشحي <b>نهاية التجربة (10 أيام)</b> و <b>انتهاء العقد (10 أيام)</b>.'
               % (menu('Contracts > Probation ending'), menu('Contracts > Renewals due'))))
    s.append(section('4.3 التجديد والاستقالة وإعادة التعيين'))
    s.append(table(['الإجراء', 'كيف', 'النتيجة'], [
        ['تجديد العقد', 'اضغط <b>تجديد العقد</b>.', 'يتقدم تاريخ التجديد سنة.'],
        ['استقالة', 'اضغط <b>تسجيل استقالة</b>. حدّد آخر يوم عمل. تظهر العهد للعلم فقط. اضغط <b>تأكيد واسترجاع العهد</b>.',
         'يُثبت تاريخ الاستقالة. كل بند عهد مسلَّم (أي نوع) يُسترجع تلقائياً.'],
        ['فصل', 'اضغط <b>تسجيل فصل</b>. نفس التأكيد بخطوة واحدة.',
         'يُثبت آخر يوم عمل كفصل. تُسترجع كل العهد تلقائياً.'],
        ['إعادة تعيين', 'ألغِ الأرشفة إن لزم ثم <b>إعادة تعيين</b>.', 'نفس الموظف ونفس الرقم. تجربة وتجديد من اليوم. تاريخ التعيين الأصلي يبقى.'],
    ], [3.4, 5.4, 7.6]))
    s.append(section('4.4 صرف نهاية الخدمة'))
    s.append(p('استخدم نموذج نهاية الخدمة عندما يلزم المالية صرف مكافأة الترك. افتحه من الموظف (<b>نهاية الخدمة</b>) أو من %s.'
               % menu('Tarco HRIS > Contracts > End of service')))
    s.append(steps([
        'اختر الموظف وآخر يوم عمل والسبب (استقالة أو فصل أو نهاية عقد أو تقاعد).',
        'اترك <b>المبلغ</b> على حساب ليطبّق قانون العمل 1997: نصف شهر من آخر إجمالي لكل سنة من الخمس الأولى، ثم شهر كامل لكل سنة بعدها. تُحتسب أجزاء السنة.',
        'أو اختر <b>مبلغ ثابت</b> واكتب ما يجب أن تصرفه المالية. المبلغ المحسوب يبقى للمرجع.',
        'علّم <b>فصل لسوء السلوك</b> فقط إن لا مكافأة. يصبح المحسوب صفراً.',
        'اضغط <b>إرسال للمالية</b>. تُسترجع العهد ويُثبت آخر يوم عمل ويُرحَّل ربح تاركو للقسيمة. اطبع التسوية للملف وللمالية.',
        'عند تأكيد القسيمة تصبح الحالة مدفوعة. إن صُرف خارج الرواتب اضغط <b>تعليم مدفوع</b>.',
    ]))
    s.append(table(['الحالة', 'المعنى'], [
        ['مسودة', 'الموارد البشرية تعدّ النموذج. يمكن الحساب أو كتابة المبلغ.'],
        ['أُرسلت للمالية', 'ربح تاركو على القسيمة التالية. اطبع التسوية للمالية.'],
        ['مدفوعة', 'قسيمة مؤكدة، أو تعليم مدفوع بعد صرف خارج الرواتب.'],
        ['ملغاة', 'لا صرف. يُغلق سطر الرواتب.'],
    ], [3.4, 13.0]))
    s.append(note('تسجيل الاستقالة ما زال لآخر يوم عمل بلا صرف. استخدم نهاية الخدمة عندما يلزم مبلغ للمالية.'))
    s.append(section('4.5 الخصومات النظامية'))
    s.append(p('في الملف علّم <b>خاضع للضريبة</b> و/أو <b>خاضع للتأمين</b> وأدخل النسب. ثم اختر <b>تسوية الضرائب تلقائياً</b>.'))
    s.append(table(['تسوية تلقائية', 'ماذا يحدث كل شهر'], [
        ['معلّمة', 'في أول الشهر ينشئ الإجراء تسويتي الضريبة والتأمين (إجمالي × %) وتُخصم من قسيمة الشهر. زر الترحيل يُخفى.'],
        ['غير معلّمة', 'يضغط موظف الموارد <b>ترحيل الضريبة والتأمين</b> مرة كل شهر قبل تشغيل الرواتب.'],
    ], [4.2, 12.2]))
    s.append(bullets([
        'حقل <b>الضرائب مُرحَّلة عن</b> يظهر آخر شهر. لا يُرحَّل الشهر مرتين.',
    ]))
    s.append(PageBreak())

    s.append(chapter('5. الحضور والبصمة'))
    s.append(section('5.1 الورديات'))
    s.append(p('الوردية تحدد البداية والنهاية والسماح والدقائق المدفوعة وبداية الإضافي وأيام الراحة.'))
    s.append(section('5.2 أجهزة البصمة و BioTime'))
    s.append(p('تجمع <b>ZKBioTime</b> البصمات من الأجهزة. أودو يرتبط بخادم BioTime ويجلب الموظفين وحركات الدخول والخروج.'))
    s.append(table(['من BioTime', 'ماذا يفعل أودو'], [
        ['الموظفون', 'يُطابق رقم الموظف في BioTime مع <b>رقم البطاقة</b> في أودو.'],
        ['الحركات', 'تُحوَّل إلى حضور أودو ثم إلى الملخص اليومي.'],
    ], [4.0, 12.4]))
    s.append(note('يجب أن يصل خادم أودو إلى BioTime، وأن تكون ساعة المنطقة صحيحة حتى لا يُحسب تأخير خاطئ.'))
    s.append(section('5.3 الحضور اليومي'))
    s.append(p('كل يوم يُلخَّص آخر ثلاثة أيام في %s: أول دخول وآخر خروج والساعات ودقائق التأخير والإضافي. '
               'يمكنك مزامنة فترة من تقرير الفترة بزر <b>مزامنة البصمة</b>.'
               % menu('Attendance > Daily attendance')))
    s.append(table(['الحالة', 'متى'], [
        ['حاضر', 'دخل في الوقت وخرج.'],
        ['متأخر', 'دخل بعد السماح. تظهر الدقائق.'],
        ['غائب', 'لا بصمة في يوم عمل بلا إجازة أو مأمورية أو عطلة.'],
        ['إجازة', 'إجازة معتمدة تغطي اليوم.'],
        ['مأمورية', 'مأمورية (مسودة أو معتمدة أو منتهية) تغطي اليوم لذلك الموظف.'],
        ['عطلة رسمية', 'عطلة بلا بصمة.'],
        ['راحة', 'يوم راحة الوردية بلا بصمة.'],
        ['خروج ناقص', 'دخل ولم يخرج. صحّح ثم زامن.'],
    ], [3.6, 12.8]))
    s.append(section('5.4 حساب اليوم'))
    s.append(bullets([
        'الخروج مع نهاية الوردية يعطي اليوم المدفوع كاملاً (8 ساعات).',
        'الإضافي بعد <b>بداية الإضافي</b>.',
        'يُدفع 1.5 من السبت للخميس و 2 يوم الجمعة والعطلة.',
        'أجر الساعة = الإجمالي / 30 / 8.',
        'اختر <b>لا تُدفع الإضافي</b> لتسجيل الساعات دون دفع.',
    ]))
    s.append(PageBreak())

    s.append(chapter('6. الإجازات'))
    s.append(section('6.1 الأنواع'))
    s.append(table(['النوع', 'القواعد'], [
        ['اعتيادي', 'من الرصيد السنوي. يعتمدها المدير ثم الموارد البشرية.'],
        ['عارضة', 'من الرصيد (6 أيام). يعتمدها المدير ثم الموارد البشرية.'],
        ['مرضية', 'منفصلة بلا رصيد. يمكن إرفاق تقرير طبي. تعتمدها الموارد البشرية.'],
        ['إجازة عطلة رسمية', 'للعطلات المأخوذة. تعتمدها الموارد البشرية.'],
    ], [4.0, 12.4]))
    s.append(section('6.2 الرصيد السنوي'))
    s.append(p('نظام 21 يوماً = 6 عارضة + 15 اعتيادي، أو 30 يوماً = 6 + 24. في أول السنة افتح قائمة الموظفين، حدد من يحتاج رصيداً، واضغط <b>تطبيق نظام الإجازة</b> من رأس القائمة أو الإجراءات. زر النموذج ما زال يطبّق موظفاً واحداً. ما وُجد لهذه السنة يبقى. يُتخطى المستقيلون. تظهر رسالة بعدد من حصل على مخصصات ومن كان لديه ومن تُخطي.'))
    s.append(section('6.3 الطلب والاعتماد'))
    s.append(steps([
        'يفتح المدير %s أو تطبيق الإجازات وينشئ الطلب.' % menu('Tarco HRIS > Leave > Leave requests'),
        'اختر النوع والتواريخ. يظهر الرصيد و<b>المأخوذ هذا الشهر</b>.',
        'اختر الخصم: من الرصيد / كامل الأجر، أو خصم من الراتب، أو خصم جزئي بنسبة.',
        'يعتمد المدير ثم الموارد البشرية.',
    ]))
    s.append(section('6.4 العطلات الرسمية'))
    s.append(steps([
        'افتح %s ثم جديد.' % menu('Tarco HRIS > Leave > Official holidays'),
        'أدخل الاسم والتاريخ الأصلي، وإن نُقلت العطلة أدخل <b>نُقلت إلى</b>.',
        'اضغط <b>نشر في التقويم</b>. تصبح الحالة <b>منشورة</b> ويختفي زر النشر ويظهر تحديث/إزالة. '
        'بعد نقل التاريخ اضغط تحديث في التقويم.',
    ]))
    s.append(section('6.5 تصفية الإجازة (بيع الرصيد)'))
    s.append(steps([
        'افتح %s ثم جديد.' % menu('Tarco HRIS > Leave > Leave encashment'),
        'اختر الموظف والأيام. السعر اليومي الافتراضي الإجمالي / 30.',
        'اضغط <b>تأكيد</b>. يُرحَّل المبلغ تسوية ربح (Tarco Earning) ويُدفع زيادة على قسيمة ذلك الشهر.',
    ]))
    s.append(p('على الموظف زر <b>تصفية الإجازة</b> يفتح السجلات. صفحة الملف تعرض <b>أيام التصفية هذا الشهر</b> '
               'و<b>مبلغ التصفية هذا الشهر</b> — الزيادة المؤكدة للشهر الجاري — مع قائمة السجلات وتسوية الراتب.'))
    s.append(PageBreak())

    s.append(chapter('7. المأموريات'))
    s.append(p('يطلبها مدير الإدارة أو الموارد البشرية في أي وقت، ويمكن ضم عدة موظفين دون فتح كل ملف.'))
    s.append(section('7.1 الإنشاء والاعتماد'))
    s.append(steps([
        'افتح %s ثم جديد.' % menu('Tarco HRIS > Missions'),
        'أدخل المكان والغرض وتاريخي البداية والنهاية ووقت المغادرة والعودة.',
        'اختر <b>عملة المأمورية</b>، مثلاً دولار لمأمورية خارجية. الافتراضي عملة الشركة.',
        'أدخل التكلفة للشخص في اليوم بعملة المأمورية إن وُجد بدل.',
        'أضف الموظفين في الأسطر بالرقم أو الاسم.',
        'احفظ. يُحجز كل موظف في تقويمه لتلك التواريخ، ويصبح حضوره اليومي <b>مأمورية</b>.',
        'تعتمد الموارد البشرية. يبقى التقويم والحضور مأمورية.',
        'اضغط <b>منتهية</b> بعد العودة أو <b>إلغاء</b> لإزالتها من التقويم والحضور.',
    ]))
    s.append(section('7.2 التقويم والحضور'))
    s.append(p('بعد الحفظ تظهر المأمورية في تقويم أودو لكل موظف على حدة، وفي تقويم المأموريات، وفي الحضور اليومي بحالة مأمورية فلا يُحتسب غياباً. زر <b>فتح التقويم</b> يفتح الاجتماعات. الإلغاء يحذفها ويعيد حساب الحضور. المأموريات الحالية تُحجز عند الترقية إلى 19.0.1.0.21.'))
    s.append(section('7.3 طباعة أمر المأمورية'))
    s.append(p('اضغط <b>طباعة أمر المأمورية</b> أو من القائمة %s. يُطبع على ترويسة الشركة بخط IBM Plex Sans Arabic.'
               % menu('Print > Mission Order')))
    s.append(PageBreak())

    s.append(chapter('8. العمل الإضافي'))
    s.append(p('يُحسب من البصمة (الفصل 5). الدفعة تجمع فترة وترسلها للرواتب.'))
    s.append(steps([
        'افتح %s ثم جديد.' % menu('Tarco HRIS > Overtime'),
        'أدخل الفترة وإن لزم الإدارة.',
        'اضغط <b>ملء من البصمة</b>. يظهر سطر لكل موظف: ساعات 1.5 و 2 والمبلغ.',
        'راجع ثم <b>تأكيد وترحيل</b>. يُضاف المبلغ للقسيمة التالية.',
    ]))
    s.append(PageBreak())

    s.append(chapter('9. الجزاءات والمكافآت'))
    s.append(section('9.1 قواعد الجزاء'))
    s.append(p('القواعد في %s. لكل قاعدة نص قانوني وطريقة حساب.'
               % menu('Penalties and rewards > Penalty rules')))
    s.append(table(['الحساب', 'المبلغ'], [
        ['مبلغ ثابت', 'المبلغ على القاعدة.'],
        ['أيام أجر', 'الأيام × الإجمالي / 30.'],
        ['ساعات أجر', 'الساعات × الإجمالي / 30 / 8.'],
        ['نسبة من الأساسي', 'الأساسي × النسبة.'],
    ], [5.0, 11.4]))
    s.append(p('ثلاث قواعد جاهزة: <b>تأخير</b> (ساعات)، <b>غياب</b> (يوم أجر)، <b>مخالفة</b> (مبلغ ثابت).'))
    s.append(section('9.2 التوليد من الحضور'))
    s.append(p('المعالج لا يخترع جزاءات. يقرأ <b>الحضور اليومي</b> وينشئ <b>مسودة لكل موظف لكل يوم</b> يستوفي الشرط.'))
    s.append(table(['الخيار', 'متى يُنشأ', 'المبلغ'], [
        ['تضمين التأخير', 'دقائق تأخير بعد بداية الوردية + السماح (افتراضي 08:00 + 15 دقيقة). المعفى يُتخطى.',
         'ساعات التأخير × أجر الساعة. قاعدة التأخير.'],
        ['تضمين الغياب', 'الحالة غائب: يوم عمل بعد التعيين وقبل الاستقالة بلا دخول، وليس إجازة أو مأمورية أو عطلة أو راحة.',
         'يوم أجر. قاعدة الغياب.'],
    ], [3.6, 8.4, 4.4]))
    s.append(p('يوم له جزاء غير ملغى لنفس القاعدة والتاريخ لا يُكرَّر. جزاء المخالفة لا يُولَّد هنا.'))
    s.append(section('9.3 السبب في كل جزاء مولَّد'))
    s.append(p('يُملأ حقل <b>السبب</b> بوقائع الحضور للمراجعة قبل التأكيد: النوع والتاريخ والموظف والرقم، '
               'والوردية، والدخول والخروج أو لا شيء، ودقائق التأخير بعد حد السماح، وهل اليوم إجازة أو مأمورية أو عطلة أو راحة.'))
    s.append(p('عمود السبب ظاهر في القائمة. المسودات القديمة بالنص القانوني: حدّدها واضغط <b>ملء السبب من الحضور</b> '
               'أو أعد التوليد لنفس التواريخ — تُحدَّث المسودات دون تكرار.'))
    s.append(section('9.4 التوليد والتأكيد الجماعي'))
    s.append(steps([
        'افتح %s.' % menu('Penalties and rewards > Generate from attendance'),
        'اختر الفترة وإن لزم الإدارة، وعلّم تأخيراً و/أو غياباً.',
        'اضغط <b>توليد</b>. تُفتح قائمة المسودات بسبب واضح.',
        'اقرأ السبب. ألغِ ما لا يطابق (مثلاً بصمة ناقصة).',
        'حدّد المسودات واضغط <b>تأكيد المحدد</b> أو %s. المسودة فقط تُرحَّل للرواتب.'
        % menu('Actions > Confirm penalties'),
    ]))
    s.append(tip('يمكن تأكيد عشرات المسودات دفعة واحدة. لا تؤكد سطراً قبل مطابقة السبب مع الحضور اليومي.'))
    s.append(section('9.5 جزاء المخالفة'))
    s.append(p('أنشئ الجزاء يدوياً من %s، اختر القاعدة، أضف الموظفين بالرقم أو الإدارة، ثم <b>تأكيد</b>.'
               % menu('Penalties and rewards > Penalties')))
    s.append(section('9.6 المكافآت'))
    s.append(p('من %s: الموظف والسبب والتاريخ ومبلغ أو أيام أجر ثم تأكيد. تُضاف للقسيمة التالية.'
               % menu('Penalties and rewards > Rewards')))
    s.append(PageBreak())

    s.append(chapter('10. السلف والقروض'))
    s.append(table(['النوع', 'الاسترداد'], [
        ['سلفة قصيرة', 'خصم مرة من راتب شهر الاستحقاق.'],
        ['قرض طويل', 'أقساط شهرية متساوية من تاريخ الاستحقاق.'],
        ['شراء بضاعة', 'كالقرض: قسط أو أكثر.'],
        ['خصم آخر', 'أي خصم بواحد أو أكثر من الأقساط.'],
    ], [4.0, 12.4]))
    s.append(note('القسط الشهري لا يجوز أن يتجاوز إجمالي الراتب.'))
    s.append(PageBreak())

    s.append(chapter('11. التوظيف'))
    s.append(p('الوظائف بأسئلة فرز. رابط التقديم العام يجمع المتقدمين. رتّبهم ثم حدّد مقابلة. '
               'إرسال وقت المقابلة يضع اجتماعاً في تقويم أودو ويظهر في الزر الذكي أعلى المتقدم.'))
    s.append(PageBreak())

    s.append(chapter('12. مؤشرات الأداء'))
    s.append(p('قوالب أسئلة بأوزان. المراجعة تحمل القالب، تسجّل الدرجات والمخرجات اليومية، وتحسب الإنجاز الكلي وساعات الحضور.'))
    s.append(PageBreak())

    s.append(chapter('13. التقارير'))
    s.append(section('13.1 تقارير الفترة'))
    s.append(p('من %s اختر التقرير والفترة ثم <b>طباعة</b> أو <b>تصدير Excel</b>.'
               % menu('Tarco HRIS > Reports > Period reports')))
    s.append(section('13.2 تقرير ملف الموظف'))
    s.append(p('من الموظف <b>طباعة الملف</b> واختر الأقسام بما فيها العهد ومتطلبات العمل وتصفية الإجازة لهذا الشهر. '
               'قسم العهد يطبع الرقم واسم النوع (من الإعداد &gt; أنواع العهد) والصنف والرقم التسلسلي والحالة.'))
    s.append(p('من نموذج نهاية الخدمة اضغط <b>طباعة</b> لتسوية المالية: الموظف ومدة الخدمة والمبلغ المحسوب أو الثابت ومبلغ الصرف وتواقيع الموارد والمالية والموظف.'))
    s.append(section('13.3 الخط العربي في PDF'))
    s.append(p('كل تقارير تاركو PDF — تقارير الفترة وملف الموظف وأمر المأمورية وتسوية نهاية الخدمة — تُطبع بخط <b>IBM Plex Sans Arabic</b> '
               'لتظهر الأسماء والنصوص القانونية العربية بوضوح بجانب الإنجليزية. النص اللاتيني بخط DejaVu حتى لا تتضاعف الحروف في wkhtmltopdf.'))
    s.append(section('13.4 تنسيق تصدير Excel'))
    s.append(p('اضغط <b>تصدير Excel</b> على أي تقرير فترة. الملف لم يعد ورقة بيضاء. كل ملف يستخدم ألوان سوفت جايد:'))
    s.append(table(['جزء الورقة', 'كيف يبدو'], [
        ['الصف 1 — الشركة وعنوان التقرير', 'شريط كحلي (#0F2C4C) ونص أبيض 16 نقطة.'],
        ['الصف 2 — الفترة', 'عنوان فرعي رمادي فاتح.'],
        ['الصف 3 — اسم القسم', 'عنوان تركواز (#13A89E).'],
        ['الصف 4 — رؤوس الأعمدة', 'كحلي وأبيض في الوسط مع التفاف. التجميد عند A5 مع تصفية.'],
        ['صفوف البيانات', 'Calibri 10 وحدود #C5CDD6 وتظليل متناوب #F4F7FA وتنسيق أرقام وتواريخ.'],
        ['إعداد الصفحة', 'أفقي A4 وملاءمة العرض وترويسة باسم التقرير.'],
    ], [5.4, 11.0]))
    s.append(note('إن بدا التصدير بلا تنسيق حدّث إلى 19.0.1.0.23 أو أحدث ثم صدّر من جديد. لا تعِد استخدام ملف حُفظ قبل التحديث.'))
    s.append(PageBreak())

    s.append(chapter('14. الربط مع الرواتب'))
    s.append(p('النظام لا يغيّر حساب القسيمة. ينشئ تسويات في %s تلتقطها القسيمة التالية.'
               % menu('Payroll > Employees > Salary Adjustments')))
    s.append(table(['المصدر', 'نوع التسوية', 'الأثر'], [
        ['مكافآت، إضافي، تصفية إجازة، نهاية الخدمة', 'ربح تاركو', 'يُضاف للإجمالي'],
        ['جزاءات، سلف، خصم إجازة، ضريبة، تأمين', 'خصم تاركو', 'يُخصم من الصافي'],
    ], [6.4, 3.6, 6.4]))
    s.append(section('14.1 بعد إنجاز القسيمة'))
    s.append(p('عند تأكيد القسيمة (منجزة / معتمدة) يسجّل النظام شهر الرواتب على التسويات المرتبطة. لا يلزم تعليم القسيمة مدفوعة.'))
    s.append(table(['التسوية', 'ماذا يحدث بعد إنجاز القسيمة'], [
        ['لمرة واحدة (إضافي، مكافأة، جزاء، ضريبة، تأمين، تصفية، خصم إجازة، سلفة شهر واحد)',
         'تصبح الحالة مغلقة. المبلغ المدفوع يساوي مبلغ الشهر. لا تظهر في القسيمة التالية.'],
        ['قرض جارٍ أو سلفة لعدة أشهر',
         'تبقى جارية. يُعلَّم قسط هذا الشهر فقط مدفوعاً وينقص المتبقي. تُغلق عند قسط القسيمة الأخيرة.'],
    ], [6.2, 10.2]))
    s.append(tip('بعد تأكيد رواتب أكتوبر افتح %s: يجب أن يكون إضافي أكتوبر والضريبة والمكافأة مغلقة. قرض الجهاز يبقى جارياً بمتبقٍ أقل.'
                 % menu('Payroll > Employees > Salary Adjustments')))
    s.append(PageBreak())

    s.append(chapter('15. الروتين اليومي والشهري'))
    s.append(table(['متى', 'من', 'المهمة'], [
        ['يومياً', 'الموارد البشرية والموظفون', 'افتح بلاطات اللوحة ثم رسوم اللوحة، واعمل على كل بلاطة فيها رقم.'],
        ['يومياً', 'الموارد البشرية', 'راجع أنشطة التجربة والتجديد. أصلح الخروج الناقص.'],
        ['يومياً', 'المديرون', 'اطلب إجازة ومأموريات للفريق.'],
        ['يومياً', 'الموارد البشرية', 'اعتمد الإجازات والمأموريات. اصرف العهدة من الأنواع المضبوطة. راجع العهد القائمة. استخدم نهاية الخدمة لإرسال مبلغ الترك للمالية.'],
        ['نهاية الشهر', 'الموارد البشرية', 'ولّد جزاءات التأخير والغياب، راجع السبب، ثم تأكيد المحدد.'],
        ['نهاية الشهر', 'الموارد البشرية', 'أنشئ دفعة الإضافي وأكّدها.'],
        ['نهاية الشهر', 'الموارد البشرية', 'رحّل الضريبة لمن بلا تسوية تلقائية.'],
        ['نهاية الشهر', 'الموارد البشرية', 'أكّد المكافآت والسلف والتصفية. راجع مبلغ التصفية هذا الشهر ثم شغّل الرواتب.'],
        ['بداية السنة', 'الموارد البشرية', 'أدخل العطلات. حدد الموظفين واضغط تطبيق نظام الإجازة مرة واحدة للجميع.'],
    ], [3.2, 2.6, 10.6]))
    s.append(PageBreak())

    s.append(chapter('16. حل المشكلات'))
    s.append(table(['المشكلة', 'الحل'], [
        ['موظف غائب رغم حضوره', 'تحقق من الحركة في BioTime ومطابقة البطاقة ثم زامن الفترة.'],
        ['لا بصمات جديدة', 'تحقق أن خادم BioTime والأجهزة والجدولة تعمل.'],
        ['البصمات متقدمة أو متأخرة ساعات', 'صحّح ساعة BioTime ومنطقة مستخدم الجلب.'],
        ['كثير من مسودات الغياب', 'نطاق واسع أو بصمات ناقصة. راجع الحضور اليومي وألغِ الخطأ ثم أصلح البطاقات.'],
        ['السبب ما زال النص القانوني', 'حدّد المسودات واضغط ملء السبب من الحضور، أو أعد التوليد.'],
        ['تأكيد المحدد لا يفعل شيئاً', 'المسودات فقط. المؤكد والملغى يُتخطى.'],
        ['التجديدات تظهر الجميع', 'القائمة تستخدم نهاية العقد في الرواتب لا تاريخ المراجعة السنوي.'],
        ['نهاية التجربة فارغة أو تظهر الجميع', 'القائمة تستخدم نهاية التجربة في الرواتب خلال 10 أيام. احفظ الموظف لنسخ التاريخ.'],
        ['العطلة لا تُنشر في التقويم', 'حدّث الوحدة ثم اضغط نشر. يجب أن تصبح الحالة منشورة ويظهر رابط إجازة التقويم.'],
        ['الترقية تفشل: التعديل غير مسموح', 'حدّث إلى 19.0.1.0.15 ثم أعد الترقية. أنواع الإجازة لم تعد تُكتب فوق الإجازات المعتمدة.'],
        ['التسويات تبقى جارية بعد إنجاز القسيمة', 'حدّث إلى 19.0.1.0.20. تأكيد القسيمة يغلق تسويات المرة الواحدة لذلك الشهر. القرض يبقى جارياً حتى آخر قسط. القسائم المؤكدة سابقاً تُغلق عند الترقية.'],
        ['لا رصيد إجازة', 'حدد الموظفين واضغط تطبيق نظام الإجازة من القائمة أو الإجراءات. زر النموذج لموظف واحد ما زال يعمل.'],
        ['لا ضريبة على القسيمة', 'تحقق الخضوع والنسبة والراتب. مع التسوية التلقائية يُرحَّل خلال يوم، وإلا اضغط ترحيل.'],
        ['المقابلة ليست في التقويم', 'حدد تاريخ ووقت المقابلة ثم أعد إرسال وقت المقابلة.'],
        ['المأمورية ليست في التقويم أو الحضور ليس مأمورية', 'حدّث إلى 19.0.1.0.21. احفظ المأمورية بموظف وتواريخ. افتح التقويم أو الحضور اليومي لذلك الموظف. الإلغاء يزيل الاثنين.'],
        ['الهيكل فارغ أو مسطّح', 'عيّن المدير على الموظف والإدارة الأم على الإدارات. حدّث إلى 19.0.1.0.25 وافتح الهيكل الوظيفي. الهرم يُفتح كاملاً.'],
        ['لا يمكن تسجيل الاستقالة', 'حدّث إلى 19.0.1.0.26. أكّد الاستقالة أو الفصل مرة واحدة؛ تُسترجع العهد تلقائياً.'],
        ['صرف العهدة ما زال أربع خانات ثابتة', 'حدّث إلى 19.0.1.0.27. أضف أو أعد تسمية الأنواع في الإعداد > أنواع العهد؛ صرف العهدة يعرض كل نوع نشط.'],
        ['يلزم صرف نهاية الخدمة', 'حدّث إلى 19.0.1.0.29. افتح نهاية الخدمة على الموظف، احسب أو اكتب مبلغاً ثابتاً ثم أرسل للمالية.'],
        ['لا زر مفقود في العهد', 'حدّث إلى 19.0.1.0.28. اضغط مفقود بجانب استرجاع؛ يصبح السطر أحمر.'],
        ['أُرسل التعريف ولا توجد عهدة', 'التعريف يجهّز القائمة فقط. اضغط صرف عهدة على الموظف وعلّم ما سلّمته.'],
        ['تقرير Excel بلا تنسيق ورأس أبيض', 'حدّث إلى 19.0.1.0.23 أو أحدث ثم صدّر Excel من جديد. الملف الجديد بعنوان كحلي ورؤوس كحلية وصفوف متناوبة وتجميد.'],
    ], [5.6, 10.8]))
    s.append(CondPageBreak(7 * cm))
    s.append(chapter('17. الدعم'))
    s.append(p('للتدريب أو التعديل أو الدعم على نظام تاركو تواصل مع <b>%s</b> عبر <b>%s</b>.' % (COMPANY, SITE)))
    s.append(ContactCard())
    s.append(p('عند الإبلاغ عن مشكلة أرفق القائمة المستخدمة ورقم الموظف ورقم السجل (مثل PEN/2026/0012) ولقطة شاشة.'))
    return with_heading_breaks(s)


def with_heading_breaks(story):
    def is_heading(flowable):
        return isinstance(flowable, ChapterBanner) or (
            isinstance(flowable, Paragraph) and flowable.style.name == 'H2Ar')

    result, i = [], 0
    while i < len(story):
        if not is_heading(story[i]):
            result.append(story[i])
            i += 1
            continue
        group = []
        while i < len(story) and is_heading(story[i]):
            group.append(story[i])
            i += 1
        if i < len(story):
            following = story[i]
            if isinstance(following, Table):
                result += [CondPageBreak(6 * cm), KeepTogether(group)]
            else:
                content = following._content if isinstance(following, KeepTogether) else [following]
                result.append(KeepTogether(group + list(content)))
                i += 1
        else:
            result += group
    return result


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'Tarco_HRIS_User_Guide_AR.pdf')
    doc = GuideDoc(out)
    doc.multiBuild(build_story())
    print(out)


if __name__ == '__main__':
    main()

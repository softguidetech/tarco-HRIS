# -*- coding: utf-8 -*-
"""Build the Tarco HRIS user guide PDF (Soft Guide Technology)."""
import os
import re
import sys
from datetime import date

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, ListFlowable, ListItem,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

COMPANY = 'SOFT GUIDE TECHNOLOGY'
SITE = 'www.softguidetech.com'
TITLE = 'Tarco HRIS for Odoo 19'
SUBTITLE = 'User Guide - Human Resources Module'
VERSION = 'Module version 19.0.1.0.1'

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


def _register_fonts():
    fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    files = {
        'Sans': 'segoeui.ttf', 'Sans-Bold': 'segoeuib.ttf', 'Sans-Italic': 'segoeuii.ttf',
        'Sans-BoldItalic': 'segoeuiz.ttf', 'Sans-Semi': 'seguisb.ttf', 'Sans-Light': 'segoeuil.ttf',
    }
    paths = {name: os.path.join(fonts_dir, f) for name, f in files.items()}
    if not all(os.path.exists(path) for path in paths.values()):
        return 'Helvetica', 'Helvetica-Bold', 'Helvetica-Bold', 'Helvetica'
    for name, path in paths.items():
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Sans-Bold', italic='Sans-Italic',
                                  boldItalic='Sans-BoldItalic')
    return 'Sans', 'Sans-Bold', 'Sans-Semi', 'Sans-Light'


F, FB, FSB, FL = _register_fonts()

BODY = ParagraphStyle('Body', fontName=F, fontSize=10, leading=15, textColor=INK, spaceAfter=7)
CELL = ParagraphStyle('Cell', parent=BODY, fontSize=9, leading=12.5, spaceAfter=0)
CELL_KEY = ParagraphStyle('CellKey', parent=CELL, fontName=FSB, textColor=NAVY)
CELL_HEAD = ParagraphStyle('CellHead', parent=CELL, fontName=FSB, textColor=colors.white)
H2 = ParagraphStyle('H2', fontName=FB, fontSize=13, leading=17, textColor=NAVY, spaceBefore=12,
                    spaceAfter=6, keepWithNext=1)
PAGE_TITLE = ParagraphStyle('PageTitle', fontName=FB, fontSize=22, leading=26, textColor=NAVY, spaceAfter=4)
TOC1 = ParagraphStyle('TOC1', fontName=FSB, fontSize=10.5, leading=15, textColor=NAVY, spaceBefore=6)
TOC2 = ParagraphStyle('TOC2', fontName=F, fontSize=9.5, leading=13, leftIndent=20, textColor=MUTED)
TILE_TITLE = ParagraphStyle('TileTitle', fontName=FSB, fontSize=10, leading=13, textColor=NAVY)
TILE_TEXT = ParagraphStyle('TileText', fontName=F, fontSize=8.5, leading=11.5, textColor=MUTED)

CHAPTER_BLURBS = {
    1: 'What the module does, where to find it and who can use it.',
    2: 'One-time configuration before HR starts daily work.',
    3: 'Codes, personal data, salary, documents and onboarding in one screen.',
    4: 'Probation, renewals, alerts, resignation and rehire.',
    5: 'Shifts, fingerprint punches, lateness and the daily attendance sheet.',
    6: 'Leave types, yearly balance, approvals, holidays and encashment.',
    7: 'Business missions for one or many employees.',
    8: 'Overtime batches calculated from fingerprint punches.',
    9: 'Labour Law penalties, automatic lateness and absence penalties, and rewards.',
    10: 'Short advances, long-term loans and instalment schedules.',
    11: 'Headcount, public application link, ranking and interviews.',
    12: 'Question templates, scores, outputs and overall achievement.',
    13: 'Period reports in PDF and Excel, and the employee file report.',
    14: 'How HR records reach the payslip.',
    15: 'A checklist for every day, month and year.',
    16: 'Common problems and how to solve them.',
    17: 'How to reach Soft Guide Technology.',
}


def draw_logo(c, x, y, size, bg=TEAL, fg=colors.white):
    c.saveState()
    c.setFillColor(bg)
    c.roundRect(x, y, size, size, size * 0.22, stroke=0, fill=1)
    c.setFillColor(fg)
    c.setFont(FB, size * 0.42)
    c.drawCentredString(x + size / 2, y + size * 0.33, 'SG')
    c.restoreState()


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
        c.circle(w - 1.0 * cm, y0 + h, 2.6 * cm, stroke=0, fill=1)
        c.setFillColor(TEAL)
        c.rect(0, y0, 0.25 * cm, h, stroke=0, fill=1)
        c.restoreState()

        c.saveState()
        cx, cy = 1.55 * cm, y0 + h / 2
        c.setFillColor(TEAL)
        c.circle(cx, cy, 0.72 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(FB, 18)
        c.drawCentredString(cx, cy - 6.3, str(self.number))
        tx = 2.75 * cm
        top = y0 + h - 0.75 * cm
        c.setFillColor(TEAL_SOFT)
        c.setFont(FSB, 8)
        c.drawString(tx, top, 'CHAPTER %02d' % self.number)
        c.setFillColor(colors.white)
        c.setFont(FB, 17)
        c.drawString(tx, top - 0.68 * cm, self.title)
        if self.blurb:
            c.setFillColor(colors.HexColor('#C9D6E3'))
            c.setFont(F, 9.5)
            for i, line in enumerate(simpleSplit(self.blurb, F, 9.5, w - tx - 0.8 * cm)[:2]):
                c.drawString(tx, top - 1.25 * cm - i * 12, line)
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
    return Paragraph(text, BODY)


def chapter(text):
    number, title = text.split('. ', 1)
    return ChapterBanner(int(number), title, CHAPTER_BLURBS.get(int(number), ''))


def section(text):
    match = re.match(r'^([\d.]+)\s+(.*)$', text)
    if match:
        text = '<font color="#13A89E">%s</font>&nbsp;&nbsp;%s' % match.groups()
    return Paragraph(text, H2)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(item, BODY), leftIndent=14) for item in items],
        bulletType='bullet', start='\u25aa', leftIndent=14, bulletFontName=F, bulletFontSize=10,
        bulletColor=TEAL,
    )


def steps(items):
    rows = [[Badge(i), Paragraph(item, BODY)] for i, item in enumerate(items, 1)]
    t = Table(rows, colWidths=[0.95 * cm, CONTENT_W - 0.95 * cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (0, -1), 1.5),
        ('TOPPADDING', (1, 0), (1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    return KeepTogether([t, Spacer(1, 4)]) if len(items) <= 5 else t


def table(headers, rows, widths):
    scale = CONTENT_W / (sum(widths) * cm)
    data = [[Paragraph(h, CELL_HEAD) for h in headers]]
    data += [[Paragraph(str(c), CELL_KEY if i == 0 else CELL) for i, c in enumerate(row)] for row in rows]
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
    body = Paragraph('<font name="%s" color="%s">%s</font><br/>%s' % (FSB, accent.hexval().replace('0x', '#'), label, text), CELL)
    t = Table([[Badge(symbol, accent, 0.6 * cm, 10), body]], colWidths=[1.1 * cm, CONTENT_W - 1.1 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (1, 0), (1, 0), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 10)])


def tip(text):
    return callout('Tip', 'i', text, TEAL, TIP_BG)


def note(text):
    return callout('Important', '!', text, ORANGE, WARN_BG)


def flow_diagram():
    w, h = CONTENT_W, 150
    d = Drawing(w, h)
    main = [('Fingerprint', 'punches'), ('Daily', 'attendance'), ('Overtime and', 'penalties'),
            ('Salary', 'adjustments'), ('Next', 'payslip')]
    feeders = {1: ('Leave, missions,', 'official holidays'), 3: ('Rewards, advances,', 'tax and insurance')}
    bw, bh, y = 80, 46, 92
    gap = (w - len(main) * bw) / (len(main) - 1)

    def box(x, y, lines, fill, text_color, stroke=None):
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fill, strokeColor=stroke,
                   strokeWidth=0.8 if stroke else 0))
        d.add(String(x + bw / 2, y + bh / 2 + 2, lines[0], fontName=FSB, fontSize=8.5,
                     fillColor=text_color, textAnchor='middle'))
        d.add(String(x + bw / 2, y + bh / 2 - 9, lines[1], fontName=F, fontSize=8.5,
                     fillColor=text_color, textAnchor='middle'))

    def arrow(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=TEAL, strokeWidth=1.6))
        if y1 == y2:
            d.add(Polygon([x2, y2, x2 - 6, y2 + 3.5, x2 - 6, y2 - 3.5], fillColor=TEAL, strokeWidth=0))
        else:
            d.add(Polygon([x2, y2, x2 - 3.5, y2 - 6, x2 + 3.5, y2 - 6], fillColor=TEAL, strokeWidth=0))

    for i, lines in enumerate(main):
        x = i * (bw + gap)
        fill = TEAL if i == len(main) - 1 else NAVY
        box(x, y, lines, fill, colors.white)
        if i < len(main) - 1:
            arrow(x + bw + 3, y + bh / 2, x + bw + gap - 3, y + bh / 2)
        if i in feeders:
            box(x, 14, feeders[i], PALE, NAVY, LINE)
            arrow(x + bw / 2, 14 + bh + 3, x + bw / 2, y - 3)
    return KeepTogether([Spacer(1, 4), d, Spacer(1, 8)])


def cover_tiles():
    items = [
        ('Employee file', 'Codes, personal data, salary and documents.'),
        ('Contracts', '89-day probation, renewals, rehire on the same code.'),
        ('Attendance', 'Fingerprint punches, shifts, lateness after 08:15.'),
        ('Leave', '21 or 30 day schemes, sick leave, holidays, encashment.'),
        ('Missions and overtime', 'Group missions, overtime at 1.5x and 2x.'),
        ('Penalties and rewards', 'Labour Law 1997 rules, automatic penalties.'),
        ('Advances and loans', 'Instalments capped at the gross salary.'),
        ('Recruitment', 'Headcount, apply link, ranked candidates.'),
        ('KPIs and reports', '20 reports in PDF and Excel.'),
    ]
    tile_w = (CONTENT_W - 2 * 0.3 * cm) / 3
    cells = []
    for title, text in items:
        inner = Table([[Paragraph(title, TILE_TITLE)], [Paragraph(text, TILE_TEXT)]], colWidths=[tile_w],
                      rowHeights=[None, 1.0 * cm])
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


class GuideDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=2.7 * cm, bottomMargin=2.2 * cm,
            title='%s - %s' % (TITLE, SUBTITLE), author=COMPANY, subject='HR module user guide',
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
            level, text = 0, flowable.toc_text
        elif isinstance(flowable, Paragraph) and flowable.style.name == 'H2':
            level, text = 1, flowable.getPlainText().replace('\xa0', ' ')
        else:
            return
        key = 'h%s' % id(flowable)
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
        self.notify('TOCEntry', (level, text, self.page, key))

    def _cover(self, c, doc):
        band_h = 15.6 * cm
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, PAGE_H - band_h, PAGE_W, band_h, stroke=0, fill=1)
        path = c.beginPath()
        path.rect(0, PAGE_H - band_h, PAGE_W, band_h)
        c.clipPath(path, stroke=0, fill=0)
        c.setFillColor(NAVY_2)
        c.circle(PAGE_W - 2.5 * cm, PAGE_H - 2.0 * cm, 6.5 * cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor('#163B63'))
        c.circle(PAGE_W - 1.0 * cm, PAGE_H - band_h + 1.0 * cm, 3.6 * cm, stroke=0, fill=1)
        c.restoreState()

        c.saveState()
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - band_h - 0.35 * cm, PAGE_W, 0.35 * cm, stroke=0, fill=1)
        x = MARGIN
        draw_logo(c, x, PAGE_H - 3.3 * cm, 1.35 * cm)
        c.setFillColor(colors.white)
        c.setFont(FB, 15)
        c.drawString(x + 1.75 * cm, PAGE_H - 2.55 * cm, COMPANY)
        c.setFillColor(TEAL_SOFT)
        c.setFont(F, 10)
        c.drawString(x + 1.75 * cm, PAGE_H - 3.15 * cm, SITE)

        c.setFillColor(TEAL_SOFT)
        c.setFont(FSB, 10.5)
        c.drawString(x, PAGE_H - 7.0 * cm, 'U S E R   G U I D E')
        c.setFillColor(colors.white)
        c.setFont(FB, 34)
        c.drawString(x, PAGE_H - 8.45 * cm, TITLE)
        c.setFillColor(colors.HexColor('#D6E2EE'))
        c.setFont(FL, 17)
        c.drawString(x, PAGE_H - 9.5 * cm, 'Human Resources Management - complete how-to')
        c.setFillColor(TEAL)
        c.rect(x, PAGE_H - 10.25 * cm, 3.2 * cm, 0.13 * cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor('#C9D6E3'))
        c.setFont(F, 10.5)
        c.drawString(x, PAGE_H - 11.1 * cm, 'Prepared for Tarco Aviation Services - Human Resources Department')

        label = 'Odoo 19 Enterprise   |   %s   |   Issued %s' % (VERSION, date.today().strftime('%d %B %Y'))
        lw = pdfmetrics.stringWidth(label, F, 9) + 0.9 * cm
        c.setStrokeColor(TEAL_SOFT)
        c.setLineWidth(0.8)
        c.roundRect(x, PAGE_H - 12.75 * cm, lw, 0.75 * cm, 0.375 * cm, stroke=1, fill=0)
        c.setFillColor(colors.white)
        c.setFont(F, 9)
        c.drawString(x + 0.45 * cm, PAGE_H - 12.47 * cm, label)

        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, 2.2 * cm, PAGE_W - MARGIN, 2.2 * cm)
        c.setFillColor(MUTED)
        c.setFont(F, 8.5)
        c.drawString(MARGIN, 1.5 * cm, 'Copyright %s %s. All rights reserved.' % (date.today().year, COMPANY))
        c.setFillColor(NAVY)
        c.setFont(FB, 10)
        c.drawRightString(PAGE_W - MARGIN, 1.5 * cm, SITE)
        c.restoreState()

    def _page(self, c, doc):
        c.saveState()
        top = PAGE_H - 1.75 * cm
        draw_logo(c, MARGIN, top, 0.75 * cm)
        c.setFillColor(NAVY)
        c.setFont(FB, 9.5)
        c.drawString(MARGIN + 1.0 * cm, top + 0.4 * cm, COMPANY)
        c.setFillColor(MUTED)
        c.setFont(F, 8)
        c.drawString(MARGIN + 1.0 * cm, top + 0.05 * cm, SITE)
        c.setFont(F, 8.5)
        c.drawRightString(PAGE_W - MARGIN, top + 0.25 * cm, '%s  |  User Guide' % TITLE)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, top - 0.3 * cm, PAGE_W - MARGIN, top - 0.3 * cm)

        c.line(MARGIN, 1.55 * cm, PAGE_W - MARGIN, 1.55 * cm)
        c.setFillColor(MUTED)
        c.setFont(F, 8)
        c.drawString(MARGIN, 0.95 * cm, SITE)
        c.drawCentredString(PAGE_W / 2, 0.95 * cm, 'Human Resources Module - Odoo 19')
        label = '%d' % doc.page
        pw = max(0.9 * cm, pdfmetrics.stringWidth(label, FB, 8.5) + 0.5 * cm)
        c.setFillColor(NAVY)
        c.roundRect(PAGE_W - MARGIN - pw, 0.78 * cm, pw, 0.52 * cm, 0.26 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(FB, 8.5)
        c.drawCentredString(PAGE_W - MARGIN - pw / 2, 0.95 * cm, label)
        c.restoreState()


def build_story():
    s = []
    s.append(Paragraph('What is inside', ParagraphStyle('CoverHead', parent=TILE_TITLE, fontSize=12, spaceAfter=8)))
    s.append(cover_tiles())
    s.append(NextPageTemplate('content'))
    s.append(PageBreak())

    s.append(Paragraph('Contents', PAGE_TITLE))
    s.append(Paragraph('Click a title to jump to it. The same list is available as PDF bookmarks.',
                       ParagraphStyle('ContentsSub', parent=BODY, textColor=MUTED, spaceAfter=10)))
    toc = TableOfContents()
    toc.levelStyles = [TOC1, TOC2]
    toc.dotsMinLevel = 1
    s.append(toc)
    s.append(PageBreak())

    # 1 Introduction
    s.append(chapter('1. Introduction'))
    s.append(p('Tarco HRIS is a custom Odoo 19 module built from the Tarco Aviation Services HR requirements '
               'document (TAS/HRM, issue 01, 1 January 2024). It extends the standard Odoo Employees, '
               'Attendance, Time Off, Recruitment and Payroll applications, so everything you already know in '
               'Odoo keeps working. The module adds the Tarco rules on top: employee codes, the 89-day '
               'probation, the 08:15 lateness rule, overtime at 1.5x and 2x, the 21 and 30 day leave schemes, '
               'Labour Law 1997 penalties, salary advances and the reports HR asked for.'))
    s.append(section('1.1 Where to find it'))
    s.append(p('Open the %s application and choose the %s menu. Every screen in this guide lives under that menu.'
               % (menu('Employees'), menu('Tarco HRIS'))))
    s.append(table(['Menu', 'What it contains'], [
        ['Employee file', 'Employees with the HR File page, and onboarding notices.'],
        ['Contracts', 'All contracts, probation ending soon, renewals due soon.'],
        ['Attendance', 'Shifts and the daily attendance summary built from fingerprint punches.'],
        ['Leave', 'Leave requests, official holidays, leave encashment (sold leave).'],
        ['Missions', 'Business missions with one or many employees.'],
        ['Overtime', 'Overtime batches calculated from fingerprint punches.'],
        ['Penalties and rewards', 'Penalty rules, penalties, automatic penalties from attendance, rewards.'],
        ['Advances and loans', 'Short advances, long-term loans, goods purchases and other deductions.'],
        ['Recruitment', 'Job positions with screening questions, and applicants.'],
        ['KPIs', 'Question templates and employee performance reviews.'],
        ['Reports', 'Period reports (PDF and Excel), employee file report, payroll rule setup.'],
    ], [4.2, 12.2]))
    s.append(section('1.2 Who can do what'))
    s.append(table(['Role', 'Access'], [
        ['HR Officer (Employees: Officer)', 'Full access to every Tarco HRIS screen and report.'],
        ['HR Administrator (Employees: Administrator)', 'Everything an officer can do, plus the payroll rule setup action.'],
        ['Department manager', 'Can request missions for their team, approve leave as the employee approver, '
                               'and fill KPI reviews for their direct reports.'],
        ['Employee', 'Sees missions and KPI reviews that concern them. Requests leave through Time Off.'],
    ], [5.4, 11.0]))
    s.append(tip('Access is given in %s. Open the user and set the Employees role.' % menu('Settings > Users & Companies > Users')))
    s.append(section('1.3 How the pieces connect'))
    s.append(flow_diagram())
    s.append(bullets([
        'The <b>employee code</b> is the key. It is shown in front of the name everywhere, it can be typed in any '
        'employee field to find the person, and it is copied to the Badge ID used by the fingerprint device.',
        'Fingerprint punches arrive in Odoo Attendance automatically through the biometric device integration. '
        'Tarco HRIS turns them into one <b>daily attendance</b> line per employee per day.',
        'Approved leave, approved missions and official holidays are written onto the same daily line, so every '
        'attendance report shows them.',
        'Penalties, rewards, overtime, advances, leave deductions, leave encashment, tax and social insurance are '
        'posted as <b>salary adjustments</b> and appear on the next payslip automatically.',
    ]))
    s.append(PageBreak())

    # 2 Getting started
    s.append(chapter('2. First-time setup'))
    s.append(p('Do these steps once, in this order, before HR starts daily work.'))
    s.append(steps([
        'Create departments and sections in %s. A section is a department placed under its parent department.'
        % menu('Employees > Configuration > Departments'),
        'Review the shifts in %s. Two shifts are created for you: Day shift 08:00-16:00 and Shift 08:00-20:00, '
        'both with Friday as the rest day.' % menu('Tarco HRIS > Attendance > Shifts'),
        'Enter the year\'s official holidays in %s and click <b>Publish on calendar</b> on each one.'
        % menu('Tarco HRIS > Leave > Official holidays'),
        'Check the penalty rules in %s. Set the amount on the Conduct rule and adjust the legal text to the '
        'Labour Law 1997 articles HR applies.' % menu('Tarco HRIS > Penalties and rewards > Penalty rules'),
        'Create KPI question templates in %s.' % menu('Tarco HRIS > KPIs > Question templates'),
        'Make sure each payroll structure has the Tarco rules. They are added automatically at install and '
        'every day. To add them immediately, an HR Administrator runs %s.'
        % menu('Tarco HRIS > Reports > Create payroll rules'),
        'Complete every employee file (next chapter), then click <b>Apply leave scheme</b> on each employee to '
        'give the year\'s leave balance.',
    ]))
    s.append(note('Employees must have a Badge ID that matches the fingerprint device user ID. When you type an '
                  'employee code and the Badge ID is empty, the code is copied into it for you.'))
    s.append(PageBreak())

    # 3 Employee file
    s.append(chapter('3. Employee file'))
    s.append(p('All the employee information is entered from one screen. Open %s, create or open an employee, and '
               'go to the <b>HR File</b> page.' % menu('Tarco HRIS > Employee file > Employees')))
    s.append(section('3.1 Fields on the HR File page'))
    s.append(table(['Group', 'Fields'], [
        ['Identity', 'Employee code, department, section, job position, hire date, birthday, nationality, gender, '
                     'marital status, religion, qualification (basic, secondary, diploma, bachelor, higher diploma, '
                     'master, doctorate), field of study, school, years of experience.'],
        ['Contact and address', 'Private phone, work mobile, emergency phone, private email, work email, and the '
                                'address as state, city, district and block.'],
        ['Contract', 'Probation end, renewal date, contract alert, length of service, resignation date, rehire date, '
                     'shift, exempt from lateness, overtime calculation.'],
        ['Salary', 'Basic salary, cost of living allowance, transport allowance, housing allowance, other allowances, '
                   'gross salary (calculated), subject to tax and tax %, subject to social insurance and insurance %.'],
        ['Leave balance', 'Annual leave scheme (21 or 30 days), casual days, annual days.'],
        ['Hiring and audit documents', 'One line per document with a file attachment.'],
    ], [3.8, 12.6]))
    s.append(section('3.2 Create a new employee'))
    s.append(steps([
        'Click <b>New</b> and type the employee name.',
        'On the HR File page enter the <b>Employee code</b>. Two employees cannot share a code.',
        'Enter the <b>Hire date</b>. The probation end (hire date + 89 days) and the annual renewal date '
        '(hire date + 1 year) fill in automatically.',
        'Fill the identity, contact and address fields.',
        'Enter the salary components. The gross salary is the total and is copied to the employee contract wage.',
        'Choose the leave scheme and the shift.',
        'Add the documents and tick <b>Received</b> as each one arrives.',
        'Save.',
    ]))
    s.append(section('3.3 Hiring and audit documents'))
    s.append(table(['Group', 'Document kinds'], [
        ['Hiring document', 'Birth certificate, qualification, experience certificates, photograph, national ID, other.'],
        ['Audit document', 'Employment application, employment contract, job description, acknowledgement of work '
                           'regulations, other.'],
    ], [3.8, 12.6]))
    s.append(section('3.4 Buttons on the employee'))
    s.append(table(['Button', 'What it does'], [
        ['Apply leave scheme', 'Creates this year\'s approved casual and annual allocations from the scheme. '
                               'It does nothing for a type that already has an allocation this year.'],
        ['Post tax and insurance', 'Creates one-time deductions for this month: gross x tax % and gross x social '
                                   'insurance %. Click it once per payroll month.'],
        ['Onboarding notice', 'Opens a notice to the departments that prepare for the new employee.'],
        ['Print file', 'Opens the employee file report with check boxes to choose the sections.'],
        ['Register resignation / Rehire / Renew contract', 'See chapter 4.'],
        ['Smart buttons', 'Documents, Missions, Penalties, Rewards, Advances and KPIs open the related records.'],
    ], [4.6, 11.8]))
    s.append(section('3.5 Onboarding notice'))
    s.append(p('Use it to notify the departments concerned when someone is hired: induction training, safety '
               'briefing, computer, library tools, uniform, or supplies from the warehouse.'))
    s.append(steps([
        'On the employee click <b>Onboarding notice</b>, or open %s and click New.'
        % menu('Tarco HRIS > Employee file > Onboarding notices'),
        'Tick the items needed and add a note.',
        'Click <b>Notify departments</b>. A message is posted on the notice, a to-do activity is created for the '
        'employee\'s manager (or the HR responsible), and an email goes to the manager and the employee.',
    ]))
    s.append(section('3.6 Finding an employee'))
    s.append(p('Type the employee code or the name in the search bar of any employee list, or in any field that '
               'asks for an employee (missions, penalties, advances and so on). The code is shown in square '
               'brackets before the name, for example <b>[T0125] Ahmed Ali</b>.'))
    s.append(PageBreak())

    # 4 Contracts
    s.append(chapter('4. Employment contracts'))
    s.append(p('Contract dates are kept on the employee. Use %s to see every employee with hire, probation, renewal, '
               'resignation and rehire dates and the length of service.' % menu('Tarco HRIS > Contracts > Contracts')))
    s.append(section('4.1 Probation and renewal dates'))
    s.append(bullets([
        '<b>Probation end</b> is set to hire date + 89 days. If you change it by hand, <b>Probation set manually</b> '
        'is ticked and the date is no longer recalculated.',
        '<b>Annual renewal date</b> is set to hire date + 1 year. Tick <b>Renewal set manually</b> to keep your own date.',
        'The probation end and the gross salary are copied to the Odoo contract of the employee.',
    ]))
    s.append(section('4.2 Alerts 7 to 10 days before'))
    s.append(p('Every day the scheduled action <b>Tarco HRIS: attendance and contract alerts</b> looks for probation '
               'ends and renewals in the next 10 days. For each one it creates a to-do activity for the HR '
               'responsible on the contract (or the manager) and emails the employee, the manager and that user. '
               'Each date is alerted only once; changing the date resets the alert.'))
    s.append(p('Use %s and %s to see the lists at any time. They use the search filters <b>Probation ending '
               '(10 days)</b> and <b>Renewal due (10 days)</b>, which you can also apply on any employee list.'
               % (menu('Contracts > Probation ending'), menu('Contracts > Renewals due'))))
    s.append(section('4.3 Renew, resign and rehire'))
    s.append(table(['Action', 'How', 'Result'], [
        ['Renew the contract', 'Click <b>Renew contract</b> on the employee.', 'Renewal date moves forward one year.'],
        ['Resignation', 'Click <b>Register resignation</b>.',
         'Resignation date and departure date are set to today. Change the date if the resignation was on another day. '
         'Archive the employee when the last working day has passed.'],
        ['Rehire', 'Unarchive the employee if needed, then click <b>Rehire</b>.',
         'Same employee and same code. The rehire date is today, the resignation is cleared, and new probation and '
         'renewal dates are calculated from today. The original hire date is kept.'],
    ], [3.4, 5.4, 7.6]))
    s.append(section('4.4 Statutory and internal deductions'))
    s.append(p('On the HR File page tick <b>Subject to tax</b> and/or <b>Subject to social insurance</b> and enter the '
               'percentages. Each payroll month, click <b>Post tax and insurance</b> on the employee once.'))
    s.append(PageBreak())

    # 5 Attendance
    s.append(chapter('5. Attendance and shifts'))
    s.append(section('5.1 Shifts'))
    s.append(p('Open %s. A shift defines the working hours and how lateness and overtime are counted.'
               % menu('Tarco HRIS > Attendance > Shifts')))
    s.append(table(['Field', 'Meaning'], [
        ['Start / End', 'Shift hours, for example 08:00 to 16:00, or 08:00 to 20:00.'],
        ['Crosses midnight', 'Tick for night shifts that end the next day.'],
        ['Lateness starts after (minutes)', 'Grace period. With 15 minutes and a start of 08:00, lateness counts from 08:15.'],
        ['Paid day hours', 'Hours paid for a full day, normally 8, even if the employee leaves at 16:30.'],
        ['Overtime starts at', 'Time after which overtime is counted, normally 16:00.'],
        ['Rest days', 'Tick the weekly rest days of this shift (Friday by default).'],
        ['Departments / Job positions', 'Apply the shift to whole departments or job groups.'],
        ['Specific employees', 'Apply the shift to named people inside a department.'],
        ['Exempt from lateness', 'People on this shift who are never counted late.'],
    ], [5.0, 11.4]))
    s.append(p('Odoo picks the shift of an employee in this order: the <b>Shift</b> field on the employee, a shift '
               'that lists the employee, a shift that matches the department or job, then a shift with no '
               'department, job or employee.'))
    s.append(tip('To exempt one person without changing the shift, tick <b>Exempt from lateness</b> on the employee.'))
    s.append(section('5.2 Fingerprint attendance'))
    s.append(p('Punches are downloaded from the device into Odoo Attendance by the biometric device integration, with '
               'no manual entry. Every day Tarco HRIS summarises the last three days into %s. You can also summarise '
               'any period with the <b>Sync fingerprint</b> button of the period report (chapter 13).'
               % menu('Attendance > Daily attendance')))
    s.append(table(['Status', 'When it is used'], [
        ['Present', 'Punched in on time and out.'],
        ['Late', 'Punched in after the grace period. The late minutes are shown.'],
        ['Absent', 'No punch on a working day with no leave, mission or holiday.'],
        ['Leave', 'An approved leave covers the day.'],
        ['Mission', 'An approved mission covers the day.'],
        ['Public holiday', 'An official holiday, with no punch.'],
        ['Rest day', 'The shift rest day, with no punch.'],
        ['Missing checkout', 'Punched in but not out. Correct the punch in Attendance and sync again.'],
    ], [3.6, 12.8]))
    s.append(section('5.3 How the day is calculated'))
    s.append(bullets([
        'Leaving at or after the shift end gives the full paid day (8 hours), so 16:30 still counts as 8 hours.',
        'Overtime is the time worked after <b>Overtime starts at</b>.',
        'Overtime is paid at <b>1.5x</b> from Saturday to Thursday and <b>2x</b> on Friday and official holidays.',
        'Hourly wage = gross salary / 30 / 8.',
        'Set <b>Overtime calculation</b> on the employee to <b>Do not pay overtime</b> to record hours without paying them.',
    ]))
    s.append(note('A day already included in a confirmed overtime batch is locked and is not recalculated.'))
    s.append(PageBreak())

    # 6 Leave
    s.append(chapter('6. Leave'))
    s.append(section('6.1 Leave types'))
    s.append(table(['Type', 'Rules'], [
        ['Annual leave', 'Uses the yearly balance. Approved by the employee\'s approver and then by HR.'],
        ['Casual leave', 'Uses the yearly balance (6 days). Approved by the employee\'s approver and then by HR.'],
        ['Sick leave', 'Kept separate from other leave. No balance needed. A medical document can be attached. Approved by HR.'],
        ['Official holiday leave', 'For official holidays taken. Approved by HR.'],
    ], [4.0, 12.4]))
    s.append(section('6.2 Annual balance'))
    s.append(p('The scheme on the employee sets the balance: <b>21 days</b> = 6 casual + 15 annual, or <b>30 days</b> '
               '= 6 casual + 24 annual. You can change the casual and annual days by hand. Click <b>Apply leave '
               'scheme</b> at the start of each year to create the approved allocations.'))
    s.append(section('6.3 Request and approve leave'))
    s.append(steps([
        'The department manager or section supervisor opens %s (or the Time Off app) and creates the request for '
        'the employee.' % menu('Tarco HRIS > Leave > Leave requests'),
        'Choose the leave type and dates. The form shows the <b>Scheme balance</b> (days left) and the days '
        '<b>Taken this month</b>.',
        'Choose the <b>Deduction</b>: <b>From balance / full pay</b>, <b>Deduct from salary</b>, or <b>Partial salary '
        'deduction</b> with a percentage.',
        'The approver approves, then HR validates. HR can also enter, edit, approve or refuse any request.',
    ]))
    s.append(p('When the leave is validated with a salary deduction, the amount is days x daily wage (gross / 30) x '
               'percentage, and it is posted to the next payslip. Use partial deduction for sick leave that is paid '
               'in part.'))
    s.append(section('6.4 Official holidays'))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Leave > Official holidays'),
        'Enter the name and the original date.',
        'If the holiday is moved, enter the <b>Moved to</b> date. The <b>Observed</b> date is the one used everywhere.',
        'Click <b>Publish on calendar</b> so Odoo working time and leave durations take it into account. Publish '
        'again after moving a date.',
    ]))
    s.append(section('6.5 Leave encashment (selling leave)'))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Leave > Leave encashment'),
        'Choose the employee and the number of days. The daily rate defaults to gross / 30 and can be changed.',
        'Click <b>Confirm</b>. The amount is added to the next payslip. Reduce the remaining balance in Time Off '
        'allocations if the sold days must be removed from it.',
    ]))
    s.append(PageBreak())

    # 7 Missions
    s.append(chapter('7. Missions'))
    s.append(p('A mission can be requested by the department manager or by HR, at any time of day, and can include '
               'many employees without opening each employee.'))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Missions'),
        'Enter the place, purpose, start and end dates, departure time and end time (any time in 24 hours).',
        'Enter the cost per person per day if the mission has an allowance.',
        'Add employees on the lines by code or by name.',
        'HR clicks <b>Approve</b>. Approved missions appear in daily attendance and in every attendance report.',
        'Click <b>Done</b> when the mission is finished, or <b>Cancel</b> to drop it.',
    ]))
    s.append(p('The form calculates the number of days, the number of employees, total hours (hours per day x days x '
               'employees) and the cost (cost per day x days x employees).'))
    s.append(PageBreak())

    # 8 Overtime
    s.append(chapter('8. Overtime'))
    s.append(p('Overtime is calculated automatically from fingerprint punches (chapter 5). An overtime batch collects '
               'it for a period and sends it to payroll.'))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Overtime'),
        'Enter the period and, if needed, a department.',
        'Click <b>Fill from fingerprint</b>. Attendance is summarised and one line per employee shows hours at 1.5x, '
        'hours at 2x, total hours and amount.',
        'Check the lines, then click <b>Confirm and post</b>. Each amount is added to the employee\'s next payslip.',
    ]))
    s.append(note('Clicking Cancel on a confirmed batch releases the days so they can be used again. It does not '
                  'remove salary adjustments already created; close those in Payroll if needed.'))
    s.append(PageBreak())

    # 9 Penalties and rewards
    s.append(chapter('9. Penalties and rewards'))
    s.append(section('9.1 Penalty rules'))
    s.append(p('Rules are kept in %s. Each rule has a fixed legal reason text and a calculation.'
               % menu('Penalties and rewards > Penalty rules')))
    s.append(table(['Calculation', 'Amount'], [
        ['Fixed amount', 'The amount on the rule.'],
        ['Days of wage', 'Days x gross / 30.'],
        ['Hours of wage', 'Hours x gross / 30 / 8.'],
        ['Percent of basic salary', 'Basic salary x percent.'],
    ], [5.0, 11.4]))
    s.append(p('Three rules are provided: <b>Lateness</b> (hours of wage), <b>Absence</b> (one day of wage) and '
               '<b>Conduct</b> (fixed amount, set it before use).'))
    s.append(section('9.2 Lateness and absence penalties from attendance'))
    s.append(steps([
        'Open %s.' % menu('Penalties and rewards > Generate from attendance'),
        'Choose the period, optionally a department, and tick lateness and/or absence.',
        'Click <b>Generate</b>. One draft penalty is created per late or absent day. Days that already have a penalty '
        'are skipped.',
        'Review the drafts and click <b>Confirm</b> on each one to apply.',
    ]))
    s.append(section('9.3 Conduct penalties on one employee or a group'))
    s.append(steps([
        'Open %s and click New.' % menu('Penalties and rewards > Penalties'),
        'Choose the rule. The legal reason fills in automatically.',
        'Enter the penalty date and the date it applies from.',
        'Add employees by code. Their basic and gross wage appear and the amount is calculated. Enter days or hours '
        'to override the rule default, or type the amount.',
        'To penalise a whole department, choose it and click <b>Add department</b>.',
        'The <b>Repeat</b> column shows how many times the employee has received the same rule.',
        'Click <b>Confirm</b>. Each amount is deducted on the next payslip.',
    ]))
    s.append(section('9.4 Rewards and grants'))
    s.append(steps([
        'Open %s and click New.' % menu('Penalties and rewards > Rewards'),
        'Choose the employee by code. The name, department, section and wage items appear.',
        'Enter the reason and date, then choose <b>Amount</b> or <b>Days of wage</b>.',
        'Click <b>Confirm</b>. The reward is added to the next payslip.',
    ]))
    s.append(PageBreak())

    # 10 Advances
    s.append(chapter('10. Advances and loans'))
    s.append(table(['Type', 'How it is recovered'], [
        ['Short advance', 'Deducted once, from the salary of the due date month.'],
        ['Long-term loan', 'Deducted in equal monthly instalments, starting at the due date.'],
        ['Goods purchase', 'Same as a loan: one or more instalments.'],
        ['Other deduction', 'Any other deduction, in one or more instalments.'],
    ], [4.0, 12.4]))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Advances and loans'),
        'Choose the employee, type and description, and enter the amount.',
        'For instalments, enter the number of instalments. The monthly amount is calculated.',
        'Enter the due date of the first deduction.',
        'Click <b>Confirm</b>. The instalment schedule is created and the deduction is sent to payroll.',
    ]))
    s.append(note('The monthly instalment cannot be more than the employee\'s gross salary. Odoo refuses to save it.'))
    s.append(p('After each payroll, the daily scheduled action marks instalments as paid from what payroll has '
               'deducted, updates the paid and remaining amounts, and sets the advance to Done when it is fully paid.'))
    s.append(PageBreak())

    # 11 Recruitment
    s.append(chapter('11. Recruitment'))
    s.append(section('11.1 Prepare the job position'))
    s.append(steps([
        'Open %s and open the job.' % menu('Tarco HRIS > Recruitment > Job positions'),
        'Enter the <b>Approved headcount</b>. <b>Vacant posts</b> is the approved headcount minus current employees.',
        'Click <b>Open recruitment for vacancies</b> to set the recruitment target to the number of vacant posts.',
        'Fill the job request: general objective, required experience, qualification, required skills, previous '
        'experience, training and expected wage.',
        'Add the <b>screening questions</b>. Enter an expected answer to score it, or leave it empty to accept any answer.',
        'Share the <b>Application link</b> (/tarco/jobs/ID/apply) in the job advertisement.',
    ]))
    s.append(section('11.2 Applications and ranking'))
    s.append(p('Candidates open the link, answer the questions and upload their CV. Each application gets a '
               '<b>Match %</b>: up to 80% for answers that match, plus up to 20% for complete information (name, '
               'email, phone, CV, qualification). Applicants are listed from the highest match down.'))
    s.append(section('11.3 Screening tracks and interviews'))
    s.append(steps([
        'Open %s. Use the filters Shortlisted, Maybe and Rejected.' % menu('Tarco HRIS > Recruitment > Applicants'),
        'On each applicant set the <b>Screening track</b> to Shortlisted, Maybe or Rejected.',
        'Set the <b>Interview</b> date and time and the interview round.',
        'Click <b>Email interview time</b>. The candidate receives the invitation from the company email.',
    ]))
    s.append(tip('The application link uses the Odoo base URL. It must be reachable from the internet for outside '
                 'candidates to apply.'))
    s.append(PageBreak())

    # 12 KPIs
    s.append(chapter('12. Performance KPIs'))
    s.append(section('12.1 Question templates'))
    s.append(p('In %s create a template per job group with questions, a weight for each question and a maximum '
               'score (5 by default).' % menu('KPIs > Question templates')))
    s.append(section('12.2 Evaluate an employee'))
    s.append(steps([
        'Open %s and click New.' % menu('KPIs > Reviews'),
        'Choose the employee, the period and the template, then click <b>Load questions</b>.',
        'The manager scores each question and adds comments. A score under 60% of the maximum is flagged as a problem point.',
        'Add the <b>daily outputs</b> with a quality score from 1 to 5, or type an output quality %.',
        'Actual hours and scheduled hours come from daily attendance and give the hours achievement %.',
        'Click <b>Done</b>.',
    ]))
    s.append(p('The <b>Overall %</b> is the average of the question score, hours achievement and output quality '
               '(parts with no value are left out). The employee\'s manager and HR can edit reviews.'))
    s.append(PageBreak())

    # 13 Reports
    s.append(chapter('13. Reports'))
    s.append(section('13.1 Period reports'))
    s.append(steps([
        'Open %s.' % menu('Tarco HRIS > Reports > Period reports'),
        'Choose the report, the period, and optionally a department or one employee.',
        'Click <b>Print</b> for a PDF or <b>Export Excel</b> for a spreadsheet. For attendance, click '
        '<b>Sync fingerprint</b> first if the period is not yet summarised (Print does it for you).',
    ]))
    s.append(table(['Area', 'Report', 'Shows'], [
        ['Contracts', 'Contracts to renew', 'Renewals falling in the period.'],
        ['Contracts', 'Length of service', 'Years, months and days of service per employee.'],
        ['Contracts', 'Hires and resignations', 'Movement during the month or year.'],
        ['Contracts', 'Turnover rate', 'Resignations / active headcount, monthly or yearly by the period chosen.'],
        ['Contracts', 'Cost of hires and resignations', 'Monthly gross of people hired and of people who left.'],
        ['Attendance', 'Attendance', 'Daily in and out, department strength with leave, absence and missions, '
                                     'and attendance % per employee.'],
        ['Leave', 'Monthly leave', 'Leave in the period and its share of working days.'],
        ['Leave', 'Official holidays', 'Holidays observed and official leave taken.'],
        ['Leave', 'Annual leave', 'Annual and casual leave taken.'],
        ['Leave', 'Sick leave', 'Sick leave with start, end and days.'],
        ['Leave', 'Leave encashment cost', 'Paid cost of leave sold.'],
        ['Missions', 'Missions', 'Missions, and hours and cost per place.'],
        ['Overtime', 'Overtime', 'Hours at 1.5x and 2x and cost per employee.'],
        ['Discipline', 'Penalties', 'Per employee, total deducted, and repeated reasons with percentages.'],
        ['Discipline', 'Rewards', 'Name, department, amount and total.'],
        ['Advances', 'Advances due', 'Instalments due in the period.'],
        ['Advances', 'Remaining advances', 'Running advances with paid and remaining amounts.'],
        ['Advances', 'Advances paid in the period', 'All instalments recovered (use a full year for the annual report).'],
        ['Recruitment', 'Recruitment', 'Open jobs with expected wages, applicants, matching CVs, first and final interviews.'],
        ['KPIs', 'KPIs', 'Achievement per employee, department average, problem points, highest and lowest.'],
    ], [2.6, 4.4, 9.4]))
    s.append(tip('Choose one employee to get the leave, penalty or overtime history for the employee\'s file.'))
    s.append(section('13.2 Employee file report'))
    s.append(p('Click <b>Print file</b> on an employee, or open %s. Tick the sections to include (personal data, job, '
               'salary, documents, contract, leave, attendance, penalties, rewards, advances, KPIs) and click '
               '<b>Print</b>.' % menu('Reports > Employee file report')))
    s.append(PageBreak())

    # 14 Payroll
    s.append(chapter('14. Payroll integration'))
    s.append(p('Tarco HRIS does not change how payslips are computed. It creates salary adjustments in %s that '
               'payroll picks up on the next payslip.' % menu('Payroll > Employees > Salary Adjustments')))
    s.append(table(['Source', 'Adjustment type', 'Effect on payslip'], [
        ['Rewards, overtime, leave encashment', 'Tarco Earning', 'Added to gross'],
        ['Penalties, advances, leave deductions, tax, social insurance', 'Tarco Deduction', 'Deducted from net'],
    ], [6.4, 3.6, 6.4]))
    s.append(p('Each adjustment carries a description such as "Penalty Lateness" or "Overtime OT/2026/0003", so the '
               'payslip lines are easy to read.'))
    s.append(note('If a new payroll structure is created, run %s (HR Administrator) so it gets the Tarco Earning '
                  'and Tarco Deduction rules. Otherwise the daily scheduled action adds them the next day.'
                  % menu('Reports > Create payroll rules')))
    s.append(PageBreak())

    # 15 Daily routine
    s.append(chapter('15. Daily and monthly routine'))
    s.append(table(['When', 'Who', 'Task'], [
        ['Daily', 'HR', 'Check activities for probation and renewal alerts. Fix missing checkouts in Attendance.'],
        ['Daily', 'Managers', 'Request leave and missions for the team.'],
        ['Daily', 'HR', 'Approve leave and missions.'],
        ['Month end', 'HR', 'Generate lateness and absence penalties and confirm them.'],
        ['Month end', 'HR', 'Create and confirm the overtime batch.'],
        ['Month end', 'HR', 'Post tax and insurance for the employees concerned.'],
        ['Month end', 'HR', 'Confirm rewards, advances and encashments, then run payroll.'],
        ['Month end', 'HR', 'Print the monthly reports.'],
        ['Year start', 'HR', 'Enter official holidays and apply the leave scheme to all employees.'],
        ['Each review period', 'Managers', 'Fill KPI reviews.'],
    ], [3.2, 2.6, 10.6]))

    # 16 Troubleshooting
    s.append(PageBreak())
    s.append(chapter('16. Troubleshooting'))
    s.append(table(['Problem', 'Solution'], [
        ['An employee is absent although they came.', 'Check the Badge ID matches the device user ID and that the '
                                                       'punch is in Attendance, then sync the period again.'],
        ['Status is Missing checkout.', 'Add the check-out in Attendance and sync again.'],
        ['Overtime amount is zero.', 'Check the salary components are filled and Overtime calculation is not '
                                     '"Do not pay overtime".'],
        ['Penalty, reward or advance is not on the payslip.', 'Make sure the record is confirmed, the payslip period '
                                                              'covers the date, and the structure has the Tarco rules.'],
        ['Cannot save an advance.', 'The monthly instalment is higher than the gross salary. Add instalments.'],
        ['Probation date did not change with the hire date.', 'Probation set manually is ticked. Untick it and set '
                                                             'the hire date again.'],
        ['No contract alert was received.', 'The alert is sent once per date. Make sure the employee and manager have '
                                            'work emails and that outgoing mail is configured.'],
        ['Leave balance is empty.', 'Click Apply leave scheme on the employee.'],
        ['Code already used.', 'Each employee code must be unique, including archived employees.'],
    ], [5.6, 10.8]))

    # Support
    s.append(CondPageBreak(7 * cm))
    s.append(chapter('17. Support'))
    s.append(p('For training, changes or support on Tarco HRIS, contact <b>%s</b> at <b>%s</b>.' % (COMPANY, SITE)))
    s.append(p('When you report a problem, include the menu you used, the employee code, the record number '
               '(for example PEN/2026/0012) and a screenshot.'))
    return s


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'Tarco_HRIS_User_Guide.pdf')
    doc = GuideDoc(out)
    doc.multiBuild(build_story())
    print(out)


if __name__ == '__main__':
    main()

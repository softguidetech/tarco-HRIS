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
VERSION = 'Module version 19.0.1.0.29'

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
    1: 'What the module does, the HRIS dashboard, where to find it, who can use it, and what is new in 19.0.1.0.29.',
    2: 'One-time configuration before HR starts daily work.',
    3: 'Codes, org chart, work requirements, custody, salary and documents in one screen.',
    4: 'Probation and renewals, end of service form (calculate or fixed amount for finance), resignation and rehire.',
    5: 'ZKTeco devices through BioTime, shifts, lateness and the daily attendance sheet.',
    6: 'Leave types, yearly balance, approvals, holidays and encashment.',
    7: 'Business missions for one or many employees, in any currency, with a printable mission order.',
    8: 'Overtime batches calculated from fingerprint punches.',
    9: 'Labour Law penalties, generate from attendance, a checkable reason on each draft, and bulk confirm.',
    10: 'Short advances, long-term loans and instalment schedules.',
    11: 'Headcount, public application link, ranking and interviews.',
    12: 'Question templates, scores, outputs and overall achievement.',
    13: 'Period reports in PDF and styled Excel, the employee file (including custody), and IBM Plex Sans Arabic on every HRIS PDF.',
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


def chain_diagram(steps_labels):
    w, h = CONTENT_W, 70
    d = Drawing(w, h)
    bw, bh, y = 84, 50, 10
    gap = (w - len(steps_labels) * bw) / (len(steps_labels) - 1)
    for i, (title, sub) in enumerate(steps_labels):
        x = i * (bw + gap)
        fill = TEAL if i == len(steps_labels) - 1 else NAVY
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=fill, strokeWidth=0))
        d.add(String(x + bw / 2, y + bh / 2 + 3, title, fontName=FSB, fontSize=8.5,
                     fillColor=colors.white, textAnchor='middle'))
        d.add(String(x + bw / 2, y + bh / 2 - 9, sub, fontName=F, fontSize=7.5,
                     fillColor=colors.HexColor('#C9D6E3') if fill == NAVY else colors.white, textAnchor='middle'))
        if i < len(steps_labels) - 1:
            x1, x2, ym = x + bw + 3, x + bw + gap - 3, y + bh / 2
            d.add(Line(x1, ym, x2, ym, strokeColor=TEAL, strokeWidth=1.6))
            d.add(Polygon([x2, ym, x2 - 6, ym + 3.5, x2 - 6, ym - 3.5], fillColor=TEAL, strokeWidth=0))
    return KeepTogether([Spacer(1, 2), d, Spacer(1, 8)])


def cover_tiles():
    items = [
        ('Employee file', 'Codes, org chart, configurable custody, salary and documents.'),
        ('Contracts', '89-day probation, renewals, rehire on the same code.'),
        ('Attendance', 'ZKTeco fingerprint via BioTime, shifts, lateness after 08:15.'),
        ('Leave', '21 or 30 day schemes, sick leave, holidays, encashment.'),
        ('Missions and overtime', 'Group missions, overtime at 1.5x and 2x.'),
        ('Penalties and rewards', 'Generate from attendance, checkable reasons, bulk confirm.'),
        ('Advances and loans', 'Instalments capped at the gross salary.'),
        ('Recruitment', 'Headcount, apply link, ranked candidates.'),
        ('Dashboard and reports', 'Company or own records, plus 20 PDF and Excel reports.'),
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
        draw_logo(c, 0.6 * cm, y0 + (h - 1.4 * cm) / 2, 1.4 * cm)
        x = 2.4 * cm
        c.setFillColor(NAVY)
        c.setFont(FB, 14)
        c.drawString(x, y0 + h - 0.95 * cm, COMPANY)
        c.setFillColor(TEAL)
        c.setFont(FSB, 11)
        c.drawString(x, y0 + h - 1.6 * cm, SITE)
        c.linkURL('https://' + SITE, (x, y0 + h - 1.75 * cm, x + 6 * cm, y0 + h - 1.25 * cm), relative=1)
        c.setFillColor(MUTED)
        c.setFont(F, 9)
        c.drawString(x, y0 + h - 2.15 * cm, 'Odoo implementation, customisation, training and support')
        c.restoreState()


def contact_card():
    return ContactCard()


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
        ['Dashboard', 'Tiles of HRIS figures, plus a Charts view (donut, histogram, bar and line). HR sees the company. An employee sees only their own records.'],
        ['Employee file', 'Employees (list and hierarchy), organization chart, departments, onboarding, work requirements, employee custody and Give custody.'],
        ['Contracts', 'All contracts; probation ending, renewals due, and End of service (calculate or fixed amount for finance).'],
        ['Attendance', 'Shifts and the daily attendance summary built from fingerprint punches.'],
        ['Leave', 'Leave requests, official holidays, leave encashment (sold leave).'],
        ['Missions', 'Business missions with one or many employees, in any currency, and the mission order PDF.'],
        ['Overtime', 'Overtime batches calculated from fingerprint punches.'],
        ['Penalties and rewards', 'Penalty rules, generate from attendance, checkable reasons, bulk confirm, rewards.'],
        ['Advances and loans', 'Short advances, long-term loans, goods purchases and other deductions.'],
        ['Recruitment', 'Job positions with screening questions, and applicants.'],
        ['KPIs', 'Question templates and employee performance reviews.'],
        ['Reports', 'Period reports (PDF and Excel), employee file report, payroll rule setup.'],
        ['Configuration', 'Demo data, and Custody types (add or rename any item the company issues).'],
    ], [4.2, 12.2]))
    s.append(section('1.2 Who can do what'))
    s.append(table(['Role', 'Access'], [
        ['HR Officer (Employees: Officer)', 'Full access to every Tarco HRIS screen and report.'],
        ['HR Administrator (Employees: Administrator)', 'Everything an officer can do, plus the payroll rule setup action.'],
        ['Department manager', 'Can request missions for their team, approve leave as the employee approver, '
                               'and fill KPI reviews for their direct reports.'],
        ['Employee', 'Opens the HRIS dashboard for their own attendance, leave, missions, overtime, '
                     'penalties, rewards, advances, encashment, custody, work requirements and KPI reviews. Requests leave through Time Off.'],
    ], [5.4, 11.0]))
    s.append(tip('Access is given in %s. Open the user and set the Employees role.' % menu('Settings > Users & Companies > Users')))
    s.append(section('1.3 How the pieces connect'))
    s.append(flow_diagram())
    s.append(bullets([
        'The <b>employee code</b> is the key. It is generated automatically from the year and month of joining '
        '(for example 202610001), it is shown in front of the name everywhere, it can be typed in any employee '
        'field to find the person, and it is copied to the Badge ID used by the fingerprint device.',
        'Fingerprint punches from the ZKTeco devices are collected by the ZKBioTime software, and Odoo fetches the '
        'employees and their check-ins and check-outs from BioTime automatically (chapter 5.2). Tarco HRIS turns them '
        'into one <b>daily attendance</b> line per employee per day.',
        'Approved leave, approved missions and official holidays are written onto the same daily line, so every '
        'attendance report shows them.',
        'Penalties, rewards, overtime, advances, leave deductions, leave encashment, tax and social insurance are '
        'posted as <b>salary adjustments</b> and appear on the next payslip automatically.',
    ]))
    s.append(section('1.4 The HRIS dashboard'))
    s.append(p('Open %s. The first screen is the dashboard. It is the same design for everyone; the numbers change '
               'with the user\'s role. Click <b>Refresh</b> after you post or confirm records.'
               % menu('Employees > Tarco HRIS > Dashboard')))
    s.append(table(['Who opens it', 'What they see'], [
        ['HR Officer or HR Administrator', 'Company overview: every employee, probation ending, contract renewals, '
                                           'applicants, unpublished holidays, and this month\'s attendance, leave, '
                                           'missions, overtime, penalties, rewards, advances, encashment and KPIs.'],
        ['Employee (no HR role)', 'My records only. Tiles and lists are limited to the employee linked to that user. '
                                  'Other people\'s files never appear. If the user has no employee, the dashboard says so.'],
    ], [5.4, 11.0]))
    s.append(p('Each tile opens the matching list, already filtered. The pages under the tiles show the latest late '
               'or absent days, leave, missions, penalties, rewards, advances and KPI reviews.'))
    s.append(p('A second view, %s, draws the same scoped data as graphs. From the tile dashboard click '
               '<b>Charts</b>, or open the menu directly. The charts are:'
               % menu('Tarco HRIS > Dashboard charts')))
    s.append(table(['Chart', 'What it shows'], [
        ['Attendance mix (donut)', 'This month\'s daily lines split by status: present, late, absent, leave, mission, holiday, rest.'],
        ['Leave types (donut)', 'Approved leave days this month, by leave type.'],
        ['Daily attendance (histogram)', 'Present, late and absent counts for each day.'],
        ['Lateness trend (line)', 'Late minutes added up by day.'],
        ['Payroll extras (bar)', 'Overtime, penalties, rewards and encashment amounts this month.'],
        ['Headcount by department (bar)', 'Active employees per department. HR only.'],
    ], [5.4, 11.0]))
    s.append(p('Scroll the Charts page to see every graph. Daily attendance also has Graph and Pivot views: open %s '
               'and switch the view icons.' % menu('Tarco HRIS > Attendance > Daily attendance')))
    s.append(p('Extra tiles for the latest HRIS screens: <b>Work to do</b> (open work requirements), '
               '<b>Custody out</b> (issued items of any configured type) and <b>EOS to pay</b> (end of service sent to finance). '
               'HR sees the company; an employee sees only their own lines.'))
    s.append(tip('An employee must be linked on the user form (%s). The dashboard uses that link to hide other records.'
                 % menu('Settings > Users & Companies > Users')))
    s.append(section('1.5 What is new in this edition'))
    s.append(p('This guide matches <b>Tarco HRIS 19.0.1.0.29</b>. Upgrade the module on Odoo.sh, then use the menus below.'))
    s.append(table(['Version', 'What was added'], [
        ['19.0.1.0.29',
         'End of service is a form: calculate the Labour Act 1997 gratuity, or type a fixed amount for finance. '
         'Send to finance posts a Tarco Earning on the next payslip. Print the settlement. Issued custody is returned.'],
        ['19.0.1.0.28',
         'Lost button on the custody list (next to Return). Lost lines are red and are not expected back at exit.'],
        ['19.0.1.0.27',
         'Custody types are configurable. Add, rename or archive types in Configuration > Custody types '
         '(headset, keys, tools, or any item). Give custody lists those types instead of four fixed ticks.'],
        ['19.0.1.0.26',
         'Give custody in one step. Saving a line issues it at once. '
         'Resignation or dismissal automatically returns every issued item. No per-item return before exit.'],
        ['19.0.1.0.25',
         'Organization chart and department hierarchy open as the full pyramid. Every manager and department is shown; you do not click "N people" to go into each branch.'],
        ['19.0.1.0.24',
         'Organization chart (employees and managers as a pyramid) and department hierarchy; work requirements after '
         'hiring; employee custody (laptop, mobile, uniform, badge); end of service returns every issued item before '
         'resignation is recorded; dashboard tiles Work to do and Custody out; custody on the employee file PDF.'],
        ['19.0.1.0.23',
         'Period Excel exports use Soft Guide styling: navy (#0F2C4C) title and headers, teal section titles, zebra '
         'rows, freeze on the header row, autofilter, and landscape A4.'],
        ['19.0.1.0.21',
         'A mission creates a calendar meeting per employee and marks Daily attendance as Mission (draft, approved or done).'],
        ['19.0.1.0.20',
         'Confirming a payslip closes one-time salary adjustments for that month. Loans stay Running until the last instalment.'],
    ], [3.4, 13.0]))
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
        'Set each department\'s <b>Parent Department</b> and <b>Manager</b>, then set <b>Manager</b> on every employee, '
        'so %s and %s show a pyramid, not a flat list.'
        % (menu('Employee file > Organization chart'), menu('Employee file > Departments')),
        'Review custody types in %s. The four starters (laptop, mobile, uniform, badge) can be renamed. '
        'Click New to add any other item (headset, keys, SIM, tools). Tick <b>Tick by default</b> on types that '
        'should already be marked when HR opens Give custody.'
        % menu('Tarco HRIS > Configuration > Custody types'),
        'Complete every employee file (next chapter), then select the employees and click <b>Apply leave scheme</b> '
        'on the list (or Actions) to give the year\'s leave balance.',
    ]))
    s.append(note('Employees must have a Badge ID that matches their Employee ID in BioTime. When an employee '
                  'gets a code and the Badge ID is empty, the code is copied into it for you. A Badge ID that is '
                  'already filled is never changed.'))
    s.append(section('2.1 Demo data'))
    s.append(p('To try every screen with sample records, open %s. Tick <b>Activate demo data</b> and click '
               '<b>Apply</b>. Odoo creates employees, documents, onboarding, contracts, fingerprint attendance, '
               'leave, holidays, a mission, overtime, penalties, a reward, advances, a job with applicants, a KPI '
               'review, the matching salary adjustments, a manager tree (Omar at the top), department hierarchy, '
               'work requirements for Sara, issued custody (laptop, phone, uniform, badge) and Khalid\'s laptop '
               'already returned at end of service.'
               % menu('Tarco HRIS > Configuration > Demo data')))
    s.append(p('Untick the same box and click Apply to remove <b>only</b> those sample records. Records you created '
               'yourself stay. Ticking Apply again while demo data is already on replaces the sample set.'))
    s.append(note('Use demo data on a training or test database. Do not load it on the live company file if HR has '
                  'already started real work.'))
    s.append(PageBreak())

    # 3 Employee file
    s.append(chapter('3. Employee file'))
    s.append(p('All the employee information is entered from one screen. Open %s, create or open an employee, and '
               'go to the <b>HR File</b> page.' % menu('Tarco HRIS > Employee file > Employees')))
    s.append(section('3.1 Fields on the HR File page'))
    s.append(table(['Group', 'Fields'], [
        ['Identity', 'Employee code, department, section, job position, manager (the parent in the org chart), hire date, birthday, nationality, gender, '
                     'marital status, religion, qualification (basic, secondary, diploma, bachelor, higher diploma, '
                     'master, doctorate), field of study, school, years of experience.'],
        ['Contact and address', 'Private phone, work mobile, emergency phone, private email, work email, and the '
                                'address as state, city, district and block.'],
        ['Contract', 'Probation end, Payroll probation end, contract end (Payroll), annual renewal date, contract '
                     'alert, length of service, resignation date, rehire date, shift, exempt from lateness, overtime '
                     'calculation.'],
        ['Salary', 'Basic salary, cost of living allowance, transport allowance, housing allowance, other allowances, '
                   'gross salary (calculated), subject to tax and tax %, subject to social insurance and insurance %, '
                   'adjust taxes automatically, taxes posted for.'],
        ['Leave balance', 'Annual leave scheme (21 or 30 days), casual days, annual days.'],
        ['Leave encashment', 'Days and amount confirmed this month (extra on this payslip), the list of encashment '
                             'records, and the linked salary adjustment.'],
        ['Work requirements', 'Checklist after the employee is accepted: training, safety, laptop, mobile, uniform, badge, warehouse, accounts.'],
        ['Employee custody', 'Items issued by the company, of any type from Configuration &gt; Custody types. Outstanding items are returned automatically at end of service.'],
        ['Hiring and audit documents', 'One line per document with a file attachment.'],
    ], [3.8, 12.6]))
    s.append(section('3.2 Create a new employee'))
    s.append(steps([
        'Click <b>New</b> and type the employee name.',
        'On the HR File page enter the <b>Hire date</b>. The probation end (hire date + 89 days) and the annual '
        'renewal date (hire date + 1 year) fill in automatically.',
        'Leave the <b>Employee code</b> empty. It is generated when you save (see 3.3).',
        'Fill the identity, contact and address fields.',
        'Enter the salary components. The gross salary is the total and is copied to the employee contract wage.',
        'Choose the leave scheme and the shift.',
        'Add the documents and tick <b>Received</b> as each one arrives.',
        'Save.',
    ]))
    s.append(section('3.3 Automatic employee codes'))
    s.append(p('The employee code is made of the <b>year and month of joining</b> followed by a <b>3-digit serial</b> '
               'for that month. The code contains only digits, so it can also be used as the fingerprint device ID.'))
    s.append(table(['Joined', 'Order in the month', 'Code'], [
        ['3 October 2026', '1st employee', '202610001'],
        ['20 October 2026', '2nd employee', '202610002'],
        ['1 March 2024', '1st employee', '202403001'],
    ], [5.0, 5.0, 6.4]))
    s.append(bullets([
        '<b>New employee:</b> the code is created as soon as you save, from the Hire date. If the Hire date is empty, '
        'the current month is used. You can still type a code yourself to override it.',
        '<b>Existing employees:</b> in the employee list tick the employees, then choose %s. The joining month comes '
        'from the Hire date, otherwise the contract start date, otherwise the date the record was created. '
        'Employees are numbered in the order they joined. Employees whose code already matches their joining '
        'month are skipped, and a message tells you how many codes were generated.'
        % menu('Actions > Generate employee code'),
        '<b>Unique:</b> the serial continues from the highest code already used in that month, including archived '
        'employees, and the database refuses a duplicate code.',
    ]))
    s.append(note('Generating codes for existing employees does not change a Badge ID that is already filled, so '
                  'fingerprint punches keep matching. Update the device or the Badge ID yourself if you want them '
                  'to use the new code.'))
    s.append(section('3.4 Hiring and audit documents'))
    s.append(table(['Group', 'Document kinds'], [
        ['Hiring document', 'Birth certificate, qualification, experience certificates, photograph, national ID, other.'],
        ['Audit document', 'Employment application, employment contract, job description, acknowledgement of work '
                           'regulations, other.'],
    ], [3.8, 12.6]))
    s.append(section('3.5 Buttons on the employee'))
    s.append(table(['Button', 'What it does'], [
        ['Apply leave scheme', 'Creates this year\'s approved casual and annual allocations from the scheme. '
                               'Select many employees on the list and use the header button or Actions. '
                               'A type that already has an allocation this year is left as it is. Resigned staff are skipped.'],
        ['Post tax and insurance', 'Creates one-time deductions for this month: gross x tax % and gross x social '
                                   'insurance %. Shown only when Adjust taxes automatically is off. Posting twice in '
                                   'the same month is refused (see 4.5).'],
        ['Onboarding notice', 'Opens a notice to the departments that prepare for the new employee.'],
        ['Print file', 'Opens the employee file report with check boxes to choose the sections.'],
        ['Give custody', 'Opens a form listing every active custody type. Tick what you hand over, fill item / serial / quantity, click Give to employee. Add types in Configuration &gt; Custody types.'],
        ['End of service', 'Opens the end of service form: calculate the benefit or type a fixed amount, then Send to finance.'],
        ['Register resignation / Register dismissal / Rehire / Renew contract', 'See chapter 4. Exit returns all issued custody automatically.'],
        ['Smart buttons', 'Documents, Missions, Penalties, Rewards, Advances, Encashment, KPIs, Work to do, Custody out and End of service open the related records.'],
        ['Actions > Generate employee code', 'Creates the code from the joining month (see 3.3). Also available '
                                             'for many employees at once from the list.'],
    ], [4.6, 11.8]))
    s.append(section('3.6 Onboarding notice'))
    s.append(p('Use it to notify the departments concerned when someone is hired: induction training, safety '
               'briefing, computer, library tools, uniform, or supplies from the warehouse.'))
    s.append(steps([
        'On the employee click <b>Onboarding notice</b>, or open %s and click New.'
        % menu('Tarco HRIS > Employee file > Onboarding notices'),
        'Tick the items needed and add a note.',
        'Click <b>Notify departments</b>. A message is posted on the notice, a to-do activity is created for the '
        'employee\'s manager (or the HR responsible), and an email goes to the manager and the employee. '
        'A <b>work requirement</b> line is also created for every ticked item.',
    ]))
    s.append(p('The message is written as a normal letter, ready to read: a welcome line, the list of items to '
               'prepare, the job position, department, start date and manager, your note, and the HR signature. '
               'The email subject is <b>Welcome [name] - onboarding arrangements</b>.'))
    s.append(section('3.7 Finding an employee'))
    s.append(p('Type the employee code or the name in the search bar of any employee list, or in any field that '
               'asks for an employee (missions, penalties, advances and so on). The code is shown in square '
               'brackets before the name, for example <b>[202610001] Ahmed Ali</b>. Typing part of a code, such as '
               '<b>202610</b>, lists everyone who joined in that month.'))
    s.append(section('3.8 Organization chart'))
    s.append(p('The functional tree of employees and managers, and the administrative tree of departments, are both '
               'shown as a pyramid (hierarchy). The full company tree opens already expanded — you do not click each '
               'manager or department to see the people under them. Set <b>Manager</b> on the employee (parent) and '
               '<b>Parent Department</b> plus <b>Manager</b> on the department.'))
    s.append(table(['Menu', 'What you see'], [
        [menu('Employee file > Organization chart'),
         'Employees as a pyramid under their manager. Drag a card onto another manager to change the reporting line. '
         'The same hierarchy switch is also on Employees.'],
        [menu('Employee file > Departments'),
         'Departments as a pyramid (Operations under Tarco Aviation, and so on), with the department manager and headcount.'],
        ['Employee form, Organization Chart',
         'The manager above and the direct reports below the person you have open. Full Chart opens the pyramid.'],
    ], [5.6, 10.8]))
    s.append(tip('Demo data builds Omar as the top manager, Fatima and Ahmed under Omar, and Sara under Fatima, with '
                 'Operations, Finance and Human Resources under Tarco Aviation.'))
    s.append(section('3.9 Work requirements after hiring'))
    s.append(p('After the employee is accepted, HR tracks what still has to be prepared: induction, safety, laptop, '
               'mobile, uniform, badge, warehouse issue or system accounts. Open %s, or the Work to do smart button '
               'on the employee and on the dashboard.'
               % menu('Tarco HRIS > Employee file > Work requirements')))
    s.append(steps([
        'Send the onboarding notice with the needed ticks, or click New on Work requirements and choose the employee.',
        'When a task is finished (training given, account created), open it and click <b>Mark done</b>.',
        'When the item is a physical asset (laptop, phone, uniform, badge), click <b>Issue custody</b> instead. '
        'That marks the requirement done and creates an issued custody record.',
    ]))
    s.append(section('3.10 Employee custody'))
    s.append(p('Custody is company property given to the employee after hiring. Types are not fixed: HR adds them in '
               '%s. Laptop, phone, uniform and badge are created for you; add headset, keys, tools or any other item. '
               'Giving is one step. Returning everything happens automatically when the employee resigns or is dismissed.'
               % menu('Tarco HRIS > Configuration > Custody types')))
    s.append(steps([
        'On the employee click <b>Give custody</b> (header or HR File), or open %s.'
        % menu('Tarco HRIS > Employee file > Give custody'),
        'The wizard lists every active custody type. Tick the ones you are handing over. Type the model, serial or quantity.',
        'To issue a type that is not in the list, add it first in %s (or create it from the Type column), then reopen Give custody.'
        % menu('Configuration > Custody types'),
        'Click <b>Give to employee</b>. The ticked items are issued immediately (today\'s date).',
        'Or add a line on the HR File custody list: type, item, serial — saving the line issues it.',
        'If an item comes back early, click <b>Return</b> on that line. You do not need this at exit.',
        'If the item will not come back, click <b>Lost</b> next to Return. Confirm; the line turns red and is not expected at end of service.',
    ]))
    s.append(table(['Status', 'Meaning'], [
        ['Issued', 'With the employee. Shown on Custody out. Blue line.'],
        ['Returned', 'Handed back. Set by Return, or automatically on resignation / dismissal / End of service. Green line.'],
        ['Lost', 'Not returned. Click Lost on the list. Red line. Not expected back at exit.'],
    ], [3.4, 13.0]))
    s.append(note('Name, code and <b>Tick by default</b> are set per type in %s. Archive a type to hide it from Give custody without deleting history.'
                  % menu('Configuration > Custody types')))
    s.append(table(['Custody type field', 'Use'], [
        ['Name', 'Shown on Give custody and on issued lines. Translate it if you work in Arabic.'],
        ['Code', 'Short unique key (laptop, headset). Spaces become underscores; stored in lowercase.'],
        ['Tick by default', 'That row is already ticked when HR opens Give custody.'],
        ['Sequence', 'Order of the rows in Give custody.'],
        ['Active', 'Untick to archive. Old issued records keep the type; Give custody no longer lists it.'],
    ], [4.2, 12.2]))
    s.append(table(['Give custody column', 'Use'], [
        ['Give', 'Tick the types you are handing over now.'],
        ['Type', 'Any active custody type. Add a line, or create a type from this column.'],
        ['Item / model', 'Free text, for example Dell Latitude.'],
        ['Serial / tag', 'Asset tag, IMEI or badge number.'],
        ['Quantity', 'Pieces (uniform, keys). At least 1.'],
    ], [4.2, 12.2]))
    s.append(PageBreak())

    # 4 Contracts
    s.append(chapter('4. Employment contracts'))
    s.append(p('Contract dates are kept on the employee. Use %s to see every employee with hire, probation, contract '
               'end, resignation and rehire dates and the length of service.' % menu('Tarco HRIS > Contracts > Contracts')))
    s.append(section('4.1 Probation and renewal dates'))
    s.append(bullets([
        '<b>Probation end</b> is set to hire date + 89 days and is copied to the trial end date on the employee '
        '<b>Payroll</b> page. If you change it by hand, <b>Probation set manually</b> is ticked and the date is no '
        'longer recalculated. %s shows only employees whose <b>Payroll probation / trial end</b> falls in the next '
        '10 days. People with no trial end date on Payroll are not listed.'
        % menu('Contracts > Probation ending'),
        '<b>Contract end</b> is the expiry date on the employee <b>Payroll</b> page (Odoo contract end). '
        '%s shows only employees whose contract end falls in the next 10 days. Open-ended contracts (no end date) '
        'and the automatic annual review date are not used for this list.'
        % menu('Contracts > Renewals due'),
        '<b>Annual renewal date</b> is set to hire date + 1 year for yearly review. It does not put the employee on '
        'Renewals due. Tick <b>Renewal set manually</b> to keep your own review date.',
        'The probation end and the gross salary are copied to the Odoo contract of the employee.',
    ]))
    s.append(section('4.2 Alerts 7 to 10 days before'))
    s.append(p('Every day the scheduled action <b>Tarco HRIS: attendance and contract alerts</b> looks for probation '
               'ends and <b>Payroll contract end dates</b> in the next 10 days. For each one it creates a to-do '
               'activity for the HR responsible on the contract (or the manager) and emails the employee, the manager '
               'and that user. Each date is alerted only once; changing the date resets the alert.'))
    s.append(p('Use %s and %s to see the lists at any time. They use the search filters <b>Probation ending '
               '(10 days)</b> and <b>Contract expiry (10 days)</b>, which you can also apply on any employee list.'
               % (menu('Contracts > Probation ending'), menu('Contracts > Renewals due'))))
    s.append(section('4.3 Renew, resign and rehire'))
    s.append(table(['Action', 'How', 'Result'], [
        ['Renew the contract', 'Click <b>Renew contract</b> on the employee.', 'Renewal date moves forward one year.'],
        ['Resignation', 'Click <b>Register resignation</b>. Choose the last working day. The wizard lists issued '
                        'custody for information only. Click <b>Confirm and return custody</b>.',
         'Resignation date is set. Every issued custody item (any type) is returned automatically.'],
        ['Dismissal / Fired', 'Click <b>Register dismissal</b>. Same one-step confirm.',
         'Last working day is set as a dismissal. All issued custody is returned automatically.'],
        ['Rehire', 'Unarchive the employee if needed, then click <b>Rehire</b>.',
         'Same employee and same code. The rehire date is today, the resignation is cleared, and new probation and '
         'renewal dates are calculated from today. The original hire date is kept.'],
    ], [3.4, 5.4, 7.6]))
    s.append(section('4.4 End of service payment'))
    s.append(p('Use the End of service form when finance must pay a leaving benefit. Open it from the employee '
               '(<b>End of service</b>) or from %s.' % menu('Tarco HRIS > Contracts > End of service')))
    s.append(steps([
        'Choose the employee, last working day and reason (resignation, dismissal, contract end or retirement).',
        'Leave <b>Amount</b> on Calculate to use Sudan Labour Act 1997: half a month of the last gross wage for each '
        'of the first five years, then one full month for each year after that. Incomplete years are included.',
        'Or set Amount to <b>Fixed amount</b> and type what finance should pay (a negotiated figure). The calculated '
        'amount stays on the form as a reference.',
        'Tick <b>Dismissed for misconduct</b> only when there is no gratuity. The calculated amount becomes 0.',
        'Click <b>Send to finance</b>. Issued custody is returned, the last working day is recorded, and a Tarco Earning '
        'is posted for the payslip. Print the settlement for the employee file and for finance.',
        'When payroll confirms the payslip the form becomes Paid. If finance pays outside payroll, click <b>Mark paid</b>.',
    ]))
    s.append(table(['Status', 'Meaning'], [
        ['Draft', 'HR is preparing the form. Amount can still be calculated or typed.'],
        ['Sent to finance', 'Tarco Earning is on the next payslip. Print the settlement for finance.'],
        ['Paid', 'Payslip confirmed, or HR clicked Mark paid after an outside payment.'],
        ['Cancelled', 'No payment. The payroll line is closed.'],
    ], [3.4, 13.0]))
    s.append(note('Register resignation still exists for a last working day with no payment. Use End of service when an amount must go to finance.'))
    s.append(section('4.5 Statutory and internal deductions'))
    s.append(p('On the HR File page tick <b>Subject to tax</b> and/or <b>Subject to social insurance</b> and enter the '
               'percentages. Then choose how the monthly deduction is posted with the <b>Adjust taxes '
               'automatically</b> flag, shown under the tax fields.'))
    s.append(table(['Adjust taxes automatically', 'What happens each month'], [
        ['Ticked', 'At the start of every month the daily scheduled action creates the income tax and social '
                   'insurance salary adjustments (gross x %) for the month. They are deducted on that month\'s '
                   'payslip. Nobody has to click anything, and the Post tax and insurance button is hidden.'],
        ['Not ticked', 'An HR officer opens the employee and clicks <b>Post tax and insurance</b> once every payroll '
                       'month, before running payroll.'],
    ], [4.2, 12.2]))
    s.append(bullets([
        'The field <b>Taxes posted for</b> shows the last month posted. Each month is posted only once, whether by '
        'the button or automatically, so clicking again in the same month does nothing and shows a message.',
        'The amount uses the gross salary at the moment of posting. If the salary changes after the month is '
        'posted, edit that month\'s adjustment in %s.' % menu('Payroll > Employees > Salary Adjustments'),
        'Automatic posting stops for archived employees and for months after the resignation date.',
        'The adjustments are named, for example, <b>Income tax 10/2026 [202610001] Ahmed Ali</b>.',
    ]))
    s.append(tip('Tick Adjust taxes automatically for all permanent staff, and leave it off only for cases HR wants to '
                 'check by hand each month.'))
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
    s.append(section('5.2 Fingerprint devices and BioTime'))
    s.append(p('Tarco HRIS works with <b>ZKTeco biometric devices</b> (fingerprint, face and card terminals) managed '
               'by the <b>ZKBioTime</b> attendance software. Odoo does not talk to each terminal: it is linked to the '
               'BioTime server, which already collects the punches from every device on site. From BioTime, Odoo '
               'fetches all employees and all their check-in and check-out punches, with no manual entry.'))
    s.append(chain_diagram([
        ('ZKTeco devices', 'finger / face / card'),
        ('ZKBioTime', 'collects all punches'),
        ('Odoo Attendance', 'check-in / check-out'),
        ('Daily attendance', 'Tarco HRIS summary'),
        ('Reports and payroll', 'lateness, overtime'),
    ]))
    s.append(table(['Data fetched from BioTime', 'What Odoo does with it'], [
        ['Employees', 'All BioTime employees are read with their employee ID, name and department. Each one is '
                      'matched to the Odoo employee whose <b>Badge ID</b> equals the BioTime employee ID.'],
        ['Check-in punches', 'Create the check-in of an attendance line in Odoo Attendance.'],
        ['Check-out punches', 'Close the open attendance line with the check-out time.'],
        ['Punch time', 'Converted from the BioTime server time zone to Odoo time, so lateness after 08:15 is '
                       'measured in local time.'],
        ['Terminal', 'The device that recorded the punch is kept for checking.'],
    ], [4.4, 12.0]))
    s.append(Paragraph('Matching employees', ParagraphStyle('H3', parent=BODY, fontName=FB, textColor=NAVY,
                                                            spaceBefore=4, spaceAfter=3)))
    s.append(bullets([
        'Use the same number everywhere: the <b>employee code</b> in Odoo (for example 202610001), the <b>Badge ID</b> '
        'in Odoo and the <b>Employee ID</b> in BioTime.',
        'When an employee gets a code and the Badge ID is empty, the code is copied into the Badge ID automatically '
        '(chapter 3.3). Enroll the employee in BioTime with the same number.',
        'For staff already enrolled in BioTime with another number, type that number in the Badge ID so the punches '
        'match. A filled Badge ID is never changed by Odoo.',
    ]))
    s.append(Paragraph('Setting up the link', ParagraphStyle('H3b', parent=BODY, fontName=FB, textColor=NAVY,
                                                             spaceBefore=4, spaceAfter=3)))
    s.append(steps([
        'In BioTime, add all terminals and check that they are online and that punches appear in BioTime '
        'transactions.',
        'In BioTime, create a user for Odoo with permission to read employees and transactions (API access).',
        'In the BioTime connection settings in Odoo, enter the BioTime server address and port, that user and its '
        'password, then test the connection.',
        'Fetch the employees once and check that every active employee is matched by Badge ID.',
        'Leave the scheduled fetch active so new punches arrive in Odoo Attendance automatically during the day.',
    ]))
    s.append(note('The Odoo server must be able to reach the BioTime server on the network (same LAN or VPN), and the '
                  'BioTime server clock and time zone must be correct. A wrong clock shifts every punch and creates '
                  'false lateness.'))
    s.append(section('5.3 Daily attendance'))
    s.append(p('Every day Tarco HRIS summarises the last three days of punches into %s: one line per employee per day '
               'with the first check-in, the last check-out, worked hours, late minutes and overtime. You can also '
               'summarise any period with the <b>Sync fingerprint</b> button of the period report (chapter 13), for '
               'example after BioTime was offline and the punches arrived late.'
               % menu('Attendance > Daily attendance')))
    s.append(table(['Status', 'When it is used'], [
        ['Present', 'Punched in on time and out.'],
        ['Late', 'Punched in after the grace period. The late minutes are shown.'],
        ['Absent', 'No punch on a working day with no leave, mission or holiday.'],
        ['Leave', 'An approved leave covers the day.'],
        ['Mission', 'A mission (draft, approved or done) covers the day for that employee.'],
        ['Public holiday', 'An official holiday, with no punch.'],
        ['Rest day', 'The shift rest day, with no punch.'],
        ['Missing checkout', 'Punched in but not out. Correct the punch in Attendance and sync again.'],
    ], [3.6, 12.8]))
    s.append(section('5.4 How the day is calculated'))
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
               '= 6 casual + 24 annual. You can change the casual and annual days by hand. At the start of each year, '
               'open the employee list, select everyone who needs a balance, and click <b>Apply leave scheme</b> in '
               'the list header or under Actions. The form button still applies one employee. A type that already has '
               'an allocation this year is left as it is. Resigned staff are skipped. A notification shows how many '
               'received allocations, already had this year, or were skipped.'))
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
        'Click <b>Publish on calendar</b>. Status becomes <b>Published</b>, the button is replaced by '
        '<b>Update on calendar</b> / <b>Remove from calendar</b>, and a company time off is created on the working '
        'calendar for the observed date. After you move a date, click Update on calendar.',
    ]))
    s.append(section('6.5 Leave encashment (selling leave)'))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Leave > Leave encashment'),
        'Choose the employee and the number of days. The daily rate defaults to gross / 30 and can be changed.',
        'Click <b>Confirm</b>. The amount is posted as a salary adjustment (Tarco Earning) and is paid extra on '
        'that month\'s payslip. Reduce the remaining balance in Time Off allocations if the sold days must be '
        'removed from it.',
    ]))
    s.append(p('On the employee, the <b>Encashment</b> smart button opens all leave encashment records. The '
               '<b>HR File</b> page shows <b>Encashment days this month</b> and <b>Encashment this month</b> — the '
               'extra amount confirmed for the current calendar month — plus the list of records and the linked '
               'salary adjustment, same as other payroll extras.'))
    s.append(PageBreak())

    # 7 Missions
    s.append(chapter('7. Missions'))
    s.append(p('A mission can be requested by the department manager or by HR, at any time of day, and can include '
               'many employees without opening each employee.'))
    s.append(section('7.1 Create and approve a mission'))
    s.append(steps([
        'Open %s and click New.' % menu('Tarco HRIS > Missions'),
        'Enter the place, purpose, start and end dates, departure time and end time (any time in 24 hours).',
        'Choose the <b>Mission currency</b>, for example USD for a mission abroad. It defaults to the company currency.',
        'Enter the cost per person per day, in the mission currency, if the mission has an allowance.',
        'Add employees on the lines by code or by name. Each line shows the job and the employee\'s amount.',
        'Save. Each employee is booked on their own calendar for those dates, and their daily attendance '
        'for those days is set to <b>Mission</b>.',
        'HR clicks <b>Approve</b>. The calendar stays booked and attendance stays Mission.',
        'Click <b>Done</b> when the mission is finished, or <b>Cancel</b> to drop it from the calendar and '
        'from attendance.',
    ]))
    s.append(p('The form calculates the number of days, the number of employees, total hours (hours per day x days x '
               'employees) and the total cost (cost per day x days x employees).'))
    s.append(section('7.2 Mission currency'))
    s.append(table(['Amount', 'Currency', 'How it is calculated'], [
        ['Cost per person per day', 'Mission currency', 'Entered by you.'],
        ['Employee amount (on each line)', 'Mission currency', 'Cost per day x number of days.'],
        ['Total cost', 'Mission currency', 'Cost per day x days x employees. The line total matches it.'],
        ['Total cost in company currency', 'Company currency', 'Total cost converted at the exchange rate of the '
                                                               'mission start date. Shown only when the currencies differ.'],
    ], [4.6, 3.4, 8.4]))
    s.append(bullets([
        'The currency can be changed only while the mission is in Draft, so approved amounts stay in the approved '
        'currency.',
        'The Missions list shows the currency of each mission. Add the optional column <b>Total cost in company '
        'currency</b> to see a total for all missions together.',
        'The Missions period report (chapter 13) shows each mission in its own currency and in company currency, and '
        'adds up the cost per place in company currency.',
    ]))
    s.append(note('Activate the currency and keep its exchange rates up to date in %s (or Invoicing &gt; '
                  'Configuration &gt; Currencies). Without a rate for the mission date, the company currency amount '
                  'equals the mission amount.' % menu('Accounting > Configuration > Currencies')))
    s.append(section('7.3 Print the mission order'))
    s.append(p('Click <b>Print mission order</b> at the top of the mission, or select one or more missions in the list '
               'and choose %s. The PDF is printed on the company letterhead and contains:' % menu('Print > Mission Order')))
    s.append(bullets([
        'the reference, status, place, currency, dates with departure and end times, days, employees, cost per day '
        'and total hours;',
        'the purpose of the mission;',
        'the employee table with code, name, department, job, days and amount, and the total in the mission currency;',
        'the equivalent in company currency when the mission is in another currency;',
        'signature boxes for the requester, Human Resources and the approver.',
    ]))
    s.append(tip('Print the mission order after approval and hand it to the employees with their allowance.'))
    s.append(section('7.4 Calendar and attendance'))
    s.append(p('As soon as the mission is saved with employees and dates, Tarco HRIS books it in two places:'))
    s.append(table(['Where', 'What you see'], [
        ['Odoo Calendar', 'One meeting per employee on those dates, named Mission: place — employee. '
                          'The employee (and you) are attendees, so it appears on that employee\'s calendar only '
                          'with their name. Draft shows as free time; approved or done shows as busy.'],
        ['Missions calendar', 'Open %s and switch to the calendar. Filter by employee to see only that person.'
         % menu('Tarco HRIS > Missions')],
        ['Daily attendance', 'Each day of the mission for that employee is status <b>Mission</b>, with the place '
                             'in the note. Open the attendance calendar to see it by employee. Those days are not '
                             'treated as absence.'],
    ], [4.4, 12.0]))
    s.append(bullets([
        'Click <b>Open calendar</b> on the mission, or the Calendar smart button, to jump to the meetings.',
        'Each employee line has a Calendar link you can open.',
        'Changing the dates or employees updates the calendar and rewrites attendance.',
        'Cancel removes the meetings and recalculates attendance (present, absent, leave, and so on).',
        'Existing missions are booked on the calendar and attendance when you upgrade to 19.0.1.0.21.',
    ]))
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
    s.append(p('The wizard does not invent penalties. It reads the <b>daily attendance</b> sheet (chapter 5.3) for the '
               'dates you choose and creates <b>one draft penalty per employee per day</b> that qualifies.'))
    s.append(table(['Wizard option', 'Created when', 'Amount'], [
        ['Include lateness', 'The attendance day has late minutes: check-in after shift start plus grace '
                             '(default 08:00 + 15 minutes). Staff marked Exempt from lateness are skipped.',
         'Late hours x hourly wage (gross / 30 / 8). Rule: Lateness.'],
        ['Include absence', 'The attendance day status is Absent: a working day after hire and before resignation, '
                            'with no check-in, and not on approved leave, an approved mission, a public holiday or a '
                            'shift rest day.',
         'One day of wage (gross / 30). Rule: Absence.'],
    ], [3.6, 8.4, 4.4]))
    s.append(p('A day that already has a non-cancelled penalty for the same employee, rule and date is not created '
               'again. <b>Conduct</b> penalties are never generated here — enter those by hand (9.5).'))
    s.append(section('9.3 Reason on each generated penalty'))
    s.append(p('Every generated penalty fills the <b>Reason</b> field with the attendance facts so HR can check the '
               'record against the system before confirming. The first line names the type, date, employee and code; '
               'the following lines list:'))
    s.append(bullets([
        'Department, and the shift with start and end (or that no shift is assigned — treated as a working day 08:00-16:00).',
        'Check-in and check-out times, or <b>none</b>.',
        'For lateness: minutes after the grace limit (for example 27 minutes after 08:15).',
        'Whether the day was leave, mission, public holiday or rest day.',
        'The attendance day status. Open %s for that employee and date to confirm.'
        % menu('Attendance > Daily attendance'),
    ]))
    s.append(p('The Reason column is shown on the penalties list. Drafts created before this text still show the old '
               'legal sentence. Select them and click <b>Fill reason from attendance</b>, or run Generate from '
               'attendance again on the same dates — draft reasons are updated and duplicates are not created.'))
    s.append(section('9.4 Generate and confirm in bulk'))
    s.append(steps([
        'Open %s.' % menu('Penalties and rewards > Generate from attendance'),
        'Choose the period, optionally a department, and tick lateness and/or absence.',
        'Click <b>Generate</b>. The list of generated drafts opens, each with a clear reason.',
        'Read the Reason column. Cancel any line that is not correct (for example a missing BioTime punch).',
        'Select the drafts to apply. Click <b>Confirm selected</b> at the top of the list, or use '
        '%s. Only Draft rows are posted to payroll; already confirmed rows are skipped.'
        % menu('Actions > Confirm penalties'),
    ]))
    s.append(tip('You can confirm dozens of drafts in one click. Do not confirm a line until the reason matches Daily attendance.'))
    s.append(section('9.5 Conduct penalties on one employee or a group'))
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
    s.append(section('9.6 Rewards and grants'))
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
    s.append(tip('The application link uses the Odoo base URL. It must be reachable from the internet for outside '
                 'candidates to apply.'))
    s.append(section('11.2 Applications and ranking'))
    s.append(p('Candidates open the link, answer the questions and upload their CV. Each application gets a '
               '<b>Match %</b>: up to 80% for answers that match, plus up to 20% for complete information (name, '
               'email, phone, CV, qualification). Applicants are listed from the highest match down.'))
    s.append(section('11.3 Screening tracks and interviews'))
    s.append(steps([
        'Open %s. Use the filters Shortlisted, Maybe and Rejected.' % menu('Tarco HRIS > Recruitment > Applicants'),
        'On each applicant set the <b>Screening track</b> to Shortlisted, Maybe or Rejected.',
        'Set the <b>Interview</b> date and time and the interview round.',
        'Click <b>Email interview time</b>. The candidate receives the invitation from the company email, with the '
        'date and time in local time.',
    ]))
    s.append(PageBreak())
    s.append(section('11.4 Interview meeting in the calendar'))
    s.append(p('Email interview time also books the interview in the Odoo calendar, so nobody has to create the '
               'meeting by hand.'))
    s.append(bullets([
        'A one-hour meeting named after the round and the candidate (for example <b>First interview - Ethan '
        'Carter</b>) is created at the interview date and time.',
        'The attendees are the candidate, the interviewers, the recruiter, the department manager and you.',
        'The <b>Meeting</b> smart button at the top of the applicant shows the date and time, for example '
        '<b>1 Meeting - 29 Oct 2026, 1:00 PM</b>. Click it to open the calendar.',
        'The <b>Interview meeting</b> field under Tarco screening opens the meeting itself.',
        'If you change the interview date, time or round, the same meeting moves. No second meeting is created.',
    ]))
    s.append(note('Set the interview date and time before clicking Email interview time. Without it Odoo stops with a '
                  'message instead of sending.'))
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
        ['Missions', 'Missions', 'Missions with currency and cost, cost in company currency, and hours and cost per place.'],
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
               'salary, documents, custody and work requirements, contract, leave including this month\'s encashment, attendance, penalties, rewards, '
               'advances, KPIs) and click <b>Print</b>. The custody section prints number, type name (from Configuration &gt; Custody types), item, serial and status.'
               % menu('Reports > Employee file report')))
    s.append(p('On an End of service form click <b>Print</b> for the settlement PDF: employee, length of service, calculated or fixed amount, amount for finance, and signature lines for HR, finance and the employee.'))
    s.append(section('13.3 Arabic font on printed PDFs'))
    s.append(p('All Tarco HRIS PDF reports — period reports, the employee file, the mission order and the end of service settlement — are printed '
               'with <b>IBM Plex Sans Arabic</b>, so Arabic names, legal texts and headings stay clear next to the '
               'English text. Latin text uses DejaVu so letters are not doubled by wkhtmltopdf.'))
    s.append(section('13.4 Excel export style'))
    s.append(p('Click <b>Export Excel</b> on any period report. The workbook is no longer a plain white sheet. Every '
               'file uses the Soft Guide colours:'))
    s.append(table(['Part of the sheet', 'How it looks'], [
        ['Row 1 — company and report title', 'Navy band (#0F2C4C), white 16 pt text.'],
        ['Row 2 — period', 'Light slate subtitle.'],
        ['Row 3 — section name', 'Teal (#13A89E) heading.'],
        ['Row 4 — column headers', 'Navy, white, centred, with wrap. The pane is frozen at A5. Autofilter is on.'],
        ['Data rows', 'Calibri 10, thin #C5CDD6 borders, zebra fill #F4F7FA on alternate rows, numbers and dates formatted.'],
        ['Page setup', 'Landscape A4, fit to width, header and footer with the report name.'],
    ], [5.4, 11.0]))
    s.append(note('If an older export still looks unstyled, upgrade to 19.0.1.0.23 or later and export again. '
                  'Do not reuse a file that was saved before the upgrade.'))
    s.append(PageBreak())

    # 14 Payroll
    s.append(chapter('14. Payroll integration'))
    s.append(p('Tarco HRIS does not change how payslips are computed. It creates salary adjustments in %s that '
               'payroll picks up on the next payslip.' % menu('Payroll > Employees > Salary Adjustments')))
    s.append(table(['Source', 'Adjustment type', 'Effect on payslip'], [
        ['Rewards, overtime, leave encashment, end of service', 'Tarco Earning', 'Added to gross'],
        ['Penalties, advances, leave deductions, tax, social insurance', 'Tarco Deduction', 'Deducted from net'],
    ], [6.4, 3.6, 6.4]))
    s.append(p('Each adjustment carries a description such as "Penalty Lateness" or "Overtime OT/2026/0003", so the '
               'payslip lines are easy to read.'))
    s.append(section('14.1 After the payslip is done'))
    s.append(p('When HR confirms the payslip (Done / Validated), Tarco HRIS records that month against the linked '
               'salary adjustments. You do not have to mark the slip as Paid for this to happen.'))
    s.append(table(['Adjustment', 'What happens when the payslip is done'], [
        ['One-time (overtime, reward, penalty, tax, insurance, encashment, leave deduction, one-month advance)',
         'Status becomes Closed. Paid amount equals the month amount. It will not appear on the next payslip.'],
        ['Running loan or multi-month advance',
         'Stays Running. Only this month\'s instalment is marked paid. Remaining amount drops. It closes when the last instalment is on a done payslip.'],
    ], [6.2, 10.2]))
    s.append(tip('Open %s after you confirm October payroll: October overtime, tax and rewards should be Closed. '
                 'A laptop loan still shows Running with a smaller remaining amount.'
                 % menu('Payroll > Employees > Salary Adjustments')))
    s.append(note('If a new payroll structure is created, run %s (HR Administrator) so it gets the Tarco Earning '
                  'and Tarco Deduction rules. Otherwise the daily scheduled action adds them the next day.'
                  % menu('Reports > Create payroll rules')))
    s.append(PageBreak())

    # 15 Daily routine
    s.append(chapter('15. Daily and monthly routine'))
    s.append(table(['When', 'Who', 'Task'], [
        ['Daily', 'HR and employees', 'Open the HRIS dashboard tiles, then Dashboard charts, and work every tile that is not zero.'],
        ['Daily', 'HR', 'Check activities for probation and renewal alerts. Fix missing checkouts in Attendance.'],
        ['Daily', 'Managers', 'Request leave and missions for the team.'],
        ['Daily', 'HR', 'Approve leave and missions. Give custody from the configured types. Check Custody out. Use End of service to send the leaving amount to finance.'],
        ['Month end', 'HR', 'Generate lateness and absence penalties, check each Reason against Daily attendance, '
                            'then click Confirm selected.'],
        ['Month end', 'HR', 'Create and confirm the overtime batch.'],
        ['Month end', 'HR', 'Post tax and insurance for employees without Adjust taxes automatically. The others '
                            'are posted by the system at the start of the month.'],
        ['Month end', 'HR', 'Confirm rewards, advances and encashments. On each employee, check Encashment this month '
                            'before running payroll.'],
        ['Month end', 'HR', 'Print the monthly reports.'],
        ['Year start', 'HR', 'Enter official holidays. Select the employees and click Apply leave scheme once for all of them.'],
        ['Each review period', 'Managers', 'Fill KPI reviews.'],
    ], [3.2, 2.6, 10.6]))

    # 16 Troubleshooting
    s.append(PageBreak())
    s.append(chapter('16. Troubleshooting'))
    s.append(table(['Problem', 'Solution'], [
        ['An employee is absent although they came.', 'Check the punch is in BioTime transactions, the Badge ID matches '
                                                       'the BioTime Employee ID and the punch is in Odoo Attendance, '
                                                       'then sync the period again.'],
        ['No new punches since this morning.', 'Check the BioTime server is running and reachable from Odoo, the '
                                               'devices are online in BioTime, and the scheduled fetch is active.'],
        ['Punches are a few hours early or late.', 'Correct the BioTime server clock and time zone, and the time zone '
                                                   'of the Odoo user that runs the fetch.'],
        ['A BioTime employee is not matched.', 'Type the BioTime Employee ID in the Badge ID of the Odoo employee, '
                                               'then fetch again.'],
        ['Status is Missing checkout.', 'Add the check-out in Attendance and sync again.'],
        ['Overtime amount is zero.', 'Check the salary components are filled and Overtime calculation is not '
                                     '"Do not pay overtime".'],
        ['Too many absence drafts after Generate.', 'A wide date range or missing BioTime punches marks working days '
                                                     'as Absent. Check Daily attendance, cancel the wrong drafts, and '
                                                     'fix Badge IDs or punches before generating again.'],
        ['Reason still shows the old legal sentence.', 'Select the drafts and click Fill reason from attendance, or '
                                                       'generate the same dates again. Drafts are updated, not duplicated.'],
        ['Confirm selected does nothing.', 'Only Draft rows are confirmed. Already confirmed or cancelled records '
                                           'are skipped.'],
        ['Penalty, reward, encashment or advance is not on the payslip.', 'Make sure the record is confirmed, the '
                                                                          'payslip period covers the date, and the '
                                                                          'structure has the Tarco rules. Encashment '
                                                                          'this month on the HR File page must be '
                                                                          'greater than zero.'],
        ['Cannot save an advance.', 'The monthly instalment is higher than the gross salary. Add instalments.'],
        ['Renewals due shows everyone, or the wrong people.', 'The list uses the Contract end date on the Payroll page, '
                                                              'not the automatic annual review date. Set that end date. '
                                                              'Open-ended contracts (no end date) are not listed.'],
        ['Probation ending is empty or shows everyone.', 'The list uses the trial / probation end date on the Payroll '
                                                         'page, due in the next 10 days. Save the employee so the HR '
                                                         'File probation end is copied to Payroll, or set it on Payroll.'],
        ['Probation date did not change with the hire date.', 'Probation set manually is ticked. Untick it and set '
                                                             'the hire date again.'],
        ['No contract alert was received.', 'The alert is sent once per date. Make sure the employee and manager have '
                                            'work emails and that outgoing mail is configured.'],
        ['Salary adjustments stay Running after the payslip is done.', 'Upgrade to 19.0.1.0.20. Confirming the slip '
                                                                       'now closes one-time adjustments for that month. '
                                                                       'A loan stays Running until the last instalment. '
                                                                       'Already confirmed slips are closed on upgrade.'],
        ['Leave balance is empty.', 'Select the employees and click Apply leave scheme on the list (or Actions). '
                                    'The form button still works for one person.'],
        ['Demo data is still there after unticking.', 'Open %s, leave Activate demo data unticked and click Apply. '
                                                      'Only records created as demo are removed.'
         % menu('Tarco HRIS > Configuration > Demo data')],
        ['Code already used.', 'Each employee code must be unique, including archived employees. Clear the code and '
                               'save, or use Actions &gt; Generate employee code, to get the next free code.'],
        ['Employee has no code or an old-style code.', 'Select the employees in the list and use Actions &gt; '
                                                       'Generate employee code.'],
        ['Tax or insurance missing on the payslip.', 'Check Subject to tax / insurance, the % and the salary are set. '
                                                     'With Adjust taxes automatically, the scheduled action posts it '
                                                     'within a day; otherwise click Post tax and insurance.'],
        ['Post tax and insurance does nothing.', 'The month is already posted (see Taxes posted for). Edit the '
                                                 'existing adjustment in Payroll instead.'],
        ['Interview not in the calendar.', 'Set the interview date and time, then click Email interview time again. '
                                           'The meeting is created or updated.'],
        ['Mission not on the calendar or attendance is not Mission.', 'Upgrade to 19.0.1.0.21. Save the mission with '
                                                                      'at least one employee and dates. Open Calendar '
                                                                      'or Daily attendance and filter that employee. '
                                                                      'Cancel clears both; existing missions are '
                                                                      'booked on upgrade.'],
        ['Organization chart is empty or flat.', 'Set Manager on each employee (HR File) and Parent Department on departments. '
                                                 'Upgrade to 19.0.1.0.25 and open Employee file > Organization chart. The full tree opens expanded.'],
        ['Cannot register resignation.', 'Upgrade to 19.0.1.0.26. Confirm resignation or dismissal once; issued custody is returned automatically.'],
        ['Give custody still shows four fixed ticks.', 'Upgrade to 19.0.1.0.27. Add or rename types in Configuration > Custody types; Give custody lists every active type.'],
        ['Need to pay end of service.', 'Upgrade to 19.0.1.0.29. Open End of service on the employee, Calculate or type a Fixed amount, then Send to finance.'],
        ['No Lost button on custody.', 'Upgrade to 19.0.1.0.28. Click Lost next to Return; the line turns red.'],
        ['Onboarding sent but no custody.', 'Onboarding only prepares the list. Click Give custody on the employee and tick the items you handed over.'],
        ['Excel report has a white header and no style.', 'Upgrade to 19.0.1.0.23 or later and click Export Excel again. '
                                                          'The new file has a navy title, navy headers, zebra rows and a freeze pane.'],
    ], [5.6, 10.8]))

    # Support
    s.append(CondPageBreak(7 * cm))
    s.append(chapter('17. Support'))
    s.append(p('For training, changes or support on Tarco HRIS, contact <b>%s</b> at <b>%s</b>.' % (COMPANY, SITE)))
    s.append(contact_card())
    s.append(p('When you report a problem, include the menu you used, the employee code, the record number '
               '(for example PEN/2026/0012) and a screenshot.'))
    return with_heading_breaks(s)


def with_heading_breaks(story):
    def is_heading(flowable):
        return isinstance(flowable, ChapterBanner) or (
            isinstance(flowable, Paragraph) and flowable.style.name == 'H2')

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
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'Tarco_HRIS_User_Guide.pdf')
    doc = GuideDoc(out)
    doc.multiBuild(build_story())
    print(out)


if __name__ == '__main__':
    main()

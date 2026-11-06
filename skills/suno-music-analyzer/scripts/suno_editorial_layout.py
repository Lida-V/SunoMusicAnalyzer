"""One-page A3 music analysis layout; inputs have already passed validation.

The visual theme (colours, fonts, header motif) follows the song's genre and
mood via suno_report_themes. Content rules are unchanged: missing values stay
"未取得", every value carries its source tag, nothing is truncated.
"""
import html
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from suno_report_themes import choose_theme, draw_header, register_fonts

SOURCE = {'audio-listen': '聴', 'audio-analysis': '構', 'audio-listen+audio-analysis': '聴/構', 'audio-retrieve': '曲',
          'user': '指', 'local': '測', 'agent': '案', 'unknown': '不'}
LEFT, RIGHT_EDGE, BOTTOM = 40, 802, 20
WIDTH = RIGHT_EDGE - LEFT
COL, X_RIGHT = 368, 434
HEADER_H = 236


def _styles(theme, scale=1.0):
    hf, bf, bb = theme['heading'], 'Gothic', 'GothicB'
    k = lambda v: round(v * scale, 2)  # body-text scale for auto-fit; headings and metrics keep their size
    ink, muted, accent = (colors.HexColor(theme[k]) for k in ('ink', 'muted', 'accent'))
    s = lambda name, font, size, lead, color, **kw: ParagraphStyle(name, fontName=font, fontSize=size, leading=lead, textColor=color, wordWrap='CJK', **kw)
    return {
        'kicker': s('kicker', bb, 10.5, 14, colors.HexColor(theme['header_muted'])),
        'title': s('title', hf, 34, 42, colors.HexColor(theme['header_ink'])),
        'chip_h': s('chip_h', bb, 10.5, 14, colors.HexColor(theme['header_ink'])),
        'subtitle': s('subtitle', bf, 12.5, 17, colors.HexColor(theme['header_muted'])),
        'section': s('section', hf, 17, 21, ink),
        'label': s('label', bb, k(10.5), k(14), accent),
        'body': s('body', bf, k(12.5), k(17.5), ink),
        'small': s('small', bf, k(11.3), k(15.5), ink),
        'muted': s('muted', bf, k(10.3), k(14.5), muted),
        'metric_label': s('metric_label', bb, 10, 13, colors.HexColor(theme['header_muted'])),
        'metric': s('metric', bb, 21, 26, colors.HexColor(theme['header_ink'])),
        'summary': s('summary', hf, k(14.5), k(21.5), ink),
        'alert': s('alert', bf, k(11.5), k(16), colors.HexColor('#6e3320')),
        'chip': s('chip', bb, k(12.5), k(16), ink),
    }


def _layout(data, fmt_seconds, theme, styles, gap):
    commands = []
    sources = data.get('sources', {})

    def paragraph(markup, x, top, w, style='body', escape=True):
        text = html.escape(str(markup)).replace('\n', '<br/>') if escape else markup
        p = Paragraph(text, styles[style])
        _, h = p.wrap(w, 3000)
        commands.append(('paragraph', p, x, top - h))
        return h

    def tag(field):
        value = data.get(field)
        if value is None or value == '' or (value == [] and field not in data.get('sources', {})):
            return ''
        return ' ［' + SOURCE[sources.get(field, 'unknown')] + '］'

    def text(field):
        value = data.get(field)
        if field == 'genre_match' and not (data.get('target_genre') or '').strip():
            return '判定保留（目標ジャンル未取得）'
        if field == 'lyrics_tags' and value == [] and field in data.get('sources', {}):
            return 'なし（歌詞欄にタグの入力なし）'
        if value is None or (isinstance(value, str) and not value.strip()) or value == []:
            return '未取得'
        if field == 'duration_seconds':
            return fmt_seconds(value)
        if field == 'tempo_bpm':
            return f'{value:g} BPM（推定）'
        if field in ('meter', 'key'):
            return str(value) + '（推定）'
        if field == 'lyrics_tags':
            return ' '.join(value)
        return str(value)

    def labeled(label, value, x, top, w, style='body', source='', stacked=False):
        if stacked:
            h1 = paragraph(label + source, x, top, w, 'label')
            h2 = paragraph(value, x, top - h1 - 2, w, style)
            return h1 + 2 + h2
        markup = ('<font name="GothicB" color="' + theme['accent'] + '">' + html.escape(label) + '</font>'
                  + ('<font size="' + str(styles[style].fontSize - 1.5) + '" color="' + theme['muted'] + '">' + html.escape(source) + '</font>' if source else '')
                  + '　' + html.escape(str(value)).replace(chr(10), '<br/>'))
        return paragraph(markup, x, top, w, style, escape=False)

    def field(label, name, x, top, w, style='body'):
        return labeled(label, text(name), x, top, w, style, tag(name))

    def section(number, title, top):
        commands.append(('badge', LEFT, top - 24, number))
        h = paragraph(title, LEFT + 36, top - 1, WIDTH - 36, 'section', escape=False)
        commands.append(('rule', LEFT + 36, top - h - 6, RIGHT_EDGE))
        return top - h - 11

    # --- header (hero) ---------------------------------------------------
    # Layers: gradient + glow + watermark + genre motif (drawn in render), then
    # kicker pill, title, subtitle, genre chips, glass metric cards and a thin
    # "fingerprint" strip of the analysed sections along the bottom edge.
    top = A3[1]
    hb = top - HEADER_H
    kicker = 'SUNO  楽曲分析シート'
    if (data.get('analyzed_at') or '').strip():
        kicker += '　｜　分析日 ' + data['analyzed_at']
    kw = pdfmetrics.stringWidth(kicker, 'GothicB', 10.5) + 22
    commands.append(('glass', LEFT, top - 40, kw, 21, 10.5))
    paragraph(kicker, LEFT + 11, top - 23, kw, 'kicker')
    title_h = paragraph(html.escape(text('title')) + ('<font size="15" color="' + theme['header_muted'] + '">' + html.escape(tag('title')) + '</font>' if tag('title') else ''),
                        LEFT, top - 52, 620, 'title', escape=False)
    if title_h > 90:
        raise ValueError('曲名がタイトル欄に収まりません。')
    cursor = top - 52 - title_h - 6
    genre = (data.get('genre') or '').strip()
    mood_in_header = genre_in_header = False
    if genre:
        sub_style = styles['subtitle']
        fits = lambda t: pdfmetrics.stringWidth(t, sub_style.fontName, sub_style.fontSize) <= 700
        with_mood = genre + tag('genre') + '　／　' + text('mood') + tag('mood')
        if (data.get('mood') or '').strip() and fits(with_mood):
            cursor -= paragraph(with_mood, LEFT, cursor, 720, 'subtitle')
            mood_in_header = genre_in_header = True
        elif fits(genre + tag('genre')):
            cursor -= paragraph(genre + tag('genre'), LEFT, cursor, 720, 'subtitle')
            genre_in_header = True
    card_h, card_bottom = 58, hb + 18
    components = data.get('genre_components') or []
    if components and cursor - 34 >= card_bottom + card_h + 8:
        cx = LEFT
        chip_top = cursor - 10
        for comp in components:
            label = comp['name'] + '［' + SOURCE[comp['source']] + '］'
            cw = pdfmetrics.stringWidth(label, 'GothicB', 10.5) + 22
            if cx + cw > LEFT + 640:
                break
            commands.append(('glass', cx, chip_top - 22, cw, 22, 11))
            paragraph(label, cx + 11, chip_top - 4, cw, 'chip_h')
            cx += cw + 8
    card_w = (WIDTH - 3 * 12) / 4
    for i, (label, name) in enumerate([('曲長', 'duration_seconds'), ('テンポ', 'tempo_bpm'), ('拍子', 'meter'), ('キー', 'key')]):
        x = LEFT + i * (card_w + 12)
        commands.append(('glass', x, card_bottom, card_w, card_h, 9))
        paragraph(label + tag(name), x + 14, card_bottom + card_h - 9, card_w - 22, 'metric_label')
        markup = html.escape(text(name)).replace('（推定）', '<font size="11">（推定）</font>')
        if paragraph(markup, x + 14, card_bottom + card_h - 24, card_w - 22, 'metric', escape=False) > 28:
            raise ValueError(label + 'が数値欄に収まりません。')
    y = hb - 18

    # --- summary & caveat -------------------------------------------------
    if (data.get('summary') or '').strip():
        h = labeled('総評', text('summary'), LEFT + 20, y - 9, WIDTH - 34, 'summary', tag('summary'))
        commands.insert(len(commands) - 1, ('summary_box', LEFT, y - h - 18, WIDTH, h + 18))
        y -= h + 18 + gap * 0.8
    if data.get('caveat'):
        h = paragraph('<font name="GothicB">要確認</font>' + html.escape(tag('caveat') + '：' + text('caveat')), LEFT + 14, y - 9, WIDTH - 28, 'alert', escape=False)
        commands.insert(len(commands) - 1, ('alert', LEFT, y - h - 18, WIDTH, h + 18))
        y -= h + 18 + gap

    # --- 01 production input ----------------------------------------------
    y = section('01', '制作時の指示', y)
    has_prompt = bool((data.get('style_prompt') or '').strip())
    has_tags = bool(data.get('lyrics_tags'))
    if not has_prompt and not has_tags:
        y -= paragraph('スタイル（原文）・歌詞欄タグ（構成とは別の指示）：いずれも未取得', LEFT, y, WIDTH, 'small')
    else:
        prompt_key = 'style_prompt_summary' if (data.get('style_prompt_summary') or '').strip() else 'style_prompt'
        prompt_label = 'スタイル（要約）' if prompt_key == 'style_prompt_summary' else 'スタイル（原文）'
        y -= labeled(prompt_label, text(prompt_key), LEFT, y, WIDTH, 'small', tag('style_prompt')) + 4
        y -= field('歌詞欄タグ（構成とは別の指示）', 'lyrics_tags', LEFT, y, WIDTH, 'small')
    y -= gap

    # --- 02 timeline -------------------------------------------------------
    section_type = data.get('sections_type', 'pattern')
    heading = '音響パターンの区間（推定）' if section_type == 'pattern' else '曲構成（推定）'
    y = section('02', html.escape(heading + tag('sections')), y)
    sections = data.get('sections') or []
    if sections:
        duration = data['duration_seconds']
        # One row when every label fits (or few sections); otherwise split into first/second half.
        # (a few too-short sections are listed under the chart instead of forcing two rows)
        label_fits = sum(WIDTH * (s['end'] - s['start']) / duration < pdfmetrics.stringWidth(s['label'], 'GothicB', 11.5) + 6
                         for s in sections) <= 3
        windows = [(0, duration)] if len(sections) <= 8 or label_fits else [(0, duration / 2), (duration / 2, duration)]
        small_intervals = []
        for window_start, window_end in windows:
            bar_y = y - 26
            commands.append(('timeline', LEFT, bar_y, WIDTH, 26, sections, duration, window_start, window_end))
            for item in sections:
                clipped_start, clipped_end = max(item['start'], window_start), min(item['end'], window_end)
                if clipped_end <= clipped_start:
                    continue
                span = WIDTH * (clipped_end - clipped_start) / (window_end - window_start)
                if span < pdfmetrics.stringWidth(item['label'], 'GothicB', 11.5) + 6 and item not in small_intervals:
                    small_intervals.append(item)
            commands.append(('ticks', LEFT, bar_y - 7, WIDTH, window_start, window_end))
            y = bar_y - 27
        if small_intervals:
            entries = [fmt_seconds(s['start']) + '–' + fmt_seconds(s['end']) + ' ' + s['label'] for s in small_intervals]
            y -= paragraph('図中に文字が入らない区間: ' + ' / '.join(entries), LEFT, y, WIDTH, 'small') + 4
        note = ('記号はモデルが付けた類似パターンの識別子で、Aメロやサビ等の名称ではありません（曲構成の名称・時刻は未確認）。同じ記号＝同じ色。目盛りは分:秒。'
                if section_type == 'pattern' else '区間名と時刻は表示された出典に基づく推定です。目盛りは分:秒。')
        y -= paragraph(note, LEFT, y, WIDTH, 'small')
    else:
        y -= paragraph('区間の開始・終了時刻は未取得', LEFT, y, WIDTH, 'small')
    y -= gap

    # --- 03 genre ----------------------------------------------------------
    y = section('03', 'ジャンルの要素とスタイルの照合<font name="Gothic" size="10.5" color="' + theme['muted'] + '">　ジャンル要素は同じ大きさで表示。比率は示しません。</font>', y)
    if not genre_in_header:
        y -= field('分析ジャンル', 'genre', LEFT, y, WIDTH) + 6
    target_markup = ('<font name="GothicB" color="' + theme['accent'] + '">目標ジャンル</font>' + html.escape(tag('target_genre'))
                     + '　' + html.escape(text('target_genre')) + '　｜　<font name="GothicB" color="' + theme['accent'] + '">全体照合</font>'
                     + html.escape(tag('genre_match')) + '　' + html.escape(text('genre_match')))
    y -= paragraph(target_markup, LEFT, y, WIDTH, 'small', escape=False) + 8
    components = data.get('genre_components') or []
    if components:
        # Two-column grid of element chips with their audible evidence.
        for row in range(0, len(components), 2):
            row_h = 0
            for col, comp in enumerate(components[row:row + 2]):
                x = LEFT + col * (COL + 26)
                name_w = min(150, pdfmetrics.stringWidth(comp['name'], 'GothicB', 12.5) + 4)
                h1 = paragraph(comp['name'], x + 10, y - 4, name_w, 'chip')
                commands.insert(len(commands) - 1, ('chip', x + 2, y - h1 - 8, name_w + 16, h1 + 8))
                role = '［' + SOURCE[comp['source']] + '］' + (comp['role'] or '根拠未取得')
                h2 = paragraph(role, x + name_w + 26, y - 4, COL - name_w - 26, 'small')
                row_h = max(row_h, h1 + 8, h2 + 4)
            y -= row_h + 6
        y -= 2
    else:
        y -= labeled('ジャンルの個別要素', '未取得', LEFT, y, WIDTH, 'small') + 6
    checks = data.get('genre_checks') or []
    if checks:
        widths = [100, 266, 306, 90]
        xs = [LEFT + sum(widths[:i]) for i in range(4)]
        head_h = 0
        for x, w, label in zip(xs, widths, ['観点', 'スタイル指示', '実際の音（出典付き）', '判定']):
            head_h = max(head_h, paragraph(label, x + 8, y - 4, w - 14, 'label'))
        commands.insert(len(commands) - 4, ('table_head', LEFT, y - head_h - 8, WIDTH, head_h + 8))
        y -= head_h + 8
        for n, item in enumerate(checks):
            start_idx = len(commands)
            cells = [item['aspect'], item['expected'], item['observed'] + ' ［' + SOURCE[item['source']] + '］']
            hs = [paragraph(v, x + 8, y - 6, w - 14, 'small') for v, x, w in zip(cells, xs, widths)]
            row_h = max(hs + [18]) + 12
            commands.insert(start_idx, ('table_row', LEFT, y - row_h, WIDTH, row_h, n % 2))
            commands.append(('verdict', xs[3] + 8, y - row_h / 2 - 9, widths[3] - 16, 18, item['verdict']))
            y -= row_h
        y -= 4
    else:
        y -= labeled('スタイル指示との項目別照合', '未取得', LEFT, y, WIDTH, 'small')
    y -= gap

    # --- 04 development & sound ---------------------------------------------
    y = section('04', '曲の展開と音の特徴' + ('<font name="Gothic" size="10.5" color="' + theme['muted'] + '">　下段は時間帯ごとの観察（時刻は推定・未確認を含む）</font>' if data.get('timeline_notes') else ''), y)
    left_y = right_y = y
    left_y -= field('展開', 'development', LEFT, left_y, COL) + 8
    left_y -= field('聴きどころ', 'highlights', LEFT, left_y, COL, 'small') + 8
    moments = data.get('timeline_notes') or []
    if not moments:
        left_y -= labeled('時間帯ごとの観察', '未取得', LEFT, left_y, COL, 'small')
    rows = [('歌声', 'vocals'), ('楽器', 'instruments'), ('リズム', 'rhythm')] + ([] if mood_in_header else [('雰囲気', 'mood')])
    for label, name in rows:
        right_y -= field(label, name, X_RIGHT, right_y, COL, 'small') + 8
    y = min(left_y, right_y) - 6
    if moments:
        # Flow strip: one card per period, left to right, joined by chevrons.
        y -= 4
        n, arrow = len(moments), 14
        box_w = (WIDTH - arrow * (n - 1)) / n
        heights = []
        start = len(commands)
        for i, item in enumerate(moments):
            bx = LEFT + i * (box_w + arrow)
            markup = ('<font name="GothicB" color="' + theme['accent'] + '">' + html.escape(item['period']) + '</font>'
                      + '<font size="9.5" color="' + theme['muted'] + '">［' + SOURCE[item['source']] + '］</font> '
                      + html.escape(item['observation']))
            heights.append(paragraph(markup, bx + 10, y - 8, box_w - 18, 'small', escape=False))
        box_h = max(heights) + 16
        for i in range(n):
            bx = LEFT + i * (box_w + arrow)
            commands.insert(start, ('flow', bx, y - box_h, box_w, box_h, i < n - 1, arrow))
        y -= box_h
    y -= gap

    # --- 05 mix & improvements -----------------------------------------------
    y = section('05', 'ミックスと改善の検討' + ('<font name="Gothic" size="10.5" color="' + theme['muted'] + '">　右は改善候補（変更・維持・理由）</font>' if data.get('recommendations') else ''), y)
    left_y = right_y = y
    left_y -= field('ミックスの観察', 'mix_observations', LEFT, left_y, COL) + 8
    suggestions = data.get('recommendations') or []
    if not suggestions:  # with cards, the memo text stays in the JSON (cards carry it)
        right_y -= field('改善メモ', 'improvements', X_RIGHT, right_y, COL) + 8
    if suggestions:
        for item in suggestions:
            parts = ['<font name="GothicB">変更</font>　' + html.escape(item['change'] or '未取得')]
            if item['keep']:
                parts.append('<font name="GothicB">維持</font>　' + html.escape(item['keep']))
            if item['reason']:
                parts.append('<font name="GothicB">理由</font>　' + html.escape(item['reason']))
            missing = [n for n, k in (('維持', 'keep'), ('理由', 'reason')) if not item[k]]
            markup = '　'.join(parts) + ' ［' + SOURCE[item['source']] + '］'
            if missing:
                markup += '　<font color="' + theme['muted'] + '">' + '・'.join(missing) + ' 未取得</font>'
            h = paragraph(markup, X_RIGHT + 12, right_y - 7, COL - 20, 'small', escape=False)
            commands.insert(len(commands) - 1, ('suggestion', X_RIGHT, right_y - h - 14, COL, h + 14))
            right_y -= h + 19
    else:
        right_y -= labeled('変更・維持の根拠', '未取得', X_RIGHT, right_y, COL, 'small')
    if (data.get('next_style_prompt') or '').strip():
        h = labeled('次の生成で試すスタイル案 ［案］ 未生成・未検証', data['next_style_prompt'], LEFT + 12, left_y - 9, COL - 24, 'small', stacked=True)
        commands.insert(len(commands) - 2, ('proposal', LEFT, left_y - h - 18, COL, h + 18))
        left_y -= h + 18
    y = min(left_y, right_y) - gap

    # --- footer ------------------------------------------------------------
    commands.append(('rule', LEFT, y + 6, RIGHT_EDGE))
    y -= 4
    y -= paragraph('出典　［聴］Suno聴取AI　［構］Suno構造解析　［曲］Suno曲情報　［指］ユーザー指定　［測］ローカル計測　［案］提案　［不］未確認'
                   '　｜　推定を含む。詳細は別保存JSON', LEFT, y, WIDTH, 'muted') + 2
    y -= paragraph('デザイン：' + theme['name'] + '（' + theme['_reason'] + '）— 配色・書体の演出で分析結果ではありません', LEFT, y, WIDTH, 'muted')
    return commands, y


def _luminance(hex_color):
    col = colors.HexColor(hex_color)
    return 0.2126 * col.red + 0.7152 * col.green + 0.0722 * col.blue


def render(data, dst, fmt_seconds, theme_override=None, font_path=None, font_index=0):
    register_fonts(font_path=font_path, font_index=font_index)
    width, height = A3
    theme_key, theme, reason, mods = choose_theme(data, theme_override or data.get('design_theme'))
    theme['_reason'] = reason
    gap, n_gaps = 8, 7
    # Auto-fit: shrink body text at most 10% (small text stays >= ~10pt) before giving up.
    for scale in (1.0, 0.97, 0.94, 0.91, 0.9):
        styles = _styles(theme, scale)
        commands, y = _layout(data, fmt_seconds, theme, styles, gap)
        if y >= BOTTOM:
            break
    else:
        raise ValueError('全項目が1ページに収まりません。原文を保持し、表示用の要約を作ってから再実行してください。')
    spare = y - BOTTOM
    if spare > 20:  # spread leftover space between sections instead of leaving a blank tail
        extra = min(spare / n_gaps, 36)
        while extra >= 1:
            trial, y2 = _layout(data, fmt_seconds, theme, styles, gap + extra)
            if y2 >= BOTTOM:
                commands = trial
                break
            extra *= 0.8

    accent = colors.HexColor(theme['accent'])
    dst.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(dst), pagesize=(width, height))
    c.setTitle(str(data.get('title') or '楽曲分析シート'))
    c.setFillColor(colors.HexColor(theme['page'])); c.rect(0, 0, width, height, stroke=0, fill=1)
    draw_header(c, theme, mods, 0, height - HEADER_H, width, HEADER_H)
    sections = data.get('sections') or []
    c.setFillColor(accent); c.rect(0, height - HEADER_H - 4, width, 4, stroke=0, fill=1)
    if sections:  # fingerprint: the analysed section pattern, to scale, along the header edge
        labels = list(dict.fromkeys(s['label'] for s in sections))
        duration = data['duration_seconds']
        for s in sections:
            c.setFillColor(colors.HexColor(theme['timeline'][labels.index(s['label'])]))
            c.rect(width * s['start'] / duration, height - HEADER_H - 4, width * (s['end'] - s['start']) / duration, 7, stroke=0, fill=1)
    light = _luminance(theme['header']) > 0.6
    for op in commands:
        kind = op[0]
        if kind == 'paragraph':
            op[1].drawOn(c, op[2], op[3])
        elif kind == 'rule':
            _, x1, yy, x2 = op
            c.setStrokeColor(colors.HexColor(theme['line'])); c.setLineWidth(0.8); c.line(x1, yy, x2, yy)
        elif kind == 'badge':
            _, x, yy, number = op
            c.setFillColor(accent); c.roundRect(x, yy, 28, 24, 6, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont('GothicB', 12); c.drawCentredString(x + 14, yy + 7, number)
        elif kind == 'glass':
            _, x, yy, w, h, r = op
            c.saveState()
            c.setFillColor(colors.white); c.setFillAlpha(0.55 if light else 0.11)
            c.setStrokeColor(colors.HexColor(theme['accent']) if light else colors.white); c.setStrokeAlpha(0.35 if light else 0.28)
            c.setLineWidth(0.8); c.roundRect(x, yy, w, h, r, fill=1, stroke=1)
            c.restoreState()
        elif kind == 'table_head':
            _, x, yy, w, h = op
            c.setFillColor(colors.HexColor(theme['accent_soft'])); c.roundRect(x, yy, w, h, 4, fill=1, stroke=0)
        elif kind == 'table_row':
            _, x, yy, w, h, odd = op
            if odd:
                c.setFillColor(colors.HexColor(theme['card'])); c.rect(x, yy, w, h, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor(theme['line'])); c.setLineWidth(0.6); c.line(x, yy, x + w, yy)
        elif kind == 'verdict':
            _, x, yy, w, h, label = op
            tone = {'一致': '#2f8a5b', '一部一致': '#b7862b', '不一致': '#b8432f'}.get(label, '#7a7f87')
            c.setFillColor(colors.HexColor(tone)); c.roundRect(x, yy, w, h, h / 2, fill=1, stroke=0)
            c.setFillColor(colors.white); size = 10
            while c.stringWidth(label, 'GothicB', size) > w - 8 and size > 7:
                size -= 0.5
            c.setFont('GothicB', size); c.drawCentredString(x + w / 2, yy + h / 2 - size * 0.36, label)
        elif kind == 'card':
            _, x, yy, w, h = op
            c.setFillColor(colors.HexColor(theme['card'])); c.roundRect(x, yy, w, h, 8, fill=1, stroke=0)
            c.setFillColor(accent); c.rect(x, yy + 10, 3, h - 20, fill=1, stroke=0)
        elif kind == 'summary_box':
            _, x, yy, w, h = op
            c.setFillColor(colors.HexColor(theme['accent_soft'])); c.roundRect(x, yy, w, h, 8, fill=1, stroke=0)
            c.setFillColor(accent); c.roundRect(x, yy, 6, h, 3, fill=1, stroke=0)
        elif kind == 'chip':
            _, x, yy, w, h = op
            c.setFillColor(colors.HexColor(theme['accent_soft'])); c.roundRect(x, yy, w, h, h / 2, fill=1, stroke=0)
        elif kind == 'spine':
            _, x, y1, y2 = op
            c.setStrokeColor(accent); c.setStrokeAlpha(0.5); c.setLineWidth(1.5); c.line(x, y1, x, y2); c.setStrokeAlpha(1)
        elif kind == 'dot':
            _, x, yy = op
            c.setFillColor(accent); c.circle(x, yy, 4, fill=1, stroke=0)
        elif kind in ('suggestion', 'proposal'):
            _, x, yy, w, h = op
            c.setFillColor(colors.HexColor(theme['card'])); c.setStrokeColor(accent)
            if kind == 'proposal':
                c.setDash(4, 3); c.setLineWidth(1); c.roundRect(x, yy, w, h, 8, fill=1, stroke=1); c.setDash()
            else:
                c.roundRect(x, yy, w, h, 6, fill=1, stroke=0)
                c.setFillColor(accent); c.rect(x, yy + 6, 3, h - 12, fill=1, stroke=0)
        elif kind == 'flow':
            _, x, yy, w, h, more, arrow = op
            c.setFillColor(colors.HexColor(theme['card'])); c.roundRect(x, yy, w, h, 7, fill=1, stroke=0)
            c.setFillColor(accent); c.rect(x, yy + h - 3, w, 3, fill=1, stroke=0)
            if more:
                ax, ay = x + w + 3, yy + h / 2
                p = c.beginPath(); p.moveTo(ax, ay + 6); p.lineTo(ax + arrow - 6, ay); p.lineTo(ax, ay - 6); p.close()
                c.drawPath(p, stroke=0, fill=1)
        elif kind == 'alert':
            _, x, yy, w, h = op
            c.setFillColor(colors.HexColor('#fff1e8')); c.setStrokeColor(colors.HexColor('#e0a07a')); c.setLineWidth(1)
            c.roundRect(x, yy, w, h, 6, fill=1, stroke=1)
        elif kind == 'timeline':
            _, x, yy, w, h, secs, duration, window_start, window_end = op
            labels = list(dict.fromkeys(s['label'] for s in secs))
            c.setFillColor(colors.HexColor(theme['card'])); c.roundRect(x, yy, w, h, 4, fill=1, stroke=0)
            for s in secs:
                start, end = max(s['start'], window_start), min(s['end'], window_end)
                if end <= start:
                    continue
                sx = x + w * (start - window_start) / (window_end - window_start)
                sw = w * (end - start) / (window_end - window_start)
                c.setFillColor(colors.HexColor(theme['timeline'][labels.index(s['label'])])); c.rect(sx, yy, sw, h, fill=1, stroke=0)
                c.setStrokeColor(colors.HexColor(theme['page'])); c.setLineWidth(1.2); c.line(sx, yy, sx, yy + h)
                if sw >= c.stringWidth(s['label'], 'GothicB', 11.5) + 6:
                    c.setFillColor(colors.white); c.setFont('GothicB', 11.5); c.drawCentredString(sx + sw / 2, yy + h / 2 - 4, s['label'])
        elif kind == 'ticks':
            _, x, yy, w, window_start, window_end = op
            c.setFont('Gothic', 10); c.setFillColor(colors.HexColor(theme['muted'])); c.setStrokeColor(colors.HexColor(theme['muted']))
            length = window_end - window_start
            interval = next((i for i in (5, 10, 15, 30, 60, 120, 300) if length / i <= 9), 600)
            ticks = [window_start]
            t = (int(window_start / interval) + 1) * interval
            while t < window_end:
                if w * (window_end - t) / length >= 70 and w * (t - window_start) / length >= 45:
                    ticks.append(t)
                t += interval
            ticks.append(window_end)
            for t in ticks:
                tx = x + w * (t - window_start) / length
                c.setLineWidth(0.6); c.line(tx, yy + 3, tx, yy + 7)
                label = fmt_seconds(t)
                if t == window_start:
                    c.drawString(tx, yy - 8, label)
                elif t == window_end:
                    c.drawRightString(tx, yy - 8, label)
                else:
                    c.drawCentredString(tx, yy - 8, label)
    c.showPage(); c.save()
    print(json.dumps({'pdf': str(dst), 'pages': 1, 'section_count': len(sections), 'design_theme': theme_key,
                      'design_reason': reason}, ensure_ascii=False))

"""Song-dependent design themes for the one-page Suno analysis sheet.

The theme only changes the visual atmosphere (colours, fonts, header motif).
It is chosen from words already present in the analysis JSON and never adds
or alters analysis content. The chosen theme and its reason are printed on
the page so a reader can tell design from evidence.
"""
import hashlib
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _font_candidates():
    """Yield system Japanese TrueType fonts; no system font is redistributed."""
    if sys.platform == 'win32':
        root = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        yield root / 'BIZ-UDGothicR.ttc', 1
        yield root / 'meiryo.ttc', 0
        yield root / 'YuGothR.ttc', 0
    elif sys.platform == 'darwin':
        for path in ('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                     '/System/Library/Fonts/Hiragino Sans GB.ttc',
                     '/Library/Fonts/Arial Unicode.ttf'):
            yield Path(path), 0
    else:
        for path in ('/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf',
                     '/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf',
                     '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
                     '/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf',
                     '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
            yield Path(path), 0
    fc_match = shutil.which('fc-match')
    if fc_match:
        for family in ('BIZ UDPGothic:lang=ja', 'Noto Sans CJK JP:lang=ja', 'sans:lang=ja'):
            try:
                result = subprocess.run([fc_match, '-f', '%{file}\n', family], capture_output=True,
                                        text=True, timeout=5, check=False)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if result.returncode == 0 and result.stdout.strip():
                yield Path(result.stdout.splitlines()[0]), 0


def _load_cjk_font(name, path, index):
    font = TTFont(name, str(path), subfontIndex=index)
    # A fontconfig fallback may be Latin-only. Verify common CJK glyphs before use.
    if not all(ord(ch) in font.face.charWidths for ch in '楽曲分析歌詞音源展開改善'):
        raise ValueError('font lacks required Japanese glyphs')
    return font


def register_fonts(font_path=None, font_index=0):
    """Register a compatible Japanese font, with explicit override if requested.

    The caller supplies and licenses any optional font. ReportLab accepts
    TrueType outlines; CFF/PostScript fonts are not supported by its TTFont.
    """
    if font_index < 0:
        raise ValueError('--font-index must be non-negative')
    if font_path is not None:
        path = Path(font_path).expanduser()
        if not path.is_file():
            raise ValueError('Font file not found: ' + str(path))
        try:
            fonts = {name: _load_cjk_font(name, path, font_index)
                     for name in ('Gothic', 'GothicB', 'MinchoB')}
        except Exception as exc:
            raise ValueError('Selected font is unsupported or lacks Japanese glyphs. '
                             'Use a Japanese TrueType .ttf/.ttc and check --font-index.') from exc
        for font in fonts.values():
            pdfmetrics.registerFont(font)
        return
    for path, index in _font_candidates():
        if not path.is_file():
            continue
        try:
            regular = _load_cjk_font('Gothic', path, index)
        except Exception:
            continue
        bold_path, serif_path = path, path
        bold_index, serif_index = index, index
        if sys.platform == 'win32' and path.name == 'BIZ-UDGothicR.ttc':
            bold_path = path.with_name('BIZ-UDGothicB.ttc')
            serif_path = path.with_name('BIZ-UDMinchoM.ttc')
        try:
            bold = _load_cjk_font('GothicB', bold_path, bold_index)
        except Exception:
            bold = _load_cjk_font('GothicB', path, index)
        try:
            serif = _load_cjk_font('MinchoB', serif_path, serif_index)
        except Exception:
            serif = _load_cjk_font('MinchoB', path, index)
        for font in (regular, bold, serif):
            pdfmetrics.registerFont(font)
        return
    raise ValueError('No compatible Japanese TrueType font found. Install a Japanese '
                     '.ttf/.ttc font and pass --font PATH (and --font-index for TTC). '
                     'CFF/PostScript fonts are unsupported by ReportLab TTFont.')


# Each theme: page/ink colours, header band, accent, 8 timeline colours,
# heading font and motif. Timeline colours keep white labels readable.
THEMES = {
    'neutral': dict(name='スタンダード', word='ANALYSIS', motif='blocks', heading='GothicB',
                    page='#f7f7f4', card='#eef3f4', ink='#22343f', muted='#56707e', line='#c9d6da',
                    header='#14324a', header2='#1f5a6e', header_ink='#ffffff', header_muted='#cfe4ea',
                    accent='#23807f', accent_soft='#e2efed',
                    timeline=['#236f89', '#3f9893', '#6d82a8', '#a0668f', '#b87444', '#638c5b', '#69649a', '#a35f5f']),
    'ballad': dict(name='バラード／アコースティック', word='BALLAD', motif='waves', heading='MinchoB',
                   page='#fbf7f2', card='#f4ece3', ink='#3b2f2c', muted='#7c6a61', line='#e2d3c6',
                   header='#6e4a4f', header2='#b07a6b', header_ink='#fffaf5', header_muted='#f3dccf',
                   accent='#a5605a', accent_soft='#f3e3dc',
                   timeline=['#a5605a', '#c18a5a', '#8b7b9e', '#6f8f86', '#b9767f', '#8a6d52', '#5f7894', '#9c8a4f']),
    'edm': dict(name='エレクトロ／ダンス', word='ELECTRONIC', motif='equalizer', heading='GothicB',
                page='#f5f5fb', card='#ebebf7', ink='#1d1f3a', muted='#5a5d82', line='#d2d3ea',
                header='#120f2e', header2='#2b1660', header_ink='#ffffff', header_muted='#c3c0f0',
                accent='#6a3fd6', accent_soft='#e9e2fb', neon=['#21d4fd', '#b721ff', '#ff3cac', '#3cf0c5'],
                timeline=['#5b3fd0', '#1f9bd1', '#c2339a', '#17a589', '#7d5ce0', '#d04f7a', '#2f6fd6', '#8a3fb8']),
    'rock': dict(name='ロック／バンド', word='ROCK', motif='slashes', heading='GothicB',
                 page='#f6f5f3', card='#ecebe8', ink='#1f1f1f', muted='#5e5b57', line='#d3d0cb',
                 header='#1b1b1d', header2='#3a3a3e', header_ink='#ffffff', header_muted='#d6d3cf',
                 accent='#c2261f', accent_soft='#f6e1df',
                 timeline=['#b8241d', '#3e3e44', '#d0612a', '#6b6b73', '#8c1c2c', '#a88a3a', '#55606e', '#7a3b2e']),
    'lofi': dict(name='ローファイ／ジャズ／チル', word='LO-FI', motif='vinyl', heading='MinchoB',
                 page='#f6f3ec', card='#ece6d9', ink='#33332b', muted='#6f6c5d', line='#dad3c1',
                 header='#3f4a3c', header2='#6d6a4f', header_ink='#fbf8ef', header_muted='#e1dcc8',
                 accent='#8a6a3f', accent_soft='#ece2cf',
                 timeline=['#7a8a5c', '#a07a4c', '#5f7a7a', '#9a6a5a', '#6a6a8a', '#8a8a4c', '#4f6a5a', '#a08a6a']),
    'pop': dict(name='ポップ／明るい', word='POP', motif='bubbles', heading='GothicB',
                page='#fff9fb', card='#fdeef4', ink='#3a2a3a', muted='#7d6478', line='#f1d9e4',
                header='#ffd6e5', header2='#cfe6ff', header_ink='#4a2440', header_muted='#7d4f70',
                accent='#e0548c', accent_soft='#fde3ee',
                timeline=['#e0548c', '#4aa3df', '#f09a3e', '#8e6bd8', '#3bb39a', '#e06b6b', '#5f7ee6', '#c9a227']),
    'cinematic': dict(name='シネマティック／オーケストラ', word='CINEMATIC', motif='arcs', heading='MinchoB',
                      page='#f6f5f1', card='#ecebe4', ink='#1f2433', muted='#5d6377', line='#d6d4c8',
                      header='#0f1630', header2='#2a2f52', header_ink='#fbf6e6', header_muted='#d8cfae',
                      accent='#a8842f', accent_soft='#efe7cf',
                      timeline=['#2f3f75', '#a8842f', '#5a6f9c', '#7d4f6e', '#3f7468', '#8f6a3a', '#4b4f80', '#6f7f9a']),
    'urban': dict(name='ヒップホップ／R&B', word='HIP-HOP', motif='halftone', heading='GothicB',
                  page='#f5f4f1', card='#eae8e2', ink='#1e1d1b', muted='#5f5c55', line='#d3cfc6',
                  header='#17161a', header2='#2c2a24', header_ink='#ffffff', header_muted='#e6d9a8',
                  accent='#d19a12', accent_soft='#f5ead0',
                  timeline=['#b5850f', '#3a3a40', '#8a4fd0', '#c4572b', '#2f7f8f', '#6a6a72', '#a03a5a', '#4f7a3a']),
}

# Keyword lists are matched case-insensitively as substrings.
GENRE_WORDS = {
    'edm': ['edm', 'electro', 'エレクトロ', 'ダンス', 'dance', 'house', 'ハウス', 'trance', 'トランス', 'techno', 'テクノ',
            'dubstep', 'ダブステップ', 'future bass', 'フューチャーベース', 'synthwave', 'シンセウェイブ', 'drum and bass',
            'ドラムンベース', 'hyperpop', 'ハイパーポップ', 'シンセポップ', 'synthpop', 'club', 'クラブ'],
    'rock': ['rock', 'ロック', 'metal', 'メタル', 'punk', 'パンク', 'grunge', 'グランジ', 'オルタナ', 'alternative',
             'hardcore', 'ハードコア', 'emo', 'ディストーション', 'distortion', 'shoegaze', 'シューゲイザー'],
    'ballad': ['ballad', 'バラード', 'acoustic', 'アコースティック', 'folk', 'フォーク', 'singer-songwriter', '弾き語り'],
    'lofi': ['lo-fi', 'lofi', 'ローファイ', 'jazz', 'ジャズ', 'chill', 'チル', 'bossa', 'ボサノバ', 'soul', 'ソウル',
             'city pop', 'シティポップ', 'cafe', 'カフェ', 'funk', 'ファンク'],
    'pop': ['pop', 'ポップ', 'アイドル', 'idol', 'kawaii', 'カワイイ', 'アニソン', 'anime', 'bubblegum'],
    'cinematic': ['orchestral', 'オーケストラ', 'cinematic', 'シネマ', '映画', 'classical', 'クラシック', 'ambient',
                  'アンビエント', 'epic', '壮大', 'soundtrack', 'サウンドトラック', '劇伴', 'post-rock', 'ポストロック', 'new age'],
    'urban': ['hip hop', 'hip-hop', 'hiphop', 'ヒップホップ', 'rap', 'ラップ', 'trap', 'トラップ', 'r&b', 'drill', 'ドリル',
              'boom bap', 'ブーンバップ', 'phonk', 'フォンク'],
}
MOOD_WORDS = {
    'ballad': ['温か', '優し', '切な', 'しっとり', '親密', '哀愁', '感傷'],
    'pop': ['明る', '元気', 'かわい', '可愛', 'キュート', '楽し', 'ハッピー', '爽やか'],
    'cinematic': ['壮大', '荘厳', '神秘', '幻想', '浮遊', '雄大', '叙事'],
    'urban': ['クール', '都会', 'ストリート', 'スモーキー'],
    'rock': ['激し', '攻撃', '荒々し', '衝動', '轟音'],
    'lofi': ['ノスタルジ', 'まったり', 'リラックス', 'くつろ', '気だる', 'レトロ'],
    'edm': ['ネオン', 'きらびや', '高揚感のあるドロップ', '疾走', 'ユーフォリ'],
}
DARK_WORDS = ['切な', '暗', 'ダーク', 'メランコ', '哀', '悲', '陰', '寂']
ENERGY_WORDS = ['激し', '高揚', 'パワフル', 'エネルギッシュ', '疾走', '力強', '爆発']
CALM_WORDS = ['穏やか', '静か', 'しっとり', '落ち着', 'まったり', '控えめ', '囁']

# (field, weight) — what the model heard outweighs side information.
FIELD_WEIGHTS = [('genre', 3.0), ('target_genre', 2.0), ('style_prompt', 2.0), ('mood', 1.5),
                 ('instruments', 1.0), ('rhythm', 0.5), ('vocals', 0.5)]
TIE_ORDER = ['edm', 'rock', 'urban', 'cinematic', 'lofi', 'ballad', 'pop']
FIELD_LABELS = {'genre': 'ジャンル', 'genre_components': 'ジャンル要素', 'target_genre': '目標ジャンル',
                'style_prompt': 'スタイル指示', 'mood': '雰囲気', 'instruments': '楽器', 'rhythm': 'リズム',
                'vocals': '歌声', 'key': 'キー'}


def _texts(data):
    pieces = [(field, weight, data.get(field)) for field, weight in FIELD_WEIGHTS]
    for comp in data.get('genre_components') or []:
        pieces.append(('genre_components', 3.0, comp.get('name')))
    return [(f, w, str(t).lower()) for f, w, t in pieces if isinstance(t, str) and t.strip()]


def choose_theme(data, override=None):
    """Return (theme_key, theme_dict, reason_text, modifiers)."""
    texts = _texts(data)
    joined_mood = ' '.join(t for f, _, t in texts if f in ('mood', 'genre', 'vocals', 'rhythm', 'development'))
    joined_mood += ' ' + str(data.get('development') or '')
    key = str(data.get('key') or '').lower()
    minor = 'minor' in key or '短調' in key
    dark_words = any(w in joined_mood for w in DARK_WORDS)
    modifiers = {
        'dark': minor or dark_words,
        'energy': 1.35 if any(w in joined_mood for w in ENERGY_WORDS) else (0.7 if any(w in joined_mood for w in CALM_WORDS) else 1.0),
        'tempo': data.get('tempo_bpm') if isinstance(data.get('tempo_bpm'), (int, float)) else None,
        'seed': int(hashlib.sha1(str(data.get('title') or '').encode('utf-8')).hexdigest()[:8], 16),
    }
    if override:
        theme = dict(THEMES[override])
        return override, _apply_modifiers(theme, modifiers), '入力で指定', modifiers

    scores, hits = {k: 0.0 for k in GENRE_WORDS}, {k: [] for k in GENRE_WORDS}
    for field, weight, text in texts:
        for theme_key, words in GENRE_WORDS.items():
            if any(w in text for w in words):
                scores[theme_key] += weight
                hits[theme_key].append(field)
        if field == 'mood':
            for theme_key, words in MOOD_WORDS.items():
                if any(w in text for w in words):
                    scores[theme_key] += weight
                    hits[theme_key].append(field)
    best = max(scores.values())
    if best <= 0:
        return 'neutral', _apply_modifiers(dict(THEMES['neutral']), modifiers), 'ジャンル・雰囲気の語が見つからないため標準', modifiers
    winner = next(k for k in TIE_ORDER if scores[k] == best)
    fields = list(dict.fromkeys(hits[winner]))
    reason = '・'.join(FIELD_LABELS.get(f, f) for f in fields) + 'の語で自動選択'
    if modifiers['dark']:
        reason += '、' + ('短調' if minor else '') + ('・' if minor and dark_words else '') + ('切なさ等の語' if dark_words else '') + 'で配色を深め'
    return winner, _apply_modifiers(dict(THEMES[winner]), modifiers), reason, modifiers


def _mix(hex_a, hex_b, t):
    a, b = colors.HexColor(hex_a), colors.HexColor(hex_b)
    r, g, bl = (a.red + (b.red - a.red) * t, a.green + (b.green - a.green) * t, a.blue + (b.blue - a.blue) * t)
    return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(bl * 255))


def _apply_modifiers(theme, mods):
    if mods['dark'] and theme['motif'] != 'bubbles':
        theme['header'] = _mix(theme['header'], '#000000', 0.22)
        theme['header2'] = _mix(theme['header2'], '#000000', 0.25)
    elif mods['dark']:
        theme['header'] = _mix(theme['header'], '#9a8cc8', 0.25)
        theme['header2'] = _mix(theme['header2'], '#8fa3c8', 0.25)
    return theme


class _Rand:
    """Small deterministic generator so the same song always gets the same motif."""

    def __init__(self, seed):
        self.state = (seed or 1) & 0x7fffffff

    def __call__(self):
        self.state = (1103515245 * self.state + 12345) & 0x7fffffff
        return self.state / 0x7fffffff


def draw_header(c, theme, mods, x, y, w, h):
    """Background band with a gradient and a genre-specific motif."""
    c.saveState()
    path = c.beginPath(); path.rect(x, y, w, h)
    c.clipPath(path, stroke=0, fill=0)
    steps = 48
    for i in range(steps):
        c.setFillColor(colors.HexColor(_mix(theme['header'], theme['header2'], i / (steps - 1))))
        c.rect(x + w * i / steps, y, w / steps + 1, h, stroke=0, fill=1)
    header_col = colors.HexColor(theme['header'])
    light = 0.2126 * header_col.red + 0.7152 * header_col.green + 0.0722 * header_col.blue > 0.6
    # Soft glow behind the right half gives depth before the motif is drawn.
    c.setFillColor(colors.HexColor(theme['accent']))
    for i in range(14):
        c.setFillAlpha(0.035)
        c.circle(x + w * 0.80, y + h * 0.62, 40 + i * 17, stroke=0, fill=1)
    # Large faint genre word as a typographic watermark.
    c.setFillColor(colors.HexColor(theme['accent']) if light else colors.white)
    c.setFillAlpha(0.10 if light else 0.06)
    size = 118
    while c.stringWidth(theme['word'], 'GothicB', size) > w * 0.52 and size > 48:
        size -= 2
    c.setFont('GothicB', size)
    c.drawRightString(x + w - 18, y + h * 0.40, theme['word'])
    c.setFillAlpha(1)
    rnd = _Rand(mods['seed'])
    energy = mods['energy']
    tempo = mods['tempo'] or 100
    motif = theme['motif']
    if motif == 'waves':
        cycles = max(1.5, min(5.0, tempo / 30))
        for k in range(5):
            amp = (10 + k * 4) * energy
            base = y + h * (0.58 + 0.07 * k)
            c.setStrokeColor(colors.white); c.setStrokeAlpha(0.10 + 0.05 * k); c.setLineWidth(1.2 + 0.4 * k)
            p = c.beginPath(); p.moveTo(x + w * 0.55, base)
            for i in range(1, 121):
                t = i / 120
                p.lineTo(x + w * 0.55 + w * 0.45 * t, base + amp * math.sin(2 * math.pi * cycles * t + k * 0.8))
            c.drawPath(p, stroke=1, fill=0)
    elif motif == 'equalizer':
        neon = theme['neon']
        c.setStrokeColor(colors.white); c.setStrokeAlpha(0.06); c.setLineWidth(0.5)
        for gx in range(0, int(w), 24):
            c.line(x + gx, y, x + gx, y + h)
        for gy in range(0, int(h), 24):
            c.line(x, y + gy, x + w, y + gy)
        bars = int(min(64, max(28, tempo / 2.5)))
        bw = (w * 0.36) / bars
        for i in range(bars):
            t = i / (bars - 1)
            env = 0.35 + 0.65 * abs(math.sin(math.pi * t * 1.5 + 0.3))
            # Bars stand on a baseline above the metric cards so values stay readable.
            bh = (h - 100) * 0.95 * env * (0.45 + 0.55 * rnd()) * min(1.0, energy)
            col = neon[i * len(neon) // bars]
            c.setFillColor(colors.HexColor(col)); c.setFillAlpha(0.32)
            c.rect(x + w * 0.63 + i * bw, y + 96, bw * 0.62, bh, stroke=0, fill=1)
            c.setFillAlpha(0.12)  # faint reflection under the baseline
            c.rect(x + w * 0.63 + i * bw, y + 96 - bh * 0.18, bw * 0.62, bh * 0.18, stroke=0, fill=1)
    elif motif == 'slashes':
        c.setFillColor(colors.HexColor(theme['accent']))
        for i in range(7):
            c.setFillAlpha(0.20 + 0.08 * (i % 3))
            sx = x + w * 0.58 + i * 34 * energy
            p = c.beginPath(); p.moveTo(sx, y); p.lineTo(sx + 16, y); p.lineTo(sx + 16 + h * 0.55, y + h); p.lineTo(sx + h * 0.55, y + h); p.close()
            c.drawPath(p, stroke=0, fill=1)
        c.setStrokeColor(colors.white); c.setStrokeAlpha(0.35); c.setLineWidth(1.4)
        p = c.beginPath(); p.moveTo(x + w * 0.55, y + h * 0.66)
        for i in range(1, 26):
            p.lineTo(x + w * 0.55 + i * w * 0.018, y + h * 0.66 + (rnd() - 0.5) * 26 * energy)
        c.drawPath(p, stroke=1, fill=0)
    elif motif == 'vinyl':
        cx, cy = x + w * 0.86, y + h * 0.45
        c.setStrokeColor(colors.white); c.setLineWidth(0.6)
        for r in range(14, 110, 6):
            c.setStrokeAlpha(0.07 + (0.06 if r % 18 == 2 else 0)); c.circle(cx, cy, r, stroke=1, fill=0)
        c.setFillColor(colors.HexColor(theme['accent'])); c.setFillAlpha(0.55); c.circle(cx, cy, 13, stroke=0, fill=1)
        c.setFillColor(colors.white)
        for _ in range(420):
            c.setFillAlpha(0.05 + 0.08 * rnd()); c.circle(x + w * rnd(), y + h * rnd(), 0.5 + rnd() * 0.9, stroke=0, fill=1)
    elif motif == 'bubbles':
        palette = [theme['accent'], '#7fc4f0', '#ffd27a', '#b9a2f0']
        for i in range(int(16 * energy) + 6):
            r = 6 + rnd() * 26
            c.setFillColor(colors.HexColor(palette[i % len(palette)])); c.setFillAlpha(0.18 + 0.2 * rnd())
            c.circle(x + w * (0.45 + 0.55 * rnd()), y + h * rnd(), r, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFillAlpha(0.9)
        for _ in range(7):
            sx, sy, s = x + w * (0.5 + 0.48 * rnd()), y + h * (0.15 + 0.7 * rnd()), 3 + rnd() * 4
            p = c.beginPath(); p.moveTo(sx, sy + s); p.lineTo(sx + s * 0.25, sy + s * 0.25); p.lineTo(sx + s, sy)
            p.lineTo(sx + s * 0.25, sy - s * 0.25); p.lineTo(sx, sy - s); p.lineTo(sx - s * 0.25, sy - s * 0.25)
            p.lineTo(sx - s, sy); p.lineTo(sx - s * 0.25, sy + s * 0.25); p.close(); c.drawPath(p, stroke=0, fill=1)
    elif motif == 'arcs':
        cx, cy = x + w * 1.02, y - h * 0.2
        c.setStrokeColor(colors.HexColor(theme['accent'])); c.setLineWidth(0.7)
        for i in range(12):
            c.setStrokeAlpha(0.18 + 0.03 * (i % 4)); c.circle(cx, cy, 60 + i * 22 * energy, stroke=1, fill=0)
        c.setStrokeColor(colors.white); c.setStrokeAlpha(0.10); c.setLineWidth(0.5)
        for i in range(5):
            yy = y + h * 0.18 + i * 6
            c.line(x + w * 0.40, yy, x + w * 0.80, yy)
    elif motif == 'halftone':
        c.setFillColor(colors.HexColor(theme['accent']))
        step = 11
        for gx in range(int(w * 0.45), int(w), step):
            for gy in range(0, int(h) + step, step):
                t = (gx - w * 0.45) / (w * 0.55)
                r = 0.4 + 3.6 * t * (0.5 + 0.5 * math.sin(gy / h * math.pi)) * min(1.2, energy)
                c.setFillAlpha(0.55); c.circle(x + gx, y + gy, r, stroke=0, fill=1)
    else:  # blocks: a quiet nod to the section timeline
        for i in range(18):
            c.setFillColor(colors.white); c.setFillAlpha(0.05 + 0.07 * rnd())
            c.rect(x + w * 0.5 + i * 22, y + 18, 18, 14 + rnd() * h * 0.5, stroke=0, fill=1)
    c.restoreState()

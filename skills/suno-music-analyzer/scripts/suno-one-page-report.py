#!/usr/bin/env python3
"""Render a normalized, evidence-labelled Suno analysis as one A3 portrait page with a song-dependent design theme."""
import argparse
import json
import math
import re
from decimal import Decimal
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suno_report_themes import THEMES  # noqa: E402

FIELDS = ('title', 'style_prompt', 'style_prompt_summary', 'lyrics_tags', 'duration_seconds', 'analyzed_at', 'tempo_bpm', 'meter', 'key', 'genre', 'genre_components', 'genre_checks', 'target_genre', 'genre_match', 'mood', 'vocals', 'instruments', 'rhythm', 'development', 'highlights', 'timeline_notes', 'mix_observations', 'improvements', 'recommendations', 'caveat', 'sections', 'sections_type', 'summary', 'next_style_prompt', 'design_theme')
SOURCE_CODES = {'audio-listen': '聴', 'audio-analysis': '構', 'audio-listen+audio-analysis': '聴/構', 'audio-retrieve': '曲', 'user': '指', 'local': '測', 'agent': '案', 'unknown': '不'}


def error(message):
    raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(data):
    if not isinstance(data, dict):
        error('入力JSONはオブジェクトにしてください。')
    extra = set(data) - set(FIELDS) - {'sources', 'source'}
    if extra:
        error('未対応の項目: ' + ', '.join(sorted(extra)))
    sources = data.get('sources', {})
    if not isinstance(sources, dict):
        error('sourcesは項目名と出典の対応を示すオブジェクトにしてください。')
    if set(sources) - set(FIELDS):
        error('sourcesに未対応の項目があります。')
    for key, value in sources.items():
        if not isinstance(value, str) or value not in SOURCE_CODES:
            error(f'{key}の出典が不正です。')
    for field in ('title', 'style_prompt', 'style_prompt_summary', 'analyzed_at', 'meter', 'key', 'genre', 'target_genre', 'genre_match', 'mood', 'vocals', 'instruments', 'rhythm', 'development', 'highlights', 'mix_observations', 'improvements', 'caveat', 'source', 'summary', 'next_style_prompt', 'design_theme'):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            error(f'{field}は文字列またはnullにしてください。')
    if (data.get('style_prompt_summary') or '').strip() and not (data.get('style_prompt') or '').strip():
        error('style_prompt_summaryを使うにはstyle_prompt原文を保持してください。')
    if data.get('design_theme') is not None and data['design_theme'] not in THEMES:
        error('design_themeは ' + ' / '.join(THEMES) + ' のいずれかにしてください。')
    if sources.get('summary') == 'agent':
        error('summaryは分析結果の要約です。出典にagentは使えません。')
    lyrics_tags = data.get('lyrics_tags')
    if lyrics_tags is not None:
        if not isinstance(lyrics_tags, list) or any(not isinstance(tag, str) or not re.fullmatch(r'\[[^\[\]\r\n]{1,80}\]', tag) for tag in lyrics_tags):
            error('lyrics_tagsには歌詞本文ではなく角括弧付きタグだけを配列で指定してください。')
    components = data.get('genre_components')
    if components is not None:
        if not isinstance(components, list) or len(components) > 6:
            error('genre_componentsは最大6要素の配列にしてください。')
        for comp in components:
            if not isinstance(comp, dict) or set(comp) != {'name', 'role', 'source'}:
                error('各ジャンル要素にはname、role、sourceを指定してください。')
            if not isinstance(comp['name'], str) or not comp['name'].strip() or not isinstance(comp['role'], str):
                error('ジャンルのnameとroleは文字列、nameは空欄不可です。')
            if not isinstance(comp['source'], str) or comp['source'] not in SOURCE_CODES:
                error('ジャンル要素の出典が不正です。')
    for field, keys, limit in [('genre_checks', {'aspect', 'expected', 'observed', 'verdict', 'source'}, 4),
                               ('timeline_notes', {'period', 'observation', 'source'}, 4),
                               ('recommendations', {'change', 'keep', 'reason', 'source'}, 3)]:
        records = data.get(field)
        if records is None:
            continue
        if not isinstance(records, list) or len(records) > limit:
            error(f'{field}は最大{limit}件の配列にしてください。')
        for record in records:
            if not isinstance(record, dict) or set(record) != keys or any(not isinstance(record[k], str) for k in keys):
                error(f'{field}の各要素には指定の文字列フィールドをすべて入れてください。')
            if record['source'] not in SOURCE_CODES:
                error(f'{field}の出典が不正です。')
    if data.get('genre_checks') and not ((data.get('target_genre') or '').strip() or (data.get('style_prompt') or '').strip()):
        error('スタイル照合には目標ジャンルまたは制作時のスタイル指示が必要です。')
    duration = data.get('duration_seconds')
    tempo = data.get('tempo_bpm')
    if (data.get('genre_match') or '').strip() and not (data.get('target_genre') or '').strip():
        error('ジャンル一致の所見には目標ジャンルが必要です。')
    if duration is not None and (not finite(duration) or duration <= 0):
        error('duration_secondsは正の有限数にしてください。')
    if tempo is not None and (not finite(tempo) or tempo <= 0):
        error('tempo_bpmは正の有限数にしてください。')
    sections = data.get('sections')
    if sections is None:
        sections = []
    if not isinstance(sections, list) or len(sections) > 100:
        error('sectionsは最大100区間の配列にしてください。')
    if sections and duration is None:
        error('区間を図示するにはduration_secondsが必要です。')
    section_type = data.get('sections_type', 'pattern')
    if section_type not in ('pattern', 'musical'):
        error('sections_typeはpatternまたはmusicalにしてください。')
    if section_type == 'musical' and sections and sources.get('sections') not in ('audio-listen', 'audio-listen+audio-analysis', 'user', 'local'):
        error('曲構成名には具体的な聴取・ユーザー・ローカル検証の出典が必要です。')
    previous_end = 0
    for n, sec in enumerate(sections, 1):
        if not isinstance(sec, dict) or set(sec) != {'start', 'end', 'label'}:
            error(f'区間{n}にはstart、end、labelを指定してください。')
        start, end, label = sec['start'], sec['end'], sec['label']
        if not finite(start) or not finite(end) or start < 0 or end <= start or end > duration or start < previous_end:
            error(f'区間{n}は0以上、開始<終了、曲長以下、時系列順・重複なしにしてください。')
        if not isinstance(label, str) or not label.strip():
            error(f'区間{n}のlabelを指定してください。')
        previous_end = end
    if len({sec['label'] for sec in sections}) > 8:
        error('凡例に収まる区間ラベルは8種類までです。詳細データを保持し、根拠に基づいて表示内容を整理してください。')
    return data


def fmt_seconds(value):
    if value is None:
        return '未取得'
    value_decimal = Decimal(str(value))
    minutes = int(value_decimal // 60)
    remainder = value_decimal - minutes * 60
    remainder_text = format(remainder, 'f')
    if '.' in remainder_text:
        remainder_text = remainder_text.rstrip('0').rstrip('.')
    whole, dot, fraction = remainder_text.partition('.')
    return f'{minutes}:{whole.zfill(2)}' + (dot + fraction if dot else '')


def main():
    parser = argparse.ArgumentParser(description='正規化した楽曲分析JSONから曲調に合わせたデザインのA3縦1ページPDFを作成')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--theme', choices=sorted(THEMES), help='デザインテーマを手動指定（既定はジャンル・雰囲気から自動選択）')
    parser.add_argument('--font', type=Path, help='日本語TrueTypeフォント（.ttf または .ttc）のパス')
    parser.add_argument('--font-index', type=int, default=0, help='--fontにTTCを指定した際のフォント番号（既定0）')
    args = parser.parse_args()
    if args.font is None and args.font_index != 0:
        parser.error('--font-index requires --font')
    src = args.input.resolve(strict=True)
    dst = args.output.resolve()
    if dst.exists() or dst == src or dst.suffix.lower() != '.pdf':
        parser.error('新しい.pdf出力先を指定してください。既存ファイルは上書きしません。')
    try:
        data = validate(json.loads(src.read_text(encoding='utf-8-sig')))
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    from suno_editorial_layout import render
    try:
        render(data, dst, fmt_seconds, args.theme, font_path=args.font, font_index=args.font_index)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()

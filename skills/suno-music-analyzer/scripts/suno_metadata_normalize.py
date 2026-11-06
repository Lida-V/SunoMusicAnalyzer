#!/usr/bin/env python3
"""Normalize reviewed Suno audio-retrieve metadata without retaining lyrics or IDs.

Accept a JSON envelope from stdin; never write the raw response to disk.  The
calling agent chooses one clip and reviews the values before marking them safe.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MISSING = object()
BRACKETS = re.compile(r'\[[^\[\]\r\n]{1,80}\]')


def presence(obj, key):
    value = obj.get(key, MISSING) if isinstance(obj, dict) else MISSING
    if value is MISSING:
        return 'missing', None
    if value is None:
        return 'null', None
    if not isinstance(value, str):
        return 'invalid_type', None
    if not value.strip():
        return 'empty', None
    return 'value', value


def unwrap(result):
    if not isinstance(result, dict):
        raise ValueError('audio-retrieve response must be an object')
    if 'content' not in result:
        return result
    content = result.get('content')
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        raise ValueError('MCP text content missing')
    if content[0].get('type') != 'text' or not isinstance(content[0].get('text'), str):
        raise ValueError('MCP response must contain text JSON')
    try:
        parsed = json.loads(content[0]['text'])
    except (ValueError, TypeError):
        raise ValueError('invalid MCP text JSON') from None
    if not isinstance(parsed, dict):
        raise ValueError('audio-retrieve response must be an object')
    return parsed


def normalize(envelope, base_report=None):
    if not isinstance(envelope, dict):
        raise ValueError('input envelope must be an object')
    item = unwrap(envelope.get('result'))
    selected_id = envelope.get('selected_id')
    # ID is used only for an in-memory comparison and is never returned.
    if not isinstance(selected_id, str) or not selected_id:
        raise ValueError('selected_id is required for matching')
    if not isinstance(item.get('id'), str) or item['id'] != selected_id:
        raise ValueError('audio-retrieve result does not match selected clip')
    if base_report is not None and envelope.get('base_selected_id') != selected_id:
        raise ValueError('base report clip has not been matched')
    review = envelope.get('review', {})
    if not isinstance(review, dict):
        raise ValueError('review must be an object')
    if set(review) - {'title', 'style_prompt', 'lyrics_tags'}:
        raise ValueError('unknown review field')
    if any(key in review and not isinstance(review[key], bool) for key in ('title', 'style_prompt')):
        raise ValueError('title and style review flags must be booleans')
    report = dict(base_report or {})
    if not isinstance(base_report or {}, dict):
        raise ValueError('base report must be an object')
    # Replace all three fields so metadata from a different clip is not retained.
    sources = dict(report.get('sources') or {})
    for key in ('title', 'style_prompt', 'lyrics_tags'):
        report[key] = None
        sources.pop(key, None)
    report.pop('style_prompt_summary', None)

    raw_meta = item.get('metadata', MISSING)
    meta_state = ('missing' if raw_meta is MISSING else 'null' if raw_meta is None
                  else 'value' if isinstance(raw_meta, dict) else 'invalid_type')
    meta = raw_meta if isinstance(raw_meta, dict) else {}
    title_state, title = presence(item, 'title')
    style_state, style = presence(meta, 'style')
    description_state, _ = presence(meta, 'description')
    lyrics_state, lyrics = presence(meta, 'lyrics')
    status = {'metadata': meta_state, 'title': title_state, 'style_prompt': style_state,
              'description': description_state, 'lyrics_field': lyrics_state}
    for field, state, value in [('title', title_state, title), ('style_prompt', style_state, style)]:
        if state == 'value':
            if review.get(field) is True:
                report[field] = value
                sources[field] = 'audio-retrieve'
                status[field + '_review'] = 'reviewed'
            else:
                status[field + '_review'] = 'review_required'

    selected_tags = review.get('lyrics_tags', MISSING)
    if selected_tags is not MISSING:
        if not isinstance(selected_tags, list) or any(not isinstance(x, str) or not BRACKETS.fullmatch(x) for x in selected_tags):
            raise ValueError('reviewed lyric tags must be bracketed strings')
        # Bracketed prose is not necessarily a tag. The agent explicitly selects
        # reviewed entries, and each one must occur verbatim in the source field.
        candidates = BRACKETS.findall(lyrics or '')
        if any(tag not in candidates for tag in selected_tags):
            raise ValueError('reviewed tag absent from lyrics')
        report['lyrics_tags'] = selected_tags
        if selected_tags:
            sources['lyrics_tags'] = 'audio-retrieve'
        status['lyrics_tags_review'] = 'reviewed'
    elif lyrics_state == 'value':
        status['lyrics_tags_review'] = 'review_required'
    report['sources'] = sources
    return {'report': report, 'field_status': status}


def main():
    parser = argparse.ArgumentParser(description='音声取得結果の検品済み曲情報をレポート用に整理')
    parser.add_argument('--base-report', type=Path, help='検品済みの既存レポートJSON')
    args = parser.parse_args()
    try:
        envelope = json.load(sys.stdin)
        base = json.loads(args.base_report.read_text(encoding='utf-8-sig')) if args.base_report else None
        result = normalize(envelope, base)
    except (ValueError, TypeError, OSError, json.JSONDecodeError):
        # Do not print JSON snippets, field contents, IDs, or traceback.
        print('入力・形式・曲ID照合・レビュー内容を確認してください。', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Meaningful layout and input-guard checks for one-page reports."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

script = Path(__file__).parents[1] / 'scripts' / 'suno-one-page-report.py'


def run(data, expected):
    runtime = Path(__file__).parents[1] / 'runtime'
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime) as folder:
        folder = Path(folder)
        src, dst = folder / 'input.json', folder / 'output.pdf'
        src.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        result = subprocess.run([sys.executable, str(script), str(src), '--output', str(dst)], capture_output=True)
        assert (result.returncode == 0) == expected, result.stderr.decode('utf-8', errors='replace')
        assert dst.exists() == expected
        if expected:
            pdf = PdfReader(str(dst))
            assert len(pdf.pages) == 1
            assert abs(float(pdf.pages[0].mediabox.width) - 841.89) < 1
            assert abs(float(pdf.pages[0].mediabox.height) - 1190.55) < 1
            return pdf.pages[0].extract_text()


missing = run({}, True)
assert '未取得' in missing
assert '判定保留' in missing

base = {'duration_seconds': 100, 'target_genre': 'ポップ', 'genre_match': 'リズムに共通点',
        'caveat': '構造解析と聴取結果が矛盾。要確認。',
        'sections': [{'start': 0, 'end': 12.5, 'label': 'A'}, {'start': 12.5, 'end': 100, 'label': 'B'}],
        'sources': {'target_genre': 'user', 'genre_match': 'audio-listen', 'sections': 'audio-listen+audio-analysis', 'caveat': 'audio-listen+audio-analysis'}}
text = run(base, True)
for word in ('1:40', 'リズムに共通点', 'A', 'B', '聴/構', '矛盾'):
    assert word in text, word
twenty = {'duration_seconds': 20, 'sections': [{'start': i, 'end': i + 1, 'label': str(i % 3)} for i in range(20)]}
text = run(twenty, True)
assert '0:20' in text

run({'genre_match': '合致'}, False)
run({'duration_seconds': 100, 'sections': [{'start': 0, 'end': 50, 'label': 'A'}, {'start': 45, 'end': 80, 'label': 'B'}]}, False)
run({'duration_seconds': 100, 'sections': [{'start': 0, 'end': 110, 'label': 'A'}]}, False)
run({'duration_seconds': 100, 'sections': [{'start': 30, 'end': 20, 'label': 'A'}]}, False)
run({'sections': [{'start': 0, 'end': 1, 'label': 'A'}]}, False)
run({'improvements': '非常に長い文章' * 200}, False)
run({'sources': {'genre': 'invented'}}, False)
eight = {'duration_seconds': 20, 'sections': [{'start': i, 'end': i + 1, 'label': chr(65 + i % 8)} for i in range(20)]}
twenty_text = run(eight, True)
assert 'H' in twenty_text and '0:10' in twenty_text
tiny = {'duration_seconds': 120, 'sections': [{'start': 0, 'end': 0.1, 'label': 'Z'}, {'start': 0.1, 'end': 120, 'label': 'A'}]}
assert '0:00.1' in run(tiny, True)
run({'duration_seconds': 9, 'sections': [{'start': i, 'end': i + 1, 'label': str(i)} for i in range(9)]}, False)
mixed = {'genre': 'ポップ / ダンス', 'genre_components': [{'name': 'ポップ', 'role': '歌声と旋律', 'source': 'audio-listen'}, {'name': 'ダンス', 'role': '規則的なリズム', 'source': 'audio-listen'}], 'style_prompt': 'x' * 1000, 'style_prompt_summary': '明るいシンセと規則的なビート', 'lyrics_tags': ['[Intro]', '[Verse]'], 'sources': {'style_prompt': 'user', 'lyrics_tags': 'user'}}
text = run(mixed, True)
for word in ('ポップ', 'ダンス', '要約', '[Intro]', '比率は示しません'):
    assert word in text, word
run({'style_prompt_summary': '原文がありません'}, False)
run({'lyrics_tags': ['歌詞本文です']}, False)
check = {'aspect': '楽器', 'expected': 'ピアノ', 'observed': '鍵盤系', 'verdict': '推定', 'source': 'audio-listen'}
assert 'ピアノ' in run({'style_prompt': 'piano', 'genre_checks': [check]}, True)
run({'genre_checks': [check]}, False)
run({'genre_match': '一致', 'style_prompt': 'piano'}, False)
musical = {'duration_seconds': 30, 'sections_type': 'musical', 'sections': [{'start': 0, 'end': 30, 'label': 'サビ'}], 'sources': {'sections': 'audio-listen'}}
assert '曲構成（推定）' in run(musical, True)
musical['sources']['sections'] = 'audio-analysis'
run(musical, False)
# Song-dependent design themes: chosen from the analysis words, shown on the page, never alter content.
sys.path.insert(0, str(script.parent))
from suno_report_themes import choose_theme  # noqa: E402
assert choose_theme({'genre': 'フューチャーベース／EDM'})[0] == 'edm'
assert choose_theme({'genre': 'オルタナティブ・ロック', 'mood': '激しい'})[0] == 'rock'
assert choose_theme({'genre': 'バンドサウンドを軸にしたポップ・バラード', 'mood': '温かく切ない'})[0] == 'ballad'
assert choose_theme({'genre': 'ローファイ・ヒップホップ／ジャズ', 'mood': 'まったり'})[0] == 'lofi'
assert choose_theme({})[0] == 'neutral'
assert choose_theme({'genre': 'EDM'}, 'cinematic')[0] == 'cinematic'
assert choose_theme({'genre': 'ポップ', 'key': 'C minor'})[3]['dark'] is True
text = run({'genre': 'トラップ／R&B', 'mood': 'クールで都会的', 'sources': {'genre': 'audio-listen', 'mood': 'audio-listen'}}, True)
assert 'ヒップホップ' in text and '分析結果ではありません' in text
text = run({'design_theme': 'pop', 'summary': '要点の一文', 'next_style_prompt': 'bright synth pop',
            'sources': {'summary': 'audio-listen', 'next_style_prompt': 'agent'}}, True)
for word in ('ポップ', '入力で指定', '総評', '要点の一文', '次の生成で試すスタイル案', '未生成', 'bright synth pop'):
    assert word in text, word
run({'design_theme': 'unknown-theme'}, False)
run({'summary': '提案ではなく要約', 'sources': {'summary': 'agent'}}, False)
timeline_notes = [{'period': p, 'observation': '観察' + p, 'source': 'audio-listen'} for p in ('冒頭', '中盤', 'サビ', '終盤')]
text = run({'timeline_notes': timeline_notes}, True)
assert '観察終盤' in text and '時間帯ごとの観察' in text
print('PASS: missing, one page, sources, 20 sections, 8 labels, mixed genres, prompt summary, tags, long text, invalid boundaries, themes, summary and proposal')

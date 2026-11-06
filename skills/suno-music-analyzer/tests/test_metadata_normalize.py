"""Synthetic tests only: no user metadata, lyrics or clip IDs are used."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


normalizer = load('suno_metadata_normalize.py', 'suno_metadata_normalize')
pdf = load('suno-one-page-report.py', 'suno_one_page_report')


class MetadataTests(unittest.TestCase):
    def envelope(self, metadata, review=None, title='Sample Song'):
        return {'selected_id': 'synthetic-clip', 'result': {'id': 'synthetic-clip',
                'title': title, 'metadata': metadata}, 'review': review or {}}

    def test_null_empty_missing_are_distinct(self):
        result = normalizer.normalize(self.envelope({'style': None, 'description': '', 'lyrics': None}))
        self.assertEqual(result['field_status']['style_prompt'], 'null')
        self.assertEqual(result['field_status']['description'], 'empty')
        self.assertEqual(result['field_status']['lyrics_field'], 'null')
        self.assertIsNone(result['report']['title'])  # unchecked content is not copied
        missing = normalizer.normalize(self.envelope({}))
        self.assertEqual(missing['field_status']['style_prompt'], 'missing')

    def test_only_reviewed_tags_are_preserved_and_lyrics_never_returned(self):
        payload = self.envelope({'style': 'dream pop / soft synth', 'lyrics':
            '[Verse]\nPRIVATE_LYRIC_A\n[not a production tag]\n[Chorus]\nPRIVATE_LYRIC_B'},
            {'title': True, 'style_prompt': True, 'lyrics_tags': ['[Verse]', '[Chorus]']})
        payload['base_selected_id'] = 'synthetic-clip'
        result = normalizer.normalize(payload, {'title': 'old title', 'style_prompt_summary': 'old'})
        self.assertEqual(result['report']['title'], 'Sample Song')
        self.assertEqual(result['report']['style_prompt'], 'dream pop / soft synth')
        self.assertEqual(result['report']['lyrics_tags'], ['[Verse]', '[Chorus]'])
        self.assertNotIn('style_prompt_summary', result['report'])
        self.assertEqual(result['report']['sources']['title'], 'audio-retrieve')
        text = json.dumps(result, ensure_ascii=False)
        self.assertNotIn('PRIVATE_LYRIC', text)
        self.assertNotIn('not a production tag', text)
        self.assertNotIn('synthetic-clip', text)
        pdf.validate(result['report'])

    def test_unreviewed_values_never_transfer_or_retain_stale_metadata(self):
        envelope = self.envelope({'style': 'Unreviewed', 'lyrics': '[Verse]\nsecret'})
        envelope['base_selected_id'] = 'synthetic-clip'
        result = normalizer.normalize(envelope,
            {'title': 'old', 'style_prompt': 'old', 'lyrics_tags': ['[old]'],
             'sources': {'title': 'user', 'genre': 'audio-listen'}})
        self.assertIsNone(result['report']['title'])
        self.assertIsNone(result['report']['style_prompt'])
        self.assertIsNone(result['report']['lyrics_tags'])
        self.assertNotIn('title', result['report']['sources'])
        self.assertEqual(result['field_status']['title_review'], 'review_required')

    def test_id_mismatch_and_invented_tags_are_rejected(self):
        mismatch = self.envelope({'lyrics': '[Verse]'})
        mismatch['selected_id'] = 'another'
        with self.assertRaises(ValueError):
            normalizer.normalize(mismatch)
        with self.assertRaises(ValueError):
            normalizer.normalize(self.envelope({'lyrics': '[Verse]'}, {'lyrics_tags': ['[Chorus]']}))
        with self.assertRaises(ValueError):
            normalizer.normalize(self.envelope({'lyrics': None}), {'title': 'previous clip'})

    def test_mcp_content_wrapper_and_missing_metadata(self):
        item = {'id': 'synthetic-clip', 'title': 'Song'}
        wrapped = {'selected_id': 'synthetic-clip', 'result': {'content': [
            {'type': 'text', 'text': json.dumps(item)}]}, 'review': {'title': True}}
        result = normalizer.normalize(wrapped)
        self.assertEqual(result['field_status']['metadata'], 'missing')
        self.assertEqual(result['field_status']['lyrics_field'], 'missing')
        self.assertEqual(result['report']['title'], 'Song')


if __name__ == '__main__':
    unittest.main()

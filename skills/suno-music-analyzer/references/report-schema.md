# One-page report input

The renderer accepts a UTF-8 JSON object assembled from the verified results. Unknown fields are rejected. Values may be omitted or `null` when unavailable; they are not filled automatically. Preserve longer evidence in a separate private project file. The PDF is one A3 portrait page.

From the skill directory, run:

```sh
python scripts/suno-one-page-report.py output/report.json --output output/report.pdf
```

The renderer requires Python 3.9+, ReportLab, and a usable CJK TrueType font. It looks for suitable system fonts; if needed pass `--font /path/to/font.ttf` and, for a font collection, `--font-index 0`. Optional `--theme` can select a supported design theme. Existing output files are not overwritten. If text will not fit, the renderer reports an error rather than silently clipping it: prepare a faithful, visibly identified summary while retaining the original elsewhere.

## Fields

| Key | Type and meaning |
|---|---|
| `title`, `analyzed_at` | Strings: track name and analysis date. |
| `style_prompt` | Original creation style or instruction, not lyrics. |
| `style_prompt_summary` | Short display summary when the original is too long; `style_prompt` must also be present. |
| `lyrics_tags` | Array of actual bracketed creation instructions only; never full lyrics. |
| `duration_seconds`, `tempo_bpm` | Positive numbers. Tempo is an estimate unless independently measured. |
| `meter`, `key`, `genre`, `target_genre`, `genre_match`, `mood` | Strings. `genre_match` requires an explicit target. |
| `genre_components` | Up to six objects: `{"name":"...","role":"audible evidence","source":"audio-listen"}`. Do not infer proportions. |
| `genre_checks` | Up to four objects with `aspect`, `expected`, `observed`, `verdict`, `source`. Requires an actual target genre or style prompt. |
| `vocals`, `instruments`, `rhythm`, `development`, `highlights` | Strings describing supported listening findings. |
| `timeline_notes` | Up to four objects with `period`, `observation`, `source`; make unverified times explicit. |
| `mix_observations`, `improvements` | Strings: listening observations and potential changes. Do not present invented numerical measurements. |
| `recommendations` | Up to three objects with `change`, `keep`, `reason`, `source`; empty strings represent unknown details. |
| `summary` | One or two sentences grounded in the obtained analysis. |
| `next_style_prompt` | Optional proposed next-generation style. This is a new, untested proposal, not the original instruction. |
| `caveat` | Important uncertainty or contradiction. |
| `sections` | Up to 100 objects with `start`, `end`, `label`; times are seconds and must be ordered, nonoverlapping, and within `duration_seconds`. |
| `sections_type` | `pattern` (default) for model-assigned labels, `musical` only for sourced musical section names with supported times. |
| `design_theme` | Optional: `neutral`, `ballad`, `edm`, `rock`, `lofi`, `pop`, `cinematic`, or `urban`. The visual theme is not an analytical conclusion. |
| `sources` | Object mapping field names to their provenance. |

Sources use `audio-listen`, `audio-analysis`, `audio-listen+audio-analysis`, `audio-retrieve`, `user`, `local`, `agent`, or `unknown`; `agent` identifies proposals rather than original metadata or measurements. Use a suitable source for each available item. See the script's validation errors for precise limits and combinations.

## Minimal synthetic example

This demonstrates shape only; its numbers are fictional and do not represent a real song.

```json
{
  "title": "Example track",
  "duration_seconds": 180,
  "tempo_bpm": 120,
  "genre": "Pop with electronic influences",
  "genre_components": [
    {"name": "Pop", "role": "melodic vocal", "source": "audio-listen"},
    {"name": "Electronic", "role": "synth textures", "source": "audio-listen"}
  ],
  "sections_type": "pattern",
  "sections": [
    {"start": 0, "end": 90, "label": "A"},
    {"start": 90, "end": 180, "label": "B"}
  ],
  "sources": {
    "title": "user",
    "duration_seconds": "user",
    "tempo_bpm": "audio-analysis",
    "genre": "audio-listen",
    "sections": "audio-analysis"
  }
}
```

The example does not establish a target-genre match, a musical section name, or a genre percentage. In actual use, only supply evidence obtained for the same clip.

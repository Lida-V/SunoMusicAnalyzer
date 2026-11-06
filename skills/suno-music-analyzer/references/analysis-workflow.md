# Analysis workflow

## Connect and identify the track

Use the official Suno MCP endpoint `https://api.suno.com/mcp` through an MCP-compatible client. Sign-in and authorization happen in that client. Available tools, schemas, quotas, access, and download or upload allowances may change; check their current descriptions before using them. Official connection instructions: <https://help.suno.com/en/articles/14551425>.

Select the requested completed Suno track and hold its clip ID consistently through the task. Use `audio-retrieve` to inspect available title and creation metadata; compare its returned ID to the selected ID before merging. List views may omit lyrics. A field returned as null or absent is **unavailable from that response**, not evidence that the user never entered it. If a usable title, style, or tags are missing, use user-provided information when available and mark its source. Never infer creation instructions from audio or treat model-generated tags as the creator's original input.

The bundled metadata normalizer can help transform a reviewed `audio-retrieve` response without outputting the clip ID or lyric text. See its `--help`. The calling agent must review values and select genuine instruction tags: not every bracketed phrase in lyrics is a production tag. Apply the user's privacy preferences; do not unnecessarily hide a work's title.

### Metadata normalizer input

Send a JSON envelope to `scripts/suno_metadata_normalize.py` on standard input. The following example is **fictional** and illustrates the structure, not a real clip or song:

```json
{
  "selected_id": "fictional-clip-id",
  "result": {
    "id": "fictional-clip-id",
    "title": "Example track",
    "metadata": {
      "style": "Bright synth pop",
      "description": null,
      "lyrics": "[Intro]\n[Verse]\n[Chorus]"
    }
  },
  "review": {
    "title": true,
    "style_prompt": true,
    "lyrics_tags": ["[Intro]", "[Verse]", "[Chorus]"]
  }
}
```

`result` can also be the MCP tool-result envelope whose first text content contains the `audio-retrieve` JSON. `selected_id` must match the response `id`. When combining with an existing report through `--base-report <path>`, include `base_selected_id` in the input envelope, equal to `selected_id`, only after confirming the base report belongs to that same clip. A missing or different ID stops the merge. The JSON output contains `report`, suitable for further normalization into renderer input, and `field_status`, which distinguishes missing, null, empty, invalid type, and present values. The output does not contain the input ID or lyric field.

The `review` flags mean the **agent has reviewed the actual values internally** and selected genuine production tags. They do not require a separate user approval for each metadata field. Do not mark unknown or unreviewed values as reviewed. Do not save or log the real input envelope, raw lyrics, or credentials; do not log clip IDs. Pass the response in memory to the subprocess and store only the authorized, necessary normalized output. If a project must be resumed, a clip ID may be stored separately in the user's designated private project outside version control, as described above.

Local files may require upload to Suno before they can be analyzed by an MCP tool that expects a clip ID. Confirm the source, rights, service destination, and current accepted input before submitting audio. If no applicable upload path exists, report the limitation rather than substitute a different track.

## Question budget

Per track and per request, use up to three new `audio-listen` questions by default. If needed, add questions up to five total, recording why; follow any different limit specified by the user. Conservatively count failed submissions and retries. Polling an existing question through `audio-listen-wait` is not another new question. Record the number of submissions, outcomes, and analysis time without storing credentials. Check the service's current daily quota rather than assuming it is unchanged.

Suggested questions, adapted to the user's purpose and language:

1. **Genre and intent:** identify potentially mixed genres and the audible rhythmic, instrumental, vocal, or harmonic cues for each. Compare with stated targets only when those targets are actually known. Do not manufacture genre percentages.
2. **Structure and development:** describe how voice, instrumentation, rhythm, dynamics, hooks, and texture change from beginning to end. Ask for timestamps only when the service can support them. Do not present inferred labels as confirmed sections.
3. **Mix and improvements:** describe audible balance, clarity, density, and space. Propose a small number of changes with reasons and elements to preserve. Do not manufacture LUFS, true peak, frequency values, or processing settings.

Use `audio-analysis` separately for its available tempo, key, time signature, section or other acoustic estimates. Values may be missing or contradict `audio-listen`. Preserve the source and uncertainty of each observation. If the results conflict, highlight the conflict and recommend checking the actual audio; do not silently reconcile them.

## Structure and report preparation

- Keep modeled pattern IDs as their original labels; do not equate A/B labels with verses or choruses. Place unverified, untimed development notes in a separate text section.
- Use a musical section name only when both its interpretation and timing have a supporting source. Mark estimated boundaries as estimates.
- List multiple genres with their evidence and source. Node size or bar length must not imply ratios when no trustworthy quantity is available.
- Record the actual title, style prompt, and selected input tags where obtained. Place personal data, credentials, audio, full lyrics, and detailed results only where authorized; do not commit private materials to a public repository.
- `summary` is a faithful synthesis of obtained evidence. `next_style_prompt`, if requested or useful, is an untested proposal and should be clearly marked as such; it is not the original prompt or a completed generation.
- Write evidence and full responses separately from the one-page PDF, subject to privacy constraints. Render the PDF to an image and check every section for legibility, clipped text, unsupported claims, and output page count.

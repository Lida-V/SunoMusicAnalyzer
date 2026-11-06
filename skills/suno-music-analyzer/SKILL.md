---
name: suno-music-analyzer
description: Analyze a specified Suno track using the official Suno MCP and create an illustrated, single-page PDF report. Use for music analysis, arrangement and style comparison, and production feedback on a Suno track.
---

# Suno Music Analyzer

Use the official Suno MCP to collect evidence about the requested track, then create a readable one-page PDF with the bundled renderer. Keep the report's observations, estimates, measured values, and proposals distinct. Do not imply that unverified model output is a human listening assessment or a measurement.

## Workflow

1. Resolve the user's track once to a clip ID. Use that same ID for metadata, listening, and analysis. Check IDs on returned metadata; do not silently merge results if the match cannot be established. If continuing later, retain the ID only in the user's designated private project, outside version control.
2. Retrieve the track's title and available creation metadata with `audio-retrieve`. Distinguish a missing field, null, empty string, and a value. Preserve the original style prompt when available. Include only actual bracketed instructions from the lyrics field, reviewed as tags; do not put lyrics in the PDF. Treat the user's instructions as intentions and the analyzed audio as a separate result. Do not invent missing values or infer original tags from the sound.
3. Use `audio-listen` for the analysis and `audio-listen-wait` to follow the same pending question. The default budget is **three new questions per track per request**, with at most five when additional questions are necessary; an explicit user limit takes precedence. Count failed submissions and retries conservatively. Waiting on the same ID is not a new question. Check the current tool description for the actual quota. Use `audio-analysis` separately when useful.
4. Collect genre components and audible evidence, target-style alignment when a target is known, arrangement, vocals and instruments, changes over time, mix observations, strengths, and practical changes with reasons and elements to preserve. Follow [references/analysis-workflow.md](references/analysis-workflow.md) for questions, source handling, and uncertainty.
5. Convert supported findings into the renderer input described in [references/report-schema.md](references/report-schema.md). Preserve the detailed evidence separately in the user's chosen project, with secrets and unnecessary lyrics omitted. Visually inspect the one-page PDF and correct overflow or illegible text before delivery. If a longer prompt cannot fit, retain the original in the project and clearly label any displayed summary.

## Guardrails

- Never invent genre percentages, timing, style alignment, acoustic measurements, lyrics, or improvements. If outputs disagree, visibly report the disagreement and do not choose a winner without evidence.
- Pattern identifiers such as A/B are not automatically intro, verse, or chorus. Show musical section names and times only when supported, otherwise label the pattern and its uncertainty.
- Respect the user's specified source and permissions. Uploading a local file sends it to Suno; do not assume a local file is already a Suno clip or that upload and download are available. Do not create or edit songs merely to test analysis.
- Use only the connected official MCP tools available in the current environment. Verify current schemas and account access at use time; do not request or embed cookies, OAuth tokens, or API keys in a report.

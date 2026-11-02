# aitranscribe

A TUI-first terminal tool that records or loads audio, transcribes it through an
OpenAI-compatible STT endpoint, and optionally post-processes the text with an
LLM. The glossary below fixes the vocabulary for live fragmentation.

## Language

### Live fragmentation

**Fragmenttakt**:
The time that must elapse before a cut may be placed, measured from the previous
actual cut. Nothing is analysed during it.
_Avoid_: Nominalfenster, Fix-Fenster, cut interval window

**Suchfenster**:
The forward span that must be fully recorded before a cut is decided, and that
is searched in full for the quietest place.
_Avoid_: Suchspan, LATE_HALF, guard zone, Schonfrist

**Fragment**:
One committed, gapless piece of the recording between two cuts. Fragment i+1
starts exactly at fragment i's end.
_Avoid_: Chunk (that is the post-hoc split of a file, `chunk_audio`)

**Festschreibung**:
The moment a fragment becomes final and enters the transcription queue.
_Avoid_: Commit (in prose; the code identifier stays `commit`)

**Erzwungener Schnitt**:
A cut without a silence candidate (Q = 0), placed at the quietest 10 ms frame of
the search window.
_Avoid_: Fallback cut

**Restfragment**:
The audio after the last cut when the recording stops; it is taken whole and
unsearched, and it determines the stop→raw latency.
_Avoid_: Tail chunk

**Q**:
The deficit area of a silence candidate under the adaptive axis
`X = 0.65 · mean level + 100` — depth and duration in one number. The cut lands
at the candidate's area centroid, clamped 150 ms inside it.
_Avoid_: Silence score, confidence

### Seams

**Naht**:
A fragment boundary — the place where one fragment's audio ends and the next
begins.
_Avoid_: Seam point, splice

**Pre-roll**:
The last second of the previous fragment's audio, prepended to the next upload
so the service hears the words on both sides of the naht.
_Avoid_: Overlap, context audio

**Prompt-Carry-over**:
The seam-local prompt built from the previous transcript tail (≤96 characters,
cut at a word boundary).
_Avoid_: Context prompt, carry prompt

**Echo-Trim**:
Removal of a transcript head that repeats the previous transcript tail (≤8
tokens, head token must match, at most one mismatch for k ≥ 2). Without a match
everything is kept.
_Avoid_: Deduplication, overlap trim

### Transcription

**Profil**:
A complete endpoint description (base_url, keys, model, upload ceilings, upload
format). A scope table holds only the selector.
_Avoid_: Provider config, account

**Upload-Format**:
The encoding of a fragment upload, owned by the STT profile: `none` (PCM WAV,
no ffmpeg), `ogg` (Opus 24 kbps), `mp3` (32 kbps).
_Avoid_: Compression setting

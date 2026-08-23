# Approach (≤200 words)

I put nearly all the intelligence server-side, in Python (FastAPI), rather
than treating this as a JS app with a thin backend. Intent parsing (add /
remove / search / quantity / price-filter), categorization, seasonal
recommendations, substitute lookup, and the "you're probably running low"
suggestion engine are all plain Python — regex and heuristics, not an LLM
call, so there's no API key and no per-request cost or latency. The browser
only handles what a browser must: capturing the mic and playing audio back,
via the free built-in Web Speech API.

The two features I focused on for the "fast and interruptible" requirement:
a `Web Audio` amplitude analyser runs alongside speech recognition and
detects the user starting to talk within ~60ms, well before the recognizer
returns any text — that's what makes barge-in interrupt the assistant's
speech instantly rather than after a lag. Second, short commands are parsed
from *interim* transcripts as soon as they stabilize (~450ms), instead of
waiting for the browser's "final" result, which can take a second or more.

Smart suggestions use a simple on-device heuristic: each grocery category
has a typical repurchase cadence (dairy ~6 days, household ~25 days), and
items removed longer ago than that cadence get resurfaced.

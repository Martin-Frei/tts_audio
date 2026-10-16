# tts_audio

**English** | [Deutsch](README.de.md)

tts_audio is a Python pipeline that turns current headlines and teasers from RSS feeds into a spoken news briefing and delivers it as a podcast feed. Along the way, two separate stages check the work: a fact check compares every statement in the script with its source, and a residue check aborts as soon as the text still contains digits, abbreviations or special characters the voice would read out wrongly. This is a learning project in progress; phase 1, local speech output with Piper, is currently being built.


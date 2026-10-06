"""Redact machine paths and credential-shaped strings from exported evidence."""
from pathlib import Path
import re
import tempfile


def redact_evidence(value, roots=()):
    text=str(value)
    prefixes=[(str(Path.home()), '$HOME'),
              (str(Path(tempfile.gettempdir())), '$TMPDIR')]
    prefixes += [(str(root), '$CHECKOUT') for root in roots]
    # Replace specific prefixes before their containing home/temp directories.
    for source,replacement in sorted(prefixes,key=lambda pair:len(pair[0]),reverse=True):
        if not source or source in ('/', '.', '\\'):
            continue
        for variant in (source,source.replace('\\','/'),source.replace('\\','\\\\')):
            text=text.replace(variant,replacement)
    text=re.sub(r'/home/[^/\s"<>]+', '$HOME', text)
    text=re.sub(r'/Users/[^/\s"<>]+', '$HOME', text)
    text=re.sub(r'[A-Za-z]:(?:\\+|/)Users(?:\\+|/)[^\\/\s"<>]+', '$HOME', text)
    text=re.sub(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{24,})', '[REDACTED_CREDENTIAL]', text)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
                lambda m:m.group() if m.group().endswith(('.invalid','@example.com','@example.org','@example.net','@users.noreply.github.com')) else '[REDACTED_EMAIL]',text)
    return text

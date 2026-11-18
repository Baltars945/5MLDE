import sys

for flux in (sys.stdout, sys.stderr):
    if flux is not None and hasattr(flux, "reconfigure"):
        flux.reconfigure(encoding="utf-8", errors="replace")

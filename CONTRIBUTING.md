# Contributing to DARK VOID

Thank you for contributing to **DARK VOID**!

## Core Invariants
Before opening a Pull Request, verify that your changes respect DARK VOID's non-negotiable engineering rules:
1. **Original File Protection**: Never delete, overwrite, or modify input video files.
2. **Mandatory Output Specification**: Output files must use QuickTime `.mov` container, `dnxhd` codec with `dnxhr_hq` profile, `yuv422p` pixel format, and `pcm_s16le` audio (or `-an` if the source has no audio stream).
3. **Output Naming**: `<original_stem>_Resolve.mov`.
4. **Subprocess Safety**: Never use `shell=True`. Always pass argument lists.
5. **CLI Only**: Keep DARK VOID strictly a terminal application.

## Running Tests Locally
```bash
python3 -m unittest discover -s tests -v
# or with pytest:
pytest -v
```

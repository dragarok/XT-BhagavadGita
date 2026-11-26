"""Bundle the Gita app: kit/gamekit.lua + src/*.lua -> index.lua.

  python -I bundle.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'kit'))
import bundle  # noqa: E402

if __name__ == '__main__':
    bundle.bundle(HERE)

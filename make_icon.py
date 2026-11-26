"""Draw icon.png: the app's 96x96 1-bpp icon for the Ink App grid: ॐ in Tiro Devanagari inside a
rounded square, like the upstream apps' icons. Drawn at 8x, reduced, then cut to black and white.

    python -I make_icon.py      # needs sources/cache/fonts (tools/fetch_sources.py)
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, 'sources', 'cache', 'fonts', 'TiroDevanagariHindi-Regular.ttf')
SIZE, K = 96, 8
S = SIZE * K


def draw():
    img = Image.new('L', (S, S), 255)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6 * K, 6 * K, 90 * K, 90 * K], radius=12 * K, outline=0, width=4 * K)
    f = ImageFont.truetype(FONT, 66 * K, layout_engine=ImageFont.Layout.RAQM)
    l, t, r, b = d.textbbox((0, 0), 'ॐ', font=f)
    d.text(((S - (r - l)) / 2 - l, (S - (b - t)) / 2 - t + 2 * K), 'ॐ', font=f, fill=0)
    small = img.resize((SIZE, SIZE), Image.BOX)
    return small.point(lambda v: 0 if v < 128 else 255).convert('1')


if __name__ == '__main__':
    out = os.path.join(HERE, 'icon.png')
    draw().save(out)
    print(f'wrote {out}')

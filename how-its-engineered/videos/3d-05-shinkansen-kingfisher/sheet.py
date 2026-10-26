import sys, glob, os
from PIL import Image, ImageDraw
d = sys.argv[1]
fs = sorted(glob.glob(d + '/*.png')); ims = [Image.open(f).convert('RGB') for f in fs]
w, h = ims[0].size; cols = 5; rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (w * cols, h * rows))
for i, (f, im) in enumerate(zip(fs, ims)):
    S.paste(im, ((i % cols) * w, (i // cols) * h)); ImageDraw.Draw(S).text(((i % cols) * w + 6, (i // cols) * h + 6), os.path.basename(f), fill=(255, 255, 0))
S.save('sheet_' + os.path.basename(d) + '.png')

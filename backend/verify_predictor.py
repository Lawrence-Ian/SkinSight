import io
import os
import sys

from PIL import Image

sys.path.insert(0, os.getcwd())
from ml.skin_model import SkinPredictor

p = SkinPredictor()
img = Image.new('RGB', (64, 64), color=(255, 0, 0))
blob = io.BytesIO()
img.save(blob, format='JPEG')
print(p.predict(blob.getvalue()))

import base64
import io
import json
import sys
from PIL import Image
import requests

# Create a test image
# Use a larger image and higher JPEG quality so the payload exceeds 3KB
img = Image.new('RGB', (512, 512), color=(120, 200, 150))
buf = io.BytesIO()
img.save(buf, format='JPEG', quality=95)
image_bytes = buf.getvalue()
print('Image size bytes:', len(image_bytes))

b64 = base64.b64encode(image_bytes).decode('ascii')
url = 'http://127.0.0.1:8000/api/analysis/scan'
payload = {'frame': b64, 'source': 'live_camera'}

resp = requests.post(url, json=payload)
print('Status:', resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print('Response text:', resp.text)

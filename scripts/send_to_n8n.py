"""Simple demo script: POST an in-memory image to the n8n webhook `generate-listing`"""
import io
import requests
from PIL import Image

URL = "http://localhost:5678/webhook/generate-listing"


def create_sample_image_bytes():
    img = Image.new("RGB", (400, 300), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def main():
    img = create_sample_image_bytes()
    files = {"data": ("sample.jpg", img, "image/jpeg")}
    # optional form fields can be added to `data=` param
    r = requests.post(URL, files=files)
    print("Status:", r.status_code)
    try:
        print("Response JSON:", r.json())
    except Exception:
        print("Response text:", r.text)


if __name__ == "__main__":
    main()

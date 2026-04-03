import os
import ssl
from urllib.request import urlopen, Request
from PIL import Image
import sys

def download_and_convert():
    url = "https://anta.obs.cn-south-1.myhuaweicloud.com/fanqie_auto_publish_logo.png"
    img_path = "downloaded_logo.png"
    
    print("Downloading logo...")
    try:
        # Ignore SSL certification errors just in case
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, context=ctx) as response, open(img_path, 'wb') as out_file:
            out_file.write(response.read())
        print("Download successful.")
    except Exception as e:
        print(f"Error downloading image: {e}")
        return

    print("Converting to ICO...")
    try:
        img = Image.open(img_path)
        icon_sizes = [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]
        img.save("logo.ico", format="ICO", sizes=icon_sizes)
        print("Success: new logo.ico generated.")
    except Exception as e:
        print(f"Error converting image: {e}")

if __name__ == '__main__':
    download_and_convert()

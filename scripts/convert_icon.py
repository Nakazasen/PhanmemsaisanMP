from PIL import Image
import os

input_path = r'C:\Users\tvn183660\.gemini\antigravity\brain\4f4f0d58-96f9-4388-bb32-a148a815298f\app_icon_v2_gold_1774838116765.png'
output_path = r'c:\ProgramData\Sandbox\PhanmemsaisanMP\assets\app_icon.ico'

img = Image.open(input_path)
# PyInstaller and Windows work best with multiple sizes in one .ico
icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
img.save(output_path, sizes=icon_sizes)
print(f"Icon saved to {output_path}")

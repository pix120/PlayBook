from PIL import Image, ImageDraw

img = Image.new("RGB", (200, 200), color=(50, 50, 50))
draw = ImageDraw.Draw(img)
draw.rectangle([60, 80, 140, 120], fill=(100, 100, 100))
draw.text((70, 90), "Аудио", fill=(200, 200, 200))
img.save("assets/default_cover.png")

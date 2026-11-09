"""Contact sheet: python sheet.py out.jpg cols img1 img2 ..."""
import sys, cv2, numpy as np, os
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
tw, th = 640, 360
tiles = []
for f in files:
    im = cv2.resize(cv2.imread(f), (tw, th), interpolation=cv2.INTER_AREA)
    cv2.putText(im, os.path.basename(f)[:-4], (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
    tiles.append(im)
while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])

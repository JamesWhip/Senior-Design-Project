import cv2
import numpy as np
from scipy import stats

# Load image
image_path = "VirtualBoard.png"   # replace with your image
img = cv2.imread(image_path)

if img is None:
    print("Error: Could not load image.")
    exit() 


pattern_size = (7, 7)


gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray,90,150,apertureSize = 3)
cv2.imwrite('canny.jpg',gray)

# Find the chessboard corners
ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

if ret:
    print("Chessboard corners found successfully.")
    # Refine the corner locations to sub-pixel accuracy
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    tileSize = int(abs(corners[0][0][0] - corners[1][0][0]))

    tiles = [[[0,0] for _ in range(8)] for _ in range(8)]

    i = 0
    for corner in corners:
        x = int(corner[0][0])
        y = int(corner[0][1])
        tiles[i%7+1][i//7+1] = [x,y]
        i += 1

    for i in range(1,8):
        x,y = tiles [1][i]
        tiles[0][i] = [x,max(y-tileSize, 0)]

    for i in range(0,8):
        x,y = tiles [i][1]
        tiles[i][0] = [max(x-tileSize, 0),y]

    for x in range(8):
        for y in range(8):
            posX,posY = tiles[x][y]
            sub_img = img[posY:posY+tileSize, posX:posX+tileSize]
            cv2.imwrite( "Squares/tile_" + str(x) + "_" + str(y) + ".jpg", sub_img)

    # Draw and display the corners on the original image
    img_corners = cv2.drawChessboardCorners(img.copy(), pattern_size, corners, ret)
    cv2.imshow('Corners', img_corners)



else:
    print("Could not find chessboard corners.")

cv2.waitKey(0)
cv2.destroyAllWindows()
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

    # Draw and display the corners on the original image
    img_corners = cv2.drawChessboardCorners(img.copy(), pattern_size, corners, ret)
    cv2.imshow('Corners', img_corners)

else:
    print("Could not find chessboard corners.")

cv2.waitKey(0)
cv2.destroyAllWindows()
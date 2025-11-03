import cv2
import numpy as np
from scipy import stats

# Load image
image_path = "old/image.png"   # replace with your image
img = cv2.imread(image_path)
split_img = [[None for _ in range(8)] for _ in range(8)] 

if img is None:
    print("Error: Could not load image.")
    exit() 

print("Found image")

pattern_size = (7, 7)


gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray, (5, 5), 0)

ret,otsu_binary = cv2.threshold(blur,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)


edges2 = cv2.Canny(otsu_binary,90,150,apertureSize = 3)

canny = cv2.Canny(blur,90,150,apertureSize = 3)

kernel = np.ones((2, 2), np.uint8) 
dilation = cv2.dilate(canny, kernel, iterations=1) 

lines = cv2.HoughLinesP(dilation, 1, np.pi/180, threshold=200, minLineLength=200, maxLineGap=100)

empty = np.zeros(canny.shape, np.uint8)

if lines is not None:
    for i, line in enumerate(lines):
        x1, y1, x2, y2 = line[0]
        
        # draw lines
        cv2.line(empty, (x1, y1), (x2, y2), (255,255,255), 2)
 
cv2.imshow("edge", canny)
cv2.imshow("lines", empty)

board_contours, hierarchy = cv2.findContours(empty, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

square_centers=list()

# draw filtered rectangles to "canny" image for better visualization
board_squared = canny.copy()  

for contour in board_contours:
    if 2000 < cv2.contourArea(contour) < 20000:
        # Approximate the contour to a simpler shape
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Ensure the approximated contour has 4 points (quadrilateral)
        if len(approx) == 4:
            pts = [pt[0] for pt in approx]  # Extract coordinates

            # Define the points explicitly
            pt1 = tuple(pts[0])
            pt2 = tuple(pts[1])
            pt4 = tuple(pts[2])
            pt3 = tuple(pts[3])

            x, y, w, h = cv2.boundingRect(contour)
            center_x=(x+(x+w))/2
            center_y=(y+(y+h))/2

            square_centers.append([center_x,center_y,pt2,pt1,pt3,pt4])

             

            # Draw the lines between the points
            cv2.line(board_squared, pt1, pt2, (255, 255, 0), 7)
            cv2.line(board_squared, pt1, pt3, (255, 255, 0), 7)
            cv2.line(board_squared, pt2, pt4, (255, 255, 0), 7)
            cv2.line(board_squared, pt3, pt4, (255, 255, 0), 7)


cv2.imshow("final", board_squared)

cv2.waitKey(0)
cv2.destroyAllWindows()
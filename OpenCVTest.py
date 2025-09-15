import cv2
import numpy as np
from scipy import stats

# Load image
image_path = "virtualboard.png"   # replace with your image
img = cv2.imread(image_path)

if img is None:
    print("Error: Could not load image.")
    exit() 
#[118, 150, 86], green tile
lower = np.array([80, 140, 110])
upper = np.array([90, 160, 125])

mask = cv2.inRange(img, lower, upper)

masked = cv2.bitwise_and(img,img, mask=mask)

result = img - masked

cv2.imshow("color mask",masked)

gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray,90,150,apertureSize = 3)
cv2.imwrite('canny.jpg',edges)

lines = cv2.HoughLines(edges,1,np.pi/180,150)

if not lines.any():
    print('No lines were found')
    exit()

vertical = []
horizontal = []

for line in lines:
    rho,theta = line[0]
    a = np.cos(theta)
    b = np.sin(theta)
    x0 = a*rho
    y0 = b*rho
    x1 = int(x0 + 1000*(-b))
    y1 = int(y0 + 1000*(a))
    x2 = int(x0 - 1000*(-b))
    y2 = int(y0 - 1000*(a))

    if (a > 0.99):
        vertical.append(x1)
    elif (a < .01):
        horizontal.append(y1)

    cv2.line(img,(x1,y1),(x2,y2),(0,0,255),2)

vertical.sort()
horizontal.sort()

vDelta = []
for i in range(len(vertical)-1):
    vDelta.append(vertical[i+1] - vertical[i])

    
hDelta = []
for i in range(len(horizontal)-1):
    hDelta.append(horizontal[i+1] - horizontal[i])

print(vDelta)
print(hDelta)

print(stats.mode(hDelta + vDelta))

# Show results
cv2.imshow("Original", img)
cv2.imshow("Edges", edges)

cv2.waitKey(0)
cv2.destroyAllWindows()

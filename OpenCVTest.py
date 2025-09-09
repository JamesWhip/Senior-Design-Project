import cv2
import numpy as np

# Load image
image_path = "VirtualBoard.png"   # replace with your image
image = cv2.imread(image_path)

if image is None:
    print("Error: Could not load image.")
    exit()

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Smooth to reduce noise
blur = cv2.GaussianBlur(gray, (11,11), 0)

# Detect edges with Canny
edges = cv2.Canny(blur, 50, 150)

# Find contours (potential pieces)
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Create masks for pieces
mask_white = np.zeros_like(gray)
mask_black = np.zeros_like(gray)

for cnt in contours:
    area = cv2.contourArea(cnt)
    if area > 100:  # filter small contours (board lines, noise)
        x, y, w, h = cv2.boundingRect(cnt)
        roi = gray[y:y+h, x:x+w]

        mean_intensity = np.mean(roi)

        # Classify based on brightness
        if mean_intensity > 127:  
            cv2.drawContours(mask_white, [cnt], -1, 255, -1)
        else:
            cv2.drawContours(mask_black, [cnt], -1, 255, -1)

# Apply masks
white_pieces = cv2.bitwise_and(image, image, mask=mask_white)
black_pieces = cv2.bitwise_and(image, image, mask=mask_black)

# Show results
cv2.imshow("Original", image)
cv2.imshow("Edges", edges)
cv2.imshow("White Pieces", white_pieces)
cv2.imshow("Black Pieces", black_pieces)

cv2.waitKey(0)
cv2.destroyAllWindows()

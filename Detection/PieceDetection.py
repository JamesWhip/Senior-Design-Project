import cv2
import mediapipe as mp
import numpy as np

PIXELS_PER_SQUARE = 80
THRESHOLD = 0.15

def detect_pieces(img):
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray,90,150,apertureSize = 3)

    norm_img, norm_gray, norm_edges = normalize_img(img, gray, edges)
    if norm_img is None:
        return img
    
    tiles = get_tiles(norm_edges)

    for pos in tiles.keys():
        if tiles[pos] > THRESHOLD:
            x, y = pos_to_pixel(pos)
            cv2.circle(norm_img, (int(x+PIXELS_PER_SQUARE/2), int(y+PIXELS_PER_SQUARE/2)), PIXELS_PER_SQUARE//2, (255,0,0), 2)
            

    return norm_img

def normalize_img(img, gray, edges):
    ret, corners = cv2.findChessboardCorners(edges, (7,7), None)

    if not ret:
        return None, None, None
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    points = [corners[0][0], corners[6][0], corners[42][0], corners[48][0]]
    
    #for pnt in points:
     #   cv2.circle(img, (int(pnt[0]), int(pnt[1])), 5, (255,0,0), 2)

    pts1 = np.float32(order_points(points))
    pts2 = np.float32([[2*PIXELS_PER_SQUARE, 2*PIXELS_PER_SQUARE], [8*PIXELS_PER_SQUARE, 2*PIXELS_PER_SQUARE], [8*PIXELS_PER_SQUARE, 8*PIXELS_PER_SQUARE], [2*PIXELS_PER_SQUARE, 8*PIXELS_PER_SQUARE]])
    M = cv2.getPerspectiveTransform(pts1, pts2)

    warped_image = cv2.warpPerspective(img, M, (10*PIXELS_PER_SQUARE, 10*PIXELS_PER_SQUARE))
    warped_gray = cv2.warpPerspective(gray, M, (10*PIXELS_PER_SQUARE, 10*PIXELS_PER_SQUARE))
    warped_edges = cv2.warpPerspective(edges, M, (10*PIXELS_PER_SQUARE, 10*PIXELS_PER_SQUARE))
    return warped_image, warped_gray, warped_edges

def order_points(pts) -> list:
    rect = [0,0,0,0]

    s = list(map(sum, pts))
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def get_tiles(img) -> dict:
    tiles = {}

    for pos in [(x, y) for x in range(1,9) for y in range(1,9)]:
        t = tile_rect(img, pos)
        tiles[pos] =  np.count_nonzero(t) / max(t.size, 1)

    return tiles

def tile_rect(img, pos):
    x = pos[0] 
    y = pos[1]
    if (x < 1 or x > 8 or y < 1 or y > 8):
        return None

    pos_y = PIXELS_PER_SQUARE * y
    pos_x = PIXELS_PER_SQUARE * x 
    return img[pos_y:pos_y+PIXELS_PER_SQUARE, pos_x:pos_x+PIXELS_PER_SQUARE]

def pos_to_pixel(pos):
    x = pos[0]
    y = pos[1]

    if (x < 1 or x > 8 or y < 1 or y > 8):
        return None
    
    pos_y = PIXELS_PER_SQUARE * y
    pos_x = PIXELS_PER_SQUARE * x 
    return pos_x, pos_y

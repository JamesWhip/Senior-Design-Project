import cv2
import mediapipe as mp
import numpy as np
import Board


PIXELS_PER_SQUARE = 80
THRESHOLD = 0.08
WHITE_RATIO = 1.00
BLACK_RATIO = 1.00


def detect_pieces(img, M):
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    canny = cv2.Canny(blur,20,100,apertureSize = 3)

    kernel = np.ones((3, 3), np.uint8) 
    dilate = cv2.dilate(canny, kernel, iterations=1) 

        
    lines = cv2.HoughLinesP(dilate, 1, np.pi/180, threshold=200, minLineLength=200, maxLineGap=100)

    if lines is not None:
        for i, line in enumerate(lines):
            x1, y1, x2, y2 = line[0]
            
            # draw lines black to remove them
            cv2.line(dilate, (x1, y1), (x2, y2), (0,0,0), 6)

    new_m = normalize_img(img, gray, canny)
    if new_m is not None:
        M = new_m

    norm_img = warp_img(img, M)
    norm_canny = warp_img(dilate, M)
    
   # disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13))

    #filled_canny = cv2.morphologyEx(norm_canny, cv2.MORPH_CLOSE, disk)
    
    tiles = get_tiles(norm_canny)

    

    empty_tiles = []
    piece_tiles = []

    for pos in tiles.keys():
        if tiles[pos] > THRESHOLD:
            x, y = pos_to_pixel(pos)
            cv2.circle(norm_canny, (int(x+PIXELS_PER_SQUARE/2), int(y+PIXELS_PER_SQUARE/2)), PIXELS_PER_SQUARE//2, (255,0,0), 2)

            piece_tiles.append(pos)
        else:
            empty_tiles.append(pos)
    
    odd_tiles = []
    even_tiles = []
    for pos in empty_tiles:
        avg = np.mean(tile_rect(norm_img, pos))
        if sum(pos) % 2 == 0:
            even_tiles.append(avg)
        else:
            odd_tiles.append(avg)

    even_avg = np.mean(even_tiles)
    odd_avg = np.mean(odd_tiles)

    t = 0
    if even_avg > odd_avg:
        white_avg = even_avg * WHITE_RATIO
        black_avg = odd_avg * BLACK_RATIO
    else:
        white_avg = odd_avg * WHITE_RATIO
        black_avg = even_avg * BLACK_RATIO
        t = 1

    ## comparing gray values not working because white piece on white square is darker than a white square, maybe just get center of image and 50/50 it
    board = Board.empty_board()
    for pos in piece_tiles:
        tile = tile_rect(norm_img, pos)
        mask = extract_piece_mask(tile, sum(pos) % 2 == t)
        board[pos[1]-1][pos[0]-1] = detect_piece_color(tile, mask)
        '''avg = np.mean(tile_rect(norm_img, pos))
        if sum(pos) % 2 == t:
            if avg > white_avg:
                board[pos[1]-1][pos[0]-1] = 'W'
            else:
                board[pos[1]-1][pos[0]-1] = 'B'
        else:
            if avg > black_avg:
                board[pos[1]-1][pos[0]-1] = 'W'
            else:
                board[pos[1]-1][pos[0]-1] = 'B' '''

    return board, norm_canny, M

def detect_piece_color(tile_img, mask):
    if mask is None:
        return None

    pixels = tile_img[mask == 255]
    if pixels.size == 0:
        return None

    lab = cv2.cvtColor(pixels.reshape(-1,1,3).astype('uint8'), cv2.COLOR_BGR2LAB)
    L = lab[:,:,0].flatten()

    mean_L = np.mean(L)

    # threshold is easy now because mask has isolated only the piece pixels
    return "W" if mean_L > 130 else "B"


import cv2
import numpy as np

def extract_piece_mask(tile_img, tile_is_white):
    """
    tile_img: BGR image of the tile
    tile_is_white: True if the board tile is white/light, False if black/dark
    Returns: mask of the piece (0/255) or None if no piece detected
    """
    gray = cv2.cvtColor(tile_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 1. Threshold based on tile color
    if tile_is_white:
        # white square → piece is darker → normal OTSU foreground
        _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        # black square → piece is brighter → invert logic
        _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 2. Clean up mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # 3. Find largest blob = piece
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    cnt = max(contours, key=cv2.contourArea)
    if cv2.contourArea(cnt) < 50:
        return None

    # final mask from contour
    final_mask = np.zeros_like(mask)
    cv2.drawContours(final_mask, [cnt], -1, 255, -1)

    return final_mask

def normalize_img(img, gray, edges):
    ret, corners = cv2.findChessboardCorners(edges, (7,7), None)

    if not ret:
        return None
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    points = [corners[0][0], corners[6][0], corners[42][0], corners[48][0]]
    
    pts1 = np.float32(order_points(points))
    pts2 = np.float32([[2*PIXELS_PER_SQUARE, 2*PIXELS_PER_SQUARE], [8*PIXELS_PER_SQUARE, 2*PIXELS_PER_SQUARE], [8*PIXELS_PER_SQUARE, 8*PIXELS_PER_SQUARE], [2*PIXELS_PER_SQUARE, 8*PIXELS_PER_SQUARE]])
    M = cv2.getPerspectiveTransform(pts1, pts2)

    return M

def warp_img(img, m):
    return cv2.warpPerspective(img, m, (10*PIXELS_PER_SQUARE, 10*PIXELS_PER_SQUARE))

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

def calibrate(cap):

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from camera. Exiting...")
            cap.release()
            cv2.destroyAllWindows()
            exit()
        
        img = cv2.flip(frame, 1)

        print("Calibrating camera")
        cv2.imshow('Calibration', img)


        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        canny = cv2.Canny(blur,90,150,apertureSize = 3)

        ret, corners = cv2.findChessboardCorners(canny, (7,7), None)

        if ret:
            break
    
    
    print("Camera succesfuly calibrated")

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    points = [corners[0][0], corners[6][0], corners[42][0], corners[48][0]]
    

    pts1 = np.float32(order_points(points))
    pts2 = np.float32([[2*PIXELS_PER_SQUARE, 2*PIXELS_PER_SQUARE], [8*PIXELS_PER_SQUARE, 2*PIXELS_PER_SQUARE], [8*PIXELS_PER_SQUARE, 8*PIXELS_PER_SQUARE], [2*PIXELS_PER_SQUARE, 8*PIXELS_PER_SQUARE]])
    M = cv2.getPerspectiveTransform(pts1, pts2)

    return M
import cv2
import mediapipe as mp
import numpy as np
import Board


PIXELS_PER_SQUARE = 80
THRESHOLD = 0.08

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

    norm_img = warp_img(gray, M)
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
    
    white_tiles = []
    black_tiles = []
    for pos in empty_tiles:
        avg = np.mean(tile_rect(norm_img, pos))
        if sum(pos) % 2 == 0:
            white_tiles.append(avg)
        else:
            black_tiles.append(avg)

    white_avg = np.mean(white_tiles)
    black_avg = np.mean(black_tiles)
    b_w_avg = (black_avg + white_avg) / 2


    ## comparing gray values not working because white piece on white square is darker than a white square, maybe just get center of image and 50/50 it
    board = Board.empty_board()
    for pos in piece_tiles:
        avg = np.mean(tile_rect(norm_img, pos))
        if sum(pos) % 2 == 0:
            if white_avg > avg:
                board[pos[1]-1][pos[0]-1] = 'W'
            else:
                board[pos[1]-1][pos[0]-1] = 'B'
        else:
            if black_avg < avg:
                board[pos[1]-1][pos[0]-1] = 'B'
            else:
                board[pos[1]-1][pos[0]-1] = 'W'

    return board, norm_canny, M

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

def get_color(img, pos):
    tile = tile_rect(img, pos)
    np.mean(tile, axis=(0,1))

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
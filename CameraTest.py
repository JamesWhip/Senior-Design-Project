import cv2
import mediapipe as mp
import numpy as np
import time
import threading

def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        exit()

    mpHands = mp.solutions.hands
    hands = mpHands.Hands(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.75,
        min_tracking_confidence=0.75,
        max_num_hands=2)


    split_img = [[None for _ in range(8)] for _ in range(8)] 

    while True:
        ret, frame = cap.read()


        if not ret:
            print("Error: Could not read frame from camera. Exiting...")
            break

        img = cv2.flip(frame, 1)

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)

        # If hands are present in image(frame)
        if results.multi_hand_landmarks:
            # Both Hands are present in image(frame)
            cv2.putText(img, 'Hand Detected', (250, 50),
                cv2.FONT_HERSHEY_COMPLEX, 0.9,
                (0, 255, 0), 2)
        # If no hands, run piece detection    
        else:
            try:
                detect_pieces(img, split_img)
            finally:
                print("piece detection failed")


        # Display the resulting frame
        cv2.imshow('Camera Feed', img)

        # Exit the loop on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


    cap.release()
    cv2.destroyAllWindows()


def detect_pieces(img, split_img):

    pattern_size = (7, 7)

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray,90,150,apertureSize = 3)
    cv2.imwrite('canny.jpg',edges)

    print("Finding corners")
    # Find the chessboard corners
    ret, corners = cv2.findChessboardCorners(edges, pattern_size, None)

    if ret:
        print("Chessboard corners found successfully.")
        # Refine the corner locations to sub-pixel accuracy
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        tile_size = int(abs(corners[0][0][0] - corners[1][0][0]))

        tiles = [[[0,0] for _ in range(8)] for _ in range(8)]

        i = 0
        for corner in corners:
            x = int(corner[0][0])
            y = int(corner[0][1])
            tiles[i//7][i%7] = [x,y]
            i += 1

        for i in range(0,7):
            x,y = tiles [6][i]
            tiles[7][i] = [x,max(y-tile_size, 0)]

        for i in range(0,8):
            x,y = tiles [i][6]
            tiles[i][7] = [max(x-tile_size, 0),y]

        for x in range(8):
            for y in range(8):
                pos_x,pos_y = tiles[x][y]
                sub_img = edges[pos_y:pos_y+tile_size, pos_x:pos_x+tile_size]
                #sub_img = cv2.Canny(sub_img, 50, 150)
                split_img[x][y] = sub_img
                cv2.imwrite( "Squares/tile_" + str(x) + "_" + str(y) + ".jpg", sub_img)

        # Draw and display the corners on the original image
        img_corners = cv2.drawChessboardCorners(img.copy(), pattern_size, corners, ret)
        cv2.imshow('Corners', img_corners)

    else:
        print("Could not find chessboard corners.")
        return

    threshold = 0.1

    for x in range(8):
        for y in range(8):
            edge_density = np.count_nonzero(split_img[x][y]) / split_img[x][y].size

            print(f"Tile:({x},{y}) Density:{edge_density}, Piece:{edge_density>=threshold}")


if __name__ == "__main__":
    main()
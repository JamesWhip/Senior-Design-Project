import cv2
import mediapipe as mp
import PieceDetection as pd
import Board
import time

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

    M = pd.calibrate(cap)

    board = Board.Board()

    while True:
        keypress = cv2.waitKey(1) & 0xFF
        if keypress == ord('q'):
            break

        if keypress == ord(' '):
            board.set_board(Board.new_board())

        if keypress == ord('<'):
            pd.THRESHOLD -= 0.01
            print(f"Threshold: {pd.THRESHOLD}")
        if keypress == ord('>'):
            pd.THRESHOLD += 0.01
            print(f"Threshold: {pd.THRESHOLD}")

        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from camera. Exiting...")
            break

        raw_img = cv2.flip(frame, 1)
        raw_img = cv2.rotate(raw_img, cv2.ROTATE_90_CLOCKWISE)

        imgRGB = cv2.cvtColor(raw_img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)
        

        # If hands are present in image(frame)
        if results.multi_hand_landmarks:
            # Both Hands are present in image(frame)
            cv2.putText(raw_img, 'Hand Detected', (250, 50),
                cv2.FONT_HERSHEY_COMPLEX, 0.9,
                (0, 255, 0), 2)
            
            cv2.imshow('Raw Camera Feed', raw_img)
            continue
        
        new_board, processed_img, M = pd.detect_pieces(raw_img, M)

        print(new_board)

        if (board.validate_board_change(new_board)):
            print("Valid Move!")

        cv2.imshow('Raw Camera Feed', raw_img)
        cv2.imshow('Camera Feed', processed_img)

        time.sleep(0.1)

        
        

    cap.release()
    cv2.destroyAllWindows()
    

if __name__ == "__main__":
    main()
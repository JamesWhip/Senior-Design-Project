import cv2
import mediapipe as mp
import PieceDetection as pd
import chess

def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        exit()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from camera. Exiting...")
            break

        img = cv2.flip(frame, 1)

        img = pd.detect_pieces(img)

        cv2.imshow('Camera Feed', img)

        # Exit the loop on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    

if __name__ == "__main__":
    main()
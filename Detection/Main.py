import cv2
import mediapipe as mp
import PieceDetection as pd
import chess

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

    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

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
            
            cv2.imshow('Raw Camera Feed', img)
            continue
        
        
        cv2.imshow('Raw Camera Feed', img)

        img, M = pd.detect_pieces(img, M)

        cv2.imshow('Camera Feed', img)

        # Exit the loop on pressing 'q'
        

    cap.release()
    cv2.destroyAllWindows()
    

if __name__ == "__main__":
    main()
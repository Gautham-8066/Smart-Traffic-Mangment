import numpy as np
import time
import cv2
import RPi.GPIO as GPIO

# ==========================================
# HARDWARE SETUP
# ==========================================
GPIO.setmode(GPIO.BCM)
# Pins: 23 (Vert Green), 25 (Horiz Green), 16 (Vert Red), 21 (Horiz Red)
for i in (23, 25, 16, 21):
    GPIO.setup(i, GPIO.OUT)

# ==========================================
# CAMERA SETUP (FIXED FOR RASPBERRY PI 5)
# ==========================================
cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
cam.set(3, 640) 
cam.set(4, 480) 
cam.set(5, 30)  

time.sleep(0.5)

# ==========================================
# VISION SETTINGS (FIXED FOR YELLOW)
# ==========================================
colorLower = np.array([20, 100, 100])  
colorUpper = np.array([40, 255, 255]) 

initvert = 0
inithoriz = 0
xur, yur, xul, yul = 0, 0, 0, 0
xdr, ydr, xdl, ydl = 0, 0, 0, 0

t = 0
t1 = time.time()

# ==========================================
# PHASE 1: 5-SECOND CALIBRATION
# ==========================================
print("Starting Calibration (5 Seconds)... Place YELLOW markers at road corners.")

while t < 5 and cam.isOpened():
    ret, frame = cam.read()
    if not ret: 
        time.sleep(0.1)
        continue
    
    frame = cv2.resize(frame, (480, 480))
    frame = np.array(frame)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, colorLower, colorUpper)   
    
    mask = cv2.blur(mask, (3, 3))   
    mask = cv2.dilate(mask, None, iterations=10)
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=5)
    
    me, thresh = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[-2]
    
    if len(cnts) > 0:
        for c in cnts:
            (x, y), radius = cv2.minEnclosingCircle(c)
            center = (int(x), int(y))
            cv2.circle(frame, center, int(radius), (0, 255, 0), 2)
            
            x, y = int(x), int(y)
            if x > 240: 
                if y > 240: xur, yur = x, y 
                if y < 240: xdr, ydr = x, y 
            if x < 240: 
                if y > 240: xul, yul = x, y 
                if y < 240: xdl, ydl = x, y 

    cv2.imshow("Calibration", frame)
    t = time.time() - t1
    if cv2.waitKey(1) & 0xFF == ord('q'): break

# --- CALIBRATION FAILSAFE ---
if xur == 0 or xdr == 0 or xul == 0 or xdl == 0:
    print("WARNING: Incomplete calibration! Using safe default center-lane boundaries.")
    xur, yur = 360, 360  
    xdr, ydr = 360, 120  
    xul, yul = 120, 360  
    xdl, ydl = 120, 120  
# ----------------------------------------

print(f"Calibration Done -> UR:{xur},{yur} | DR:{xdr},{ydr} | UL:{xul},{yul} | DL:{xdl},{ydl}")
print("Remove calibration objects. System starting in 5 seconds...")
cv2.destroyAllWindows() 
time.sleep(5)

# ==========================================
# PHASE 2: MAIN TRAFFIC LOGIC
# ==========================================

last_switch_time = time.time()
current_green_lane = "VERTICAL"
NORMAL_DELAY = 10  

while(cam.isOpened()):
    ret, frame = cam.read()
    if not ret: 
        time.sleep(0.01)
        continue
    
    frame = cv2.resize(frame, (480, 480))
    frame = np.array(frame)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, colorLower, colorUpper)   
    maskhsv = cv2.resize(mask, (250, 250))
    
    mask = cv2.blur(mask, (3, 3))   
    mask1 = cv2.resize(mask, (250, 250))
    mask = cv2.dilate(mask, None, iterations=10)
    mask2 = cv2.resize(mask, (250, 250))
    mask = cv2.erode(mask, None, iterations=1)
    mask3 = cv2.resize(mask, (250, 250))
    mask = cv2.dilate(mask, None, iterations=5)
    mask4 = cv2.resize(mask, (250, 250))
    
    imstack = np.hstack((maskhsv, mask1, mask2, mask3, mask4))
    cv2.imshow("masks", imstack)
    
    me, thresh = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    cv2.imshow("thresh", thresh)

    cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[-2]

    vert = 0
    horiz = 0 
    priority = 0
    
    if len(cnts) > 0:
        # Check for Priority Vehicle (Large Area)
        for c in cnts:
            rect = cv2.minAreaRect(c)
            (x, y), (width, height), angle = rect
            Area = width * height
            if Area > 16000:
                priority = 1
        
        # Analyze each object detected
        for c in cnts:
            rect = cv2.minAreaRect(c)
            box = cv2.boxPoints(rect) 
            box = np.int32(box)
            (x, y), (width, height), angle = rect
            Area = width * height
            x, y = int(x), int(y)

            # --- ALWAYS DRAW BOXES ---
            # If the object is bigger than 500 pixels (ignoring speckles of dust), draw it!
            if Area > 500:
                if Area > 16000:
                    cv2.drawContours(frame, [box], 0, (0, 0, 255), 3) # Red box for Priority
                else:
                    cv2.drawContours(frame, [box], 0, (0, 255, 0), 2) # Green box for Normal

            # PRIORITY LOGIC
            if priority == 1 and Area > 16000:
                if xul < x < xur: 
                    GPIO.output(21, GPIO.HIGH); GPIO.output(23, GPIO.HIGH) 
                    GPIO.output(25, GPIO.LOW);  GPIO.output(16, GPIO.LOW)
                    print("PRIORITY OVERRIDE: VERTICAL LANE")
                    current_green_lane = "VERTICAL"
                    last_switch_time = time.time()
                    
                elif ydr < y < yur: 
                    GPIO.output(25, GPIO.HIGH); GPIO.output(16, GPIO.HIGH) 
                    GPIO.output(21, GPIO.LOW);  GPIO.output(23, GPIO.LOW)
                    print("PRIORITY OVERRIDE: HORIZONTAL LANE")
                    current_green_lane = "HORIZONTAL"
                    last_switch_time = time.time()
            
            # NORMAL DENSITY COUNTING
            elif priority == 0 and Area > 500: # Only count objects that are actually car-sized
                if xul < x < xur: 
                    if y > yur or y < ydr:
                        vert += 1
                if ydr < y < yur: 
                    if x > xur or x < xul:
                        horiz += 1

        # Print terminal updates only when the count changes
        if priority == 0 and (vert != initvert or horiz != inithoriz):
            print(f"Cars - Vertical: {vert} | Horizontal: {horiz}")
            initvert = vert
            inithoriz = horiz

        # APPLY DENSITY SWITCHING
        if priority == 0 and (vert > 0 or horiz > 0):
            last_switch_time = time.time() 
            
            if vert < horiz:
                GPIO.output(25, GPIO.HIGH); GPIO.output(16, GPIO.HIGH) 
                GPIO.output(21, GPIO.LOW);  GPIO.output(23, GPIO.LOW)
                current_green_lane = "HORIZONTAL"
            elif horiz < vert:
                GPIO.output(21, GPIO.HIGH); GPIO.output(23, GPIO.HIGH) 
                GPIO.output(25, GPIO.LOW);  GPIO.output(16, GPIO.LOW)
                current_green_lane = "VERTICAL"

    # ==========================================
    # TIMED NORMAL MODE (When Intersection is Empty)
    # ==========================================
    if priority == 0 and vert == 0 and horiz == 0:
        current_time = time.time()
        
        if (current_time - last_switch_time) > NORMAL_DELAY:
            if current_green_lane == "VERTICAL":
                current_green_lane = "HORIZONTAL"
                print(f"EMPTY ROAD: Switching to Horizontal Green ({NORMAL_DELAY}s elapsed)")
            else:
                current_green_lane = "VERTICAL"
                print(f"EMPTY ROAD: Switching to Vertical Green ({NORMAL_DELAY}s elapsed)")
                
            last_switch_time = current_time 
            
        if current_green_lane == "HORIZONTAL":
            GPIO.output(25, GPIO.HIGH); GPIO.output(16, GPIO.HIGH) 
            GPIO.output(21, GPIO.LOW);  GPIO.output(23, GPIO.LOW)
        else:
            GPIO.output(21, GPIO.HIGH); GPIO.output(23, GPIO.HIGH) 
            GPIO.output(25, GPIO.LOW);  GPIO.output(16, GPIO.LOW)

    # ==========================================
    # VIDEO OUTPUT
    # ==========================================
    hsvim = cv2.resize(hsv, (500, 500))
    frameim = cv2.resize(frame, (500, 500))
    imstack2 = np.hstack((hsvim, frameim))
    cv2.imshow("Frame + hsv", imstack2)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Cleanup ---
cam.release()
cv2.destroyAllWindows()
GPIO.cleanup()

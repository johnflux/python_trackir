#!/usr/bin/env python3

from trackir import TrackIRDLL, TrackIR_6DOF_Data, logprint
import time
import signal
import sys
import tkinter

def main():

    app = tkinter.Tk()
    app.title("TrackIR Log to CSV")
    app.update_idletasks()
    app.update()
    tkinter.Label(app, text="Running, and outputting values to the console.  Close to stop").grid(column=0,row=0)

    try:
        trackrIr = TrackIRDLL(app.wm_frame())
    except Exception as e:
        logprint("Crash!\n  (This usually means you need to restart the trackir gui)\n")
        raise e

    previous_frame = -1

    print("timestamp ms, framenum, roll, pitch, yaw, x, y, z")

    num_logged_frames = 0
    num_missed_frames = 0
    start_time = time.time()

    def signal_handler(sig, frame):
        trackrIr.stop()
        logprint("num_logged_frames:", num_logged_frames)
        logprint("num_missed_frames:", num_missed_frames)
        end_time = time.time()
        logprint("Total time:", round(end_time - start_time), "s")
        logprint("Rate:", round(num_logged_frames / (end_time - start_time)), "hz")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    
    while(True):
        data = trackrIr.NP_GetData()
        if data.frame != previous_frame:
            num_logged_frames += 1
            if previous_frame != -1:
                num_missed_frames += data.frame - previous_frame - 1
            previous_frame = data.frame
            time_ms = round((time.time() - start_time)*1000)
            print(time_ms, ',', data.frame, ',', round(data.roll, 1), ',', round(data.pitch, 1), ',', round(data.yaw, 1), ',', round(data.x, 1), ',', round(data.y, 1), ',', round(data.z, 1))
            #logprint(data)
        try:
            app.update_idletasks()
            app.update()
        except Exception:
            signal_handler(0,0)
        time.sleep(1/240.0) # Sample at ~240hz, for the ~120hz signal

if __name__ == "__main__":
    main()

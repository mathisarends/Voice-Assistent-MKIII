"""
Module for handling audio playback in a non-blocking manner.
"""
import threading
import logging
import numpy as np
import sounddevice as sd

# Audio configuration
SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_LENGTH_S = 0.05  # 50ms

class AudioPlayerAsync:
    """
    Asynchronous audio player that handles playback of audio buffers in a
    non-blocking manner.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queue = []
        self.lock = threading.Lock()
        
        # Create an output stream for playing audio
        self.stream = sd.OutputStream(
            callback=self.callback,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.int16,
            blocksize=int(CHUNK_LENGTH_S * SAMPLE_RATE),
        )
        
        self.playing = False
        self._frame_count = 0
    
    def callback(self, outdata, frames, time, status):
        """
        Callback function for the sound device output stream.
        This is called by the audio device when it needs more audio data.
        
        Args:
            outdata: Buffer to fill with audio data
            frames: Number of frames to fill
            time: Timing information (unused)
            status: Status of the stream (unused)
        """
        with self.lock:
            data = np.empty(0, dtype=np.int16)
            
            # Get audio data from the queue
            while len(data) < frames and len(self.queue) > 0:
                item = self.queue.pop(0)
                frames_needed = frames - len(data)
                data = np.concatenate((data, item[:frames_needed]))
                
                # If we didn't use all of the item, put the rest back in the queue
                if len(item) > frames_needed:
                    self.queue.insert(0, item[frames_needed:])
            
            self._frame_count += len(data)
            
            # Fill the rest with silence if we don't have enough data
            if len(data) < frames:
                data = np.concatenate((data, np.zeros(frames - len(data), dtype=np.int16)))
        
        # Copy our data to the output buffer
        outdata[:] = data.reshape(-1, 1)
    
    def reset_frame_count(self):
        """Reset the frame counter to start a new audio sequence."""
        self._frame_count = 0
    
    def get_frame_count(self):
        """Get the current frame count."""
        return self._frame_count
    
    def add_data(self, data: bytes):
        """
        Add audio data to the playback queue.
        
        Args:
            data: Audio data as bytes (PCM16 format)
        """
        with self.lock:
            # Convert bytes to numpy array
            np_data = np.frombuffer(data, dtype=np.int16)
            self.queue.append(np_data)
            
            # Start playback if not already playing
            if not self.playing:
                self.start()
    
    def start(self):
        """Start audio playback."""
        if not self.playing:
            self.playing = True
            self.stream.start()
            self.logger.debug("Audio playback started")
    
    def stop(self):
        """Stop audio playback and clear the queue."""
        if self.playing:
            self.playing = False
            self.stream.stop()
            with self.lock:
                self.queue = []
            self.logger.debug("Audio playback stopped")
    
    def terminate(self):
        """Clean up resources."""
        self.stop()
        self.stream.close()
        self.logger.debug("Audio player terminated")
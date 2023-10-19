import os
import time
from threading import Thread
import http.client
import json
import pyperclip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import src.ffmpeg as ffmpeg

os.chdir(os.path.dirname(os.path.abspath(__file__)))

running = set()

class MonitorFolder(FileSystemEventHandler):
    def on_created(self, event):
        global running

        if event.is_directory:
            return

        # ensure file is a video file (.mp4, .mkv, etc)
        # get file extension
        ext = event.src_path.split('.')[-1]
        if ext not in ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'mpg', 'mpeg']:
            return

        print("New video detected, starting encoding process...")

        # encode and upload to e-z.host in a new thread
        job = Thread(target=encode_and_upload, args=[event.src_path])
        job.start()
        running.add(job)

def encode_and_upload(filepath):
    global target_size, output_dir, ez_host_key

    # use ffmpeg two-pass encoding to convert to a webm that is less than the target size
    # calculate bitrate of new video
    # bitrate = (bits) / (time in seconds)
    new_bitrate = int(target_size) / ffmpeg.get_length(filepath)
    ffmpeg.two_pass_encode(filepath, new_bitrate, output_dir + '\\' + filepath.split('\\')[-1].split('.')[0] + '.webm')

    # upload to e-z.host
    video_data = open(output_dir + '\\' + filepath.split('\\')[-1].split('.')[0] + '.webm', 'rb').read()

    conn = http.client.HTTPSConnection("api.e-z.host")

    form_data_boundary = '---data-boundary-' + str(time.time())
    headers = {
        'Content-Type': 'multipart/form-data; boundary=' + form_data_boundary,
        'key': ez_host_key
    }

    body = '--' + form_data_boundary + '\r\n'
    body += 'Content-Disposition: form-data; name="file"; filename="' + filepath.split('\\')[-1] + '"\r\n'
    body += 'Content-Type: video/webm\r\n\r\n'
    body += video_data.decode('iso-8859-1') + '\r\n'
    body += '--' + form_data_boundary + '--\r\n'

    conn.request("POST", "/files", body, headers)

    print("Uploaded " + filepath.split('\\')[-1] + " to e-z.host")

    # copy link to clipboard
    response = conn.getresponse().read().decode('utf-8')
    link = json.JSONDecoder().decode(response)['imageUrl']
    pyperclip.copy(link)

# read config file for:
# file with paths to watch
# target size of videos
# output directory
# e-z.host key
config_file = open('config.txt', 'r')
paths_file = config_file.readline().strip()
target_size = config_file.readline().strip()
output_dir = config_file.readline().strip()
ez_host_key = config_file.readline().strip()
config_file.close()

# create observer and watch every directory in paths_file
observer = Observer()
observables = []
with open(paths_file, 'r') as f:
    for path in f.readlines():
        observable = observer.schedule(MonitorFolder(), path.strip(), recursive=True)
        observables.append(observable)
observer.start()

try: 
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('Exiting...')
    observer.unschedule_all()
    observer.stop()
    for j in running:
        if j.is_alive():
            print('Waiting for job to finish...')
            j.join()

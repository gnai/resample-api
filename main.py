from tempfile import NamedTemporaryFile
from fastapi import FastAPI, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path
from pydub.utils import mediainfo
import shutil
import ffmpeg
import os
#import time # used for concurrency testing

# Utils
working_dir = Path().resolve()
app = FastAPI()

# Background tasks
def remove_resampled(file: str):
    os.remove(file) 

# Upload and resample audio file
@app.post("/resample/")
def upload_resample(uploaded_file: UploadFile):

    original_file = uploaded_file.filename

    ### Check concurrency when multiple simultaneous clients requests submitted
    print('{} uploaded.'.format(original_file)) 
    #time.sleep(5)
    
    try:
        
       # Save uploaded file as temp file
       with NamedTemporaryFile(delete=False) as tmp:
           shutil.copyfileobj(uploaded_file.file, tmp)
           tmp_path = Path(tmp.name)
           print('{} saved.'.format(original_file)) # concurrency testing
            
           # Extract original audio sample rate and format
           original_audio_info = mediainfo(tmp_path)
           original_audio_sample_rate = int(int(original_audio_info['sample_rate']) / 1000)
           original_audio_format = original_audio_info['format_name']
           
           # Check if audio already in required format
           if original_audio_sample_rate == 32 and original_audio_format == 'mp3':
               return {'original_file': original_file, 'resampled_server_file_path': 'N/A', 'original_audio_sample_rate': original_audio_sample_rate,
                       'original_audio_format': original_audio_format}
           else:
               temp_filename = os.path.basename(tmp_path) # temp name used just in case to help easily differentiate file saved on server from client download
                       
               # Resample file and save to working dir with temp file name
               stream = ffmpeg.input(tmp_path)
               audio = stream.audio                       
               output_file_path = os.path.join(working_dir, temp_filename + ".mp3") # Downloads to project folder
               stream = ffmpeg.output(audio, output_file_path, **{'ar': '32000','acodec': 'mp3', 'b:a': '320k'})
               ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
               print('{} resampled.'.format(original_file)) # concurrency testing
            
               # Extract resampled audio sample rate and format
               resampled_audio_info = mediainfo(output_file_path)
               resampled_audio_sample_rate = int(int(resampled_audio_info['sample_rate']) / 1000)
               resampled_audio_format = resampled_audio_info['format_name']           
         
               return {'original_file': original_file, 'resampled_server_file_path': output_file_path,
                       'resampled_audio_sample_rate': resampled_audio_sample_rate, 'resampled_audio_format': resampled_audio_format}                   
    finally:
        # Delete temp file
        tmp_path.unlink()

# Client download
@app.get("/resample/", response_class=FileResponse)
def client_download(file_path: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(remove_resampled, file_path) # delete resampled file from server after download
    return file_path # returns stream

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.1.1', port=5000)
    print("running")
import uuid
import io
import os

from fastapi import FastAPI, File, UploadFile, HTTPException
from google.cloud import storage, speech
from google.api_core.exceptions import GoogleAPIError
from pydub import AudioSegment

# Path to your service account JSON
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "accounts_key.json"

app = FastAPI()

# Your GCS bucket
BUCKET_NAME = "valence_pharma_audios"

# Initialize GCS & Speech clients once
storage_client = storage.Client()
speech_client = speech.SpeechClient()

def upload_buffer_to_gcs(bucket_name: str, buffer: io.BytesIO, destination_blob_name: str, content_type: str) -> str:
    """
    Upload an in-memory buffer to GCS, return the gs:// URI.
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    # rewind buffer and stream into GCS
    buffer.seek(0)
    blob.upload_from_file(buffer, content_type=content_type)  # stream upload :contentReference[oaicite:3]{index=3}
    return f"gs://{bucket_name}/{destination_blob_name}"

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 1. Load upload into pydub and normalize
    try:
        # Read incoming file into AudioSegment
        audio_seg = AudioSegment.from_file(file.file)  # auto-detect format :contentReference[oaicite:4]{index=4}
        # Force mono, 16-bit samples, and 16 kHz
        audio_seg = (
            audio_seg
            .set_channels(1)
            .set_sample_width(2)       # 2 bytes = 16 bits :contentReference[oaicite:5]{index=5}
            .set_frame_rate(16000)     # resample to 16 kHz :contentReference[oaicite:6]{index=6}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Audio processing failed: {e}")

    # 2. Export to in-memory WAV
    wav_buffer = io.BytesIO()
    audio_seg.export(wav_buffer, format="wav")  # writes header with 16 kHz, mono, 16-bit :contentReference[oaicite:7]{index=7}

    # 3. Upload processed WAV buffer to GCS
    blob_name = f"{uuid.uuid4().hex}_{file.filename.rsplit('.',1)[0]}.wav"
    try:
        gcs_uri = upload_buffer_to_gcs(
            bucket_name=BUCKET_NAME,
            buffer=wav_buffer,
            destination_blob_name=blob_name,
            content_type="audio/wav"
        )
    except GoogleAPIError as e:
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}")

    # 4. Configure and call Speech-to-Text
    recognition_audio = speech.RecognitionAudio(uri=gcs_uri)
    recognition_config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,          # must match buffer header :contentReference[oaicite:8]{index=8}
        language_code="hi-IN",            # Hindi (India)
        audio_channel_count=1,
    )

    try:
        operation = speech_client.long_running_recognize(
            config=recognition_config,
            audio=recognition_audio
        )
        response = operation.result(timeout=120)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech-to-Text failed: {e}")

    # 5. Collect transcript
    transcript = "\n".join(r.alternatives[0].transcript for r in response.results)
    return {"transcript": transcript}


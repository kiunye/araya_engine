import uuid
import logging
from pathlib import Path
from typing import Optional

from araya.ingestor.models import ResearchObject, SourceType
from araya.core.config import settings

logger = logging.getLogger(__name__)


class AudioIngestor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or (settings.DEEPGRAM_API_KEY if hasattr(settings, 'DEEPGRAM_API_KEY') else None)
        self._deepgram_available = False
        try:
            from deepgram import DeepgramClient
            self._deepgram_available = True
            self._client_cls = DeepgramClient
        except ImportError:
            logger.info("Deepgram SDK not installed. Audio ingestion will be unavailable.")

    def ingest(self, file_path: str, metadata: Optional[dict] = None) -> ResearchObject:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self._deepgram_available or not self.api_key:
            raise ValueError(
                "Audio ingestion requires the deepgram-sdk package and a DEEPGRAM_API_KEY. "
                "Install with: pip install araya-research-engine[ingest-audio]"
            )

        from deepgram import PrerecordedOptions, FileSource

        client = self._client_cls(self.api_key)

        with open(file_path, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {"buffer": buffer_data}

        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            diarize=True,
            utterances=True,
            punctuate=True,
        )

        response = client.listen.prerecorded.v("1").transcribe_file(payload, options)

        transcript = []
        try:
            if hasattr(response.results, 'channels') and response.results.channels:
                channel = response.results.channels[0]
                if hasattr(channel, 'alternatives') and channel.alternatives:
                    alternative = channel.alternatives[0]
                    if hasattr(alternative, 'paragraphs') and alternative.paragraphs:
                        for para in alternative.paragraphs.paragraphs:
                            for sent in para.sentences:
                                speaker = para.speaker if hasattr(para, 'speaker') else "Unknown"
                                transcript.append(f"Speaker {speaker}: {sent.text}")
                    else:
                        transcript.append(alternative.transcript)
        except Exception as e:
            logger.error(f"Error parsing Deepgram response: {e}")
            transcript.append(str(response))

        content = "\n".join(transcript)

        obj_metadata = {
            "filename": path.name,
            "duration": response.metadata.duration if hasattr(response, 'metadata') else None,
        }
        if metadata:
            obj_metadata.update(metadata)

        return ResearchObject(
            id=str(uuid.uuid4()),
            source_type=SourceType.AUDIO,
            content=content,
            metadata=obj_metadata,
            elements=[]
        )

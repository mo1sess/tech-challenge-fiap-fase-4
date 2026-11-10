
import azure.cognitiveservices.speech as speechsdk

from app.core.config import get_settings

settings = get_settings()

if not settings.azure_speech_key or not settings.azure_speech_region:
    raise RuntimeError("Configure AZURE_SPEECH_KEY e AZURE_SPEECH_REGION no .env")

speech_config = speechsdk.SpeechConfig(
    subscription=settings.azure_speech_key,
    region=settings.azure_speech_region,
)

speech_config.speech_recognition_language = "pt-BR"

audio_config = speechsdk.audio.AudioConfig(
    use_default_microphone=True
)

recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config,
    audio_config=audio_config,
)

print("Fale uma frase em português no microfone...")

result = recognizer.recognize_once_async().get()

if result.reason == speechsdk.ResultReason.RecognizedSpeech:
    print("Transcrição:", result.text)

elif result.reason == speechsdk.ResultReason.NoMatch:
    print("Nenhuma fala foi reconhecida.")

elif result.reason == speechsdk.ResultReason.Canceled:
    details = result.cancellation_details
    print("Erro:", details.reason)
    print("Detalhes:", details.error_details)

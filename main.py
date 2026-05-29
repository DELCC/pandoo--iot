import cv2
from pyzbar.pyzbar import decode
from picamera2 import Picamera2
import time
from gtts import gTTS
import os
import uuid
import signal
import sys
import requests
from PIL import Image
import numpy as np

API_BASE_URL = "http://10.0.16.15:8000"

def text_to_speech(texte: str) -> None:
    id_unique = uuid.uuid4().hex
    tts = gTTS(text=texte, lang="fr")
    tts.save(f'/tmp/{id_unique}.mp3')
    os.system(f'mpg123 /tmp/{id_unique}.mp3')


class BarcodeScanner:
    CAPTURE_SIZE = (1280, 720)
    SCAN_INTERVAL = 0.05
    DEBOUNCE_DELAY = 2.0
    WARMUP_DELAY = 2.0

    def __init__(self):
        self.picam2 = None
        self.last_code: bytes | None = None
        self.last_detected_time: float = 0.0
        self._running = False

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def start(self) -> None:
        self.picam2 = Picamera2()

        config = self.picam2.create_preview_configuration(
            main={"size": self.CAPTURE_SIZE, "format": "RGB888"},
            controls={
                "FrameDurationLimits": (33333, 100000),
                "AfMode": 2,
                "AeEnable": True,
                "AwbEnable": True,
            },
        )
        self.picam2.configure(config)
        self.picam2.start()

        text_to_speech("Caméra démarrée")
        time.sleep(self.WARMUP_DELAY)

    def stop(self) -> None:
        self._running = False
        if self.picam2 is not None:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
            text_to_speech("Caméra arrêtée")

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

    def scan_loop(self) -> None:
        self._running = True
        try:
            while self._running:
                frame = self.picam2.capture_array()
                self._process_frame(frame)
                time.sleep(self.SCAN_INTERVAL)
        finally:
            self.stop()

    # ------------------------------------------------------------------
    # Traitement d'une frame
    # ------------------------------------------------------------------

    def _process_frame(self, frame: np.ndarray) -> None:
        codes = decode(frame)

        now = time.monotonic()
        for code in codes:
            raw: bytes = code.data
            elapsed = now - self.last_detected_time

            if raw == self.last_code and elapsed < self.DEBOUNCE_DELAY:
                continue

            text = raw.decode("utf-8", errors="replace")
            kind = code.type

            print(f"[{kind}] {text}")
            text_to_speech(f"Code détecté")

            self.last_code = raw
            self.last_detected_time = now

            # ✅ Appel API à l'intérieur de la boucle, après le debounce
            try:
                print(text)
                print(API_BASE_URL)
                print(text)
                response = requests.post(
                            f"{API_BASE_URL}/products/scan",
                            params={"barcode": text}
                )
                response.raise_for_status()
                product = response.json()
                print(f"Produit trouvé : {product}")
                text_to_speech(f"Produit : {product['name']}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"Produit non trouvé pour le code : {text}")
                elif e.response.status_code == 503:
                    print("API Open Food Facts indisponible")
            except requests.exceptions.ConnectionError:
                print("Impossible de joindre le serveur FastAPI")

    # ------------------------------------------------------------------
    # Gestion des signaux
    # ------------------------------------------------------------------

    def _handle_signal(self, signum, frame) -> None:
        print("\nArrêt demandé…")
        self.stop()
        sys.exit(0)


# ----------------------------------------------------------------------
# Point d'entrée
# ----------------------------------------------------------------------

def main() -> None:
    scanner = BarcodeScanner()
    try:
        scanner.start()
        scanner.scan_loop()
    except Exception as exc:
        print(f"Erreur fatale : {exc}")
        scanner.stop()
        raise


if __name__ == "__main__":
    main()
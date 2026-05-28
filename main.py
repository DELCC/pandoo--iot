import cv2
from pyzbar.pyzbar import decode
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import os


def create_barcode_pdf(code_value, output_pdf="barcode.pdf"):
    image_file = "barcode_temp"

    barcode = Code128(code_value, writer=ImageWriter())
    barcode_path = barcode.save(image_file)

    c = canvas.Canvas(output_pdf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 40 * mm, "Code-barres")

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 55 * mm, code_value)

    c.drawImage(
        barcode_path,
        40 * mm,
        height - 110 * mm,
        width=130 * mm,
        height=40 * mm,
        preserveAspectRatio=True
    )

    c.save()

    os.remove(barcode_path)
    print(f"PDF créé : {output_pdf}")


def scan_barcode():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Erreur : webcam non détectée.")
        return None

    print("Présente un code-barres devant la webcam.")
    print("Appuie sur Q pour quitter.")

    detected_code = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        codes = decode(frame)

        for code in codes:
            detected_code = code.data.decode("utf-8")
            code_type = code.type

            print(f"Code détecté : {detected_code}")
            print(f"Type : {code_type}")

            x, y, w, h = code.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cap.release()
            cv2.destroyAllWindows()
            return detected_code

        cv2.imshow("Scanner code-barres", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return None


if __name__ == "__main__":
    print("début")
    code = scan_barcode()

    if code:
        create_barcode_pdf(code, "code_barres.pdf")
    else:
        print("Aucun code-barres détecté.")
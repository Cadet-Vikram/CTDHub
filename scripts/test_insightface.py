import cv2
from pathlib import Path

import insightface


def main() -> None:
    image_path = Path("any_photo.jpg")
    if not image_path.exists():
        raise FileNotFoundError(f"Missing test image: {image_path}")

    app = insightface.app.FaceAnalysis(providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1)

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    faces = app.get(img)
    print(f"Found {len(faces)} face(s)")
    if faces:
        print(f"Embedding shape: {faces[0].embedding.shape}")


if __name__ == "__main__":
    main()

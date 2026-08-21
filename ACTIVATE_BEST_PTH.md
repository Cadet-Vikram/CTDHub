# How to Use Your Trained best.pth

You trained ArcFace on Colab and got best.pth. Here is exactly what to do with it.

---

## What best.pth is

It is your trained ArcFace face recognition model — 512-dimensional face embeddings
trained specifically on your dataset. It replaces the DeepFace default weights with
your custom-trained weights for potentially better accuracy.

## What the epoch_XXXX.pth files are

Just intermediate checkpoints saved every 5 epochs during training.
You only need best.pth — it is the checkpoint with the lowest validation loss.
You can delete the epoch files or leave them in Google Drive.

---

## Step 1 — Download best.pth from Google Drive

Open Colab and run:
```python
from google.colab import files
files.download('/content/drive/MyDrive/connecting_the_dots/arcface/best.pth')
```

Or just open Google Drive → MyDrive → connecting_the_dots → arcface → download best.pth

---

## Step 2 — Put it in your project

Create the folder and copy the file:

Windows:
```
mkdir connecting-the-dots\backend\checkpoints
copy best.pth connecting-the-dots\backend\checkpoints\arcface_custom.pth
```

---

## Step 3 — Update face_model.py

Open `backend/models/face_model.py`

Find the `EmbeddingExtractor.load()` method.
Add this block as the VERY FIRST try block inside load(), before the deepface block:

```python
def load(self):
    # ── Try custom trained ArcFace first ────────────────────────────────
    try:
        import torch, sys, os
        ckpt_path = "checkpoints/arcface_custom.pth"
        if os.path.exists(ckpt_path):
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml/training"))
            from train_arcface import FaceEmbeddingNet
            ckpt = torch.load(ckpt_path, map_location="cpu")
            self._model = FaceEmbeddingNet("resnet50", 512, pretrained=False)
            self._model.load_state_dict(ckpt.get("model", ckpt))
            self._model.eval()
            self._model_type = "custom_arcface"
            self.EMBEDDING_SIZE = 512
            logger.info("  Custom ArcFace (best.pth) loaded ✅")
            return
    except Exception as e:
        logger.warning(f"  Custom ArcFace failed: {e} — trying DeepFace")

    # ── Fallback: DeepFace ArcFace ───────────────────────────────────────
    try:
        from deepface import DeepFace
        import numpy as np
        DeepFace.represent(np.zeros((224,224,3), dtype=np.uint8),
                           model_name="ArcFace", enforce_detection=False)
        self._model = "deepface"
        self.EMBEDDING_SIZE = 512
        logger.info("  DeepFace ArcFace loaded ✅")
        return
    except Exception as e:
        logger.warning(f"  DeepFace unavailable: {e} — mock mode")
        self._model = None
```

Also update the extract() method to handle custom_arcface:

```python
def extract(self, face_image: np.ndarray) -> np.ndarray:
    # Custom trained model
    if hasattr(self, '_model_type') and self._model_type == "custom_arcface":
        try:
            import torch, cv2
            img = cv2.resize(face_image, (112, 112))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            t   = torch.FloatTensor(img).permute(2,0,1).unsqueeze(0) / 127.5 - 1.0
            with torch.no_grad():
                emb = self._model(t).squeeze().numpy()
            return emb / (np.linalg.norm(emb) + 1e-10)
        except Exception as e:
            logger.warning(f"Custom model extract error: {e}")

    # DeepFace
    if self._model == "deepface":
        try:
            from deepface import DeepFace
            result = DeepFace.represent(face_image, model_name="ArcFace",
                                        enforce_detection=False, detector_backend="skip")
            emb = np.array(result[0]["embedding"], dtype=np.float32)
            return emb / (np.linalg.norm(emb) + 1e-10)
        except Exception as e:
            logger.warning(f"DeepFace error: {e}")

    # Mock fallback
    seed = int(np.sum(face_image.astype(np.float32)) % (2**31))
    v = np.random.RandomState(seed).randn(self.EMBEDDING_SIZE).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-10)
```

---

## Step 4 — Add torch to requirements.txt

Add this line to backend/requirements.txt:
```
torch==2.5.1
```

---

## Step 5 — Test locally

```
cd backend
uvicorn main:app --reload --port 8000
```

Terminal should show:
```
INFO:  Custom ArcFace (best.pth) loaded ✅
INFO:  ✅ Face model ready
```

---

## Step 6 — Deploy with best.pth on Cloud Run

The checkpoints/ folder is included in the Docker image automatically.
Just redeploy:

```
cd backend
gcloud run deploy ctd-backend --source . --region asia-south1
```

---

## Important note about embedding compatibility

If you already registered children using DeepFace embeddings (before adding best.pth),
those stored embeddings WON'T match with your custom model embeddings.
The 512-dim vectors from DeepFace ArcFace and your trained ArcFace are in different
embedding spaces.

Fix: after activating best.pth, re-register all children to regenerate embeddings.
Or clear the database: delete connecting_dots.db and restart.

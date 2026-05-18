@echo off
echo ==========================================
echo  Phase 3 ML Setup (CPU mode)
echo ==========================================

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install mtcnn tensorflow
pip install opencv-python-headless Pillow numpy
pip install scikit-learn matplotlib tqdm pyyaml

echo.
echo Done! Now run the Phase 3 steps from README_PHASE3.md
pause

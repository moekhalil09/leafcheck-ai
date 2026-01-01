# 🍅 LeafCheckAI – Tomato Disease Detection

LeafCheckAI is a desktop application that detects **tomato leaf diseases** using a deep learning model.
Users can upload a tomato leaf image and receive a disease prediction with a confidence score.
## 👥 Contributors

- **Hadj Ahmed Mohammed Khalil** – [@yourGitHub](https://github.com/yourGitHub)
- **Mohammed El Amine Hamdani ** – [@friend1]([https://github.com/friend1](https://www.researchgate.net/profile/Mohammed-El-Amine-Hamdani))



## ✨ Features

* Detects **8 tomato leaf conditions**
* Deep learning model (MobileNetV2-based)
* Simple **desktop GUI (PyQt5)**
* Confidence-based prediction
* Works offline once the model is downloaded

## 🦠 Supported Classes

* Early Blight
* Late Blight
* Leaf Mold
* Septoria Leaf Spot
* Bacterial Spot
* Mosaic Virus
* Yellow Leaf Curl Virus
* Healthy Tomato

## 🛠️ Technologies Used

* Python
* PyTorch
* PyQt5
* Pillow
* MongoDB (optional – local fallback supported)

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/leafcheck-ai.git
cd leafcheck-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the model

Place the trained model file in:

```
models/attentive_mobilenetv2_tomato.pth
```

### 4. Run the application

```bash
python main.py
```

## 📁 Project Structure

```
leafcheck-ai/
├── main.py
├── config.py
├── requirements.txt
├── models/
├── views/
├── utils/
└── data/
```

## ⚙️ Configuration

You can modify basic settings in `config.py`, such as:

* Confidence threshold
* Model path
* Image size

## 📝 Notes

* If MongoDB is not available, the app automatically uses local storage.
* GPU is optional; the application also works on CPU.

## 📜 License

This project is licensed under the **MIT License**.

---

Made for learning and plant health 🌱


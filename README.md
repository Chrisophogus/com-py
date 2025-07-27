# 🎞 Colours of Motion Generator

This project extracts frames from a video file at regular intervals, computes the average colour for each frame, and creates visualisations of the movie’s colour palette.

## 🛠 How It Works

1. Frames are extracted from a video file (default every 10 seconds).
2. Average colour is computed for each frame.
3. Visual summaries are generated in 3 styles:
   - **Horizontal bar**: Colours stacked left to right.
   - **Vertical bar**: Colours stacked top to bottom.
   - **Wave pattern**: A quarter-section radial swirl using a sine-based wave distortion.

HDR content is tone-mapped to SDR during frame extraction using `ffmpeg`.

---

## 📁 Folder Structure

<pre>
project-root/
├── frames/
│   └── Aliens (1986) - tt0090605/
│       ├── frame_0001.jpg
│       ├── ...
│       └── frame_0824.jpg
├── outputs/
│   └── Aliens (1986) - tt0090605/
│       ├── linear_output.png
│       ├── vertical_output.png
│       └── debug_output.png
├── colours_of_motion_radial_.py
├── processed_files.json
├── requirements.txt
├── .gitignore
└── README.md
</pre>

## 🛠️ Setup

### 1. Install ffmpeg (via Homebrew)

Make sure `ffmpeg` is installed on your system. If you're on macOS:

```bash
brew install ffmpeg
```

### 2. Set up a Python virtual environment

From the root of this project:
```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
```

▶️ Usage

Run the script and follow the prompts:
```bash
python colours_of_motion.py
```

You will be asked:

1.	The full path to the video file (e.g. /Volumes/Media/.../Aliens.mkv)

2.	A name to use for the output folder (e.g. Aliens (1986) - tt0090605)

If the video has already been processed, only the output visualisations will be regenerated.

## 📌 Notes

- Outputs are saved to `outputs/<foldername>/`.
- Frame data is not committed, only final images.
- Uses `ffmpeg`, `Pillow`, `OpenCV`, and `numpy`.

---

## 📂 Output Example

Below is an example of the outputs generated from:

**🎬 Aliens (1986) - Theatrical Cut**

### Wave Pattern (Quarter Debug Style)

![Wave Pattern Output](outputs/Aliens%20(1986)%20-%20tt0090605/debug_output.png)

### Horizontal Bar

![Horizontal Output](outputs/Aliens%20(1986)%20-%20tt0090605/linear_output.png)

## 🧠 Notes
•	HDR sources are tone-mapped to SDR using Hable tonemapping and BT.709 output profile

•	Frame extraction happens at 0.1 fps (~1 frame every 10 seconds)

•	Outputs are stored in /outputs/your-folder-name


## 📸 Inspired By

Project concept inspired by [The Colours of Motion](https://thecolorsofmotion.com/), visualising the emotional palette of cinema.

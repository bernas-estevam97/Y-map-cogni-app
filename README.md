# Animal Y-Maze Behaviour Tracking

A computer vision application for automatically tracking an animal navigating a **Y-shaped maze** and analysing its movement patterns throughout a recorded experiment.

The application detects the animal's position frame-by-frame, determines which arm of the maze it occupies, and generates a chronological sequence representing every transition between the three maze sections (**A**, **B**, and **C**). This provides a compact representation of exploratory behaviour that can be used for behavioural neuroscience, memory studies, and locomotion analysis.

---

## Features

- 🎥 Process recorded experimental videos.
- 🐭 Automatically detect and track the animal throughout the recording.
- 📍 Divide the Y-maze into three predefined regions:
  - **A**
  - **B**
  - **C**
- 🔄 Detect every entry into each maze arm.
- 📝 Generate a complete behavioural sequence from the beginning to the end of the experiment.
- 📊 Record transition statistics between maze arms.
- 💾 Export results for further behavioural analysis.

---

## How It Works

1. Load a video of an animal exploring a Y-maze.
2. Detect the animal in each frame.
3. Track the animal's position over time.
4. Determine which maze section (A, B, or C) contains the animal.
5. Whenever the animal enters a new section, record the transition.
6. Produce the complete exploration sequence.

Example:

```
Sequence:
ABCBCABACBCBABABC
```

This sequence indicates the chronological order in which the animal entered each arm during the experiment.

---

## Example Output

### Entry Sequence

```
ABCBCABACBCBABABC
```

### Transition Log

| Step | Entered Section |
|------|-----------------|
| 1 | A |
| 2 | B |
| 3 | C |
| 4 | B |
| 5 | C |
| 6 | A |
| ... | ... |

### Summary Statistics

- Total transitions
- Number of visits to each section
- Time spent in each section
- Transition frequencies
- Percentage occupancy per section

---

## Applications

This project is suitable for:

- Behavioural neuroscience
- Animal cognition studies
- Spatial memory experiments
- Y-maze spontaneous alternation tests
- Rodent locomotor analysis
- Automated behavioural phenotyping

---

## Project Workflow

```
Video Input
      │
      ▼
Animal Detection
      │
      ▼
Object Tracking
      │
      ▼
Region Classification
(A / B / C)
      │
      ▼
Transition Detection
      │
      ▼
Behaviour Sequence Generation
      │
      ▼
Statistics & Export
```

---

## Sequence Interpretation

Each letter represents the maze arm occupied after a successful transition.

Example:

```
ABCBCABACBCBABABC
```

can be interpreted as:

- Start in **A**
- Move to **B**
- Move to **C**
- Return to **B**
- Enter **C**
- Enter **A**
- Continue until the end of the recording

Repeated letters are not recorded unless the animal exits and re-enters the same section, ensuring that the sequence reflects meaningful transitions between maze arms.

---

## Output Files

The application can generate outputs such as:

```
results/
├── annotated_video.mp4
├── trajectory.png
├── transitions.csv
├── statistics.csv
└── sequence.txt
```

Example `sequence.txt`

```
ABCBCABACBCBABABC
```

Example `transitions.csv`

| Transition | Count |
|------------|------:|
| A → B | 8 |
| B → C | 7 |
| C → A | 5 |
| C → B | 4 |
| B → A | 3 |
| A → C | 2 |

---

## Advantages

- Fully automated analysis
- Eliminates manual scoring errors
- Reproducible behavioural measurements
- Suitable for long-duration recordings
- Easy integration into behavioural analysis pipelines

---

## Future Improvements

- Real-time tracking
- Multi-animal support
- Deep learning-based detection
- Automatic maze calibration
- Heatmap generation
- Speed and acceleration analysis
- Behavioural event detection
- Interactive graphical user interface (GUI)

---

## License

This project is intended for research and educational purposes. Feel free to modify and extend it for your own experimental workflows.


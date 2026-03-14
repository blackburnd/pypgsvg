# Animated GIF Requirements for README

This document describes the animated GIFs that need to be created to complete the README documentation update.

## Style Guidelines

The GIFs should be similar in style to those in the portfoliosite repository:
- Professional, clean appearance
- Smooth transitions
- Clear demonstration of features
- Not too fast or too slow (3-5 seconds per feature demonstration)
- Optimized file size (under 5MB each)
- Resolution: 1200x800 or similar aspect ratio

## Required GIFs

### 1. Smart Navigation & Initial View
**File name suggestion:** `initial-zoom-demo.gif`

**What to show:**
1. Loading the SVG file
2. The automatic selection of the table with the most connections
3. The automatic zoom to show all related tables
4. The highlighted relationships

**Duration:** ~5 seconds

---

### 2. Double-Click to Explore Relationships
**File name suggestion:** `double-click-navigation.gif`

**What to show:**
1. Cursor hovering over a table
2. Double-clicking the table
3. The zoom/pan animation centering on the table and its connections
4. The highlighted edges showing relationships
5. Repeat with another table for clarity

**Duration:** ~8 seconds

---

### 3. Real-Time Graphviz Settings
**File name suggestion:** `graphviz-settings-demo.gif`

**What to show:**
1. Opening the Metadata Panel
2. Expanding the Graphviz Settings section
3. Changing the rank direction (e.g., from TB to LR)
4. Clicking "Apply Settings"
5. The diagram regenerating with the new layout
6. Optionally changing node separation to show the effect

**Duration:** ~10 seconds

---

### 4. Focused ERD Generation
**File name suggestion:** `focused-erd-generation.gif`

**What to show:**
1. Clicking on several tables to select them
2. Opening the Selection Panel
3. Clicking "Generate Focused ERD" button
4. The Graphviz settings panel appearing
5. Adjusting settings (optional)
6. Clicking "Create ERD" button
7. The new focused ERD appearing in a new tab/window

**Duration:** ~10 seconds

---

### 5. Database Querying & Switching
**File name suggestion:** `database-query-switch.gif`

**What to show:**
1. Opening the Metadata Panel
2. Expanding the Database Connection section
3. Clicking "Refresh Databases" button
4. The dropdown populating with database names and table counts
5. Selecting a different database
6. Clicking "Load Database" or equivalent button
7. The new schema loading

**Duration:** ~10 seconds

---

### 6. Print-Friendly Export
**File name suggestion:** `print-friendly-export.gif`

**What to show:**
1. A complex ERD with all interactive panels visible
2. Clicking the "Print-Friendly View" button
3. The UI elements (panels) disappearing
4. The diagram resetting to show the full ERD cleanly
5. The print dialog appearing (optional)
6. The clean, professional output

**Duration:** ~6 seconds

---

## Recording Tips

1. **Use a clean test environment** with a well-structured sample database
2. **Use the `Samples/complex_schema.dump`** file from the repository
3. **Record at high resolution** (at least 1920x1080) then scale down
4. **Use smooth cursor movements** - not too fast
5. **Add subtle padding/margins** around the recording area
6. **Use consistent timing** - pause briefly between steps
7. **Test the GIF** before finalizing to ensure it loops well

## Tools Recommended

- **macOS:** Kap, LICEcap, or ScreenToGif
- **Windows:** ScreenToGif, LICEcap
- **Linux:** Peek, SimpleScreenRecorder + ffmpeg
- **Browser-based:** CloudApp, Loom (then convert to GIF)

## Conversion & Optimization

After recording, optimize GIFs:
```bash
# Using gifsicle (install via brew/apt)
gifsicle -O3 --lossy=80 input.gif -o output.gif

# Using ffmpeg for better compression
ffmpeg -i input.gif -vf "fps=15,scale=1200:-1:flags=lanczos" -c:v gif output.gif
```

## Placement in README

Once created, replace the TODO comments in README.md with:
```markdown
![Smart Navigation Demo](docs/gifs/initial-zoom-demo.gif)
```

Or use hosted images if preferred:
```markdown
![Smart Navigation Demo](https://yourimagehost.com/path/to/initial-zoom-demo.gif)
```

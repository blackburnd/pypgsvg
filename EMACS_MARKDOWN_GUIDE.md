# Emacs Markdown Preview Guide

Your Emacs is now configured with powerful markdown preview capabilities!

## ✅ What's Installed

- **glow** - Beautiful terminal markdown renderer
- **grip** - GitHub-flavored markdown server
- **pandoc** - Universal document converter
- **markdown-mode** - Enhanced Emacs markdown editing

## 🎯 Quick Start

1. **Open a markdown file in Emacs:**
   ```bash
   emacs README.md
   # or from within Emacs: C-x C-f README.md
   ```

2. **Preview the markdown:**
   - `C-c C-c g` - Preview with glow (in Emacs buffer)
   - `C-c C-c p` - Preview with glow (pager mode)
   - `C-c C-c e` - Preview in EWW (Emacs browser)
   - `C-c C-c b` - Preview in default web browser
   - `C-c C-c s` - Stop grip server

## 📝 Key Bindings Reference

### Markdown Preview
| Key Binding | Action | Description |
|-------------|--------|-------------|
| `C-c C-c g` | Glow preview | Terminal rendering in new buffer (press `q` to quit) |
| `C-c C-c p` | Glow pager | Interactive terminal pager |
| `C-c C-c e` | EWW preview | Emacs built-in browser |
| `C-c C-c b` | Browser preview | Opens in Chrome/Firefox with GitHub styling |
| `C-c C-c s` | Stop grip | Stops the grip preview server |

### General Emacs
| Key Binding | Action |
|-------------|--------|
| `C-x C-s` | Save file |
| `C-x C-c` | Quit Emacs |
| `C-c r` | Reload config |
| `C-s` | Search (swiper) |
| `C-x g` | Git status (magit) |

## 🎨 Preview Methods Explained

### 1. Glow Preview (Recommended for Terminal)
**Command:** `C-c C-c g`

- Renders markdown beautifully in terminal with colors
- Shows up in a new Emacs buffer
- Press `q` to close the preview
- Perfect for quick checks while coding

**Example:**
```
Opening README.md → C-c C-c g → Beautiful rendered view
```

### 2. Glow Pager Mode
**Command:** `C-c C-c p`

- Opens in external terminal with scrolling
- More interactive than buffer mode
- Good for longer documents

### 3. EWW Preview
**Command:** `C-c C-c e`

- Uses Emacs' built-in web browser
- Converts to HTML via pandoc
- Stays inside Emacs
- Good for checking HTML rendering

### 4. Browser Preview
**Command:** `C-c C-c b`

- Opens in your default web browser
- GitHub-flavored markdown
- Live reloading
- Best for final review before publishing

## 🔧 Customization

Your config is at: `~/.emacs.d/init.el`

### Change Key Bindings

Edit the markdown-mode key bindings section:

```elisp
(with-eval-after-load 'markdown-mode
  (define-key markdown-mode-map (kbd "C-c C-c g") 'markdown-preview-glow)
  ;; Change to your preferred keys
)
```

### Add a Theme

Uncomment one of these in your init.el:

```elisp
;; Dark theme
(use-package zenburn-theme
  :ensure t
  :config
  (load-theme 'zenburn t))

;; Or Solarized
(use-package solarized-theme
  :ensure t
  :config
  (load-theme 'solarized-dark t))
```

Then reload: `C-c r`

## 📚 Additional Features

### Visual Line Mode
- Automatically wraps long lines
- Active by default in markdown files

### Spell Checking
- Flyspell mode enabled automatically
- Highlights potential typos

### Syntax Highlighting
- Headers shown in different sizes
- Code blocks highlighted
- Links and formatting visible

## 🐛 Troubleshooting

### Preview doesn't work
```bash
# Verify tools are installed
which glow grip pandoc

# Reinstall if needed
brew install glow grip pandoc
```

### Emacs can't find the tools
Add to your `~/.emacs.d/init.el`:

```elisp
(setenv "PATH" (concat (getenv "PATH") ":/opt/homebrew/bin"))
(setq exec-path (append exec-path '("/opt/homebrew/bin")))
```

### Config not loading
```bash
# Restart Emacs or reload config
C-c r  # In Emacs
```

## 🎓 Learning Resources

### Emacs Basics
- `C-h t` - Built-in tutorial
- `C-h k <key>` - Describe key binding
- `C-h f <function>` - Describe function

### Markdown Mode
- `C-h m` - Show current mode help
- `C-c C-c` prefix shows all markdown commands

## 💡 Tips

1. **Quick Preview:** Use `C-c C-c g` for instant feedback
2. **Before Committing:** Use `C-c C-c b` to see GitHub rendering
3. **Long Documents:** Use `C-c C-c p` for better navigation
4. **Editing:** Visual-line-mode wraps text nicely
5. **Reloading:** After editing config, use `C-c r`

## 🚀 Next Steps

Try opening any markdown file:

```bash
cd /Users/danielblackburn/Documents/pypgsvg
emacs README.md

# Then press: C-c C-c g
```

Enjoy your enhanced markdown editing experience!

# Setup testing checklist

Run through this on each platform. Each section is independent — fresh clone each time.

---

## Before you start (all platforms)

```
git clone https://github.com/loxed/porypal.git
cd porypal
```

---

## Windows — PowerShell

**Prerequisites to install manually first:**
- Python 3.10+ from https://python.org — check "Add Python to PATH" during install
- Node 18+ from https://nodejs.org

**Run:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
.\venv\Scripts\Activate.ps1
python main.py
```

**Verify:**
- [ ] Setup prints `+ Python 3.x` (not an error)
- [ ] Setup prints `+ Node vXX`
- [ ] `npm install` and `npm run build` complete without errors
- [ ] `frontend/dist/` folder exists after setup
- [ ] `python main.py` starts and prints the URL
- [ ] Browser opens automatically at http://127.0.0.1:7860
- [ ] All 7 tabs load without console errors

---

## WSL (Ubuntu inside Windows)

**Prerequisites — run these before setup if needed:**
```bash
# Python
sudo apt update
sudo apt install python3 python3-venv python3-pip

# Node via nvm (apt version is too old)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install --lts
```

**Run:**
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

**Verify:**
- [ ] Setup detects "Platform: WSL"
- [ ] Setup prints `+ Python 3.x`
- [ ] Setup prints `+ Node vXX`
- [ ] Setup prints WSL note at the end (no-browser warning)
- [ ] `./run.sh` starts with `--no-browser` automatically
- [ ] Manually open http://127.0.0.1:7860 in Windows browser — it works
- [ ] All 7 tabs load without console errors

**Common WSL issues:**
- `python3-venv` not installed → `sudo apt install python3-venv`
- Node too old (v12 from apt) → use nvm as above
- Port not accessible from Windows → check Windows Firewall, try `localhost` instead of `127.0.0.1`

---

## Ubuntu (native)

**Prerequisites — run these before setup if needed:**
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip

# Node via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install --lts
```

**Run:**
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

**Verify:**
- [ ] Setup detects "Platform: Linux"
- [ ] Setup prints `+ Python 3.x`
- [ ] Setup prints `+ Node vXX`
- [ ] `./run.sh` starts and opens browser automatically
- [ ] http://127.0.0.1:7860 loads
- [ ] All 7 tabs load without console errors

---

## macOS

**Prerequisites — install Homebrew first if needed:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python node
```

**Run:**
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

**Verify:**
- [ ] Setup detects "Platform: macOS"
- [ ] Setup prints `+ Python 3.x`
- [ ] Setup prints `+ Node vXX`
- [ ] `./run.sh` starts and opens browser automatically
- [ ] http://127.0.0.1:7860 loads
- [ ] All 7 tabs load without console errors

---

## What "all tabs load" means

Open devtools (F12) → Console. There should be no red errors.

| Tab | Quick sanity check |
|-----|--------------------|
| remap | Drop a PNG, results appear |
| extract | Drop a PNG, click extract palette |
| pipeline | Add a step, folder picker works |
| tileset | Drop a PNG, tiles appear |
| palettes | Palette list loads (or empty state) |
| groups | Drop PNGs, groups appear |
| shiny | Mode toggle works |
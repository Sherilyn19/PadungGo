# First GitHub Setup — Windows Beginner Guide

## 1. Create an empty GitHub repository

1. Sign in to GitHub and open <https://github.com/new>.
2. Repository name: `padunggo`.
3. Description: `Open-source Metro Cebu commuter route planner with verified jeepney and bus directions, multiple journey options, fares, and interactive maps.`
4. Select **Public**.
5. **Do not check** the options to initialize README, `.gitignore`, or license: this starter package already includes all three.
6. Create the repository. GitHub will show a page with the empty repository address, e.g. `https://github.com/YOUR_USERNAME/padunggo`.

## 2. Add files using GitHub Desktop (beginner-friendly)

1. Install [GitHub Desktop](https://desktop.github.com/) and sign in.
2. In GitHub Desktop choose **File → Clone repository** and choose `padunggo`. Select your local destination folder.
3. Unzip the starter package; open the folder named `PadungGo_GitHub_Starter` inside it.
4. Copy **the contents** of `PadungGo_GitHub_Starter` into the local `padunggo` clone. Do not copy the enclosing folder as an extra directory. Ensure hidden `.github`, `.editorconfig`, `.gitignore` files are included. Do **not** copy any extracted `.git` directory from elsewhere.
5. In GitHub Desktop, review the changed files; enter commit summary `docs: initialize PadungGo open-source project` and choose **Commit to main**.
6. Click **Push origin** to publish the files.
7. Refresh the `padunggo` repository page and confirm `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/`, `frontend/`, `backend/`, and `.github/` are visible.

## 3. Alternative: Git CLI

With the starter files copied into a local project folder:

```powershell
cd "C:\path\to\padunggo"
git init
git branch -M main
git add .
git commit -m "docs: initialize PadungGo open-source project"
git remote add origin https://github.com/YOUR_USERNAME/padunggo.git
git push -u origin main
```

Do not include any `.env` secrets, API credentials, personal locations, or third-party datasets with unverified redistribution permission.

## 4. After initial push

- Confirm competition registration and exact submission deadlines.
- Verify the initial Cebu City–Mandaue–Lapu-Lapu transport corridor and source evidence before adding trusted route data.
- Scaffold frontend (React + Vite + TypeScript) and backend (Django + DRF) in separate folders.
- Update the README with tested run instructions after each app actually starts locally.

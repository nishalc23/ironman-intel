#!/usr/bin/env bash
#
# Publish the demo dashboard to GitHub Pages.
#
# Builds the frontend in demo mode and force-pushes the result to the
# gh-pages branch, which Pages serves at
# https://nishalc23.github.io/ironman-intel/
#
# Run ./scripts/snapshot.sh first if you want fresh numbers.
#
# Usage: ./scripts/deploy.sh

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

REPO_NAME=$(basename -s .git "$(git config --get remote.origin.url)")

# Where the published build sends requests once someone signs in. Anonymous
# visitors never reach it — they read the bundled snapshot.
API_BASE=${API_BASE:-https://ironman-intel.onrender.com/api}

echo "Building demo bundle…"
VITE_DEMO=true VITE_BASE="/$REPO_NAME/" VITE_API_BASE="$API_BASE" npm --prefix frontend run build

# Pages would otherwise run the output through Jekyll, which drops any path
# starting with an underscore.
touch frontend/dist/.nojekyll

# Publish from a scratch worktree so the checked-out branch is left alone.
WORKTREE=$(mktemp -d)
cleanup() { git worktree remove --force "$WORKTREE" 2>/dev/null || true; }
trap cleanup EXIT

if git show-ref --quiet refs/heads/gh-pages; then
  git worktree add -q "$WORKTREE" gh-pages
else
  git worktree add -q --detach "$WORKTREE"
  git -C "$WORKTREE" checkout -q --orphan gh-pages
fi

# The branch holds only the build, so clear it before copying the new one.
git -C "$WORKTREE" rm -rqf --ignore-unmatch .
cp -R "$ROOT/frontend/dist/." "$WORKTREE/"

git -C "$WORKTREE" add -A
if git -C "$WORKTREE" diff --cached --quiet; then
  echo "No change since the last deploy."
  exit 0
fi

git -C "$WORKTREE" commit -qm "Deploy demo build from $(git rev-parse --short HEAD)"
git -C "$WORKTREE" push -q --force origin gh-pages

echo
echo "Deployed. Live in a minute or so at:"
echo "  https://$(git config --get remote.origin.url | sed -E 's#.*github.com[:/]([^/]+)/.*#\1#').github.io/$REPO_NAME/"

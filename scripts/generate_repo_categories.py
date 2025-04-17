#!/usr/bin/env python3
"""Generate a Markdown file categorizing all GitHub links found in this repo."""

import os
import re
from collections import defaultdict

import requests
import openai

# Predefined categories; tweak to suit your projects.
CATEGORIES = [
    "frontend",
    "backend",
    "infrastructure",
    "devops",
    "documentation",
    "tooling",
    "data science",
    "mobile",
    "security",
    "other"
]

def find_repo_links(root_dir):
    pattern = re.compile(r'https?://github\\.com/([^/\\s]+)/([^/\\s\\)\\]]+)', re.IGNORECASE)
    repos = set()
    for root, _, files in os.walk(root_dir):
        if root.startswith(os.path.join(root_dir, '.github')) or root.startswith(os.path.join(root_dir, 'scripts')):
            continue
        for fn in files:
            if not fn.lower().endswith(('.md', '.rst', '.txt', '.yml', '.yaml', '.py', '.js', '.ts', '.go', '.java', '.sh')):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue
            for m in pattern.finditer(content):
                owner, repo = m.group(1), m.group(2).rstrip('.git')
                repos.add((owner, repo))
    return repos

def classify_repo(owner, repo, github_token, openai_key):
    if not openai_key:
        return "uncategorized"
    desc = ""
    if github_token:
        headers = {'Authorization': f'token {github_token}'}
        resp = requests.get(f'https://api.github.com/repos/{owner}/{repo}', headers=headers)
        if resp.ok:
            desc = resp.json().get('description') or ''
    prompt = (
        f"Classify the following GitHub repository into one of: {', '.join(CATEGORIES)}.\n"
        f"Name: {owner}/{repo}\n"
        f"Description: {desc}\n"
        "Category:"
    )
    try:
        openai.api_key = openai_key
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You classify GitHub repos into predefined categories."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        cat = resp.choices[0].message.content.strip()
        return cat if cat in CATEGORIES else "other"
    except Exception:
        return "other"

def main():
    root = os.getcwd()
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("Warning: OPENAI_API_KEY not set. All repos will be 'uncategorized'.")
    github_token = os.getenv('GITHUB_TOKEN', '')

    repos = find_repo_links(root)
    buckets = defaultdict(list)
    for owner, repo in sorted(repos):
        cat = classify_repo(owner, repo, github_token, openai_key)
        buckets[cat].append(f"https://github.com/{owner}/{repo}")

    with open('REPO_CATEGORIES.md', 'w', encoding='utf-8') as out:
        out.write("# Repository Categories\n\n")
        for cat in sorted(buckets):
            out.write(f"## {cat}\n\n")
            for link in buckets[cat]:
                out.write(f"- {link}\n")
            out.write("\n")
    print("✅ REPO_CATEGORIES.md updated.")

if __name__ == "__main__":
    main()
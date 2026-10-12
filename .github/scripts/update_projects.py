import os
import json
import urllib.request
import re

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "amitpaul2004")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")
PROJECT_LIMIT = 4

# Repositories to exclude from the showcase (e.g., config/profile repo itself)
EXCLUDED_REPOS = {
    USERNAME.lower(),
    f"{USERNAME.lower()}.github.io",
}

# Fallback descriptions for repos where GitHub description field is not set
FALLBACK_DESCRIPTIONS = {
    "agentguard": "AI Agent Security Gateway – Local, policy-first gateway preventing unauthorized tool & file access.",
    "dogtalk-ai": "Experimental Human ↔ Dog Voice Communication Lab with BarkCode pattern analysis.",
}

def get_headers():
    headers = {
        "User-Agent": "GitHub-Action-Recent-Projects",
        "Accept": "application/vnd.github.v3+json",
    }
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    return headers

def fetch_json(url):
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_raw_readme(owner, repo_name, default_branch="main"):
    branches = [default_branch, "main", "master"]
    for branch in branches:
        url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/README.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GitHub-Action-Recent-Projects"})
            with urllib.request.urlopen(req) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            continue
    return None

def extract_description_from_readme(readme_text):
    if not readme_text:
        return ""
    lines = readme_text.splitlines()
    for line in lines:
        line_strip = line.strip()
        # Look for header tagline or first descriptive line
        if line_strip.startswith("# ") and "–" in line_strip:
            return line_strip.split("–", 1)[1].strip()
        if line_strip.startswith("# ") and "-" in line_strip:
            return line_strip.split("-", 1)[1].strip()
        if line_strip.startswith("### ") and not line_strip.startswith("### Run"):
            return line_strip.replace("### ", "").strip()
    # Find first non-empty paragraph without html tags or badges
    for line in lines:
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#") or line_strip.startswith("<") or line_strip.startswith("[!["):
            continue
        if len(line_strip) > 20:
            return line_strip
    return ""

def get_recent_projects():
    url = f"https://api.github.com/users/{USERNAME}/repos?sort=pushed&direction=desc&per_page=20"
    repos = fetch_json(url)
    if not repos or not isinstance(repos, list):
        print("Failed to retrieve repositories or empty list.")
        return []

    active_projects = []
    for repo in repos:
        name = repo.get("name", "")
        # Filter out forks, archived repos, private repos, and profile repo
        if repo.get("fork") or repo.get("archived") or repo.get("private"):
            continue
        if name.lower() in EXCLUDED_REPOS:
            continue

        # Get tech stack / languages
        languages_url = repo.get("languages_url")
        tech_list = []
        if languages_url:
            langs = fetch_json(languages_url)
            if isinstance(langs, dict) and langs:
                tech_list = list(langs.keys())[:3]
        
        # Fallback to primary language if languages_url didn't return list
        if not tech_list and repo.get("language"):
            tech_list = [repo["language"]]
        
        # Add topics if available and space allows
        topics = repo.get("topics", [])
        if topics and len(tech_list) < 3:
            for t in topics:
                t_clean = t.replace("-", " ").capitalize()
                if t_clean not in tech_list and len(tech_list) < 3:
                    tech_list.append(t_clean)

        description = repo.get("description") or ""
        if not description:
            # Check fallback dict
            description = FALLBACK_DESCRIPTIONS.get(name.lower(), "")
        if not description:
            # Try fetching from README
            readme_text = fetch_raw_readme(USERNAME, name, repo.get("default_branch", "main"))
            extracted = extract_description_from_readme(readme_text)
            if extracted:
                description = extracted
            else:
                description = f"Project built with {repo.get('language') or 'code'}."

        # Clean up any markdown link syntax or pipes in description
        description = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', description)
        description = description.replace("|", "\\|").replace("\n", " ").strip()

        # Truncate clean description if too long
        if len(description) > 130:
            description = description[:127].rstrip() + "..."

        homepage = repo.get("homepage")
        if homepage:
            homepage = homepage.strip()
            if not (homepage.startswith("http://") or homepage.startswith("https://")):
                homepage = ""

        # Choose an icon based on primary language or name
        lang_lower = (repo.get("language") or "").lower()
        icon = "🚀"
        if "python" in lang_lower:
            icon = "🐍"
        elif "javascript" in lang_lower or "typescript" in lang_lower:
            icon = "⚡"
        elif "html" in lang_lower or "css" in lang_lower:
            icon = "🌐"
        elif "ai" in name.lower() or "bot" in name.lower() or "model" in name.lower():
            icon = "🤖"

        active_projects.append({
            "name": name,
            "full_name": repo.get("full_name", f"{USERNAME}/{name}"),
            "html_url": repo.get("html_url", f"https://github.com/{USERNAME}/{name}"),
            "description": description,
            "tech": " · ".join(tech_list) if tech_list else "Code",
            "homepage": homepage,
            "icon": icon,
        })

        if len(active_projects) >= PROJECT_LIMIT:
            break

    return active_projects

def build_table_markdown(projects):
    if not projects:
        return ""

    lines = [
        "| 🗂️ Project | 📝 Description | 🛠️ Tech | 🔗 Links |",
        "|:----------:|:--------------|:-------:|:--------:|",
    ]

    for p in projects:
        project_cell = f"{p['icon']} **[{p['name']}]({p['html_url']})**"
        desc_cell = p['description']
        tech_cell = p['tech']
        links_cell = f"[![Repo](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github)]({p['html_url']})"
        if p['homepage']:
            links_cell += f"&nbsp;[![Demo](https://img.shields.io/badge/Live_Demo-007ACC?style=flat-square&logo=googlechrome&logoColor=white)]({p['homepage']})"

        lines.append(f"| {project_cell} | {desc_cell} | {tech_cell} | {links_cell} |")

    return "\n".join(lines)

def update_readme():
    readme_file = os.path.abspath(README_PATH)
    if not os.path.exists(readme_file):
        print(f"README file not found at {readme_file}")
        return False

    with open(readme_file, "r", encoding="utf-8") as f:
        content = f.read()

    marker_start = "<!-- RECENT-PROJECTS:START -->"
    marker_end = "<!-- RECENT-PROJECTS:END -->"

    if marker_start not in content or marker_end not in content:
        print("Recent projects markers not found in README.md")
        return False

    projects = get_recent_projects()
    if not projects:
        print("No active projects found to insert.")
        return False

    table_md = build_table_markdown(projects)
    replacement = f"{marker_start}\n{table_md}\n{marker_end}"

    pattern = re.compile(f"{re.escape(marker_start)}.*?{re.escape(marker_end)}", re.DOTALL)
    new_content = pattern.sub(replacement, content)

    if new_content == content:
        print("README is already up to date with the latest projects.")
        return False

    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Successfully updated README.md with {len(projects)} active projects!")
    return True

if __name__ == "__main__":
    update_readme()

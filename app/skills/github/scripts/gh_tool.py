import argparse
import os
from github import Github
from github import Auth

def get_github_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set.")
        return None
    auth = Auth.Token(token)
    return Github(auth=auth)

def list_repos(args):
    g = get_github_client()
    if not g: return
    
    user = g.get_user()
    print(f"Repositories for {user.login}:")
    for repo in user.get_repos(sort="updated", direction="desc")[:args.limit]:
        print(f"- {repo.full_name} ({repo.html_url}) - ⭐ {repo.stargazers_count}")

def get_repo_issues(args):
    g = get_github_client()
    if not g: return
    
    try:
        repo = g.get_repo(args.repo)
        print(f"Issues for {repo.full_name}:")
        issues = repo.get_issues(state=args.state)[:args.limit]
        for issue in issues:
            print(f"#{issue.number} {issue.title} [{issue.state}] - {issue.html_url}")
    except Exception as e:
        print(f"Error: {e}")

def create_issue(args):
    g = get_github_client()
    if not g: return

    try:
        repo = g.get_repo(args.repo)
        issue = repo.create_issue(title=args.title, body=args.body)
        print(f"Created issue #{issue.number}: {issue.html_url}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="GitHub CLI Tool")
    subparsers = parser.add_subparsers()

    # List Repos
    parser_repos = subparsers.add_parser("repos", help="List recent repositories")
    parser_repos.add_argument("--limit", type=int, default=10, help="Max repos to list")
    parser_repos.set_defaults(func=list_repos)

    # List Issues
    parser_issues = subparsers.add_parser("issues", help="List issues for a repo")
    parser_issues.add_argument("repo", help="Repository (owner/name)")
    parser_issues.add_argument("--state", choices=["open", "closed", "all"], default="open")
    parser_issues.add_argument("--limit", type=int, default=10)
    parser_issues.set_defaults(func=get_repo_issues)

    # Create Issue
    parser_create = subparsers.add_parser("create-issue", help="Create an issue")
    parser_create.add_argument("repo", help="Repository (owner/name)")
    parser_create.add_argument("title", help="Issue Title")
    parser_create.add_argument("body", help="Issue Body")
    parser_create.set_defaults(func=create_issue)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

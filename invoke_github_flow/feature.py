import webbrowser
import os
from django.utils.text import slugify
from invoke import task
from git import Repo
from django.conf import settings


def _connect_github():
    from github import Github
    token_path = os.path.join(os.getcwd(), '.githubtoken')
    print("Connecting to GitHub...")
    try:
        with open(token_path, "r") as f:
            g = Github(login_or_token=f.read().strip())
        user = g.get_user('moberries')
        return user.get_repo(name='backend')
    except FileNotFoundError:
        exit("Github token not found. Create one here https://github.com/settings/tokens "
             "and place it in the root directory with the filename .githubtoken")


@task(help={
    "update": "Pull the current origin master state?"
})
def start(context, update=True):
    """Create new feature by name"""
    issue_number = input("Github issue number: ")

    grepo = _connect_github()
    if issue_number:
        issue = grepo.get_issue(int(issue_number))
        print("Issue found: %s" % issue.title)
        issue_title = issue.title
    else:
        issue_title = ""
    name = slugify(input("Human readable branch name[default - built from issue name]: ") or issue_title)
    if not name:
        exit("Feature name was empty")
    branch_name = "%s-%s" % (issue_number, name) if issue_number else name

    repo = Repo(settings.PROJECT_ROOT)

    repo.heads.master.checkout()
    if update:
        origin = repo.remotes['origin']
        origin.pull("--rebase")
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    print("New branch based on master created and checked out: %s" % branch_name)


@task(help={
    "delete_branch": "Delete branch? If used with -m, removes remote branch also",
    "merge": "Merge pull request?"
})
def finish(context, delete_branch=False, merge=False):
    """Finish current feature"""
    repo = Repo(settings.PROJECT_ROOT)
    current_branch = repo.head.reference
    if current_branch.name in ['release', 'staging', 'master']:
        exit("Not on a feature branch")

    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    origin = repo.remotes.origin
    if current_branch.name not in origin.refs or origin.refs[current_branch.name].commit != current_branch.commit:
        exit("Won't finish, feature is not pushed")

    feature_branch_name = current_branch.name

    if merge:
        grepo, pr = pull_request(context)
        if not pr.mergeable:
            exit("PR %s is not mergeable" % pr.number)
        print("Getting checks statuses...")
        try:
            last_status = grepo.get_commit(str(current_branch.name)).get_statuses()[0]
            print("%s. See for more %s" % (last_status.description, last_status.target_url))
            if last_status.state != 'success':
                checks_passed = False
            else:
                checks_passed = True

        except IndexError:
            checks_passed = True

        if checks_passed:
            print("Checks passed, merging...")
            pr.merge()
            print("Merged")
            if delete_branch:
                origin.push(":" + feature_branch_name)
                print("Remote branch removed")
        else:
            print("Checks didn't pass, won't merge")
            return

    repo.heads.master.checkout()
    origin.pull("--rebase")
    if delete_branch:
        repo.delete_head(feature_branch_name)
        print("Local branch removed")
    print("Done")


@task(help={
    "rebase_first": "Rebase before publishing",
    "pull_request_create": "Create pull request"
})
def publish(context, rebase_first=True, pull_request_create=False):
    """Publish feature"""
    if rebase_first:
        rebase(context)

    repo = Repo(settings.PROJECT_ROOT)
    current_branch = repo.head.reference
    if current_branch.name in ['release', 'staging', 'master']:
        exit("Not on a feature branch")

    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    origin = repo.remotes.origin
    print("Pushing to github...")
    origin.push()
    print("Setting tracking...")
    remote_branch = origin.refs[current_branch.name]
    current_branch.set_tracking_branch(remote_branch)
    if pull_request_create:
        pull_request(context)
    print("Done")


@task
def rebase(context):
    """Rebase current feature on master"""
    repo = Repo(settings.PROJECT_ROOT)
    current_branch = repo.head.reference
    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    if current_branch.name in ['release', 'staging', 'master']:
        exit("Not on a feature branch")

    print("Updating master...")
    master = repo.heads.master
    master.checkout()
    origin = repo.remotes.origin
    print("Pulling...")
    origin.pull("--rebase")

    print("Rebasing current branch")
    current_branch.checkout()
    repo.git.rebase('master')

    print("Done.")


@task
def pull_request(context):
    """Create pull request"""

    print("Creating pull request...")
    repo = Repo(settings.PROJECT_ROOT)

    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    origin = repo.remotes.origin
    current_branch = repo.head.reference

    if current_branch.name in ['release', 'staging', 'master']:
        exit("Not on a feature branch")

    if current_branch.name not in origin.refs or origin.refs[current_branch.name].commit != current_branch.commit:
        exit("Won't create pull request, feature is not pushed")

    grepo = _connect_github()

    try:
        issue_number = int(current_branch.name.split("-")[0])
    except (ValueError, IndexError):
        print("Can't extract issue number from %s" % current_branch.name)
        issue_number = None

    existing_pulls = list(grepo.get_pulls(head="moberries:" + current_branch.name))
    if len(existing_pulls):
        pr = existing_pulls[0]
        print("Won't create pull request, already exists: %s" % pr.html_url)

        return grepo, pr

    title = current_branch.name.replace("-", " ").capitalize()
    pr = grepo.create_pull(
        title=title,
        body=input("Pull request description: ") + (" #%s" % issue_number if issue_number else ""),
        head=current_branch.name,
        base='master',
    )
    print("Successfully created PR: %s" % pr.html_url)
    webbrowser.open(pr.html_url)
    return grepo, pr

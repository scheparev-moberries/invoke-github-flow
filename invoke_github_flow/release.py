from git import Repo
from invoke import task
from datetime import datetime
import os


@task(help={
    "push": "Push changes to the server",
    "master_checkout": "Return to master after push"
})
def stage(context, push=False, master_checkout=True):
    """Merge master into staging and push"""

    repo = Repo(os.getcwd())
    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    print("Updating master...")
    master = repo.heads.master
    master.checkout()
    origin = repo.remotes['origin']
    origin.pull("--rebase")

    print("Updating staging...")
    staging = repo.heads.staging
    staging.checkout()
    origin.pull("--rebase")

    print("Merging...")
    repo.git.merge('master')
    if push:
        sure = input("Are you sure? (Y/n):")
        if sure == "Y":
            origin.push()
    if master_checkout:
        master.checkout()
    print("Done.")


@task(help={
    "push": "Push changes to the server",
})
def start(context, push=False):
    """Start release"""

    repo = Repo(os.getcwd())
    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    print("Updating master...")
    master = repo.heads.master
    master.checkout()
    origin = repo.remotes['origin']
    origin.pull("--rebase")

    print("Updating release...")
    release = repo.heads.release
    release.checkout()
    origin.pull("--rebase")

    print("Merging...")
    repo.git.merge('master')
    if push:
        sure = input("Are you sure? (Y/n):")
        if sure == "Y":
            origin.push()
    print("Done.")


@task
def publish(context):
    """Publish release"""

    repo = Repo(os.getcwd())
    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    origin = repo.remotes['origin']

    print("Updating release...")
    release = repo.heads.release
    release.checkout()
    origin.push()
    print("Done.")


@task
def finish(context):
    """Finish and tag release"""
    repo = Repo(os.getcwd())

    if repo.is_dirty():
        if repo.untracked_files:
            print("Untracked changes: %s" % ",".join(repo.untracked_files))
        exit("Won't proceed, index is not clean")

    current_branch = repo.head.reference
    if current_branch.name != 'release':
        exit("Not on release branch")

    tag_name = open("version.txt").read()

    origin = repo.remotes['origin']
    new_tag = repo.create_tag(tag_name, message='Automatic tag "{0}"'.format(tag_name))

    print("Merging...")
    staging = repo.heads.staging
    master = repo.heads.master

    master.checkout()
    repo.git.merge('release')
    repo.git.merge('staging')
    origin.push()
    origin.push(new_tag)

    staging.checkout()
    origin.push()

#!/usr/bin/env python3

import os
import sys

from argparse import ArgumentParser
from PIL import Image, ImageOps
from datetime import datetime, date, time, timezone, timedelta
from git import Repo, Actor


def convert_image(im):
    "Convert an image to a single channel with 0=white/transparent to 255=black"
    im = im.convert('RGBA')

    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.paste(im, mask=im.getchannel('A'))
    return ImageOps.invert(bg.convert('L'))


def process_image(im, start_date, scale=1):
    "Process a single channel image into a list of dates and target commit counts"
    width, height = im.size
    counts = {}
    date = start_date
    for x in range(width):
        for y in range(height):
            pix = im.getpixel((x, y))
            n = (pix * (scale + 1)) // 256
            if n > 0:
                counts[date] = n
            date += timedelta(days=1)
    return counts


def create_commit(repo, dir, commit_date, nth, author=None):
    fname = os.path.join(dir, 'dummy.txt')
    dt = datetime.combine(commit_date, time(12, 0, tzinfo=timezone.utc)) + timedelta(minutes=nth)
    with open(fname, 'w') as f:
        f.write(f"Commit number {nth + 1} for {commit_date.isoformat()}\n")
    repo.index.add([fname])
    repo.index.commit(f"Commit for {commit_date.isoformat()} #{nth + 1}",
                      author_date=dt,
                      author=author,
                      skip_hooks=True)


def create_commits(dir, counts, name=None, email=None):
    author = None
    if name is not None and email is not None:
        author = Actor(name, email)
    with Repo.init(dir) as repo:
        for d in sorted(counts.keys()):
            n = counts[d]
            for i in range(n):
                create_commit(repo, dir, d, i, author)


def main(image, dir='repo', start_date=None, num_commits=1, name=None, email=None):
    if start_date is None:
        start_date = date.today()
        while start_date.weekday() != 6:
            start_date -= timedelta(days=1)
        start_date -= timedelta(days=52*7)
    im = Image.open(image)
    im = convert_image(im)
    counts = process_image(im, start_date, scale=num_commits)
    path = os.path.join(os.getcwd(), dir)
    os.makedirs(path, exist_ok=True)
    create_commits(path, counts, name=name, email=email)
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate GitHub contributions from an image")
    parser.add_argument("image", help="Input image file")
    parser.add_argument("--dir", default="repo", help="Directory to create the repo in (default: repo)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD), defaults to 52 weeks ago on a Sunday")
    parser.add_argument("--num-commits", type=int, default=1, help="Number of commits per darkest pixel (default: 1)")
    parser.add_argument("--name", help="Name to use for commits (if set, must also set email)")
    parser.add_argument("--email", help="Email to use for commits (if set, must also set name)")
    args = parser.parse_args()

    start_date = None
    if args.start_date:
        start_date = date.fromisoformat(args.start_date)

    sys.exit(main(**vars(args)))

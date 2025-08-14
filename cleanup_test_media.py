#!/bin/bash
"""
Test Media Cleanup Script for Videoflix

This script provides various cleanup options for test media files.
Run with: docker-compose exec web python cleanup_test_media.py [options]
"""

import os
import shutil
import glob
import argparse
from pathlib import Path


def cleanup_test_videos():
    """Remove all test video files."""
    patterns = [
        '/app/test_media/videos/*',
        '/app/media/test_*',
        '/tmp/videoflix_test_*',
    ]
    
    removed_count = 0
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    removed_count += 1
                    print(f"Removed file: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    removed_count += 1
                    print(f"Removed directory: {path}")
            except Exception as e:
                print(f"Error removing {path}: {e}")
    
    return removed_count


def cleanup_test_directories():
    """Remove all test directories."""
    directories = [
        '/app/test_media',
        '/app/media/test_videos',
    ]
    
    removed_count = 0
    for directory in directories:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                removed_count += 1
                print(f"Removed directory: {directory}")
            except Exception as e:
                print(f"Error removing {directory}: {e}")
    
    return removed_count


def cleanup_temp_files():
    """Remove temporary files created during testing."""
    patterns = [
        '/tmp/videoflix_test_*',
        '/tmp/test_*',
    ]
    
    removed_count = 0
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    removed_count += 1
                    print(f"Removed temp file: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    removed_count += 1
                    print(f"Removed temp directory: {path}")
            except Exception as e:
                print(f"Error removing {path}: {e}")
    
    return removed_count


def get_test_media_info():
    """Get information about current test media files."""
    patterns = [
        '/app/test_media/**/*',
        '/app/media/test_*',
        '/tmp/videoflix_test_*',
    ]
    
    files = []
    total_size = 0
    
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isfile(path):
                size = os.path.getsize(path)
                files.append((path, size))
                total_size += size
    
    return files, total_size


def main():
    parser = argparse.ArgumentParser(description='Cleanup test media files')
    parser.add_argument('--videos', action='store_true', help='Remove test video files')
    parser.add_argument('--directories', action='store_true', help='Remove test directories')
    parser.add_argument('--temp', action='store_true', help='Remove temporary files')
    parser.add_argument('--all', action='store_true', help='Remove everything')
    parser.add_argument('--info', action='store_true', help='Show info about test files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed')
    
    args = parser.parse_args()
    
    if args.info:
        files, total_size = get_test_media_info()
        print(f"Found {len(files)} test media files")
        print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
        for path, size in files:
            print(f"  {path} ({size} bytes)")
        return
    
    if args.dry_run:
        print("DRY RUN - Would remove:")
        files, _ = get_test_media_info()
        for path, _ in files:
            print(f"  {path}")
        return
    
    total_removed = 0
    
    if args.all or args.videos:
        removed = cleanup_test_videos()
        total_removed += removed
        print(f"Removed {removed} video files/directories")
    
    if args.all or args.directories:
        removed = cleanup_test_directories()
        total_removed += removed
        print(f"Removed {removed} test directories")
    
    if args.all or args.temp:
        removed = cleanup_temp_files()
        total_removed += removed
        print(f"Removed {removed} temporary files/directories")
    
    if not any([args.videos, args.directories, args.temp, args.all]):
        print("No cleanup action specified. Use --help for options.")
        return
    
    print(f"Total items removed: {total_removed}")


if __name__ == "__main__":
    main()

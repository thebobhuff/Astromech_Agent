import os
import argparse
from pathlib import Path

# Default Google Drive mount point on Windows
DRIVE_PATH = Path('G:/My Drive')

def list_files(directory=''):
    target = DRIVE_PATH / directory
    if not target.exists():
        print(f'Error: Path {target} does not exist.')
        return
    
    print(f'Contents of {target}:')
    for item in target.iterdir():
        type_str = '[DIR]' if item.is_dir() else '[FILE]'
        print(f' {type_str} {item.name}')

def main():
    parser = argparse.ArgumentParser(description='Local Google Drive Tool')
    subparsers = parser.add_subparsers(dest='command')
    
    list_parser = subparsers.add_parser('list', help='List files in a directory')
    list_parser.add_argument('path', nargs='?', default='', help='Relative path in Drive')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_files(args.path)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import os
import shutil
import datetime
import argparse
import hashlib
from pathlib import Path
import logging
import time
import re


FILE_CATEGORIES = {
    'Dokumente': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', 
                 '.xlsx', '.ppt', '.pptx', '.csv', '.ods', '.odp'],
    
    'Bilder': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff', 
              '.ico', '.webp', '.heic', '.raw', '.psd', '.ai'],
    
    'Videos': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', 
              '.m4v', '.mpg', '.mpeg', '.3gp'],
    
    'Audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a', 
              '.mid', '.midi'],
    
    'Archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso'],
    
    'Code': ['.py', '.java', '.cpp', '.c', '.h', '.hpp', '.js', '.html', 
            '.css', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.json', 
            '.xml', '.sql', '.sh', '.bat', '.ps1'],
    
    'Programme': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm'],
    
    'Andere': []
}


def setup_logger():
    logger = logging.getLogger("file_organizer")
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def get_file_hash(file_path):
    hash_md5 = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Fehler beim Berechnen des Hashes für {file_path}: {e}")
        return None


def get_category_for_extension(ext):
    ext = ext.lower()
    
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    
    return "Andere"


def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Verzeichnis erstellt: {directory}")


def organize_files_by_type(source_dir, destination_dir=None, preview=False, 
                         include_date=False, handle_duplicates="rename"):
    if not destination_dir:
        destination_dir = source_dir
    
    stats = {
        "verschoben": 0,
        "übersprungen": 0,
        "fehler": 0,
        "kategorien": {}
    }
    
    file_hashes = {}
    
    if not preview:
        for category in FILE_CATEGORIES.keys():
            create_directory_if_not_exists(os.path.join(destination_dir, category))
    
    for root, _, files in os.walk(source_dir):
        for filename in files:
            source_path = os.path.join(root, filename)
            
            if any(category in root for category in FILE_CATEGORIES.keys()):
                stats["übersprungen"] += 1
                continue
            
            try:
                _, ext = os.path.splitext(filename)
                category = get_category_for_extension(ext)
                
                if category not in stats["kategorien"]:
                    stats["kategorien"][category] = 0
                
                target_dir = os.path.join(destination_dir, category)
                
                if include_date:
                    file_time = os.path.getmtime(source_path)
                    date_str = datetime.datetime.fromtimestamp(file_time).strftime('%Y-%m')
                    target_dir = os.path.join(target_dir, date_str)
                    
                    if not preview:
                        create_directory_if_not_exists(target_dir)
                
                target_path = os.path.join(target_dir, filename)
                
                if os.path.exists(target_path):
                    file_hash = get_file_hash(source_path)
                    
                    if file_hash and file_hash in file_hashes:
                        if handle_duplicates == "skip":
                            logger.info(f"Duplikat übersprungen: {filename}")
                            stats["übersprungen"] += 1
                            continue
                        elif handle_duplicates == "rename":
                            name, ext = os.path.splitext(filename)
                            timestamp = int(time.time())
                            new_filename = f"{name}_{timestamp}{ext}"
                            target_path = os.path.join(target_dir, new_filename)
                            logger.info(f"Duplikat umbenannt: {filename} -> {new_filename}")
                    
                    file_hashes[file_hash] = target_path
                
                if preview:
                    logger.info(f"VORSCHAU: {source_path} -> {target_path}")
                else:
                    shutil.move(source_path, target_path)
                    logger.info(f"Verschoben: {filename} -> {category}")
                
                stats["verschoben"] += 1
                stats["kategorien"][category] += 1
                
            except Exception as e:
                logger.error(f"Fehler bei {filename}: {e}")
                stats["fehler"] += 1
    
    return stats


def print_summary(stats):
    logger.info("\n" + "="*50)
    logger.info("ZUSAMMENFASSUNG")
    logger.info("="*50)
    logger.info(f"Dateien verschoben: {stats['verschoben']}")
    logger.info(f"Dateien übersprungen: {stats['übersprungen']}")
    logger.info(f"Fehler aufgetreten: {stats['fehler']}")
    
    if stats["kategorien"]:
        logger.info("\nDateien pro Kategorie:")
        for category, count in stats["kategorien"].items():
            logger.info(f"  {category}: {count}")
    
    logger.info("="*50)


def main():
    parser = argparse.ArgumentParser(description="Organisiert Dateien nach Typ in Ordner")
    parser.add_argument("source", help="Quellverzeichnis mit den zu organisierenden Dateien")
    parser.add_argument("-d", "--destination", help="Zielverzeichnis (Standard: Quellverzeichnis)")
    parser.add_argument("-p", "--preview", action="store_true", 
                        help="Vorschaumodus (keine Änderungen vornehmen)")
    parser.add_argument("--date", action="store_true", 
                        help="Nach Datum in Unterordnern organisieren")
    parser.add_argument("--duplicates", choices=["rename", "skip", "replace"], 
                        default="rename", help="Strategie für Duplikate")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.source):
        logger.error(f"Fehler: Das Verzeichnis '{args.source}' existiert nicht.")
        return 1
    
    logger.info(f"Starte Dateiorganisation von: {args.source}")
    if args.preview:
        logger.info("VORSCHAUMODUS AKTIV - Es werden keine Dateien verschoben")
    
    start_time = time.time()
    stats = organize_files_by_type(
        args.source, 
        args.destination, 
        args.preview,
        args.date,
        args.duplicates
    )
    end_time = time.time()
    
    print_summary(stats)
    logger.info(f"Ausführungszeit: {end_time - start_time:.2f} Sekunden")
    
    return 0


if __name__ == "__main__":
    logger = setup_logger()
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nProgramm durch Benutzer abgebrochen.")
        exit(1)
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
        exit(1)
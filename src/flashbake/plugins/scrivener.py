#    copyright 2025 Thomas Gideon, Ian Paul
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

"""
scrivener.py - Modern cross-platform Scrivener flashbake plugin

This plugin works directly with Scrivener's .scriv file format which is
cross-platform compatible between Mac, Windows, and Linux. It avoids GUI
automation and external dependencies for maximum reliability.
"""

from flashbake.plugins import AbstractFilePlugin, AbstractMessagePlugin
import fnmatch
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def find_scrivener_projects(hot_files, config, flush_cache=False):
    """Find all .scriv projects in the monitored files."""
    if flush_cache:
        config.scrivener_projects = None

    if config.scrivener_projects is None:
        scrivener_projects = []
        for f in hot_files.control_files:
            if fnmatch.fnmatch(f, '*.scriv'):
                scrivener_projects.append(f)
        config.scrivener_projects = scrivener_projects

    return config.scrivener_projects


def find_scrivener_project_contents(hot_files, scrivener_project):
    """Recursively find all files within a Scrivener project."""
    project_path = Path(hot_files.project_dir) / scrivener_project
    
    if not project_path.exists():
        logging.warning(f"Scrivener project not found: {project_path}")
        return
        
    for file_path in project_path.rglob('*'):
        if file_path.is_file():
            # Get relative path from project directory
            rel_path = file_path.relative_to(Path(hot_files.project_dir))
            yield str(rel_path)


def extract_text_from_rtf(rtf_content):
    """Extract plain text from RTF content."""
    if not rtf_content:
        return ""
    
    # Simple RTF parsing - removes RTF control codes
    # This regex removes RTF control words and groups
    rtf_pattern = re.compile(r'\\[a-zA-Z]+\d*\s?|\{|\}|\\\'[0-9a-fA-F]{2}')
    
    # Remove RTF header and control codes
    text = rtf_pattern.sub('', rtf_content)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def count_words(text):
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def get_wordcount_cache_path(project_path):
    """Get the path for storing word count cache."""
    project_name = project_path.stem
    cache_dir = project_path.parent
    return cache_dir / f".{project_name}.flashbake.wordcount.json"


class ScrivenerFile(AbstractFilePlugin):
    """Plugin to monitor all files within Scrivener projects."""

    def __init__(self, plugin_spec):
        AbstractFilePlugin.__init__(self, plugin_spec)
        self.share_property('scrivener_projects')
        self.share_property('scrivener_project_dir')

    def pre_process(self, hot_files, config):
        """Add all Scrivener project files to monitoring."""
        # Store project directory for use by message plugin
        config.scrivener_project_dir = hot_files.project_dir
        
        for project in find_scrivener_projects(hot_files, config):
            logging.debug(f"ScrivenerFile: adding project '{project}'")
            
            # Add all files within the project
            for file_path in find_scrivener_project_contents(hot_files, project):
                hot_files.control_files.add(file_path)
                logging.debug(f"  - monitoring: {file_path}")

    def post_process(self, to_commit, hot_files, config):
        """Clean up any deleted files from version control."""
        import flashbake.commit
        flashbake.commit.purge(config, hot_files)


class ScrivenerWordCount(AbstractMessagePlugin):
    """Plugin to track and report word counts for Scrivener projects."""

    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.share_property('scrivener_projects')
        self.share_property('scrivener_project_dir')

    def addcontext(self, message_file, config):
        """Add word count information to commit message."""
        try:
            projects = find_scrivener_projects(None, config)  # Use cached projects
            if not projects:
                return True
            
            # Get project directory from shared property
            if not hasattr(config, 'scrivener_project_dir') or config.scrivener_project_dir is None:
                logging.warning("Scrivener project directory not available")
                return False
            
            for project_name in projects:
                project_path = Path(config.scrivener_project_dir) / project_name
                
                # Try to get word count from Scrivener's project file
                word_counts = self._get_word_counts_from_project(project_path)
                
                if word_counts:
                    message_file.write(f"Scrivener Project: {project_name}\n")
                    
                    if 'draft' in word_counts:
                        message_file.write(f"  Draft word count: {word_counts['draft']:,}\n")
                    
                    if 'total' in word_counts:
                        message_file.write(f"  Total word count (including notes): {word_counts['total']:,}\n")
                    
                    # Show word count changes if we have historical data
                    changes = self._calculate_word_count_changes(project_path, word_counts)
                    if changes:
                        for section, change in changes.items():
                            if change != 0:
                                sign = "+" if change > 0 else ""
                                message_file.write(f"  {section.title()} change: {sign}{change:,} words\n")
                    
                    message_file.write("\n")
            
            return True
            
        except Exception as e:
            logging.warning(f"Error generating Scrivener word count: {e}")
            return False

    def _get_word_counts_from_project(self, project_path):
        """Extract word counts from Scrivener project XML."""
        if not project_path.exists():
            return None
        
        # Look for the main project file
        scrivx_files = list(project_path.glob("*.scrivx"))
        if not scrivx_files:
            logging.debug(f"No .scrivx file found in {project_path}")
            return None
        
        scrivx_file = scrivx_files[0]
        
        try:
            tree = ET.parse(scrivx_file)
            root = tree.getroot()
            
            word_counts = {}
            
            # Look for word count elements in the XML
            for element in root.iter():
                if element.tag == 'DraftWordCount' and element.text:
                    word_counts['draft'] = int(element.text)
                elif element.tag == 'TotalWordCount' and element.text:
                    word_counts['total'] = int(element.text)
                elif element.tag == 'OtherWordCount' and element.text:
                    word_counts['notes'] = int(element.text)
            
            # If we didn't find XML word counts, calculate manually
            if not word_counts:
                word_counts = self._calculate_word_counts_manually(project_path)
            
            return word_counts
            
        except (ET.ParseError, ValueError, OSError) as e:
            logging.debug(f"Error parsing {scrivx_file}: {e}")
            return self._calculate_word_counts_manually(project_path)

    def _calculate_word_counts_manually(self, project_path):
        """Manually calculate word counts by parsing RTF files."""
        draft_words = 0
        notes_words = 0
        
        # Look for document files in typical Scrivener structure
        files_dir = project_path / "Files" / "Data"
        if not files_dir.exists():
            # Try older structure
            files_dir = project_path / "Files" / "Docs"
        
        if files_dir.exists():
            for rtf_file in files_dir.rglob("*.rtf"):
                try:
                    content = rtf_file.read_text(encoding='utf-8', errors='ignore')
                    text = extract_text_from_rtf(content)
                    word_count = count_words(text)
                    
                    # Heuristic: files with numbers are usually draft content,
                    # files with _notes or _synopsis are metadata
                    filename = rtf_file.stem.lower()
                    if '_notes' in filename or '_synopsis' in filename:
                        notes_words += word_count
                    else:
                        draft_words += word_count
                        
                except (OSError, UnicodeDecodeError) as e:
                    logging.debug(f"Error reading {rtf_file}: {e}")
                    continue
        
        return {
            'draft': draft_words,
            'notes': notes_words,
            'total': draft_words + notes_words
        }

    def _calculate_word_count_changes(self, project_path, current_counts):
        """Calculate changes in word count since last commit."""
        cache_path = get_wordcount_cache_path(project_path)
        
        try:
            # Load previous counts
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    previous_counts = json.load(f)
            else:
                previous_counts = {}
            
            # Calculate changes
            changes = {}
            for section, current in current_counts.items():
                previous = previous_counts.get(section, 0)
                changes[section] = current - previous
            
            # Save current counts for next time
            with open(cache_path, 'w') as f:
                json.dump(current_counts, f)
            
            return changes
            
        except (OSError, json.JSONDecodeError) as e:
            logging.debug(f"Error handling word count cache: {e}")
            return {}
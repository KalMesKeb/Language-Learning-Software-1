# models.py
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Alignment:
    eng: str
    amh: str

@dataclass
class Sentence:
    id: int
    english: str
    amharic: str
    alignment: List[Dict]
    notes: str = ""

@dataclass
class Lesson:
    id: int
    title: str
    level: str
    sentences: List[Sentence]
    vocabulary: List[Dict] = field(default_factory=list)

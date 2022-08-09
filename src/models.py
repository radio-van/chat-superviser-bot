from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Ratio:
    gallery: float
    link: float
    media: float
    text: float

    @property
    def effective(self):
        # consider only ratios that are > 0
        effective_ratios = [r for r in (self.gallery, self.media, self.link, self.text) if r > 0]

        # calculate weighted ratio of the whole message
        return sum(effective_ratios)/len(effective_ratios) if effective_ratios else 0


@dataclass
class RecentMessage:
    id: int
    link: Optional[str] = None
    media_id: Optional[int] = None
    media_group_id: Optional[int] = None
    text: Optional[str] = None

    duplicate_of: List[int] = field(default_factory=list)
    has_duplicate: List[int] = field(default_factory=list)

    relation_graph: dict = field(default_factory=dict)

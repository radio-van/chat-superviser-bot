from dataclasses import dataclass
from typing import Optional


@dataclass
class RecentMessage:
    id: int
    link: Optional[str] = None
    media_id: Optional[int] = None
    media_group_id: Optional[int] = None
    text: Optional[str] = None

    duplicate_of: Optional[int] = None
    has_duplicate: Optional[int] = None

    relation_graph: dict = {}
